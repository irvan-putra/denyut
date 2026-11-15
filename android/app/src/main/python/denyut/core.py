"""Core message routing. No transport code here.

Incoming text is parsed into (command, payload). A registered skill may
claim a command. Unclaimed text goes to the configured model backend, or
to a help reply when no model is configured.

Approval boundaries: a skill may ask for confirmation before doing
something consequential (delete, spend, send). It returns
Confirm(action_id, question); the core holds it as pending and the next
yes/no from the same sender resolves it. Nothing consequential happens
without an explicit yes.
"""

import time

from .behavior import load_behavior
from .models import build_backend
from .skills.notes import NotesSkill
from .skills.reminders import RemindersSkill

HELP = """Available commands:
/help - this message
/note <text> - remember something
/notes - show your notes
/done <n> - archive note n
/remind <delay> <text> - remind in 30, 90s, 45m, 2h or 1d
/reminders - show pending reminders
/cancel <n> - cancel reminder n
/echo <text> - say it back
Anything else is answered by the model, if one is configured."""


class Confirm:
    """A skill's request for an explicit yes before acting."""

    def __init__(self, question, on_yes, on_no=None):
        self.question = question
        self.on_yes = on_yes
        self.on_no = on_no


def parse_message(text):
    text = (text or "").strip()
    if text.startswith("/"):
        parts = text.split(None, 1)
        return parts[0].lower(), (parts[1] if len(parts) > 1 else "")
    return None, text


class Assistant:
    def __init__(self, behavior_path=None, store_dir="."):
        self.config = load_behavior(behavior_path)
        self.name = self.config.get("assistant", {}).get("name", "Denyut")
        self.system_prompt = self.config.get("assistant", {}).get(
            "system_prompt", "")
        self.backend = build_backend(self.config)
        self.skills = []
        self.reminders = None
        skills_cfg = self.config.get("skills", {})
        import os
        if skills_cfg.get("notes", {}).get("enabled"):
            store = os.path.join(
                store_dir, skills_cfg["notes"].get("store", "notes.json"))
            self.skills.append(NotesSkill(store))
        if skills_cfg.get("reminders", {}).get("enabled"):
            store = os.path.join(
                store_dir,
                skills_cfg["reminders"].get("store", "reminders.json"))
            self.reminders = RemindersSkill(store)
            self.skills.append(self.reminders)
        self._echo_enabled = skills_cfg.get("echo", {}).get("enabled", True)
        self._history = {}
        self._pending = {}

    def handle(self, text, sender="local", now=None):
        """Return the reply text for one incoming message."""
        now = now if now is not None else time.time()

        pending = self._pending.get(sender)
        if pending is not None:
            answer = (text or "").strip().lower()
            if answer in ("yes", "y"):
                del self._pending[sender]
                return pending.on_yes()
            if answer in ("no", "n"):
                del self._pending[sender]
                return pending.on_no() if pending.on_no else "Okay, cancelled."
            return "Please answer yes or no. " + pending.question

        command, payload = parse_message(text)

        if command == "/help":
            return HELP
        if command == "/echo" and self._echo_enabled:
            return payload or "(nothing to echo)"

        for skill in self.skills:
            if isinstance(skill, RemindersSkill):
                reply = skill.handle(command, payload, sender, now)
            else:
                reply = skill.handle(command, payload, sender)
            if isinstance(reply, Confirm):
                self._pending[sender] = reply
                return reply.question
            if reply is not None:
                return reply

        if command is not None:
            return "Unknown command %s. /help lists what I can do." % command

        if self.backend is None:
            return ("No model is configured, so I can only run commands. "
                    "/help lists them. To give me free-form conversation, "
                    "set a model backend in behavior.json.")

        history = self._history.setdefault(sender, [])
        reply = self.backend.complete(self.system_prompt, history, payload)
        history.append({"role": "user", "content": payload})
        history.append({"role": "assistant", "content": reply})
        del history[:-20]
        return reply

    def due_reminders(self, now=None):
        """Reminders that just fired: [(sender, text), ...]."""
        if self.reminders is None:
            return []
        return self.reminders.check_due(now if now is not None else time.time())

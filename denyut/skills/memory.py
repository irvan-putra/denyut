"""Memory skill: long-term facts, plus an optional daily journal.

Two layers, both plain files you can read and edit:

1. Facts (always loaded). /remember adds a short fact. The facts are sent
   to the model with every free-form message, so the model starts each
   chat already knowing them. /forget archives a fact (never destroys it).
2. Journal (searched on demand, off by default). When switched on in
   behavior.json, every free-form message you send (not /commands) is appended to a file for that
   day. Nothing from the journal is sent to the model automatically;
   /recall <word> searches it when you ask.

Commands:
  /remember <fact>   add a long-term fact
  /memory            list facts
  /forget <n>        archive fact n
  /recall <word>     search the journal (only when the journal is on)

Nothing here needs a model, an account or the network.
"""

import json
import os
import re
import time

MAX_RECALL = 10


def _safe(sender):
    return re.sub(r"[^A-Za-z0-9._-]", "_", sender) or "local"


class MemorySkill:
    name = "memory"

    def __init__(self, store_path, journal_dir=None):
        self.store_path = store_path
        self.journal_dir = journal_dir
        self._data = self._load()

    # --- facts -----------------------------------------------------
    def _load(self):
        if os.path.exists(self.store_path):
            with open(self.store_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return {}

    def _save(self):
        tmp = self.store_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, self.store_path)

    def _facts(self, sender):
        return self._data.setdefault(sender, {"open": [], "archived": []})

    def facts(self, sender):
        """Open facts for one sender, for the model's context."""
        return list(self._facts(sender)["open"])

    def context_block(self, sender):
        facts = self.facts(sender)
        if not facts:
            return ""
        return ("Things the user asked you to remember:\n"
                + "\n".join("- " + f for f in facts))

    # --- journal ---------------------------------------------------
    def log(self, sender, text, now=None):
        if not self.journal_dir or not (text or "").strip():
            return
        now = now if now is not None else time.time()
        folder = os.path.join(self.journal_dir, _safe(sender))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, time.strftime("%Y-%m-%d", time.localtime(now)) + ".md")
        line = "%s %s\n" % (time.strftime("%H:%M", time.localtime(now)),
                            " ".join(text.split()))
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)

    def recall(self, sender, word):
        folder = os.path.join(self.journal_dir, _safe(sender))
        if not os.path.isdir(folder):
            return []
        needle = word.lower()
        hits = []
        for day in sorted(os.listdir(folder), reverse=True):
            if not day.endswith(".md"):
                continue
            with open(os.path.join(folder, day), "r", encoding="utf-8") as fh:
                for line in reversed(fh.read().splitlines()):
                    if needle in line.lower():
                        hits.append("%s %s" % (day[:-3], line))
                        if len(hits) >= MAX_RECALL:
                            return hits
        return hits

    # --- commands --------------------------------------------------
    def handle(self, command, payload, sender):
        if command == "/remember":
            text = payload.strip()
            if not text:
                return "Usage: /remember <a fact about you or your preferences>"
            facts = self._facts(sender)
            facts["open"].append(text)
            self._save()
            return "Remembered (%d): %s" % (len(facts["open"]), text)
        if command == "/memory":
            facts = self._facts(sender)["open"]
            if not facts:
                return "I have no remembered facts yet. Add one with /remember <fact>."
            return "\n".join("%d. %s" % (i + 1, t) for i, t in enumerate(facts))
        if command == "/forget":
            facts = self._facts(sender)
            try:
                item = facts["open"].pop(int(payload.strip()) - 1)
            except (ValueError, IndexError):
                return "No fact with that number. /memory shows them."
            facts["archived"].append(item)
            self._save()
            return "Forgotten: %s (kept in archive)" % item
        if command == "/recall":
            if not self.journal_dir:
                return ("The journal is off. Set skills.memory.journal to true "
                        "in behavior.json to keep a daily log you can search.")
            word = payload.strip()
            if not word:
                return "Usage: /recall <word>"
            hits = self.recall(sender, word)
            return "\n".join(hits) if hits else "Nothing in the journal matches that."
        return None

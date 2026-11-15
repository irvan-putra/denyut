"""Reminders skill: time-based notes that fire when due.

Commands:
  /remind <minutes> <text>   remind in N minutes (also accepts 2h, 1d)
  /reminders                 list pending reminders
  /cancel <n>                cancel reminder n (archived, not destroyed)

Firing: check_due() returns reminders whose time has come. The transport
adapter calls it on each incoming message and, in the DeltaChat adapter,
from a background timer - so reminders fire even when nobody is chatting.
"""

import json
import os
import re
import time

UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_delay(text):
    """'30' -> 30 min; '90s','45m','2h','1d' supported. Returns seconds."""
    text = text.strip().lower()
    m = re.fullmatch(r"(\d+)([smhd]?)", text)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2) or "m"
    seconds = n * UNITS[unit]
    return seconds if seconds > 0 else None


class RemindersSkill:
    name = "reminders"

    def __init__(self, store_path):
        self.store_path = store_path
        self._data = self._load()

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

    def _items(self, sender):
        return self._data.setdefault(sender, {"pending": [], "done": []})

    def handle(self, command, payload, sender, now):
        if command == "/remind":
            parts = payload.split(None, 1)
            if len(parts) < 2:
                return "Usage: /remind <delay> <text> - e.g. /remind 45m call mom"
            seconds = parse_delay(parts[0])
            if seconds is None:
                return "I don't understand the delay %r. Try 30, 90s, 45m, 2h or 1d." % parts[0]
            items = self._items(sender)
            items["pending"].append({"text": parts[1].strip(),
                                     "due": now + seconds})
            self._save()
            return "Okay, reminding you in %s: %s" % (parts[0], parts[1].strip())
        if command == "/reminders":
            pending = self._items(sender)["pending"]
            if not pending:
                return "No pending reminders."
            out = []
            for i, r in enumerate(pending, 1):
                left = int(r["due"] - now)
                out.append("%d. %s (in %dm%ds)" % (i, r["text"], left // 60, left % 60))
            return "\n".join(out)
        if command == "/cancel":
            items = self._items(sender)
            try:
                idx = int(payload.strip()) - 1
                item = items["pending"].pop(idx)
            except (ValueError, IndexError):
                return "No reminder with that number. /reminders shows them."
            items["done"].append(item)
            self._save()
            return "Cancelled: %s (kept in archive)" % item["text"]
        return None

    def check_due(self, now):
        """Return [(sender, text), ...] for reminders that just fired."""
        fired = []
        for sender, items in self._data.items():
            still = []
            for r in items["pending"]:
                if r["due"] <= now:
                    fired.append((sender, r["text"]))
                    items["done"].append(r)
                else:
                    still.append(r)
            items["pending"] = still
        if fired:
            self._save()
        return fired

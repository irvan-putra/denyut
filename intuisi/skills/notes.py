"""Notes skill: a small persistent list per sender.

Commands:
  /note <text>    add a note
  /notes          list notes
  /done <n>       remove note number n (archive-style: it is moved to
                  "archived" in the store, not destroyed)
"""

import json
import os


class NotesSkill:
    name = "notes"

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

    def _notes(self, sender):
        return self._data.setdefault(sender, {"open": [], "archived": []})

    def handle(self, command, payload, sender):
        if command == "/note":
            text = payload.strip()
            if not text:
                return "Usage: /note <something to remember>"
            notes = self._notes(sender)
            notes["open"].append(text)
            self._save()
            return "Noted (%d): %s" % (len(notes["open"]), text)
        if command == "/notes":
            notes = self._notes(sender)["open"]
            if not notes:
                return "No notes yet. Add one with /note <text>."
            return "\n".join("%d. %s" % (i + 1, t) for i, t in enumerate(notes))
        if command == "/done":
            notes = self._notes(sender)
            try:
                idx = int(payload.strip()) - 1
                item = notes["open"].pop(idx)
            except (ValueError, IndexError):
                return "No note with that number. /notes shows them."
            notes["archived"].append(item)
            self._save()
            return "Done: %s (kept in archive)" % item
        return None

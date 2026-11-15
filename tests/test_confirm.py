import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from denyut.core import Assistant, Confirm  # noqa: E402

BEHAVIOR = os.path.join(os.path.dirname(__file__), "..", "behavior.json")


class DeleteAllSkill:
    """Test skill that asks before a destructive action."""

    def __init__(self):
        self.deleted = False

    def handle(self, command, payload, sender):
        if command == "/deleteall":
            return Confirm(
                "Really delete everything?",
                on_yes=self._do_delete,
                on_no=lambda: "Kept everything.")
        return None

    def _do_delete(self):
        self.deleted = True
        return "Deleted."


def make(tmp_path):
    a = Assistant(behavior_path=BEHAVIOR, store_dir=str(tmp_path))
    skill = DeleteAllSkill()
    a.skills.insert(0, skill)
    return a, skill


def test_yes_confirms(tmp_path):
    a, skill = make(tmp_path)
    assert "Really delete" in a.handle("/deleteall", sender="u1")
    assert not skill.deleted
    assert a.handle("yes", sender="u1") == "Deleted."
    assert skill.deleted


def test_no_cancels(tmp_path):
    a, skill = make(tmp_path)
    a.handle("/deleteall", sender="u1")
    assert a.handle("no", sender="u1") == "Kept everything."
    assert not skill.deleted


def test_pending_is_per_sender(tmp_path):
    a, skill = make(tmp_path)
    a.handle("/deleteall", sender="u1")
    # another sender's messages are unaffected
    assert "/note" in a.handle("/help", sender="u2")
    assert "yes or no" in a.handle("maybe", sender="u1")

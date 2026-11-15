import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from denyut.core import Assistant  # noqa: E402

BEHAVIOR = os.path.join(os.path.dirname(__file__), "..", "behavior.json")


def test_notes_lifecycle(tmp_path):
    a = Assistant(behavior_path=BEHAVIOR, store_dir=str(tmp_path))
    assert "No notes yet" in a.handle("/notes", sender="u1")
    assert "Noted (1)" in a.handle("/note buy milk", sender="u1")
    assert "Noted (2)" in a.handle("/note call mom", sender="u1")
    listing = a.handle("/notes", sender="u1")
    assert "1. buy milk" in listing and "2. call mom" in listing
    done = a.handle("/done 1", sender="u1")
    assert "buy milk" in done and "archive" in done
    listing = a.handle("/notes", sender="u1")
    assert "call mom" in listing and "buy milk" not in listing


def test_notes_per_sender(tmp_path):
    a = Assistant(behavior_path=BEHAVIOR, store_dir=str(tmp_path))
    a.handle("/note private to u1", sender="u1")
    assert "No notes yet" in a.handle("/notes", sender="u2")


def test_notes_persist_across_instances(tmp_path):
    a1 = Assistant(behavior_path=BEHAVIOR, store_dir=str(tmp_path))
    a1.handle("/note survives restart", sender="u1")
    a2 = Assistant(behavior_path=BEHAVIOR, store_dir=str(tmp_path))
    assert "survives restart" in a2.handle("/notes", sender="u1")


def test_done_bad_number(tmp_path):
    a = Assistant(behavior_path=BEHAVIOR, store_dir=str(tmp_path))
    a.handle("/note only one", sender="u1")
    assert "No note with that number" in a.handle("/done 9", sender="u1")
    assert "No note with that number" in a.handle("/done x", sender="u1")

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from denyut.core import Assistant  # noqa: E402

BEHAVIOR = os.path.join(os.path.dirname(__file__), "..", "behavior.json")
T0 = 1_700_000_000.0


def make(tmp_path):
    return Assistant(behavior_path=BEHAVIOR, store_dir=str(tmp_path))


def test_remind_and_fire(tmp_path):
    a = make(tmp_path)
    reply = a.handle("/remind 30m stretch", sender="u1", now=T0)
    assert "30m" in reply and "stretch" in reply
    assert a.due_reminders(now=T0 + 60) == []
    fired = a.due_reminders(now=T0 + 31 * 60)
    assert fired == [("u1", "stretch")]
    assert a.due_reminders(now=T0 + 32 * 60) == []  # fires once


def test_delay_formats(tmp_path):
    a = make(tmp_path)
    assert "Okay" in a.handle("/remind 90s quick", sender="u1", now=T0)
    assert "Okay" in a.handle("/remind 2h later", sender="u1", now=T0)
    assert "Okay" in a.handle("/remind 1d tomorrow", sender="u1", now=T0)
    assert "don't understand" in a.handle("/remind soon thing", sender="u1", now=T0)
    listing = a.handle("/reminders", sender="u1", now=T0)
    assert "quick" in listing and "later" in listing and "tomorrow" in listing


def test_cancel_archives(tmp_path):
    a = make(tmp_path)
    a.handle("/remind 10m tea", sender="u1", now=T0)
    reply = a.handle("/cancel 1", sender="u1", now=T0)
    assert "Cancelled" in reply and "tea" in reply
    assert a.due_reminders(now=T0 + 11 * 60) == []
    assert "No pending" in a.handle("/reminders", sender="u1", now=T0)


def test_reminders_persist(tmp_path):
    a1 = make(tmp_path)
    a1.handle("/remind 5m persisted", sender="u1", now=T0)
    a2 = make(tmp_path)
    assert a2.due_reminders(now=T0 + 6 * 60) == [("u1", "persisted")]

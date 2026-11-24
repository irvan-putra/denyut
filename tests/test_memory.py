import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from denyut.core import Assistant  # noqa: E402

BEHAVIOR = os.path.join(os.path.dirname(__file__), "..", "behavior.json")


class Spy:
    def __init__(self):
        self.prompts = []

    def complete(self, system, history, text):
        self.prompts.append(system)
        return "ok"


def make(tmp_path, journal=False):
    cfg = json.load(open(BEHAVIOR))
    cfg["skills"]["memory"]["journal"] = journal
    path = tmp_path / "b.json"
    path.write_text(json.dumps(cfg))
    return Assistant(behavior_path=str(path), store_dir=str(tmp_path))


def test_facts_lifecycle_and_archive(tmp_path):
    a = make(tmp_path)
    assert "no remembered facts" in a.handle("/memory", sender="u1")
    assert "Remembered (1)" in a.handle("/remember I prefer short answers", sender="u1")
    assert "1. I prefer short answers" in a.handle("/memory", sender="u1")
    assert "kept in archive" in a.handle("/forget 1", sender="u1")
    assert "no remembered facts" in a.handle("/memory", sender="u1")
    assert "No fact with that number" in a.handle("/forget 3", sender="u1")


def test_facts_reach_the_model_per_sender(tmp_path):
    a = make(tmp_path)
    a.backend = Spy()
    a.handle("/remember I live in Jakarta", sender="u1")
    a.handle("hello", sender="u1")
    a.handle("hello", sender="u2")
    assert "I live in Jakarta" in a.backend.prompts[0]
    assert "Jakarta" not in a.backend.prompts[1]


def test_facts_persist(tmp_path):
    make(tmp_path).handle("/remember keeps", sender="u1")
    assert "keeps" in make(tmp_path).handle("/memory", sender="u1")


def test_journal_off_by_default_writes_nothing(tmp_path):
    a = make(tmp_path)
    a.handle("secret plan", sender="u1")
    assert not (tmp_path / "journal").exists()
    assert "journal is off" in a.handle("/recall plan", sender="u1")


def test_journal_on_logs_and_recalls_never_sent_to_model(tmp_path):
    a = make(tmp_path, journal=True)
    a.backend = Spy()
    a.handle("dentist on friday", sender="u1", now=1_700_000_000)
    a.handle("/recall dentist", sender="u1")
    out = a.handle("/recall Dentist", sender="u1")
    assert "dentist on friday" in out
    assert "Nothing" in a.handle("/recall dentist", sender="u2")
    assert all("dentist" not in p for p in a.backend.prompts)

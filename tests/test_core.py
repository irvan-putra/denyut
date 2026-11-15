import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from denyut.core import Assistant, parse_message  # noqa: E402

BEHAVIOR = os.path.join(os.path.dirname(__file__), "..", "behavior.json")


def make_assistant(tmp_path):
    return Assistant(behavior_path=BEHAVIOR, store_dir=str(tmp_path))


def test_parse_command():
    assert parse_message("/note buy milk") == ("/note", "buy milk")
    assert parse_message("/NOTES") == ("/notes", "")
    assert parse_message("hello there") == (None, "hello there")
    assert parse_message("") == (None, "")


def test_help(tmp_path):
    a = make_assistant(tmp_path)
    reply = a.handle("/help")
    assert "/note" in reply and "/notes" in reply


def test_echo(tmp_path):
    a = make_assistant(tmp_path)
    assert a.handle("/echo hello world") == "hello world"
    assert a.handle("/echo") == "(nothing to echo)"


def test_unknown_command(tmp_path):
    a = make_assistant(tmp_path)
    reply = a.handle("/frobnicate now")
    assert "Unknown command" in reply and "/frobnicate" in reply


def test_freeform_without_model(tmp_path):
    a = make_assistant(tmp_path)
    reply = a.handle("what is the meaning of life?")
    assert "No model is configured" in reply
    assert "behavior.json" in reply

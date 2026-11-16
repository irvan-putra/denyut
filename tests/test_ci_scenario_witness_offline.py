"""Offline qualification of `ci-chat-test.py --scenario notes-reminders`.

Same style as test_ci_witness_offline.py: a fake transport replays raw
JSON-RPC shapes through the real deltachat2 parsers. Here the fake peer
chat is backed by the REAL Assistant, with a fake clock and a fake 30s
reminder timer, so restore mode, /echo, then the notes and reminder
scenario run end to end on the host. Proves the witness wiring and
assertions. Does not prove anything about Android or real delivery.
"""

import importlib.util
import os
import sys
import threading

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WITNESS_PATH = os.path.join(REPO_ROOT, "tools", "ci-chat-test.py")
BEHAVIOR = os.path.join(REPO_ROOT, "android", "app", "src", "main", "python",
                        "behavior.json")
sys.path.insert(0, REPO_ROOT)

deltachat2 = pytest.importorskip("deltachat2")
from denyut.core import Assistant  # noqa: E402

PEER = "peer@example.invalid"
CHAT = 10
SENDER = "42"


class FakeClock:
    def __init__(self):
        self.now = 2_000_000.0

    def time(self):
        return self.now

    def sleep(self, _s):  # only the watchdog sleeps; it must never fire
        threading.Event().wait()


class FakeChat:
    def __init__(self, tmp_path, clock, never_remind=False):
        self.clock = clock
        self.a = Assistant(behavior_path=BEHAVIOR, store_dir=str(tmp_path))
        self.texts = {}
        self.events = []
        self.next_id = 100
        self.never_remind = never_remind
        self.calls = []

    def _incoming(self, text):
        self.next_id += 1
        self.texts[self.next_id] = text
        self.events.append({"context_id": 1, "event": {
            "kind": "IncomingMsg", "chat_id": CHAT, "msg_id": self.next_id}})

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def call(self, method, *args):
        self.calls.append(method)
        if method == "get_all_account_ids":
            return [1]
        if method == "start_io_for_all_accounts":
            return None
        if method == "lookup_contact_id_by_addr":
            return 42 if args[1] == PEER else 0
        if method in ("get_chat_id_by_contact_id", "create_chat_by_contact_id"):
            return CHAT
        if method == "send_msg":
            body = getattr(args[2], "text", None) or args[2]["text"]
            self._incoming(self.a.handle(body, sender=SENDER,
                                         now=self.clock.now))
            return 1
        if method == "get_next_event":
            if not self.events:
                self.clock.now += 30
                if not self.never_remind:
                    for _s, t in self.a.due_reminders(now=self.clock.now):
                        self._incoming("Reminder: " + t)
                self.events.append({"context_id": 1,
                                    "event": {"kind": "ConnectivityChanged"}})
            return self.events.pop(0)
        if method == "get_message":
            return {"text": self.texts[args[1]]}
        raise AssertionError("unexpected rpc method %r" % (method,))


def _run(monkeypatch, capsys, tmp_path, argv_extra, **chat_kw):
    import deltachat2.transport as dt

    clock = FakeClock()
    chat = FakeChat(tmp_path, clock, **chat_kw)
    monkeypatch.setattr(dt, "IOTransport", lambda accounts_dir=None: chat)
    monkeypatch.setattr(sys, "argv", ["ci-chat-test.py", "-", "-", "tok123",
                                      "--accounts-dir", str(tmp_path),
                                      "--peer-address", PEER] + argv_extra)
    spec = importlib.util.spec_from_file_location("ci_chat_test_sc", WITNESS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "time", clock)
    rc = mod.main()
    return rc, capsys.readouterr().out, chat


def test_scenario_passes_end_to_end(monkeypatch, capsys, tmp_path):
    rc, out, chat = _run(monkeypatch, capsys, tmp_path,
                         ["--scenario", "notes-reminders"])
    assert rc == 0, out
    assert "CHAT PASS" in out and "CHAT SCENARIO PASS" in out
    assert "dnt-" not in out and PEER not in out


def test_echo_only_mode_unchanged(monkeypatch, capsys, tmp_path):
    rc, out, chat = _run(monkeypatch, capsys, tmp_path, [])
    assert rc == 0, out
    assert "CHAT PASS" in out and "SCENARIO" not in out


def test_scenario_fails_when_reminder_never_arrives(monkeypatch, capsys, tmp_path):
    rc, out, _ = _run(monkeypatch, capsys, tmp_path,
                      ["--scenario", "notes-reminders"], never_remind=True)
    assert rc == 1
    assert "CHAT SCENARIO FAIL: step reminder-unsolicited" in out


def test_scenario_requires_restore_mode(monkeypatch, capsys, tmp_path):
    import deltachat2.transport as dt
    monkeypatch.setattr(dt, "IOTransport", lambda accounts_dir=None: None)
    monkeypatch.setattr(sys, "argv", ["ci-chat-test.py", "r", "i", "t",
                                      "--scenario", "notes-reminders"])
    spec = importlib.util.spec_from_file_location("ci_chat_test_sc2", WITNESS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main() == 1
    assert "requires restore mode" in capsys.readouterr().out

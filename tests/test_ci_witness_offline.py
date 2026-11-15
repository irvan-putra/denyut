"""Offline qualification of the CI chat witness (tools/ci-chat-test.py).

No network, no relay, no accounts: a FakeTransport replays the exact raw
JSON-RPC shapes the witness consumes, through the REAL deltachat2 parsing
code. Locks the contract that run 43688709457 violated:

- deltachat2 2.58.0's typed Message parse REQUIRES sender.is_verified
  (Contact field), which the drifted deltachat-rpc-server 2.69.0 omits.
  That mismatch crashed the witness after secure-join had completed.
- The witness therefore reads the reply via the raw get_message call,
  which must tolerate BOTH the 2.58 shape (is_verified present, the
  pinned pair) and the 2.69 shape (is_verified absent, observed drift).

The 2.69 fixture models the observed failure only as far as the first
missing field (sender.is_verified); dacite aborts there, so later fields
were never validated against a real 2.69 response.
"""

import importlib.util
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WITNESS_PATH = os.path.join(REPO_ROOT, "tools", "ci-chat-test.py")

deltachat2 = pytest.importorskip("deltachat2")
from deltachat2.types import Message, _from_dict  # noqa: E402

TOKEN = "denyut-ci-offline-fixture"

CONTACT_258 = {
    "address": "bot@nine.testrun.org",
    "auth_name": "Denyut",
    "color": "#e05b8f",
    "display_name": "Denyut",
    "e2ee_avail": True,
    "id": 42,
    "is_blocked": False,
    "is_bot": True,
    "is_key_contact": True,
    "is_verified": True,
    "last_seen": 1731700000,
    "name": "Denyut",
    "name_and_addr": "Denyut (bot@nine.testrun.org)",
    "status": "",
    "was_seen_recently": True,
}


def _message(sender):
    return {
        "chat_id": 10,
        "dimensions_height": 0,
        "dimensions_width": 0,
        "download_state": "Done",
        "duration": 0,
        "file_bytes": 0,
        "from_id": 42,
        "has_deviating_timestamp": False,
        "has_html": False,
        "has_location": False,
        "id": 77,
        "is_bot": False,
        "is_edited": False,
        "is_forwarded": False,
        "is_info": False,
        "received_timestamp": 1731700001,
        "sender": sender,
        "show_padlock": True,
        "sort_timestamp": 1731700001,
        "state": 13,
        "subject": "",
        "system_message_type": "Unknown",
        "text": "/echo " + TOKEN,
        "timestamp": 1731700000,
        "view_type": "Text",
    }


MESSAGE_258 = _message(CONTACT_258)
MESSAGE_269 = _message({k: v for k, v in CONTACT_258.items() if k != "is_verified"})


def _event(kind, **fields):
    body = {"kind": kind}
    body.update(fields)
    return {"context_id": 1, "event": body}


# The raw event sequence of a successful round trip, as the server's
# get_next_event returns them (snake_case, "kind" discriminator).
EVENTS_SUCCESS = [
    _event("ConfigureProgress", comment=None, progress=1000),
    _event("SecurejoinJoinerProgress", contact_id=42, progress=400),
    # An unrelated event mid-join must not derail the phase machine.
    _event("ConnectivityChanged"),
    _event("SecurejoinJoinerProgress", contact_id=42, progress=1000),
    _event("IncomingMsg", chat_id=10, msg_id=77),
]


class FakeTransport:
    """Replays scripted raw JSON-RPC responses through the real parsers."""

    def __init__(self, message, events):
        self._message = message
        self._events = list(events)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def call(self, method, *args):
        self.calls.append((method,) + args)
        if method == "add_account":
            return 1
        if method in ("set_config", "add_transport_from_qr"):
            return None
        if method == "get_next_event":
            if not self._events:
                raise AssertionError("witness asked for more events than scripted")
            return self._events.pop(0)
        if method == "secure_join":
            return 0
        if method == "get_chat_id_by_contact_id":
            return 10
        if method == "create_chat_by_contact_id":
            return 10
        if method == "send_msg":
            return 77
        if method == "get_message":
            return self._message
        raise AssertionError("unexpected rpc method %r" % (method,))


def _run_witness(monkeypatch, capsys, tmp_path, message, events):
    import deltachat2.transport as dt

    fake = FakeTransport(message, events)
    monkeypatch.setattr(dt, "IOTransport", lambda accounts_dir=None: fake)

    invite = tmp_path / "invite.txt"
    invite.write_text("OPENPGP4FPR:offline-fixture-invite")
    monkeypatch.setattr(
        sys, "argv", ["ci-chat-test.py", "https://relay.invalid/new", str(invite), TOKEN]
    )

    spec = importlib.util.spec_from_file_location("ci_chat_test", WITNESS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rc = mod.main()
    out = capsys.readouterr().out
    return rc, out, fake


def test_witness_chat_pass_with_258_message_shape(monkeypatch, capsys, tmp_path):
    """Pinned pair (client 2.58 + server 2.58): full flow reaches CHAT PASS."""
    rc, out, fake = _run_witness(
        monkeypatch, capsys, tmp_path, MESSAGE_258, EVENTS_SUCCESS
    )
    assert rc == 0, out
    assert "secure-join completed" in out
    assert "CHAT PASS" in out
    # The reply was read via the raw call, not the typed parse.
    assert ("get_message", 1, 77) in fake.calls


def test_witness_chat_pass_with_269_message_shape(monkeypatch, capsys, tmp_path):
    """Drifted server 2.69 shape (no sender.is_verified): raw read still passes."""
    rc, out, _ = _run_witness(monkeypatch, capsys, tmp_path, MESSAGE_269, EVENTS_SUCCESS)
    assert rc == 0, out
    assert "CHAT PASS" in out


def test_typed_parse_reproduces_run_43688709457_failure():
    """The exact crash that burned the run: typed parse vs the 2.69 shape."""
    import dacite

    with pytest.raises(dacite.exceptions.MissingValueError) as excinfo:
        _from_dict(Message, dict(MESSAGE_269))
    assert "sender.is_verified" in str(excinfo.value)


def test_typed_parse_accepts_258_shape():
    """The matched pair keeps the typed path valid - this is what the bot
    framework (deltachat2/bot.py get_message) relies on inside the app."""
    msg = _from_dict(Message, dict(MESSAGE_258))
    assert msg.text == "/echo " + TOKEN
    assert msg.sender.is_verified is True

"""Offline qualification of the Android adapter (android_bot.py).

No rpc-server, no accounts, no relay, no network: the adapter module is
loaded from its bundled path (android/app/src/main/python/android_bot.py)
and driven with fakes, so the code under test is the exact code the app
runs on-device.

The CI transport proofs (smoke + /echo round trip) cover process
liveness and the message path. This file qualifies the ASSISTANT paths
the transport proofs cannot reach:

- notes round trip + archive through the adapter's real NewMessage hook
- proactive reminder firing from the adapter's real _reminder_loop
  timer thread, WITHOUT any incoming message
- freeform text with model backend "none" keeps the honest no-model
  reply (no silent fallback, no invented answer)
"""

import importlib.util
import json
import os
import sys
import threading
import time

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAPTER_PATH = os.path.join(
    REPO_ROOT, "android", "app", "src", "main", "python", "android_bot.py")
BEHAVIOR_PATH = os.path.join(
    REPO_ROOT, "android", "app", "src", "main", "python", "behavior.json")

deltachat2 = pytest.importorskip("deltachat2")
from deltachat2 import MessageData  # noqa: E402


def _load_adapter():
    spec = importlib.util.spec_from_file_location("android_bot", ADAPTER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeMsg:
    def __init__(self, text, from_id=42, chat_id=99):
        self.text = text
        self.from_id = from_id
        self.chat_id = chat_id


class FakeEvent:
    def __init__(self, text, from_id=42, chat_id=99):
        self.msg = FakeMsg(text, from_id, chat_id)


class FakeRpc:
    """Records outgoing messages; stands in for the live rpc transport."""

    def __init__(self):
        self.sent = []
        self.lock = threading.Lock()

    def get_all_account_ids(self):
        return [1]

    def get_chat_id_by_contact_id(self, accid, contact_id):
        return 99

    def send_msg(self, accid, chat_id, data):
        with self.lock:
            self.sent.append((chat_id, data.text))


class FakeBot:
    def __init__(self, rpc):
        self.rpc = rpc


def _assistant(tmp_path):
    # denyut.core resolves to the repo package; the android bundle copy
    # is byte-identical (diff-verified), so semantics match on-device.
    from denyut.core import Assistant
    return Assistant(behavior_path=BEHAVIOR_PATH, store_dir=str(tmp_path))


def _on_message_hook(adapter, assistant):
    hooks = adapter._make_hooks(assistant, None)
    funcs = [func for func, _flt in hooks]
    assert len(funcs) == 1, "expected exactly one registered hook"
    return funcs[0]


def test_notes_roundtrip_and_archive_through_adapter_hook(tmp_path):
    adapter = _load_adapter()
    assistant = _assistant(tmp_path)
    rpc = FakeRpc()
    on_message = _on_message_hook(adapter, assistant)
    bot = FakeBot(rpc)

    on_message(bot, 1, FakeEvent("/note buy milk"))
    on_message(bot, 1, FakeEvent("/note call dentist"))
    on_message(bot, 1, FakeEvent("/notes"))
    on_message(bot, 1, FakeEvent("/done 1"))

    replies = [text for _chat, text in rpc.sent]
    assert replies[0] == "Noted (1): buy milk"
    assert replies[1] == "Noted (2): call dentist"
    assert replies[2] == "1. buy milk\n2. call dentist"
    assert replies[3] == "Done: buy milk (kept in archive)"

    # Archive survives on disk: done notes are moved, not destroyed.
    store = json.loads((tmp_path / "notes.json").read_text())
    assert store["42"]["open"] == ["call dentist"]
    assert store["42"]["archived"] == ["buy milk"]


def test_reminder_fires_proactively_without_incoming_message(tmp_path, monkeypatch):
    adapter = _load_adapter()
    monkeypatch.setattr(adapter, "REMINDER_POLL_SECONDS", 0.05)
    adapter._stop.clear()
    assistant = _assistant(tmp_path)
    rpc = FakeRpc()

    reply = assistant.handle("/remind 1s stretch", sender="42")
    assert reply.startswith("Okay, reminding you in 1s")
    time.sleep(1.2)

    # The timer thread alone must fire the reminder: no on_message call
    # happens anywhere in this test.
    thread = threading.Thread(
        target=adapter._reminder_loop, args=(assistant, rpc), daemon=True)
    thread.start()
    deadline = time.time() + 10
    while time.time() < deadline:
        with rpc.lock:
            if rpc.sent:
                break
        time.sleep(0.05)
    adapter._stop.set()
    thread.join(timeout=5)

    assert rpc.sent, "reminder timer never fired"
    chat_id, text = rpc.sent[0]
    assert chat_id == 99
    assert text == "Reminder: stretch"

    store = json.loads((tmp_path / "reminders.json").read_text())
    assert store["42"]["pending"] == []
    assert [r["text"] for r in store["42"]["done"]] == ["stretch"]


def test_freeform_keeps_honest_no_model_reply(tmp_path):
    adapter = _load_adapter()
    assistant = _assistant(tmp_path)
    rpc = FakeRpc()
    on_message = _on_message_hook(adapter, assistant)

    on_message(FakeBot(rpc), 1, FakeEvent("what do you think about tomorrow?"))

    assert len(rpc.sent) == 1
    assert rpc.sent[0][1].startswith("No model is configured")

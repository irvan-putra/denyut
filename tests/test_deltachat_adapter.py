"""Contract test for the DeltaChat adapter without any DeltaChat
dependency: deltabot_cli and deltachat2 are stubbed in sys.modules so the
adapter module imports on any Python version, and a fake rpc object
verifies the send path and reminder firing."""

import importlib
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def load_adapter():
    # stub deltabot_cli
    dbc = types.ModuleType("deltabot_cli")

    class BotCli:
        def __init__(self, name):
            self.name = name
            self.config_dir = os.environ["DENYUT_TEST_STORE"]
            self._handlers = []
            self._starts = []

        def on(self, event):
            def deco(fn):
                self._handlers.append(fn)
                return fn
            return deco

        def on_start(self, fn):
            self._starts.append(fn)
            return fn

        def start(self):
            pass

    dbc.BotCli = BotCli

    # stub deltachat2
    dc2 = types.ModuleType("deltachat2")

    class MessageData:
        def __init__(self, text=None):
            self.text = text

    class _Events:
        class NewMessage:
            pass

    dc2.MessageData = MessageData
    dc2.events = _Events

    sys.modules["deltabot_cli"] = dbc
    sys.modules["deltachat2"] = dc2
    mod = importlib.import_module("denyut.deltachat_bot")
    return mod, dbc.BotCli


class FakeMsg:
    def __init__(self, text, from_id=42, chat_id=7):
        self.text = text
        self.from_id = from_id
        self.chat_id = chat_id


class FakeEvent:
    def __init__(self, msg):
        self.msg = msg


class FakeRpc:
    def __init__(self):
        self.sent = []

    def send_msg(self, accid, chat_id, data):
        self.sent.append((accid, chat_id, data.text))
        return 1

    def get_all_account_ids(self):
        return [1]

    def get_chat_id_by_contact_id(self, accid, contact_id):
        return 700 + contact_id


class FakeBot:
    def __init__(self):
        self.rpc = FakeRpc()


def test_adapter_routes_and_replies(tmp_path, monkeypatch):
    monkeypatch.setenv("DENYUT_TEST_STORE", str(tmp_path))
    mod, _ = load_adapter()
    bot = FakeBot()
    mod.on_message(bot, 1, FakeEvent(FakeMsg("/note adapter works")))
    assert bot.rpc.sent[-1][2].startswith("Noted (1)")
    mod.on_message(bot, 1, FakeEvent(FakeMsg("/notes")))
    assert "adapter works" in bot.rpc.sent[-1][2]


def test_adapter_fires_due_reminders(tmp_path, monkeypatch):
    monkeypatch.setenv("DENYUT_TEST_STORE", str(tmp_path))
    mod, _ = load_adapter()
    bot = FakeBot()
    assistant = mod.get_assistant()
    assistant.handle("/remind 1s ping", sender="42", now=1000.0)
    monkeypatch.setattr("time.time", lambda: 1002.0)
    mod.fire_due(bot, 1)
    assert (1, 742, "Reminder: ping") in bot.rpc.sent
    # fires once only
    bot.rpc.sent.clear()
    mod.fire_due(bot, 1)
    assert bot.rpc.sent == []

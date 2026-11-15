"""DeltaChat transport adapter.

Runs the assistant as a DeltaChat bot using deltabot-cli + deltachat2
(see https://bots.delta.chat/quickstart.html). Requires Python >= 3.11
(deltachat2 uses enum.StrEnum). The bot has its own chatmail account;
nobody can reach it without the invite QR code/link.

This module is the ONLY DeltaChat-specific file; the core is transport
agnostic and unit-tested without any DeltaChat dependency.

Usage:
  pip install deltabot-cli
  python -m denyut.deltachat_bot init DCACCOUNT:https://nine.testrun.org/new
  python -m denyut.deltachat_bot link     # prints invite link/QR
  python -m denyut.deltachat_bot serve
"""

import threading
import time

from deltabot_cli import BotCli  # noqa: E402  (optional dependency)
from deltachat2 import MsgData, events  # noqa: E402

from .core import Assistant

cli = BotCli("denyut")
_assistant = None
REMINDER_POLL_SECONDS = 30


def get_assistant():
    global _assistant
    if _assistant is None:
        _assistant = Assistant(store_dir=cli.config_dir)
    return _assistant


@cli.on(events.NewMessage)
def on_message(bot, accid, event):
    text = (event.msg.text or "").strip()
    if not text:
        return
    sender = str(event.msg.from_id)
    reply = get_assistant().handle(text, sender=sender)
    bot.rpc.send_msg(accid, event.msg.chat_id, MsgData(text=reply))
    fire_due(bot, accid)


def fire_due(bot, accid):
    for sender, text in get_assistant().due_reminders():
        chat_id = bot.rpc.get_chat_id_by_contact_id(accid, int(sender))
        if chat_id:
            bot.rpc.send_msg(accid, chat_id,
                             MsgData(text="Reminder: " + text))


@cli.on_start
def start_timer(bot, _args):
    def loop():
        while True:
            time.sleep(REMINDER_POLL_SECONDS)
            try:
                for accid in bot.rpc.get_all_account_ids():
                    fire_due(bot, accid)
            except Exception:
                pass

    threading.Thread(target=loop, daemon=True).start()


if __name__ == "__main__":
    cli.start()

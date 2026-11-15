"""Host-side half of the Denyut CI chat round trip.

Runs on the CI runner (Linux x86_64; deltachat2 + deltachat-rpc-server
from PyPI), NOT on the emulator. Creates a second throwaway relay
account, secure-joins the bot via the invite QR printed by
android_bot.ci_autosetup, sends a token with /echo, and waits for the
bot's reply through the real DeltaChat message path.

Usage: python3 tools/ci-chat-test.py <relay_url> <invite_qr_file> <token>
The invite QR is read from a chmod-600 file so the credential never
appears in argv, logs, or artifacts.
Prints "CHAT PASS" or "CHAT FAIL: <reason>" and exits 0/1.
"""

import sys
import tempfile
import threading

TOKEN_TIMEOUT = 300


def main():
    relay_url, invite_file, token = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(invite_file, "r", encoding="utf-8") as f:
        invite_qr = f.read().strip()

    from deltachat2 import MsgData, Rpc
    from deltachat2.transport import IOTransport

    accounts_dir = tempfile.mkdtemp(prefix="denyut-ci-chat-")
    with IOTransport(accounts_dir=accounts_dir) as trans:
        rpc = Rpc(trans)
        accid = rpc.add_account()
        rpc.set_config(accid, "displayname", "Denyut CI peer")

        configured = threading.Event()
        failed = threading.Event()

        def wait_configure():
            while not configured.is_set() and not failed.is_set():
                event = rpc.get_next_event().event
                progress = getattr(event, "progress", None)
                if progress is not None:
                    if progress >= 1000:
                        configured.set()
                    elif progress == 0:
                        failed.set()

        watcher = threading.Thread(target=wait_configure, daemon=True)
        watcher.start()
        rpc.add_transport_from_qr(accid, "DCACCOUNT:" + relay_url)
        configured.wait(timeout=180)
        if not configured.is_set():
            print("CHAT FAIL: peer account configuration did not complete")
            return 1

        # Secure-join the bot. Joiner progress 1000 = done; the joiner
        # handshake also surfaces as contact/chat creation.
        joined = threading.Event()

        def wait_join():
            while not joined.is_set():
                event = rpc.get_next_event().event
                kind = getattr(event, "kind", "")
                progress = getattr(event, "progress", None)
                if kind == "SecurejoinJoinerProgress" and progress and progress >= 1000:
                    joined.set()

        joiner = threading.Thread(target=wait_join, daemon=True)
        joiner.start()
        rpc.secure_join(accid, invite_qr)
        joined.wait(timeout=180)
        if not joined.is_set():
            print("CHAT FAIL: secure-join did not complete")
            return 1

        # Find the bot contact (the only non-self contact) and its chat.
        contacts = rpc.get_contacts(accid)
        bot_contact = None
        for c in contacts:
            if not getattr(c, "is_self", False):
                bot_contact = c
                break
        if bot_contact is None:
            print("CHAT FAIL: no bot contact after secure-join")
            return 1
        chat_id = rpc.get_chat_id_by_contact_id(accid, bot_contact.id)

        replied = threading.Event()

        def wait_reply():
            while not replied.is_set():
                event = rpc.get_next_event().event
                kind = getattr(event, "kind", "")
                msg = getattr(event, "msg", None)
                text = getattr(msg, "text", "") or ""
                if kind in ("IncomingMsg", "MsgDelivered", "NewMessage") \
                        and token in text:
                    replied.set()

        listener = threading.Thread(target=wait_reply, daemon=True)
        listener.start()
        rpc.send_msg(accid, chat_id, MsgData(text="/echo " + token))
        replied.wait(timeout=TOKEN_TIMEOUT)
        if not replied.is_set():
            print("CHAT FAIL: no reply containing the token within %ds"
                  % TOKEN_TIMEOUT)
            return 1

    print("CHAT PASS: /echo round trip through the bot's real message path")
    return 0


if __name__ == "__main__":
    sys.exit(main())

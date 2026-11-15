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

Written against deltachat2 2.58.0 API, verified from the wheel source:
- events are EventType* dataclass instances on Event().event, not dicts
- configure progress: EventTypeConfigureProgress(progress 1-999, 1000 done, 0 error)
- joiner progress: EventTypeSecurejoinJoinerProgress(contact_id, progress; 1000 done)
- incoming message: EventTypeIncomingMsg(chat_id, msg_id); body via raw get_message call
- send via rpc.send_msg(accid, chat_id, MessageData(text=...))

A single event loop consumes get_next_event() - parallel consumer
threads would steal each other's events from the shared queue.
"""

import os
import sys
import tempfile
import threading
import time

TOTAL_TIMEOUT = 420


def main():
    relay_url, invite_file, token = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(invite_file, "r", encoding="utf-8") as f:
        invite_qr = f.read().strip()

    from deltachat2 import MessageData, Rpc
    from deltachat2.transport import IOTransport
    from deltachat2.types import (
        EventTypeConfigureProgress,
        EventTypeIncomingMsg,
        EventTypeSecurejoinJoinerProgress,
    )

    # get_next_event() blocks with no timeout; a watchdog enforces the
    # overall bound so a stuck phase can never hang the CI job.
    def watchdog():
        time.sleep(TOTAL_TIMEOUT)
        print("CHAT FAIL: overall timeout after %ds" % TOTAL_TIMEOUT, flush=True)
        os._exit(1)

    threading.Thread(target=watchdog, daemon=True).start()

    accounts_dir = tempfile.mkdtemp(prefix="denyut-ci-chat-")
    phase = "configure"
    chat_id = None
    with IOTransport(accounts_dir=accounts_dir) as trans:
        rpc = Rpc(trans)
        accid = rpc.add_account()
        rpc.set_config(accid, "displayname", "Denyut CI peer")
        rpc.add_transport_from_qr(accid, "DCACCOUNT:" + relay_url)

        deadline = time.time() + TOTAL_TIMEOUT
        while time.time() < deadline:
            ev = rpc.get_next_event().event

            if phase == "configure" and isinstance(ev, EventTypeConfigureProgress):
                if ev.progress and ev.progress >= 1000:
                    print("peer account configured", flush=True)
                    rpc.secure_join(accid, invite_qr)
                    phase = "join"
                elif ev.progress == 0:
                    print("CHAT FAIL: peer configuration failed: %s"
                          % (ev.comment or "?"), flush=True)
                    return 1

            elif phase == "join" and isinstance(ev, EventTypeSecurejoinJoinerProgress):
                if ev.progress and ev.progress >= 1000:
                    print("secure-join completed", flush=True)
                    for _ in range(6):
                        chat_id = rpc.get_chat_id_by_contact_id(accid, ev.contact_id)
                        if chat_id:
                            break
                        time.sleep(2)
                    if not chat_id:
                        chat_id = rpc.create_chat_by_contact_id(accid, ev.contact_id)
                    rpc.send_msg(accid, chat_id, MessageData(text="/echo " + token))
                    print("sent /echo with token, awaiting reply", flush=True)
                    phase = "chat"

            elif phase == "chat" and isinstance(ev, EventTypeIncomingMsg):
                # Raw call, not rpc.get_message(): the typed Message parse is
                # version-fragile (deltachat2 2.58.0 expects sender.is_verified,
                # which current deltachat-rpc-server does not return). The
                # witness only needs the text.
                msg = rpc.transport.call("get_message", accid, ev.msg_id)
                if token in (msg.get("text") or ""):
                    print("CHAT PASS: /echo round trip through the bot's "
                          "real message path", flush=True)
                    return 0

    print("CHAT FAIL: did not complete (phase=%s)" % phase, flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())

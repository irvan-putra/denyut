"""Host-side half of the Denyut CI chat round trip.

Runs on the CI runner (Linux x86_64; deltachat2 + deltachat-rpc-server
from PyPI), NOT on the emulator. Two modes:

Create mode (legacy): creates a throwaway relay account, secure-joins
the bot via an invite QR, sends a token with /echo, and waits for the
bot's reply. Usage:
    python3 tools/ci-chat-test.py <relay_url> <invite_qr_file> <token>
The invite QR is read from a chmod-600 file so the credential never
appears in argv, logs, or artifacts.

Restore mode (current CI path): reopens an EXISTING account directory
from the vault-backed reusable test pair (no account creation), sends
the token over the already-established chat with the bot, and waits for
the reply. Usage:
    python3 tools/ci-chat-test.py - - <token> \\
        --accounts-dir <dir> --peer-address <addr>
The accounts dir and peer address arrive via protected CI secrets and
temp files, never the public log.

Optional, restore mode only: add `--scenario notes-reminders` to run, after
the /echo check passes, a real notes create/list/archive and a reminder
that must arrive unsolicited (see tools/ci_chat_scenario.py). The echo
check is unchanged and still runs first.

Prints "CHAT PASS" or "CHAT FAIL: <reason>" and exits 0/1.

Written against deltachat2 2.58.0 API, verified from the wheel source:
- events are EventType* dataclass instances on Event().event, not dicts
- configure progress: EventTypeConfigureProgress(progress 1-999, 1000 done, 0 error)
- joiner progress: EventTypeSecurejoinJoinerProgress(contact_id, progress; 1000 done)
- incoming message: EventTypeIncomingMsg(chat_id, msg_id); body via raw get_message call
- send via rpc.send_msg(accid, chat_id, MessageData(text=...))
- a restored accounts dir needs start_io_for_all_accounts() before
  anything is sent or received (configure starts IO implicitly, restore
  does not)

A single event loop consumes get_next_event() - parallel consumer
threads would steal each other's events from the shared queue.
"""

import os
import sys
import tempfile
import threading
import time

TOTAL_TIMEOUT = 420
SCENARIO_TIMEOUT = 900


def _run_scenario(rpc, accid, chat_id, incoming_type):
    """Notes + reminders over the same established chat, same single
    event consumer. Only the synthetic marker is ever logged."""
    from deltachat2 import MessageData
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ci_chat_scenario as sc

    def send(text):
        rpc.send_msg(accid, chat_id, MessageData(text=text))

    def wait(pred, timeout_s):
        end = time.time() + timeout_s
        while time.time() < end:
            ev = rpc.get_next_event().event
            if not isinstance(ev, incoming_type) or ev.chat_id != chat_id:
                continue
            msg = rpc.transport.call("get_message", accid, ev.msg_id)
            text = (msg.get("text") or "").strip()
            if pred(text):
                return text
        return None

    ok, step = sc.run(send, wait, sc.new_marker(), time.time,
                      lambda line: print(line, flush=True))
    if ok:
        print("CHAT SCENARIO PASS: notes create/list/archive and an "
              "unsolicited reminder through the bot's real message path",
              flush=True)
        return 0
    print("CHAT SCENARIO FAIL: step %s" % step, flush=True)
    return 1


def main():
    argv = sys.argv[1:]
    restore_dir = None
    peer_address = None
    if "--accounts-dir" in argv:
        i = argv.index("--accounts-dir")
        restore_dir = argv[i + 1]
        del argv[i:i + 2]
    if "--peer-address" in argv:
        i = argv.index("--peer-address")
        peer_address = argv[i + 1]
        del argv[i:i + 2]
    scenario = None
    if "--scenario" in argv:
        i = argv.index("--scenario")
        scenario = argv[i + 1]
        del argv[i:i + 2]
    relay_url, invite_file, token = argv[0], argv[1], argv[2]
    if scenario not in (None, "notes-reminders"):
        print("CHAT FAIL: unknown scenario", flush=True)
        return 1
    if scenario and not restore_dir:
        print("CHAT FAIL: --scenario requires restore mode", flush=True)
        return 1
    total_timeout = SCENARIO_TIMEOUT if scenario else TOTAL_TIMEOUT

    if restore_dir and not peer_address:
        print("CHAT FAIL: restore mode requires --peer-address", flush=True)
        return 1

    invite_qr = None
    if not restore_dir:
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
        time.sleep(total_timeout)
        print("CHAT FAIL: overall timeout after %ds" % total_timeout, flush=True)
        os._exit(1)

    threading.Thread(target=watchdog, daemon=True).start()

    accounts_dir = restore_dir or tempfile.mkdtemp(prefix="denyut-ci-chat-")
    phase = "restore" if restore_dir else "configure"
    chat_id = None
    with IOTransport(accounts_dir=accounts_dir) as trans:
        rpc = Rpc(trans)

        if restore_dir:
            ids = rpc.get_all_account_ids()
            if len(ids) != 1:
                print("CHAT FAIL: restored accounts dir holds %d accounts, "
                      "expected exactly 1" % len(ids), flush=True)
                return 1
            accid = ids[0]
            rpc.start_io_for_all_accounts()
            # The pair's secure-join already created a verified key-contact
            # and chat. create_contact() would mint a NEW address-contact
            # whose 1:1 chat is unencrypted, and chatmail refuses to send
            # unencrypted ("e2e encryption unavailable"); look the existing
            # contact up instead so the token rides the established chat.
            contact_id = rpc.lookup_contact_id_by_addr(accid, peer_address)
            if not contact_id:
                print("CHAT FAIL: no existing contact for peer address",
                      flush=True)
                return 1
            chat_id = rpc.get_chat_id_by_contact_id(accid, contact_id)
            if not chat_id:
                chat_id = rpc.create_chat_by_contact_id(accid, contact_id)
            rpc.send_msg(accid, chat_id, MessageData(text="/echo " + token))
            print("restored peer account, sent /echo with token, "
                  "awaiting reply", flush=True)
            phase = "chat"
        else:
            accid = rpc.add_account()
            rpc.set_config(accid, "displayname", "Denyut CI peer")
            rpc.add_transport_from_qr(accid, "DCACCOUNT:" + relay_url)

        deadline = time.time() + total_timeout
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
                    if not scenario:
                        return 0
                    return _run_scenario(rpc, accid, chat_id, EventTypeIncomingMsg)

    print("CHAT FAIL: did not complete (phase=%s)" % phase, flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())

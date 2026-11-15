"""In-app DeltaChat bot service.

Runs the Denyut assistant as a DeltaChat bot inside the Android app.
BotService (Java) calls serve() on a Python thread; the UI calls
status(), setup_account() and invite_link().

Account data stays in the app's private storage. No account, relay or
contact is hardcoded; setup happens once from the UI.

Built against deltachat2 2.58 API (verified against the installed
package): IOTransport spawns the deltachat-rpc-server binary bundled in
the official Android wheel; hooks receive (bot, account_id, event).
"""

import logging
import os
import stat
import threading
import time

from denyut.core import Assistant

logger = logging.getLogger("denyut.android_bot")

_state = {"status": "stopped", "detail": ""}
_stop = threading.Event()
_rpc_holder = {}

REMINDER_POLL_SECONDS = 30
DEFAULT_RELAY = "https://nine.testrun.org/new"


def status():
    return _state["status"] + (": " + _state["detail"] if _state["detail"] else "")


def _set(status, detail=""):
    _state["status"] = status
    _state["detail"] = detail
    logger.info("status: %s %s", status, detail)
    # Chaquopy bridges stdout to logcat; logging.info has no handlers by
    # default, so print too. Keeps the service observable and lets the CI
    # smoke test assert on real runtime state.
    print("denyut status: %s %s" % (status, detail), flush=True)


def find_server_executable(provided=None):
    """Use the binary path the app extracted from its assets. The
    package-bundled path is only a fallback: Chaquopy's asset packing
    drops extension-less executables from Python packages."""
    if provided:
        exe = provided
    else:
        import deltachat_rpc_server
        exe = os.path.join(os.path.dirname(deltachat_rpc_server.__file__),
                           "deltachat-rpc-server")
    mode = os.stat(exe).st_mode
    if not mode & stat.S_IXUSR:
        try:
            os.chmod(exe, mode | stat.S_IXUSR)
        except PermissionError:
            # Android extracts native libs as apk_data_file: SELinux
            # denies setattr there, but the system already installs
            # them executable (CI run 43682543915). Only real when the
            # file ends up non-executable.
            if not os.access(exe, os.X_OK):
                raise
    return exe


def setup_account(accounts_dir, rpc_server=None, relay_url=DEFAULT_RELAY, display_name="Denyut"):
    """One-time: create a chatmail account for the bot.

    Mirrors deltabot-cli's init: add account, mark as bot, configure
    from the relay's DCACCOUNT QR code, wait for configure to finish.
    Returns True on success. Called from the UI, never automatically.
    """
    from deltachat2 import Rpc
    from deltachat2.transport import IOTransport

    _set("setup", "creating account via " + relay_url)
    with IOTransport(accounts_dir=accounts_dir,
                     rpc_executable=find_server_executable(rpc_server)) as trans:
        rpc = Rpc(trans)
        accid = rpc.add_account()
        rpc.set_config(accid, "bot", "1")
        rpc.set_config(accid, "displayname", display_name)
        done = threading.Event()
        ok = threading.Event()

        def watch():
            while not done.is_set():
                event = rpc.get_next_event().event
                progress = getattr(event, "progress", None)
                if progress is not None:
                    if progress >= 1000:
                        ok.set()
                        done.set()
                    elif progress == 0:
                        done.set()  # failure

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        rpc.add_transport_from_qr(accid, "DCACCOUNT:" + relay_url)
        done.wait(timeout=120)
    if ok.is_set():
        _set("stopped", "account ready")
        return True
    _set("setup_failed", "configuration did not complete")
    return False


def invite_link(accounts_dir, rpc_server=None):
    """The bot's invite link: the owner shares/QRs it to contacts."""
    from deltachat2 import Rpc
    from deltachat2.transport import IOTransport

    with IOTransport(accounts_dir=accounts_dir,
                     rpc_executable=find_server_executable(rpc_server)) as trans:
        rpc = Rpc(trans)
        accids = rpc.get_all_account_ids()
        if not accids:
            return ""
        return rpc.get_chat_securejoin_qr_code(accids[0], None)


def _make_hooks(assistant, rpc_ref):
    from deltachat2 import MsgData, events

    hooks = events.HookCollection()

    @hooks.on(events.NewMessage())
    def on_message(bot, accid, event):
        text = (event.msg.text or "").strip()
        if not text:
            return
        reply = assistant.handle(text, sender=str(event.msg.from_id))
        bot.rpc.send_msg(accid, event.msg.chat_id, MsgData(text=reply))

    return hooks


def _reminder_loop(assistant, rpc):
    from deltachat2 import MsgData

    while not _stop.wait(REMINDER_POLL_SECONDS):
        try:
            for accid in rpc.get_all_account_ids():
                for sender, text in assistant.due_reminders():
                    chat_id = rpc.get_chat_id_by_contact_id(accid, int(sender))
                    if chat_id:
                        rpc.send_msg(accid, chat_id,
                                     MsgData(text="Reminder: " + text))
        except Exception:
            logger.exception("reminder loop")


def serve(accounts_dir, store_dir, rpc_server=None):
    """Blocking bot loop; runs on BotService's Python thread."""
    from deltachat2 import Bot, Rpc
    from deltachat2.transport import IOTransport

    _stop.clear()
    # Pass the behavior file explicitly: behavior.py's DEFAULT_PATH uses
    # "<pkg>/../behavior.json", and Chaquopy's AssetFinder paths are
    # virtual - the ".." component cannot resolve there (FileNotFoundError
    # in CI run 43681839133). behavior.json sits next to this module.
    behavior = os.path.join(os.path.dirname(__file__), "behavior.json")
    assistant = Assistant(behavior_path=behavior, store_dir=store_dir)
    _set("starting")
    try:
        with IOTransport(accounts_dir=accounts_dir,
                         rpc_executable=find_server_executable(rpc_server)) as trans:
            rpc = Rpc(trans)
            _rpc_holder["rpc"] = rpc
            accids = rpc.get_all_account_ids()
            if not accids or not rpc.is_configured(accids[0]):
                _set("waiting_setup",
                     "no account yet - run setup from the app")
                polls = 0
                while not _stop.wait(5):
                    accids = rpc.get_all_account_ids()
                    if accids and rpc.is_configured(accids[0]):
                        break
                    # Every poll is a fresh JSON-RPC round trip; printing
                    # it proves over an interval that the rpc-server child
                    # is still alive and answering (CI smoke gate).
                    polls += 1
                    print("denyut poll: waiting_setup round trip #%d ok" % polls,
                          flush=True)
                if _stop.is_set():
                    return
            bot = Bot(rpc, _make_hooks(assistant, rpc))
            threading.Thread(target=_reminder_loop, args=(assistant, rpc),
                             daemon=True).start()
            _set("running")
            bot.run_forever()
    except Exception as e:
        _set("error", repr(e))
    finally:
        _rpc_holder.pop("rpc", None)
        if _state["status"] not in ("error",):
            _set("stopped")


def stop():
    _stop.set()
    rpc = _rpc_holder.get("rpc")
    if rpc is not None:
        try:
            rpc.stop_io_for_all_accounts()
        except Exception:
            logger.exception("stop_io")

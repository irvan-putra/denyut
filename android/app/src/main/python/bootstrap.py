"""Smoke-test entry point for the Android packaging.

Proves the Denyut core and the DeltaChat dependency chain can be imported
and run inside Android-embedded Python. No account, no network use.
"""

import importlib
import os
import sys
import tempfile


def selftest():
    lines = ["Denyut Android smoke test", "Python " + sys.version.split()[0]]
    try:
        from denyut.core import Assistant
        store = tempfile.mkdtemp()
        behavior = os.path.join(os.path.dirname(__file__), "behavior.json")
        a = Assistant(behavior_path=behavior, store_dir=store)
        lines.append("denyut core: " + a.handle("/note android smoke", sender="smoke"))
        lines.append("denyut core: " + a.handle("/notes", sender="smoke"))
    except Exception as e:
        lines.append("denyut core: FAILED (%r)" % (e,))
    try:
        import android_bot
        lines.append("android_bot service module: imports OK")
    except Exception as e:
        lines.append("android_bot service module: FAILED (%r)" % (e,))
    for mod in ("deltachat_rpc_server", "deltachat2", "deltabot_cli"):
        try:
            importlib.import_module(mod)
            lines.append(mod + ": installed")
        except Exception as e:
            lines.append(mod + ": MISSING (%r)" % (e,))
    return "\n".join(lines)

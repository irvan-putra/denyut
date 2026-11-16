"""Host-only synthetic bridge checks: not native/model execution evidence."""
import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "android/app/src/main/python/denyut/local_android.py"
spec = importlib.util.spec_from_file_location("local_android_under_test", MODULE)
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)


class Runtime:
    state = "unloaded"
    calls = []

    def status(self):
        return self.state

    def complete(self, system, text):
        self.calls.append((system, text))
        return "synthetic answer"


def test_unloaded_does_not_generate():
    runtime = Runtime()
    runtime.calls = []
    backend = local.LocalAndroidBackend(lambda: runtime)
    assert "unloaded" in backend.complete("", [], "hello")
    assert runtime.calls == []


def test_ready_stateless_request_omits_history():
    runtime = Runtime()
    runtime.state = "ready"
    runtime.calls = []
    backend = local.LocalAndroidBackend(lambda: runtime)
    assert backend.complete("public system", [{"content": "other private history"}], "synthetic") == "synthetic answer"
    assert runtime.calls == [("public system", "synthetic")]


def test_busy_does_not_generate():
    runtime = Runtime()
    runtime.state = "generating"
    runtime.calls = []
    assert "busy" in local.LocalAndroidBackend(lambda: runtime).complete("", [], "hi")
    assert not runtime.calls


def test_failure_sanitized_no_remote_fallback():
    def fail():
        raise RuntimeError("private diagnostics")
    reply = local.LocalAndroidBackend(fail).complete("", [], "synthetic")
    assert "private diagnostics" not in reply
    assert "No cloud request" in reply


def test_long_input_does_not_resolve_native():
    def forbidden():
        raise AssertionError("must not resolve")
    assert "too long" in local.LocalAndroidBackend(forbidden).complete("", [], "a" * 4001)


def test_empty_reply_is_not_success():
    runtime = Runtime()
    runtime.state = "ready"
    runtime.complete = lambda *_: " "
    assert "no text" in local.LocalAndroidBackend(lambda: runtime).complete("", [], "hi")

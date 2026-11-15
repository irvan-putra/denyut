import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

from intuisi.models import EchoBackend, OpenAICompatibleBackend  # noqa: E402


def test_echo_backend():
    b = EchoBackend()
    assert "placeholder" in b.complete("sys", [], "hi")


def test_openai_backend_requires_key(monkeypatch):
    monkeypatch.delenv("INTUISI_API_KEY", raising=False)
    b = OpenAICompatibleBackend("http://127.0.0.1:9/v1", "m")
    with pytest.raises(RuntimeError, match="INTUISI_API_KEY"):
        b.complete("sys", [], "hi")

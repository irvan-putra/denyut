"""Prove the openai-compatible backend speaks the right HTTP protocol,
using a local mock server. No real model, no network."""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from intuisi.core import Assistant  # noqa: E402
from intuisi.models import OpenAICompatibleBackend  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert self.path == "/v1/chat/completions"
        assert self.headers["Authorization"] == "Bearer test-key"
        assert body["model"] == "test-model"
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][-1]["content"] == "hello"
        out = {"choices": [{"message": {"role": "assistant",
                                        "content": "hi from mock"}}]}
        payload = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def test_backend_against_mock(monkeypatch, tmp_path):
    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        monkeypatch.setenv("INTUISI_API_KEY", "test-key")
        backend = OpenAICompatibleBackend(
            "http://127.0.0.1:%d/v1" % server.server_port, "test-model")
        reply = backend.complete("you are helpful", [], "hello")
        assert reply == "hi from mock"

        # and through the full Assistant with this backend configured
        cfg = tmp_path / "behavior.json"
        cfg.write_text(json.dumps({
            "assistant": {"name": "Intuisi", "system_prompt": "s"},
            "model": {"backend": "openai-compatible",
                      "base_url": "http://127.0.0.1:%d/v1" % server.server_port,
                      "model": "test-model", "api_key_env": "INTUISI_API_KEY"},
            "skills": {"notes": {"enabled": False},
                       "reminders": {"enabled": False},
                       "echo": {"enabled": False}}}))
        a = Assistant(behavior_path=str(cfg), store_dir=str(tmp_path))
        assert a.handle("hello", sender="u1") == "hi from mock"
    finally:
        server.shutdown()

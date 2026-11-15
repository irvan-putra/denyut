"""Model backends.

The assistant does not require a model: rule-based skills work offline.
A model, when configured, handles free-form messages that no skill claims.

Backends:
- EchoBackend: test double, returns a fixed canned reply. Offline.
- OpenAICompatibleBackend: POST /chat/completions to any OpenAI-compatible
  endpoint (llama.cpp server, OpenRouter, Groq, Mistral, ...). Uses only
  the Python standard library; the API key comes from the environment,
  never from the config file or chat.
"""

import json
import os
import urllib.request


class EchoBackend:
    name = "echo"

    def complete(self, system_prompt, history, user_text):
        return "No model is configured. This is a placeholder reply."


class OpenAICompatibleBackend:
    name = "openai-compatible"

    def __init__(self, base_url, model, api_key_env="INTUISI_API_KEY",
                 max_tokens=512, timeout=60):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.max_tokens = max_tokens
        self.timeout = timeout

    def complete(self, system_prompt, history, user_text):
        api_key = os.environ.get(self.api_key_env, "")
        if not api_key:
            raise RuntimeError(
                "Model backend needs env var %s set (kept out of the repo "
                "on purpose)" % self.api_key_env)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + api_key},
            method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()


def build_backend(cfg):
    m = cfg.get("model", {})
    kind = m.get("backend", "none")
    if kind in ("none", ""):
        return None
    if kind == "echo":
        return EchoBackend()
    if kind == "openai-compatible":
        return OpenAICompatibleBackend(
            base_url=m.get("base_url", "http://localhost:8080/v1"),
            model=m.get("model", "local-model"),
            api_key_env=m.get("api_key_env", "INTUISI_API_KEY"),
            max_tokens=int(m.get("max_tokens", 512)))
    raise ValueError("unknown model backend: %r" % kind)

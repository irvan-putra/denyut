# Denyut

An independent, open-source personal assistant you can inspect and change.
Every behavior lives in plain files: `behavior.json` for persona/model/skills,
`denyut/skills/` for what it can do. No hidden prompts.

First channel: a **DeltaChat bot** (its own chatmail account, reachable only
via its invite QR code). The core is transport-agnostic, so an Android app
or another channel can drive the same `Assistant` class later.

## Layout

- `denyut/core.py` — message routing: commands, skills, model fallback,
  and an approval-boundary mechanism (skills ask yes/no before
  consequential actions)
- `denyut/behavior.py` + `behavior.json` — all tunable behavior
- `denyut/models.py` — model backends: none (default, free, offline),
  `echo` (testing), `openai-compatible` (llama.cpp server, OpenRouter,
  Groq, Mistral, ...). API key comes from the `DENYUT_API_KEY` environment
  variable, never from the repo or chat.
- `denyut/skills/notes.py` — persistent notes (/note, /notes, /done;
  archives instead of deleting)
- `denyut/skills/reminders.py` — time-based reminders (/remind 45m ...;
  fires even when nobody is chatting, via a timer in the adapter)
- `denyut/deltachat_bot.py` — DeltaChat adapter (only DeltaChat-specific
  file)

## Run the tests (no network, no account, no model needed)

    pip install pytest
    python -m pytest tests/

## Run the DeltaChat bot

Requires Python >= 3.11 (deltachat2 uses enum.StrEnum).

    pip install deltabot-cli
    python -m denyut.deltachat_bot init DCACCOUNT:https://nine.testrun.org/new
    python -m denyut.deltachat_bot config displayname "Denyut"
    python -m denyut.deltachat_bot link    # invite link / QR
    python -m denyut.deltachat_bot serve

Open the invite link in DeltaChat and chat. Commands: /help, /note,
/notes, /done, /remind, /reminders, /cancel, /echo. Free-form messages
need a configured model backend.

## Model options (decide before any cost)

- **none** (default): commands + reminders, fully free.
- **local**: llama.cpp's OpenAI-compatible server on your own hardware.
  On a phone, only small quantized models (roughly 1B-3B parameters) are
  realistic, and speed depends heavily on the device.
- **hosted**: any OpenAI-compatible API. Some providers have offered free
  tiers; verify current terms at setup time. Set base_url/model in
  behavior.json and the key in DENYUT_API_KEY.

## Security notes

- No secrets in the repo; the model API key is an environment variable.
- The bot accepts messages only from DeltaChat contacts it has accepted
  (invite-link model), and stores data locally as plain JSON.
- Store paths and the behavior file are owner-controlled local config;
  skill store filenames come from behavior.json.
- Consequential actions go through an explicit yes/no confirmation in
  core (see Confirm in denyut/core.py).

## License

Denyut's own code is MIT (see LICENSE). The bundled DeltaChat core stays MPL-2.0 - its notices and corresponding-source links live in NOTICE.

## Research notes

- [Android background bot constraints](docs/research/android-background-bot-constraints.md) - official Android documentation notes on executable loading, foreground-service time limits and background starts; no device test or service-type choice claimed.
- [Cloud options for Android testing](docs/research/cloud-android-test-options.md) - dated public prices and limits checked 2026-11-16; not quotes or reservations.
- [Small local model and low-cost provider options](docs/research/small-local-model-options.md) - source notes on a local model candidate, a llama.cpp route, and provider-side cost controls; no phone performance claims.
- [Denyut hosting cost estimate](docs/research/hosting-cost-estimate.md) - bounded single-user hosting prices, dated sources, and open tax/traffic/performance questions; no rental made.
- [Gemma and AI Studio hosted-access supplement](docs/research/gemma-hosted-access-supplement.md) - current API, subscription-credit and privacy constraints; no account, billing, model download or integration tested.
- [Local Gemma bridge checkpoint](docs/research/local-gemma-bridge-checkpoint.md) - preparatory code/build evidence, independent review findings and remaining activation gates; no weights or inference proven.

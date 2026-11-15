# Intuisi

An independent, open-source personal assistant you can inspect and change.
Every behavior lives in plain files: `behavior.json` for persona/model/skills,
`intuisi/skills/` for what it can do. No hidden prompts.

First channel: a **DeltaChat bot** (its own chatmail account, reachable only
via its invite QR code). The core is transport-agnostic, so an Android app
or another channel can drive the same `Assistant` class later.

## Layout

- `intuisi/core.py` — message routing: commands, skills, model fallback,
  and an approval-boundary mechanism (skills ask yes/no before
  consequential actions)
- `intuisi/behavior.py` + `behavior.json` — all tunable behavior
- `intuisi/models.py` — model backends: none (default, free, offline),
  `echo` (testing), `openai-compatible` (llama.cpp server, OpenRouter,
  Groq, Mistral, ...). API key comes from the `INTUISI_API_KEY` environment
  variable, never from the repo or chat.
- `intuisi/skills/notes.py` — persistent notes (/note, /notes, /done;
  archives instead of deleting)
- `intuisi/skills/reminders.py` — time-based reminders (/remind 45m ...;
  fires even when nobody is chatting, via a timer in the adapter)
- `intuisi/deltachat_bot.py` — DeltaChat adapter (only DeltaChat-specific
  file)

## Run the tests (no network, no account, no model needed)

    pip install pytest
    python -m pytest tests/

## Run the DeltaChat bot

Requires Python >= 3.11 (deltachat2 uses enum.StrEnum).

    pip install deltabot-cli
    python -m intuisi.deltachat_bot init DCACCOUNT:https://nine.testrun.org/new
    python -m intuisi.deltachat_bot config displayname "Intuisi"
    python -m intuisi.deltachat_bot link    # invite link / QR
    python -m intuisi.deltachat_bot serve

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
  behavior.json and the key in INTUISI_API_KEY.

## Security notes

- No secrets in the repo; the model API key is an environment variable.
- The bot accepts messages only from DeltaChat contacts it has accepted
  (invite-link model), and stores data locally as plain JSON.
- Store paths and the behavior file are owner-controlled local config;
  skill store filenames come from behavior.json.
- Consequential actions go through an explicit yes/no confirmation in
  core (see Confirm in intuisi/core.py).

## License

MIT (see LICENSE). DeltaChat core itself is MPL-2.0 (see NOTICE).

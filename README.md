# Denyut

An independent, open-source personal assistant you can inspect and change.
Every behavior lives in plain files: `behavior.json` for persona/model/skills,
`denyut/skills/` for what it can do. No hidden prompts.

First channel: a **DeltaChat bot** (its own chatmail account, reachable only
via its invite QR code). The core is transport-agnostic, so an Android app
or another channel can drive the same `Assistant` class later.

## Android app

The signed Android v0.6.4 test APK is published as a direct [GitHub release asset](https://github.com/irvan-putra/denyut/releases/download/v0.6.4/denyut-v0.6.4.apk) (`denyut-v0.6.4.apk`, for arm64 phones); see the [release page](https://github.com/irvan-putra/denyut/releases/tag/v0.6.4). The app runs the DeltaChat bot on the phone: notes and reminders work offline with no model. Local-model loading is disabled in this build and has not been validated on real phones; there is no cloud fallback. Builds come from the manual `sign test apk` workflow, which tests without secrets before a separate minimal signing job.

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
- `denyut/skills/memory.py` — long-term facts (/remember, /memory,
  /forget; archived, sent to the model as context) and an optional,
  off-by-default daily journal searched with /recall
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
/notes, /done, /remind, /reminders, /cancel, /remember, /memory,
/forget, /recall, /echo. Free-form messages
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

- [Mermaid diagrams inside GitHub pull requests](docs/research/github-pr-mermaid-diagrams.md) - inline diagrams, preservation of existing PR text, and the difference between authenticated readback and visual verification.

- [Android emulator in GitHub Actions: documented setup facts](docs/research/android-emulator-in-github-actions-setup-facts.md) - documentation-only notes on runner acceleration and emulator setup; nothing was run for this note.
- [AOSP iptables: how interface negation prints](docs/research/aosp-iptables-listing-format-for-firewall-checks.md) - source reading at one AOSP tag; no device test or shipped-variant claim.

- [Android background bot constraints](docs/research/android-background-bot-constraints.md) - official Android documentation notes on executable loading, foreground-service time limits and background starts; no device test or service-type choice claimed.
- [Cloud options for Android testing](docs/research/cloud-android-test-options.md) - dated public prices and limits checked 2026-11-16; not quotes or reservations.
- [Small local model and low-cost provider options](docs/research/small-local-model-options.md) - source notes on a local model candidate, a llama.cpp route, and provider-side cost controls; no phone performance claims.
- [Denyut hosting cost estimate](docs/research/hosting-cost-estimate.md) - bounded single-user hosting prices, dated sources, and open tax/traffic/performance questions; no rental made.
- [Gemma and AI Studio hosted-access supplement](docs/research/gemma-hosted-access-supplement.md) - current API, subscription-credit and privacy constraints; no account, billing, model download or integration tested.
- [Local Gemma bridge checkpoint](docs/research/local-gemma-bridge-checkpoint.md) - preparatory code/build evidence, independent review findings and remaining activation gates; no weights or inference proven.
- [Existing Delta Chat LLM bots and design options](docs/design-review-existing-work-and-options.md) - excerpt-based leads only (repos not read directly), four decision cards with Central Logs not proposed, and unchanged open gaps; no code, dependency, model or account change.
- [Always-on bot patterns mapped to Denyut](docs/research/always-on-bot-patterns.md) - what a public talk's ideas (memory files, daily log, dreaming, wake-ups, permissions) mean for Denyut; offline memory commands built, dreaming and event wake-ups not built, no new account, service or cost.

---

Built with AI assistance (Instinct and others). Not everything has been reviewed by Irvan.

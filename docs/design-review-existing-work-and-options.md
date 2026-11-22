---
id: denyut-design-review
type: design-note
---
# Denyut design review: what already exists, and options to choose from

Written 22 Nov 2026. Applies two habits from the Kaji notes to Denyut: [check what exists before building](https://vanipy.com/kaji/internal-tools/) and [one review page per decision set](https://github.com/irvan-putra/kaji/blob/main/docs/human-review-pages.md). Nothing here changes code, adds a dependency, or turns on a model.

## 1. What already exists (checked 22 Nov 2026, search-result excerpts only)

Public Delta Chat bots that connect a language model. Existence, the one-line descriptions and the license fields below were seen in search-result excerpts, not by reading each repository page; treat every row as an unverified lead until its repo is read directly. Code quality, safety and whether they still work were not assessed.

| Project | What it says it is | License shown |
| --- | --- | --- |
| [deltachat-bot/llmbot](https://github.com/deltachat-bot/llmbot) | Conversational Delta Chat bot using a local LLM | not checked |
| [deltachat-bot/chatbot](https://github.com/deltachat-bot/chatbot) | Conversational chat-bot for Delta Chat | GPL-3.0 |
| [aidik/Delta-Chat-AI-Bot](https://github.com/aidik/Delta-Chat-AI-Bot) | AI-powered chatbot for Delta Chat | BSD-3-Clause |
| [Simon-Laux/hermes-deltachat-platform](https://github.com/Simon-Laux/hermes-deltachat-platform) | Delta Chat platform for the Hermes gateway | not checked |
| [maphouse/deltachat-claude-code](https://github.com/maphouse/deltachat-claude-code) | Bridges Claude Code CLI sessions into Delta Chat | MIT |

What this tells us: a model behind a Delta Chat bot is not new. Denyut's own goals are inspectable behavior files, offline notes and reminders with no model, an approval step before consequential actions, and an Android app that carries the bot. The excerpts do not say whether any of these projects have similar features, so this search does not show that Denyut is different; a direct read of the repos would be needed for any comparison.

Not found or not looked for: any project that combines all of that. That is a limit of a short excerpt-based search, not a claim that none exists.

## 2. Decision cards

Each card says what it would do, what it would not do, and whether it is done or only proposed. Tick state belongs on the reviewer's device. A tick selects only that card.

**A. Read before reuse (proposed).** Before writing any new Denyut skill or adapter, spend a short, dated search for existing code, and record the result in `docs/research/`. Does not: add a dependency, copy code, or change the license mix without its own decision.

**B. Borrow ideas, not code (proposed).** Read the MIT and BSD projects above for design ideas such as command layout and message handling. Does not: vendor their code. Denyut stays MIT, with Delta Chat parts MPL-2.0.

**C. Review page per design choice (proposed).** Future design choices, such as local model activation gates or a new skill, get one short decision page in this repo with limits and non-goals listed. Does not: replace the existing approval step in `core.py`.

**D. Central Logs as a dependency (not proposed).** Listed so it is visible. Denyut already keeps notes locally as plain JSON. Adding an external logging dependency would need its own decision and a code check. Revisit only if a concrete need appears.

## 3. Deliberately not proposed

- Turning on local model loading. Still gated by the open items in the [local Gemma bridge checkpoint](research/local-gemma-bridge-checkpoint.md).
- Any cloud model, paid service, new account or hosting. Needs explicit approval first.
- Replacing offline notes and reminders.

## 4. Unchanged open gaps

- Android emulator tests: three widget due-time format tests fail on the CI runners, a defect that predates the browser companion. Assertions were not changed to hide it.
- Not verified: on a real phone, model import, inference, phone performance.

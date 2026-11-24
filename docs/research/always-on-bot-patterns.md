# Always-on bot patterns, mapped to Denyut

Checked 2026-11-24. Source: a talk summarized in Kaji's [How always-on bots work](https://github.com/irvan-putra/kaji/blob/main/docs/always-on-bot-patterns.md) (speaker's account; nothing verified inside any named product; automatic transcript, not reviewed against the video). This page only maps its ideas onto Denyut. No paid or usage-billed service, new account or new connection is proposed.

| Pattern from the talk | Denyut today | Decision |
| --- | --- | --- |
| Context is files loaded every turn | Only the system prompt in `behavior.json` | **Built (2026-11-24):** `/remember`, `/memory`, `/forget` keep plain facts per sender (archived, not destroyed) and send them to the model with each free-form message. Offline; unit-tested; not run on a phone. |
| Daily logs, searched on demand, not auto-loaded | None | **Built, off by default:** set `skills.memory.journal` to `true` and free-form messages are appended to one file per day under `journal/`. `/recall <word>` searches it. Never sent to the model automatically. Not tested on a phone. |
| "Dreaming": a nightly pass that promotes log lines to long-term memory | None | **Not built.** Needs a model to judge what matters. Would run only on a local model, with the result shown for a yes before it is saved. Parked until local model loading is validated. |
| Wake on a schedule | Reminders fire from a timer, even when nobody is chatting | Already there. A periodic "heartbeat" check is not added: no task needs it yet, and Android background limits apply (see [background constraints](android-background-bot-constraints.md)). |
| Wake on events | None | Not built. Would need a source that sends events, which means a new connection. Not proposed. |
| Terminal, browser, 1,700 apps via a vendor | None | Not adopted. Needs new accounts or paid services; out of scope for Denyut. |
| More channels, one agent | DeltaChat adapter; core is transport-agnostic | Unchanged. |
| Permissions: scopes and a block list | Approval step (`Confirm`) before consequential actions; archive instead of delete | Unchanged. No outside tools are connected, so there is nothing to scope yet. |

## Limits

- The new memory code was tested with the repo's offline tests (41 passed, 3 skipped, the Delta Chat adapter tests excluded here because that library was not installed). The emulator suite and a real phone were not run.
- No new APK was built or published; the Android bundle copies `denyut/` at build time, so a release is needed before the phone has `/remember`.
- Facts and journal lines are stored in plain JSON and Markdown on the device and are not encrypted.

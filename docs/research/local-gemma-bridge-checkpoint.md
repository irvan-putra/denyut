# Local Gemma preparation and independent review checkpoint

2026-11-16. Unmerged preparatory patch based on
8f501b0497300a8072d5b8eb365dcb979cd792f0. Not a model-enabled release.

## Evidence, separated by kind
The initial bridge patch compiled and full assembleDebug passed under JDK21,
Gradle8.9, AGP8.7.3, compileSdk35, with actual LiteRT-LM Android0.19.1 AAR. D8
and APK packaging passed. Python3.12 plus the real deltachat2/full rpc-server2.58.0
dependency were installed; 47 tests passed. The suite also includes a host-only
adapter test that swaps a stub into `sys.modules`. Six new bridge checks used a
synthetic runtime; neither these tests nor the manual Java boundary harness
initialize or exercise real native inference. The harness passed against the
actual AAR classpath but is not wired into CI.

An independent static review read all eight initial files and pinned dependency
metadata. That review did not build or run native inference. It confirmed no
new HTTP/downloader/fallback; lazy Java resolution; app-private size/hash checked
model import; fresh no-history/no-tool conversations; sanitized errors; unloaded
default. It found concrete bugs and gates listed below. Review is not an audit.

No model weights downloaded, no inference or phone-speed/RAM/battery proof,
no user device installation or release. The 2,588,147,712-byte size and SHA256
181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c
were copied from public repository metadata, not computed from a download.
Runtime is Apache-2.0 per POM; model Apache-2.0 per linked license/metadata.
No app license change or model binary redistribution.

## Review findings and correction work
- Engine construction was outside its load failure handler. Constructor failure
  could leave status stuck loading. Moved construction inside the handler;
  constructor-failure injection is added to the manual Java boundary harness.
- A 4000-character guard was too loose for a 1024-token total budget. Reduced to
  1500 characters as a conservative trial cap, NOT a tokenizer guarantee. Native
  overflow still fails locally; no remote fallback.
- Native generation is synchronous and has no proven wall-clock timeout. The
  combined draft routes it through a single worker so deterministic command
  handling is not tied to inference completion, and adds a synthetic blocked-
  transport test. This does not establish a runtime timeout or Android behavior.
- The draft includes session-only owner/account/chat binding and fresh peer
  verification; host tests exercise synthetic RPC shapes. The owner-picker and
  real-device path are not runtime-verified. Activation remains false.
- Java boundary checks now cover a tiny synthetic import, hash/rename, failure
  preservation and cancellation. Those are small fixtures, not the real model;
  the full-file hash of the 2.59 GB artifact was not computed here.
- Runtime0.19.1 is pre-1.0; API/version changes require recompile and review.
  Transitive dependency locking still needed before release. The local follow-up
  adds a bundled, in-app readable copy of the versioned AAR LICENSE and
  THIRD_PARTY_NOTICE.txt. It loads the asset off the UI thread and shows bounded
  pages so the full bundle is accessible without placing all of it in one view;
  its dependency notices must be regenerated/reviewed
  when upgrading LiteRT-LM. This is not a release inventory for other app parts.
- Native memory failure can kill the process, including the bot. This is a trial,
  not an unattended reliable assistant. Existing sender authorization/reminder
  durability issues are not fixed by adding a model.

## Owner UI work, still gated
An unmerged owner-only file-picker/import/load/unload/cancel screen is being
prepared with explicit 2.59GB copy consent, background work, percentage progress,
space preflight and stale partial-file cleanup. No automatic download/load or
exported activation intent. Load remains disabled for the owner-routing gate.
The UI is not pixel-verified or runtime-proven and must not be called ready.
Import cancellation is cooperative; blocked provider reads and native loading
are not guaranteed cancellable. Process death leaves no persistent opt-in.

## Sequence and next work
The combined local follow-up changes both Android build workflows to JDK21,
enables KVM for the account-free UI emulator, installs with ordinary runtime
permission grants, and adds polled UI smoke checks plus explicit CI assertions
that both activation gates remain false. The smoke now checks the bundled
license text and disabled controls; it has not been dispatched or run on an
emulator. Executable changes remain unmerged pending independent review. No
protected chat E2E rerun, account activity, model weights or activation is part
of this work. UI pixels and runtime behavior still require the gated review.

## Sources
- https://github.com/google-ai-edge/LiteRT-LM/blob/v0.19.1/kotlin/java/com/google/ai/edge/litertlm/Engine.kt
- https://github.com/google-ai-edge/LiteRT-LM/blob/v0.19.1/kotlin/java/com/google/ai/edge/litertlm/Config.kt
- https://github.com/google-ai-edge/LiteRT-LM/blob/v0.19.1/kotlin/java/com/google/ai/edge/litertlm/Conversation.kt
- https://github.com/google-ai-edge/LiteRT-LM/blob/v0.19.1/kotlin/java/com/google/ai/edge/litertlm/Message.kt
- https://dl.google.com/dl/android/maven2/com/google/ai/edge/litertlm/litertlm-android/0.19.1/litertlm-android-0.19.1.pom
- https://huggingface.co/api/models/litert-community/gemma-4-E2B-it-litert-lm?blobs=true
- https://ai.google.dev/gemma/docs/core
- https://ai.google.dev/gemma/apache_2

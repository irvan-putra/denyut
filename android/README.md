# Intuisi Android wrapper

Embeds the same Python `intuisi` core in an Android app via Chaquopy, with
the DeltaChat stack resolved from PyPI's official Android wheels
(deltachat2, deltabot-cli, deltachat-rpc-server android_21_arm64_v8a).

## What is verified (locally, 2026-11-15)

- `./gradlew :app:assembleDebug` succeeds (JDK 17, SDK 35, Gradle 8.9,
  AGP 8.7.3, Chaquopy 17.2.0): ~50 MB debug APK, arm64-v8a only.
- APK contents checked byte-level: Python 3.12 runtime, the intuisi package
  + behavior.json, and `assets/deltachat-rpc-server` - a 22 MB ARM
  aarch64 ELF with interpreter /system/bin/linker64 (a real Android
  bionic binary), fetched from PyPI with sha256 pinned in
  tools/fetch_rpc_server.py.
- Import/runtime test on the same Python version (3.12): intuisi core runs
  /note + /notes; android_bot service module imports with the real
  deltachat2/deltabot_cli/deltachat_rpc_server installed.
- Foreground service implemented: BotService (persistent notification,
  dataSync type) runs android_bot.serve() on a Python thread; UI shows
  live status and start/stop. Reminder timer fires from the service.

## Caught during verification

- Chaquopy's asset packing silently drops extension-less executables
  from Python packages: the wheel's bundled rpc-server binary never
  reached the APK. Fixed by shipping it as an explicit asset via
  tools/fetch_rpc_server.py (pinned URL + sha256) and extracting it at
  runtime (ServerBin.java). The first "APK contains the binary" claim
  was wrong; it was only in build intermediates.

## What is NOT proven yet

- On-device/on-emulator runtime. Next evidence: the GitHub Actions
  emulator job (.github/workflows/android.yml, x86_64 google_apis API-34 image with ARM64 translation)
  once the repo exists, or installing the APK on the actual phone.
  arm64-only is deliberate: deltachat-rpc-server ships no x86_64
  Android wheel, so a dual-ABI build cannot carry the DeltaChat core.
- Account setup flow (setup_account/invite_link) is written against the
  verified deltachat2 2.58 API but has never run against a real relay.
- Battery/background behavior of the service on the actual phone.

## Licensing

- Chaquopy: free and open source since 12.0.1 (vendor licensing page,
  chaquo.com/chaquopy/license/, checked 2026-11-15); distributed via
  Maven Central. We use 17.2.0 from mavenCentral().
- DeltaChat core is MPL-2.0; deltabot-cli/deltachat2/deltachat-rpc-client
  are published by the Delta Chat project. Intuisi's own code is MPL-2.0
  (see ../LICENSE), the same license as the DeltaChat core.

## Build

Needs JDK 17, Android SDK 35, and a host Python 3.12 (Chaquopy resolves
requirements with the same major.minor). Then:

    python3 tools/fetch_rpc_server.py   # once, or when bumping core
    cd android && ./gradlew :app:assembleDebug

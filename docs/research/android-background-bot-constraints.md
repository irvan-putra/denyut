# Running a long-lived bot inside an Android app: what the official pages say

Status: official Android pages re-read on 2026-11-16. Nothing here was tested on a device. This note lists documented constraints. It does not decide which service type or distribution route a given app should use.

## Running a bundled executable
- Android's Android 10 behavior-change page says: "Untrusted apps that target Android 10 cannot invoke `execve()` directly on files within the app's home directory." It adds that apps "should load only the binary code that's embedded within an app's APK file." Source: https://developer.android.com/about/versions/10/behavior-changes-10
- A design that unpacks an executable into the app's own files folder and runs it is therefore the pattern this page warns against. This note does not name a replacement approach. Any alternative needs its own source and an on-device test.

## Foreground service time limits
- For apps that target Android 15 or higher, `dataSync` and `mediaProcessing` each have a separate six-hour budget in a 24-hour period while the app is in the background; services of the same type share that type’s budget. After a type’s budget is used, the system calls `Service.onTimeout()` and the service must call `stopSelf()` within a few seconds. If the user brings the app to the foreground, the timer resets. The page lists `WorkManager` as an alternative to a `dataSync` service. Source: https://developer.android.com/develop/background-work/services/fgs/timeout
- The same page describes a separate, more restrictive limit for `shortService`. It does not say which type suits a long-lived connection. That classification is unresolved here: which supported foreground service type fits such a bot, and whether its use is compliant for the chosen distribution route (for example a store listing versus direct install), must be checked against the current rules for that type before building around it.

## Starting the service
- Apps that target Android 12 or higher generally cannot start a foreground service while in the background, with a list of exemptions. Source: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- Whether the exemptions cover auto-start after a reboot for a given service type was not checked.

## Not covered
Emulator and CI options for testing this were not re-verified in this note.

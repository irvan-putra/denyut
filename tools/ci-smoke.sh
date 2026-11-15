#!/bin/sh
# CI smoke test for the Denyut Android app.
#
# android-emulator-runner executes each workflow script line as its own
# "sh -c", so multi-line shell constructs cannot live in the workflow
# YAML; the logic lives here.
#
# What this proves on green: the arm64 app booted under x86_64
# libndk_translation, Chaquopy started Python, BotService exec'd the
# bundled deltachat-rpc-server from nativeLibraryDir, and the server
# answered a real JSON-RPC round trip (the waiting_setup/running marker
# is only printed after get_all_account_ids returns) - plus a live
# rpc-server process on the device.

ls -l apk/
adb install -r -g apk/app-debug.apk || echo "install command failed"
adb logcat -c

# The autostart_bot extra (honored by debug builds only) makes
# MainActivity start BotService through the Start button's own code
# path - adb shell cannot start a non-exported FGS on API 34+
# ("Requires permission not exported from uid", run 43680668213).
adb shell am start -n com.vanipy.denyut/.MainActivity --ez autostart_bot true

i=0
while [ "$i" -lt 15 ]; do
  sleep 10
  adb logcat -d > smoke.log 2>/dev/null
  if grep -q "denyut status: waiting_setup\|denyut status: running\|denyut status: error" smoke.log; then
    break
  fi
  i=$((i + 1))
done

echo "===== filtered logcat ====="
grep -i "denyut\|python\|chaquo\|AndroidRuntime" smoke.log || true

# ps runs on-device, the grep runs HERE - it can never self-match the
# device process list.
adb shell "ps -A" > ps.txt 2>/dev/null || true
echo "===== rpc-server process check ====="
grep -i "rpc" ps.txt || { echo "no rpc process visible; full ps output:"; cat ps.txt; }

# Anything logged between the marker and the ps check (server crash,
# poll error) only lands in a second capture.
adb logcat -d > smoke2.log 2>/dev/null || true
echo "===== post-marker logcat ====="
grep -i "denyut\|python\|Fatal signal\|tombstone" smoke2.log | tail -40 || true

if grep -q "denyut status: error" smoke.log; then
  echo "SMOKE FAIL: bot service reported error"
  exit 1
fi
if grep -q "rpc-server missing\|not executable\|AndroidRuntime.*FATAL" smoke.log; then
  echo "SMOKE FAIL: rpc-server exec problem"
  exit 1
fi
if grep -q "denyut status: waiting_setup\|denyut status: running" smoke.log \
  && grep -qi "rpc" ps.txt; then
  echo "SMOKE PASS: rpc-server exec + live process + JSON-RPC round trip under translation"
  exit 0
fi
echo "SMOKE FAIL: missing status marker or live rpc-server process"
exit 1

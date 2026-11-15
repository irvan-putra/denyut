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

# Give the poll loop time to emit heartbeats (one per 5s, each a fresh
# JSON-RPC round trip) so liveness is proven over an interval, and any
# post-response server death has time to surface.
sleep 15

# ps runs on-device, the grep runs HERE - it can never self-match the
# device process list. Under binfmt_misc translation the server's
# kernel comm is the interpreter name (run 43684014113: pid 3623,
# child of the app, shown as
# "ndk_translation_program_runner_binfmt_misc_arm64"), so a name grep
# for rpcserver/librpcserver never matches. Identity instead: USER ==
# the app's user AND PPID == the app process PID AND runner comm,
# corroborated by /proc/<pid>/cmdline.
app_uid=$(adb shell "pm list packages -U com.vanipy.denyut" | tr -d '\r' | sed 's/.*uid://')
app_user="u0_a$((app_uid - 10000))"
app_pid=$(adb shell "pidof com.vanipy.denyut" | tr -d '\r ')
echo "app uid: $app_uid  user: $app_user  pid: $app_pid"
adb shell "ps -A" > ps.txt 2>/dev/null || true
tr -d '\r' < ps.txt > ps-clean.txt
echo "===== rpc-server process check ====="
server_pid=$(awk -v usr="$app_user" -v ppid="$app_pid" \
  '$1==usr && $3==ppid && $NF ~ /^ndk_translation_program_runner/ {print $2}' ps-clean.txt)
server_line=""
if [ -n "$server_pid" ]; then
  server_line=$(awk -v pid="$server_pid" '$2==pid' ps-clean.txt)
  echo "$server_line"
  echo "server cmdline: $(adb shell "cat /proc/$server_pid/cmdline" 2>/dev/null | tr '\0' ' ')"
else
  echo "no translated-runner child of the app process; full ps output:"
  cat ps-clean.txt
fi

# Anything logged between the marker and the ps check (server crash,
# poll error) only lands in a second capture. Poll heartbeats are
# fresh JSON-RPC round trips: >=2 of them over the wait interval is a
# core-owned liveness signal independent of ps.
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
polls=$(grep -c "denyut poll: waiting_setup round trip" smoke2.log)
echo "poll heartbeats: $polls"
if grep -q "denyut status: waiting_setup\|denyut status: running" smoke.log \
  && { [ -n "$server_pid" ] || [ "$polls" -ge 2 ]; }; then
  echo "SMOKE PASS: rpc-server exec + JSON-RPC round trips under translation"
  echo "(liveness: ${server_line:-no process match} / $polls poll heartbeats)"
  exit 0
fi
echo "SMOKE FAIL: missing status marker, app-owned rpc-server process, or poll heartbeats"
exit 1

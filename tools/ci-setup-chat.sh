#!/bin/sh
# CI setup + chat round trip for the Denyut Android app.
#
# Runs AFTER ci-smoke.sh has passed. Drives the DEBUG-only autosetup
# hook: the app configures a throwaway account on the relay and prints
# its securejoin invite; a second throwaway account on the CI host
# joins and does an /echo round trip. Proves account setup and real
# message send/receive, not just process liveness.
#
# Requires the relay to be reachable from BOTH the emulator and the
# runner. Uses only throwaway accounts; no personal data or contacts.

# Runs AFTER ci-smoke.sh has passed. Push-triggered runs never reach
# the relay: RUN_CHAT_TEST is set only by an explicit workflow_dispatch
# with chat_test=true, so account creation stays tied to a deliberate,
# user-scoped action (approved: two throwaway accounts per dispatch).
if [ "$RUN_CHAT_TEST" != "true" ]; then
  echo "chat round trip skipped (dispatch with chat_test=true to run it)"
  exit 0
fi

echo "===== host-side preflight (no accounts created) ====="
# Every deltachat2 API name the round trip relies on, imported BEFORE
# anything touches the relay: run 43687128731 burned the bot account
# because an ImportError surfaced only after setup had succeeded. This
# check creates no account and costs nothing.
# PINNED matched pair: deltachat2 2.58.0's typed API mirrors chatmail
# core 2.58 (coordinated same-day releases; deltachat2[full] itself pins
# deltachat-rpc-server==2.58.0). Run 43688709457 proved unpinned installs
# drift (client 2.58.0 + server 2.69.0 -> sender.is_verified missing,
# witness crash). tests/test_ci_witness_offline.py guards the parse
# contract offline; the witness also reads replies via the raw call.
python3 -m pip install --quiet deltachat2==2.58.0 deltachat-rpc-server==2.58.0
python3 - <<'PYEOF'
from deltachat2 import MessageData, Rpc
from deltachat2.transport import IOTransport
from deltachat2.types import (
    EventTypeConfigureProgress,
    EventTypeIncomingMsg,
    EventTypeSecurejoinJoinerProgress,
)
print("host preflight ok: deltachat2 API names verified")
PYEOF

RELAY_URL="https://nine.testrun.org/new"
TOKEN="denyut-ci-$(date +%s)"
INVITE_FILE=$(mktemp)
chmod 600 "$INVITE_FILE"

# Redaction for anything printed into the PUBLIC job log. The
# securejoin invite (OPENPGP4FPR:...) is a credential: whoever holds
# it can join the bot account, and it can surface outside the
# "denyut invite" prefix (stack traces, protocol errors). The throwaway
# account addresses are identifiers. The QR travels only through a
# chmod-600 file, never the log; raw logcat files stay on the
# ephemeral runner and are never uploaded as artifacts.
redact() {
  sed -E 's/OPENPGP4FPR:[^ ]*/[invite-redacted]/g;
          s/(denyut invite: ).*/\1[redacted]/;
          s/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]+/[addr]/g'
}

adb logcat -c
# The smoke phase leaves MainActivity running on top; a plain am start
# then only delivers the intent to the running instance ("Activity not
# started, intent has been delivered to currently running top-most
# instance", run 43685398773) and onCreate - which holds the DEBUG
# hooks - never re-runs. Force a cold start so the extras are honored.
adb shell am force-stop com.vanipy.denyut
adb shell am start -n com.vanipy.denyut/.MainActivity \
  --ez autostart_bot true --ez autosetup_bot true

echo "===== waiting for setup + invite ====="
i=0
while [ "$i" -lt 36 ]; do
  sleep 10
  adb logcat -d > setup.log 2>/dev/null
  if grep -q "denyut setup: failed" setup.log; then
    grep "denyut" setup.log | redact
    echo "SETUP FAIL: app reported setup failure"
    exit 1
  fi
  grep "denyut invite: " setup.log | tail -1 | sed 's/.*denyut invite: //' | tr -d '\r ' > "$INVITE_FILE"
  if [ -s "$INVITE_FILE" ]; then
    break
  fi
  i=$((i + 1))
done

echo "===== filtered setup logcat ====="
grep -i "denyut\|python" setup.log | redact | tail -30 || true

if [ ! -s "$INVITE_FILE" ]; then
  echo "SETUP FAIL: no invite printed within the wait window"
  exit 1
fi
echo "SETUP PASS: throwaway account configured, invite captured (redacted from logs)"

echo "===== host-side /echo round trip ====="
python3 tools/ci-chat-test.py "$RELAY_URL" "$INVITE_FILE" "$TOKEN"
result=$?

# Disposal: the invite credential is shredded here; the bot account's
# keys live only in the ephemeral emulator's app storage and the
# peer's in a mktemp dir on the runner - both are destroyed with the
# job. Relay-side the throwaway accounts are not deleted immediately:
# chatmail deletes messages after 20 days and sweeps accounts after
# 90 days without a successful login (chatmail relay chatmail.ini
# defaults, verified). The random addresses/credentials are retained
# by no one once the runner is gone.
rm -f "$INVITE_FILE"
exit $result

#!/bin/sh
# Restored-account chat round trip for the Denyut Android app.
#
# Runs AFTER ci-smoke.sh has passed, inside the same emulator step.
# Proves the app on the emulator RECEIVES and REPLIES to a real message:
# the reusable CI test account A is restored into the app's private
# storage, the app's bot code picks it up and starts IO, and the peer
# account B (restored on the runner) sends /echo over the pair's
# already-established chat and waits for the reply.
#
# Creates NO relay accounts. The pair comes from protected,
# environment-scoped Actions secrets (4 base64 chunks of a tar.xz plus
# the peer address), present only for this dispatch's job. The payload
# is assembled into a chmod-700 temp dir and shredded on exit; nothing
# derived from it is printed (the redact filter below also covers
# accidental surfacing in logcat).

set -u

# Optional first argument: "notes-reminders" also runs the notes and
# reminder scenario after the /echo check. No argument = echo only.
SCENARIO="${1:-}"
case "$SCENARIO" in
  ""|notes-reminders) ;;
  *) echo "CHAT FAIL: unknown scenario"; exit 1 ;;
esac

for v in DENYUT_BACKUP_B64_1 DENYUT_BACKUP_B64_2 DENYUT_BACKUP_B64_3 DENYUT_BACKUP_B64_4; do
  eval "val=\${$v:-}"
  if [ -z "$val" ]; then
    echo "CHAT FAIL: required secret $v is not set"
    exit 1
  fi
done
if [ -z "${DENYUT_PEER_ADDRESS:-}" ]; then
  echo "CHAT FAIL: required secret DENYUT_PEER_ADDRESS is not set"
  exit 1
fi

WORK=$(mktemp -d)
chmod 700 "$WORK"
cleanup() {
  rm -rf "$WORK"
  adb shell "run-as com.vanipy.denyut rm -rf /data/data/com.vanipy.denyut/files/accounts" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# chunk 5 is optional headroom; concatenation must match the encoder
printf '%s%s%s%s%s' \
  "$DENYUT_BACKUP_B64_1" "$DENYUT_BACKUP_B64_2" "$DENYUT_BACKUP_B64_3" \
  "$DENYUT_BACKUP_B64_4" "${DENYUT_BACKUP_B64_5:-}" \
  | base64 -d > "$WORK/pair.tar.xz"
tar xJf "$WORK/pair.tar.xz" -C "$WORK" || { echo "CHAT FAIL: backup payload did not decode"; exit 1; }
rm -f "$WORK/pair.tar.xz"
if [ ! -f "$WORK/A/accounts.toml" ] || [ ! -f "$WORK/B/accounts.toml" ]; then
  echo "CHAT FAIL: backup payload has unexpected layout"
  exit 1
fi

# Redaction for anything printed into the PUBLIC job log. Account
# addresses are identifiers; nothing derived from the payload prints.
redact() {
  sed -E 's/OPENPGP4FPR:[^ ]*/[invite-redacted]/g;
          s/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]+/[addr]/g'
}

echo "===== host-side preflight (no accounts created) ====="
python3 -m pip install --quiet deltachat2==2.58.0 deltachat-rpc-server==2.58.0
python3 - <<'PYEOF'
from deltachat2 import MessageData, Rpc
from deltachat2.transport import IOTransport
from deltachat2.types import EventTypeIncomingMsg
print("host preflight ok: deltachat2 API names verified")
PYEOF

echo "===== restoring bot account into the app ====="
adb logcat -c
adb shell am force-stop com.vanipy.denyut

# Push account A's dir contents into the app's private accounts dir.
# run-as works because this is a debuggable build. Each remote command
# is ONE adb-shell argument: adb joins its argv on the device, so a
# nested sh -c 'a && b' arrives misquoted (run 43693783820: mkdir got
# zero args, the account never landed, the bot stayed waiting_setup).
adb shell "run-as com.vanipy.denyut mkdir -p /data/data/com.vanipy.denyut/files/accounts"
tar cf - -C "$WORK/A" . | adb shell "run-as com.vanipy.denyut tar xf - -C /data/data/com.vanipy.denyut/files/accounts"
LISTING=$(adb shell "run-as com.vanipy.denyut ls /data/data/com.vanipy.denyut/files/accounts")
echo "$LISTING"
if ! echo "$LISTING" | grep -Eq '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'; then
  echo "SETUP FAIL: account dir did not reach the app's private storage"
  exit 1
fi

adb shell am start -n com.vanipy.denyut/.MainActivity --ez autostart_bot true

echo "===== waiting for the bot to come up on the restored account ====="
i=0
status=""
while [ "$i" -lt 24 ]; do
  sleep 10
  adb logcat -d > restore.log 2>/dev/null
  if grep -q "denyut status: error\|denyut status: failed" restore.log; then
    grep -i "denyut\|python" restore.log | redact | tail -30
    echo "SETUP FAIL: app reported an error on the restored account"
    exit 1
  fi
  if grep -q "denyut status: running" restore.log; then
    status="running"
    break
  fi
  i=$((i + 1))
done
grep -i "denyut\|python" restore.log | redact | tail -30 || true

if [ "$status" != "running" ]; then
  echo "SETUP FAIL: bot did not reach running state on the restored account"
  exit 1
fi
echo "SETUP PASS: bot running on the restored account"

echo "===== host-side /echo round trip (restored peer) ====="
TOKEN="denyut-ci-$(date +%s)"
if [ -n "$SCENARIO" ]; then
  python3 tools/ci-chat-test.py - - "$TOKEN" \
    --accounts-dir "$WORK/B" --peer-address "$DENYUT_PEER_ADDRESS" \
    --scenario "$SCENARIO"
else
  python3 tools/ci-chat-test.py - - "$TOKEN" \
    --accounts-dir "$WORK/B" --peer-address "$DENYUT_PEER_ADDRESS"
fi
result=$?

if [ "$result" -eq 0 ]; then
  echo "ANDROID CHAT PASS: the app on the emulator received the /echo and its reply came back through the real message path"
  [ -n "$SCENARIO" ] && echo "ANDROID SCENARIO PASS: $SCENARIO ran on the emulator app"
else
  echo "ANDROID CHAT FAIL: see witness output above"
fi
exit $result

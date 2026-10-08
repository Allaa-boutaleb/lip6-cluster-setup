#!/bin/bash
# The helper block both managers share: identical copies, free ports, tunnels that outlive a hangup.
. "$(dirname "$0")/lib.sh"

block() { sed -n '/^# ---- BEGIN shared helpers/,/^# ---- END shared helpers ----$/p' "$ROOT/$1"; }
CASE="identical"
block conv-manager > "$T/conv.sh"
block hpc-notebook > "$T/hpc.sh"
grep -q '^# ---- END shared helpers ----$' "$T/conv.sh" || fail "no shared block in conv-manager"
cmp -s "$T/conv.sh" "$T/hpc.sh" || fail "the shared blocks differ: $(diff "$T/conv.sh" "$T/hpc.sh" | head -5)"

CASE="old /tmp state adopted"
mkdir -p /tmp/jupyter_tunnels_fake-tester
echo "99999 1234" > /tmp/jupyter_tunnels_fake-tester/42
. "$T/conv.sh"
case $TUNNEL_DIR in "$HOME"/*) ;; *) fail "TUNNEL_DIR outside the sandbox: $TUNNEL_DIR" ;; esac
[ -f "$TUNNEL_DIR/42" ] && [ ! -e /tmp/jupyter_tunnels_fake-tester ] || fail "old tunnel state not moved"

CASE="dead entry forgotten"
[ -z "$(tunnel_list)" ] && [ ! -e "$TUNNEL_DIR/42" ] || fail "dead tunnel entry kept"

CASE="ssh sharing"
rssh hpc true
grep -q 'ControlMaster=auto' "$FAKE_LOG" || fail "rssh does not share connections"
: > "$FAKE_LOG"; LIP6_NO_MUX=1; . "$T/conv.sh"; unset LIP6_NO_MUX
rssh hpc true
! grep -q 'ControlMaster' "$FAKE_LOG" || fail "LIP6_NO_MUX=1 ignored"

CASE="free port skips a busy one"
RANDOM=7; first=$((20000 + RANDOM % 20000))
ssh -N -L "127.0.0.1:$first:x:1" busy & busy=$!
i=0; until port_in_use "$first"; do i=$((i + 1)); [ $i -lt 50 ] || fail "listener never came up"; /bin/sleep 0.1; done
RANDOM=7; find_free_port > "$T/port"
port=$(cat "$T/port")
[ "$port" != "$first" ] && ! port_in_use "$port" || fail "got busy port $port (first try $first)"
kill "$busy"

CASE="tunnel survives a hangup"
tunnel_start 7 node:8888 hpc > "$T/out" 2>&1 || fail "tunnel_start failed: $(cat "$T/out")"
read -r pid port target < "$TUNNEL_DIR/7"
kill -HUP "$pid"; /bin/sleep 0.3
[ "$(tunnel_list)" = "7 $pid $TUNNEL_PORT node:8888" ] || fail "tunnel gone after SIGHUP"
tunnel_start 7 node:8888 hpc > "$T/out" 2>&1 && [ "$(tunnel_list | wc -l | tr -d ' ')" = 1 ] || fail "reconnect started a second tunnel"
kill "$pid"

CASE="failed tunnel says why"
export FAKE_TUNNEL=fail
! tunnel_start 8 node:8888 hpc > "$T/out" 2>&1 || fail "tunnel_start succeeded"
grep -q "Address already in use" "$T/out" && [ ! -e "$TUNNEL_DIR/8" ] || fail "ssh error not shown: $(cat "$T/out")"
unset FAKE_TUNNEL

CASE="open_url"
PLATFORM=mac; open_url http://127.0.0.1:1/x
grep -qx 'open http://127.0.0.1:1/x' "$FAKE_LOG" || fail "mac open not called"
PLATFORM=linux; unset DISPLAY WAYLAND_DISPLAY
open_url http://127.0.0.1:1/x | grep -q 'copy the URL' || fail "no hint without a display"

echo "ok"

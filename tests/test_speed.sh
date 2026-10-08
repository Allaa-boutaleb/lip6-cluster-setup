#!/bin/bash
# Speed: the menu shows before the first status check ends, and a Jupyter launch costs at most two ssh round
# trips (submit, then one streamed wait for the URL) besides the tunnel.
. "$(dirname "$0")/lib.sh"

new_case "menu before the status check"
start=$SECONDS
FAKE_SSH_SLOW=5 run_tool conv-manager q
[ $((SECONDS - start)) -lt 4 ] || fail "the menu waited for the status check"
has 'front: checking...'
[ "$RC" = 0 ] || fail "exit status $RC"

# launch TOOL ERR_FILE ANSWER...: launch Jupyter on a job whose log already shows the URL
launch() {
    local tool=$1 err=$2 pid
    shift 2
    new_case "$tool launch"
    seed_jupyter
    echo "http://node01:8888/lab?token=t" > "$HOME/$err"
    run_tool "$tool" "$@"
    has 'Session ready!'
    has 'http://127.0.0.1:'
    [ "$(grep '^ssh ' "$FAKE_LOG" | grep -v -e ' -N ' -e 'reachable' | grep -c .)" -le 2 ] \
        || fail "more than 2 ssh calls: $(grep '^ssh ' "$FAKE_LOG")"
    read -r pid _ < "$HOME/.local/state/lip6-cluster/tunnels/4242" && kill "$pid"
}
launch conv-manager gpu-session-4242.err 1 1 '' '' '' '' '' '' 1 q
launch hpc-notebook OAR.4242.stderr 1 4 2h 1 q

echo "ok"

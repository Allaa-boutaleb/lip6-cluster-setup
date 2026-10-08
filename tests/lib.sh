#!/bin/bash
# Shared setup for the tests that run a manager. Source it. It sandboxes HOME, puts tests/fake-bin (fake ssh,
# schedulers, openers) first on PATH and aborts unless `ssh` resolves there: a real ssh would reach the real
# clusters with the user's keys.
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
FAKE_BIN="$ROOT/tests/fake-bin"

fail() { echo "FAIL: ${CASE:+$CASE: }$1" >&2; exit 1; }

T=$(mktemp -d "${TMPDIR:-/tmp}/lip6-test.XXXXXX")
trap 'rm -rf "$T" "/tmp/jupyter_tunnels_fake-tester"' EXIT
mkdir -p "$T/home" "$T/state"
export HOME="$T/home" TMPDIR="$T" FAKE_STATE="$T/state" FAKE_LOG="$T/calls.log"
export PATH="$FAKE_BIN:$PATH"
[ "$(command -v ssh)" = "$FAKE_BIN/ssh" ] || fail "ssh is not tests/fake-bin/ssh: refusing to run"

# new_case NAME: forget the previous case's jobs, call log and fake-tool knobs
new_case() {
    CASE=$1
    : > "$FAKE_STATE/jobs"; : > "$FAKE_LOG"
    unset FAKE_SSH FAKE_SESSION_RC FAKE_SBATCH FAKE_SQUEUE FAKE_SINFO FAKE_SCANCEL FAKE_SCANCEL_IDS FAKE_OARSUB \
        FAKE_OARSTAT FAKE_OARDEL FAKE_OARDEL_IDS FAKE_NEW_STATE FAKE_CLUSTER
    [ "$HOME" = "$T/home" ] || fail "HOME is not the sandbox: refusing to clean it"
    rm -rf "$HOME"; mkdir -p "$HOME"
}

# seed_job ID STATE [NAME]: a job the fake scheduler already knows, with its log files in $HOME
seed_job() {
    echo "$1 $2 ${3:-gpu-session}" >> "$FAKE_STATE/jobs"
    : > "$HOME/${3:-gpu-session}-$1.out"; : > "$HOME/${3:-gpu-session}-$1.err"
}

# seed_jupyter: the Jupyter env the conv launch looks for on the cluster
seed_jupyter() { mkdir -p "$HOME/.venvs/conv_jupyter/bin"; printf '#!/bin/sh\n' > "$HOME/.venvs/conv_jupyter/bin/jupyter"; chmod +x "$HOME/.venvs/conv_jupyter/bin/jupyter"; }

# run_tool MANAGER ANSWER...: each ANSWER is one stdin line; no answers = immediate Ctrl-D.
# Output lands in $OUT, the exit status in $RC. A hang or a spin (more than 15 s) fails the test.
run_tool() {
    local tool=$1 pid i=0
    shift
    case $tool in /*) ;; *) tool=$ROOT/$tool ;; esac
    if [ $# -gt 0 ]; then printf '%s\n' "$@" > "$T/in"; else : > "$T/in"; fi
    "${TEST_BASH:-/bin/bash}" "$tool" < "$T/in" > "$T/out" 2>&1 &
    pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        i=$((i + 1))
        [ "$i" -le 150 ] || { kill "$pid" 2>/dev/null; fail "$tool still running after 15 s (hang or spin)"; }
        /bin/sleep 0.1
    done
    wait "$pid"; RC=$?
    OUT=$(cat "$T/out")
}

has()   { printf '%s\n' "$OUT" | grep -qF -- "$1" || fail "missing '$1'"; }
lacks() { ! printf '%s\n' "$OUT" | grep -qF -- "$1" || fail "unexpected '$1'"; }
# survives: the tool printed its message, showed the menu again and ended only on 'q' (exit 0)
survives() {
    [ "$RC" = 0 ] || fail "exit status $RC, expected 0"
    [ "$(printf '%s\n' "$OUT" | grep -cF 'What do you want to do?')" -ge 2 ] || fail "the menu did not come back"
    has 'Bye!'
}

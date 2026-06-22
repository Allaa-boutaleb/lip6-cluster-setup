#!/bin/bash
set -e

cd "$(dirname "$0")/.."

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

remote_setup=$(awk '
    /^# ---- Remote bashrc setup ----/ { found=1 }
    found { print }
    found && /^# ---- Final instructions ----/ { exit }
' lip6-cluster-setup)

printf '%s\n' "$remote_setup" | grep -q 'install_remote_block' || fail "missing install_remote_block helper"
printf '%s\n' "$remote_setup" | grep -q 'remove_remote_block' || fail "missing remove_remote_block helper"
printf '%s\n' "$remote_setup" | grep -q 'verify_remote_login' || fail "missing verify_remote_login helper"
printf '%s\n' "$remote_setup" | grep -q 'BEGIN LIP6 Convergence Cluster Aliases' || fail "missing managed Convergence block marker"
printf '%s\n' "$remote_setup" | grep -q 'BEGIN LIP6 HPC Aliases' || fail "missing managed HPC block marker"

if printf '%s\n' "$remote_setup" | grep -Eq 'codex-node07|autojump|exec[[:space:]]+ssh'; then
    fail "remote setup contains a persistent auto-ssh login hook"
fi

grep -q '^doctor()' lip6-cluster-setup || fail "missing doctor command"
grep -q '^repair_login()' lip6-cluster-setup || fail "missing repair-login command"
grep -q '^uninstall_remote_blocks()' lip6-cluster-setup || fail "missing uninstall --remote-blocks command"

echo "ok"

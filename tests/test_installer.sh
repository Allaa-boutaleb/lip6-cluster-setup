#!/bin/bash
# The installer end to end, offline. The fake ssh runs the "cluster" side in the same sandbox HOME, so the
# remote ~/.bashrc blocks and authorized_keys land next to the local files.
. "$(dirname "$0")/lib.sh"

# Answers: Enter, username, email, team 1, storage 3 ("not sure"), CLUSTERS, Enter (confirm), Enter (step 4)
install() { run_tool lip6-cluster-setup "" jdupont j.d@lip6.fr 1 3 "${1:-3}" "" ""; }
# seed: an existing key (no ssh-keygen), an existing ssh config and a user line in ~/.bashrc
seed() {
    mkdir -p "$HOME/.ssh"
    echo fake-private > "$HOME/.ssh/id_ed25519"
    echo "ssh-ed25519 AAAAfake j.d@lip6.fr" > "$HOME/.ssh/id_ed25519.pub"
    echo "Host old" > "$HOME/.ssh/config"
    echo "my own line" > "$HOME/.bashrc"
}
count() { grep -cxF -- "$1" "$2"; }

new_case "zsh install"
export SHELL=/bin/zsh
seed
install
[ "$RC" = 0 ] || fail "exit $RC: $OUT"
has "Setup complete!"
grep -q "^ssh .*hpc bash -s 'jdupont' '~/  (check with your team)'" "$FAKE_LOG" || fail "storage text not sent intact"
[ "$(sed -n 2p "$HOME/.ssh/config")" = "Include config.d/*" ] || fail "Include not at the top of ~/.ssh/config"
grep -qxF "Host old" "$HOME/.ssh/config" && [ -f "$HOME/.ssh/config.pre-lip6" ] || fail "old ssh config lost"
grep -qxF "    IdentityFile \"$HOME/.ssh/id_ed25519\"" "$HOME/.ssh/config.d/lip6" || fail "IdentityFile not quoted"
grep -qxF "Host conv" "$HOME/.ssh/config.d/lip6" && grep -qxF "Host hpc" "$HOME/.ssh/config.d/lip6" || fail "Host blocks"
[ "$(count "ssh-ed25519 AAAAfake j.d@lip6.fr" "$HOME/.ssh/authorized_keys")" = 1 ] || fail "key not added exactly once"
[ -x "$HOME/conv-manager" ] && grep -qxF 'MAIL_TO="j.d@lip6.fr"' "$HOME/hpc-notebook" || fail "managers not installed"
grep -qxF 'alias conv="~/conv-manager"' "$HOME/.zshrc" || fail "conv alias missing from ~/.zshrc"
[ "$(count '    eval "$(conda shell.bash hook)"' "$HOME/.bashrc")" = 2 ] || fail "conda hook line not literal"
grep -qF '~/  (check with your team)   team storage' "$HOME/.bashrc" || fail "storage text mangled"

CASE="re-run"
install
[ "$RC" = 0 ] || fail "exit $RC"
[ "$(count "# BEGIN LIP6 HPC Aliases" "$HOME/.bashrc")" = 1 ] || fail "HPC block duplicated"
[ "$(count "Include config.d/*" "$HOME/.ssh/config")" = 1 ] || fail "Include duplicated"
[ "$(grep -c 'alias hpc=' "$HOME/.zshrc")" = 1 ] || fail "alias duplicated"
grep -qxF "my own line" "$HOME/.bashrc" || fail "user line lost"

CASE="remove blocks"
"${TEST_BASH:-/bin/bash}" "$ROOT/lip6-cluster-setup" uninstall --remote-blocks > "$T/out" 2>&1 || fail "uninstall failed"
! grep -q "LIP6 .* Aliases" "$HOME/.bashrc" && grep -qxF "my own line" "$HOME/.bashrc" || fail "blocks not removed cleanly"
[ -f "$HOME/.bashrc.lip6-bak" ] || fail "no ~/.bashrc.lip6-bak"

CASE="reset"
echo "Include more/*" >> "$HOME/.ssh/config"
printf '1\n' | "${TEST_BASH:-/bin/bash}" "$ROOT/lip6-cluster-setup" --reset > "$T/out" 2>&1 || fail "reset failed"
! grep -qF "config.d" "$HOME/.ssh/config" && grep -qxF "Include more/*" "$HOME/.ssh/config" || fail "reset removed the wrong Include"
[ ! -e "$HOME/conv-manager" ] && ! grep -q "alias" "$HOME/.zshrc" || fail "reset left managers or aliases"

new_case "broken block"
export SHELL=/bin/zsh
seed
printf '%s\n' "# BEGIN LIP6 HPC Aliases" "half a block" >> "$HOME/.bashrc"
cp "$HOME/.bashrc" "$T/before"
install 1
[ "$RC" = 1 ] || fail "exit $RC, expected 1"
has "HPC: the aliases block was not added"
cmp -s "$HOME/.bashrc" "$T/before" || fail "~/.bashrc changed despite a BEGIN without END"

new_case "hpc down, bash"
export SHELL=/bin/bash FAKE_SSH_DOWN=hpc
seed
install
[ "$RC" = 1 ] || fail "exit $RC, expected 1"
has "HPC: passwordless login failed"
lacks "Setup complete!"
grep -qxF "# BEGIN LIP6 Convergence Cluster Aliases" "$HOME/.bashrc" || fail "Convergence skipped too"
grep -qF ". ~/.bashrc" "$HOME/.bash_profile" || fail "~/.bash_profile does not load ~/.bashrc"

echo "ok"

#!/bin/bash
# The installer copies conv-manager / hpc-notebook from the repo and fills in
# exactly one line (MAIL_TO). These checks keep the repo files and that copy honest.
set -e

cd "$(dirname "$0")/.."

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

# ---- Menu labels (docs and README refer to these) ----

for label in \
    "Start smart GPU session" \
    "Reconnect to running session" \
    "Jobs and logs" \
    "Cluster status" \
    "Cleanup jobs or tunnels" \
    "Refresh cached status"; do
    grep -q "$label" conv-manager || fail "conv missing: $label"
done

for label in \
    "Start CPU session" \
    "Reconnect to running session" \
    "Jobs and logs" \
    "Cleanup jobs or tunnels" \
    "Refresh cached status"; do
    grep -q "$label" hpc-notebook || fail "hpc missing: $label"
done

# ---- No embedded managers, no personal identity ----

grep -Eq "<< '(HPC|CONV)_SCRIPT'" lip6-cluster-setup && fail "installer still embeds a manager"

# Author credit lines (comments, installer banner) may name the author; nothing else may.
for f in conv-manager hpc-notebook lip6-cluster-setup; do
    grep -n 'boutaleb' "$f" | grep -v '^[0-9]*:[[:space:]]*#' | grep -v 'By Allaa Boutaleb' \
        && fail "$f contains the author's account or address"
    grep -q 'CONV_USER\|__USERNAME__\|__EMAIL__' "$f" && fail "$f has a leftover placeholder"
done

for f in conv-manager hpc-notebook; do
    [ "$(grep -c '^MAIL_TO=""$' "$f")" = 1 ] || fail "$f needs exactly one MAIL_TO=\"\" line"
    [ "$(grep -c 'MAIL_TO=""' "$f")" = 1 ] || fail "$f mentions MAIL_TO=\"\" more than once"
    # the cluster resolves the account: every -u must be the remote \$USER, expanded remotely
    grep -E '(squeue|scancel|oarstat)[^|]* -u ' "$f" | grep -q . || fail "$f has no -u user filter to check"
    grep -E '(squeue|scancel|oarstat)[^|]* -u ' "$f" | grep -v '\\\$USER' \
        && fail "$f filters on a local value instead of the remote \$USER"
done

# ---- Simulate the installer's copy step ----

extract_function() {
    awk -v name="$1" '
        $0 ~ "^" name "\\(\\)[[:space:]]*\\{" { found=1 }
        found { print }
        found && /^}/ { exit }
    ' "$2"
}

tmp=$(mktemp -d "${TMPDIR:-/tmp}/lip6-sync.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

eval "$(extract_function install_manager lip6-cluster-setup)"
[ "$(type -t install_manager)" = function ] || fail "installer has no install_manager"

SCRIPT_DIR="$PWD"
RED=""
NC=""
# a path with spaces (Windows homes) and an address full of sed-special characters
INSTALL_DIR="$tmp/Home With Spaces"
mkdir -p "$INSTALL_DIR"

for email in 'first.last+tag%x@lip6.fr' 'a&b|c\d/e@x.fr'; do
    for name in conv-manager hpc-notebook; do
        rm -f "$INSTALL_DIR/$name"
        EMAIL="$email" install_manager "$name"
        dest="$INSTALL_DIR/$name"
        [ -x "$dest" ] || fail "$name not executable after install"
        [ ! -e "$dest.tmp" ] || fail "$name left a .tmp file behind"
        # exactly the MAIL_TO line differs
        changed=$(diff "$name" "$dest" | grep -c '^>' || true)
        [ "$changed" = 1 ] || fail "$name: installer changed $changed lines instead of 1"
        [ "$(grep -c '^MAIL_TO=""$' "$dest")" = 0 ] || fail "$name: MAIL_TO still empty"
        installed=$(grep '^MAIL_TO=' "$dest")
        [ "$installed" = "MAIL_TO=\"$email\"" ] || fail "$name: got $installed for $email"
    done
done

# ---- Installer refuses to run without the managers (before touching anything) ----

mkdir -p "$tmp/bin" "$tmp/lonely" "$tmp/home"
printf '#!/bin/sh\necho "$@" >> "%s/ssh.log"\nexit 99\n' "$tmp" > "$tmp/bin/ssh"
chmod +x "$tmp/bin/ssh"
[ "$(PATH="$tmp/bin:$PATH" command -v ssh)" = "$tmp/bin/ssh" ] || fail "ssh does not resolve to the stub"
cp lip6-cluster-setup "$tmp/lonely/"
out=$(HOME="$tmp/home" PATH="$tmp/bin:$PATH" "${TEST_BASH:-/bin/bash}" "$tmp/lonely/lip6-cluster-setup" </dev/null 2>&1) \
    && fail "installer ran without the managers next to it"
printf '%s\n' "$out" | grep -q 'Missing .*hpc-notebook' || fail "no clear message for missing managers: $out"
[ ! -e "$tmp/ssh.log" ] || fail "installer contacted a cluster before checking its files"
[ -z "$(ls -A "$tmp/home")" ] || fail "installer touched HOME before checking its files"

echo "ok"

#!/bin/bash
# Run the managers' real remote job-script code locally: mail directives appear only
# when MAIL_TO is set, and empty arguments must not shift the others.
set -e

cd "$(dirname "$0")/.."

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

tmp=$(mktemp -d "${TMPDIR:-/tmp}/lip6-mail.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/home"

# Fake cluster tools. ssh runs the command string the way a remote shell would:
# all argv joined with spaces, then re-split. It is a function, never a real ssh.
ssh() { shift; HOME="$tmp/home" PATH="$tmp/bin:$PATH" bash -c "$*"; }
SSH_ERR=/dev/null   # the real manager sets it; the line under test redirects ssh's stderr there
[ "$(type -t ssh)" = function ] || fail "ssh must be the local stub"

REAL_SED=$(command -v sed)
printf '#!/bin/sh\necho "Submitted batch job 4242"\necho 4242\n' > "$tmp/bin/sbatch"
printf '#!/bin/sh\necho "OAR_JOB_ID=4242"\n' > "$tmp/bin/oarsub"
# the cluster has GNU "sed -i EXPR FILE"; BSD sed on macOS does not
printf '#!/bin/sh\nif [ "$1" = -i ]; then shift; "%s" "$1" "$2" > "$2.t" && mv "$2.t" "$2"; else exec "%s" "$@"; fi\n' \
    "$REAL_SED" "$REAL_SED" > "$tmp/bin/sed"
chmod +x "$tmp/bin/sbatch" "$tmp/bin/oarsub" "$tmp/bin/sed"

# run_remote FILE HOST: feed FILE's remote heredoc to the exact `ssh HOST bash -s ...` line
run_remote() {
    local file="$1" host="$2" body line
    body=$(awk "/<< 'REMOTE'\$/ { f=1; next } /^REMOTE\$/ { exit } f" "$file")
    line=$(grep -m1 "ssh $host bash -s" "$file" | sed "s/^.*\\(ssh $host bash -s .*\\) << 'REMOTE'\$/\\1/")
    [ -n "$body" ] && [ -n "$line" ] || fail "cannot find the remote heredoc in $file"
    printf '%s\n' "$body" | eval "$line" >/dev/null 2>&1 || true
}

has() { grep -q -- "$1" "$2" || fail "$3: missing '$1'"; }
lacks() { ! grep -q -- "$1" "$2" || fail "$3: unexpected '$1'"; }

# ---- conv: job script ----

job="$tmp/home/._conv_jupyter.sh"
num_gpus=1 GPU_TYPE=a100_7g.80gb wall=08:00:00 job_name=gpu-session CPU_FEATURE="" MEMORY="" NODE_LIST=node03

MAIL_TO="me@lip6.fr"
run_remote conv-manager conv
has '^#SBATCH --mail-type=ALL$' "$job" "conv with mail"
has '^#SBATCH --mail-user=me@lip6.fr$' "$job" "conv with mail"
# empty CPU_FEATURE and MEMORY before NODE_LIST: the node must not land in --mem
has '^#SBATCH --nodelist=node03$' "$job" "conv node"
lacks '--mem=' "$job" "conv node"
lacks '--constraint=' "$job" "conv node"

# unpinned node + mail (the usual launch): the address must not land in the node slot
rm -f "$job"
NODE_LIST=""
run_remote conv-manager conv
[ -f "$job" ] || fail "conv unpinned: no job script written"
lacks '--nodelist=' "$job" "conv unpinned with mail"
has '^#SBATCH --mail-user=me@lip6.fr$' "$job" "conv unpinned with mail"

rm -f "$job"
MAIL_TO=""
run_remote conv-manager conv
[ -f "$job" ] || fail "conv without mail: no job script written"
lacks 'mail' "$job" "conv without mail"
has '^#SBATCH --time=08:00:00$' "$job" "conv without mail"

# ---- hpc: job script ----

job="$tmp/home/._jupyter_job.sh"
cores=4 wall=8:0:0

MAIL_TO="me@lip6.fr"
run_remote hpc-notebook hpc
has '^#OAR --notify mail:me@lip6.fr$' "$job" "hpc with mail"
has 'core=4,walltime=8:0:0' "$job" "hpc with mail"
lacks '__[A-Z]*__' "$job" "hpc with mail"

rm -f "$job"
MAIL_TO=""
run_remote hpc-notebook hpc
[ -f "$job" ] || fail "hpc without mail: no job script written"
lacks 'notify' "$job" "hpc without mail"
lacks '__[A-Z]*__' "$job" "hpc without mail"
has 'core=4,walltime=8:0:0' "$job" "hpc without mail"

echo "ok"

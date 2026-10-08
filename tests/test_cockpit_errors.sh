#!/bin/bash
# A failing ssh, scheduler rejection, bad input or Ctrl-D must print a message and leave the cockpit running
# until 'q' (never "set -e" silently ending it). Runs both managers against tests/fake-bin only.
cd "$(dirname "$0")/.." || exit 1
. tests/lib.sh

# ---- conv-manager: unreachable cluster ----
new_case "conv unreachable: jobs list"
FAKE_SSH=down run_tool conv-manager 3 q
has 'Could not list your jobs on Convergence.'
has 'Connection timed out'
survives

new_case "conv unreachable: launch"
FAKE_SSH=down run_tool conv-manager 1 1 '' '' '' '' '' '' 1 q
has 'Cannot reach the Convergence cluster.'
survives

new_case "conv unreachable: cancel, reconnect, status, login"
FAKE_SSH=down run_tool conv-manager 5 2 4 6 q
has 'Could not list your jobs on Convergence.'
has 'Could not read the cluster status.'
has 'Could not connect.'
survives

# ---- conv-manager: scheduler rejection ----
new_case "conv sbatch rejected (QoS / job limit)"
seed_jupyter
FAKE_SBATCH=fail run_tool conv-manager 1 1 '' '' '' '' '' '' 1 q
has 'Job was NOT submitted.'
has 'QOSMaxSubmitJobPerUserLimit'
has 'violates accounting/QOS policy'
lacks 'Waiting for it to start'
survives

new_case "conv custom script missing"
run_tool conv-manager 1 1 '' '' '' '' '' '' 4 '~/nope.sh' q
has 'Job was NOT submitted.'
has 'Unable to open file'
survives

new_case "conv custom script ok (~ expands on the cluster)"
: > "$HOME/train.sh"
run_tool conv-manager 1 1 '' '' '' '' '' '' 4 '~/train.sh' q
has 'Job 4242 submitted!'
lacks 'NOT submitted'
survives

new_case "conv launch: --parsable id with ;cluster suffix is read, job state is reported"
seed_jupyter
FAKE_CLUSTER=convergence FAKE_NEW_STATE=FAILED run_tool conv-manager 1 1 '' '' '' '' '' '' 1 q
has 'Job 4242 submitted.'
has 'Job ended (state: FAILED)'
survives

# ---- Ctrl-D (end of input) ----
new_case "conv Ctrl-D at the menu"
run_tool conv-manager
[ "$RC" = 0 ] || fail "exit status $RC, expected 0"
has 'Bye!'

new_case "conv Ctrl-D inside a question"
run_tool conv-manager 1
[ "$RC" = 0 ] || fail "exit status $RC, expected 0"
has 'Bye!'

# ---- bad job id ----
new_case "conv bad job ids"
seed_job 4242 RUNNING; seed_job 4243 PENDING
run_tool conv-manager 5 abc 2 9999 2 xyz q
has 'Invalid job ID'
has 'Job 9999 is not one of your jobs'
lacks 'cancelled'
survives
[ "$(grep -c . "$FAKE_STATE/jobs")" = 2 ] || fail "a bad id must not cancel anything"

# ---- cancel tells the truth ----
new_case "conv cancel one job"
seed_job 4242 RUNNING
run_tool conv-manager 5 4242 q
has 'Job 4242 cancelled and log files cleaned up.'
[ ! -e "$HOME/gpu-session-4242.out" ] || fail "log of a cancelled job should be gone"
[ ! -s "$FAKE_STATE/jobs" ] || fail "job should be gone"
survives

new_case "conv cancel refused: no success message, logs kept"
seed_job 4242 RUNNING
FAKE_SCANCEL_IDS=4242 run_tool conv-manager 5 4242 q
has 'Could not cancel job 4242'
has 'Access/permission denied'
lacks 'cancelled and log files cleaned up'
[ -e "$HOME/gpu-session-4242.out" ] && [ -e "$HOME/gpu-session-4242.err" ] || fail "logs of a job that is still alive must stay"
survives

new_case "conv cancel all: asks first, with the count"
seed_job 4242 RUNNING; seed_job 4243 RUNNING; seed_job 4244 PENDING
run_tool conv-manager 5 all no q
has 'This cancels ALL 3 of your jobs (2 running, 1 pending)'
has 'Nothing cancelled.'
[ "$(grep -c . "$FAKE_STATE/jobs")" = 3 ] || fail "answering no must cancel nothing"
survives

new_case "conv cancel all: Ctrl-D at the question cancels nothing"
seed_job 4242 RUNNING
run_tool conv-manager 5 all
[ "$RC" = 0 ] || fail "exit status $RC, expected 0"
[ "$(grep -c . "$FAKE_STATE/jobs")" = 1 ] || fail "Ctrl-D must cancel nothing"

new_case "conv cancel all: yes, one job refused"
seed_job 4242 RUNNING; seed_job 4243 RUNNING; seed_job 4244 PENDING
FAKE_SCANCEL_IDS=4243 run_tool conv-manager 5 all yes q
has 'Not every job was cancelled'
has 'job 4243'
lacks 'All 3 jobs cancelled'
[ ! -e "$HOME/gpu-session-4242.out" ] && [ ! -e "$HOME/gpu-session-4244.out" ] || fail "logs of cancelled jobs should be gone"
[ -e "$HOME/gpu-session-4243.out" ] || fail "log of the job that survived must stay"
survives

new_case "conv cancel all: yes"
seed_job 4242 RUNNING; seed_job 4243 PENDING
run_tool conv-manager 5 all yes q
has 'All 2 jobs cancelled and log files cleaned up.'
[ ! -s "$FAKE_STATE/jobs" ] || fail "all jobs should be gone"
survives

# ---- interactive ssh: only 255 means "could not connect" ----
new_case "conv login shell exits non-zero"
FAKE_SESSION_RC=1 run_tool conv-manager 6 q
lacks 'Could not connect'
survives

new_case "conv login ssh fails (255)"
FAKE_SESSION_RC=255 run_tool conv-manager 6 q
has 'Could not connect.'
survives

new_case "conv reconnect, terminal mode"
seed_job 4242 RUNNING; seed_job 4243 PENDING
run_tool conv-manager 2 4243 2 q
has 'Could not find the node for job 4243'
survives
FAKE_SESSION_RC=255 run_tool conv-manager 2 4242 2 q
has 'Connecting to node01'
has 'Could not connect.'
survives

# ---- argv quoting: a mail address with spaces and shell syntax stays one literal argument ----
new_case "conv quoting"
seed_jupyter
sed "s|^MAIL_TO=\"\"\$|MAIL_TO='a b;touch $T/pwned \$(touch $T/pwned2)'|" conv-manager > "$T/conv-mail"
chmod +x "$T/conv-mail"
grep -q 'pwned' "$T/conv-mail" || fail "could not set MAIL_TO in the test copy"
FAKE_NEW_STATE=FAILED run_tool "$T/conv-mail" 1 1 '' '' '' '' '' '' 1 q
has 'Job 4242 submitted.'
grep -qF -- 'mail-user=a b;touch' "$HOME/._conv_jupyter.sh" || fail "the address must reach the job script literally"
[ ! -e "$T/pwned" ] && [ ! -e "$T/pwned2" ] || fail "shell syntax in an argument was executed on the cluster"

# ---- hpc-notebook (menu: 1 launch, 2 reconnect, 3 jobs, 4 cleanup, 5 login) ----
new_case "hpc unreachable"
FAKE_SSH=down run_tool hpc-notebook 3 1 '' '' 1 4 2 5 q
has 'Could not list your jobs on HPC.'
has 'Job was NOT submitted.'
has 'Connection timed out'
has 'Could not connect.'
survives

new_case "hpc oarsub rejected"
FAKE_OARSUB=fail run_tool hpc-notebook 1 '' '' 1 q
has 'Job was NOT submitted.'
has 'ADMISSION RULE'
lacks 'Waiting for it to start'
survives

new_case "hpc launch: job id read, job state reported"
FAKE_NEW_STATE=Error run_tool hpc-notebook 1 4 2h 1 q
has 'Job 4242 submitted.'
has 'no longer waiting (state: Error)'
survives

new_case "limits are refused before anything is submitted"
run_tool conv-manager 1 1 '' 15d q
has 'at most 14 days'
run_tool conv-manager 1 1 '' '' '' 2 '' node03 q
has 'node03 does not have amd CPUs'
run_tool hpc-notebook 1 49 q
has 'from 1 to 48'
run_tool hpc-notebook 1 '' 25h 2 q
has 'at most 24 hours'
survives
! grep -Eq 'sbatch|salloc|oarsub' "$FAKE_LOG" || fail "a refused request reached the scheduler"

new_case "narrow terminal: one-line title instead of the logo"
COLUMNS=80 run_tool conv-manager q
lacks '▒████▒   ░████░'
has 'CONVERGENCE'
COLUMNS=120 run_tool conv-manager q
has '▒████▒   ░████░'

new_case "hpc Ctrl-D at the menu and inside a question"
run_tool hpc-notebook
[ "$RC" = 0 ] || fail "exit status $RC, expected 0"
has 'Bye!'
run_tool hpc-notebook 1
[ "$RC" = 0 ] || fail "exit status $RC, expected 0"
has 'Bye!'

new_case "hpc bad job ids"
seed_job 4242 Running; seed_job 4243 Waiting
run_tool hpc-notebook 4 abc 2 9999 2 xyz q
has 'Invalid job ID'
has 'Job 9999 is not one of your jobs'
lacks 'cancelled'
survives
[ "$(grep -c . "$FAKE_STATE/jobs")" = 2 ] || fail "a bad id must not cancel anything"

new_case "hpc cancel one job"
seed_job 4242 Running OAR
run_tool hpc-notebook 4 4242 q
has 'Job 4242 cancelled and log files cleaned up.'
[ ! -s "$FAKE_STATE/jobs" ] || fail "job should be gone"
survives

new_case "hpc cancel refused: no success message"
seed_job 4242 Running
FAKE_OARDEL_IDS=4242 run_tool hpc-notebook 4 4242 q
has 'Could not cancel job 4242'
has 'oardel: cannot delete job 4242'
lacks 'cancelled and log files cleaned up'
survives

new_case "hpc cancel all: asks first, then does it; one refusal is reported"
seed_job 4242 Running; seed_job 4243 Waiting
run_tool hpc-notebook 4 all no q
has 'This cancels ALL 2 of your jobs'
has 'Nothing cancelled.'
[ "$(grep -c . "$FAKE_STATE/jobs")" = 2 ] || fail "answering no must cancel nothing"
FAKE_OARDEL_IDS=4243 run_tool hpc-notebook 4 all yes q
has 'Not every job was cancelled'
lacks 'All 2 jobs cancelled'
[ "$(cat "$FAKE_STATE/jobs")" = "4243 Waiting gpu-session" ] || fail "only the refused job should be left"
run_tool hpc-notebook 4 all
[ "$RC" = 0 ] || fail "Ctrl-D at the question: exit status $RC"
[ "$(grep -c . "$FAKE_STATE/jobs")" = 1 ] || fail "Ctrl-D must cancel nothing"

new_case "hpc reconnect, terminal mode"
seed_job 4242 Running; seed_job 4243 Waiting
run_tool hpc-notebook 2 4243 2 q
has 'Could not find the node for job 4243'
survives
run_tool hpc-notebook 2 4242 2 q
has 'Connecting to bignode1'
lacks 'Could not connect'
survives

new_case "hpc login shell exits non-zero"
FAKE_SESSION_RC=1 run_tool hpc-notebook 5 q
lacks 'Could not connect'
survives

echo "ok"

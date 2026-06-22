#!/bin/bash
set -e

cd "$(dirname "$0")/.."

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

for file in conv-manager hpc-notebook; do
    grep -q '^render_header()' "$file" || fail "$file missing render_header"
    grep -q '^render_status()' "$file" || fail "$file missing render_status"
    grep -q '^refresh_status()' "$file" || fail "$file missing refresh_status"
    grep -q '^run_spinner()' "$file" || fail "$file missing run_spinner"
    grep -q '^spinner_step()' "$file" || fail "$file missing spinner_step"
    grep -q '^print_action_menu()' "$file" || fail "$file missing print_action_menu"
    grep -q 'Refresh cached status' "$file" || fail "$file missing explicit refresh menu action"

    awk -v file="$file" '
        /^render_status\(\)/ { in_status=1 }
        in_status && /ssh[[:space:]]/ {
            printf("FAIL: %s render_status must not run ssh; use refresh_status cache\n", file) > "/dev/stderr"
            exit 1
        }
        in_status && /squeue|sinfo|oarstat/ {
            printf("FAIL: %s render_status must not query scheduler; use refresh_status cache\n", file) > "/dev/stderr"
            exit 1
        }
        in_status && /^}/ { in_status=0 }
    ' "$file"

    awk -v file="$file" '
        /^collect_status\(\)/ { in_collect=1 }
        in_collect && /sinfo/ {
            printf("FAIL: %s collect_status must not scan GPU inventory; leave that to the cluster status action\n", file) > "/dev/stderr"
            exit 1
        }
        in_collect && /^}/ { in_collect=0 }
    ' "$file"

    awk -v file="$file" '
        /^render_header\(\)/ { in_header=1 }
        in_header && /^EOF$/ { in_art=0 }
        in_header && in_art && length($0) > 280 {
            printf("FAIL: %s header line too wide (%d): %s\n", file, length($0), $0) > "/dev/stderr"
            exit 1
        }
        in_header && /cat << '\''EOF'\''/ { in_art=1 }
        in_header && /^}/ { in_header=0 }
    ' "$file"
done

grep -q '▒████▒   ░████░' conv-manager || fail "conv header does not use convergence.md logo art"
grep -q '██    ██  ██████▒' hpc-notebook || fail "hpc header does not use HPC.md logo art"

echo "ok"

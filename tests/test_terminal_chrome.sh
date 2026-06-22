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
    grep -q '^spinner_step()' "$file" || fail "$file missing spinner_step"
    grep -q '^print_action_menu()' "$file" || fail "$file missing print_action_menu"

    awk -v file="$file" '
        /^render_header\(\)/ { in_header=1 }
        in_header && /^EOF$/ { in_art=0 }
        in_header && in_art && length($0) > 64 {
            printf("FAIL: %s header line too wide (%d): %s\n", file, length($0), $0) > "/dev/stderr"
            exit 1
        }
        in_header && /cat << '\''EOF'\''/ { in_art=1 }
        in_header && /^}/ { in_header=0 }
    ' "$file"
done

echo "ok"

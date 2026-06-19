#!/bin/bash
set -e

cd "$(dirname "$0")/.."

extract_function() {
    awk "
        /^$1\\(\\)[[:space:]]*\\{/ { found=1 }
        found { print }
        found && /^}/ { exit }
    " conv-manager
}

eval "$(extract_function is_mem)"
eval "$(extract_function slurm_options)"

assert_eq() {
    local expected="$1"
    local actual="$2"
    local label="$3"
    if [ "$expected" != "$actual" ]; then
        echo "FAIL: $label" >&2
        echo "expected: $expected" >&2
        echo "actual:   $actual" >&2
        exit 1
    fi
}

assert_not_contains() {
    local pattern="$1"
    local file="$2"
    if grep -q "$pattern" "$file"; then
        echo "FAIL: $file contains $pattern" >&2
        exit 1
    fi
}

is_mem 512G
is_mem 512g
is_mem 2048000M
is_mem 0
! is_mem 512GB
! is_mem abc

assert_eq "" "$(slurm_options "" "")" "empty options"
assert_eq " --constraint=amd" "$(slurm_options amd "")" "cpu constraint"
assert_eq " --mem=512G" "$(slurm_options "" 512G)" "memory"
assert_eq " --mem=512G" "$(slurm_options "" 512g)" "lowercase memory"
assert_eq " --constraint=intel --mem=128G" "$(slurm_options intel 128G)" "cpu and memory"

conv_template_header=$(awk '
    /^CONV_USER=/ { found=1 }
    found { print }
    found && /^# parse_duration INPUT/ { exit }
' lip6-cluster-setup)
printf '%s\n' "$conv_template_header" | grep -q '^is_mem()'
printf '%s\n' "$conv_template_header" | grep -q '^slurm_options()'

assert_not_contains 'CPU_FEATURE=""' conv-manager
assert_not_contains 'CPU vendor.*Auto\|)  Auto' conv-manager
assert_not_contains 'CPU_FEATURE=""' lip6-cluster-setup
assert_not_contains 'CPU vendor.*Auto\|)  Auto' lip6-cluster-setup

echo "ok"

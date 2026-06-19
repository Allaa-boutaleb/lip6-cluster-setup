#!/bin/bash
set -e

cd "$(dirname "$0")/.."

extract_nth_function() {
    local name="$1"
    local wanted="$2"
    awk -v name="$name" -v wanted="$wanted" '
        $0 ~ "^" name "\\(\\)[[:space:]]*\\{" { count++; if (count == wanted) found=1 }
        found { print }
        found && /^}/ { exit }
    ' lip6-cluster-setup
}

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

assert_fails() {
    local label="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "FAIL: $label" >&2
        exit 1
    fi
}

eval "$(extract_nth_function parse_duration 1)"
assert_eq "8:0:0" "$(parse_duration 8h)" "hpc 8h"
assert_eq "30:30:0" "$(parse_duration 1d 6h 30m)" "hpc compound duration"
assert_eq "8:0:0" "$(parse_duration 08:00:00)" "hpc leading zero H:M:S"
assert_fails "hpc invalid duration" parse_duration soon
unset -f parse_duration

eval "$(extract_nth_function parse_duration 2)"
eval "$(extract_nth_function duration_to_minutes 1)"
assert_eq "08:00:00" "$(parse_duration 8h)" "conv 8h"
assert_eq "1-06:30:00" "$(parse_duration 1d 6h 30m)" "conv compound duration"
assert_eq "08:00:00" "$(parse_duration 08:00:00)" "conv leading zero HH:MM:SS"
assert_eq "1-06:00:00" "$(parse_duration 30:00:00)" "conv long HH:MM:SS"
assert_eq "480" "$(duration_to_minutes 08:00:00)" "conv minutes leading zero"
assert_eq "1800" "$(duration_to_minutes 30:00:00)" "conv minutes long HH:MM:SS"
assert_fails "conv invalid duration" parse_duration soon

if grep -q '\${\*,,}' lip6-cluster-setup /Users/sp00ky/conv-manager /Users/sp00ky/hpc-notebook; then
    echo "FAIL: found Bash 4 lowercase expansion" >&2
    exit 1
fi

echo "ok"

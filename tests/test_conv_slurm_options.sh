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
eval "$(extract_function is_conv_node)"
eval "$(extract_function node_matches_gpu)"
eval "$(extract_function node_matches_cpu)"
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

assert_eq "" "$(slurm_options "" "" "")" "empty options"
assert_eq " --constraint=amd" "$(slurm_options amd "" "")" "cpu constraint"
assert_eq " --mem=512G" "$(slurm_options "" 512G "")" "memory"
assert_eq " --mem=512G" "$(slurm_options "" 512g "")" "lowercase memory"
assert_eq " --constraint=intel --mem=128G" "$(slurm_options intel 128G "")" "cpu and memory"
assert_eq " --nodelist=node03" "$(slurm_options "" "" node03)" "node list"
assert_eq " --constraint=intel --mem=128G --nodelist=node03" "$(slurm_options intel 128G node03)" "cpu memory and node"
assert_eq " --nodelist=node03 --qos=long" "$(slurm_options "" "" node03 long)" "qos"

is_conv_node node01
is_conv_node node10
! is_conv_node node00
! is_conv_node node11
! is_conv_node node7
! is_conv_node front

node_matches_gpu node03 a100_7g.80gb
node_matches_gpu node07 a100_3g.40gb
! node_matches_gpu node07 a100_7g.80gb
! node_matches_gpu node03 a100_3g.40gb
node_matches_cpu node01 amd
node_matches_cpu node03 intel
! node_matches_cpu node01 intel
! node_matches_cpu node08 amd

grep -q '~/.venvs/conv_jupyter/bin/jupyter' conv-manager
grep -q 'source ~/.venvs/conv_jupyter/bin/activate' conv-manager

assert_not_contains 'CPU_FEATURE=""' conv-manager
assert_not_contains 'CPU vendor.*Auto\|)  Auto' conv-manager
assert_not_contains 'pip install --quiet jupyterlab' conv-manager

echo "ok"

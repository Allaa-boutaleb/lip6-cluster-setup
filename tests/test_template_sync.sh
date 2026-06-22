#!/bin/bash
set -e

cd "$(dirname "$0")/.."

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

for label in \
    "Start smart GPU session" \
    "Reconnect to running session" \
    "Jobs and logs" \
    "Cluster status" \
    "Cleanup jobs or tunnels"; do
    grep -q "$label" conv-manager || fail "standalone conv missing: $label"
    grep -q "$label" lip6-cluster-setup || fail "installer conv template missing: $label"
done

for label in \
    "Start CPU session" \
    "Reconnect to running session" \
    "Jobs and logs" \
    "Cleanup jobs or tunnels"; do
    grep -q "$label" hpc-notebook || fail "standalone hpc missing: $label"
    grep -q "$label" lip6-cluster-setup || fail "installer hpc template missing: $label"
done

grep -q '^render_header()' conv-manager || fail "standalone conv missing render_header"
grep -q '^render_header()' hpc-notebook || fail "standalone hpc missing render_header"
grep -q '^render_header()' lip6-cluster-setup || fail "installer templates missing render_header"

echo "ok"

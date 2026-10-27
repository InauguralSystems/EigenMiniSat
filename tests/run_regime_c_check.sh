#!/usr/bin/env bash
# The CLI's CDCL path on a conflict-heavy checked-in fixture, byte for byte
# against the banked regime-C output (benchmarks/oracle/). EigenScript#1995:
# a compiler regression crashed this path ("cannot index num") while the
# in-process --proof-bench solve and both suites stayed green.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
out=$(mktemp) norm=$(mktemp)
trap 'rm -f "$out" "$norm"' EXIT
if ! eigenscript minisat.eigs --cdcl tests/fixtures/tseitin_torus_3x3_odd.cnf > "$out" 2>&1; then
    echo "FAIL: regime C 3x3: the CLI exited non-zero:"
    tail -20 "$out"
    exit 1
fi
sed -E -f benchmarks/normalize_regime_c.sed "$out" > "$norm"
if cmp -s "$norm" benchmarks/oracle/regime-c-3x3.stdout; then
    echo "PASS: regime C 3x3 (CLI --cdcl, byte-exact excluding ms)"
else
    echo "FAIL: regime C 3x3 differs from benchmarks/oracle/regime-c-3x3.stdout:"
    diff -u benchmarks/oracle/regime-c-3x3.stdout "$norm" | head -40
    exit 1
fi

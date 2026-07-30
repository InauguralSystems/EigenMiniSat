#!/usr/bin/env bash
# ============================================================
# DRAT proof verification -- the external oracle for UNSAT
# ============================================================
# A SAT answer self-verifies: check the model against the clauses. An UNSAT
# answer has nothing to check it, so a bug that over-prunes the search reports
# UNSAT and every assertion in the suite still passes. This script closes that
# hole: --cdcl --proof emits a DRAT refutation and drat-trim, which shares no
# code with this solver, verifies it independently.
#
# drat-trim signals its verdict in the exit code (0 verified, 1 not verified).
# Do NOT grep for "s VERIFIED" -- drat-trim prefixes that line with a carriage
# return, so line-anchored patterns silently never match and the check passes
# no matter what the solver emitted.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EIGS="${EIGENSCRIPT_BIN:-$(command -v eigenscript || echo ../EigenScript/src/eigenscript)}"
DRAT_TRIM="${DRAT_TRIM:-$(command -v drat-trim || true)}"

cd "$ROOT"

if [ -z "$DRAT_TRIM" ]; then
    echo "proof-check: drat-trim not found."
    echo "  Set DRAT_TRIM=/path/to/drat-trim, or build it:"
    echo "    git clone --depth 1 https://github.com/marijnheule/drat-trim /tmp/drat-trim"
    echo "    cc -O2 -o /tmp/drat-trim/drat-trim /tmp/drat-trim/drat-trim.c"
    exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# UNSAT instances whose refutations we verify. Kept to the cheap end of each
# family plus one genuinely hard case (Tseitin) so the proof machinery is
# exercised on a refutation that is not trivially short.
CASES="
tests/fixtures/unit_unsat.cnf
tests/corpus/multi_clause_line_unsat.cnf
tests/corpus/xor_contradiction_unsat.cnf
tests/corpus/pigeonhole_4_3.cnf
tests/corpus/k4_3color_unsat.cnf
tests/corpus/vendor/satlib_style_pigeonhole_5_4.cnf
tests/corpus/vendor/satlib_style_k5_4color.cnf
tests/fixtures/tseitin_torus_3x3_odd.cnf
"

fail=0
for cnf in $CASES; do
    name="$(basename "$cnf" .cnf)"
    proof="$WORK/$name.drat"

    out="$("$EIGS" minisat.eigs --cdcl --proof "$proof" "$cnf")"
    if ! grep -q "^s UNSATISFIABLE" <<<"$out"; then
        echo "FAIL $name: solver did not report UNSATISFIABLE"
        fail=1
        continue
    fi

    if "$DRAT_TRIM" "$cnf" "$proof" >"$WORK/$name.log" 2>&1; then
        lemmas="$(wc -l <"$proof" | tr -d ' ')"
        echo "ok   $name: refutation verified ($lemmas proof lines)"
    else
        echo "FAIL $name: drat-trim rejected the refutation"
        sed -n '1,20p' "$WORK/$name.log"
        fail=1
    fi
done

# Compaction-path regression (clause_locked position-0 bug, fixed 2026-07-30).
# The cases above are all too small to trigger physical compaction, so they
# cannot catch a dangling-reason bug. This one forces ~25 compactions and was
# REJECTED by drat-trim before the fix.
reg_cnf="tests/fixtures/pigeonhole_6_5.cnf"
reg_proof="$WORK/pigeonhole_6_5_eager.drat"
"$EIGS" minisat.eigs --cdcl --compact-policy eager --restart-policy luby \
    --proof "$reg_proof" "$reg_cnf" >/dev/null
if "$DRAT_TRIM" "$reg_cnf" "$reg_proof" >/dev/null 2>&1; then
    echo "ok   pigeonhole_6_5 under eager compaction: refutation verified"
else
    echo "FAIL pigeonhole_6_5 under eager compaction: drat-trim rejected"
    echo "     a learnt clause still in use as a reason was deleted (see clause_locked)"
    fail=1
fi

# Planted fault: the checker must REJECT a proof with a needed lemma removed.
# Without this, a checker that silently verifies everything (wrong path, bad
# build, misread exit code) would let every case above pass.
planted="$WORK/planted.drat"
src="$WORK/pigeonhole_5_4.drat"
"$EIGS" minisat.eigs --cdcl --proof "$src" tests/corpus/vendor/satlib_style_pigeonhole_5_4.cnf >/dev/null
head -1 "$src" >"$planted"
tail -1 "$src" >>"$planted"
if "$DRAT_TRIM" tests/corpus/vendor/satlib_style_pigeonhole_5_4.cnf "$planted" >/dev/null 2>&1; then
    echo "FAIL planted-fault: drat-trim accepted a proof with lemmas removed"
    echo "     the checker is not actually gating anything -- every ok above is meaningless"
    fail=1
else
    echo "ok   planted-fault: drat-trim rejected the truncated proof"
fi

# A SAT instance must not produce a refutation.
sat_out="$("$EIGS" minisat.eigs --cdcl --proof "$WORK/should_not_exist.drat" tests/fixtures/simple_sat.cnf)"
if grep -q "^s SATISFIABLE" <<<"$sat_out" && [ ! -f "$WORK/should_not_exist.drat" ]; then
    echo "ok   simple_sat: SAT answer wrote no proof file"
else
    echo "FAIL simple_sat: SAT run should report SATISFIABLE and write no proof"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "proof-check: FAILED"
    exit 1
fi
echo "proof-check: all refutations verified"

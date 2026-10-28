#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Prefer an explicit EIGENSCRIPT_BIN, then an `eigenscript` on PATH (how CI
# exposes its freshly built binary), then the maintainer's local dev path.
EIGS="${EIGENSCRIPT_BIN:-$(command -v eigenscript || echo ../EigenScript/src/eigenscript)}"

cd "$ROOT"
python3 tests/check_corpus_diversity.py --selftest
"$EIGS" tests/test_solver.eigs
"$EIGS" tests/test_active_learnts.eigs
"$EIGS" tests/test_tseitin_invariant.eigs
"$EIGS" tests/test_xor_detection.eigs
"$EIGS" tests/test_gf2_elimination.eigs
bash tests/run_gf2_corpus.sh
gf2_off_out="$("$EIGS" minisat.eigs tests/corpus/xor_ladder_sat.cnf)"
case "$gf2_off_out" in
    *"gf2=on"*) echo "FAIL: GF(2) arm is not off by default" >&2; exit 1 ;;
    *) echo "GF(2) arm: off by default" ;;
esac
gf2_on_out="$("$EIGS" minisat.eigs --gf2 tests/corpus/xor_ladder_sat.cnf)"
case "$gf2_on_out" in
    *"c gf2=on "*" xors="*) echo "GF(2) arm: opt-in switch reports census" ;;
    *) echo "FAIL: --gf2 did not report its census" >&2; exit 1 ;;
esac
gf2_proof="${TMPDIR:-/tmp}/eigenminisat-gf2-proof.$$"
rm -f "$gf2_proof"
gf2_unsat_out="$("$EIGS" minisat.eigs --gf2 --cdcl --proof "$gf2_proof" tests/corpus/xor_contradiction_unsat.cnf)"
case "$gf2_unsat_out" in
    *"certificate=uncertified"*"UNCERTIFIED:"*) ;;
    *) echo "FAIL: elimination UNSAT was not explicitly uncertified" >&2; exit 1 ;;
esac
if [ -e "$gf2_proof" ]; then
    echo "FAIL: elimination UNSAT emitted a fake DRAT file" >&2
    exit 1
fi
echo "GF(2) elimination UNSAT: uncertified and no fake DRAT"
"$EIGS" minisat.eigs tests/fixtures/simple_sat.cnf
"$EIGS" minisat.eigs --watched tests/fixtures/simple_sat.cnf
"$EIGS" minisat.eigs --persistent tests/fixtures/simple_sat.cnf
cdcl_out="$("$EIGS" minisat.eigs --cdcl tests/fixtures/simple_sat.cnf)"
printf '%s\n' "$cdcl_out"
for telemetry_field in minimize_checks minimize_removed minimize_steps lbd_improved peak_learnts max_level; do
    case "$cdcl_out" in
        *" $telemetry_field="*) ;;
        *)
            echo "FAIL: --cdcl counters line omitted $telemetry_field" >&2
            exit 1
            ;;
    esac
done
echo "cdcl counters: all computed telemetry is visible"
"$EIGS" minisat.eigs tests/fixtures/unit_unsat.cnf
"$EIGS" minisat.eigs --watched tests/fixtures/unit_unsat.cnf
"$EIGS" minisat.eigs --persistent tests/fixtures/unit_unsat.cnf
"$EIGS" minisat.eigs --cdcl tests/fixtures/unit_unsat.cnf
# #83: a genuine SATLIB uf/uuf instance ends with a `%` line and a trailing
# `0`, neither of which belongs to the formula. Gate on the VERDICT and not on
# the parse succeeding: reading that `0` as a clause terminator closes an empty
# clause, so a "fix" that skips `%` but keeps the `0` parses cleanly and
# answers UNSATISFIABLE for every SATLIB instance — with a one-line DRAT
# refutation drat-trim will correctly verify, because the empty clause really
# is RUP against the clause list the checker was handed.
for satlib_case in satlib_trailer_sat:SATISFIABLE satlib_trailer_unsat:UNSATISFIABLE; do
    satlib_file="tests/fixtures/${satlib_case%%:*}.cnf"
    satlib_want="s ${satlib_case##*:}"
    for satlib_mode in dpll --watched --persistent --cdcl; do
        [ "$satlib_mode" = dpll ] && satlib_mode=""
        satlib_out="$("$EIGS" minisat.eigs ${satlib_mode:+$satlib_mode} "$satlib_file")"
        case "$satlib_out" in
            *"$satlib_want"*) ;;
            *)
                echo "FAIL: $satlib_file under '${satlib_mode:-dpll}' did not answer '$satlib_want'" >&2
                echo "$satlib_out" >&2
                exit 1
                ;;
        esac
    done
done
echo "satlib trailer fixtures: verdicts hold on every propagation path"

"$EIGS" minisat.eigs --bench --size "${1:-1}"
"$EIGS" minisat.eigs --restart-bench --size "${1:-1}"
"$EIGS" minisat.eigs --phase-bench --size "${1:-1}"
"$EIGS" minisat.eigs --copy-bench --size "${1:-1}"
"$EIGS" minisat.eigs --storage-bench --size "${1:-1}"
"$EIGS" minisat.eigs --metadata-bench --size "${1:-1}"
"$EIGS" minisat.eigs --parse-bench --size "${1:-1}"
"$EIGS" minisat.eigs --scan-parse-bench --size "${1:-1}"
"$EIGS" minisat.eigs --diagnostic-bench --size "${1:-1}"
"$EIGS" minisat.eigs --file-bench --size "${1:-1}"
"$EIGS" minisat.eigs --corpus-bench

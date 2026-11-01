#!/usr/bin/env bash
# ============================================================
# --gf2 --cdcl answers checked by an oracle that shares no code with GF(2)
# elimination (hq#58 EMS-GF2-1)
# ============================================================
# Every tracked manifest row is solved with `--gf2 --cdcl --model --proof`.
# The verdict is never trusted on its own:
#   * SAT                   -> the model must satisfy the ORIGINAL CNF;
#   * UNSAT, certified      -> the DRAT refutation must verify with drat-trim
#                              against the ORIGINAL CNF;
#   * UNSAT, uncertified    -> elimination found 0 = 1: the run must say so
#                              and must not write a proof file.
# Rows are not filtered by their expected verdict: a SAT instance that --gf2
# wrongly refutes is exactly the case this exists for, and the DRAT check
# catches it without consulting the manifest. The verdict must also equal the
# manifest's expected column.
#
# drat-trim is required. Without it this exits nonzero (CI builds it first),
# so a missing oracle can never read as a pass.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EIGS="${EIGENSCRIPT_BIN:-$(command -v eigenscript || echo ../EigenScript/src/eigenscript)}"
DRAT_TRIM="${DRAT_TRIM:-$(command -v drat-trim || true)}"
cd "$ROOT"

if [ -z "$DRAT_TRIM" ]; then
    echo "FAIL: drat-trim not found (set DRAT_TRIM or put it on PATH); refusing to pass without the oracle"
    exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

manifest=tests/corpus/manifest.txt
awk -F '|' '!/^#/ && NF { print $1 "|" $2 "|" $3 }' "$manifest" > "$WORK/rows"
want_rows="$(wc -l < "$WORK/rows" | tr -d ' ')"
if [ "$want_rows" -eq 0 ]; then
    echo "FAIL: $manifest yielded 0 rows"
    exit 1
fi

fail=0
examined=0
sat_models=0
drat_verified=0
drat_verified_xors=0
uncertified=0
while IFS='|' read -r name path expected; do
    examined=$((examined + 1))
    proof="$WORK/$name.drat"
    out="$WORK/$name.out"
    "$EIGS" minisat.eigs --gf2 --cdcl --model --proof "$proof" "$path" > "$out"
    if [ "$(grep -c '^s ' "$out" || true)" != 1 ]; then
        echo "FAIL $name: expected exactly one status line"
        sed -n '1,20p' "$out"
        fail=1
        continue
    fi
    verdict="$(awk '/^s / { print $2 }' "$out")"
    result_line="$(grep '^c gf2_result ' "$out" || true)"
    xors="$(printf '%s\n' "$result_line" | sed -n 's/.* xors=\([0-9][0-9]*\) .*/\1/p')"
    if [ -z "$xors" ]; then
        echo "FAIL $name: no 'c gf2_result ... xors=N' line"
        fail=1
        continue
    fi
    case "$verdict:$expected" in
        SATISFIABLE:SAT | UNSATISFIABLE:UNSAT) ;;
        *)
            echo "FAIL $name: --gf2 --cdcl answered $verdict, manifest says $expected ($result_line)"
            fail=1
            ;;
    esac
    if [ "$verdict" = SATISFIABLE ]; then
        awk -f benchmarks/normalize_cnf.awk "$path" > "$WORK/normalized.cnf"
        if PYTHONDONTWRITEBYTECODE=1 python3 - "$WORK/normalized.cnf" "$out" <<'PY'
import sys
sys.path.insert(0, "benchmarks")
import certificate_validation
certificate_validation.check_model(sys.argv[1], open(sys.argv[2], "rb").read())
PY
        then
            sat_models=$((sat_models + 1))
            echo "ok   $name: SAT model verifies against the original CNF (xors=$xors)"
        else
            echo "FAIL $name: SAT model does not verify against the original CNF"
            fail=1
        fi
        continue
    fi
    case "$result_line" in
        *"certificate=uncertified"*)
            if ! grep -q '^c UNCERTIFIED: ' "$out"; then
                echo "FAIL $name: uncertified UNSAT did not say so"
                fail=1
            elif [ -e "$proof" ]; then
                echo "FAIL $name: uncertified UNSAT wrote a proof file"
                fail=1
            else
                uncertified=$((uncertified + 1))
                echo "ok   $name: elimination UNSAT reported uncertified, no proof file (xors=$xors)"
            fi
            continue
            ;;
        *"certificate=certified"*) ;;
        *)
            echo "FAIL $name: no certificate field ($result_line)"
            fail=1
            continue
            ;;
    esac
    if [ ! -s "$proof" ]; then
        echo "FAIL $name: certified UNSAT wrote no proof"
        fail=1
        continue
    fi
    set +e
    "$DRAT_TRIM" "$path" "$proof" > "$WORK/$name.log" 2>&1
    checker_rc=$?
    set -e
    if reason="$(python3 benchmarks/drat_verdict.py "$checker_rc" "$WORK/$name.log")"; then
        drat_verified=$((drat_verified + 1))
        if [ "$xors" -gt 0 ]; then
            drat_verified_xors=$((drat_verified_xors + 1))
        fi
        echo "ok   $name: certified --gf2 refutation verified by drat-trim (xors=$xors)"
    else
        echo "FAIL $name: certified --gf2 UNSAT, drat-trim did not verify ($reason, rc $checker_rc; $result_line)"
        sed -n '1,20p' "$WORK/$name.log"
        fail=1
    fi
done < "$WORK/rows"

if [ "$examined" -ne "$want_rows" ]; then
    echo "FAIL: examined $examined of $want_rows manifest rows"
    fail=1
fi
# The run must reach every outcome class, or a class can rot unexamined.
if [ "$drat_verified_xors" -lt 1 ]; then
    echo "FAIL: no certified refutation with xors>0 was DRAT-checked"
    fail=1
fi
if [ "$uncertified" -lt 1 ]; then
    echo "FAIL: no elimination-UNSAT (uncertified) row was examined"
    fail=1
fi
if [ "$sat_models" -lt 1 ]; then
    echo "FAIL: no SAT model was checked"
    fail=1
fi
if [ "$fail" -ne 0 ]; then
    exit 1
fi
echo "gf2 proof-check: examined=$examined sat_models=$sat_models drat_verified=$drat_verified (xors>0: $drat_verified_xors) uncertified=$uncertified"

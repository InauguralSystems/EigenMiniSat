#!/usr/bin/env bash
# --gf2 against the WHOLE tracked corpus manifest (hq#58 EMS-GF2-1/-2).
#
# Each row is solved with --gf2 off and on. Both verdicts must equal the
# manifest's expected column -- not merely each other -- and each run must
# print exactly one status line. A SAT answer's model is checked against the
# original CNF. The run must examine every manifest row, and at least one SAT
# row on which elimination actually derived equivalence clauses: before this,
# only the `vendored-*` rows ran, all with xors=0, so --gf2 did nothing here
# and a sign error in the derived clauses (UNSAT on a SAT instance, labelled
# certified) passed every gate.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EIGS="${EIGENSCRIPT_BIN:-$(command -v eigenscript || echo ../EigenScript/src/eigenscript)}"
tmp="${TMPDIR:-/tmp}/eigenminisat-gf2-corpus.$$"
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
mkdir -p "$tmp"
cd "$ROOT"

manifest=tests/corpus/manifest.txt
# Derive the population from the tracked manifest, never a hand list.
awk -F '|' '!/^#/ && NF { print $1 "|" $2 "|" $3 }' "$manifest" > "$tmp/rows"
want_rows="$(wc -l < "$tmp/rows" | tr -d ' ')"
if [ "$want_rows" -eq 0 ]; then
    echo "FAIL: $manifest yielded 0 rows"
    exit 1
fi

# Exactly one `s ` line, printed as its second field; anything else fails.
one_verdict() {
    local file=$1 label=$2 count
    count="$(grep -c '^s ' "$file" || true)"
    if [ "$count" != 1 ]; then
        echo "FAIL: $label printed $count status lines (want exactly 1)" >&2
        sed -n '1,20p' "$file" >&2
        return 1
    fi
    awk '/^s / { print $2 }' "$file"
}

examined=0
sat_equiv_rows=0
while IFS='|' read -r name path expected; do
    case "$expected" in
        SAT) want=SATISFIABLE ;;
        UNSAT) want=UNSATISFIABLE ;;
        *) echo "FAIL: $name: manifest expected '$expected' is not SAT/UNSAT"; exit 1 ;;
    esac
    "$EIGS" minisat.eigs --model "$path" > "$tmp/off"
    "$EIGS" minisat.eigs --gf2 --model "$path" > "$tmp/on"
    off_verdict="$(one_verdict "$tmp/off" "$name (gf2 off)")"
    on_verdict="$(one_verdict "$tmp/on" "$name (gf2 on)")"
    if [ "$off_verdict" != "$want" ]; then
        echo "FAIL: $name: MiniSat path answered $off_verdict, manifest says $want"
        exit 1
    fi
    if [ "$on_verdict" != "$want" ]; then
        echo "FAIL: $name: --gf2 answered $on_verdict, manifest says $want"
        grep '^c gf2' "$tmp/on" || true
        exit 1
    fi
    echo "PASS: $name: --gf2 on/off verdicts match the manifest ($on_verdict)"
    equivalences="$(awk '/^c gf2=on / { for (i = 1; i <= NF; i++) if ($i ~ /^equivalences=/) { sub(/^equivalences=/, "", $i); print $i } }' "$tmp/on")"
    if [ -z "$equivalences" ]; then
        echo "FAIL: $name: --gf2 printed no census line"
        exit 1
    fi
    if [ "$on_verdict" = SATISFIABLE ]; then
        # Reuse the competition harness's SATLIB-tail normalizer and complete
        # model checker rather than maintaining a second certificate policy.
        awk -f benchmarks/normalize_cnf.awk "$path" > "$tmp/normalized.cnf"
        PYTHONDONTWRITEBYTECODE=1 python3 - "$tmp/normalized.cnf" "$tmp/on" <<'PY'
import sys
sys.path.insert(0, "benchmarks")
import certificate_validation
certificate_validation.check_model(sys.argv[1], open(sys.argv[2], "rb").read())
PY
        echo "PASS: $name: GF(2) SAT model verifies against original CNF"
        if [ "$equivalences" -gt 0 ]; then
            sat_equiv_rows=$((sat_equiv_rows + 1))
        fi
    fi
    awk -v name="$name" '/^c gf2_result / { print "REPORT: instance=" name " " substr($0, 3) }' "$tmp/on"
    examined=$((examined + 1))
done < "$tmp/rows"

if [ "$examined" -ne "$want_rows" ]; then
    echo "FAIL: examined $examined of $want_rows manifest rows"
    exit 1
fi
if [ "$sat_equiv_rows" -lt 1 ]; then
    echo "FAIL: no SAT row derived equivalence clauses; --gf2's derived clauses went unexamined"
    exit 1
fi
echo "PASS: gf2 corpus examined $examined manifest rows ($sat_equiv_rows SAT row(s) with derived equivalences)"

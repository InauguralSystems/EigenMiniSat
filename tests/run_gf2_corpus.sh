#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EIGS="${EIGENSCRIPT_BIN:-$(command -v eigenscript || echo ../EigenScript/src/eigenscript)}"
tmp="${TMPDIR:-/tmp}/eigenminisat-gf2-corpus.$$"
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
mkdir -p "$tmp"
cd "$ROOT"

# Derive the vendored population from the tracked manifest, never a hand list.
awk -F '|' '!/^#/ && $6 ~ /^vendored-/ { print $1 "|" $2 }' tests/corpus/manifest.txt |
while IFS='|' read -r name path; do
    "$EIGS" minisat.eigs --model "$path" > "$tmp/off"
    "$EIGS" minisat.eigs --gf2 --model "$path" > "$tmp/on"
    off_verdict="$(awk '/^s / { print $2; exit }' "$tmp/off")"
    on_verdict="$(awk '/^s / { print $2; exit }' "$tmp/on")"
    if [ "$off_verdict" != "$on_verdict" ]; then
        echo "FAIL: $name: GF(2) verdict $on_verdict differs from MiniSat path $off_verdict"
        exit 1
    fi
    echo "PASS: $name: --gf2 on/off verdict agreement ($on_verdict)"
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
    fi
    awk -v name="$name" '/^c gf2_result / { print "REPORT: instance=" name " " substr($0, 3) }' "$tmp/on"
done

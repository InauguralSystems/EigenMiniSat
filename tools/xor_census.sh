#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EIGS="${EIGENSCRIPT_BIN:-$(command -v eigenscript || echo ../EigenScript/src/eigenscript)}"
MANIFEST="${1:-tests/corpus/manifest.txt}"

cd "$ROOT"
printf '%s\n' '| instance | XORs | covered clauses | fraction |'
printf '%s\n' '|---|---:|---:|---:|'
awk -F '|' '!/^#/ && NF >= 2 { print $1 "|" $2 }' "$MANIFEST" |
while IFS='|' read -r name path; do
    line="$($EIGS minisat.eigs --gf2 "$path" | awk '/^c gf2=on / { print; exit }')"
    xors="$(printf '%s\n' "$line" | awk '{ for (i=1;i<=NF;i++) if ($i ~ /^xors=/) { sub(/^xors=/,"",$i); print $i } }')"
    covered="$(printf '%s\n' "$line" | awk '{ for (i=1;i<=NF;i++) if ($i ~ /^xor_clauses=/) { sub(/^xor_clauses=/,"",$i); print $i } }')"
    clauses="$(printf '%s\n' "$line" | awk '{ for (i=1;i<=NF;i++) if ($i ~ /^clauses=/) { sub(/^clauses=/,"",$i); print $i } }')"
    fraction="$(printf '%s\n' "$line" | awk '{ for (i=1;i<=NF;i++) if ($i ~ /^xor_coverage=/) { sub(/^xor_coverage=/,"",$i); print $i } }')"
    printf '| %s | %s | %s/%s | %s |\n' "$name" "$xors" "$covered" "$clauses" "$fraction"
done

"$EIGS" tools/xor_census_controls.eigs

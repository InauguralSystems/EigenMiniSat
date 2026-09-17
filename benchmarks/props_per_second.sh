#!/usr/bin/env bash
# props_per_second.sh -- EigenMiniSat's "MHz".
#
# A rate of a PRIMITIVE OPERATION (propagations/second), not a time-to-answer.
# Time-to-solve is policy-confounded: two solvers that pick different decision
# literals do different amounts of work, so a wall-clock ratio measures the
# search's luck as much as the runtime's speed. A propagation is the same unit
# of work whoever performs it -- so props/sec measures the MACHINE, the way MHz
# measures an emulator regardless of which game is loaded.
#
# Measured 2026-09-17 on tseitin_torus_4x4_odd.cnf (idle ASUS X540NA): EMS under
# the VM did 44,166 propagations in 19.55 s (2,259/s) while native MiniSat did
# 546,950 in 0.2295 s (2,383,256/s) -- EMS at 0.095% of native.
#
# The wall ratio for the same pair is 85x. The RATE ratio is 1,055x. They differ
# by 12x because native needed 12.4x MORE propagations to close the instance.
# Those two numbers support opposite conclusions -- "a normal interpreted-language
# gap" vs "the propagation loop is three orders of magnitude off, and our CDCL
# policy is the strong part" -- which is the whole reason this script exists.
#
#   bash benchmarks/props_per_second.sh [file.cnf]
#
# EIGS   path to the eigenscript binary (default: ../EigenScript/src/eigenscript,
#        the repo convention -- build/release/ cannot resolve the stdlib, whose
#        root is derived from the binary's own directory).
# MINISAT path to native minisat       (default: minisat on PATH)
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CNF="${1:-$ROOT/benchmarks/oracle/tseitin_torus_4x4_odd.cnf}"
EIGS="${EIGS:-$ROOT/../EigenScript/src/eigenscript}"
MINISAT="${MINISAT:-minisat}"

die() { echo "props_per_second: $*" >&2; exit 1; }
[ -f "$CNF" ]       || die "no such CNF: $CNF"
[ -x "$EIGS" ]      || die "no eigenscript binary at $EIGS (set EIGS=)"
command -v "$MINISAT" >/dev/null || die "no native minisat (set MINISAT=)"

# A rate off a sanitizer build is not a performance number. `make asan`
# OVERWRITES src/eigenscript with a ~5x slower binary, and --version does not
# say so: this script first read 129 s for a 20 s instance and reported 0.0146%
# of native instead of ~0.1%. Refuse rather than publish it.
if nm -D "$EIGS" 2>/dev/null | grep -q "__asan\|__ubsan" ||
   ldd "$EIGS" 2>/dev/null | grep -qi asan; then
    die "$EIGS is a sanitizer build (~5x slow) -- rebuild with 'make build' or set EIGS="
fi

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

# --- EigenMiniSat ------------------------------------------------------------
( cd "$ROOT" && "$EIGS" minisat.eigs --cdcl "$CNF" ) > "$tmp/ems.out" 2>&1 \
  || die "EMS run failed (rc=$?); see $tmp/ems.out"
ems_verdict=$(sed -n 's/^s \(SATISFIABLE\|UNSATISFIABLE\)$/\1/p' "$tmp/ems.out")
ems_props=$(tr ' ' '\n' < "$tmp/ems.out" | sed -n 's/^propagations=\([0-9][0-9]*\)$/\1/p')
ems_ms=$(tr ' ' '\n' < "$tmp/ems.out" | sed -n 's/^ms=\([0-9.eE+-]*\)$/\1/p')
[ -n "$ems_verdict" ] || die "EMS produced no verdict"
[ -n "$ems_props" ] && [ -n "$ems_ms" ] || die "EMS report lacks propagations= / ms="

# --- native MiniSat ----------------------------------------------------------
"$MINISAT" "$CNF" /dev/null > "$tmp/nat.out" 2>&1
nat_rc=$?
# minisat exits 10 = SAT, 20 = UNSAT; anything else is a real failure.
[ "$nat_rc" = 10 ] || [ "$nat_rc" = 20 ] || die "native minisat rc=$nat_rc; see $tmp/nat.out"
nat_verdict=$(sed -n 's/^\(SATISFIABLE\|UNSATISFIABLE\)$/\1/p' "$tmp/nat.out")
nat_props=$(sed -n 's/^propagations *: *\([0-9][0-9]*\).*/\1/p' "$tmp/nat.out")
nat_cpu=$(sed -n 's/^CPU time *: *\([0-9.eE+-]*\) s.*/\1/p' "$tmp/nat.out")
[ -n "$nat_props" ] && [ -n "$nat_cpu" ] || die "native report lacks propagations / CPU time"

# --- the verdicts must agree: a rate off a wrong answer is meaningless -------
[ "$ems_verdict" = "$nat_verdict" ] \
  || die "VERDICTS DISAGREE: EMS=$ems_verdict native=$nat_verdict -- not a perf question"

awk -v ep="$ems_props" -v ems="$ems_ms" -v np="$nat_props" -v nc="$nat_cpu" \
    -v cnf="$(basename "$CNF")" -v verdict="$ems_verdict" 'BEGIN {
  es = ems/1000.0
  er = ep/es; nr = np/nc
  printf "instance: %s   verdict: %s (both arms agree)\n\n", cnf, verdict
  printf "%-18s %14s %12s %16s\n", "arm", "propagations", "seconds", "props/sec"
  printf "%-18s %14d %12.4f %16.0f\n", "EigenMiniSat", ep, es, er
  printf "%-18s %14d %12.4f %16.0f\n", "native MiniSat", np, nc, nr
  printf "\nEigenMiniSat is %.4f%% of native  (native is %.0fx faster per propagation)\n", 100*er/nr, nr/er
  printf "search:  EigenMiniSat closed it with %.2fx the propagations -- native needed %.1fx MORE\n", ep/np, np/ep
  printf "wall:    %.0fx  <- POLICY-CONFOUNDED, shown only for contrast\n", es/nc
}'

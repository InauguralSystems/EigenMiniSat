#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EIGS="${EIGENSCRIPT_BIN:-/home/jon/EigenScript/src/eigenscript}"

cd "$ROOT"
"$EIGS" tests/test_solver.eigs
"$EIGS" minisat.eigs tests/fixtures/simple_sat.cnf
"$EIGS" minisat.eigs --watched tests/fixtures/simple_sat.cnf
"$EIGS" minisat.eigs --persistent tests/fixtures/simple_sat.cnf
"$EIGS" minisat.eigs --cdcl tests/fixtures/simple_sat.cnf
"$EIGS" minisat.eigs tests/fixtures/unit_unsat.cnf
"$EIGS" minisat.eigs --watched tests/fixtures/unit_unsat.cnf
"$EIGS" minisat.eigs --persistent tests/fixtures/unit_unsat.cnf
"$EIGS" minisat.eigs --cdcl tests/fixtures/unit_unsat.cnf
"$EIGS" minisat.eigs --bench --size "${1:-1}"
"$EIGS" minisat.eigs --restart-bench --size "${1:-1}"
"$EIGS" minisat.eigs --phase-bench --size "${1:-1}"
"$EIGS" minisat.eigs --metadata-bench --size "${1:-1}"
"$EIGS" minisat.eigs --parse-bench --size "${1:-1}"
"$EIGS" minisat.eigs --scan-parse-bench --size "${1:-1}"
"$EIGS" minisat.eigs --file-bench --size "${1:-1}"
"$EIGS" minisat.eigs --corpus-bench

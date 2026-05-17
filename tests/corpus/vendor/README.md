# Vendored Structural Corpus

These DIMACS files are checked-in, generated corpus fixtures. They are not
byte-for-byte copies of external benchmark archives; they are small local
instances generated from standard SAT benchmark families so the corpus remains
self-contained on constrained hardware.

Provenance:

- Pigeonhole and graph-coloring formulas follow the standard DIMACS/SATLIB
  benchmark family style documented by SATLIB:
  https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html
- The parity file follows the existing EigenMiniSat XOR-triangle generator.
- Large SAT Competition archives are intentionally excluded from this corpus
  because they are too large for routine local validation on this machine.

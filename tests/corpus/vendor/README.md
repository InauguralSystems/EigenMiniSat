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

Each file carries the SATLIB two-line trailer — a line containing only `%`,
then a line containing only `0` — because every instance in the real `uf`/`uuf`
archives does. Omitting it was how #83 hid: the generator and the parser shared
an author and therefore shared the assumption that the archives are clean
DIMACS, so the fixtures agreed with the parser and both disagreed with the
outside world. Neither line belongs to the formula; the parser cuts the text at
the `%` before tokenizing (`lib/dimacs.eigs`), and a bare `0` with no `%` above
it is now a parse error rather than an empty clause. Keep the trailer when
regenerating these files — it is the part that tests the convention.

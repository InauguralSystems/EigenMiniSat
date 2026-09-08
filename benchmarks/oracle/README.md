# Regime C preflight outputs

`regime-c-3x3.stdout` and `regime-c-4x4.stdout` pin the complete EMS-VM CLI
output under CDCL current defaults (regime C), with only the trailing numeric
` ms=` removed. `run_native_oracle.sh` compares every ladder lane's two
preflight solves against them byte for byte, independent of the AOT arm.

Banked on 2026-09-08 from a fresh native/VM run at EigenMiniSat `fb031b7`,
with unchanged solver and emitter, using EigenScript v0.43.0
(`a6c50fba6a6250ea347a34500d6c9fa503a5c931`). Before banking, the 3x3 DIMACS
tokens matched the existing repository fixture, and both runs matched the
independently documented regime-C conflicts and resolutions in CLAUDE.md and
TSEITIN_LADDER.md. The captured readings were:

```text
BANK 3x3: conflicts=592 resolutions=1681; normalized stdout bytes=1129
BANK 4x4: conflicts=9986 resolutions=33873; normalized stdout bytes=1174
```

These are deterministic counter/format fixtures, not wall-time benchmarks.
There is deliberately no automatic regeneration mode: an intentional solver
policy or CLI change requires reviewing the regime and the independent CNF
identity before replacing either bank. The identity checker separately pins
every rung's ordered torus encoding; an UNSAT answer alone is insufficient.

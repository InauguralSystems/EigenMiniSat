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

`tseitin_torus_4x4_odd.cnf` is an ordered input anchor captured on 2026-09-08
from the unchanged EigenScript emitter at EigenMiniSat `69aff93`, with the
same pinned VM. Command (from the repository root):

```bash
/home/jon/src/wt/es-v043/src/eigenscript benchmarks/dump_tseitin_cnf.eigs 4 4
```

Only the emitter's extra blank line at EOF was removed. The identity awk
program did not generate this artifact. Native MiniSat
returned UNSAT, and the captured CNF's full normalized VM output matched the
already committed `regime-c-4x4.stdout`. The harness compares emitted 4x4
tokens directly to this capture, alongside its existing 3x3 fixture comparison.
Selftest corrupts each reference independently and requires the production
bank comparison to reject it. Larger rungs still use the general identity
model; these two anchors do not constitute independent fixtures for all sizes.

The ordering pin and regime bank cover different observations. Swapping
3x3 vertex blocks 1 and 2 left normalized VM output identical in the round-3
measurement. The ordered identity check rejected it. A matching regime bank
alone therefore does not establish that the input's order is unchanged.

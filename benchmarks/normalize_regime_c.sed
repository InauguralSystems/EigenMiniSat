# Strip only the trailing wall-clock field from a CDCL statistics line, so
# the rest of the CLI output compares byte for byte against a regime-C bank.
# One definition, used by benchmarks/run_native_oracle.sh and
# tests/run_regime_c_check.sh.
/^c /s/ ms=[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$//

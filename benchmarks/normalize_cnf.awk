# Shared SATLIB-tail normalization. cnf_preservation.py independently checks
# every output against its source before any solver consumes it.
/^[[:space:]]*%[[:space:]]*$/ && !tail {tail=1; next}
tail && /^[[:space:]]*$/ {next}
tail && /^[[:space:]]*0[[:space:]]*$/ && !zero {zero=1; next}
tail {bad=1; exit 65}
{print}
END {if (bad) exit 65}

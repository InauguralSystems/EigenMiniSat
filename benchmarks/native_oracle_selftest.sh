# Sourced only for --selftest, --selftest-case, or explicit --plant.
# No comparator is called here. Each case starts the actual harness CLI;
# injections change inputs, command outputs, or accounting state, then the
# ordinary discovery/build/emission/solve/finalization path must detect them.

mapfile -t oracle_cases < <(python3 "$ROOT/benchmarks/oracle_selftest.py" --list)

plant_fault() {
    local stage=$1 known=0 item target
    for item in "${oracle_cases[@]}"; do [[ "$plant" != "$item" ]] || known=1; done
    ((known)) || fail options configuration "unknown plant: $plant"
    printf 'PLANT %s: %s (explicit fault injection)\n' "$plant" "$stage"
    if [[ "$stage" == input ]]; then
        case "$plant" in
            unreadable-input|unopenable-input|open-race|empty-input|trailer-junk|header-count|variable-bound|unterminated-clause|missing-header|invalid-header|invalid-literal)
                cp "$input" "$dir/source.cnf"
                input="$dir/source.cnf"
                ;;
        esac
    fi
    case "$stage:$plant" in
        setup:missing-tool)
            command() { [[ "$*" != '-v awk' ]] && builtin command "$@"; } ;;
        setup:missing-vm) EIGS=/nonexistent/oracle-vm ;;
        setup:missing-native) MINISAT=/nonexistent/oracle-native ;;
        resolved:not-executable) MINISAT="$work/not-executable"; : > "$MINISAT" ;;
        enumeration:find-error) find() { return 7; } ;;
        enumeration:sort-error) sort() { return 7; } ;;
        enumeration:execution-error) mapfile() { return 7; } ;;
        input:unreadable-input) chmod 000 "$input" ;;
        input:unopenable-input) rm "$input" ;;
        open:open-race) rm "$input" ;;
        input:empty-input) : > "$input" ;;
        input:trailer-junk) printf '\n%%\nJUNK\n' >> "$input" ;;
        input:normalizer-error)
            printf '#!/usr/bin/env bash\nexit 7\n' > "$work/normalizer.sh"
            normalizer_cmd=(bash "$work/normalizer.sh") ;;
        input:normalizer-empty) normalizer_cmd=(true) ;;
        normalized:header-line-merge)
            awk '$1=="p" {hdr=$0; next}
                hdr && NF && $1!="c" {print hdr" "$1; $1=""; print; hdr=""; next}
                {print}' "$output" > "$dir/header-merged.cnf"
            mv "$dir/header-merged.cnf" "$output"
            ;;
        normalized:normalization-corruption)
            # Header-consistent corruption after the real awk. All three arms
            # would receive this SAT formula if the post-condition were removed.
            printf 'p cnf 18 1\n1 0\n' > "$output" ;;
        input:header-count) sed -i 's/p cnf 18 72/p cnf 18 73/' "$input" ;;
        input:variable-bound) sed -i 's/p cnf 18 72/p cnf 17 72/' "$input" ;;
        input:unterminated-clause) printf '1\n' >> "$input" ;;
        input:missing-header) sed -i '/^p /d' "$input" ;;
        input:invalid-header) sed -i 's/p cnf 18 72/p cnf X 72/' "$input" ;;
        input:invalid-literal) printf 'X 0\n' >> "$input" ;;
        native-report:native-empty-report) : > "$dir/native.out" ;;
        native-report:native-empty-result) : > "$dir/native.result" ;;
        native-report:native-unterminated-result) printf UNSAT > "$dir/native.result" ;;
        native-report:native-inconsistent-result) printf 'SAT\n' > "$dir/native.result" ;;
        oracle-answer:odd-torus-answer) native_verdict=SATISFIABLE ;;
    esac
    if [[ "$stage" == discovery ]]; then
        case "$plant" in
            absent-aot) AOT=on; AOT_BUILD="$work/absent" ;;
            mismatched-vm|version-missing|version-wrong|invalid-aot-binary)
                # Metadata guards need presence, not the external build script.
                AOT_BUILD="$work/present-build.sh"; : > "$AOT_BUILD"
                [[ "$plant" != mismatched-vm ]] || EIGS="$work/different-vm"
                [[ "$plant" != version-missing ]] || git() { return 1; }
                [[ "$plant" != version-wrong ]] || git() { echo v0.42.0; }
                [[ "$plant" != invalid-aot-binary ]] || AOT_BINARY="$work/missing-aot"
                ;;
        esac
        case "$plant" in
            vacuity-discovery) selected=0 ;;
            auto-degrades|required-build-fails)
                unset AOT_BINARY
                AOT=auto
                [[ "$plant" != required-build-fails ]] || AOT=on
                mkdir -p "$work/failed-toolchain/aot" "$work/failed-toolchain/src"
                printf '{}\n' > "$work/failed-toolchain/eigs.json"
                printf '#!/usr/bin/env bash\nexit 7\n' > "$work/failed-toolchain/aot/build.sh"
                AOT_BUILD="$work/failed-toolchain/aot/build.sh"
                # The real prepare_aot must clear stale state on failure.
                aot_enabled=1; aot_cmd=(false)
                ;;
        esac
        return
    fi

    [[ "$stage" == run ]] || return 0

    export ORACLE_VM="$EIGS" ORACLE_AOT="${aot_cmd[0]:-}" ORACLE_FAULT="$plant"
    case "$plant" in
        emitted-read-error) cnf_tokens() { return 7; } ;;
        fixture-read-error) rung_fixtures[3x3]="$work/missing-fixture.cnf" ;;
        output-normalize-error) sed() { return 7; } ;;
        native-error)
            printf '#!/usr/bin/env bash\nexit 3\n' > "$work/native-error.sh"
            chmod +x "$work/native-error.sh"; MINISAT="$work/native-error.sh" ;;
        fixture-3x3|fixture-4x4)
            target=${plant#fixture-}
            # Corrupt the reference, not the emitted input: the model check
            # passes, so it cannot absorb the bank comparison's witness.
            awk 'NF && $1!="c" && $1!="p" && !changed {$1=-$1; changed=1} {print}' \
                "${rung_fixtures[$target]}" > "$work/corrupt-reference.cnf"
            rung_fixtures[$target]="$work/corrupt-reference.cnf"
            ;;
        corrupted-cnf|wrong-ems-verdict|regime-3x3|regime-4x4)
            export ORACLE_CORRUPT="$work/corrupt.cnf"
            cat > "$work/vm-wrapper.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
args=("$@")
if [[ "$ORACLE_FAULT" == corrupted-cnf ]]; then
    # Delete the first clause of the actual emitted rung, updating its header.
    # The native oracle has already solved the intact input.
    awk '
        $1=="p" {$4--; print; next}
        NF && $1!="c" && !removed {removed=1; next}
        {print}
        END {if (!removed) exit 1}
    ' "${args[${#args[@]}-1]}" > "$ORACLE_CORRUPT"
    args[${#args[@]}-1]=$ORACLE_CORRUPT
    exec "$ORACLE_VM" "${args[@]}"
fi
case "$ORACLE_FAULT" in
    wrong-ems-verdict) edit='s/^s UNSATISFIABLE$/s SATISFIABLE/' ;;
    regime-3x3) edit='s/ conflicts=592 / conflicts=593 /' ;;
    regime-4x4) edit='s/ conflicts=9986 / conflicts=9987 /' ;;
esac
"$ORACLE_VM" "${args[@]}" | sed "$edit"
EOF
            vm_cmd=(bash "$work/vm-wrapper.sh" "$ROOT/minisat.eigs")
            ;;
        perturbed-aot)
            cat > "$work/aot-wrapper.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
"$ORACLE_AOT" "$@"
printf 'c planted AOT byte\n'
EOF
            aot_cmd=(bash "$work/aot-wrapper.sh")
            ;;
        solver-timeout)
            printf '#!/usr/bin/env bash\nexec sleep 10\n' > "$work/dead-vm.sh"
            vm_cmd=(bash "$work/dead-vm.sh"); SOLVE_TIMEOUT=1
            ;;
        empty-output) vm_cmd=(true) ;;
        resized-emitter|identity-clauses|vertex-order)
            cat > "$work/emitter-wrapper.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
args=("$@")
case "$ORACLE_FAULT" in
    resized-emitter)
        args[${#args[@]}-1]=3
        exec "$ORACLE_VM" "${args[@]}"
        ;;
    identity-clauses)
        "$ORACLE_VM" "${args[@]}" | awk '
            NF && $1!="c" && $1!="p" && !changed {$1=-$1; changed=1} {print}'
        ;;
    vertex-order)
        # Exchange zero-based vertex blocks 1 and 2; keep every clause intact.
        "$ORACLE_VM" "${args[@]}" | awk '
            !NF || $1=="c" || $1=="p" {print; next}
            {n++; if(n>=9 && n<=24) line[n]=$0; else print}
            n==24 {for(i=17;i<=24;i++) print line[i]; for(i=9;i<=16;i++) print line[i]}'
        ;;
esac
EOF
            emitter_cmd=(bash "$work/emitter-wrapper.sh" "$ROOT/benchmarks/dump_tseitin_cnf.eigs")
            ;;
        vacuity-completion) selected=0 ;;
        coverage-passed) passed=-1 ;;
        coverage-native) native_runs=-1 ;;
        coverage-vm) vm_runs=-1 ;;
        coverage-aot) aot_runs=-1 ;;

    esac
}

selftest_run() {
    if ORACLE_SOLVE_TIMEOUT="$SOLVE_TIMEOUT" ORACLE_VM_REF="$EIGS" python3 "$ROOT/benchmarks/oracle_selftest.py" "$HARNESS" "$work" "$aot_enabled" "${aot_cmd[0]:-}" "$selftest_case"; then
        exit 0
    else
        exit "$?"
    fi
}

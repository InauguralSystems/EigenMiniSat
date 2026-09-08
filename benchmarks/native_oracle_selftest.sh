# Sourced only for --selftest, --selftest-case, or explicit --plant.
# No comparator is called here. Each case starts the actual harness CLI;
# injections change inputs, command outputs, or accounting state, then the
# ordinary discovery/build/emission/solve/finalization path must detect them.

oracle_cases=(clean corrupted-cnf wrong-ems-verdict perturbed-aot zero-instances
    solver-timeout empty-output resized-emitter identity-clauses vertex-order
    fixture-3x3 fixture-4x4 regime-3x3 regime-4x4 vacuity-discovery
    vacuity-completion coverage-passed coverage-native coverage-vm coverage-aot
    unreadable-input unopenable-input auto-degrades required-build-fails)

plant_fault() {
    local stage=$1 known=0 item target
    for item in "${oracle_cases[@]}"; do [[ "$plant" != "$item" ]] || known=1; done
    ((known)) || fail options configuration "unknown plant: $plant"
    printf 'PLANT %s: %s (explicit fault injection)\n' "$plant" "$stage"
    if [[ "$stage" == discovery ]]; then
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

    export ORACLE_VM="$EIGS" ORACLE_AOT="${aot_cmd[0]:-}" ORACLE_FAULT="$plant"
    case "$plant" in
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
        unreadable-input|unopenable-input)
            # Replace only this process's input list, never chmod a real fixture.
            cp "$ROOT/tests/fixtures/unit_unsat.cnf" "$work/unreadable.cnf"
            files=("$work/unreadable.cnf")
            selected=$((${#lane_rungs[@]}+1))
            if [[ "$plant" == unreadable-input ]]; then
                chmod 000 "$work/unreadable.cnf"
            else
                rm "$work/unreadable.cnf"
            fi
            ;;
    esac
}

selftest_run() {
    local name rc expected_rc markers marker ok count=0 caught=0 missed=0 controls=0
    local expected=24 mode=off pinned=0
    local -a cases=("${oracle_cases[@]}") child_args
    local real_aot=${aot_cmd[0]:-}
    ((aot_enabled)) && mode=on
    if [[ -x "$EIGS_DIR/src/eigenscript" && "$(realpath "$EIGS_DIR/src/eigenscript")" == "$EIGS" ]] &&
        [[ "$(git -C "$EIGS_DIR" describe --tags --exact-match 2>/dev/null || true)" == v0.43.0 ]]; then
        pinned=1
    fi
    if [[ -n "$selftest_case" ]]; then
        local known=0
        for name in "${cases[@]}"; do [[ "$name" != "$selftest_case" ]] || known=1; done
        ((known)) || fail options configuration "unknown selftest case: $selftest_case"
        cases=("$selftest_case"); expected=1
        printf 'SELFTEST selection=%s (partial; not the full suite)\n' "$selftest_case"
    fi
    mkdir -p "$work/probe-inputs" "$work/empty"
    cp "$ROOT/tests/fixtures/unit_unsat.cnf" "$work/probe-inputs/unit.cnf"
    cp "$ROOT/tests/fixtures/simple_sat.cnf" "$work/probe-inputs/sat.cnf"
    for name in "${cases[@]}"; do
        if [[ "$name" == perturbed-aot || "$name" == coverage-aot ]] && ((!aot_enabled)); then
            echo "SELFTEST $name: SKIPPED (AOT not enabled)"
            expected=$((expected-1)); continue
        fi
        if [[ "$name" == auto-degrades || "$name" == required-build-fails ]] && ((!pinned)); then
            echo "SELFTEST $name: SKIPPED (matching pinned runtime absent)"
            expected=$((expected-1)); continue
        fi
        expected_rc=1
        child_args=(--rungs '3x3 4x4' --instances "$work/probe-inputs" --aot "$mode" --plant "$name")
        case "$name" in
            clean)
                expected_rc=0
                markers=$'IDENTITY 3x3: PASS (banked repository fixture\nIDENTITY 4x4: PASS (banked repository fixture\nPREFLIGHT 3x3: PASS\nPREFLIGHT 4x4: PASS\nSUMMARY PASS selected=4 passed=4 native=4 VM=4 AOT='
                markers+=$((aot_enabled*4))
                ;;
            corrupted-cnf|wrong-ems-verdict) markers='FAIL tseitin-3x3-odd [verdict]:' ;;
            perturbed-aot) markers='FAIL tseitin-3x3-odd [aot-diff]:' ;;
            zero-instances)
                child_args=(--rungs '' --instances "$work/empty" --aot "$mode" --plant "$name")
                markers='FAIL instances-discovery [vacuity]:'
                ;;
            solver-timeout) markers='FAIL tseitin-3x3-odd [vm]: rc=124' ;;
            empty-output) markers='FAIL tseitin-3x3-odd [vm-output]:' ;;
            resized-emitter) markers='FAIL 4x4 [rung-identity]:' ;;
            identity-clauses|vertex-order) markers='FAIL 3x3 [rung-identity]:' ;;
            fixture-*) markers="FAIL ${name#fixture-} [rung-fixture]:" ;;
            regime-*) markers="FAIL ${name#regime-} [regime]:" ;;
            vacuity-discovery) markers='FAIL instances-discovery [vacuity]:' ;;
            vacuity-completion) markers='FAIL instances-completion [vacuity]:' ;;
            coverage-*) markers='FAIL instances [coverage]:' ;;
            unreadable-input|unopenable-input) markers='[input-open]:' ;;
            auto-degrades)
                expected_rc=0
                markers=$'AOT: SKIPPED (build failed rc=7;\nSUMMARY PASS selected=2 passed=2 native=2 VM=2 AOT=0'
                # Build policy has no dependence on ladder selection. Its own
                # control is file-only; comparator plants above use real rungs.
                child_args=(--rungs '' --instances "$work/probe-inputs" --plant "$name")
                ;;
            required-build-fails) markers='FAIL AOT [build]: rc=7;' ;;
        esac
        # HARNESS is this invocation's actual path, including a critic's mutant
        # copy. The child does not call helper functions or use a saved script.
        # A child gets a fresh shell: errexit is not suppressed by this if.
        if KEEP_WORK=0 AOT_BINARY="$real_aot" bash "$HARNESS" "${child_args[@]}" --timeout "$SOLVE_TIMEOUT" \
            > "$work/selftest-$name.log" 2>&1; then rc=0; else rc=$?; fi
        ok=1
        [[ "$rc" == "$expected_rc" ]] || ok=0
        while IFS= read -r marker; do
            grep -qF "$marker" "$work/selftest-$name.log" || ok=0
        done <<< "$markers"
        count=$((count+1))
        if ((ok)); then
            if ((expected_rc == 0)); then
                controls=$((controls+1))
                printf 'CONTROL %s: PASS (production CLI rc=0)\n' "$name"
            else
                caught=$((caught+1))
                printf 'SELFTEST %s: RED (production CLI rc=%s)\n' "$name" "$rc"
            fi
        else
            missed=$((missed+1))
            printf 'SELFTEST %s: MISS (production CLI rc=%s, expected rc=%s and named evidence)\n' "$name" "$rc" "$expected_rc"
            cat "$work/selftest-$name.log"
        fi
    done
    # The fixed full-suite floor detects removal from the case inventory too.
    if ((count == 0 || count != expected || missed != 0)); then
        printf 'SELFTEST BROKEN checked=%s expected=%s caught=%s controls=%s missed=%s (exit 2)\n' "$count" "$expected" "$caught" "$controls" "$missed"
        exit 2
    fi
    if ((caught == 0)); then
        printf 'SELFTEST CONTROL PASS checked=%s controls=%s (no negative case selected; exit 1)\n' "$count" "$controls"
    else
        printf 'SELFTEST ALL RED checked=%s expected=%s caught=%s controls=%s (intentional exit 1)\n' "$count" "$expected" "$caught" "$controls"
    fi
    exit 1
}

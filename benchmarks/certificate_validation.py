"""Explicit certificate evidence for timings beyond the tractable VM anchors.

This verifies answers, not VM equivalence on unanchored inputs. Prebuilt binary
hashes identify the checked executable; declared build commands do not prove a
source-to-binary relationship. The caller owns source snapshots and cancellation.
"""
import os
from pathlib import Path
import re
import shutil

import cnf_preservation


def check_model(cnf, data, native=False):
    """Require one complete, consistent DIMACS assignment satisfying all clauses."""
    records = cnf_preservation.formula(cnf, False)
    variables = int(records[0][2])
    if native:
        status, separator, body = data.partition(b"\n")
        if status != b"SAT" or not separator:
            raise ValueError("native SAT model lacks SAT header")
        fields = body.split()
    else:
        lines = [line for line in data.split(b"\n") if line.startswith(b"v ") or line == b"v"]
        if len(lines) != 1:
            raise ValueError("SAT model needs exactly one v-line")
        fields = lines[0].split()[1:]
    if not fields or fields[-1] != b"0" or any(not re.fullmatch(rb"-?[0-9]+", x) for x in fields):
        raise ValueError("SAT model is malformed or unterminated")
    literals = [int(x) for x in fields[:-1]]
    if len(literals) != variables or {abs(x) for x in literals} != set(range(1, variables + 1)):
        raise ValueError("SAT model needs every declared variable exactly once")
    assignment = {abs(x): x > 0 for x in literals}
    clause = []
    for token in (token for record in records[1:] for token in record):
        value = int(token)
        if value:
            clause.append(value)
        else:
            if not any(assignment[abs(x)] == (x > 0) for x in clause):
                raise ValueError("SAT model does not satisfy input clause")
            clause = []


def certificate_reference(api, cnf, data, proof):
    """Remove only the exact requested proof report and a validated SAT model.

    All other bytes (including every deterministic counter) remain compared.
    Timed runs never enable proof or model output.
    """
    verdict, _ = api.ems_report(data)
    lines = data.splitlines(keepends=True)
    report = (b"c proof written to " + os.fsencode(proof) + b"\n" if verdict == "UNSATISFIABLE"
              else b"c satisfiable: no refutation to write (check the model instead)\n")
    api.require(lines.count(report) == 1, "certificate run needs exactly the requested proof report")
    lines.remove(report)
    if verdict == "SATISFIABLE":
        check_model(cnf, data)
        lines = [line for line in lines if not line.startswith(b"v ")]
    api.require(not any(line.startswith((b"c proof ", b"v ")) for line in lines),
                "unexpected certificate report or model output")
    return api.normalized_ems(b"".join(lines))


def verify_evidence(api, case):
    evidence = case.get("certificate_evidence")
    api.require(evidence and evidence["files"] and evidence["arms"], "missing certificate evidence")
    for path, digest in evidence["files"].items():
        api.require(Path(path).is_file() and api.sha256(path) == digest,
                    f"missing/stale/corrupt certificate artifact: {path}")
    api.require(api.sha256(case["cnf"]) == case["sha256"], "certificate input identity changed")


def checked_process(api, command, directory, args, environment, deadline):
    record = api.run_process([str(value) for value in command], directory,
                             api.remaining(deadline, args.timeout), environment)
    api.require(record["returncode"] == 0, f"certificate command failed rc={record['returncode']}: {directory}")
    return record


def prepare_rung(api, args, output, environment, deadline, rung):
    directory = output / "certificate-inputs" / rung
    directory.mkdir(parents=True)
    checked_process(api, [args.vm, api.ROOT / "benchmarks/dump_tseitin_cnf.eigs", *rung.split("x")],
                    directory / "emitter", args, environment, deadline)
    source = directory / "emitter/stdout"
    checked_process(api, ["awk", "-v", "rows=" + rung.split("x")[0], "-v", "cols=" + rung.split("x")[1],
                          "-f", api.ROOT / "benchmarks/torus_identity.awk", source],
                    directory / "identity", args, environment, deadline)
    checked_process(api, ["awk", "-f", api.ROOT / "benchmarks/normalize_cnf.awk", source],
                    directory / "normalize", args, environment, deadline)
    cnf = directory / "input.cnf"
    shutil.copyfile(directory / "normalize/stdout", cnf)
    cnf_preservation.compare(source, cnf)
    return {"name": f"tseitin-{rung}-odd", "cnf": cnf, "sha256": api.sha256(cnf),
            "verdict": "UNSATISFIABLE", "validation": "certificate", "extra_rung": True,
            "input_evidence": [str(p) for p in directory.rglob("*") if p.is_file()]}


def certify_case(api, args, output, environment, deadline, case, commands):
    directory = output / "certificates" / case["name"]
    directory.mkdir(parents=True)
    cnf = case["cnf"]
    files = {str(cnf): case["sha256"]}
    for path in [*commands.values(), args.drat_trim, *case.get("input_evidence", [])]:
        files[str(path)] = api.sha256(path)
    def remember(directory):
        for path in directory.rglob("*"):
            if path.is_file():
                files.setdefault(str(path), api.sha256(path))
    # Input/tool hashes captured before the first process are checked again
    # after all verification, so a checker cannot rewrite its own evidence.
    native_dir = directory / "native"
    native = api.run_process([str(commands["native"]), str(cnf), str(native_dir / "native.result")],
                             native_dir, api.remaining(deadline, args.timeout), environment)
    verdict, conflicts = api.native_report((native_dir / "stdout").read_bytes(),
                                           native_dir / "native.result", native["returncode"])
    api.require(verdict == case["verdict"], "certificate native verdict differs from input/preflight")
    api.require("native_conflicts" not in case or case["native_conflicts"] == conflicts,
                "certificate native counters differ from VM preflight")
    case["native_conflicts"] = conflicts
    if verdict == "SATISFIABLE":
        check_model(cnf, (native_dir / "native.result").read_bytes(), native=True)
    remember(native_dir)
    certified = []
    for arm, binary in commands.items():
        if arm == "native":
            continue
        proof = directory / (arm + ".drat")
        checked_process(api, [binary, "--cdcl", "--model", "--proof", proof, cnf],
                        directory / arm, args, environment, deadline)
        data = (directory / arm / "stdout").read_bytes()
        remember(directory / arm)
        reference = certificate_reference(api, cnf, data, proof)
        ems_verdict, ems_conflicts = api.ems_report(reference)
        api.require(ems_verdict == verdict, f"certificate verdict differs: {arm}")
        if "reference" in case:
            api.require(reference == case["reference"], f"certificate output differs from preflight reference: {arm}")
        if verdict == "UNSATISFIABLE":
            api.require(proof.is_file() and proof.stat().st_size > 0, "UNSAT certificate proof missing or empty")
            proof_hash = api.sha256(proof)
            files[str(proof)] = proof_hash
            # drat-trim's EXIT STATUS is the oracle. Its CR-prefixed VERIFIED
            # text is retained but never grepped as a correctness gate.
            checked_process(api, [args.drat_trim, cnf, proof], directory / (arm + "-checker"),
                            args, environment, deadline)
            api.require(api.sha256(proof) == proof_hash, "proof changed during verification")
        else:
            api.require(not proof.exists(), "SAT run unexpectedly wrote a refutation")
        case["reference"] = reference
        case["aot_conflicts"] = ems_conflicts
        certified.append(arm)
    api.require(certified == [arm for arm in commands if arm != "native"], "certificate arm population differs")
    remember(directory)
    case["certificate_evidence"] = {"arms": certified, "files": files}
    case["validation"] = ("vm-differential+certificate" if not case.get("extra_rung") else "certificate")
    verify_evidence(api, case)
    api.write_json(directory / "evidence.json", case["certificate_evidence"])
    case["certificate_evidence"]["files"][str(directory / "evidence.json")] = api.sha256(directory / "evidence.json")


def preflight(api, args, output, environment, deadline, cases, commands):
    api.require({"tseitin-3x3-odd", "tseitin-4x4-odd"}.issubset(case["name"] for case in cases),
                "certificate mode requires both VM regime anchors")
    for rung in args.extra_rung:
        cases.append(prepare_rung(api, args, output, environment, deadline, rung))
    api.require(len(cases) == len({case["name"] for case in cases}), "duplicate certificate case")
    pilots = []
    for case in cases:
        print(f"CERTIFICATE case={case['name']}", flush=True)
        certify_case(api, args, output, environment, deadline, case, commands)
        if not case.get("extra_rung"):
            continue
        for arm, binary in commands.items():
            directory = output / "pilots" / case["name"] / arm
            command = ([str(binary), str(case["cnf"]), str(directory / "native.result")] if arm == "native"
                       else [str(binary), "--cdcl", str(case["cnf"])])
            verify_evidence(api, case)
            record = api.run_process(command, directory, api.remaining(deadline, args.timeout), environment)
            api.validate_sample(case, arm, record)
            verify_evidence(api, case)
            record.update(case=case["name"], arm=arm, validated=True, validation=case["validation"])
            api.write_json(directory / "validation.json", record)
            pilots.append(record)
            api.write_json(output / "pilots.json", pilots)
    if not args.pilot_only:
        api.require(all(record["wall_ns"] <= 600_000_000_000 for record in pilots),
                    "extra-rung pilot exceeded 600 seconds; five-run timing remains incomplete")
    return sorted(cases, key=lambda case: case["name"])

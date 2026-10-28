#!/usr/bin/env python3
"""Reject identical normalized CNFs declared as different corpus families."""

import argparse
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalized_clauses(path):
    tokens = []
    for raw in path.read_text(encoding="ascii").splitlines():
        line = raw.strip()
        if not line or line.startswith("c") or line.startswith("p"):
            continue
        if line == "%":
            break
        tokens.extend(line.split())
    clauses, clause = [], []
    for token in tokens:
        literal = int(token)
        if literal == 0:
            clauses.append(tuple(sorted(clause)))
            clause = []
        else:
            clause.append(literal)
    if clause:
        raise ValueError(f"{path}: unterminated final clause")
    return tuple(sorted(clauses))


def load_manifest(path):
    entries = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("|")
        if len(fields) < 6:
            raise ValueError(f"{path}:{line_no}: expected six manifest fields")
        entries.append((fields[0], fields[1], fields[5]))
    if not entries:
        raise ValueError(f"{path}: examined 0 manifest entries")
    return entries


def check_manifest(path, root=ROOT):
    entries = load_manifest(path)
    seen = {}
    for name, relative, family in entries:
        normalized = normalized_clauses(root / relative)
        previous = seen.get(normalized)
        if previous and previous[1] != family:
            old_name, old_family = previous
            raise ValueError(
                "normalized corpus duplicate across different families: "
                f"{old_name} ({old_family}) and {name} ({family})"
            )
        seen.setdefault(normalized, (name, family))
    print(f"PASS: corpus diversity examined {len(entries)} manifest entries")


def selftest():
    manifest = ROOT / "tests/corpus/manifest.txt"
    check_manifest(manifest)
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        source = ROOT / "tests/corpus/pigeonhole_4_3.cnf"
        planted = tmp / "k4_3color_unsat.cnf"
        # Restore the old collision's normalized formula with a distinct header.
        planted.write_text(
            "c restored old K4/3-color duplicate for the #64 planted fault\n"
            + source.read_text(encoding="ascii"),
            encoding="ascii",
        )
        control = tmp / "control.txt"
        control.write_text(
            "php|tests/corpus/pigeonhole_4_3.cnf|UNSAT|12|34|pigeonhole\n"
            f"alias|{planted}|UNSAT|12|34|pigeonhole\n",
            encoding="utf-8",
        )
        check_manifest(control)
        planted_manifest = tmp / "planted.txt"
        planted_manifest.write_text(
            "php|tests/corpus/pigeonhole_4_3.cnf|UNSAT|12|34|pigeonhole\n"
            f"k4-3color-unsat|{planted}|UNSAT|12|34|graph-coloring\n",
            encoding="utf-8",
        )
        try:
            check_manifest(planted_manifest)
        except ValueError as error:
            expected = "php (pigeonhole) and k4-3color-unsat (graph-coloring)"
            if expected not in str(error):
                raise AssertionError(f"plant failed for the wrong reason: {error}")
            print(f"PASS: planted old duplicate pair rejected: {error}")
        else:
            raise AssertionError("planted old duplicate pair was accepted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path,
                        default=ROOT / "tests/corpus/manifest.txt")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
    else:
        check_manifest(args.manifest)

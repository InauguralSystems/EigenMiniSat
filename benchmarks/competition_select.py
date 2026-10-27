#!/usr/bin/env python3
"""Seeded, stratified SAT Competition sample from the Global Benchmark Database (#131).

The population, the strata and the draw are derived from GBD's own metadata
(its `meta` and `base` databases, recorded by SHA-256). Instances are never
committed: competition_run.py downloads each one by its GBD hash and re-derives
that hash from the downloaded bytes.

  python3 benchmarks/competition_select.py                    # download GBD, write the manifest
  python3 benchmarks/competition_select.py --check            # re-derive and compare (same GBD databases)
  python3 benchmarks/competition_select.py --meta meta.db --base base.db --output /tmp/m.json
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import urllib.request

GBD = "https://benchmark-database.de"
MANIFEST = Path(__file__).resolve().with_name("competition_manifest.json")
SEED = 131                  # fixed before the first draw (the issue number); never re-drawn for a better sample
PER_STRATUM = 4
MAX_BYTES = 25_000_000      # GBD `bytes` feature; a declared departure, sized by the CI job budget
FIRST_MAIN_YEAR = 2017      # GBD `main_YYYY`: one combined main-track instance set per competition from 2017
THRESHOLD, BAND = 4.267, 0.1
STRATA = ("tseitin", "parity", "pigeonhole", "random-3sat", "application", "other")
# Main-track strata by GBD family label. The first matching rule wins; every other
# main-track family is "other". The manifest lists every family under its stratum.
# Tseitin is its own stratum: the first draw (five strata of five, Tseitin inside
# parity) held no tseitin-formulas instance, and #131 names the family. Changed
# before any solver ran; the seed did not change.
RULES = (
    ("tseitin", r"tseitin"),
    ("parity", r"parity|xor"),
    ("pigeonhole", r"pigeon|php"),
    ("application", r"verification|model-checking|bmc|equi[v]?alence-checking|miter|cryptograph|planning|scheduling|timetabling"),
)
NOT_PARITY = {"parity-games": "games on graphs (a verification problem), not XOR constraints",
              "xor-shifting": "xorshift generator inversion (cryptanalysis), not a parity principle"}


def main_stratum(family):
    for name, pattern in RULES:
        if re.search(pattern, family) and not (name == "parity" and family in NOT_PARITY):
            return name
    return "other"


def number(value):
    return int(value) if re.fullmatch(r"[0-9]+", str(value)) else None


def load(meta, base):
    """One row per GBD hash with every track label it carries."""
    db = sqlite3.connect(f"file:{meta}?mode=ro", uri=True)
    db.execute("ATTACH DATABASE ? AS base", (f"file:{base}?mode=ro",))
    rows = {}
    for digest, family, result, track, size, variables, clauses, cls3, filename in db.execute(
            "SELECT f.hash, f.family, f.result, t.value, b.bytes, b.variables, b.clauses, b.cls3, "
            "(SELECT MIN(value) FROM filename n WHERE n.hash = f.hash) "
            "FROM features f JOIN track t ON t.hash = f.hash LEFT JOIN base.features b ON b.hash = f.hash"):
        row = rows.setdefault(digest, {"hash": digest, "family": family, "result": result, "tracks": set(),
                                       "bytes": number(size), "variables": number(variables),
                                       "clauses": number(clauses), "cls3": number(cls3), "filename": filename})
        row["tracks"].add(track)
    db.close()
    return rows


def classify(rows):
    """Assign each row to a stratum or to an exclusion reason, never to both."""
    members = {name: [] for name in STRATA}
    excluded = {}
    outside = 0
    for row in rows.values():
        years = [int(t[5:]) for t in row["tracks"] if re.fullmatch(r"main_[0-9]{4}", t)]
        main = any(year >= FIRST_MAIN_YEAR for year in years)
        random_track = any(re.fullmatch(r"random_[0-9]{4}", t) for t in row["tracks"])
        if main:
            stratum = main_stratum(row["family"])
        elif (random_track and row["family"] == "uniform-random" and row["clauses"] and row["variables"]
              and row["cls3"] == row["clauses"] and abs(row["clauses"] / row["variables"] - THRESHOLD) <= BAND):
            stratum = "random-3sat"
        else:
            outside += 1
            continue
        reason = ("missing GBD base features" if None in (row["bytes"], row["variables"], row["clauses"])
                  else f"over {MAX_BYTES} bytes" if row["bytes"] > MAX_BYTES else None)
        if reason:
            excluded.setdefault(stratum, {}).setdefault(reason, 0)
            excluded[stratum][reason] += 1
        else:
            members[stratum].append(row)
    return members, excluded, outside


def key(*parts):
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def draw(stratum, rows, seed, count):
    """Round-robin over the stratum's families (keyed order) so the sample spreads by family."""
    families = {}
    for row in rows:
        families.setdefault(row["family"], []).append(row)
    order = sorted(families, key=lambda family: key(seed, stratum, "family", family))
    queues = [sorted(families[family], key=lambda row: key(seed, stratum, family, row["hash"])) for family in order]
    chosen = []
    for depth in range(max(map(len, queues), default=0)):
        chosen += [queue[depth] for queue in queues if depth < len(queue)]
    if len(chosen) < count:
        raise ValueError(f"stratum {stratum}: {len(chosen)} eligible instances, {count} required")
    return chosen[:count]


def manifest(meta, base, sources):
    rows = load(meta, base)
    members, excluded, outside = classify(rows)
    strata = {}
    instances = []
    for stratum in STRATA:
        families = {}
        for row in members[stratum]:
            families[row["family"]] = families.get(row["family"], 0) + 1
        chosen = draw(stratum, members[stratum], SEED, PER_STRATUM)
        strata[stratum] = {"eligible": len(members[stratum]), "excluded": excluded.get(stratum, {}),
                           "selected": len(chosen), "families": dict(sorted(families.items()))}
        for row in chosen:
            instances.append({"hash": row["hash"], "stratum": stratum, "family": row["family"],
                              "gbd_result": row["result"], "tracks": sorted(row["tracks"]),
                              "bytes": row["bytes"], "variables": row["variables"],
                              "clauses": row["clauses"], "filename": row["filename"]})
    total = sum(item["eligible"] + sum(item["excluded"].values()) for item in strata.values())
    if total + outside != len(rows):
        raise ValueError(f"population accounting: {total} classified + {outside} outside != {len(rows)} rows")
    return {"schema": 1, "issue": "InauguralSystems/EigenMiniSat#131", "seed": SEED,
            "per_stratum": PER_STRATUM, "max_bytes": MAX_BYTES, "first_main_year": FIRST_MAIN_YEAR,
            "random_3sat": {"family": "uniform-random", "threshold": THRESHOLD, "band": BAND,
                            "rule": "every clause has 3 literals and |clauses/variables - threshold| <= band"},
            "rules": [list(rule) for rule in RULES], "not_parity": NOT_PARITY, "gbd": sources,
            "design_history": ["first draw (seed 131): five strata of five with Tseitin inside parity; it held no "
                               "tseitin-formulas instance, so Tseitin became its own stratum and each stratum four "
                               "instances, before any solver ran. Same seed."],
            "population": {"gbd_rows_with_a_track": len(rows), "outside_population": outside},
            "strata": strata, "instances": instances}


def fetch(name, directory):
    path = Path(directory) / f"{name}.db"
    with urllib.request.urlopen(f"{GBD}/getdatabase/{name}", timeout=300) as response, path.open("wb") as out:
        modified = response.headers.get("Last-Modified")
        while chunk := response.read(1 << 20):
            out.write(chunk)
    return path, modified


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--meta", type=Path, help="local GBD meta database (default: download)")
    parser.add_argument("--base", type=Path, help="local GBD base database (default: download)")
    parser.add_argument("--output", type=Path, default=MANIFEST)
    parser.add_argument("--check", action="store_true", help="re-derive and compare with --output")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="ems-gbd-") as scratch:
        sources = {}
        paths = {}
        for name in ("meta", "base"):
            local = getattr(args, name)
            path, modified = (local, None) if local else fetch(name, scratch)
            paths[name] = path
            sources[name] = {"url": f"{GBD}/getdatabase/{name}", "sha256": sha256(path)}
            if modified:
                sources[name]["last_modified"] = modified
        derived = manifest(paths["meta"], paths["base"], sources)
    if args.check:
        committed = json.loads(args.output.read_text())
        for name in ("meta", "base"):
            if committed["gbd"][name]["sha256"] != sources[name]["sha256"]:
                print(f"FAIL GBD {name} database differs from the one this manifest was drawn from "
                      f"({sources[name]['sha256']} != {committed['gbd'][name]['sha256']}); cannot re-derive")
                return 1
            for side in (derived, committed):  # provenance only; the SHA-256 is the identity
                side["gbd"][name].pop("last_modified", None)
        if derived != committed:
            print(f"FAIL re-derived manifest differs from {args.output}")
            return 1
        print(f"CHECK PASS {len(derived['instances'])} instances re-derived identically from seed {SEED}")
        return 0
    args.output.write_text(json.dumps(derived, indent=1) + "\n")
    print(f"WROTE {args.output}: {len(derived['instances'])} instances, "
          + ", ".join(f"{name}={item['selected']}/{item['eligible']}" for name, item in derived["strata"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

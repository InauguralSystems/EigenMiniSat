#!/usr/bin/env python3
"""Seeded, stratified SAT Competition sample from the Global Benchmark Database (#131).

Two committed artifacts:
- competition_frame.json, the FROZEN sampling frame: each stratum's eligible pool
  ([GBD hash, GBD result, GBD bytes] per family) and its exclusion counts, built
  once from GBD's own `meta` and `base` databases, whose SHA-256, Last-Modified
  date and retrieval time it records;
- competition_manifest.json, the sample: the seeded draw from that frame.

  python3 benchmarks/competition_select.py --check      # re-derive the manifest from the frame (offline)
  python3 benchmarks/competition_select.py --refresh    # rebuild frame and manifest from GBD (downloads)
  python3 benchmarks/competition_select.py --check-frame    # rebuild the frame from the archived databases
  python3 benchmarks/competition_select.py --check-frame --meta meta.db --base base.db

Instances are never committed: competition_run.py downloads each one by its GBD
hash and re-derives that hash from the downloaded bytes.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import urllib.request

GBD = "https://benchmark-database.de"
# Durable copies of the GBD databases a frame was built from, keyed by SHA-256, so
# --check-frame still runs after GBD replaces its live databases.
ARCHIVE = "https://github.com/InauguralSystems/EigenMiniSat/releases/download/gbd-databases/{name}-{sha256}.db"
FRAME = Path(__file__).resolve().with_name("competition_frame.json")
MANIFEST = Path(__file__).resolve().with_name("competition_manifest.json")
SEED = 131                  # fixed before the first draw (the issue number); never re-drawn for a better sample
PER_STRATUM = 4
MAX_BYTES = 25_000_000      # GBD `bytes` feature; a declared departure, sized by the CI job budget
FIRST_MAIN_YEAR = 2017      # GBD `main_YYYY`: one combined main-track instance set per competition from 2017
THRESHOLD, BAND = 4.267, 0.1
STRATA = ("tseitin", "parity", "pigeonhole", "random-3sat", "application", "other")
RESULTS = ("sat", "unsat", "unknown")
# Main-track strata by GBD family label. The first matching rule wins; every other
# main-track family is "other". The frame lists every family under its stratum.
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
# Families whose label does not name their structure, placed by what they encode.
# This map is consulted before RULES.
STRUCTURE = {
    "genurq": ["tseitin", "generalized Urquhart formulas: Tseitin parity constraints on random regular graphs"],
    "lights-out": ["parity", "the Lights Out puzzle: a linear system over GF(2)"],
    "mutilated-chessboard": ["pigeonhole", "domino tiling of a mutilated board: a matching (counting) principle"],
    "perfect-matching": ["pigeonhole", "the perfect matching principle on odd vertex sets: a counting principle"],
    "subset-cardinality": ["pigeonhole", "subset cardinality formulas (Miksa and Nordstrom): a counting principle"],
}
DESIGN_HISTORY = ["first draw (seed 131): five strata of five with Tseitin inside parity; it held no "
                  "tseitin-formulas instance, so Tseitin became its own stratum and each stratum four "
                  "instances, before any solver ran. Same seed.",
                  "second change, before the first dispatched measurement: the label rules had put genurq "
                  "(Tseitin on expanders), mutilated-chessboard and perfect-matching (matching principles) into "
                  "other. The STRUCTURE map now places five families by what they encode; the tseitin, parity "
                  "and pigeonhole pools grew, and their draws were re-derived with the same seed."]


def main_stratum(family):
    if family in STRUCTURE:
        return STRUCTURE[family][0]
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
    for digest, family, result, track, size, variables, clauses, cls3 in db.execute(
            "SELECT f.hash, f.family, f.result, t.value, b.bytes, b.variables, b.clauses, b.cls3 "
            "FROM features f JOIN track t ON t.hash = f.hash LEFT JOIN base.features b ON b.hash = f.hash"):
        row = rows.setdefault(digest, {"hash": digest, "family": family, "result": result, "tracks": set(),
                                       "bytes": number(size), "variables": number(variables),
                                       "clauses": number(clauses), "cls3": number(cls3)})
        row["tracks"].add(track)
    db.close()
    return rows


def classify(rows):
    """Assign each row to a stratum or to an exclusion reason, never to both."""
    members = {name: [] for name in STRATA}
    excluded = {}
    families = {name: {} for name in STRATA}
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
        count = families[stratum].setdefault(row["family"], {"eligible": 0, "excluded": 0})
        count["excluded" if reason else "eligible"] += 1
        if reason:
            excluded.setdefault(stratum, {}).setdefault(reason, 0)
            excluded[stratum][reason] += 1
        else:
            members[stratum].append(row)
    return members, excluded, families, outside


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


def build_frame(meta, base, sources):
    rows = load(meta, base)
    members, excluded, families, outside = classify(rows)
    strata = {}
    for stratum in STRATA:
        pool = {}
        for row in sorted(members[stratum], key=lambda row: row["hash"]):
            pool.setdefault(row["family"], []).append([row["hash"], row["result"], row["bytes"]])
        strata[stratum] = {"excluded": excluded.get(stratum, {}),
                           "families": dict(sorted(families[stratum].items())),
                           "pool": dict(sorted(pool.items()))}
    frame = {"schema": 1, "issue": "InauguralSystems/EigenMiniSat#131", "seed": SEED, "per_stratum": PER_STRATUM,
             "max_bytes": MAX_BYTES, "first_main_year": FIRST_MAIN_YEAR,
             "random_3sat": {"family": "uniform-random", "threshold": THRESHOLD, "band": BAND,
                             "rule": "every clause has 3 literals and |clauses/variables - threshold| <= band"},
             "rules": [list(rule) for rule in RULES], "not_parity": NOT_PARITY, "structure": STRUCTURE,
             "gbd": sources,
             "design_history": DESIGN_HISTORY,
             "population": {"gbd_rows_with_a_track": len(rows), "outside_population": outside},
             "strata": strata}
    validate_frame(frame)
    return frame


def validate_frame(frame):
    """The frame's own accounting: every pool row is unique, well formed and counted."""
    seen = set()
    classified = 0
    for stratum, item in frame["strata"].items():
        if set(item["pool"]) - set(item["families"]):
            raise ValueError(f"frame stratum {stratum}: pool family missing from its family counts")
        for family, count in item["families"].items():
            pool = item["pool"].get(family, [])
            if count["eligible"] != len(pool):
                raise ValueError(f"frame {stratum}/{family}: {len(pool)} pool rows, {count['eligible']} eligible counted")
            for digest, result, size in pool:
                if not re.fullmatch(r"[0-9a-f]{32}", digest) or digest in seen:
                    raise ValueError(f"frame {stratum}/{family}: malformed or repeated hash {digest!r}")
                if result not in RESULTS or not isinstance(size, int) or not 0 < size <= frame["max_bytes"]:
                    raise ValueError(f"frame {stratum}/{family}/{digest}: result {result!r} or size {size!r} out of range")
                seen.add(digest)
        excluded = sum(count["excluded"] for count in item["families"].values())
        if excluded != sum(item["excluded"].values()):
            raise ValueError(f"frame stratum {stratum}: family exclusions {excluded} != {sum(item['excluded'].values())}")
        classified += sum(count["eligible"] + count["excluded"] for count in item["families"].values())
    population = frame["population"]
    if classified + population["outside_population"] != population["gbd_rows_with_a_track"]:
        raise ValueError(f"frame accounting: {classified} classified + {population['outside_population']} outside "
                         f"!= {population['gbd_rows_with_a_track']} GBD rows")


def load_frame(path=FRAME):
    frame = json.loads(Path(path).read_text())
    validate_frame(frame)
    return frame


def derive_manifest(frame):
    """The sample is a pure function of the frozen frame."""
    strata = {}
    instances = []
    for stratum, item in frame["strata"].items():
        rows = [{"hash": digest, "family": family, "result": result, "bytes": size}
                for family, pool in item["pool"].items() for digest, result, size in pool]
        chosen = draw(stratum, rows, frame["seed"], frame["per_stratum"])
        strata[stratum] = {"eligible": len(rows), "excluded": item["excluded"], "selected": len(chosen),
                           "families": item["families"]}
        instances += [{"hash": row["hash"], "stratum": stratum, "family": row["family"],
                       "gbd_result": row["result"], "bytes": row["bytes"]} for row in chosen]
    design = ("schema", "issue", "seed", "per_stratum", "max_bytes", "first_main_year", "random_3sat",
              "rules", "not_parity", "structure", "gbd", "design_history", "population")
    return {**{name: frame[name] for name in design}, "frame": FRAME.name, "strata": strata, "instances": instances}


def dump_frame(frame):
    """Readable but compact: one pool row per line."""
    text = json.dumps(frame, indent=1)
    return re.sub(r'\[\s+("[0-9a-f]{32}"),\s+("[a-z]+"),\s+([0-9]+)\s+\]', r"[\1, \2, \3]", text) + "\n"


def fetch(name, directory):
    path = Path(directory) / f"{name}.db"
    with urllib.request.urlopen(f"{GBD}/getdatabase/{name}", timeout=300) as response, path.open("wb") as out:
        modified = response.headers.get("Last-Modified")
        while chunk := response.read(1 << 20):
            out.write(chunk)
    return path, modified


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch_archived(name, recorded, directory):
    """The archived copy of a database the frame records, checked against its SHA-256."""
    path = Path(directory) / f"{name}.db"
    try:
        with urllib.request.urlopen(recorded["archive"], timeout=300) as response, path.open("wb") as out:
            while chunk := response.read(1 << 20):
                out.write(chunk)
    except OSError as error:  # urllib's HTTPError and URLError are OSErrors
        raise ValueError(f"cannot fetch the archived {name} database {recorded['archive']}: {error}") from error
    if sha256(path) != recorded["sha256"]:
        raise ValueError(f"archived {name} database {recorded['archive']} does not hash to {recorded['sha256']}")
    return path


def sources_from(args, scratch, known=None):
    """Provenance of the databases used. A local file with the SHA-256 a frame already
    records keeps that frame's retrieval record: same bytes, same provenance."""
    sources, paths = {}, {}
    for name in ("meta", "base"):
        local = getattr(args, name)
        if local:
            path, modified = local, None
            retrieved = datetime.datetime.fromtimestamp(Path(local).stat().st_mtime, datetime.timezone.utc)
        else:
            path, modified = fetch(name, scratch)
            retrieved = datetime.datetime.now(datetime.timezone.utc)
        paths[name] = path
        digest = sha256(path)
        sources[name] = {"url": f"{GBD}/getdatabase/{name}", "sha256": digest,
                         "retrieved_utc": retrieved.strftime("%Y-%m-%dT%H:%M:%SZ")}
        if modified:
            sources[name]["last_modified"] = modified
        if known and known[name]["sha256"] == digest:
            sources[name] = {key: value for key, value in known[name].items() if key != "archive"}
        sources[name]["archive"] = ARCHIVE.format(name=name, sha256=digest)
    return sources, paths


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="re-derive the manifest from the frame (the default)")
    mode.add_argument("--refresh", action="store_true", help="rebuild the frame and the manifest from GBD")
    mode.add_argument("--check-frame", action="store_true",
                      help="rebuild the frame from the archived databases (or --meta/--base) and compare")
    parser.add_argument("--meta", type=Path, help="local GBD meta database (default: download)")
    parser.add_argument("--base", type=Path, help="local GBD base database (default: download)")
    parser.add_argument("--frame", type=Path, default=FRAME)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args(argv)
    if not (args.refresh or args.check_frame):
        try:
            derived = derive_manifest(load_frame(args.frame))
            committed = json.loads(args.manifest.read_text())
        except (OSError, ValueError, KeyError) as error:
            print(f"FAIL {error}")
            return 1
        if derived != committed:
            print(f"FAIL {args.manifest} is not the draw re-derived from {args.frame}")
            return 1
        print(f"CHECK PASS {len(derived['instances'])} instances re-derived identically from the frozen frame "
              f"(seed {derived['seed']}, {sum(item['eligible'] for item in derived['strata'].values())} eligible)")
        return 0
    try:
        return rebuild(args)
    except (OSError, ValueError, KeyError, sqlite3.Error) as error:
        print(f"FAIL {error}")
        return 1


def rebuild(args):
    """--check-frame and --refresh: both start from the GBD databases."""
    with tempfile.TemporaryDirectory(prefix="ems-gbd-") as scratch:
        if args.check_frame:
            committed = load_frame(args.frame)
            if args.meta or args.base:
                sources, paths = sources_from(args, scratch)
            else:
                paths = {name: fetch_archived(name, committed["gbd"][name], scratch) for name in ("meta", "base")}
                sources = committed["gbd"]
            for name in ("meta", "base"):
                if committed["gbd"][name]["sha256"] != sources[name]["sha256"]:
                    print(f"FAIL GBD {name} database differs from the one the frame was built from "
                          f"({sources[name]['sha256']} != {committed['gbd'][name]['sha256']}); cannot re-verify")
                    return 1
            rebuilt = build_frame(paths["meta"], paths["base"], committed["gbd"])
            if rebuilt != committed:
                print(f"FAIL {args.frame} differs from the frame rebuilt from the recorded GBD databases")
                return 1
            print(f"CHECK-FRAME PASS {args.frame} rebuilt identically from the recorded GBD databases")
            return 0
        known = json.loads(args.frame.read_text())["gbd"] if args.frame.exists() else None
        sources, paths = sources_from(args, scratch, known)
        frame = build_frame(paths["meta"], paths["base"], sources)
    args.frame.write_text(dump_frame(frame))
    manifest = derive_manifest(frame)
    args.manifest.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"WROTE {args.frame} and {args.manifest}: {len(manifest['instances'])} instances, "
          + ", ".join(f"{name}={item['selected']}/{item['eligible']}" for name, item in manifest["strata"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

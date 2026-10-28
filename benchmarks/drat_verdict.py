#!/usr/bin/env python3
"""The repository-wide interpretation of a drat-trim result.

Verification requires both exit status zero and exactly one ``s VERIFIED``
status line.  Lines are split on CR as well as LF because drat-trim uses both.
"""
import re
import sys
from pathlib import Path


def classify(returncode, output):
    """Return (verified, reason); never infer a verdict from status alone."""
    lines = [line.strip() for line in re.split(rb"[\r\n]", output) if line.strip()]
    statuses = [line for line in lines if line.startswith(b"s ")]
    if returncode == 0 and statuses == [b"s VERIFIED"]:
        return True, "VERIFIED"
    if any(b"MEMOUT" in line for line in lines):
        return False, "MEMOUT"
    if b"s TIMEOUT" in statuses:
        return False, "TIMEOUT"
    if b"s NOT VERIFIED" in statuses:
        return False, "NOT VERIFIED"
    if not statuses:
        return False, "missing verdict line"
    if statuses.count(b"s VERIFIED") != 1 or len(statuses) != 1:
        return False, "ambiguous verdict lines: " + repr([x.decode(errors="replace") for x in statuses])
    return False, f"VERIFIED with nonzero exit status {returncode}"


def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: drat_verdict.py RETURN_CODE OUTPUT_FILE")
    verified, reason = classify(int(argv[1]), Path(argv[2]).read_bytes())
    print(reason)
    return 0 if verified else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

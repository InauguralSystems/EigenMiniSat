#!/usr/bin/env python3
"""Post-condition for shared DIMACS preparation (stdlib only, no solver oracle).

Only comments, blank lines, within-line whitespace and the SATLIB tail may disappear.
Token grouping on each remaining data line is preserved.
Unused declared variables, empty clauses, and clauses spanning lines are legal.
"""
import re
import sys
import subprocess
from pathlib import Path


def formula(path, trailer):
    records = []
    tail = zero = False
    # Match EMS's LF-delimited records; CR remains within-line whitespace.
    for line in Path(path).read_bytes().split(b'\n'):
        fields = line.split()
        if tail:
            if not fields:
                continue
            if fields == [b'0'] and not zero:
                zero = True
                continue
            raise ValueError('unsupported data after SATLIB trailer')
        if trailer and fields == [b'%']:
            tail = True
        elif fields and fields[0] != b'c':
            records.append(tuple(fields))
    tokens = [token for record in records for token in record]
    if len(tokens) < 4 or tokens[:2] != [b'p', b'cnf']:
        raise ValueError('missing DIMACS header')
    if len(records[0]) != 4:
        raise ValueError('DIMACS header must occupy its own four-token line')
    if any(not re.fullmatch(rb'[0-9]+', t) for t in tokens[2:4]):
        raise ValueError('invalid DIMACS header counts')
    variables, declared = map(int, tokens[2:4])
    clauses = 0
    pending = False
    for token in tokens[4:]:
        if not re.fullmatch(rb'-?[0-9]+', token):
            raise ValueError('non-integer clause token')
        value = int(token)
        if abs(value) > variables:
            raise ValueError('literal exceeds declared variable bound')
        pending = value != 0
        clauses += value == 0
    if pending:
        raise ValueError('unterminated clause')
    if clauses != declared:
        raise ValueError(f'clause count declared={declared} actual={clauses}')
    return records


def compare(source, prepared):
    for label, path, tail in [('source', source, True), ('prepared', prepared, False)]:
        try:
            value = formula(path, tail)
        except (OSError, ValueError) as error:
            raise ValueError(f'{label}: {error}') from error
        if label == 'source':
            original = value
        elif original != value:
            # Deliberately fixed evidence: no filenames guessed from a failing parser.
            raise ValueError('ordered DIMACS token lines changed during shared preparation')


def main():
    if sys.argv[1:] == ['--selftest']:
        return subprocess.call(['bash', str(Path(__file__).with_name('run_native_oracle.sh')),
                                '--selftest-case', 'normalization-corruption', '--aot', 'off'])
    try:
        compare(*sys.argv[1:])
    except ValueError as error:
        print(error)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

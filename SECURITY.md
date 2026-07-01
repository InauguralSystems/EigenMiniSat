# Security Policy

`EigenMiniSat` is a pure-EigenScript SAT solver and benchmark suite. It opens no
network sockets. Its one real input surface is the DIMACS `.cnf` files it parses,
so malformed-input handling in the DIMACS parser is the part most worth a report.
The attack surface is small, but reports are welcome.

## Reporting a vulnerability

Please report security issues privately rather than in a public issue — via
[GitHub private vulnerability reporting](https://github.com/InauguralSystems/EigenMiniSat/security/advisories/new)
or by contacting the maintainer at the address on the
[InauguralSystems](https://github.com/InauguralSystems) profile
(`contact@inauguralsystems.com`, subject prefix `[SECURITY]`). Include steps to
reproduce and the affected EigenScript version.

## Scope

- The DIMACS `.cnf` parser's handling of malformed or adversarial input is the
  primary in-scope concern for this repo.
- Issues in the EigenScript interpreter, runtime, or observer predicates belong
  in the [EigenScript](https://github.com/InauguralSystems/EigenScript)
  repository, which has its own security process.
- EigenMiniSat's own scope is the `.eigs` solver/benchmark code and its fixtures.

## Supported versions

The latest tag on `main` is supported. EigenMiniSat runs against the EigenScript
interpreter; run against a current EigenScript release or newer.

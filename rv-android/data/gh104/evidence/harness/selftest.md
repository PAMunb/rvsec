# Differential harness — self-test

`jca` against a synthetic mutant of `jca`, written into scratch by
`scripts/gh104_diff_harness.py --selftest` and never committed. One authored
mutation per verdict the classifier must produce, so a single run covers all four
and the direction of every difference is known before the run rather than after.

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant` (scratch)
- traces replayed: 159

## Mutations

- **introduced** — MessageDigestSpec: the commented-out g4 report at :57-58 is revived, so a bare getInstance("MD5") is accused where the seed accuses only the call that consumes it
- **moved** — TrustManagerFactorySpec: g3 loops at start, so the accusation lands on init
- **removed** — IvParameterSpecSpec: c3's condition is closed off, so the branch never fires
- **unchanged** — KeyStoreSpec and every other file: not mutated

## Verdict counts

- `introduced`: 2
- `moved`: 7
- `removed`: 3
- `unchanged`: 147

## Traces that differ

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `IvChainJunctionSpec-decrypt.txt` | removed | c3:?, c3:? | — |
| `IvChainJunctionSpec-unprepared.txt` | removed | c3:?, c3:? | — |
| `IvParameterSpecSpec-unrandomised.txt` | removed | c3:?, c3:? | — |
| `MessageDigestSpec-md5-only.txt` | introduced | — | g4:? |
| `MessageDigestSpec-md5.txt` | moved | update:?, update:? | g4:?, update:? |
| `MessageDigestSpec-sha1.txt` | moved | update:?, update:? | g4:?, update:? |
| `MessageDigestSpec-unlisted-only.txt` | introduced | — | g4:? |
| `SecretKeySpec-hardcoded-iv.txt` | moved | c3:?, c3:?, c3:?, c3:? | c3:?, c3:? |
| `TrustManagerFactorySpec-x509.txt` | moved | g3:?, init:? | init:?, init:? |
| `d15-MessageDigestSpec-md5.txt` | moved | update:?, update:? | g4:?, update:? |
| `d15-MessageDigestSpec-sha1-alias.txt` | moved | update:?, update:? | g4:?, update:? |
| `d15-MessageDigestSpec-sha1.txt` | moved | update:?, update:? | g4:?, update:? |

## Self-contradicting envelopes

None. On the frozen `jca` every guard-on-field site reports the same field it guards, so the envelope reads `but found .` rather than a value inside its own expected list; the flag fires once E1 makes the message report the object's algorithm, and goes to zero again when E4 task 8.16 moves the guard with it.

# Differential harness — self-test

`jca` against a synthetic mutant of `jca`, written into scratch by
`scripts/gh104_diff_harness.py --selftest` and never committed. One authored
mutation per verdict the classifier must produce, so a single run covers all four
and the direction of every difference is known before the run rather than after.

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant` (scratch)
- traces replayed: 57

## Mutations

- **introduced** — MessageDigestSpec: the commented-out g4 report at :57-58 is revived, so a bare getInstance("MD5") is accused where the seed accuses only the call that consumes it
- **moved** — TrustManagerFactorySpec: g3 loops at start, so the accusation lands on init
- **removed** — IvParameterSpecSpec: c3's condition is closed off, so the branch never fires
- **unchanged** — KeyStoreSpec and every other file: not mutated

## Verdict counts

- `introduced`: 1
- `moved`: 3
- `removed`: 1
- `unchanged`: 52

## Traces that differ

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `IvParameterSpecSpec-unrandomised.txt` | removed | IvParameterSpecSpec.c3 | — |
| `MessageDigestSpec-md5-only.txt` | introduced | — | MessageDigestSpec.g4 |
| `MessageDigestSpec-md5.txt` | moved | MessageDigestSpec.update | MessageDigestSpec.g4, MessageDigestSpec.update |
| `MessageDigestSpec-sha1.txt` | moved | MessageDigestSpec.update | MessageDigestSpec.g4, MessageDigestSpec.update |
| `TrustManagerFactorySpec-x509.txt` | moved | TrustManagerFactorySpec.g3, TrustManagerFactorySpec.init | TrustManagerFactorySpec.init |

## Self-contradicting envelopes

None. On the frozen `jca` every guard-on-field site reports the same field it guards, so the envelope reads `but found .` rather than a value inside its own expected list; the flag fires once E1 makes the message report the object's algorithm, and goes to zero again when E4 task 8.16 moves the guard with it.

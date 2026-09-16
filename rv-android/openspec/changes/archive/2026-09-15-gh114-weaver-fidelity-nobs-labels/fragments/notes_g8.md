# G8 hand-over notes

## Record reasons

Every hunk G8 changed in its seven files is of one of the two kinds the design admits.

`message` (label code, evidence key, handler field):

- `boolean creationObserved = false;` with its comment, `creationObserved = true;` as the first
  statement of each creation event, and the `@fail` split into `-ORDER-01` / `-ORDER-00`
  (`IvParameterSpec`, `GCMParameterSpecSpec`, `PBEKeySpecSpec`, `SecureRandomSpec`, `CipherSpec`,
  `MacSpec`);
- in `CipherSpec` and `MacSpec` also `boolean operationFinished` / `boolean reuseObserved` with
  their comment, `operationFinished = true;` in each final-operation event, and the third `@fail`
  branch `-ORDER-02` (`reuse-after-final`);
- `Evidence.keysFor(<bound>)` appended to every `-NOBS-` envelope;
- the comment rewrites `CipherSpec.mop` above the `fsm` (the refused re-`init` at `end` is now
  reported as CIPHER-ORDER-02; the sentence about a future divergence row was dropped because it
  described a transition nobody adds) and `MacSpec.mop` above the `ere` (a paragraph saying a
  re-`init` after a final is reported as MAC-ORDER-02); the cascade paragraph of
  `IvChainJunction.mop` above `use` (the second report of an unprepared spec is the
  `upstream-refused` code when the spec is marked); `IvParameterSpec.mop` line reference to
  `IvChainJunction.mop:166`.

`predicate-store` (upstream mark):

- producers: `IvParameterSpec.c1`, `.c2` (local `reported`), `GCMParameterSpecSpec.c1`, `.c2`
  and `PBEKeySpecSpec.c1` (`else` branch of the existing `conforms`, which in these three bodies
  is false exactly when the body reported);
- consumers: `IvChainJunction.use` (two reads, `PREPARED_IV` and `PREPARED_GCM`),
  `CipherSpec.i2`, `MacSpec.i1`.

## Creation and final-operation events

| File | Creation events | Final-operation events |
|---|---|---|
| `IvParameterSpec` | `c1`, `c2` | -- |
| `GCMParameterSpecSpec` | `c1`, `c2` | -- |
| `PBEKeySpecSpec` | `f1`, `f2`, `c1` (`c2` is bound through `target`) | -- |
| `SecureRandomSpec` | `c1`, `c2`, `g1`, `g2`, `g3`, `g4`, `g5` | -- |
| `CipherSpec` | `g1`, `g2`, `g3` | `wkb1`, `f1`, `f2`, `f3`, `f5`, `f6`, `f7` (every event whose transition enters `end`) |
| `MacSpec` | `g1`, `g2`, `g3` | `f1`, `f1Input`, `f2` (the three finals of the `ere`) |
| `IvChainJunction` | no `@fail` | -- |

## Census (G13c, `test_gh105_predicate_gates.py`, `predicate_graph.csv`)

New `REPORTED_UPSTREAM` sites in G8's files: 5 `ensure` (`IvParameterSpec` c1, c2;
`GCMParameterSpecSpec` c1, c2; `PBEKeySpecSpec` c1) and 4 `validateAny` (`IvChainJunction.use` x2,
`CipherSpec.i2`, `MacSpec.i1`). No `GENERATED_TRUST_MANAGERS` site.

## Decisions the artifacts did not settle

- `MacSpec.i2` carries the same key-origin read as `i1` (MAC-NOBS-01) and is not a consumer of the
  mark, because the specification's consumer list names only `MacSpec.i1`. It keeps `not-observed`.
- `PBEKeySpecSpec.f1`/`f2` report `FORB` on the object they produce and do not mark it: the
  producer list names only `PBEKeySpecSpec.c1`.
- `MacSpec.g2` has no refused twin, so a Mac obtained through `getInstance(unsafe, provider)` has no
  creation event and its failures are `creation-unobserved`.

## Harness replay done by G8 (informative, not the 13.5 report)

A monitor generated from G8's seven files plus the working-tree `KeyGeneratorSpec`,
`SecretKeyFactorySpec`, `SecretKeySpecSpec`, `SecretKeySpec` and `KeySpec` (G7 in progress), and
one from the same twelve files at `HEAD`, replayed 92 traces (every trace of those specs in
`data/gh104/traces` plus the four of `traces_g8/`): no trace changed its `(spec, event)` set, and
every code change maps within the family. The four `traces_g8` traces produced exactly the codes
their comments state.

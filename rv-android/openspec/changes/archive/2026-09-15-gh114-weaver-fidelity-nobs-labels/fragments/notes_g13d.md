# G13d hand-over notes (task 13.6)

Refused two-argument creation twins and the `creation-refused` label in `CipherSpec`, `MacSpec`,
`MessageDigestSpec`, `KeyStoreSpec`, `KeyGeneratorSpec` and `KeyManagerFactorySpec` (design D7).

## Record reasons

Every hunk is of kind `message` (label code, handler field, creation twin). None touches the
predicate store, so `predicate_graph.csv` and the census pins have no reason to move.

### `CipherSpec.mop` (17 events, unchanged)

- field comment above the flags: "Three facts" became "Four facts"; `creationObserved` paragraph
  says the refused `g3` is included; new `creationRefused` paragraph (CIPHER-ORDER-03);
- `boolean creationRefused = false;` (line 122);
- `g3` widened from `getInstance(String)` / `args(transformation)` to
  `getInstance(String, ..)` / `args(transformation, ..)`, negated guard kept; new comment
  paragraph; body gains `creationRefused = true;` (event at line 151);
- `@fail`: new branch `else if (creationRefused)` → `CIPHER-ORDER-03` (anchor line 564), between
  `-ORDER-01` and `-ORDER-02`.
- `fsm` unchanged (`start`/`unsafeAlg` keep `g3 -> unsafeAlg`, lines 481 and 486).

### `MacSpec.mop` (12 → 13 events)

- field comment: "Three facts" became "Four facts"; `creationObserved` paragraph lists `g1` to
  `g4`; new `creationRefused` paragraph (MAC-ORDER-03);
- `boolean creationRefused = false;` (line 106);
- `g3` body gains `creationRefused = true;`;
- new event `g4` (line 151): `call(public static Mac Mac.getInstance(String, Object+)) &&
  args(alg, provider) && condition(!ConscryptAliasTable.matches("Mac", alg, safeAlgorithms))`,
  body `creationObserved = true; creationRefused = true;`;
- comment above the `ere`: first sentence covers `g3` and `g4` and names MAC-ORDER-03 instead of
  MAC-ORDER-00 as the code of a run that only asks for unsafe algorithms;
- `ere` (line 523): `((g3 | g4)* g1 | (g3 | g4)* g2) (i1 | i2) (f1Input | ((update | updateBytes | updateRange | updateBuffer)+ (f1 | f1Input | f2)))`
  (was `(g3* g1 | g3* g2) …`);
- `@fail`: new branch `else if (creationRefused)` → `MAC-ORDER-03` (anchor line 542), between
  `-ORDER-01` and `-ORDER-02`.

### `MessageDigestSpec.mop` (8 → 9 events)

- `creationObserved` comment rewritten (five creation events, the refused `g4` and `g5`); new
  commented `boolean creationRefused = false;` (line 56);
- comment above `g1`: the `GENERATED_MESSAGE_DIGEST` write excludes `g4` and `g5`;
- `g4` body gains `creationRefused = true;` (its ALG-02 report unchanged);
- new event `g5` (line 136): `call(public static MessageDigest MessageDigest.getInstance(String, Object+))
  && args(alg, provider) && condition(!ConscryptAliasTable.matches("MessageDigest", alg, algorithms))`,
  body `creationObserved = true; creationRefused = true;` (no report);
- `ere` (line 229): `((g4 | g5)* g1 | (g4 | g5)* g2 | (g4 | g5)* g3) (d2 | (update+ (d1 | d2 | d3)))+`;
- `@fail`: new branch → `MESSAGEDIGEST-ORDER-02` (anchor line 237).

### `KeyStoreSpec.mop` (8 → 9 events)

- header comment: "the two `getInstance` events" became "the four";
- `creationObserved` comment rewritten; new commented `boolean creationRefused = false;`
  (line 73), which states that a refused store never read by `getKey` has this code as its only
  report;
- `g2` body gains `creationRefused = true;`;
- `g3` comment: the event-count sentence now reads "declares 9 of the 17"; the last paragraph
  says a refused two-argument type runs `g4`;
- new event `g4` (line 121): `call(public static KeyStore KeyStore.getInstance(String, Object+))
  && args(ksType, provider) && condition(!ConscryptAliasTable.matches("KeyStore", ksType, types))`;
- `ere` (line 157): `((g2 | g4)* (g1 | g3) load (((ge1 gk1) | gk1) | (se1 store))*)+`;
- `@fail`: new branch → `KEYSTORE-ORDER-02` (anchor line 165);
- `@match` comment: the routes to the handler are `g1 load` or `g3 load`; `g2` or `g4` sends
  `load` to `fail`.

### `KeyGeneratorSpec.mop` (8 → 9 events)

- `generatedKeyAlgorithm` comment: prefix written `(g3 | g4)*`;
- `creationObserved` comment (four events, the refused `g3` and `g4`); new commented
  `boolean creationRefused = false;` (line 69);
- `g3` body gains `creationRefused = true;` (its `currentAlgorithmInstance` write unchanged);
- new event `g4` (line 113): `call(public static KeyGenerator KeyGenerator.getInstance(String, Object+))
  && args(alg, provider) && condition(!ConscryptAliasTable.matches("KeyGenerator", alg, safeAlgorithms))`,
  body `creationObserved = true; creationRefused = true;` — it does not write
  `currentAlgorithmInstance`;
- `ere` (line 208): `((g3 | g4)* g1+ | (g3 | g4)* g2+) (((init | initRandom | initRandomSize | initRandomSpec) gk1) | gk1)`;
- `@fail`: new branch → `KEYGENERATOR-ORDER-02` (anchor line 216).

### `KeyManagerFactorySpec.mop` (5 → 6 events)

- `creationObserved` comment (`g1` to `g4`); new commented `boolean creationRefused = false;`
  (line 55);
- `g3` body gains `creationRefused = true;`;
- new event `g4` (line 92): `call(public static KeyManagerFactory KeyManagerFactory.getInstance(String, ..))
  && args(alg, *) && condition(!ConscryptAliasTable.matches("KeyManagerFactory", alg, safeAlgorithms))`;
- `init` comment: "this file declares five events" became "six events";
- `fsm`: `g4 -> unsafeAlg` added in `start` (line 222) and `unsafeAlg` (line 228), after each
  `g3 -> unsafeAlg`;
- comment above `@fail`: one sentence on `creation-refused`;
- `@fail`: new branch → `KEYMANAGERFACTORY-ORDER-02` (anchor line 254).

## Codes and anchors

New codes (all `InvalidSequenceOfMethodCalls`, `ORDER`, `@fail`, label `creation-refused`):
`CIPHER-ORDER-03`, `MAC-ORDER-03`, `MESSAGEDIGEST-ORDER-02`, `KEYSTORE-ORDER-02`,
`KEYGENERATOR-ORDER-02`, `KEYMANAGERFACTORY-ORDER-02`. The numbers are the next free `-ORDER-`
number of each spec in `codes.csv` at HEAD.

Anchors were measured with a script over the edited files (line of `new ErrorDescription(` whose
envelope carries the code). Against HEAD every one of the 48 existing rows of the six specs matched
`codes.csv`; after the edits all 48 moved, and `codes_g13d.csv` lists them with the new anchor and
the other columns unchanged, plus the 6 new rows (54 rows).

## Verification

- Event counts (`grep -cE '^\s*event '`): CipherSpec 17, MacSpec 13, MessageDigestSpec 9,
  KeyStoreSpec 9, KeyGeneratorSpec 9, KeyManagerFactorySpec 6.
- `rv-monitor-generator generate` over a scratch copy of the whole set (G13e's files as they stood
  in the working tree at copy time included): all 47 `.rvm`, the aspect and
  `MultiSpec_1RuntimeMonitor.java` were generated and the pipeline logged "completed successfully".
  The command exits 1 only because `--summary` raises `'int' object is not subscriptable` in
  `rv_monitor_generator/__main__.py` while printing the summary (`summary['aspectj_files']['count']`
  on an int) — a defect of the summary printer, not of the specifications. No file landed in the
  real `jca_android/` directory.
- Generated monitor: pointcuts and dispatchers exist for `MacSpec_g4`, `MessageDigestSpec_g5`,
  `KeyStoreSpec_g4`, `KeyGeneratorSpec_g4`, `KeyManagerFactorySpec_g4`; the aspect's
  `CipherSpec_g3` pointcut is `call(public static Cipher Cipher.getInstance(String, ..)) &&
  args(transformation, ..)`; each of the six `@fail` handlers contains the `else if (creationRefused)`
  branch in the order `-01`, refused, (`-02` reuse,) `-00`.

## Not settled by the artifacts (for 13.8 / 13.10 / 13.11)

- **Alphabet maps.** The new events `MacSpec.g4`, `MessageDigestSpec.g5`, `KeyStoreSpec.g4`,
  `KeyGeneratorSpec.g4` and `KeyManagerFactorySpec.g4` have no row in
  `data/jca_android/order_alphabet_map_expert.csv` (nor in `order_alphabet_map.csv`). By the
  reading of the existing one-argument twins they are `order-unmapped` (a call rejected on a
  CONSTRAINTS clause has no ORDER symbol). The `CipherSpec.g3` row's reason says "over the same
  `getInstance(String)` call as g1"; `g3` now also covers the call of `g2`. G-ORDER may report the
  new events as unmapped until those rows exist.
- **`NEW_SPEC_CONVENTIONS.md` §5** (`:221-224`) still says a creation route guarded by a
  `condition(...)` that rejects the call runs no body and reads `creation-unobserved`, and that a
  refused creation followed by use is a `sequence` failure; after 13.6/13.7 that is
  `creation-refused`. Task 13.8 owns the label table of that file.
- **Trace harness and the widened `CipherSpec.g3`.** The harness resolver accepts any call from the
  first wildcard of a `call(...)` signature onward; for `getInstance(String, ..)` that is the
  intended "both overloads", but no trace yet exercises a refused two-argument `Cipher.getInstance`
  (13.8 lists one).
- **`CipherSpec`: a refused two-argument `getInstance` now fires `g3` where previously no event
  fired.** The first use still fails at the same event (`unsafeAlg` has no use transition, as the
  state 0 row has none), so no site should change; 13.9's same-sites comparison is where that is
  confirmed.
- **Stale comment not touched:** `MacSpec.mop:60-64` ("This one is assigned by the three
  `getInstance` events and read by nothing") names no field that exists; it predates this task and
  is outside its hunks.

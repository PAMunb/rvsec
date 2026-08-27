# G6 — Records, censuses, enforcement constants

Two slices. The M1 slice is coupled to the first new spec (same commit — otherwise CI breaks); the
M2 slice is a batched correction pass over records whose claims were verified this session.

## 6.1 [M1] Enumeration constants (design D-23; same commit as the first new spec of G2)

| Enforcement point | Today | Change |
|---|---|---|
| `rvsec-crysl` `Corpora.java:28` (`new Corpus("jca_android", 24)`) | 24 | 24 + landed specs (runs in CI) |
| `MopLiftCorpusTest.java:118,129` | 215 | 215 + landed specs (runs in CI) |
| `MopLiftCorpusTest.java:143` (`assertEquals(907, total.events())`) | 907 | re-measured — **R2 alone moves it, so G1 owes a re-pin too** |
| `MopLiftCorpusTest.java:144` (`assertEquals(381, total.parameters())`) | 381 | re-measured |
| `MopLiftCorpusTest.java:196` (`assertEquals(907, checked)`, one provenance check per event) | 907 | re-measured, same number as `:143` |
| `MopLiftCorpusTest.java:276,277` (42 refusing files / 56 `OverlappingDispatch` refusals) | 42 / 56 | re-measure: a new spec with an overlapping dispatch moves them |
| `MopLiftCorpusTest.java:122,134` (`@DisplayName` literals) | 215 / 907 / 381 | cosmetic but stale — move with their assertions |
| `CalibrationTargets.java:69` (string `"215 files, 215 ok, 0 fail"`) | 215 | updated literal (MAIN code of rvsec-crysl-core) |
| `CalibrationTargets.java:70` (per-corpus list, `"jca_android 24/24"`) | 24 | updated literal, same commit as `:69` |
| `tests/parity/test_gh105_predicate_gates.py:1868` (G-PARAM `len(result.passed) == 24`) | 24 | new count, over the 0.3 `.rvm`-preserving fixture |
| `tests/parity` G-ORDER skip-set pin `:2287` (`{RandomStringPassword, IvChainJunction}`) | 2 names | unchanged IF 6.2 maps every new spec; otherwise the declared-skip set grows and the `MAP_HEADER` prose moves with it |

Update per milestone (G2 lands → constants move once; G3/G4 land → move again). Keep each move in
the same commit as the specs it counts.

## 6.2 [M1] Alphabet-map chain for new specs

`scripts/gh105_expert_alphabet.py --emit map` + `--emit delta` + `--check` (byte-for-byte
reproduction) after each spec group, so G-ORDER compares every new automaton against its rule's
ORDER instead of skipping. The R2 `initError2` mapping rides this task too: it goes to **`init2`'s symbol** (`i4` in
`order_alphabet_map.csv`, `i2` in `order_alphabet_map_expert.csv`), the way `initError` goes to
`init1`'s — each accuser stands for the call it guards, not for the other accuser. Mapping it to
`initError`'s own symbol would erase the wrong language.

The `next1`/`next3` item listed under 6.3 belongs here in substance, and it is **not** a stale-record
correction: the rows exist in all three maps (`order_alphabet_map.csv:150,152`,
`order_alphabet_map_expert.csv:62,64`, `order_alphabet_map_delta.csv:56,58`), all `order-unmapped`.
What is open is whether to *map* them to `Next` per `SecureRandom.crysl:32-34` — which the expert
map's own reason defers to gh105 11.5/11.6 and which changes the language G-ORDER compares. A
decision, not a repair.

## 6.3 [M2] Verified stale-record corrections (batched; every item was source-verified this session)

- `data/jca_android/README.md`: site census 115 → 125 (and the narrative "112 → 114 → 115");
  monitor line count 17,087 → current; the "**38**" predicate reads of `:105` → **36 `validate(` plus
  5 `validateAbsent(`, 41 in total** (measured — the sentence should carry both numbers, not one);
  "ten specs with allow-list" → eleven; the `in_api30_allowlist` sentence (the 4 `yes` rows are not
  the ARC4 rows); the `order_alphabet_map.csv` sentence ("nothing reads it" → "no gate reads it; the
  derivation and `--check` do") and its invariant citation (INV-INS-118 → INV-INS-138).
- `data/jca_android/constraint_table.csv`: the 4 stale `IGUAL` cells (`KeyStore.crysl:52`,
  `SSLContext.crysl:29` → MOP-MAIS-PERMISSIVO/platform-value; `GCMParameterSpec.crysl:19,:20` →
  deferred); the 3 `Cipher.crysl:115/:116/:118` rows (today `NAO-DERIVADO`) → CRYSL-NAO-IMPLEMENTADO; the `mop_line`
  pointer column resolves against the seed — rename to `seed_mop_line` or re-point (pick one,
  record it in the CSV header comment).
- `data/jca_android/predicate_graph.csv`: the `preparedPBE` "required by no rule" reason (false —
  `AlgorithmParameters.crysl:37-39` requires it; moot once 3.1 lands, but the row must not lie
  meanwhile); every reason still citing a `.cryptsl` pointer — **measured: 69 of the file's 76 rows** carry an
  explicit `<Rule>.cryptsl:NN` pointer and 70 mention api30, not the 7–8 first estimated. Size this
  task accordingly, or split it: it is a re-anchoring pass over almost the whole file, and the gh105
  conformance record's own adendum form ("kept as history, not an authority") is the precedent.
- `data/jca_android/predicate_ledger.csv`: the `SecretKeySpec` chain rows (#49/#118/#119 — the
  chain IS wired; wireable 24 → 25) and the pairing-convention fix in `gh105_expert_ledger.py`
  (pair by SPEC type, not file stem); undo the `PREDICATE_ALIASES` singular/plural fusion
  (`generatedKeyManager(s)`, `generatedTrustManager(s)` are four distinct predicates; singulars are
  `unread`).
- ~~`data/jca_android/oracle/expert_rules.sha256` recipe: pin `LC_ALL=C`~~ — **withdrawn, measured**.
  The recipe at `README.md:27` (`sha256sum $(ls *.crysl | sort) | sha256sum`) already reproduces
  `d7bcc019…` as written; adding `LC_ALL=C` yields `6d92bc6d94132ff1…` instead, because the pinned
  manifest is in the locale collation (`CertificateFactory.crysl` before
  `CertPathTrustManagerParameters.crysl`, which C ordering inverts). Pinning it would require
  re-pinning the frozen hash across the gh104/gh105 records — not a stale-record correction. Nothing
  to do here; making the recipe locale-independent is its own decision.
- Run `/rv-doc-code` is NOT needed here (CSV/MD edits); close the task with every `--check` green.

## 6.4 [M2] Sole-oracle gate extension

`scripts/gh105_sole_oracle_gate.py` today scans CSV/MD/`.mop` only; extend to `rvsec-core` Java and
amend the three stale citations that name the withdrawn api30 catalogue as living authority
(`ConscryptAliasTable.java:11`, `:297`, `eh/ErrorType.java:16` — sentence emendation, no behavior
change). Reactor build + tests after.

**Blocked on a researcher decision before the extension is written** (design Open Questions): the
conformance component of `rvsec-crysl` legitimately reads a different oracle — `rvsec-cognicrypt`
at `f2f4d3b`, stamped in `CalibrationTargets.java:36-37,62`, `StampedTable.java:29` and
`SourceStamp.java:11` — and a gate that scans reactor Java for oracle citations will flag those. The
difference to the pinned expert copy is one file and two lines (`Cipher.crysl:97` and `:113`, the
`CCM` entry), already an `oracle-wart` row. Either the gate exempts the component by name, or this
task shrinks to the three stale api30 citations it was written for. Do not extend the gate before
this is answered.

## 6.5 [M2, at sync] Re-derive the gh105-delta literals in the main spec

The gh105 delta (synced first — archive order) asserts "the successor set holds 24 specifications"
and "of the 35 connectable clauses, 25 are wireable — of which 24 are wired". Both are falsified by
this change. During gh109's manual `/opsx:sync` review, replace them with derived formulations
(counts by enumeration — the INV-INS-150 rule); the main spec must not keep the stale literals.

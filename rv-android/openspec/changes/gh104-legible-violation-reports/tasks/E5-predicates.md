# Group 9 — E5: predicates

Tracked checkboxes: `tasks.md` §9. After Group 8. Files: `rvsec-core` `ErrorType.java` (+ test), `jca_v2/*.mop` (predicate reads only), `jca_v2/codes.csv` (`REQ`/`FORB` rows), `data/jca_v2/predicate_omissions.csv`, `data/jca_v2/README.md`, `scripts/gh101_predicate_pairing_check.py` (parametrise by set) and its pytest.

## Subagent brief

Read `design.md` D-11 and the `instrumentation` delta `Requirement: Predicate Failure Reporting`; `data/gh101/README.md:42-61,117-120,255-317` (inventory 49 WRITE / 27 READ / 9 REMOVE on `jca`; 18 of 23 constants written-never-read; the seven terminal in both anchors: `DIGESTED`, `SIGNED`, `VERIFIED`, `WRAPPED_KEY`, `GENERATE_SSL_CONTEXT`, `GENERATE_SSL_ENGINE`, `GENERATED_KEY_PAIR`; the stale identity-keying section); `data/gh101/predicate_omissions.csv` (20 rows: 11 `constant-write-no-read`, 9 `predicate-no-constant`: `preparedAlg`, `preparedRSA`, `preparedDSA`, `generatedManagerFactoryParameters`, `preparedEC`, `preparedOAEP`, `cipheredInputStream`, `cipheredOutputStream`, `generatedMessageDigest`); gh101 D-S14. `ExecutionContext` is equality-keyed at HEAD (`e204e2a4`; `HashMap`/`HashSet` `:30-31,:81`) — do not re-key; record the eight identity-sensitive reads (D-S10 table, corrected: `SecureRandom` seeds are `byte[]`) as they stand.

## Tasks in detail

- 9.1 `ErrorType` gains `RequiredPredicate`, `ForbiddenMethod` (`rvsec-core/.../eh/ErrorType.java`, today six values `:4-9`); Java test; `codes.csv` KIND `REQ`, `FORB`.
- 9.2 For each `condition(ExecutionContext.instance().validate(...))` in `jca_v2` (grep `validate(` inside `condition(`), move the read into the body: the event transitions normally and, when the predicate is unmet, reports `RequiredPredicate` with `val` = the object's simple class and `exp` = the predicate name; co-edit the automaton so no orphan appears (G-2 stays 0); harness before/after; divergence entries.
- 9.3 For each of the nine `predicate-no-constant` omissions decide: add a producer specification (`SecretKeyFactorySpec`, `AlgorithmParametersSpec`, `*GenParameterSpecSpec`) — new `.mop` files, each with its envelope from day one — or record in `data/jca_v2/predicate_omissions.csv` with the CrySL reason (copy gh101's reason where it holds under D-10's anchor). Re-point `scripts/gh101_predicate_pairing_check.py` (parametrised `--set`) and `tests/parity/...::test_every_written_constant_is_read_or_recorded` at `jca_v2`; green.
- 9.4 `data/jca_v2/README.md`: the equality ruling, the eight reads, and that the `generatedCipher` edge (gh101 task 5.1) is not in `jca_v2` (D-1).

## Acceptance

- Pairing gate green on `jca_v2`; G-2 still 0; lint clean; every hunk recorded; harness evidence per file.
- No `condition()` in `jca_v2` reads a predicate.

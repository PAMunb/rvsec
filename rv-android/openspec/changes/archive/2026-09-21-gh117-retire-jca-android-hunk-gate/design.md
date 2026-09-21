## Context

`jca_android` was seeded byte-for-byte from the frozen `jca` (gh104), and every hunk by which it departed from the seed was enumerated in `data/jca_android/divergence_record.csv`, one row per hunk, keyed by a 12-hex sha1 of the hunk's changed lines. `scripts/gh104_divergence_record.py --check` recomputes the diff and fails both ways: a live hunk with no row is an `unrecorded divergence`, a row whose hunk no longer exists is a `stale entry`. `tests/parity/test_gh104_specset_gates.py::test_jca_android_hunks_all_recorded` runs that check, and since the cross-cutting step was added to `.github/workflows/ci.yml` it runs on every push.

gh116 rewrote the comments of all 47 specifications. A comment edit changes the digest of the hunk it falls in, so the record went stale wholesale: 227 unrecorded hunks and 168 stale entries (394 problems over 390 hunks). gh116 declared the record out of scope because it measures the set against a seed no experiment uses any more; this change turns that declaration into the spec and the tree.

The record has 382 rows. 334 carry a hunk key: 306 content hunks, 25 `new-file` rows (24 `coverage-spec`, one `junction`), one `removed-file` row (`RandomStringPassword.mop`, kind `removed-spec`) and two `platform-value` rows keyed by a hunk of `KeyStoreSpec.mop` and `SSLContextSpec.mop`. 48 rows have an empty key: `behavioural` 13, `oracle-wart` 12, `gate-scope` 7, `value-decision` 6, `spelling-variant` 5, `api30-omits` 2, `platform-value` 2, `set-archived` 1. Other gates read the record by kind and specification:

- `scripts/gh104_gates.py` — `read_records` keys every row by the stem of its `file` column; `backing_record` accepts a row of a `NARRATIVE_KINDS` kind (`api30-omits`, `platform-value`, `oracle-wart`, `spelling-variant`) as the account of a G-CONF list difference of that specification.
- `scripts/gh109_coverage_matrix.py` and `tests/parity/test_gh109_coverage_matrix.py` — join `oracle-wart` rows whose `file` names a rule path.

Separately, gh116's wave 3 re-anchored `rvsec-mop/src/main/resources/jca_android/codes.csv`. The table anchored each code at the line of the `ErrorCollector.instance().addError(` call that emits it (before gh116, `AlgorithmParameterGeneratorSpec.mop:68` for `ALGORITHMPARAMETERGENERATOR-ALG-00`, the `addError(` line; `code=` sat on :69). After gh116 every anchor names the `code=` line instead: 326 codes one line late, four two lines late. `scripts/gh104_message_gate.py`'s `code-anchor` check compares the anchor with the `addError(` line, so `test_jca_android_message_gate_is_clean` fails locally with 330 hits. CI does not see it because `_crysl()` skips the test when the pinned expert rules (`RVSec-replication-package/tools/rules`) are absent.

## Architecture

No runtime component changes. The change touches the gate layer over the specification set:

```
rvsec-mop/.../jca_android/*.mop ──┬── gh104_gates.py (G-CONF) ──reads── divergence_record.csv (narrative rows)
                                  │                                └──── conformance_record.csv
                                  ├── gh104_message_gate.py (code-anchor) ──reads── codes.csv (file_line)
                                  ├── gh109_coverage_matrix.py ──reads── divergence_record.csv (oracle-wart)
                                  └── gh104_divergence_record.py --check   ← retired, with its test
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `scripts/gh104_divergence_record.py` | per-hunk completeness against the `jca` seed | `jca/`, `jca_android/`, the record | retired (moved to `backup/gh117/`) |
| `tests/parity/test_gh104_specset_gates.py::test_jca_android_hunks_all_recorded` | CI gate of INV-INS-118 | the script's exit code | retired (the file keeps its other tests) |
| `data/jca_android/divergence_record.csv` | narrative account of the set's departures from its oracle | — | 50 rows, all with an empty `hunk` |
| `jca_android/codes.csv` | label codes and their emitting line | — | 330 `file_line` values on the `addError(` line |
| `scripts/gh104_gates.py` G-CONF | every allow-list difference is backed by a record row | monitor, expert rules, records | unchanged; re-run |
| `rvsec-crysl-core/src/test/resources/roundtrip_csv_readers.py` | manual check that the committed readers parse the CSVs the MOP–CrySL component emits | `target/emitted-csv/` | reads the emitted record with `gh104_gates.read_records` instead of the retired script's `load` |
| `scripts/gh104_message_gate.py` `code-anchor` | anchor equals emitting line | `.mop`, `codes.csv` | unchanged; re-run |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-INS-118 (restated: seed provenance, membership by count, no per-hunk record) | script and test removed; record pruned | `grep` for dangling references; `tests/` suite green |
| INV-INS-141 (restated: departures enumerated by `predicate_graph.csv`, not by hunk) | spec text | `test_gh105_*` predicate gates unchanged |
| INV-INS-109 (restated: per-hunk record binds the archived set only) | spec text | `tests/parity/test_gh101_specset_gates.py` unchanged |
| INV-INS-147 (restated without the hunk clause) | spec text | existing zero-call gate unchanged |
| Documentation Convention — anchor is the `addError(` line | `codes.csv` re-anchored | `test_jca_android_message_gate_is_clean` |
| G-CONF backed by narrative rows | record keeps the two `platform-value` rows with a blank key | `test_jca_android_allow_lists_conform_to_the_expert_rules` |
| `oracle-wart` join | record keeps all 12 `oracle-wart` rows | `tests/parity/test_gh109_coverage_matrix.py` |

## Goals / Non-Goals

**Goals:**
- The cross-cutting CI step is green.
- The gates CI skips — G-CONF and the message gate over `jca_android` — are green locally with the pinned expert rules and a generated monitor.
- No text in `openspec/specs/instrumentation/spec.md`, `data/jca_android/README.md`, `data/jca_android/NEW_SPEC_CONVENTIONS.md` or the test module docstring still requires or describes a per-hunk record for `jca_android`.

**Non-Goals:**
- Any change to a `.mop`, to `jca/`, to `CipherTransformationUtil`, or to the archived `jca_android_bug_predicate` and its `data/gh101/` records and gates.
- The other line references gh116 left stale and nobody reads at runtime (`constraint_table.csv` `mop_line`, `predicate_graph.csv`, the `Spec.mop:N` citations inside `spec.md`) — gh116 accepted them and no gate fails on them.
- Making CI able to run the gates that need the pinned expert rules. The rules live in a sibling repository; bringing them into the checkout is a separate question.

## Decisions

**D1 — Retire the gate instead of skipping it (researcher's decision).** A skip marker keeps a script and a test that nobody runs, which P3 excludes. The record's per-hunk question — how does `jca_android` differ from `jca` — has no consumer since `jca` left use; the set answers to its oracle. *Alternative:* refresh the record with `--refresh` and re-attribute 227 hunks by hand — rejected, it rebuilds an account against an instrument no experiment reads and would go stale at the next comment edit.

**D2 — Remove every keyed row except the two `platform-value` rows (researcher's decision).** A reason attached to a hunk that no longer exists reads as a reason for content it was never checked against. The two `platform-value` rows are kept with a blank key because G-CONF reads them: measured with the monitor generated from the current set and the pinned expert rules, G-CONF has 0 failures with the full record and 1 with the record cut to the 48 unkeyed rows — `KeyStoreSpec`, `KeyStore.crysl:52`, `type in {"JCEKS", "JKS", "DKS", "PKCS11", "PKCS12"}`, verdict `MOP-MAIS-PERMISSIVO`, `record: unbacked`. The `SSLContextSpec` row is kept on the same ground (same kind, same reader), without a failure to show for it. The `removed-file` row of `RandomStringPassword.mop` and the 25 `new-file` rows go with the rest: the spec states the absence of `RandomStringPassword.mop` and its reason directly, and a new specification is enumerated by the tree count, `codes.csv`, `predicate_graph.csv` and G-ORDER, not by a record row.

**D3 — Keep the `hunk` column.** It stays in the header, empty in every row. Dropping the column is a schema change for three readers to gain nothing; an empty key is already how the narrative kinds are written.

**D4 — Re-anchor from the gate's own report.** The `code-anchor` findings carry the emitting line the gate reads. `file_line` is rewritten to `<Spec>.mop:<that line>` for each finding, once, by a throwaway command in the task, not by a committed script (P1: a one-time operation). The message gate re-run is the check.

**D5 — Name the anchor in the spec.** The documentation-convention requirement said "the line each code is emitted from", and gh116 read it as the `code=` line. The requirement now names the `addError(` line — the line `code-anchor` compares.

**D6 — Track and schema.** FF SDD with `rv-sdd`: the change edits invariants and requirements of `instrumentation`, which a Quick Path plan cannot carry. Invariants live in the spec's `## Invariants` list, not in requirement blocks, so the four restated invariants are synced into the main spec by hand at archive time, as gh105 and gh109 did.

## API Design

No function signatures change. Data contracts after the change:

- `data/jca_android/divergence_record.csv` — header `file,hunk,kind,summary,reason,task`; 50 rows; `hunk` empty in every row; kinds `behavioural` 13, `oracle-wart` 12, `gate-scope` 7, `value-decision` 6, `spelling-variant` 5, `platform-value` 4, `api30-omits` 2, `set-archived` 1.
- `jca_android/codes.csv` — header unchanged; `file_line` = `<Spec>.mop:<N>` where line N holds the `ErrorCollector.instance().addError(` call whose envelope carries the row's `code`.

## Data Flow

1. Copy `scripts/gh104_divergence_record.py`, the full `divergence_record.csv` and the retired test function into `backup/gh117/`.
2. Delete the script and the test function; rewrite the test module docstring so it lists only INV-INS-128.
3. Filter the record: keep rows with an empty `hunk` and the two `platform-value` rows, blank the key of those two, write with the same header and quoting.
4. Run the message gate over `jca_android`, rewrite `file_line` from its `code-anchor` findings, re-run until zero.
5. Rewrite the spec delta into `openspec/specs/instrumentation/spec.md` at archive (requirements via `openspec archive`, invariants by hand).

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| G-CONF `unbacked` after the prune | a keyed row that backed a list difference was removed | compare G-CONF failures before and after on the same monitor | restore that row from `backup/gh117/` with a blank key |
| `code-anchor` hits after the re-anchor | a code emitted from two sites, or a finding without a parsable line | inspect the finding; fix by hand | re-run the message gate |
| monitor generation times out (`javamop -h` 10 s probe) | a cold JVM on the host | re-run; the probe passed on the second attempt during analysis | — |

## Risks / Trade-offs

- [The departure of `jca_android` from `jca` is no longer enumerable by a gate] → Accepted by decision: `jca` is out of use and the article uses `jca_android`. `git diff` between the two directories still answers the question for a reader who asks it.
- [A narrative row loses the hunk that located it in the file] → The two affected rows name their specification in `file` and describe the site in `summary`; G-CONF reads them by specification and kind, which is all it ever used.
- [The gates CI skips can break again unseen] → The tasks run them locally before the commit; the question of bringing the pinned rules into CI is left open.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Gate (CI) | cross-cutting suite | `uv run pytest tests/ -m "not (slow or online or sglang or performance or dataset)" --import-mode=importlib -o "addopts="` with `RVSEC_HOME` set | whole suite |
| Gate (local) | G-CONF, message gate, the rest of the structural gates | `uv run pytest tests/parity/test_gh104_structural_gates.py --import-mode=importlib -o "addopts="` with the pinned expert rules present | file |
| Gate (local) | coverage-matrix join | `uv run pytest tests/parity/test_gh109_coverage_matrix.py --import-mode=importlib -o "addopts="` | file |
| CI | the pushed commit | `gh run list` after push | 1 run |

## Open Questions

None.

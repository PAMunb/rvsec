# Retire the Per-Hunk Divergence Gate of `jca_android` and Re-Anchor Its Label Codes

GitHub Issue: #117

## Why

The CI pipeline has been red since the push of gh116 (`8287dc4f`, run 35518491430, 2026-09-20). The step "Run cross-cutting gates (rv-android/tests)" fails on one test, `tests/parity/test_gh104_specset_gates.py::test_jca_android_hunks_all_recorded`, the gate of INV-INS-118: `scripts/gh104_divergence_record.py --check` reports 227 unrecorded hunks and 168 stale entries across 22 specifications of `jca_android` (394 problems over 390 hunks when run locally).

The gate keys every row of `data/jca_android/divergence_record.csv` by a sha1 of the changed lines of a diff hunk between the frozen `jca` seed and `jca_android`. gh116 rewrote the comments of all 47 specifications of the set, and a comment edit changes the digest of every hunk it touches, so every such row went stale at once and every new hunk went unrecorded. gh116 took the record out of its own scope on purpose — its design states that the record compares the set with `jca`, which is no longer used, and "goes stale and is not refreshed" — but did not account for the gate running on every push. Re-keying the record by hand would mean re-attributing a reason and a task to 227 hunks whose content is comment prose, against a seed that no experiment uses any more; the question the record answered — how does `jca_android` differ from `jca`, and why — no longer has a consumer. What governs `jca_android` today is its own oracle: the pinned expert rules (G-CONF, INV-INS-125/127), the predicate graph (G-PRED2), the label-code table and the message gate.

Running the gates locally, with the pinned expert rules present, shows a second break from the same change that CI cannot see. gh116 re-anchored the `file_line` column of `rvsec-mop/src/main/resources/jca_android/codes.csv` to the line carrying `code=` instead of the line of the `ErrorCollector.instance().addError(` call that emits the code, which is the line the message gate's `code-anchor` check compares and the convention the table followed before gh116. All 330 codes are displaced (326 by one line, four by two), and `tests/parity/test_gh104_structural_gates.py::test_jca_android_message_gate_is_clean` fails with `{'code-anchor': 330}`. CI skips that test because the pinned expert rules are not in the checkout, so the break is invisible there.

## What Changes

- **Retire the per-hunk completeness gate.** Delete `test_jca_android_hunks_all_recorded` from `tests/parity/test_gh104_specset_gates.py` and delete `scripts/gh104_divergence_record.py`, whose only gate caller is that test; the manual round-trip check of the MOP–CrySL component also imported its `load`, and is switched to `gh104_gates.read_records` (researcher's decision). Both are copied to `backup/gh117/` first (P3).
- **Prune `data/jca_android/divergence_record.csv` to its narrative rows.** Keep the 48 rows whose `hunk` column is empty — the rows G-CONF (`scripts/gh104_gates.py`) and the gh109 coverage matrix read — plus the two `platform-value` rows that carried a hunk key (`KeyStoreSpec.mop` `33b3f12ae43a`, `SSLContextSpec.mop` `bc1429e12409`), whose key is blanked. Without the `KeyStoreSpec` row, G-CONF reports `KeyStore.crysl:52` (`type in {"JCEKS", "JKS", "DKS", "PKCS11", "PKCS12"}`, `MOP-MAIS-PERMISSIVO`) as unbacked: measured with the generated monitor and the pinned expert rules, G-CONF has 0 failures with the current record and 1 with the record pruned to the 48 rows. The remaining 332 keyed rows — 306 content hunks, 25 `new-file` rows and the `removed-file` row of `RandomStringPassword.mop` — are removed, with a copy of the full record in `backup/gh117/`. The result is a 50-row record.
- **Re-anchor the 330 label codes.** Every `file_line` of `jca_android/codes.csv` names the line of the `addError(` call that emits the code.
- **Rewrite the spec text that requires per-hunk records for `jca_android`.** INV-INS-109, INV-INS-118, INV-INS-141 and INV-INS-147 are restated, and six requirements are modified. The seed provenance of `jca_android`, the freeze of `jca` and the membership-by-count clause stay; the archived set `jca_android_bug_predicate` keeps its own record `data/gh101/divergence_record.csv` and its gh101 gates, which this change does not touch.
- **Pin the anchor convention in the spec.** The documentation-convention requirement names the `addError(` line as the anchor, so the next comment review does not repeat the displacement.
- **Update the documents that describe the record**: `data/jca_android/README.md`, the module docstring of `tests/parity/test_gh104_specset_gates.py`, the docstring of `backing_record` in `scripts/gh104_gates.py` (which gave the hunk key as the reason its rows are file-level), and `data/jca_android/NEW_SPEC_CONVENTIONS.md` where it tells an author to add a `new-file` row.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `instrumentation`: the divergence record of `jca_android` no longer enumerates hunks against the `jca` seed and no gate checks it by hunk; it carries only narrative rows. The `file_line` anchor of `codes.csv` is defined as the `addError(` line. Restated invariants: INV-INS-109, INV-INS-118, INV-INS-141, INV-INS-147. Modified requirements: "Specification Set Support (FR03)", "The Java SE Specification Set Is Frozen", "Successor Specification Set `jca_android`", "Documentation Convention of the `jca_android` Specification Set", "Predicate Sites of the Frozen Seed and Their Record in the Successor Set", "Reformulated Scope of G-PRED and Retirement of `rvsec-mop-defsuses`", "Producer Specifications for Expert Rules".

## Impact

- **Modules**: none of the uv workspace modules changes. The affected files are the cross-cutting gates under `rv-android/tests/parity/`, `rv-android/scripts/`, the records under `rv-android/data/jca_android/`, and `codes.csv` in the sibling Java reactor (`rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv`). No `.mop` changes, so no generated monitor, instrumented APK or measurement changes.
- **Readers of `divergence_record.csv`**: `scripts/gh104_gates.py` (`read_records`, `backing_record`, the `NARRATIVE_KINDS`), `scripts/gh109_coverage_matrix.py` and `tests/parity/test_gh109_coverage_matrix.py` (the `oracle-wart` join). All read rows by kind and specification, never by hunk, so the pruned record serves them unchanged; G-CONF is re-run to confirm it. The manual round-trip check `rvsec/rvsec-crysl/rvsec-crysl-core/src/test/resources/roundtrip_csv_readers.py`, run by hand after `mvn -pl rvsec-crysl-core test` and by no build or CI step, re-read the record the component emits with the retired script's `load`; it reads it with `read_records` instead, staging the fixture under `<tmp>/data/emitted/` because that reader resolves `<repo>/data/<set>/`.
- **Readers of `codes.csv`**: the message gate (`scripts/gh104_message_gate.py`, `code-anchor`) and the consumers of the label codes, which read `code`, `site_kind` and `label` and not `file_line`.
- **CI**: the cross-cutting step turns green; the gates CI skips (G-CONF, message gate) are run locally, where the pinned expert rules exist.
- **FRs/NFRs**: FR03 (specification set support) — the set and its selection are unchanged; only its bookkeeping against the frozen seed is retired.

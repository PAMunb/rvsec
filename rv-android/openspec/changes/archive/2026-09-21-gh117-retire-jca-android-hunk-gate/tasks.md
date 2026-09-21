<!-- Subagent dispatch hints:
     - Groups 1, 2 and 3 share no file and can run in parallel (three subagents at once).
       Group 1: the record, the retired script and test (rv-android/scripts, tests, data, backup).
       Group 2: codes.csv in the sibling Java reactor (rvsec/rvsec-mop/.../jca_android/codes.csv).
       Group 3: the prose documents under data/jca_android/.
     - Group 4 (verification) runs after all three, in the main window.
     - Critical path: {1, 2, 3} -> 4.
     - The change touches about 8 files; the repository is shared with other sessions, so every
       commit names its paths explicitly (`git commit -- <paths>`), never `git add -A`. -->

## 1. Retire the per-hunk gate and prune the record (parallel — subagent)

- [x] 1.1 Copy `scripts/gh104_divergence_record.py` and `data/jca_android/divergence_record.csv` (all 382 rows) to `backup/gh117/`, and write the source of `test_jca_android_hunks_all_recorded` to `backup/gh117/test_jca_android_hunks_all_recorded.py`
- [x] 1.2 Delete `scripts/gh104_divergence_record.py`
- [x] 1.3 Delete `test_jca_android_hunks_all_recorded` from `tests/parity/test_gh104_specset_gates.py`; rewrite the module docstring so it lists INV-INS-128 only and says nothing of the divergence record; remove imports the file no longer uses
- [x] 1.4 Rewrite `data/jca_android/divergence_record.csv` with the same header and quoting: keep the 48 rows whose `hunk` is empty, keep the two `platform-value` rows keyed `33b3f12ae43a` (`KeyStoreSpec.mop`) and `bc1429e12409` (`SSLContextSpec.mop`) with `hunk` blanked, drop the other 332; confirm 50 rows and the kind counts of design.md "API Design"
- [x] 1.5 `git grep -n "gh104_divergence_record\|test_jca_android_hunks_all_recorded"` returns nothing outside `backup/`, `openspec/changes/`, `openspec/specs/` (INV-INS-141 is replaced by the hand-sync of task 4.7), `docs/`, `audit/`, `data/jca_android/evidence/`, `data/gh104/evidence/` and `data/gh105/evidence/` (past measurement logs)
- [x] 1.6 Run `uv run pytest tests/parity/test_gh104_specset_gates.py tests/parity/test_gh109_coverage_matrix.py --import-mode=importlib -o "addopts="` with `RVSEC_HOME` set; all pass
- [x] 1.7 Switch the manual round-trip check `rvsec/rvsec-crysl/rvsec-crysl-core/src/test/resources/roundtrip_csv_readers.py` from the retired script's `load` to `gh104_gates.read_records`, staging the emitted fixture under a temporary `<repo>/data/emitted/` (researcher's decision, found by task 1.5)
- [x] 1.8 In `scripts/gh104_gates.py`, the docstring of `backing_record` says `divergence_record.csv` has no per-clause key (its `hunk` column is empty) instead of calling it keyed by hunk (researcher's decision, found by `/rv-code-reviewer`)

## 2. Re-anchor the label codes (parallel — subagent)

- [x] 2.1 Run `uv run python scripts/gh104_message_gate.py <RVSEC_HOME>/rvsec/rvsec-mop/src/main/resources/jca_android --crysl <pinned expert rules>` and confirm 330 `code-anchor` findings and no other kind
- [x] 2.2 Rewrite `file_line` of each `jca_android/codes.csv` row named by a finding to `<Spec>.mop:<line>` from the finding (a throwaway command, not a committed script — design D4); leave every other column and row byte-unchanged
- [x] 2.3 Re-run the message gate: `counts` is `{}`

## 3. Documents that describe the record (parallel — subagent)

- [x] 3.1 `data/jca_android/README.md`: the `divergence_record.csv` row of the records table (and every passage that calls the record "one entry per hunk") describes a record of narrative rows with an empty `hunk`, read by G-CONF and the coverage matrix; no text says a gate checks it per hunk
- [x] 3.2 `data/jca_android/NEW_SPEC_CONVENTIONS.md`: remove `divergence_record.csv` from the per-group ownership table and the "A new file is one `new-file` divergence row" paragraph; keep the `oracle-wart` paragraph (narrative rows are still written); state that `file_line` in `codes.csv` names the `addError(` line
- [x] 3.3 Both documents follow P4 (current state, no history of the gate)

## 4. Verification (main window)

- [x] 4.1 Run `uv run pytest tests/ -m "not (slow or online or sglang or performance or dataset)" --import-mode=importlib --tb=short -q -rs -o "addopts="` with `RVSEC_HOME` set — the CI command of the cross-cutting step; zero failures
- [x] 4.2 Run `uv run pytest tests/parity/test_gh104_structural_gates.py --import-mode=importlib -o "addopts="` with the pinned expert rules present; G-CONF (`test_jca_android_allow_lists_conform_to_the_expert_rules`) and `test_jca_android_message_gate_is_clean` pass, and no test fails
- [x] 4.3 Run `/rv-qa-lint-fix` over the touched Python files (`tests/parity/test_gh104_specset_gates.py`)
- [x] 4.4 Invoke `/rv-code-reviewer` via Skill tool
- [x] 4.5 Commit by path with `refs #117`: the rv-android files, `backup/gh117/`, the change directory, and `rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv`
- [x] 4.6 Push and confirm the `CI Pipeline` run of the commit is green (`gh run list`)
- [x] 4.7 `/opsx:verify`, then `/opsx:archive` with the four restated invariants (INV-INS-109, 118, 141, 147) hand-synced into `openspec/specs/instrumentation/spec.md`; `grep -n "INV-INS-118" openspec/specs/instrumentation/spec.md` shows the restated text; final commit `closes #117`

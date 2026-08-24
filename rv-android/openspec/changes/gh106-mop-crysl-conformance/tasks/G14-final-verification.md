# G14 · final verification

**Depends on:** everything. **Size:** the verification sequence plus the documentation sync.

## Tasks

- [ ] 14.1 `/rv-qa-lint-fix scripts` and `/rv-qa-lint-fix tests/parity` — the Python surface this change touches.
- [ ] 14.2 `cd $W/rvsec && mvn clean install -DskipMopAgent` with JDK 21, **tests enabled** for the four new modules. Note that the reactor also builds under JDK 25; 21 is what the pom targets and what this gate uses.
- [ ] 14.3 `/rv-verify scripts` and `uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh106_retirement.py`.
- [ ] 14.4 Confirm the five surviving gates are still green, **locally**, and record the invocations — they are not run by any CI job (G13a 13a.7).
- [ ] 14.4-bis Confirm the CI step from G05 5.10 exists and that the four new modules' tests actually ran in a CI run, not only locally. Read the workflow log rather than the exit code: `-DskipTests` produces a green build with zero tests, which is the exact failure this step exists to prevent.
- [ ] 14.4-ter Confirm the oracle-dependent tests are **tagged and declaredly excluded** in CI (G05 5.11), and that the exclusion is written where a reader of the green will see it. A partial green that looks total is worse than a red.
- [ ] 14.5 Confirm the calibration gate passes at the current HEAD, and that the commit it ran at is recorded beside the commit the targets were taken at. If HEAD moved during implementation — it moved during **each** of the three preceding rounds — re-run the eight targets and record the new stamp rather than assuming they carried.
- [ ] 14.6 Invoke `/rv-code-reviewer` via the Skill tool over the full change diff.
- [ ] 14.7 `/rv-docs-sync`: update `rvsec/CLAUDE.md` (module map and reactor build order, which gains `rvsec-crysl`), `openspec/specs/README.md` (a `conformance` row in the domain table, and the `CONF` invariant abbreviation in the conventions list), and the `rvsec/rvsec-crysl/*/CLAUDE.md` module docs if the module-doc convention applies to the reactor tree.
- [ ] 14.8 Verify the cross-referencing convention end to end: `proposal.md` carries `GitHub Issue: #106`; intermediate commits use `refs #106`; the final commit uses `closes #106`; the PR body carries `Closes #106`.
- [ ] 14.9 Check off every acceptance criterion in issue #106 that is satisfied, and annotate any that a scope change superseded — an unchecked box on a closed issue reads as incomplete work.
- [ ] 14.10 Run `/opsx:verify` for the change, then `/opsx:archive` once the researcher approves.
- [ ] 14.11 Move the Kanban card to Done via `gh project item-edit` (project `PVT_kwDOAJRqj84BPHtv`, status field `PVTSSF_lADOAJRqj84BPHtvzg9n4kM`, option `53305933`). The automation does not do this.

## Closing
G14 closes when 14.1–14.11 are `[x]`, and with it the change.

# Architecture Decision Records

This directory holds Architecture Decision Records (ADRs) for the rv-android
workspace — focused notes that capture the **why** of a non-obvious technical
decision, the alternatives considered, and the consequences. ADRs document
decisions whose rationale is not derivable from reading the code alone.

## Numbering convention

Files are named `NNNN-kebab-case-title.md`, sequential, never reused.

- Numbers are assigned at acceptance time; reserve a number with a draft PR if
  you are working in parallel with someone else.
- Keep titles short and focused — one decision per ADR. If a decision splits
  in two during review, file two ADRs.

## Template

ADRs are written with `/rv-doc-adr`, from `.claude/skills/rv-doc-adr/templates/adr.md`, which
holds the section structure: metadata (Status, Date, Deciders, Supersedes), a one-paragraph
summary, context, decision drivers ranked before the options, the considered options (keeping the
current state among them) judged against those drivers, the decision, consequences and risks,
the conditions under which to revisit it, and references.

## Lifecycle

ADRs are immutable once Accepted. To amend a decision, write a new ADR with
status `Supersedes NNNN` and update the original's status to `Superseded by`.
Do not edit accepted ADRs in place — that loses the trail of why we changed
our mind. This is the documented exception to the current-state principle (P4
in the root `CLAUDE.md`): an ADR is a historical record, not a description of
the present system.

## Index

| # | Title | Status |
|---|-------|--------|
| 0001 | [Environment-variable pattern: ENV_* registry + Layer Purity](0001-env-var-pattern.md) | Accepted (gh55) |
| 0002 | [Resume path obtains static_data via on-demand JSON re-parse](0002-resume-path-static-data-reparse.md) | Accepted (gh58) |
| 0003 | [Resume path derives results_dir from logcat path; error aggregates before early return](0003-resume-results-dir-derived-from-logcat.md) | Accepted (gh65) |
| 0004 | [Generic-spec subtype target matching via FastHierarchy.canStoreType at match-time](0004-generic-subtype-target-matching-canstoretype.md) | Accepted (gh69) |
| 0005 | [Build ape-rv.jar from source inside the rvandroid image](0005-build-ape-rv-jar-from-source-in-image.md) | Accepted (gh71) |
| 0006 | [Fixed emulator execution profile: no GPU, no persisted state, cold boot per task; env-parameterized boot budget](0006-emulator-execution-profile-cold-boot-no-gpu.md) | Proposed (gh92) |
| 0007 | [Relax the "do not touch GATOR" rule for semantics-preserving performance fixes](0007-relax-gator-no-touch-rule-for-semantics-preserving-perf-fixes.md) | Proposed (gh66) |
| 0008 | [Separate stateful diagnostic parser over a union return type](0008-separate-stateful-diagnostic-parser.md) | Accepted (gh72) |

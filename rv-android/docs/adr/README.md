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

Use `.claude/skills/rv-doc-adr/templates/adr.md` as the starting point. The
canonical sections are:

1. **Status** — Proposed | Accepted | Deprecated | Superseded by NNNN
2. **Context** — what problem prompted the decision; relevant FRs/NFRs from `docs/PRD.md`
3. **Decision** — what we decided, in normative language
4. **Alternatives considered** — concrete options, each with trade-offs that ruled it out
5. **Consequences** — positive, negative, neutral
6. **References** — proposals, change directories, code references

## Lifecycle

ADRs are immutable once Accepted. To amend a decision, write a new ADR with
status `Supersedes NNNN` and update the original's status to `Superseded by`.
Do not edit accepted ADRs in place — that loses the trail of why we changed
our mind.

## Index

| # | Title | Status |
|---|-------|--------|
| 0001 | [Environment-variable pattern: ENV_* registry + Layer Purity](0001-env-var-pattern.md) | Accepted (gh55) |
| 0002 | [Resume path obtains static_data via on-demand JSON re-parse](0002-resume-path-static-data-reparse.md) | Accepted (gh58) |
| 0003 | [Resume path derives results_dir from logcat path; error aggregates before early return](0003-resume-results-dir-derived-from-logcat.md) | Accepted (gh65) |

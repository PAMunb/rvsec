---
name: rv-doc-adr
description: >-
  Create Architecture Decision Record (ADR) for significant decisions.
  Use when making refactoring decisions, choosing technologies, or changing architecture.
  Do NOT use for: minor code changes, bug fixes, or documentation updates.
  Use /rv-doc-architecture for module docs, /rv-doc-generate-claude-md for CLAUDE.md.
argument-hint: [decision-title]
allowed-tools: Read, Grep, Glob, Write, Edit, Bash, AskUserQuestion
---

# Create ADR: $ARGUMENTS

Writes an Architecture Decision Record at `docs/adr/NNNN-<kebab-title>.md`, the single location and
numbering sequence for every ADR of the workspace (convention and index in `docs/adr/README.md`). An ADR
records one decision, the criteria it was judged by, the options weighed against those criteria,
and what was accepted in exchange — so that a reader months later can tell whether the reasons
still hold.

The skill runs in the main conversation, not in a fork: the decision, the options the user
weighed and who decided are facts only the user holds, and a forked agent cannot ask for them.

Follow `.claude/documentation-principles.md` for everything written here.

## When to Create an ADR

| Situation | ADR? |
|-----------|------|
| Major refactoring | Yes |
| New architectural pattern | Yes |
| Technology choice | Yes |
| Breaking API change | Yes |
| Bug fix, minor refactoring, formatting | No |

## Supporting Files

Read each one at the step that uses it, not all up front:

- `checklists/decision-drivers.md` — step 2, to name and rank the criteria.
- `templates/adr.md` — step 5, the single section structure of the record.
- `checklists/adr-quality.md` — step 6, the review before reporting.

## Workflow

```
1. GATHER CONTEXT     sources first, then ask the user what only they know
2. FIX CRITERIA       drivers ranked must/should/nice, before any option is judged
3. LIST OPTIONS       status quo included; each option judged against every driver
4. CHALLENGE          steelman the strongest rejected option; 1-2 pre-mortems
5. NUMBER AND WRITE   highest existing number + 1; fill templates/adr.md
6. LINK AND CHECK     architecture.md entry; quality checklist; report
```

### 1. Gather Context

Read what already exists before asking anything: the GitHub issue, the OpenSpec change under
`openspec/changes/` if there is one, the affected specs, the module's `CLAUDE.md` and
`docs/architecture.md`, and the code the decision touches. The index in
`docs/adr/README.md` shows whether this decision replaces an earlier one.

Then use `AskUserQuestion` for what the sources cannot settle: the affected module, the decision,
the options the user considered, the chosen option, who decided (`Deciders`), and whether it
replaces an earlier ADR. Never fill the chosen option or the deciders yourself. When you have a
preference of your own, put it to the user as a question; if the user adopts it, record the
deciders as "the user, on the agent's proposal".

### 2. Fix the Decision Criteria

Read `checklists/decision-drivers.md` and state the drivers, each ranked must-have, should-have
or nice-to-have, before judging any option. Criteria written after the options tend to be the
ones the preferred option happens to win; fixing them first is what keeps the record honest.
Confirm the must-haves with the user, since a must-have eliminates options outright.

### 3. List and Evaluate the Options

Include doing nothing (keeping the current state) whenever the decision changes something: it
forces the record to show that acting is better than not acting. Judge every option against every
driver from step 2. An option that fails a must-have is out; the rest are separated by the
should-haves, and nice-to-haves only break ties.

### 4. Challenge the Choice

Two short exercises, done before writing, so the record carries the objections rather than
discovering them later:

- **Steelman**: rewrite the strongest rejected option in its best form — the version a capable
  advocate would defend — and check it against the drivers again. If it now wins, stop and take
  that to the user instead of writing the ADR.
- **Pre-mortem**: write one or two narratives that start "It is six months later and this decision
  has failed." Each names a concrete trigger, a threshold or number, and the chain of effects.
  A vague "it didn't scale" is not a narrative.

What survives goes into the record: the cost the steelman exposes becomes a Negative consequence,
each plausible failure becomes a Risk with a mitigation and an early warning sign, and any
assumption a failure depends on becomes a Revisit When trigger.

### 5. Number and Write

The number is the highest existing one plus one. Counting files would reuse a number whenever the
sequence has a gap.

```bash
LAST=$(ls docs/adr | sed -n 's/^\([0-9]\{4\}\)-.*\.md$/\1/p' | sort -n | tail -1)
printf '%04d\n' $((10#${LAST:-0} + 1))   # 10# keeps 0008 from being read as octal
```

Read `templates/adr.md` and write `docs/adr/NNNN-<kebab-title>.md` from it, then add its row to
the index table of `docs/adr/README.md`. The Status is `Proposed` unless the user says the
decision is already taken. When the ADR replaces an earlier one, fill `Supersedes` here and, in the
earlier ADR, set the Status to `Superseded by NNNN` and add its `Superseded by` line, so each record
points at the other; update both rows of the index.

### 6. Link and Check

For each module the decision is scoped to, if `modules/<module>/docs/architecture.md` exists, add
an entry for the decision to its design decisions section: one paragraph with the why, ending with the path of the ADR that holds the full
option analysis. Then read `checklists/adr-quality.md` and fix every item the draft fails before
reporting.

## Rules

1. One decision per ADR.
2. Neutral comparison: every option, the rejected ones included, appears with its real strengths;
   no bias terms ("modern", "better", "elegant").
3. Criteria before options, and the decision justified only by those criteria.
4. Implementation design lives in the OpenSpec `design.md`; the ADR points to it.
5. An ADR is a historical record: it states the decision and the reasons as they stood when it was
   taken, and is the documented exception to the current-state rule (P4 in `CLAUDE.md`). Once
   Accepted, only its Status and `Superseded by` lines change. A revised decision is a new ADR that
   supersedes it; a later development is never written into the old record.

## Output

```
## Created: ADR NNNN — [title]

- **Path**: docs/adr/NNNN-[kebab-title].md
- **Index**: row added to docs/adr/README.md
- **Status**: Proposed | Accepted
- **Decision**: [one sentence]
- **Deciders**: [who]
- **Supersedes**: [NNNN, or none]
- **architecture.md**: [entry added in modules/<m>/docs/architecture.md | none]
- **Open points**: [anything the user still has to confirm]
```

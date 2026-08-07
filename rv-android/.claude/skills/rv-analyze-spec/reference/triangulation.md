# Checking the same thing from several angles

## Contents

- [Why one angle is never enough](#why-one-angle-is-never-enough)
- [The twelve angles](#the-twelve-angles)
- [Choosing angles: which ones actually disagree](#choosing-angles-which-ones-actually-disagree)
- [Four worked triangulations](#four-worked-triangulations)
- [Reading a disagreement](#reading-a-disagreement)

## Why one angle is never enough

Every artefact in this pipeline is a translation of another artefact. The `.mop` is a
translation of a CrySL rule. The `.rvm` is a translation of the `.mop`. The aspect is a
translation of the pointcuts. The monitor is a translation of the automaton. And each
translation is lossy in a way its author did not write down.

So a claim checked against exactly one of them is a claim about that artefact, not about the
system. The habit this file encodes is simple: **decide what the claim is about, then check
it from angles that would disagree if you were wrong.**

The corollary matters as much. When two angles disagree, that is not noise to be resolved by
picking the more convenient one. It is the most informative thing that will happen all day.

## The twelve angles

Ordered roughly from strongest evidence to weakest.

**1. The production source.** Open the class that does the work and cite `file:line`. A
handoff document, a report, or arithmetic done in your head is not verification. This is the
angle that tells you *why*, and it is the only one that does.

**2. A harness over the production classes.** Call the real class from a small driver and
count what it produces. Because it is the shipped code, its output is authority. `scripts/`
has two: `CoenableProbe` (drives `FSMCoenables`) and `PointcutBudget` (drives
`PointcutMatcher`). Prefer this over reasoning whenever a number is involved.

**3. The end-to-end run.** The real pipeline on real input, timed, with peak RSS. Slower than
a harness, but it is the only angle that can surprise you with a failure mode nobody
predicted — the `StackOverflowError` in a regex was found this way, and no amount of reading
`FSMCoenables` would have suggested it.

**4. The generated Java.** Read the `.rvm`, the `.aj` aspect and the `RuntimeMonitor.java`.
They routinely contradict what the `.mop` appears to say — see `generated-artifacts.md` for
the specific surprises. Cheap, and it settles most arguments about semantics.

**5. The grammar.** The parser sources (`*.jj`, and the AST classes next to them) tell you
what the notation can express at all, which is a different question from what it means. This
is how you learn that the `ere` grammar has no `?`, and that the `fsm` grammar has a
`default -> <state>` nobody uses.

**6. A second formalisation.** Rewrite the same language in another logic — `ere` against
`fsm`, or either against `ltl` — and run both. This is the sharpest instrument for separating
a property *of the language* from a property *of the notation*. If a claim is about the
language, it must survive the rewrite. If the numbers move, the claim was about the notation
all along.

**7. The history.** `git log --follow` on the specification, then extract old revisions and
run them. Old revisions are experiments someone already performed. They tell you what was
tried, and a diff across the revision where something was simplified often tells you what
wall they hit.

**8. The oracle.** For a translated specification, the source it was translated from — here,
the generated CrySL rule. When a `.mop` looks awkward, read the `.cryptsl`. Go to the oracle,
not to the translation.

**9. The real API.** `javap` over the actual `android.jar` for the API level in question. Not
the rule's event list, not the `.mop`, not memory. Overload sets are exactly the kind of thing
everyone is confident and wrong about.

**10. The existing tests and invariants.** A named invariant with a test is someone's earlier
verification, already written down. Find it, read what it actually asserts, and *run it* — a
test you have not run is a claim, not evidence.

**11. A closed form.** Derive a formula from the mechanism, then check that it predicts the
*next* measurement rather than the one you fitted it to. `n × (2ⁿ − 1)` was derived from
reading the walk, confirmed at n=17, and then used to predict n=18 before that run happened.
A formula that only explains data you already have is a description, not a check.

**12. A model or re-implementation.** Weakest, and the one most likely to mislead, because it
reproduces your understanding rather than the system. A Python re-implementation of the
coenable walk once predicted 7× growth and "slow but tractable"; it had silently omitted the
`fail` category, and the real failure was in a regex it did not model at all. Use a model to
generate a hypothesis, never to close one.

## Choosing angles: which ones actually disagree

Two angles are only worth running if they could disagree. Pick by what the claim is about.

| the claim is about… | angles that can contradict it |
|---|---|
| what a notation can express | grammar (5), production source (1) |
| what a pointcut matches | harness (2), generated aspect (4), real API (9), tests (10) |
| what a language accepts | second formalisation (6), generated monitor (4), end-to-end (3) |
| how much something costs | harness (2), end-to-end (3), closed form (11) |
| whether a defect is real | generated Java (4), harness (2), history (7) |
| whether a translation is faithful | oracle (8), real API (9), generated aspect (4) |
| why something was done this way | history (7), oracle (8) |

Note what is missing from every row: "the planning document said so". Enumerations in
artefacts are floors, not ceilings — verify counts against the material with a script, not
against the prose that motivated them.

## Four worked triangulations

**"Rewriting the automaton as an `ere` would avoid the blow-up."**
Four angles, and they had to agree before the answer was reportable. *Source* (1): `EREPlugin`
sets `logic = "fsm"` and never emits `"done"`, and `LogicPluginFactory` re-dispatches on that
— so the `ere` path ends in the `fsm` plugin. *Harness* (2): identical coenable counts,
2,228,207 on both. *Second formalisation* (6): the same language written both ways, generated
end to end, 53.55 s against 53.56 s. *End-to-end at the ceiling* (3): both fail with the same
`StackOverflowError` at 18 events. Answer: no, and the reason is structural, not incidental.

**"The 18-event version of this specification used to generate quickly."**
*History* (7) was the only angle that could settle it, and it did so by producing an artefact
to run rather than an argument: extract the old revision, feed it to the real pipeline. It
failed with `StackOverflowError` at 1 m 02 s. Cross-checked with *source history* — the two
files that impose the ceiling had never been modified since the initial commit — and with the
*diff* of the revision that followed, which fused two events into one wildcard. The old
version never generated; the current one is the workaround.

**"`Object+` in the provider position is a fidelity defect."**
*Source* (1): the matcher resolves `T+` through `InheritanceResolver`, whose `Object` fast
path accepts any non-primitive. *Tests* (10): a named invariant, INV-INS-86, asserts exactly
`getInstance(String, Object+)` against `getInstance(String, Provider)` — and running it
mattered, because a test that exists is not a test that passes. *Harness* (2): the pointcut
matches exactly the two two-argument overloads and nothing else. *Oracle* (8): the CrySL rule
writes `g2: getInstance(transformation, _)`, an anonymous argument. Four angles, one answer:
the wildcard is the faithful translation, not a defect.

**"`doFinal(..)` swallows one event and double-fires another."**
*Generated aspect* (4) showed the pointcut as woven. *Real API* (9) gave the seven overloads
that actually exist. *Harness* (2) resolved the pointcut against them and returned
`[f1, f2, f4]` — overlapping the separate `f1` event, and absorbing the rule's `f4`. A defect
that is invisible in the `.mop` and obvious the moment three angles are put side by side.

## Reading a disagreement

When two angles conflict, the resolution is almost always one of four things, and it is worth
naming which:

- **The model was incomplete.** Something real was left out. Fix the model or discard it.
- **The claim was about the notation, not the language.** A second formalisation exposes this
  immediately.
- **The artefact is stale.** The document, the handoff or the planning table describes a state
  that no longer exists. Trust the code.
- **You are measuring a different thing than you think.** The most common one. State precisely
  what each angle measured before deciding which is wrong.

A claim that survives only one angle is a hypothesis. Say so when you report it, in the same
sentence as the claim — not in a footnote.

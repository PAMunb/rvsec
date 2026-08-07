---
name: rv-analyze-spec
description: Analyze and (re)design JavaMOP .mop specifications — event alphabet, automaton, pointcuts, CrySL conformance, generator cost. Do NOT use for Python modules (use /rv-analyze-module).
argument-hint: "<spec file or specification set>"
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# Analyze a JavaMOP specification: $ARGUMENTS

## What this skill is for

A `.mop` specification looks like a small, declarative thing: a handful of events, an
automaton, two handlers. It is not. Behind it sits a code generator with a hard and
non-obvious complexity wall, an AspectJ dialect that a hand-written weaver reimplements only
in part, and — in this project — a CrySL rule that the specification is supposed to be a
faithful translation of. Those three constraints pull in different directions, and a change
that looks like a one-line improvement in one of them can make the specification stop
generating entirely.

This skill is the accumulated map of that territory. It exists so you do not rediscover, by
burning twelve minutes and twenty-seven gigabytes, that a specification with twenty-four
events cannot be built at all.

The single most important habit it encodes: **measure the tool, do not reason about it.**
Every number in the reference files was produced by running the real generator on real input
and is reproducible with the commands given here. When your model of the pipeline and the
pipeline disagree, the pipeline is right.

## The five dimensions

An honest analysis of a specification looks at five things. They are ordered by how often
they turn out to be the real problem, not by how interesting they are.

1. **Cost** — how many events does it have, and what will that cost the generator?
2. **Pointcuts** — what does each pointcut actually match, in the weaver, against the real API?
3. **Automaton** — what language does it accept, and which events have no honest home in it?
4. **Bindings** — which arguments does each event make available, and which clauses need them?
5. **Conformance** — where does it stand against the CrySL rule it came from?

You rarely need all five. Pick by the question. The sections below say when each applies.

Cutting across all of them is a practice rather than a dimension: **check every claim from
more than one angle.** Every artefact here is a lossy translation of another one, so a claim
checked against exactly one of them is a claim about that artefact, not about the system. The
angles available — production source, a harness over it, an end-to-end run, the generated
Java, the grammar, a second formalisation, the specification's own history, the CrySL oracle,
the real API from `android.jar`, the existing invariants and their tests, a closed form, and
(weakest, last) a model — are catalogued in `reference/triangulation.md`, together with which
ones can actually contradict which kind of claim. Read it before starting an investigation
that matters; it is where the method lives.

## Before anything else

Two mechanical rules, both learned the hard way.

**Copy the `.mop` to a scratch directory before running javamop.** It writes the `.rvm`
into the *source* directory, so running it in place pollutes the specification tree.

**Read the generated output before reasoning about `.mop` semantics.** The `.rvm`, the
`.aj` aspect and the `RuntimeMonitor.java` are all readable, and they routinely contradict
what the `.mop` appears to say. `reference/generated-artifacts.md` lists the specific
surprises.

Set up the working environment once:

```bash
MOP=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources     # note: nested rvsec
RULES=$WS/MetaCrySL/generated/api30                    # read-only CrySL oracle
S=<session scratchpad>                                 # never /tmp directly
AJ=$ANDROID_HOME/platforms/android-30/android.jar
```

## Dimension 1 — Cost: will it even generate?

Start here whenever a specification is slow, fails, or is about to grow. It is the cheapest
check and it is decisive more often than anything else.

Count the events:

```bash
grep -cE '^\s*event ' path/to/Spec.mop
```

Now apply the law. For any specification that has an `@fail` handler — which is nearly all
of them — the generator computes a *coenable set* for the `fail` category, and that set is
the **full powerset of the alphabet**:

```
coenable sets for `fail`  =  n × (2ⁿ − 1)      where n = number of events
```

This is not an estimate. It was verified to the unit at n=17 (2,228,207) and n=18
(4,718,574). Measured consequences on a loaded workstation:

| events | coenable sets | outcome |
|---:|---:|---|
| 14 | 229,362 | generates in **6 s**, 1.0 GB |
| 17 | 2,228,207 | generates in **53 s**, 3.3 GB |
| 18 | 4,718,574 | **`StackOverflowError`** — a regex with nested quantifiers over a 184 MB string |
| 24 | 402,653,160 | **impossible in principle** — the string exceeds Java's maximum `String` length |

**The practical ceiling is 17 events per specification.** The stack cannot be raised: the
launcher already passes `-Xss1g` and the JVM refuses to start with more on the main thread.

Note what this does *not* depend on. It does not depend on the number of states — the
minimised automaton had five states at 14, 17 and 18 events alike. It does not depend on
whether you wrote an `fsm` or an `ere`. The alphabet is the only lever.

And note the insult in it: for a single-parameter specification, that entire computation
collapses to one line in the generated monitor. See `reference/generator-pipeline.md` for
why, and for the exact code path.

If you need the count rather than the estimate, `scripts/CoenableProbe.java` runs the real
`FSMCoenables` class and reports it without generating any code.

## Dimension 2 — Pointcuts: what does this actually match?

Use this whenever an event seems to fire twice, seems not to fire, or when you are about to
split one event into several.

The weaver is not AspectJ. It is a hand-written matcher (`pointcut-engine`,
`PointcutMatcher.matchCall`) that implements a well-defined subset. What it does support is
more than people assume, and this is the key to the whole budget method:

- **Owner** — exact, or any subtype when written `T+`.
- **Method name** — exact, unless it ends in `*`, which is a prefix glob.
- **Return type** — exact, unless it is `*`. This *discriminates overloads*, and it is the
  lever that separates `byte[] doFinal(...)` from `int doFinal(...)`.
- **Parameter types** — positional. Exact descriptor equality, or subtype-aware when the
  position is written `T+`. `Object+` matches any reference type and *rejects primitives*.
- **Arity** — exact, unless the list ends in `..`, which accepts any tail.

The consequence is the load-bearing insight of this skill:

> **Overload granularity is free at weave time.** One pointcut can cover several overloads
> exactly. Therefore an event only earns a slot in the alphabet if it carries a **distinct
> binding** or a **distinct body**. Splitting purely by method signature buys nothing and
> costs a bit of the exponent.

The one thing you cannot do is bind a positional argument that some of the matched overloads
do not have. `args(mode, key, third, ..)` requires arity ≥ 3, so a two-argument overload
falls out of the automaton entirely. Fusion across arities is therefore impossible; fusion
*within* an arity, using `Object+` and an `instanceof` in the event body, is legal and cheap.

Never assert what a pointcut matches. Verify it. `scripts/PointcutBudget.java` runs the
production matcher over every overload of a real class from `android.jar` and prints the
matched set for each candidate pointcut. `reference/pointcut-semantics.md` has the recipe
and a worked example.

## Dimension 3 — Automaton: notation, and honest placement

Two facts settle most arguments here.

**The choice of notation barely affects anything.** The logic repository is a *rewriting
system*, not a set of independent back ends: `LogicPluginFactory.process` re-dispatches a
plugin's output under whatever new logic name that plugin wrote, until some plugin declares
itself terminal. Three of the ten logics — `ere`, `ltl` and `ptltl` — rewrite into `fsm`, and
`fsm` is where the enable and coenable sets are computed. So whichever of those notations you
write, you land in the same back end and pay the same `n × (2ⁿ − 1)`.

Measured on the same language written both ways: same minimised automaton, same coenable
counts, same wall-clock, same failure at the ceiling. **Choose the notation for readability.**
What would genuinely change the cost profile is a logic with a different terminal plugin
(`pda`, `srs`, `po`, `ptcaret` compute no enable sets at all) — but that changes
expressiveness and semantics, and is a design decision rather than a workaround. The full
map of which logic rewrites into which is in `reference/generator-pipeline.md`.

**The `ere` grammar has no `?` operator.** It accepts `*`, `+`, `~`, `&`, `|`, `^<digit>`,
`epsilon` and `empty`. A rule's `ORDER ge*, d?` is written `e1* (d | epsilon)`. Grammar
questions like this one are answered from the parser sources (`*.jj`), not from the
specifications that happen to exist.

For placement, the question to ask about every event is whether its row in the transition
table is all-`fail`. Every `(state, event)` pair you do not declare is sent to `fail`, and
`fail` reports a sequence violation. So an event that is declared but never placed turns a
legitimate API call into a reported misuse. Check it against the generated monitor, not
against the `.mop`.

## Dimension 4 — Bindings: what each event makes available

This is where a specification quietly loses most of its fidelity, and it is invisible in the
`.mop` because nothing looks wrong.

For each clause of the rule, write down the argument it quantifies over, and then the events
that bind that argument. That table is the **binding profile** of the specification. Two
events with the same binding profile and the same body are candidates for fusion; two events
with different profiles cannot be fused unless an `instanceof` in the body can recover the
difference.

Bindings must happen in the pointcut. The event body is compiled out of the advice into a
static method of the monitor, so `thisJoinPoint` is not available there. If a clause needs an
argument the pointcut does not bind, the clause is unreachable — no amount of body code
fixes it.

## Dimension 5 — Conformance: go to the oracle, not the translation

When a `.mop` looks awkward, read the `.cryptsl` it came from. The translation is a
secondary source and it has been wrong before.

Read the rule's `EVENTS`, its aggregates (`Inits := IWOIV | IWIV`), the `ORDER`, and then
`REQUIRES` / `ENSURES` / `NEGATES` / `CONSTRAINTS`. Two habits matter:

- **An `_` in a rule event is an anonymous argument.** `g2: getInstance(transformation, _)`
  means CrySL itself does not distinguish the overloads. A wildcard pointcut is then the
  *faithful* translation, not a divergence. Do not flag it as a defect.
- **The `ORDER` usually mentions only the aggregate.** So fusing events is lossless for the
  automaton; what fusion costs is always the bindings, never the language.

## The alphabet-budget method

This is the procedure that ties the five dimensions together. Use it whenever a
specification has to grow but cannot afford to, which — given a ceiling of 17 — is most of
the time.

1. **Count and price.** Current n, and n for the literal 1:1 transcription of the rule.
   Apply `n × (2ⁿ − 1)`. If the literal transcription exceeds 17 events, say so immediately;
   it is not a matter of patience.

2. **Get the real API.** Do not work from the rule's event list or from memory:

   ```bash
   javap -classpath $AJ javax.crypto.Cipher | grep -E 'getInstance|init|update|doFinal'
   ```

3. **Build the binding-profile table.** One row per rule event: which clauses mention it,
   which arguments they need bound. Collapse rows with identical profiles.

4. **Group by arity and propose an alphabet.** Within each arity, fuse events whose profiles
   are compatible, using `Object+` for the positions that vary and an `instanceof` in the
   body where the clause differs. Use the return type to keep unrelated overloads out.

5. **Verify every candidate against the real API.** Run `scripts/PointcutBudget.java`. Two
   properties must hold: the union covers every overload the rule names, and the candidates
   are **pairwise disjoint** (overlap is what causes an event to fire twice).

6. **Check for leakage.** Include the neighbouring methods in the fixture set — the ones with
   similar names or shapes — and confirm nothing matches them.

7. **Generate end to end and measure.** Build the `.rvm`, run rv-monitor, record wall-clock
   and peak RSS. Placeholder bodies are fine at this stage: you are validating the alphabet,
   not the specification. Say so when you report it.

`reference/crysl-to-mop.md` walks a full worked example, which took one specification from a
24-event impossible transcription to a verified 14-event alphabet that binds every argument
the rule quantifies over — under the ceiling, with three slots to spare.

## Reporting

State what you measured, with the command that produced it, and separate it from what you
inferred. When a count comes from a script, name the script. When a claim comes from reading
code, cite `file:line`. When something is a sketch you have not validated — placeholder
bodies, a fusion you did not run through the matcher — label it as a sketch in the same
sentence, not in a footnote.

Prefer a table of measurements over prose about them.

## Pitfalls this skill exists to prevent

- **Believing a model over the tool.** A Python re-implementation of the coenable walk once
  predicted 7× growth and "slow but tractable". The real answer was exponential, and the real
  failure was a stack overflow in a regex — somewhere the model never reached. The model
  became useful only after the measurement contradicted it.
- **Offering an option without checking it is expressible.** "Bind it as `Object` with no new
  events" is impossible when the overloads differ in arity. Check expressibility *before*
  putting a choice to someone.
- **Reading a fused pointcut as a translation defect.** Run `git log --follow` on the
  specification first. A fusion may be a deliberate workaround for the ceiling, introduced
  years ago by someone who hit exactly the wall you are standing in front of. It may also be
  the rule's own `_`.
- **Trusting the enumerations in planning artefacts.** They are floors, not ceilings. Verify
  counts against the material with a script, not against the prose that motivated them.
- **Assuming states are the cost.** They are not. The alphabet is.

## Bundled resources

| File | What is in it |
|---|---|
| `reference/triangulation.md` | **The method.** Twelve angles for checking a claim, which ones can contradict which kind of claim, four worked triangulations, and how to read a disagreement |
| `reference/generator-pipeline.md` | How javamop, the logic repository and rv-monitor fit together; the rewriting system that funnels `ere`, `ltl` and `ptltl` into `fsm`; the exact code path of the coenable blow-up; the measurement recipes and every reproducible number |
| `reference/pointcut-semantics.md` | The AspectJ subset the weaver implements, rule by rule, with the `file:line` seat of each; fusion patterns and their limits; a worked verification |
| `reference/generated-artifacts.md` | What the `.rvm`, the `.aj` and the `RuntimeMonitor.java` reveal, and the six things about `.mop` semantics that only the generated output tells you |
| `reference/crysl-to-mop.md` | Reading a `.cryptsl` rule; the binding-profile table; a full worked alphabet-budget example, 24 events down to 14 |
| `scripts/CoenableProbe.java` | Prices a property using the production `FSMCoenables`, in either notation, without generating code |
| `scripts/PointcutBudget.java` | Runs the production `PointcutMatcher` over a class's real overloads for each candidate pointcut; reports overlaps and unmatched members |
| `scripts/api_members.py` | Turns `javap` output into the member table `PointcutBudget` consumes |
| `scripts/README.md` | Compile and run recipes, with expected output for both harnesses |

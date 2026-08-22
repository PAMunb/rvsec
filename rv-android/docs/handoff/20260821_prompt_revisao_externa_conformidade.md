# External Review Request — MOP↔CrySL Conformance Component

**You are being asked to perform a rigorous, adversarial, multi-dimensional review of an
engineering + research plan. Nothing is to be implemented. The deliverable is a report.**

Read this whole document before touching anything. It is self-contained on *what to do*; the
material to review is on disk at the absolute paths given below.

---

## 0. Hard requirements

1. **Do not implement anything.** No production code, no edits to any file under review, no
   OpenSpec artifacts, no GitHub issues. You may write throwaway scripts and probes in a scratch
   directory, and you may *run* the existing toolchain read-only (§7 gives the commands).
2. **Use multiple subagents.** Fan out across the dimensions in §6. Each subagent must recount /
   re-derive from primary sources rather than confirming the number already printed.
3. **Use the `sequential-thinking` MCP server when it is available to you** for the synthesis and
   for the architecture-alternatives dimension (D7). If it is not available, say so in the report.
4. **Write the report to:**
   ```
   /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/analise_mop2crysl_<MODEL_NAME>.md
   ```
   Replace `<MODEL_NAME>` with your own model identifier, lowercase, no spaces
   (e.g. `analise_mop2crysl_gpt5.md`, `analise_mop2crysl_gemini3.md`, `analise_mop2crysl_grok4.md`).
   Do not overwrite another model's file.
5. **Write the report in Portuguese (Brazil) or English — your choice — but be consistent.** If you
   write Portuguese, use correct accentuation.
6. **Evidence or silence.** Every factual claim in your report carries `file:line` or a command
   transcript. Anything you could not check is listed explicitly as UNVERIFIED with the reason.
   A confident-sounding unverified claim is the single worst outcome of this review.

---

## 1. What this project is

**RVSec** is a runtime-verification framework for Android crypto-API misuse. Two specification
languages meet in it:

- **CrySL** — a declarative DSL from the CogniCrypt/CROSSING project. A `.crysl` rule states, for
  one JCA type, its `OBJECTS`, `EVENTS`, an `ORDER` (a regular expression over method-call
  aggregates), `CONSTRAINTS` (value restrictions), and `REQUIRES`/`ENSURES`/`NEGATES` predicate
  clauses. CrySL is consumed by a **static** analysis (CogniCrypt).
- **JavaMOP** — a runtime-monitoring DSL. A `.mop` spec declares parameterised monitors over
  AspectJ pointcuts, a formalism (`ere` regex or `fsm` state machine), and handlers (`@fail`,
  `@match`). JavaMOP compiles `.mop` → `.rvm` → a generated Java monitor + AspectJ aspect, which is
  woven into the app under test.

RVSec's JCA specifications were **translated by hand** from CrySL rules into JavaMOP. That
translation is unverified: nobody has mechanically checked that a `.mop` spec says what the CrySL
rule it came from demands.

**The proposed component closes that gap.** It is the object of this review.

### 1.1 The four-artifact structure — read this before judging any number

```
        R_java  ────MetaCrySL────▶  R_android          (CrySL-Rules → generated/api30)
          │                            │
    manual translation           manual translation
          ▼                            ▼
        S_java  ───gh100..105────▶  S_android          (jca → jca_android)
```

- **Vertical divergence** = translation infidelity. This is noise, and it is what the component
  measures.
- **Horizontal divergence** = Java SE → Android platform adaptation. This is deliberate and is the
  paper's contribution.

A comparator that runs `S_android` against `R_java` conflates the two and reports the deliberate
Android adaptation as infidelity. **Any critique you make must respect this axis distinction**, and
one of your jobs is to check whether the plan itself always respects it (it does not, in at least
one place — find it).

### 1.2 Current state

- The design work is finished across **four rounds** of analysis (documented, see §3).
- **Nothing is implemented.** No production code, no OpenSpec change, no GitHub issue.
- A fifth pass — an independent **consistency audit** — has just been completed and found real
  defects in the plan document. That audit is itself part of what you should review (it may be
  wrong).
- The target corpus is **moving under the plan**: an in-flight change (`gh105`, predicate wiring)
  is rewriting the Android specs right now — it went from 33/74 to 35/74 tasks *during the audit*,
  and `HEAD` moved twice. Several of the plan's tables are already stale.

---

## 2. The plan being reviewed, in one page

**Reframing.** The original request was a `.mop` → `.crysl` translator. The investigation inverted
it: **the comparison is the product; translation is the means.** Rationale: a synthesised CrySL rule
has no consumer (the originals already exist), whereas the metric determines how much translation is
even needed, and the common ground is not text but an automaton.

```
.mop     ──lift──┐
                 ├──▶ CANONICAL MODEL ──▶ compare ──▶ verdict + witness
.crysl   ─parse──┘                     └──▶ (optional) emit readable .crysl
```

A later round reopened the **`.crysl` → `.mop`** direction, which *does* have a consumer (RVSec's own
pipeline), and argues it is the stronger product of the two — without displacing the comparator,
since both share model, automaton, and validation gate.

**Four metrics**, one per CrySL section, each reporting a concrete witness rather than a bare
percentage:

| | compares | output |
|---|---|---|
| **M1** events | sets of concrete signatures | coverage + both differences |
| **M2** order | L(A_mop) vs L(A_crysl) | equivalent / more-permissive / stricter / incomparable + shortest witness |
| **M3** constraints | per variable: matched, divergent, absent, unrecognised | verdict per clause |
| **M4** predicates | `ENSURES`/`REQUIRES`/`NEGATES` graph | edges present, absent, inverted |

M2 has two legitimate variants: **M2-decl** (from the `.mop` text) and **M2-eff** (from the
*generated monitor*, i.e. what actually ran in the experiments).

**Proposed module shape** — decomposition by *technology*, not by direction, because building a
`MOPSpecFile` to hand to the writer requires the javamop types:

```
rvsec-crysl                    (parent pom; overrides guava.version, scala.version)
├── rvsec-crysl-core           canonical model · automata · M1–M4        [zero deps]
├── rvsec-crysl-mop            lift: SpecExtractor → model               [javamop]
│                              lower: model → MOPSpecFile → DumpVisitor
└── rvsec-crysl-crysl          lift: CrySLParser → model                 [CrySLParser 4.0.6]
                               lower: model → Domainmodel → CrySLSemanticSequencer
```

with **JSON as the seam**: the two readers have hostile dependency worlds (`CrySLParser` pulls Guava
33.5.0-jre; `javamop` lives in a reactor pinning Guava 19.0 for Soot), so each reader runs as its own
process and they never share a JVM.

**Claimed scientific framing** (§10.6 of the plan): a working translator is *engineering, not
contribution*; what is publishable is **translation as instrument, and the measured map of what does
not translate as the result** — a compiler that translates the translatable fragment and *explicitly
refuses* the rest, with a typed `Unknown` category and a defensible negative result.

---

## 3. Everything you must read — absolute paths

Common prefix: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`
(`/home/pedro/desenvolvimento/...` is a symlink to the same place; both work — see §8).
Below, `$W` = that prefix.

### 3.1 The plan and its evidence (primary objects of review)

| path | what it is | size |
|---|---|---|
| `$W/rvsec/rv-android/docs/20260821_conformidade_mop_crysl.md` | **THE PLAN.** 1283 lines, 13 sections. Four rounds of analysis. | 87 KB |
| `$W/rvsec/rv-android/docs/20260821_validacoes_conformidade_mop_crysl.md` | The V1–V10 validation record the plan cites as evidence | 27 KB |
| `$W/rvsec/rv-android/docs/handoff/20260821_arnes_validacoes/` | Reproducible harness for V1–V10: `v1/`…`v10/`, `crysl.json`, `mop.json`, `maps/*.map`, `m2/M2.java`, `v2/Gen.java`, `NOTAS-BRUTAS.md` | dir |
| `$W/rvsec/rv-android/docs/handoff/20260821_conformidade_mop_crysl_prompt.md` | The handoff that commissioned round four | 17 KB |
| `$W/rvsec/rv-android/docs/20260821_auditoria_conformidade_mop_crysl.md` | **The consistency audit.** 14 high-severity findings + ~30 precision findings. Review this too — it may be wrong. | 39 KB |
| `$W/rvsec/rv-android/docs/handoff/20260821_arnes_auditoria/` | The audit's own harness: three probes (A order, B verdict, C robustness) + `README.md` with reproduction commands | dir |

### 3.2 The corpora

| path | what | n |
|---|---|---|
| `$W/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/` | Android JCA specs — **the live target**, being rewritten by gh105 | 23 `.mop` |
| `$W/rvsec/rvsec/rvsec-mop/src/main/resources/jca/` | Java SE JCA specs — **frozen**, the published measurements come from here | 23 `.mop` |
| `$W/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android_bug_predicate/` | mutation variant | 23 `.mop` |
| `$W/rvsec/rvsec/rvsec-mop/src/main/resources/generic/` | generic API specs (not JCA) | 118 `.mop` |
| `$W/rvsec/rvsec/rvsec-mop/src/main/resources/generic_new/` | newer generic specs | 27 `.mop` |
| `$W/MetaCrySL/generated/api30/` | **The oracle**: CrySL rules generated for Android API 30, `.cryptsl` dialect | 33 |
| `$W/MetaCrySL/samples/jca/base/` | MetaCrySL base templates the api30 is generated from | 34 |
| `$W/rvsec-cognicrypt/CrySL-Rules/` | Original upstream CrySL rules (JCA 1.5.2) | 49 |
| `$W/MetaCrySL/src/generator/PrettyPrinter.rsc` | The Rascal generator that emits api30 | 7.8 KB |
| `$W/MetaCrySL/src/lang/crysl/ConcreteSyntax.rsc` | MetaCrySL's own CrySL grammar | 4.4 KB |

### 3.3 Hand-made mapping artifacts the component is meant to replace

All under `$W/rvsec/rv-android/data/jca_android/`:
`order_alphabet_map.csv`, `predicate_graph.csv`, `constraint_table.csv`, `divergence_record.csv`,
`conformance_record.csv`, `alias_table.csv`, `gate_allowlist.csv`, `gate_baseline.json`, `README.md`.

Plus `$W/ase-journal/docs/20260816_analise_tematica_anexos/04_assimetria_specs.md` (664 lines — the
allow-list parity table and the CogniCrypt error-type matrix).

### 3.4 Code the plan depends on

| path | why |
|---|---|
| `$W/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/` | `Property.java` (the predicate vocabulary), `ExecutionContext`, `PredicateStore` — the two substrates |
| `$W/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` | `CipherTransformationUtil`, `Api30CipherTransformationUtil`, `ConscryptAliasTable` |
| `$W/rvsec/javamop/` | The JavaMOP fork. `SpecExtractor`, `DumpVisitor` (1670 l.), `javamop.jj` grammar |
| `$W/rvsec/rv-monitor/` | Monitor generator + `rv-monitor-rt`; `plugins_logicrepository/ptltl` (the Scala module) |
| `$W/rvsec/pom.xml` | Reactor root: `java.version=21`, `scala.version=2.11.12`, `guava.version=19.0` |
| `$W/rvsec/rv-android/scripts/gh10*.py` | 18 scripts, ~10.4 kloc — the ad-hoc precursors the component subsumes. Especially `gh105_order_gate.py` (has a **known precedence bug**) |
| `$W/rvsec/rv-android/audit/20260808_validacao_jca_android/fase0/upstream_CrySL_e92f5607.xtext` | The **official** CrySL Xtext grammar, 423 lines — the ground truth for `ORDER` precedence |

### 3.5 Project conventions you must respect in any recommendation

| path | what |
|---|---|
| `$W/rvsec/rv-android/CLAUDE.md` | Development principles **P1–P4** (simplicity; human-readable docs; **no backward compatibility**; current-state comments). Non-negotiable. |
| `$W/rvsec/CLAUDE.md` | Reactor build order, the `main.basedir` mechanism |
| `$W/rvsec/rv-android/docs/WORKFLOW.md` | The OpenSpec spec-driven workflow any change must follow |
| `$W/rvsec/rv-android/docs/PRD.md` | 37 FRs, 8 NFRs |
| `$W/rvsec/rv-android/openspec/specs/README.md` | Domain-spec map |

---

## 4. What was already found — verify, do not assume

The consistency audit (§3.1) reports the following. **Treat every item as a hypothesis to check, not
as established fact.** Some may be wrong; at least one high-severity item rests on a single
execution. Say so where you disagree.

**Structural findings (high severity):**

1. **§10 has no harness.** Ten numbers (`152/167`, `22/22`, `7/22`, `11/22`, `16/55`, `47/55`,
   `87/92`, `67.6%`, `9%`, `97/97`) exist nowhere outside their own table. Three don't close
   arithmetically: `92−87=5` but the text says "4 gaps" twice; `16+47=63>55`; `67.6+9=76.6`.
2. **§12's decision undermines the whole document's denominator.** "One `CrySLModelReader` per rule"
   implies `Signature.crysl` fails to load, so the corpus is 30/33, not the 31/33 used throughout.
3. **§8 says five lexical substitutions, §12 still says four** — a validation correction applied to
   one section and not the other. §12 is the table that becomes the proposal.
4. **The `CipherSpec` witness `g1 i1 f1` is refuted by execution** (audit harness, probes A/B/C):
   `f1` and `f2` both match a bare `doFinal()`, both fire, and the trajectory FAILs in both
   declaration orders. The INCOMPARABLE verdict survives via a substitute witness that was derived
   by reading, **not executed**.
5. **§6's "the formulation to use"** — presented as revisor-proof — drops the largest of three
   debt terms: `26+19+19 = 64 ≠ 92`.
6. **Two M4 counts are not derivable** from any published artifact ("SEM-BASE 16"; the
   FIEL/PROJETADO/CONFLADO/AUSENTE classification).
7. **Three refuted counts**: `generic` multi-parameter specs are 97, not 93 (appears 3×); specs
   absorbing incorrect-use are 16/23, not 12; `Property.java` has 26 constants, not 24.
8. **The "oracle ceiling" is understated by an order of magnitude**: api30 lost 95→62 clauses across
   16 rules, not ~9 across 3.
9. **A quoted sentence attributed to the group's own TSE 2023 paper does not appear in it.**
10. **Numbers carry no commit stamp** on a corpus that gh105 moves daily; seven tables are stale.

**What held up under independent recount** (so you know where the plan is strong): the 62/55
constraint census and the entire A/B/C/D/Absent matrix; the 92 predicate clauses as 54/36/2; 32
distinct predicates, arity 59/33; denominators 73, 54, 44; 8 realized producer→consumer chains
byte-identical across both corpora; the gate's inverted precedence and the three-word table proving
it; 214/214 parse; 96→64 `DumpVisitor`; 167 events and 61 aggregates in api30; the verification of
absent Android classes against real `android.jar` for API 26/30/33/35/36.

---

## 5. The specific technical claims most worth attacking

These are load-bearing. If any is wrong, a large part of the plan changes.

1. **"The comparison is the product; translation is the means."** Is the reframing right? The
   counter-case is §10, which argues `.crysl` → `.mop` generation is the *stronger* product. Are
   these actually one component, or has the plan fused two products to justify one module?
2. **"`ORDER` comparison should be language equivalence over automata."** Is language equivalence
   the right relation? What about simulation, bisimulation, or a refinement preorder? The plan
   reports "more permissive / stricter / incomparable" — is that lattice adequate, and is
   "incomparable" actionable for a spec author?
3. **The `ORDER` precedence issue.** The official Xtext grammar makes `|` bind *tighter* than `,`.
   Two independent implementations in this repo (`gh105_order_gate.py` and MetaCrySL's
   `ConcreteSyntax.rsc`) get it backwards. Verify the grammar yourself; verify the blast radius
   claim ("exactly one of 33 rules is affected").
4. **M2-eff over M2-decl.** The plan prefers reading the *generated monitor*'s transition tables.
   Is that sound? What does it assume about the generator? The audit found `RVM_eventNames` is
   emitted by some generations and not others.
5. **The parametric-slicing normalisation (N1)** — "at most one creation event per monitor". Is this
   a general law of JavaMOP or an artifact of these specs? It was measured with probes, not on the
   corpus.
6. **`IncompleteOperationError` has no `.mop` counterpart.** The plan concedes M2 is blind to it.
   Is that a fatal limitation for a conformance claim, or an honest scope boundary?
7. **The single-parameter frontier.** CrySL names one type in `SPEC`; JavaMOP slices over a tuple.
   The plan declares out-of-scope with "typed refusal", cost 0/23 on JCA but 93 (audit says 97) of
   118 on `generic`. Is the refusal principled or is it hiding an expressiveness gap that
   invalidates the approach for the general case?
8. **JSON-as-seam / separate processes.** Elegant or overengineered? What is lost by serialising the
   automaton across a process boundary? Is there a simpler answer to the Guava conflict
   (shading? classloader isolation? just not depending on the reactor's `dependencyManagement`)?
9. **`ExecutionContext` (arity 1, boolean) vs `PredicateStore` (arity N, three-valued).** The plan
   treats the substrate as a *generator parameter*. Is the arity-2 ceiling a real limit of the
   design or of the current implementation?
10. **The scientific framing.** Is "the map of what doesn't translate" actually a publishable
    contribution, or is it a negative result dressed up? What would a hostile TSE/ICSE/ASE reviewer
    say? Note the group already published the manual translation (TSE 2023) — what genuinely new
    claim survives?

---

## 6. Verification protocol — the dimensions

Run these as **parallel subagents**, then synthesise. Each dimension produces findings classified
`CONFIRMED` / `REFUTED` / `UNVERIFIABLE`, with severity `HIGH` (changes a verdict or a number the
plan depends on) / `MEDIUM` (imprecision a reviewer would flag) / `LOW` (cosmetic).

**D1 — Factual and numerical.** Recount every quantitative claim from primary sources. Do not
confirm the printed number; derive it independently and compare. Where a denominator is not defined
in the text, say so — an underivable denominator is a finding.

**D2 — Internal coherence.** Cross-references (`§N` citations that don't contain what's attributed
to them), corrections applied to one section but not another, numbers that contradict each other
across sections, claims in the plan that the validation record contradicts.

**D3 — Architectural soundness.** Module decomposition, dependency management, the canonical model's
adequacy, the JSON seam, the round-trip gate. Does the design honour P1 (simplicity)? Is anything
speculative or built for a second use case that doesn't exist?

**D4 — Methodological validity.** *Does the measurement measure what it claims?* This is the most
important dimension. Consider: the four-artifact axis distinction (§1.1); ceiling effects (the plan
names three — subject, instrument, oracle); the `Unknown` category; whether the metrics are
comparable across corpora and over time as gh105 lands; whether any metric can be gamed by moving a
denominator.

**D5 — Feasibility and engineering risk.** Can this be built as described? Reproduce what you can
(§7). Attack the parser assumptions, the classpath semantics, the version pins. What's the riskiest
unvalidated step?

**D6 — Scientific contribution.** Is there a paper here? What is the precise claim? What is the
baseline? What would kill it in review? Is the framing of §10.6 defensible?

**D7 — Alternatives, including radical ones.** *This is explicitly invited and welcome.* Do not
limit yourself to patching the current design. If a fundamentally different architecture would be
more **effective, more ELEGANT, and more correct**, argue for it concretely — with its costs, its
migration path, and what it gives up. Candidate directions worth thinking about (not exhaustive, and
you should generate your own):
   - a single shared intermediate language both DSLs compile *into*, rather than lift-and-compare;
   - deriving the `.mop` corpus from CrySL as a build step, making conformance true by construction
     and the comparator unnecessary;
   - differential/property-based testing over generated traces instead of automaton comparison;
   - treating conformance as a refinement-checking problem with an off-the-shelf model checker;
   - encoding both sides in a theorem prover / SMT and discharging equivalence as a proof
     obligation;
   - inverting the whole thing: generate CrySL rules *from* observed runtime traces.
   For each, be honest about whether it actually fits this corpus and this team's constraints.

**D8 — Adversarial.** Actively try to break the plan. Construct the input that makes it give a wrong
answer. Find the spec, rule, or trace where the design silently reports "conforming" when it isn't,
or vice versa. Where the plan says "no-op on today's corpus", find tomorrow's corpus that breaks it.

---

## 7. Commands — verified working on this machine

**Toolchain locations** (Maven local repo is redirected; see `~/.m2/settings.xml`):
```bash
R=/home/pedro/desenvolvimento/repository
JM=$R/br/unb/cic/javamop/javamop/0.9.3-SNAPSHOT/javamop-0.9.3-SNAPSHOT.jar
AJTOOLS=$R/org/aspectj/aspectjtools/1.9.25.1/aspectjtools-1.9.25.1.jar
AJRT=$R/org/aspectj/aspectjrt/1.9.25.1/aspectjrt-1.9.25.1.jar
RT=$R/br/unb/cic/rvmonitor/rv-monitor-rt/0.9.3-SNAPSHOT/rv-monitor-rt-0.9.3-SNAPSHOT.jar
CRYSL=$R/de/darmstadt/tu/crossing/CrySL/CrySLParser/4.0.6/CrySLParser-4.0.6.jar
W=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv
```

**Build the javamop classpath** (needed to call `SpecExtractor` / `DumpVisitor`):
```bash
cd $W/rvsec/javamop && mvn -o -q dependency:build-classpath -Dmdep.outputFile=/tmp/jmcp.txt
CPM="$JM:$(cat /tmp/jmcp.txt)"
```

**Parse all 214 specs** (the plan claims 214/214, 0 failures):
```bash
java -cp "$CPM" javamop.JavaMOPMain -merge -d <outdir> <spec.mop>
```

**Generate a monitor.** ⚠️ Use the *script*, not the class — it sets `LOGICPLUGINPATH`, without
which you get the unhelpful `Logic Engine Error: null`:
```bash
$W/rvsec/rv-monitor/target/release/rv-monitor/bin/rv-monitor -merge -d <outdir> <spec.rvm>
# the main class, if you must: com.runtimeverification.rvmonitor.java.rvj.Main  (NOT rvmonitor.Main)
```

**Weave and run a probe** (JSE, no emulator):
```bash
java -cp "$AJTOOLS" org.aspectj.tools.ajc.Main -1.8 -nowarn -cp "$AJRT:$RT" -d out \
     Prog.java <Spec>RuntimeMonitor.java <Spec>MonitorAspect.aj
java -cp "out:$AJRT:$RT" Prog
```

**Reactor build** (only if you need it; JDK 21 or 25 both work despite the pom targeting 21):
```bash
cd $W/rvsec && mvn clean install -DskipMopAgent -DskipTests
```

**⛔ Never start, stop, or manage an Android emulator.** This project's `CLAUDE.md` forbids it
absolutely, in every context. Everything you need runs on the JSE.

---

## 8. Learnings and traps — paid for in wasted time

1. **`rvmonitor.Main` is not the main class.** It is
   `com.runtimeverification.rvmonitor.java.rvj.Main`, and calling it directly fails with
   `Logic Engine Error: null` because logic plugins are located via the `LOGICPLUGINPATH` env var.
   Use `bin/rv-monitor`.
2. **In an `fsm`, the acceptance handler is named after the alias.** `@match` gives
   `match is not a supported state in this logic, fsm`; the correct form is `@match1`, `@match2`, …
   In an `ere`, plain `@match` is right.
3. **`fsm` transitions need one per line.** Several on one line parses but then fails downstream.
4. **`/pedro/...` is the canonical mount** (`/dev/sda1`, ext4); `/home/pedro/desenvolvimento` is the
   symlink. **Both work from the JVM** — this was measured. An earlier note claiming `/pedro` "does
   not open in the JVM" was wrong; if you hit a path failure, suspect a container mount, not the JVM.
5. **"It parsed" is not a sanity oracle.** `jca/GCMParameterSpecSpec.mop` declares two events with
   the same id `c1` and an `ere` referencing a nonexistent `c2`. It parses, generates a monitor,
   **and compiles with 0 errors** — the `c2` vanishes from the alphabet silently. Neither the
   parser, nor the monitor generator, nor `javac` catches it.
6. **A `condition(...)` compiles to `if (!(guard)) return false;` *before* the event body and
   *before* the transition.** So a false guard removes the call from the automaton, and the *next*
   call is then accused of a sequence violation the program does not have. This drives a real design
   decision in the plan (§10.3).
7. **Two events on the same join point both fire, in declaration order.** Measured. This is the
   mechanism behind audit finding #4.
8. **The `CrySLModelReader` leaks `OBJECTS` scope between rules read by the same reader.**
   `Signature.crysl` uses undeclared `offset`/`len`: alone it fails; after `GCMParameterSpec.crysl`
   it loads. A rule's meaning depends on its company.
9. **The CrySL classpath is part of the semantics** and cannot be pinned to Android:
   `CrySLModelReaderClassPath` is strictly *additive* and `URLClassLoader` is parent-first, so the
   host JDK wins every name it has. Measured impact on this corpus: zero.
10. **The corpus moves.** gh105 is actively rewriting `jca_android`. Stamp every measurement with a
    commit hash. During the audit alone, `HEAD` moved twice and task count went 33→35 of 74.

---

## 9. Report structure

Write to `.../docs/analise_mop2crysl_<MODEL_NAME>.md`. Suggested structure — deviate if you have a
better one, but cover all of it:

1. **Verdict** — 3–5 sentences. Is the plan sound? Should it proceed as designed, proceed amended,
   or be redirected?
2. **Method** — what you actually did: how many subagents, what each verified, whether
   sequential-thinking was available, what you executed vs. read.
3. **Findings by dimension (D1–D8)** — each with evidence and severity.
4. **Audit review** — where you agree with the existing consistency audit, where you disagree, and
   what it missed.
5. **The load-bearing claims (§5)** — your verdict on each of the ten.
6. **Alternatives (D7)** — including any radical redesign you want to argue for. Be concrete:
   architecture sketch, what it costs, what it gives up, why it is more elegant.
7. **Risks, ranked** — what most likely goes wrong, and the cheapest way to find out early.
8. **Recommendations, in order of return** — separate *mechanical* fixes (unambiguous) from
   *judgement calls* (the human decides).
9. **Unverified** — everything you could not check, and why.

---

## 10. A closing note on stance

The plan's own best quality is that it repeatedly caught itself being wrong and said so in the text.
Match that stance. We are not looking for validation — we are looking for the thing that is wrong
and hasn't been found yet.

Two specific invitations:

- **Be willing to say the whole framing is off.** If the comparator is the wrong product, or the
  four metrics are the wrong four, or this should not be a Maven module at all, say it plainly and
  argue it.
- **Note the filename you are writing to says `mop2crysl`.** The plan concluded that `.mop` → CrySL
  is the *weakest* of the three products (it has no consumer) and that the comparator is the
  product, with `.crysl` → `.mop` the strongest. That the working name still encodes the rejected
  framing may be harmless, or may be a sign the reframing never fully landed. Consider which.

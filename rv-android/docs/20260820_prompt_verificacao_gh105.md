# Rigorous verification of the OpenSpec change `gh105-predicate-wiring`

**This file is an entry prompt for a fresh LLM session. Read it in full before acting.**

You are one of several independent LLMs asked to perform a **rigorous, multi-dimensional
verification** of the OpenSpec change `gh105-predicate-wiring` — its four planning artifacts
(`proposal.md`, `specs/instrumentation/spec.md`, `design.md`, `tasks.md`) — against the primary
sources: the CrySL api30 oracle, the actual specification files and Java code, the generated
monitors, the twice-audited planning document, and the contract of the predecessor change gh104.

**You MUST NOT implement anything.** Do not edit any repository file, do not create issues or
OpenSpec changes, do not modify `.mop` files, do not commit. Your only write is the report file
described in §8. This is analysis, not repair.

The domain standard applies: **JavaMOP is a formal method and everything depends on the
correctness of the specifications.** Two wiring attempts have already failed; a defect that
survives into implementation costs a third. An artifact claim that does not survive verification
must be named, with evidence, before implementation starts. Verify against the source, never
against the document that made the claim.

---

## 1. What this project is, and where we are

RVSEC does runtime verification of Android apps: JavaMOP/RV-Monitor specifications (`.mop`) are
compiled into monitors, woven into APKs, and violations are reported as one logcat line each. The
`jca_android` specification set (23 `.mop` + `codes.csv`) targets misuse of the Java Cryptography
Architecture, with `MetaCrySL/generated/api30/*.cryptsl` (33 generated CrySL rules) as its
oracle. The predecessor change **gh104** ("legible violation reports", 87/96 tasks done, Group 10
deliberately deferred) built the message envelope, the failure codes, the structural gates and a
differential trace harness — and preserved the predicate machinery byte-for-byte (gate G-PRED)
precisely so that wiring it correctly could be its own change. gh104's `design.md` D-11 names
that change explicitly. **gh105 is that change.**

What gh105 will do (when implemented — not now): wire the CrySL predicates
(`ENSURES`/`REQUIRES`/`NEGATES`) in `jca_android`. Today, against the 33 api30 rules there are
19 connectable predicates (35 connectable `REQUIRES` clauses) and the set realizes 3; all 27
predicate reads sit inside `condition(...)` where a false guard suppresses the automaton
transition and produces a wrong `InvalidSequenceOfMethodCalls`; 17 orphan accuser events sustain
49,817 events = 70.4 % of that published category; the substrate (`ExecutionContext`) keys by
`equals` while the monitors key by identity, is arity-1 where 31 of 90 clauses need arity ≥ 2,
and returns a boolean that conflates *violated* with *not observed*.

### What has been done so far (all of it is verifiable input for you)

1. **A planning document (Fase 0)** was written and then audited twice:
   - `docs/20260820_plano_fiacao_predicados.md` — the plan, ~1,230 lines, carrying audit marks
     `[auditado]` (first audit) and `[auditado-v2]` (second pass).
   - `docs/20260820_auditoria_plano_predicados.md` — first audit: 47 claims, 33 confirmed, 10
     corrected, 3 refuted.
   - `docs/20260820_verificacao_plano_predicados_v2.md` — second pass: 58 claims re-examined by
     8 parallel agents; **4 verdicts of the first audit reverted** (oracle arities are 59 unary /
     31 binary / max 2 — the "quaternary" was a splitter-counting artifact; the D1 venn is
     300/322 under the narrow reading and 255/355 under a defensible broader one — "299 was the
     ceiling" fell; the n=18 generator failure is a `StackOverflowError` in the parent's
     enable-set parser, not an OOM; "raising `-Xmx` unlocks CipherSpec" is false — 17 events
     generate under 1 GB); the IV-chain pilot was **executed** (mechanism B works on the hard
     case via the `Object` idiom; four design rules derived); the root cause of the silent
     parameter-list collapse was located (`javamop.jj:1456` vs `:1470`, silent `catch` in both
     translators). Raw evidence: `audit/20260820_verificacao_plano_predicados_v2/agent{A..I}/`.
2. **GitHub issue #105** was created (`PAMunb/rvsec`, template Feature, track Full SDD).
3. **The OpenSpec change was created and its four artifacts written** (the objects of YOUR
   verification): `openspec/changes/gh105-predicate-wiring/{proposal.md,design.md,tasks.md}` and
   `openspec/changes/gh105-predicate-wiring/specs/instrumentation/spec.md` (a delta spec with 2
   MODIFIED requirements, 6 ADDED requirements, and 16 new invariants INV-INS-130…145).
   `openspec validate gh105-predicate-wiring` passes.

### Next steps (after your verification)

The researcher ratifies the recorded decisions (D-1…D-10 in `design.md`, notably D-9 scope),
folds in whatever your verification finds, and only then starts implementation via
`/opsx:apply` (Group 1: the new predicate store in `rvsec-core`). Final validation of gh104 and
gh105 together happens in a separate joint experiment (`experimento-gh104/`) — **not now**.

---

## 2. Ground rules (non-negotiable)

1. **Read-only.** Your only write is the report file (§8). No edits to any repository file, no
   `git` state changes, no issue/change creation, no `.mop` edits.
2. **Never start, stop or manage an Android emulator**, in any context. Claims that need a
   device (e.g. `equals` of `OpenSSLRSAPublicKey`) are recorded as NOT VERIFIABLE HERE.
3. **Paths**: the alias `/pedro/...` does not resolve inside a JVM. Always use
   `/home/pedro/...` for anything that goes through Maven, JavaMOP, rv-monitor or `javap`.
4. **Trust artifacts, never exit codes.** This toolchain fails silently: JavaMOP returns rc=0
   with a success message after deleting a spec's entire parameter list, and even after hard
   pointcut parse errors; the logic-repository launcher masks a child OOM as
   `Logic Engine Error: null` with exit 0. Inspect the generated `.rvm`/monitor.
5. **Expected measurement point**: the `rvsec` reactor at commit `bd61abea`
   (`git -C /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec rev-parse --short HEAD`).
   If HEAD moved, say so prominently and re-anchor your measurements to the new HEAD.
6. **Verify against the source, not against the plan.** The plan is itself an audited document,
   but your job includes checking that the change artifacts transcribe it *and* that both match
   the primary sources. Where artifact, plan and source disagree, the source wins.
7. **Use scratch space** for any generated files (compiled specs, drivers, CSVs):
   a temporary directory of your own, never the repository tree.
8. If your environment provides the **`sequential-thinking` MCP tool**, use it for the
   multi-step reasoning chains (e.g. tracing a clause from `.cryptsl` through the delta spec's
   invariant to the task that implements it). If your environment supports **subagents /
   parallel task delegation, use several** — the dimensions in §5 are designed to run in
   parallel. If neither is available, proceed sequentially and say so in the report.

---

## 3. The objects under verification

```
openspec/changes/gh105-predicate-wiring/proposal.md
openspec/changes/gh105-predicate-wiring/specs/instrumentation/spec.md   ← the deepest artifact
openspec/changes/gh105-predicate-wiring/design.md
openspec/changes/gh105-predicate-wiring/tasks.md
```
(All paths in this file are relative to
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/`
unless written absolute.)

## 4. The sources to verify against

### The oracle (read-only)
```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30/*.cryptsl
    33 rules; expected clause census: 54 ENSURES, 36 REQUIRES, 2 NEGATES, 32 distinct predicates
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/CryptoAnalysis/
    the OLD-generation analyzer the rules belong to (checkout 349073ff):
    .../analysis/AnalysisSeedWithSpecification.java   ← doPredsMatch ~:475, trackedTypes ~:563
    .../constraints/ConstraintSolver.java             ← ImpreciseValueExtractionError :174,:484
/home/pedro/tmp/CryptSL/                              ← the CrySL Xtext grammar (Order at :99-134)
```

### The specifications and Java substrate (sibling `rvsec` tree)
```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/
    jca_android/   ← the target, 23 .mop + codes.csv
    jca/           ← FROZEN baseline (do not judge it repairable; it anchors negative fixtures)
    jca_android_bug_predicate/  ← archived failed attempt (a record, not a seed)
    generic/ (118 .mop)  generic_new/ (27 .mop)      ← genericity test bed; total universe 214 .mop
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/
    ExecutionContext.java   Property.java   eh/ErrorType.java   jca/util/…
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/javamop/       ← translator ( .mop → .rvm/.aj )
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/    ← generator + runtime lib
```

### The gh104 contract and instrument (rv-android tree)
```
openspec/changes/gh104-legible-violation-reports/{proposal.md,design.md,tasks.md,specs/}
openspec/specs/instrumentation/spec.md      ← MAIN spec the delta modifies (INV-INS-109…115 etc.)
scripts/gh104_gates.py  scripts/gh104_diff_harness.py  scripts/gh104_message_gate.py  scripts/gh104_mop_lint.py
data/jca_android/{README.md,conformance_record.csv,constraint_table.csv,divergence_record.csv,alias_table.csv,gate_allowlist.csv}
data/gh104/traces/     tests/parity/test_gh104_specset_gates.py     tests/parity/test_gh104_structural_gates.py
```

### The planning/audit chain (secondary sources — themselves already verified twice)
```
docs/20260820_plano_fiacao_predicados.md
docs/20260820_auditoria_plano_predicados.md
docs/20260820_verificacao_plano_predicados_v2.md
audit/20260820_verificacao_plano_predicados_v2/agent{A,B,C,D,E,F,H,I}/   ← raw evidence + scripts
docs/WORKFLOW.md   CLAUDE.md   docs/PRD.md
```

### Published-dataset sources (for numeric claims)
```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/
    dataset/results/errors.csv (97,018 events)      data-analysis/rvsec/rq1_rv_cc.py (the venn join, :80-145)
results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java  ← generated-monitor evidence
```

---

## 5. Verification protocol — the dimensions

Run each dimension as an independent workstream (a subagent each, if available). For **every**
checked claim produce one row: *claim → verdict → evidence (file:line or command+output) →
severity if not CONFIRMED*. Verdicts: `CONFIRMED` / `REFUTED` / `INCONSISTENT` (artifacts
disagree with each other) / `INCOMPLETE` (a gap, not an error) / `NOT VERIFIABLE HERE` (say what
would verify it). Severity: `BLOCKER` (would produce a wrong monitor/verdict or break the
freeze) / `MAJOR` (wrong number, wrong mapping, missing task) / `MINOR` (wording, traceability).

### D1 — Factual accuracy of every number and measured claim

Re-derive from source (do not copy from the plan) and compare with what the four artifacts
state. Non-exhaustive checklist of the numbers the artifacts carry: 19 connectable predicates /
35 connectable `REQUIRES` clauses (34 distinct pairs — check the `Mac.cryptsl` double
`encrypted` clause) / 44 producer→consumer edges; 54/36/2/32 oracle census; arities 59 unary,
31 binary, max 2 (verify the splitter argument on `Cipher.cryptsl` — `part(0,"/",…)` is ONE
CrySL parameter); `Property` enum = 25 values; 21 written / 4 read values; 49 write sites
(42 body / 7 `@match`) / 27 read sites (27/27 in `condition`) / 9 `remove` (8 `@fail` + 1 body,
4 using the deprecated 1-arg overload); 18 written-never-read values over 35 sites; only `MACED`
and `GENERATED_CIPHER` with zero sites; 134 `ExecutionContext` lines (= 23 import + 27 validate
+ 49 setProperty + 9 remove + 25 accepting-state + 1 comment); 17 orphans in 9 specs
(`jca_android`), 18/10 (`jca`), 0 (archived); 49,817 = 70.4 % ISoMC; `preparedEC` as the only
producerless required predicate; the two NEGATES clauses and the single correspondence
(`PBEKeySpecSpec.mop:74`); generator: `n·(2ⁿ−1)` exact, 17 events generate under `-Xmx1g`, 18 →
`StackOverflowError` in `EnableSet.parseSets` at any heap. Useful recipes are in §6.

### D2 — CrySL conformance (the heart of the verification)

Check the delta spec's semantic commitments against the api30 rules AND the old-generation
CryptoAnalysis semantics they belong to:
- Predicate matching in the oracle is **by name** (`CrySLPredicate.equals`); `REQUIRES` is
  **monotonic per object**; `NEGATES` is a **no-op** in this generation; value comparison
  happens ONLY for positions whose `OBJECTS` type is in `trackedTypes`
  (`String`/`int`/`Integer`), case-insensitively, with splitters. Does the delta spec's hybrid
  store contract (INV-INS-131) and the MODIFIED "Predicate Contract" requirement encode exactly
  this — no more, no less? Is any commitment *stronger* than the oracle without being declared
  as a deliberate strengthening?
- Walk **every one of the 35 connectable `REQUIRES` clauses** in the oracle and check that the
  change's account of them (F3 chains in `tasks.md` §5, the graph closure invariant) covers each:
  which chain/task does each clause land in? Name any clause with no home. Check the same for
  the 54 `ENSURES` (write placement) and both `NEGATES`.
- `ORDER` regularity: confirm from the Xtext grammar that `Order` is regular (sequence,
  alternative, `*`/`+`/`?`, grouping), so G-ORDER's DFA-equivalence claim is sound — and confirm
  the alphabet-mapping caveat (the `.mop` splits overloads, so no bijection) is honestly carried
  as a versioned artifact, not hand-waved.
- The three-valued verdict semantics (design.md D-4: entry+match / entry+mismatch / no entry):
  is `VIOLATED`-requires-positive-evidence consistent with the oracle's silence-in-favor-of-the-
  program behavior (`doPredsMatch` with empty extraction)? Is there a case where the store would
  say `VIOLATED` where the oracle would stay silent, or vice versa, that the artifacts fail to
  declare?
- Spot-check at least 5 rules end-to-end (recommend: `Cipher`, `SecureRandom`, `PBEKeySpec`,
  `Mac`, `SSLContext`): read the `.cryptsl`, read the current `.mop`, read what the artifacts
  promise for that pair, and judge whether an implementation following the artifacts verbatim
  would be faithful to the rule.

### D3 — Internal coherence of the four artifacts

- Every invariant INV-INS-130…145: is it implemented by at least one task and tested by at least
  one mapped test (design.md mapping table vs tasks.md)? Every task: does it trace back to a
  requirement/invariant? Name orphans in both directions.
- Do proposal, delta spec, design and tasks agree on: the mechanism partition (D-2), the
  `remove()` disposition (D-3 / INV-INS-142 / task 6.4), the *not observed* code timing
  (INV-INS-143 / task 4.2), the G-PRED rescoping choreography (INV-INS-141 / task 2.5 + 4.1
  same-commit rule), the counts (35/34, 17/9, 27, 8+1)?
- Scenario/format contract: every `#### Scenario:` uses exactly 4 hashtags; every requirement
  has ≥ 1 scenario; RFC 2119 usage; MODIFIED requirements copied faithfully from the main spec
  (compare headers and content against `openspec/specs/instrumentation/spec.md` — a partial copy
  loses detail at archive time).

### D4 — Consistency with gh104 (unarchived) and the main spec

gh104 is still an active change; its delta spec carries INV-INS-118…129. Check for collisions:
- INV-INS-128 (G-PRED byte-identity of the 134 lines in `jca_android`) is **directly
  contradicted** by gh105's migration. Does INV-INS-141's supersession-for-`jca_android` clause
  resolve it cleanly, and is the collateral list complete? Verify the collateral by reading
  `scripts/gh104_gates.py` yourself: `predicate_divergences` (~:1014-1051, wiring ~:1454-1468),
  `accept_requires` (~:1189-1191), `PREDICATE_CALL` (~:514-517) — and search for **any other**
  site in scripts/ or tests/parity/ that greps `ExecutionContext`, `setProperty`, `validate(` or
  the 134-line census and would break on migration. A missed site is a MAJOR finding.
- INV-INS-119 (four-arg `ErrorDescription`, envelope), INV-INS-123 (G-2 clause exemptions for
  `REQUIRES`), INV-INS-115 (17/18 generator numbers — already updated in the main spec; do
  gh105's numbers agree?), INV-INS-111 vs INV-INS-137. Any silent double-definition?
- Does anything in gh105 pre-empt gh104's Group 10 (which must NOT be executed now)?

### D5 — Technical feasibility of the design

- `PredicateStore` API vs actual `.mop` call shapes: can every current call site pattern be
  expressed through `ensure`/`negate`/`validate` at the placements the delta mandates? Where do
  splitters get applied (design says "by the caller") — is that implementable in a `.mop` body?
- `condition(...)` compiles to a boolean guard (verify in the generated monitor) — so
  three-valued reads are body-only. Consistent everywhere?
- Junction rules (INV-INS-136) vs the pilot evidence in
  `audit/20260820_verificacao_plano_predicados_v2/agentI/` (specs + drivers + relatorio.md):
  do the four rules actually follow from the pilot's measured failures? Reproduce the pilot's
  generation step if feasible (§6.4) — at minimum G-PARAM's collapse matrix on `byte[]` vs
  `Object`.
- The `Object`-idiom caveat: `args(b)` with `Object` matches ANY single argument — is the
  fixed-overload requirement stated everywhere a junction is described?
- Generator budget: any F3 chain that would push `CipherSpec` past 17 events? (The rule's six
  REQUIRES clauses need bindings — count what task 5.4 implies for the alphabet.) This is a
  known hard ceiling (18 = parser `StackOverflowError`), so an alphabet overrun is a BLOCKER.

### D6 — Freeze safety (the highest-stakes dimension)

Enumerate every path by which implementing these artifacts could alter the behavior of the
frozen `jca` set, and check the artifacts close each: the `@Deprecated`-only edit (what does
adding the annotation do to the reactor build and to any `-Werror`-like config?); shared classes
other than `ExecutionContext` that `jca` `.mop` files call (enumerate the imports of `jca/*.mop`
yourself); the gate collateral (D4 above); `codes.csv` scoping; the two-stores-in-one-process
question (only via `custom` set mixing — is the exclusion airtight?); the
`rvsec-mop-defsuses` reactor removal (does anything else in the reactor depend on it?).

### D7 — Completeness, gaps and risks

What did the change forget? Candidates to probe: the 17 orphans — enumerate them yourself from
the `.mop` files and check tasks 3.1-3.5 cover all 17 (names per spec); the 8 accuser-less reads
list; the seven genericity gaps (incl. the reverse-orphan/duplicate-event fixture
`jca/GCMParameterSpecSpec.mop:23,34,48` — confirm those line numbers); the fate of the 35
written-never-read sites (wired, removed, or recorded — where does each land?); accepting-state
bookkeeping (25 sites — INV-INS-131 says "not offered"; which task removes those calls and is
the 134-line census's fate fully accounted?); error handling for generation failures inside gate
scripts; task-order soundness (can 4.3 really run before 5.x wires producers, given lesson
"never add a reader without its producer in the same task"? — check the F2/F3 boundary
carefully: moving an EXISTING read to the body before its producer exists changes what is
accused. If the artifacts do not resolve this, it is a MAJOR finding); anything in
`docs/20260820_verificacao_plano_predicados_v2.md` §7 (open items) that the artifacts should
carry but do not.

### D8 — Workflow and principle compliance

P1 (no premature abstraction — is anything in the design speculative?), P2 (are the artifacts
self-contained for an implementer who has NOT read the plan?), P3 (no shims — is `@Deprecated`
correctly argued as not-a-shim? is the defsuses retirement complete?), P4 (no migration-history
or promotional language in anything that will become code/comments); WORKFLOW.md conventions
(issue cross-refs `#105`, `refs #105`/`closes #105`, no Co-Authored-By, change dir naming);
English throughout the artifacts.

---

## 6. Command recipes (all read-only; run from the paths shown)

```bash
R=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources
A=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

# 6.1 anchor
git -C /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec rev-parse --short HEAD   # expect bd61abea

# 6.2 predicate distribution (compare with artifact claims)
grep -ho "setProperty(Property\.[A-Z_]*" $R/jca_android/*.mop | sed 's/.*Property\.//' | sort | uniq -c | sort -rn
grep -ho "validate(Property\.[A-Z_]*"    $R/jca_android/*.mop | sed 's/.*Property\.//' | sort | uniq -c | sort -rn
grep -ho "remove(Property\.[A-Z_]*"      $R/jca_android/*.mop | sed 's/.*Property\.//' | sort | uniq -c
grep -c  "ExecutionContext" $R/jca_android/*.mop | awk -F: '{s+=$2} END {print s}'      # expect 134
# CAUTION: a naive count of "validate(" gives 31, not 27 — KeyPairGeneratorSpec has a private
# helper validate(int). The discriminator is "(Property".

# 6.3 oracle census (write your own parser; two independent methods should agree)
ls /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30/*.cryptsl | wc -l   # 33

# 6.4 parameter-collapse smoke (optional but decisive for D5; use YOUR scratch dir)
JM=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/javamop/target/release/javamop/javamop
RM=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-monitor/target/release/rv-monitor
# minimal 2-event spec varying one parameter type: byte[]|char[]|Object → check the T(...) header
$JM/bin/javamop -s T.mop && grep -m1 "^T\?.*(" T.rvm && $RM/bin/rv-monitor -merge T.rvm \
  && grep -c CachedWeakReference *RuntimeMonitor.java    # 0 = global monitor (collapse)

# 6.5 existing gates still green (CI contract is mandatory: without these flags collection breaks)
cd $A && uv run pytest tests/parity/test_gh104_specset_gates.py --import-mode=importlib -o "addopts="
cd $A && uv run python scripts/gh104_diff_harness.py --selftest

# 6.6 OpenSpec artifact sanity
cd $A && openspec validate gh105-predicate-wiring && openspec status --change gh105-predicate-wiring

# 6.7 reactor build, ONLY if you need fresh javamop/rv-monitor binaries (slow; JDK 21 prefix)
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec && mvn clean install -DskipMopAgent -DskipTests
```

---

## 7. Learnings that have already cost dearly (test the artifacts against each)

1. A predicate read in `condition(...)` never merely "fails" — it suppresses the transition and
   the NEXT call is accused of order. 2. An event outside the `fsm`/`ere` gets an all-`fail` row
   and accuses unconditionally. 3. Never add a reader without its producer modeled in the same
   set and the same task — an unwritten predicate reads as `false` and accuses every conforming
   call. 4. Never fix a binding without putting the event into the automaton in the same edit.
   5. Never change shared Java believing the freeze gate covers it — it checks `.mop`, not
   classes (this is how `233df18a` happened and was reverted). 6. The alphabet ceiling is real
   but it is 18, and it is the enable-set parser, not the heap; 17 generates under 1 GB.
   7. Never anchor a record to a different rule version than the set uses. 8. Never repair spec
   content while the weaver deletes the category (`UnsatisfiedConstraint`: 0 in 97,018 dexlib2
   events vs 43 in the AspectJ control). 9. Aggregated CSVs do not decide per-event hypotheses —
   the generated transition table and a replayed trace do. 10. "Repair is costly" does not imply
   "removal is cheap". 11. The failed attempt was not all wrong — its automaton bucket is rescue
   material under fresh evidence, never copied. 12. Three oracles before classifying a defect:
   the rule, the generated monitor, the trace. 13. This toolchain errs silently and silence
   looks like success — inspect artifacts, never exit codes. 14. A pilot that can only pass
   decides nothing — pick the hard case. 15. Check the unit, not just the number ("19 edges"
   was 19 predicates; the work is 35 clause-sites).

---

## 8. Your deliverable

Write ONE file (create it; this is your only write):

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/analise_gh105_<MODEL_NAME>.md
```

where `<MODEL_NAME>` is your model's short lowercase name (e.g. `claude`, `gpt5`, `gemini`,
`qwen`). Structure it as:

1. **Header**: date, model, HEAD verified against, tools used (subagents? sequential-thinking?),
   what you could not run and why.
2. **Executive verdict** (≤ 15 lines): is the change safe to implement as written? The blockers,
   if any, first.
3. **Findings table**: every finding, most severe first — `id | dimension | severity | verdict |
   claim | evidence (file:line / command) | recommended amendment (concrete text or edit)`.
4. **Per-dimension sections (D1–D8)**: one line per claim checked, including the CONFIRMED ones
   (an unchecked claim and a confirmed claim must be distinguishable). Include the commands you
   actually ran and their relevant output.
5. **The 35-clause ledger** (from D2): one row per connectable `REQUIRES` clause — rule, clause,
   where the artifacts place it, verdict.
6. **Open questions for the researcher** — only things genuinely his to decide, with the
   numbers ready.
7. **Limitations** — what a device, a weave, or a campaign would still have to show.

Do not soften findings. A `REFUTED` with file:line evidence is worth more than ten polite
`PLAUSIBLE`s. If everything holds, say so plainly — a clean bill from a rigorous pass is itself
a result. If you find a BLOCKER, put it in the first line of the executive verdict.

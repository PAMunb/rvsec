# EMPIRICAL-DEMAND.md — pipeline-level demand audit (round-10, 2026-05-29)

Compiled monitors for all three spec corpora via `rv-monitor-generator` (uses
the fork JavaMOP + RV-Monitor toolchain at `$RVSEC_HOME/{javamop,rv-monitor}/`).
Output preserved under `empirical-monitors/{jca,generic,generic_new}/`.

Inputs (all freshly compiled 2026-05-29):
- `jca/`         ← `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/` (23 specs)
- `generic/`     ← `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic/` (118 specs)
- `generic_new/` ← `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic_new/` (27 specs)

Each corpus dir contains four artefacts:

| File                                | Role                                                       | Why preserved                                              |
| ----------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- |
| `MultiSpec_1MonitorAspect.aj`       | JavaMOP-compiled aspect (pipeline-level demand target)     | the §4.* demand-counting input                             |
| `MultiSpec_1MonitorAspect.json`     | `AspectDescriptor` consumed by dexlib2 `DescriptorReader`  | confirms `baseAspectExclusions` schema (§4.B / §4.D)       |
| `MultiSpec_1RuntimeMonitor.java`    | runtime monitor classes invoked by advice bodies           | ABI of `evaluateIf` (§4.I), `staticinitEvent` (§4.Y/§4.JP) |
| `Coverage.aj`                       | auxiliary aspect (copied, not compiled)                    | semantic reference for `coverage-weaver` (NOT-NEEDED β)    |

Counts in the table below are taken from `MultiSpec_1MonitorAspect.aj` per corpus.

## Demand table (POSITIVE pipeline-level sites per corpus)

| Construct                              | Round-9 claim         | Empirical (jca, generic, generic_new) | Verdict                                                  |
| -------------------------------------- | --------------------- | ------------------------------------- | -------------------------------------------------------- |
| `execution(...)` POSITIVE              | 24 jca pipeline       | **0, 0, 0**                           | RECLASSIFY §4.E → NOT-NEEDED β (absorption by JavaMOP)   |
| `within(...)` POSITIVE                 | 13 jca + 13 generic_new | **0, 0, 0**                           | RECLASSIFY §4.W → NOT-NEEDED β (no positive consumer)    |
| `!within(...)`                         | absorbed via BaseAspect.notwithin | 13, 13, 13 (identical inline expansion of 13-entry list) | confirms §4.B/§4.D scope                        |
| `if(...)` PCD                          | 8 generic_new         | **0, 0, 3** (generic_new)             | §4.I real, smaller scope                                 |
| `staticinitialization(T+)`             | 6 generic_new         | **0, 0, 3** (generic_new)             | §4.Y real, smaller scope                                 |
| `after() throwing(...)`                | 2 generic_new         | **0, 0, 1** (generic_new)             | §4.T real (single site)                                  |
| `target(Type)`                         | 44 generic_new        | **0, 0, 22** (generic_new)            | §4.TT real, ~½ scope                                     |
| `args(Type)`                           | 10 generic_new        | **0, 0, 5** (generic_new)             | §4.AT real, ½ scope                                      |
| `!target(T)`                           | 28 generic_new        | **0, 0, 14** (generic_new)            | §4.N real (matches Claude/Deepseek panel re-grep)        |
| `!args(T)`                             | 4 generic_new         | **0, 0, 2** (generic_new)             | §4.N real                                                |
| `T+` in `call()` owner                 | ~73 generic_new       | **0, 0, 64** (generic_new)            | §4.O confirmed                                           |
| Method-name glob `*name`               | ~16 generic_new       | **0, 0, 14** (generic_new)            | §4.X confirmed                                           |
| `__STATICSIG`                          | 0 (absorbed)          | **0, 0, 0**                           | absorption CONFIRMED ✓                                   |
| `condition(...)`                       | 0 (absorbed)          | **0, 0, 0**                           | absorption CONFIRMED ✓                                   |
| **`thisJoinPoint` / `JoinPoint.`**     | **0 (§4.JP NOT-NEEDED β)** | **0, 0, 3** (generic_new staticinit)  | **CLAIM REFUTED — survives in staticinit advice bodies** |
| `cflow*` / `withincode` / `handler`    | 0                     | **0, 0, 0**                           | NOT-NEEDED α confirmed ✓                                 |
| `get(FieldPattern)` / `set(FieldPattern)` | 0                  | **0, 0, 0**                           | NOT-NEEDED α confirmed ✓ (resolves mimo concern)         |
| `around`                               | 0                     | **0, 0, 0**                           | EXPLICIT-NO-OP confirmed ✓                               |
| `adviceexecution()` (negated form)     | 0 (vacuous)           | 1, 1, 1 — all from `!adviceexecution()` in `MOP_CommonPointCut` | NOT-NEEDED β confirmed ✓ |
| `BaseAspect.notwithin()`               | 1 jca + 1 generic_new | 2 each (signature + body of same call) | confirmed                                               |

## Three decisive evidences

### 1. §4.E POSITIVE `execution(...)` = 0 across all 3 corpora

The only `execution(` substring hits across all three compiled `.aj` files
are inside `!adviceexecution()` in `MOP_CommonPointCut`:

```
jca/MultiSpec_1MonitorAspect.aj:76:        pointcut MOP_CommonPointCut() : !within(... RVMObject+) && !adviceexecution() && BaseAspect.notwithin();
generic/MultiSpec_1MonitorAspect.aj:24:    pointcut MOP_CommonPointCut() : !within(... RVMObject+) && !adviceexecution() && BaseAspect.notwithin();
generic_new/MultiSpec_1MonitorAspect.aj:39: pointcut MOP_CommonPointCut() : !within(... RVMObject+) && !adviceexecution() && BaseAspect.notwithin();
```

No spec uses `execution(...)` positively at pipeline level. The round-9
defensive-shipping rationale for §4.E ("future specs might use it") is now
dominated by P1 (no speculative features): **§4.E reclassified NOT-NEEDED β**
with absorption stage = JavaMOP compiler (source-level `execution()` in `.mop`
files is rewritten into matching `call()` events during compilation).

### 2. §4.W POSITIVE `within(...)` = 0 across all 3 corpora

All `within(...)` occurrences are inside pointcut declarations themselves
(`pointcut notwithin(): ... within(...) ...` or `MOP_CommonPointCut(): !within(... RVMObject+) ...`).
Zero specs use positive `within(...)` as an event predicate.

**§4.W reclassified NOT-NEEDED β** — the source-level 13+13 count was inflated
by counting body declarations of the `notwithin()` macro.

### 3. §4.JP `thisJoinPoint` SURVIVES 3× in generic_new staticinit (refutes NOT-NEEDED β)

```
empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:260:     MultiSpec_1RuntimeMonitor.Collection_HashCode_staticinitEvent(thisJoinPoint.getStaticPart().getSignature());
empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:319:     MultiSpec_1RuntimeMonitor.Serializable_NoArgConstructor_staticinitEvent(thisJoinPoint.getStaticPart().getSignature());
empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:328:     MultiSpec_1RuntimeMonitor.URLConnection_OverrideGetPermission_staticinitEvent(thisJoinPoint.getStaticPart().getSignature());
```

The round-8 claim that `thisJoinPoint*` is absorbed by Coverage.aj + `__STATICSIG`
is **false for the `staticinit` advice family**: when JavaMOP emits a staticinit
event, it passes the signature derived from `thisJoinPoint.getStaticPart().getSignature()`
as the first argument. §4.Y must therefore deliver the signature object to the
runtime call site (synthesised `<clinit>` injection point + Signature
construction), not just the bare advice invocation.

## Impact on scope

| Closure       | Round-9 status                          | Round-10 (empirical) status                              |
| ------------- | --------------------------------------- | -------------------------------------------------------- |
| §4.E          | COVERED in-change (~230 LOC)            | **NOT-NEEDED β** — saves ~230 LOC                        |
| §4.W          | COVERED in-change (~80 LOC)             | **NOT-NEEDED β** — saves ~80 LOC                         |
| §4.JP         | NOT-NEEDED β (claim of Coverage.aj absorption) | **COVERED inside §4.Y** — extends §4.Y to deliver Signature (+30-50 LOC) |
| §4.I          | 8 sites estimated                       | 3 sites — proportional scope reduction                   |
| §4.T          | 2 sites estimated                       | 1 site — single-fixture validation                       |
| §4.Y          | 6 sites estimated                       | 3 sites (plus Signature delivery sub-task)               |
| §4.TT/§4.AT/§4.N | 44/10/(28+4) estimated               | 22/5/(14+2) confirmed in pipeline                        |
| §4.O          | ~73 estimated                           | 64 confirmed                                             |
| §4.X          | ~16 estimated                           | 14 confirmed                                             |
| §4.B/§4.D     | 1+1 estimated                           | 1+1 confirmed                                            |
| §4.V          | 14 jca + 2 generic_new estimated        | pending pipeline-level re-grep (proposal counts retained, marked PROVISIONAL) |

**In-change closures**: 14 → **12** (§4.E and §4.W exit; §4.JP enters as §4.Y sub-closure).
**Production LOC**: ~865-940 → **~565-660**.
**Coverage**: a real silent gap (`thisJoinPoint` in staticinit) is now closed.

## Decision codes consumed in this round

- **AA-decision** (2026-05-29): §4.E reclassified NOT-NEEDED β based on empirical pipeline demand = 0 across all three corpora. Supersedes round-8 user defensive-shipping decision. The future "execution(...) might be used positively" risk is downgraded to "amend matrix when DemandCounter.countCompiledAj(execution) > 0" — exactly the trigger MatrixIntegrityTest already enforces.
- **AB-decision** (2026-05-29): §4.W reclassified NOT-NEEDED β. Source-level 13+13 was a macro-body inflation; pipeline demand = 0.
- **AC-decision** (2026-05-29): §4.JP `thisJoinPoint`/`Signature` reactivated as in-change work, folded into §4.Y as the Signature-delivery sub-closure. Round-8 NOT-NEEDED β rationale (Coverage.aj absorption) is refuted by 3 generic_new staticinit sites.

## Reproducing this audit

```bash
export RVSEC_HOME=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
CHANGE=openspec/changes/gh62-aspectj-grammar-coverage

for corpus in jca generic generic_new; do
  uv run rv-monitor-generator generate \
    --specs-dir $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/$corpus \
    --output $CHANGE/empirical-monitors/$corpus
done
```

Counting recipe used per construct: see commit message of round-10 update.

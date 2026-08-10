# Agent Beta report — Batch A (DHG, HMC, PBE, IVP, SKS)

Agent Beta (toolchain red team), 2026-08-09. Scope: 5 specs of batch A per the pairing
inventory. Rules fixed for the round respected: D-piloto-1 (ORDER reading A), D-piloto-3
(effective automaton is the evidence source — published in `beta_effective_automata.md`),
D-piloto-4 (one dimension per claim, SET claims separate, six normative states).
Sequential Thinking MCP was not used (not required; the decomposition below is the
published log). Every material claim has an executable leg; labels used:
PROVADO / MEDIDO / OBSERVADO_EM_ARTEFATO / INFERIDO / NAO_VERIFICADO.

## 0. Inputs, freeze checks, and reproduction — MEDIDO

- The 5 `.mop` and 5 `.cryptsl` hashes match `fase0/manifest_hashes.md` /
  `batchA/generation_manifest.md` exactly (sha256sum, this session).
- The 20 round-input artifacts match the generation manifest hash-for-hash (20/20).
- **Independent regeneration** in my own scratch (`beta/gen_<S>/`), same frozen toolchain
  and commands (`javamop -d out -merge --emit-descriptor`; `rv-monitor -d out -merge`):
  all 10 executions exit 0, empty stderr, and **all 20 artifacts byte-identical** to the
  round input (determinism confirmed; note this is generator determinism, not independent
  replication — REF-11 wording).
- One correction to my briefing: the android.jar path given there
  (`/home/pedro/Android/Sdk/...`) does not exist on this host. The frozen jar is
  `$ANDROID_HOME/platforms/android-30/android.jar` per `fase0/toolchain_ambiente.md` §4,
  verified by hash `96ccfdc84d15fad4e22d76cbb8ef38b150a4b56327957067875ca7e18113a424`.
- Methodological trap found and neutralized: `javap -classpath android.jar` silently
  resolves `javax.*` classes from the host JDK system image (proven: it printed
  `javax.xml.crypto.dsig.spec.HMACParameterSpec` although the jar has zero such entry).
  All member tables were therefore derived from **class files extracted from the jar**.

## 1. Generability / budget (G2) — MEDIDO

`/usr/bin/time -v`, this session, host of `toolchain_ambiente.md`:

| Spec | events | javamop wall/RSS | rv-monitor wall/RSS | CoenableProbe (ERE, production plugins) |
|---|---|---|---|---|
| DHG | 1 | 0.42 s / 85.7 MB | 0.88 s / 86.1 MB | states_min=2; coenable[fail]=1 = 1×(2¹−1) saturated; chars=57 |
| HMC | 1 | 0.42 s / 84.7 MB | 0.93 s / 85.1 MB | 1 = saturated; chars=54 |
| PBE | 3 | 0.43 s / 86.2 MB | 0.91 s / 87.2 MB | 21 = 3×(2³−1) saturated; chars=261 |
| IVP | 4 | 0.41 s / 87.8 MB | 0.91 s / 87.2 MB | 60 = 4×(2⁴−1) saturated; chars=719 |
| SKS | 4 | 0.44 s / 86.7 MB | 0.90 s / 86.7 MB | 60 = 4×(2⁴−1) saturated; chars=719 |

All five are far below the 17-event ceiling (max 4). All have `@fail`, all coenable-fail
sets exactly saturated at n×(2ⁿ−1) (closed form = probe output). Full 23-spec production
merge, measured for context: javamop 0.68 s / 176.8 MB; rv-monitor 29.16 s / 1.68 GB
(dominated by CipherSpec, consistent with the pilot's 28.09 s).

## 2. Capture matrices vs real android.jar API 30 (G5) — MEDIDO

Harness: `PointcutBudgetCtor` (pilot's ctor-capable variant driving the production
`PointcutMatcher`/`PointcutExpressionParser`/`AndroidClassIndex` from `instr-cli.jar`
`356e8b70…`; provenance and hash recorded) plus my variant `PointcutBudgetCtorB` that takes
the **descriptor's** import list, so simple names resolve exactly as production does
(`TypeResolver.resolveFqn`, `TypeResolver.java:110-131`; owner match is exact descriptor
equality for non-`+` owners, `PointcutMatcher.java:333-345`; two-predicate constructor
gate `PointcutMatcher.java:437-438`). Member tables from javap over **extracted** class
files of the frozen android-30 jar. Outputs: `beta_capture_outputs.txt`.

| Spec | Esperado (rule × API 30) | Capturado | Vizinhos testados (0 hits) | Verdict |
|---|---|---|---|---|
| DHG | ctor(int,int) | ctor/2 only | getters; DHParameterSpec ctors | exact |
| PBE | ctor(byte[],int); ctor(byte[],int,APS) | ctor/2 by c1&c3; ctor/3 by c2 | getters; GCMParameterSpec ctors | exact |
| IVP | ctor(byte[]); ctor(byte[],int,int) | ctor/1 by c1&c3; ctor/3 by c2&c4 | getIV; GCMParameterSpec ctors | exact |
| SKS | ctor(byte[],String); ctor(byte[],int,int,String) | ctor/2 by c1&c3; ctor/4 by c2&c4 | getters; DESKeySpec ctors; `com.example.SecretKeySpec` (same simple name, wrong package) under production imports | exact |
| HMC | **∅ — class absent from android-30** | ctor/1 matched for an app-bundled owner | getOutputLength | see BETA-HMC-02 |

- Esperado ⊆ Capturado holds for all (HMC vacuously on the platform). Capturado ∩
  Vizinhos = ∅ in every run. No `..`, no `+`, no glob in any pointcut.
- The only OVERLAPs are the deliberate pairs (c1/c3, c2/c4) sharing one pointcut; the
  discrimination is semantic (complementary `condition(...)`) and was PROVEN by execution
  (§4): exactly one event of each pair transitions per construction. No unexpected
  double-fire; no zero-fire at member level.
- **HMC**: `javax/xml/crypto` does not exist in android-30 (0 jar entries; only
  datatype/namespace/parsers/transform/validation/xpath under `javax/xml/`). Also absent
  from android-36 and android-37.0. The API-30 CrySL rule therefore models a class the
  declared platform does not provide — the spec can never fire against platform API; it
  can fire only if the app bundles the class (dexlib2 matcher matches bundled call sites —
  MEDIDO). The ajc path would face an unresolvable pointcut type against the android-30
  classpath — NAO_VERIFICADO (no ajc on host; named pendency, same family as BETA-CIP-08).
- **Triangulation (REF-12 test)**: ctor sets of the four `javax.crypto.spec` classes are
  identical across android-30 / android-36 (host) / android-37.0 (host; the dexlib2 CLI's
  lexicographic-max choice). The container's android-36 remains untriangulated — pendency
  kept open, but for these 5 specs the jar-resolution anomaly cannot change matching
  unless the container jar differs from the host jar of the same API level.

## 3. Artifact chain `.mop → .rvm → .aj + .json → RuntimeMonitor.java` (G6 static) — MEDIDO/OBSERVADO_EM_ARTEFATO

- **Cardinality/order**: programmatic comparison of `.aj` vs descriptor for all 5 —
  monitorCalls match 1:1 in method, order and argument lists (DHG 1/1, HMC 1/1, PBE 3/3,
  IVP 4/4, SKS 4/4); advice counts match (1,1,2,2,2); every advice is
  `after returning`, none `around`/`throwing` (correct for construction events).
- **Merged production mode**: full 23-spec `-merge` run in scratch. The five `.rvm` are
  byte-identical to the per-spec runs; the five monitors inside
  `MultiSpec_1RuntimeMonitor.java` carry identical transition tables, identical advice
  pair order, and wrappers named `<Spec>_c*Event` — the per-spec artifacts are a valid
  proxy for production at automaton level.
- **condition(...) prologue**: suppression via `return false` **before** `handleEvent` in
  all events with conditions (e.g. SKS `:187`→`:194`) — silent suppression, no transition,
  exactly the pilot's pattern.
- **`__LOC`**: survives into the monitor as
  `ViolationRecorder.getLineOfCode()` in every handler and violating body (e.g. SKS
  `:224`, `:241`, `:254`). IVP c3/c4 and every `@fail` use the 3-arg `ErrorDescription`,
  which delegates with `"unknown"` expecting (pilot finding, recurs; Gama's lane).
- **Naming (IVP)**: the public runtime-monitor class and aspect take the **file** basename
  (`IvParameterSpecRuntimeMonitor`, `IvParameterSpecMonitorAspect`, descriptor
  `fileName/shortName = IvParameterSpec`), while inner monitor classes, wrappers, and
  descriptor `specName` take the **spec** name (`IvParameterSpecSpec`). The chain is
  internally consistent (descriptor `monitorCalls.method` strings reference the class that
  actually exists), and in production merge the public class is `MultiSpec_1RuntimeMonitor`
  anyway; `errors.csv` spec attribution comes from the literal `"IvParameterSpecSpec"` in
  the bodies. No consumer keys on the file-derived name — benign, recorded.
- **Codegen variance (HMC)**: HMC's monitor extends `AbstractSynchronizedMonitor` (plain
  `Prop_1_state` int) while the other four extend `AbstractAtomicMonitor` (CAS pairValue) —
  consequence of the unparameterized property (see §5). Same table semantics.
- **Stale-flag pattern (pilot BETA-CIP-06)**: recurs and is **exercised here** — see §4.

## 4. Executable drive of the generated monitors — PROVADO/MEDIDO

`beta_BetaDrive.java` compiles the five generated monitors **unmodified** against the
production runtime (`rvsec-core.jar` `7b4d72aa…`, `rvsec-logger-csv` `6787f411…`,
`rv-monitor-rt.jar` `0fa65fbc…`) and drives the static wrappers in the exact order the
generated advices call them, feeding only **normally-returning real constructions** (JDK
classes) to mirror `after returning`. 30/30 assertions pass; **3 repetitions
byte-identical** (`betadrive_run{1,2,3}.out`, same sha256). Highlights:

1. **Automaton walks confirm every table** (compliant → match handler and Property writes;
   violating → own-body error, state loop at 0, no `@fail`).
2. **`@fail` dead in real execution** for DHG/PBE/IVP/SKS: state 2 requires a second event
   in the same per-object monitor; only an artificial second event on the same object
   triggers it (demonstrated). The specs' `InvalidSequenceOfMethodCalls` channel is dead
   code in production traces (FEN-SET-fail-morto, pilot's GCM phenomenon).
3. **Stale-flag handler re-execution PROVEN live**: after a compliant c1 (match), removing
   the just-written Property and delivering the suppressed sibling c3 re-writes it — the
   suppressed event's wrapper re-ran `@match` off the stale category flag (PBE-a-stale,
   SKS-a-stale). Unlike the pilot's GCM (inert), the pattern fires on **every monitored
   construction** here (merged advice = 2 wrappers per call). Benign in effect (idempotent
   handlers); the mechanism defect is the generator's.
4. **PBE 3-arg silent FN (realizable)**: `new PBEParameterSpec(salt, 100, aps)` with
   randomized salt returns normally on the real API; the only advice for that ctor calls
   `c2Event`; condition false → zero events, zero errors, no `PREPARED_PBE`. Combined with
   `PREPARED_PBE` having **no reader anywhere in the set**
   (`data/gh101/predicate_omissions.csv:8` registers the write-no-read), the violation of
   the rule's `iterationCount >= 10000` constraint through the 3-arg ctor is invisible
   end-to-end. Terminal FN in a realizable trace — critical.
5. **SKS 4-arg REQUIRES drop (realizable FN)**: non-randomized key material through the
   4-arg ctor gets `GENERATED_KEY` granted with zero errors (c2 checks only
   whitelist+length). The rule REQUIRES `preparedKeyMaterial[keyMaterial]` (surrogate
   RANDOMIZED) for **both** ctors; `data/gh101/predicate_edges.csv:66` records the REQUIRES
   as "present-surrogate" without noting it holds only for the 2-arg path.
6. **SKS whitelist extra-oracle FP (realizable)**: "DES" with randomized material fires
   `UnsatisfiedConstraint`, yet the api30 rule carries **no** algorithm membership
   constraint (`SecretKeySpec.cryptsl:27-29` has only the length constraint;
   `data/gh101/conformance_record.csv:21` registers the list as a declared hand
   translation with no derived anchor). Registered ≠ approved (pilot precedent).
7. **DHG extra-oracle suppression**: `exponentSize >= primeSize` (oracle-legal — the api30
   rule has no CONSTRAINTS) is silently suppressed and denied `PREPARED_DH`
   (executable). `KeyPairGeneratorSpec.mop:96,107` accuses on `!validate(PREPARED_DH,
   params)` — downstream FP chain for an oracle-legal construction (last link read, not
   executed: INFERIDO).
8. **IVP c2/c4 predicate hole closed by the platform**: randomized iv + invalid ranges
   fires neither event, but every such construction throws on the JDK implementation
   (offset=-1 → ArrayIndexOutOfBounds; len>length → IllegalArgumentException; overflow →
   IllegalArgumentException — measured), so `after returning` can never observe the gap.
   Android libcore behavior INFERIDO equal (OpenJDK-derived) — named threat.
9. **SKS folding**: lowercase "aes" accepted through `toUpperCase()` (executable; relevant
   to the round's standardized folding test, D-piloto-2a).

## 5. HMC global monitor — the batch's critical toolchain-visible defect — PROVADO

The spec parameter `hmacParameterSpec` (`HMACParameterSpecSpec.mop:17`) is never bound by
the single event, which binds `s` (`:21`). JavaMOP binds spec parameters **by name**; with
no event binding it, the generated property is unparameterized: the indexing tree is one
static `Tuple2` (`HMACParameterSpecSpecRuntimeMonitor.java:212`, FindOrCreateEntry at
`:236-239` always returns it), i.e. **one monitor per process** — also in the production
merged artifact (`MultiSpec_1RuntimeMonitor.java:9462`). Discriminating test
(`beta_BetaDriveHmc.java`, 3 identical reps): two distinct, CrySL-legal constructions →
`errors=1 InvalidSequenceOfMethodCalls` (**false positive**) and the second object is
denied `PREPARED_HMAC` (which `MacSpec.mop:99` reads — second-order FP). The CrySL
lifecycle is per `this`; the artifact's is per process. Two claims: the spec-level binding
defect (BETA-HMC-03, critical) and the generator's silent acceptance of a spec whose
parameter no event binds (BETA-SET-02 — no warning, exit 0). Both predate gh101: the
frozen `jca` HMC is byte-identical (manifest anomaly 2).

## 6. AJC × dexlib2 static comparison — OBSERVADO_EM_ARTEFATO / NAO_VERIFICADO

The descriptor is the dexlib2 input; `MonitorInvokeBuilder.buildInvoke`
(`MonitorInvokeBuilder.java:69-77`) emits one invoke-static per `monitorCalls` entry in
descriptor order, and `DexWeaver.weave` (`DexWeaver.java:303`) drives the same
`PointcutMatcher` I ran (both verified in source this session). Since descriptor ≡ `.aj`
(1:1, §3), the two paths encode the same event set/order for all five specs.
What only a weave+device can close (INCONCLUSIVE, named): actual `after returning`
equivalence on ART, `__LOC` under DEX, and the HMC unresolvable-type behavior under ajc.

## 7. Fail-open probes — MEDIDO

Mutated copies in scratch only, frozen toolchain:

| Probe | Input | Result | Reading |
|---|---|---|---|
| p1 | stray `)` added to HMC pointcut | exit 0, empty stderr, `.rvm` **byte-identical** to unmutated | parser swallows unbalanced close-paren silently |
| p2 | two stray `)` in SKS conditions | exit 0, `.rvm` byte-identical | tolerance is systematic; explains the stray `)` frozen in `SecretKeySpecSpec.mop:30` (artifact unaffected — benign there) |
| p3 | undefined `c9` added to PBE's ERE | exit 0 both phases; `c9` flows into `.rvm` ERE and is silently dropped (3 events, no table) | GCM fail-open phenomenon reproduced first-hand on a batch-A shape |
| p4 | stray `(` in HMC pointcut | javamop prints `MOPException ... error ... parsing the pointcut` to stderr **but exits 0** and produces **no artifacts** | exit 0 with error + spec silently vanishes from the set — pilot BETA-SET-04 reproduced |

## 8. Scientific log (decomposition, per protocol §2)

Per spec, the same loop: (Q) does the artifact chain realize the spec, and what breaks it?
(H) hypotheses raised from reading (stray paren, name mismatch, missing negative branch,
platform absence); (T) discriminating tests chosen so one leg is executable (regeneration
hash-compare; ctor matcher desk over extracted API bytes; monitor drive with real
constructions; global-vs-parametric two-object test; mutation probes); (E) evidence filed
above with file:line and outputs; (R) results in claims; (U) uncertainties: container
android-36 (REF-12), ART/dexlib2 runtime behavior (G6/G10 phase), Android libcore ctor
exception behavior (JDK-verified only), KeyPairGeneratorSpec downstream FP link (read,
not executed). Nothing unknown was converted to PASS; INCONCLUSIVEs are named.

## 9. Files

- `beta_effective_automata.md` — effective transition tables (common reference).
- `beta_claims.csv` — 39 claims.
- `beta_hashes.txt` — sha256 of all inputs/outputs used or produced.
- Harness sources/outputs: `beta_BetaDrive.java`, `beta_BetaDriveHmc.java`,
  `beta_PointcutBudgetCtorB.java` (+ provenance of the pilot's `PointcutBudgetCtor.java`),
  `beta_betadrive_run1.out`, `beta_betadrive_hmc.out`, `beta_capture_outputs.txt`,
  `beta_probes_summary.txt`.
- Scratch (ephemeral): `<scratchpad>/batchA/beta/` — regenerations, probes p1–p4, full
  merged generation, logs with `/usr/bin/time -v`.

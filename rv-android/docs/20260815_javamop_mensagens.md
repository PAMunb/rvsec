# Making JavaMOP Violation Reports Legible

**Date:** 2026-08-15
**Status:** analysis + plan. Nothing implemented.
**Target:** the *next* campaign. The `ase-journal` dataset is used here only as measurement of the
problem; no published artifact is to be revised.

---

## 0. Scope and reading guide

This document answers one question: **why is a RVSEC violation report unreadable by a human, and
what has to change in the source so the next campaign produces reports that support a decision?**

It is organised as:

- §1 — the finding, in one page.
- §2 — the evidence base. Every number here was measured, not estimated.
- §3 — root-cause analysis, in seven layers. Each layer is an independent defect; fixing one does
  not fix the others.
- §4 — what an actionable report has to contain, derived from first principles and from what
  CogniCrypt/CrySL already emits.
- §5 — the plan: eight workstreams, sequenced, with cost, risk, blast radius and verification.
- §6 — decisions that are the researcher's to make, not the implementer's.
- §7 — acceptance criteria for the next campaign.
- §8 — the full defect register, with `file:line`.

Provenance rule used throughout: every claim carries a `file:line`. Claims that were inferred
rather than read are marked **[inferred]**. There are four of them.

---

## 1. The finding

**72.93% of all reported violations carry the literal string `unknown` as their message.** All of
them are `InvalidSequenceOfMethodCalls`, and — the converse also holds — *every*
`InvalidSequenceOfMethodCalls` in the dataset carries `unknown`. The two labels are perfect
synonyms. That error type has never, in the history of this codebase, produced a message.

This is not a parsing loss, not a truncation, and not a sampling artifact. It is a literal:

```java
// rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorDescription.java:34-36
public ErrorDescription(ErrorType type, String spec, String location) {
    this(type, spec, location, "unknown");
}
```

All 21 `@fail` handlers in `jca/` and all 21 in `jca_android/` call the three-argument constructor.
No site anywhere in the repository emits `InvalidSequenceOfMethodCalls` *with* a message.

But the mute constructor is the smallest of the problems, and fixing it alone would change very
little. Three deeper defects sit underneath it:

1. **The FSM sink absorbs unrelated failure kinds.** JavaMOP's generated transition function is
   *total*, with an explicit dead state. Any `(state, event)` pair not written in the `fsm:`/`ere:`
   block lands there and fires `@fail`. Eighteen events across the `jca` set exist *only* to report
   a specific error and were never given a transition — so each specific violation emits **two**
   records: one informative, one mute and misclassified. Around **80 distinct event sequences**
   collapse onto the single string `unknown`.

2. **A failed `REQUIRES` predicate is invisible.** CrySL's `REQUIRES` was translated as
   `condition(ExecutionContext.instance().validate(...))` *inside the pointcut*. When it fails the
   event is not generated at all — the trace acquires a hole, and the FSM later interprets the hole
   as a sequencing violation. "the key was never tracked as `generatedKey`" is reported as
   "invalid sequence of method calls, unknown".

3. **The location names the wrong code.** `__LOC` expands to a *dynamic* stack walk that keeps only
   the top frame. That frame is the immediate caller of the JCA API, which is almost always a
   bundled library: **73.4%** of all errors are attributed to third-party code, `okhttp3.internal
   .platform.Platform` alone accounting for **36.93%**. This is not an attribution bug — it is the
   weaving scope, and it is a deliberate choice that was never revisited.

Put together, the pipeline reduces 97,018 events to **28 findings a developer could act on**
(§2.3) — an amplification factor of 3,465×.

**The good news, and the reason this plan is tractable:** in four of the five things a reader needs,
the data is already in scope at the point of the report and is simply not captured. The generated
monitor knows the current state, the offending event, the legal continuations, and the monitored
object. The weaver knows the calling class, method and (before it destroys it) the source line.
None of it crosses the reporting boundary.

---

## 2. Evidence base

Source: `ase-journal/dataset/results/errors.csv` — 97,018 rows, 163 apps, 11 tools, 3 repetitions,
3 timeouts. Columns: `apk, rep, timeout, tool, time, spec, class, method, message, unique_msg`.

### 2.1 The message distribution

| ErrorType | rows | % | distinct messages |
|---|---:|---:|---:|
| `InvalidSequenceOfMethodCalls` | 70,760 | 72.93% | **1** (`unknown`) |
| `UnsafeAlgorithm` | 15,444 | 15.92% | 12 |
| `UnsafeProtocol` | 8,802 | 9.07% | 3 |
| `InvalidKeyStoreType` | 2,005 | 2.07% | 1 |
| `InvalidKeySize` | 7 | 0.01% | 2 |

**19 distinct messages in 97,018 events.** The whole corpus of diagnostic text produced by this
system fits on one screen.

### 2.2 The shadow-error phenomenon

Grouping by `(apk, rep, tool, spec, class, method)` and pairing each `InvalidSequenceOfMethodCalls`
with a value violation at the same site:

| | events | % of InvSeq |
|---|---:|---:|
| `InvalidSequenceOfMethodCalls` total | 70,760 | 100% |
| — **shadow**: co-occurs with a value error at the same site | 26,152 | 37.0% |
| — **orphan**: no value error at the site; genuinely only reported this way | 44,608 | 63.0% |

**27.0% of the entire CSV is a mute, misclassified duplicate of a violation that was already
reported correctly next to it.**

Per specification the pattern is sharply different, and the difference tells you which fix each
specification needs:

| Spec | InvSeq | shadow | orphan | reading |
|---|---:|---:|---:|---|
| `TrustManagerFactorySpec` | 9,015 | 9,007 | 8 | 99.9% pure duplication |
| `SSLContextSpec` | 17,510 | 8,798 | 8,712 | half and half |
| `MessageDigestSpec` | 10,135 | 5,953 | 4,182 | |
| `KeyStoreSpec` | 8,655 | 2,005 | 6,650 | |
| `CipherSpec` | 10,814 | 109 | 10,705 | almost all mute-only |
| `SecureRandomSpec` | 12,400 | **0** | 12,400 | 100% mute; spec emits nothing else |
| `KeyPairSpec` | 668 | **0** | 668 | 100% mute |
| `MacSpec` | 806 | 31 | 775 | |
| `SignatureSpec` | 748 | 242 | 506 | |
| `KeyPairGeneratorSpec` | 9 | 7 | 2 | |

`TrustManagerFactorySpec` is the cleanest proof: **1,733 of 1,748 sites have byte-identical counts
of `UnsafeAlgorithm` and `InvalidSequenceOfMethodCalls`** (global ratio 1.0001). Every unsafe
algorithm produces exactly one mute twin.

An independent measurement at event granularity — grouping by `(apk, rep, tool, time, spec, class,
method)`, 46,330 distinct events — gives the same picture from the other side: **20,507 events
(44.26%) carry a `unknown` record and a concrete record together**, and **32,232 of the 70,760
`unknown` rows (45.55%) are redundant** in that sense.

### 2.3 The actionability funnel

| Stage | findings | % of CSV |
|---|---:|---:|
| Rows | 97,018 | 100% |
| → distinct `(apk, spec, class, method, message)` | 661 | 0.68% |
| → excluding `message = "unknown"` | 207 | 0.21% |
| → excluding empty observed value (`but found .`) | 136 | 0.14% |
| → excluding third-party library classes | **28** | **0.03%** |

Of those 28, several are benign by construction — MD5 as a non-cryptographic hash in
`Schedule$Item.hashCode`, `DiskCache.getCacheFile`, `GraphWrapper.calculateGraphType` — and three
are `AndroidKeyStore` false positives (§3.7). **Roughly 15–20 genuine security findings survive.**

### 2.4 Attribution

117 distinct classes across 97,018 rows.

| Measure of "third-party" | rows | % |
|---|---:|---:|
| Conservative vendor-prefix list (okhttp3, Google, Kotlin, Ktor, BouncyCastle, AndroidX, Conscrypt) | 82,890 | 85.44% |
| Class outside the app's own package (derived from the APK filename) | 85,384 | 88.01% |

**In 78 of 113 apps (69.0%), not a single error falls inside the app's own package.** The median
per-app fraction of own-code errors is **0.000**. `okhttp3.internal.platform.Platform` alone:
35,828 rows (36.93%).

### 2.5 Volume amplification

| Key | distinct | rows/distinct |
|---|---:|---:|
| `(apk, spec, class, method, message)` | 661 | **146.8×** |
| `(apk, rep, tool, spec, class, method, message)` | 15,748 | 6.2× |
| All 10 columns, `time` included | 85,257 | 1.14× |

**11,761 rows (12.12%) are identical in all ten columns**, `time` included — literally
indistinguishable. The largest single group is 3,098 rows: Ktor's `nonceGeneratorJob` background
loop in one app.

The device-side `HashSet` in `ErrorCollector` is the only deduplication anywhere in the pipeline,
and it is per *process*. Measured on `e3_decisiva_05`, the same `unique_msg` at `Platform.kt:83`
appears 24 times at 24 distinct timestamps; on `exp_00`, one `(apk, rep, tool, unique_msg)` group
has **1,542 rows** in pairs spaced ~16 s apart — periodic activity restart. There is no cap, no
sampling and no rate limit at any point.

### 2.6 Degenerate and malformed messages

| Class | messages | rows | % of CSV |
|---|---|---:|---:|
| Empty observed value (`but found .`) | 5 | 8,843 | 9.11% |
| Missing space (`expecting one ofJCEKS,…`) | 1 | 2,005 | 2.07% |
| Literal ellipsis in the expected set | 1 | 109 | 0.11% |
| Braced set `{a, b}` style | 9 | 14,959 | 15.42% |
| Unbraced `a,b` style | 7 | 11,292 | 11.64% |
| Observed value equals an expected value modulo case | 1 | 4 | 0.004% |

The braced/unbraced split is 57/43 — **two independent message generators coexist**, neither a
corner case. `SHA-1`, `SHA1` and `SHA` — the same algorithm in three spellings — appear as three of
the nineteen distinct messages, together 2,340 rows.

The case-sensitivity defect is demonstrable, not theoretical: the message
`expecting one of SHA256withRSA,… but found SHA256WITHRSA` reports as a violation a value that **is
in its own expected list**, differing only in case. JCA algorithm names are case-insensitive by
specification. Four rows, all from BouncyCastle's `JcaContentVerifierProviderBuilder`, which
uppercases the name internally before the JCA call.

---

## 3. Root-cause analysis

Seven independent layers. They compose; none subsumes another.

### L1 — The mute constructor

`ErrorDescription` has exactly two constructors (`ErrorDescription.java:34-44`). The 3-argument one
writes the literal `"unknown"` into the `expecting` field. Not a field default, not a getter
default, not a `toString` fallback — a literal written at construction time.

Inventory of the 50 live `addError` call sites in `jca/`: **25 use the 3-argument form**, 25 use the
4-argument form. Of the 25 mute ones, 23 emit `InvalidSequenceOfMethodCalls` (21 `@fail` handlers +
`PBEKeySpecSpec.mop:24` and `:30`, which are in *event bodies*) and 2 emit `UnsatisfiedConstraint`
(`IvParameterSpec.mop:48` and `:55`).

`jca_android/` has the same 25 mute sites, unchanged, plus 24 additional 4-argument sites. **No
sequence `@fail` gained a message in the Android variant.**

### L2 — The FSM sink, and the orphan-event pattern

`@fail` is not "an event with no transition". The generator builds a *total* transition function
with an explicit dead state, and the category is evaluated on *state*:

```java
// results/gh99_jca_android_monitors/monitors/MultiSpec_1RuntimeMonitor.java:7345-7349
static final int Prop_1_transition_g1[]              = {2, 3, 3, 3};
static final int Prop_1_transition_g2[]              = {2, 3, 3, 3};
static final int Prop_1_transition_unsafe_protocol[] = {3, 3, 3, 3};   // always fails
static final int Prop_1_transition_init[]            = {3, 3, 1, 3};
static final int Prop_1_transition_engine[]          = {3, 1, 3, 3};
// after every event:  Category_fail = (Prop_1_state == 3);
```

The mechanism in the generator: the ERE plugin builds the DFA over the **entire declared alphabet**
(`ere/EREPlugin.java:21-33`), and for symbols whose derivative is empty it simply emits no
transition (`ere/FSM.java:52-58`). The FSM pipeline then completes the missing entries as default
transitions into the distinguished `fail` state (`fsm/FSMMin.java:24-28,53-55`), and
`fsm/JavaFSM.java:158` sets `fail condition` to `$state$ == countState`.

**Consequence: any event declared in a specification but absent from its `fsm:`/`ere:` block sends
the monitor straight to `fail`.** Eighteen such orphan events exist in `jca/`, and every one of them
was created precisely to report a *specific* error:

| Spec | orphan event(s) | line(s) | what it was meant to report |
|---|---|---|---|
| `SSLContextSpec` | `unsafe_protocol` | `:46` | unsafe protocol |
| `TrustManagerFactorySpec` | `g3` | `:44` | unsafe algorithm |
| `SignatureSpec` | `g3` | `:45` | unsafe algorithm |
| `SecureRandomSpec` | `c3`, `g4`, `setSeed3` | `:43,76,95` | non-random seed / unsafe algorithm |
| `KeyPairGeneratorSpec` | `initError` | `:92` | invalid key size |
| `PBEKeySpecSpec` | `f1`, `f2`, `err1`, `err2`, `err3` | `:21,27,45,53,61` | wrong ctor / iterations / randomness |
| `SecretKeySpecSpec` | `c3`, `c4` | `:41,51` | algorithm / key material |
| `IvParameterSpec` | `c3`, `c4` | `:42,51` | non-random IV |
| `PBEParameterSpecSpec` | `c3` | `:42` | iterations / salt |
| `MessageDigestSpec` | `reset` | `:74` | **nothing — this is legitimate API use** |

Firing order matters and makes the duplication deterministic: the user's event body is emitted
*before* the transition and category computation (`BaseMonitor.java:428-453`). So an event that
reports `UnsafeAlgorithm` in its body **and** transitions to `fail` emits both records, informative
first.

This is the structural origin of the volume in §2.2, and it also produces **false positives on
correct, common code**:

| Code | Why it fails |
|---|---|
| `sr.nextBytes(b1); sr.nextBytes(b2);` | `next2` has a transition in state `init` (`SecureRandomSpec.mop:151`) but **not in `end`** (`:155-161`) |
| `SSLContext.getInstance("TLS")` | `unsafe_protocol` orphan → sink, and **no** `UnsafeProtocol` is emitted (that test lives in `init`'s body, `:56-59`) |
| `cipher.doFinal()` | state `s2` accepts `f2,f5,f6,f7` but **not `f1`** (`CipherSpec.mop:176-187`) |
| `md.reset()` | `reset` declared `:74`, absent from the ERE at `:108` |
| `kpg.generateKeyPair().getPublic()` | `KeyPairSpec.c1` is the *constructor* `new KeyPair(pub,priv)` (`:24`); `gpu` without a preceding `c1` fails immediately |
| second `cipher.init(...)` to reuse for decryption | state `end` has no `i1`/`i2` (`:196-207`) |

The `MessageDigestSpec.mop:48-52` comment shows the authors had already met this phenomenon and
patched **one** instance of it:

> *"We no longer throw errors after unsafe instantiation events, otherwise we would throw
> InvalidSequenceOfMethodCalls… Not throwing here eliminates the false positive in
> bench02.BrokenHashABPSCase1"*

The mechanism (L2) remained active for `reset` in the same file.

### L3 — Predicate failure is silent

`BaseMonitor.getHandlerCallingCode` (`:604-610`) wraps all handler dispatch in
`if (RVM_conditionFail) { … = false; } else { <handlers> }`. **A false `condition` does not
transition and does not fire `@fail` — the event simply disappears.**

CrySL's `REQUIRES` was translated into exactly such a condition. The clean case:

```java
// jca/MacSpec.mop:43-53
event i1 before(java.security.Key key, Mac m):
  call(public void Mac.init(java.security.Key)) &&
  args(key) && target(m) &&
  condition(ExecutionContext.instance().validate(Property.GENERATED_KEY, key)) {
```

If the key was not tracked, `i1` is never generated, the observed trace becomes `g1 f1`, the ERE
(`:83`) requires `(i1|i2)` between them, and the monitor lands in the sink. CogniCrypt would say
`"[key] was not properly generated as generatedKey"` (`RequiredPredicateError.java:42-50`).

Two aggravations:

**The predicate graph is largely inert.** Of 24 `Property` values, **18 are written and never read**.
`GENERATED_PRIVATE_KEY` is read (`CipherSpec.mop:72`) and **never written** — permanently false.
`KeyPairSpec.mop:38` writes the *private* key under `GENERATED_PUBLIC_KEY`. The entire `REQUIRES`
branch of `Cipher.crysl:138-141` (IV, GCM, OAEP) is dead, even though the parameter specifications
compute those predicates correctly.

**The randomness predicate is poisoned at the source.** `SecureRandomSpec.mop:111-116` marks the
*argument* `randIntInRange` — the upper bound — as `RANDOMIZED`, not the return value; the `TODO` at
`:110` admits the doubt. Every downstream `validate(Property.RANDOMIZED, …)` in `IvParameterSpec`,
`PBEKeySpecSpec`, `GCMParameterSpecSpec` and `SecretKeySpecSpec` inherits the error.

**Three specifications detect nothing at all.** `DHGenParameterSpecSpec`, `GCMParameterSpecSpec` and
`HMACParameterSpecSpec` are object-parameterised monitors with a single constructor event guarded by
a condition. A malformed object drops the event (L3); `@fail` is unreachable. They are dead weight.

### L4 — There is no end-of-trace check

`terminateInternal` for `SSLContextSpec` (`MultiSpec_1RuntimeMonitor.java:7505-7530`) is a `switch`
in which every case is a bare `return`. A live-but-incomplete prefix is never reported.

`grep` for `@end`/`__END` across `jca/`: zero. `fail` is reachable only by transition
(`JavaFSM.java:158`).

**CrySL's `IncompleteOperationError` does not collapse into the mute bucket — it does not exist.**
An `SSLContext` that does `getInstance` and never `init`, a `Cipher` that is initialised and never
used, a `KeyStore` loaded and never read: all die in silence. This is a whole class of misuse the
system currently cannot see.

### L5 — Localisation

**L5a — Only one frame survives.** `__LOC` is a *textual substitution performed by the generator*,
not a runtime token. It is replaced at `BaseMonitor.java:361-362`, `RawMonitor.java:104-105` and
`HandlerMethod.java:45` with the value in `Util.java:7-8`:

```java
public static final String defaultLocation = "com.runtimeverification.rvmonitor.java.rt."
        + "ViolationRecorder.getLineOfCode()";
```

and `getLineOfCode` (`ViolationRecorder.java:53-60`) collects the whole relevant stack and returns
`relevantStack.get(0).toString()`. **N−1 frames are discarded on every violation.** The one frame
kept is the immediate caller of the JCA API. The application frame that would let a developer act is
in the collected list and is thrown away.

**L5b — The weaving scope includes all libraries.** This is the cause of §2.4, and it is a policy,
not a bug. `BatchRunner.java:395-422` extracts every `classes*.dex`; `DexWeaver.java:359` iterates
all classes with no package predicate. The only gate is `commonPointcut`, fixed in
`javamop/…/DescriptorWriter.java:68-70`, whose exclusion list (`DescriptorWriter.java:233-249`,
verified) is exactly twelve prefixes:

```
sun..*  java..*  javax..*  com.sun..*  org.dacapo.harness..*  org.apache.commons..*
org.apache.geronimo..*  net.sf.cglib..*  mop..*  javamoprt..*  rvmonitorrt..*  com.runtimeverification..*
```

None covers `android.`, `androidx.`, `kotlin.`, `com.google.` or `okhttp3.`. There is no allowlist
and no CLI option for scope (full inventory: `InstrumentationCli.java:39-115`).

Worse, **two divergent scope policies live in the same module**: `PackageFilter.java:22-43`, used
only by the coverage weaver, *does* exclude `android`, `androidx`, `kotlin` and `com.google` — and
still does not exclude `okhttp3`.

**L5c — Debug info is destroyed in a large class of methods.** `RegisterShifter.cloneInstructions`
(`RegisterShifter.java:174-267`) builds its destination with the **empty**
`MutableMethodImplementation(int)` constructor, not the copying one. It re-copies instructions in
three passes and re-installs try-blocks explicitly; its own javadoc enumerates what it carries over
and **debug items are not among them**. The writer then emits `debug_info_off = 0`
(`DexWriter.java:1156-1159`).

Four production routes reach it; the highest-volume is `CoverageWeaver.injectLogCall →
spillLowRegisters` for methods with `localCount < 1`, whose javadoc admits *"extremely common —
getters / setters / one-liners"*, with `--coverage` defaulting to `true`
(`InstrumentationCli.java:104-106`).

Effect on the reported frame:

| Method | `StackTraceElement.toString()` |
|---|---|
| untouched, or wrapper-substituted | `com.app.Foo.bar(Foo.java:117)` |
| **passed through `cloneInstructions`** | `com.app.Foo.bar(Foo.java)` — **no line** |
| class without `source_file_idx` (R8) | `com.app.a.b(Unknown Source)` |

The degradation is binary and silent per method. There is no test in the module that checks debug
info preservation. Wrapper substitution itself is innocent — `InstructionInjector.replaceInvoke`
reuses the `MethodLocation`, which dexlib2 treats as transparent.

**L5d — The generator's static localisation was disabled, not omitted.** `rv-monitor` had a
per-monitor `RVM_loc` field fed from the aspect's join point. It is commented out at
`BaseMonitor.java:363,484-487,790`, `RawMonitor.java:161-164,235`, `SuffixMonitor.java:246-249`,
`MonitorSet.java:300-303,648`. The variable is still declared (`SuffixMonitor.java:27`) and method
signatures still carry the unused `loc` parameter. The dynamic stack walk is the fallback that
survived.

**L5e — The site is statically recoverable.** In the weaving loop (`DexWeaver.java:359-413`) the
calling `classDef`, the calling `method`, the instruction index `idx`, the callee's
`MethodReference` and — while the original debug info still exists — the `DebugItem` are all in
scope. Proof of feasibility is in the same module: `SignatureFormatter.java:27-40` formats exactly
such a string and `CoverageWeaver.java:181-183` materialises it as a `const-string` in the DEX.

What is missing is the **channel**, not the information. And there is a hard constraint on the
obvious channel: the wrapper is **one per signature, not one per site** (`DexWeaver.java:146-147`,
with a collision guard at `:170-176`). Passing the site as a wrapper argument would require one
wrapper per site; adding a register would trigger `bumpRegisterCount` → clone → and thereby destroy
the caller's debug info (L5c).

**L5f — Latent, not observed.** `ViolationRecorder.makeRelevantList` (`:87-105`) guards its whole
exclusion with `fileName != null && className != null`. When `getFileName()` returns null the guard
is false and the frame is **kept** — including RV frames. The generated classes are `mop.
MonitorWrappers`, `mop.Coverage`, `mop.MultiSpec_<N>RuntimeMonitor`, all matching the `mop.` prefix,
so today they are correctly excluded. But `monitor-builder` invokes `javac` with no explicit `-g`
(`MonitorBuilder.java:87-101`) and relies on the compiler default. Measured on this dataset: 0 rows
with `class == method`, 0 with `Unknown Source`. **Latent fragility, not an active defect.**

### L6 — Identity and deduplication

`ErrorSummary.equals/hashCode` (`:73-120`) uses `(spec, error, classQualifiedName, methodName,
location)`. `ErrorDescription.equals/hashCode` (`:109-139`) delegates entirely to it. **The message
is not part of identity.** The javadoc states the consequence:

> *"`expecting` is not part of the identity, so two reports of the same violation that differ only
> in the expected value are one record, and which of the two survives an in-JVM `HashSet` is arrival
> order."*

Two consequences, one of them serious:

- The same method using MD5 on one call and SHA-1 on another, at the same line, yields **one**
  record with an arbitrary reported value.
- **A mute record that arrives first permanently suppresses its informative twin at the same site.**
  Combined with L2's deterministic double-fire, this is a live data-loss path.

Three deduplication keys coexist and none equals another:

| Layer | Key | Includes line? | Includes message? |
|---|---|---|---|
| In-JVM (`ErrorCollector`) | `(spec, errorType, class, method, file:line)` | **yes** | no |
| `unique_msg` (Python) | `(class, method, spec, errorType, message)` | no | **yes** |
| Article/thesis analysis | `(apk, class, method, spec)` | no | no |

### L7 — Transport and schema

The device emits a **7-field, comma-separated, unescaped** line:

```java
// rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java:36-42
String message = err.getErrorSummary() + "," + err.getExpecting().trim();
//Log.v("RVSEC", escapeSpecialCharacters(message));
Log.v("RVSEC", message);
```

→ `spec , classFQN , simpleClass , method , File.java:line , errorType , expecting`

`escapeSpecialCharacters` exists (`:44-51`) and its call is **commented out**. The JSE sibling
(`rvsec-logger-csv/.../ErrorCollector.java:41`) *does* escape and declares the canonical header
`spec,class,className,method,location,error,expecting`. **The two branches diverge.**

Today this survives only because the message is the last field and the parser rejoins it
(`logcat_parser.py:348`, `",".join(parts[6:])`). Any new field placed after `message` breaks
everything; any new field before it must be provably comma-free. A newline in a message splits the
logcat line and the orphan half is dropped with a `logging.warning` and no counter (`:369-371`) —
this is the already-known A8 residue.

**The four specification sets do not share a reporting mechanism.**

| Set | files | mechanism | `addError` sites |
|---|---:|---|---:|
| `jca/` | 23 | `ErrorCollector`/`ErrorDescription` in 21 | 51 (25 mute / 26 with message) |
| `jca_android/` | 23 | same, in 21 | 75 (25 mute / 50 with message) |
| `generic/` | 118 | `android.util.Log.v` **direct**, 118/118 | 0 |
| `generic_new/` | 27 | `android.util.Log.v` **direct**, 27/27 | 0 |

`generic/` emits one fixed boilerplate, 118 times identically
(`generic/FSM100.mop:43-47`): `__LOC + " ::: FSM100 went into an error state."` — no `ErrorType`, no
observed value, no simple class name. It does not even import `br.unb.cic.mop.eh`.

**On the schema-convergence thesis.** The intuition that the CSV schema is a lowest common
denominator is directionally right but the mechanism is worse than omission: **the parser
fabricates the missing fields.**

```python
# rv-coverage/.../logcat_parser.py:305-316  (Format 1, the generic path)
return RvErrorLog(
    generic["spec"],
    generic["spec"],       # <-- error_type := spec   FABRICATED
    generic["class"],
    generic["method"],
    generic["file_name"],  # <-- source WITHOUT the line number
    generic["message"],    # <-- FABRICATED at :397
)
```

```python
# :366-368  (Format 3, the generic_new path)
return RvErrorLog(spec, spec, clazz, method, "Unknown Source:1", message_text)
```

`RvErrorLog` has had six fields all along (`log.py:62-75`); no field was ever dropped to
accommodate `generic`. What happens is that `error_type := spec` and `source := "Unknown Source:1"`
are written as if they were real. **An analyst counting `error_type` over a mixed CSV will read
`FSM101` as an error type, with nothing in the file marking it synthetic.**

The two missing CSV columns have separate, unrelated causes:

- **`source`** was absent because the era's writer did not emit it
  (`backup/rvandroid/experiment/workflow/result_manager.py:311-314`, 10 columns). The current
  writer emits **11 columns including `source`** (`result_processor.py:562-576`, added by
  `cf234788`, 2026-07-28). Five `errors.csv` files under `results/` already carry the 11-column
  header. Nothing to fix for the next campaign — but the column must be *used*.
- **`error_type`** has never been a column in any writer, in any era. It lives inside `unique_msg`
  by an identity decision documented at `log.py:88-112`. Extracting it costs
  `str.split(":::").str[3]`.

### L8 — Specification defects that are independent of all of the above

These would corrupt the next campaign even with a perfect reporting layer. Full register in §8.

**Pointcuts that can never match** (return type wrong; the generated aspect preserves the error
literally):

| Spec | line | declared | actual JDK signature | aspect |
|---|---|---|---|---|
| `SignatureSpec` | `:99` | `public byte Signature.sign()` | `byte[]` | `.aj:979` |
| `SignatureSpec` | `:106` | `public byte Signature.sign(byte[],int,int)` | `int` | `.aj:984` |
| `TrustManagerFactorySpec` | `:62` | `public KeyManager[] getTrustManagers()` | `TrustManager[]` | `.aj:1037` |

**`SignatureSpec`'s entire signing branch is unsatisfiable.** A correct
`getInstance/initSign/update/sign` flow can never reach `@match` and always ends in a mute `@fail`.

**Messages that contradict their own condition:**

| Site | message says | condition is |
|---|---|---|
| `PBEKeySpecSpec.mop:50` | `"third argument should be >= 1000"` | `iterationCount < 10000` (`:48`) |
| `PBEParameterSpecSpec.mop:50` | `"at least 1000 iterations"` | `iterationCount < 10000` (`:46`) |
| `MessageDigestSpec.mop:70,92` | `{SHA-256, SHA-384, SHA-512}` | list at `:16` has **six** entries |
| `SSLContextSpec.mop:58` | `{TLSv1.2, TLSv1.3}` | list at `:23` is uppercase `TLSV1.2/TLSV1.3` |

**Wrong `ErrorType`:** `PBEParameterSpecSpec.mop:49` reports an iteration-count/salt violation as
`ErrorType.UnsafeAlgorithm`.

**A latent NPE inside a monitor:** `KeyPairGeneratorSpec.mop:29` does `switch(algorithm)` on a field
declared without an initialiser at `:26`. When `initialize(int)` runs on a generator whose
`getInstance` was not woven, `algorithm` is `null` and the switch throws — *inside a pointcut
condition*.

**Condition tests the wrong variable:** `KeyGeneratorSpec.mop:47` and `MessageDigestSpec.mop:55`
test `currentAlgorithmInstance` (the *previous* value) instead of the incoming `alg`. Effect:
`getInstance("SHA-256")` followed by `getInstance("MD5")` generates **no event at all** for the MD5
call — a false negative.

**CrySL constraint divergences:** `CipherTransformationUtil.isValid` rejects the eight
`PBEWithHmacSHA*AndAES_*` transformations that `Cipher.crysl:90-105` explicitly accepts —
guaranteed false positives. Its case handling is asymmetric within one function: algorithm
comparison is case-**sensitive** (`:44`), mode case-**sensitive** (`:45`), padding case-**insensitive**
(`:46,65`). So `AES/CBC/pkcs5padding` is valid while `aes/CBC/PKCS5Padding` is not.

**`AndroidKeyStore` reported as an invalid keystore type** — 2,005 rows, 2.07% of the CSV. The
expected list in `jca/KeyStoreSpec.mop:23` is the JSE list; `AndroidKeyStore` is the
hardware-backed provider *recommended* by the platform. `jca_android/KeyStoreSpec.mop:23` already
fixes this (`AndroidCAStore, AndroidKeyStore, BKS, BouncyCastle, PKCS12`).

**34 of the 118 `generic/` specifications are inert on Android** — they import `java.awt`,
`javax.swing` or `java.beans`. The effective set is ≤ 84.

**Two `generic_new/` specifications are unparseable.** `ServerSocket_Backlog.mop:20` and
`TreeMap_Comparable.mop:23` emit with the literal prefix `"[helper]"` (because `__LOC` does not
expand inside a helper method), which has no `.` and no `(`; Format 3 requires `dot_idx != -1`
(`:361`) and the row is dropped.

---

## 4. What an actionable report must contain

A runtime-verification report supports a decision when it answers five questions. CogniCrypt/CrySL
answers all five; RVSEC currently answers, at best, part of one.

| # | Question | CrySL's answer | RVSEC today |
|---|---|---|---|
| **Q1** | What happened? | `TypestateError`: *"Unexpected call to method `X` on object of type `T`"* (`TypestateError.java:41-64`) | **absent**. `RVM_lastevent` holds the offending event id and is ignored |
| **Q2** | Why is it a violation, and what was expected? | *"Expect a call to one of the following methods: A, B, C"*; for constraints, the accepted value set | **partial**. Good on the value branch (with the defects of §2.6); absent on the order branch |
| **Q3** | Where, in code the developer owns? | statically resolved call site | **degraded**. 73.4% in libraries; `source` computed and dropped; line number destroyed in many methods |
| **Q4** | What is the consequence, and what should I do? | named categories + remediation hints, e.g. *"[ with CBC, It's required to use IVParameterSpec]"* (`RequiredPredicateError.java:51-54`) | **absent entirely** |
| **Q5** | Which object? | per-allocation-site | **absent**. The monitored object is in scope at `@fail` and only used to unset a property |

**The critical observation for planning:** for Q1, Q2, Q3 and Q5 the data is already present at the
report site.

- `Prop_N_state` — current state, and `getState()` (`:3616-3618`).
- `RVM_lastevent` — offending event id, declared at `BaseMonitor.java:106`, assigned at `:428`,
  readable via `getLastEvent()` (`:3619-3621`).
- `static final int Prop_N_transition_<ev>[]` — **the legal continuations from any state are
  derivable by indexing**, and the tables are compiled into the monitor.
- All specification variables (`currentAlgorithmInstance`, `currentProtocol`, `currentKSType`,
  `currentTransformation`) and the monitored object — all instance fields, all alive.

Two mechanical facts make this cheap:

1. **The `@fail` body is inlined verbatim into the monitor class**, and `Prop_N_handler_fail()` is an
   *instance method of the class that declares those fields*. Java written in a `.mop` `@fail` block
   can reference `Prop_1_state` and `RVM_lastevent` directly — **no generator change required**.
2. **`__RESET` does not clear specification variables.** `HandlerMethod.java:39` maps it to
   `this.reset()`, and the generated `reset()` (`BaseMonitor.java:951-973`) re-emits
   `localDeclaration` but *not* `monitorDeclaration` (emitted once at `:786`). The observed
   algorithm/protocol survives.

Seven of the 21 `@fail` handlers *already* read those fields on the line after the mute `addError`,
to clear `ExecutionContext` properties. The context was alive, in hand, and dropped from the message.

What is genuinely *not* in scope at `@fail` is the offending event's **arguments** — those are
parameters of the generated event method, not fields. That is a real JavaMOP limitation, and it is
exactly why specifications that want to report values copy them into fields.

Symbolic names for states and events exist in the `.mop` and in
`MultiSpec_1MonitorAspect.json` (`"eventId": "c1"`, 115 advices) and are degraded to **comments** in
the generated Java (`MultiSpec_1RuntimeMonitor.java:8703-8712`). No `int → String` table is emitted.

---

## 5. The plan

Eight workstreams. **WS-1 through WS-4 are specification-level and buy most of the value.** WS-5 and
WS-6 touch shared infrastructure and need decisions. WS-7 is a defect backlog that must be cleared
regardless. WS-8 is the cross-set unification.

Blast radius legend: **S** = `.mop` files only · **C** = `rvsec-core` · **M** = `rv-monitor` /
`rv-monitor-rt` (affects every consumer) · **I** = dexlib2 instrumenter · **P** = Python
parser/writer.

---

### WS-1 — Give the sequence `@fail` a message

**Goal:** eliminate `unknown` as a value. Answer Q1, Q2 and Q5 from data already in scope.

**Why it is cheap:** §4's two mechanical facts. This is a `.mop` edit, nothing else.

| Step | Change | Radius |
|---|---|---|
| 1.1 | In each of the 21 `@fail` handlers, switch to the 4-argument `ErrorDescription` constructor | S |
| 1.2 | Compose the message from `Prop_N_state`, `RVM_lastevent`, the monitored object's identity hash, and the specification variables already in scope | S |
| 1.3 | Emit a `static final String[]` state-name and event-name table per specification, hand-written in the `.mop` declarations block, so the message reads `state=waitingInit event=getTrustManagers` rather than `state=2 event=4` | S |
| 1.4 | Derive the legal continuations by indexing the transition tables and include them: *"expected one of: init"* | S |
| 1.5 | Do the same for the 4 non-`@fail` mute sites (`IvParameterSpec.mop:48,55`; `PBEKeySpecSpec.mop:24,30`), where the event parameters **are** in scope and carry the answer directly | S |

**Alternative to 1.3/1.4, to evaluate:** emit the tables from the generator instead of by hand
(`BaseMonitor`/`HandlerMethod`). Radius **M**, benefits all four specification sets, but touches
shared infrastructure and cannot be validated by a `.mop`-only test. **Recommendation: hand-written
first, generator change only if WS-1 proves the message design.**

**Risk:** the message becomes a comma-bearing free-text field. Safe *only* while it stays the last
positional field (L7/R3).

**Verification:** zero rows with `message = "unknown"`; for a synthetic app exercising each failure
mode of `SSLContextSpec`, six distinct messages for the six modes of §3/L2.

---

### WS-2 — Eliminate the orphan-event pattern

**Goal:** stop reporting value violations as sequence violations. Removes ~27% of the volume and a
false classification.

| Step | Change | Radius |
|---|---|---|
| 2.1 | For each of the 18 orphan events (§3/L2 table), give it an explicit transition — either a self-loop that keeps the automaton in place, or an explicit `unsafeAlg`-style state | S |
| 2.2 | Use `KeyManagerFactorySpec` as the reference: it *already* has `g3 → unsafeAlg` (`:68`) while its twin `TrustManagerFactorySpec` does not. **Fix the asymmetry between the twins.** | S |
| 2.3 | Remove `MessageDigestSpec.reset` from the alphabet or add it to the ERE — it is legitimate API use and must never fail | S |
| 2.4 | Add the missing `next2` transition in `SecureRandomSpec`'s `end` state (`:155-161`) | S |
| 2.5 | Review `CipherSpec` state `s2` for the missing `f1` (`doFinal()`), and state `end` for re-`init` (cipher reuse) | S |
| 2.6 | Reconsider `KeyPairSpec.c1`: keying the protocol on the `KeyPair` *constructor* makes the normal `generateKeyPair()` path fail immediately | S |

**This changes measured semantics.** Violation counts will drop and their distribution will shift.
It is a correction, not a regression — but it must be recorded as a deliberate break in
comparability with prior campaigns. See D-2.

**Verification:** a synthetic suite exercising each of the six false-positive patterns in §3/L2
produces **zero** violations.

---

### WS-3 — Make a missing predicate a first-class error

**Goal:** stop `RequiredPredicateError` from masquerading as a sequencing failure (L3).

| Step | Change | Radius |
|---|---|---|
| 3.1 | Add `ErrorType.MissingRequiredPredicate` (or reuse `UnsatisfiedConstraint`) | C |
| 3.2 | Invert the pattern: instead of `condition(validate(P, x))` suppressing the event, let the event fire and test `P` **in the body**, reporting *"`x` was not established as `generatedKey`"* — the shape `SecureRandomSpec.mop:100-101` already uses, and the only counterexample in the whole set | S |
| 3.3 | Fix the poisoned source: `SecureRandomSpec.mop:111-116` marks the argument, not the return value | S |
| 3.4 | Fix `KeyPairSpec.mop:38` (private key written under `GENERATED_PUBLIC_KEY`) and populate `GENERATED_PRIVATE_KEY` | S |
| 3.5 | Decide the fate of the 18 write-only `Property` values: wire the readers, or delete them (P3 — no dead code) | S/C |
| 3.6 | Note that `preparedIV`/`preparedGCM`/`preparedOAEP` are *computed correctly* by the parameter specs and never read — this is the cheapest reachable win in the predicate graph | S |

**Prerequisite for 3.6:** CrySL rules with no `.mop` counterpart make some `REQUIRES` unsatisfiable
by construction — notably `SecretKeyFactory` (source of `generatedKey` for the PBE flow) and
`ECGenParameterSpec`/`RSAKeyGenParameterSpec`/`DSAGenParameterSpec`/`DHParameterSpec` (sources of
`preparedEC`/`preparedRSA`/`preparedDSA`/`preparedDH`, required by `KeyPairGenerator.crysl:35-38`).
**Implementing those `REQUIRES` without first adding these specs would create false positives.**
See D-4.

---

### WS-4 — Detect incomplete operations

**Goal:** recover the missing `IncompleteOperationError` (L4).

| Step | Change | Radius |
|---|---|---|
| 4.1 | Decide the mechanism: a `@violation`-style end-of-trace handler in the generator, or a device-side sweep at process teardown over live monitors not in an accepting state | M or C |
| 4.2 | The message should name the *missing* continuation, which is derivable from the transition tables exactly as in WS-1.4 | S |
| 4.3 | Assess the volume risk: on Android, objects are abandoned constantly and process death is routine. An aggressive end-of-trace check could produce more noise than the current mute bucket | — |

**This is the highest-uncertainty workstream.** It adds a whole error class that has never been
measured. **Recommendation: prototype and measure on a small app set before committing it to a full
campaign.** See D-5.

---

### WS-5 — Fix localisation

**Goal:** point at code the developer owns, with a line number.

| Step | Change | Radius | Note |
|---|---|---|---|
| 5.1 | `getLineOfCode()` returns more than one frame — minimally `(immediate caller, first application frame)` | M | affects every rv-monitor consumer |
| 5.2 | Add an *application-package* filter so the "first application frame" is well defined | M/C | requires knowing the app package at runtime |
| 5.3 | Harden `makeRelevantList`'s `fileName != null` guard (L5f) and pin `javac -g` in `MonitorBuilder` | M/I | latent, cheap, do it |
| 5.4 | **Preserve debug items in `RegisterShifter.cloneInstructions`** (L5c) | I | *the highest-value single fix in this workstream* — restores line numbers for every getter/one-liner |
| 5.5 | Add a regression test for debug-info preservation; there is none today | I | |
| 5.6 | Decide the weaving scope (L5b): keep whole-APK, or introduce an app-package allowlist | I | **changes the coverage denominator** — see D-3 |
| 5.7 | Reconcile the two divergent scope policies (`DescriptorWriter.java:233-249` vs `PackageFilter.java:22-43`) | I/M | |
| 5.8 | Consider re-enabling the static join-point location (`RVM_loc`, L5d) instead of the stack walk | M | removes a `new Exception()` per violation under the global lock — also a performance win |
| 5.9 | Emit a per-site weave manifest `(class, method, callee, line)` so a runtime error can be traced back statically | I | none exists today (`WeaveReport` is a vector of integers) |

**Explicitly rejected:** passing the site as a wrapper argument. The wrapper is one-per-signature
(`DexWeaver.java:146-147`); a per-site wrapper plus an extra register would trigger
`bumpRegisterCount` → clone → and destroy the caller's debug info. Self-defeating.

**Note on scope (5.6).** Keeping libraries in scope is defensible: an app *is* responsible for the
crypto its dependencies perform. But then the report must **label** the finding as library-origin
and name the application frame that reached it (5.1/5.2). Excluding libraries is the other coherent
option. **Reporting a library finding as if it were app code, with no app frame, is the only
incoherent option — and it is what happens today.**

---

### WS-6 — Identity, deduplication and schema

**Goal:** stop losing informative records, and stop fabricating fields.

| Step | Change | Radius |
|---|---|---|
| 6.1 | Include the message in `ErrorSummary`'s identity, or at minimum ensure an informative record replaces a mute one rather than being suppressed by arrival order (L6) | C |
| 6.2 | Add `error_type` as a **first-class CSV column** — it is the most structuring dimension of the dataset and today exists only inside `unique_msg` | P |
| 6.3 | **Use** the `source` column that `result_processor.py:562-576` already writes | P |
| 6.4 | Add an `is_library` (or `origin`) column so the app/library distinction is not re-derived by prefix heuristics in every consumer | P |
| 6.5 | Stop fabricating. When `generic`/`generic_new` cannot supply `error_type` or a real `source`, emit an explicit sentinel that is *distinguishable* from real data — never `error_type := spec`, never `source := "Unknown Source:1"` (L7) | P |
| 6.6 | Re-enable escaping in the logcat `ErrorCollector` (`:39`) and align it with the JSE collector, which already escapes and declares the canonical header (L7/R10) | C |
| 6.7 | Decide on report suppression: the per-process `HashSet` is defeated by activity restart, producing 1,542-row groups. Options: a persistent key, a rate limit, or downstream aggregation | C/P |

**6.6 is a prerequisite for any message redesign.** While escaping is off and the parser splits
positionally, the message must remain the last field.

---

### WS-7 — Clear the specification defect backlog

These are independent of the reporting redesign and would corrupt the next campaign on their own.
Full register in §8. Priority order:

1. The three never-matching pointcuts (`SignatureSpec.mop:99,106`; `TrustManagerFactorySpec.mop:62`)
   — **`SignatureSpec`'s signing branch is currently unsatisfiable**.
2. The `KeyPairGeneratorSpec.mop:29` NPE.
3. The two order-of-magnitude message/condition contradictions (`PBEKeySpecSpec.mop:50`,
   `PBEParameterSpecSpec.mop:50`).
4. The `currentAlgorithmInstance`-instead-of-`alg` condition bug (`KeyGeneratorSpec.mop:47`,
   `MessageDigestSpec.mop:55`) — a *false negative* generator.
5. `PBEParameterSpecSpec.mop:49` using `UnsafeAlgorithm` for an iteration-count violation.
6. Case-insensitive algorithm comparison throughout, plus hyphen normalisation
   (`SHA-1`/`SHA1`/`SHA`). Removes demonstrable false positives.
7. `CipherTransformationUtil` divergences from `Cipher.crysl`: the eight rejected
   `PBEWithHmacSHA*AndAES_*` transformations, the extra `CCM` mode, and the asymmetric case handling.
8. Message formatting: the missing space (`KeyStoreSpec.mop:67`, `KeyGeneratorSpec.mop:63`), the
   literal ellipsis (`CipherSpec.mop:60,75`), the missing `expecting` (`MacSpec.mop:62`), and the
   hard-coded lists that disagree with the code (`MessageDigestSpec.mop:70,92`).
9. Decide the fate of the three specs that detect nothing (`DHGenParameterSpecSpec`,
   `GCMParameterSpecSpec`, `HMACParameterSpecSpec`) — fix or delete (P3).
10. `HMACParameterSpecSpec` targets `javax.xml.crypto.dsig.spec.HMACParameterSpec`, **absent from
    Android** — inert in the Android arm regardless.

---

### WS-8 — Unify the four specification sets

**Goal:** one reporting contract, so the parser stops fabricating.

| Step | Change | Radius |
|---|---|---|
| 8.1 | Decide whether `generic`/`generic_new` migrate to `ErrorCollector` (145 files, 44 `Log.v` sites in `generic_new` alone) or keep the direct-log path with an explicit, parseable, self-describing format | S/C |
| 8.2 | If they migrate: note that `ErrorCollector`'s `HashSet` deduplicates while the current `__RESET`+re-emit path does not — **the counts change**, breaking comparability | S/C |
| 8.3 | Prune the 34 `generic/` specs that import AWT/Swing and are inert on Android | S |
| 8.4 | Fix the two unparseable `generic_new` specs (`ServerSocket_Backlog.mop:20`, `TreeMap_Comparable.mop:23`) before the set is ever enabled | S |
| 8.5 | Register `generic_new` in the CLI — it is absent from `click.Choice` (`rv_experiment/__main__.py:443`) and from the mapping in `config.py:688-694`; today it is reachable only via `--specification-set custom` | P |
| 8.6 | Make `@severity` real: it exists in all 27 `generic_new` specs but lives **inside a javadoc block** (`CharSequence_NotInSet.mop:17`) and is inert at runtime. Severity is exactly the Q4 field the reports lack | S/C |
| 8.7 | Note the parser's discrimination is a literal suffix match — `message.endswith("went into an error state.")` (`logcat_parser.py:306`) — with no `else` branch. Changing that sentence in 118 files without changing the parser silently reroutes those rows into the comma-split path | P |

---

### Sequencing

```
Phase A (spec-only, no infrastructure risk, largest value)
  WS-7 (defect backlog)  →  WS-2 (orphan events)  →  WS-1 (fail messages)  →  WS-3 (predicates)

Phase B (infrastructure, needs decisions)
  WS-6.6 (escaping)  →  WS-6.2/6.3/6.4 (schema)  →  WS-5.4/5.5 (debug info)  →  WS-5.1/5.2 (frames)

Phase C (measured prototypes before commitment)
  WS-4 (incomplete operations)  ·  WS-5.6 (scope)  ·  WS-8 (set unification)
```

Phase A alone should take `unknown` to zero, remove the ~27% shadow volume, and eliminate the six
documented false-positive patterns — **without touching a single line of shared infrastructure.**

---

## 6. Decisions required

These are the researcher's, not the implementer's. Each one changes what the next campaign measures.

**D-1 — Which specification set does the next campaign use?** `jca` reports `AndroidKeyStore` as a
violation (2,005 rows, 2.07%) against the JSE list; `jca_android` already accepts it. But
`jca_android` is *more permissive* in six specs (it accepts MD5 and SHA-1 in `MessageDigestSpec`,
`SSL`/`TLSv1` in `SSLContextSpec`) and *more restrictive* in four, because it models **platform
availability, not recommendation**. The bias changes direction per specification and that has to be
stated.

**D-2 — Is comparability with prior campaigns being deliberately broken?** WS-2 and WS-1 both change
counts. WS-2 removes records; WS-1 changes the cardinality of any message-bearing key. Prior
measurements cannot be compared to the new ones on violation counts. Recommendation: **accept the
break, state it explicitly, and re-baseline.**

**D-3 — Weaving scope: whole APK, or app packages only?** Whole-APK is the current behaviour and
produces 73.4% library attribution. Excluding libraries changes the coverage denominator and
invalidates comparison with the published measurements. The middle path — keep the scope, add
origin labelling and an application frame — is the recommendation, but it costs WS-5.1/5.2.

**D-4 — Do the CrySL `REQUIRES` predicates get implemented?** They are the largest single source of
mute errors, but implementing them without first adding `SecretKeyFactory` and the four
`*ParameterSpec` generators would create false positives, because the predicates would be
unsatisfiable by construction.

**D-5 — Is `IncompleteOperationError` in scope?** It is a whole missing error class, and on Android
its volume is unpredictable. Prototype-and-measure first.

**D-6 — Report suppression policy.** Today: none, beyond a per-process `HashSet` defeated by
activity restart. A campaign-scale decision, since it directly sets the CSV size.

**D-7 — Does `generic_new` enter the next campaign?** It has real messages with interpolated values
— it is the *only* set whose messages are already good — but it is not CLI-selectable, two of its
files are unparseable, and its `@severity` is inert.

**D-8 — Severity and remediation text (Q4).** Nothing in the current design carries either. This is
the difference between "MD5 was used" and "MD5 was used for a security decision — replace with
SHA-256", and between that and "MD5 was used as a cache-key hash, which is fine". Roughly half of
the 28 surviving actionable findings in §2.3 are benign non-cryptographic hashing, and **nothing in
the report distinguishes them.**

---

## 7. Acceptance criteria for the next campaign

Measurable, on the produced `errors.csv`:

1. **Zero rows with `message = "unknown"`.**
2. **Zero rows with an empty observed value** (`but found .`), or those cases carry an explicit
   "value not observed — `getInstance` was not woven" message instead.
3. `error_type`, `source` and an origin/`is_library` marker are **first-class columns**.
4. No fabricated field is indistinguishable from a real one; synthetic values use an explicit,
   documented sentinel.
5. On a synthetic suite covering the six documented false-positive patterns (§3/L2): **zero
   violations reported**.
6. On a synthetic suite covering the distinct failure modes of `SSLContextSpec`, `CipherSpec` and
   `SecureRandomSpec`: **one distinct message per mode**.
7. `SignatureSpec`'s signing branch reaches `@match` on a correct
   `getInstance/initSign/update/sign` flow — proving the pointcut fix.
8. Line numbers present in the reported location for methods that carry debug info in the original
   APK — measured as a ratio before/after instrumentation, on the same APK.
9. Report volume: an explicit, stated suppression policy, with the drop count logged rather than
   silent.

---

## 8. Defect register

Numbered for tracking. Severity: **A** = corrupts results · **B** = destroys diagnostic value ·
**C** = cosmetic or latent.

| # | Sev | Site | Defect |
|---|---|---|---|
| D01 | B | `ErrorDescription.java:34-36` | 3-arg constructor writes literal `"unknown"`; used by all 21 `@fail` |
| D02 | A | 18 sites, §3/L2 table | Orphan events fall into the FSM sink → mute misclassified duplicate |
| D03 | A | `SecureRandomSpec.mop:155-161` | `next2` missing from state `end` → two `nextBytes()` calls are a false positive |
| D04 | A | `MessageDigestSpec.mop:74` vs `:108` | `reset` declared, absent from ERE → legitimate API use fails |
| D05 | A | `CipherSpec.mop:176-187` | `doFinal()` (`f1`) not accepted in state `s2` |
| D06 | A | `KeyPairSpec.mop:24` | Protocol keyed on the `KeyPair` constructor; `generateKeyPair()` path fails |
| D07 | A | `SignatureSpec.mop:99` | `call(public byte Signature.sign())` — actual return is `byte[]`; never matches (`.aj:979`) |
| D08 | A | `SignatureSpec.mop:106` | `call(public byte Signature.sign(byte[],int,int))` — actual is `int` (`.aj:984`) |
| D09 | A | `TrustManagerFactorySpec.mop:62` | `KeyManager[] getTrustManagers()` — actual is `TrustManager[]` (`.aj:1037`) |
| D10 | A | `KeyPairGeneratorSpec.mop:29` | `switch(algorithm)` on uninitialised field (`:26`) → NPE inside a pointcut condition |
| D11 | A | `KeyGeneratorSpec.mop:47`, `MessageDigestSpec.mop:55` | Condition tests `currentAlgorithmInstance`, not `alg` → false negative |
| D12 | A | `SecureRandomSpec.mop:111-116` | Marks the *argument* as `RANDOMIZED`, not the return value; poisons all downstream `validate` |
| D13 | A | `KeyPairSpec.mop:38` | Private key written under `GENERATED_PUBLIC_KEY` |
| D14 | A | `CipherSpec.mop:72` | Reads `GENERATED_PRIVATE_KEY`, which is never written — permanently false |
| D15 | A | `CipherTransformationUtil.java:32-68` | Rejects 8 `PBEWithHmacSHA*AndAES_*` accepted by `Cipher.crysl:90-105` |
| D16 | A | `CipherTransformationUtil.java:44,45,46,65` | Case handling asymmetric within one function |
| D17 | A | `jca/KeyStoreSpec.mop:23` | JSE keystore list flags `AndroidKeyStore` — 2,005 rows; fixed in `jca_android` |
| D18 | A | `PBEKeySpecSpec.mop:50` vs `:48` | Message says `>= 1000`; condition is `< 10000` |
| D19 | A | `PBEParameterSpecSpec.mop:50` vs `:46` | Same, one order of magnitude |
| D20 | A | `PBEParameterSpecSpec.mop:49` | `UnsafeAlgorithm` used for an iteration-count violation |
| D21 | B | `ViolationRecorder.java:53-60` | `getLineOfCode()` discards N−1 frames |
| D22 | B | `RegisterShifter.java:174-267` | `cloneInstructions` drops all `DebugItem` → `debug_info_off = 0` |
| D23 | B | `DescriptorWriter.java:233-249` | 12-prefix exclusion covers no Android/Kotlin/Google/okhttp3 package |
| D24 | B | `PackageFilter.java:22-43` vs above | Two divergent scope policies in one module |
| D25 | B | `ErrorSummary.java:73-120` | Message excluded from identity → a mute record suppresses its informative twin |
| D26 | B | `logcat_parser.py:305-316,366-368` | Fabricates `error_type := spec` and `source := "Unknown Source:1"` |
| D27 | B | `ErrorCollector.java:39` | `escapeSpecialCharacters` call commented out; JSE sibling escapes — branches diverge |
| D28 | B | `ErrorCollector.java` (device) | Per-process `HashSet` defeated by activity restart → 1,542-row groups |
| D29 | B | 3 specs | `DHGenParameterSpecSpec`, `GCMParameterSpecSpec`, `HMACParameterSpecSpec` detect nothing |
| D30 | B | `HMACParameterSpecSpec.mop:3` | Targets `javax.xml.crypto.dsig.spec.HMACParameterSpec`, absent from Android |
| D31 | B | `generic/` × 34 | Import AWT/Swing; inert on Android |
| D32 | B | `generic_new/ServerSocket_Backlog.mop:20`, `TreeMap_Comparable.mop:23` | `"[helper]"` prefix is unparseable; rows dropped |
| D33 | B | `generic_new/` × 27 | `@severity` lives in a javadoc block; inert at runtime |
| D34 | B | 18 of 24 `Property` values | Written and never read |
| D35 | C | `KeyStoreSpec.mop:67`, `KeyGeneratorSpec.mop:63` | `"expecting one of"` missing trailing space |
| D36 | C | `CipherSpec.mop:60,75` | Literal `...` in the expected set — reader cannot know what was expected |
| D37 | C | `MacSpec.mop:62` | Message begins `"one of "` — missing `expecting`; twin at `:50` differs |
| D38 | C | `MessageDigestSpec.mop:70,92` | Hard-coded `{SHA-256, SHA-384, SHA-512}` vs six-entry list at `:16` |
| D39 | C | `KeyPairGeneratorSpec.mop:98` | `InvalidKeySize` message omits the observed `keySize`, which is in scope at `:92` |
| D40 | C | `SignatureSpec.mop:58,68,78,88` | Four identical messages across four different `init` events — indistinguishable |
| D41 | C | `KeyPairGeneratorSpec.mop:110-113` | The only `@fail` without `__RESET` — inconsistent recurrence behaviour |
| D42 | C | `ViolationRecorder.java:87-105` | `fileName != null` guard disables the whole exclusion when debug info is absent |
| D43 | C | `MonitorBuilder.java:87-101` | `javac` invoked without explicit `-g`; relies on the compiler default |
| D44 | C | `ViolationRecorder.record()` | Dead code — 0 calls in the generated monitor; all 50 references are `getLineOfCode()` |
| D45 | C | `BaseMonitor.java:363,484-487,790` et al. | Static join-point location (`RVM_loc`) commented out across five files |
| D46 | C | `rv_experiment/__main__.py:443`, `config.py:688-694` | `generic_new` absent from the CLI choices |
| D47 | C | `logcat_parser.py:306` | Format 1 discriminated by a literal sentence suffix, with no `else` branch |
| D48 | C | `DexWeaver.java:861-869`, `:716-721` | Unparseable pointcut / failed match swallowed into anonymous counters |
| D49 | C | `BatchRunner.java:379-383` | APK failure reports `ex.getMessage()` only — no cause, no trace |
| D50 | C | `DexWeaver.java:978-1008` | `WeaveReport` is a vector of integers; no per-site weave manifest exists |

---

## 9. Claims marked [inferred]

Four statements in this document were not read directly from source and should be verified before
being relied on:

1. **[inferred]** That `okhttp3`'s `platformTrustManager` reaches `TrustManagerFactory.getInstance`
   through a path the weaver misses, producing the 8,371 empty-value rows. The *mechanism* verified
   is that `currentAlgorithmInstance` is `""` because no `getInstance` event was observed
   (`TrustManagerFactorySpec.mop:24`) and `init` creates a fresh monitor. Which specific weaving
   path is responsible was not established.
2. **[inferred]** That the generated `int → String` tables of WS-1.3 can be hand-written in the
   `.mop` declarations block. The mechanism (verbatim inlining, instance-method handler) is
   verified; that a `static final String[]` declaration survives the generator's declaration
   emission is not.
3. **[inferred]** The volume estimate for WS-4 on Android. No measurement exists.
4. **[inferred]** That re-enabling `RVM_loc` (WS-5.8) still works. The code is present but
   commented out across five files and has not been exercised.

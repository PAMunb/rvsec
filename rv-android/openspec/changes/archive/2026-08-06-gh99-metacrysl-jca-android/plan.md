# Change Plan: MetaCrySL-derived Android CrySL rules and the `jca_android` spec set

**Date**: 2026-08-06
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#99](https://github.com/PAMunb/rvsec/issues/99)
**PRD Reference**: FR01 (Monitor Generation from JavaMOP Specifications), FR03 (Specification Set Support)
**Domains**: instrumentation

## 1. Context

Phase F2 of `docs/20260806_plano_specs_jca_android.md` calls for a `jca_android` variant of
the 23 JCA `.mop` specifications, corrected for the Android platform. The existing `jca` set
was hand-translated from CrySL 1.5.2 rules for Java SE, and the plan's Layer 1 catalogue
(items L1.1 through L1.8) documents eight classes of platform-encoding defect that follow
from that translation: allow-lists naming keystore types, protocols, provider algorithms and
padding schemes that do not exist on Android, alongside case-sensitive comparisons and
missing algorithm aliases.

Producing `jca_android` by a second hand translation would repeat threat **W3** of the
thesis — adaptation without an equivalence argument. The revision-4 investigation in
`docs/20260806_grafo_predicados_e_pcd_dexlib2.md` supplies fresh evidence of what that costs:
roughly 17 175 of 18 029 `TrustManagerFactorySpec` events in the campaign are instrumentation
artefact, and true positives in the dataset are zero.

MetaCrySL removes the hand step. It is a meta-specification layer over CrySL, implemented in
Rascal, that generates plain `.cryptsl` files from a set of base specifications plus an
ordered chain of per-API-level refinements. The rules become *derived* rather than *guessed*,
which is the property W3 is missing. Work happens on the fork
`git@github.com:phtcosta/MetaCrySL.git`, cloned at
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL`.

### 1.1 The composition rule, established by investigation

The upstream repository documents no rule for which refinement tiers belong in a given
target. Reading the tier contents establishes it:

- **Four-digit tiers are closed availability windows** — things that existed and were then
  removed. `1025/SSLContext.ref` defines `SSLv3` (present API 10 through 25, removed in 26);
  `1013/KeyGenerator.ref` defines `RC4` (removed in 14); `0103/Signature.ref` defines
  `MD2withRSA` (removed in 4).
- **`XXplus` tiers apply from API XX onward** — `18plus/KeyStore.ref` defines
  `AndroidKeyStore`, introduced at API 18.

An API 30 target therefore composes **only** the `XXplus` tiers with XX ≤ 30, and **no**
four-digit tier. That yields fourteen existing tiers: `01plus`, `10plus`, `11plus`, `14plus`,
`16plus`, `17plus`, `18plus`, `19plus`, `20plus`, `22plus`, `23plus`, `24plus`, `26plus`,
`28plus`. Measured against the same rule, `android/Android25plus.config` wrongly omits
`17plus`, `19plus` and `23plus`, all of which are ≤ 25. That omission is recorded here as
evidence that the rule has diagnostic power — it is **not repaired**. This change targets API 30
only, and the earlier targets do not feed it.

Composition itself is a set union over `define` values, and that union is the intended
semantics: each tier declares the *delta* introduced at its API level, not a total. This was
confirmed against committed output — `target/research/25plus/Cipher.cryptsl` carries
`algorithm in {"AES_128","ARC4","AES","BLOWFISH","DESede","AES_256","RSA"}`, exactly the union
of the tiers that config loads, and its `rsa_paddings` omits the `23plus` values, exactly as
that config's omission predicts.

### 1.2 Two gaps requiring authorship

`TrustManagerFactory` is absent from the 32 base specifications, yet
`samples/jca/base/SSLContext.cryptsl:32` requires the predicate `generatedTrustManager[tms]`,
which no base specification produces. An orphan predicate is evidence of an upstream
omission rather than a deliberate exclusion. `KeyManagerFactory.cryptsl` is the template: it
already constrains `algo in {"PKIX"}`, which is precisely what plan item L1.3 identifies as
correct for Android, and where the current `.mop` errs by also accepting `SunX509`.

`TLSv1.3`, introduced at API 29, appears in no tier, so a `30plus/` tier must be authored.

### 1.3 Availability is not recommendation — recorded, not corrected

The `android` profile models **which algorithms exist** at an API level, not **which are
advisable**. Composed for API 30, the generated `SSLContext` will admit
`{"TLS","Default","SSL","TLSv1","TLSv1.1","TLSv1.2"}`. `SSLv3` drops out on its own, because
the `1025` window closes before 26, but `SSL` and `TLSv1` remain. The current `.mop` requires
`{TLSV1.2, TLSV1.3}`, so the derived set is **more permissive** than what it replaces.

The decision is to adopt the raw output regardless, on the grounds that MetaCrySL was
authored and recommended by members of the project. The consequence is a documentation
obligation, not a defect to patch: the bias inverts direction. The current `jca` set produces
false positives; the derived `jca_android` trades some of them for false negatives, ceasing
to flag `SSL` and `TLSv1` usage. This must appear as a threat to validity.

The `-cc` and `-bsi` profiles are not an alternative. `android-bsi` is byte-identical to
`android` for `SSLContext` and restricts nothing despite its name, and `android-cc` defines
`{"Insecure"}` at `01plus`, which is not a JCA protocol name.

### 1.4 Toolchain state, measured

The README and `Dockerfile` prescribe Java 8. That is stale, and the measurements say so:

| Attempt | Result |
|---|---|
| Java 8 (`~/.sdkman/candidates/java/8.0.502-tem`) + `rascal-shell-stable.jar` | **Fails.** `UnsupportedClassVersionError`: the jar is class file 55 (Java 11+). Today's "stable" is no longer the Java 8 build the README assumed |
| Java 25 + `rascal-shell-stable.jar`, REPL | **Shell starts** (Rascal 0.42.0, source path auto-resolved to `src/`), but `import generator::Main;` crashes with `StringIndexOutOfBoundsException` in `TerminalProgressBarMonitor.ProgressBar.write`. A Rascal REPL bug, not a MetaCrySL one. Reproduced under a pty (`script`), with `stty cols 200`, and with `TERM=dumb` |
| Java 25 + `java -jar rascal-shell-stable.jar generator::Main` | **Modules compile.** `Job: loading modules` completes — the 2020 source is still valid under 0.42.0. Rejected only at the entry point: `main function should either have one argument of type list[str], or keyword parameters`, while MetaCrySL declares `main(loc configurationFile)` |
| Java 11 or 25 + REPL **under a pty with an explicit width** | **`import` succeeds.** The crash was terminal width zero, because the java process had a pipe on stdin. Working invocation: `printf '<commands>' \| script -qec "stty cols 200 rows 50; java -Xmx2G -Xss32m -jar rascal-shell-stable.jar" /dev/null` |
| Same, running `main(...)` on a probe config | **Generation fails** in the pre-processor: `invalid definition for variable`, 0 files written |

**Resolved.** Narrowing ruled out every easy explanation before arriving at the real cause:

| probe | result |
|---|---|
| Rascal 0.19.6 (Nov 2021, contemporary with MetaCrySL) on Java 8, `Android0108` | same `invalid definition for variable`, 0 files |
| Single tier only (`base/` + `01plus/`), no merge possible | same throw |
| One refinement in isolation — `SSLContext`, `SecureRandom`, `Cipher` | **all three throw** |

`01plus/SSLContext.ref` is the most trivial refinement in the repository — one
`define algorithm = {"TLS"};` against a base whose only meta-variable use is
`protocol in ${algorithm}`. Every base meta-variable required by a `01plus` refinement is in
fact defined by it (verified mechanically across all ten). So the failure was **not** a tier
collision, **not** a missing definition, and **not** the merge.

**Root cause.** `bindLiteralSet` and `bindObjectDecl` (`src/generator/PreProcessor.rsc:81`
and `:45`) compare `metaVariable(v) == var`. `MetaVariable` is declared as
`data MetaVariable = metaVariable(str varName);` with no `location` or `comments` field, but
`implode` attaches both as **keyword parameters** — and keyword parameters participate in
equality. The node built in code (empty fields) is therefore never equal to the node coming
from the parse (populated fields). This is the historical Rascal migration from *annotations*,
which `==` ignored, to *keyword parameters*, which it does not. Proved directly in the REPL:

```
metaVariable("algorithm") == metaVariable("algorithm", location=..., comments=[])
bool: false
```

**The fix is two lines** — replace `metaVariable(v) == var` with `v == var.varName` at both
sites.

**Validated.** With the patch applied to a scratch copy, `Android0108` prints `done` and
writes 32 files. Against the committed `target/research/0108`: 21 byte-identical, and **32/32
equivalent** once the ordering of elements inside `{...}` is normalised. That ordering is not
a defect — `set[Literal]` has no stable iteration order in Rascal, so serialisation order may
differ between runs. **The gate passes.**

The upstream branches contain no fix, and this was checked rather than assumed: `android` only
removes the `try`/`catch` from `Main.rsc` and the `exists` check from `Loader.rsc`; `docker`
adds an `EcoopRunner`; `issue-3` and `issue-4` are *behind* master (`git log master..` is
empty on both).

**Working toolchain**: `rascal-0.19.6.jar` with Java 8 (`~/.sdkman/candidates/java/8.0.502-tem`),
invoked from **inside** the project directory — `META-INF/RASCAL.MF` (`Source: src`) is what
puts `src/` on the search path; without it the import fails with `can not find in search path`.
No pty is needed at 0.19.6. Alternatives A1 (a `Cli.rsc` entry point) and A2 (hunting an even
older shell) are moot: A1 would have hit the same `throw`, and 0.19.6 already works.

**This supersedes the "no `.rsc` edits" constraint of §1.5 for these two lines only.** The
patch is a prerequisite for any generation at all; without it the change cannot proceed. It
is also a genuine upstream defect, but contributing it is out of scope for this change — see
Group G below.

Two parser constraints discovered while probing, both of which apply to every config we write:

- **No trailing newline.** `Parser.rsc` calls `parse(#ConfigurationDef, contents)` rather than
  `#start[ConfigurationDef]`; without `start`, Rascal permits no layout at the outer edges, so
  a final `\n` after `}` is a parse error. All nine committed configs end at `}` with no
  newline, and most editors add one. Because `Main.rsc` swallows exceptions, this fails
  **silently** — 0 files and no error message beyond a printed exception.
- **Restricted path alphabet.** `lexical Path = [a-zA-Z0-9/\-]*` (`lang/common/ConcreteSyntax.rsc`)
  admits no `_`, `.` or `~`. Our absolute paths satisfy this, but a scratch or home-relative
  path may not.

### 1.5 Explicitly out of scope

Defects in the Rascal generator are recorded as optional debt. **No `.rsc` file is edited
beyond the two-line fix of §1.4** — that fix was a prerequisite for generating anything at
all, and it remains the only source change this project makes. Everything below is documented
and left alone, however tempting a small patch might look:

- Constraints are duplicated in the output, growing with chain length — 0 duplicates in
  target `0108`, 7 in `0116`, 22 in `25plus`. `Cipher.cryptsl` in `25plus` writes 41
  constraints where 23 are distinct. Logically inert, since conjunction is idempotent, but it
  inflates diffs and human reading, and our chain is the longest yet composed.
- `src/generator/Loader.rsc` accumulates into module-level `specifications` and `refinements`
  that are never reset, so two generations in one Rascal session contaminate the second. Each
  target requires a fresh session.
- `src/generator/Main.rsc` swallows exceptions (`catch e: println(e)`); only the trailing
  `"done"` distinguishes success from failure.
- Paths must be absolute — `Loader.rsc` and `Main.rsc` both build locations as
  `|file:///| + fullPath`, so a relative path would resolve against the filesystem root.
- The `config <Name>` identifier is parsed into the AST but never read by `main`, so the
  upstream copy-paste error in `Android25plus.config` is harmless.

Weaver defects from the revision-4 report (wrapper collision, empty-slice binding, inline
truncation) are a separate track and are **not** addressed here.

## 2. Scope

Three trees are touched. Everything outside `rv-android` is given by absolute path, where
`$WS` = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`.

| Group | Tree | What it does |
|-------|------|--------------|
| **A** | `$WS/MetaCrySL` | Unblock the invocation path (§1.4) and reproduce an existing target as a baseline |
| **B** | `$WS/MetaCrySL` | Publish the tier map that determines which tiers the API 30 target composes |
| **C** | `$WS/MetaCrySL` | Author `TrustManagerFactory.cryptsl` and the `30plus/` tier |
| **D** | `$WS/MetaCrySL` | Author `Android30.config`, generate, diff against CrySL 1.5.2 |
| **E** | `$WS/rvsec/rvsec/rvsec-mop` | Create `jca_android/` from `jca/` and adapt the `.mop` files |
| **F** | `rv-android` (this repo) | Document the tier map, the permissiveness finding, and the debt |
| **G** | `$WS/MetaCrySL` | Commit the fork deliverables: the two-line fix, `generated/api30/`, and a README appendix recording how it was run |

Group A is a gate: until an existing config reproduces its committed output, nothing
generated afterwards is trustworthy.

## 3. File Inventory

### Group A — toolchain and baseline

| File | Action | Detail |
|------|--------|--------|
| `$WS/MetaCrySL/src/generator/PreProcessor.rsc` | **Edit** | The two-line fix at `:45` and `:81` — `metaVariable(v) == var` becomes `v == var.varName`. Root cause in §1.4. Approved as the sole exception to §1.5 |
| `$WS/MetaCrySL/rascal-0.19.6.jar` | Present | Downloaded (113 MB). The working shell, paired with Java 8. Should be gitignored, not committed |
| `$WS/MetaCrySL/rascal-shell-stable.jar` | Present | Rascal 0.42.0 (82 MB). Runs under Java 11/25 only, and its REPL needs a pty. Superseded by 0.19.6; gitignore or delete |
| `$WS/MetaCrySL/META-INF/RASCAL.MF` | Read only | `Source: src` — this is what puts `src/` on the search path. The generator must be invoked from the project directory |
| `$WS/MetaCrySL/samples/jca/android/target/research/0108/` | Read only | 32 `.cryptsl` files serving as the reproduction oracle |

### Group B — tier map

| File | Action | Detail |
|------|--------|--------|
| `$WS/MetaCrySL/samples/jca/android/config/Android0108.config` | Edit | Replace `src`/`out` (`/Users/rbonifacio/...`) with absolute paths under `$WS/MetaCrySL`. Needed to run Group A |
| `$WS/MetaCrySL/samples/jca/android/` (19 tiers) | Read only | The source of the tier → specifications → constraint table |

`Android0116.config` and `Android25plus.config` are left untouched. They target earlier API
levels, nothing in the API 30 composition reads them, and repairing them would be work this
change does not need. The `android-cc` and `android-bsi` configs are likewise untouched —
those profiles are not part of this change (§1.3).

### Group C — authored specifications

| File | Action | Detail |
|------|--------|--------|
| `$WS/MetaCrySL/samples/jca/base/TrustManagerFactory.cryptsl` | Create | Model on `base/KeyManagerFactory.cryptsl`: `algo in {"PKIX"}`; events `getInstance`/`init`/`getTrustManagers`; `ENSURES generatedTrustManager[...]` so `SSLContext`'s requirement stops being orphaned |
| `$WS/MetaCrySL/samples/jca/android/30plus/SSLContext.ref` | Create | `define algorithm = {"TLSv1.3"};` — API 29 |

Further `30plus/` refinements are added only where an API 29/30 addition is verified against
platform documentation; the tier is not padded speculatively (P1).

### Group D — generation and cross-check

| File | Action | Detail |
|------|--------|--------|
| `$WS/MetaCrySL/samples/jca/android/config/Android30.config` | Create | 14 existing `XXplus` tiers (§1.1) plus the authored `30plus` — 15 `load refinement` lines — over `load spec base/`; `out` targets `generated/api30` (**not** `target/`, which `.gitignore` excludes) |
| `$WS/MetaCrySL/generated/api30/` | Create | Generated output, **committed**: 33 `.cryptsl` (32 base + `TrustManagerFactory`) |
| `$WS/rvsec-dataset/src/rvsec_dataset/cognicrypt/CrySL-Rules/` | Read only | The 49 CrySL 1.5.2 rules the current `.mop` set was translated from — the diff baseline |

### Group E — the `jca_android` specification set

Source: `$WS/rvsec/rvsec/rvsec-mop/src/main/resources/jca/` (23 `.mop` plus one `.aj`).
Destination: `$WS/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/`.

| File | Action | Detail |
|------|--------|--------|
| `.../jca_android/` (directory) | Create | Copy the **23 `.mop` files only**. `MultiSpec_1MonitorAspect.aj` is **not** copied — plan §9.1 warns it is stale residue carrying defect L2.7 |
| `.../jca_android/SSLContextSpec.mop` | Edit | Protocol allow-list from the generated `SSLContext.cryptsl` (L1.2). Records the permissiveness finding of §1.3 |
| `.../jca_android/KeyStoreSpec.mop` | Edit | Keystore-type allow-list from the generated `KeyStore.cryptsl` (L1.1) |
| `.../jca_android/TrustManagerFactorySpec.mop` | Edit | `{PKIX}` per the authored base spec (L1.3) |
| `.../jca_android/KeyManagerFactorySpec.mop` | Edit | `{PKIX}` per `base/KeyManagerFactory.cryptsl` (L1.3) |
| `.../jca_android/SecureRandomSpec.mop` | Edit | Algorithm allow-list from the generated `SecureRandom.cryptsl` (L1.4) |
| `.../jca_android/CipherSpec.mop` | Edit | Transformation constraints from the generated `Cipher.cryptsl` (L1.5) |
| `.../jca_android/MessageDigestSpec.mop` | Edit | Algorithm set and aliases from the generated `MessageDigest.cryptsl` (L1.7) |
| `.../jca_android/*.mop` (remaining 16) | Copy / Edit | Verbatim copies unless a generated rule contradicts them; every edit anchored to a generated rule, every non-edit an explicit decision |

`RandomStringPassword.mop` has no MetaCrySL counterpart and is not a JCA specification — it
propagates randomness taint through `String.valueOf`/`toCharArray` so that a password derived
from `SecureRandom` is not accused by `PBEKeySpecSpec`. It is copied verbatim and declared a
hand translation.

### Group F — documentation in this repository

| File | Action | Detail |
|------|--------|--------|
| `docs/20260806_metacrysl_tier_map.md` | Create | Tier → specifications → constraint table; the window/`plus` semantics of §1.1; the config omissions found |
| `docs/20260806_plano_specs_jca_android.md` | Edit | Record in the F2 section that the set is MetaCrySL-derived, and link the tier map |

### Group G — fork deliverables (committed to `$WS/MetaCrySL`)

| File | Action | Detail |
|------|--------|--------|
| `$WS/MetaCrySL/README.md` | Edit | Append a section recording the reproducible procedure: the Rascal 0.19.6 + Java 8 pairing, invocation from the project directory, the two-line fix and why it was needed, the no-trailing-newline and restricted-path-alphabet config constraints, and the set-ordering caveat when diffing output |
| `$WS/MetaCrySL/.gitignore` | Edit | Add `*.jar` so the two shells (195 MB combined) are not committed |

Commits go to the fork's `master`, and stay there. Nothing is pushed to any remote and no pull
request is opened against CROSSINGTUD/MetaCrySL: the two-line fix (§1.4) is carried as
documented upstream debt, not as a contribution. The README appendix records the defect and its
cause in enough detail that a contribution could be assembled later from the fork alone.

## 4. Execution Order

```
A (fix + baseline reproduction)         ← gate, must pass before anything else
        │
        ├── B (tier map)
        └── C (authored specs)          ← B and C are independent, may run in parallel
                │
                D (Android30 + generation into generated/api30)
                │
                ├── G (fork: README appendix, .gitignore, commit)
                │
                E (jca_android .mop set)
                │
                F (documentation in rv-android)
```

A gates everything: a toolchain that cannot reproduce `Android0108` cannot be trusted to
generate `Android30`. B and C touch disjoint files and may be dispatched in parallel. D needs
both. E needs D's generated rules as its anchor. F needs E's decisions to describe them.

Per `docs/WORKFLOW.md` §5, subagent dispatch is not warranted here: the groups are small and
several are sequential. F may be dispatched separately if the tier map grows large.

**Session discipline**: because of the unreset global state in `Loader.rsc` (§1.4), every
generation runs in a **fresh Rascal session**. Reusing a session silently contaminates the
second target.

## 5. Acceptance Criteria

- [x] The two-line fix applied to `PreProcessor.rsc`; `Android0108` regenerates `target/research/0108` with 32/32 equivalence after normalising set ordering
- [x] Tier → specifications → constraint table published, documenting the window/`plus` semantics
- [x] `base/TrustManagerFactory.cryptsl` authored; `generatedTrustManager` is produced by some base spec and no longer orphaned
- [x] `android/30plus/` authored and covers `TLSv1.3` (API 29)
- [x] `Android30.config` composes the 14 existing tiers plus `30plus` and generates 33 `.cryptsl` into `generated/api30/`
- [x] The fork carries a commit with the fix, `generated/api30/`, the README appendix and the `.gitignore` entry; the two shell jars are **not** committed
- [x] The README appendix is sufficient for someone else to reproduce the generation from a clean clone
- [x] Diff against the CrySL 1.5.2 rules in `rvsec-dataset` documented
- [x] `jca_android/` exists under `rvsec-mop/src/main/resources/` containing 23 `.mop` and **no** `.aj`
- [x] Every divergence between `jca` and `jca_android` is anchored to a generated rule or declared a hand translation
- [x] The `SSLContext` permissiveness is recorded as a threat to validity, stating that the bias inverts from false positives toward false negatives
- [x] The set runs end to end via `--specification-set custom --custom-specs-dir <path to jca_android>`
- [x] Generator defects recorded as optional debt; the only change `git diff` reports under `$WS/MetaCrySL/src/` is the approved two-line fix in `PreProcessor.rsc`

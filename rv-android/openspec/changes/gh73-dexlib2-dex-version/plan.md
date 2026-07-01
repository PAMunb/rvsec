# Change Plan: dexlib2 instrumenter — preserve input DEX format version

**Date**: 2026-06-30
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#73](https://github.com/PAMunb/rvsec/issues/73)
**PRD Reference**: FR01–FR03 (instrumentation pipeline)
**Domains**: instrumentation

## 1. Context

The dexlib2 instrumenter (`rvsec-instrumentation-dexlib2`, shipped in image
`phtcosta/rvandroid:0.9.1`) re-writes **every output DEX at format version `035`**
(API 20), regardless of the app's real `minSdkVersion`. Kotlin/Compose interface
`static`/`default` methods (the `$default` default-argument shims) are legal only in
DEX ≥ `037` (API 24+). An app originally compiled to `037`+ becomes malformed once
downgraded to `035`; at runtime ART rejects the `invoke-static` into the interface with
`java.lang.IncompatibleClassChangeError: Found interface … but class was expected` on
the first Compose draw. This blocks Phase 8 of the rvsec-dataset (instrumentation of
225 APKs): **136/225 (60%)** ship an original DEX ≥ `037` and are downgraded into the
illegal-interface-static zone.

The root cause is verified at three independent levels (source read, shipped
smali-3.0.9 bytecode, and byte-level DEX forensics on the pilot APKs):

- `cli/.../BatchRunner.java:337` reads every `classes*.dex` with
  `DexBackedDexFile.fromInputStream(Opcodes.getDefault(), buf)`.
- In smali 3.0.9, `Opcodes.getDefault()` is hardcoded to `forApi(20)` (bytecode:
  `bipush 20; invokestatic forApi`); `VersionMap.mapApiToDexVersion` returns `35` for
  `api ≤ 23`.
- `cli/.../BatchRunner.java:240` writes via `DexPool.writeTo(out, mutator.toDexFile())`.
  `DexPool.writeTo(String, DexFile)` builds the writer from `dexFile.getOpcodes()` →
  `DexWriter` stamps the magic via `HeaderItem.getMagicForApi(opcodes.api = 20)` → every
  output DEX is `dex035`.
- Secondary: `monitor-builder/.../MonitorBuilder.java:100-141` (`runD8`) invokes `d8`
  with **no `--min-api`**, so the monitor DEX is also produced at a low version / with
  desugaring. This is a separate instance of the same version problem, addressed by the
  monitor-dex arm of the fix (Group B — see §1 note below).

Empirical proof of cause (report §5): flipping only the magic version bytes
`035 → 038`/`039` on the already-instrumented APKs (zero bytecode changes) makes both
crashing apps (openbible, lumo) launch cleanly **with coverage still active**. The
defect is purely the DEX container version, not the weave.

**Note on the two fixes.** The instrumented APK contains **N app dexes + 1 monitor dex**
(report §4.1: instrumented openbible = 10 dexes). The §5 proof flipped **all** output DEX
versions (openbible: 10 dexes `035→038`; lumo: 20 dexes `035→039`) — both the app dexes
and the monitor dex — and this restored clean launch with coverage active. Consequently
**both fixes are in scope**: Group A (`BatchRunner`) restores the *app* dexes, which are
the interface-static crash site and remove the launch crash; Group B (`MonitorBuilder`
`d8 --min-api`) restores the *monitor* dex, which dexlib2 does not write. Group B is
required for the acceptance criterion "every output dex ≥ `037`" — the monitor dex is
produced by `d8`, so without `--min-api` it would remain `035` even after Group A.

Full report (absolute path, rvsec-dataset repo — read-only here):
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-dataset/docs/20260630_phase8-pilot-instrumentation-dex-downgrade.md`

**Chosen approach** (decided 2026-06-30): preserve the input DEX format version
**per dex** by parsing the magic header and using `Opcodes.forDexVersion(v)`. This is
more robust than deriving from the manifest `minSdkVersion` (per-dex, no manifest parse).
The `forDexVersion` round-trip is verified in 3.0.9 bytecode: `forDexVersion(38)` →
`api 27` → write `getMagicForApi(27)` → `dex038` (and 35/37/38/39/40/41 all round-trip).
**No smali/baksmali version bump is required** — `Opcodes.forDexVersion(int)` and the
full `VersionMap` (dex 035–041) already exist in the pinned `smali.version=3.0.9`.

## 2. Scope

The fix is in the **Java instrumenter** under `PAMunb/rvsec@modules`, in the
`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` subtree. This is the **same git
repository** as `rv-android/` (both are tracked subdirectories of `PAMunb/rvsec`); it is
**not** a sibling repository. The change directory lives in `rv-android/openspec/` (the
configured workflow), while the edited code lives outside the `rv-android/` subtree —
hence absolute paths for the code, repo-relative for the openspec artifacts.

- **Group A — App-dex fix (decisive):** `BatchRunner.extractDexes` preserves each input
  DEX's format version via `Opcodes.forDexVersion(parsedVersion)`, with a safe fallback
  to `Opcodes.getDefault()` for unsupported versions (e.g. `dex036`, which `forDexVersion`
  rejects and which does not occur in the dataset).
- **Group B — Monitor-dex fix (required):** `MonitorBuilder.runD8` passes
  `--min-api <api>` to `d8`, where `<api>` is the max input-DEX API computed in
  BatchRunner (no manifest parse), threaded into the builder invocation. Required so the
  monitor dex is also ≥ `037` (see §1 note). `--lib <android.jar>` is intentionally
  **omitted** (P1): the monitor sources are plain Java 1.8 and the runtime jars are
  already passed as d8 inputs, so `--min-api` alone prevents the low-version/desugar
  outcome; add `--lib` only if a desugaring gap surfaces.
- **Group C — Tests:** module test harness (`mvn`) coverage for the version-preserving
  read path (unit) where a harness exists.
- **Group D — Local verification, then delivery:** (1) local `mvn` build + dexdump check,
  (2) emulator re-verification with the **locally built jar** (launch openbible + lumo on
  the AVD), then (3) rebuild `phtcosta/rvandroid:0.9.1` from `modules` and update report
  §7.1. The image rebuild is a delivery step **after** the emulator confirms the fix — it
  is not on the verification critical path (avoids a 15–25 min rebuild before knowing the
  fix works).

**Group ↔ tasks map:** A → tasks §1, B → tasks §2, C → tasks §3, D-(1) → tasks §4,
D-(2) → tasks §5, D-(3) → tasks §6, final review → tasks §7.

Out of scope: weaver, `RegisterShifter`, `MultidexMerger` repack/sign logic, coverage
logic. No bytecode-shape change beyond the container version.

## 3. File Inventory

All paths under the absolute root
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`.

| File | Action | Detail |
|------|--------|--------|
| `cli/src/main/java/br/unb/cic/rv/cli/BatchRunner.java` | Edit (2 sites) | **(a)** `extractDexes` (325–344): read each `classes*.dex` entry fully into a `byte[]`; parse the DEX magic version (bytes `[4,7)` as ASCII digits → int); build the `DexBackedDexFile` with `Opcodes.forDexVersion(version)` instead of `Opcodes.getDefault()` (line 337). Fallback to `Opcodes.getDefault()` if `forDexVersion` throws (unsupported version, e.g. dex036). Compute the max input-DEX API across the APK's dexes for Group B. Line 240 (`DexPool.writeTo`) is unchanged — it correctly inherits the now-correct opcodes. **(b)** `mb.build(...)` call site (287): pass the computed max input-DEX API into `MonitorBuilder.build(...)`. |
| `monitor-builder/src/main/java/br/unb/cic/rv/builder/MonitorBuilder.java` | Edit | `build(Path,Path)` (52) + `runD8` (100–141): extend `build` (or `BuilderConfig`) to receive the max input-DEX API; add `--min-api <api>` to the d8 command (line ~115). `--lib` intentionally omitted (see §2 Group B). |
| `cli/src/test/java/.../*` (if harness exists) | Add/Edit | Unit test: a small in-memory DEX (or fixture) with magic `038` round-trips to `038` after read+`DexPool.writeTo`; a `035` input stays `035`. |

Exact helper (magic parse) is mechanical: `int v = (b[4]-'0')*100 + (b[5]-'0')*10 + (b[6]-'0')`
for magic `dex\n0XY\0`, then `Opcodes.forDexVersion(v)` guarded by try/catch.

## 4. Execution Order

1. **Group A** lands first (it also computes the max input-DEX API that Group B consumes).
2. **Group B** depends on Group A (consumes the threaded max-API value).
3. **Group C** (tests) accompanies A/B in the same module build.
4. **Local `mvn` build + dexdump check** (D-1) — confirm output ≥ `037` on openbible/lumo
   using the locally built `instr-cli.jar`; no emulator.
5. **Emulator re-verification** (D-2) — install + launch openbible/lumo built with the
   **local jar**. Requires a user-booted AVD (`RVSec`) — the emulator is NOT started by
   this workflow.
6. **Image rebuild + report update** (D-3) — only after D-2 confirms the fix. Delivery
   step, off the verification critical path.

This is a small, single-module change; no subagent fan-out is needed (well under the
20-file threshold of WORKFLOW.md §5).

## 5. Acceptance Criteria

- [ ] `BatchRunner.extractDexes` uses `Opcodes.forDexVersion(parsedInputVersion)` per dex
      (with a `getDefault()` fallback on unsupported versions); `Opcodes.getDefault()` is
      no longer the read opcodes for the happy path.
- [ ] `MonitorBuilder.runD8` passes `--min-api <maxInputApi>` to `d8`.
- [ ] Local build succeeds: `mvn -q -pl cli -am package` produces `cli/target/instr-cli.jar`.
- [ ] dexdump/magic check — re-instrument openbible (minSdk 27) with the fixed jar: every
      output `classes*.dex` — **app dexes (Group A) and the monitor dex (Group B)** — is
      `dex038` (not `035`).
- [ ] dexdump/magic check — re-instrument lumo (minSdk 29): every output `classes*.dex`
      (app + monitor) is `dex039` (not `035`).
- [ ] DEX `≤ API23` inputs round-trip unchanged (a `dex035` input stays `dex035`; no
      spurious upgrade).
- [ ] Unit test added (where a harness exists) asserting the read+write version round-trip.
- [ ] Real re-verification, openbible (pkg `com.schwegelbin.openbible`): install + launch
      on AVD `RVSec` → no `IncompatibleClassChangeError`/`FATAL EXCEPTION`, `Displayed`
      present in logcat, `RVSEC-COV` count > 0 (reference: 208).
- [ ] Real re-verification, lumo (manifest pkg `me.proton.lumo`, file
      `me.proton.android.lumo_50.apk`): launch → no crash, `Displayed` present,
      `RVSEC-COV` > 0 (reference: 2424).
- [ ] Coverage/weave logic unchanged (diff touches only the read-opcodes call site, the
      d8 `--min-api` arg, the threaded API value, and tests).
- [ ] _(delivery — tasks §6)_ Image `phtcosta/rvandroid:0.9.1` rebuilt from
      `PAMunb/rvsec@modules` with the fix; `instr-cli.jar` inside the image carries the change.
- [ ] _(delivery — tasks §6)_ Report §7.1 updated to APPLIED + VERIFIED (commit hash +
      re-verification numbers).
- [ ] _(delivery — tasks §6)_ Final commit on `modules` uses `closes #73`; Kanban card
      moved to Done.

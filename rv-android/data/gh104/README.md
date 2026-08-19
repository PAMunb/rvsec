# `data/gh104` — the regeneration control of the legible-violation-reports change

This directory holds the versioned half of one measurement: the sha256 manifest
of the **frozen `jca` monitor control**, against which the monitor generator's
output is compared after gh104 edits `rv-monitor/rv-monitor`.

The control itself lives at

```
results/gh101_group8_jca_frozen_control/monitors/
```

which is **gitignored** (`/results/` in `.gitignore`) and which
`./clear.sh --clean-results` deletes. That is exactly why the manifest is
versioned and the control is not: the manifest is what survives, and it is what
lets a later run say whether the control on this disk is still the one the
measurement was taken against — or whether it has to be regenerated.

## Why one control and not several

The generator edit of gh104 is global: it serves all 191 `.mop` files in the
tree. `jca` exercises the same emitter paths as any set derived from it, so a
second control buys no signal and costs a generation run, a directory, a
manifest and a recipe. The archived `jca_android_bug_predicate/` is regenerated
by no task of this change; it is read only by the gh101 gate scripts and by the
identity checks.

## What the manifest covers, and what it deliberately does not

`jca_frozen_control.sha256` names exactly the three files the *generator*
produces:

| file | produced by |
|---|---|
| `MultiSpec_1RuntimeMonitor.java` | rv-monitor |
| `MultiSpec_1MonitorAspect.aj` | javamop (`-merge`) |
| `MultiSpec_1MonitorAspect.json` | javamop (`--emit-descriptor`, same run) |

Two files in the control directory are **outside** the manifest:

- `Coverage.aj` — not a generator output at all. The Python pipeline copies it
  from the aspects directory into the control directory *after* generation
  (`runtime_verification_generator.py`, the `copy_files_by_extension` of the
  javamop step), so comparing it would compare the copy, not the generator.
- `mop/MonitorWrappers.java` — produced by the instrumentation step (the
  dexlib2 weaver), not by the generator.

## Recipe: regenerating the control if it is lost

The control is the output of the **unmodified** generator over the frozen
specification set. Reproduce it by pinning the generator, not by pinning the
output:

1. Check out the generator as it stood before gh104 touched it. The last commit
   to `rv-monitor/rv-monitor` before this change is
   **`4153939` — "open 0.9.3-SNAPSHOT dev cycle (refs #84)"** (2026-07-20). The
   whole reactor at that point is `git checkout 4153939 -- rv-monitor/` from the
   `rvsec` repository root, or a full checkout of that commit.
2. Build and install the reactor so the `rv-monitor`/`javamop` launchers under
   `$RVSEC_HOME` are the pinned ones. The reactor **builds** under JDK 21, which
   is what the pom targets:

   ```bash
   export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem
   export PATH=$JAVA_HOME/bin:$PATH
   cd "$RVSEC_HOME" && mvn clean install -DskipMopAgent -DskipTests
   ```

   **The JDK that runs the generation is part of the pin, and it is not the one
   that builds.** This control was generated under **JDK 25**
   (`$HOME/.sdkman/candidates/java/25.0.3-tem`), and the state numbering of the
   generated monitor depends on it: regenerating the same frozen sources with
   the same generator under JDK 21 yields the same 133 transition tables, with
   the same event names, carrying different state numbers — 347 differing lines,
   every one of them a `Prop_N_transition_*` row. Two runs under one JDK are
   byte-identical, so the generator is deterministic; the variation is across
   JDK versions and arises inside rv-monitor. javamop is not implicated: its
   `MultiSpec_1MonitorAspect.json` is byte-identical under either JDK.

   Export JDK 25 for step 3, and leave JDK 21 for step 2. Measured 2026-08-19,
   `data/gh104/evidence/g_regeneration.md`.

3. Generate from the frozen source set
   `rvsec/rvsec-mop/src/main/resources/jca` into
   `rv-android/results/gh101_group8_jca_frozen_control/monitors/`:

   ```bash
   export JAVA_HOME=$HOME/.sdkman/candidates/java/25.0.3-tem   # the control's JDK
   export PATH=$JAVA_HOME/bin:$PATH
   export TMPDIR=$HOME/tmp-gh104 && mkdir -p "$TMPDIR"   # /tmp is tmpfs here
   cd rv-android
   python3 scripts/gh104_regen_diff.py \
       --specs-dir "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca" \
       --out results/gh101_group8_jca_frozen_control/monitors --keep \
       --control results/gh101_group8_jca_frozen_control/monitors \
       --manifest data/gh104/jca_frozen_control.sha256
   ```

   (or run the pipeline through `rv-experiment`, which is what produced the
   original: javamop `-merge --emit-descriptor` into the output directory, the
   `.rvm` files moved out of the source directory, then rv-monitor `-merge`.)

4. Confirm the manifest still holds:

   ```bash
   cd results/gh101_group8_jca_frozen_control/monitors && \
     sha256sum -c "$OLDPWD/data/gh104/jca_frozen_control.sha256"
   ```

**Generation writes `.rvm` files into the source directory before moving them.**
That is why a generation run must never overlap a rename or an edit of
`resources/jca`, and why `scripts/gh104_regen_diff.py` removes any `.rvm` it
finds there even when the run fails.

## How the control is used

`scripts/gh104_regen_diff.py` regenerates `jca` into a scratch directory with
the *current* toolchain, verifies the control against this manifest, diffs the
monitor file ignoring leading whitespace, and classifies every remaining
difference. After gh104's generator change the only admissible categories are

- `table` — the per-monitor-class `static final String[] RVM_eventNames`
- `helper` — the per-monitor-class `RVM_eventName()` decoder
- `lock-framing` — `try {` after the lock acquisition and `} finally { … }` in
  place of the bare release

No expanded macro appears in that diff: the frozen `jca` writes no
`__EVENTNAME`. The script also asserts the INV-INS-129 arithmetic on the
regenerated monitor — acquisitions = releases = `finally` blocks, and every
acquisition inside a `try`. On the *pre-change* control that check reads
134 / 134 / **0** and fails by design; that is the defect the change repairs.

A missing control directory makes the script **skip** with a named reason
(exit 2). A control directory that is present but disagrees with this manifest
makes it **fail** (exit 1): a control that has drifted is worse than no control.

## Evidence

`evidence/` holds the red-then-green records of the group's two test-first
tasks and the regeneration diff:

| file | what it records |
|---|---|
| `evidence/g_eventname_red.md` | `EventNameMacroTest` failing before the generator emits the macro |
| `evidence/g_lock_red.md` | `DispatcherLockReleaseTest` failing before the framing lands |
| `evidence/g_regeneration.md` | the `jca` regeneration diff (written by the between-waves step) |

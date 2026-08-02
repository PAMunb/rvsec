# ADR 0006 — Fixed emulator execution profile: no GPU, no persisted state, cold boot per task; boot budget sized and parameterized by environment variable

**Status**: Proposed (gh92)

Constraints 1–3 below describe the regime already in force in the running system; they had never been written down, and this ADR records them for the first time. Constraint 4 (the parameterization form) is decided here and lands with change `gh92-emulator-boot-gating`.

## Context

RV-Android executes every experiment task by cold-booting an Android emulator inside a Docker container, installing the instrumented APK, running one testing tool against it for a fixed budget, and tearing the emulator down. `Android.start_emulator` launches the emulator and then blocks in `Android._wait_for_boot`, which gates APK installation on boot completion under a single budget (`modules/rv-android-core/src/rv_android_core/util/android/android.py:143`, default 180 s).

Change gh92 establishes that this gate does not work: phase 2 of `_wait_for_boot` returns success in milliseconds, so the APK is installed against a device that never finished booting. Repairing the gate converts today's misattributed install failures into legitimate boot timeouts, because the execution environment guarantees a cold boot on every task and the 180 s budget has already been exhausted 322 times by the phase that does work. Restoring the gate (gh92 C1) and sizing the budget (gh92 C4) are therefore a single, indivisible correction.

That correction only stands if the boot cost it is sizing for is genuinely irreducible. It is — but for reasons that live in three different places (the Docker image, the emulator argv, the UI-automation timing constants) and had never been recorded anywhere. The absence of that record has a demonstrated cost: an earlier attempt at this same problem proposed GPU pinning, snapshot warming, and emulator reuse, all three of which had already been decided against, and the review of that attempt had to re-derive the reasons from the code. Anyone who next sees a 300 s boot budget in a config file will reach for the same three ideas unless the reasons are written down.

The forces are:

- **Experimental validity.** Coverage and monitored-operations (MOP) metrics are the output of the whole system. Any residue carried from one task into the next — an installed APK, app data, ART cache, granted permissions — contaminates the next task's measurement and invalidates the comparison the experiment exists to make.
- **Parallel execution.** Several containers run concurrently against the same AVD directory `/data/RVSec.avd` baked into the image.
- **Calibration already committed to the profile.** The UI-automation timing constants in `modules/rv-uiautomator/src/rv_uiautomator/constants.py:4-6` are documented as tuned for headless SwiftShader software rendering. They are not independent of the rendering mode.
- **Build-time capability.** `/dev/kvm` is mapped into containers at *run* time by the composes (for example `docker/docker-compose.aperv-comparacao.yml:29`). `docker build` has no such mapping and cannot obtain one.
- **P1 Simplicity and module boundaries.** `rv-android-core` is the Layer-1 foundation, with fan-in of 14 of the 16 workspace modules and zero declared `rv-*` dependencies. The boot budget is consumed there, at a point that reads no configuration at all today.

Relevant requirements: **FR07** (Android Emulator Management), **FR09** (Component-Based Task Execution), **NFR04** (resilience), **NFR05** (reproducibility), **NFR07**.

## Decision Drivers

- **Experimental validity (must-have)**: no state may cross a task boundary, or the coverage measurement of the following task is not trustworthy.
- **Parallel-instance capability (must-have)**: multiple containers must be able to open the same AVD image concurrently.
- **Calibration coherence (must-have)**: changing the rendering mode invalidates timing constants that are already tuned and in production use.
- **Environment capability (constraint)**: `docker build` cannot access `/dev/kvm`; anything requiring hardware virtualization at build time is not an option, independent of its merits.
- **P1 Simplicity (must-have)**: a value consumed in one Layer-1 function must not be plumbed through three module boundaries to reach it.
- **Existing in-code prohibition (constraint)**: `modules/rv-experiment/src/rv_experiment/__main__.py:296-303` instructs, in code, that the per-flag Click `envvar=` pattern is a gh55 stopgap and must not be expanded to new flags.

## Decision

We will treat the emulator execution profile as fixed and non-negotiable, and size the boot budget for it rather than attempt to reduce it. Specifically:

**1. The emulator never uses GPU.** Headless operation with software rendering is the intended regime, not a gap to be closed. The AVD baked into `phtcosta/rvsec_android:0.9.3` carries `hw.gpu.enabled = no`, and the rv-uiautomator timing constants are calibrated against exactly that. The `EMU_GPU_MODE` environment variable (`docker/android/Dockerfile:29`) and the `GPU_ACCELERATED` branch that selects `-gpu host` (`docker/android/scripts/start-emulator.sh:54-59,78`) are dead code: the `COPY` that would place `start-emulator.sh` into the image is commented out (`docker/android/Dockerfile:88-94`), so nothing in the running image ever reads either name. They are deletion candidates under P3, not configuration to reactivate.

**2. No state persists between tasks.** The flags `-read-only`, `-no-cache` and `-no-snapshot-save` (`modules/rv-android-core/src/rv_android_core/util/android/android.py:105-110`) are a requirement, not an accident. They exist to guarantee that each task starts from an identical device state, and `-read-only` is additionally what permits several containers to open the same `/data/RVSec.avd` at once.

**3. Cold boot on every task is the accepted, irreducible price of (2).** Because nothing persists, `/data/RVSec.avd` remains permanently in a never-booted state, and every boot repeats zygote start, boot-image `dex2oat`, and the first package-manager scan in full. This cost is accepted, not mitigated.

**4. The boot and adb timeouts are parameterized by environment variable, read at the point of use.** `RV_EMULATOR_BOOT_TIMEOUT`, `RV_ADB_CMD_TIMEOUT` and `RV_APK_INSTALL_TIMEOUT` are declared as `ENV_*` constants in `modules/rv-android-core/src/rv_android_core/constants.py` (per ADR 0001) and resolved inside `rv-android-core` at the call site, following the "L1 cross-layer infra exception" established by gh55 and implemented for `RV_PYDANTIC` in `modules/rv-android-core/src/rv_android_core/util/validation/config.py:75-88`. Precedence is argument, then environment, then default. These are host- and concurrency-dependent operational values, not properties of the experiment being run.

The single sentence that ties the four together: **the only correct response to an irreducible cost is to size the budget for it.** That is why restoring the gate and sizing/parameterizing the budget must ship together — a working gate under a budget calibrated for a cost that was never measured merely relabels the same failures.

## Alternatives Considered

**D1 — Warm the AVD at image build time.** Boot the emulator once during `docker build`, let it complete `dex2oat` and the first package scan, and bake the resulting warm state into the image so that runtime boots are short. Rejected as **technically impossible**, not merely undesirable: `docker build` does not expose `/dev/kvm` (the composes map it as a runtime device, and there is no build-time equivalent), so the build-time boot would run under pure software emulation. It would also produce persisted state, colliding with decision (2).

**D2 — Runtime snapshots / quickboot.** Save a snapshot after the first boot of a container and restore from it for subsequent tasks. Rejected: this is persistence by definition. Restored state carries whatever the previous task left behind, which is precisely the contamination decision (2) exists to prevent. The speed gain is real; it is bought with the validity of every metric downstream.

**D3 — Reuse one emulator across tasks.** Boot once per container and run several tasks against the same live device. Rejected for the same reason as D2, more directly: no teardown means no reset, and the second task's coverage measurement is conditioned on the first task's residue.

**D4 — Remove `-read-only` and/or `-no-cache`.** These flags cost boot time; dropping them would let the AVD retain its dexopt cache. Rejected on two independent grounds. First, it breaks task isolation (D2/D3 again). Second, `-read-only` is what allows more than one container to open the same `/data/RVSec.avd`; without it, parallel instances of the same AVD are not possible at all, and parallelism is how experiment throughput is obtained.

**D5 — Enable GPU acceleration (device passthrough, `-gpu host`, or Xvfb + a virtual framebuffer).** Rejected by project decision. Independently of the deployment cost, the rv-uiautomator timing constants are documented as tuned for software rendering, so switching the rendering mode silently invalidates a calibration already in production use — the change would not be confined to the emulator. The dead `GPU_ACCELERATED` branch in `docker/android/scripts/start-emulator.sh` is the residue of this path, and its presence in the tree is the reason it keeps being re-proposed.

**D6 — Expose the boot timeout as a CLI flag instead of an environment variable.** Rejected: `modules/rv-experiment/src/rv_experiment/__main__.py:296-303` carries an explicit in-code instruction not to expand the per-flag Click `envvar=` pattern, which is a gh55 stopgap awaiting an architectural fix. Adding a flag here would expand exactly the pattern that instruction forbids.

**D7 — Thread the timeout through `ExperimentConfig` → `PlatformConfig` → `TaskConfiguration`.** This is the route `no_window` takes, so it is an established path. Rejected under P1: it means editing two modules to carry a value consumed in a third, arriving at a function that reads no configuration today — plumbing across three module boundaries to reach a fourth. It would also raise the efferent coupling of the Layer-1 foundation module for an operational knob.

## Consequences

**Positive.**

- The three constraints now have a written home. The next reader who sees a long boot budget finds the reasons before proposing GPU pinning, snapshot warming, or emulator reuse for the third time.
- Task isolation is stated as a requirement with a named cause, so `-read-only` / `-no-cache` / `-no-snapshot-save` cannot be removed as a "performance optimization" without contradicting an accepted decision.
- The boot budget becomes adjustable per host and per concurrency level without a code change or an image rebuild, which is what makes it possible to raise it once the real boot-time distribution under contention is known.
- Reading at the point of use leaves `rv-android-core`'s dependency set untouched: no new inter-module edge is introduced.

**Negative / Trade-offs.**

- Boot time per task stays at its full cold-boot cost, permanently. Every avenue for reducing it is closed by this ADR; throughput can only be recovered through parallelism, not through faster individual boots.
- Environment variables are less discoverable than CLI flags. Mitigated by the ADR 0001 machinery: every name is an `ENV_*` constant, `docker/rvandroid/scripts/validate_env_vars.sh` rejects unknown `RV_*` names, and `scripts/check_env_vars_drift.py` requires each constant to be documented in `README.md` or `.env.example`.
- A misconfigured value is a silent operational hazard in one direction: a budget set too low turns healthy slow boots into task failures. Mitigated by resolving invalid values loudly rather than falling back to a default, and by logging the observed boot `elapsed` so the distribution can be measured rather than guessed.
- The dead GPU code (`EMU_GPU_MODE`, the `GPU_ACCELERATED` branch, the commented `COPY`) is documented here but not deleted here. Until it is removed, the tree still contains a plausible-looking GPU switch that this ADR says must not be used.

**Neutral.**

- The emulator argv itself is unchanged by this decision — it already implements constraints (1) through (3). What changes is that the flags now have a recorded rationale and are load-bearing rather than incidental.
- Tuning `hw.ramSize`, `hw.cpu.ncore` and `disk.dataPartition.size` is neither adopted nor rejected here. Those are AVD sizing questions that require measurement first and belong to a separate change.

## References

- GitHub Issue: #92
- Change: `openspec/changes/gh92-emulator-boot-gating/` — `proposal.md` (C1, C4, Out of scope), `design.md` (Context; decision D2)
- Emulator launch flags and boot gate: `modules/rv-android-core/src/rv_android_core/util/android/android.py:100-127` (argv), `:143` (`_wait_for_boot` budget)
- L1 cross-layer infra exception pattern: `modules/rv-android-core/src/rv_android_core/util/validation/config.py:75-88`
- In-code prohibition on expanding the Click `envvar=` pattern: `modules/rv-experiment/src/rv_experiment/__main__.py:296-303`
- Software-rendering calibration: `modules/rv-uiautomator/src/rv_uiautomator/constants.py:4-6`
- Dead GPU path: `docker/android/Dockerfile:29` (`EMU_GPU_MODE`), `docker/android/Dockerfile:88-94` (commented `COPY`), `docker/android/scripts/start-emulator.sh:54-59,78`
- Runtime `/dev/kvm` mapping (absent at build time): `docker/docker-compose.aperv-comparacao.yml:29` and the other emulator composes
- Env-var registry and lint: `modules/rv-android-core/src/rv_android_core/constants.py`, `scripts/check_env_vars_drift.py`, `docker/rvandroid/scripts/validate_env_vars.sh`
- Related ADRs: 0001 (environment-variable pattern: `ENV_*` registry + Layer Purity)

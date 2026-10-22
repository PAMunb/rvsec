## Why

The e03igg4 investigation (`docs/20261021_e03igg4_investigacao.md`, outside git) found two harness-side
reasons why the comparison between the `ape` arm and the `aperv` cells did not isolate the guidance:

- **The arms did not get the same host time.** The `ape` arm is killed exactly at its budget, while
  `aperv` gets 45 s of teardown grace on top of it, so `ape` loses its startup seconds and `aperv` does
  not. They also do not capture the same things: upstream APE writes a screenshot and a GUI-tree XML on
  every step, while `aperv` writes per-step captures in no cell.
- **The MOP coin was spending steps on targets that never paid off.** The callback families added by
  the callback stamp (menu, navigation drawer, preference, dialog) took 798 MOP coin steps in `mop` (11 %
  of the coin's steps, 90 tasks, 33 APKs). No MOP misuse followed any of them, and none of 800 such steps
  in `as_mop` did either.

Pedro decided on 21/10/2026 (`docs/20261021_plano_base_igual_ape.md` §3.2, §3.3 and §3.5) to give both
arms the same grace and the same capture policy, and to take these callback families out of the coin.
No GitHub issue.

## What Changes

- **One teardown grace for every APE-family tool.** The 45 s grace moves to `rv-android-core`
  constants. `aperv-tool` reads it both for the command timeout and for the completion floor, and so
  does the `aperv-tool` liveness analysis, which drops its own copy.
- **The `ape` built-in gets the grace and `aperv`'s completion rule.**
  - The command timeout becomes the budget plus the grace.
  - A run that returns before the budget minus the grace raises `RVToolExecutionError`, so the task is
    stored as ERROR and resumed.
  - A non-zero exit code is no longer an error, because APE exits non-zero when the app under test
    crashes.
  - **BREAKING** for comparisons: `ape` results stop being comparable with e03igg/e03igg4.
- **The `ape` built-in pushes `/data/local/tmp/ape.properties`** before each run, with exactly
  `ape.takeScreenshotForEveryStep=false`, `ape.saveGUITreeToXmlEveryStep=false` and
  `ape.takeScreenshotForNewState=true`. The arm then captures once per new abstract state instead of on
  every step. This is the only setting of the `ape` arm that departs from the author's defaults.
- **The MOP artifact derivation drops the library-dispatched app callbacks from the handler table.**
  - `onOptionsItemSelected`, `onNavigationItemSelected`, `onMenuItemClick`, `onMenuItemSelected`,
    `onPreferenceClick`, `onPreferenceTreeClick`, `onPreferenceChange` and
    `onClick(DialogInterface,int)` no longer fill `click`.
  - `CALLBACK_PARAMS` is removed. The MOP coin ledger's k = 2 and the distance cut d ≤ 3 are unchanged.
  - `FORMAT_VERSION` stays 2, so a results directory that is reused keeps its cached artifacts. A run
    under this change uses a new results directory.
  - Known limit: the handler table is keyed by class. A class that declares one of these callbacks and
    also a View handler stays listed. On the e7 corpus this is 9 of 3109 callback classes, in 8 APKs.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `tools`: the `ape` built-in gains the teardown grace, the elapsed-time completion rule and the
  pushed `ape.properties` (FR19, NFR04).
- `aperv`: INV-DRV-11 and the handler-table contract shrink to View handlers and Compose `invoke`.
  The cryptoapp scenario's handler table goes from four keys to two. The completion rule
  (INV-APV-60) reads the shared grace (FR04, FR06, FR18).

## Impact

- **Modules:**
  - `rv-android-core`, which gains the shared constant;
  - `rv-tools`, through `builtin/ape/tool.py` and its tests;
  - `aperv-tool`, through `tools/aperv/tool.py`, `tools/aperv/derive_mop_artifact.py`,
    `analysis/liveness.py`, their tests and the module docs.
- **Dependencies:** `aperv-tool` and `rv-tools` already depend on `rv-android-core`, so no dependency
  changes.
- **Docs:** `docs/architecture/ape-rv.md` and `docs/architecture/rv-experiment.md` name the old constant.
- **Out of scope:**
  - The dexlib2 stamp keeps writing these callbacks into `rvsec.click`; the derive no longer reads
    them, and the corpus is not re-instrumented.
  - `experimento-comp162/scripts/admissibility.py` is a frozen campaign file and is not touched.
  - The `ape-rv.jar` changes to the base cell are made in the `ape` repository.

GitHub Issue: #120

## Why

Static analysis guides APE-RV only when a static widget or target matches what the agent sees at run time. In Study 03's E6 (623,566 click steps across the three aperv arms), only 17.3 % of clicks land on a widget GATOR knows; 17.0 % land on a resource id GATOR never emits, and in 53 % of those the owner is app code GATOR does not model (fragments 5.9 % of all clicks; activities, adapters and DialogFragments 3.2 %). Where the bind does work, the signal saturates: 41 % of handlers reach some target and the only question the artifact answers ("does this handler reach any target?") does not discriminate. Two thirds (67.8 %) of the first executions of direct callers during exploration happen after the 3-step arrival window, during interaction, so the per-widget channel matters more than the per-activity one.

The causes are in the producer (GATOR, `rvsec/rvsec-android/rvsec-gator`), all checked in code:
- GATOR models no Fragment at any GUI level, no ViewBinding/DataBinding, no RecyclerView adapter, and of dialogs only `android.app.AlertDialog$Builder` and `new X` of a `Dialog` subclass;
- the reverse BFS (`RvsecAnalysisClient.multiSourceBfs`) keeps only a visited set, so there is no distance, and it is also seeded by library direct callers;
- a D8 lambda wrapper (`X$$ExternalSyntheticLambdaN`) may lack an edge to its own body; the derive compensates with the per-class recovery of INV-DRV-01;
- the `-exclude kotlin.`/`kotlinx.`/`androidx.compose.` options never reach Soot: Soot 4.7.1 reads the exclusion list only in the `Scene` constructor, and GATOR creates the `Scene` in `PrerunEntrypoint.run()` before `soot.Main.main(args)` parses its arguments. Measured on 2026-10-07: call graph, classes and flags are identical with and without the exclusions. The `analysis` spec claims the opposite.

The corpus static analysis for the next campaign starts on 2026-10-07, so the producer must be fixed now. This change lifts in writing, for this fix, the 2026-07-29 rule "do not touch GATOR except for gross errors" (`docs/20260729_propostas_melhorias_e3.md:10`).

## What Changes

- **Distance per target.** The reverse BFS records the level at which it reaches each method, seeded only by the app's direct callers (C = methods with `directlyReachesTarget`). The `.apk.json` gains the list C and, per app method, the distances `[[i, d], …]` to each target `i` with `d ≤ Dmax`. Field names are added on both sides of `JsonSchema.Keys` = `_JK` (INV-ANA-32).
- **Lambda wrapper → body edge.** The call graph used by the BFS links a D8 synthetic-lambda wrapper to the `lambda$…` body it forwards to, so the wrapper gets its own distance and reach flags.
- **Fragments.** A host → fragments map (layout `<fragment>`/`FragmentContainerView`, `add`/`replace` transactions, Navigation graphs, pagers) and each fragment's widgets in a window `Host#Fragment` of type `FRAGMENT` (never `DIALOG`). ViewBinding (`ViewBindings.findChildViewById`) and the framework link `onCreateView` → `onViewCreated(view)`/`getView()` are modeled; they also recover activity listeners.
- **Dialogs, DataBinding and adapters**, with the host being the activity that shows them.
- **Effective exclusions and the app → library boundary target**, applied as decided by the distance experiment of 2026-10-07 (verdict recorded in `design.md`).
- **Placement rule.** Everything that does not depend on the WTG (reachability, distance, boundary set, fragment/dialog/adapter windows) is computed and written in the pre-WTG part of the `.apk.json`, so it survives a WTG timeout. In September 2026, 29 of the 89 APKs with direct callers hit the time cap and 44 of 163 artifacts have no `complete`.
- **Spinner items from array resources.** The programmatic spinner extractor also reads `ArrayAdapter.createFromResource(ctx, R.array.X, layout)` and `getResources().getStringArray(R.array.X)`/`getTextArray(R.array.X)`, resolving the array from the decoded resources. Today a spinner filled that way leaves `entries` empty although its items are static (all 5 spinners of `org.cry.otp_31`).
- **Spec text.** `analysis` describes the real behaviour of the exclusions; `aperv` INV-DRV-01 states the recovery condition as the code applies it.
- **Repeated widget records.** A window keeps one widget record per distinct content: a layout reached from several view roots of one window used to be listed once per root (`org.hwyl.sexytopo_93`: the leg-form dialog built by three methods appeared three times in each of its windows).
- Without any new input applying (no fragment, dialog, binding or lambda wrapper), the `.apk.json` content is unchanged, except that exactly repeated widget records of a window appear once. Widget/window node ids may shift when new classes are loaded (identity-hash iteration), so equality is by content, not bytes.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `analysis`: new `.apk.json` fields (target list, per-method distances, boundary set as decided), the `FRAGMENT` window type and hosted dialog/adapter windows, pre-WTG placement of all WTG-independent sections, BFS seeding by app direct callers only, the lambda edge, and the real exclusion behaviour (replaces the claim at `analysis/spec.md:695` and the scenario at `:844-850`).
- `aperv`: INV-DRV-01 wording of the D8 recovery condition; `FRAGMENT` windows fold onto the host through `_base_activity` like the existing `#` suffixes (no derive code change expected; confirmed in design).

## Impact

- **GATOR** (`rvsec/rvsec-android/rvsec-gator`, Java, outside the uv workspace): `sootandroid` (`Main`, `Flowgraph`, `GUIAnalysis`, new fragment/ViewBinding/library-inflate models), `client` (`RvsecAnalysisClient`, `ReachabilityEngine`, `JsonSchema`, new `fragment`/`hosted`/`reach` packages). The jar is deployed into `rv-android/lib/gator` through `main.basedir`.
- **rv-static-analysis**: `_JK` constants and the parity test (INV-ANA-32), schema/validation of the new fields.
- **aperv-tool**: spec text only, unless design finds a derive change is needed for `FRAGMENT` windows.
- **Not affected**: the APE-RV consumer of the distance and of the handler stamp (change in the `ape` repository); the instrumenter stamp (#121).
- **Cost**: GATOR wall time per APK rises (fragment model and per-target BFS); measured in design on the test APKs. The corpus list and per-app verdicts stay outside rv-android (thesis / replication package).
- PRD: FR04 (GATOR analysis), FR06 (REACH analysis).

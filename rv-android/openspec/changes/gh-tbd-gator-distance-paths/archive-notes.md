# Archive notes — gh-tbd-gator-distance-paths

The sync of this change merges the requirements of `specs/analysis/spec.md` (ADDED and MODIFIED) into `openspec/specs/analysis/spec.md`. It does not merge the text outside the requirements, and the main spec states the entry points and the document's members there too. This file lists those edits so they are made by hand in the same commit as the sync. Every quotation below is the main spec as it stands on branch `wip/gator-paths` before the sync. The line numbers are that file's, so they shift once the edits are made from the top down: apply them from the bottom up, or look each one up by its text.

The delta's own `## Purpose` is not copied. It tells how the three defects were found on 2026-10-19, and the main spec states the current behaviour only (P4). The entry-point sentence below carries what the main spec needs from it.

## 1. Purpose — Key Design Decision 2, the entry points (required)

`openspec/specs/analysis/spec.md:90` lists the entry points as the four manifest component kinds. Since this change the entry points also include the Application subclass and the framework-created classes, and the callbacks seed the same search.

Current text (the part of line 90 to replace):

> Entry points include all four Android component types: Activity lifecycle handlers, Service lifecycle methods (`onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`), BroadcastReceiver (`onReceive`), and ContentProvider lifecycle methods (`onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`).

Replacement:

> Entry points include all four Android component types: Activity lifecycle handlers, Service lifecycle methods (`onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`), BroadcastReceiver (`onReceive`), and ContentProvider lifecycle methods (`onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`). They also include the classes the framework or a library creates and drives, which no app code calls into: the `Application` subclass named in the manifest, every app `Fragment` subclass, the `doWork`/`startWork` of every `ListenableWorker` subclass, and the public methods of every RecyclerView `Adapter` and `ViewHolder` subclass (INV-ANA-95). The callbacks (activity lifecycle handlers, GUI event handlers, Service/Receiver/Provider lifecycle methods) seed the forward search together with the entry points (INV-ANA-94).

The rest of line 90 stays. Its write order ("reachability first … then components") was already out of date before this change (the writer emits `components` before `reachability`, gh60 D14). It is not this change's to fix, but the sync may correct it in the same edit.

## 2. Data Contracts — Output: `pathMethods` and `distancePaths` (required)

Insert after `openspec/specs/analysis/spec.md:335`, the converter's output line:

> - `<out.json>` — the converter's output, byte-identical to the compact document GATOR writes for the same analysis (INV-ANA-87) (destination: the operator)

the three Output lines of the delta (`specs/analysis/spec.md` lines 36–38):

> - `pathMethods: list[str]` — top-level, only with `distancePaths=true`: the Soot signatures of the methods that occur in some step, app and library, sorted by signature; the index space of `distancePaths` (destination: stand-alone readers of the document)
> - `distancePaths: list[[int, int, int]]` — top-level, only with `distancePaths=true`, written right after `reachability`: steps `[i, v, n]`, `i` an index into `distanceTargets`, `v` and `n` indices into `pathMethods`, sorted by `(i, v)`, at most one step per `(i, v)` (destination: same)
> - `path` subcommand stdout — for each target of the method's written pairs, sorted by `i`: one header line `[i] d=<d> <target signature>` followed by the `d + 1` signatures of the chain from the method to the target, one per line, indented by two spaces (destination: the operator)

The delta's fourth Output line (`reachable`, `reachesTarget`, `targetDistances` "as today") is not copied. The flags line already at `:330` and the requirements cover it, and "as today" names a moment, which P4 rules out.

Also replace the parsed-copy line at `:338`, because the copy now lacks the path members too:

> - `<results_dir>/<apk_name>.static.json` -- the source document without `distanceTargets` and `reachability[].methods[].targetDistances`, plus a top-level `source: …`

becomes

> - `<results_dir>/<apk_name>.static.json` -- the source document without `distanceTargets`, `reachability[].methods[].targetDistances`, `pathMethods` and `distancePaths`, plus a top-level `source: …`

with the rest of the line unchanged.

## 3. Data Contracts — the other sections the delta extends (same reason, same commit)

These sit outside the requirements too, so the sync does not carry them either.

**Input.** Insert after `:300` (`<full.json>`) the delta's Input lines 30–33: `-clientParam distancePaths=true|false`, `RVStaticAnalysisConfig.distance_paths` with `--distance-paths`, `rv-static-analysis path DOC METHOD [--target I]`, and the manifest's `<application android:name="…">`. Then replace `:311`:

> - `Scene.v().getCallGraph()` — the SPARK call graph after the client's lambda edges are added (source: GATOR/Soot 4.7.1)

with

> - `Scene.v().getCallGraph()` — the SPARK call graph after the client's lambda edges and empty-site edges are added (source: GATOR/Soot 4.7.1)

**Side-Effects.** After `:350` (the lambda-edge line), add the delta's line 42:

> - **[Soot call graph]**: `EmptySiteEdges.addTo` adds edges to `Scene.v().getCallGraph()` before the reachability search; the WTG reads them only when `cgDelegation=true`

**Error.** After `:365` (the line on fragment, hosted-window and distance pass failures), add the delta's lines 45–47: an `EmptySiteEdges.addTo` failure is logged and the run continues on the graph as it stands; a path-pass failure costs only `pathMethods` and `distancePaths`; and the `path` subcommand's exit 1 cases. Replace `:367`:

> - `rv-static-analysis compact` exits with status 1 and one line on stderr, leaving no output file, when the input is truncated, already compact, holds a non-integer number, or resolves to the same file as the output; exit status 2 is argparse's usage error

with

> - `rv-static-analysis compact` exits with status 1 and one line on stderr, leaving no output file, when the input is truncated, already compact, carries `distancePaths`, holds a non-integer number, or resolves to the same file as the output; exit status 2 is argparse's usage error

The delta's line 48 says the same thing, so this one replacement covers it.

## 4. Invariants — INV-ANA-90 to INV-ANA-98

The main spec's `## Invariants` section ends at `:722` with INV-ANA-89. Append the delta's nine invariants (lines 52–64) after it, in numeric order: 90, 91, 92, 93, 94, 95, 96, 97, 98. The delta lists INV-ANA-98 before INV-ANA-97. Copy each text unchanged.

## Notes on the implemented code (checked against the delta before the sync)

- `EmptySiteEdges` dispatches over the class the invoke's method reference names (`ref.declaringClass()`) and its concrete app subclasses or implementers. This is the receiver's static type as the compiler wrote it. The delta now says "the class the invoke instruction names" throughout (revised 2026-10-19 after the code review). The code takes the app subtypes of a library class as well, for example an app implementer of `java.lang.Runnable` or `kotlin.jvm.functions.Function1` when an empty site in an app method invokes that interface. The requirement's bullet ("on the class the invoke instruction names, when that class is a concrete app class, and on each concrete app subclass or implementer of it") and INV-ANA-96 both match that: the named class itself is a callee holder only when it is a concrete app class, its app subtypes always.
- `path` sorts a method's pairs by `(i, d)`. A method holds one pair per target, so this is the same order as "sorted by `i`". It also refuses a pair whose index lies outside `distanceTargets`, a refusal the requirement does not list.

## Why

GitHub Issue: #113

`derive()` refuses any static-analysis document that does not carry the `"complete": true` sentinel, and that refusal fails the whole task on **both** `aperv` arms. The refusal is too broad: a document without the sentinel is not a defective file, it is the intermediate report the producer writes deliberately when the WTG stage does not finish — valid JSON with intact `reachability` and `windows`, which is exactly the shape `INV-ANA-20` already mandates.

Measured on the `jca_android` corpus of 164 APKs, **45** carry no sentinel and are refused today; **18** of those hold MOP substrate the explorer can use without any WTG. The refusal already cost 12 identities in `experimento-smk111` on 2026-08-31, where the `ape` arm ran normally on the same APKs.

## What Changes

- **BREAKING** (spec-level): `derive()` no longer raises `DerivationError` when the `"complete": true` sentinel is absent or false. A structurally sound document is derived whatever its WTG status, producing an artifact whose `wtg` is empty and whose `stats["wtgEdges"]` is `0`.
- `derive()` keeps refusing a document that is not an object, carries no `package`, or holds a section of the wrong type. Nothing partial is ever returned.
- `_derive_mop_artifact()` is unchanged and keeps failing on unreadable or unparseable JSON, leaving no temporary file behind.
- The `derive()` docstring stops promising the sentinel refusal.
- Four tests move: the two that pin the refusal are replaced by the positive case; the two that used `complete: False` merely as a convenient `DerivationError` trigger switch to a failure that remains a failure.

Nothing changes on the Java side and nothing changes in the GATOR producer. No new field, column or gate is introduced: the `<apk>.json` is already archived next to each identity's results, and its `transitions` section answers whether that run had a WTG.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `aperv`: the `DerivationError` contract. The spec currently states that `derive()` raises it when the document is structurally unusable, listing "`complete` absent or false" among the causes. WTG absence stops being a cause of refusal and becomes an ordinary property of the derived artifact, observable as an empty `wtg` and `wtgEdges == 0`.
- `analysis`: the requirement "Derived MOP Artifact as a Device-Only Consumer" declares the sentinel to be a precondition of derivation, both in prose and in its scenario "truncated analysis yields no artifact", which states that the MOP arm SHALL fail loudly. That precondition is withdrawn and the scenario is rewritten to describe what the first-pass document actually yields. This is a spec-level edit only: no `rv-static-analysis` code changes, and the sentinel keeps its producer-side meaning (`INV-ANA-31`) untouched.

## Impact

**Modules**: code changes in `aperv-tool` only — `src/aperv_tool/tools/aperv/derive_mop_artifact.py` (the refusal and its docstring), plus `tests/test_derive_mop_artifact.py` and `tests/test_aperv_tool.py`.

**Not affected**: `ape-rv.jar` and every Java scoring pass; `rvsec-gator` and the `JsonReportWriter` that emits the sentinel; `rv-static-analysis` code, whose `StaticAnalysisParser` already reads `complete` as a propagated flag rather than a refusal — only the `analysis` capability spec is edited, because it is where the withdrawn precondition is written down; `rv-platform`; every experiment manifest and gate script.

**Cross-module contract**: the sentinel keeps its producer-side meaning (`INV-ANA-31`) and stays available to consumers that require completeness (`rv-android-core`'s `StaticAnalysisData.complete` documents that consumers "MUST filter on this flag"). What changes is that `aperv-tool` stops being one of them.

**Downstream behaviour**: a run over a WTG-less artifact arms both `aperv` arms. In the jar, `MopData.hasWtgData()` disables `WtgPass`, `FrontierPass` and `MopFrontierPass` on its own, while `MopWidgetPass`, `MenuGatewayPass`, `CoveragePass`, `FormCompletionPass` and the activity-trigger launcher keep running. Three of the four weights the `mop_off_llm_off` control zeroes (`mop_weight_direct`, `mop_weight_transitive`, `mop_weight_open_menu`) feed passes that do not need a WTG, so the arm contrast the experiment measures still exists on those APKs.

**Requirements**: FR14 (static analysis feeding monitored-operation targeting), FR21 (tool execution), NFR03 (robustness of the execution pipeline).

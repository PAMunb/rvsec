## Purpose

This delta renames the Pydantic field family carrying method-of-interest reachability flags from `*_mop` / `*Mop` to `*_target` / `*Target` across the `rv-android-core` domain models that are consumed by every other module. The rename is mechanical and behavior-preserving — only the field names change; the data, semantics, and validation rules are identical. Justification: the JSON contract on the producer side (`analysis` capability delta) is renamed from `reachesMop` to `reachesTarget` to remove semantic hostility once a user loads a `--targets-file` of arbitrary methods (e.g., taint sinks, audit targets) unrelated to JavaMOP specs. The Pydantic models that materialize that JSON must follow.

P3 (no backward compatibility) is honored: the rename is atomic per module via commit C1f; no shims, no dual-naming, no `_unused` renames. Consumers that read the affected fields (`rv-coverage`, `rv-platform`, `rv-experiment`, `aperv-tool`, `scripts/`) are updated in the same commit. `rv-agent` is deprecated and not updated by design.

## ADDED Requirements

### Requirement: Reachability Field Naming in Core Domain Models (FR33, NFR04)

The `rv-android-core` Pydantic domain models that carry method-of-interest reachability flags MUST use the field-name family `*_target` / `*_directly_target` / `target_methods` exclusively. The legacy family `*_mop` / `*_directly_mop` / `mop_methods` MUST NOT survive in any model after this change is merged (INV-CORE-33).

Affected models and their renamed fields:

- `rv_android_core.domain.classes.Method`:
  - `reaches_target: bool` (renamed from `reaches_mop`)
  - `directly_reaches_target: bool` (renamed from `directly_reaches_mop`)
- `rv_android_core.domain.widget.Widget`:
  - `reaches_target: bool` (renamed from `reaches_mop`)
  - `directly_reaches_target: bool` (renamed from `directly_reaches_mop`)
- `rv_android_core.domain.widget.WidgetEvent`:
  - Field reserved for future enrichment: `handler_reaches_target` and `handler_directly_reaches_target` are NOT added in this change (they belong to follow-up change C3 `agent-enrichment`). The naming convention is established here so C3 can add fields without further renames.
- `rv_android_core.domain.components.ComponentInfo`:
  - `reaches_target: bool` (renamed from `reaches_mop`)
  - `directly_reaches_target: bool` (renamed from `directly_reaches_mop`)
  - `target_methods: List[str]` (renamed from `mop_methods`) — list of resolved target signatures attributed to this component
- `rv_android_core.domain.wtg.WindowTransition`:
  - `target_reaches_target: bool` — Python `@property` derived from the methods of the target window. The transition itself does not embed the target window object; the property resolves `target_window` indirectly via a `window_id → List[Method]` map populated by `StaticAnalysisParser` and exposed to the transition through a parser-owned context (constructor injection of `window_methods_index: Mapping[str, list[Method]]` keyed by `target_window_id`). This avoids storing derived data (INV-CORE-34) while keeping the property accessible without re-traversing `StaticAnalysisData`. Renamed from `target_reaches_mop`; behavior unchanged.

The Pydantic `field description` strings for renamed fields MUST use the term "target method" (replacing "MOP method") to align the docstring with the new field name.

**New field introduced by this change:** `rv_android_core.domain.static.StaticAnalysisData.complete: bool` (default `False`) — the parser surface of the JSON sentinel emitted by `JsonReportWriter`. Declared here (not in `analysis` spec) because the field lives on a `core` Pydantic model and is consumed by every downstream module. Default `False` so that truncated outputs parse without error. No other new fields. No fields are removed (the rename preserves the field; only the name changes).

**Module**: rv-android-core (`src/rv_android_core/domain/classes.py`, `widget.py`, `components.py`, `wtg.py`, `static.py`).

#### Scenario: Method instantiation with renamed fields

- **WHEN** `Method(signature="<com.example.Foo: void bar()>", reaches_target=True, directly_reaches_target=False)` is constructed
- **THEN** the instance MUST have `method.reaches_target == True`
- **AND** `method.directly_reaches_target == False`
- **AND** accessing `method.reaches_mop` MUST raise `AttributeError` (P3 — no shim)

#### Scenario: Widget instantiation with renamed fields

- **WHEN** `Widget(id=1, type=WidgetType.BUTTON, reaches_target=True, directly_reaches_target=True)` is constructed
- **THEN** the instance MUST have both renamed fields populated
- **AND** legacy attribute access MUST raise `AttributeError`

#### Scenario: ComponentInfo instantiation with renamed fields

- **WHEN** a `ComponentInfo` for a Service is constructed with `reaches_target=False` and `target_methods=["<com.example.S: void onCreate()>"]`
- **THEN** the instance MUST have `component.reaches_target == False`
- **AND** `component.target_methods == ["<com.example.S: void onCreate()>"]`
- **AND** legacy attribute access (`reaches_mop`, `mop_methods`) MUST raise `AttributeError`

#### Scenario: WindowTransition derived property with window methods index

- **WHEN** a `WindowTransition` is constructed with `target_window_id="W2"` and the parser provides a `window_methods_index` where `index["W2"]` contains at least one `Method` with `reaches_target == True`
- **THEN** the `@property target_reaches_target` MUST return `True`
- **AND** the property MUST be lazy (computed on access, not stored — INV-CORE-34)
- **AND** the legacy property name `target_reaches_mop` MUST NOT exist on the class
- **AND** when no `window_methods_index` is injected (e.g., orphan transition constructed in unit test), the property MUST return `False` rather than raise

#### Scenario: Pydantic deserialization from JSON with new key names

- **WHEN** `Method.model_validate({"signature": "<...>", "reaches_target": true, "directly_reaches_target": false})` is invoked
- **THEN** validation MUST succeed
- **AND** the resulting instance MUST have the renamed fields populated correctly

#### Scenario: Pydantic deserialization with legacy keys under RV_PYDANTIC=true

- **WHEN** `Method.model_validate({"signature": "<...>", "reaches_mop": true})` is invoked AND the env var `RV_PYDANTIC=true` is active (development/CI mode — `extra="forbid"` semantics)
- **THEN** Pydantic MUST raise `ValidationError` indicating `reaches_mop` is not a valid field (P3 — no field alias for the legacy name)

#### Scenario: Pydantic deserialization with legacy keys under RV_PYDANTIC=false

- **WHEN** `Method.model_validate({"signature": "<...>", "reaches_mop": true})` is invoked AND `RV_PYDANTIC` is unset or `false` (production mode — `extra="ignore"` per existing `BaseValidatedModel` behavior)
- **THEN** the legacy key MUST be silently dropped
- **AND** `reaches_target` MUST default to its declared default value
- **AND** no warning or error MUST be emitted

#### Scenario: StaticAnalysisData sentinel default

- **WHEN** `StaticAnalysisData.model_validate({...})` is invoked on a JSON payload that does not include the `complete` key
- **THEN** validation MUST succeed
- **AND** `data.complete` MUST be `False`

## Invariants

- **INV-CORE-33**: After commit C1f, no Pydantic model in `rv_android_core.domain` MUST contain a field whose name ends with `_mop`, `_directly_mop`, or equals `mop_methods`. Verified by AST inspection in `tests/domain/test_no_legacy_mop_fields.py` (part of the `G_no_legacy_mop` CI gate scope).
- **INV-CORE-34**: The `target_reaches_target` member on `WindowTransition` MUST be implemented via the `@property` decorator, not as a stored Pydantic field. Verified by `tests/domain/test_wtg.py` asserting `isinstance(WindowTransition.__dict__['target_reaches_target'], property)`. Storing it as a field would duplicate derivable data (P1 violation).

## Data Contracts

### Input

- Pydantic models receive their data from `rv_static_analysis.parser.static.static_analysis_parser` (which reads the GATOR JSON via `_JK` constants). The parser populates the renamed fields directly — no transformation layer.

### Output

- Renamed fields are read by `rv-coverage` (for `cov_reaches_target` CSV header and aggregation), `rv-platform` (in coverage components), `rv-experiment` (in post-processing scripts), `aperv-tool` (in prioritizer and transition_picker), and `scripts/` (in aggregators).

### Error

- `AttributeError` — raised on any attempt to access the legacy field names (`reaches_mop`, etc.) on instances. No shim is provided.
- `pydantic.ValidationError` — raised on deserialization if a required renamed field is missing (subject to existing `BaseValidatedModel` semantics around `RV_PYDANTIC`).

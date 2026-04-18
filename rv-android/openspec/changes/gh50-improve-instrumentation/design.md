## Context

The instrumentation pipeline has very low success rates on modern APKs (17.5% JCA, 54% generic_new). Analysis of 1164 APKs across 3 datasets identified d8 rejecting ajc-corrupted stack frames in library code as the dominant failure family (64%). Three layered improvements target distinct error families. GitHub Issue: #50, builds on #49 (error masking fix).

References: FR02, NFR04. Main file: `modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py`.

## Architecture

```
weaving_excludes.yaml (assets/)
    │
    ▼ _generate_aop_xml() [NEW]
aop.xml (generated in tmp/)
    │
    ▼
ajc -xmlConfigured -proceedOnError -Xlint:ignore -inpath ... -d ... -source 1.8
    │
    ▼
d8 --no-desugaring --release --min-api 26 --lib android.jar
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `_generate_aop_xml()` [NEW] | Generate aop.xml from YAML patterns | `weaving_excludes.yaml` | `aop.xml` in `tmp_dir` |
| `__weave_monitors()` [MODIFIED] | Add `-proceedOnError` and `-xmlConfigured` to ajc | ajc command | woven classes (partial on error) |
| `__d8()` [MODIFIED] | Add `--no-desugaring` to d8 | d8 command | DEX bytecode |
| `RVInstrumentationConfig` [MODIFIED] | Resolve `weaving_excludes.yaml` path | config | excludes file path |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|------------------------|----------------|------|
| INV-INS-13: d8 --no-desugaring | `rvandroid.py:__d8()` — add flag | `test_d8_includes_no_desugaring` |
| INV-INS-14: ajc -proceedOnError | `rvandroid.py:__weave_monitors()` — add flag | `test_ajc_includes_proceed_on_error` |
| INV-INS-15: -xmlConfigured + aop.xml | `rvandroid.py:__weave_monitors()` + `_generate_aop_xml()` | `test_aop_xml_generated_from_yaml` |
| INV-INS-16: default exclude patterns | `assets/weaving_excludes.yaml` | `test_default_excludes_loaded` |
| Backward compat: no YAML = no flag | `__weave_monitors()` conditional | `test_no_yaml_no_xml_configured` |

## Goals / Non-Goals

**Goals:**
- Improve instrumentation success rate from ~17% to ~50-70% for JCA specs
- Preserve full MOP monitoring of app code (only library code excluded)
- Maintain backward compatibility when `weaving_excludes.yaml` is absent
- Configurable exclude patterns (researchers can tune per experiment)

**Non-Goals:**
- Fixing dex2jar conversion issues (separate tool, different problem)
- Replacing AspectJ with alternative weaving tools (DiSL, ASM)
- Dynamic per-APK exclude lists (static YAML is sufficient)
- Pre-filtering Python fallback (evaluate after empirical test; implement in separate change if needed)

## Decisions

### D1: `aop.xml` generation vs static file

**Choice**: Generate `aop.xml` at runtime from YAML patterns.

**Alternative**: Ship a static `aop.xml` in assets/.

**Rationale**: YAML is more readable and maintainable than XML. Runtime generation allows researchers to modify patterns without understanding AspectJ XML syntax. The `aop.xml` is a build artifact, not a configuration artifact.

### D2: Where to place generated `aop.xml`

**Choice**: In `tmp_dir` (same directory as `-inpath` and `-d`).

**Rationale**: `-xmlConfigured` looks for `META-INF/aop.xml` on the classpath. Since `tmp_dir` is in `-inpath`, placing `META-INF/aop.xml` inside `tmp_dir` puts it on the classpath automatically. Cleaned up with other temp files after each APK.

### D3: `-proceedOnError` risk assessment

**Choice**: Always enable `-proceedOnError`.

**Risk**: Partially woven classes may have inconsistent monitoring. A class where ajc failed to inject advice will not be monitored, but its calls to monitored APIs from other (successfully woven) classes WILL be captured.

**Rationale**: Partial monitoring > no APK at all. The alternative (complete failure) means 0% coverage. With `-proceedOnError`, we get coverage for all successfully woven classes.

## API Design

### `_generate_aop_xml(excludes: List[str], output_dir: str) -> Optional[str]`

```python
def _generate_aop_xml(self, excludes: List[str], output_dir: str) -> Optional[str]:
    """Generate META-INF/aop.xml with exclude patterns for -xmlConfigured.
    
    Returns path to generated aop.xml, or None if no patterns provided.
    """
    if not excludes:
        return None
    meta_inf = os.path.join(output_dir, "META-INF")
    os.makedirs(meta_inf, exist_ok=True)
    aop_xml = os.path.join(meta_inf, "aop.xml")
    # Write XML with <exclude within="..."/> for each pattern
    return aop_xml
```

### `_load_weaving_excludes() -> List[str]`

```python
def _load_weaving_excludes(self) -> List[str]:
    """Load exclude patterns from weaving_excludes.yaml in assets/.
    
    Returns empty list if file not found (backward compatible).
    """
```

## Data Flow

```
RVInstrumentationConfig
    │ assets/weaving_excludes.yaml
    ▼
_load_weaving_excludes() → ["com.google..*", "androidx..*", ...]
    │
    ▼
_generate_aop_xml(excludes, tmp_dir) → tmp_dir/META-INF/aop.xml
    │
    ▼
__weave_monitors():
    ajc -xmlConfigured -proceedOnError -Xlint:ignore
        -inpath tmp/ -d tmp/ -source 1.8 -sourceroots tmp/
    │
    ▼
__d8():
    d8 monitored.jar --no-desugaring --release --min-api 26 --lib android.jar
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `weaving_excludes.yaml` not found | `_load_weaving_excludes()` | Return empty list, log info | ajc runs without -xmlConfigured (backward compatible) |
| `aop.xml` generation fails | `_generate_aop_xml()` | Log warning, skip -xmlConfigured | ajc runs without exclusion |
| ajc class-level error with -proceedOnError | ajc execution | ajc continues, produces partial output | Other classes are woven normally |

## Risks / Trade-offs

- **[Risk: -proceedOnError produces broken classes]** → Mitigated by d8 rejecting truly invalid bytecode. If a partially-woven class is still invalid, d8 will catch it.
- **[Risk: -xmlConfigured may not prevent frame corruption]** → If ajc still corrupts frames of excluded classes (reads them via -inpath), pre-filtering fallback is needed (separate change). Empirical test will validate.
- **[Trade-off: Excluded library code is not monitored]** → Acceptable. MOP specs target `javax.crypto.*` and `java.util.*` — call sites in app code ARE monitored. Library-internal calls to these APIs are not the research target.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | d8 --no-desugaring flag | Mock Command, verify args | 1 |
| Unit | ajc -proceedOnError flag | Mock Command, verify args | 1 |
| Unit | aop.xml generation from YAML | Write YAML, call _generate_aop_xml, parse result | 2 |
| Unit | _load_weaving_excludes | Test with/without YAML file | 2 |
| Unit | __weave_monitors with -xmlConfigured | Mock, verify flag presence when YAML exists | 1 |
| Unit | __weave_monitors without YAML (backward compat) | Mock, verify flag absent | 1 |
| Empirical | 10 previously-failing JCA APKs | Run instrumentation, measure success | 1 manual |

**Total**: ~8 unit tests + 1 empirical validation

## Open Questions

None — design is complete. Empirical test after implementation will determine if pre-filtering fallback is needed.

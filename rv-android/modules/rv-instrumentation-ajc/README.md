# rv-instrumentation-ajc

AspectJ-based APK instrumentation variant: dex2jar → AspectJ weave → d8 → sign.

`AjcInstrumentation` implements the `Instrumenter` ABC from
`rv-instrumentation-core`. The parent `rv-instrumentation` re-exports shared
types and dispatches to this variant via `get_instrumenter("ajc", config)`.

```python
from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation
from rv_instrumentation_ajc.config import AjcInstrumentationConfig

config = AjcInstrumentationConfig(
    monitor_output_dir="/path/to/monitors",
    android_jar_path="/path/to/android.jar",
    instrumented_dir="/output",
)
results = AjcInstrumentation(config).instrument_apks(apks_dir, results_dir)
```

See `docs/architecture.md` for the full pipeline description and `CLAUDE.md`
for module-level guidance.

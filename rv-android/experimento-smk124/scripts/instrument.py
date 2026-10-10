"""Instrument APKs on the host with a given instr-cli jar and the handler stamp on.

The configuration is the one of the e03mini A/B (data/e03mini_a2/instrument_ab.py):
`jca_android` monitors of experimento-smk121, the shared keystore, `--stamp-handlers`.
The instrumented APKs land in `<out_dir>/instrumented/`, with the per-APK
`instrument_results.json` that carries `weaveCounts`.

Usage: uv run python experimento-smk124/scripts/instrument.py <instr-cli.jar> <out_dir> <apk>...
"""
import sys
from pathlib import Path

from rv_instrumentation_dexlib2.config import DexlibInstrumentationConfig
from rv_instrumentation_dexlib2.dexlib_instrumentation import DexlibInstrumentation

jar, out_dir, apks = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3:]
rv_android = Path(__file__).resolve().parents[2]
config = DexlibInstrumentationConfig(
    cli_jar_path=jar,
    monitor_output_dir=rv_android / "experimento-smk121/results/monitors",
    instrumented_dir=out_dir / "instrumented",
    working_dir=out_dir / "work",
    keystore_file=rv_android / "modules/rv-instrumentation/assets/keystore.jks",
    keystore_password="password",
    keystore_alias="server",
    key_password="password",
    stamp_handlers=True,
)
results = DexlibInstrumentation(config).instrument_apks(
    apks_dir=Path(apks[0]).parent, results_dir=out_dir / "instrumented", apk_paths=apks
)
print(jar, results.success_count, "/", results.total_count, results.errors)

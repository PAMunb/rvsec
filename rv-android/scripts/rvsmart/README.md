# rvsmart Calibration Scripts

Scripts for validating and calibrating the rvsmart Java agent.

## Scripts

### test_hash_equivalence.py

Validates INV-RSM-03: structural hash compatibility between Python rv-agent and Java rvsmart.

The hash algorithm (SHA-256[:12] of canonical JSON with sorted keys) must produce identical
output in both implementations for the same UI tree. This script tests determinism on
UIAutomator XML dumps and, when used with a live device, enables end-to-end comparison.

**Offline (no device needed):**

```bash
# Test determinism on pre-captured XML dumps
python scripts/rvsmart/test_hash_equivalence.py --dumps-dir ./ui_dumps/

# Test a single file
python scripts/rvsmart/test_hash_equivalence.py --file window_dump.xml

# Test with Java-style simplified class names (strips package prefix)
python scripts/rvsmart/test_hash_equivalence.py --dumps-dir ./ui_dumps/ --simplify-class
```

**Live device (requires running emulator):**

```bash
# Capture UI dumps from cryptoapp and run equivalence test
python scripts/rvsmart/test_hash_equivalence.py \
    --live \
    --packages br.unb.cic.cryptoapp \
    --output-dir ./ui_dumps/ \
    --screens-per-app 6
```

**Known class name difference:**

Java `UiCapture.simplifyClassName()` strips the package prefix from class names read
via `AccessibilityNodeInfo.getClassName()`:
- Java path: `"android.widget.Button"` -> `"Button"`
- Python path (UIAutomator XML): `"android.widget.Button"` -> `"android.widget.Button"`

This means hashes from Python XMLs will differ from Java live hashes unless
`--simplify-class` is passed. End-to-end validation requires:
1. Capture a UI dump via `adb shell uiautomator dump`
2. Capture the Java hash from logcat (`adb logcat -s RVSMART`)
3. Run `test_hash_equivalence.py --file dump.xml --simplify-class`
4. Compare the printed hash with the Java-side hash in logcat

### optuna_calibration.py

Bayesian hyperparameter calibration for rvsmart using Optuna TPE sampler.

Each trial generates a `rvsmart.properties` file, pushes it to the device, runs rvsmart
for `--timeout` seconds, parses the `RVSMART_METRICS:` line from stdout, and returns:

```
objective = throughput_evt_per_s * (unique_states / elapsed_s)
```

Trials with crash_rate > 1% return -inf and are discarded.

**Prerequisites:**

```bash
pip install optuna
adb devices  # must show a connected device or emulator
# rvsmart.jar must already be deployed:
adb push target/rvsmart.jar /data/local/tmp/rvsmart.jar
# APK under test must be installed:
adb install apks_examples/cryptoapp.apk
```

**Running:**

```bash
# Single package, 50 trials
python scripts/rvsmart/optuna_calibration.py \
    --package br.unb.cic.cryptoapp \
    --timeout 120 \
    --n-trials 50 \
    --output rvsmart_best.properties

# Multi-package calibration (averages objective across apps)
python scripts/rvsmart/optuna_calibration.py \
    --packages br.unb.cic.cryptoapp,org.secuso.privacyfriendlysudoku \
    --timeout 120 \
    --n-trials 100

# Persistent study (resume on interruption)
python scripts/rvsmart/optuna_calibration.py \
    --package br.unb.cic.cryptoapp \
    --storage sqlite:///rvsmart_calibration.db \
    --study-name rvsmart_v1 \
    --n-trials 200
```

**Output:**

The script writes the best parameters to `rvsmart_best.properties` (or `--output`).
Copy this file to the device for production runs:

```bash
adb push rvsmart_best.properties /sdcard/rvsmart.properties
```

## Tunable Parameters

All parameters map 1:1 to `rvsmart.properties` keys (see `Config.java` for defaults):

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `throttle_ms` | 50 | 50–500 | Delay between actions (ms) |
| `gradual_decay_base` | 200 | 50–500 | GradualDecayScorer base score |
| `gradual_decay_rate` | 0.7 | 0.3–0.95 | Decay rate per visit |
| `gradual_decay_min_visits` | 5 | 3–20 | Visits before decay starts |
| `mop_direct_score` | 500 | 100–1000 | Score for direct MOP-reaching actions |
| `mop_transitive_score` | 300 | 50–500 | Score for transitive MOP-reaching actions |
| `coverage_density_weight` | 200 | 50–500 | CoverageDensityScorer weight |
| `saturation_bonus` | 100 | 20–300 | Bonus for unsaturated states |
| `component_high_priority` | 50 | 10–200 | High-priority widget bonus (EditText, etc.) |
| `component_medium_priority` | 40 | 5–150 | Medium-priority widget bonus (Button, etc.) |
| `strength_weight` | 50 | 10–200 | StrengthScorer weight |
| `reward_score_weight` | 1.0 | 0.1–5.0 | Cumulative reward weight |
| `visitation_penalty_factor` | 15 | 5–50 | Logarithmic penalty per visit |
| `back_decay_per_repeat` | 200 | 50–500 | BACK action score decay per repeat |
| `reward_gamma` | 0.8 | 0.5–0.99 | N-step reward discount factor |
| `reward_propagation_n` | 5 | 3–15 | N for N-step reward propagation |
| `reward_mop_weight` | 5.0 | 1–15 | MOP event reward weight |
| `multi_value_saturation_threshold` | 4 | 2–10 | Saturation threshold for multi-value widgets |
| `ui_coverage_threshold` | 0.8 | 0.5–0.95 | UI coverage threshold for saturation |
| `backtrack_saturation_threshold` | 0.8 | 0.5–0.95 | Saturation level triggering backtrack |
| `max_backtrack_hops` | 8 | 3–20 | Max BFS hops for backtrack path |
| `stuck_max_blocks` | 10 | 3–20 | Stuck threshold (consecutive unchanged screens) |

## Device Setup (one-time)

```bash
# 1. Build rvsmart JAR
cd rvsec/rvsec-android/rvsmart
./gradlew assembleDebug

# 2. Deploy JAR
adb push app/build/outputs/apk/debug/rvsmart-debug.apk /data/local/tmp/rvsmart.jar

# 3. Verify deployment
adb shell "CLASSPATH=/data/local/tmp/rvsmart.jar /system/bin/app_process / br.unb.cic.rvsmart.Main --help"
```

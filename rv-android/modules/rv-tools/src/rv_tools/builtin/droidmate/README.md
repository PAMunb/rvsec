# DroidMate Tool

DroidMate-2 JAR-based Android UI exploration tool. DroidMate-2 is a platform for automated Android app exploration that runs as a local Java process using a fat JAR (~46MB) containing all dependencies.

**Upstream:** https://github.com/uds-se/droidmate

## Execution

Runs as a local `java -jar` process:

```
java -jar droidmate-2-X.X.X-all.jar \
  --Exploration-apkNames=cryptoapp.apk \
  --Exploration-apksDir=/path/to/apks \
  --Output-outputDir=/path/to/output \
  --Selectors-timeLimit=60000 \
  --Selectors-actionLimit=100000000 \
  --Core-logLevel=debug
```

DroidMate-2 uses a `--Category-settingName=value` CLI flag format. The APK path is split into filename (`--Exploration-apkNames`) and directory (`--Exploration-apksDir`) because DroidMate-2 requires them separately.

The JAR is resolved by `JarResolver`, which searches the module directory first.

## Variants

| Variant | Action Limit | Notes |
|---------|-------------|-------|
| `default` | 100,000,000 | Time-limited exploration (controlled by platform timeout) |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `action_limit` | 100,000,000 | Maximum number of actions |
| `device_serial` | emulator-5554 | Target device serial |
| `timeout` | 3,600 | Execution timeout in seconds |

## Docker Usage

```bash
# Standalone (Tier 4 - requires bundled JAR)
docker run --rm --device /dev/kvm \
  -e RV_TOOLS=droidmate \
  -e RV_TIMEOUTS=60 \
  ...
```

The DroidMate-2 JAR (`droidmate-2-X.X.X-all.jar`, ~46MB) is bundled in the module directory — no external volume mount is needed.

## Dependencies

- Java Runtime Environment (JRE)
- `droidmate-2-X.X.X-all.jar` (bundled in module directory, resolved by JarResolver)
- Android SDK (adb)
- Running Android emulator or device

## Process Pattern

`org.droidmate` — used by the platform to detect if the tool process is still running.

## Output

DroidMate creates a `droidmate_output/` directory alongside the trace file containing:
- Model data (state graphs, widget trees)
- Screenshots from exploration
- Action reports and statistics

## ICST Study

DroidMate was one of the 8 official tools in the ICST experiment, contributing JAR-based exploration as an alternative to ADB shell and Python-based tools.

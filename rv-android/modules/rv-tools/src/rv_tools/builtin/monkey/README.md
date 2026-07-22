# Monkey Tool

Android UI/Application exerciser that generates pseudo-random user events (touches, gestures, key presses, system events) for stress testing and monitored operations validation.

**Upstream:** https://developer.android.com/studio/test/monkey

## Execution

Runs via ADB shell command directly on the device:

```
adb -s emulator-5554 shell monkey -v -p <package> <event_count>
```

The tool sends a configurable number of pseudo-random events to the target application. When used with instrumented APKs (JCA or generic specification sets), monkey's random exploration triggers monitored operations that are logged to logcat for coverage analysis.

## Variants

| Variant | Event Count | Seed | Ignore Crashes | Ignore Timeouts | Notes |
|---------|------------|------|----------------|-----------------|-------|
| `default` | 1,000 | none | no | no | Basic exploration |
| `fast` | 500 | 12345 | yes | yes | Reproducible, crash-tolerant |
| `stress` | 10,000 | none | no | no | Extended exploration |

In practice, the `event_count` from variants is a fallback — the platform's `timeout` parameter controls actual execution duration. The monkey process runs until it exhausts events or is killed by the timeout handler.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `event_count` | 1,000,000,000 | Number of events to generate |
| `seed` | none | Random seed for reproducible runs |
| `throttle` | 0 | Delay between events in milliseconds |
| `device_id` | emulator-5554 | Target device serial |
| `verbosity` | 2 | Output verbosity (0-3) |
| `ignore_crashes` | false | Continue after app crashes |
| `ignore_timeouts` | false | Continue after ANR timeouts |
| `ignore_monitored_violations` | true | Skip MOP violations |

## Docker Usage

```bash
# Standalone (Tier 1 - no external dependencies)
docker run --rm --device /dev/kvm \
  -e RV_TOOLS=monkey:fast \
  -e RV_TIMEOUTS=60 \
  -e RV_NO_WINDOW=true \
  ...
```

## Dependencies

- Android SDK (adb)
- Running Android emulator or device

## Process Pattern

`com.android.commands.monkey` — used by the platform to detect if the tool process is still running.

## ICST Study

Monkey was one of the 8 official tools in the ICST experiment. The `default` variant was used for baseline random testing. The `fast` variant with `--ignore-crashes --ignore-timeouts` is recommended for Docker and automated pipelines because it handles app crashes gracefully (non-zero exit codes from crashes cause task failures without these flags).

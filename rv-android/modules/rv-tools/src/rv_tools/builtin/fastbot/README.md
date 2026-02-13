# FastBot Tool

Model-based testing tool with reinforcement learning capabilities for Android app exploration. Developed by ByteDance, FastBot uses Q-learning to build a model of the app and guide exploration toward unexplored states.

**Upstream:** https://github.com/bytedance/Fastbot_Android

## Execution

Runs via ADB shell using `app_process` with multiple JARs set in CLASSPATH:

1. Push 3 JAR files to `/sdcard/` on the device:
   - `fastbot-thirdpart.jar`
   - `framework.jar`
   - `monkeyq.jar`
2. Execute via:
   ```
   adb shell "CLASSPATH=/sdcard/fastbot-thirdpart.jar:/sdcard/framework.jar:/sdcard/monkeyq.jar \
     exec app_process /system/bin com.android.commands.monkey.Monkey \
     -p <package> --agent reuseq --running-minutes <minutes> \
     --throttle <throttle> -v -v"
   ```

The JARs are resolved by `JarResolver`, which searches the module directory first.

## Variants

| Variant | Max Steps | Strategy | Throttle | Timeout | Learning Rate |
|---------|----------|----------|----------|---------|---------------|
| `default` | 10,000 | balanced | 500ms | 3,600s | 0.1 |
| `conservative` | 5,000 | conservative | 1,000ms | 1,800s | 0.05 |
| `aggressive` | 20,000 | aggressive | 200ms | 5,400s | 0.2 |
| `balanced` | 15,000 | balanced | 300ms | 4,200s | 0.15 |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_step` | 10,000 | Maximum exploration steps |
| `strategy` | balanced | Exploration strategy |
| `device_serial` | emulator-5554 | Target device serial |
| `throttle` | 500 | Delay between actions in milliseconds |
| `timeout` | 3,600 | Execution timeout in seconds |
| `learning_rate` | 0.1 | RL learning rate (0.0-1.0) |
| `exploration_rate` | 0.2 | Exploration epsilon |

## Docker Usage

```bash
# Standalone (Tier 1 - JARs bundled in module)
docker run --rm --device /dev/kvm \
  -e RV_TOOLS=fastbot \
  -e RV_TIMEOUTS=60 \
  ...
```

## Dependencies

- Android SDK (adb)
- 3 JAR files (bundled in module directory, resolved by JarResolver):
  - `fastbot-thirdpart.jar`
  - `framework.jar`
  - `monkeyq.jar`
- Running Android emulator or device

## Process Pattern

`fastbot` — used by the platform to detect if the tool process is still running.

## ICST Study

FastBot was one of the 8 official tools in the ICST experiment, providing reinforcement learning-based exploration as a complement to random (monkey), model-based (APE), and policy-based (DroidBot) approaches.

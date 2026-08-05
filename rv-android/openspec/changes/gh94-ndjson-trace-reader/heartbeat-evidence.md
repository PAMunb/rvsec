# Heartbeat evidence — the observation INV-APV-54 requires

Task 4.2's deliverable. This file exists to answer one question with a measurement rather than an
assumption: **do the per-step heartbeat lines actually reach a captured run's `.logcat`?**

They do. INV-APV-54 and its jar-side counterpart INV-SNK-14 forbid deleting `_align_clocks()` and the
UTC-offset reconstruction until that is shown, because the heartbeat is filtered at the device under
any tag outside the capture allowlist — a deletion taken on faith would trade a working mechanism for
an inert one, and would do it silently. The gate is now open.

## The run

| | |
|---|---|
| Date | 2026-08-05 |
| Command | `uv run rv-experiment run --tools aperv --apks-dir ./apks_examples --timeouts 60 --skip-monitors --skip-instrument --skip-static --name gh94_heartbeat` |
| Task id | `61ef88ed-2c43-4524-992b-0fd84f4ab2b4` |
| Run id | `20260805T141540Z-1785987443007-abe25833` |
| Arm | `aperv:default` — the `sata` baseline, `preset=aperv`, `agent=sata` |
| APK | `cryptoapp.apk`, repetition 1, timeout 60 s |
| Device | `emulator-5554`, headless, logcat cleared before capture |
| State | `COMPLETED`, 112 s wall clock, 0 detected errors |
| Trace | `results/gh94_heartbeat/cryptoapp.apk/cryptoapp.apk__1__60__aperv.trace` (672,796 bytes) |
| Logcat | `results/gh94_heartbeat/cryptoapp.apk/cryptoapp.apk__1__60__aperv.logcat` (4,528 bytes) |
| Jar | sha256 `5cebabc54a5202ba216731661bd5a8d2cb291a1632d5ba6844f364af6477b657`, built from the `ape-rearch` worktree 2026-08-05 02:08 |
| `t0` | `1785939340912` |

The `sata` arm was chosen deliberately: the heartbeat is emitted once per exploration step regardless
of arm, so the cheapest arm that exercises the mechanism is the right one. It needs no MOP artifact
and no LLM server, which removes two ways the run could have failed for reasons unrelated to what is
being measured. Monitors, instrumentation and static analysis were skipped for the same reason —
this task counts heartbeats against steps and reads neither coverage nor violations. Coverage is
consequently `0.0` in `tasks.json`, which is the expected consequence of running an uninstrumented
APK and not a finding.

## The counts

Counted four ways, because they fail differently — a raw tag grep catches lines the parser rejects,
the parser's count is what `clock_logcat_join` will actually see, and the distinct-`s` counts catch
duplicates that neither of the first two would reveal.

| Measure | Value |
|---|---|
| Logcat lines matching `ApeRvHb` (raw grep) | **79** |
| Heartbeats parsed by `_read_heartbeats()` | **79** |
| Distinct heartbeat `s` values | **79** |
| `StepRecord`s read by `TraceReader` | **79** |
| Distinct `StepRecord` `s` values | **79** |
| `RUN_START` present | yes |
| `RUN_END` present | yes |

**The two `s` value sets are identical**, covering `1..79` with no gap, no duplicate and no
heartbeat without a step or step without a heartbeat. Every heartbeat the jar wrote survived the
device-side tag filter and reached the file, and the raw and parsed counts agreeing means no line
arrived in a shape the parser refuses.

The lines look like this, and carry the step number beside its run-relative milliseconds:

```
08-05 11:15:44.401  2428  2428 I ApeRvHb : s=1 t=3489
08-05 11:15:45.890  2428  2428 I ApeRvHb : s=2 t=4978
08-05 11:15:48.578  2428  2428 I ApeRvHb : s=3 t=7666
```

That is the whole point of the mechanism: the step series and the violation series now live in one
file, on one clock, in one rendering, so a violation is placed by comparing two stamps whose unknowns
cancel — no year-candidate search, no quarter-hour rounding, no anchor selection (design D-4, D-5).

## Task 4.3 was not triggered

4.3 lists the diagnoses to run if no heartbeat appears — tag mismatch between the repositories, the
jar's heartbeat flag off, or capture launched before Group 1 landed. None was needed. Recorded for
completeness: the tag literal agrees on both sides, `TAG_APERV_HEARTBEAT = "ApeRvHb"` in
`rv-android-core` `util/logging/constants.py:33`, reaching the capture allowlist through
`logcat_manager.py:80` (`default_tags = [RVSEC, RVSEC-COV, ApeRvHb]`), and matching
`NdjsonSink.HEARTBEAT_TAG` on the jar side.

## An unrelated finding this run confirms

The trace's `RUN_START` carries `build = {"sha": "c638142", "time": "2026-08-05T05:08:15Z"}`.

`c638142` is **`../ape`'s master**, not the `ape-rearch` worktree commit the jar was actually built
from. This is design D10's failure reproducing in a real run rather than in an experiment:
`git-commit-id-maven-plugin` cannot read a linked worktree's `HEAD` — `.git` is a file, and the
plugin normalises it to the main repository's common directory. The 2026-08-03 investigation had
predicted exactly this digest from worktree HEAD `0675f67a`.

It is immaterial to this task, which reads heartbeat counts and `StepRecord` counts and never
`BuildInfo.GIT_SHA`. It is **not** immaterial to `gh97`, whose pre-flight check 3 compares
`build.sha` to catch the gh71 failure mode where the image's own default-branch jar wins the mount.
Against a jar stamped this way that check is green and blind. `gh97` 6.2 must supply the stamp on the
command line, as its task already requires:

```
mvn -o package -Dmaven.gitcommitid.skip=true \
    -Dgit.commit.id.abbrev=$(git rev-parse --short HEAD) \
    -Dgit.build.time=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

## What this unblocks

Group 5.5–5.10 — the migration of the clock-to-violation join onto heartbeats and the deletion of the
reconstruction that placement no longer needs. INV-APV-54's precondition is met by measurement.

It also discharges `ape` `rearch-04` 9.1b (INV-SNK-14), which was delegated here on 2026-08-05.
`gh97` 7.2b still re-observes heartbeats across the smoke's three arms, as breadth rather than as the
primary record: this run exercised one arm, and an arm that produced no heartbeat where another did
would be a difference between arms worth catching.

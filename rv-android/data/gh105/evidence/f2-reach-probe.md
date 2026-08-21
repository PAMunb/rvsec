# The reach probe — gh105 task 4.3

This is the task that could have stopped the change. Design D-12 states its blocking condition:
if `UnsatisfiedConstraint` stays at zero on the production path, the weaver is a prerequisite and
the wiring groups must not be started. It runs here, immediately after the first migrated file,
so the kill switch fires before the expensive half rather than after it.

**Verdict: the change is not blocked.** A predicate-derived report produced by the new substrate
reached `errors.csv` three times on one device run. Group 5 may start.

## The question, and why it needed three answers rather than one

"Did a predicate-derived report reach `errors.csv`?" collapses three different failures into one
"no". A monitor that was never woven, a monitor woven at a call site the test never executed, and
a report emitted but lost between the device and the CSV are three separate defects with three
separate remedies, and only the first blocks this change. So the probe was run with one oracle per
layer, each answerable from a committed artefact:

| layer | question | oracle |
|---|---|---|
| L1 | is the read in the shipped APK? | `dexdump` over the instrumented APK's DEX |
| L2 | did the call site execute? | `RVSEC-COV` lines in the run's logcat |
| L3 | did the report reach the CSV? | a row in `errors.csv` carrying the code |

Only an L1 failure is the blocking condition. An L2 failure says the probe did not exercise the
site — it is an inconclusive probe, not a blocked change, and that distinction is what made the
first run readable instead of alarming.

## Two runs, because the first one answered L2 and not L3

Both ran `cryptoapp.apk` (the only APK in `apks_examples/`, and the one whose DEX carries 14
`Cipher.init(int, Key, …)` call sites — 12 in `classes4.dex`, 2 in `classes5.dex`), specification
set `jca_android`, dexlib2, headless, one repetition. The platform owned the emulator lifecycle in
both; no emulator command was issued by hand.

**Run A — `ape`, 60 s** (`results/gh105_reach_probe`). Chosen because three independent runs in
the archive (`gh75_docker_e2e`, `cli_experiment_20260722_120956_ce63f929`, `e2e_resume`) show plain
APE reaching `CipherUtil.des` within 60 s. This time it did not: the 27 covered methods are all UI,
and they end at `CryptographyActivity.validateInputs()`. APE opened the crypto screen and pressed
the execute button with the input fields empty, validation refused, and no `Cipher` was ever
constructed. L1 green, L2 red, L3 therefore uninformative. APE's exploration is stochastic; this is
the same tool and the same APK that reached the code on other days.

**Run B — `aperv:sata_mop`, 300 s** (`results/gh105_reach_probe_b`). The MOP-guided arm, chosen
because `g7_crash_cryptoapp` measured it reaching `CipherUtil.des` with the most sites of any run in
the archive. It reached, and all three layers closed.

## L1 — the read is in the shipped APK

Measured on run B's `instrumented_apks/cryptoapp.apk` (run A's is identical):

* `classes7.dex` defines `br.unb.cic.mop.PredicateStore` with all five nested classes
  (`BoundKey`, `Entry`, `Holder`, `ValueKey`, `ValueTuple`) and `br.unb.cic.mop.PredicateVerdict`
  — 122 references. The new substrate ships.
* `CipherSpec_i2Event` is invoked **14** times outside the monitor DEX: 12 in `classes4.dex`,
  2 in `classes5.dex`. The uninstrumented APK has exactly 14 `Cipher.init(int, Key, …)` call sites
  in exactly those two DEX files. The correspondence is one-to-one — every site the pointcut names
  carries the dispatcher.
* The string `CIPHER-NOBS-00` is present in `classes7.dex`, and in the generated `CipherSpec.rvm`
  alongside six `PredicateStore` references. The read survived generation, weaving and dexing.

Had the probe returned nothing, L1 alone would have said the cause was not the weaver.

## L2 — the call site executed

Run B's logcat carries 73 `RVSEC-COV` lines, among them:

```
<br.unb.cic.cryptoapp.cipher.CipherUtil: byte[] des(java.lang.String)>
<br.unb.cic.cryptoapp.generated.CryptographyActivity: byte[] encryptWithSecretKey(java.lang.String,java.lang.String)>
<br.unb.cic.cryptoapp.generated.CryptographyActivity: void executeHmacOperation()>
```

`summary.csv`: `cov_act` 100 %, `cov_class` 68.75 %, `cov_method` 53.77 %, 11 MOP reports, 10 unique.

## L3 — the report reached `errors.csv`

Three rows carry `code=CIPHER-NOBS-00 ev=i2`, at three distinct sites:

| site | method |
|---|---|
| `CryptographyActivity.java:457` | `encryptWithSecretKey` |
| `CryptographyActivity.java:461` | `encryptWithSecretKey` |
| `CipherUtil.java:54` | `des` |

The row's `code` and `event` columns are populated — the gh104 envelope carried the identity
through the logcat, the parser and the CSV writer without loss. That is the whole chain the probe
was asked about, end to end.

**Precision about what is evidence for what.** The run also emitted two
`SECRETKEYSPEC-CONSTR-00` rows, which are predicate reads but of the **old** substrate:
`SecretKeySpecSpec.mop:45` still reads `ExecutionContext.instance().validate(Property.RANDOMIZED, …)`
— its migration is task 4.10. They show that predicate-derived reports reach the CSV in general;
only the three `CIPHER-NOBS-00` rows are evidence for the new store.

## What the device confirmed that only the harness had shown

Two facts measured on traces in `f2-CipherSpec.md` now have a production witness.

**The guard was suppressing a true accusation.** At `CipherUtil.java:54` the run emits
`CIPHER-ALG-01 ev=i2 val='DES'` — the accusation the file exists to make. On the pre-image the
`i2` guard compiled to `if (!(guard)) return false;` ahead of the body, so a key with no observed
producer took the whole event out, this report included. It is now made on the production path.

**The event body runs before the transition is decided.** The same call at `:54` produced
`CIPHER-NOBS-00`, `CIPHER-ALG-01` *and* `CIPHER-ORDER-00 ev=i2` together: the body ran and accused,
and then the automaton refused the transition. That refusal is the `unsafeAlg` sink recorded in
`f2-CipherSpec.md` — `g3` on `getInstance("DES")` moves to a state whose only exits are more
`getInstance` calls, so the following legitimate `init` draws an ordering report about an ordering
api30 accepts. Recorded there, recorded here, repaired nowhere: it still deserves its own task.

By contrast the two reports at `CryptographyActivity.java:457` and `:461` come with **no** ordering
report. On that path the automaton accepts the `init` and the only accusation is the predicate's —
which is the shape task 4.1 was built to produce.

## Two pipeline defects the probe surfaced, both outside this change

Neither is repaired here; both are recorded so the next reader does not rediscover them.

1. **`ANDROID_SDK_HOME` is not set by the pipeline.** `lib/gator/gator:64` reads it straight from
   `os.environ` and raises `KeyError` when it is absent. Run A lost its static analysis entirely to
   this and reported `cov_*` as zero; run B was given the variable and the analysis completed in
   33 s. Nothing in the experiment configuration supplies it, so any host without it in the shell
   silently loses static analysis.

2. **Static analysis targets the frozen `jca` set even under `--specification-set jca_android`.**
   `StaticAnalysisConfig` defaults `mop_dir` to `…/resources/jca` (`config.py:199-208`) and no
   caller on the `--specification-set` path overrides it. Both runs show the GATOR command line
   carrying `-clientParam mopDir=…/resources/jca`. Under `jca_android` the reachability columns
   (`cov_reachable`, `cov_reaches_target`, `cov_directly_reaches_target`) and the MOP guidance the
   `sata_mop` arm consumes are computed against the wrong specification set. This is not new to
   gh105 — it applies to every `jca_android` experiment run through this path, `gh101_group8`
   included — and it does not affect this probe's verdict, which rests on the woven monitor and
   not on the analysis.

## Reproducing

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
export ANDROID_HOME=/home/pedro/desenvolvimento/aplicativos/android/sdk
export ANDROID_SDK_HOME=$ANDROID_HOME          # without it GATOR dies, see defect 1
uv run rv-experiment run --tools aperv:sata_mop --timeouts 300 --repetitions 1 \
    --apks-dir ./apks_examples --specification-set jca_android \
    --instrumentation-variant dexlib2 --name gh105_reach_probe_b --no-window
```

The reactor must be installed first (`mvn clean install -DskipMopAgent -DskipTests`, JDK 21
prefix): the instrumenter resolves `rvsec-core.jar` from the local repository through
`rv-android/pom.xml`, so the DEX gets `PredicateStore` from there and not from the source tree.
Note that the stale `lib_tmp/` at the repository root is **not** what is used — the instrumenter
passes `-DoutputDirectory=results/<run>/lib_tmp`, a fresh directory per run.

The L1 oracle, on the instrumented APK:

```bash
unzip -o -q results/gh105_reach_probe_b/instrumented_apks/cryptoapp.apk 'classes*.dex' -d /tmp/probe
DEXDUMP=$ANDROID_HOME/build-tools/34.0.0/dexdump
for d in /tmp/probe/*.dex; do
  echo "$(basename $d) predicate=$($DEXDUMP -f $d | grep -c 'PredicateStore\|PredicateVerdict')" \
       "i2=$($DEXDUMP -d $d | grep -c CipherSpec_i2Event)" \
       "nobs=$(strings $d | grep -c CIPHER-NOBS-00)"
done
```

Committed artefacts of both runs are under `data/gh105/evidence/reach-probe/` (`results/` is
git-ignored): run B's `errors.csv`, `summary.csv`, `coverage.csv`, `experiment_config.json` and
`probe-b.logcat`, plus run A's `probe-a-errors.csv` and `probe-a.logcat` — the inconclusive run is
kept because the L2-red reading is the part of the method worth being able to check.

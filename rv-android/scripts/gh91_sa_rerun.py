#!/usr/bin/env python3
"""gh91 — re-analyse 30 APKs under the neutralised manifest package (`Mneut`).

Runs GATOR directly, once per row of the frozen `30_apks.csv`, passing that row's `Mneut`
verbatim as `-clientParam codePackage=`. Writes into a dedicated output directory; the
corpus is never touched.

WHY GATOR IS INVOKED DIRECTLY (change design D1)
    `rv-static-analysis analyze` has no `--code-package` option: its filter key is
    `App(apk).code_package`, which is the declared applicationId or, under
    `--package-detector`, the `PackageDetector` election — never an arbitrary value such
    as `Mneut`. Routing `Mneut` through the CLI would require editing `rv-android-core`,
    which this change excludes.
    The argv built below mirrors `RVStaticAnalysisConfig.get_tool_command`
    (`modules/rv-static-analysis/src/rv_static_analysis/config.py`) verbatim, so the
    invocation is identical to a production one apart from `codePackage`.

WHY THE WTG RUNS HERE
    Study 03's guided arm consumes the derived MOP artefact, and that artefact needs a WTG:
    `_build_wtg` turns `click` transitions into the edges the arm walks. The previous round
    passed `skipWtg=true` and so produced JSONs that carry the corrected key but no
    transitions — right for a reachability-only question, useless for this corpus. These 30
    are the only APKs that have never been analysed with both the corrected key and the WTG,
    which is the whole reason this round exists.

    The cost is real and was the reason to skip it: GATOR's write order is
    components -> reachability -> windows -> transitions, so the WTG is the expensive tail,
    and 9 of these 30 timed out inside it in Phase 7. The escalation ladder in
    `gh91_campaign.py` is what pays that cost, and the completeness predicate there is what
    keeps a timeout inside the WTG from being mistaken for a finished run.

WHY THE PER-APK (memory, timeout) PAIR IS READ BACK FROM THE ORIGINAL LOGS (design D3)
    `rvsec-dataset`'s Phase 7 recorded the exact argv on line 1 of every
    `rvsec-dataset-sa/logs/<id>.apk.log`. Those 30 lines are the authority for each APK's
    budget: 120g/5400 x1, 60g/3600 x1, 56g/3600 x1, 32g/3600 x16, 12g/1800 x11. Flattening
    them to a single pair would cut short the 19 APKs that originally needed more than
    12g/1800. With the WTG running, a budget that runs out no longer necessarily leaves a
    loud failure: the client writes the JSON once before building the WTG, so a kill in the
    tail leaves a file that parses, carries the sentinel, and holds no transitions. Judging
    completeness therefore takes the sentinel *and* the run's own timeout flag — see
    `gh91_campaign.is_complete`.

WHY CONCURRENCY IS BOUNDED BY MEMORY AND NOT BY A WORKER COUNT (design D4/R4)
    The tiers are heterogeneous, so `workers x jvm-memory` cannot express what fits: five
    concurrent 32g workers would demand 160 GB on a 123.48 GiB host. The dispatcher admits
    jobs while the sum of their `--jvm-memory` stays under `--budget-gib` (default 100),
    which reproduces the packings the original sweep ran (8 x 12g = 96 GB) and allows mixed
    ones (2 x 32g + 2 x 12g). The single 120g APK exceeds the budget and therefore runs
    alone, as a deliberate, logged exception: `--jvm-memory` becomes a bare `-Xmx` with no
    `-Xms`, a lazy ceiling rather than a reservation, and that same 120g run completed on
    this host before.

Reuse (design D5): status classification and the truncation-tolerant JSON load come from
`rvsec-dataset`'s Phase 7 runner, imported across repos rather than duplicated. What is new
here is exactly the two pieces that project lacks — the budget-aware dispatcher, and the
direct-GATOR argv that replaces its `build_command`.

Usage:
    python scripts/gh91_sa_rerun.py --plan          # per-APK table, nothing executed
    python scripts/gh91_sa_rerun.py --dry-run       # full argv per APK, nothing executed
    python scripts/gh91_sa_rerun.py --smoke         # infra check on cryptoapp (task 2.1)
    python scripts/gh91_sa_rerun.py                 # all 30, resumable

This is one *round*. The unattended multi-round campaign — escalation, failure
classification, REGISTRO.md — lives in `scripts/gh91_campaign.py`, which drives this module.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# --- Paths ------------------------------------------------------------------------------

RV_ANDROID = Path(__file__).resolve().parent.parent
WORKSPACE = RV_ANDROID.parent.parent  # .../workspace-rv

# The list of the 30 and their keys. It lives at the repository root because the change that
# produced it has been archived, and an archived change directory is not a path anything may
# still read from.
APKS_CSV = RV_ANDROID / "30_apks.csv"

DATASET_ROOT = Path(os.environ.get(
    "GH91_DATASET_ROOT", "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET"))
# The uninstrumented corpus. NEVER the APKS_INSTRUMENTED_* copies: those carry woven
# monitor classes and therefore a different class universe.
APKS_DIR = DATASET_ROOT / "APKS"
# This run's output. `SA_RERUN_gh91/` holds the previous round — a signed deliverable with its
# own `record/` and sha256 manifests — and is never written into again. `REGISTRO`,
# `_campaign_state.json` and `_superseded/` all derive from this path in `gh91_campaign.py`, so
# the whole campaign follows the rename.
OUT_DIR = DATASET_ROOT / "SA_RERUN_gh91_wtg"

# The smoke (change task 2.1) checks the driver's plumbing on a small APK that is NOT one of
# the 30, and writes to a SIBLING directory — never into OUT_DIR, not even in a subdirectory,
# so that the gate's cardinality assertion keeps seeing exactly 30 JSONs however it globs.
SMOKE_OUT_DIR = DATASET_ROOT / "SA_RERUN_gh91_smoke"
SMOKE_APK_PATH = RV_ANDROID / "apks_examples" / "cryptoapp.apk"
SMOKE_PACKAGE = "br.unb.cic.cryptoapp"
SMOKE_JVM_MEMORY = "12g"
SMOKE_TIMEOUT = 1800

# Phase 7's own output, read-only here: line 1 of each log is the original argv.
RVSEC_DATASET_DIR = Path(os.environ.get(
    "RVSEC_DATASET_DIR", str(WORKSPACE / "rvsec-dataset")))
ORIGINAL_LOGS_DIR = Path(os.environ.get(
    "GH91_ORIGINAL_LOGS_DIR", str(WORKSPACE / "rvsec-dataset-sa" / "logs")))
# Phase 7's per-APK outcome records: `seconds`, `sa_status`, `timed_out`. Read-only, and used
# here only to order a round cheapest-first — never to decide a parameter.
ORIGINAL_PROGRESS_DIR = Path(os.environ.get(
    "GH91_ORIGINAL_PROGRESS_DIR", str(WORKSPACE / "rvsec-dataset-sa" / "_progress")))

GATOR_DIR = RV_ANDROID / "lib" / "gator"
GATOR = GATOR_DIR / "gator"
ANALYSIS_CLIENT_JAR = GATOR_DIR / "rvsec-analysis-client.jar"

# --- Analysis constants (as recorded in all 30 original log lines) -----------------------

CG_ALGORITHM = "spark"
CG_DELEGATION = "true"
# No `--succ-depth` was passed originally, so `-succDepth` is omitted here too.

DEFAULT_BUDGET_GIB = 100.0
# Two timeout layers, neither inside the JVM. GATOR's own `--timeout` is enforced by its
# Python launcher, which wraps the JVM in `subprocess.call(timeout=...)` and exits -50 (206
# after masking) on expiry (`lib/gator/gator:111-113`) — it kills the JVM but does NOT reach
# `remove_temp_dirs()` (`:119`), because `sys.exit` raises past it, so a timed-out run leaks
# its apktool temp dir. The outer wait below is not merely belt-and-braces: `decode_res_from_apk`
# runs at `:68`, well before the timed call, so the unpacking phase is covered by this layer
# alone. The grace gives the inner layer a head start rather than racing it.
DEFAULT_GRACE_SECONDS = 120

# --- Cross-repo reuse of Phase 7's classification (design D5) ----------------------------

if str(RVSEC_DATASET_DIR / "src") not in sys.path:
    sys.path.insert(0, str(RVSEC_DATASET_DIR / "src"))
try:
    # `classify_status` maps (sections present, methods total, file existence, timeout) to
    # the dataset's closed `sa_status` vocabulary; `_load_json` is the bracket-recovery
    # loader for a timeout-truncated file; `_kill_group` kills the whole JVM subtree.
    from rvsec_dataset.static_analysis import runner as sa_runner
except ImportError as exc:  # pragma: no cover - environment problem, not a code path
    raise SystemExit(
        f"cannot import rvsec_dataset.static_analysis.runner from {RVSEC_DATASET_DIR}/src "
        f"({exc}). Set RVSEC_DATASET_DIR to the rvsec-dataset checkout."
    )


# --- Plan -------------------------------------------------------------------------------


@dataclass
class Job:
    """One APK to re-analyse, with the budget its own Phase 7 run was given."""

    apk: str
    code_package: str  # `Mneut`, taken verbatim from 30_apks.csv
    manifest_package: str
    jvm_memory: str  # as recorded, lower-case (e.g. "32g"); upper-cased on the argv
    timeout: int
    apk_path: Path
    out_dir: Path
    # Wall clock this APK took in the Phase 7 run, used only to order a round: cheapest
    # first, so results and failures surface early instead of after the longest job.
    prior_seconds: float = 0.0
    mem_gib: float = field(init=False)

    def __post_init__(self) -> None:
        self.mem_gib = _parse_mem_gib(self.jvm_memory)

    @property
    def json_path(self) -> Path:
        return self.out_dir / f"{self.apk}.json"

    @property
    def log_path(self) -> Path:
        return self.out_dir / "logs" / f"{self.apk}.log"


def _parse_mem_gib(mem: str) -> float:
    """Parse a JVM memory string ('12g', '512m') to GiB."""
    s = mem.strip().lower()
    if s.endswith("g"):
        return float(s[:-1])
    if s.endswith("m"):
        return float(s[:-1]) / 1024.0
    if s.endswith("k"):
        return float(s[:-1]) / (1024.0 * 1024.0)
    return float(s) / (1024.0**3)


def _free_ram_gib() -> float | None:
    """Available RAM in GiB from /proc/meminfo, or None if it cannot be read."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / (1024.0 * 1024.0)
    except (OSError, ValueError, IndexError):
        return None
    return None


def _original_argv(apk: str) -> list[str]:
    """Line 1 of this APK's Phase 7 log, tokenised. Raises if the log is absent.

    The line has the form `# cmd: uv run --project ... rv-static-analysis analyze ...`;
    it is the only record of the budget each APK was actually given.
    """
    log = ORIGINAL_LOGS_DIR / f"{apk}.log"
    if not log.is_file():
        raise SystemExit(f"original Phase 7 log missing for {apk}: {log}")
    with log.open(encoding="utf-8", errors="replace") as fh:
        first = fh.readline()
    if not first.startswith("# cmd:"):
        raise SystemExit(f"unexpected first line in {log}: {first[:80]!r}")
    return first.split()


def _flag(tokens: list[str], flag: str) -> str | None:
    try:
        return tokens[tokens.index(flag) + 1]
    except (ValueError, IndexError):
        return None


def _prior_seconds(apk: str) -> float:
    """Wall clock this APK took in Phase 7, or 0.0 if unrecorded (sorts it first)."""
    path = ORIGINAL_PROGRESS_DIR / f"{apk}.json"
    try:
        return float(json.loads(path.read_text(encoding="utf-8")).get("seconds") or 0.0)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return 0.0


def read_plan() -> list[Job]:
    """Build the per-APK parameter table from `30_apks.csv` + the 30 original log lines.

    The CSV supplies the key (`Mneut`) and the expected manifest package; the logs supply
    the `(jvm_memory, timeout)` pair. Both are read verbatim — nothing here recomputes a
    key, and nothing flattens a budget.
    """
    if not APKS_CSV.is_file():
        raise SystemExit(f"missing {APKS_CSV}")
    jobs: list[Job] = []
    with APKS_CSV.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            apk = row["apk"].strip()
            tokens = _original_argv(apk)
            jvm_memory = _flag(tokens, "--jvm-memory")
            timeout = _flag(tokens, "--analysis-timeout")
            if not jvm_memory or not timeout:
                raise SystemExit(f"cannot read (memory, timeout) for {apk} from its log")
            jobs.append(Job(
                apk=apk,
                code_package=row["Mneut"].strip(),
                manifest_package=row["manifest_package"].strip(),
                jvm_memory=jvm_memory,
                timeout=int(timeout),
                apk_path=APKS_DIR / apk,
                out_dir=OUT_DIR,
                prior_seconds=_prior_seconds(apk),
            ))
    return jobs


def smoke_job() -> Job:
    """The infrastructure smoke (change task 2.1): `cryptoapp.apk`, outside the 30.

    It checks the driver, not the corpus — argv assembly, SDK/jar/mopDir resolution, the
    output path, the `"complete": true` sentinel, and the
    `[RvsecAnalysisClient] Filter package:` line landing in the log, which is the evidence
    gate 3.3(b) reads back. A real APK from the list would cost hours and would establish
    nothing the gate does not assert for all 30 afterwards. Its `(memory, timeout)` is the
    corpus base tier, not a recorded pair: this APK has no Phase 7 log, and none is implied.
    """
    return Job(
        apk=SMOKE_APK_PATH.name,
        code_package=SMOKE_PACKAGE,
        manifest_package=SMOKE_PACKAGE,
        jvm_memory=SMOKE_JVM_MEMORY,
        timeout=SMOKE_TIMEOUT,
        apk_path=SMOKE_APK_PATH,
        out_dir=SMOKE_OUT_DIR,
    )


# --- Command ----------------------------------------------------------------------------


def build_argv(job: Job) -> list[str]:
    """The direct-GATOR argv (design D2), mirroring `get_tool_command` field by field.

    Two behaviours of that builder are replicated deliberately and are easy to lose:
    `--jvm-memory` is upper-cased (GATOR receives `32G`), and the launcher is invoked with
    `sys.executable` rather than a literal `python`, which is absent on clean Debian/Ubuntu
    installs and in containers.
    """
    return [
        sys.executable,
        str(GATOR),
        "a",
        "-p", str(job.apk_path),
        "--client-jar", str(ANALYSIS_CLIENT_JAR),
        "--out", str(job.json_path),
        "-client", "RvsecAnalysisClient",
        "-clientParam", f"mopDir={_mop_dir()}",
        "-cgAlgorithm", CG_ALGORITHM,
        "--timeout", str(job.timeout),
        "--jvm-memory", job.jvm_memory.upper(),
        "-clientParam", f"codePackage={job.code_package}",
        "-cgDelegation", CG_DELEGATION,
    ]


def _mop_dir() -> Path:
    rvsec_home = os.environ.get("RVSEC_HOME")
    if not rvsec_home:
        raise SystemExit("RVSEC_HOME is not set — it locates the 23 JCA .mop specs")
    return Path(rvsec_home) / "rvsec" / "rvsec-mop" / "src" / "main" / "resources" / "jca"


def _gator_env() -> dict[str, str]:
    """The environment GATOR needs.

    `lib/gator/gator` reads `os.environ['ANDROID_SDK_HOME']` as a bare subscript — a
    `KeyError` if unset, and it is *not* `ANDROID_HOME`, which is the one usually exported.
    """
    env = dict(os.environ)
    if "ANDROID_SDK_HOME" not in env:
        sdk = env.get("ANDROID_HOME") or env.get("ANDROID_SDK_ROOT")
        if not sdk:
            raise SystemExit(
                "neither ANDROID_SDK_HOME nor ANDROID_HOME/ANDROID_SDK_ROOT is set")
        env["ANDROID_SDK_HOME"] = sdk
    return env


# --- Execution --------------------------------------------------------------------------

# Every GATOR child is started with `start_new_session=True`, so it does NOT die with this
# process — that is deliberate (it lets the outer timeout kill the whole JVM subtree), but it
# means an interrupted run would otherwise orphan multi-hour JVMs holding tens of GB. The
# registry lets a caller shut them down explicitly; the campaign runner does so on a signal.
_LIVE_PROCS: set[subprocess.Popen] = set()
_LIVE_LOCK = threading.Lock()


def kill_running() -> int:
    """Kill every GATOR process group still running. Returns how many were signalled."""
    with _LIVE_LOCK:
        procs = list(_LIVE_PROCS)
    for proc in procs:
        try:
            sa_runner._kill_group(proc)
        except Exception:  # best effort: a dead pid must not mask the shutdown
            pass
    return len(procs)


def run_one(job: Job, *, grace: int) -> dict:
    """Run GATOR on one APK and classify the outcome. Never raises.

    The log is the gate's evidence, not a convenience: assertion 3.3(b) reads the
    `[RvsecAnalysisClient] Filter package: <Mneut>` line out of it, which is the only place
    the filtering key is recorded at all — the JSON's top-level `package` field is the
    *manifest* package regardless of what was filtered on.
    """
    argv = build_argv(job)
    job.log_path.parent.mkdir(parents=True, exist_ok=True)
    base = {
        "apk": job.apk,
        "code_package": job.code_package,
        "jvm_memory": job.jvm_memory,
        "timeout": job.timeout,
        "argv": argv,
        "log_path": str(job.log_path),
        "json_path": "",
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }

    # Pre-clean any stale/partial JSON so existence after the run is meaningful.
    try:
        job.json_path.unlink(missing_ok=True)
    except OSError:
        pass

    outer_timeout = job.timeout + grace
    start = time.monotonic()
    timed_out = False
    returncode = -1
    try:
        with job.log_path.open("w", encoding="utf-8", errors="replace") as log:
            log.write(f"# cmd: {' '.join(argv)}\n")
            log.write(f"# cwd: {RV_ANDROID}\n")
            log.write(f"# jvm_memory: {job.jvm_memory}  timeout: {job.timeout}s  "
                      f"outer: {outer_timeout}s\n")
            log.write(f"# codePackage: {job.code_package}  "
                      f"manifest_package: {job.manifest_package}\n")
            log.write(f"# started: {base['started_at']}\n\n")
            log.flush()
            proc = subprocess.Popen(
                argv,
                cwd=str(RV_ANDROID),
                stdout=log,
                stderr=subprocess.STDOUT,
                env=_gator_env(),
                start_new_session=True,  # own process group -> clean kill of the JVM subtree
            )
            with _LIVE_LOCK:
                _LIVE_PROCS.add(proc)
            try:
                returncode = proc.wait(timeout=outer_timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                sa_runner._kill_group(proc)
                returncode = -1
                log.write(f"\n# OUTER TIMEOUT after {outer_timeout}s — group killed\n")
            finally:
                with _LIVE_LOCK:
                    _LIVE_PROCS.discard(proc)
    except Exception as exc:  # never let one APK kill the run
        return {**base,
                "sa_status": sa_runner.STATUS_FAILED_EXCEPTION,
                "seconds": round(time.monotonic() - start, 1),
                "returncode": returncode,
                "timed_out": timed_out,
                "error": f"driver error: {str(exc)[:200]}"}

    seconds = round(time.monotonic() - start, 1)
    json_exists = job.json_path.is_file()
    raw = sa_runner._load_json(job.json_path) if json_exists else None
    # GATOR's launcher exits -50 on its own timeout (206 once the shell masks it). With the
    # WTG running, that timeout most often lands in the WTG builder, after the client has
    # already written the JSON — so a file on disk proves nothing by itself, and the flag
    # recorded here is what the campaign reads to tell a finished run from a killed one.
    inner_timed_out = returncode in (-50, 206)
    status = sa_runner.classify_status(
        raw, json_exists=json_exists, timed_out=timed_out or inner_timed_out)
    return {**base,
            "sa_status": status,
            "json_path": str(job.json_path) if json_exists else "",
            "seconds": seconds,
            "returncode": returncode,
            "timed_out": timed_out or inner_timed_out}


def _write_progress(record: dict, out_dir: Path) -> None:
    """Atomically record one APK's outcome under `_progress/<id>.json` (temp + os.replace).

    Same convention as Phase 7's sweeper, so a killed run never leaves a half-written entry.
    """
    pdir = out_dir / "_progress"
    pdir.mkdir(parents=True, exist_ok=True)
    path = pdir / f"{record['apk']}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=0, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


# --- Dispatcher -------------------------------------------------------------------------


def _admits(job: Job, running: dict, budget: float) -> bool:
    """Whether `job` may start now given what is already running.

    A job larger than the whole budget (the 120g tier) is admitted only into an empty
    host — it is the recorded exception of design R4, not a packing decision. While such a
    job runs, nothing else is admitted.
    """
    if any(j.mem_gib > budget for j in running.values()):
        return False
    if job.mem_gib > budget:
        return not running
    used = sum(j.mem_gib for j in running.values())
    return used + job.mem_gib <= budget


def run_all(jobs: list[Job], *, budget: float, grace: int,
            on_done: Callable[[dict, Job], None] | None = None) -> list[dict]:
    """Run every job under the memory budget, cheapest first within a memory tier.

    Ordering is by `prior_seconds` — the wall clock the Phase 7 run measured — so a round
    delivers its quick results first and a failure shows up early. A job that exceeds the
    whole budget can only ever run alone; ordering cannot overlap it with anything, so it
    costs nothing to let the cheap jobs go first.

    `on_done` is called with each APK's record as soon as it finishes, before the next one
    is awaited. The campaign runner uses it to flush `REGISTRO.md` after every APK, which is
    what makes an unattended overnight run inspectable and resumable (design D8/D10).
    """
    pending = sorted(jobs, key=lambda j: (j.prior_seconds, j.apk))
    running: dict = {}
    records: list[dict] = []
    total = len(pending)

    with ThreadPoolExecutor(max_workers=max(1, total)) as pool:
        while pending or running:
            for job in list(pending):
                if not _admits(job, running, budget):
                    continue
                pending.remove(job)
                if job.mem_gib > budget:
                    print(f"  [budget exception] {job.apk} requests {job.jvm_memory} > "
                          f"budget {budget:g}g — running alone (design R4)")
                running[pool.submit(run_one, job, grace=grace)] = job
                used = sum(j.mem_gib for j in running.values())
                print(f"  start {job.apk}  ({job.jvm_memory}/{job.timeout}s)  "
                      f"in flight={len(running)} using ~{used:g}g")
            if not running:
                raise RuntimeError(
                    f"nothing admissible and nothing running; {len(pending)} pending — "
                    f"raise --budget-gib")
            done, _ = wait(list(running), return_when=FIRST_COMPLETED)
            for fut in done:
                job = running.pop(fut)
                record = fut.result()
                _write_progress(record, job.out_dir)
                records.append(record)
                if on_done is not None:
                    on_done(record, job)
                print(f"  done  {job.apk} -> {record['sa_status']} "
                      f"({record['seconds']}s, rc={record['returncode']})  "
                      f"[{len(records)}/{total}]")
    return records


# --- Entry point ------------------------------------------------------------------------


def _print_plan(jobs: list[Job]) -> None:
    print(f"{'apk':45} {'mem':>5} {'timeout':>8}  codePackage")
    for job in sorted(jobs, key=lambda j: (-j.mem_gib, j.apk)):
        print(f"{job.apk:45} {job.jvm_memory:>5} {job.timeout:>8}  {job.code_package}")
    tiers: dict[tuple[str, int], int] = {}
    for job in jobs:
        tiers[(job.jvm_memory, job.timeout)] = tiers.get((job.jvm_memory, job.timeout), 0) + 1
    print("\ntiers:")
    for (mem, timeout), n in sorted(tiers.items(), key=lambda kv: -_parse_mem_gib(kv[0][0])):
        print(f"  {mem:>5} / {timeout:>5}s  x{n}")
    ceiling = sum(j.timeout for j in jobs)
    print(f"\nsum of timeout ceilings: {ceiling}s ({ceiling / 3600:.1f} h, fully serialised)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", action="store_true",
                    help="print the per-APK parameter table and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the full argv per APK and exit; nothing is executed")
    ap.add_argument("--smoke", action="store_true",
                    help=f"infrastructure check on {SMOKE_APK_PATH.name} (not one of the "
                         f"30); writes to {SMOKE_OUT_DIR.name}, never to the deliverable dir")
    ap.add_argument("--only", action="append", default=None, metavar="APK",
                    help="restrict to this APK id (repeatable)")
    # Escalation rounds (change design D9) need to raise an APK's budget above the pair its
    # Phase 7 log recorded. These override that pair for every selected APK — and only that
    # pair: `codePackage` still comes verbatim from 30_apks.csv, never from a flag.
    ap.add_argument("--jvm-memory", default=None, metavar="MEM",
                    help="override the recorded --jvm-memory for the selected APKs (e.g. 64g)")
    ap.add_argument("--timeout", type=int, default=None, metavar="SECONDS",
                    help="override the recorded --timeout for the selected APKs")
    ap.add_argument("--budget-gib", type=float, default=DEFAULT_BUDGET_GIB,
                    help=f"cap on the sum of concurrent --jvm-memory "
                         f"(default {DEFAULT_BUDGET_GIB:g})")
    ap.add_argument("--grace", type=int, default=DEFAULT_GRACE_SECONDS,
                    help=f"seconds the outer kill waits past GATOR's own --timeout "
                         f"(default {DEFAULT_GRACE_SECONDS})")
    ap.add_argument("--rerun", action="store_true",
                    help="re-analyse APKs whose output JSON already exists")
    ap.add_argument("--force", action="store_true",
                    help="proceed even if the budget exceeds free RAM")
    args = ap.parse_args()

    if args.smoke:
        if args.only:
            raise SystemExit("--smoke and --only are mutually exclusive")
        jobs = [smoke_job()]
    else:
        jobs = read_plan()
        if args.only:
            wanted = set(args.only)
            jobs = [j for j in jobs if j.apk in wanted]
            unknown = wanted - {j.apk for j in jobs}
            if unknown:
                raise SystemExit(f"not in 30_apks.csv: {', '.join(sorted(unknown))}")
    if not jobs:
        raise SystemExit("no APKs selected")
    for job in jobs:
        if args.jvm_memory:
            job.jvm_memory = args.jvm_memory
            job.mem_gib = _parse_mem_gib(args.jvm_memory)  # keep the dispatcher's view honest
        if args.timeout is not None:
            job.timeout = args.timeout
    out_dir = jobs[0].out_dir

    if args.plan:
        _print_plan(jobs)
        return 0

    if args.dry_run:
        for job in jobs:
            print(f"# {job.apk}  ({job.jvm_memory}/{job.timeout}s)")
            print(" ".join(build_argv(job)))
            print()
        return 0

    missing = [str(j.apk_path) for j in jobs if not j.apk_path.is_file()]
    if missing:
        raise SystemExit(f"APK(s) not found: {', '.join(missing)}")
    if not ANALYSIS_CLIENT_JAR.is_file():
        raise SystemExit(f"analysis client jar not found: {ANALYSIS_CLIENT_JAR}")
    mop_dir = _mop_dir()
    if not mop_dir.is_dir():
        raise SystemExit(f"MOP specs directory not found: {mop_dir}")
    _gator_env()  # fails fast if the SDK path cannot be resolved

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "logs").mkdir(exist_ok=True)

    # Resume by output-file existence: `rv-static-analysis`'s own `--force` is declared but
    # never read anywhere in its sources, so it cannot be relied on for this.
    if not args.rerun:
        skipped = [j for j in jobs if j.json_path.is_file()]
        jobs = [j for j in jobs if not j.json_path.is_file()]
        if skipped:
            print(f"resume: {len(skipped)} already have a JSON (use --rerun to redo)")
    if not jobs:
        print("nothing to do")
        return 0

    free = _free_ram_gib()
    free_note = f"; MemAvailable {free:.1f}g" if free is not None else ""
    label = "smoke (infrastructure check)" if args.smoke else "re-analysis"
    print(f"gh91 {label}: {len(jobs)} APK(s); budget {args.budget_gib:g}g{free_note}")
    print(f"  output: {out_dir}")
    if free is not None and args.budget_gib > free and not args.force:
        print(f"REFUSING: budget {args.budget_gib:g}g exceeds free RAM {free:.1f}g. "
              f"Lower --budget-gib or override with --force.")
        return 2

    records = run_all(jobs, budget=args.budget_gib, grace=args.grace)

    by_status: dict[str, int] = {}
    for rec in records:
        by_status[rec["sa_status"]] = by_status.get(rec["sa_status"], 0) + 1
    print("\n--- sa_status breakdown ---")
    for status, n in sorted(by_status.items(), key=lambda kv: -kv[1]):
        print(f"  {status:32} {n}")
    ok = by_status.get(sa_runner.STATUS_COMPLETE, 0)
    if args.smoke:
        print(f"\n{ok}/{len(records)} complete. Inspect {out_dir} — the JSON must carry "
              f'"complete": true and an empty `transitions`, and the log must carry the '
              f"[RvsecAnalysisClient] Filter package: {SMOKE_PACKAGE} line.")
    else:
        print(f"\n{ok}/{len(records)} complete. Nothing may be copied into the corpus until "
              f"the change's validation gate (task group 3) passes on {out_dir}.")
    return 0 if ok == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())

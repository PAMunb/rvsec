#!/usr/bin/env python3
"""E1: which classes and signatures make up `unmatched_in_scope`, for ONE estudo02 container.

`summary.csv` carries only the two crossing counters (INV-PLT-34); the names behind them
exist nowhere on disk. This script re-parses each identity's logcat with the platform's own
reconstruction (`ResultProcessorComponent._reconstruct_repository_from_logcat`, the path
that produced the regenerated `summary.csv`) and wraps `LogcatRepository._count_unmatched`
to record, for every in-scope discard, the class, the signature and why the artefact did
not match it: `class_absent` (the class is not in the static model) or `method_absent`
(the class is, the signature is not). Out-of-scope discards are only counted.

Part (a) of E1 is built in: the per-identity totals written here must equal the
`unmatched_in_scope`/`unmatched_out_of_scope` cells of the regenerated `summary.csv`,
which is what shows the wrapper counts the same events the exporter counted.

Usage (one container; run the ten in parallel; an optional second argument limits identities):
    VALIDACAO_DIR=... uv run python experimento-estudo02/scripts/validacao/e1_unmatched.py estudo02_00 [N]

Output: $VALIDACAO_DIR/e1/<cid>_identities.tsv (apk, tool, rep, timeout, in, out) and
$VALIDACAO_DIR/e1/<cid>_in_scope.tsv (apk, tool, rep, timeout, class, signature, reason, events).
"""
import csv
import logging
import os
import sys
from collections import Counter
from pathlib import Path

from rv_android_core.domain.coverage import LogcatRepository
from rv_android_core.util.logging.manager import LoggingManager
from rv_platform.components.result_processor import ResultProcessorComponent

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experimento-estudo02" / "scripts"))
from regenerate_tables import host_logcat_path, load_identities  # noqa: E402

_register = LogcatRepository.register_method_call
_count = LogcatRepository._count_unmatched


def register_method_call(self, coverage_log):
    # `_count_unmatched` receives only the class name; the signature is stashed here.
    self._e1_signature = coverage_log.signature
    return _register(self, coverage_log)


def count_unmatched(self, class_name):
    _count(self, class_name)
    if self.scope_key is not None and class_name.startswith(self.scope_key):
        reason = "class_absent" if self.get_class(class_name) is None else "method_absent"
        self.__dict__.setdefault("_e1_in", Counter())[(class_name, self._e1_signature, reason)] += 1


LogcatRepository.register_method_call = register_method_call
LogcatRepository._count_unmatched = count_unmatched


def main() -> int:
    cid = sys.argv[1]
    container_dir = str(ROOT / "data" / "results" / cid / cid)
    out = Path(os.environ.get("VALIDACAO_DIR", ".")) / "e1"
    out.mkdir(parents=True, exist_ok=True)
    LoggingManager.get_instance().configure_output(console_level=logging.ERROR)

    tasks = load_identities(os.path.join(container_dir, "tasks.json"))
    if len(sys.argv) > 2:
        tasks = tasks[: int(sys.argv[2])]
    processor = ResultProcessorComponent(tasks, container_dir)
    static_cache = {}
    with open(out / f"{cid}_identities.tsv", "w", newline="") as fi, \
         open(out / f"{cid}_in_scope.tsv", "w", newline="") as fs:
        wi, ws = csv.writer(fi, delimiter="\t"), csv.writer(fs, delimiter="\t")
        for task in tasks:
            apk = task.config.apk_name
            task.result.logcat_file = host_logcat_path(container_dir, task.result.logcat_file)
            if apk in static_cache:
                task.static_data = static_cache[apk]
            repo = processor._reconstruct_repository_from_logcat(task)
            if repo is None:
                print(f"ERROR: no repository for {apk} {task.config.tool_config.get_full_tool_name()}", file=sys.stderr)
                return 1
            if task.static_data is not None and apk not in static_cache:
                static_cache = {apk: task.static_data}
            key = (apk, task.config.tool_config.get_full_tool_name(), task.config.repetition, task.config.timeout)
            d = repo.parser_diagnostics
            wi.writerow([*key, d.unmatched_in_scope, d.unmatched_out_of_scope, d.unmatched_unclassified, repo.scope_key])
            for (cls, sig, reason), n in sorted(repo.__dict__.get("_e1_in", {}).items()):
                ws.writerow([*key, cls, sig, reason, n])
            task.static_data = None
    print(f"[{cid}] {len(tasks)} identities", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

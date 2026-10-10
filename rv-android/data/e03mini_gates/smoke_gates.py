"""Per-task gates of an e03mini smoke run: one Markdown row per task identity.

Usage: python3 smoke_gates.py data/results/<c> [...]
Reads <c>/<c>/tasks.json; logcat/trace paths are relative to data/results/<c>/ after
stripping the leading "results/". Counts by identity (apk, tool:variant, rep, timeout);
the last record of an identity wins.
"""
import json
import os
import re
import sys


def count(path, needles):
    counts = dict.fromkeys(needles, 0)
    if not path or not os.path.exists(path):
        return None
    with open(path, errors="replace") as handle:
        for line in handle:
            for needle in needles:
                if needle in line:
                    counts[needle] += 1
    return counts


def trace_facts(path):
    facts = {"sha": "-", "mopd": 0, "steps": "-", "stampNodes": "-", "stampHits": "-"}
    if not path or not os.path.exists(path):
        return facts
    with open(path, errors="replace") as handle:
        for line in handle:
            if line.startswith('{"type":"RUN_START"'):
                facts["sha"] = json.loads(line).get("build", {}).get("sha", "-")
            elif line.startswith('{"type":"RUN_END"'):
                end = json.loads(line)
                facts["steps"] = end.get("steps", "-")
                facts["stampNodes"] = end.get("counters", {}).get("stampNodes", "-")
                facts["stampHits"] = end.get("counters", {}).get("stampHits", "-")
            elif line.startswith('{"s":') and '"mopd":' in line:
                facts["mopd"] += 1
    return facts


def rows(container_dir):
    name = os.path.basename(os.path.normpath(container_dir))
    with open(os.path.join(container_dir, name, "tasks.json")) as handle:
        tasks = json.load(handle)["tasks"]
    tasks = list(tasks.values()) if isinstance(tasks, dict) else tasks
    by_identity = {}
    for task in tasks:
        config, tool = task["config"], task["config"]["tool_config"]
        arm = tool["name"] if tool.get("variant") in (None, "default") else f"{tool['name']}:{tool['variant']}"
        by_identity[(config["apk_name"], arm, config["repetition"], config["timeout"])] = task["result"]
    for (apk, arm, rep, timeout), result in sorted(by_identity.items()):
        def local(key):
            value = result.get(key)
            return os.path.join(container_dir, re.sub(r"^results/", "", value)) if value else None

        log = count(local("logcat_file"), ["RVSEC-COV", "RVSEC-OCC", "RVSEC-BIND", "VerifyError"])
        trace = trace_facts(local("trace_file"))
        log_cells = " | ".join(str(log[k]) for k in ("RVSEC-COV", "RVSEC-OCC", "RVSEC-BIND", "VerifyError")) if log else "- | - | - | -"
        cov = (result.get("coverage_metrics") or {}).get("method_coverage")
        print(
            f"| {name[-2:]} | {apk.removesuffix('.apk')} | {arm} | {rep} | {result['state']} | "
            f"{result.get('execution_time_seconds')} | {'' if cov is None else f'{cov:.2f}'} | {log_cells} | "
            f"{trace['sha']} | {trace['steps']} | {trace['mopd']} | {trace['stampNodes']} | {trace['stampHits']} | "
            f"{(result.get('error_message') or '')[:60]} |"
        )


print("| c | APK | arm | rep | state | exec s | cov_method % | COV | OCC | BIND | VerifyError | build | steps | steps with mopd | stampNodes | stampHits | error |")
print("|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|")
for argument in sys.argv[1:]:
    rows(argument)

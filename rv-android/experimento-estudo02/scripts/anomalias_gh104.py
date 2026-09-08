#!/usr/bin/env python3
"""Análise de anomalias por APK na campanha gh104 (2026-09-06/07).

Lê todos os tasks.json dos containers, deduplica por identidade
(apk_name, tool.name, tool.variant, repetition, timeout) ficando com o ÚLTIMO registro,
enriquece com logcat (RVSEC-COV, 'RVSEC :'), traço (passos), app_events.csv e <apk>.json,
aplica C1–C5 e escreve dois CSVs (por identidade e por APK) no diretório dado como
argumento 1 — a campanha guarda a saída em experimento-estudo02/anomalias_gh104/.
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android")
RESULTS_GLOB = str(ROOT / "data/results/gh104_*/gh104_*")
MANIFEST = ROOT / "experimento-gh104/manifest.json"
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
TEARDOWN_FRAC = 0.10  # C2: folga de teardown ~10 % (a campanha usa 45 s; ambos reportados)
CAMPAIGN_GRACE_S = 45

COV_RE = re.compile(rb"RVSEC-COV\s*:\s*(.+?)\s*$")
VIOL_RE = re.compile(rb"\sV\s+RVSEC\s*:\s*(.+?)\s*$")
STEP_RE = re.compile(rb"begin step \[(\d+)\]")
VERIFY_RE = re.compile(rb"VerifyError|Verifier rejected|Rejecting class")
DIED_RE = re.compile(rb"Process .* has died|FATAL EXCEPTION|ANR in ")


def arm(tc: dict) -> str:
    return "ape" if tc.get("name") == "ape" else f"{tc.get('name')}:{tc.get('variant')}"


def scan_logcat(path: Path) -> dict:
    sigs: set[bytes] = set()
    viol = 0
    viol_distinct: set[bytes] = set()
    verify = 0
    n = 0
    with path.open("rb") as fh:
        for line in fh:
            n += 1
            if b"RVSEC-COV" in line:
                m = COV_RE.search(line)
                if m:
                    sigs.add(m.group(1))
            elif b"RVSEC" in line:
                m = VIOL_RE.search(line)
                if m:
                    viol += 1
                    # spec,class,file,method,source,type,envelope -> chave sem o envelope
                    viol_distinct.add(b",".join(m.group(1).split(b",")[:6]))
            if VERIFY_RE.search(line):
                verify += 1
    return {"logcat_lines": n, "cov_distinct": len(sigs), "viol_lines": viol,
            "viol_distinct": len(viol_distinct), "verify_lines": verify}


def scan_trace(path: Path) -> int:
    last = 0
    with path.open("rb") as fh:
        for line in fh:
            m = STEP_RE.search(line)
            if m:
                last = max(last, int(m.group(1)))
    return last


def load_apk_json(path: Path) -> dict:
    try:
        d = json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        return {"apk_json": f"unreadable:{type(e).__name__}"}
    reach = d.get("reachability") or []
    n_methods = sum(len(c.get("methods") or []) for c in reach)
    n_reaches = sum(1 for c in reach for m in (c.get("methods") or []) if m.get("reachesTarget"))
    acts = (d.get("components") or {}).get("activities") or []
    return {"apk_json": "ok", "package": d.get("package"), "sa_complete": d.get("complete"),
            "sa_methods": n_methods, "sa_methods_reach_mop": n_reaches,
            "sa_activities": len(acts),
            "sa_activities_reach_mop": sum(1 for a in acts if a.get("reachesTarget"))}


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    probes = manifest.get("probes", {})
    excluded = manifest.get("excluded_apks", {})
    timeout_default = manifest.get("timeout", 300)

    # 1. tasks.json de todos os containers, dedup por identidade ficando com o ÚLTIMO.
    last: dict[tuple, dict] = {}
    history: dict[tuple, list[str]] = defaultdict(list)
    for tdir in sorted(glob.glob(RESULTS_GLOB)):
        tj = Path(tdir) / "tasks.json"
        if not tj.exists():
            continue
        doc = json.loads(tj.read_text())
        for t in doc["tasks"] if isinstance(doc, dict) else doc:
            cfg = t["config"]; tc = cfg["tool_config"]
            k = (cfg["apk_name"], tc.get("name"), tc.get("variant"), cfg["repetition"], cfg["timeout"])
            history[k].append((t["result"] or {}).get("state"))
            last[k] = {"container": Path(tdir).name, "dir": Path(tdir), "task": t}

    # 2. app_events.csv por container -> (apk, rep, tool) -> contadores
    events: dict[tuple, Counter] = defaultdict(Counter)
    ev_first_crash: dict[tuple, int] = {}
    ev_foreign: dict[tuple, Counter] = defaultdict(Counter)
    for tdir in sorted(glob.glob(RESULTS_GLOB)):
        f = Path(tdir) / "app_events.csv"
        if not f.exists():
            continue
        with f.open(newline="") as fh:
            for row in csv.DictReader(fh):
                k = (row["apk"], int(row["rep"]), row["tool"])
                cat = row["category"]
                events[k][cat] += 1
                events[k][f"{cat}:{row['exception_class']}"] += 1
                events[k]["_proc:" + row["process"]] += 1
                if cat == "crash":
                    try:
                        t = int(row["time"])
                        ev_first_crash[k] = min(ev_first_crash.get(k, 10**9), t)
                    except ValueError:
                        pass

    # 3. por identidade
    apk_json_cache: dict[str, dict] = {}
    rows = []
    for k in sorted(last, key=lambda x: (x[0], x[1], x[2] or "", x[3])):
        apk, name, variant, rep, timeout = k
        rec = last[k]; t = rec["task"]; r = t["result"] or {}
        a = arm(t["config"]["tool_config"])
        cm = r.get("coverage_metrics") or {}
        apk_dir = rec["dir"] / apk
        if apk not in apk_json_cache:
            apk_json_cache[apk] = load_apk_json(apk_dir / f"{apk}.json") if apk_dir.exists() \
                else {"apk_json": "no_apk_dir"}
        aj = apk_json_cache[apk]
        base = f"{apk}__{rep}__{timeout}__{a}"
        logcat = apk_dir / f"{base}.logcat"
        trace = apk_dir / f"{base}.trace"
        lc = scan_logcat(logcat) if logcat.exists() else {"logcat_lines": None, "cov_distinct": None,
                                                           "viol_lines": None, "viol_distinct": None,
                                                           "verify_lines": None}
        steps = scan_trace(trace) if trace.exists() else None
        ev = events.get((apk, rep, a), Counter())
        pkg = aj.get("package") or ""
        declared = (probes.get(apk) or {}).get("declared_package") or ""
        own = {pkg, declared} - {""}
        proc_own = sum(v for c, v in ev.items() if c.startswith("_proc:")
                       and any(c[6:] == p or c[6:].startswith(p + ":") for p in own))
        proc_all = sum(v for c, v in ev.items() if c.startswith("_proc:"))
        exec_t = r.get("execution_time_seconds") or 0
        floor10 = timeout * (1 - TEARDOWN_FRAC)
        fails = []
        if r.get("state") != "COMPLETED" or r.get("error_message"):
            fails.append("C1")
        if exec_t < floor10:
            fails.append("C2")
        if not steps:
            fails.append("C3")
        if not lc["cov_distinct"]:
            fails.append("C4")
        if not ((cm.get("method_coverage") or 0) > 0 and (cm.get("activities_coverage") or 0) > 0):
            fails.append("C5")
        rows.append({
            "apk": apk, "arm": a, "rep": rep, "timeout": timeout, "container": rec["container"],
            "n_records": len(history[k]), "record_states": "/".join(s or "?" for s in history[k]),
            "state": r.get("state"), "error_message": (r.get("error_message") or "").replace("\n", " ")[:160],
            "execution_time_seconds": exec_t, "c2_floor10": floor10,
            "c2_campaign_floor": timeout - CAMPAIGN_GRACE_S,
            "cov_method": cm.get("method_coverage"), "cov_act": cm.get("activities_coverage"),
            "cov_mop": cm.get("methods_mop_reachable_coverage"), "mop_unique": cm.get("total_errors"),
            "total_method_calls": cm.get("total_method_calls"),
            "trace_steps": steps, "logcat_lines": lc["logcat_lines"],
            "cov_sig_distinct": lc["cov_distinct"], "viol_lines": lc["viol_lines"],
            "viol_distinct": lc["viol_distinct"], "verify_lines": lc["verify_lines"],
            "ev_crash": ev.get("crash", 0), "ev_anr": ev.get("anr", 0),
            "ev_verify_error": ev.get("verify_error", 0),
            "ev_other": sum(v for c, v in ev.items() if ":" not in c and c not in ("crash", "anr", "verify_error") and not c.startswith("_proc")),
            "ev_proc_own": proc_own, "ev_proc_all": proc_all,
            "ev_first_crash_s": ev_first_crash.get((apk, rep, a)),
            "ev_top": ";".join(f"{c}={v}" for c, v in ev.most_common() if ":" in c and not c.startswith("_proc"))[:200],
            "fails": "+".join(fails),
            "sa_methods_reach_mop": aj.get("sa_methods_reach_mop"),
            "sa_activities": aj.get("sa_activities"),
            "sa_activities_reach_mop": aj.get("sa_activities_reach_mop"),
            "sa_complete": aj.get("sa_complete"), "apk_json": aj.get("apk_json"),
            "excluded_in_manifest": apk in excluded,
        })

    ident_csv = OUT_DIR / "anomalias_gh104_identidades.csv"
    with ident_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    # 4. por APK
    by_apk: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_apk[r["apk"]].append(r)

    def mm(vals, fmt="{:.1f}"):
        v = [x for x in vals if x is not None]
        return (fmt.format(min(v)) + "/" + fmt.format(max(v))) if v else ""

    apk_rows = []
    for apk, rs in sorted(by_apk.items()):
        n = len(rs)
        states = Counter(r["state"] for r in rs)
        fail_sets = [set(r["fails"].split("+")) - {""} for r in rs]
        crit_all = sorted(set.intersection(*fail_sets)) if fail_sets else []
        crit_any = Counter(c for s in fail_sets for c in s)
        arms_bad = {a: [r["rep"] for r in rs if r["arm"] == a and r["fails"]] for a in sorted({r["arm"] for r in rs})}
        arms_dead = [a for a, bad in arms_bad.items() if len(bad) == sum(1 for r in rs if r["arm"] == a)]
        covm = [r["cov_method"] for r in rs if r["cov_method"] is not None]
        flags = []
        if crit_all:
            flags.append("FALHA_TODAS:" + "+".join(crit_all))
        if arms_dead:
            flags.append("BRACO_SEM_REP_ADMISSIVEL:" + ",".join(arms_dead))
        if covm and all(c == 0 for c in covm):
            flags.append("cov_method=0_todas")
        if covm and any(c >= 100 for c in covm):
            flags.append("cov_method=100")
        if covm and all(c < 1 for c in covm):
            flags.append("cov_method<1_todas")
        cova = [r["cov_act"] for r in rs if r["cov_act"] is not None]
        if cova and all(c == 0 for c in cova):
            flags.append("cov_act=0_todas")
        if any((r["viol_lines"] or 0) > 5000 for r in rs):
            flags.append("viol_lines>5000")
        if rs[0]["sa_methods_reach_mop"] == 0:
            flags.append("apk.json:0_metodos_alcancam_MOP")
        if rs[0]["sa_activities"] == 0:
            flags.append("apk.json:0_activities")
        if rs[0]["apk_json"] != "ok":
            flags.append("apk.json:" + str(rs[0]["apk_json"]))
        fc = [r["ev_first_crash_s"] for r in rs if r["ev_first_crash_s"] is not None]
        if fc and len(fc) == n and max(fc) <= 15:
            flags.append("crash<=15s_todas")
        if any((r["ev_verify_error"] or 0) > 0 or (r["verify_lines"] or 0) > 0 for r in rs):
            flags.append("verify_error")
        if any(r["state"] == "COMPLETED" and (r["total_method_calls"] or 0) == 0 for r in rs):
            flags.append("COMPLETED_com_0_chamadas")
        if rs[0]["excluded_in_manifest"]:
            flags.append("JA_EXCLUIDO_manifest")
        apk_rows.append({
            "apk": apk, "n_ident": n, "n_records": sum(r["n_records"] for r in rs),
            "states": ",".join(f"{s}x{c}" for s, c in sorted(states.items())),
            "exec_time_min/max": mm([r["execution_time_seconds"] for r in rs], "{:.0f}"),
            "error_messages": " | ".join(sorted({r["error_message"][:80] for r in rs if r["error_message"]})),
            "cov_method_min/max": mm([r["cov_method"] for r in rs]),
            "cov_method_mean": f"{statistics.mean(covm):.1f}" if covm else "",
            "cov_act_min/max": mm([r["cov_act"] for r in rs]),
            "cov_mop_min/max": mm([r["cov_mop"] for r in rs]),
            "mop_unique_min/max": mm([r["mop_unique"] for r in rs], "{:.0f}"),
            "cov_sig_distinct_min/max": mm([r["cov_sig_distinct"] for r in rs], "{:.0f}"),
            "viol_lines_min/max": mm([r["viol_lines"] for r in rs], "{:.0f}"),
            "viol_lines_sum": sum(r["viol_lines"] or 0 for r in rs),
            "trace_steps_min/max": mm([r["trace_steps"] for r in rs], "{:.0f}"),
            "ev_crash_sum": sum(r["ev_crash"] for r in rs),
            "ev_anr_sum": sum(r["ev_anr"] for r in rs),
            "ev_verify_sum": sum(r["ev_verify_error"] for r in rs),
            "ev_proc_own/all": f"{sum(r['ev_proc_own'] for r in rs)}/{sum(r['ev_proc_all'] for r in rs)}",
            "ev_first_crash_s_min/max": mm(fc, "{:.0f}"),
            "ident_with_crash": sum(1 for r in rs if r["ev_crash"]),
            "C1_fail": crit_any.get("C1", 0), "C2_fail": crit_any.get("C2", 0),
            "C3_fail": crit_any.get("C3", 0), "C4_fail": crit_any.get("C4", 0),
            "C5_fail": crit_any.get("C5", 0),
            "ident_inadmissiveis": sum(1 for s in fail_sets if s),
            "fails_all": "+".join(crit_all),
            "arms_dead": ",".join(arms_dead),
            "sa_methods_reach_mop": rs[0]["sa_methods_reach_mop"],
            "sa_activities": rs[0]["sa_activities"],
            "sa_activities_reach_mop": rs[0]["sa_activities_reach_mop"],
            "sa_complete": rs[0]["sa_complete"],
            "flags": ";".join(flags),
        })

    apk_csv = OUT_DIR / "anomalias_gh104_por_apk.csv"
    with apk_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(apk_rows[0].keys())); w.writeheader(); w.writerows(apk_rows)

    # 5. resumo
    print(f"identidades: {len(rows)}  registros brutos: {sum(len(v) for v in history.values())}  "
          f"APKs: {len(by_apk)}  containers: {len(set(r['container'] for r in rows))}")
    print(f"identidades com >1 registro: {sum(1 for v in history.values() if len(v) > 1)}")
    print("estados finais:", Counter(r["state"] for r in rows))
    for c in ("C1", "C2", "C3", "C4", "C5"):
        print(f"{c} reprova em {sum(1 for r in rows if c in r['fails'].split('+'))} identidades")
    print(f"C2 com piso da campanha ({timeout_default - CAMPAIGN_GRACE_S}s): "
          f"{sum(1 for r in rows if r['state']=='COMPLETED' and r['execution_time_seconds'] < r['c2_campaign_floor'])} identidades")
    print("sem logcat:", sum(1 for r in rows if r["logcat_lines"] is None),
          " sem trace:", sum(1 for r in rows if r["trace_steps"] is None))
    print()
    print("== APKs com flag ==")
    for a in apk_rows:
        if a["flags"]:
            print(f"{a['apk']:48s} {a['states']:26s} t={a['exec_time_min/max']:8s} "
                  f"covM={a['cov_method_min/max']:12s} covA={a['cov_act_min/max']:12s} "
                  f"C1..5={a['C1_fail']}{a['C2_fail']}{a['C3_fail']}{a['C4_fail']}{a['C5_fail']} "
                  f"crash={a['ev_crash_sum']} anr={a['ev_anr_sum']} :: {a['flags']}")
    print()
    print("== identidades inadmissíveis (parciais) ==")
    for r in rows:
        if r["fails"]:
            print(f"{r['apk']:48s} {r['arm']:22s} rep{r['rep']} {r['container']} {r['state']:9s} "
                  f"t={r['execution_time_seconds']:4} covM={r['cov_method']} covA={r['cov_act']} "
                  f"steps={r['trace_steps']} sigs={r['cov_sig_distinct']} :: {r['fails']} :: {r['error_message'][:70]}")
    print()
    top = sorted(rows, key=lambda r: -(r["viol_lines"] or 0))[:10]
    print("== top-10 viol_lines por identidade ==")
    for r in top:
        print(f"{r['apk']:48s} {r['arm']:22s} rep{r['rep']} viol={r['viol_lines']} distinct={r['viol_distinct']} mop_unique={r['mop_unique']}")
    print()
    print("== top-10 crashes por APK (app_events) ==")
    for a in sorted(apk_rows, key=lambda a: -a["ev_crash_sum"])[:10]:
        print(f"{a['apk']:48s} crash={a['ev_crash_sum']} anr={a['ev_anr_sum']} ident_c_crash={a['ident_with_crash']}/{a['n_ident']} first={a['ev_first_crash_s_min/max']} proc_own/all={a['ev_proc_own/all']}")
    print(f"\nCSV: {ident_csv}\nCSV: {apk_csv}")


if __name__ == "__main__":
    main()

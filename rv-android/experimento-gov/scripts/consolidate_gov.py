#!/usr/bin/env python3
"""Consolidação MOP-focada da run gov.br (offline, via logcats).

Entregável: violações MOP JCA por app. Cobertura % NÃO é reportada (análise estática
pulada → denominador ausente → cov_mop=0 por design; ver REGISTRO §8b).

Fontes:
- `results/exp_NN/exp_NN/tasks.json` (duplo-nesting) — dedup por identidade
  (apk,tool,variant,rep,timeout); `coverage_metrics.total_errors` = mop_unique
  (violações distintas por Spec,classe,método,tipo — dedup do próprio platform, gh58-safe).
- `.logcat` de cada task — linhas `RVSEC   :` = violações (mop_total bruto + breakdown
  por tipo); `RVSEC-COV` = métodos executados (numerador de cobertura, informativo).

Saída: `results/consolidado_gov/per_app.csv` + `summary.md` + print.

Uso:
    uv run python experimento-gov/scripts/consolidate_gov.py [--results experimento-gov/results]
"""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

RVSEC_LINE = re.compile(r"\bRVSEC\s+:\s*(.+)$")
RVSEC_COV_LINE = re.compile(r"\bRVSEC-COV\s*:\s*(.+)$")
# tipo de violação = token CamelCase logo após a localização "...:<n>,"
TYPE_AFTER_LOC = re.compile(r":\d+,([A-Za-z][A-Za-z0-9]+),")
# fallback: penúltimo-ish — token CamelCase conhecido
KNOWN_TYPES = re.compile(
    r"\b(UnsafeAlgorithm|InvalidSequenceOfMethodCalls|PredictableKey|PredictableIV|"
    r"ConstantKey|ConstantIV|ReusedIV|InsecureMode|InsecurePadding|StaticSalt|"
    r"WeakIteration|UntrustedKeyStore|HostnameVerifier|TrustAllCerts|Randomness)\b"
)


def identity(cfg: dict) -> tuple:
    tc = cfg.get("tool_config", {})
    return (cfg.get("apk_name"), tc.get("name"), tc.get("variant"),
            cfg.get("repetition"), cfg.get("timeout"))


def parse_logcat(path: Path) -> tuple[int, Counter, int]:
    """Return (mop_total_lines, type_counter, distinct_cov_methods)."""
    mop_total = 0
    types = Counter()
    cov_methods = set()
    if not path.is_file():
        return 0, types, 0
    with path.open(errors="ignore") as f:
        for line in f:
            m = RVSEC_LINE.search(line)
            if m:
                mop_total += 1
                payload = m.group(1)
                t = TYPE_AFTER_LOC.search(payload)
                if t:
                    types[t.group(1)] += 1
                else:
                    k = KNOWN_TYPES.search(payload)
                    types[k.group(1) if k else "Other"] += 1
                continue
            c = RVSEC_COV_LINE.search(line)
            if c:
                cov_methods.add(c.group(1).strip())
    return mop_total, types, len(cov_methods)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="experimento-gov/results")
    a = ap.parse_args()
    results = Path(a.results)

    # dedup por identidade, mantendo o COMPLETED mais recente
    by_ident: dict[tuple, dict] = {}
    for tj in results.glob("exp_*/exp_*/tasks.json"):
        try:
            data = json.loads(tj.read_text())
        except Exception:
            continue
        tasks = data.get("tasks", data) if isinstance(data, dict) else data
        for t in tasks:
            cfg = t.get("config", {})
            res = t.get("result", {})
            ident = identity(cfg)
            state = res.get("state")
            prev = by_ident.get(ident)
            # prefere COMPLETED; senão mantém qualquer
            if prev is None or (state == "COMPLETED" and prev[1].get("result", {}).get("state") != "COMPLETED"):
                by_ident[ident] = (tj, t)

    rows = []
    agg_types = Counter()
    apps_with_viol = 0
    for ident, (tj, t) in sorted(by_ident.items()):
        cfg = t.get("config", {})
        res = t.get("result", {})
        apk = cfg.get("apk_name")
        state = res.get("state")
        cov = res.get("coverage_metrics", {}) or {}
        mop_unique = cov.get("total_errors", 0)
        # localizar logcat
        lc = res.get("logcat_file", "")
        lc_path = tj.parent / Path(lc).name if lc else None
        if lc_path is None or not lc_path.is_file():
            # fallback: procurar sob a pasta do apk
            cand = list((tj.parent / apk).glob("*.logcat")) if apk else []
            lc_path = cand[0] if cand else Path("/nonexistent")
        mop_total, types, cov_methods = parse_logcat(lc_path)
        agg_types.update(types)
        if mop_unique or mop_total:
            apps_with_viol += 1
        rows.append({
            "apk": apk, "container": tj.parent.name, "state": state,
            "mop_unique": mop_unique, "mop_total": mop_total,
            "cov_methods_executed": cov_methods,
            "exec_time_s": res.get("execution_time_seconds"),
            "types": ";".join(f"{k}={v}" for k, v in types.most_common()),
        })

    outdir = results / "consolidado_gov"
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "per_app.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                           ["apk", "container", "state", "mop_unique", "mop_total",
                            "cov_methods_executed", "exec_time_s", "types"])
        w.writeheader()
        w.writerows(rows)

    completed = sum(1 for r in rows if r["state"] == "COMPLETED")
    total_unique = sum(r["mop_unique"] for r in rows)
    lines = []
    lines.append(f"# Consolidação MOP — gov.br ({len(rows)} identidades, {completed} COMPLETED)\n")
    lines.append(f"- Apps com ≥1 violação MOP JCA: **{apps_with_viol}/{len(rows)}**")
    lines.append(f"- Total de violações distintas (Σ mop_unique): **{total_unique}**")
    lines.append(f"- Breakdown por tipo: " + ", ".join(f"{k}={v}" for k, v in agg_types.most_common()))
    lines.append("\n## Por app (ordenado por mop_unique)\n")
    lines.append("| app | estado | mop_unique | mop_total | métodos exec | tipos |")
    lines.append("|---|---|---:|---:|---:|---|")
    for r in sorted(rows, key=lambda r: -r["mop_unique"]):
        lines.append(f"| {r['apk']} | {r['state']} | {r['mop_unique']} | {r['mop_total']} "
                     f"| {r['cov_methods_executed']} | {r['types']} |")
    (outdir / "summary.md").write_text("\n".join(lines) + "\n")

    print("\n".join(lines))
    print(f"\nCSV: {csv_path}\nSummary: {outdir/'summary.md'}")


if __name__ == "__main__":
    main()

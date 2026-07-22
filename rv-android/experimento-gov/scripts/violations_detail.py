#!/usr/bin/env python3
"""Planilha DETALHADA de todas as violações MOP JCA da run gov.br (offline, via logcats).

Diferente de `consolidate_gov.py` (agregado por app), aqui cada linha é uma
**violação distinta** (spec, classe, método, local, tipo) por app, com a contagem
de ocorrências e a mensagem do monitor. É a lista acionável completa de misuse.

Linha RVSEC no logcat:
    RVSEC   : <Spec>,<classe>,<classeSimples>,<metodo>,<arquivo:linha>,<Tipo>,<mensagem>
A mensagem pode conter vírgulas (ex.: "{SHA-256, SHA-384}") → split com maxsplit=6.

Saída: results/consolidado_gov/all_violations.csv (uma linha por violação distinta)
       + all_violations_by_type.csv (agregado por tipo).
"""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

RVSEC = re.compile(r"\bRVSEC\s+:\s*(.+?)\s*$")


def identity(cfg):
    tc = cfg.get("tool_config", {})
    return (cfg.get("apk_name"), tc.get("name"), tc.get("variant"),
            cfg.get("repetition"), cfg.get("timeout"))


def parse_line(payload):
    """'<spec>,<class>,<simple>,<method>,<loc>,<type>,<msg>' → tupla de 7 (msg pode ter vírgula)."""
    parts = payload.split(",", 6)
    if len(parts) < 6:
        return None
    while len(parts) < 7:
        parts.append("")
    return tuple(p.strip() for p in parts)


def apk_dir_for(container_dir, apk_name):
    d = container_dir / apk_name
    return d if d.is_dir() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="experimento-gov/results")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    results = Path(args.results)
    outdir = Path(args.out) if args.out else results / "consolidado_gov"
    outdir.mkdir(parents=True, exist_ok=True)

    # chave da violação distinta por app: (spec, class, method, loc, type)
    # valor: [simpleClass, msg_exemplo, ocorrencias]
    rows = defaultdict(lambda: defaultdict(lambda: [None, None, 0]))
    by_type = Counter()
    apk_state = {}

    for tj in sorted(results.glob("exp_*/exp_*/tasks.json")):
        container_dir = tj.parent
        data = json.load(open(tj))
        raw = data.get("tasks", data) if isinstance(data, dict) else data
        entries = list(raw.values()) if isinstance(raw, dict) else raw
        # estado efetivo por identidade (COMPLETED > ERROR); guarda o apk_name
        for t in entries:
            cfg = t.get("config", {})
            apk = cfg.get("apk_name")
            st = (t.get("result") or {}).get("state")
            prev = apk_state.get(apk)
            if prev != "COMPLETED":
                apk_state[apk] = st
        # varre logcats presentes no container
        for apk in {t.get("config", {}).get("apk_name") for t in entries}:
            adir = apk_dir_for(container_dir, apk)
            if not adir:
                continue
            for lc in adir.glob("*.logcat"):
                with open(lc, errors="replace") as fh:
                    for line in fh:
                        if "RVSEC" not in line:
                            continue
                        m = RVSEC.search(line)
                        if not m:
                            continue
                        p = parse_line(m.group(1))
                        if not p:
                            continue
                        spec, cls, simple, method, loc, vtype, msg = p
                        key = (spec, cls, method, loc, vtype)
                        rec = rows[apk][key]
                        rec[0] = simple
                        if rec[1] is None and msg and msg != "unknown":
                            rec[1] = msg
                        rec[2] += 1
                        by_type[vtype] += 1

    # CSV detalhado
    detail = outdir / "all_violations.csv"
    total_distinct = 0
    with open(detail, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["app", "estado_task", "spec", "classe", "metodo", "local",
                    "tipo_violacao", "mensagem", "ocorrencias"])
        for apk in sorted(rows, key=lambda a: -len(rows[a])):
            for (spec, cls, method, loc, vtype), (simple, msg, n) in sorted(
                    rows[apk].items(), key=lambda kv: -kv[1][2]):
                w.writerow([apk, apk_state.get(apk, "?"), spec, cls, method, loc,
                            vtype, msg or "", n])
                total_distinct += 1

    # CSV por tipo
    bytype = outdir / "all_violations_by_type.csv"
    with open(bytype, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tipo_violacao", "ocorrencias_brutas"])
        for vtype, n in by_type.most_common():
            w.writerow([vtype, n])

    print(f"apps com violações: {sum(1 for a in rows if rows[a])}/{len(apk_state)}")
    print(f"violações DISTINTAS (linhas na planilha): {total_distinct}")
    print(f"ocorrências brutas por tipo: {dict(by_type)}")
    print(f"\nCSV detalhado : {detail}")
    print(f"CSV por tipo  : {bytype}")


if __name__ == "__main__":
    main()

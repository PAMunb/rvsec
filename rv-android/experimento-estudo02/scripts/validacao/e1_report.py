#!/usr/bin/env python3
"""E1 verdict from the per-container output of `e1_unmatched.py`.

(a) the wrapper's per-identity counters equal `unmatched_in_scope`/`unmatched_out_of_scope`
    of the consolidated `summary.csv` (tolerance zero);
(b) share of in-scope discard events whose class is generated code — simple name `R`,
    `R$*`, `BuildConfig`, `Manifest`, `Manifest$*`, or a last `$` segment `Log` — against
    the 99 % threshold declared in `docs/20260914_validacao_execucao.md`;
(c) every APK with an unexplained discard, with its distinct (class, signature, reason)
    set, the number of its identities and arms that touch each, and whether the class
    or signature appears in the co-located `.apk.json` under any spelling.

Writes `$VALIDACAO_DIR/e1_unexplained.tsv`.
"""
import csv
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V = Path(os.environ.get("VALIDACAO_DIR", "."))
THRESHOLD = 0.99


def generated(cls: str) -> bool:
    simple = cls.rsplit(".", 1)[-1]
    return (simple in ("R", "BuildConfig", "Manifest") or simple.startswith(("R$", "Manifest$"))
            or simple.rsplit("$", 1)[-1] == "Log" and "$" in simple)


def static_model(apk: str):
    path = next(iter(glob.glob(str(ROOT / "data" / "results" / "estudo02_*" / "estudo02_*" / apk / f"{apk}.json"))))
    d = json.loads(Path(path).read_text())
    classes = {c["className"]: {m.get("signature") for m in c.get("methods") or []} for c in d["reachability"]}
    return d.get("codePackage"), classes


def main():
    summary = {(r["apk"], r["tool"], r["rep"], r["timeout"]): (r["unmatched_in_scope"], r["unmatched_out_of_scope"])
               for r in csv.DictReader(open(ROOT / "data" / "results" / "estudo02_consolidado" / "summary.csv"))}
    seen, mism, unclassified = set(), [], 0
    for f in sorted(V.glob("e1/*_identities.tsv")):
        for row in csv.reader(open(f), delimiter="\t"):
            k = tuple(row[:4])
            seen.add(k)
            unclassified += int(row[6])
            if summary.get(k) != (row[4], row[5]):
                mism.append((k, row[4:6], summary.get(k)))
    print(f"E1(a): identidades={len(seen)} de {len(summary)}; divergem do summary.csv: {len(mism)}; "
          f"unclassified={unclassified}")
    for m in mism[:10]:
        print("   ", m)

    events, explained = 0, 0
    by_apk = defaultdict(lambda: defaultdict(lambda: {"events": 0, "idents": set(), "arms": set()}))
    for f in sorted(V.glob("e1/*_in_scope.tsv")):
        for apk, tool, rep, to, cls, sig, reason, n in csv.reader(open(f), delimiter="\t"):
            events += int(n)
            if generated(cls):
                explained += int(n)
                continue
            e = by_apk[apk][(cls, sig, reason)]
            e["events"] += int(n)
            e["idents"].add((tool, rep, to))
            e["arms"].add(tool)
    share = explained / events if events else 1.0
    print(f"E1(b): eventos in_scope={events} explicados por classe gerada={explained} ({100 * share:.2f} %) "
          f"-> {'PASSA' if share >= THRESHOLD else 'ACUSA'} (limiar {100 * THRESHOLD:.0f} %)")

    rows = []
    for apk in sorted(by_apk):
        key, classes = static_model(apk)
        canon = {c.replace("$", "."): c for c in classes}
        for (cls, sig, reason), e in sorted(by_apk[apk].items(), key=lambda x: -x[1]["events"]):
            in_model = cls in classes or cls.replace("$", ".") in canon
            sig_elsewhere = any(sig in sigs for sigs in classes.values())
            rows.append((apk, key, cls, sig, reason, e["events"], len(e["idents"]), len(e["arms"]),
                         int(in_model), int(sig_elsewhere)))
    with open(V / "e1_unexplained.tsv", "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["apk", "codePackage", "class", "signature", "reason", "events", "identities", "arms",
                    "class_in_model_any_spelling", "signature_in_model"])
        w.writerows(rows)
    apks = Counter(r[0] for r in rows)
    print(f"E1(c): APKs com evento nao explicado={len(apks)}; (classe, assinatura) distintas={len(rows)}; "
          f"razoes={dict(Counter(r[4] for r in rows))}")
    for apk, n in apks.most_common():
        ev = sum(r[5] for r in rows if r[0] == apk)
        print(f"    {apk}: {n} distintas, {ev} eventos")


if __name__ == "__main__":
    sys.exit(main())

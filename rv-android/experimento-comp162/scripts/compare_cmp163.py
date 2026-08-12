#!/usr/bin/env python3
"""Comparação pareada entre campanhas: comp162 (instrumentação nova) x cmp163.

    uv run python scripts/compare_cmp163.py

A MESMA regra de admissibilidade é aplicada aos dois lados, a partir dos `tasks.json` de cada
campanha e não de listas de exclusão transcritas — `admissibility.py` é o único lugar onde
ela existe. Do lado da cmp163, com R=1, a regra degenera para "a réplica única tem de ser
admissível", que é como aquela campanha já foi julgada; derivar em vez de copiar a lista das
três exclusões dela é o que garante que os dois conjuntos foram julgados igual.

**Este script é descritivo, e a distinção não é formalidade.** Três coisas diferem entre as
duas campanhas, e uma diferença medida aqui não é atribuível a nenhuma delas isoladamente:

1. **Os binários.** Os APKs foram reinstrumentados em 2026-08-12. É o objeto do ensaio.
2. **A imagem.** A `0.9.3-comp162` carrega a guarda INV-APV-60; a `0.9.3-rearch` não. Isso
   muda quais runs sobrevivem, não como um run se comporta — mas muda a composição da
   amostra, que é o suficiente para não poder ser ignorado.
3. **O substrato.** A re-análise da gh91 recuperou o WTG de 10 aplicações (41 -> 51 com WTG
   povoado). Alimenta exatamente o braço de referência, que consome `wtgEdges`.

Há ainda uma assimetria de desenho: a comp162 tem R=3 e a cmp163 tem R=1, então o valor por
aplicação é média de até três réplicas de um lado e sorteio único do outro. Isso torna a
diferença pareada **assimetricamente ruidosa** — mais variância do lado de R=1. A direção do
viés é conhecida e favorável a esta leitura (o lado novo é o menos ruidoso), mas o efeito é
real. É o mesmo mecanismo que a gh97 recusou pagar quando exigiu que a perna B tivesse as
três réplicas da perna A.

A §3 é a única parte com hipótese de mecanismo: se o ganho do braço guiado se concentrar nas
dez aplicações cujo WTG foi recuperado, isso é consistente com o substrato novo sendo a
causa. n=10, exploratório por construção, sem valor confirmatório.
"""

from __future__ import annotations

import csv
import json
import statistics as st
import sys
from pathlib import Path

from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from admissibility import judge_identities, select  # noqa: E402

EXP = Path(__file__).resolve().parents[1]
ROOT = EXP.parent

NOVA_CSV = EXP / "consolidado" / "per_apk_admissivel.csv"
VELHA_TASKS = str(ROOT / "data/results/cmp163_0*/cmp163_0*/tasks.json")
VELHA_PER_TASK = ROOT / "data" / "results" / "cmp163_consolidado" / "per_task.csv"
CENSO_NOVO = EXP / "censo_substrato.csv"
CENSO_VELHO = ROOT / "data" / "results" / "cmp163_substrato.csv"
VELHA_TIMEOUT = 300

ARMS = ["ape", "aperv:mop_off_llm_off", "aperv:mop_on_llm_off"]
SHORT = {"ape": "ape", "aperv:mop_off_llm_off": "mop_off", "aperv:mop_on_llm_off": "mop_on"}
METRICS = ["cov_method", "cov_act", "cov_mop", "mop_unique"]


def load_nova() -> dict:
    """`(apk, braço)` -> métricas. Já é a média sobre as réplicas admissíveis."""
    out = {}
    with NOVA_CSV.open() as f:
        for row in csv.DictReader(f):
            for arm in ARMS:
                out[(row["apk"], arm)] = {m: float(row[f"{arm}__{m}"]) for m in METRICS}
    return out


def load_velha() -> tuple[dict, dict]:
    """Aplica a mesma regra à cmp163 e devolve `((apk, braço) -> métricas, seleção)`."""
    sel = select(judge_identities(VELHA_TASKS, VELHA_TIMEOUT), ARMS)
    per_rep = {}
    with VELHA_PER_TASK.open() as f:
        for row in csv.DictReader(f):
            per_rep[(row["apk"], row["tool"], int(row["rep"]))] = {
                m: float(row[m]) for m in METRICS
            }
    out = {}
    for (apk, arm), reps in sel["good_reps"].items():
        vals = [per_rep[(apk, arm, r)] for r in reps if (apk, arm, r) in per_rep]
        if vals:
            out[(apk, arm)] = {m: st.mean(v[m] for v in vals) for m in METRICS}
    return out, sel


def recovered_wtg() -> list[str]:
    """As aplicações cujo WTG a re-análise da gh91 recuperou (0 -> povoado)."""
    old = {r["apk"]: int(r["wtg_edges"]) for r in csv.DictReader(CENSO_VELHO.open())}
    new = {r["apk"]: int(r["wtg_edges"]) for r in csv.DictReader(CENSO_NOVO.open())}
    return sorted(a for a in new if old.get(a, 0) == 0 and new[a] > 0)


def paired(nova: dict, velha: dict, apks: list, arm: str, metric: str):
    xs = [nova[(a, arm)][metric] for a in apks]
    ys = [velha[(a, arm)][metric] for a in apks]
    diffs = [x - y for x, y in zip(xs, ys)]
    wins = sum(d > 0 for d in diffs)
    losses = sum(d < 0 for d in diffs)
    if any(d != 0 for d in diffs):
        try:
            _, p = wilcoxon(xs, ys, zero_method="wilcox", alternative="two-sided")
        except ValueError:
            p = float("nan")
    else:
        p = 1.0
    return dict(n=len(xs), med_nova=st.median(xs), med_velha=st.median(ys),
                med_diff=st.median(diffs), wins=wins, losses=losses, p=p)


def bloco(titulo: str, nova: dict, velha: dict, apks: list) -> None:
    print()
    print("=" * 84)
    print(f"{titulo}  (n = {len(apks)})")
    print("=" * 84)
    if len(apks) < 6:
        print(f"n={len(apks)} — pequeno demais para o teste; só as medianas abaixo.")
    print(f"{'braço':10s}{'métrica':13s}{'comp162':>10s}{'cmp163':>10s}"
          f"{'Δ mediana':>11s}{'nova>':>7s}{'nova<':>7s}{'p':>10s}")
    for arm in ARMS:
        for m in METRICS:
            r = paired(nova, velha, apks, arm, m)
            p = "  -" if len(apks) < 6 else f"{r['p']:10.5f}"
            print(f"{SHORT[arm]:10s}{m:13s}{r['med_nova']:10.2f}{r['med_velha']:10.2f}"
                  f"{r['med_diff']:11.2f}{r['wins']:7d}{r['losses']:7d}{p}")


def main() -> int:
    if not NOVA_CSV.exists():
        sys.exit(f"{NOVA_CSV} ausente — rode scripts/analise.py primeiro")
    nova = load_nova()
    velha, sel_velha = load_velha()

    apks_nova = {a for a, _ in nova}
    apks_velha = {a for a, _ in velha}
    comuns = sorted(
        a for a in apks_nova & apks_velha
        if all((a, arm) in nova for arm in ARMS) and all((a, arm) in velha for arm in ARMS)
    )

    print("=" * 84)
    print("PAREAMENTO ENTRE CAMPANHAS")
    print("=" * 84)
    print("A mesma regra de admissibilidade nos dois lados, derivada dos tasks.json de cada")
    print("campanha. Do lado da cmp163 (R=1) ela degenera para 'a réplica única tem de ser")
    print("admissível' — que é como aquela campanha já foi julgada.")
    print()
    print(f"admissíveis na comp162: {len(apks_nova)}")
    print(f"admissíveis na cmp163:  {len(apks_velha)}  "
          f"(excluídas lá: {sorted(sel_velha['excluded'])})")
    print(f"aplicações pareadas (nas duas): {len(comuns)}")
    so_nova = sorted(apks_nova - apks_velha)
    so_velha = sorted(apks_velha - apks_nova)
    print(f"só na comp162: {len(so_nova)}  {so_nova[:6]}")
    print(f"só na cmp163:  {len(so_velha)}  {so_velha[:6]}")
    print()
    print("LEITURA DESCRITIVA. Três diferenças simultâneas — binários reinstrumentados,")
    print("imagem com a guarda INV-APV-60, e substrato com 10 WTGs recuperados — mais a")
    print("assimetria R=3 x R=1. Nenhuma diferença medida abaixo é atribuível a uma causa.")

    bloco("CORPUS INTEIRO", nova, velha, comuns)

    rec = [a for a in recovered_wtg() if a in comuns]
    print()
    print("=" * 84)
    print("§3 — AS APLICAÇÕES CUJO WTG A RE-ANÁLISE RECUPEROU (exploratório)")
    print("=" * 84)
    print("Hipótese de mecanismo: se o ganho do braço guiado se concentrar aqui, é")
    print("consistente com o substrato novo sendo a causa. Declarado antes dos dados,")
    print("mas com n pequeno demais para valor confirmatório.")
    for a in rec:
        print(f"  {a}")
    bloco("SUBGRUPO: WTG RECUPERADO", nova, velha, rec)

    resto = [a for a in comuns if a not in rec]
    bloco("SUBGRUPO: SUBSTRATO INALTERADO (controle do contraste acima)", nova, velha, resto)

    print()
    print("Se o braço guiado melhorar no subgrupo recuperado e não no inalterado, o")
    print("substrato explica; se melhorar nos dois, a explicação está na instrumentação")
    print("nova ou na composição da amostra, e não no WTG.")

    (EXP / "comparacao_cmp163.json").write_text(json.dumps({
        "n_comuns": len(comuns),
        "admissiveis_comp162": sorted(apks_nova),
        "admissiveis_cmp163": sorted(apks_velha),
        "excluidas_cmp163": sorted(sel_velha["excluded"]),
        "so_comp162": so_nova,
        "so_cmp163": so_velha,
        "wtg_recuperado": rec,
    }, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

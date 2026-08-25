#!/usr/bin/env python3
"""ANÁLISE gh104 — admissibilidade primeiro, depois agregação.

CÓPIA de `../../experimento-comp162/scripts/analise.py`. Mudou o `TASKS_GLOB` (prefixo
`gh104_NN`) e as referências à campanha de referência, que agora é a `comp162`. Os
critérios, as quatro famílias de hipótese e o Holm-Bonferroni ficam como estavam: a leitura
pareada entre as duas campanhas exige que os dois lados sejam agregados pela mesma regra.


    uv run python scripts/analise.py

O `consolidate.py` agrega toda task `COMPLETED`, que é o comportamento certo para um
consolidador e o errado para o veredito: `COMPLETED` registra que a ferramenta retornou sem
levantar exceção, não que o run fez o que devia. Este script aplica os critérios antes de
somar qualquer coisa, e a regra mora em `admissibility.py` porque a leitura pareada contra
a `comp162` precisa aplicar exatamente a mesma aos dois lados. O `admissibility.py` desta
campanha é BYTE-IDÊNTICO ao da `comp162` de propósito: julgar os dois lados com o mesmo
código é o que torna a exclusão derivada em vez de escolhida.

**A regra, em uma frase**: réplica inadmissível é descartada, e a aplicação só sai quando
algum braço fica sem nenhuma réplica admissível. É para isso que R=3 existe — uma falha
transiente não diz nada sobre a aplicação, e deixá-la excluir a aplicação inteira jogaria
fora dado bom em três vezes mais oportunidades do que a campanha de R=1 teve.

**O que R=3 acrescenta.** A §2 mede o desvio-padrão entre réplicas: com R=1 dava para dizer
que uma diferença era consistente entre aplicações, mas não que era maior que o ruído de
repetição. Aqui isso importa duas vezes, porque a diferença procurada entre as campanhas
pode ser da mesma ordem do ruído de exploração.

Contraste MOP sai três vezes — sobre o corpus, restrito a quem tem widget sinalizado, e
restrito a quem tem os três sinais — porque um efeito que só pode existir onde há substrato
aparece diluído no agregado.

Escreve `consolidado/per_apk_admissivel.csv`: a média por aplicação **sobre as réplicas
admissíveis**, restrita às aplicações mantidas. É esse CSV, e não o `per_apk_paired.csv`
cru, que entra na leitura pareada contra
`experimento-comp162/consolidado/per_apk_admissivel.csv`.

**`cov_mop` desta campanha não é "cobertura das specs novas".** Os `.apk.json` são os da
`comp162`, reusados para manter o denominador idêntico (decisão D-c), então `cov_mop` mede
o alcance das 23 specs do `jca` nos dois lados. É a mesma régua aplicada de propósito, e
tem de ser declarada em qualquer leitura deste número.
"""

from __future__ import annotations

import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from admissibility import judge_identities, report, select  # noqa: E402

EXP = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((EXP / "manifest.json").read_text())

ARMS = ["ape", "aperv:mop_off_llm_off", "aperv:mop_on_llm_off"]
SHORT = {"ape": "ape", "aperv:mop_off_llm_off": "mop_off", "aperv:mop_on_llm_off": "mop_on"}
METRICS = ["cov_method", "cov_act", "cov_mop", "mop_unique"]
TASKS_GLOB = str(EXP / "results/gh104_0*/gh104_0*/tasks.json")


def load_per_rep() -> dict:
    """`(apk, braço, réplica)` -> métricas."""
    out = {}
    with (EXP / "consolidado" / "per_rep.csv").open() as f:
        for row in csv.DictReader(f):
            out[(row["apk"], row["tool"], int(row["rep"]))] = {
                m: float(row[m]) for m in METRICS
            }
    return out


def load_substrate() -> dict:
    with (EXP / "censo_substrato.csv").open() as f:
        return {r["apk"]: r for r in csv.DictReader(f)}


def paired(mean_of: dict, apks: list, a: str, b: str, metric: str):
    xs = [mean_of[(k, a)][metric] for k in apks]
    ys = [mean_of[(k, b)][metric] for k in apks]
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
    return dict(n=len(xs), med_a=st.median(xs), med_b=st.median(ys),
                med_diff=st.median(diffs), wins=wins, losses=losses, p=p)


def holm(pvals: list) -> list:
    """Holm-Bonferroni: devolve os p ajustados na ordem original."""
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    adj = [0.0] * len(pvals)
    running = 0.0
    for rank, i in enumerate(order):
        val = (len(pvals) - rank) * pvals[i]
        running = max(running, val)
        adj[i] = min(1.0, running)
    return adj


def main() -> None:
    verdict = judge_identities(TASKS_GLOB, MANIFEST["timeout"])
    if not verdict:
        sys.exit(f"nenhum tasks.json em {TASKS_GLOB}")
    sel = select(verdict, ARMS)
    per_rep = load_per_rep()
    substrate = load_substrate()

    print("=" * 82)
    print("ADMISSIBILIDADE")
    print("=" * 82)
    print("Réplica inadmissível é descartada; a aplicação só sai quando algum braço fica sem")
    print("nenhuma réplica admissível. Critérios C1 (COMPLETED limpo), C2 (>= "
          f"{MANIFEST['timeout'] - 45} s) e C5 (cov_method e cov_act > 0),")
    print("aplicados cegos ao braço e à direção do efeito.")
    print()
    report(sel, ARMS, total_observed=len({apk for apk, _, _ in verdict}))

    kept = sel["kept"]
    # A média por aplicação é sobre as réplicas ADMISSÍVEIS, e não sobre todas as COMPLETED.
    mean_of = {}
    for (apk, arm), reps in sel["good_reps"].items():
        vals = [per_rep[(apk, arm, r)] for r in reps if (apk, arm, r) in per_rep]
        if vals:
            mean_of[(apk, arm)] = {m: st.mean(v[m] for v in vals) for m in METRICS}
    kept = [a for a in kept if all((a, arm) in mean_of for arm in ARMS)]

    # Sem arredondar. Este CSV é a ENTRADA da estatística da comparação pareada, não uma
    # tabela para ler: arredondar a 4 casas injeta um erro de ~5e-05 com sinal essencialmente
    # aleatório em cada célula, que vira contagem de vitórias e p-valor espúrios sempre que a
    # diferença real for da mesma ordem. Medido: comparar dados idênticos com as duas pontas
    # arredondadas dava 87 vitórias contra 70 e p=0,25, onde o correto é empate perfeito.
    # O `per_apk_paired.csv` do consolidador continua com 4 casas — ele é para leitura, e não
    # entra em teste nenhum.
    out = EXP / "consolidado" / "per_apk_admissivel.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["apk"] + [f"{arm}__{m}" for arm in ARMS for m in METRICS]
                   + [f"{arm}__n_reps" for arm in ARMS])
        for apk in kept:
            w.writerow([apk]
                       + [repr(mean_of[(apk, arm)][m]) for arm in ARMS for m in METRICS]
                       + [len(sel["good_reps"][(apk, arm)]) for arm in ARMS])
    print(f"\nescrito {out} ({len(kept)} aplicações)")

    # --- §2: dispersão entre réplicas — o que R=1 não podia medir --------------
    print()
    print("=" * 82)
    print(f"DISPERSÃO ENTRE RÉPLICAS (desvio-padrão dentro da célula, n = {len(kept)})")
    print("=" * 82)
    print("A gh97 mediu desvio-padrão entre réplicas de 1,75-2,12 pp em")
    print("cov_method a 1800 s; a 300 s a dispersão tende a ser maior, e aqui ela é medida.")
    print("Só células com >= 2 réplicas admissíveis entram — uma célula de réplica única não")
    print("tem dispersão a informar, e incluí-la como zero enviesaria a mediana para baixo.")
    print()
    print(f"{'braço':10s}{'células':>9s}" + "".join(f"{m + ' sd':>22s}" for m in METRICS))
    for arm in ARMS:
        cells = [a for a in kept if len(sel["good_reps"][(a, arm)]) >= 2]
        line = f"{SHORT[arm]:10s}{len(cells):9d}"
        for m in METRICS:
            sds = [st.stdev(per_rep[(a, arm, r)][m] for r in sel["good_reps"][(a, arm)])
                   for a in cells]
            if sds:
                p90 = sorted(sds)[min(int(0.9 * len(sds)), len(sds) - 1)]
                line += f"{'med ' + format(st.median(sds), '.2f') + ' p90 ' + format(p90, '.2f'):>22s}"
            else:
                line += f"{'(sem réplica)':>22s}"
        print(line)

    # Uma aplicação nos resultados e fora do censo significa que a campanha rodou algo que
    # não está no corpus declarado — o censo cobre exatamente os 162 do dataset. Isso é dito
    # em voz alta e a aplicação fica FORA dos estratos de substrato, nunca empurrada para o
    # grupo "sem substrato": não se sabe o substrato dela, e tratar desconhecido como zero
    # engordaria o grupo de controle com dado que ninguém verificou.
    sem_censo = [a for a in kept if a not in substrate]
    if sem_censo:
        print()
        print(f"AVISO: {len(sem_censo)} aplicação(ões) nos resultados e AUSENTES do censo:")
        for a in sem_censo:
            print(f"  {a}")
        print("Elas entram no grupo 'corpus' e ficam fora dos estratos de substrato.")
        print("Na campanha real isto não deve acontecer — o censo cobre os 162 do dataset.")

    com_censo = [a for a in kept if a in substrate]
    groups = [
        ("corpus", kept),
        ("substrato (flagged>0)",
         [a for a in com_censo if int(substrate[a]["flagged"]) > 0]),
        ("três sinais",
         [a for a in com_censo if int(substrate[a]["flagged"]) > 0
          and int(substrate[a]["wtg_edges"]) > 0
          and int(substrate[a]["mop_acts"]) > 0]),
    ]

    print()
    print("=" * 82)
    print(f"RESUMO POR BRAÇO (mediana / média das médias por aplicação), n = {len(kept)}")
    print("=" * 82)
    print(f"{'braço':10s}" + "".join(f"{m:>22s}" for m in METRICS))
    for arm in ARMS:
        cells = []
        for m in METRICS:
            vals = [mean_of[(a, arm)][m] for a in kept]
            cells.append(f"{st.median(vals):9.2f} /{st.mean(vals):8.2f}")
        print(f"{SHORT[arm]:10s}" + "".join(f"{c:>22s}" for c in cells))

    # As mesmas quatro famílias da comp162, para que as duas campanhas respondam à mesma
    # pergunta. H3 continua sem direção declarada de propósito.
    families = {
        "H1  mop_on > mop_off  (substrato monitorado)":
            [("aperv:mop_on_llm_off", "aperv:mop_off_llm_off", m) for m in ("cov_mop", "mop_unique")],
        "H2  mop_on > mop_off  (atividades)":
            [("aperv:mop_on_llm_off", "aperv:mop_off_llm_off", "cov_act")],
        "H3  ape ~ mop_off     (custo da re-arquitetura, sem direção declarada)":
            [("ape", "aperv:mop_off_llm_off", "cov_method")],
        "H4  mop_on > ape      (entre ferramentas)":
            [("aperv:mop_on_llm_off", "ape", m) for m in ("cov_mop", "mop_unique")],
    }

    for gname, apks in groups:
        if len(apks) < 6:
            print(f"\n(subgrupo '{gname}' com n={len(apks)} — pequeno demais, omitido)")
            continue
        print()
        print("=" * 82)
        print(f"WILCOXON PAREADO — {gname}  (n = {len(apks)})")
        print("=" * 82)
        print(f"{'hipótese/métrica':34s}{'medA':>8s}{'medB':>8s}{'A>B':>5s}{'A<B':>5s}"
              f"{'p':>10s}{'p_holm':>10s}  sig")
        for fam, tests in families.items():
            print(f"-- {fam}")
            res = [paired(mean_of, apks, a, b, m) for a, b, m in tests]
            adj = holm([r["p"] for r in res])
            for (a, b, m), r, pa in zip(tests, res, adj):
                sig = "sim" if pa < 0.05 else "nao"
                print(f"   {SHORT[a]}>{SHORT[b]} {m:20s}"
                      f"{r['med_a']:8.2f}{r['med_b']:8.2f}{r['wins']:5d}{r['losses']:5d}"
                      f"{r['p']:10.5f}{pa:10.5f}  {sig}")

    print()
    print("Teste bilateral em todas as linhas, inclusive nas hipóteses com direção declarada")
    print("— escolha conservadora; a direção é lida das medianas e da contagem de vitórias.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""A regra de admissibilidade da comp162, num lugar só.

Dois consumidores: `analise.py`, que lê a campanha nova, e `compare_cmp163.py`, que precisa
aplicar a MESMA regra aos dois lados para que o pareamento entre campanhas compare conjuntos
julgados igual. Duplicar a regra é precisamente como as duas leituras divergiriam sem que
ninguém notasse.

## Os critérios, aplicados por identidade `(apk, braço, réplica)`

Cegos ao braço e à direção do efeito. `COMPLETED` registra que a ferramenta retornou sem
levantar exceção, **não** que o run fez o que devia:

- **C1** — `COMPLETED` com `error_message` vazio.
- **C2** — `execution_time_seconds >= timeout - APERV_TEARDOWN_GRACE_S`. A exploração é
  limitada por orçamento **por construção**, então tempo decorrido é o discriminador; o
  código de saída não serve, porque emulador morto e crash da aplicação são indistinguíveis
  por ele.
- **C5** — `cov_method > 0` e `cov_act > 0`.

## A regra de exclusão

**Uma réplica inadmissível não derruba a aplicação.** Ela é descartada e a célula
`(aplicação, braço)` fica com as réplicas que sobraram. É para isso que R=3 existe: uma
falha transiente — `adb install` que pegou o device offline, um emulador que morreu — não
diz nada sobre a aplicação, e deixá-la excluir a aplicação inteira jogaria fora dado bom em
três vezes mais oportunidades do que a campanha de R=1 teve.

**A aplicação sai quando algum braço fica sem nenhuma réplica admissível.** Aí não há valor
para aquele braço, e o par se quebra. A exclusão é então **por aplicação, nunca por braço**:
o teste é pareado, e remover um braço deixando os outros dois desequilibra o par exatamente
onde o dado é pior — o viés entra na direção de quem sobrou. A cmp163 mostrou por quê: no
`org.wikipedia_50595` o braço sobrevivente seria justamente o de referência.

O que resta registrar, e o módulo devolve para que seja registrado: **quantas células
ficaram com menos de R réplicas**. A média de uma célula sobre duas réplicas é mais ruidosa
que sobre três, e isso é assimetria entre células que a leitura precisa enxergar em vez de
absorver em silêncio.
"""

from __future__ import annotations

import glob
import json
from collections import defaultdict
from pathlib import Path

# APERV_TEARDOWN_GRACE_S — a folga de teardown que a própria ferramenta usa dos dois lados:
# o timeout do comando é o orçamento mais esta folga, e o piso de completude é o orçamento
# menos ela.
TEARDOWN_GRACE_S = 45


def floor_for(timeout_s: int) -> int:
    """O piso de C2 para um orçamento."""
    return timeout_s - TEARDOWN_GRACE_S


def arm_label(tool_name: str, variant: str | None) -> str:
    """O rótulo de braço usado em toda parte: `ape` ou `<tool>:<variant>`.

    O builtin `ape` grava `variant='default'` no `tool_config`, e o consolidador colapsa
    isso para `ape` seco. Esta função tem de fazer o MESMO colapso, porque os rótulos aqui
    são casados contra a coluna `tool` do `per_rep.csv`: sem ele o braço vira `ape:default`,
    não casa com nada, e toda aplicação sai por "braço sem execução" — que foi exatamente
    o que aconteceu ao rodar isto contra os dados da cmp163 antes da correção.
    """
    return "ape" if tool_name == "ape" else f"{tool_name}:{variant}"


def judge_identities(tasks_glob: str, timeout_s: int) -> dict:
    """`(apk, braço, réplica)` -> lista de critérios reprovados (vazia == admissível).

    Julga por identidade, nunca por registro: o resume ACRESCENTA um registro em vez de
    sobrescrever, então uma identidade recuperada guarda dois — o `ERROR` e o `COMPLETED`.
    O melhor registro da identidade é o que manda.
    """
    floor = floor_for(timeout_s)
    verdict: dict[tuple, list[str]] = {}
    for f in sorted(glob.glob(tasks_glob)):
        doc = json.loads(Path(f).read_text())
        recs = doc["tasks"] if isinstance(doc, dict) else doc
        best: dict[tuple, dict] = {}
        for t in recs:
            cfg = t.get("config") or {}
            tc = cfg.get("tool_config") or {}
            k = (cfg.get("apk_name"), arm_label(tc.get("name"), tc.get("variant")),
                 cfg.get("repetition"))
            r = t.get("result") or {}
            if k not in best or r.get("state") == "COMPLETED":
                best[k] = r
        for k, r in best.items():
            cm = r.get("coverage_metrics") or {}
            fails = []
            if r.get("state") != "COMPLETED" or r.get("error_message"):
                fails.append("C1")
            if (r.get("execution_time_seconds") or 0) < floor:
                fails.append("C2")
            if not ((cm.get("method_coverage") or 0) > 0
                    and (cm.get("activities_coverage") or 0) > 0):
                fails.append("C5")
            verdict[k] = fails
    return verdict


def select(verdict: dict, arms: list[str]) -> dict:
    """Aplica a regra de exclusão. Devolve o que a leitura precisa reportar.

    Chaves do resultado:
      `kept`          — aplicações que entram na análise pareada, ordenadas
      `excluded`      — `{apk: {braço: [motivos das réplicas]}}` para as que saíram
      `good_reps`     — `{(apk, braço): [réplicas admissíveis]}`
      `dropped_reps`  — `{(apk, braço): [(réplica, motivos)]}` das descartadas em célula viva
      `partial_cells` — células vivas com menos réplicas que o máximo observado
    """
    by_cell: dict[tuple, dict[int, list[str]]] = defaultdict(dict)
    for (apk, arm, rep), fails in verdict.items():
        by_cell[(apk, arm)][rep] = fails

    apks = sorted({apk for apk, _ in by_cell})
    max_reps = max((len(v) for v in by_cell.values()), default=0)

    kept, excluded = [], {}
    good_reps, dropped_reps = {}, {}
    for apk in apks:
        cells = {arm: by_cell.get((apk, arm), {}) for arm in arms}
        good = {arm: sorted(r for r, f in c.items() if not f) for arm, c in cells.items()}
        dead = {arm: [f"rep{r}:{'+'.join(f)}" for r, f in sorted(c.items()) if f]
                for arm, c in cells.items() if not good[arm]}
        if dead or any(not g for g in good.values()):
            # Algum braço sem réplica admissível — ou sem execução nenhuma. O par se quebra.
            excluded[apk] = {arm: dead.get(arm) or ["sem execução"]
                             for arm in arms if not good[arm]}
            continue
        kept.append(apk)
        for arm in arms:
            good_reps[(apk, arm)] = good[arm]
            bad = [(r, cells[arm][r]) for r in sorted(cells[arm]) if cells[arm][r]]
            if bad:
                dropped_reps[(apk, arm)] = bad

    partial = {k: len(v) for k, v in good_reps.items() if len(v) < max_reps}
    return {
        "kept": kept,
        "excluded": excluded,
        "good_reps": good_reps,
        "dropped_reps": dropped_reps,
        "partial_cells": partial,
        "max_reps": max_reps,
    }


def report(sel: dict, arms: list[str], total_observed: int) -> None:
    """Imprime o bloco de admissibilidade. Mesmo formato nos dois consumidores."""
    print(f"aplicações observadas: {total_observed}")
    print(f"aplicações na análise pareada: {len(sel['kept'])}")
    if sel["excluded"]:
        print(f"excluídas ({len(sel['excluded'])}) — braço sem nenhuma réplica admissível:")
        for apk, arms_dead in sorted(sel["excluded"].items()):
            for arm, motivos in sorted(arms_dead.items()):
                print(f"  {apk:44s} {arm:24s} {', '.join(motivos)}")
    else:
        print("nenhuma exclusão — todo braço de toda aplicação tem réplica admissível")

    dropped = sel["dropped_reps"]
    n_drop = sum(len(v) for v in dropped.values())
    print()
    print(f"réplicas descartadas em célula que SOBREVIVEU: {n_drop} "
          f"em {len(dropped)} célula(s)")
    for (apk, arm), bad in sorted(dropped.items())[:15]:
        detalhe = ", ".join(f"rep{r}:{'+'.join(f)}" for r, f in bad)
        print(f"  {apk[:40]:40s} {arm:24s} {detalhe}")
    if len(dropped) > 15:
        print(f"  ... e mais {len(dropped) - 15} célula(s)")

    partial = sel["partial_cells"]
    if partial:
        dist = defaultdict(int)
        for n in partial.values():
            dist[n] += 1
        resumo = ", ".join(f"{q} célula(s) com {n} réplica(s)" for n, q in sorted(dist.items()))
        print()
        print(f"células com menos de {sel['max_reps']} réplicas: {len(partial)} — {resumo}")
        print("A média dessas células é mais ruidosa que a das completas. É assimetria entre")
        print("células, e está aqui para ser enxergada e não absorvida em silêncio.")

#!/usr/bin/env python3
"""ADMISSIBILIDADE — os seis critérios da `estudo02`, por identidade, e que NÃO exclui nada.

    uv run python experimento-estudo02/scripts/admissibility.py            # relatório
    uv run python experimento-estudo02/scripts/admissibility.py --json out.json

Aplica os critérios C1–C6 do §8.2 do plano (`docs/20260908_estudo02.md`) **cegos ao braço e à
direção do efeito**, porque `COMPLETED` registra apenas que a ferramenta retornou sem levantar
exceção — **não** que o run fez o que devia. Um emulador que morre no meio é gravado
`COMPLETED` com `error_message` vazio.

Dois consumidores, e a regra mora aqui uma vez só: o relatório humano e o `repair.py`, que
devolve à fila o que este módulo reprovou. Duplicar a regra é exatamente como as duas leituras
divergiriam sem ninguém notar.

## Este script NUNCA exclui APK, e isso é decisão de projeto, não omissão

A campanha da gh104 excluía a aplicação inteira quando **algum** braço ficava sem nenhuma
réplica admissível, porque lá o teste pareado tinha 3 braços e remover um deles desequilibrava
o par. Aqui são **11 braços × 3 orçamentos**, e a mesma regra é muito mais agressiva: basta uma
célula morta entre 33 para a aplicação sair. Pior, ela sairia por motivo que o artigo aceitou —
os 19 APKs sem `launchable-activity` publicaram cobertura zero em `qtesting` e permaneceram na
análise.

Então este módulo **calcula e reporta** as candidatas à exclusão, com o motivo célula a célula,
e **para por aí**. Nenhuma aplicação sai da análise sem aprovação explícita do responsável pela
campanha. O relatório existe para essa decisão ser tomada com o dado na frente, não para
substituí-la.

## Os critérios, por identidade `(apk, braço, réplica, orçamento)`

- **C1** — `COMPLETED` com `error_message` vazio.
- **C2** — `execution_time_seconds >= orçamento - TEARDOWN_GRACE_S`. A exploração é limitada por
  orçamento **por construção**, então o tempo decorrido é o discriminador; o código de saída não
  serve, porque emulador morto e crash da aplicação são indistinguíveis por ele. **O piso é por
  identidade**, não da campanha: esta corrida mistura 60, 180 e 300 s na mesma passada, e um piso
  único reprovaria todo o bloco de 60 s ou passaria todo o de 300 s.
- **C3** — o traço carrega ao menos um passo além do cabeçalho do run (≥ 2 linhas não vazias).
- **C4** — ao menos uma assinatura `RVSEC-COV` no logcat.
- **C5** — `cov_method > 0` e `cov_act > 0`.
- **C6** — o conjunto de identidades observadas é igual ao previsto pelo manifesto da campanha.
  É o único critério de campanha, não de identidade, e por isso sai no fim do relatório.

## O zero estrutural do `qtesting` não é inadmissibilidade

O `qtesting` upstream resolve a activity de entrada por `aapt dump badging | grep launchable` e
cai no literal `noactivityname` quando o `aapt` não emite a linha. O run então sobe, falha ao
lançar a activity e devolve cobertura zero — sem erro, sem exceção, sem nada a recuperar. São 19
APKs, e são **exatamente os mesmos 19** que o artigo publicou com cobertura zero nesse braço.

Repetir essas identidades produziria o mesmo zero. Elas saem aqui como categoria própria,
`ESTRUTURAL`, que **não** volta à fila e **não** conta como reprovação de C3/C4/C5. Sem essa
ressalva o `repair.py` devolveria 171 identidades à fila para sempre e o C6 nunca fecharia.

A detecção é pelo próprio traço (`cmp=<pacote>/noactivityname`), não por lista congelada: uma
lista escrita à mão envelheceria em silêncio se o corpus mudasse.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "data" / "results"
FILTERS = ROOT / "data" / "estudo02_filters"

#: A folga de teardown que a ferramenta usa dos dois lados (APERV_TEARDOWN_GRACE_S).
TEARDOWN_GRACE_S = 45

#: Os 11 braços do desenho, na ordem do plano §2.
ARMS = [
    "monkey", "droidbot:dfs_greedy", "droidbot:bfs_greedy", "droidbot:dfs_naive",
    "droidbot:bfs_naive", "ape", "droidmate", "humanoid", "ares", "fastbot", "qtesting",
]
REPS = (1, 2, 3)
TIMEOUTS = (60, 180, 300)

#: O literal que o `qtesting` injeta quando o `aapt` não emite `launchable-activity`.
NO_ACTIVITY = "noactivityname"

COV_RE = re.compile(r"RVSEC-COV\s*:\s*\S")

#: Abaixo disto o traço não carrega passo nenhum além do cabeçalho.
TRACE_MIN_LINES = 2


def arm_label(name: str, variant: str | None) -> str:
    """`ape`/`monkey` gravam `variant='default'`; o consolidador colapsa para o nome seco.

    Tem de fazer o MESMO colapso que o `consolidate_compare.py`, porque estes rótulos são
    casados contra a coluna `tool` dele. Sem isso o braço vira `ape:default`, não casa com
    nada, e toda aplicação sai por "braço sem execução".
    """
    return name if not variant or variant == "default" else f"{name}:{variant}"


@dataclass
class Verdict:
    """O julgamento de uma identidade. `fails` vazio e `structural` falso == admissível."""

    container: str
    elapsed: int
    timeout: int
    fails: list[str] = field(default_factory=list)
    structural: bool = False
    records: int = 1
    cov_method: float = 0.0
    cov_act: float = 0.0
    cov_mop: float = 0.0
    mop_unique: int = 0

    @property
    def admissible(self) -> bool:
        return not self.fails and not self.structural


def artifact(container: str, rel: str | None) -> Path | None:
    """Resolve um caminho do `tasks.json` (visão do container) no host.

    O volume mapeia `data/results/<cid>` sobre `/opt/rvsec/rv-android/results` e o experimento
    escreve em `results/<cid>/...` relativo ao workdir — daí o `<cid>` aparecer duas vezes no
    host e o prefixo `results/` sair fora.
    """
    if not rel:
        return None
    return RESULTS / container / rel.replace("results/", "", 1)


def _trace_lines_and_structural(path: Path | None) -> tuple[int, bool]:
    """Linhas não vazias do traço e se ele é o zero estrutural do `qtesting`.

    `-1` linhas significa traço ausente, que é reprovação inequívoca de C3.
    """
    if not path or not path.exists():
        return -1, False
    n, structural = 0, False
    with path.open(errors="ignore") as fh:
        for line in fh:
            if line.strip():
                n += 1
            if NO_ACTIVITY in line:
                structural = True
    return n, structural


def _has_cov_signature(path: Path | None) -> bool:
    """C4: basta UMA assinatura `RVSEC-COV`, então para na primeira.

    O logcat de um run de 300 s passa de 1 MB e a campanha tem 16 137 deles; varrer o arquivo
    inteiro para responder "existe ao menos uma" custaria dezenas de GB de leitura à toa.
    """
    if not path or not path.exists():
        return False
    with path.open(errors="ignore") as fh:
        for line in fh:
            if COV_RE.search(line):
                return True
    return False


def expected_identities() -> set[tuple]:
    """O manifesto da campanha: os filtros × 11 braços × 3 réplicas × 3 orçamentos.

    Lido dos filtros e não de um literal, porque o corpus é o que os filtros dizem que é — foi
    assim que o corte do `stardroid` entrou sem ninguém reescrever uma constante.
    """
    apks = []
    for f in sorted(FILTERS.glob("batch_*.txt")):
        apks += [ln.strip() for ln in f.read_text().splitlines() if ln.strip()]
    return {(a, arm, rep, to) for a in apks for arm in ARMS for rep in REPS for to in TIMEOUTS}


def judge(containers: list[str], read_artifacts: bool = True) -> dict[tuple, Verdict]:
    """`(apk, braço, réplica, orçamento)` -> `Verdict`.

    Julga por identidade, nunca por registro: o resume ACRESCENTA um registro em vez de
    sobrescrever, então uma identidade recuperada guarda dois — o `ERROR` e o `COMPLETED`. O
    melhor registro da identidade é o que manda, e a contagem de registros fica guardada
    porque o `repair.py` a usa para não reparar duas vezes a mesma identidade.

    `read_artifacts=False` pula C3 e C4 (os dois que tocam disco) e serve para uma leitura
    rápida de C1/C2/C5 no meio da campanha.
    """
    best: dict[tuple, tuple[str, dict]] = {}
    seen: dict[tuple, int] = defaultdict(int)
    for cid in containers:
        p = RESULTS / cid / cid / "tasks.json"
        if not p.exists():
            continue
        doc = json.loads(p.read_text())
        for t in (doc["tasks"] if isinstance(doc, dict) else doc):
            cfg, res = t.get("config") or {}, t.get("result") or {}
            tc = cfg.get("tool_config") or {}
            ident = (cfg.get("apk_name"), arm_label(tc.get("name"), tc.get("variant")),
                     cfg.get("repetition"), cfg.get("timeout"))
            seen[ident] += 1
            if ident not in best or res.get("state") == "COMPLETED":
                best[ident] = (cid, res)

    verdicts: dict[tuple, Verdict] = {}
    for ident, (cid, res) in best.items():
        timeout = ident[3] or 0
        elapsed = res.get("execution_time_seconds") or 0
        cm = res.get("coverage_metrics") or {}
        v = Verdict(
            container=cid,
            elapsed=elapsed,
            timeout=timeout,
            records=seen[ident],
            cov_method=cm.get("method_coverage") or 0.0,
            cov_act=cm.get("activities_coverage") or 0.0,
            cov_mop=cm.get("methods_mop_reachable_coverage") or 0.0,
            mop_unique=int(cm.get("total_errors") or 0),
        )

        if res.get("state") != "COMPLETED" or res.get("error_message"):
            v.fails.append("C1")
        # O piso é por identidade: esta corrida mistura três orçamentos na mesma passada.
        if elapsed < timeout - TEARDOWN_GRACE_S:
            v.fails.append("C2")

        if read_artifacts:
            lines, structural = _trace_lines_and_structural(artifact(cid, res.get("trace_file")))
            v.structural = structural
            if lines < TRACE_MIN_LINES:
                v.fails.append("C3")
            if not _has_cov_signature(artifact(cid, res.get("logcat_file"))):
                v.fails.append("C4")

        if not (v.cov_method > 0 and v.cov_act > 0):
            v.fails.append("C5")

        # O zero estrutural do `qtesting` não é inadmissibilidade: o run correu como devia
        # correr dado o APK, e repeti-lo produz o mesmo zero. Sai como categoria própria e
        # some das reprovações de conteúdo, que são justamente a consequência dele.
        if v.structural:
            v.fails = [c for c in v.fails if c not in ("C3", "C4", "C5")]

        verdicts[ident] = v
    return verdicts


def exclusion_candidates(verdicts: dict[tuple, Verdict]) -> dict[str, dict]:
    """As aplicações que a regra da gh104 excluiria — para DECISÃO HUMANA, não para ação.

    Uma célula é `(apk, braço, orçamento)` e vive de 3 réplicas. Célula sem nenhuma réplica
    admissível quebra o pareamento naquele orçamento. Devolve, por APK, quais células ficaram
    mortas e por quê.

    Nada aqui exclui coisa alguma. Ver o cabeçalho do módulo.
    """
    cells: dict[tuple, dict[int, Verdict]] = defaultdict(dict)
    for (apk, arm, rep, to), v in verdicts.items():
        cells[(apk, arm, to)][rep] = v

    dead: dict[str, dict] = defaultdict(dict)
    for (apk, arm, to), reps in cells.items():
        if any(v.admissible for v in reps.values()):
            continue
        motivo = "zero estrutural (qtesting sem launchable-activity)" \
            if all(v.structural for v in reps.values()) \
            else ", ".join(f"rep{r}:{'+'.join(v.fails) or 'ESTRUTURAL'}"
                           for r, v in sorted(reps.items()))
        dead[apk][f"{arm}@{to}s"] = motivo
    return dict(dead)


def report(verdicts: dict[tuple, Verdict], expected: set[tuple], read_artifacts: bool) -> None:
    """O bloco de admissibilidade. Mesmo formato para leitura humana e para o registro."""
    adm = {i: v for i, v in verdicts.items() if v.admissible}
    struct = {i: v for i, v in verdicts.items() if v.structural}
    bad = {i: v for i, v in verdicts.items() if v.fails}

    print("=" * 78)
    print("ADMISSIBILIDADE — estudo02")
    print("=" * 78)
    if not read_artifacts:
        print("!! modo --skip-artifacts: C3 e C4 NÃO foram avaliados; o zero estrutural do")
        print("!! qtesting não é detectável sem o traço, então ele aparece reprovado em C5.")
    print(f"identidades observadas : {len(verdicts)}")
    print(f"  admissíveis          : {len(adm)}")
    print(f"  zero estrutural      : {len(struct)}  (qtesting sem launchable-activity)")
    print(f"  inadmissíveis        : {len(bad)}")
    print()

    if bad:
        por_criterio = defaultdict(int)
        por_braco = defaultdict(int)
        for i, v in bad.items():
            for c in v.fails:
                por_criterio[c] += 1
            por_braco[i[1]] += 1
        print("inadmissíveis por critério (uma identidade pode reprovar em mais de um):")
        for c in sorted(por_criterio):
            print(f"  {c}  {por_criterio[c]:>6}")
        print("inadmissíveis por braço:")
        for a in sorted(por_braco, key=lambda x: -por_braco[x]):
            print(f"  {a:<22}{por_braco[a]:>6}")
        print()
        print("as 30 primeiras (identidade, decorrido/orçamento, critérios):")
        for i, v in sorted(bad.items())[:30]:
            print(f"  {i[1]:<22}{i[0][:38]:<38} rep{i[2]} {v.elapsed:>4}/{v.timeout:<4} "
                  f"{'+'.join(v.fails)}")
        if len(bad) > 30:
            print(f"  ... e mais {len(bad) - 30}")
        print()

    if struct:
        apks = sorted({i[0] for i in struct})
        print(f"zero estrutural: {len(struct)} identidades em {len(apks)} APK(s).")
        print("Não voltam à fila: repeti-las produz o mesmo zero. São as mesmas que o artigo")
        print("publicou com cobertura zero neste braço.")
        for a in apks:
            print(f"  {a}")
        print()

    # --- C6: o critério de campanha ---------------------------------------
    obs = set(verdicts)
    faltando, sobrando = expected - obs, obs - expected
    print("-" * 78)
    print(f"C6 — completude: observadas {len(obs)} / previstas {len(expected)}")
    if faltando:
        print(f"  AUSENTES: {len(faltando)}")
        for i in sorted(faltando)[:10]:
            print(f"    {i[1]:<22}{i[0][:38]:<38} rep{i[2]} {i[3]}s")
        if len(faltando) > 10:
            print(f"    ... e mais {len(faltando) - 10}")
    if sobrando:
        print(f"  INESPERADAS: {len(sobrando)}")
        for i in sorted(sobrando)[:10]:
            print(f"    {i[1]:<22}{i[0][:38]:<38} rep{i[2]} {i[3]}s")
    if not faltando and not sobrando:
        print("  o conjunto observado é exatamente o previsto pelo manifesto.")
    print()

    # --- Candidatas à exclusão: relatório, nunca ação ---------------------
    cand = exclusion_candidates(verdicts)
    print("-" * 78)
    print("CANDIDATAS À EXCLUSÃO — relatório para decisão, NENHUMA foi excluída")
    print("-" * 78)
    if not cand:
        print("nenhuma: toda célula (apk, braço, orçamento) tem ao menos uma réplica admissível.")
        return
    so_estrutural = [a for a, cs in cand.items()
                     if all("zero estrutural" in m for m in cs.values())]
    outras = [a for a in cand if a not in so_estrutural]
    print(f"{len(cand)} APK(s) com ao menos uma célula sem réplica admissível.")
    print(f"  {len(so_estrutural)} apenas pelo zero estrutural do qtesting")
    print(f"  {len(outras)} por outros motivos")
    print()
    for apk in sorted(outras) + sorted(so_estrutural):
        print(f"  {apk}")
        for cell, motivo in sorted(cand[apk].items()):
            print(f"      {cell:<28}{motivo}")
    print()
    print("Este script não exclui APK. A regra da gh104 (aplicação sai quando um braço fica sem")
    print("réplica) foi escrita para 3 braços; aqui são 11 × 3 orçamentos, e os 19 APKs sem")
    print("launchable-activity permaneceram na análise do artigo. A decisão é do responsável")
    print("pela campanha, com esta lista na frente.")



def campaign_is_running(containers: list[str]) -> list[str]:
    """Quais dos containers estão de pé agora. Lista vazia == campanha parada."""
    up = []
    for cid in containers:
        try:
            r = subprocess.run(["docker", "inspect", cid, "--format", "{{.State.Running}}"],
                               capture_output=True, text=True, timeout=30)
        except Exception:
            continue
        if r.returncode == 0 and r.stdout.strip() == "true":
            up.append(cid)
    return up


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("containers", nargs="*", default=None,
                    help="containers a ler (default: estudo02_00..09)")
    ap.add_argument("--json", metavar="ARQ",
                    help="grava os veredictos para o repair.py consumir")
    ap.add_argument("--skip-artifacts", action="store_true",
                    help="pula C3/C4 (não tocam disco); leitura rápida no meio da campanha")
    ap.add_argument("--during-campaign", action="store_true",
                    help="autoriza a varredura de artefatos com a campanha no ar (ver a guarda)")
    args = ap.parse_args()

    containers = args.containers or [f"estudo02_{i:02d}" for i in range(10)]

    # C3 e C4 abrem os 16 137 traços e logcats, no MESMO disco que os containers estão
    # usando para escrever. Rodar isso com a campanha no ar rouba I/O de quem está medindo
    # e contamina o próprio dado: o tempo decorrido é o discriminador do C2, e ele mede
    # mais alto sob contenção. A guarda existe porque o custo já foi pago uma vez.
    if not args.skip_artifacts:
        up = campaign_is_running(containers)
        if up and not args.during_campaign:
            print(f"!! {len(up)} container(es) de pé: {', '.join(up)}")
            print("!! C3/C4 varrem todos os traços e logcats no mesmo disco que eles usam.")
            print("!! Rode --skip-artifacts agora, ou espere a campanha fechar.")
            print("!! Para forçar mesmo assim: --during-campaign.")
            return 2
    verdicts = judge(containers, read_artifacts=not args.skip_artifacts)
    if not verdicts:
        print("!! nenhuma identidade lida — confira os containers e os caminhos de resultado")
        return 1
    report(verdicts, expected_identities(), not args.skip_artifacts)

    if args.json:
        out = {
            "|".join(str(x) for x in i): {
                "container": v.container, "elapsed": v.elapsed, "timeout": v.timeout,
                "fails": v.fails, "structural": v.structural, "records": v.records,
                "cov_method": v.cov_method, "cov_act": v.cov_act,
                "cov_mop": v.cov_mop, "mop_unique": v.mop_unique,
            }
            for i, v in verdicts.items()
        }
        Path(args.json).write_text(json.dumps(out, indent=1))
        print(f"\nveredictos gravados em {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# `experimento-comp162` — a instrumentação nova na grade do cmp163

**Isto não é o experimento final do Estudo 03.** É um ensaio: a mesma grade da `cmp163`
rodando sobre o corpus recém-instrumentado
(`APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162`, montado em 2026-08-12), para
ver como ele se comporta antes que o final dependa dele. O resultado é lido **contra** a
`cmp163`, que é a campanha de referência: plano em `../docs/20260806_cmp163.md`, resultados
em `../docs/20260807_resultados_cmp163.md`.

O plano desta corrida está em `../docs/20260812_comp162.md`.

## O desenho

| | |
|---|---|
| Braços | `ape` · `aperv:mop_off_llm_off` · `aperv:mop_on_llm_off` |
| Corpus | 162 APKs — `selected162.txt`, sha256 `3bbc5fa9…` |
| Repetições | **3** |
| Timeout | 300 s por task |
| Total | **1458 runs**, 8 containers, ≈ 20 h |
| Imagem | `phtcosta/rvandroid:0.9.3-comp162` (tag nova, a construir) |
| Jar | `ape-rv.jar` local `a7eddf5a…` por bind-mount — o mesmo da `cmp163` |
| SGLang | não — nenhum braço LLM |

Os braços são os da `cmp163`, com os papéis inalterados:

- **`ape`** — o APE original, `ape.jar` builtin do `rv-tools`. Binário comitado, **não
  alterado desde fevereiro**: é literalmente o mesmo binário que rodou na `cmp163`.
- **`mop_off_llm_off`** — controle. Artefato MOP presente no dispositivo, cinco pesos em 0,
  gatilho de atividade desligado. Remove a **guia**, não a navegação (INV-APV-30).
- **`mop_on_llm_off`** — referência. O mesmo, mais `ACTIVITY_TRIGGER`, `MENU_GATEWAY`,
  `MOP_FRONTIER` e `WTG`.

## Três repetições, e não uma

É a lacuna que a §7 do relatório da `cmp163` declarou: com R=1 não há medida de variância
dentro da célula, então dá para dizer que uma diferença é **consistente entre aplicações**,
mas não que ela é **maior que o ruído de repetição**. A gh97 mediu desvio-padrão entre
réplicas de 1,75–2,12 pp em `cov_method` a 1800 s; a 300 s a dispersão tende a ser maior, e
é isso que R=3 torna mensurável. `scripts/analise.py` §dispersão reporta esse número.

O custo é 3× o relógio: ~6,7 h viram ~20 h.

## Três coisas diferem da `cmp163`, e todas tocam a leitura

**Os binários.** Os APKs foram reinstrumentados em 2026-08-12. É o objeto do ensaio, e a
razão de a campanha existir.

**A imagem carrega a guarda INV-APV-60.** O commit `c1d28365` é de 2026-08-06 e a
`0.9.3-rearch` foi construída em 2026-08-05 — a `cmp163` rodou sem a guarda, e pagou por
isso: exploração truncada chegava ao consolidador indistinguível de run íntegro, o resume
não a alcançava, e a recuperação dependeu de um script de reparo offline. O
`com.starry.myne_500` truncou aos 168 s e, na re-execução nove horas depois, aos 169 s. Aqui
a ferramenta levanta exceção no ato do truncamento e o resume comum recupera a identidade.
`scripts/repair.py` continua existindo como rede de segurança; zero reparos é o resultado
esperado. O portão 7 do smoke confere que a guarda está **dentro da imagem**.

**O substrato mudou em 10 aplicações.** A re-análise da gh91 recuperou o WTG de dez APKs
que antes entregavam grafo vazio — 41 → 51 com WTG povoado no censo. Isso alimenta
exatamente o braço de referência, que consome `wtgEdges`. As dez são um subgrupo declarado
da análise entre campanhas.

O que **não** difere: a partição, o jar, o corpus (menos uma aplicação), o orçamento por
task, o conjunto de especificações, e o binário do braço `ape`.

## A partição é herdada, e isso é deliberado

`filters/batch_00.txt` … `batch_07.txt` vêm dos filtros da `cmp163` menos
`info.dvkr.screenstream_44000.apk`, o APK que saiu do corpus por estourar o teto de 64K
referências do DEX. Lotes de 21, 20, 21, 20, 20, 20, 20, 20.

O motivo é o pareamento entre campanhas. As duas rodam no mesmo host com oito containers
competindo; se uma aplicação trocasse de índice de container, efeito-de-container deixaria
de cancelar na diferença pareada — foi o custo que a emenda 01 da gh97 teve de assumir e
registrar. Aqui esse custo não precisa ser pago, porque o corpus novo é o antigo menos
exatamente um elemento. **Gerar round-robin sobre a lista nova faria o oposto**: remover um
elemento renumera tudo que vem depois dele e desloca cerca de metade do corpus.

`scripts/make_filters.py` deriva e verifica: união == dataset, sem duplicata, sem perda.

## Como rodar

```bash
cd experimento-comp162

# 0. a imagem (depois do push do rvsec — o Dockerfile clona, não copia a árvore local)
docker build --no-cache --build-arg RVSEC_BRANCH=modules \
  -t phtcosta/rvandroid:0.9.3-comp162 ../docker/rvandroid
uv run python scripts/make_manifest.py --image-id "$(docker inspect -f '{{.Id}}' phtcosta/rvandroid:0.9.3-comp162)"

# 1. smoke primeiro; os sete portões são o critério de aceitação dele
docker compose -f docker-compose.smoke.yml up -d       # 2 apps, 1 rep, 120 s, 6 runs
uv run python scripts/smoke_gates.py

# 2. a campanha só começa com 7/7 portões PASS
docker compose up -d
bash scripts/monitor.sh                                # ou: watch -n 300 bash scripts/monitor.sh
bash scripts/cycle.sh                                  # monitor + reparo + resume + admissibilidade

# 3. consolidação, análise, e a leitura contra a campanha anterior
uv run python scripts/consolidate.py
uv run python scripts/analise.py
uv run python scripts/compare_cmp163.py
```

**`--no-cache` no build não é opcional.** O `RUN git clone` do Dockerfile é uma camada como
qualquer outra: sem invalidar o cache, o Docker reusa a camada da `0.9.3-rearch` e a imagem
sai sem nenhum commit novo — inclusive sem a guarda, que é a razão do rebuild.

**Não usar `../docker/rvandroid/build.sh`**: ele marca `0.9.3` e `latest`, que são a
identidade da imagem da perna A do E3.

**Resume**: re-rodar o mesmo `docker compose up -d`. A identidade de um run é
`(apk, tool, variant, repetition, timeout)`, então o que já completou não é refeito e tasks
`FAILED`/`ERROR` transientes são recuperadas.

**Não dar `down` antes de extrair os traces** — os artefatos vivem no device e são efêmeros.

## Os scripts

| Arquivo | Papel |
|---|---|
| `make_filters.py` | Deriva `filters/` dos filtros da `cmp163`; verifica união, duplicata e perda |
| `censo_substrato.py` | Chama `derive()` — a mesma função que o `aperv-tool` roda — sobre os 162 `.apk.json`; gera `censo_substrato.csv` |
| `make_manifest.py` | Gera `manifest.json` a partir de `get_variants()`; as definições dos braços são a autoridade, nunca transcritas |
| `smoke_gates.py` | Os sete portões do smoke; sai 1 em qualquer FAIL |
| `monitor.sh` | Progresso por container, contado por identidade distinta, com alvo por lote |
| `repair.py` | Rede de segurança: devolve à fila run truncado, preservando evidência antes de reescrever |
| `cycle.sh` | Ciclo: monitor → reparo → resume → admissibilidade |
| `consolidate.py` | `tasks.json` + logcats → `consolidado/` (`per_rep`, `per_apk_paired`, `per_tool_summary`, `wilcoxon`) |
| `admissibility.py` | A regra de admissibilidade, num lugar só — os dois consumidores abaixo a aplicam |
| `analise.py` | Admissibilidade, dispersão entre réplicas, e as quatro famílias H1–H4 por estrato |
| `compare_cmp163.py` | A leitura pareada contra a campanha anterior, com o subgrupo dos 10 WTGs recuperados |

## A regra de admissibilidade

Por identidade `(apk, braço, réplica)`, cegos ao braço e à direção do efeito: **C1** `COMPLETED`
com `error_message` vazio · **C2** `execution_time_seconds >= 255 s` (orçamento menos a folga de
teardown) · **C5** `cov_method > 0` e `cov_act > 0`.

**Réplica inadmissível é descartada; a célula fica com as que sobraram.** É para isso que R=3
existe: uma falha transiente — `adb install` que pegou o device offline — não diz nada sobre a
aplicação, e na `cmp163` nove das dez re-execuções foram exatamente disso.

**A aplicação só sai quando algum braço fica sem nenhuma réplica admissível.** Aí não há valor para
aquele braço e o par se quebra; a exclusão é por aplicação, nunca por braço, porque o teste é
pareado e remover um braço deixando os outros dois desequilibra o par onde o dado é pior.

Quantas células ficaram com menos de três réplicas é **reportado**, não absorvido: a média de uma
célula sobre duas réplicas é mais ruidosa que sobre três.

A regra vive em `scripts/admissibility.py` porque tem dois consumidores — a análise da campanha e a
comparação com a `cmp163`, que precisa julgar os dois lados igual. Validada rodando contra os
`tasks.json` da `cmp163`: reproduz o julgamento publicado daquela campanha exatamente — n=160, as
mesmas três exclusões, os mesmos critérios por braço.

## O que o censo do substrato mostra

`censo_substrato.csv`, calculado chamando `derive()` e não lendo o JSON cru — é o resultado
da derivação, e não o JSON de entrada, que o jar consome.

| | 162 |
|---|---:|
| com widget sinalizado (`flagged>0`) | 30 |
| com WTG povoado após derivação | 51 |
| com os três sinais | 11 |
| **WTG cru vazio (`transitions==0`)** | **41** |
| destes, declarando `complete=true` | 41 |
| WTG derivado vazio (`wtg_edges==0`) | 111 |

As duas últimas linhas são a leitura do **P11**
(`../docs/20260812_registro_execucao_prontidao_e3.md` §3.1). O predicado do P11 é
`transitions==0`, e os 41 são 40 truncados mais 1 genuinamente vazio — separá-los exige o
`timed_out` do `_progress`, que mora no `rvsec-dataset-sa`. Todos os 41 se declaram
completos pelo sentinela, que é exatamente o defeito que a Fase A expôs.

`wtg_edges==0` é o número maior e o mais relevante para ler a cobertura: **111 das 162
entregam grafo de clique vazio ao braço guiado**. Não é o mesmo defeito — a visão
só-de-clique descarta janela sem widget e funde diálogo, então um app pode ter transições e
nenhuma aresta de clique. É por isso que a análise estratifica.

## Estado

Andaime pronto e verificado, **imagem não construída e campanha não executada**. Estado em
2026-08-12:

1. ✅ Filtros derivados e verificados — 162 APKs, lotes `[21, 20, 21, 20, 20, 20, 20, 20]`.
2. ✅ Censo do substrato gerado; reproduz o P11 (41) a partir do artefato.
3. ✅ Manifesto gerado de `get_variants()` — 1458 identidades previstas, `image.id` nulo.
4. ✅ Composes validados (`docker compose config`).
5. ⏳ **Push do `rvsec` pelo pesquisador** — o Dockerfile clona a branch `modules`, então o
   commit da guarda precisa estar no remoto antes do build.
6. ⏳ Build da imagem, `make_manifest.py --image-id`, smoke, sete portões, campanha.

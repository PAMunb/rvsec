# Portão empírico da re-arquitetura do APE-RV — `experimento-rearch-aperv`

A perna B de uma comparação A/B que decide se a linha `rearch` do APE-RV entra em merge. É a
execução do change `gh97-rearch-ab-gate`, e o plano de análise está **pré-registrado** em
`../docs/20260804_preregistro_gate_rearch.md`.

A perna A já existe e está congelada: é a corrida decisiva E3
(`../experimento-e3-decisiva/per_apk_paired.csv`, 360 runs, 2026-08-01/02), medida no jar
`386ce08d…` sobre o commit `5dcf2259…` do `ape`. **Ela não pode ser refeita** — o
`gh96-mop-artifact-derivation` já está implementado nesta árvore, e o jar da perna A não sabe ler o
artefato que o `tool.py` de hoje empurra. Metade da medição, portanto, já está paga; o custo marginal
do portão é uma campanha pós-reescrita do mesmo formato.

O pré-registro é o que dá peso probatório ao resultado: ele fixa desfechos, margens e regra de
decisão **antes de qualquer dado ser visto**. Depois do congelamento — o registro do sha256 do
arquivo em `../calibracao/journal.jsonl` — nada nele pode mudar, e toda análise não prevista lá é
exploratória por definição. **Congelar antes de construir o jar.**

## O desenho

| | |
|---|---|
| Braços | `mop_on_llm_off` · `mop_off_llm_off` · `mop_on_llm_70` |
| Corpus | 40 APKs — `../calibracao/subset40.txt`, sha256 `b60903ad…d48d4` |
| Repetições | 3 |
| Timeout | 1800 s por task |
| Total | 360 runs, **10 containers** (emenda 01), ≈ 18,6 h |
| Imagem | `phtcosta/rvandroid:0.9.3-rearch` (tag nova) |
| Jar | build do worktree `ape-rearch`, branch `rearch`, por bind-mount |

O desenho é **idêntico ao da perna A por exigência, não por preferência**. O valor por aplicação da
perna A é a média de três réplicas (`consolidate_cal.py:311`); rodar uma réplica só aqui tornaria a
diferença pareada assimetricamente mais ruidosa — mais variância de um lado de uma diferença que
depois é testada contra zero. Esse é o mecanismo por trás da falsa catástrofe de 2026-06-19, em que
um smoke não pareado de 16 aplicações mostrou −4,7 pp que, pareado a n≈70, era empate exato.

## Duas coisas diferem da perna A, e ambas são o ponto

**A imagem é uma tag nova.** Reconstruir `0.9.3` no lugar tornaria as duas pernas
indistinguíveis por tag e reproduziria a forma do gh71 na camada de imagem. O ID da imagem da perna A
está registrado (`sha256:b2904fdf…`), e `:latest` aponta para ele — outra razão para não reaproveitar
tag alguma.

**O jar sob teste chega por bind-mount.** O `docker/rvandroid/Dockerfile` clona `phtcosta/ape` sem
`--branch` e sem pin de SHA — decisão deliberada do gh71 — e no momento da campanha `rearch` ainda
não está em merge. Existem portanto **dois jars dentro do container**, e `RUN_START.build.sha` é o
único que diz qual deles rodou. É por isso que o pre-flight bloqueia a campanha.

## A regra de decisão, em três partes

**G1 (bloqueia)** compara a perna B contra a perna A **só no braço de controle**, pareado por
aplicação (n=40). Esse braço zera os cinco pesos MOP e desliga o gatilho de atividade, então a
mudança de substrato do gh96 não alcança o comportamento dele — o que se move nesse contraste é a
reescrita. Foi medido, não argumentado: o portão de validade 1 do E3 estabeleceu `decision_source=MOP`
== 0 e `mop=` == 0 em todo passo do braço.

**G2 (bloqueia, unilateral)** exige que o contraste **dentro da campanha nova**
`mop_on_llm_off − mop_off_llm_off` em `cov_act` continue positivo com IC excluindo zero (na perna A:
+14,916, IC95 [7,754; 22,039]). Os dois termos são medidos sobre o mesmo substrato, então o contraste
é imune ao confundimento; e ele cobre o que o G1 por construção não vê — o caminho de escore ponderado
por MOP, que é justamente o que a reescrita reescreveu. É unilateral porque `cov_act` está no teto nos
dois braços guiados (mediana 100,0; 31 das 40 aplicações exatamente em 100): regressão é detectável,
melhora não é.

**G3 (descritivo)** reporta os níveis de operações monitoradas dos braços guiados ao lado do
deslocamento de substrato calculado no host antes do congelamento: 104 → 159 widgets sinalizados e
38 → 49 atividades sinalizadas sobre as 40 aplicações, concentrados em 4 delas. Não bloqueia e não
prediz direção — o gh96 amplia a superfície sinalizada e ao mesmo tempo achata o ranking entre os
widgets, e um pré-registro não deve afirmar um sinal que não consegue justificar.

**Um achado bloqueante exige as duas coisas**, nunca uma só: IC excluindo zero na direção danosa **e**
|Δ| acima da margem do desfecho. As margens são derivadas da dispersão entre réplicas da própria
perna A (`docs/20260804_gh97_notas_de_trabalho.md` §3.2): `cov_method` 1,92 pp · `cov_act` 1,50 pp ·
`cov_mop` 2,09 pp. `mop_unique`, `mop_total` e `crashes` são reportados com IC e não bloqueiam.

## Como rodar

```bash
cd experimento-rearch-aperv

# 0. o manifesto é gerado, nunca transcrito (as definições dos braços são a autoridade)
uv run python scripts/make_manifest.py --out manifest.json

# 1. smoke primeiro; o pre-flight é o critério de aceitação dele
docker compose -f docker-compose.smoke.yml up -d          # 2 apps, 1 rep, 300 s, 6 runs
uv run python scripts/preflight_runstart.py --results results_smoke --manifest manifest.json

# 2. a campanha só começa com 3/3 braços PASS nas quatro checagens
docker compose up -d
bash scripts/monitor.sh                    # ou: watch -n 120 bash scripts/monitor.sh

# 3. portões de validade antes de qualquer desfecho, depois consolidação e verdito
uv run python scripts/verify.py --iter-dir .
uv run python scripts/consolidate.py --iter-dir .
uv run python scripts/compare.py --leg-b per_apk_paired.csv
```

**Resume**: re-rodar o mesmo `docker compose up -d`. A identidade de um run é
`(apk, tool, variant, repetition, timeout)`, então o que já completou não é refeito e tasks FAILED
transientes são recuperadas.

**Não dar `down` antes de extrair os traces** — os artefatos vivem no device e são efêmeros.

## Particionamento

`filters10/batch_00.txt` … `batch_09.txt`, 4 aplicações cada, split determinístico em ordem alfabética
do `subset40.txt`. União == subset, sem duplicata e sem perda, verificado na geração.

**Emenda 01 (2026-08-05)**: a partição passou de 8 × 5 para 10 × 4, pela mesma regra alfabética
determinística, para caber no orçamento de relógio — ~18,6 h contra ~23,2 h. Os oito arquivos da perna
A ficam intactos em `filters/`, porque são a partição dela e portanto evidência.

O que isso custa, dito sem atenuação: os arquivos **deixam de ser byte-idênticos aos da perna A**,
então uma aplicação já não roda no mesmo container-índice das duas vezes e efeitos de container param
de cancelar na diferença pareada. O pareamento **por aplicação**, que é o que sustenta G1/G2/G3,
continua intacto, e é sobre ele que os intervalos de confiança são construídos. Nenhum elemento da
grade estatística foi tocado: 3 braços, 40 aplicações, 3 réplicas, 1800 s, 360 runs.

Cada container roda os **três braços sobre as suas 4 aplicações**. O pareamento estatístico é por
aplicação, então manter os três braços de uma aplicação no mesmo container faz uma falha de container
derrubar o par inteiro em vez de meio par — o que o resume recupera limpo, enquanto meio par exigiria
descarte.

## Os scripts

| Arquivo | Papel |
|---|---|
| `make_manifest.py` | Gera `manifest.json` a partir de `get_variants()`. Duas chaves ficam nulas até existirem: `build.expected_sha` (task 6.2) e `image.id` (task 6.5) |
| `preflight_runstart.py` | As quatro checagens sobre o `RUN_START`; sai 1 em qualquer FAIL. É o critério de aceitação do smoke |
| `consolidate.py` | Cópia do `consolidate_cal.py` → `per_apk_paired.csv` e `tel_proxies.csv` |
| `verify.py` | Cópia do `verify_iteration.py`; re-derivação independente e os portões de validade |
| `multiarm_stats.py` · `stats_utils.py` | Cópias verbatim; `paired_bootstrap_ci` é o estimando |
| `compare.py` | G1, G2 e G3 contra o plano congelado |
| `test_compare.py` | Testes de `compare.py` e do pre-flight sobre entradas sintéticas |
| `monitor.sh` | Progresso por container, contado por identidade distinta |

**As cópias são cópias, e os originais não se tocam.** `experimento-cal/scripts/*` é leitor de corpus
congelado (INV-APV-55): aqueles arquivos parseiam a família `[APE-*]` de uma campanha que não será
regerada, e `TestFrozenCorpusCarveOut` reprova se alguém os migrar. Aqui as cópias tiveram **apenas o
caminho de leitura de trace** adaptado para `aperv_tool.analysis.trace_ndjson`; os caminhos de logcat
e de `tasks.json` — que produzem todo desfecho de manchete e o `per_apk_paired.csv` inteiro — ficaram
intactos, de modo que as duas pernas permanecem idênticas em coluna e em agregação. Qualquer coisa
mais larga quebraria o pareamento sobre o qual o portão inteiro se apoia.

`stats_utils.py` é cópia byte-idêntica: `paired_bootstrap_ci` não lê trace nenhum e precisa ser
exatamente a rotina que a análise do E3 usou. O teste
`TestEstimandMatchesLegA::test_g2_reproduces_the_published_e3_contrast` fecha esse laço reproduzindo
+14,916 [7,754; 22,039] a partir do CSV congelado — se a cadeia deixar de ler o que o E3 leu, esse
teste cai.

## O que o pre-flight checa, e por quê

Quatro checagens sobre a **primeira linha** de um trace por braço. A campanha não começa sem 3/3 braços
PASS em todas.

1. **`props_digest`** bate com o sha256 do `ape.properties` que o harness empurrou. Prova o transporte
   sem ambiguidade de mapeamento: o jar leu exatamente os bytes enviados.
2. **`preset` + `params`** batem com o plano declarado do braço. É a única execução que o `gh95`
   adiou para cá: sem ela, um jar anterior ao estágio 2 trataria `ape.preset` como chave desconhecida
   e colapsaria todos os braços aos defaults do jar, com o diretório de resultados ainda carregando o
   nome do braço.
3. **`build.sha`** bate com o commit `rearch` construído. É a que sustenta as outras — com dois jars
   no container, ela é o único discriminador.
4. **`corpus_basis`** bate com o sha256 recomputado do arquivo da lista. Esta faz papel duplo, e por
   isso bloqueia em vez de só reportar: **ausente** significa que o caminho de parâmetros do DSL
   perdeu o valor antes do `ape.properties`; **divergente** significa que ele chegou com a lista
   errada.

Uma sutileza que o teste fixa: uma chave declarada **ausente** de `params` não é falha. O jar omite do
eco toda chave que está no próprio default, e duas chaves desta campanha —
`frontierBoostWeight=200` e `activityTriggerEnabled=true` — são exatamente os defaults do jar. Tratar
a ausência como erro reprovaria toda corrida saudável. O que autoriza essa leitura é a checagem 1: o
`props_digest` já provou que o jar recebeu os bytes empurrados. E para que a checagem não fique vazia
por esse caminho, um braço em que **nenhuma** chave declarada pôde ser comparada reprova.

## Ambiente — o que quebra e por quê

- **A GPU é pedida como dispositivo CDI** (`devices: [nvidia.com/gpu=0]`), e não por
  `deploy.resources.reservations.devices` com driver `nvidia`. O host roda Docker 29 com o NVIDIA
  container toolkit instalado mas com o runtime nvidia **não registrado** no daemon, então a reserva
  por driver falha com `could not select device driver "nvidia" with capabilities: [[gpu]]`.
- **O spec CDI vive em `/var/run/cdi/nvidia.yaml`, que é tmpfs** e não sobrevive a um reboot.
  Persistir com `sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml`.
- **O modelo é o stock `Qwen/Qwen3-VL-4B-Instruct`**, o mesmo da perna A. Trocá-lo colocaria uma
  segunda diferença entre as pernas além da que o portão mede.
- **A ponte do LLM é socat** (`docker/rvandroid/docker-entrypoint.sh:38-40`): com
  `RVSMART_LLM_MODE=true` o container liga `127.0.0.1:30000` ao container `sglang`. O jar lê `llm_url`
  de dentro do emulador, onde `10.0.2.2` é o alias de host-loopback do QEMU.
- **A gestão do emulador é do `rv-platform`, do início ao fim.** Nenhum comando de emulador é dado à
  mão, em nenhum contexto, sem exceção.

## Estado

Andaime pronto, **campanha não executada**. Estado em 2026-08-05:

1. ✅ Pré-registro congelado — `c0ac9a7f…` em `../calibracao/journal.jsonl` (2026-08-04), com o
   apêndice de proveniência preenchido depois e registrado em entrada separada (`a0da2273…`).
2. ✅ Jar construído do worktree `ape-rearch` em `9e948102`, sha256 `a7eddf5a…`, e
   `build.expected_sha` preenchido no manifesto. O carimbo foi conferido **antes** do deploy:
   dentro de uma worktree o `git-commit-id-maven-plugin` carimba o HEAD do `master`, então o build
   fornece a revisão pela linha de comando (design D10).
3. ✅ Imagem `phtcosta/rvandroid:0.9.3-rearch` construída, ID `sha256:2cc5c3aa…`. **Não empurrada**
   (decisão do dono, 2026-08-05): a campanha roda neste host e o compose não declara `pull_policy`,
   então o Compose resolve a imagem local sem falar com o registry.
   Construída com `--build-arg RVSEC_BRANCH=rearch-counterparts` — o default do `Dockerfile` é
   `modules` e produziria uma imagem sem nenhuma das contrapartes. **Não usar `docker/rvandroid/
   build.sh`**: ele marca `0.9.3` e `latest`, que são a identidade da imagem da perna A.
4. ⏳ Smoke (`docker-compose.smoke.yml`), pre-flight, e só então a campanha.

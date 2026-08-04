# Notas de trabalho — gh97, portão empírico da re-arquitetura do APE-RV

**Início**: 2026-08-04 · **Change**: `openspec/changes/gh97-rearch-ab-gate/` · **Issue**: #97

Este arquivo é o caderno de campo da change: guarda os fatos medidos, as derivações e as decisões
tomadas durante a implementação. Não é artefato OpenSpec e não é o pré-registro — o pré-registro
(`docs/20260804_preregistro_gate_rearch.md`) é o plano congelado, e o que estiver aqui e não estiver
lá não vincula a análise.

Cada fato abaixo foi **medido nesta árvore**, com o comando registrado ao lado. Nenhum número foi
transposto de artefato: os artefatos da change citam os mesmos valores, e a coincidência é a
verificação, não a fonte.

---

## 1. Proveniência da perna A — capturada antes que algo a destrua

A perna A é a corrida decisiva E3, executada em 2026-08-01/02. Sua imagem Docker existe apenas na
máquina local: um `docker prune` apaga o ID e ele não é recuperável depois. Por isso este grupo vem
antes de qualquer outra coisa.

### 1.1 Identidade da imagem

| Campo | Valor |
|---|---|
| Tag | `phtcosta/rvandroid:0.9.3` |
| ID | `sha256:b2904fdfc3ddfc81ad455abd5e5685ddc97666c9411c4d994fec9111311aedec` |
| Criada em | `2026-08-01T11:47:43.532501911-03:00` |
| `RepoTags` | `["phtcosta/rvandroid:0.9.3", "phtcosta/rvandroid:latest"]` |

`:latest` aponta para **o mesmo ID**, e é isso que torna o registro necessário: uma retag futura de
`:latest` para outra imagem não deixaria rastro no ID, e sem esta linha alguém poderia ler a retag
como se fosse um rebuild da perna A. Registrado em 2026-08-04, com a imagem ainda presente
localmente.

```bash
docker inspect --format '{{.Id}} {{.Created}} {{json .RepoTags}}' phtcosta/rvandroid:0.9.3
docker inspect --format '{{.Id}} {{.Created}} {{json .RepoTags}}' phtcosta/rvandroid:latest
```

Ambos os comandos devolvem o mesmo ID e a mesma data de criação. A imagem da perna B será
`phtcosta/rvandroid:0.9.3-rearch` (design D9): tag nova, nenhuma reutilização de `0.9.3` ou
`:latest`.

### 1.2 Identidade do jar e o commit de base

| Campo | Valor |
|---|---|
| `ape-rv.jar` sha256 | `386ce08d1846a4088755a8d755e5b70391af3b42add091d231dbcc52aed24e69` |
| Caminho na árvore | `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar` |
| Commit de base | `5dcf225976b26ce78d8b31dd88d7f858dad29d43` |
| Onde vive o commit | repositório **`ape`**, branch `master`, 2026-07-31 17:27:27 -0300 |

O jar implantado **ainda tem esse hash** em 2026-08-04 — ou seja, o binário da perna A continua no
lugar e nada o substituiu desde a corrida. É esse jar que a task 6.2 vai sobrescrever com o build do
`rearch`, e é por isso que o hash é registrado agora.

O commit `5dcf2259…` é do repositório `ape`, **não** desta árvore. Procurá-lo aqui devolve
`fatal: Not a valid object name`, o que é o esperado e não um erro: o jar da perna A foi construído a
partir do `master` do `ape` naquele commit, e o `git sha` desta árvore na época é registro separado.

```bash
sha256sum modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar
git -C ../../ape log -1 --format='%H %ci %s' 5dcf2259
```

### 1.3 O dígito do corpus — a base de ambas as pernas

| Campo | Valor |
|---|---|
| Arquivo | `calibracao/subset40.txt` |
| Linhas | 40 |
| sha256 | `b60903adf4c8fca07e014e3655db158a220184d112f2f995a181fd98dd3d48d4` |

O valor de `corpus_basis` que as duas pernas declaram é, portanto:

```
subset40:b60903adf4c8fca07e014e3655db158a220184d112f2f995a181fd98dd3d48d4
```

Esta é a string que viaja pelo DSL de ferramentas até `ape.corpusBasis`, e é contra ela que o
pre-flight recomputa o hash do arquivo (design D7, quarta checagem).

```bash
sha256sum calibracao/subset40.txt && wc -l calibracao/subset40.txt
```

### 1.4 A entrada congelada da perna A

| Campo | Valor |
|---|---|
| Arquivo | `experimento-e3-decisiva/per_apk_paired.csv` |
| Linhas | 41 (cabeçalho + 40) |
| Aplicações distintas | 40 |
| sha256 | `a90b34cbc0ebcd85776fd288ac94129e7a6806e8bd672efd492e3b7c779e3031` |

Os três braços esperados estão presentes, cada um com seis desfechos, nas 18 colunas de dados:

| Braço | Colunas |
|---|---|
| `aperv:mop_off_llm_off` | `cov_method`, `cov_act`, `cov_mop`, `mop_unique`, `mop_total`, `crashes` |
| `aperv:mop_on_llm_70` | idem |
| `aperv:mop_on_llm_off` | idem |

A verificação que importa para o pareamento não é a contagem, é a identidade: a coluna `apk` do CSV é
**idêntica ao conteúdo de `calibracao/subset40.txt`**, aplicação por aplicação, sem sobra dos dois
lados. Isso é o que autoriza a perna B a parear contra a perna A por nome de aplicação.

```bash
diff <(sort calibracao/subset40.txt) \
     <(tail -n +2 experimento-e3-decisiva/per_apk_paired.csv | cut -d, -f1 | sort)   # sem saída
sha256sum experimento-e3-decisiva/per_apk_paired.csv
```

---

## 2. `corpus_basis` — o único código que o portão acrescenta

### 2.5 — o alcance da varredura do `RUN_START`

INV-APV-57 diz que **nenhum componente lê `RUN_START` em caminho de execução**, e é assim que a
varredura foi escrita: ela cobre `modules/aperv-tool/src/aperv_tool/` **exceto o pacote
`analysis/`**. A exceção não é uma brecha, é o próprio invariante: `trace_ndjson.py` e
`clock_logcat_join.py` existem justamente para consumir `RUN_START` *post-hoc*, sobre traces já
gravados, e é lá que o pre-flight da campanha vai conferir o eco do `corpus_basis`. Uma varredura
literal sobre todo o `src` reprovaria a entrega do `gh94` e não diria nada sobre o que o invariante
protege.

A varredura traz duas asserções de não-vacuidade, porque um teste que afirma uma ausência fica verde
por construção: uma confere que a lista varrida realmente contém `tool.py` e
`derive_mop_artifact.py` (um pacote renomeado esvaziaria a lista em silêncio), e a outra confere que
a **mesma busca acha** `trace_ndjson.py` no pacote `analysis/` — se o token estivesse escrito errado,
a primeira asserção passaria sem verificar nada.

O teste `TestRetiredGuards::test_no_run_start_parsing`, que já existia e cobre só `tool.py`,
mostrou-se mais estrito do que parecia: ele reprova a simples **menção** ao token, e reprovou de
fato quando um comentário novo no `APERV_PROPERTY_MAPPING` dizia que o jar "ecoa a chave no
`RUN_START`". O comentário foi reescrito para falar do "registro de abertura do trace". O guarda
guarda.

Os guardas novos foram verificados quebrando o mecanismo e vendo o teste reprovar, e não apenas
vendo-o passar:

| Mecanismo removido | Efeito na suíte |
|---|---|
| a validação de forma em `configure()` | 7 reprovações em `TestCorpusBasis` |
| a entrada `corpus_basis` do `APERV_PROPERTY_MAPPING` | 11 reprovações |
| (restaurados) | 316 passando |

### 2.6 — o pré-check local do seam do DSL: **PASSA**

A pergunta é se `@corpus_basis=<id>:<sha256>` sobrevive à cadeia inteira até virar linha no
`ape.properties`, dado que `_parse_single_tool_spec` emite uma forma plural que o próprio
`TODO(FR15)` do módulo declara morta. **Sobrevive** — e o motivo é que aquela função não está no
caminho: o parser vivo é `CLIContext.parse_tool_specification` (`rv_experiment/__main__.py:163`),
que produz um `ToolConfig` **por braço**, cada um com a mesma cópia dos parâmetros.

A cadeia exercitada, sem dispositivo (o push é interceptado, o arquivo é escrito e lido de volta):

```
"aperv:mop_on_llm_off:mop_off_llm_off:mop_on_llm_70@corpus_basis=subset40:<sha256>"
  → _split_tool_specifications        devolve a spec inteira, sem quebrar na vírgula (não há)
  → CLIContext.parse_tool_specification  3 × ToolConfig, parameters={'corpus_basis': '…'}
  → ToolFactory.create_tool           {**variant_config, **tool_config.parameters}
  → ApeRVTool.configure               dobra a chave mapeada em `overrides`
  → ApeRVTool._push_properties        emite a linha na ordem da tabela de mapeamento
```

O `@` é separado **antes** do `:`, então os dois-pontos de dentro do dígito sobrevivem — é o que o
design D8 previa, agora medido. Os três braços produziram a linha, byte a byte igual ao configurado:

```
ape.corpusBasis=subset40:b60903adf4c8fca07e014e3655db158a220184d112f2f995a181fd98dd3d48d4
```

Exemplo completo do arquivo gerado para `aperv:mop_off_llm_off`, que é o braço de controle e o canal
do G1:

```properties
ape.preset=mop
ape.mopDataPath=/data/local/tmp/mop-artifact.json
ape.mopWeightDirect=0
ape.mopWeightTransitive=0
ape.mopWeightOpenMenu=0
ape.mopWeightWtg=0
ape.mopActivitySourceComponents=true
ape.frontierBoostWeight=200
ape.corpusBasis=subset40:b60903adf4c8fca07e014e3655db158a220184d112f2f995a181fd98dd3d48d4
```

**Consequência para a campanha**: o `RV_TOOLS` do `docker-compose.yml` entrega o corpus pelo DSL, e
o fallback previsto na 2.6 — uma entrada `overrides` por braço — **não é necessário**. Nenhum desvio
a registrar.

Isto continua sendo o check barato. O veredito autoritativo é o da task 7.2, sobre os traces do
smoke: só ele percorre a cadeia até o jar e de volta pelo eco, e é lá que um `corpus_basis` ausente
seria diagnosticado como quebra do caminho de parâmetros.

---

## 3. Margens e premissas, derivadas da perna A

### O estimando, antes de qualquer margem

Toda margem abaixo está na unidade do estimando que a análise usa, e o estimando **não** é a média
das diferenças pareadas: `stats_utils.paired_bootstrap_ci` estima a **diferença de médias aparadas a
10%**, recomputada a cada reamostra, com reamostragem pareada por APK (B=10.000, semente 42). A
diferença entre as duas leituras não é acadêmica — no `cov_act` do contraste E3 a média das
diferenças dá +14,006 e o estimando aparado dá +14,916.

O número aparado é o que o relatório da corrida decisiva publicou, e a cadeia foi verificada
reproduzindo-o a partir do CSV congelado com o código copiado:

| | `cov_act`, `mop_on_llm_off` − `mop_off_llm_off` |
|---|---|
| Relatório E3 (`docs/20260802_resultados_corrida_decisiva.md:345`) | +14,916 · IC95 [7,754; 22,039] |
| Recomputado aqui sobre `per_apk_paired.csv` | +14,916 · IC95 [7,754; 22,039] |

Casamento exato. Isso é o que autoriza o `compare.py` da campanha a ler a perna A do CSV congelado
em vez de reprocessá-la.

### 3.1 — dispersão entre réplicas, na granularidade `(apk, rep, tool)`

Medida **sobre as mesmas definições que a perna A usou**, e não sobre o `coverage.csv`: o
`consolidate_cal.py` monta os desfechos a partir do `tasks.json` (`method_coverage`,
`activities_coverage`, `methods_mop_reachable_coverage`, `total_errors`) e recontabiliza o
`mop_total` das linhas `RVSEC` do logcat. O script de dispersão **importa** aquele módulo em vez de
reimplementá-lo, então mede o que o portão compara. O `coverage.csv` continua sendo a mesma
granularidade, mas é uma segunda derivação dos mesmos runs, e usá-lo introduziria uma diferença de
definição bem no lugar onde a comparação precisa ser idêntica.

Cobertura: **360 identidades, 120 células `(apk, braço)`, todas com 3 réplicas** — nenhuma célula
incompleta, o que é o esperado para 40 × 3 braços e confirma que a perna A está completa.

Dispersão dentro da célula (SD entre as 3 réplicas), resumida sobre as 40 aplicações:

| Braço | Desfecho | SD mediana | SD média | SD p90 | SD máx | Nível mediano |
|---|---|---:|---:|---:|---:|---:|
| `mop_off_llm_off` | `cov_method` | 1,659 | 2,307 | 4,728 | 9,174 | 48,19 |
| `mop_off_llm_off` | `cov_act` | 0,000 | 2,070 | 6,415 | 28,868 | 87,99 |
| `mop_off_llm_off` | `cov_mop` | 1,812 | 3,074 | 7,762 | 15,746 | 49,68 |
| `mop_off_llm_off` | `mop_unique` | 0,000 | 0,087 | 0,000 | 2,887 | 5,00 |
| `mop_off_llm_off` | `mop_total` | 6,009 | 10,133 | 21,733 | 99,204 | 40,50 |
| `mop_off_llm_off` | `crashes` | 0,000 | 0,000 | 0,000 | 0,000 | 0,00 |
| `mop_on_llm_off` | `cov_method` | 1,889 | 2,687 | 5,016 | 11,495 | 47,58 |
| `mop_on_llm_off` | `cov_mop` | 2,255 | 3,354 | 6,963 | 18,924 | 49,29 |
| `mop_on_llm_off` | `mop_total` | 6,030 | 11,638 | 28,184 | 67,211 | 45,17 |
| `mop_on_llm_70` | `cov_method` | 1,891 | 2,370 | 5,287 | 7,024 | 45,47 |
| `mop_on_llm_70` | `cov_mop` | 1,636 | 3,675 | 5,890 | 57,735 | 47,35 |
| `mop_on_llm_70` | `mop_total` | 5,387 | 8,542 | 23,116 | 42,720 | 28,67 |

O valor que a perna A leva ao CSV é a **média de 3 réplicas**, cujo ruído de réplica é `SD/√3`. No
braço de controle — o canal do G1 — isso dá `cov_method` 0,958 · `cov_act` 0,000 · `cov_mop` 1,046 ·
`mop_unique` 0,000 · `mop_total` 3,469.

Duas leituras que a tabela entrega de graça e que valem para o desenho: `crashes` é identicamente
zero nos três braços (nenhuma variação, nenhum nível — é a evidência que sustenta o D3), e
`mop_unique` tem SD mediana zero com nível mediano 5,0, ou seja, é estável por aplicação e quase não
distingue braços.

### 3.2 — a margem por desfecho

**Regra congelada** (decisão do dono, 2026-08-04):

```
margem(desfecho) = max( 1,5 pp ,  2 × SD_mediana(média de 3 réplicas, braço de controle) )
```

com o piso de 1,5 pp aplicando-se apenas aos desfechos percentuais. A justificativa dos dois termos:

- **O piso** é o dobro do drift entre campanhas já documentado (−0,743 pp de `cov_mop`, p=0,0099,
  sem nenhuma mudança de código). Um portão que exigisse apenas "IC exclui zero" reprovaria a fusão
  em cima desse drift.
- **O fator 2 sobre a dispersão** aplica à dispersão medida a mesma conservadoria que o piso aplica
  ao drift. A dispersão intra-campanha é **limite inferior** da variabilidade entre campanhas: as
  duas pernas rodam com dias de diferença, imagem diferente e carga de host diferente. Tomá-la como
  estimativa direta subestimaria por construção.

| Desfecho | SD da média de 3 réplicas | 2 × | Piso | **Margem** |
|---|---:|---:|---:|---:|
| `cov_method` | 0,958 | 1,916 | 1,5 | **1,92 pp** |
| `cov_act` | 0,000 | 0,000 | 1,5 | **1,50 pp** |
| `cov_mop` | 1,046 | 2,092 | 1,5 | **2,09 pp** |
| `mop_unique` | 0,000 | 0,000 | — | não bloqueia (D3) |
| `mop_total` | 3,469 | 6,938 | — | não bloqueia (3.3) |
| `crashes` | 0,000 | 0,000 | — | não bloqueia (D3) |

Uma constatação que a derivação obriga a declarar: no `cov_act` a SD mediana é **zero** porque mais
da metade das aplicações não varia entre réplicas — o desfecho está no teto. A margem dele vem
inteira do piso, e é por isso que a premissa do 3.6 existe.

### 3.3 — `mop_total` é **descritivo**, não bloqueia

Decisão do dono, 2026-08-04, tomada antes do congelamento e sobre a evidência do 3.1:

- No braço de controle a SD entre réplicas tem mediana 6,01 linhas e média 10,13, contra nível
  mediano de 40,5 — ruído típico de ~15% do nível. A cauda é pior: p90 de 21,7 e uma aplicação com
  SD de 99,2 linhas.
- Ele conta **linhas de violação**, não violações distintas. Um laço que re-dispara a mesma violação
  infla o desfecho sem que a capacidade de detecção tenha mudado. O desfecho que mede detecção é o
  `mop_unique`, e esse é praticamente constante (SD mediana 0,0).
- No próprio contraste E3 entre braços que diferem **por desenho**, `mop_total` dá +2,52 linhas com
  IC95 [−2,14; 7,62] — inclui zero. Um desfecho que não separa braços deliberadamente diferentes não
  vai separar uma regressão da reescrita.

Continua sendo reportado com IC, como todos os outros. O que muda é que não bloqueia sozinho.

### 3.4 — o deslocamento de substrato esperado no G3

Comparação por aplicação entre a semântica **antiga** (a de enriquecimento, que a produção rodava
antes do gh96: todo listener carregava `handlerReachesTarget == handlerDirectlyReachesTarget ==
reachesTarget(handler)`) e a **nova** (`derive_mop_artifact.derive()`).

Método, e por que ele é assim: os dois lados passam pelo **mesmo** `derive()`. O lado antigo é
obtido reproduzindo em memória a escrita que o `_enrich_listener_reach` fazia
(`backup/gh96-compaction/tool.py:1119-1127`) e derivando o artefato a partir do documento
enriquecido. Assim as duas contagens compartilham todas as regras que **não** estão sob comparação —
o descarte por *short id* vazio, o mapa de widgets por atividade, a dobra do menu — e o delta é a
mudança semântica sozinha. Contar o lado antigo pelo *probe* e o novo pelo `derive()` misturaria a
semântica com uma regra de contagem diferente, e nas três aplicações que mais se movem isso de fato
acontece (o probe conta ocorrências de widget; o mapa as chaveia por atividade).

Verificação do método antes de usá-lo: recomputados sobre o corpus fixado de 345 aplicações, os
totais pré-descarte deram **3.733 (antiga) e 4.965 (nova)** — exatamente o que o gh96 registrou.

Sobre as 40 aplicações do portão, contagem pós-descarte (que é a que chega ao dispositivo):

| | Widgets sinalizados | Atividades sinalizadas |
|---|---:|---:|
| Semântica antiga (perna A) | 104 | 38 |
| Semântica nova (perna B) | 159 | 49 |
| Delta | **+55 (+52,9%)** | **+11 (+28,9%)** |

O deslocamento é **concentrado, não difuso**: 36 das 40 aplicações não mudam nada.

| Aplicação | Antiga | Nova | Δ | Recuperados pelo D8 |
|---|---:|---:|---:|---:|
| `de.blau.android_3404` | 1 | 42 | +41 | 36 |
| `com.smartpack.packagemanager_79` | 0 | 10 | +10 | 10 |
| `com.beemdevelopment.aegis_81` | 47 | 50 | +3 | 17 |
| `com.owncloud.android_48000100` | 10 | 11 | +1 | 1 |

Em atividades sinalizadas movem-se duas: `com.smartpack.packagemanager_79` de 0 para 6 e
`de.blau.android_3404` de 2 para 7. Essa é a coluna que mais importa para o comportamento, porque
`activity_has_mop` é o que arma o gatilho de atividade: a `smartpack` tinha **zero** atividade
sinalizada na perna A, ou seja, rodava os braços guiados sem nenhuma orientação por atividade, e na
perna B passa a ter seis.

Além do volume há a mudança de **camada**, que o gh96 já havia estabelecido e que esta contagem não
mede: todo widget antes sinalizado migra do nível `direct` para o `transitive`, e os dois entram no
escore por pesos diferentes (`ape.mopWeightDirect` contra `ape.mopWeightTransitive`). Nenhuma
direção é predita a partir disso — é exatamente por não haver sinal defensável que o G3 é descritivo
e que o G1 se apoia no braço de controle.

### 3.5 — o guarda de pegada não teria disparado em nenhuma das 40

O guarda vive no jar (`ape/.../utils/MopData.java:197`) e é uma função pura do tamanho do arquivo:
rejeita quando `fileSize > Runtime.maxMemory() / 6`. O que ele pesava antes do gh96 era o **JSON
completo compactado** que o `tool.py` empurrava — `transitions` deduplicado, listeners enriquecidos,
serializado sem espaços. Esse é o arquivo reproduzido byte a byte aqui.

Os logcats da perna A não trazem nenhuma linha `[APE-MOP-DATA]`, então a ausência de rejeição não
podia ser lida deles — a verificação teve de ser por tamanho.

| | Valor |
|---|---:|
| Maior documento empurrado, entre as 40 | **15,50 MB** (`org.prauga.messages_8.apk`) |
| Segundo maior | 9,18 MB (`com.darkrockstudios.apps.hammer.android_303020000.apk`) |
| Soma das 40 | 83,81 MB |

| Heap do processo | Limiar (`heap/6`) | Rejeitadas | Folga sobre o maior |
|---|---:|---:|---:|
| 128 MB | 21,33 MB | **0 de 40** | 1,4× |
| 192 MB (o do emulador) | 32,00 MB | **0 de 40** | 2,1× |
| 256 MB | 42,67 MB | **0 de 40** | 2,8× |

Nenhuma aplicação a declarar. A folga se mantém mesmo na hipótese pessimista de heap de 128 MB, que
é menor do que o ~192 MB documentado. Consequência para o portão: a remoção do guarda pelo gh96 não
pode inflar a perna B, porque não havia nada represado na perna A.

### 3.6 — o teto do `cov_act`, declarado como premissa

Medido, não citado:

| Braço | `cov_act` média | mediana | Aplicações em 100,0 |
|---|---:|---:|---:|
| `mop_off_llm_off` (controle) | 81,50 | 87,99 | 18/40 |
| `mop_on_llm_off` (referência) | 95,51 | 100,00 | 31/40 |
| `mop_on_llm_70` (LLM) | 92,72 | 100,00 | 31/40 |

Nos dois braços guiados a mediana é 100,0 e 31 das 40 aplicações estão exatamente no teto. A
consequência é assimétrica e precisa estar no pré-registro **antes** de qualquer resultado:
**regressão é detectável, melhora não é**. Um braço guiado que melhorasse não teria para onde subir
em 31 aplicações. Por isso o G2 é declarado **unilateral** — ele afirma que o contraste dentro da
campanha continua positivo e com IC excluindo zero, e não que ele cresceu.

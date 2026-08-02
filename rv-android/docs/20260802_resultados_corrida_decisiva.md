# Resultados da corrida decisiva E3

**Data**: 2026-08-02
**Change**: `gh90-e3-decisive-run-setup` (GitHub issue #90)
**Plano de análise**: `docs/20260730_preregistro_corrida_decisiva.md` — congelado antes da corrida,
sha256 `4157faa0…` em `calibracao/journal.jsonl`, emendado e recongelado (`893a80d7…`) às 15:13:59Z de
2026-08-01, ainda antes de qualquer dado existir.
**Campanha**: `experimento-e3-decisiva/`

---

## 1. Sumário executivo

A corrida rodou por completo e os quatro portões de validade passaram. **Os dois contrastes
pré-registrados deram resultado plano**: nenhum dos 40 APKs mudou de estado de detecção binária em
nenhuma direção, em nenhum dos três braços. O `n_discordante` do McNemar é **zero** nos dois
contrastes, e nenhum teste rejeita.

Pela regra de empate do §5, a conclusão registrada é **"o tratamento não acrescenta"** — para o LLM
(RQ-C3) isso significa sair do desenho; para a guia MOP (RQ-C1) significa registrar **resultado
negativo para a hipótese central da tese** e reportá-lo como tal. Ao lado disso registra-se, como o
§3 exige, que **o desenho não tinha poder para rejeitar**: com `n_discordante` abaixo de 7 o McNemar
exato bicaudal não alcança a correção de Holm, e aqui não houve sequer um par discordante para o
teste operar.

O que a corrida **não** foi é silenciosa quanto ao mecanismo. A guia MOP funciona no que se propõe a
fazer — o braço de referência alcança **95,5%** das activities contra **81,5%** do controle, uma
diferença de +14,9 pontos com IC95 [7,75; 22,04] —, e mesmo assim encontra as mesmas violações. Esse
é o achado central: **neste corpus a exploração de GUI não é o gargalo da detecção de mau uso de
JCA**, exatamente a leitura que o §6 do pré-registro havia declarado como honesta caso o binário
viesse plano.

---

## 2. O que rodou

### 2.1 Desenho executado

| | |
|---|---|
| Braços | `mop_on_llm_off` (referência) · `mop_off_llm_off` (controle, RQ-C1) · `mop_on_llm_70` (LLM, RQ-C3) |
| Corpus | 40 APKs instrumentados (jca/dexlib2, campanha `20260706`), `calibracao/subset40.txt` |
| Repetições | 3 por (APK, braço) |
| Timeout | 1800 s por task |
| Total | **360 runs** = 40 × 3 × 3 |
| Paralelismo | 8 containers × 5 APKs, cada um rodando os três braços dos seus APKs |
| Imagem | `phtcosta/rvandroid:0.9.3` |
| Backend LLM | SGLang `v0.5.6.post2`, `Qwen/Qwen3-VL-4B-Instruct` stock |

O particionamento mantém os três braços de um mesmo APK no mesmo container. Isso não é detalhe de
paralelização: a unidade de pareamento estatístico é o APK, então uma falha de container derruba o
par inteiro (que o resume recupera) em vez de meio par (que forçaria descarte).

### 2.2 Linha do tempo

| momento | evento |
|---|---|
| 2026-08-01 15:02:33Z | congelamento do pré-registro (`4157faa0…`) |
| 2026-08-01 15:13:59Z | emenda para 3 réplicas e recongelamento (`893a80d7…`) |
| 2026-08-01 15:43:19Z | **lançamento** (`docker compose up -d`) — posterior aos dois congelamentos |
| 2026-08-02 12:19 | 358 runs completos; os 8 containers saem sozinhos |
| 2026-08-02 12:19–12:56 | resume automático recupera as 2 falhas transitórias → 360 |
| 2026-08-02 13:13–13:45 | re-execução da réplica invalidada (§3.3) → 360 válidos |

Custo medido: **~31 min por run** em regime (medido nos traces: 13:14:19 → 13:45:20 → 14:15:32),
contra os ~31 min que o modelo de custo previa a partir do smoke. Duração total ≈ 23 h 36 min.

A ordenação dos congelamentos antes do primeiro run é evidência auditável de que a emenda de 3
réplicas não foi feita depois de ver dados.

### 2.3 Incidentes e como foram tratados

**Duas falhas transitórias de instalação.** `broccoli_1040400` rep1 (braço LLM) e `aegis_81` rep2
(braço referência) morreram em ~57 s com `adb: device offline` no `install`. A causa é uma espera de
boot que nunca funciona: o comando
`adb wait-for-device shell 'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 1; done;'` falha
com `exit 127` porque `[[ ]]` não existe no shell do device, e o código declara `booted!` sem ter
verificado nada. Normalmente é inócuo — o emulador já está de pé quando o `install` ocorre. Nessas
duas vezes não estava. Ambas foram recuperadas pelo resume, que as re-executa por serem `ERROR`.

**Uma falha silenciosa, gravada como sucesso.** `info.metadude.android.fossgis.schedule_118` rep1
(braço referência) foi registrada `COMPLETED` com 65 s dos 1800 s, trace de **864 bytes**, **zero**
linhas `[APE-STEP]` e todas as métricas de cobertura em zero. O trace inteiro é um stack trace: o
Monkey do APE morreu em `getSystemInterfaces` → `setActivityController` com `DeadObjectException`,
isto é, o binder do `system_server` sumiu antes do acoplamento. A plataforma observa o processo da
ferramenta terminar, não se ele explorou, e por isso marcou sucesso.

Isso importa porque o desfecho primário é maioria de 3 réplicas: uma réplica morta lida como zero
imporia ao braço de referência a exigência de que as **duas** sobreviventes detectassem, enquanto os
outros braços teriam três chances — desvantagem artificial imposta justamente à referência, e num dos
oito clones `fahrplan`. O §3 proíbe explicitamente substituir por zero uma réplica que não completou.

Tratamento: a entrada foi marcada `ERROR` (com justificativa gravada no próprio `error_message`) para
que o resume a regerasse — um resume não a recuperaria sozinho, porque `_skip_completed_tasks()` só
pula o que está `COMPLETED` (`platform.py:277`, `task_storage.py:536`). A re-execução produziu 1890 s,
trace de 14.378.365 bytes, 1265 passos e cobertura de métodos 48,53%, plenamente dentro do intervalo
das irmãs (47,3%–50,9%). A tentativa morta e o `tasks.json` original estão preservados em
`backup/gh90-fossgis-rep1-invalida/`.

**Detecção**: a varredura que encontrou o caso testou os 360 runs por três sinais (trace < 100 KB,
cobertura toda zero, `DeadObjectException`) e retornou **exatamente 1**. Não há zona cinzenta: o
segundo menor trace da campanha tem 2,4 MB.

---

## 3. Portões de validade (§2 do pré-registro)

Nenhum desfecho foi lido antes destes quatro passarem. Um portão reprovado invalida o que ele
protege; a análise não é ajustada para contorná-lo.

### 3.1 Portão 1 — controle limpo (bloqueante) · **PASS**

No braço `mop_off_llm_off`, varridos os 120 traces:

| verificação | resultado |
|---|---|
| `decision_source=MOP` | **0** |
| `mop=` não-zero (ancorado `(?<![a-z_])mop=`) | **0 linhas em 0 runs** |
| `mop_frontier=` não-zero | **0 runs** |
| qualquer tag `[APE-LLM-*]` | **0 runs** |

As fontes de decisão observadas no controle são apenas `SATA`, `Coverage`, `Budget`, `Form` e `WTG` —
sem `MOP`, sem `Component` e sem `Menu`, coerente com o gatilho de activity desligado.

A ancoragem importa: um `grep -o 'mop=[0-9]*'` solto também casa a cauda de `activity_has_mop=1` e
produz centenas de violações fantasmas. O padrão usado exige que `mop=` não seja precedido por
`[a-z_]`.

### 3.2 Portão 2 — jar correto (bloqueante) · **PASS**

Os 120 sidecars `*.provenance.json` do braço LLM trazem
`jar_sha256 = 386ce08d1846a4088755a8d755e5b70391af3b42add091d231dbcc52aed24e69`, idêntico ao
`expected_jar_sha256` declarado no manifesto do braço (`tool.py`). **120 iguais, 0 divergentes, 0
ausentes.**

Registro de uma imprecisão conhecida do documento congelado: o §2 ainda nomeia um banner
`[APE-BUILD]` que nunca existiu (`gh14-build-provenance-stamp` foi arquivado sem implementação). O
autor decidiu em 2026-08-01 não corrigir o texto congelado; o portão é satisfeito pelo sha256 do jar
instalado, que é evidência mais forte que um banner autodeclarado.

### 3.3 Portão 3 — atribuição de braço (bloqueante) · **PASS**

O nome do arquivo (`…__2__1800__aperv:mop_on_llm_off.trace`) identifica o braço, e é assim que os
runs são agrupados — mas ele é o **rótulo** que o orquestrador atribuiu, escrito pelo mesmo código que
deveria aplicar a configuração. Se a variante fosse resolvida errado, o rótulo continuaria dizendo o
esperado. A atribuição exige evidência do lado do jar.

Ela existe: o jar despeja `[APE] Configurations:` com todas as propriedades resolvidas, no relatório
final de cada run. Verificado nos 360:

| chave | referência | controle | LLM |
|---|---:|---:|---:|
| `ape.mopWeightDirect` | 500 | **0** | 500 |
| `ape.mopWeightTransitive` | 300 | **0** | 300 |
| `ape.mopWeightOpenMenu` | 250 | **0** | 250 |
| `ape.mopWeightWtg` | 200 | **0** | 200 |
| `ape.mopFrontierWeight` | 200 | **0** | 200 |
| `ape.activityTriggerEnabled` | true | **false** | true |
| `ape.frontierBoostWeight` | 200 | 200 | 200 |
| runs conformes | 119/119 | 120/120 | 120/120 |

São exatamente as seis chaves do `_MOP_OFF_OVERRIDES`. O `frontierBoostWeight` igual nos três é
desenho, não vazamento: o controle remove **guia MOP**, não navegação (INV-APV-30) — zerá-lo tornaria
o contraste "substrato completo contra quase nenhum substrato".

Os 119 do braço de referência são 120 menos o run morto descrito em §2.3, que não chegou a emitir o
bloco; sua re-execução emite.

Complementarmente, os 120 runs do braço LLM trazem `[APE-LLM-CONFIG]` conforme o manifesto
(`prompt_variant=v13`, `llm_percentage=0.7`, `temperature=0.0`, `top_p=0.6`, `top_k=50`,
`on_new_state=true`, `on_stagnation=true`), e os braços 1 e 2 não emitem nenhuma tag LLM.

### 3.4 Portão 4 — integridade de tasks · **PASS**

```
360 identidades distintas (apk, tool, variant, rep, timeout)
360 com pelo menos um COMPLETED · 0 perdidas
120 por braço × 3 braços · 40 APKs
363 linhas em tasks.json = 360 COMPLETED + 3 ERROR
```

As 3 linhas `ERROR` são as duas falhas transitórias e a réplica invalidada manualmente; todas têm uma
linha `COMPLETED` de mesma identidade. **A contagem correta aqui é por identidade, não por linha** —
um resume anexa uma task com `id` novo para a mesma identidade, então contar linhas daria 363. A
consolidação (`consolidate_cal.py`) deduplica pela mesma regra, preferindo o `COMPLETED` de maior
cobertura, e confirmou: `363 records -> 360 identities, 40 APKs, 3 arms`.

Nenhum run foi perdido e nenhum foi silenciosamente descartado.

---

## 4. Desfechos pré-registrados (§3)

### 4.1 Primário — detecção binária por APK, McNemar exato

Agregação declarada: o `achou` de um APK é decidido por **maioria — ao menos 2 das 3 réplicas com
`mop_unique > 0`**. União e unanimidade foram descartadas *a priori* por serem monótonas em R.

| contraste | ambos | só referência | só o outro | nenhum | n_disc | p (exato) | p (Holm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **RQ-C1** ref × controle | 30 | 0 | 0 | 10 | **0** | 1,0000 | 1,0000 |
| **RQ-C3** ref × LLM | 30 | 0 | 0 | 10 | **0** | 1,0000 | 1,0000 |

Nenhum contraste rejeita. Pelo critério de falsificação do §5, **C1 e C3 estão ambas falsificadas** na
forma declarada: a guia MOP não faz o sistema encontrar violação onde ele não encontrava, e o LLM
tampouco.

**As duas frases que o §5 exige que convivam.** Primeira: não rejeitou, e pela regra de empate a
conclusão é "o tratamento não acrescenta", não "inconclusivo" — não há reanálise, troca de desfecho
nem aumento de n em busca de significância. Segunda: **não tinha como rejeitar**. O §3 declarou antes
da corrida que com `n_discordante` < 7 o McNemar exato bicaudal não alcança a Holm α=0,025, porque o p
mínimo é 2·(0,5)ⁿ. Aqui `n_discordante = 0`, o caso extremo — não existe par discordante sobre o qual
o teste possa operar. Registrar o não-rejeitar sem registrar isto seria omitir o que a própria iter0
já previa (que estimava `n_disc ≈ 3–4`).

**Robustez à regra de agregação** (exploratória; união e unanimidade seguem rejeitadas e **não**
substituem o desfecho): apenas **4 de 120** células (APK, braço) têm réplicas mistas, de modo que a
regra de agregação é quase inerte neste conjunto.

| regra | RQ-C1 n_disc | RQ-C3 n_disc | p |
|---|---:|---:|---:|
| maioria ≥2/3 (declarada) | 0 | 0 | 1,0000 |
| união ≥1/3 (rejeitada a priori) | 1 | 2 | 1,0000 |
| unanimidade 3/3 (rejeitada a priori) | 1 | 2 | 1,0000 |

O nulo não é artefato da agregação escolhida.

**Estrutura do corpus por trás do nulo.** Dos 40 APKs, **8 dão zero em todas as 9 réplicas de todos os
braços** (`habitmaker`, `broccoli`, `vscan`, `greenstash`, `freebloks`, `canta`, `messages`,
`book_story`) — o mesmo número que a iter0 registrava. Outros 30 detectam em todos os braços. Os 2
restantes (`easynotes`, `freeotpplus`) detectaram em exatamente uma réplica e, pela maioria, contam
como não-detecção — em todos os braços, sem gerar discordância.

### 4.2 Secundário — Δ pareado de `mop_unique`, Wilcoxon

Agregação declarada: o `mop_unique` de um APK num braço é a **média das 3 réplicas** (convenção do
`per_apk_paired.csv` da iter0, mantida para comparabilidade).

| contraste | média ref. | média outro | pares Δ≠0 | Wilcoxon p | Δ médias aparadas (10%) | IC95 bootstrap |
|---|---:|---:|---:|---:|---:|---|
| RQ-C1 | 4,375 | 4,258 | 5/40 | 0,2249 | +0,083 | [0,000; 0,229] |
| RQ-C3 | 4,375 | 4,392 | 8/40 | 0,7794 | +0,042 | [−0,104; 0,188] |

Mediana do Δ pareado é **0** nos dois contrastes. Bootstrap pareado com B=10.000 e seed 42, a mesma
configuração da iter0.

Nenhum Δ negativo com IC excluindo zero: **não há evidência de que qualquer tratamento prejudique** o
desfecho contínuo, o que seria, pelo §5, resultado mais forte que o empate.

### 4.3 Terciário — `cov_mop` (suporte, não decide)

| braço | `cov_mop` médio |
|---|---:|
| referência | 51,53% |
| controle | 50,05% |
| LLM | 48,74% |

O terciário existe para distinguir "não alcançou" de "alcançou e não detectou". Os três braços
alcançam cerca de metade dos métodos que chegam aos sítios monitorados, e a diferença entre eles é de
poucos pontos. **O nulo não se explica por falta de alcance.**

---

## 5. Análises declaradas no §4

### 5.1 Estratificação por toolkit (descritiva)

Detector determinístico e offline, aplicado aos 40 `.apk.json`: o app é Compose quando
`androidx.compose.runtime.Composer` aparece em qualquer `reachability[].methods[].signature`.
Resultado: **22 Compose, 18 View** — exatamente a partição que a iter0 registrava.

| estrato | contraste | ambos | só ref. | só outro | nenhum | n_disc |
|---|---|---:|---:|---:|---:|---:|
| Compose (22) | RQ-C1 | 16 | 0 | 0 | 6 | 0 |
| Compose (22) | RQ-C3 | 16 | 0 | 0 | 6 | 0 |
| View (18) | RQ-C1 | 14 | 0 | 0 | 4 | 0 |
| View (18) | RQ-C3 | 14 | 0 | 0 | 4 | 0 |

O §4 previu **aproximadamente zero pares discordantes no estrato Compose**, e a previsão se
confirmou. O que ele não previu é que o estrato View — de onde a discordância deveria vir, já que na
iter0 os três discordantes do análogo de RQ-C3 eram todos View — também viesse zerado. Essa é a
diferença entre a previsão declarada e o observado, e fica registrada como tal.

### 5.2 Dependência entre unidades — os oito clones

O pareamento trata os 40 APKs como independentes, e oito não são: os seis `info.metadude.*.schedule`
mais `at.linuxtage.Eventfahrplan_1700028` e `ch.digitale_gesellschaft.winterkongress.schedule_118`
são uma base de código em oito empacotamentos (mesma `mainActivity`
`nerd.tuxmobil.fahrplan.congress.schedule.MainActivity`).

Colapsando os oito num único representante (n = 33):

| contraste | ambos | só ref. | só outro | nenhum | n_disc | p |
|---|---:|---:|---:|---:|---:|---:|
| RQ-C1 | 23 | 0 | 0 | 10 | 0 | 1,0000 |
| RQ-C3 | 23 | 0 | 0 | 10 | 0 | 1,0000 |

A dependência declarada **não sustenta o nulo**: ele sobrevive intacto ao colapso.

### 5.3 Normalização por passo

Declarada no §4 porque, neste substrato, o braço LLM é limitado por latência e não por seleção — e as
duas coisas são indistinguíveis no nível da corrida.

| braço | `mop_unique` médio | passos médios | `mop_unique` por passo |
|---|---:|---:|---:|
| referência | 4,375 | 1847,2 | 0,002369 |
| controle | 4,258 | 1909,3 | 0,002230 |
| LLM | 4,392 | **1049,7** | **0,004184** |

O braço LLM executa **0,568×** os passos da referência — a iter0, a 300 s, media 0,622×, então a
razão se manteve ao sextuplicar o orçamento. Chegando ao mesmo `mop_unique` com 43% menos passos, seu
rendimento **por passo** é **1,77×** o da referência.

A leitura correta disso é a que o §4 fixa: a razão por passo diz *por quê* o resultado por corrida é
plano — o LLM não seleciona pior, ele recebe menos oportunidades —, mas **não desloca o desfecho por
corrida**, que segue primário. Uma ferramenta que não consegue gastar seu relógio é pior na prática.

---

## 6. Métricas descritivas comparativas

**Estas métricas não são desfechos pré-registrados.** Os p-valores abaixo não têm correção de
multiplicidade e são exploratórios; entram para descrever o mecanismo, não para decidir.

### 6.1 Coberturas e violações

Médias por APK (média das 3 réplicas), n = 40:

| métrica | referência | controle | LLM |
|---|---:|---:|---:|
| `cov_method` (%) | 47,78 | 46,96 | 45,71 |
| `cov_act` (%) | **95,51** | **81,50** | 92,72 |
| `cov_mop` (%) | 51,53 | 50,05 | 48,74 |
| `mop_unique` | 4,375 | 4,258 | 4,392 |
| `mop_total` | 53,76 | 52,39 | **35,91** |
| `crashes` | 0,000 | 0,000 | 0,000 |

Δ pareado por APK (referência menos o outro braço), Wilcoxon e IC95 bootstrap:

| métrica | contraste | mediana Δ | pares Δ≠0 | p | Δ aparado | IC95 |
|---|---|---:|---:|---:|---:|---|
| `cov_method` | RQ-C1 | +0,473 | 40/40 | 0,1181 | +0,345 | [−0,889; 1,613] |
| `cov_method` | RQ-C3 | +1,877 | 40/40 | 0,0025 | +2,069 | [0,279; 3,916] |
| `cov_act` | RQ-C1 | 0,000 | 22/40 | **0,0002** | **+14,916** | **[7,754; 22,039]** |
| `cov_act` | RQ-C3 | 0,000 | 7/40 | 0,0280 | +2,083 | [−0,347; 5,465] |
| `cov_mop` | RQ-C1 | +0,468 | 37/40 | 0,0668 | +1,366 | [−0,291; 2,911] |
| `cov_mop` | RQ-C3 | +2,226 | 36/40 | 0,0045 | +2,097 | [−0,163; 4,850] |
| `mop_unique` | RQ-C1 | 0,000 | 5/40 | 0,2249 | +0,083 | [0,000; 0,229] |
| `mop_unique` | RQ-C3 | 0,000 | 8/40 | 0,7794 | +0,042 | [−0,104; 0,188] |
| `mop_total` | RQ-C1 | +0,167 | 31/40 | 0,5052 | +2,521 | [−2,135; 7,615] |
| `mop_total` | RQ-C3 | +10,000 | 31/40 | **0,0000** | **+16,115** | **[8,979; 24,011]** |
| `crashes` | ambos | 0,000 | 0/40 | 1,0000 | 0,000 | [0,000; 0,000] |

Três leituras se destacam, todas descritivas:

1. **A guia MOP funciona no mecanismo, e não no desfecho.** O maior efeito medido em toda a corrida é
   `cov_act` no RQ-C1: +14,9 pontos percentuais, IC95 [7,75; 22,04], com 22 dos 40 APKs mudando de
   valor. O braço guiado alcança quase todas as activities (95,5%) e o controle fica em 81,5%. Ainda
   assim, `mop_unique` é estatisticamente indistinguível entre os dois. O tratamento faz o que promete
   — leva o explorador a mais lugares — e isso não se converte em mais violações encontradas.
2. **O braço LLM produz muito menos violações totais pelo mesmo número de violações distintas.**
   `mop_total` cai de 53,8 para 35,9 (Δ +16,1, IC95 [8,98; 24,01]) enquanto `mop_unique` fica igual.
   Ele repete menos os mesmos sítios, o que é consistente com executar 43% menos passos.
3. **Zero crashes em todos os 360 runs**, nos três braços.

### 6.2 Rastreador de UI

Médias por run, agregadas sobre os 120 runs de cada braço:

| métrica | referência | controle | LLM |
|---|---:|---:|---:|
| passos | 1847,2 | 1909,3 | 1049,7 |
| decisões `[APE-OUTCOME]` | 1814,6 | 1886,3 | 1031,2 |
| estados novos | 57,9 | 62,7 | 48,2 |
| estados distintos | 65,8 | 69,7 | 55,3 |
| activities distintas | 6,0 | 5,4 | 5,3 |
| trocas de activity | 195,2 | 172,6 | 110,3 |
| passos em activity com MOP | 1475,0 | 1502,0 | 826,5 |
| widgets descobertos | 191,2 | 184,5 | 169,0 |
| widgets interagidos | 136,0 | 136,5 | 101,6 |
| `gap` médio (UICOV-ACT) | 0,2 | 0,2 | 0,3 |
| estados no `UICOV` | 67,1 | 70,4 | 56,6 |
| estados com `mopReach=1` | 47,0 | 48,0 | 40,4 |
| **taxa de estado novo** (%) | 3,19 | 3,32 | **4,67** |
| **interação/descoberta** (%) | 71,12 | 73,97 | **60,11** |

A taxa de estado novo por decisão é **maior** no braço LLM (4,67% contra 3,19%), e ainda assim ele
termina com **menos** estados distintos (55,3 contra 65,8): a vantagem por decisão não compensa
executar 43% menos decisões. É a mesma assimetria da §5.3, vista pelo lado da exploração em vez do
lado da detecção.

A razão interação/descoberta é a métrica em que o braço LLM fica claramente atrás (60,1% contra
71,1%): ele deixa proporcionalmente mais widgets descobertos sem tocar, o que também decorre do
orçamento de passos consumido por latência de inferência.

**Fontes de decisão** (contadas apenas nas linhas `[APE-OUTCOME]`, pois `decision_source` também
aparece em `[APE-STEP]` e somar as duas contaria cada decisão duas vezes):

| fonte | referência | controle | LLM |
|---|---:|---:|---:|
| `SATA` | 196.515 (90,2%) | 205.660 (90,9%) | 70.098 (56,7%) |
| `LLM` | 0 | 0 | **40.318 (32,6%)** |
| `Coverage` | 13.880 (6,4%) | 14.331 (6,3%) | 7.041 (5,7%) |
| `Budget` | 4.117 (1,9%) | 4.220 (1,9%) | 4.990 (4,0%) |
| `Form` | 1.434 (0,7%) | 1.538 (0,7%) | 547 (0,4%) |
| `MOP` | **921 (0,4%)** | **0 (0,0%)** | 463 (0,4%) |
| `WTG` | 854 (0,4%) | 612 (0,3%) | 257 (0,2%) |
| `Menu` | 27 (0,0%) | 0 (0,0%) | 24 (0,0%) |
| **total** | **217.748** | **226.361** | **123.738** |

Dois pontos merecem destaque. Primeiro, `MOP` responde por **0,4%** das decisões no braço guiado —
a guia MOP em nível de widget quase não dispara, o que dá contexto ao nulo do RQ-C1: o canal que o
contraste deveria medir é raro por construção neste substrato. Segundo, `LLM` responde por 32,6% das
decisões e não por 70%: a dose `llm_percentage=0.7` se aplica dentro dos gatilhos declarados
(`on_new_state`, `on_stagnation`), não a todo passo.

**O gatilho de activity, que é o mecanismo por trás do maior efeito medido.** A fonte `Component`
aparece somente nas linhas `[APE-STEP]` — não nas `[APE-OUTCOME]` —, e por isso não consta da tabela
acima. Contada nas linhas `[APE-STEP]` sobre os 120 runs de cada braço:

| | referência | controle | LLM |
|---|---:|---:|---:|
| decisões `Component` | **1.075** | **0** | 472 |
| passos com ação `EVENT_TRIGGER_ACTIVITY` | ~1.069 | **0** | ~468 |

No controle, a única ocorrência da string `EVENT_TRIGGER_ACTIVITY` em cada run é a linha de sumário
final `[APE]      0  EVENT_TRIGGER_ACTIVITY`, isto é, a contagem **zero** — o gatilho realmente nunca
disparou, como `ape.activityTriggerEnabled: false` determina. (A contagem bruta de 118 ocorrências no
braço controle é essa linha de sumário, uma por run, e não gatilhos.)

Este é o elo causal do achado da §6.1: `activity_trigger_enabled` é uma das seis chaves que separam
referência de controle, ele produz ~1.069 lançamentos diretos de activity no braço guiado contra zero
no controle, e é isso que leva `cov_act` de 81,5% para 95,5%. O tratamento age exatamente onde foi
projetado para agir — e o desfecho de detecção não se move.

**Ações por tipo** (interagidas/descobertas, agregado sobre os 120 runs de cada braço):

| ação | referência | controle | LLM |
|---|---|---|---|
| `MODEL_CLICK` | 10.973/15.430 (71%) | 11.097/15.045 (74%) | 8.270/13.394 (62%) |
| `MODEL_LONG_CLICK` | 1.866/2.922 (64%) | 1.820/2.828 (64%) | 1.196/2.657 (45%) |
| `MODEL_SCROLL_TOP_DOWN` | 702/921 (76%) | 693/896 (77%) | 500/830 (60%) |
| `MODEL_SCROLL_BOTTOM_UP` | 711/921 (77%) | 717/896 (80%) | 514/830 (62%) |
| `MODEL_BACK` | 607/760 (80%) | 585/657 (89%) | 491/685 (72%) |
| `MODEL_MENU` | 580/760 (76%) | 580/657 (88%) | 455/685 (66%) |
| `MODEL_SCROLL_RIGHT_LEFT` | 437/613 (71%) | 433/583 (74%) | 312/528 (59%) |
| `MODEL_SCROLL_LEFT_RIGHT` | 440/613 (72%) | 456/583 (78%) | 310/528 (59%) |
| `MODEL_LLM_TAP` | 0/0 | 0/0 | **140/140 (100%)** |

`MODEL_LLM_TAP` só existe no braço LLM: são os toques em coordenada que o LLM emitiu sem casar com
nenhum widget do modelo. São **140** em 120 runs — marginais diante das 40.318 decisões LLM, o que
indica que o mecanismo de *snap* para widget está resolvendo quase tudo.

---

## 7. Leitura, nos termos já declarados

### 7.1 O que a regra de decisão determina (§5)

- **RQ-C3 (LLM)** — empate ⇒ o LLM **sai do desenho**. É decisão de engenharia sobre ônus da prova e
  custo, não inferência estatística: o custo é certo e medido (43% menos passos por run, mais GPU e
  complexidade) e o benefício não foi demonstrado. Destrava a fila de itens adiados que dependiam dele
  (B8, B10-LLM, B7(ii)).
- **RQ-C1 (MOP)** — empate ⇒ registra-se **resultado negativo para a hipótese central** e reporta-se
  como tal. **Não** é decisão de remover o MOP: a tese é *sobre* ele. É a obrigação de reportar o
  negativo sem reprocessá-lo até virar positivo.

A regra de troca de desfecho por `n_disc ≤ 3` **caducou** junto com a sonda de poder do RQ-C1,
cancelada em 2026-08-01 sem ser executada, e não é invocada aqui.

### 7.2 A premissa que a corrida testou e refutou

O §6 declarava como premissa falsificável que o timeout de 1800 s existia porque se esperava que o
algoritmo estagnasse enquanto o LLM continuasse explorando, registrando que **não havia indicador
antecedente disso**. A corrida testou a premissa: a 1800 s o braço LLM continua executando 0,568× os
passos da referência, a mesma razão medida a 300 s. O sextuplicar do orçamento não inverteu nada.

O §6 também declarava, antes do resultado, qual seria a leitura honesta caso o binário viesse plano:
**neste corpus a exploração de GUI não é o gargalo da detecção de mau uso de JCA**. Os dados
sustentam essa leitura — 8 APKs dão zero em todas as 9 réplicas de todos os braços, 30 detectam em
todos os braços independentemente do que se ligue ou desligue, e o braço que alcança +14,9 pontos de
`cov_act` encontra exatamente as mesmas violações. É um resultado **sobre o corpus**, e é reportável.

### 7.3 O que este resultado não autoriza a concluir

- **Não** autoriza concluir que a guia MOP ou o LLM sejam inúteis em geral. O desenho não tinha poder
  para rejeitar (`n_discordante = 0`), e o próprio §3 previa `n_disc ≈ 3–4`. O que se afirma é que
  neste corpus, neste orçamento e neste desfecho, o benefício não apareceu.
- **Não** autoriza reanálise em busca de significância, troca de desfecho ou aumento de n — o §5
  proíbe explicitamente, e é para isso que o pré-registro existe.
- **Não** autoriza ler as métricas descritivas da §6 como testes de hipótese. Elas não têm correção de
  multiplicidade e não foram pré-registradas como desfechos.
- **Não** permite ler a comparação entre orçamentos (`cal_a1`@300 s contra o braço 3@1800 s) como
  interação dose × orçamento limpa: o §6 já declarava que os dois pontos diferem em orçamento **e** em
  caminho de LLM, por sete itens do jar da corrida decisiva que não existiam no jar da iter0. O
  contraste primário não é afetado, porque os braços 1 e 3 rodam no mesmo jar e são pareados por APK.

---

## 8. Procedência e reprodutibilidade

| artefato | localização |
|---|---|
| Resultados brutos (360 runs) | `experimento-e3-decisiva/results/` (7,7 G; gitignored) |
| Datasets consolidados | `experimento-e3-decisiva/per_apk_paired.csv`, `tel_proxies.csv` |
| stdout dos containers | `experimento-e3-decisiva/logs/` (48 M) |
| Réplica invalidada + `tasks.json` original | `backup/gh90-fossgis-rep1-invalida/` |
| Plano de análise congelado | `docs/20260730_preregistro_corrida_decisiva.md` |
| Registro dos congelamentos | `calibracao/journal.jsonl` |
| Definição dos braços | `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` |
| Compose do experimento | `experimento-e3-decisiva/docker-compose.yml` |

**Identidade do binário**: `ape-rv.jar` sha256 `386ce08d…d24e69`, git sha `5dcf2259…`. O build do
`ape` é bit-reproduzível — medido em 2026-08-01, o rebuild do mesmo commit no host e dentro da imagem
recém-construída produz o mesmo digest. (O design D4 afirma o contrário e está errado neste ponto.)

**Consolidação**: `experimento-cal/scripts/consolidate_cal.py --iter-dir experimento-e3-decisiva`,
que lê `mop_unique` de `tasks.json → result.coverage_metrics.total_errors` e `mop_total` das linhas
`RVSEC` dos logcats, deduplicando por identidade (INV-CAL-07, INV-CAL-08).

**Estatística**: McNemar exato via `scipy.stats.binomtest` sobre os pares discordantes; Holm sobre os
dois contrastes; Wilcoxon de postos sinalizados via `scipy.stats.wilcoxon`; IC95 por
`stats_utils.paired_bootstrap_ci` com B=10.000 e seed 42 (diferença de médias aparadas a 10%, a mesma
configuração da iter0).

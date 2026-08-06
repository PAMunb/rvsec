# Resultados — portão empírico da re-arquitetura do APE-RV

**Data**: 2026-08-06 · **Change**: `openspec/changes/gh97-rearch-ab-gate/` · **Issue**: #97
**Plano congelado**: `docs/20260804_preregistro_gate_rearch.md` (emendas 01 e 02)
**Pernas**: A = `experimento-e3-decisiva/` (2026-08-01/02) · B = `experimento-rearch-aperv/` (2026-08-05/06)

Este documento reporta o que a campanha mediu e o que esse resultado sustenta. Ele tem duas partes
que não devem ser confundidas: a **leitura confirmatória**, que aplica as três regras congeladas em
2026-08-04 e nada além delas; e a **investigação posterior**, inteiramente exploratória por
definição, porque toda ela foi concebida depois de o resultado existir. A recomendação da §6 é uma
recomendação. O veredito de merge é do dono e vive na tarefa 10.4.

---

## 1. As premissas declaradas, restatadas

Vale a pena repetir o que o portão prometeu medir, porque parte da conclusão depende de o leitor
lembrar disso.

**Isto é um antes/depois, não um teste A/B.** Não houve atribuição concorrente nem aleatória de
aplicações às pernas. A perna A é um experimento terminado; a perna B roda quatro dias depois, em
outra imagem e outro jar. O pareamento é por aplicação entre duas campanhas separadas no tempo.

**Os três braços são o mesmo APE-RV com coisas diferentes ligadas.** O controle
(`mop_off_llm_off`) zera os cinco pesos MOP e desliga o gatilho de atividade; é o instrumento, não a
configuração fraca. A referência (`mop_on_llm_off`) liga a guia; o braço LLM soma a dose de decisão
por LLM.

**As três regras.** **G1** (bloqueante) compara perna B contra perna A no braço de controle,
pareado por aplicação (n=40). **G2** (bloqueante) exige que o contraste interno
`mop_on_llm_off − mop_off_llm_off` em `cov_act` continue positivo com IC excluindo zero. **G3**
(descritiva) reporta os níveis de operações monitoradas ao lado do deslocamento esperado do
substrato.

**O estimando é a diferença de médias aparadas a 10 %**, com bootstrap pareado por aplicação
(`stats_utils.paired_bootstrap_ci`, B = 10.000, seed 42, pares completos). **Não é a média.** É por
isso que `cov_method` sai −1,011 onde a média simples dá −0,771. Os dois estão certos e estimam
coisas diferentes; misturá-los numa coluna é erro.

**Um confundidor era estrutural e foi declarado antes.** A `gh96` mudou de propósito a semântica do
substrato de operações monitoradas. Comparar níveis de `cov_mop`, `mop_unique` ou `mop_total` entre
campanhas mede a reescrita **somada** à mudança intencional. O G1 contorna isso pela escolha do
braço, não por ajuste posterior.

---

## 2. O resultado medido

`scripts/compare.py`, executado em 2026-08-06, saída 0:
**`no blocking finding: the gate does not oppose the merge`.**

### 2.1 G1 (bloqueante) — braço de controle, perna B − perna A, n=40

| desfecho | Δ | IC95 | margem | leitura |
|---|---:|---|---:|---|
| `cov_method` | −1,011 | [−1,769; −0,190] | 1,92 | IC nocivo, **dentro** da margem |
| `cov_act` | −0,412 | [−2,023; +1,275] | 1,50 | sem achado bloqueante |
| `cov_mop` | −1,026 | [−2,038; −0,008] | 2,09 | IC nocivo, **dentro** da margem |
| `mop_unique` | +0,010 | [−0,052; +0,094] | — | descritivo |
| `mop_total` | −2,042 | [−5,615; +1,448] | — | descritivo |
| `crashes` | 0,000 | [0,000; 0,000] | — | exatamente zero, 40 apps, ambas as pernas |

Duas margens tocadas, nenhuma cruzada.

### 2.2 G2 (bloqueante, unilateral) — PASSA

`mop_on_llm_off − mop_off_llm_off` em `cov_act`, dentro da perna B: **+15,415** [8,506; 22,212],
n=40, contra os **+14,916** [7,754; 22,039] da perna A. O intervalo de cada perna contém a
estimativa pontual da outra. **É o resultado mais forte do conjunto: a guia continua guiando, tanto
quanto guiava antes da reescrita.**

### 2.3 G3 (descritiva)

Deslocamento declarado sobre o corpus: 104 → 159 widgets sinalizados, 38 → 49 atividades,
concentrado em 4 das 40 aplicações.

| braço | `cov_mop` | `mop_unique` | `mop_total` |
|---|---|---|---|
| `mop_on_llm_off` | +0,355 [−0,932; +2,429] | +0,052 [0,000; +0,177] | +1,281 [−2,458; +5,000] |
| `mop_on_llm_70` | −1,539 [−3,955; +0,266] | +0,010 [−0,073; +0,104] | +3,979 [−1,750; +13,448] |

Todo intervalo cruza zero. O limite inferior de `mop_unique` na referência é **exatamente 0,0** em
precisão plena — a impressão `[+0.000, +0.177]` está arredondada a 4 casas. **Não há braço em que a
detecção de operações monitoradas tenha melhorado de forma mensurável.** A afirmação honesta é a
negativa: não piorou em lugar nenhum.

---

## 3. A campanha executou como devia?

Sete portões de validade já passavam. A investigação foi além deles e não encontrou nada que
invalide o conjunto.

**As sete falhas de instalação estão certas.** As 36–54 ocorrências de `adb: device offline` por
container são **uma por partida de emulador** (a segunda sonda de boot, cinco segundos depois do
`device not found`) **mais oito linhas por falha de instalação**. As UUIDs de tarefa distintas que
falharam na instalação são exatamente sete. `boots == tarefas` em todo container.

**370 execuções, 369 registros, 360 identidades.** As nove recuperações são sete falhas de
instalação e dois runs truncados. A execução restante é um resume abortado no container 07
(`a97735d8`, iniciado 10:37, morto por volta dos seis minutos quando o processo da plataforma foi
reiniciado). Não deixou registro **nem contaminou artefato**: o traço da identidade tem exatamente um
`RUN_START` e um `RUN_END`, e o logcat cobre 10:44→11:14, uma janela única de trinta minutos. Os 360
traços da perna B têm um `RUN_START` cada.

**A linha de base não está contaminada.** Aplicando retroativamente à perna A o critério de
integridade que a emenda 02 introduziu (INV-APV-60: retorno fora de timeout mais de 45 s abaixo do
orçamento), **zero das 360 identidades da perna A** ficam abaixo do piso — duração mínima 1857 s
contra 1859 s na perna B. O defeito descoberto na perna B não existe na perna A. A perna A tem três
registros `ERROR` próprios (duas falhas de partida de emulador e uma invalidação manual de
2026-08-02), todos sucedidos por um `COMPLETED`.

**As nove identidades recuperadas não destoam.** Normalizando dentro da própria célula
aplicação × braço, elas ficam em z = +0,044 em passos e −0,029 em assinaturas de cobertura
distintas, contra ≈ 0,000 das irmãs. Um run retomado começa em emulador novo e isso não enviesou nada.

**Uma anomalia é correlacionada com braço.** Marcadores de ANR e de aplicação não-responsiva
**dobram no braço LLM** da perna B (152 → 315 e 114 → 255; permutação p = 0,022 e p = 0,016),
enquanto controle e referência não mostram efeito (p ≥ 0,43). Ver §5.4.

---

## 4. As duas pernas são comparáveis?

**São, com uma ressalva que precisa ser dita.**

**O jar é uniforme e o corpus é o mesmo.** `build.sha = 9e948102` (build de 2026-08-05T17:22Z) nos
**360** runs da perna B; `corpus_basis` idêntico nos 360; `preset` conforme o braço; um
`props_digest` distinto por braço, como esperado. As 360 seeds são distintas — não há determinismo
semeado.

**Os binários instrumentados são literalmente os mesmos.** As duas pernas montam o mesmo diretório
do hospedeiro em modo somente-leitura
(`APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706_selected181`), com
`RV_SKIP_MONITORS`/`RV_SKIP_INSTRUMENT`/`RV_SKIP_STATIC_ANALYSIS` ligados nas duas.

**A régua de medição é idêntica.** O denominador de `cov_method` — o universo de métodos alcançáveis
que vem da análise estática — é **igual nas 40 aplicações**, aplicação por aplicação (universo total
251.173 métodos; a primeira app registra 1498 classes e 7706 métodos em ambas as pernas). O
`coverage.csv` lista só métodos cobertos, então divergência de linhas ali é cobertura, não régua.

**O substrato é idêntico onde não devia mudar.** `windows` (682) e `widgets` (6834) batem aplicação
por aplicação entre as pernas. O que muda é `flagged` (104 → 159) em **4** aplicações — aegis 47→50,
owncloud 10→11, smartpack 0→10, de.blau 1→42 — e `mopActsAugmented`, que **cai** de 214 para 204
(smartpack 8→2, de.blau 27→23). Para 36 das 40 aplicações, o controle da perna B difere do da perna A
apenas pelo jar.

**Não há efeito de container.** A emenda 01 sacrificou o pareamento de container (perna A 8×5, perna
B 10×4). Regredindo cobertura sobre o índice de container dentro da perna B, nenhuma correlação é
distinguível de zero (a maior é `Δcov_mop` na referência, r = +0,295, p = 0,058). O sacrifício saiu
barato. **A ressalva vale ser dita mais alto**: o Δ médio por container tem desvio-padrão de 0,77 a
2,95 pp conforme a métrica — a mesma ordem de grandeza das margens do G1. Não é viés detectável, mas
é ruído não modelado que mora dentro da margem.

### 4.1 A ressalva: as pernas não diferem só pelo jar

A imagem da perna A é `phtcosta/rvandroid:0.9.3` (construída 2026-08-01T11:47:43-03) e a da perna B é
`phtcosta/rvandroid:0.9.3-rearch` (2026-08-05T14:39:39-03). Compartilham 24 das 28 camadas e têm
ambiente idêntico, mas foram construídas de **branches diferentes do lado Python**: `modules` e
`rearch-counterparts`.

No commit em que a imagem da perna B foi construída (`7173c15d`), a diferença de código-fonte Python
entre as branches é de **sete arquivos**: quatro no `aperv-tool` (`tool.py` reescrito,
`derive_mop_artifact.py` e `trace_ndjson.py` novos, `clock_logcat_join.py`), dois no
`rv-android-core` (`logcat_manager.py`, `logging/constants.py`) e um no `rv-coverage`
(`parser/log/diagnostic_parser.py`). **O `logcat_parser.py`, que é quem calcula cobertura, está
intacto.**

Isto não invalida o G1 — o que o portão compara é a re-arquitetura, e as contrapartes Python fazem
parte dela. Mas corrige a formulação de que "o `build.sha` é o único discriminador entre as pernas
dentro do container": é o único discriminador entre os **dois jars**, não entre as duas pernas.

---

## 5. Os deltas medidos têm mecanismo?

Procurei quatro mecanismos para o −1,011 pp de `cov_method`. Três estão refutados por medição direta,
e o quarto não é o que parecia.

### 5.1 Vazão — refutada como canal

A perna B executa **menos passos de exploração** no mesmo orçamento de 1800 s, e isso é robusto:

| braço | passos, perna A | perna B | Δ (aparado, IC95) | mediana relativa | apps com queda |
|---|---:|---:|---|---:|---:|
| controle | 1909,3 | 1787,1 | **−130,2 [−191,4; −72,2]** | −4,52 % | 32/40 |
| referência | 1847,2 | 1776,0 | **−68,3 [−113,3; −25,8]** | −4,49 % | 30/40 |
| LLM | 1049,7 | 961,7 | **−91,7 [−115,3; −67,0]** | −8,29 % | 35/40 |

(O contador de passos foi validado: o número de linhas `>>>>>>>> SATA begin step` bate **exatamente**
com `RUN_END.steps` nos 360 runs da perna B, e é o único marcador de passo presente nos dois formatos
de traço.)

**Mas a perda de passos não é por onde a cobertura foi embora.** `corr(Δpassos, Δcov_method)` no
controle é **+0,005** (Pearson) e +0,104 (Spearman). Dentro de cada perna, a correlação entre passos
e cobertura **entre aplicações** também é nula (−0,119 a +0,152). As duas aplicações que mais
perderam passos (owncloud −575, nextcloudpasswords −562) têm Δcobertura ≈ 0; a que mais perdeu
cobertura (osmfocus, −5,68 pp) **ganhou** 182 passos. Aos trinta minutos a exploração não é limitada
por passos, e uma queda de vazão de 4–8 % não se converte em cobertura.

O **mix de decisões é preservado**: `EPSILON_GREEDY` ≈ 59 % dos passos nas duas pernas,
`EARLY_STAGE` ≈ 34 %, e as demais razões escalam com a contagem de passos. A reescrita mudou a
vazão, não o perfil de comportamento.

### 5.2 Captura de logcat — refutada

A perna B admitiu um **terceiro tag** no filtro estrito do dispositivo: `ApeRvHb`, o heartbeat que o
jar escreve uma linha por passo (`-s RVSEC:V RVSEC-COV:V ApeRvHb:V` contra os dois tags da perna A;
as duas pernas somam ainda os quatro `DIAGNOSTIC_TAGS`). Como o logcat é um buffer em anel, mais
tráfego admitido poderia despejar marcadores `RVSEC-COV` antes de o `adb` drená-los — e marcador
perdido é **cobertura medida a menos, sem regressão de comportamento nenhuma**.

O heartbeat numera os passos, então a perda é contável diretamente: **4 linhas ausentes em 542.963
heartbeats** ao longo dos 360 runs (0,001 %, em 4 runs). O buffer não está descartando nada. E os
marcadores capturados por run nem caem na perna B: assinaturas distintas de `RVSEC-COV` vão de 5.123
para 5.056 no controle, mas de 5.148 para 5.212 na referência e o volume bruto sobe 10 % no braço
LLM. Hipótese refutada.

### 5.3 Régua e substrato — refutados

Ver §4: denominador idêntico nas 40 aplicações, binários idênticos, substrato idêntico em 36 das 40.

### 5.4 O que sobra: a diferença está no limite do ruído, e não é específica do controle

**O piso de ruído.** O desvio-padrão de `cov_method` **entre as três repetições da mesma célula** tem
mediana de 1,75 a 2,12 pp conforme o braço (intervalo interquartil até ≈ 3,9). O sinal procurado é de
1 pp.

**Teste de permutação.** Trocando o rótulo da perna **dentro de cada aplicação** — o que a hipótese
nula do pareamento autoriza — e recomputando o estimando do portão 10.000 vezes:

| métrica | braço | observado | p bilateral | banda nula 95 % |
|---|---|---:|---:|---|
| `cov_method` | controle | −1,011 | **0,0279** | [−0,907; +0,906] — fora |
| `cov_mop` | controle | −1,026 | 0,1174 | [−1,294; +1,264] — **dentro** |
| `cov_act` | controle | −0,412 | 0,6640 | [−1,767; +1,799] |
| `cov_method` | referência | +0,446 | 0,3510 | [−0,953; +0,937] |
| `cov_method` | LLM | −0,272 | 0,5561 | [−0,899; +0,887] |

**O `cov_mop` do controle não é distinguível do ruído**, apesar de o IC bootstrap excluir zero por
−0,008. O `cov_method` do controle é, mas com p = 0,0279 — que **não sobrevive a Holm** nem na
família de três métricas do mesmo braço (limiar 0,0167), e o G1 relata seis desfechos.

**O custo não é específico do controle.** A diferença-de-diferenças entre braços:

| contraste (`cov_method`) | Δ | IC95 |
|---|---:|---|
| controle − referência | −0,547 | [−1,548; +0,627] |
| controle − LLM | −0,278 | [−1,375; +0,891] |
| média dos três braços, B − A | −0,251 | [−0,908; +0,367] |

Nenhum separa os braços. E em **médias simples** o braço LLM perdeu mais que o controle (−0,821
contra −0,771); é a referência que destoa (−0,132). A inversão que faz o controle parecer o único
braço afetado vem do aparamento a 10 % interagindo com a cauda, não dos dados. *A diferença entre
"significativo" e "não significativo" não é, ela mesma, significativa.*

**A perda não se concentra nas mesmas aplicações entre braços**: 25/40 perdem no controle, 22/40 na
referência, 26/40 no LLM, e apenas **9 perdem nos três** — contra 8,9 esperadas por acaso sob
independência. É o padrão de ruído de exploração, não de um efeito do arcabouço ou do corpus.

### 5.5 Uma anomalia real, de outro tipo

No braço LLM da perna B, a latência por chamada subiu **10 %** (1023 → 1123 ms) com o **mesmo volume
de tokens por chamada** (≈ 1316 de entrada, ≈ 26 de saída), no mesmo processo SGLang que serviu as
duas pernas. O tempo total de LLM é praticamente igual (71,9 M ms contra 71,6 M ms) para 9,4 % menos
chamadas. Isso é carga do servidor, não o jar — e é coerente com o excesso de ANR desse braço (§3).
É a explicação mais provável para o braço LLM ter perdido mais passos que os outros (−8,3 %).

---

## 6. Validade inferencial: o corpus tem clones

Este é o achado que mais mexe com o portão, e ele não é sobre a reescrita.

**Sete dos 40 APKs são o mesmo aplicativo.** Declaram o pacote idêntico
`info.metadude.android.congress.schedule.debug`, com estrutura idêntica (9 janelas, 7 widgets, 9
atividades MOP) e o mesmo universo de métodos (9443 em seis deles; 9380 no sétimo):
`ch.digitale_gesellschaft.winterkongress`, `info.metadude.android.{clt, datenspuren, fosdem, fossgis,
gpn, protocolberg}`. São sete builds do mesmo código-base para conferências diferentes.
(`at.linuxtage.Eventfahrplan` é a mesma família Fahrplan sob outro pacote.)

O bootstrap pareado reamostra **aplicações**, e trata essas sete como sete sorteios independentes.
Não são um. Isso **estreita todos os intervalos** do portão e dá peso sétuplo a qualquer efeito que a
família carregue. Colapsando as sete numa única linha (média), com n = 34:

| contraste | como está (n=40) | clones colapsados (n=34) |
|---|---|---|
| controle `cov_method` | −1,011 [−1,769; −0,189] * | −0,863 [−1,815; −0,142] * |
| controle **`cov_mop`** | −1,026 [−2,038; −0,008] * | **−0,824 [−2,158; +0,118]** |
| controle `cov_act` | −0,412 [−2,023; +1,275] | +0,039 [−1,337; +1,645] |
| **G2, perna B** | +15,415 [+8,506; +22,212] * | **+17,745 [+10,338; +25,384] *** |
| G2, perna A | +14,916 [+7,754; +22,039] * | +17,916 [+10,104; +25,619] * |

Duas consequências, em direções opostas:

1. **Uma das duas "margens tocadas" desaparece.** O `cov_mop` do controle deixa de excluir zero. Duas
   análises independentes — permutação (§5.4) e colapso de clones — concordam que não é achado.
2. **O G2 sai reforçado**, não enfraquecido: +17,7 pp com IC ainda longe de zero. O resultado mais
   importante do conjunto é robusto ao problema.

O `cov_method` do controle sobrevive aos dois testes, e continua sem sobreviver à multiplicidade.

---

## 7. G3 e o corpus (exploratório)

A observação devida pela tarefa 10.3 está medida: **o substrato é estruturalmente ausente na maior
parte do corpus.** `flagged > 0` em 8 das 40 aplicações, `wtgEdges > 0` em 15, e os três
(`flagged`, `wtg`, `mopActivities`) juntos em apenas **4**:
`com.rastislavkish.vscan`, `com.smartpack.packagemanager`, `org.cry.otp`, `org.liberty.android.freeotpplus`.

Restringindo o contraste do G3 a esses subgrupos — **exploratório e de subgrupo, nunca a ser
apresentado como G3**:

| subgrupo | braço | `cov_mop` | `mop_total` |
|---|---|---|---|
| `flagged>0` (n=8) | referência | −1,140 [−3,534; +1,186] | −5,542 [−16,667; +1,042] |
| `flagged>0` (n=8) | LLM | −3,563 [−12,510; +1,859] | −0,042 [−3,458; +4,750] |
| `wtg>0` (n=15) | referência | −0,752 [−3,142; +1,795] | +2,846 [−1,128; +6,462] |
| `wtg>0` (n=15) | LLM | −2,360 [−8,250; +1,522] | −0,923 [−4,923; +1,282] |

Tudo cruza zero, e **onde o substrato de fato mudou os pontos ficam negativos**. O único intervalo
que exclui zero é `mop_total` da referência no subgrupo de 4 (+1,333 [+0,250; +2,917]) — um bootstrap
sobre quatro itens, sem valor inferencial, registrado só para não parecer omitido.

**O `mop_total` +3,979 do braço LLM, o intervalo mais largo do conjunto, é artefato dos clones**: a
soma dos Δ por aplicação é +325,0, e **as duas maiores contribuições somam +180,7 (56 %)** —
datenspuren (55,0 → 154,7) e clt (82,7 → 163,7). As seis maiores contribuições são todas da família
de clones.

---

## 8. Braço LLM

- **A dose observada é ~56 % dos passos, não 70 %**, e é igual nas duas pernas (mediana 57,9 % na
  perna A, 56,6 % na B). Não é defeito da perna B, mas a expressão "dose de 70 %" não descreve o que
  se mede. Adotada a proposta do LLM, a fração de passos cuja decisão sai por `src=LLM` é menor ainda.
- **Taxa de match** 50,7 % → 53,7 %; `no_match` 41,4 % → 38,1 %, com a decomposição praticamente
  inalterada (`boundary` 14,8 % → 12,9 % dos `no_match`, `other` 85,2 % → 87,1 %, `degenerate`
  essencialmente ausente nas duas).
- **`tel_proxies.llm_tap` não é comparável entre pernas.** Nos traços da perna B o resultado
  `llm_tap` aparece 5.208 vezes, mas o CSV registra 39.469 (perna A: 5.501). O contador mudou de
  semântica na reescrita; as demais colunas conferem (o `matched` do CSV bate exatamente com a
  contagem por traço, 34.261).

### 8.1 Dois defeitos abertos, quantificados nesta campanha

**`type_text` nunca digita.** O prompt do sistema oferece `type_text` nos três modos. O LLM propôs
`type_text` **1.198 vezes**; das 1.066 que viraram passo com `src=LLM`, **1.051 executaram
`MODEL_CLICK`** e **15 executaram `MODEL_LONG_CLICK`**. Nenhuma digitou. O defeito registrado
("`type_text` executa `MODEL_LONG_CLICK`", 28 de 1.233 respostas) é a ponta visível de um problema
maior: a ação degenera em clique em 100 % dos casos. Sítios apontados anteriormente:
`LlmRouter.java:689` e `:807`. Sem issue aberta.

**90,6 % das respostas do LLM chegam malformadas e são reparadas.** Dos 63.813 chamados, 57.828
carregam um marcador de reparo: `missing_y` 43.404 (68,0 % de todas as chamadas), `quoted_xy` 12.216,
`array_xy` 1.420, `int_scan` 788. O modelo emite coisas como `{"x": 727, 70}` e o parser conserta.
Os "100 % de sucesso" do tool calling híbrido são o reparo funcionando, não o modelo acertando o
contrato.

**`long_click` é oferecido e jamais proposto** — 0 de 63.813 chamadas.

**Resíduo A8 reproduzido: 74.** Linhas `[APE-STEP]` da perna A partidas por uma quebra crua, contadas
como linhas sem o campo `decision_source=`: **74 de 576.739** (0,0128 %). Confere exatamente com a
contagem registrada. O formato NDJSON da perna B não carrega o defeito.

---

## 9. Leitura: o que este resultado sustenta

**Sustenta:**

1. **A guia continua guiando.** G2 passa com folga em ambas as pernas e **fica mais forte** quando os
   clones do corpus são colapsados (+17,7 [+10,3; +25,4]). É o achado mais sólido da campanha.
2. **Nada quebrou.** Zero crashes em 40 aplicações nas duas pernas. Erros de operação monitorada
   estáticos em todo braço. Nenhuma métrica piorou de forma que sobreviva a escrutínio.
3. **A campanha é sadia.** 360/360 identidades admissíveis, linha de base não contaminada, sem viés
   de resume, sem efeito de container, mesma régua, mesmos binários, mesmo substrato em 36 das 40.
4. **A reescrita custa vazão**: 4–8 % menos passos por run, em todos os braços, com IC excluindo
   zero. Isso é real e vale registrar — mas não se converte em cobertura no orçamento de 1800 s.

**Não sustenta:**

1. **"O custo é de ~1 pp e cai no braço de controle."** O `cov_mop` cai fora ao colapsar clones e ao
   permutar. O `cov_method` sobrevive aos dois, mas não à correção de multiplicidade, e a
   diferença-de-diferenças não separa os braços — em médias simples o braço LLM perde mais que o
   controle. A formulação defensável é mais fraca: *há indício de uma perda pequena e geral de
   cobertura de métodos na perna B, da ordem de meio ponto percentual, no limite do que esta
   campanha resolve, sem mecanismo identificado e sem localização por braço.*
2. **Um mecanismo para essa perda.** Vazão, captura de logcat, régua de medição e substrato foram
   testados e refutados por medição direta. Ou o mecanismo é sutil demais para este desenho, ou não
   há efeito a explicar.
3. **Melhora de detecção.** Nenhum braço melhora `mop_unique` de forma mensurável, e onde o substrato
   de fato mudou (8 aplicações) as estimativas pontuais são negativas.

**Não se pode dizer, com esta campanha:** se `cov_act` poderia ter melhorado — a métrica tem
**desvio-padrão exatamente zero entre repetições** em toda célula, e mediana 100,0 nos dois braços
guiados. Uma métrica no teto não pode mostrar melhora, e isso limita o que o G1 conseguiria detectar.
(Os empates não vêm de determinismo semeado: a perna B tem 360 seeds distintas.)

---

## 10. Recomendação

**A recomendação é fazer o merge.** O portão não se opõe, e o escrutínio da §5 e da §6 **fortaleceu**
a leitura em vez de enfraquecê-la: o achado bloqueante que passou (G2) ficou mais forte, e as duas
margens tocadas encolheram para uma, que por sua vez não sobrevive à multiplicidade. Não existe
resultado nesta campanha que se oponha ao merge, e existe um que o apoia diretamente.

**Com três ressalvas que devem viajar junto com a decisão:**

1. **O corpus tem sete clones em 40.** Isso afeta esta campanha, a perna A e qualquer campanha futura
   que use `calibracao/subset40.txt`. Não invalida nada aqui, mas todo IC produzido sobre esse corpus
   é mais estreito do que deveria ser. Merece uma decisão própria, fora desta change.
2. **A vazão caiu 4–8 %.** É real, mede-se com IC, e não teve custo observável em cobertura a 1800 s.
   Em orçamento menor poderia ter.
3. **Três defeitos abertos no braço LLM** (§8.1), nenhum introduzido por esta reescrita, nenhum com
   issue.

**O veredito de merge não é registrado aqui.** É do dono, e vive na tarefa 10.4 junto com a entrada
`DECIDE` em `calibracao/journal.jsonl`.

---

## 11. Registro exploratório

Tudo abaixo foi concebido **depois** de o resultado existir e é exploratório por definição. Nada
aqui altera margem, braço ou regra de decisão do plano congelado em 2026-08-04. A lista completa,
com o que cada análise mediu, está na tarefa 10.3 de
`openspec/changes/gh97-rearch-ab-gate/tasks.md`.

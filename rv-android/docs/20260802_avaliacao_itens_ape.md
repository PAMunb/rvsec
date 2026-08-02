# Avaliação dos itens de eficácia do ape na corrida decisiva (2026-08-02)

**Contexto.** A change irmã `telemetry-proof-llm-efficacy` (repo `ape`, issue #16) embarcou sete
itens que alteram o comportamento do braço LLM, cada um justificado por um número medido em corpus
de 300 s (calibração `cal_a1`). A corrida decisiva E3 (gh90, issue #90) produziu 120 runs LLM de
1800 s com telemetria completa — a primeira oportunidade de confrontar cada claim com dados na
escala e no horizonte reais. Este documento responde, item a item: **funcionou como projetado? Qual
a evidência, e onde ela não alcança?**

**O que este documento não é.** Nada aqui é desfecho pré-registrado, nada carrega correção de
multiplicidade, e nada relitiga o nulo dos dois contrastes pré-registrados — aquele resultado está
fechado em `docs/20260802_resultados_corrida_decisiva.md` e permanece como está. A pergunta deste
documento é outra: o relatório diz que o tratamento não moveu o desfecho; aqui se pergunta se o
tratamento *entregou o mecanismo* que foi construído para entregar. As duas respostas são
independentes, e mantê-las separadas é o que permite ler o nulo corretamente (§8).

## 1. Dados e método

- **120 traces do braço LLM** (`mop_on_llm_70`), identificados pelos registros COMPLETED dos
  `tasks.json` da campanha (nunca pelo nome do arquivo). Os caminhos de logcat dos registros são
  relativos ao container; o mapeamento local é
  `results/e3_decisiva_NN/e3_decisiva_NN/<apk>/<arquivo>.trace`.
- As linhas `[APE-LLM-TEL]`, `[APE-LLM-RESPONSE]`, `[APE-LLM-CONFIG]` e o dump `Configurations:`
  vivem no **`.trace`**, não no `.logcat` (mesma armadilha já paga com `[DM]`).
- **`experimento-e3-decisiva/logs/sglang.stdout.log`** (31 MB), stdout completo do servidor SGLang
  da campanha.
- Três passes de scan (scripts no scratchpad da sessão, descartáveis): (i) agregação das linhas
  `[APE-LLM-TEL]`/`[APE-LLM-RESPONSE]` dos 120 traces; (ii) `[APE-STEP]`/`[APE-OUTCOME]` e a linha
  `LLM Summary` do router; (iii) gates (c)–(f) da tarefa 17.4 sobre os 360 traces.

**Sanidade — as fontes fecham entre si.** Linhas `[APE-LLM-TEL]`: 70.212. Soma de `calls` das
linhas `LLM Summary` dos 120 runs: 70.313 (= soma da coluna `calls` de `tel_proxies.csv`). A
diferença de 101 é explicada **exatamente** pelos contadores de erro do próprio router:
`screenshot_failed` 98 + `parse_error` 2 + `timeout` 1 — chamadas que não chegam a emitir TEL.
Decisões LLM com outcome (`[APE-OUTCOME] decision_source=LLM`): 40.318, idêntico ao relatório.
O "pointer" de um trace citado no hand-off (441 chamadas, 308 matched) é o run
`at.linuxtage.Eventfahrplan` rep 1 — sua linha `LLM Summary` confere campo a campo.

## 2. Síntese — claim contra observado

| item | claim declarado (pré-registro §6 / design do ape) | observado a 1800 s (120 runs) | veredicto |
|---|---|---|---|
| **B1** ban de par morto, k=5 | recusa 27,5% das decisões (teto <30%); rendimento/decisão ≈11,4% → ≈14,7% | dispara em **120/120** runs (24.799 recusas); recusa **35,3%** das chamadas (37,6% das executáveis) — **teto violado**; rendimento realizado **6,6%** | mecanismo funciona; premissa quantitativa não se sustenta no horizonte real |
| **B6(i)** `click` restrito a `MODEL_CLICK` | pré-fix o click executava CLICK só 80,9% | **99,92%** (35.147/35.175; resíduo: 28 `MODEL_LONG_CLICK`) | atingiu o alvo |
| **B6(iii)** schema de tools por requisição | (sem número; coerência schema↔prompt) | via nativa de tool call segue minoritária: **22,3%**; 77,7% caem no fallback XML | sem efeito mensurável sobre a malformação; o repair é quem carrega (§5) |
| **B6(iv)** `fixTextEdit` | pré-fix `type_text` ≈ 0 (colapso) | **1.233** chamadas `type_text`, **91,1%** matched, 0 `dead_pair` (isenção ativa) | atingiu o alvo |
| **N1** identificadores no prompt | acerto 33,1% sem → 71,4% com | **78,4%** de acerto sobre tentativas (matched/(matched+boundary+llm_tap)) | atingiu o alvo (com ressalva de protocolo) |
| **B4** snap por borda, piso 150 px | (sem número) | `ape.llmSnapTolerancePx: 150` em 120/120 configs; **21,9%** dos matches a 50–150 px | ativo e fazendo trabalho; sem contrafactual |
| **B7(i)** gatilho de estagnação | "passa a disparar" (antes: nunca) | **131** disparos em **55/120** runs (0,19% das chamadas) | dispara; volume marginal |

Cinco dos sete itens atingiram o alvo declarado. As duas exceções são o B1 (funciona, mas fora da
premissa que escolheu k=5 — §3) e o B6(iii) (o problema que ele mirava não era dele para resolver —
§5).

## 3. B1 — o ban funciona; a premissa do k=5 não sobrevive a 1800 s

**Mecânica: correta.** O ban dispara em todos os 120 runs (mín 8, mediana 174, máx 510 recusas por
run), sempre como `result=no_match reason=dead_pair` seguido de fallback SATA. A isenção
input-capable funciona como especificada: **zero** `dead_pair` em `type_text` (as 110 falhas de
`type_text` são todas `reason=boundary`). O bucket degenerado — a razão de ser do ban — é **0** em
todos os 120 runs (`no_match_degenerate` em `tel_proxies.csv`). E o k embarcado é de fato 5
(`LlmRouter.java:50`, `DEAD_PAIR_STRIKES = 5`; jar bit-reprodutível, sha conferido no gate 2).

```bash
# recusas e denominadores (traces do braço LLM)
find results -name '*mop_on_llm_70.trace' -print0 | xargs -0 grep -h -F '[APE-LLM-TEL]' \
  | grep -c 'reason=dead_pair'          # 24.799
# calls=70.313 (soma das linhas 'LLM Summary'); executáveis = matched+llm_tap+dead_pair = 65.921
```

**Premissa quantitativa: violada.** O design selecionou k=5 porque, no replay estático do corpus de
300 s, k=5 recusava 27,5% e k=3 recusava 37,6% — e o critério vinculante era o teto de 30%, abaixo
do qual o braço ainda "significa o LLM explorando" em vez do seu fallback SATA. Na corrida real, a
recusa foi **35,3% de todas as chamadas** (24.799/70.313) e **37,6% das decisões executáveis**
(24.799/65.921). A coincidência numérica com a previsão de k=3 é isso — coincidência: o k=5 está no
fonte e no jar. O que mudou é o horizonte: o replay era um contrafactual estático sobre runs de
300 s, e o próprio design registrou que o número era "um limite sobre a disrupção, não uma
previsão". A 1800 s, com o modelo re-emitindo as mesmas coordenadas por milhares de passos, os pares
banidos acumulam recusas por muito mais tempo — e a fração recusada cresce até furar o teto.

**Rendimento por decisão: abaixo do previsto, com ressalvas.** O claim projetava o rendimento
(new_state por decisão executada) subindo de ≈11,4% para ≈14,7%. O realizado é **6,6%**
(2.651/40.318 decisões LLM com outcome). As ressalvas: (i) rendimento por fonte é endógeno
(pré-registro §6) — contexto interpretativo, não desfecho; (ii) os 11,4%/14,7% foram derivados a
300 s, e rendimento cai com o horizonte (saturação); (iii) sem braço "ban desligado" na corrida,
o dado não separa quanto o ban elevou ou não o rendimento. O que o dado sustenta afirmar: a 1800 s
o rendimento por decisão LLM é 6,6%, três vezes o do SATA no mesmo braço (2,2% = 1.560/70.098) e um
terço do Coverage (18,7% = 1.319/7.041).

**Consequência interpretativa** (não relitiga nada): no braço LLM efetivamente entregue, ~35% das
respostas do LLM viraram decisões SATA. O braço que o contraste RQ-C3 comparou é "LLM ⊕ fallback"
numa proporção maior que a projetada — exatamente o cenário que o teto de 30% queria evitar, pela
razão que o design enunciou: acima dele fica mais difícil separar "o ban ajudou" de "o SATA fez o
trabalho". Isso não afeta a validade do contraste pareado (mesmo jar nos dois braços), mas entra no
que o nulo *significa* (§8).

## 4. B6(i), B6(iv), N1, B4, B7(i) — os alvos atingidos

**B6(i).** Das 41.112 decisões LLM executadas ([APE-STEP] `decision_source=LLM`): `MODEL_CLICK`
35.147, `MODEL_LLM_TAP` 5.501, `MODEL_BACK` 436, `MODEL_LONG_CLICK` 28. O join step↔TEL mostra que
os 28 `MODEL_LONG_CLICK` vêm todos de respostas **`type_text`** (28/28, sempre `matched` em
EditText), nunca de `click` — logo, para respostas `click`, a restrição é **100%** (35.147/35.147),
contra 80,9% pré-fix. O vazamento dos 28 é um defeito distinto e pequeno (2,3% das `type_text`): o
passe de containment restringe ActionType só para `click` (INV-RTR-17, `LlmRouter.java`), e o
`fixTextEdit` devolve `type_text` inalterado, então uma resposta `type_text` pode agarrar a ação
`MODEL_LONG_CLICK` do mesmo EditText — executando um long-click onde deveria digitar. Severidade:
smell, candidato a item de follow-up no ape.

**B6(iv).** `type_text` voltou a existir: 1.233 chamadas (1,8% das TEL), 91,1% matched, `text="…"`
presente, zero `llm_tap`, zero `dead_pair` — a isenção do ban para alvos input-capable, que existe
para não matar o único canal de entrada de texto, está operante. Pré-fix, a conversão do click em
EditText descartava o texto e `type_text` era ≈0.

**N1.** O acerto sobre tentativas — `matched/(matched+no_match_boundary+llm_tap)` =
35.621/45.413 = **78,4%** — supera o 71,4% medido offline com identificadores. Duas ressalvas: o
protocolo é outro (produção a 1800 s vs grounding offline), e a parcela bruta de matched sobre
todas as chamadas é 50,7%, puxada para baixo pelas recusas do B1 (que não são erros de grounding: o
router recusa *antes* de tentar). A heterogeneidade por run é grande: mediana 58,2% da parcela
bruta, mínimo 9,0%, máximo 94,0%.

**B4.** `ape.llmSnapTolerancePx: 150` confirmado no dump `Configurations:` dos 120/120 traces
(dump que fica ~60 KB antes do EOF — buscar no fim, nunca nas primeiras linhas). Distribuição de
`nearest_dist` dos matches: 0,3% a 0 px, 36,5% a (0,10], 30,2% a (10,50], **21,9% a (50,150]** — a
faixa que o piso de 150 px abriu — e 11,1% acima de 150 px, possíveis porque a tolerância real é
`max(150, min(w,h)/2)` (widgets grandes casam de mais longe). Dos `llm_tap`, 72% estavam a >150 px
do widget mais próximo, coerente com o corte; os poucos a ≤10 px têm `nearest_class` não clicável
(ex.: TextView), que o snap corretamente não aceita. Funciona como desenhado; sem braço sem-snap,
não há como quantificar o ganho.

**B7(i).** `mode=stagnation` aparece 131 vezes, em 55 dos 120 runs, com 44 matched / 86 no_match /
1 llm_tap. O claim era o mínimo — "passa a disparar", contra uma janela de 1 passo que nunca
disparava — e ele se cumpre. O volume é marginal (0,19% das chamadas): o gatilho existe, mas quase
não participa do comportamento do braço.

## 5. B6(iii) e o caminho de repair — o veredicto do caso sglang

Sobre a corrida inteira (`logs/sglang.stdout.log`, 31 MB):

```bash
grep -c 'Failed to parse JSON part' sglang.stdout.log     # 54.508
grep -c 'chat/completions' sglang.stdout.log              # 70.215 POSTs
```

**54.508 falhas de parse em 70.215 requisições (77,6%)** — a amostra parcial do hand-off (78%)
confirma-se na população. O espelho jar-side fecha 1:1: das 70.214 linhas `[APE-LLM-RESPONSE]`,
54.516 (77,7%) caíram no fallback XML e apenas 15.685 (22,3%) chegaram como tool_calls nativos. A
forma dominante da malformação é uma só: **`{"x": N, M}` — a chave `"y"` omitida** — 47.009 das
54.508 falhas (86,2%); mais 5.650 strings não terminadas e 1.389 outras. 54.132 falhas são da tool
`click`, 376 de `type_text`.

Do lado do jar, o caminho de repair reparou **63.600 das 70.313 chamadas (90,5%)**: `missing_y`
47.389, `quoted_xy` 14.170, `array_xy` 1.545, `int_scan` 496. O custo terminal da malformação na
corrida inteira foi **2 chamadas** (`parse_error` no summary dos 120 runs).

**Veredicto: sucesso do repair, e não-solução — não falha — do B6(iii).** O item B6(iii) corrigiu
uma incoerência real (oferecer no schema uma tool que o prompt negava), mas o defeito dominante é
de *emissão do modelo* (Qwen3-VL-4B emite JSON malformado em 4 de cada 5 tool calls), algo que
nenhum schema por requisição poderia consertar. Não há contrafactual sem o item na corrida, então
seu efeito próprio é inseparável de zero nos dados. O que sustenta o braço LLM é o parser híbrido +
repair: sem ele, 77,6% das decisões LLM não existiriam. A proporção repair/nativo é um número a
citar em qualquer avaliação futura de troca de modelo.

## 6. Correção pontual ao relatório — `MODEL_LLM_TAP` não são 140

O relatório (`docs/20260802_resultados_corrida_decisiva.md`, tabela de ações por tipo) registra
`MODEL_LLM_TAP` como "**140/140** … São 140 em 120 runs — marginais diante das 40.318 decisões
LLM". Três medições independentes concordam que os *eventos* são **5.501**, não 140:

```bash
# 1) TEL: result=llm_tap                                  → 5.501
# 2) [APE-STEP] com @MODEL_LLM_TAP (execuções)            → 5.501
# 3) linhas 'New  action: …@MODEL_LLM_TAP' (ações criadas) → 5.501
```

O "140/140" vem da agregação UICOV, que colapsa os taps a 1/1 por estado (`byType=…
MODEL_LLM_TAP:1/1`): 140 é o número de *estados* que receberam pelo menos um tap, não o número de
taps. Como eventos, os taps são **13,6%** das 40.318 decisões LLM com outcome — não marginais. A
conclusão qualitativa do relatório ("o snap está resolvendo a maioria") permanece válida — 78,4%
das tentativas casam widget — mas o número e a palavra "marginais" precisam de emenda. A decisão de
emendar o relatório é do autor; este documento apenas registra a medição.

## 7. Os gates da tarefa 17.4 (ape), medidos sobre a corrida decisiva

A tarefa 17.4 pede um smoke de 2–3 APKs × 5 min com seis gates. A corrida decisiva é uma instância
estritamente mais forte (120 runs por braço × 1800 s), e cada gate foi medido sobre ela:

| gate | resultado | evidência |
|---|---|---|
| (a) braço MOP-off limpo | **PASS** | já estabelecido nos gates §2 do relatório: 120 runs de controle, `decision_source=MOP` 0, `mop=` 0 |
| (b) ban B1 dispara; bucket D ≈ 0 | **PASS** | 24.799 `reason=dead_pair` em 120/120 runs, sempre → fallback SATA; `no_match_degenerate` = 0 nos 120 runs |
| (c) `activity_has_mop`/`pick_channel` em toda `[APE-STEP]`; `patched` nos alvos resolvidos; zero linhas quebradas | **PASS com resíduo** | 576.665/576.739 linhas íntegras (99,987%); **74 linhas quebradas** (16/43/15 por braço) por `\n` no `text=` do *Name* da ação — sítio de interpolação distinto do que o A8 corrigiu (`resolvedInfo`); as 44 "sem `patched`" são subconjunto dessas 74; nenhum campo se perde (segue na linha física seguinte) |
| (d) `[APE-LLM-ERROR] cause=screenshot` em APK FLAG_SECURE | **PASS** | 67 eventos no freeotpplus (mais 18 em easynotes, 13 em prauga.messages) |
| (e) dump de cobertura precede `Save graph data` | **PASS** | ordem correta em **360/360** traces |
| (f) `cf_changed==0` em todo o braço MOP-off | **PASS** | 0 linhas com `cf_changed`≠0 no controle (515/179 nos braços com boost, como esperado) |

O único desvio da letra dos gates é o resíduo de 74 linhas quebradas em (c) — taxa 0,013%, contra
0,45% pré-A8 (redução de ~35×), sem perda de campo, concentrado em dois APKs cujo texto de widget
contém `\n`. Classificação: **smell residual**, com sítio de correção conhecido (a interpolação do
`Name` da ação), não bloqueante. A decisão de dar 17.4 por satisfeita com esta evidência — em vez
de rodar um smoke separado que seria estritamente mais fraco — é do autor.

## 8. O que isto implica

A pergunta que separa este documento do relatório: **o nulo é evidência sobre o quê?**

- Para **B6(i), B6(iv), N1, B4 e B7(i)**, a engenharia entregou o que prometeu — grounding acima do
  alvo, `type_text` vivo, click restrito, snap operante, gatilho disparando — e o desfecho
  pré-registrado ainda assim não se moveu. Para esses itens, a leitura "o gargalo está no corpus e
  na sensibilidade do desfecho, não na engenharia do braço" é a que os dados sustentam.
- Para **B1**, a qualificação é obrigatória: o braço LLM efetivamente entregue devolveu ~35% das
  respostas do LLM ao SATA — acima do teto que o próprio design definiu como fronteira de
  interpretabilidade. "O LLM não adiciona" é, com precisão, "o LLM *com um terço das suas decisões
  recusadas e substituídas pelo algoritmo* não adiciona". Um k maior (ou um ban por decaimento)
  reduziria a fração recusada — se isso mudaria o desfecho é pergunta aberta, e a resposta do
  pré-registro (§5: o negativo se reporta, não se reprocessa) continua valendo.
- Para **B6(iii)**, o dado redimensiona o problema: o modelo de 4B emite tool calls malformados em
  78% das respostas e o repair é quem carrega o braço. Qualquer iteração futura do braço LLM
  (modelo maior, outro formato de tool call, constrained decoding no servidor) ataca esse número
  antes de qualquer outro.

Nenhum desses pontos reabre RQ-C1/RQ-C3. Eles delimitam o que o nulo significa — e onde a próxima
rodada de engenharia ou de desenho experimental teria tração: sensibilidade do desfecho e corpus
(discussão de tese, com o achado `cov_act` +14,9 pp como pista principal), fração de recusa do ban
no horizonte longo, e a via nativa de tool calling do modelo.

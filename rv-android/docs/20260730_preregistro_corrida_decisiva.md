# Pré-registro — corrida decisiva E3

**Data**: 2026-07-30 · **Revisto**: 2026-07-31 · **Estado**: a congelar antes do launch ·
**Escopo**: RQ-C1 e RQ-C3

**Revisão de 2026-07-31, anterior ao congelamento.** Verificação adversarial
(`docs/20260731_verificacao_analise_percepcao.md`) encontrou três coisas que precisavam entrar antes
do carimbo: a justificativa de poder do desfecho primário citava a estatística errada (§3); o estrato
Compose tem expectativa de zero pares discordantes e isso precisa ser previsão, não descoberta (§4);
e oito dos 40 APKs são a mesma base de código, o que viola a independência que todo teste pareado
assume (§4). Nenhum desfecho, contraste, braço ou regra de decisão mudou — o que mudou foi o que este
documento declara saber de antemão. O congelamento (sha256 no `calibracao/journal.jsonl`) ainda não
ocorreu; verificado no journal, que traz 9 entradas, todas da iter0 e nenhuma deste arquivo.

Este documento fixa o plano de análise **antes de qualquer resultado ser visto**. Depois do congelamento,
nada aqui pode ser alterado; toda análise não prevista abaixo é exploratória por definição e deve ser
rotulada como tal ao ser reportada.

O congelamento é o registro do sha256 deste arquivo em `calibracao/journal.jsonl` (append-only,
INV-CAL-11), o que dá o carimbo temporal auditável. Análise rodada antes desse registro não conta
como confirmatória.

Fontes das decisões já tomadas: `openspec/changes/gh90-e3-decisive-run-setup/{proposal,design,specs}.md`
(braços, nomes, dose, timeout), `docs/20260729_propostas_melhorias_e3.md` §RQs e §"Decisões que só o
autor pode tomar" (D5), `docs/20260730_analise_corrida_decisiva_e3.md` (ameaças medidas).

---

## 1. O que a corrida é

| | |
|---|---|
| Braços | `mop_on_llm_off` (referência) · `mop_off_llm_off` (controle) · `mop_on_llm_70` (LLM) |
| Corpus | os 40 APKs do subset (`bitbanana` não entra) |
| Repetições | 1 |
| Timeout | 1800 s por task |
| Total | 120 runs, 8 containers, ≈ 8 h |
| Substrato | `_FRONTIER_SUBSTRATE` em todos os braços (INV-APV-30) |
| Dose LLM | `llm_percentage=0.7` + bloco `cal_a1` (v13, temp 0, top_p 0,6, top_k 50, ambos os gatilhos) |

**Contrastes.** Cada um é de fator único e ambos compartilham a mesma referência:

- **RQ-C1** — `mop_on_llm_off` × `mop_off_llm_off`: mantido todo o resto fixo, a guia MOP aumenta a
  detecção de violações? Diferem exatamente nas cinco chaves de peso MOP e em `activity_trigger_enabled`.
- **RQ-C3** — `mop_on_llm_off` × `mop_on_llm_70`: sob MOP fixo, o LLM acrescenta algo? Diferem apenas
  em chaves LLM.

**RQ-C0 (APE-RV × conjunto E2) não é respondida por esta corrida** — exige o conjunto E2, que não roda
aqui. Fica adiada.

## 2. Ordem dos portões — validade antes de desfecho

Nenhum desfecho é lido antes destes portões passarem. Um portão reprovado invalida o que ele protege;
não se "ajusta a análise" para contornar.

1. **Controle limpo** (bloqueante). No braço `mop_off_llm_off`, `decision_source=MOP` == 0 **e** o campo
   `mop=` == 0 em todo passo. Se vazou guia MOP no controle, o contraste C1 não mede nada e a corrida
   não é lida.
2. **Jar correto** (bloqueante). O `git_sha` do banner `[APE-BUILD]` bate com o declarado no braço.
3. **Atribuição de braço** (bloqueante). O `[APE-LLM-CONFIG]` de cada run bate com o manifesto, 40/40
   por braço — o mesmo check que a iter0 passou.
4. **Integridade de tasks**. Toda task COMPLETED; ERROR re-executados no resume até esgotar. Runs
   perdidos são reportados em número, não silenciados.

## 3. Desfechos

### Primário — detecção binária por app, McNemar (D5, opção (a))

Para cada APK, `achou = mop_unique > 0`. O desfecho é a tabela pareada 2×2 entre os dois braços do
contraste, e o teste é **McNemar exato** (binomial sobre os pares discordantes), não a aproximação
qui-quadrado — as contagens discordantes serão pequenas.

Este é o limiar de melhoria declarado *a priori*: **o tratamento funciona quando encontra violação em
apps onde a referência não encontra nenhuma**. É a formulação da própria arguidora, e é o desfecho que
mede exatamente a transição que interessa, enquanto o delta contínuo tem pouco a enxergar — 8 dos 40
APKs dão zero em todo braço.

**Correção da justificativa de poder (2026-07-31, antes do congelamento).** A versão anterior deste
parágrafo apoiava a escolha do binário em "25 dos 40 dão valor idêntico entre os onze braços da
iter0". Esse número é a concordância na **identidade do valor contínuo**, que não é o conjunto
concordante do McNemar. Sob a definição binária que o teste de fato usa (`mop_unique > 0`), a
concordância na iter0 é maior, não menor:

| definição | Compose | View | total |
|---|---:|---:|---:|
| identidade de `mop_unique`, 11 braços (o número antes citado) | 19/22 | 6/18 | 25/40 |
| **binária `>0`, 11 braços** | 21/22 | 12/18 | **33/40** |
| **binária `>0`, 10 braços `aperv`** | **22/22** | 13/18 | **35/40** |

O binário continua sendo o desfecho certo pelo argumento da arguidora — mede a transição que
interessa —, mas **não** porque tenha mais a enxergar que o contínuo neste corpus. Ele tem menos.
A escolha se sustenta no significado, não no poder, e este pré-registro passa a dizer isso.

### O poder do primário, declarado antes de qualquer resultado

Registrado aqui porque só vale como pré-registro se for escrito antes: **o McNemar exato bicaudal não
consegue rejeitar a Holm α=0,025 com menos de 7 pares discordantes**, ainda que todos apontem no mesmo
sentido. O p mínimo é 2·(0,5)ⁿ: 0,0625 em n=5, 0,03125 em n=6, **0,015625 em n=7**. A α=0,05 sem
ajuste, o piso é n=5.

Os análogos da iter0 preveem **n_discordante ≈ 3–4** nos dois contrastes:

- **RQ-C3, análogo exato** — `sata_mop_act_frontier` × `cal_a1`, mesmo substrato, mesma dose 0,7,
  mesmo bloco de prompt que esta corrida adota: **n_disc = 3, p = 1,0**, e os três discordantes são
  todos do estrato View.
- **RQ-C1, análogo confundido** — `ape:default` × `sata_mop_act_frontier`, que diferem em 18 chaves e
  não nas 6 do contraste real: **n_disc = 4, p = 0,625**.

**Consequência declarada antes do resultado**: se n_discordante vier abaixo de 7, o teste primário não
rejeita **por construção aritmética**, e não por ausência de efeito. Nesse caso a regra de empate (§5)
continua valendo como decisão de engenharia — o ônus da prova é do tratamento e o custo dele é real —
mas o relatório **registrará explicitamente que o desenho não tinha poder para rejeitar**, em vez de
apresentar o não-rejeitar como evidência sobre a hipótese. As duas leituras não são a mesma, e
distingui-las depois de ver o resultado seria escolha post-hoc.

Dois fatores conhecidos apontam para **mais** discordância do que a iter0 sugere, e nenhum é
quantificável antes de rodar: esta corrida usa **1800 s contra os 300 s da iter0** (6× o orçamento), e
produz **observação única** onde o `per_apk_paired.csv` traz média de 2 réplicas — uma média 0,5 é
cara-ou-coroa a n=1. Ficam registrados como esperança declarada, não como resposta.

### Secundário — Δ pareado de `mop_unique`, Wilcoxon

Diferença pareada por APK, teste de postos sinalizados de Wilcoxon, IC95 por bootstrap pareado
(B=10.000, seed 42 — mesma configuração da iter0, para comparabilidade).

### Terciário / suporte — `cov_mop`

Alcance dos métodos que chegam aos sítios monitorados. Não decide nada sozinho; entra para interpretar
um primário nulo (distinguir "não alcançou" de "alcançou e não detectou").

### Adiado

O GLM do conjunto E2 (RQ-C0) só é computável quando o E2 rodar. Não é parte deste pré-registro.

## 4. Plano de análise

- **Unidade de pareamento**: o APK. Sem seed compartilhado entre braços — o pareamento estatístico é
  por APK e não depende de trajetórias replicáveis (A2 rejeitado no ledger).
- **Correção de multiplicidade**: Holm sobre os **dois contrastes** dentro de cada desfecho. Os
  desfechos primário, secundário e terciário formam famílias separadas — o primário decide, os demais
  descrevem.
- **Estratificação por toolkit**, declarada: cada Δ é reportado também por estrato (Compose / View).
  Detector determinístico, offline, sobre os `.apk.json` existentes: o app é Compose quando
  `androidx.compose.runtime.Composer` aparece em qualquer `reachability[].methods[].signature`.
  Motivo: em ~30% dos apps Compose toda activity é MOP-flagged, então `activity_has_mop` é constante
  e o braço guiado não tem contraste a exibir ali — um Δ nulo nesse estrato é ausência de contraste no
  instrumento, não evidência contra a hipótese. A estratificação é **descritiva**, não uma família de
  testes adicional.

  **Expectativa declarada para o estrato Compose: aproximadamente zero pares discordantes.** Nos dez
  braços `aperv` da iter0, **22 dos 22** APKs Compose são concordantes no desfecho binário, contra 13
  de 18 no View. Ou seja, 55% do corpus não deve contribuir com pares para o teste primário. Isso é
  previsão, não observação sobre esta corrida, e está escrita antes para que um nulo no estrato
  Compose não possa ser lido depois como evidência sobre a hipótese. Acrescenta-se a razão mecânica,
  medida em 2026-07-31: o canal MOP em nível de widget é **identicamente nulo** no estrato — 0 de
  85.158 passos nos dez braços —, e a causa não é o `resource-id` ausente e sim o substrato estático,
  que entrega **zero widgets MOP-flagged** para os 22 apps (`flagged=0` em 22/22). O canal em nível de
  *activity*, esse, continua vivo lá (465 passos de `EVENT_TRIGGER_ACTIVITY` em 15 dos 22 apps), então
  a previsão de zero vale para o desfecho, não para todo mecanismo.

- **Dependência entre unidades, declarada.** O pareamento trata os 40 APKs como independentes, e
  **oito não são**: os seis `info.metadude.*.schedule`, `at.linuxtage.Eventfahrplan_1700028` e
  `ch.digitale_gesellschaft.winterkongress.schedule_118` declaram todos a mesma
  `mainActivity = nerd.tuxmobil.fahrplan.congress.schedule.MainActivity` — é uma base de código com
  oito empacotamentos. Na iter0 os oito são Compose, os oito são concordantes e os oito dão
  `mop_unique = 8` em todos os braços; seis deles compartilham inclusive um `.apk.json` byte-idêntico.
  O subset permanece com os 40 (decisão do autor, inalterada), mas **todo teste pareado reportado
  declarará essa dependência**, e qualquer associação entre estrato e desfecho será acompanhada da
  versão com os clones colapsados. Ordem de grandeza do efeito, medida na iter0: a associação
  toolkit × concordância vai de p=0,00091 para p=0,0135 (odds ratio 12,67 → 8,0) — direção e
  significância sobrevivem, a precisão não.
- **Normalização por passo**, declarada: cada desfecho é reportado também dividido pelo número de
  passos do braço, ao lado do valor por corrida. Motivo: neste substrato o braço LLM é limitado por
  latência, não por seleção, e as duas coisas são indistinguíveis no nível da corrida. Medido nas 84
  corridas `cal_a1` do iter0 contra a referência pareada (`sata_mop_act_frontier`, a configuração do
  braço 1): o braço LLM executa **0,622×** os passos (mediana 168 contra 264,5) e descobre **0,729×**
  os estados distintos (mediana 22 contra 27; perde em 67 dos 80 pares APK×rep, Δ mediano −7),
  gastando **35%** do orçamento de 300 s esperando inferência — enquanto **por passo** os dois braços
  são quase iguais (≈11,9% contra ≈12,5% de taxa de estado novo). Um nulo por corrida admite duas
  leituras incompatíveis, "o LLM seleciona pior" e "o LLM seleciona igual mas recebe menos chances", e
  só a razão por passo as separa. A normalização é **descritiva**, não uma família de testes
  adicional, e **não** desloca o desfecho por corrida, que segue primário: uma ferramenta que não
  consegue gastar seu relógio é pior na prática — a razão por passo diz *por quê*, para que a decisão
  de tirar o LLM do desenho se apoie no motivo certo.
  Distinta da "vantagem por passo do LLM" registrada em §6: aquela é yield **por fonte de decisão**,
  condicionada a quando o roteador resolveu chamar, portanto endógena — e por isso fora dos desfechos.
  Esta é o total do **braço** dividido pelos passos do **braço**, sem condicionar em roteamento.
- **Sem exclusão de APK depois de ver resultado.** Os 40 entram. APKs com zero violação em todo braço
  permanecem na tabela do McNemar (são pares concordantes) e são reportados.

## 5. Regras de decisão

### A regra de empate — o ônus da prova é do tratamento

**Empate ⇒ o algoritmo vence.** Operacionalmente: se o teste pré-registrado não rejeita, a conclusão
registrada é **"o tratamento não acrescenta"**, e não "inconclusivo". Não há reanálise, nem troca de
desfecho, nem aumento de n em busca de significância.

**A regra vale; o relatório do não-rejeitar não é único.** Se n_discordante ficar abaixo de 7, o teste
não podia rejeitar (§3, "O poder do primário"), e o relatório dirá isso ao lado da conclusão. A regra
de empate continua decidindo — ela é uma regra de decisão de engenharia sobre ônus da prova e custo,
não uma inferência estatística — mas registrar "não rejeitou" sem registrar "não tinha como rejeitar"
seria omitir o que a própria iter0 já previa. As duas frases convivem: o tratamento sai do desenho, e
o motivo declarado é que não demonstrou benefício num desenho que, sabidamente, tinha pouco poder para
detectá-lo.

A assimetria é deliberada. Com n=40 e 1 repetição, um resultado inconclusivo não é evidência de efeito;
e o custo do tratamento é real, medido e pago continuamente — o braço LLM executa 161,8 passos por run
contra 260,2 da referência (−38%), além de GPU e complexidade. Diante de custo certo e benefício não
demonstrado, o sistema mais simples vence por padrão.

**Consequência por contraste — as duas não são simétricas:**

- **RQ-C3 (LLM)**: empate ⇒ o LLM **sai do desenho**. É decisão de engenharia, e destrava a fila de
  itens adiados que dependiam dele (B8, B10-LLM, B7(ii)).
- **RQ-C1 (MOP)**: empate ⇒ registra-se **resultado negativo para a hipótese central** e reporta-se
  como tal. Não é decisão de remover o MOP — a tese é *sobre* ele; é obrigação de reportar o negativo
  sem reprocessá-lo até virar positivo.

### Critério de falsificação

- **C1 falsificada** se o McNemar pareado `mop_on_llm_off` × `mop_off_llm_off` não rejeitar. Ou seja:
  a guia MOP não faz o sistema encontrar violação onde ele não encontrava.
- **C3 falsificada** se o McNemar pareado `mop_on_llm_off` × `mop_on_llm_70` não rejeitar.
- Um Δ **negativo** com IC excluindo zero é resultado mais forte que o empate e é reportado como
  evidência de que o tratamento **prejudica** — precedente já existente: `cal_a1` a 300 s deu
  Δ`cov_mop` −4,07 [−7,39; −0,40], Holm p=0,0169.

## 6. Premissas declaradas

Registradas como premissas falsificáveis da corrida, não como fatos estabelecidos.

- **A premissa do orçamento.** O timeout de 1800 s existe porque se espera que o algoritmo estagne
  enquanto o LLM continua explorando. **Não há indicador antecedente disso**: a 300 s o decaimento de
  descoberta de estados novos é 0,32 na referência contra 0,33 no braço de 70%, curvas paralelas, e o
  SOTA externo prevê a direção oposta (always-LLM platôa em ~60 min). A corrida testa esta premissa;
  não a assume.
- **A insensibilidade do desfecho.** 73,1% das violações distintas aparecem nos primeiros 10 s, e a
  mediana da última descoberta nova por run é 2,6 s — dominadas por inicialização de TLS/HTTP
  (`okhttp3`, `okio`). A escolha do binário como primário é a resposta pré-registrada a isso. Se o
  binário também vier plano, a conclusão registrada é a da regra de empate, e a leitura honesta é que
  **neste corpus a exploração de GUI não é o gargalo da detecção de mau uso de JCA** — que é um
  resultado sobre o corpus, reportável.
- **Vantagem por passo do LLM, com ressalva.** 6,95 violações por 1000 passos contra 4,32 da
  referência. A ressalva é que yield por fonte é endógeno (condicionado a quando o roteador decidiu
  chamar) — o relatório de calibração falsifica o uso preditivo dessa razão com erro de +39,2% no A1.
  Por isso ela **não** entra como desfecho, apenas como contexto interpretativo. (A normalização por
  passo declarada em §4 é outra medida: total do braço sobre passos do braço, sem condicionar em
  roteamento, e portanto não afetada por esta endogeneidade.)
- **O contrafactual de 300 s roda outro caminho de LLM.** A leitura entre orçamentos — `cal_a1`@300 s
  contra o braço 3@1800 s — pressupõe o mesmo tratamento com apenas o orçamento mudando. A change
  irmã (`telemetry-proof-llm-efficacy`, repo `ape`) põe todo o seu grupo de eficácia no jar da corrida
  decisiva, e nada disso estava no jar do iter0. São **sete** itens que mudam o comportamento do braço
  LLM, não um: **B1** (ban de par morto — recusa 27,5% das decisões executáveis a **k=5**, elevando o
  rendimento por decisão de ≈11,4% para ≈14,7%; o k subiu de 3 para 5 em 2026-07-31, quando se
  verificou que a varredura original fora feita sobre uma chave diferente da que o ban embarca — a
  k=3 a recusa real seria 37,6%), **B6(i)** (`click` restrito a `MODEL_CLICK`, hoje
  acerta 80,9%), **B6(iii)** (schema de tools por requisição), **B6(iv)** (`fixTextEdit`), **N1**
  (identificadores nas linhas de elemento do prompt — acerto medido 33,1% sem contra 71,4% com),
  **B4** (snap por borda) e **B7(i)** (gatilho de estagnação passa a disparar). Os itens do grupo A
  são telemetria neutra por braço e não entram nessa lista. Logo os dois pontos diferem em orçamento
  **e** em caminho de LLM — não há interação dose × orçamento limpa a ser lida.
  O confundimento é **direcional**: seis dos sete favorecem o LLM, e só o B7(i) adiciona custo (mais
  chamadas, mais latência). O tratamento pré-registrado dessa assimetria está em §7.
  O contraste **primário não é afetado**: os braços 1 e 3 rodam no mesmo jar e são pareados por APK,
  então os sete itens são constantes na comparação que decide.

## 7. Análises exploratórias — declaradas como tais

Não confirmatórias. Geram hipótese, não decidem nada, e serão rotuladas assim no relatório: mecanismo
elo a elo (C2), alcance de telas-MOP como régua de qualidade (C4), moderação por Compose e FLAG_SECURE
(C5), decomposição por canal de decisão, o join clock↔logcat (A9), e qualquer corte por estrato além
do toolkit já declarado.

### A sonda de poder do RQ-C1 — declarada em 2026-08-01 e cancelada no mesmo dia

**Esta subseção registra uma análise que foi declarada e depois abandonada, e permanece no documento
por isso mesmo.** A declaração chegou a ser commitada (`1eed2891`) antes de a sonda rodar; apagá-la
tornaria invisível uma decisão que faz parte da história do desenho. **A sonda não foi executada. Não
existem dados dela. Nada nesta subseção está em vigor** — o que se segue descreve o que ela seria e
por que foi abandonada.

#### O que ela seria

Antes de comprometer as ~8 h da corrida decisiva, rodaria-se uma **sonda de poder** sobre o contraste
primário do RQ-C1. Estaria declarada aqui, e não no §3, porque não seria desfecho: seria diagnóstico
de desenho. Ao contrário das demais análises desta seção, decidiria **uma** coisa — se a corrida
decisiva rodaria como pré-registrada ou se o desfecho primário seria revisado antes do congelamento.
Sobre a hipótese não diria nada, nem poderia.

**O que é.** Os dois braços do RQ-C1 apenas — `mop_on_llm_off` e `mop_off_llm_off`, ambos com o LLM
desligado —, 40 APKs × 1 repetição × 2 braços = 80 runs. Computa o mesmo desfecho binário do §3
(`achou = mop_unique > 0`), a mesma tabela 2×2 pareada e o mesmo McNemar exato, e reporta o
**n_discordante**, a decomposição por estrato Compose/View e quantos dos 40 são concordantes-em-zero
— que é o outro modo de o teste não ter o que medir.

**Por que.** O §3 declara que o McNemar exato não rejeita a Holm α=0,025 com menos de 7 pares
discordantes, e que os análogos da iter0 preveem 3–4. Só que **nenhum braço da iter0 responde isso
para o contraste real**: nenhum fixa o substrato frontier e desliga o MOP, e o análogo mais próximo
(`ape:default`) difere em 18 chaves, não nas 6 que separam os braços 1 e 2. A sonda responde por
cerca de 1/5 do custo da corrida completa se o contraste primário tem pares discordantes a ver.

**Orçamento distinto: 300 s, não 1800 s.** A escolha é de isolamento, não de economia. A 300 s a
sonda não produz nenhum run da corrida decisiva — a identidade de um run é `(apk, tool, variant,
repetition, timeout)`, e o timeout diferente mantém as duas campanhas disjuntas no resume —, então
**nenhum dado é reutilizado nem descartado**. E a 300 s ela é diretamente comparável ao análogo
confundido da iter0, isolando exatamente o que muda: um braço MOP-off que *mantém* o substrato
frontier.

**Seus resultados não entram na análise confirmatória, em hipótese alguma** — nem como dado, nem como
n adicional, nem como réplica. A sonda roda a 300 s e a corrida decisiva a 1800 s: o n_discordante que
ela devolve é diagnóstico sobre o desenho, não estimativa do que a corrida vai encontrar.

**O que se fará com cada desfecho, fixado aqui antes de rodar:**

- **n_disc ≥ 7** → a corrida decisiva roda como pré-registrada; a sonda confirmou que o contraste tem
  o que medir.
- **n_disc entre 4 e 6** → roda, e o relatório declara de antemão que o poder é marginal a 300 s (a
  1800 s pode melhorar, e é justamente o que a corrida testa).
- **n_disc ≤ 3** → **primário e secundário trocam de posição antes do congelamento**: o Δ pareado de
  `mop_unique` sob Wilcoxon de postos sinalizados (§3, "Secundário") passa a primário, e o binário sob
  McNemar exato passa a secundário. Nada mais se move: mesma unidade de pareamento, mesmo Holm sobre
  os dois contrastes, mesma estratificação Compose/View, mesma declaração de dependência dos oito
  clones.

A troca não inventa desfecho: **os dois já estão declarados no §3**, escritos antes de qualquer dado.
O que a sonda seleciona é qual dos dois decide, não o que se mede. E o ramo é forçado pela aritmética,
não escolhido — a n ≤ 3 o piso do McNemar exato bicaudal é 2·(0,5)ⁿ ≥ 0,125, então ele não alcança
Holm α=0,025 diga o que disserem os dados. Mais runs não compram poder para esse desfecho, e o 4º
braço do §8 mudaria o contraste em vez de dar poder ao contraste do RQ-C1.

**O resíduo, declarado.** Uma regra adaptativa, ainda que pré-comprometida, aposta parte da
credibilidade do desenho em a sonda ser diagnóstico limpo. O que se faria a respeito é tornar a ordem
inspecionável: o resultado da sonda seria registrado no `calibracao/journal.jsonl` com o sha256 do seu
relatório, em **entrada separada** do carimbo de congelamento deste documento, de modo que qualquer
leitor pudesse verificar que a regra acima foi escrita antes de o número existir.

#### Por que foi cancelada, no mesmo dia e antes de rodar

Decisão do autor em 2026-08-01, algumas horas depois da declaração acima: **a sonda não muda nenhuma
ação subsequente**. Nos três ramos da regra de leitura a corrida decisiva roda igual — mesmos três
braços, mesmos 40 APKs, mesmos 1800 s, mesma repetição única. A única coisa que o `n_discordante`
selecionaria é qual de dois desfechos **já declarados no §3** levaria o rótulo de primário. Isso é
rótulo de análise, não parâmetro de execução, e 80 runs seriam gastos e depois descartados — a própria
declaração os proibia de entrar na análise confirmatória — para escolher entre duas etiquetas que já
existiam.

E o risco que ela mediria já tem tratamento declarado sem ela: o §3, em "O poder do primário", fixa
**antes de qualquer resultado** que um `n_discordante` abaixo de 7 significa que o teste não rejeitou
*por construção aritmética*, e que o relatório registrará isso explicitamente em vez de apresentar o
não-rejeitar como evidência sobre a hipótese. Esse `n_discordante` é computado ao fim, sobre os dados
da própria corrida decisiva — exatamente como seria computado sobre os da sonda, e sobre a amostra que
de fato interessa, a de 1800 s, em vez de sobre uma de 300 s que mede outro regime.

**Consequência para o plano de análise: nenhuma.** O desfecho primário continua sendo o binário por
app sob McNemar exato, e o Δ pareado de `mop_unique` sob Wilcoxon continua secundário, como o §3
sempre disse. A regra de troca descrita acima **caduca junto com a sonda** e não pode ser invocada
depois de ver os resultados da corrida — trocar o primário à luz do `n_discordante` observado na
amostra confirmatória seria precisamente a escolha post-hoc que este documento existe para impedir.

### A leitura entre orçamentos, com compromisso direcional

Comparar `cal_a1`@300 s com o braço 3@1800 s — mesma dose de 70%, mesmo subset, orçamentos diferentes
— serviria para diagnosticar um resultado nulo: separar "a dose está errada" de "o orçamento ainda é
curto". O confundimento declarado em §6 (sete itens do caminho de LLM mudaram junto com o orçamento)
tira dela o estatuto de interação limpa. Ela permanece como exploratória, e **a direção em que será
lida fica fixada aqui, antes de qualquer resultado**:

- **Braço 3 nulo ou negativo a 1800 s** → a comparação **é lida**, e o confundimento a *reforça*: o
  caminho do LLM foi corrigido em sete pontos e recebeu 6× o orçamento, e ainda assim não supera o
  algoritmo. A conclusão negativa fica mais forte do que o desenho previa, não mais fraca.
- **Braço 3 positivo a 1800 s** → a comparação **não é lida**. O ganho não é repartível entre
  orçamento e consertos, e tentar reparti-lo depois de ver o resultado seria escolha post-hoc.

O compromisso é assimétrico de propósito, e é a assimetria do próprio confundimento que o justifica:
seis dos sete itens favorecem o LLM, então eles só podem inflar um resultado positivo — jamais
explicar um negativo. Nada aqui altera o desfecho primário, que roda com os sete itens constantes
entre os braços 1 e 3.

## 8. Itens ainda em aberto

- **Onde a corrida mora** (diretório / convenção). Precede a geração do manifesto. Ver
  `gh90/design.md` §Open Questions.
- **D13/C12 — critério de qualidade dos testes.** O D14 (spec como régua, = C4) é a única sugestão
  concreta da banca; falta decidir se é *o* critério ou *um*, e qual denominador.
- **O 4º braço opcional** ("sem substrato"): +40 runs, ≈ 10,5 h no total. Segue em aberto como decisão
  de escopo. Registre-se que ele **não é remédio para um n_discordante baixo**: acrescentar um braço
  cria outro contraste, não dá poder ao contraste do RQ-C1, cujo n_discordante depende dos pares em
  que os braços 1 e 2 divergem.

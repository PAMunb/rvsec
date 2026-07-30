# Pré-registro — corrida decisiva E3

**Data**: 2026-07-30 · **Estado**: a congelar antes do launch · **Escopo**: RQ-C1 e RQ-C3

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
apps onde a referência não encontra nenhuma**. É a formulação da própria arguidora, e é o desfecho com
melhor poder no regime medido — 8 dos 40 APKs dão zero em todo braço e 25 dão valor idêntico entre os
onze braços da iter0, de modo que o delta contínuo tem pouco a enxergar enquanto o binário mede
exatamente a transição que interessa.

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
- **Sem exclusão de APK depois de ver resultado.** Os 40 entram. APKs com zero violação em todo braço
  permanecem na tabela do McNemar (são pares concordantes) e são reportados.

## 5. Regras de decisão

### A regra de empate — o ônus da prova é do tratamento

**Empate ⇒ o algoritmo vence.** Operacionalmente: se o teste pré-registrado não rejeita, a conclusão
registrada é **"o tratamento não acrescenta"**, e não "inconclusivo". Não há reanálise, nem troca de
desfecho, nem aumento de n em busca de significância.

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
  Por isso ela **não** entra como desfecho, apenas como contexto interpretativo.

## 7. Análises exploratórias — declaradas como tais

Não confirmatórias. Geram hipótese, não decidem nada, e serão rotuladas assim no relatório: mecanismo
elo a elo (C2), alcance de telas-MOP como régua de qualidade (C4), moderação por Compose e FLAG_SECURE
(C5), decomposição por canal de decisão, o join clock↔logcat (A9), e qualquer corte por estrato além
do toolkit já declarado.

## 8. Itens ainda em aberto

- **Onde a corrida mora** (diretório / convenção). Precede a geração do manifesto. Ver
  `gh90/design.md` §Open Questions.
- **D13/C12 — critério de qualidade dos testes.** O D14 (spec como régua, = C4) é a única sugestão
  concreta da banca; falta decidir se é *o* critério ou *um*, e qual denominador.
- **O 4º braço opcional** ("sem substrato"): +40 runs, ≈ 10,5 h no total.

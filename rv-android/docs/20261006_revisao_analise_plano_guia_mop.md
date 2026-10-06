# Revisão da análise do plano da guia MOP

**Data**: 06/10/2026.
**Objeto**: `docs/20261006_analise_rigorosa_plano_guia_mop.md` (commit `48b360c0`), daqui em diante
"a análise". Foi escrita por outra sessão, que leu o relatório
(`docs/20261005_gator_fragments_compose_guia_teste.md`, "o relatório") e a verificação
(`docs/20261005_verificacao_plano_gator_compose.md`, não comitada, "a verificação").
**Natureza**: só leitura. Nada rodou: nem GATOR, nem docker, nem emulador, nem build. Os subagentes
recontaram números com scripts curtos sobre arquivos que já existem (`.apk.json`, CSVs do E6,
saídas da tese). Os scripts ficaram no scratchpad da sessão, e cada número que pesa está dito de
onde veio. Nada foi comitado.
**Estado dos repositórios na leitura**: `ape` em `43664568`, com `src/` igual ao de `e93dea86`, o jar
do E6. A sessão do `ape` analisa a mesma análise em paralelo. Antes de qualquer uso, confira se o
`ape` mudou.
**Re-investigação (06/10, segunda sessão)**: os erros da análise foram reabertos na fonte, com o
`derive()` de produção sobre os 163 `.apk.json`, `dexdump` dos APKs instrumentados e as tabelas do
E6. Ela mudou o R3, o R4, o R5, o R6, o R8 e o R10, e o resumo abaixo. Em dois pontos (R6 e a
premissa do R4) a primeira versão desta revisão também errava. Os scripts estão no scratchpad da
sessão (`d1/`, `d2.py`), fora do repositório; a §6 lista o que foi reaberto.

**Rótulos**:
- **[conferido]**: aberto por mim nesta sessão.
- **[relato]**: trazido por subagente e não reaberto por mim.
- **[hipótese]**: inferência.
- **[web/conhecimento]**: conhecimento do framework sem fonte local da versão em causa.

---

## 0. Resumo

A análise acerta mais do que erra. Os pontos de código que ela diz ter conferido conferem. Os erros
estão em quatro lugares:
- em duas generalizações tiradas de um único APK: o `aegis` no D1 (R4) e o `eu.faircode.email` no
  D2, que tem 502 das 528 marcas presas a chave de diálogo (R5);
- na parcela de decisões do LLM no E6 e na conclusão tirada dela (R6). A primeira versão desta
  revisão também errava aqui;
- na citação do desfecho da decisão 6: o SQ9 é outra medida, mas com as medidas certas a conclusão
  dela se mantém (R3);
- em números menores e numa estimativa de custo (inventário, R10).

O que ela muda no plano, do que mais muda ao que menos muda:

1. **A queda de `reachesTarget` no C0 não decide nada sozinha** (R1). Decidido em 06/10: o C0 só
   mede, e o veredito sai do 7.5 ampliado. O mecanismo do leque que o relatório dá
   na §4.2 está errado, e a análise tem razão nisso: o GATOR roda SPARK, e o SPARK não semeia
   parâmetro de ponto de entrada. Consertar as exclusões também corta arestas verdadeiras. Uma queda
   de `reachesTarget` não basta para aprovar o C0. Há ainda um fato novo para o desenho dos braços
   do C0: `kotlinx.*` não está no `libPackages.txt`.
2. **A distância do 7.5 tem de ser calculada também sobre o grafo restrito ao app** (R2). A BFS de
   hoje não guarda nível e atravessa todo o call graph, inclusive a biblioteca. Os chamadores
   diretos que estão na biblioteca também semeiam a BFS reversa.
3. **O desenho da próxima campanha precisa de unidade de análise mais fina que o APK** (R3). As
   contas de poder reproduzem exatamente. A conclusão certa é "a guia teria de recuperar 70–80 % de
   uma lacuna inflada pelo ruído", e não "só uma guia quase perfeita passaria". A frase "o desfecho
   da decisão 6 já foi lido no E6 e não se moveu" cita a medida errada (o SQ9), mas vale com as
   medidas da decisão 6: 125 × 136 chamadores diretos executados e 19 × 19 sítios de origem no app
   durante a interação, braço 2 × braço 3, nos 89 APKs.
4. **A recomendação para o D1 desligaria a recuperação D8 inteira** (R4). Dos 731 widgets marcados só
   pela recuperação, 601 têm o alvo específico do wrapper alcançando: são lacuna do call graph, o
   caso do `cryptoapp`. Os outros 130 herdam a flag das lambdas irmãs, o caso do `aegis`. A premissa
   da análise vale para os 130 e falha para os 601. O defeito real é de precisão (o OU por classe),
   e o tamanho dele é 130 widgets, cerca de 5 % dos 2.681 marcados [conferido].
5. **O D2 é, quase todo, a WTG que não terminou, e quase todo um APK** (R5). 524 das 528 marcas
   presas a chave de diálogo estão em 7 APKs sem WTG, e 502 delas no `eu.faircode.email`. Os 44
   artefatos sem `complete` carregam 1.550 dos 2.681 widgets marcados do corpus (58 %) [conferido].
6. **No braço MOP+LLM do E6, o LLM decidiu cerca de 37 % das ações executadas** (R6) [conferido].
   O 0,9 do `arms.json` é a moeda por passo admitido, não a parcela de decisões. O LLM foi consultado
   em 70,9 % dos passos, e quase metade das respostas do modo aleatório caiu no resto do pipeline por
   par banido. A conclusão "nesse braço, a guia só chega ao agente pelo marcador do prompt", da
   análise e da primeira versão desta revisão, não vale: o algoritmo, onde o reforço MOP age, decide
   cerca de 63 % das ações.
7. **O histórico do LLM grava, na entrada da ação N, o efeito da ação N−1** [conferido] (R7). O
   defeito é anterior à change `llm-coordinate-single-base`: a spec principal `exploration` descreve
   o alinhamento certo, e o código não o faz.
8. **O defeito do `invoke-super` no weaver existe e já está no corpus instrumentado** (R8). No
   myexpenses, `super.close()` de uma subclasse de `CipherInputStream` virou chamada ao wrapper, que
   volta à sobrescrita [conferido no `dexdump`]. O padrão aparece em 4 dos 348 `head_apks` [relato];
   2 deles estão entre os 163 instrumentados, o myexpenses e o passportreader [conferido], em
   caminhos raros. É issue do instrumentador, fora do esforço da guia. As duas correções possíveis
   (não trocar o `invoke-super`, ou um acessor na subclasse) não são neutras. A primeira perde
   eventos, e a segunda pode **contar o mesmo evento duas vezes**, o que gera violação falsa numa
   spec como a `CipherInputStreamSpec`. No passportreader, a contagem dupla de `initialize` existe
   com qualquer das duas, porque o próprio Spi chama `this.initialize(spec)`.
9. Correções menores e confirmações, na §2.9 e no inventário (§1).

Nada disso muda a ordem decidida, que é C0 → 7.5 → 7.1 ampliado → change do GATOR. Mudam o portão
do C0, as configurações do 7.5, o custo da modelagem de diálogos, DataBinding e adapters, e as
opções do desenho da campanha.

---

## 1. Inventário das afirmações

Linhas da análise. Tipos: **código** (fato sobre código), **dado** (fato sobre dado), **desenho**
(proposta), **rec.** (recomendação), **decisão** (pedido de decisão). Veredito: **vale**, **não
vale**, **em parte**, ou **não conferível sem rodar**. "Plano" diz se a afirmação já estava no
relatório (Rel.) ou na verificação (Ver.).

### 1.1 Leitura do E6 (§1)

| # | linha | afirmação | tipo | veredito | plano |
|---|---|---|---|---|---|
| I-01 | 66 | C2 = 1,012 [0,897; 1,142], mínimo detectável 1,18; SQ9 C2 = 0,990 [0,825; 1,188] | dado | vale [conferido, `rerun-avare/report.md:79,98`] | novo |
| I-02 | 66 | "o desfecho que a decisão 6 propõe já foi lido no E6 e não se moveu" | dado | em parte: cita a medida errada (o SQ9); com as medidas da decisão 6, a conclusão vale (R3) [conferido] | contradiz Ver. A6 só na leitura |
| I-03 | 77–81 | marca rara: limiar ≤ 3 escolhido depois de ver os dados | dado | vale [conferido: `m9_robust.py:1` se declara *post hoc*] | Rel. §6.4 não diz |
| I-04 | 80 | novidade confundida com o tempo de execução | hipótese | plausível, não medida | novo |
| I-05 | 83 | regra do esqueleto para M14–M17 | dado | em parte: a regra existe (`esqueleto.md:87-106`), mas a pasta `20261005_e6_graduacao_marca` não está na lista; vale se o artigo citar [relato] | novo |

### 1.2 Contrato GATOR → APE-RV (§2)

| # | linha | afirmação | tipo | veredito | plano |
|---|---|---|---|---|---|
| I-06 | 95 | activity casa exata | código | vale; "fragment não muda o `topActivity`" é comportamento da plataforma [web/conhecimento] | Rel. §3.4 |
| I-07 | 96 | `shortId` casa exato por nome | código | vale [conferido, `MopData.java:690-694`] | Rel. §2.1 |
| I-08 | 97 | eventos fora de click/longClick/itemSelected/scroll caem no agregado | código | vale; o INV-MOP-14 só está definido no arquivo da gh13 [relato] | novo (como o A8) |
| I-09 | 98, 121–124 | handler → flag é aproximado; marcador do prompt ≠ pontuação | código | vale, com três casos de divergência (R9) [relato] | Ver. §7.2 em parte |
| I-10 | 106–112 | D1: a recuperação D8 passa por cima de um "falso" explícito | código + dado | mecanismo e números valem; a premissa vale em 130 dos 731 widgets e falha em 601; **a correção não vale** (R4) [conferido] | Rel. §6.7 cita a recuperação |
| I-11 | 113–115 | D2: 19,7 % das marcas presas a chave de diálogo | dado | número vale; **a causa é a WTG ausente**, e 502 das 528 são de um APK (R5) [conferido] | Ver. A10 ("outra janela", 1,1 %) |
| I-12 | 116 | D3: `windowNodeIds` por nome de classe | código | vale (`RvsecAnalysisClient.java:203,212`) [relato]; o dano no derive é pequeno, porque ele já chaveia diálogo por classe | novo |
| I-13 | 117 | D4: 120 de 20.569 cliques em `android:id/…` com reforço | dado | vale [relato, recontado] | novo |
| I-14 | 100, 118 | D6: deep link em 50 de 57 não resolve | código + dado | código vale; **50/57 não reproduz**; recontagem aproximada: 94 activities com URI, ~49 provavelmente falham [relato] | Rel. §6.9 cita o URI |
| I-15 | 119 | D7: paridade INV-ANA-32 não protege o caminho real | código | vale: 69 `w.name("…")` e 38 `.put("…")` literais no cliente; o derive só usa literais [relato] | novo |
| I-16 | 120 | D8: `static-analysis-entrypoints` exige `complete==true`; INV-DRV-08 e código aceitam o parcial | código | vale [relato; `aegis` sem `complete` conferido] | novo |
| I-17 | 128–130 | F1/F2 com `Host#Fragment` casa exato, com duas condições | código | vale; reproduzido num artefato sintético: uma janela DIALOG `Host#Frag` arrasta o balde inteiro [relato] | Rel. §3.4 não tem as condições |
| I-18 | 131–136 | vetor v2: merge de diálogos, ordem, `SUPPORTED_FORMAT_VERSION` | código | vale (`derive:891-898,207`; `MopData.java:149,207-212`) [relato] | Ver. A12 em parte |
| I-19 | 138 | diálogos e adapters pela WTG quebram; exatos se o produtor nomear `Host#…` sem WTG | desenho | vale, com a condição de I-17 (não emitir como DIALOG) | Ver. §3.1 |

### 1.3 Produtor (GATOR) (§3)

| # | linha | afirmação | tipo | veredito | plano |
|---|---|---|---|---|---|
| I-20 | 148 | `Scene.isExcluded` só casa `.*`/`$*` | código | vale [conferido no 4.4 local; relato no bytecode do 4.7.1] | Ver. A7 |
| I-21 | 149–153 | o SPARK não semeia parâmetros de ponto de entrada; a §4.2 do relatório está errada | código | **vale** (R1) [conferido]; a citação `MethodPAG.java:239` é de método nativo; a semeadura de biblioteca fica em `MethodNodeFactory.caseIdentityStmt` [relato] | **corrige Rel. §4.2** |
| I-22 | 154–159 | leque por fusão insensível a contexto | hipótese | plausível [relato]; o caminho composable → `invoke` precisa ser mostrado num APK | novo |
| I-23 | 160 | a correção das exclusões tira recall | hipótese | plausível, com o mecanismo conferido (R1) | Rel. §4.2 antecipa em parte |
| I-24 | 161 | o portão do C0 precisa de verdade de campo de recall | rec. | **vale**, com ajuste (R1) | novo |
| I-25 | 165 | `multiSourceBfs` só guarda `visited`; "já calcula e descarta" é impreciso | código | vale [conferido, `RvsecAnalysisClient.java:497-525`] | corrige Rel. §4.5 |
| I-26 | 166 | a BFS atravessa a biblioteca | código | vale [conferido, `buildJGraph`, `:466-484`]; e os chamadores diretos da biblioteca semeiam a BFS (R2) [relato] | novo |
| I-27 | 167–168 | conflito app-só × aresta de lambda; a aresta não repropaga points-to | desenho | vale como raciocínio [hipótese] | Rel. §6.5 peça 1 em parte |
| I-28 | 169 | distância de call graph, não de UI: sem arestas de ICC | código | vale [relato: nem ICC nem ciclo de vida no grafo] | novo |
| I-29 | 175 | F1 falha com transação em classe auxiliar | código | plausível; o relatório (§3.5, F1 item 2) já estende a regra aos fragments, não a auxiliares | em parte |
| I-30 | 176–180 | F2(b) só cobre o caso simples; o fluxo de GUI só segue classes do app | código | vale (`Flowgraph.java:366-392`) [relato] | novo |
| I-31 | 181 | só `android.app.AlertDialog$Builder` é modelado; DialogFragment não | código | quase: um `new X` com X subclasse de `android.app.Dialog` em código do app **é** modelado (`Flowgraph.java:4574-4580`) [relato] | novo |
| I-32 | 182–183 | nada de DataBinding/ViewBinding nem RecyclerView | código | vale [relato] | novo |
| I-33 | 185 | modelar diálogos, DataBinding e adapters custa médio a grande | rec. | vale; **corrige Ver. §3.1** ("a mesma passada que o F1/F2 estende") | corrige Ver. |
| I-34 | 186–191 | causas da sobre-atribuição: `LocalPacker`, CHA no tipo do listener, activity base | código | as três existem; para o `LocalPacker`, o código do conserto é pequeno e no GATOR, mas a causa é hipótese e a validação tem custo (R10) | Ver. A2 |
| I-35 | 192 | JSON pré-WTG antes da WTG; timeout de 600 s | código | vale [relato]; o timeout é do rv-android (`rv_static_analysis/config.py:101-102`), de relógio, e cobre também o apktool | novo |

### 1.4 Instrumentador (§4)

| # | linha | afirmação | tipo | veredito | plano |
|---|---|---|---|---|---|
| I-36 | 200–205 | tabela das variantes A, B, B+, E2 | desenho | em parte: dois números e a incompatibilidade com os monitores não se sustentam (R8, "Variantes") | Ver. A9 |
| I-37 | 208 | a verdade de campo do 7.5 é circular | rec. | em parte (R8) | Ver. A5 |
| I-38 | 209 | B+ no APK original não toca o APE-RV | desenho | vale, mas exige execução nova no dispositivo | novo |
| I-39 | 210 | a captura aceita três tags (`logcat_manager.py:80-81`) | código | vale, com o caminho corrigido (`rv-android-core`) | novo |
| I-40 | 211 | Variante A não antes do 7.5 | rec. | já decidido | Ver. §1 |
| I-41 | 213–219 | `invoke-super` vira chamada estática ao wrapper, com recursão | código | **vale**: 4 dos 348 `head_apks`, 2 dos 163 instrumentados (R8) [conferido no myexpenses e no passportreader] | novo |

### 1.5 Change `llm-coordinate-single-base` (§5)

| # | linha | afirmação | tipo | veredito | plano |
|---|---|---|---|---|---|
| I-42 | 227–230 | o ganho ao vivo supõe a mesma entrada; o prompt proíbe repetir posição | código | a regra existe (`ApePromptBuilder.java:258`) [relato]; os 7,8 % não foram conferidos | novo |
| I-43 | 234–240 | o histórico rotula a ação N com o efeito da N−1 | código | **vale** [conferido] (R7) | novo |
| I-44 | 241–243 | captura com rotação 0 | código | o código vale (`ScreenshotCapture.java:80-81`) [relato]; o efeito em paisagem não é conferível sem rodar | novo |
| I-45 | 246–248 | toque fora da árvore, teclado, nós de altura zero | dado | não conferido | — |
| I-46 | 251 | 4,2 % dos prompts com marcador | dado | não conferido | — |
| I-47 | 252–257 | o efeito real vem do banimento de par morto; reportar a parcela de ações do LLM | rec. | vale: a tarefa 8.2 só mede a recusa [relato]; e a chave do banimento é por `StateKey`, então o refinamento zera os *strikes* [relato] | Ver. §7.2 em parte |

### 1.6 Consumidor APE-RV (§6.1, §6.2, §10.4)

| # | linha | afirmação | tipo | veredito | plano |
|---|---|---|---|---|---|
| I-48 | 267 | atalho MOP determinístico em dois pontos | código | vale, com nuance: os dois pontos usam conjuntos diferentes (não saturado no passo 0, inédito no ε), e ambos param no limite de 3 [relato; passo 0 conferido] | Rel. §6.6 |
| I-49 | 270 | na roleta, o reforço domina (550 × 50) | código | em parte: ação sem MOP chega a 150–450 com fronteira, cobertura e WTG; a roleta é o ramo minoritário (ε de 2–15 %) [relato] | novo |
| I-50 | 271 | no "menos visitado", a prioridade só desempata | código | vale, com `leastVisitedPriorityTiebreak=true` no preset aperv [relato] | novo |
| I-51 | 272 | no braço com LLM, o LLM decide 70 % dos passos admitidos, antes do lançador e do SATA | código + dado | ordem vale [conferido, `DecisionPipeline.java:64-76`]; a moeda do E6 é 0,9 (`arms.json:66`), o LLM foi consultado em 70,9 % dos passos e **decidiu ~37 % das ações** [conferido] (R6) | novo |
| I-52 | 273 | sem planejador para tela não vista | código | vale [relato, `Graph.java:673-731`] | novo |
| I-53 | 280 | `CoveragePass` soma até 100 ao inédito na activity | código | vale; divisão inteira [relato] | Rel. §6.6 |
| I-54 | 281 | a novidade por activity não sobrevive quando o `Name` muda | código | **vale** [conferido `widgetId` → `toXPath()`; relato sobre o que o refinamento muda]; zera também o limite MOP e a chave do banimento | **corrige Rel. §6.6** |
| I-55 | 282 | passo 0 usa "não saturado", a spec diz "não visitado" | código | **vale** [conferido] | novo |
| I-56 | 283–287 | aposentadoria por contador é fraca | desenho | vale; os toques do LLM fora da árvore viram uma chave só, `MODEL_LLM_TAP` [relato] | Rel. §6.7 não diz |
| I-57 | 288 | lançador ordenado por distância pede a mesma activity sempre | desenho | vale como raciocínio: o lançador é binário visitada/não visitada e o INV-CT-14 proíbe agir sobre o resultado | Rel. §6.7 não diz |
| I-58 | 497–529 | `UICoverageTracker`: chave, LRU, consumidores, prompt `v13` sem visitas | código | vale [conferido `widgetId`, `arms.json:65`; demais relato] | Rel. §6.6 em parte |

### 1.7 Teto, poder e desenho de campanha (§6.3, §7)

| # | linha | afirmação | tipo | veredito | plano |
|---|---|---|---|---|---|
| I-59 | 294–297 | lacuna de 42 chamadores e 21 sítios | dado | 42 vale; 21 vale contra a união dos braços, e o máximo por APK dá 20 [relato, recontado] | novo |
| I-60 | 299–305 | mínimo detectável 33/15, 19/8,6, 10,5/4,7 | dado | os números reproduzem exatamente [relato]; as hipóteses estão na R3 | novo |
| I-61 | 307–309 | só uma guia quase perfeita passaria com R = 1 | rec. | em parte: são 79 % e 71 % de uma lacuna inflada (R3) | novo |
| I-62 | 310–312 | micro-randomização, desfecho por alvo, R ≥ 3 | desenho | propostas; a primeira exige mudança no APE-RV (R3) | Ver. §8, aberta 3 |
| I-63 | 311 | um terço das primeiras execuções nos primeiros 5 s | dado | vale: 32 %, 130 de 406, dados selados de 03/10 [relato] | novo |
| I-64 | 314–319 | três braços; o braço com LLM sai da família confirmatória | desenho | proposta; R6 tira o argumento "a guia só chega pelo marcador" | Ver. §7.2 propõe outra coisa |

### 1.8 Compose (§9)

| # | linha | afirmação | tipo | veredito | plano |
|---|---|---|---|---|---|
| I-65 | 368–370 | o `compose-probe` não liga elemento a tela; a §4.3 do relatório erra | código + dado | **vale** (172 de 689 sítios de navegação, nos 87 Compose/mistos) [relato] | **corrige Rel. §4.3** |
| I-66 | 373–376 | 69,6 % classe concreta, 24,5 % `param`, 1.101 TextField/Switch/… fora do `AbstractClickableNode` | dado + código | 69,6 % e 24,5 % valem; 1.101 não reproduz (1.114); **Switch e Checkbox passam sim pelo `AbstractClickableNode`**, mas com um `onClick` do próprio Compose, não o do app [relato] | novo |
| I-67 | 379 | 77,7 % das classes de handler Compose com `reachesTarget` | dado | vale [relato] | novo |
| I-68 | 380–385 | onde ficam os 214 chamadores diretos; `kotlinx` *phantom* corta ViewModel → `invokeSuspend` | dado + hipótese | vale como classificação por nome, frágil [relato]; a consequência é a mesma da R1 | novo |
| I-69 | 386 | a identidade de composable do E1 acumula | código | **vale** [conferido: `ComposeProbeRuntimeMonitor.java:86-87,204`, só `add`]; contradiz `20260806_compose_e1_resultado.md:25` | **corrige o doc de 06/08** |
| I-70 | 387–388 | rota do Navigation por reflexão; manter o `compose-probe` | desenho | propostas; o `compose-probe` mora no repositório do artigo (R11) | Rel. §4.5 (C1) |

### 1.9 Desenho do zero (§10)

| # | linha | afirmação | tipo | veredito | plano |
|---|---|---|---|---|---|
| I-71 | 394–402 | o jar não lê logcat; os dois logs só registram a primeira vez | código | vale (ver §2.8) | Ver. §7, A5 |
| I-72 | 404–411 | malha fechada não compensa | rec. | de acordo | — |
| I-73 | 422–426 | quatro exigências da distância | desenho | síntese coerente com R1, R2 e R10 | Rel. §6.5 |
| I-74 | 432 | voltar a estado visto com widget perto do alvo | desenho | proposta nova; muda o APE-RV (§3) | novo |
| I-75 | 442–448 | 7.5 com duas perguntas, a segunda sem bind | desenho | vale; a segunda alcança Compose (R2) | novo |
| I-76 | 458–474 | visitas: definição e números | código + dado | valem; os números do docstring vêm de 60 execuções de campanha, não do E6 [relato] | novo |
| I-77 | 476–484 | X6.3/X6.4: 267 = 107 + 39 + 102 + 14 | dado | a soma dá 262; faltam os 5 de `pre_exploration` [conferido, `report.md` X6.4]; a regra (a) não tem janela de chegada **por construção**, então a "discordância" dela é de definição [relato] | novo |
| I-78 | 488–490 | pergunta nova: chamador direto dispara na chegada ou na interação? | desenho | vale e é offline (R2) | novo |

---

## 2. Achados, do que mais muda o plano ao que menos muda

### R1. O C0 precisa de um portão de recall, e o mecanismo da §4.2 do relatório está errado

**Fatos.**
- **O call graph é SPARK** [conferido]:
  - `Configs.cgAlgorithm = "spark"` (`Configs.java:74`);
  - o rv-android passa `-cgAlgorithm spark` (`rv_static_analysis/config.py:104-105,385-386`);
  - o log da campanha `jca_android` registra `cgAlgorithm spark`;
  - `Main.java:233-246` liga `-p cg all-reachable:true` e `cg.spark enabled:true`.
- **No SPARK, ponto de entrada não ganha points-to nos parâmetros** [conferido no fonte 4.4; relato
  no bytecode 4.7.1]:
  - `MethodPAG.addMiscEdges` só liga `main(String[])` e alguns métodos do JDK;
  - a semeadura de biblioteca só existe com `cg library` ligado, e o padrão é `disabled`;
  - com `all-reachable:true`, todo método das classes de aplicação vira raiz, mas nem `this` nem os
    parâmetros recebem alocação;
  - chamada virtual sobre receptor vazio não gera aresta.
- **A frase da §4.2 do relatório ("ponto de entrada tem parâmetros sem restrição de points-to") está
  errada.** O leque só pode vir de fusão: alocações reais do app que se encontram num mesmo
  parâmetro, campo ou fila do corpo da biblioteca, como o `_block` de `ComposableLambdaImpl`
  [hipótese plausível; relato].
- **Fato novo** [conferido]: o `lib/gator/libPackages.txt` rebaixa `androidx.*` (linha 110) e
  `kotlin.*` (1425), mas não `kotlinx.*`. As corrotinas continuam "do app" também para o fluxo de GUI.

**Por que a correção tira recall** [mecanismo conferido; efeito hipótese]:
- com `kotlin.`/`kotlinx.`/`androidx.compose.` *phantom*, uma lambda chamada só pela biblioteca
  (`launch {}`, `collect {}`, `setContent {}`) perde a única aresta de entrada;
- o `invoke` dela continua raiz, por `all-reachable`, mas com `this` vazio. As chamadas virtuais
  sobre o que ela captura também somem;
- o chamador direto continua marcado, porque a varredura de bytecode não depende do call graph
  (`ReachabilityEngine.java:108-117`). Quem perde `reachesTarget` é quem chega a ele através da
  biblioteca;
- um risco a mais, não conferido: `kotlin.jvm.internal.Lambda` e as interfaces `Function*` também
  ficariam *phantom*, o que pode afetar o despacho entre lambdas do próprio app.

**O `cryptoapp` mostra que essa lacuna já existe hoje.** O wrapper
`CryptographyActivity$$ExternalSyntheticLambda0.onClick` tem `reachesTarget=false`, e o corpo
`lambda$setupExecuteButton$0$…` tem `true` (`tests/fixtures/cryptoapp.apk.json`) [conferido]. O nome
do corpo indica um método de instância chamado sobre o `this` capturado [hipótese]. Sem quem chame o
wrapper, esse receptor é vazio e a aresta não existe. É o mesmo mecanismo que a correção espalharia.
No corpus, o mesmo padrão (wrapper `false`, corpo `lambda$…$<pacote>` alcançando) está por trás de 601
widgets marcados só pela recuperação D8, 589 deles no redreader (R4) [conferido].

**O que já estava no plano.**
- O relatório antecipou parte disso (§4.2, último parágrafo): com o framework *phantom*, "a aresta
  `composable → Button → onClick` simplesmente desaparece", e o resultado é "uma super-aproximação
  diferente, não precisão".
- A aresta de lambda da §6.5, peça 1, existe por essa razão.
- O que faltava é o portão. O C0 da §4.5 prevê "queda grande em composables e fragments" como
  sucesso, e uma queda por recall perdido passaria nesse portão.

**Decidido em 06/10** (§5): o C0 só mede; o veredito sobre a correção das exclusões sai do 7.5
ampliado. A proposta abaixo foi a primeira redação. Fica como registro da alternativa que não foi
escolhida, porque é heurística: uma lambda criada num método auxiliar seria contada como caminho
falso.

**O que mudar no C0** (proposta original; o C0 continua adiado):
- **Critério de recall.** Para cada método do app que perde `reachesTarget` entre a linha de base e
  um braço, o mesmo GATOR descartável escreve um caminho da linha de base até o alvo e diz se ele
  passa por um `invoke` de lambda do app feito dentro de pacote excluído. Se passa, a perda é de
  recall; se só passa por fusão de biblioteca, é precisão.
  - Custo: cabe nas ~3 h somadas do C0 (Ver. A1), mais o tempo de escrever os caminhos.
  - Onde: só na cópia do GATOR, sem tocar o repositório.
- **A verdade de campo que a análise propõe** (os chamadores diretos executados no E6 continuam
  alcançáveis a partir dos handlers que os precederam) serve como segundo critério. Mas ela existe
  em 13 dos 21 APKs e em nenhum Compose (Ver. A5), e a perda de recall é maior justamente em Compose
  e em corrotinas.
- **Desenho dos braços.** Dizer, em cada braço, se `kotlinx.*` entra no `libPackages.txt`. Hoje ele
  fica "do app" no fluxo de GUI mesmo com a exclusão funcionando.

**Muda**: o portão do C0 e a §4.2 do relatório. Não muda a ordem.

### R2. A distância do 7.5: grafo restrito ao app, sementes, e a pergunta sem bind

**Fatos.**
- `multiSourceBfs` guarda só `visited` (`RvsecAnalysisClient.java:497-525`) [conferido].
- O doc de 03/08 (`20260803_compose_d1_decisao_plano_rearch.md:149`) dizia que "`minHops` é
  exatamente a camada em que a BFS visita o método", e que trocar o `Set` por um `Map` dá a
  distância na mesma passada.
  - Isso é verdade como custo.
  - Como fato sobre o código, "já calcula e descarta" é impreciso, e a análise tem razão.
  - A correção da §4.5 é de texto. O custo de acrescentar o nível continua pequeno.
- `buildJGraph` (`:466-484`) copia todas as arestas do call graph, só sem os laços [conferido]. A
  distância passaria pela biblioteca. Hoje ela inclui o corpo de `androidx.*` não-Compose mesmo no
  braço (i) do C0; só o braço (ii) os rebaixa.
- **Fato novo** [relato]: `findDirectTargetCallers` percorre todos os vértices do grafo
  (`RvsecAnalysisClient.java:527-543`). Assim, chamadores diretos **de biblioteca** também semeiam a
  BFS reversa (`ReachabilityEngine.java:125-126`).
  - Para o desenho da §6.7, C são só os chamadores diretos do app (o `reachability[]` só lista o
    app).
  - A BFS por alvo tem de partir só deles, ou a distância herda as sementes de biblioteca.
- O grafo não tem arestas de ICC nem de ciclo de vida [relato]. Um widget que só navega até a tela do
  alvo fica a distância infinita.

**O que mudar no 7.5** (proposta, a juntar à aberta 1 da verificação):
- calcular d em duas versões do grafo: o grafo inteiro e o subgrafo induzido pelos métodos do app,
  este com e sem a aresta de lambda;
- semear só com C;
- manter a medida dupla do A2: handlers atribuídos × handler que rodou;
- acrescentar a **pergunta sem bind** da análise (§10.2, pergunta 2): a menor distância dos métodos
  executados pela primeira vez num passo prediz a primeira execução de um chamador direto nos passos
  seguintes?
  - Ela não depende do casamento widget → handler, e por isso alcança Compose e os nós sem id.
  - Usa a mesma junção heartbeat × `RVSEC-COV` que o E6 já fez.
- acrescentar a **pergunta da chegada** (§10.3): cada chamador direto dispara na chegada à activity ou
  na interação?
  - É offline, sobre os dados do E6, e não precisa de GATOR.
  - Decide se o lançador e a distância por activity merecem peso igual ao da distância por widget.
  - Ressalva [relato]: a regra (a) das visitas não tem janela de chegada por construção, então só
    R-A2 e (b) separam chegada de interação.

**Custo**: o mesmo do 7.5 (Ver. A1: 21 APKs × três configurações ≈ 22 h somadas, mais as BFS). O
subgrafo do app é filtro sobre o mesmo grafo e não pede outra rodada do Soot.

### R3. Poder estatístico e o desenho da próxima campanha

**O que reproduz** [relato; scripts `sa4/s2_gap.py`, `s3_mdd.py`]:
- a lacuna de 42 chamadores diretos: o máximo por APK entre os cinco braços dá 167, contra 125 no
  braço 2, nos 89 APKs;
- a lacuna de sítios dá 21 contra a **união** dos braços (72 × 51), e 20 contra o máximo por APK;
- os mínimos detectáveis 33,1 / 19,1 / 10,5 e 14,9 / 8,6 / 4,7, sob estas hipóteses:
  - diferença pareada braço 3 − braço 2 por APK;
  - α = 0,025 bilateral;
  - aproximação normal;
  - escala 1/√R.

**O que não se sustenta, ou precisa de ressalva**:
- **"Só uma guia quase perfeita passaria."** A guia teria de recuperar 79 % da lacuna de chamadores e
  71 % da de sítios, com R = 1. Essa lacuna é o máximo de cinco contagens ruidosas, então está
  inflada. A conclusão prática não muda: com R = 1 e contraste por APK, a campanha quase certamente
  não decide.
- **A escala 1/√R** supõe que toda a variância da diferença é ruído de execução dentro do APK. Se
  houver heterogeneidade real APK × braço, ela não cai com R, e os mínimos de R = 3 e R = 10 ficam
  otimistas.
- **O desvio-padrão vem de uma realização dominada por cerca de 13 APKs** com diferença não nula.
- **"O desfecho que a decisão 6 propõe já foi lido no E6 e não se moveu": a citação está errada, a
  conclusão vale** [conferido]:
  - o SQ9 conta, por tarefa, os misuses primários cuja primeira ocorrência vem mais de 5 s depois do
    lançamento (`subq.py:1896-1910`). "Interação" ali é só um corte de tempo, inclui sítios de
    biblioteca e não mede a execução do alvo. Não é o desfecho da decisão 6;
  - o desfecho da decisão 6 tem duas partes, e as duas foram lidas no E6, nos 89 APKs, braço 2 ×
    braço 3 (`rerun-avare/results/{tasks,misuses}.csv`):
    - chamadores diretos executados: 125 × 136, diferença de +11 contra um mínimo detectável de 33.
      A contagem por tarefa é aproximada pelo script da revisão (`cov_directly_reaches_mop` × total
      estático);
    - sítios primários de origem no app durante a interação: 19 × 19;
  - a conclusão "não se moveu" vale, portanto. O que limita o que ela diz é a dose que a própria
    análise registra (§1): 1,10 % dos passos, com widget marcado na tela em 3,88 % deles [relato].
    Um nulo sob uma guia que quase não agiu diz pouco sobre uma guia que agisse.

**As três saídas da análise, com onde cada uma mora:**
- **Desfecho por alvo** (tempo até a primeira execução de cada chamador direto, modelo de risco com
  fragilidade por APK): só análise, no `$P3`. Não muda o APE-RV.
  - Usa o heartbeat e o `RVSEC-COV`, que já existem.
  - Os 32 % de primeiras execuções nos primeiros 5 s são, na maior parte, startup e saem do risco de
    interação.
  - É compatível com a decisão 6: muda o estimador, não o desfecho.
- **R ≥ 3 com orçamento menor** (por exemplo, 3 × 600 s): muda o protocolo, não o código. O custo é
  de máquina: a conta da Ver. §4 (~0,54 h de container por tarefa) tem de ser refeita no `tasks.json`
  antes de virar prazo.
- **Micro-randomização dentro do braço guiado**: muda o APE-RV.
  - Repositório `ape`, `SataAgent` (os dois pontos do atalho MOP) e `MopWidgetPass`: uma moeda por
    decisão com candidato.
  - `event-sink`: o registro da moeda, com o custo em bytes pelo INV-SNK-13.
  - Roda no dispositivo.
  - Estima um efeito proximal, por decisão, e não o efeito do braço. Exige pré-registro da janela w.
  - Como os logs só registram a primeira execução, o alvo sai da amostra depois que roda.

**Recomendação**: desfecho por alvo como estimador principal da decisão 6, com R ≥ 3. A
micro-randomização fica como opção, porque é a única que muda o jar.

### R4. D1: a recomendação desligaria a recuperação D8 inteira

**Fatos.**
- O mecanismo da análise vale [conferido]:
  - `_index_reachability` só indexa quem alcança (`derive:422`);
  - um wrapper presente com `reachesTarget=false` cai na recuperação pela classe (`derive:510-514`).
- Os números valem [relato, recontados com o `derive()` de produção]:
  - 2.681 widgets marcados no corpus;
  - 731 (27,3 %) só pela recuperação;
  - 703 desses 731 no redreader (de 912 marcados nele).
- A recuperação é decisão registrada [conferido]:
  - a gh74 (`proposal.md:18-30`) mostrou que, no `cryptoapp`, o sinal MOP era inerte em todos os
    passos porque o join exato perdia o wrapper;
  - a gh96 (`design.md:184-186`) a manteve como "genuine call-graph gap… 61,057 wrapper handlers…
    fail the exact join".
- **O caso que a motivou é exatamente um wrapper presente com `false`** [conferido no fixture]. Logo,
  a premissa da análise ("o falso de um wrapper é resposta, não lacuna") vale no `aegis` e falha no
  `cryptoapp`. A R1 explica por quê: depende de como o wrapper chama o corpo.
- **Medido no corpus, widget a widget** [conferido]. Para cada listener recuperado, o `dexdump` do
  APK instrumentado dá o método que o wrapper chama de fato. O `derive()` de produção rodou duas
  vezes: como está, e com a recuperação tomando as flags desse alvo em vez do OU da classe.
  - 731 widgets marcados só pela recuperação, em 6 APKs; 703 no redreader;
  - **601 continuam marcados** com o alvo específico: o alvo alcança e o wrapper não, a lacuna do
    `cryptoapp`. 589 deles estão no redreader, vindos de 13 wrappers (por exemplo,
    `RedditPostView$$ExternalSyntheticLambda0.onLongClick` → `RedditPostView.lambda$new$0$…`);
  - **130 caem**: o alvo não alcança e a flag veio das lambdas irmãs, o caso do `aegis` (3 widgets
    lá; 114 no redreader; 6 no packagemanager; 5 no sexytopo; 1 no owncloud e 1 no opencloud).
  - A premissa da análise vale para os 130 e falha para os 601. Cada sessão generalizou o seu APK.
- **A correção proposta ("restringir a assinaturas ausentes do `reachability`") desliga a
  recuperação** [relato]: dos wrappers recuperados no corpus, 0 de 59 ausentes recuperam e 105 de 105
  estão presentes com `false`. Os 731 cairiam, os 601 de lacuna real junto, e o `cryptoapp` voltaria
  a ter MOP inerte.
- **O defeito real é de precisão, e pequeno**: o OU por classe dá ao wrapper as flags das irmãs. A
  primeira versão desta revisão o sustentava com "102 dos 105 wrappers recuperados estão em classes
  com alguma `lambda$…` que não alcança" [relato], que é só a condição para o erro acontecer. O
  tamanho medido é 130 widgets, cerca de 5 % dos 2.681 marcados.

**O texto da spec diverge, o desenho não.** O INV-DRV-01 (`aperv/spec.md:159-161`) diz "no exact
`reachability[].methods[].signature` match". O código e a gh96 querem dizer "sem match entre os
métodos que alcançam". Corrigir o texto é reparo provável, como o A7, e não muda o que se mede. No
`ape`, o cenário do `cryptoapp` em `static-analysis-entrypoints/spec.md` (perto de `:193`) descreve o
wrapper como ausente [relato].

**A correção que preserva o recall** é ligar cada wrapper ao seu `lambda$…` específico, e não à
classe. O wrapper tem uma única chamada ao corpo. Duas vias:
- **No produtor**: a aresta de lambda da §6.5, peça 1, já cobre o caso. Com ela o wrapper alcança
  pelo próprio caminho, e a recuperação deixa de ser necessária. Fica na change do GATOR, sob a
  regra de julho.
- **No produtor, mais barato**: emitir por wrapper a assinatura do corpo que ele chama (campo novo,
  INV-ANA-32 nos dois lados). O derive passa a juntar por ela.

As duas mudam o que é guiado nos 731 widgets: preservam os 601 e tiram os 130. São decisão sua. Para
a §6.7, a regra 2 da agregação herda a imprecisão enquanto a recuperação for por classe.

### R5. D2 é, na maior parte, a WTG que não terminou

**Fatos.**
- 528 widgets marcados (19,7 %) sob chaves de diálogo, em 8 APKs, **502 no `eu.faircode.email`**
  [conferido com o `derive()` de produção]. Os outros: aegis 11, binaryeye 5, wikipedia 4, unchained
  3, libchecker, opencloud e glpi 1 cada.
- 524 deles estão em 7 artefatos sem `complete` e com 0 transições: faircode, aegis, libchecker,
  unchained, binaryeye, opencloud, glpi [conferido]. Sem WTG, todo diálogo é órfão e fica com a
  própria classe como chave. Só os 4 do wikipedia são órfãos dentro de artefato completo.
- A análise leu o D2 como quebra geral do host de diálogo ("quebra na maioria", tabela da §2.1). Em
  número de marcas, é o faircode sem WTG: 95 % das 528.
- 44 dos 163 artefatos não têm `complete`, e carregam 1.550 dos 2.681 widgets marcados (58 %)
  [conferido]; sem o avare, 43 de 162 e 1.542 de 2.673 [relato].
- A spec do `ape` exige `complete == true` (`static-analysis-entrypoints/spec.md:189`, cenário
  `:201-204`). O INV-DRV-08 e o derive aceitam o parcial. O comentário de `MopData.java:204-206`
  ("complete by construction") é falso [relato]. É o D8 da análise, e ele pesa mais que o D2.
- "A órfã com chave própria é registrada (INV-DRV-03)": é só contada em `stats.orphanDialogs`, e
  nenhum log do host nem do jar a imprime [relato].

**O que isso muda.**
- A correção certa é a que a verificação já pôs na change do GATOR (§3.1): o diálogo sai com o host
  = activity que o mostra, no bloco **pré-WTG**. Assim vale também nos 43 artefatos sem WTG.
- A §3.1 da verificação deve dizer isso. Cuidado com a condição de I-17: se a janela sair com tipo
  DIALOG e nome `Host#…`, o `_rekey_dialogs` arrasta o balde do host.
- A divergência de spec do `ape` (`complete == true`) é reparo de texto, a fazer pelo fluxo do `ape`.
  Não muda o que se mede.

### R6. No E6, o LLM decidiu cerca de 37 % das ações do braço MOP+LLM

A primeira versão desta seção dizia "o LLM foi consultado em 90 % dos passos admitidos, não em 70 %"
e concluía que a guia só chegava ao agente pelo marcador. O 0,9 é a configuração, não o que
aconteceu, e a conclusão não vale.

**Fatos** [conferido]:
- `E6-campaign/config/arms.json:66` traz `"llm_percentage": 0.9`, e `:65` traz o prompt `v13`. O
  E5 e o E5b usaram 0,7 (`E5b-inloop/config/arms.json:60`).
- O 0,9 é uma moeda por passo, sorteada só nos passos que passam o portão do LLM
  (`LlmRandomStage.java`: `random.nextDouble() >= percentage` continua a cadeia).
- A ordem do pipeline é Budget → LlmNewState → LlmStagnation → LlmRandom → MopLauncher →
  ComponentTrigger → SataChain (`DecisionPipeline.java:64-76`). O primeiro que decide vence; uma
  resposta nula do LLM continua a cadeia.
- **O que o E6 mediu** (`rerun-avare/report.md`):
  - o LLM foi consultado em **70,9 %** de todos os passos, média por tarefa (mediana 78,4 %; portão
    12; `effective_fraction` = (matched + llm_tap + no_match) / steps, `readers.py:514-520`);
  - no modo aleatório, das 123.596 respostas, 58.900 (47,7 %) foram `no_match`, e 89,8 % dos
    `no_match` são par banido (X5.5). Esses passos caem no resto do pipeline;
  - **decisões por origem** (X5.1): LLM 71.386 ações; algoritmo 121.900, das quais SATA 105.996,
    cobertura 7.567, orçamento 5.669, atalho MOP 868. O LLM decidiu **36,9 %** das ações executadas.
- O "70 %" da análise coincide com a fração consultada, mas ela o leu como decisão.

**Nuances** [relato]:
- os passos do LLM não avançam a cadência do lançador, que dispara menos no braço com LLM;
- o `v13` não mostra visitas. O único sinal de revisita é o histórico, que vem deslocado (R7).

**O que muda.**
- No braço MOP+LLM, cerca de 63 % das ações são escolhidas pelo algoritmo, onde o reforço MOP age
  (SATA, atalho, lançador). A guia não chega só pelo marcador `[DM]`/`[M]`.
- Esses 63 % não são uma amostra dos passos: são, em boa parte, as telas em que o LLM respondeu um
  par banido. O braço mistura dois mecanismos, e o efeito da guia nele não se separa do LLM.
- A razão para deixar o braço com LLM fora da família confirmatória continua, por esse motivo e não
  pelo do marcador. Isso entra no desenho da campanha (aberta 3).

### R7. O histórico do LLM vem deslocado de uma ação

**Fatos** [conferido]:
- em `updateStateInternal` (`StatefulAgent.java:824-859`), `_lastState = currentState` é o estado
  de onde partiu a ação N−1, e `newState` é a tela que ela produziu;
- `resolveNewAction()` escolhe a ação N, e só então `recordActionHistory(action)` grava a entrada
  com o widget de N e o resultado da comparação `newState` × `_lastState`
  (`:1847-1853`), que é o efeito de N−1;
- o prompt imprime o par na mesma linha (`… → result`) [relato, `ApePromptBuilder.java:536-560`].

**Contra o registrado**: a spec principal `exploration/spec.md:580` e o delta da change
(`specs/exploration/spec.md:13`, cenário `:39-41`) dizem "after each action is executed…", com
`result` da própria ação [relato]. É código contra spec, anterior à change. No mesmo método, a
atribuição do resultado ao `currentAction` para o sink e o banimento está certa (`:1090-1114`)
[relato].

**O que muda**: nada a acrescentar. A change de coordenadas já o corrige como decisão D12
(`ape@a695709e`, só artefatos), com um MODIFIED do delta de `exploration` e testes nas tarefas
3.6/3.7 (§5, item 5). A rotação 0 da captura ficou registrada lá como risco fora do escopo.
Repositório `ape`, componente `StatefulAgent`; muda o comportamento do LLM no dispositivo.

### R8. `invoke-super` no weaver: o defeito existe e já está em APKs instrumentados do corpus

**Fatos** [conferido]:
- `DexWeaver.findWrapperReplacement` aceita todo opcode de `isInvokeOpcode`, inclusive
  `INVOKE_SUPER`/`INVOKE_SUPER_RANGE` (`DexWeaver.java:302-320,398-407`).
- `InstructionInjector.replaceInvoke` troca o `invoke-super` por `invoke-static` para o wrapper
  (`InstructionInjector.java:488-512`).
- O wrapper chama o método original por `invoke-virtual`, que volta à sobrescrita.
- **No `org.totschnig.myexpenses_858` instrumentado** (`APKS_INSTRUMENTED_jca_android_dexlib2`):
  - `EncryptionHelper$1` é subclasse de `CipherInputStream`;
  - o `close()` dela, que no fonte é `super.close()`, virou
    `invoke-static {v1}, Lmop/MonitorWrappers;.javax_crypto_CipherInputStream_close`;
  - o wrapper faz `invoke-virtual {v1}, Ljavax/crypto/CipherInputStream;.close`, que despacha de
    volta para `EncryptionHelper$1.close()`;
  - se o caminho rodar, a recursão vai até estourar a pilha.

**Exposição** [relato, varredura dos 348 `head_apks`]:
- só métodos não `final` são afetados: `Cipher`, `Mac` e `Signature` são `final`;
- 6 APKs têm `invoke-super` para um método embrulhado. Em 4 deles, a chamada está dentro da
  sobrescrita do mesmo método:
  - myexpenses, num caminho de backup/restauração cifrada;
  - passportreader, pretix e blau, no `McEliece…KeyPairGeneratorSpi.initialize` do
    spongycastle/bouncycastle, código praticamente morto;
- nenhum teste cobre `invoke-super`;
- o weaver de cobertura não é afetado;
- se algum desses caminhos rodou nas campanhas, não foi conferido.

**No corpus instrumentado** [conferido]: dos 4, só o myexpenses e o passportreader estão entre os
163 de `APKS_INSTRUMENTED_jca_android_dexlib2`. O pretix e o blau aparecem só nos 348 `head_apks`.
No passportreader instrumentado, `McElieceKeyPairGeneratorSpi.initialize(AlgorithmParameterSpec)`
tem o `super.initialize` trocado por
`invoke-static … MonitorWrappers;.java_security_KeyPairGenerator_initialize_2`, e a recursão existe
ali como no myexpenses. A varredura usa uma lista de métodos escrita à mão, maior que a que o weaver
troca: em `PACESecretKeySpec.getKey` (passportreader), o `invoke-super` para
`SecretKeySpec.getEncoded` ficou intacto.

**Proporção**: 4 APKs de 348 `head_apks` e 2 de 163 instrumentados, em caminhos raros. É defeito do
instrumentador (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2`, `dex-mutator`, `DexWeaver`), não
da guia.

**Corrigir não é reparo neutro.** Pular `invoke-super` muda o que se monitora nesses APKs, porque o
evento do `super.close()` deixa de ser emitido. Pela semântica de `call()` do AspectJ, chamada a
`super` não é ponto de junção de chamada [web/conhecimento; citado como semântica, não como
comparação]. A decisão é sua: issue própria, separada do esforço da guia.

#### Por que o wrapper não pode chamar o método da classe-mãe

[conferido: `WrapperEmitter.java:837-897`, `dexdump` do myexpenses; regras da linguagem e do
verificador: web/conhecimento]

- O wrapper é um método estático em `mop.MonitorWrappers`, gerado como **fonte Java** e compilado com
  javac/d8. A chamada original é escrita `recv.<método>(…)` (`:868-874`), uma chamada comum, que
  despacha para a versão reescrita da subclasse.
- `super.m()` só existe dentro de um método de instância da própria subclasse. No DEX, o verificador
  do ART só aceita `invoke-super` quando o alvo está na hierarquia da classe que contém a instrução.
  `MonitorWrappers` não é subclasse de `CipherInputStream`.
- Não há atalho genérico: reflexão (`Method.invoke`) também despacha para a versão reescrita, e
  `MethodHandles.Lookup.findSpecial` exige acesso de dentro da subclasse.

#### As duas correções possíveis

Ambas ficam em `rvsec/rvsec-android/rvsec-instrumentation-dexlib2` e não tocam o APE-RV.

**(1) Não trocar o `invoke-super`.**
- Um filtro em `DexWeaver.findWrapperReplacement` e um teste.
- O `super.m()` fica como está, e o monitor não o vê. O weaver recusa inserir o aviso "depois" no
  próprio ponto (`DexWeaver.java:639-651`), então o evento se perde.

**(2) Acessor dentro da subclasse.** É genérico: vale para qualquer método monitorado não `final`,
com qualquer aridade e qualquer retorno, e não só para `close()`. Para cada ponto em que uma classe
`S` do app faz `super.m(args)`:
1. o instrumentador gera, em `mop`, uma interface por método monitorado afetado:
   `interface Super_T_m { R rvsec$super$T_m(args); }`;
2. a classe `S` passa a implementar a interface, com um acessor escrito direto em DEX: só o
   `invoke-super` para `T.m` e o `return`. É o mesmo truque dos `access$NNN` do javac: o
   `invoke-super` fica onde é permitido;
3. o `WrapperEmitter` gera uma variante do wrapper, em Java, que chama
   `((Super_T_m) recv).rvsec$super$T_m(args)` dentro do mesmo `try/catch` e dos mesmos avisos ao
   monitor. Ela só referencia tipos `mop.*` e da JCA, então compila como os wrappers de hoje;
4. no ponto da chamada, o `invoke-super` vira `invoke-static` para a variante.

A parte difícil (`try/catch`, avisos) continua em Java, e a parte em DEX tem duas instruções. Mexe
em `DexWeaver` (planejamento), `dex-mutator` (acrescentar interface e método a uma classe do app,
o que hoje ele não faz) e `advice-emitter` (interfaces e variantes), com testes novos: `invoke-super`
e `/range`, com retorno, lançando exceção.

Cuidados da correção (2):
- cada acessor é um método a mais no DEX da classe `S`, o que pesa no limite de 64K métodos;
- `invoke-super` para método *default* de interface (`X.super.m()`) pede tratamento próprio ou
  exclusão explícita.

#### A contagem dupla de eventos: o risco que decide entre (1) e (2)

**O que é.** Uma subclasse `S` reescreve `m` e chama `super.m()` dentro dela. Se o app também chama
`obj.m()` sobre esse objeto num ponto que o weaver instrumenta, uma única operação lógica gera **dois
eventos** para o monitor: um na chamada externa e outro no `super.m()` interno. Com a correção (2),
os dois são entregues. Com a (1), só o externo.

**Por que importa.** Se o evento não é repetível na propriedade da spec, o segundo vira violação
falsa. O caso concreto [conferido, `rvsec/rvsec-mop/src/main/resources/jca_android/CipherInputStreamSpec.mop`]:
- a propriedade é `ere : c1 (r1 | r2)+ cl1`;
- um segundo `cl1` não é palavra da expressão e vai para o `@fail`, que reporta
  `CIPHERINPUTSTREAM-ORDER-00`;
- o mesmo vale, em princípio, para qualquer spec cujo evento só aparece uma vez na expressão
  (`close`, a criação). Eventos repetíveis, como as leituras `(r1 | r2)+`, não geram violação.

**Quando acontece.** Só quando os **dois** pontos são instrumentados:
- a chamada externa tem de estar tipada como a classe monitorada (ou subtipo resolvido pelo alias de
  subtipo do weaver);
- uma chamada externa tipada como `InputStream`, por exemplo, não é instrumentada, e não há dupla.

**O que se sabe nos APKs com o padrão.**
- **myexpenses** [conferido no `dexdump` do APK instrumentado]: o wrapper
  `javax_crypto_CipherInputStream_close` tem **um único** ponto de chamada no APK inteiro, o
  `super.close()` dentro de `EncryptionHelper$1.close()`. Não há dupla. Aqui a correção (1) **perde o
  único `close`** que o monitor vê, e a (2) entrega exatamente um.
- **passportreader** (`McElieceKeyPairGeneratorSpi`, spongycastle) [conferido no `dexdump` do APK
  instrumentado e na spec]:
  - `initialize(int, SecureRandom)` chama `this.initialize(spec)`, e essa chamada também foi trocada
    pelo wrapper `initialize_2`. Ela é instrumentada independentemente do `invoke-super`;
  - a `KeyPairGeneratorSpec` (`jca_android`, `:476`) aceita exatamente um `initialize` entre o
    `getInstance` e o `gen`:
    `ere: ((g3 | g4)* g1 | (g3 | g4)* g2) (init1 | init2 | init3 | init4 | initError | initError2) gen`;
  - se o app chama `kpg.initialize(n, random)` sobre um gerador McEliece, o monitor vê `init2` e
    depois `init3`, e reporta uma violação de ordem. Isso vale **com qualquer das duas correções**:
    a (1) deixa os dois eventos, e a (2) acrescenta um terceiro. A dupla contagem aqui vem de
    código de biblioteca que estende a classe monitorada e chama os próprios métodos monitorados,
    não do `invoke-super`;
  - o código McEliece é praticamente morto.
- **pretix, blau**: fora dos 163; não verificados.

**Consequência para a escolha.**
- Nenhuma das duas correções é neutra:
  - a (1) perde eventos onde o `super.m()` é o único ponto instrumentado, como no myexpenses;
  - a (2) duplica eventos onde a chamada externa também é instrumentada.
- Uma correção que acerte os dois casos teria de entregar o evento do `super.m()` **só quando** a
  chamada externa sobre o mesmo objeto não foi instrumentada. Isso é decisão de semântica (o que é um
  "evento" para a spec), não de mecânica do weaver.
- **Antes de decidir**, medir sem rodar nada no dispositivo: para cada um dos pontos `invoke-super`,
  ler no `dexdump` do APK instrumentado se existe chamada externa instrumentada ao mesmo método sobre
  a mesma classe. Para cada spec envolvida, ler se o evento é repetível na propriedade. O myexpenses
  e o passportreader já estão medidos acima; os outros dois estão fora dos 163.
- O passportreader mostra que o problema da contagem dupla é mais largo que o `invoke-super`: toda
  subclasse de biblioteca que chama os próprios métodos monitorados gera eventos internos. Medir isso
  no corpus é outra pergunta, também só por leitura do `dexdump`.
- Proporção: 2 dos 163 APKs instrumentados, em caminhos raros. É issue do instrumentador, fora do
  esforço da guia, e a decisão é sua quando a execução for liberada.

### Variantes de carimbo (§4 da análise)

[relato, salvo o indicado]
- **A tag de log**: a captura aceita `RVSEC`, `RVSEC-COV` e `ApeRvHb`, mas a lista está em
  `rv-android-core/…/logcat_manager.py:80-81`, não no rv-platform. Uma tag nova toca o INV-PLT-21 e o
  INV-CORE-37. O E1 usou `RVSEC` com prefixo `E1 ` (`20260806_compose_e1_resultado.md:183`).
- **"A Variante B não convive com os monitores no mesmo APK"**: não vale como limite de arquitetura.
  O descritor aceita um `before` a mais. O E1 usou o APK original porque o do corpus já tinha os
  monitores, e uma segunda passada sobre APK instrumentado não foi testada.
- **"Os limites no momento do set são 0"**: vale para listeners postos no `onCreate`, antes do
  layout; não vale para `onBindViewHolder` nem para listeners postos depois do layout.
- **"41–45 `setAccessibilityDelegate` por APK"**: varia (9 a 47 em três APKs). O argumento contra a
  Variante A continua, sem o número.
- **"87 de 87 com `AbstractClickableNode.onClick` legível"**: confirmado em 5 de 5 da amostra.
- **"O 7.5 de hoje é circular"**: em parte. O handler que rodou vem do `RVSEC-COV`, não do mapa do
  GATOR. O mapa só define os candidatos, e o que roda fora deles fica invisível.
- **"A Variante A não deve vir antes do 7.5"**: já decidido (Ver. §1, direção do bind depois do 7.5).
- **Variante B+ como portão antes do GATOR**:
  - ela muda o instrumentador (`rvsec-instrumentation-dexlib2`, um passo novo no estilo do
    `CoverageWeaver`);
  - exige execução nova no dispositivo, porque os APKs do E6 não têm o probe. Não é offline;
  - roda pelo rv-platform; o custo é de campanha, por tarefa, e não foi medido;
  - dá o handler de todo clique, não só da primeira execução;
  - a alternativa só de medição é a verdade de campo atual: 13 dos 21 APKs, View, com a medida dupla
    do A2.

  A sua reserva quanto ao instrumentador e o "nada roda agora" a deixam como opção para o caso de o
  7.5 sair inconclusivo, não como portão.

### R9. Marcador do prompt × pontuação

Vale, com três casos concretos [relato, `MopScorer.java:65-84,191-206`, `MopData.java:782-797`]:
- um contêiner ou filho recebe reforço por contenção (até dois níveis) e não mostra marca;
- um widget direto só para clique longo aparece `[DM]`, e o clique dele recebe +300 ou nada;
- uma entrada por evento `none` mostra a marca, e o reforço é 0.

A verificação (§7.2) já dizia que, com a §6.7, o marcador precisa de regra própria. Estes casos
dizem que a regra precisa existir já, se o braço com LLM ficar na campanha.

### R10. A sobre-atribuição: as causas existem, e o custo do `LocalPacker` está na validação

[relato, com `ListenerInstance.java:63-67` conferido]
- **CHA no tipo declarado do listener** (`computePossibleListenerTypesCHA`): explica as chaves com
  vários handlers quando o local é declarado como interface (`View$OnClickListener`). **Não explica o
  caso do `aegis`**: lá o local tem o tipo concreto do wrapper, e o espalhamento é do lado da view
  (um handler em 4 widgets).
- **`LocalPacker`**: em `DexBody` ele é chamado direto, `LocalPacker.v().transform(jBody)`, fora do
  `PackManager` (`soot/dexpler/DexBody.java:869`, checkout local do Soot) [conferido], então
  `-p jb.lp enabled:false` não o desliga. Junto com o fluxo insensível a fluxo do GATOR (um nó por
  local), é a explicação provável do lado da view [hipótese].
  - O conserto não exige mexer no Soot. O GATOR controla os corpos que lê (`retrieveActiveBody` em
    `Hierarchy`, `FlowgraphRebuilder` e outros) e pode separar os locais (`LocalSplitter`, que divide
    um local por teia def-uso) antes do SPARK. É código pequeno, na change do GATOR.
  - O custo está em outro lugar: a causa ainda é hipótese, e a separação muda os nós do PAG e do
    fluxo de GUI do corpus inteiro. Validar pede re-análise e comparação. A primeira versão desta
    revisão dizia "custo médio, não pequeno", e a análise dizia "custo pequeno"; as duas eram
    palpite.
- **Callbacks herdados**: estruturalmente vale (`Flowgraph.java:141-157`).

O A2 da verificação continua sendo o ponto: o 7.5 mede se a sobre-atribuição contamina a distância.
Se contaminar, a correção ganha portão e entra na change do GATOR.

### R11. Compose: o `compose-probe` não dá o par tela → handlers, e o E1 não diz o que está na tela

- **O `compose-probe` atribui origem só a `navigate`/`backstack_add`** (172 de 689 nos 87 APKs
  Compose/mistos) [relato]. Não existe tripla tela → handler → alcance. A §4.3 do relatório ("esse par
  sai") está errada, e o C1 precisa de um grafo de chamadas entre composables.
- **A identidade de composable do E1 acumula** [conferido: `TRACED` só recebe `add`]. Ela diz o que
  já foi composto, não o que está na tela. O doc de 06/08 (`20260806_compose_e1_resultado.md:25`)
  afirma o contrário.
- **Switch e Checkbox passam pelo `AbstractClickableNode`** (`ToggleableNode` é subclasse de
  `ClickableNode`), mas o `onClick` guardado é um wrapper do Compose, não a lambda do app [relato,
  `dexdump` do `parceltracker`]. O E2 tem de ler o handler um nível adiante nesses nós.
- **"Manter o `compose-probe`"**: ele mora em `rvsec-study03-artigo` (repositório do artigo). Para
  alimentar o APE-RV, ele teria de ir para o pipeline do rvsec, num módulo próprio ou no GATOR.
  - O relatório (§4.3) já disse que a regra do rv-android genérico não impede o porte.
  - A escolha de onde ele mora é sua e não muda a ordem: C1 e E2 esperam o C0.

### R12. Correções menores e confirmações

- **§6.6 do relatório, "sobrevive ao refinamento"** [conferido `widgetId` → `toXPath()`; relato sobre
  os namers]:
  - a novidade por activity sobrevive à divisão de estado (`StateKey` novo, `Name` igual);
  - não sobrevive ao refinamento de ação, que troca o namer e muda a XPath;
  - o mesmo vale para o limite de 3 escolhas MOP (`mopPickKey`) e para a chave do banimento do LLM.

  A decisão 9 continua de pé, porque ordenar pelo inédito na activity ainda é melhor que pelo inédito
  no estado. Muda a frase.
- **Passo 0 do EARLY_STAGE** [conferido]: o código usa "não saturado" (`StateActionDiffer.java:50-56`)
  e a spec diz "unvisited" (`action-selection/spec.md:219`, INV-SEL-MOP-03 em `:221`). Uma ação já
  visitada com vários nós continua elegível. É divergência de texto, a registrar no `ape` quando a
  change do atalho ordenado (decisão 9) for aberta, porque ela mexe exatamente nesse caminho.
- **A roleta**: o "550 × 50" exagera, como mostra o I-49. Isso não muda nada no plano.
- **Toques do LLM fora da árvore** viram a chave única `MODEL_LLM_TAP` no rastreador [relato]. O
  contador de aposentadoria da §6.7 nunca os veria.
- **`getActivityCoverageGap`** não tem consumidor fora dos testes [relato].
- **INV-MOP-14** só está definido no arquivo da gh13 [relato]. Mesma situação do A8 da verificação
  (INV-DRV-05/06, INV-SNK-13).
- **A regra do esqueleto** existe, mas não cita a pasta `20261005_e6_graduacao_marca` [relato]. Vale
  pela regra geral se o artigo citar M14–M17. Nada a fazer daqui; o artigo e o esqueleto não se tocam.

---

## 3. Contra as decisões registradas

| proposta da análise | decisão registrada que toca | leitura |
|---|---|---|
| restringir a recuperação D8 (D1) | gh74 `proposal.md:18-30`; gh96 `design.md:184-186`; INV-DRV-01 | contradiz o registrado e desligaria a recuperação (R4). Não propor como está |
| resolver o host do diálogo sem WTG (D2) | INV-DRV-03; Ver. §3.1 (06/10) | coerente com a §3.1; é a mesma peça |
| portão de recall no C0 | C0 adiado (05/10); decisão 8 depois do C0 | não muda a ordem; muda o portão |
| distância com BFS restrita ao app | regra de julho (`20260729_propostas_melhorias_e3.md:10`); decisão 7 | entra na cópia descartável do 7.5; código só na change do GATOR |
| micro-randomização | decisão 6 (desfecho primário da próxima campanha); A6 | não contradiz o desfecho; muda a unidade e o jar. Decisão sua |
| braço com LLM fora da família confirmatória | nenhuma decisão de campanha nova registrada; Ver. §7.2 propõe fork × MOP e MOP × MOP+LLM | aberta 3 |
| Variante B+ antes do GATOR | reserva quanto ao instrumentador; "nada roda agora" (06/10) | opção, não portão (R8) |
| Variante A depois do 7.5 | Ver. §1 (direção do bind depois do 7.5) | já decidido |
| lançador ordenado por distância mantendo o rodízio | INV-CT-14 (`component-triggering:182`), `:175`; Ver. §1 ("não aposentar") | coerente: ordena, não age sobre o resultado |
| voltar a estado visto com widget perto do alvo (§10.1) | nenhuma | proposta nova; muda o `ape` (`Graph.findShortestPaths`, `SataAgent`), no dispositivo; depende do 7.5 |
| manter o `compose-probe` | C1 e E2 esperam o C0 (05/10); rv-android genérico | não muda a ordem; o lugar do código é decisão sua (R11) |
| corrigir a §4.2, §4.5, §6.6 e §3.5 do relatório | §7–§9 do relatório a reescrever num commit pedido | entram na lista da §4 |
| issue do `invoke-super` | nenhuma | nova; decisão sua |

Nenhuma proposta da análise re-propõe algo que você já recusou: a aposentadoria de alvo de lançamento
e a inferência de extras não aparecem como recomendação.

---

## 4. Edições propostas (texto, não aplicado)

### 4.1 Ao relatório

1. **§4.2, "O mecanismo que isso torna plausível"**: trocar o primeiro item por "O GATOR roda SPARK
   com `all-reachable:true`. Ponto de entrada não recebe points-to nos parâmetros, mas, com as
   exclusões inertes, o corpo da biblioteca funde as alocações reais do app num mesmo parâmetro,
   campo ou fila (o `_block` de `ComposableLambdaImpl`, o `onClick` de `ClickableElement`, as filas de
   corrotina), e um `invoke` alcança todas." Acrescentar ao último parágrafo: "A correção também tira
   recall: lambda chamada só pela biblioteca perde a aresta de entrada, e o `this` dela fica vazio."
2. **§4.5, C0**: trocar o portão por "o C0 só mede: reproduz a linha de base, tempo e queda de
   `reachesTarget` por estrato. A queda mistura caminho falso removido com caminho verdadeiro perdido;
   o veredito sai do 7.5 ampliado (decisão de 06/10)". Acrescentar: "`kotlinx.*` não está no
   `libPackages.txt`; dizer em cada braço se entra". Na §8 e na §9, a decisão 8 passa a "depois do
   7.5". Na C1, trocar "`minHops`, que a BFS reversa já
   calcula e descarta" por "`minHops`, que sai da mesma BFS guardando o nível (hoje ela só guarda o
   conjunto visitado)".
3. **§4.3, "Leitura"**: trocar "esse par sai" por "saem telas e handlers, mas não o par: o
   `compose-probe` só atribui origem a sítios de navegação (172 de 689). O C1 precisa de um grafo de
   chamadas entre composables a partir da lambda de cada destino".
4. **§6.6, tabela, linha `activityInteracted`**: "Sim" → "Sim para divisão de estado; não quando o
   refinamento de ação muda o `Name` (a XPath muda). O mesmo vale para o limite MOP."
5. **§6.7, "O produtor"** e **agregação, item 2**: dizer que a BFS atravessa a biblioteca e é semeada
   também por chamadores diretos da biblioteca; que a distância por alvo parte só de C; e que a
   recuperação D8 por classe dá ao wrapper a menor distância das lambdas irmãs enquanto não houver
   ligação wrapper → corpo.
6. **§6.7, "O lançador"**: acrescentar "mantendo o rodízio dentro de faixas de distância; ordenar sem
   rodízio pediria sempre a activity mais próxima que não abre (INV-CT-14)".
7. **§7.5**: acrescentar as configurações sobre o subgrafo do app, a semente só em C, a pergunta sem
   bind e a pergunta da chegada (R2).
8. **§3.5 ou §6.10**: "O GATOR não modela o `AlertDialog.Builder` do AppCompat nem o Material,
   DialogFragment, DataBinding/ViewBinding nem RecyclerView. Um `new X` com X subclasse de
   `android.app.Dialog` no código do app é modelado."

### 4.2 À verificação

1. **§3.1**: trocar "a mesma passada de coleta de widgets que o F1/F2 estende" por "a mesma passada
   de coleta de widgets, com modelos novos: builder do AppCompat/Material, DialogFragment, binding e
   RecyclerView não existem hoje (custo médio a grande)". Acrescentar: "o host sai no bloco pré-WTG,
   para valer nos 43 artefatos sem WTG, onde estão 524 das 528 marcas presas a chave de diálogo; e a
   janela não pode sair com tipo DIALOG e nome `Host#…`".
2. **§3, mapa, linha "id sob outra janela"**: acrescentar "a maior parte é WTG ausente (R5)".
3. **§8, aberta 4**: registrar que o histórico deslocado (R7) já entrou na change como D12
   (`ape@a695709e`), e que a rotação da captura ficou lá como risco fora do escopo.
4. **§7.2, "Desenho de campanha"**: no braço MOP+LLM do E6, a moeda era 0,9 (`arms.json:66`), o LLM
   foi consultado em 70,9 % dos passos e decidiu 36,9 % das ações; o algoritmo decidiu o resto (R6).

### 4.3 À análise (para a outra sessão, se for revisá-la)

- §1, linha 66: o SQ9 não é o desfecho da decisão 6; com as medidas dele (125 × 136 chamadores
  diretos, 19 × 19 sítios de app na interação) a conclusão se mantém (R3).
- §2.2, D1: a premissa vale em 130 dos 731 widgets e falha em 601; a correção desligaria os 731
  (R4); o defeito é o OU por classe.
- §2.2, D2: a causa é a WTG ausente, e 502 das 528 marcas são do faircode (R5).
- §4, tabela: os números de `setAccessibilityDelegate` e a incompatibilidade de B com os monitores.
- §4.1: o defeito está em 2 dos 163 APKs instrumentados (4 dos 348 `head_apks`), não só latente.
- §5: a regra do "não clicar duas vezes" está certa; o histórico deslocado é anterior à change.
- §6.1: o LLM decidiu 36,9 % das ações do braço, não 70 % dos passos admitidos; a guia não chega só
  pelo marcador (R6).
- §6.3: 21 é contra a união; "quase perfeita" → "70–80 % de uma lacuna inflada".
- §9: 1.101 → 1.114; Switch e Checkbox passam pelo `AbstractClickableNode`.
- §10.3: 267 inclui 5 de `pre_exploration`; a regra (a) não tem janela de chegada por construção.

---

## 5. Suas decisões, atualizadas

Decididas antes e mantidas: as da Ver. §1 e §8. Nada aqui as reabre.

**Decididas em 06/10, nesta sessão:**
- **7.5 ampliado** (item 2 abaixo, opção a): grafo inteiro e subgrafo do app, com e sem aresta de
  lambda; semente só nos chamadores diretos do app; a pergunta sem bind e a pergunta chegada ×
  interação; mantida a medida dupla do A2.
- **D1** (item 3, opção a + b): corrigir agora só o texto do INV-DRV-01 (reparo, junto da correção já
  decidida da spec `analysis`, quando você mandar abrir); ligar cada wrapper ao seu corpo na change do
  GATOR.
- **Portão do C0** (item 1, nova forma): **o C0 só mede**.
  - Ele confere que a linha de base reproduz o `.apk.json` vigente, e mede o tempo e a queda de
    `reachesTarget` por estrato, sem aprovar nem reprovar.
  - O veredito sai do 7.5 ampliado. Lá, o que a correção das exclusões tira e a aresta de lambda
    devolve é caminho verdadeiro perdido; o que não volta é candidato a caminho falso removido; e a
    verdade de campo do E6 julga.
  - Consequência: a decisão 8 (corrigir o `-exclude`) passa de "depois do C0" para "depois do 7.5".
  - A razão, em exemplo:
    - `LoginViewModel.onLogin()` → `viewModelScope.launch { repo.encrypt(senha) }` → `Cipher` é um
      caminho verdadeiro que a correção corta;
    - `SettingsScreen` → `Button(onClick = …)` → lambda de outra tela → `Cipher` é um caminho falso
      que a correção remove;
    - os dois aparecem como a mesma queda de `reachesTarget`.
- **Forma da próxima campanha** (item 4; os braços fecham depois do 7.5):
  - os 89 APKs;
  - 3 execuções de 600 s por APK e por braço, no lugar de 1 de 1800 s, com o mesmo tempo de
    dispositivo por braço;
  - o desfecho da decisão 6, contado por alvo: o segundo da primeira execução de cada chamador direto
    em cada execução;
  - o braço com LLM, se entrar, é exploratório.
  - Proposta de braços, a fechar depois do 7.5: (1) sem guia; (2) marca sim/não do E6 + atalho
    ordenado; (3) distância + atalho ordenado. Principal 3 × 1, secundário 3 × 2.
  - A razão do orçamento [conferido, `20261003_e6_dose_orientacao/m6_steps_methods/analyze.out`,
    Parte 3]: nas tarefas com algum chamador direto executado, a mediana da última primeira execução
    foi 59–97 s, 4–10 % da execução de 1800 s.
  - O custo de máquina tem de ser conferido no `tasks.json` antes de virar prazo.

**Abertas, com recomendação:**

1. **Portão de recall no C0** (R1).
   - Opções: (a) acrescentar o critério estático de caminho mais a verdade de campo do E6; (b) só a
     verdade de campo do E6; (c) manter o portão de hoje.
   - Recomendo (a): a verdade de campo não alcança Compose nem corrotinas, onde a perda é maior.
2. **Configurações do 7.5** (R2; junta-se à aberta 1 da verificação, a medida dupla do A2).
   - Opções: (a) grafo inteiro e subgrafo do app (com e sem aresta de lambda), semente só em C, mais
     as perguntas sem bind e da chegada; (b) só o desenho de hoje, mais o A2.
   - Recomendo (a): o filtro roda sobre o mesmo grafo, sem outra rodada do Soot.
3. **D1, a recuperação D8** (R4).
   - Opções: (a) manter como está e só corrigir o texto do INV-DRV-01; (b) ligar cada wrapper ao seu
     corpo, na change do GATOR (aresta de lambda ou campo novo); (c) restringir a assinaturas
     ausentes, como propõe a análise.
   - Recomendo (a) agora e (b) na change do GATOR: (b) preserva os 601 widgets de lacuna real e
     tira os 130 herdados. (c) desliga a recuperação inteira.
4. **Desenho da próxima campanha** (aberta 3 da verificação; R3, R6).
   - Opções de estimador: (a) desfecho por alvo (tempo até a primeira execução), com R ≥ 3; (b)
     contraste por APK, com R ≥ 3; (c) micro-randomização, que muda o jar.
   - Opções para o braço com LLM: dentro ou fora da família confirmatória.
   - Recomendo (a) e o braço com LLM fora da família confirmatória: nele o LLM decide cerca de 37 %
     das ações e o algoritmo decide o resto, sobretudo nas telas em que o LLM respondeu par banido,
     e o efeito da guia não se separa do LLM (R6).
5. **Change `llm-coordinate-single-base`** (aberta 4 da verificação; R7): **já resolvido no `ape`**.
   - O histórico deslocado entrou como decisão D12, comitada em `ape@a695709e` (só artefatos; `src/`
     intocado). [conferido: commit, `design.md:277`, cenários em `specs/exploration/spec.md:62,68`;
     o resto é relato da sessão `aperv`.]
   - O delta de `exploration` é um MODIFIED que torna a spec principal verdadeira; as tarefas 3.6/3.7
     o testam.
   - A tarefa 8.2 passou a reportar também a parcela de ações executadas cuja decisão veio do LLM.
   - A rotação 0 da captura ficou só como risco, fora do escopo: o smoke roda em retrato.
6. **Issue do `invoke-super`** (R8).
   - Opções: (a) abrir issue no rvsec agora, sem change; (b) registrar e decidir depois; (c) nada.
   - Recomendo (b): nada roda agora, e o conserto muda o que se monitora em 2 dos 163 APKs.
   - Quando decidir: há duas correções, (1) não trocar o `invoke-super` e (2) acessor na subclasse,
     e **nenhuma é neutra por causa da contagem dupla** (R8):
     - a (1) perde o único `close` do myexpenses;
     - a (2) duplica o evento onde a chamada externa também é instrumentada, e um `close` duplicado
       viola o `CipherInputStreamSpec`.
     - no passportreader, as duas deixam uma contagem dupla de `initialize`, que vem de
       `this.initialize(spec)` dentro do Spi e não do `invoke-super`;
     - medir antes, só por leitura do `dexdump`, quantas subclasses de biblioteca chamam os
       próprios métodos monitorados.
7. **Correções de texto de spec**, todas reparo provável, nenhuma muda a medição:
   - INV-DRV-01, no rv-android;
   - `complete == true` em `static-analysis-entrypoints`, o cenário do `cryptoapp` e o comentário de
     `MopData.java:204-206`, no `ape`;
   - "unvisited" no passo 0, no `ape`.

   Recomendo juntá-las à correção já decidida da spec `analysis` (A7), quando você mandar abrir. As do
   `ape` vão pelo fluxo de lá.
8. **Variante B+ como portão** (R8).
   - Recomendo não: exige execução nova e mudança no instrumentador. Fica para o caso de o 7.5 sair
     inconclusivo.

**Continuam abertas, da verificação**: limiar do 7.1 ampliado (2); commit das edições do relatório e
da verificação (5), agora com as da §4 deste documento.

---

## 6. Proveniência

- **Reaberto por mim**:
  - GATOR: `Main.java:205-246`; `Configs.java:74`; `rv_static_analysis/config.py:104-105`; log
    `rvsec-dataset/jca_android/sa_state/logs/app.clauncher_430.apk.log` (`cgAlgorithm spark`);
    `RvsecAnalysisClient.java:466-484,497-525`; `ListenerInstance.java:50-67`;
    `lib/gator/libPackages.txt:110,1425`.
  - Soot: `soot/src/main/java/soot/Scene.java:2049-2060`; `MethodPAG.java:228-300` (checkout 4.4.0;
    o bytecode do 4.7.1 é relato).
  - Consumidor: `derive_mop_artifact.py:378-430,466-518`; `openspec/specs/aperv/spec.md:150-170`;
    gh96 `design.md:180-192`; gh74 `proposal.md:18-30`; `tests/fixtures/cryptoapp.apk.json`;
    `complete` e `transitions` dos 8 `.apk.json` do D2; `20260803_compose_d1_decisao_plano_rearch.md:134-176`.
  - `ape`: `StatefulAgent.java:824-860,1820-1860`; `DecisionPipeline.java:60-80`;
    `StateActionDiffer.java:46-60`; `action-selection/spec.md:215-222`; `Model.java:592-606`;
    `UICoverageTracker.java:238-248`.
  - E6: `rerun-avare/report.md:70-100`; `subq.py:1890-1912`; `arms.json:60-70`.
  - Tese: `20261005_e6_graduacao_marca/README.md:55-80`, `m9_robust.py:1,20`.
  - E1: `backup/e1-compose-probe/monitor-src/mop/ComposeProbeRuntimeMonitor.java:84-88,200-214,432`;
    `20260806_compose_e1_resultado.md:25`.
  - Instrumentador: `DexWeaver.java:302-320,398-407`; `InstructionInjector.java:488-512`; `dexdump`
    do `org.totschnig.myexpenses_858.apk` instrumentado (`EncryptionHelper$1.close` e
    `MonitorWrappers.javax_crypto_CipherInputStream_close`).
- **Subagentes** (relato; scripts em
  `/tmp/claude-1000/…/6290e234-…/scratchpad/sa1`–`sa5`, fora do repositório):
  - consumidor APE-RV (C1–C22);
  - contrato e derive (D1–D8, V1–V4), recontado com o `derive()` de produção sobre os 163 `.apk.json`;
  - GATOR (G1–G15), com `javap` sobre o `soot-4.7.1.jar`;
  - estatística, E6 e Compose (S1–S13);
  - instrumentador e logs (I1–I9), com varredura dos 348 `head_apks` e `dexdump` de 3–5 APKs.
- **Reaberto na re-investigação** (segunda sessão de 06/10; scripts em
  `/tmp/claude-1000/…/31474112-…/scratchpad/`, fora do repositório):
  - D1: `d1/rec.py`, `d1/widgets.py`. O `dexdump` (build-tools 35.0.1) dos 163 APKs instrumentados
    dá o alvo de cada wrapper; o `derive()` de produção roda com a recuperação por classe e com a
    recuperação pelo alvo específico. Fixture `cryptoapp.apk.json` com `apks_examples/cryptoapp.apk`.
  - D2: `d2.py`, `derive()` de produção sobre os 163 `.apk.json`, contando as marcas sob chave de
    janela DIALOG que não é activity.
  - E6: `arms.json:55-75` (E6) e `E5b-inloop/config/arms.json:60`; `LlmRandomStage.java` (`ape`
    `a695709e`); `rerun-avare/report.md` X5.1, X5.5, portão 12 e X6.4; `readers.py:514-520`.
  - Decisão 6: `rerun-avare/results/{tasks,misuses}.csv`, com o `sa4/s2_gap.py` da primeira sessão
    e a contagem por `origin`.
  - `invoke-super`: `dexdump` do passportreader e do myexpenses instrumentados;
    `rvsec-mop/…/jca_android/KeyPairGeneratorSpec.mop:476`; `sa5/scan_all.tsv` da primeira sessão.
  - `LocalPacker`: `soot/src/main/java/soot/dexpler/DexBody.java:869` (checkout local,
    `4.2.1-828-g9ae4bab678`); `retrieveActiveBody` no GATOR.
- **Não lidos, por regra**: os `docs/analise_*` e o prompt da sessão do `ape`
  (`ape/docs/20261006_prompt_analyze_mop_guide_plan_review.md`).
- **Antes de usar este documento**: confira o `ape` (`git log -1`), porque a sessão de lá analisa a
  mesma análise e pode ter mudado specs, change ou código.

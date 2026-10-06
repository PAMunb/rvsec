# Análise do plano para a guia MOP: GATOR, consumidor, instrumentador e base de coordenadas

**Data**: 06/10/2026.
**Objeto**:
- o relatório `docs/20261005_gator_fragments_compose_guia_teste.md` ("o relatório");
- a verificação `docs/20261005_verificacao_plano_gator_compose.md` ("a verificação");
- a change `ape/openspec/changes/llm-coordinate-single-base` (`ape@43664568`).

**Natureza**: só leitura. Nada rodou: nem GATOR, nem docker, nem emulador, nem build. Nada foi comitado.

**Perguntas**:
1. As mudanças resolvem o problema?
2. Com que confiança?
3. O contrato casa ponta a ponta: o GATOR salva X, o APE-RV recupera exatamente X e usa X?
4. Como, e se, a exploração melhora?

**Rótulos**:
- **[conferido]**: aberto por mim nesta sessão.
- **[relato]**: trazido por subagente e não reaberto por mim.
- **[hipótese]**: inferência.

Seis subagentes cobriram:
- o contrato de dados;
- o produtor (GATOR);
- o consumidor (APE-RV);
- o instrumentador;
- a change de coordenadas;
- a lógica causal e o poder estatístico.

Os scripts de leitura que eles escreveram estão no scratchpad da sessão. Não fazem parte do repositório.

---

## 0. Resposta curta

1. **Explicar o E6 não depende de nenhuma dessas mudanças.** A fraqueza da guia no E6 já está explicada pelo que foi medido:
   - a dose: o MOP mudou a escolha, ou o lançador saltou, em 1,10 % dos passos;
   - o casamento: 17,3 % dos cliques caem num widget estático;
   - a marca saturada: nenhum handler a 0 saltos, 41 % marcados por via transitiva;
   - o teto do desfecho: 33 sítios no startup, e 29 APKs em que nenhum chamador direto rodou.

   As mudanças servem a um próximo estudo. No artigo, entram como trabalho futuro, não como explicação.
2. **O plano ataca as causas certas, mas duas premissas técnicas mudam:**
   - **O mecanismo da saturação não é o que a §4.2 descreve.** No SPARK, os parâmetros de um ponto de entrada ficam **vazios**, não "sem restrição". O leque continua plausível, mas por fusão insensível a contexto das alocações reais. E a correção das exclusões também **tira recall**: lambdas chamadas só pela biblioteca perdem a aresta de entrada e o `this`.
   - **A distância não está pronta para ser calculada.** A BFS não guarda nível, e ela atravessa a biblioteca. Uma distância calculada assim satura pelo mesmo leque.
3. **O contrato X → X funciona no caso comum e falha em pontos concentrados.**
   - **Casam exatamente:** activity e `shortId`.
   - **Casa de forma aproximada:** a ligação handler → flag.
   - **Falham:** uma regra do derive marca 27 % dos widgets marcados contra um "falso" explícito do produtor, em 4 APKs. E 19,7 % dos marcados ficam sob chave de diálogo, que nunca casa em runtime.
   - **Fragments com `Host#Fragment`:** casariam exatamente, sob duas condições (§2).
4. **Mesmo com tudo funcionando, uma campanha com contraste agregado por APK quase certamente não resolve.**
   - Nos 89 APKs, a lacuna conhecida é de 42 chamadores diretos e 21 sítios de violação durante a interação.
   - O mínimo detectável com uma repetição é de cerca de 33 chamadores e 15 sítios.
   - Só uma guia quase perfeita passaria o limiar.
   - O que tem poder é medir **por decisão** (micro-randomização) ou **por alvo** (tempo até a primeira execução).
5. **Instrumentador.** A sugestão que mais vale é a **Variante B**, de preferência na forma B+: um carimbo que só mede, sem guiar. Ela dá a verdade de campo do bind e do experimento 7.5, que hoje é a mais fraca da cadeia. A Variante A (guiar pelo carimbo) não deve vir antes do 7.5. Achou-se também um defeito latente no weaver: `invoke-super` vira chamada virtual ao wrapper (§4.1).
6. **Change de coordenadas.**
   - **Resolve o defeito que descreve**, com confiança alta no mecanismo e média-baixa na magnitude.
   - **Deixa dois problemas vizinhos conferidos:** o histórico grava o resultado da ação anterior na entrada da ação nova, e a captura em paisagem usa rotação 0.
   - **Toca a guia MOP quase nada** (§5).

---

## 1. O que precisa ser explicado, e o que já está

**O que o E6 decidiu.** O contraste C2 (braço 3 contra braço 2) dá IRR 1,012 [0,897; 1,142], e o mínimo detectável é 1,18 (`rvsec-study03-replication-package/experiments/E6-campaign/rerun-avare/report.md:79`) [conferido]. O desfecho de interação, SQ9, dá C2 = 0,990 [0,825; 1,188] (`:98`) [conferido]. Ou seja, o desfecho que a decisão 6 propõe para a próxima campanha já foi lido no E6 e não se moveu.

**O que já explica o resultado** [relato do subagente metodológico, com as fontes do relatório]:
- **A dose**: 1,10 % dos 304.306 passos; 62 de 163 tarefas sem nenhuma ação vinda do MOP; widget marcado na tela em 3,88 % dos passos.
- **A seletividade**: JCA nova em 7,2 % dos passos depois de clique marcado, contra 6,7 % nos passos comuns.
- **O teto**: 33 sítios no startup; 29 APKs sem chamador direto executado, nem no E2.

**A força de cada medição da exploração:**

| medida | força | ressalva |
|---|---|---|
| casamento 17,3 % (33,7 % só-View, 8,2 % misto, 0 % só-Compose) | forte, censo de 623.566 cliques | é fração dos cliques que o APE fez, não dos widgets |
| saturação de `reachesTarget` | o censo é forte; a causa é hipótese, e a §3 mostra que o mecanismo citado está errado | — |
| marca rara 2,01 [1,57; 2,67] | fraca: post hoc, 192 cliques, limiar ≤ 3 escolhido depois de ver os dados | o desfecho é 98 % primeira execução só transitiva |
| novidade por activity (26–30 % contra 3–5 %) | grande, mas associativa | confundida com o tempo de execução: passos inéditos se concentram no começo |
| lançador ≈ chegada orgânica | só no desfecho transitivo (0,96 [0,88; 1,05]) | no chamador direto é inconclusivo |

**Regra do esqueleto.** As medidas M14–M17 excluem o avare e moram nos scripts da tese. Só viram número do artigo depois de portadas ao adendo post hoc do `$P3`, lidas da raiz composta (`esqueleto.md`, regra do incidente de 05/10).

---

## 2. O contrato ponta a ponta: o GATOR salva X, o APE-RV lê X

Relato do subagente de contrato. Ele reproduziu com o `derive()` de produção os artefatos de `aegis_81` e `mtgfam_99`. A equivalência com o que rodou no E6 foi conferida pelo `sourceDigest` do registro `MOP_DATA` e pelas estatísticas, que batem. Os `.mop.json` do E6 não puderam ser lidos (`root 0600`).

### 2.1 Salto por salto

| campo | produtor | derive | MopData | chave em runtime | casa? |
|---|---|---|---|---|---|
| activity | `SootClass.getName()`: FQN com `$` | `_base_activity` corta no 1º `#` (`derive:367-375`) | chave literal (`MopData.java:627-631`) | `topActivity.getClassName()` (`AndroidDevice.java:142-149`) | **exato** |
| `shortId` | `getIdName()`, nome sem pacote | `idName`; vazio é descartado e contado | chave do mapa | `extractShortId`: sufixo depois de `:id/` (`MopData.java:690-694`) [conferido] | **exato por nome**; o pacote se perde dos dois lados (app, `android:`, biblioteca) |
| evento | `click`, `long_click`, `item_click`, `enter_text`… | tira `_` e `-` | renormaliza | `eventTypeOf`: só `click`, `longClick`, `itemSelected`, `scroll` | exato nos três primeiros; o resto passa pelo agregado (INV-MOP-14, decisão registrada) |
| handler → flag | assinatura Soot | junção exata, mais a recuperação D8 pela classe que envolve a lambda | `none`/`direct`/`transitive` | `MopScorer.score`, contenção até ±2 níveis | **aproximado** (D1) |
| host do diálogo | janela DIALOG nomeada pela classe (`android.app.AlertDialog`) | primeira transição de entrada | chave = host | `topActivity` | **quebra na maioria** (D2, D3) |
| deep link | filtros de intent | `scheme://host+path` do primeiro filtro VIEW; ignora `pathPrefix`, `pathPattern` e mime | string | `ACTION_VIEW` sem componente e sem alternativa | não garante X (D6) |

### 2.2 Descasamentos

Corpus de 163 `.apk.json`, 2.681 widgets marcados emitidos.

- **D1. A recuperação D8 passa por cima de um "falso" explícito** [conferido no código; números em relato].
  - **O mecanismo**: `_index_reachability` só indexa métodos que alcançam: `if not (direct or reaches): continue` (`derive_mop_artifact.py:422`). Por isso um handler que está no `reachability` com `reachesTarget=false` não aparece em `by_signature`. Ele cai na recuperação pela classe que envolve a lambda (`:510-514`) e herda a flag das lambdas irmãs.
  - **A spec** restringe a recuperação ao handler "with no exact `reachability[].methods[].signature` match" (`openspec/specs/aperv/spec.md:160-162`). O código lê isso como "sem match entre os que alcançam".
  - **O tamanho**: 731 dos 2.681 marcados (27 %) só existem por essa via, quase todos no redreader (703 de 912).
  - **Por que o "falso" é provavelmente o certo**: no aegis, `Lambda3.onClick` tem `reachesTarget=true` sem `direct`. Logo a BFS atravessa a aresta wrapper → lambda, e o "falso" de um wrapper é resposta, não lacuna.
  - Não há prova caso a caso, mas é provável sobre-marcação.
  - **Consequência**: um reparo aqui muda o que é guiado, então é decisão do Pedro, não reparo silencioso.
- **D2. Marcas presas à chave de diálogo** [relato]: 528 marcados (19,7 %) ficam sob chaves que não são activity, em 8 APKs, sendo 502 do `eu.faircode.email`. Nenhuma `topActivity` tem esses nomes, então essas marcas nunca agem.
  - De 922 janelas DIALOG, 715 não têm transição de entrada.
  - A órfã com chave própria é registrada (INV-DRV-03). A "auto-hospedada", que tem por única entrada um laço sobre si mesma, não é contada nem registrada.
- **D3. Ids de janela duplicados no produtor** [relato]: `windowNodeIds` é indexado por nome de classe, então diálogos da mesma classe herdam o id do último nó. Afeta 32 APKs e 366 janelas DIALOG.
- **D4. Namespace do id perdido** [relato]: raro na prática. Só 120 de 20.569 cliques em `android:id/…` receberam reforço.
- **D6. Deep link** [relato; o efeito é hipótese]: em 50 das 57 activities do censo com URI, o filtro escolhido provavelmente não resolve. O URI ignora mime e `pathPrefix`/`pathPattern`.
- **D7. A paridade INV-ANA-32 não protege o caminho do APE-RV** [relato]: o teste compara os conjuntos `JsonSchema.Keys` e `_JK`, mas o escritor do GATOR e o derive usam literais.
- **D8. Deriva entre specs** [relato]: `ape/openspec/specs/static-analysis-entrypoints/spec.md:190,198-201` exige `complete==true`. O INV-DRV-08 e o código aceitam o JSON parcial, e o aegis é exatamente esse caso.
- **O marcador do prompt e a pontuação não usam a mesma regra** [conferido]:
  - `buildMopMarker` usa o `shortId` exato e as flags agregadas (`ApePromptBuilder.java:456-468`);
  - o `MopWidgetPass` usa contenção e tipo de evento;
  - por isso o LLM vê marcas diferentes das que a pontuação aplica.

### 2.3 Como as mudanças atravessariam os saltos

- **F1/F2, com janela `Host#Fragment`: exato**, pois o fragment não muda o `topActivity` [relato do consumidor, `AndroidDevice.java:142-150`]. Duas condições:
  - a janela não pode ter tipo DIALOG, senão `_rekey_dialogs` move o balde inteiro;
  - o derive não lê `hostActivities[]`, então o produtor tem de emitir **uma janela por par (host, fragment)**.
- **Vetor de distâncias, `formatVersion` 2: aproximado.**
  - O que muda além do previsto:
    - o merge de diálogos (`derive:893`) também tem de tomar o mínimo por alvo;
    - `serialize_canonical` não ordena arrays, então a ordem do vetor e a numeração de C precisam ser fixadas (INV-DRV-05);
    - `SUPPORTED_FORMAT_VERSION = 1` rejeita a v2, o que obriga um corte coordenado.
  - **A recuperação D8 contamina a distância** (D1): ela dá ao wrapper a menor distância entre as lambdas irmãs. Ela teria de valer só para assinaturas ausentes do `reachability`.
- **Alvo de fronteira B: exato no salto**, pois é campo por método unido por assinatura.
- **Diálogos e adapters pela via atual: quebram**, porque dependem da WTG, que não termina ou cria laços. Ficam exatos se o produtor nomear `Host#DialogFragment` e pendurar as linhas do adapter na janela do host pelo mapa F1, sem passar pela WTG.

---

## 3. O produtor (GATOR): o que o código sustenta

Relato do subagente do GATOR. Dois pontos centrais conferidos por mim.

### 3.1 C0: o diagnóstico de que as exclusões não fazem nada está certo; a explicação do leque, não

- **[conferido]** `Scene.isExcluded` só casa por igualdade exata ou por padrão terminado em `.*`/`$*` (`soot/.../Scene.java:2052-2062`). Com `kotlin.` sem `.*`, as três exclusões não têm efeito.
- **[conferido em parte]** O SPARK não semeia os parâmetros dos pontos de entrada:
  - `MethodPAG.addMiscEdges` só os liga para `main` e alguns métodos do JDK;
  - o tratamento de biblioteca só existe com `cg library` ligado (`MethodPAG.java:239`).

  Logo, a frase da §4.2 do relatório ("ponto de entrada tem parâmetros sem restrição de points-to") está errada.
- **O leque continua plausível por outro caminho** [relato]: o SPARK é insensível a contexto. Por isso:
  - todas as lambdas passadas a `Button(onClick)` caem no mesmo parâmetro;
  - todos os `_block` de `ComposableLambdaImpl` caem no mesmo campo;
  - as corrotinas passam por filas compartilhadas.

  O resultado é "toda lambda que flui para o mesmo parâmetro ou campo da biblioteca", e não "toda `Function0` do app".
- **A correção pode tirar recall** [relato; hipótese sobre o efeito]: com a biblioteca *phantom*, uma lambda chamada só pela biblioteca (`launch{}`, `Flow.collect{}`, `setContent{}`) perde a aresta de entrada. Sem receptor real, também perde as chamadas virtuais sobre as variáveis que captura.
- **Consequência para o portão do C0**: uma queda de `reachesTarget` mistura saturação desfeita com recall perdido. O portão precisa de verdade de campo: os chamadores diretos executados no E6 devem continuar alcançáveis a partir dos handlers que os precederam. Só a queda não basta.

### 3.2 Distância

- **[conferido]** `multiSourceBfs` guarda só o conjunto `visited` (`RvsecAnalysisClient.java:497-520`). A §4.5 diz que o `minHops` "a BFS reversa já calcula e descarta"; isso é impreciso. Acrescentar o nível é fácil.
- **A BFS atravessa a biblioteca** [relato]: o grafo é uma cópia JGraphT do call graph inteiro. Uma distância calculada sobre ele herda o leque. A §6.5 pede "poucos saltos dentro do código do app", mas o desenho da §6.7 não diz isso.
- **O conflito**: restringir a BFS a vértices do app corta os caminhos legítimos que passam por `viewModelScope.launch{}`. A aresta de lambda é o que os devolveria.
- **A aresta de lambda é viável, mas incompleta** [relato]: ela entra só no grafo JGraphT e não repropaga points-to. As chamadas de dentro da lambda continuam ausentes se dependerem do receptor. Dificuldade média a grande.
- **A distância é de call graph, não de UI** [relato do consumidor]. Um widget que só navega até a tela do alvo tem distância infinita, porque o grafo não tem arestas de ICC (Intent entre componentes) nem de ciclo de vida.

### 3.3 Fragments, diálogos, adapters

[relato]

- **F1**: viável. A regra "host = classe que faz a transação" falha quando a transação está numa classe auxiliar.
- **F2(b)**: cobre só o caso inflate + `findViewById` + `setOnClickListener` dentro do próprio `onCreateView`. Perde:
  - `onViewCreated(view)`, `requireView()` e o construtor `Fragment(R.layout.x)`;
  - o ViewBinding novo (`ViewBindings.findChildViewById`) e o DataBinding.

  O fluxo de GUI só segue chamadas para classes do app (`Flowgraph.java:366-393`). Sai barato um "(a)-mínimo": o retorno de `onCreateView` → o parâmetro de `onViewCreated` e `getView`/`requireView`, mais `findChildViewById` como `FindView1`.
- **Diálogos**: só `android.app.AlertDialog$Builder` é modelado. O builder do AppCompat e o `MaterialAlertDialogBuilder` não são subclasses dele e ficam de fora. DialogFragment não é modelado.
- **DataBinding e ViewBinding**: nenhuma ocorrência no `sootandroid`.
- **Adapters**: só `ListView`/`GridView`; nada de RecyclerView.

  A decisão de 06/10 ("modelar diálogos, DataBinding e adapters") é, portanto, de custo médio a grande, e não uma extensão do F1/F2.
- **Sobre-atribuição listener → view** (o caso aegis) [hipóteses com linhas]. Três causas prováveis:
  - (i) o `LocalPacker` do Soot funde variáveis locais do mesmo tipo (`DexBody.java:869`);
  - (ii) a CHA sobre o tipo declarado do listener (`ListenerInstance.java:56-67`) explicaria os handlers presos a centenas de chaves;
  - (iii) callbacks herdados de uma activity base recebem os nós de todas as filhas.

  (i) e (ii) são corrigíveis com custo pequeno a médio. Para o desenho por distância isso importa, como a verificação apontou em A2.
- **WTG incompleta**: o JSON anterior à WTG é escrito antes dela (`RvsecAnalysisClient.java:183-192`). Peças inseridas antes desse ponto saem também no JSON parcial, mas cada uma aumenta o risco de o timeout (600 s, relógio do processo) matar a análise antes da primeira escrita.

---

## 4. O instrumentador (a sugestão de mexer nele)

O relatório tem três propostas que mexem no instrumentador dexlib2 (§6.3, §6.10, §7.4), e a verificação A9 leu a viabilidade da Variante A. O subagente foi mais fundo. A tabela abaixo é o relato dele; conferi o defeito da §4.1.

| variante | instrumentador | APE-RV | cobertura | riscos | confiança |
|---|---|---|---|---|---|
| **A** (guiar pelo carimbo no nó de acessibilidade) | descritor `before`, delegate composto; com MOP no mesmo APK, um dono por advice (Java) | ler o extra em `fillNode`; `Feature` nova; `.mop.json` novo | só-View: metade a dois terços dos cliques sem id; Compose: zero | apagado por delegate posterior (41–45 sítios de `setAccessibilityDelegate` por APK em androidx/Material); cache velho; APK diferente em todos os braços | média-baixa |
| **B** (carimbo que só mede, no logcat) | descritor no estilo do E1, com `before`; zero Java | nenhuma | toda view criada | os limites no momento do set são 0, então não casa nós sem id; não convive com os monitores no mesmo APK | alta para o bind da view |
| **B+** (B mais probe na entrada de `onClick(View)`) | passo novo no estilo do `CoverageWeaver` | nenhuma | clique → handler exato, com limites na tela | mudança Java pequena a média; volume por clique | alta |
| **E2** (Compose) | descritor e probe, como no E1 | nenhuma | 87 de 87 APKs Compose/mistos com `AbstractClickableNode.onClick` legível, sem ofuscação | o canal até o APE-RV não é viável sem efeito observador (`testTag` vira `resource-id` e muda a abstração de estado de todos os braços) | alta para medir |

**Leitura**:
- **B+ resolve o elo mais fraco do plano**: a verdade de campo do 7.5. Hoje ela é o "handler do clique anterior à primeira execução". Esse critério cobre 13 de 21 APKs, nenhum Compose, sofre com execução assíncrona e é circular, porque identifica o handler pelo mesmo mapa do GATOR que sobre-atribui.
- **Rodado sobre o APK original, sem monitores**, o B+ não toca o APE-RV nem o conjunto acusado.
- **Tag de log**: a captura só aceita `RVSEC`, `RVSEC-COV` e `ApeRvHb` (`logcat_manager.py:80-81`) [relato]. Uma tag nova mexe no INV-PLT-21. Usar `RVSEC` com prefixo, como o E1 fez, evita isso.
- **A Variante A** muda a guia por definição e, por isso, muda o que se mede em todos os braços. Ela não deve vir antes do 7.5. É o mesmo princípio de separar reparo de mudança comportamental.

### 4.1 Defeito latente no weaver: `invoke-super` [conferido no código; ocorrência no corpus não medida]

- **O mecanismo**: `InstructionInjector.replaceInvoke` converte também `INVOKE_SUPER`/`INVOKE_SUPER_RANGE` em `invoke-static` para o wrapper (`dex-mutator/.../InstructionInjector.java:494,509`). O passo 1 de `DexWeaver` não filtra o opcode antes (`DexWeaver.java:524-535`). O wrapper chama o método original de forma virtual.
- **O efeito**: num método que sobrescreve o alvo e chama `super`, a chamada volta à sobrescrita, numa recursão infinita.
- **Onde aparece**: o subagente o achou ao estudar um carimbo `after` em `setOnClickListener`, sobre `Snackbar$SnackbarLayout`.
- **Para as specs atuais**: o defeito só se manifesta se uma classe do APK sobrescrever um método JCA embrulhado e chamar `super` (por exemplo, uma subclasse de `SecureRandom`). Não medi se isso ocorre no corpus.
- **Proporção**: é candidato a issue própria, não um problema de campanha.

---

## 5. A change `llm-coordinate-single-base`

**Veredito** [relato do revisor adversarial, mais o conferido abaixo]:
- **Resolve o defeito**, com confiança alta no mecanismo.
- **O ganho ao vivo** (3,3–5,4 % das decisões) depende da suposição de que o modelo escolheria a mesma entrada da lista. Essa suposição é mais fraca do que o design admite:
  - o prompt manda "Do not click the same position twice in a row" (`ApePromptBuilder.java:258`);
  - com a base única, a repetição passa a ser visível no texto;
  - 7,8 % das cópias re-selecionam o widget da última entrada do histórico.
- **Os números centrais reproduzem**: 70,8 % → 87,1 %; o ganho de 7.085; e 191 = 174 + 17, com o erro de atribuição que a verificação já apontou.

**Achados novos, conferidos por mim:**
- **O histórico rotula a ação com o resultado da anterior.** A sequência em `updateStateInternal` (`StatefulAgent.java:828-853`) é esta:
  1. `_lastState = currentState`, o estado de onde partiu a ação anterior;
  2. `newState` é a tela atual;
  3. `resolveNewAction` escolhe a ação nova;
  4. `recordActionHistory(action)` compara `newState` com `_lastState` (`:1847-1853`).

  O "same / new screen" gravado na entrada da ação N descreve o efeito da ação N−1. O delta `exploration` da change diz "after each action is executed", e o Goal 6 diz "the history tells the model what actually ran". A change carrega a discrepância adiante.
- **A captura usa rotação fixa 0** (`ScreenshotCapture.java:80-81`).
  - **[relato]**: em paisagem, as respostas visuais caem a uma mediana de 513 px do widget, contra 24 px em retrato, e 68,6 % viram toque fora da árvore. É pouco volume: 105 respostas em 13 APKs.
  - A faixa superior de 0,035 × H dá 37 px em paisagem, contra 63 px de status bar.

**Achados novos [relato]:**
- **Toque fora da árvore no histórico**: o histórico passa a mostrar a coordenada do toque. Com a ida e volta de até 2 px, o mesmo ponto pode gerar duas chaves de banimento.
- **Teclado**: sem a faixa inferior, a fileira de baixo do teclado (y > 1686) passa a receber toques.
- **Nós de altura zero**: continuam listados com coordenada, mas o despachante os descarta (27 cópias).

**Relação com a guia MOP**:
- **O marcador**: a change não toca `buildMopMarker`. Só 4,2 % dos prompts do E6 têm algum `[DM]`/`[M]`. A deduplicação move a parcela de entradas marcadas de 2,52 % para 2,60 %, um efeito de saliência desprezível [relato].
- **O efeito real é pelo banimento de par morto.** Com mais acertos no widget certo, ele chega aos 5 strikes antes, a recusa aumenta e mais passos voltam ao SATA. Isso muda a fração de ações executadas pelo LLM no braço MOP+LLM.
- **Se entrar no mesmo jar que mudanças do GATOR**, é preciso reportar por braço:
  - a parcela de decisões recusadas por par morto;
  - a parcela de ações executadas pelo LLM.

  A change só prevê a primeira (tarefa 8.2).

---

## 6. A exploração melhora? Onde a guia age no APE-RV

Relato do subagente do consumidor. O atalho determinístico e o marcador foram conferidos por mim em `SataAgent.java:571-585,1443-1457` e `ApePromptBuilder.java:456-468`.

### 6.1 Onde a guia age

- **No atalho MOP, ela decide tudo.** O atalho é **determinístico**: se há candidato elegível, o de maior `mopBoost` vence. Existe em dois pontos:
  - o passo 0 do EARLY_STAGE;
  - o ε-greedy.
- **Na roleta por prioridade, ela só pesa.** O reforço domina (550 contra cerca de 50 por ação).
- **No "menos visitado", nada.** A prioridade é só desempate.
- **No braço com LLM, não age, salvo pelo marcador.** O LLM decide todo estado novo que passa o portão e 70 % dos passos admitidos. Esses passos vêm antes do lançador e do SATA, então o reforço é calculado e ignorado. A melhoria do GATOR só chega ao LLM pelo texto do prompt, e o LLM não vê distância, alvo nem "já exercitado".
- **Para tela nunca vista, não há planejador.** A navegação do APE (`findShortestPaths`) usa só transições já observadas, e a densidade MOP é só desempate. Para um alvo a várias telas de distância, a guia continua sendo "na tela atual" mais o lançador por activity.

  Nenhum dos 30 sítios do app durante a interação está numa classe activity ou no conjunto A′ (relatório §6.5). Chegar ao widget certo depende da exploração genérica.

### 6.2 As propostas do lado do dispositivo

- **Decisão 9 (atalho ordenado)**: pequena e segura.
  - **Parte já existe**: o `CoveragePass` soma até 100 ao inédito na activity, o que já desempata a favor do inédito entre empatados. O que a decisão 9 acrescenta é a precedência sobre o `mopBoost`.
  - **Correção à §6.6** do relatório: a novidade por activity **não** sobrevive ao refinamento quando o `Name` muda (`Model.java:594-618`). O mesmo widget físico ganha xpath nova e mais 3 escolhas.
  - **Divergência entre spec e código**: no passo 0, o código usa "não saturado" (`StateActionDiffer.java:50-56`), não "não visitado" como diz `action-selection/spec.md:217-221`.
- **Aposentadoria por contador (§6.7)**: o gatilho é observável em `UICoverageTracker.recordInteraction`, antes da execução. Mas é fraco.
  - **Aposenta cedo** quando o handler precisa de entrada válida ou de sessão, ou quando três widgets perto do alvo somam 3 sem que o alvo rode.
  - **Nunca aposenta** nos alvos alcançáveis só por widget sem id, nem nos toques do LLM fora da árvore.

  Não aposentar é o comportamento de hoje, então a falha é segura. Contar só quando d(w, c) for o mínimo do widget reduz o problema.
- **Lançador ordenado por distância: risco de inanição.** 75–83 % dos lançamentos aceitos não chegam (§6.9), e o INV-CT-14 proíbe agir sobre o resultado. Ordenando por distância, a activity mais próxima que não abre seria pedida sempre. É preciso manter o rodízio dentro de faixas de distância.

### 6.3 O teto, e por que um contraste agregado não resolve

Relato do subagente metodológico, sobre `rerun-avare/results/{misuses,tasks}.csv`:

- **A lacuna conhecida nos 89 APKs.** Contando por APK o máximo entre os cinco braços, e comparando com o braço 2:
  - 167 chamadores diretos contra 125 executados, uma lacuna de 42;
  - 72 sítios de violação durante a interação contra 51, uma lacuna de 21.

  As duas lacunas estão infladas, porque o máximo de cinco contagens ruidosas puxa para cima.
- **O mínimo detectável** (diferença pareada por APK, α = 0,025, poder de 80 %):

  | R | chamadores diretos | violações na interação |
  |---|---|---|
  | 1 | 33 | 15 |
  | 3 | 19 | 8,6 |
  | 10 | 10,5 | 4,7 |

- **A cadeia multiplicada**, com faixas por elo que são ordem de grandeza e não estimativa: de +0,3 a +6 chamadores diretos, e de +0,05 a +1 sítio de violação.

**A conclusão é robusta à arbitrariedade das faixas.** Só uma guia que capturasse quase toda a lacuna passaria o limiar com R = 1. Para a próxima campanha ter resposta, o desenho precisa medir onde o sinal está:
- **micro-randomização dentro do braço guiado**: em cada decisão com alvo candidato, aplicar ou não a guia com probabilidade 0,5, e medir a primeira execução do alvo em até w passos. Milhares de decisões viram unidade;
- **desfecho por alvo**: tempo até a primeira execução de cada chamador direto, num modelo de risco com fragilidade por APK. Um terço das primeiras execuções ocorre nos primeiros 5 s, então a contagem final a 1800 s converge entre os braços;
- **R ≥ 3 com orçamento menor** (por exemplo, 3 × 600 s), pareado por APK.

**Braços mínimos** [proposta], todos no mesmo jar e com o mesmo artefato:
1. o fork sem guia;
2. a marca booleana do E6 mais o atalho ordenado;
3. a distância mais o atalho ordenado.

O primário seria 3 × 1. O secundário, 3 × 2, isola a distância. O braço com LLM sai da família confirmatória. Nenhuma comparação com o E6 é válida.

---

## 7. Confiança por elo

| elo | o plano supõe | evidência hoje | confiança |
|---|---|---|---|
| casamento sobe com F1/F2 + diálogos/adapters | 17 % → até ~26 % dos cliques | teto medido (M15); F2(b) é parcial no código; diálogos AppCompat/Material, DataBinding e RecyclerView não modelados | média para fragments simples; baixa para o teto inteiro |
| atribuição correta | handler atribuído = handler que roda | 80 % nas chaves de handler único, 34,6 % nos handlers das chaves de vários; causas prováveis achadas | média; melhora com `LocalSplitter` e points-to do listener |
| exclusões corrigidas tiram a saturação | queda de `reachesTarget` = precisão | o mecanismo citado está errado; a correção também tira recall | **baixa sem um portão de recall** |
| a distância discrimina | o handler verdadeiro fica no topo | não medido; BFS sem nível e atravessando a biblioteca; nenhum chamador direto mora na classe de um handler marcado (0 de 207) | **desconhecida** |
| o agente toma o widget | o atalho decide | medido no desenho atual (reforço tomado em 58 % dos passos em que a tela o ofereceu) | média, só no SATA; nula nos passos do LLM |
| tomar leva a executar o alvo | — | 3 de 1.823 passos; 8 e 13 eventos no desfecho seletivo | **muito baixa evidência** |
| executar leva à violação | 34/34 sítios do app em chamadores diretos | cerca de 0,18 violação por chamador executado | média |
| o contraste agregado resolve | — | mínimo detectável maior que o teto plausível | **não, com R = 1** |

---

## 8. O que muda na ordem e nas decisões (perguntas, não tarefas)

Nada aqui foi decidido. São propostas para o Pedro.

1. **Portão de medição antes do GATOR.** Usar a Variante B+ (APK original, sem monitores, `before`, tag `RVSEC` com prefixo) como verdade de campo do bind e do 7.5 nos 21 APKs com sítio no app, mais alguns só-View? Ela substitui o "handler do clique anterior" e mede a sobre-atribuição sem inferência. É mudança no instrumentador só para medir; ele tem reserva quanto a isso.
2. **Portão do C0.** Acrescentar o critério de recall: os chamadores diretos executados no E6 continuam alcançáveis a partir dos handlers que os precederam. Só a queda de `reachesTarget` não basta.
3. **7.5.** Calcular a distância com a BFS restrita a vértices do app, com e sem a aresta de lambda. Pré-registrar uma AUC de −d sobre todos os pares (clique, alvo) contra a AUC da marca booleana, com permutação dentro da tela como acaso, deixar-um-APK-de-fora e um limiar fixado antes.
4. **D1 e D2 do derive.** O que fazer?
   - D1: restringir a recuperação D8 a assinaturas ausentes do `reachability`.
   - D2: resolver o host do diálogo sem a WTG.

   Os dois mudam o que é guiado. São mudança comportamental, separada de reparo.
5. **Desenho da próxima campanha**: micro-randomização ou desfecho por alvo, R ≥ 3, e os três braços da §6.3.
6. **A change de coordenadas.** Antes do apply, corrigir os quatro pontos da verificação e incluir:
   - o rótulo do histórico (ou registrar a discrepância);
   - um teste de paisagem;
   - a métrica da parcela de ações executadas pelo LLM.
7. **O defeito do `invoke-super` no weaver**: abrir issue própria?
8. **Redação do relatório**:
   - a §4.2 deve trocar "parâmetros sem restrição" pelo mecanismo de fusão, e dizer que a correção pode tirar recall;
   - a §4.5 deve trocar "a BFS já calcula `minHops`" por "não guarda nível";
   - a §6.6 deve corrigir "sobrevive ao refinamento" para o caso em que o `Name` muda;
   - a §3.5 deve dizer que diálogos AppCompat/Material, DataBinding e RecyclerView não existem hoje no GATOR.

---

## 9. Compose, auditado à parte (06/10, segunda rodada)

Relato do subagente de Compose; os números são medições dele sobre `sites.csv` do `compose-probe` e sobre os 87 `.apk.json` Compose/mistos. Os scripts estão no scratchpad.

- **O `compose-probe` não liga elemento a tela.**
  - `sourceOf` (`Probe.java:441`) só atribui `navigate`, por aninhamento léxico, e acertou 172 de 689 sítios.
  - A frase da §4.3 do relatório, "o par tela → handlers → alcance sai", está errada. Saem telas e saem handlers; o par não sai.
  - Consertar exige um grafo de chamadas entre composables a partir da lambda do destino. É barato no dexlib2, porque os composables são quase todos `invoke-static` em `*Kt`.
- **Classe do handler**:
  - 69,6 % dos 7.865 sítios resolvem para uma classe concreta;
  - 24,5 % ficam como `param`: são wrappers, e o handler vem de quem os chama;
  - 1.101 sítios são `TextField`/`Switch`/`Checkbox`/`Slider`, que não passam por `AbstractClickableNode.onClick`;
  - a precisão das classes nunca foi validada.

  O denominador proposto para o E2 penaliza os `param`, mas o bind não precisa do sítio: basta a tabela classe de runtime → `reachability`.
- **A marca satura também em Compose**: 77,7 % das classes de handler têm `reachesTarget` verdadeiro (mediana por app 0,77). Sem distância graduada, qualquer via de bind marca três de cada quatro clicáveis.
- **Onde ficam os chamadores diretos** nos 34 APKs Compose/mistos com chamador direto (214 métodos), por classificação de nome:
  - quase todos em utilitários de cripto e de infraestrutura;
  - ViewModel em 2 APKs, repositório em 4, composable em 1 método, lambda `onClick` em nenhum;
  - corrotinas em 22 métodos de 9 APKs.

  **Consequência**: tornar `kotlinx` *phantom* no C0 corta a aresta ViewModel → `invokeSuspend` sem um modelo de despacho de corrotina.
- **A identidade de composable do E1** registra o que foi **composto**, não o que está **na tela**: o `Set` só acumula, e uma tela estável não recompõe. Isso foi provado num APK só.
- **Uma chave de tela mais simples, para decidir** [proposta do subagente]: em Navigation-Compose (55 APKs), a rota do `currentBackStackEntry`, lida por reflexão.
- **Recomendação do subagente**: manter telas e handlers no `compose-probe` (1,2 s por APK, 0 falhas) e acrescentar o grafo de chamadas entre composables. Mexer no GATOR só para a distância e para o C0. Portar para o GATOR (C1) ganha pouco.

## 10. Se o desenho fosse do zero (revisado em 06/10 depois da correção do Pedro)

A primeira versão desta seção propunha uma guia em malha fechada: o agente usaria, durante a execução, os métodos que cada ação fez rodar. A premissa estava errada em dois pontos [conferido]:

- **O agente não tem esse dado durante a execução.**
  - O `RVSEC-COV` é um `Log.i` do processo do app.
  - Quem o lê é o host: o `CoverageTracker` do rv-platform segue o arquivo de logcat numa thread em segundo plano (`rv-coverage/.../tracker.py:1-20`).
  - O jar não lê logcat por regra (`ape/openspec/specs/action-selection/spec.md:65`, INV-SNK-10 em `event-sink/spec.md:180`, decisão D4 "final, do not reopen" em `rearch-04/design.md:5`), e nenhum canal leva esse dado ao agente.
- **Os dois logs só registram a primeira ocorrência.**
  - O `RVSEC-COV` emite uma vez por assinatura e por processo (`Coverage.log`: `if (SEEN.add(signature)) Log.i(…)`, `CoverageSourceEmitter.java:51-56`).
  - O `RVSEC` emite uma vez por violação distinta (`ErrorCollector.addError`: `if (errors.add(err)) Log.v("RVSEC", …)`, `rvsec-logger-logcat/.../ErrorCollector.java:51-55`).
  - Depois da primeira vez, repetir o caminho não produz linha nenhuma. Mesmo com um canal, o agente saberia só quem **descobriu** um método, e uma vez só. Não saberia se uma ação volta a chegar perto do alvo.
- **O que existe é a junção offline**: o heartbeat `ApeRvHb s=<passo> t=<ms>` no logcat, contra o `s` de cada registro NDJSON do trace (INV-SNK-10; INV-CAN-18). Ela atribui cada primeira execução de método e cada primeira violação ao passo, e portanto à ação do passo. É o que o `m6` do E6 fez.

**Reavaliação.** Com essas duas restrições, a malha fechada não é melhor que o plano.
- O que ela acrescentaria se reduz a duas coisas:
  - aposentar o alvo pela execução do método, em vez de pelo contador;
  - um rótulo "esta ação já chegou a distância d", válido uma vez, para nós sem chave estática.
- Os dois ganhos são pequenos: um rótulo de uma vez só não diz o que falta para o alvo executar, em geral entrada válida ou estado.
- O custo é reabrir a D4 e a R4, e criar um canal com atraso e com ruído de atribuição.

**Fica como opção futura, não como recomendação.** Do que propus, o que se sustenta é o que o próprio plano já tem como núcleo: **distância graduada no lugar do sim/não**.

### 10.1 O núcleo: a distância graduada, e o que ela exige

**Por que é o núcleo.** O sim/não satura em toda parte:
- 41 % dos widgets com handler marcam;
- 77,7 % das classes de handler Compose marcam;
- 100 % das activities, na mediana.

Uma marca que vale para quase tudo não discrimina, e nenhum bind novo resolve isso.

**O que a distância precisa para não saturar de novo:**
1. **BFS restrita a vértices do app.** A BFS de hoje atravessa a biblioteca, e o leque passaria para a distância (§3.2).
2. **Arestas de lambda e de despacho de corrotina.** Sem elas, a restrição ao app corta caminhos verdadeiros. Nos APKs Compose, 22 dos 214 chamadores diretos passam por corrotina.
3. **Uma BFS por alvo, guardando o nível.** Hoje a BFS não guarda nível.
4. **A sobre-atribuição listener → view contida.** Com distância, um handler atribuído por engano dá a sua distância ao widget (A2 da verificação). As causas prováveis são o `LocalPacker` do Soot e a CHA no tipo do listener, e são corrigíveis (§3.3).

**Onde a distância age no APE-RV** (estado que o jar já tem, sem canal novo):
- **o atalho MOP e a roleta**, com a pontuação graduada, onde o bind casa;
- **o lançador de activities**, ordenado pela distância mínima da activity, mantendo o rodízio;
- **o marcador do prompt**, graduado, no braço com LLM;
- **acréscimo a avaliar**: preferir, na navegação do APE (`findShortestPaths` com um `SubsequenceFilter`), voltar a um estado **já visto** que tenha widget perto de um alvo não aposentado. É a única forma de a guia agir fora da tela atual sem planejador novo, e só para telas já visitadas (§6.1).

**O que a distância não resolve:**
- **Compose sem bind**: só o grão de activity, e o canal por classe de handler esbarra no efeito observador.
- **Os alvos com precondição**: login, entrada válida, sessão.
- **Os sítios do startup.**
- **Os sítios de biblioteca**: só com o alvo de fronteira, que tem o mesmo risco de saturar.

### 10.2 Como validar a distância antes de construir (o 7.5, com os dados que existem)

A junção offline passo × logcat permite testar a distância sem rodar nada novo no dispositivo. Só falta a tabela de distâncias, que vem de um GATOR descartável. Duas perguntas, nos 21 APKs com sítio no app:

1. **Por clique.** A distância estática do widget clicado (pelo bind, onde casa) prediz a primeira execução de um chamador direto na janela seguinte, contra a marca sim/não?
   - Medida pré-registrada: AUC de −d contra a AUC da marca, com permutação dentro da tela.
2. **Sem bind.** A menor distância entre os métodos **executados pela primeira vez** num passo prediz a primeira execução de um chamador direto nos passos seguintes?
   - Isso testa se a distância forma um gradiente ao longo da exploração.
   - Não precisa ligar o clique ao handler, então vale também para Compose.

**A limitação que vem do primeiro registro.** Só a primeira execução aparece. Um caminho que o explorador já percorreu some dos dados, então:
- a pergunta 1 vale só para cliques cujo handler ainda não tinha rodado na tarefa (a mesma restrição do M14: 0,5 % dos cliques testáveis);
- a pergunta 2 vale para a fronteira de descoberta, que é justamente o que importa para o desfecho "primeira execução de chamador direto".

A Variante B+ do instrumentador (§4) é o que daria verdade de campo por clique sem essa limitação. Ela custa mudar o instrumentador, só para medir.

### 10.3 A visita de tela ("cena") como unidade da validação [conferido]

**O que existe.** A visita de tela já está implementada e já foi usada no E6:
- no rv-android, em `aperv-tool/src/aperv_tool/analysis/screen_visits.py`;
- portada para o `$P3`, em `src/rvsec_study03/e6/analysis/visits.py`, que é o adendo X6 do E6.

**Como é definida:**
- **A visita** é a sequência máxima de passos consecutivos com a mesma `act`. Fecha pela primeira regra que casar: sem `out`, *teardown*, `out.act_changed`, a `act` do passo seguinte diferente, fim do trace. Revisitas não se fundem.
- **A janela de chegada e a de interação.** Pela regra primária (R-A2), os eventos do passo que fechou a visita anterior com troca de activity formam a **janela de chegada** da visita nova. Os passos da própria visita formam a **janela de interação**.
- **Duas sensibilidades**, (a) e (b), deslocam essa fronteira.
- **A regra de citação**: só se cita o que as três regras concordam.
- **Os eventos** são as primeiras linhas `RVSEC-COV` e `RVSEC`, postas no passo pelo heartbeat.

**Por que a activity, e não o estado abstrato** (docstring de `screen_visits.py`):
- o estado abstrato tem visita mediana de 1 passo, e 75,5 % das visitas duram um passo só;
- a activity dá mediana de 14,5 visitas por execução;
- a activity é a única chave comparável entre execuções.

A limitação registrada é a mesma desta análise: a navegação entre fragments dentro de uma activity é invisível (a visita mais longa medida tem 294 passos), e num app de uma activity só a execução inteira é uma visita.

**O que o E6 já mostrou com ela** (`rerun-avare/report.md`, X6.3 e X6.4):
- **Violações primárias, braços 2–4, regra R-A2.** De 267 primeiras ocorrências:
  - 107 no startup;
  - 39 na chegada a tela MOP;
  - 102 na interação em tela MOP;
  - 14 em tela não MOP.

  As três regras concordam que a interação em tela MOP domina. Ressalva: 81 % dos passos (mediana 100 %) já estão em telas MOP, então "tela MOP" quase não discrimina.
- **Primeiras execuções de métodos `reachesMop` por visita MOP.** As regras discordam entre chegada e interação (dominante na chegada por R-A2 e (b), na interação por (a)). Uma parte material do código MOP roda na **chegada**: ciclo de vida, `onCreate`, inicialização de ViewModel. Não roda no clique.

**O que isso muda no desenho:**
- **A unidade.** A validação da distância (§10.2) deve usar a visita, com as três regras de atribuição, no lugar da janela fixa de 3 passos do `m6`. É mais robusta à execução assíncrona dentro da tela, e é a metodologia que o artigo já usa.
- **Uma pergunta nova, antes do desenho do consumidor:** cada chamador direto, na primeira execução, dispara **na chegada** ou **na interação**? Os alvos de chegada pedem navegação: lançador e caminho até a activity, ordenados pela distância a partir dos callbacks de ciclo de vida da activity. Os de interação pedem a distância por widget.
  - O vetor da §6.7 já prevê distâncias para callbacks de activity, mas o desenho trata os dois tipos de alvo da mesma forma.
  - A medida é offline: chamadores diretos no lugar do conjunto saturado `reachesMop`, com a mesma junção visita × logcat.
- **O que a visita não resolve:**
  - durante a execução, o agente sabe quando troca de activity, mas não o que rodou: a visita é construção offline;
  - em apps de uma activity, e na navegação entre fragments, a visita não separa telas. Para isso faltaria um sinal de tela abaixo da activity, como o fragment ativo (`dumpsys activity top`) ou a rota do Navigation.

### 10.4 O `UICoverageTracker`: como é usado hoje, e o que ele daria à guia [conferido, salvo indicação]

**O que ele guarda** (`ape/.../utils/UICoverageTracker.java`):
- **A chave do widget.** É `xpath|tipo` (`widgetId`, `:240-252`), a partir do `Name` do APE. **Não depende de `resource-id`**, então existe também para nó sem id e para Compose.
- **Por estado**: os widgets registrados e um contador de interações, num LRU de 2.000 estados (`stateData`). O que é despejado vai para um consolidado por activity (`activityRollup`).
- **Por activity**: o conjunto monotônico dos widgets já exercitados (`activityInteracted`, `:260-266`, INV-COV-09).

**Onde é atualizado:**
- **O registro da tela** acontece a cada passo (`StatefulAgent.java:840`).
- **A interação** é gravada em `moveForward`, depois da escolha e antes da execução (`:1498`).

**Quem o usa na decisão:**
1. **`CoveragePass`** (`agent/scoring/CoveragePass.java:35-58`). Soma 100/(1 + visitas do estado/5) à prioridade de todo widget ainda não exercitado na activity.
   - Está nos braços aperv com e sem MOP: o `dec.cov` do trace coincide com a novidade por activity em 100 % dos passos (§6.6 do relatório).
   - Compete com prioridades de base de cerca de 8–80, e perde para o reforço MOP (+300/+500).
2. **O ε dinâmico** (`SataAgent.java:1148-1158`): ε = 0,02 + 0,13 × a lacuna de cobertura **do estado** (`ape.dynamicEpsilon=true` no preset `aperv`). Com mais lacuna, a decisão cai mais vezes na roleta por prioridade, onde os reforços pesam.
3. **A convenção de chave** é reaproveitada pelo limite de 3 escolhas MOP (`mopPickKey`, `SataAgent.java:690-710`) e pela chave do banimento de par morto do LLM (`CoordinateMapper.java:361`).
4. **No fim da execução**, as linhas `UICOV`/`UICOV-ACT`, só para análise (X6.6 do E6).

**Quem não o usa:**
- **O atalho MOP**: filtra por inédito **no estado** (`ENABLED_VALID_UNVISITED`), não pelo tracker. Daí a falsa novidade de 59–67 % (§6.6). A decisão 9 corrige isso.
- **O lançador**: abre a próxima activity **não visitada** do censo, sem olhar quanto dela já foi exercitado.
- **O prompt do LLM** [conferido, corrigindo o relato]. O prompt mostra visitas, mas **do modelo do APE, não do tracker**:
  - `(v:N)` por ação vem de `action.getVisitedCount()`, a contagem do `GraphElement` por estado abstrato (`ApePromptBuilder.java:413-444`). Aparece nas variantes `ape_current`, `ape_reasoning` e `compact_v1`.
  - A `v17` tem as etiquetas `[UNTESTED]`/`[TESTED-Nx]`/`[WELL-TESTED]` e a linha `N/M actions tested` (`:694-739`), da mesma fonte.
  - O bloco "Visited Nx" (`buildExplorationContext`, `:599-604`) conta as visitas ao estado e entra nas variantes padrão, `v17` e `visual_only`.

  As três fontes são a granularidade de estado, a mesma em que 59–67 % dos "inéditos" já tinham sido feitos na activity.

  **A `v13`, a variante do braço com LLM do E6** (`E6-campaign/config/arms.json:65`):
  - a lista não traz visita nenhuma (`:618-650`);
  - o system message manda "PRIORITY: [DM]/[M] elements > navigation to new screens > unvisited elements > visited elements" (`:250`).

  O modelo recebe a regra sem o dado para aplicá-la, exceto pelo histórico das 5 últimas ações.
- **`getActivityCoverageGap`**: existe, mas não tem consumidor de decisão (só testes e dump).

**O que ele já mostrou** (§6.6 do relatório):
- a novidade por activity é a variável que mais pesa no rendimento: 26–30 % de JCA nova no clique inédito, contra 3–5 % no repetido;
- com ela controlada, a marca MOP rara fica em 2,01 e a comum em 1,15.

**Limites** [relato do subagente do consumidor, sobre `Model.java:594-618`]:
- quando o refinamento do APE renomeia o widget, a xpath muda e ele volta a ser "inédito";
- itens de lista com a mesma xpath viram uma chave só;
- em app de uma activity, a novidade por activity vira novidade global.

**O que ele daria à guia, sem canal novo:**
- **É a única memória do dispositivo que cobre nós sem id e Compose.** A guia MOP não alcança esses nós, porque depende do `resource-id`; a novidade alcança.
- **Atalho ordenado (decisão 9) e aposentadoria por contador (§6.7)**: as duas já se apoiam nele.
- **Lançador e navegação.** Combinar a distância da activity ao alvo com a lacuna dela (`getActivityCoverageGap`, hoje sem uso), em vez de só "não visitada". Isso põe a guia de chegada (§10.3) sobre activities que ainda têm o que exercitar. É proposta, não medida.

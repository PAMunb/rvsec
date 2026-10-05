# Fragments e Compose no GATOR: o que falta para a análise estática guiar o teste

**Data**: 2026-10-05
**Escopo**: como o `rvsec/rvsec-android/rvsec-gator` trata Fragments e Jetpack Compose hoje, por que
nos dois casos a informação estática não chega à decisão do APE-RV, e o que mudar no produtor (e, quando
inevitável, no consumidor) para que chegue. Serve ao próximo estudo; não altera nada do estudo 03, que
rodou e foi analisado com a configuração atual.
**Status**: análise. Nada foi implementado nem executado contra o gator; as medições são leituras dos
artefatos existentes e dos dados do E6. As decisões da §9 são do Pedro. Em 05/10 o Pedro decidiu não
rodar a análise estática agora (C0, 7.1, 7.5 ficam registrados, não executados).

**Marcas de evidência**: **[conferido]** = li no fonte ou medi eu mesmo nesta sessão;
**[relato]** = relatório de subagente que não reconferi linha a linha; **[web]** = fonte externa citada
pelo subagente de literatura; **[hipótese]** = inferência minha, não medida.

**Corpus das medições**: os 163 `.apk.json` de
`/home/pedro/desenvolvimento/RV_ANDROID_DATASET_FINAL/APKS_INSTRUMENTED_jca_android_dexlib2` (estudo 02
e estudo 03, `jca_android`). Scripts no scratchpad da sessão (§10).

**Relação com a série de julho/agosto**: sucede os seis documentos sobre Compose
(`20260730_compose_gator_substrato_estatico.md` … `20260806_compose_e1_resultado.md`) e o relatório
`doutorado-tese/docs/estudo-03/escrita/20261003_compose-static-analysis.md`. Fragments nunca tiveram
análise própria; foram registrados de passagem como perdidos
(`20260421_gh51_analise_callgraph_reachability.md:338`) e como invisíveis na granularidade de activity
(`20260815_gh103_analysis_layer.md:187`).

---

## 1. Respostas diretas

1. **O GATOR não modela Fragment em nenhum nível de GUI.** Não há classe, nó de janela, operação de
   fluxo nem leitura de XML que reconheça fragment. Os widgets inflados em `onCreateView` ficam órfãos:
   o grafo de fluxo os constrói, mas nada os liga à janela da activity hospedeira, e por isso não
   aparecem nem em `windows[].widgets` nem na WTG [conferido, §3.1].
2. **O GATOR não usa o FlowDroid.** São linhagens distintas sobre o Soot. O FlowDroid entra no reator
   só pelo `rvsec-apk`, e o `client` do gator exclui `soot-infoflow*` dessa dependência. O FlowDroid
   trata fragments, mas para a análise de fluxo: liga Activity → Fragment por um padrão dentro de um
   único método e põe o ciclo de vida do fragment no *dummy main*. Não produz modelo de tela e não
   conhece o Navigation component [conferido, §3.2].
3. **Para Fragments, o conserto mora só no produtor, e o consumidor já está pronto para recebê-lo.**
   O `derive_mop_artifact.py` funde no balde da activity hospedeira toda janela cujo nome seja
   `Activity#Sufixo` ("an activity and its fragments", nas palavras do próprio docstring). E o join em
   runtime é por resource-id, que views de fragment têm. Emitir os widgets de cada fragment sob a
   activity hospedeira ativa o boost MOP de widget nesses apps sem tocar no APE-RV [conferido, §3.4].
4. **O rendimento potencial é grande.** 65 dos 163 APKs (40 %) usam fragments como tela [relato, §2.3; pelo
   proxy de nome, 69]. Neles, o código
   de fragment alcança alvos MOP em 61 de 69 apps com classes `*Fragment`, mas só 19 deles têm na WTG
   algum listener cujo handler está num fragment [conferido, §3.3]. O estudo 03 concluiu que a guia
   só agiu onde havia widget marcado (32 APKs), não "onde não é Compose" [relato, §2.2]. Fragments são
   o caminho mais barato para aumentar esse estrato.
5. **Para Compose, a premissa central da série de julho está errada, e isso reabre o gate que ela
   fechou.** A série supôs que `-exclude androidx.compose.` torna o framework *phantom*. Em 28/08
   mediu-se que as três exclusões são **inertes**: o Soot só faz casamento de prefixo com `.*`
   (`20260828_cadeia_medicao_rvandroid.md:877-880`). O SPARK roda antes do rebaixamento para biblioteca,
   e com `all-reachable:true` todo método de `androidx.*`/`kotlin.*` vira ponto de entrada. Daí sai um
   mecanismo concreto para a saturação de `reachesTarget` em composables, que a série deixou sem causa:
   um `onClick.invoke()` dentro do corpo de `Button`, com parâmetro sem restrição, faz leque para toda
   lambda do app [hipótese com suporte no fonte, §4.2]. Se isso se confirmar, o sinal por tela (D1),
   reprovado no pré-gate por saturação, volta a ter chance.
6. **O bind que já existe funciona; a marca só informa quando é rara na tela.** No agregado, depois
   de um clique em widget marcado veio JCA nova em 7,2 % dos passos, contra 6,7 % nos passos comuns
   (§6.1). Graduando a marca pelo número de alvos marcados na tela e controlando a novidade do clique
   por activity, o widget que é um de no máximo três marcados rende **2,01 vezes** [1,57; 2,67] a JCA
   nova de um clique comum igualmente inédito, nos dois braços com orientação. Com quatro ou mais
   marcados, 1,15 [0,92; 1,55]. A ressalva: "JCA nova" é quase toda primeira execução de método só
   transitivo, e o desfecho seletivo (chamador direto ou violação nova) tem contagem pequena demais
   para concluir [conferido, §6.4, §6.6]. Para Compose existe uma chave de bind que a série não
   considerou: a **classe da lambda `onClick`**, alcançável dentro do processo a partir do nó de
   semantics. Está conferido no bytecode; falta medir em execução (§6.3).
7. **"Já exercitado" existe no APE-RV, em três granularidades, e a do atalho MOP é a mais fraca.** O
   inédito por estado (`[, UNVISITED]`) é falso em 59–67 % dos cliques: o widget já fora clicado na
   mesma activity, sob outro estado abstrato. O `UICoverageTracker.activityInteracted` guarda a
   novidade por activity, sobrevive ao refinamento e custa O(1). O limite de 3 escolhas MOP por
   widget é decisão registrada. A novidade pesa mais que a marca: o clique inédito na activity rende
   26–30 % de JCA nova, contra 13–15 % do inédito só no estado e 3–5 % do repetido. Proposta:
   **ordenar** o atalho MOP por inédito na activity, sem filtrar, mantendo os 3 tiros [conferido,
   §6.6].
8. **O sinal seletivo é o alvo, e falta o caminho até ele.** Os ~3 métodos por APK que chamam a JCA
   diretamente cobrem todos os sítios de violação do app. A proposta é guiar pela distância do
   handler ao alvo mais próximo ainda não aposentado:
   - a distância é calculada no GATOR e projetada no host;
   - ao dispositivo vão só pares `[índice, distância]` por widget e por activity (~270 bytes por APK
     na mediana);
   - a aposentadoria é por contador;
   - exige emendar o INV-DRV-06.

   O desenho só tem base se o 7.5 mostrar que a distância não satura [proposta, §6.5, §6.7].
9. **Sítios de biblioteca durante a interação também são alvo possível.** Dos 105 sítios primários do
   E6, só os 33 do startup estão fora do alcance de qualquer orientação por UI. Durante a interação há
   42 sítios em biblioteca (32 APKs), mais que os 30 do app (18 APKs). Um alvo de fronteira (método do
   app que chama a biblioteca da qual a JCA é alcançável) os poria ao alcance. O risco é a saturação
   por `okio`/OkHttp [conferido, §6.8; proposta].
10. **Escopo**: Compose entra (decisão do Pedro). A re-análise estática, quando for autorizada,
    cobriria o corpus, ou ao menos 81 + 11 APKs. A re-execução cobriria 60 APKs (cerca de 4 h por
    braço, pelo ritmo do E6), ou 89 com mais tempo [§7.6].
11. **Ordem** (§8): a graduação já foi feita. Depois vêm o C0 (saturação) e o 7.5 (distância e
    fronteira), ambos com GATOR e adiados pelo Pedro em 05/10. Só então as changes: fragments
    F1/F2, Compose C1 (activity) e E2 + INV-RUN-06 (widget), e o consumidor no `ape`.

---

## 2. Onde a guia age, e por que "tela" é a palavra-chave

### 2.1 O que o APE-RV consome

O dispositivo nunca vê o `.apk.json`. O `aperv-tool` deriva no host um artefato compacto
(`formatVersion: 1`), que o jar lê em `MopData` [relato; o derive conferido nas linhas citadas abaixo].
Os canais que o artefato alimenta são dois, e só um deles discrimina:

- **Canal de widget** — `MopWidgetPass` → `MopScorer.score`: +500 (direto) ou +300 (transitivo) para a
  ação cujo nó em runtime tem o resource-id de um widget marcado, mais o atalho determinístico de
  `SataAgent.pickBestMopTarget`. A chave é `(topActivity, extractShortId(resourceId))`
  (`ape/.../utils/MopData.java:690-694` [conferido]). É o único canal que muda a escolha *dentro* de
  uma tela.
- **Canal de activity** — `activityHasMop` (conjunto A′): nunca dá boost por ação; age por desempate de
  densidade, pela porta do OPTIONSMENU e pelo lançador de activities (`MopLauncherStage`) [relato].

### 2.2 O que o estudo 03 mostrou sobre isso

Do relatório do subagente sobre o E6 [relato; fontes em
`rvsec-study03-replication-package/openspec/changes/archive/2026-10-02-e6-campaign/` e
`doutorado-tese/docs/estudo-03/escrita/20261003_triagem_auditorias_esqueleto_r3.md`]:

- A hipótese principal ficou "não resolvível com n = 163". O efeito da guia sobre o fork tem teto de
  cerca de +11 % (C2, intervalo de 90 % [0,926; 1,106]).
- A guia mudou a escolha, ou o lançador disparou, em 1,10 % dos 304.306 passos. 99,4 % desses passos
  estão nos 32 APKs com widget marcado. Fora desse conjunto, os braços MOP e sem MOP são, na prática,
  idênticos.
- A leitura registrada pela própria triagem: a restrição que amarra o efeito é **ter widget marcado**,
  e não "ser Compose". Removendo os apps Compose, o C2 não sobe.

Esse resultado define o alvo deste documento. Para que a análise estática guie o teste, ela precisa
produzir **widgets marcados que casem em runtime**, ou um **sinal por tela** fino o bastante para
discriminar telas dentro de uma activity. Hoje nenhum dos dois existe para fragments nem para Compose.

### 2.3 O corpus por estrato de UI

**Atenção**: esta tabela é [relato] de um subagente cujos scripts se perderam com o scratchpad; ela
não foi regenerada e não deve ser citada. O estrato oficial do estudo 03 é o `ui_tech` congelado em
`rvsec-study03-replication-package/experiments/E6-campaign/config/strata.csv`: 73 só View, 50 só
Compose, 37 mistos, 3 engine. É ele que as §7.6 e §6.8 usam.

Classificação feita sobre o DEX, com escopo no `codePackage` do artefato. Compose = método do app com
parâmetro `Composer`, chamada a `setContent*` ou referência a `ComposeView`; concorda 163/163 com o
detector B da série de julho. Fragment = classe concreta do app cuja cadeia de superclasses chega a um
dos três `Fragment`, excluídos `DialogFragment` [relato; script em §10].

| estrato | APKs | dos quais WTG completa | mediana de widgets | mediana de listeners | % sem aresta entre janelas (completos) | % com 1 activity do app |
|---|---:|---:|---:|---:|---:|---:|
| só Compose | 71 | 54 | **0** | **0** | 85,2 % | **43,7 %** |
| só Fragment | 56 | 37 | 240,5 | 45,5 | 35,1 % | 10,7 % |
| ambos | 9 | 5 | 20 | 4 | 60,0 % | 22,2 % |
| só View | 27 | 23 | 196 | 36 | 43,5 % | 18,5 % |

Três observações:

- **44 dos 163 artefatos (27 %) não têm `complete: true`.** A WTG não terminou nesses apps, e eles têm
  zero transições qualquer que seja o toolkit. Toda conta de transição deve olhar só os completos.
- **O padrão "uma activity só" deste corpus é Compose, não fragment.** Apps com fragments mantêm, em
  mediana, 10 activities. "Uma ou duas activities com cinco ou mais fragments" aparece em 10 dos 65 apps
  com fragment.
- **Apps com fragment têm widgets na WTG, mas não os dos fragments.** A mediana de 240 widgets vem dos
  layouts de activity, da toolbar, dos diálogos e dos menus. A §3.3 mostra isso.

---

## 3. Fragments

### 3.1 O que o GATOR faz hoje [conferido]

Caminhos relativos a `rvsec/rvsec-android/rvsec-gator/sootandroid/src/main/java/presto/android/`:

- **Nenhum tipo Fragment é reconhecido.** `Hierarchy` categoriza activities, views, menus e diálogos. O
  registro de callbacks gerenciados pelo framework para no teste de activity, com o comentário
  `// TODO: for now, just deal with activities; later deal with the other interesting application
  classes` (`Hierarchy.java:362-366`).
- **Janela é Activity, Dialog ou Menu, por definição.** `ExplicitForwardEdgeBuilder.java:324-332` semeia
  a lista de janelas só com `getActivities()` e `getDialogs()`. O comentário "Catch-all: WTG nodes not
  captured above (context menus, fragments, etc.)" em `RvsecAnalysisClient.java:1065` é aspiracional:
  nenhum nó de fragment chega até ali. Nos 163 artefatos os tipos de janela são só ACTIVITY (1.532),
  DIALOG (922) e OPTIONSMENU (299) [relato]. O tipo `FRAGMENT` existe no parser Python e em
  `WindowType`, mas nunca é produzido.
- **A raiz de janela só aceita activity ou diálogo.** `FixpointSolver.addViewToWindowRoot`
  (`gui/FixpointSolver.java:761-773`) trata `NActivityNode` e `NDialogNode`; qualquer outra coisa é
  "Unknown window". O `inflate(id, container, false)` de `onCreateView` é modelado e a subárvore é
  construída. Só que `onCreateView` devolve a view ao framework, nenhuma operação a liga ao host, e a
  subárvore fica sem dono.
- **No XML, `<fragment>` vira `LinearLayout`.** `xml/AndroidView.java:102,148` e
  `xml/PrerunXMLParser.java:53` reescrevem a tag com `// TODO: read about mechanism of these tags, and
  get the real thing in`. O atributo `android:name` nunca é lido. `FragmentContainerView` é carregado
  como view comum e fica vazio.
- **`Fragment.startActivity` não gera aresta.** O papel de `startActivity` no `wtg.xml` cobre só
  `Context` e `Activity` [relato; `WTGUtil.java:183-210`, `lib/gator/wtg.xml:18-58`].
- **Fragments não são semente de `reachable`.** `getEntryPoints` (`client/.../RvsecAnalysisClient.java:376-460`)
  semeia activities e componentes do manifesto. Medido pelo subagente sobre classes `*Fragment`:
  `onCreateView` alcançável em 1 de 512, métodos de fragment alcançáveis em 22 % contra 87,5 % dos de
  activity [relato]. `reachesTarget` não sofre com isso, porque é BFS reversa a partir dos alvos sob
  `all-reachable:true`.

### 3.2 Por que o FlowDroid não resolve, e o que vale aproveitar dele [conferido]

Lido no fonte de `soot-infoflow-android-2.10.0` (repositório Maven local):

- `AbstractCallbackAnalyzer.analyzeMethodForFragmentTransaction` (linhas 484–559) liga Activity →
  Fragment quando o **mesmo método** chama `getFragmentManager`/`getSupportFragmentManager`,
  `beginTransaction` e `add`/`replace`. A classe do fragment vem do tipo do argumento. Cobre
  `android.app`, support-v4 e androidx. Há também `analyzeMethodForViewPagers`.
- `FragmentEntryPointCreator` põe `onAttach`, `onCreateView`, `onViewCreated`, … no *dummy main*.
- **Não produz janela, widget nem transição.** A finalidade é dizer quais callbacks são pontos de
  entrada para fluxo de dados.
- **Não conhece o Navigation component**: nenhuma ocorrência de `navigation`, `NavHost` ou `navigate`
  no fonte.
- **O padrão "tudo no mesmo método" perde as transações feitas em métodos auxiliares.** É o caso comum
  em Kotlin, com `supportFragmentManager.commit { replace(...) }` e helpers de navegação.

O que vale aproveitar é a **ideia**, não a biblioteca: casar `add`/`replace` sobre receptor do tipo
`FragmentTransaction` e ler a classe do argumento. A gh51 já avaliou trazer o FlowDroid inteiro
(`20260421_gh51_analise_callgraph_reachability.md` §10.5–10.6) e registrou o custo: ele constrói o
próprio call graph e as próprias exclusões, e não expõe o `PackManager`. Para obter o mapa
Activity → Fragment, uma varredura de sítios de chamada no próprio gator basta e não tem esse custo.

### 3.3 Medição: a UI de fragment está fora da WTG [conferido]

Fragment aproximado por nome: classe do app cujo nome simples termina em `Fragment`. É um proxy;
a classificação por hierarquia da §2.3 (65 apps) dá números da mesma ordem. Medido nos 69 apps que
têm classe `*Fragment` no `reachability` (script `docs/handoff/20261005_gator_fragments_compose/frag_coverage.py`,
saída `frag_coverage.out` ao lado):

| medida | valor |
|---|---|
| apps em que alguma classe de fragment alcança alvo MOP (`reachesTarget`) | **61 / 69** |
| mediana, por app, da fração de classes de fragment que alcançam alvo | **100 %** |
| apps com ≥1 listener na WTG cujo handler está num fragment | **19 / 69** |
| listeners com handler em fragment / total de listeners desses apps | 1.661 / 22.770 (7,3 %), concentrados nos 19 apps |

Uma primeira versão desta tabela trazia "1,7 %". Era a mesma conta com outra seleção de apps, que
incluía `eu.faircode.email`: sozinho, ele tem 79 mil listeners e nenhuma classe `*Fragment` no
`reachability`. A medida robusta é a contagem por app: em 50 dos 69 apps, nenhum listener de
fragment está na WTG.

Exemplo, `com.gelakinetic.mtgfam_99`: 21 fragments de tela e 2 activities. A janela de
`FamiliarActivity` tem 20 widgets e 3 listeners, todos com handler na própria activity. A UI dos 21
fragments não está lá.

Duas leituras, ambas necessárias:

- **O código existe e alcança MOP; a tela não existe.** A camada de alcançabilidade enxerga os
  fragments. A camada GUI não enxerga. É exatamente o padrão que a série de julho descreveu para
  Compose, só que aqui a causa é uma lacuna de modelagem View clássica, e não uma incompatibilidade de
  categoria.
- **A saturação aparece também aqui.** Mediana de 100 % das classes de fragment com `reachesTarget`.
  Ligar os widgets de fragment sem antes resolver a saturação pode produzir um conjunto de widgets
  "todos transitivos". O boost transitivo (+300) ainda reordena, porque compete com ações de prioridade
  8–60, mas discrimina pouco entre os widgets da mesma tela. O direto (+500) depende de
  `directlyReachesTarget`, que é quase nulo em código de UI (3 métodos de fragment no corpus [relato]).
  Este é o ponto que liga a §3 à §4.2: **a saturação é um problema dos dois estratos.**

### 3.4 O consumidor já aceita fragments [conferido]

`modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py`:

- `_base_activity` (linhas 367–375) corta o nome da janela no separador e devolve a activity dona. O
  docstring diz literalmente "Drops any `#OptionsMenu`/fragment suffix".
- `_build_widget_map` (linhas 737–797) funde no mesmo balde "an activity and its `#OptionsMenu`, an
  activity and its fragments". Em colisão de `shortId`, vence o widget de flag mais forte.
- Em runtime, o join é `(topActivity, shortId)`. Views de fragment são Views: têm resource-id.

Portanto, se o gator emitir uma janela `pkg.HostActivity#pkg.SomeFragment` com os widgets e listeners
do fragment, o APE-RV passa a impulsionar esses widgets **sem nenhuma linha nova no jar**. O preço
conhecido é a colisão: dois fragments do mesmo host com o mesmo `shortId` (`btn_save`) e flags
diferentes recebem ambos a flag mais forte. Isso precisa ser medido antes de ser chamado de problema
(§7.1).

### 3.5 Desenho proposto para o produtor

Quatro peças, em ordem de custo. As duas primeiras entregam o valor; a terceira e a quarta são
opcionais e independentes.

**F1 — mapa host → fragments (atribuição).** Uma varredura nova em `scanInvokesInAppClasses`
(`client/.../RvsecAnalysisClient.java:593-638`) com quatro fontes:
1. XML: `<fragment android:name=…>` e `<FragmentContainerView android:name=…>` no layout passado a
   `setContentView` do host. Substitui a reescrita para `LinearLayout`. O `resolveIncludes`
   (`DefaultXMLParser.java:770-826`) é o molde de enxerto que já existe.
2. Transação: `add`/`replace` sobre receptor `FragmentTransaction` (os três pacotes); classe do
   fragment pelo tipo do argumento ou por `const-class`. Host = a activity em cujo código, ou em cujos
   fragments, a chamada está. É a regra do FlowDroid sem a exigência de "mesmo método".
3. Navigation: `res/navigation/*.xml`, destinos `<fragment android:name>` e ações
   `<action app:destination>`. O grafo é atribuído ao host do `NavHostFragment` (fonte 1).
4. Paginadores: `FragmentStateAdapter.createFragment` e `FragmentPagerAdapter.getItem`, pelo tipo de
   retorno alocado.

Saída: `componentType: "fragment"` mais `hostActivities[]` em `reachability[]`. Exige atualizar juntos
`JsonSchema.Keys` e `_JK`, por causa do teste de paridade INV-ANA-32.

**F2 — widgets do fragment na janela do host.** Para cada par (host, fragment) de F1, ligar a view
devolvida por `onCreateView` (e o `inflate` de `onViewCreated`/`DataBinding`/`ViewBinding.inflate`) a
uma janela `Host#Fragment`. Dois caminhos possíveis:
- (a) **no grafo de fluxo**: um `NFragmentNode` (ou reaproveitar `NActivityNode` com identidade
  própria) aceito por `addViewToWindowRoot`, e o ciclo de vida do fragment em
  `processFrameworkManagedCallbacks` (`gui/Flowgraph.java:118-156`), que hoje registra
  `"[TODO] Unhandled framework-managed class"`. É o conserto principiado. Faz `findViewById` e
  `setOnClickListener` do fragment caírem nas views certas, e faz `android:onClick` funcionar.
- (b) **no client, por pós-processamento**: localizar o nó de `inflate` dentro de `onCreateView` de cada
  fragment e chamar `collectWidgets` a partir dele. É mais barato, mas os listeners registrados sobre
  essas views só aparecem se o solver já os tiver resolvido para a subárvore órfã. Há indício de que
  resolve, porque o fluxo de `inflate`/`findViewById` é genérico. Isso precisa ser confirmado num APK
  antes de escolher (b).

A recomendação é começar por (b) como experimento descartável. Se os listeners aparecerem, (b) basta;
se não, vale (a).

**F3 — arestas fragment → fragment.** `<action>` do grafo de navegação, `navigate(R.id.action_x)` e
transações disparadas de dentro de listeners. Viram transições `Host#A → Host#B`. **O consumidor não
usa isso hoje**: o APE-RV não tem o conceito de "tela dentro da activity". `ActivityNode` é por classe
de activity e o lançador só abre activities [relato]. Aproveitar F3 exige um sinal de runtime de qual
fragment está na tela, por exemplo `dumpsys activity top`, que lista o estado do `FragmentManager` da
activity em primeiro plano. Isso é mudança no APE-RV e fica para depois.

**F4 — sementes.** Ciclo de vida e métodos públicos de fragment em `getEntryPoints` e
`complementWithCallbacks`. Corrige `reachable`, que hoje marca 22 % dos métodos de fragment. Também
melhora a cobertura de métodos usada como denominador.

### 3.6 Rendimento esperado e o que pode dar errado

- **Teto de rendimento**: os 65 apps com fragment, 40 % do corpus. Destes, os 55 em que fragments
  alcançam MOP são candidatos a ganhar widgets marcados. O estrato onde a guia agiu no estudo 03 tinha
  32 APKs. **Quanto F1+F2 o aumentam é a medida decisiva**, e ela é offline (§7.1).
- **WTG incompleta**: em 44 apps a WTG não termina. F1 e a variante (b) de F2 rodam no bloco barato
  (antes da WTG), e por isso funcionam também nesses apps, desde que a seção de janelas parcial já
  escrita os inclua. Isso tem de ser garantido no desenho.
- **Fragments criados por reflexão, por fábrica (`FragmentFactory`, Hilt) ou em bibliotecas** ficam de
  fora da atribuição. O efeito é perda de recall, não erro de atribuição.
- **Colisão de `shortId`** entre fragments do mesmo host (§3.4).
- **Re-análise do corpus**: qualquer mudança no produtor invalida os `.apk.json`. Isso não é problema
  para o próximo estudo, mas impede comparar com os artefatos congelados do estudo 03 sem rodar as duas
  versões.

---

## 4. Compose

### 4.1 Onde a série parou

Resumo, lido nos documentos [conferido]:

- A WTG colapsa em Compose. O boost MOP de widget foi 0 em 629.417 ações avaliadas, e a causa
  vinculante é o gator entregar zero widget marcado (`flagged=0`), não o resource-id
  (`20260731_verificacao_analise_percepcao.md` §1.2.1).
- Join por texto, saco de textos e `testTag` foram reprovados (`20260731_gator_compose_viabilidade.md`).
- A identidade de composable (FQN + arquivo:linha de `traceEventStart`) existe dos dois lados. O E1
  passou: 343 FQNs em runtime, 27/27 do app casando com o estático, ~1,8 µs por composable
  (`20260806_compose_e1_resultado.md`).
- Escolheu-se D1: sinal por tela = conjunto de composables ativos consultado numa tabela
  FQN → alcance. Ele esbarrou no pré-gate: 89,9 % das classes com composables estão saturadas em 100 %
  de `reachesTarget` (`20260803_compose_d1_decisao_plano_rearch.md` §6.1). `minHops` exigiria mudar o
  produtor.
- No APE-RV nada foi implementado. A rearch-07 apagou `isWidgetlessSubstrate()`, e o seam
  `llmPercentageNoSubstrate` segue sem consumidor [relato].
- O relatório de 03/10 do estudo 03 marcou como "aberta" a explicação por `ComposableLambdaImpl` e
  recomendou não afirmar causa para a saturação
  (`doutorado-tese/docs/estudo-03/escrita/20261003_compose-static-analysis.md` §2.2, §4.1 regra 4).

### 4.2 O que a série não sabia: a exclusão não exclui

**O fato** [conferido]:

- `Main.java:224-227` passa `-no-bodies-for-excluded` e `-exclude kotlin.`, `kotlinx.`,
  `androidx.compose.`, sem `.*`.
- `soot.Scene.isExcluded` só casa prefixo quando o padrão termina em `.*`. Medido no `petals`: 36.800
  classes de aplicação com os padrões atuais contra 12.842 com `.*`
  (`20260828_cadeia_medicao_rvandroid.md:877-880, 2146-2147`). A linha ficou "registrada e não
  reparada", porque mexer nela muda medição.
- Os padrões estão sem `.*` desde que a exclusão entrou (`65444e26`, gh51, 20/04). A análise da gh51,
  porém, os escreve com `.*` (`20260421_gh51_analise_callgraph_reachability.md:332`): a intenção era
  excluir de fato.

**A ordem das fases** [conferido]:

- O rebaixamento de `androidx.*` e `kotlin.*` para classe de biblioteca (via `libPackages.txt`,
  linhas 110 e 1425) acontece em `AnalysisEntrypoint.java:136-147`, dentro da transformação
  registrada no pack `wjtp` (`Main.java:262-268`).
- O Soot constrói o call graph no pack `cg`, antes do `wjtp`. Durante o SPARK, portanto, `Button`,
  `clickable`, `LaunchedEffect`, `ComposableLambdaImpl.invoke` e as corrotinas de `kotlinx` são classes
  de aplicação com corpo.
- Com `-p cg all-reachable:true` (`Main.java:234`), todos os seus métodos são pontos de entrada.

**O mecanismo que isso torna plausível** [hipótese]:

- Ponto de entrada tem parâmetros sem restrição de points-to.
- O corpo de `Button(onClick: () -> Unit, …)` chama `onClick.invoke()`, e o SPARK resolve essa chamada
  para **toda** implementação de `Function0` do app. Uma delas chega a JCA (lambda → ViewModel →
  repositório → `Cipher`).
- Todo composable do app que chama `Button`, `clickable` ou `TextField` passa a alcançar o alvo por
  intermédio do corpo da biblioteca. Isso explicaria:
  - os 96,1 % de `reachesTarget` entre composables contra 28,8 % nos demais métodos (série de julho,
    outro corpus);
  - o nulo do teste lateral da série (§6.5.2 do doc 1), que procurou o leque em parâmetros de métodos
    **do app** e não poderia vê-lo, porque o leque acontece dentro da biblioteca;
  - os 100 % de classes de fragment com `reachesTarget` da §3.3 (corrotinas e `LiveData`/`Flow` de
    `kotlinx`/`androidx` fazem o mesmo papel).

Mesmo com a exclusão funcionando, o problema não sumiria por inteiro. Com o framework *phantom*, a
aresta `composable → Button → onClick` simplesmente desaparece, e o alcance passa a depender de
`all-reachable` sobre as próprias lambdas do app. Isso daria uma super-aproximação diferente, não
precisão. O conserto principiado é modelar o despacho (a lambda passada a `onClick` é chamada quando o
elemento é clicado), como o GATOR faz para `setOnClickListener`. A pergunta barata que vem antes é se a
saturação **cai**. Se cair, o sinal FQN → alcance e o boost de widget de fragment passam a discriminar.

### 4.3 O que já existe para o lado produtor

O repositório do artigo do estudo 03 tem um protótipo em dexlib2 (`rvsec-study03-artigo/tools/compose-probe`,
change `e3-data-compose-static`), que rodou nos 163 APKs originais em 2026-10-03
(`data-analysis/compose-probe/out/20261003T163209Z/`). Agregação minha do `apps.csv` [conferido]:

| medida (80 APKs com composables do app) | APKs com ≥1 | mediana |
|---|---:|---:|
| raiz `setContent` em activity | 74 | 1 |
| destinos de navegação | 56 | 6 |
| rotas distintas | 47 | 4,5 |
| sítios de `navigate` | 46 | 2 |
| transições resolvidas (origem ≠ destino) | **20** | 0 |
| sítios de elemento (`Button`, `clickable`, …) com handler | 79 | 58 |
| bibliotecas: Navigation-Compose 55, Navigation 3 12, Compose Destinations 3, Voyager 1 | | |

Leitura: **tela e handler saem bem; aresta sai mal.** O protótipo acha os destinos e os handlers
`onClick` com suas classes de lambda em quase todos os apps. Ele raramente consegue atribuir a origem
de um `navigate` a uma tela, porque a lambda de navegação é criada longe do destino que a compõe. Para
guiar o teste, o par que importa é **tela → handlers → alcance**, e esse par sai. A aresta serviria a
um B9/pathfinding que o APE-RV também não tem.

O protótipo foi feito para descrever o corpus no artigo, não para alimentar o APE-RV. Ele não emite
`.apk.json`, e a regra `rv-android-generico-sem-dataset` não impede portá-lo: a lógica é semântica da
API Compose/Navigation, não do corpus.

### 4.4 O bloqueio que continua: o consumidor não tem chave nem canal

Mesmo com a tabela perfeita, o APE-RV não sabe **qual composable está na tela**. A chave de runtime
que existe é a identidade de composable do E1, entregue por um probe injetado. O canal para levá-la ao
jar está fechado por desenho: INV-RUN-06 proíbe input comportamental de `/sdcard` além de
`ape.properties`, e logcat como entrada é proibido [relato; `ape/openspec/specs/run-spec/spec.md:43`,
`action-selection/spec.md:65`]. As duas saídas registradas em agosto continuam as mesmas: um nó
sentinela na árvore de acessibilidade (efeito observador) ou emenda a INV-RUN-06
(`20260803_compose_d1_decisao_plano_rearch.md` §5.2).

Há uma terceira via, que não estava na mesa e não precisa de probe: **a guia por handler, sem
identificar a tela**. O protótipo dá, por app, as classes de lambda dos `onClick`. O que o APE-RV
precisaria é ligar o clique executado ao handler, e isso já sai da instrumentação de cobertura. Ela
registra quais métodos rodaram, e a lambda executada identifica o handler *depois* do clique. Isso
serve para aprendizado (que ação levou a código MOP), mas não para escolher *antes*. Por isso fica
registrada como ideia, não como recomendação.

### 4.5 Desenho para Compose, em ordem

- **C0 — decidir a saturação (barato, descartável, decisivo).** Mesmo protocolo do experimento de
  07/08 (`20260730…` §6.5.1): patch de constant pool numa **cópia** de `lib/gator`, rodada com
  `--gator-dir` apontando para a cópia, sobre o APK **original** e com `-v` para conferir os
  `[SOOT-ARG]`. Dois braços contra a linha de base:
  - (i) `kotlin.*`, `kotlinx.*`, `androidx.compose.*`;
  - (ii) os mesmos padrões mais `androidx.*`.

  Quatro APKs: `parceltracker` (Compose, já usado em 07/08), um só-View, e dois fragment-heavy
  (`mtgfam`, `wikipedia`). Medir `reachesTarget` por estrato de método (composable, fragment, demais),
  o tamanho do call graph e o tempo. **Portão**: a linha de base tem de reproduzir o `.apk.json`
  vigente. **Previsão da hipótese**: queda grande em composables e fragments, pequena em métodos de
  activity. Se não cair, a hipótese morre e a §4.2 vira registro.
- **C1 — passada Compose no produtor.** Portar a lógica do `compose-probe` para um `InvokeVisitor` do
  gator, emitindo por app os composables (FQN), as telas (destino ou raiz `setContent`), os handlers
  por tela e o alcance graduado (`minHops`, que a BFS reversa já calcula e descarta;
  `20260803_compose_d1…` §6.1). Isso só vale a pena se C0 mostrar que o alcance discrimina.
- **C2 — chave e canal no APE-RV** (D1 de agosto), condicionado a C1 e a uma decisão sobre INV-RUN-06.
  É change no repositório `ape`.

---

## 5. O que a literatura oferece

Tudo nesta seção é [relato] do subagente de literatura. Ele leu o PDF dos trabalhos marcados com
[web], porque os resumos do WebFetch inventaram detalhes duas vezes, e leu o código local quando
existia (`workspace-rv/GoalExplorer`, `SceneDroid`, `backstage`, `Gator`). Não reconferi linha a linha.

**Fragments: quem modela, e como identifica a tela em runtime.**

| ferramenta | como acha fragments | tela | identidade em runtime | androidx / Navigation |
|---|---|---|---|---|
| GoalExplorer (ASE 2019) | `<fragment>` em layout + análise interprocedural de transações | activity + conjunto de fragments (+ menu/diálogo) | `dumpsys activity top` ("Added Fragments") | não: só `android.app`/support-v4 (`FragmentChangeAnalysis.java:740-767`, "To-do add androidx later"); `NavigationComponentAnalyzer` é stub vazio |
| ICCBot (ICSE 2022 demo) | layout + `inflate` + sequência de transação válida até `commit` | ⟨act, frag⟩, ⟨frag, frag⟩ e o conjunto de hosts de cada fragment | — | sem menção |
| SceneDroid (ASE 2023) | dinâmico; usa o CTG do ICCBot para lançamento indireto | "cena" = layout que difere da activity | `dumpsys activity top`, só o primeiro fragment | registra que ICCBot e GoalExplorer **não** pegam `navigate(actionId)` |
| FragDroid (DSN 2018) | varredura de smali; modelo A→A, A→F, F→F | fragment | força a troca por reflexão (`FragmentManager` + `commit`) | — |
| DeUEDroid (ISSTA 2023) | API de transição + `NavController`, alvo por *taint* | activity e fragment | — | único que trata Navigation; não diz se lê o XML |
| StoryDroid (ICSE 2019) | `replace`/`add` + `commit`, `setAdapter` | funde fragments de volta em activity | — | — |
| Frontmatter (FSE 2021 demo) | arestas de `FragmentManager` e `onCreateView` no call graph do FlowDroid | — | — | — |

Três pontos importam aqui:

- O GATOR original, segundo o DeUEDroid, "does not account for fragment-related transitions and
  navigation-based transitions". Isso confirma a §3.1 de fora.
- **Ninguém lê `res/navigation/*.xml`** entre os trabalhos encontrados.
- O mecanismo `NavController.handleDeepLink` abre **qualquer destino** do grafo a partir de uma activity
  exportada que hospede o `NavHostFragment`. Basta passar os ids no extra
  `android-support-nav:controller:deepLinkIds` (PT Swarm, 2024; o Google tratou como documentação, não
  como defeito). Os ids saem do XML de navegação e do `R`. Isso daria ao `MopLauncherStage` um "lançar
  fragment" análogo ao "lançar activity" que ele já tem [hipótese minha].

**Compose: nada novo que extraia do APK.** O GAPS (arXiv 2511.23213) declara que não suporta Compose e
chama o problema de aberto. Navigation 3 está estável desde 19/11/2025 e tira o `navigate()` de cena:
o app manipula a pilha. O HapTest (FSE 2025, OpenHarmony/ArkUI) monta um grafo de páginas estático a
partir do **fonte** (decoradores + `router.pushUrl` dentro de `onClick`). É a receita mais próxima do
que o `compose-probe` faz, mas ainda sobre fonte. Os trabalhos recentes de teste com LLM (EpiDroid,
GraphDroid, FuncDroid) não citam Compose nem fragments.

**Teste dirigido: quem define alvo como fragment.** Só o GoalExplorer (tela = activity + fragments,
casada em runtime por `dumpsys`) e o FragDroid (força por reflexão). O GAPS, o mais forte em alvos
de método (57,44 % de alvos alcançados contra 12,82 % do APE), resolve o alvo até o nível de activity
e de ids de `findViewById`.

---

## 6. O bind estático → runtime, e quanto ele vale

Análise estática só guia o teste se cada widget estático encontrar o seu nó de runtime. Por isso a
eficácia do bind tem de ser medida em três degraus, e os três são diferentes:

1. **Casamento**: a fração dos nós acionáveis de runtime que encontra um widget estático.
2. **Valor preditivo da marca**: dado que casou e foi clicado, quanto mais provável é chegar a código
   MOP do que num clique comum.
3. **Teto do desfecho**: quanto do que se quer achar (violações) está em código que a análise estática
   enxerga.

### 6.1 O que o E6 já mediu sobre o bind que existe (estrato View)

Lido em `doutorado-tese/docs/estudo-03/analise/scripts/20261003_e6_dose_orientacao/README.md` e
`m4_power/a_signals.out` [conferido nos arquivos de resultado; as contas são da triagem r3, não
refeitas por mim]:

- **Casamento**: no braço com orientação, a tela ofereceu widget marcado em 11.795 de 304.306 passos
  (3,88 %), em 22 APKs. Quando ofereceu, a ação executada levou o reforço em 58 % das vezes. A taxa de
  casamento por nó não foi medida diretamente. A verificação de julho, em outro corpus, achou
  resource-id em 53–96 % dos passos dos apps View e em 5,7 % dos passos Compose.
- **Valor preditivo — este é o número que importa**: depois de um clique em widget marcado (7.106
  passos, 24 APKs), JCA nova em **7,2 %**, contra **6,7 %** nos passos comuns dos mesmos APKs. A
  razão é ~1,07. **Quando o bind funciona, a marca quase não informa.** O motivo está na própria
  medição:
  - 41 % dos 11.631 widgets com handler de clique têm handler que alcança a JCA, todos por via
    transitiva;
  - nenhum alcança a 0 saltos, então o peso direto (+500) nunca age;
  - nas activities, a seletividade é pior: mediana de **100 %** das activities com algum método que
    alcança alvo.

  É a saturação da §4.2, vista do lado do desfecho.
- **O que funcionou foi a navegação, não o widget** (`m6_steps_methods/analyze.out`, janela de 3 passos,
  braço MOP): depois de um salto do lançador de activities, chamador direto novo em 10 de 1.522 passos
  (0,66 %), contra 0,046 % nos passos comuns (razão de Mantel-Haenszel 7,9, IC [3,5; 14,2]; 8 APKs).
  Depois de um passo em que o boost de widget mudou a escolha, 3 de 1.823 (razão 0,6). Números
  pequenos, mas na direção: levar o explorador para a tela certa rende; empurrar o clique dentro da tela
  não.
- **Teto**: dos 101 sítios distintos de violação primária, **70 estão em biblioteca**, e nenhuma
  dessas classes aparece no `reachability` do artefato (0/70). Só 31 sítios, em 21 APKs, estão no
  código do app. A análise estática mira só esses 31. Sobre eles, `reachesTarget` e
  `directlyReachesTarget` têm recall de 100 %. *Correção de 05/10 (§6.8)*: "fora do alcance" vale
  para os sítios do startup, não para todos os de biblioteca. 42 sítios de biblioteca ocorrem durante
  a interação.

**Consequência direta para fragments e Compose**: ampliar o bind sem mudar a marca produz **mais
casamentos de um sinal que não discrimina**. F1+F2 aumentariam o degrau 1 em 65 apps e deixariam o
degrau 2 em ~1,07. Por isso o C0 (saturação) vem antes, e o experimento de fragments (§7.1) precisa
medir o degrau 2, não só o 1.

### 6.2 Fragments: a chave existe, falta o lado estático e a desambiguação

- **Chave**: `(topActivity, resource-id)`. Views de fragment têm resource-id, e o `topActivity` em
  runtime é o host, que é a chave do lado estático depois da fusão por `#` (§3.4). Não há chave nova
  a inventar.
- **Risco de casamento errado**: o mesmo `shortId` em dois fragments do mesmo host (`btn_save`,
  `recycler`, `toolbar`). Duas desambiguações possíveis, em ordem de custo:
  1. **Impressão digital por resource-ids**: o lado estático sabe o conjunto de ids de cada fragment,
     e o runtime tem o conjunto de ids da tela. Escolhe-se o fragment de maior interseção.
     Diferentemente do saco de textos, reprovado em Compose (§4.1), ids de View são estáveis entre
     execuções e não dependem de dado do usuário. É o candidato natural, e mede-se offline.
  2. **Fragment ativo pelo sistema**: `dumpsys activity top` lista os fragments adicionados. É o que
     GoalExplorer e SceneDroid fazem (§5). Custa uma chamada ADB por estado novo, e o APE já chama
     `dumpsys activity` hoje [relato]. Exige a chave `(activity, fragment, shortId)` no jar.
- **Eficácia esperada do casamento**: alta onde há resource-id, mas é hipótese até medir. Se a
  impressão digital resolver as colisões, o APE-RV não muda.

### 6.3 Compose: a chave só existe dentro do processo, e o handler pode ser a chave

Na árvore de acessibilidade não há chave (§4.1). Dentro do processo do app há duas. A identidade de
composable (E1) diz **quais composables estão na tela**. A segunda, nova, diz **qual handler cada
elemento clicável dispara**:

- **Conferido no bytecode do `parceltracker`**:
  - a ação de clique que o Compose publica na árvore de semantics é a lambda
    `androidx.compose.foundation.AbstractClickableNode$applySemantics$1`, com o campo `this$0` do tipo
    `AbstractClickableNode`;
  - `AbstractClickableNode` guarda a lambda do app no campo privado `onClick: Function0` (há também
    `getOnClick()`);
  - nomes intactos neste build de debug.
- **Logo, um probe em processo** (o mesmo mecanismo do E1, injetado pela instrumentação dexlib2) pode
  percorrer os nós de semantics e, para cada nó com ação de clique, obter: `bounds` (os mesmos que o
  APE vê no nó de acessibilidade) → `onClick.getClass().getName()` → a classe de handler. O
  `compose-probe` já extrai essa classe do lado estático, por sítio de elemento, inclusive através
  das pontes `$$ExternalSyntheticLambda` do R8 (`e3-data-compose-static`, D8c).
- **O bind fica por classe de handler**, que existe dos dois lados, sem precisar identificar a tela
  nem casar texto. Isso evita a cadeia J2 que o doc 4 de agosto considerou o maior risco
  (composição → `LayoutNode` → `SemanticsNode.id` → nó de acessibilidade). Aqui o probe já parte do
  nó de semantics.
- **O que falta**:
  1. **Medir em execução** (E2, mesmo custo do E1: um descritor e um `.java`): a fração de nós
     clicáveis cuja classe de handler o probe recupera, e a fração dessas que casa com o
     `handler_lambda_class` estático;
  2. **o canal** probe → APE-RV. Continua fechado por INV-RUN-06 e pela proibição de logcat
     (§4.4). Com o bind feito dentro do processo, o canal só precisa carregar "estes retângulos são
     MOP", consultado no momento do snapshot. As opções seguem sendo emenda de invariante ou escrita
     na semântica (efeito observador).
- **Eficácia**: desconhecida nos três degraus. O degrau 2 herda a saturação, como em View.

### 6.4 Como medir o degrau 2 antes de construir qualquer bind novo

O E6 deixou os dados para isso. Basta trocar a marca booleana por uma graduada e recomputar o
"JCA nova depois do clique" por gradação:

- **com o artefato atual**: separar os 7.106 cliques marcados pela fração de handlers da tela que
  são marcados (marca rara na tela × marca comum). Se a marca rara tiver razão bem acima de 1,07, há
  sinal escondido pela saturação;
- **depois do C0**: refazer com `reachesTarget` recomputado sob exclusão efetiva. Se a razão subir, a
  correção do produtor vale também para View, antes de fragments e Compose.

**Resultado com o artefato atual (05/10)** [conferido; scripts e saídas em
`doutorado-tese/docs/estudo-03/analise/scripts/20261005_e6_graduacao_marca/`, `README.md`]:

- **A graduação.** Ela usa o par `dec.mopx = [boosted, total]` de cada passo, calculado em
  `MopWidgetPass.apply` (`ape@e93dea86`, `agent/scoring/MopWidgetPass.java:55-83`). O desfecho é o
  rótulo de janela de 3 passos do M8 ("JCA nova").
- **O `com.ds.avare_404.apk` ficou de fora.** Os brutos aperv dele no E6 foram sobrescritos em 05/10
  por um reinício do container `e6_07`. O README da pasta registra o desvio.
- **A marca raramente é rara.** Na mediana, 6–7 alvos da tela são marcados, 67 % dos alvos. Telas
  com 1–3 marcados respondem por 11,5 % (MOP) e 30,2 % (MOP+LLM) dos cliques marcados.
- **A novidade do clique pesa mais que a marca.** Clique em ação inédita rende de 4 a 7 vezes o
  repetido (17–19 % contra 3–5 % nos passos comuns). Sem controlar a novidade, a marca rara parecia
  ter sinal só no braço MOP (MH 1,92) e nenhum no MOP+LLM (0,91). A diferença era de composição: 40 %
  dos cliques raros do MOP eram inéditos, contra 14 % no MOP+LLM.
- **Com a novidade controlada** (clique marcado inédito contra passo comum inédito, mesmos APKs):
  - marca rara (≤ 3 na tela): MH **1,63** [1,25; 2,17], 577 cliques, 37 estratos braço × APK. O
    resultado se reproduz nos dois braços: 1,68 [1,15; 2,62] no MOP e 1,56 [1,12; 2,26] no MOP+LLM;
  - marca comum (≥ 4): 0,85 [0,65; 1,24];
  - marca booleana sem graduação: 0,96 [0,75; 1,36].
- **Ressalva do desfecho.** "JCA nova" é 98 % primeira execução de método só transitivo, o próprio
  conjunto saturado. Sobre o desfecho seletivo (chamador direto ou misuse novo) há 8 e 13 eventos em
  4 e 5 APKs, contagem que não permite concluir nada.

**Leitura.** A marca booleana não informa nada além da novidade. Ela só carrega sinal quando é rara
na tela, e então o sinal é de cerca de 1,6 vez. Isso é coerente com a saturação diluindo a marca. Uma
mudança só no consumidor tem base, limitada a esse desfecho: ponderar o reforço pelo número de alvos
marcados na tela, mantendo a preferência por ação inédita. Ela não substitui a orientação dirigida
por alvo (§6.5), única que mira o desfecho seletivo. Aqui "inédito" é por estado abstrato. Com a
novidade por activity (§6.6), a marca rara sobe para 2,01 [1,57; 2,67].

### 6.5 O que dá valor ao APE-RV: guiar para o alvo, não para a marca

Os resultados do E6 já mostram onde está o sinal seletivo
(`20261003_e6_dose_orientacao/m1_location/m1_location.out`, `m1_reachable.out`, `m4_power/a_signals.out`,
`m5_why_direct/m5_q3_breadth.csv`, `m5_q5_proxy.csv` [conferido nos arquivos; agregação minha das
duas últimas]):

| fato | valor |
|---|---|
| sítios de violação primária (união dos braços) | 105 em 54 APKs: 71 em biblioteca, 34 no app; 33 no startup |
| sítios no app durante a interação (alvo: chamador direto) | **30, em 18 APKs** |
| sítios em biblioteca durante a interação (alvo: fronteira app → biblioteca, §6.8) | **42, em 32 APKs** |
| desses 30, quantos estão numa classe activity ou no conjunto A′ | **0** |
| métodos do app que chamam a JCA diretamente | 495 em 81 APKs; mediana **3 por APK**, em geral num só pacote |
| recall desses métodos sobre os sítios do app | **34/34** |
| seletividade (fração dos métodos do APK marcada) | `directlyReachesTarget` mediana **0 %**; `reachesTarget` mediana 25 % |
| desses 495, quantos o gator marca como `reachable` | 215 (os demais não têm semente: fragment, ViewModel, DI) |
| APKs sem nenhum chamador direto, mas com `reachesTarget` > 0 | 82 de 82, mediana 27 % dos métodos (o alcance passa por biblioteca) |
| handlers marcados na mesma classe que um chamador direto (32 APKs) | 0 de 207 chamadores; mesmo pacote em 11 |

**A leitura**: o **alvo** seletivo já está no artefato (`reachability[].methods[].directlyReachesTarget`); o **caminho** da UI até ele, não — o `.apk.json` só carrega booleanos por método, sem arestas nem distância. São os ~3 métodos por APK que chamam a
JCA, que cobrem todos os sítios do app. O que a orientação de hoje usa é outra coisa: a pergunta
"este handler alcança *algum* alvo?", que satura. Os handlers e os chamadores diretos moram em
camadas diferentes (UI → ViewModel → repositório → utilitário de cripto). Por isso nenhum handler
está a 0 saltos e a marca transitiva vale para quase tudo.

**O que daria valor** é trocar a pergunta: *"este handler leva, em poucos saltos dentro do código do
app, a um dos chamadores diretos que ainda não executaram?"*. É orientação dirigida por alvo, como em
GoalExplorer e GAPS (§5), e é seletiva por construção, porque o alvo é raro. Ela pede quatro peças no
produtor e uma no consumidor:

1. **Call graph sem o leque de biblioteca, com a aresta de lambda explícita.** Corrigir as exclusões
   (§4.2) corta o leque. Para não perder os caminhos legítimos que passam por biblioteca
   (`setOnClickListener`, `onClick = {}` do Compose, `viewModelScope.launch {}`, `Flow.collect {}`),
   acrescenta-se uma aresta direta "método do app que passa a lambda L a um método de biblioteca →
   `L.invoke`". É o modelo de callback por argumento que o GATOR já aplica a `setOnClickListener`,
   generalizado a qualquer `FunctionN`/interface funcional alocada no app.
2. **Distância por alvo.** `minHops(handler, chamador direto)`, calculado pela BFS reversa semeada em
   cada chamador direto, e não no conjunto de todos os alvos. A BFS já existe (`multiSourceBfs`); muda a
   semente e guarda a distância em vez do booleano.
3. **Handlers de todas as telas.** Os de View já existem. Os de fragment entram por F2 (§3.5). Os de
   Compose entram pelas classes de lambda `onClick` (§6.3; o `compose-probe` já as extrai).
4. **Tela hospedeira de cada handler**, para navegar até ela: activity e fragment (F1), e o destino de
   navegação no Compose. Serve ao lançador, que hoje só abre activities, e ao deep link do Navigation
   (§5).
5. **No consumidor**: a pontuação do widget passa a vir da distância ao chamador direto mais próximo
   ainda não executado. O "ainda não executado" não precisa de cobertura de métodos. O APE-RV já tem o
   `UICoverageTracker` (`ape/.../utils/UICoverageTracker.java`, spec `ape/openspec/specs/ui-coverage/spec.md`),
   que registra por estado quais widgets já foram exercitados, além de `visitedCount` por ação e do
   limite de picks por alvo. Um handler que leva ao chamador X e já foi exercitado indica, de forma
   aproximada, que X já teve a sua chance. A §6.6 analisa isso no código e nos dados do E6 (correção
   do Pedro em 05/10; a primeira redação desta seção dizia que o dado não existia).

**O que isso não muda**, e o estudo precisa dizer:

- 33 dos 105 sítios ocorrem no startup (4 no app e 29 em biblioteca). Nenhuma orientação por UI os
  move. *Correção de 05/10*: a primeira redação dizia que os 71 de biblioteca também não se moviam.
  Mas 42 deles ocorrem durante a interação. A orientação dirigida aos chamadores diretos não os
  alcança, porque a chamada à JCA está dentro da biblioteca; um alvo na fronteira app → biblioteca
  poderia alcançá-los (§6.8).
- Dos 81 APKs com chamador direto, em 29 nenhum braço executou nenhum deles no E6, nem o E2 em 99
  execuções por APK (login, servidor, root, hardware, entrada válida ou código morto).

O teto do que a orientação por chamador direto pode mudar é da ordem dos **30 sítios em 18 APKs** do
E6. Com o alvo de fronteira (§6.8), soma-se até 42 sítios de biblioteca durante a interação, em 32
APKs. Medir o efeito
sobre o total de violações dilui o tratamento no que ele não pode alcançar. A medida que responde à
pergunta do tratamento é a execução dos chamadores diretos (`cov_directly_reaches_mop`, que o E6 já
tem) e as violações de origem no app durante a interação. Trocar o desfecho primário de uma nova
campanha é decisão sua, e é mudança no que se mede, não reparo.

### 6.6 "Já exercitado": o que o APE-RV sabe, e em que granularidade

O código lido é o do HEAD do `ape`. Os arquivos citados não mudaram desde `e93dea86`, o jar do E6
(`git diff --stat` vazio). As medições estão em
`doutorado-tese/docs/estudo-03/analise/scripts/20261005_e6_graduacao_marca/` (`m10_*`), sem o avare
(§6.4).

**Três memórias, em três granularidades** [conferido]:

| memória | onde | granularidade | sobrevive ao refinamento de estado? | quem consulta |
|---|---|---|---|---|
| visitado/inédito da ação | `GraphElement.firstVisitTimestamp`/`visitedCount` (`model/GraphElement.java:26-75`), marcado em `Graph.markVisited` (`model/Graph.java:583-611`) | estado abstrato | Em parte. `Model.rebuild` (`model/Model.java:251-356`) refaz os estados e repete só as transições executadas, que voltam a marcar a ação no estado refinado de onde partiram. Os estados irmãos, e qualquer outro estado em que a mesma tela reapareça, recebem cópias inéditas do mesmo widget. | atalho MOP `selectUnvisitedMopTarget` (filtro `ENABLED_VALID_UNVISITED`, `ActionFilter.java:49-53`, `agent/SataAgent.java:621-628`), roleta EARLY_STAGE, `[, UNVISITED]` no trace |
| `UICoverageTracker.activityInteracted` | `utils/UICoverageTracker.java:80, 148-167, 260-266` | activity × `Name.toXPath()` × tipo de ação | Sim. Monotônico, nunca despejado (INV-COV-09, `ui-coverage/spec.md:266`), O(1) por consulta. | `CoveragePass` (`agent/scoring/CoveragePass.java:47-53`): o reforço de cobertura (`dec.cov`) só vai para widget não exercitado na activity |
| limite de escolhas MOP | `SataAgent.mopPickKey`/`pickCappedMopTarget` (`agent/SataAgent.java:691-709, 836-857`), `ape.mopTargetPickCap = 3` | activity × xpath × tipo, igual à anterior | Sim. | só os sítios determinísticos do MOP |

O mapa por estado (`stateData`, LRU de 2.000 estados, `Config.java:204`) e o consolidado
(`activityRollup`) servem ao `getCoverageGap` e ao resumo `UICOV`/`UICOV-ACT` do fim da execução. Não
servem para decisão por widget.

**Medição: a novidade por estado é, na maior parte, falsa** [conferido]:

- **A reconstrução.** Reconstruí a novidade por activity a partir de `dec.a`: tripla (activity, tipo,
  `Name.toString()` do alvo), não executada antes na tarefa. Ela coincide com o `dec.cov > 0` do jar
  em 100 % dos 746.170 passos com alvo dos três braços. A chave é a mesma do `activityInteracted`.
- **A falsa novidade.** Dos cliques "inéditos" pela marca de estado, **59–67 %** já tinham sido
  executados na mesma activity: 18.727 de 31.513 no MOP+LLM, 31.343 de 47.642 no MOP e 32.380 de
  48.605 no fork. Entre os cliques marcados, 65–68 %. O atalho MOP escolhe por esse filtro; só o
  limite de 3 escolhas por chave segura a repetição.
- **O rendimento segue a novidade por activity.** JCA nova na janela de 3 passos, passos comuns, por
  braço:
  - inédito nas duas granularidades: 30,1 % (MOP) e 26,6 % (MOP+LLM);
  - inédito no estado, mas já feito na activity: 13,4 % e 14,7 %;
  - repetido: 3,0 % e 4,8 %.
- **A marca rara, com a novidade por activity controlada** (clique marcado contra passo comum, ambos
  inéditos na activity, mesmos APKs):
  - marca rara (≤ 3 na tela): MH **2,01** [1,57; 2,67], 192 cliques, 33 estratos braço × APK. Nos
    dois braços: 2,01 [1,46; 2,98] no MOP e 2,02 [1,38; 3,13] no MOP+LLM;
  - marca comum (≥ 4): 1,15 [0,92; 1,55];
  - qualquer marca: 1,30 [1,07; 1,71].
  - Entre cliques repetidos, a marca comum fica abaixo do passo comum: 0,65 [0,48; 0,91].
- **A ressalva da §6.4 continua valendo**: "JCA nova" é quase toda primeira execução de método só
  transitivo.

**Leitura para o desenho (Passo 3)**:

- **O sinal de "já exercitado" que serve está no dispositivo e custa O(1)**: é o
  `activityInteracted`, na granularidade de activity. Não precisa de cobertura de métodos nem de
  canal novo. Para pontuar uma ação, basta consultar
  `hasActivityInteraction(activity, widgetId(ação))`, como o `CoveragePass` já faz.
- **O atalho MOP: ordenar, não filtrar** [hipótese de mudança, não medida como intervenção].
  - **O que ele faz hoje.** Filtra por inédito no estado. Dois terços dos seus "inéditos" são
    repetições na activity.
  - **O limite de 3 escolhas por chave é decisão registrada, não descuido.** A change
    `mop-target-revisit-cap` (`ape/openspec/changes/archive/2026-07-07-mop-target-revisit-cap/`)
    escolheu a chave por activity justamente porque o refinamento re-arma o widget. Escolheu 3
    tiros, e não 1, porque os widgets que produziram violação dispararam "nas primeiras interações".
  - **Rendimento dos cliques marcados do E6**, por tipo de novidade:
    - inédito na activity: 38,3 % e 36,1 % de JCA nova, 1.264 cliques;
    - inédito só no estado (2º e 3º tiros): 7,0 % e 5,2 %, 2.547 cliques;
    - repetido: 1,8 % e 3,6 %.

    O desfecho seletivo teve 13 eventos no primeiro grupo e 2 no segundo.
  - **Por que filtrar por activity seria errado.** Equivaleria a um limite de 1 tiro. Contrariaria a
    decisão registrada e perderia os 2º e 3º tiros, que rendem como um passo comum (~6–7 %), e não
    zero.
  - **Também não quebraria o modelo.** O atalho só se antecipa à escolha. Quando não acha candidato,
    a seleção segue para os canais do SATA (menos visitado, roleta, EARLY_STAGE), que continuam
    usando o inédito por estado. As marcas de visita do grafo não mudam.
  - **A proposta coerente com a decisão registrada é ordenar dentro do atalho.** Primeiro os alvos
    inéditos na activity; depois os inéditos só no estado, até o limite de 3. Nenhum candidato sai.
    Muda só a ordem dos tiros. É mudança no comportamento do braço com MOP, e por isso é decisão sua.
- **"Aposentar o alvo X" pede um estado por alvo**, que hoje não existe. A memória é por widget. Um
  alvo X (chamador direto) pode ser alcançado por vários handlers, em vários widgets e telas. Para
  dizer "X já teve a sua chance", o dispositivo precisa saber, por widget, quais alvos ele alcança, e
  manter o conjunto de alvos cujos widgets já foram exercitados na activity. A agregação é do
  Passo 3.
- **A chave do lado estático continua sendo `(activity, shortId)`**, ligada ao nó resolvido pelo
  `MopWidgetPass`. O `widgetId` do rastreador é `xpath|tipo` sobre o `Name`. O `Name` só contém o
  resource-id quando o namer da tela o inclui: no E6 aparecem nomes com `resource-id=` e nomes só com
  `class=…;enabled=…` [conferido em amostra; a proporção não foi medida]. O registro "alvo exercitado"
  deve ser gravado no momento da execução, a partir da ação executada, que tem os dois lados. Não deve
  ser reconstruído casando `xpath` com `shortId`.

### 6.7 Desenho para vários caminhos e vários alvos (proposta para decisão)

Tudo aqui é proposta. Os números de parâmetro (Dmax, K, pesos, limite) são pontos de partida, e o
desenho inteiro só vale se o 7.5 mostrar que a distância discrimina (§7.5).

**O que já existe e o que falta** [conferido]:

- **O produtor.** Faz uma única BFS reversa sobre o call graph do SPARK, semeada com alvos ∪
  chamadores diretos, e guarda só o booleano `reachesTarget`
  (`client/.../reach/ReachabilityEngine.java:126-132`; `multiSourceBfs` em
  `RvsecAnalysisClient.java:497-520`).
- **O que falta é a distância por chamador direto.** Ela sai trocando a semente (um chamador por vez)
  e guardando o nível da BFS. Isso precisa do grafo, que só existe dentro do GATOR. O `.apk.json` não
  tem arestas, então o `derive_mop_artifact.py` não consegue calculá-la.
- **O tamanho do problema no corpus** (163 `.apk.json`):
  - 52 APKs têm ao mesmo tempo widget com handler (com `idName`) e chamador direto. É onde a
    orientação por widget pode agir hoje; fragments e Compose aumentariam esse número.
  - Nesses 52, a mediana é de 24 chaves de widget com handler (máximo 3.320) e 2,5 chamadores
    diretos (máximo 32).

**Definições:**
- C = os chamadores diretos do APK (`directlyReachesTarget`), numerados de 0 a |C|−1.
- d(m, c) = número mínimo de arestas de m até c no grafo do produtor, limitado a Dmax (proposta: 6).
- O grafo é o vigente, ou o corrigido pelo C0 e pela aresta de lambda (§6.5, peça 1). É o 7.5 que diz
  qual deles serve.

**Agregação** (a correção 2 do Pedro):

1. **Vários caminhos entre um handler e um alvo: vale o mais curto.** d(h, c) já é o mínimo. Somar
   ou contar caminhos não serve: num call graph sobre-aproximado, o número de caminhos mede o leque
   da biblioteca, que é exatamente o artefato da saturação.
2. **Vários handlers num widget** (vários listeners, ou a recuperação D8 pela classe que envolve a
   lambda): d(w, c) = mínimo sobre os handlers do widget.
3. **Vários alvos por widget: guardar os K mais próximos** (proposta: K = 3) com d ≤ Dmax. A
   pontuação usa o **mais próximo ainda não aposentado**. O número de alvos distintos não aposentados
   dentro de d+1 entra só como desempate, para premiar um widget que leva a mais de um alvo sem deixar
   o leque dominar.
4. **Vários widgets e telas levando ao mesmo alvo.** Cada widget carrega o seu vetor. O alvo é
   aposentado por um contador próprio (abaixo), e não por widget.
5. **A raridade na tela.** A §6.4 e a §6.6 mostraram que a marca só informa quando é rara: 2,01 com 1
   a 3 marcados, 1,15 com 4 ou mais. Com distância, a raridade vem da construção (poucos widgets
   ficam perto de um dos ~3 chamadores). Mesmo assim, se vários widgets da tela empatarem na melhor
   distância, o reforço se divide pelo número de empatados.

**Onde cada coisa é calculada:**

| onde | o quê | custo |
|---|---|---|
| host, GATOR | uma BFS reversa por chamador direto, com profundidade até Dmax; no `.apk.json`, a lista `C` (assinaturas) e, só para métodos que são handler de listener ou callback de activity (depois, de fragment e de lambda Compose), o vetor `[[i, d], …]` | ≤ \|C\| BFS sobre o mesmo grafo (mediana 2,5; máximo 32) |
| host, `derive_mop_artifact.py` | d(w, c) por chave `(activity, shortId, eventType)`, pela mesma junção listener → handler (com a recuperação D8) que já produz a flag; os K mais próximos; por activity, o mínimo sobre os seus widgets e callbacks, para o lançador | linear no tamanho do `.apk.json` |
| dispositivo, APE-RV | `int[|C|]` de contadores; a pontuação por ação; a ordem do atalho e do lançador | O(K) por ação candidata |

**O que vai para o dispositivo, e o tamanho.** Por widget, `[[i, d], …]` com até K pares; por
activity, idem; e |C|. Nenhuma assinatura e nenhuma aresta. Limite superior medido no corpus, contando
todos os widgets com handler como se alcançassem algum alvo (`doutorado-tese/.../20261005_e6_graduacao_marca/m11_payload.py`):
- com K = 3: mediana de 30 pares (~270 bytes) e máximo de 9.960 (~90 KB);
- o artefato atual tem mediana de 5,0 KB e máximo de 263 KB (163 `.mop.json` do E6).

O valor real é menor, porque só entram widgets a d ≤ Dmax.

**No dispositivo:**
- **Aposentar um alvo.** Quando uma ação é executada e o seu widget é exercitado pela primeira vez
  na activity (a transição de `hasActivityInteraction` de falso para verdadeiro, §6.6), cada c do
  vetor do widget ganha +1 no contador. c se aposenta quando o contador chega a N. Proposta: N = 3,
  pelo mesmo argumento registrado da `mop-target-revisit-cap`: o que dispara, dispara nas primeiras
  interações. Isso é aproximado: clicar no handler não garante executar c. A alternativa exata,
  marcar c ao ser executado, exigiria ler a cobertura em execução, o que o canal proíbe (INV-RUN-06).
- **A pontuação.** Peso pela distância ao mais próximo não aposentado, somado à prioridade
  (INV-MOP-03 mantido). Proposta: 500 para d ≤ 1, 400 para d = 2, 300 para d = 3 e 0 além de Dmax.
  Isso substitui a escada direto/transitivo (+500/+300) da "MopScorer — Priority Boost"
  (`mop-guidance/spec.md:156-170`).
- **O atalho MOP.** Primeiro os inéditos na activity, depois pela pontuação; o limite de 3 escolhas
  continua (§6.6).
- **O lançador.** Ordena as activities pela distância mínima a um alvo não aposentado. No E6 foi o
  lançador, e não o widget, que moveu chamadores diretos (§6.1).

**Specs que mudam:**

| repositório | spec / invariante | mudança |
|---|---|---|
| rv-android | `analysis`: `JsonSchema.Keys` = `_JK` (INV-ANA-32, `openspec/specs/analysis/spec.md:380`) | campos novos nos dois lados; o INV-ANA-64 (`reachesTarget ⊇ directlyReachesTarget`) não muda |
| ape | `static-analysis-entrypoints`, item 3 (widgets, `spec.md:182`) | campo novo por widget e por activity; `formatVersion` 1 → 2; ordem canônica do vetor (INV-DRV-05) |
| ape | INV-DRV-06 (`spec.md:208, 253`) | **emenda explícita, e a decisão é sua**: o vetor não tem chave `*Target*` nem seção de call graph, mas carrega informação derivada do call graph; a letra do invariante passa, o espírito precisa ser reescrito. A regra R9 (métricas só leem o JSON completo) não muda |
| ape | `mop-guidance`: "MopScorer — Priority Boost"; INV-MOP-19 (colisão de `shortId`: hoje vence a flag mais forte; passaria a ser o mínimo por alvo) | pontuação por distância |
| ape | `action-selection`: INV-SEL-MOP-01..05 | ordem do atalho; o limite (INV-SEL-MOP-04) continua |
| ape | `event-sink` | telemetria de aposentadoria e da distância escolhida; o custo em bytes passa pelo INV-SNK-13 |

**O que este desenho não resolve:**
- Os 33 sítios do startup (§6.5). Os 42 de biblioteca durante a interação só entram se o conjunto de
  alvos incluir a fronteira app → biblioteca (§6.8).
- Fragments e Compose só entram com F1/F2 e C1 (§3.5, §4.5).
- Se o 7.5 mostrar que a distância satura como o booleano, o desenho não tem base.

### 6.8 O alvo de fronteira app → biblioteca, e os APKs sem chamador direto

**O que é "chamador direto"** [conferido]:
- É um método **do código do app** com `directlyReachesTarget = true`: ele invoca uma API JCA
  monitorada, por aresta do call graph ou pela varredura de bytecode das classes do app
  (`ReachabilityEngine.java:104-117`).
- O `reachability[]` do `.apk.json` só lista classes do app. Das classes de biblioteca onde houve
  violação no E6, nenhuma aparece nele (0/70, §6.1).
- Um APK "sem chamador direto" não é um APK sem JCA. Ele usa a JCA só por bibliotecas: OkHttp/okio,
  Tink, BouncyCastle, Netty… Nos 82 casos, `reachesTarget` é verdadeiro para alguma parte do código
  do app (82 de 82, mediana de 27 % dos métodos, §6.5), por caminhos que atravessam a biblioteca.

**Onde caem as violações do E6** (`doutorado-tese/.../20261005_e6_graduacao_marca/m13_library_sites.py`,
105 sítios primários, união dos braços) [conferido]:

| origem | fase | APK com chamador direto | sítios | APKs |
|---|---|---|---:|---:|
| app | interação | sim | 30 | 18 |
| app | startup | sim | 4 | 4 |
| biblioteca | interação | sim | 33 | 24 |
| biblioteca | interação | **não** | 9 | 8 |
| biblioteca | startup | sim | 23 | 8 |
| biblioteca | startup | **não** | 6 | 3 |

- Durante a interação, há **mais** sítios em biblioteca (42, em 32 APKs) do que no app (30, em 18).
- Por biblioteca, os 42 se dividem em `okio.ByteString` 18, `com.google` (Tink e outras) 11 e 13
  espalhados.
- Por estrato de UI: 18 sítios em 15 APKs só-View, 12 em 9 mistos e 12 em 8 só-Compose.
- Dos 82 APKs sem chamador direto, só 11 tiveram algum sítio primário no E6 (15 sítios), e só 8
  durante a interação (9 sítios).

**Por que o desenho da §6.7 não os alcança.** O alvo de lá é o chamador direto. Num sítio de
biblioteca, quem chama a JCA é um método da biblioteca, que não está no `reachability[]` e não é
chamador direto. A orientação para o chamador direto passa ao largo.

**Proposta: alvo de fronteira** [hipótese de desenho, não medida]:
- **A definição.** B = os métodos do app que invocam um método de biblioteca do qual a JCA é
  alcançável **dentro da biblioteca**. O conjunto de alvos passa a ser C ∪ B. Tudo o mais da §6.7
  (distância, K, aposentadoria) vale igual.
- **Como o GATOR calcula.** A BFS reversa já atravessa os corpos de biblioteca. O GATOR já tem o
  conjunto L = métodos de biblioteca em `reachesTargetSet`. B = métodos do app com aresta (ou invoke
  no bytecode) para L. Para o `.apk.json`, é um campo novo por método, `boundaryReachesTarget` ou
  equivalente, com a paridade INV-ANA-32.
- **O risco é a saturação, de novo.** `okio.ByteString` (18 dos 42 sítios) é usado pelo OkHttp em
  quase todo caminho de rede. Nesses apps, B pode conter muitos métodos e não discriminar nada.
  Antes de entrar no desenho, o 7.5 tem de medir o tamanho de B por APK e a sua seletividade.
- **A relação com o C0.** As exclusões corrigidas afetam `kotlin.*`, `kotlinx.*` e
  `androidx.compose.*` (e `androidx.*` no braço ii). okio, Tink e BouncyCastle continuam com corpo, e
  B continua calculável.

**Consequência para o escopo (§7.6).** Com o alvo de fronteira, os 82 APKs sem chamador direto ganham
alvo. O peso deles no desfecho do E6, porém, é pequeno: 9 sítios durante a interação, em 8 APKs.
Nos APKs que já têm chamador direto, B acrescenta 33 sítios de biblioteca durante a interação, em 24
APKs. É aí que o alvo de fronteira mais vale.

### 6.9 O canal de activity e lançador: quanto acerta, e fazer o lançamento chegar

O bind do canal de activity é exato: o nome da classe da activity é a mesma string no `.apk.json`,
no artefato e no `topActivity` de runtime. O `MopLauncherStage` abre, a cada `cadence` passos, a
próxima activity **ainda não visitada** do censo MOP, em rodízio
(`ape/.../agent/pipeline/MopLauncherStage.java:28-34, 138-161`). A pergunta é quanto esse canal acerta
e quanto rende, já que o E6 o apontou como o único mecanismo com efeito (§6.1).

**Medição no E6** [conferido; `doutorado-tese/.../20261005_e6_graduacao_marca/m17_launcher.py`,
`.out`, `m17_launches.csv`, sem o avare]. O alvo de cada lançamento está no registro do passo
(`dec.a = EVENT_TRIGGER_ACTIVITY@<activity>`). Como o passo do lançador não tem `out`, a chegada é a
activity do passo seguinte.

| | MOP | MOP+LLM |
|---|---:|---:|
| lançamentos disparados | 1.986 | 760 |
| aceitos pela plataforma (`dec.comp.r = 0`) | 76 % | 81 % |
| aceitos que chegam à activity pedida | **16,7 %** | **25,2 %** |
| alvos distintos alcançados ao menos uma vez | **61 %** de 416 | **57 %** de 273 |
| alvos distintos nunca alcançados | 163 (39 %) | 118 (43 %) |
| lançamentos sobre o total de passos | 0,65 % | 0,39 % |

- **O acerto por lançamento é baixo porque o mesmo alvo que falha é tentado de novo**, até 60 vezes
  numa tarefa. Isso é decisão registrada: o INV-CT-14 manda gravar o resultado do lançamento e não
  agir sobre ele (`ape/openspec/specs/component-triggering/spec.md:182`), para que a medição não
  mudasse o comportamento.
- **Onde os erros caem.** Na `MainActivity` (919 dos 1.646 lançamentos aceitos que não chegam) e em
  telas de login, senha ou conta (`LoginActivity`, `PassCodeActivity`, `ImportAccountActivity`…). A
  leitura provável é que a activity pedida precisa de extras do Intent ou de uma sessão, falha ou se
  encerra, e o app volta ao início [hipótese; a causa por alvo não foi medida].
- **O censo quase não seleciona.** O `mopActivitiesAugmented`, recalculado com o próprio `derive()`
  sobre os `.apk.json`, cobre na mediana 71 % das activities declaradas (quartis 50–100 %). Em 27 %
  dos APKs cobre todas. A mediana é de 5 activities declaradas, 3 no censo e 2 alvos distintos por
  tarefa.
- **O efeito é de novidade de activity, não de orientação.** Chamador direto novo na janela de 3
  passos:

  | | MOP | MOP+LLM |
  |---|---:|---:|
  | lançamento que chega a activity nova | 3,0 % | 4,3 % |
  | primeira visita orgânica a uma activity | 1,8 % | 1,6 % |
  | passo comum | 0,04 % | 0,08 % |
  | razão lançamento ÷ primeira visita orgânica (MH por APK) | 1,09 [0,35; 7,05] | 1,54 [0,38; 16,05] |

  Chegar a uma activity nova rende muito, por qualquer caminho. O lançador não rende mais que a
  chegada orgânica; ele só chega a activities que a exploração não alcançou. Isso corrige a leitura
  da §6.1, que comparava o lançamento com o passo comum.
- **Peso no resultado.** Os lançamentos respondem por 6,6 % (MOP) e 5,6 % (MOP+LLM) das primeiras
  execuções de chamador direto e por 4,3 % e 3,6 % das violações, na janela de 3 passos.
- **Limite estrutural.** A activity é um grão grosso onde a tela não é activity. A mediana de
  activities do próprio app é 2 nos estratos só-Compose e misto, contra 7 no só-View. Têm uma só
  activity do app 46 % dos APKs só-Compose e 27 % dos mistos (`ui_tech` congelado do estudo 03).

**Proposta: fazer o lançamento chegar** [proposta; não medida]. É a melhoria do canal que ataca os
39–43 % de alvos nunca alcançados, sem tocar no bind.

- **O que existe hoje.** O lançador dispara um Intent explícito para a activity, sem extras (INV-CT-04,
  `component-triggering/spec.md:171`). O artefato leva, por activity, só o `deepLinkUri` montado a
  partir dos intent filters (`derive_mop_artifact.py:1034-1162`). O GATOR não extrai extras: não há
  ocorrência de `getStringExtra`/`getExtras` nas fontes do `rvsec-gator`.
- **No produtor**, por activity:
  1. **os extras que ela lê**: `getIntent().getXxxExtra(chave[, padrão])` e
     `getIntent().getExtras().getXxx(chave)` em `onCreate`/`onStart`/`onResume` e nos métodos da própria
     classe chamados por eles, com a chave quando é constante (`const-string`) e o tipo pelo método
     chamado;
  2. **os valores que o app manda**: os sítios `putExtra(chave, valor)` sobre Intents cujo alvo é essa
     activity (`const-class` em `Intent(Context, Class)`, `setClass`, `setComponent`), com o valor
     quando é constante.

  A saída seria `components.activities[].extras[]` = `{key, type, values[]}`. Exige atualizar juntos
  `JsonSchema.Keys` e `_JK` (INV-ANA-32).
- **No consumidor**: o lançador preenche cada extra com um valor visto num sítio de envio; sem valor
  conhecido, com o padrão do tipo (`""`, `0`, `false`). Extras `Parcelable`/`Serializable` não se
  sintetizam: a activity fica marcada como "exige objeto". Isso não age sobre o resultado do
  lançamento, então não esbarra no INV-CT-14. Muda o artefato (`static-analysis-entrypoints`,
  `formatVersion`) e o `component-triggering` no `ape`.
- **O que não resolve.** Activities protegidas por sessão ou login continuam voltando ao início; extra
  nenhum substitui a sessão.
- **Experimento barato antes de qualquer change.** Sobre os 163 + 118 alvos nunca alcançados no E6
  (`m17_launches.csv`), uma varredura de bytecode (`dexdump`, como no `m15`) que conte quantos leem
  extras, de que tipo, e quantos têm sítio de envio com valor constante. Isso dá o teto de
  recuperação. Só então vale uma rodada curta pela plataforma.
- **O teto do ganho é pequeno em termos absolutos**: mediana de 2 alvos por tarefa, e o efeito de
  chegar é o de uma primeira visita. A melhoria vale pelo que acrescenta às activities que a
  exploração não alcança sozinha, não por tornar o canal seletivo. A seletividade continua sendo a
  da §6.5–6.7.

---

## 7. Experimentos que decidem, antes de qualquer change

### 7.1 Fragments: rendimento de F1+F2, offline

Rodar uma versão descartável do gator com F1 + F2(b) sobre os 65 apps com fragment (cópia em
`--gator-dir`, sem tocar o repositório). Medir:

1. widgets e listeners novos por app;
2. **widgets marcados novos** (direto e transitivo) e quantos apps entram no estrato "tem widget
   marcado", que era de 32;
3. colisões de `shortId` dentro do mesmo host com flags diferentes;
4. a fração dos novos widgets marcados que é só transitiva (saturação);
5. a taxa de colisão que a impressão digital por resource-ids (§6.2) resolve, usando os layouts
   estáticos de cada fragment contra o conjunto de ids das telas observadas no E6.

O degrau 2 (valor preditivo, §6) só se mede com execução: uma rodada curta do braço com orientação
nos apps que ganharem widgets marcados.

**Portão proposto**: se o estrato com widget marcado não crescer de forma material, F2 não se justifica
como change; F1 ainda pode valer pela atribuição. O limiar é decisão sua.

### 7.2 Compose e saturação: C0 (§4.5)

Independente da 7.1, e informa as duas: se a saturação cair, os widgets de fragment da 7.1 ganham
discriminação, e o D1 de agosto reabre.

### 7.3 Marca graduada sobre os dados do E6 (§6.4)

Custo zero de máquina: só leitura dos dados do E6 e dos `.apk.json`. Diz se há sinal escondido pela
saturação no estrato View que já tem bind. Se nem a marca rara tiver razão bem acima de ~1,07, ampliar o
bind (fragments, Compose) não muda o resultado do teste enquanto a marca não mudar.

### 7.4 Bind por classe de handler em Compose: E2 (§6.3)

Um APK Compose (`parceltracker`), um probe reflexivo injetado como no E1. Mede a fração de nós
clicáveis cuja classe de handler o probe recupera e a fração que casa com o `compose-probe`. Não
precisa de canal, porque o probe mede a si mesmo.

### 7.5 Distância ao alvo validada contra o E6 (§6.5) — o experimento que decide o desenho

**Pergunta**: a distância `minHops(handler, chamador direto)` aponta o handler certo?

**Verdade de campo, já medida**: no E6, o `m6_steps_methods` alinha os passos à primeira execução
de cada método direto (heartbeat). Para cada primeira execução de chamador direto durante a
interação, o handler clicado no passo anterior é o que levou até lá.

**Desenho**: um gator descartável (cópia em `--gator-dir`) que emite, por handler, a distância a cada
chamador direto, em três configurações:
- (a) a atual;
- (b) com as exclusões efetivas;
- (c) com (b) mais a aresta de lambda explícita.

Rodar nos 21 APKs com sítio de violação no app.

**Medida**:
- a posição do handler verdadeiro na ordem por distância, entre os handlers da mesma tela;
- a razão "chamador direto novo depois do clique" para handlers a ≤ k saltos contra os demais, nos
  moldes do 7,2 % × 6,7 % da §6.1.

**Portão**: se (b) ou (c) não puserem o handler verdadeiro no topo bem acima do acaso, a orientação por
alvo não tem base estática, e nenhum bind novo a salva.

### 7.6 Escopo da re-análise e da re-execução: só os APKs necessários

Tabela por APK em `doutorado-tese/.../20261005_e6_graduacao_marca/m12_rerun_sets.py` (+ `.csv`,
`.out`) [conferido]. O estrato de UI é o congelado do estudo 03 (`E6-campaign/config/strata.csv`,
`ui_tech`). Fragment é pelo nome (classe `*Fragment` no `reachability`), um proxy.

| conjunto | APKs | só View | misto | só Compose | engine | com fragment | com Compose |
|---|---:|---:|---:|---:|---:|---:|---:|
| corpus | 163 | 73 | 37 | 50 | 3 | 69 | 87 |
| com chamador direto | **81** | 46 | 14 | 20 | 1 | 44 | 34 |
| com chamador direto e widget com handler | 52 | 41 | 11 | **0** | 0 | 35 | 11 |
| com sítio de violação no app (E6) | 21 | 14 | 5 | 2 | 0 | 13 | 7 |
| com sítio no app durante a interação (móvel) | **18** | 13 | 4 | 1 | 0 | 12 | 5 |
| com chamador direto executado por algum braço do E6 | 52 | 30 | 10 | 12 | 0 | 30 | 22 |
| com chamador direto nunca executado no E6 | 29 | 16 | 4 | 8 | 1 | 14 | 12 |

**Leitura**:

- **Os 82 sem chamador direto não ficam de fora por definição; ficam sem alvo no desenho atual.**
  "Sem chamador direto" quer dizer que nenhum método do código do app chama a JCA diretamente. A
  JCA, quando existe, é usada só por bibliotecas. Com alvo = chamador direto, esses APKs não têm o
  que mirar. Com o alvo de fronteira da §6.8, ganham alvo. No E6, porém, só 11 dos 82 tiveram algum
  sítio primário (15 sítios), e só 8 durante a interação (9 sítios). O peso deles no desfecho é
  pequeno (`m13_library_sites.out`).
- **Compose entra, e o canal decide o quanto.** São 34 APKs com Compose e chamador direto.
  - Nos 20 só-Compose não há nenhum widget com handler (0 de 20). Hoje eles só podem receber
    orientação pelo canal de activity e pelo lançador. Mesmo isso precisa saber qual activity hospeda
    cada composable que leva ao alvo: a raiz `setContent`, que o `compose-probe` já acha em 74 de 80
    (§4.3) e que o C1 levaria ao produtor.
  - O canal de widget em Compose precisa do C1, do bind por classe de handler (E2, §6.3) e da
    decisão sobre o INV-RUN-06.
- **Fragments: 44 dos 81.** O F1/F2 (§3.5) é o que lhes dá widgets.
- **Os 29 em que nenhum braço executou chamador direto** (28 deles também nunca no E2, §6.5) custam
  36 % do tempo de campanha. Como nenhuma ferramenta os executou em 99 execuções por APK, a
  orientação por UI dificilmente os move. Mantê-los ou não é decisão sua; a proposta é mantê-los na
  re-análise estática, que é barata, e tirá-los da campanha se o tempo apertar.

**Proposta** (revista depois da §6.8):

1. **Re-análise estática (GATOR com as correções)**: o corpus inteiro, 163 APKs. Com o alvo de
   fronteira, todo APK com `reachesTarget` ganha alvo; isso inclui os 82 sem chamador direto. Se o
   tempo exigir corte, os 81 com chamador direto mais os 11 sem chamador direto que tiveram sítio
   primário no E6.
   **Adiada por decisão do Pedro em 05/10**: a análise estática não roda agora. Este documento
   registra o que rodar quando ela for autorizada.
2. **Re-execução**: os **52** com chamador direto já executado no E6, mais os **8** sem chamador
   direto com sítio de biblioteca durante a interação (60 APKs). Se houver tempo, os 81 mais esses 8.
   O desfecho primário a decidir (§9, decisão 6) seria lido nos sítios durante a interação (30 no
   app, 42 em biblioteca) e na execução dos alvos (C ∪ B).
3. **Custo pelo medido no E6**: cerca de 0,54 h de container por tarefa. Isso dá, por braço, ~4 h de
   relógio com 60 APKs e ~6 h com 89, em 8 containers, com R = 1. Multiplica-se pelo número de
   braços e de repetições, que são do protocolo. É uma estimativa por proporção; precisa ser
   conferida no `tasks.json` do primeiro container antes de virar prazo.

---

## 8. Ordem recomendada

1. ~~**7.3, marca graduada sobre o E6**~~ — feita em 05/10 (§6.4, §6.6). Depois dela, também feitos
   sem máquina: a análise do "já exercitado" (§6.6), o desenho para vários caminhos (§6.7), o escopo
   (§7.6) e o alvo de fronteira (§6.8).
2. **C0** (horas de máquina livre, nada permanente). Decide se a saturação é artefato da configuração.
3. **7.5, distância ao alvo contra o E6.** É o experimento que decide se a orientação dirigida por
   alvo (§6.5) tem base. Reaproveita a cópia do gator do C0. Deve medir também o tamanho e a
   seletividade do alvo de fronteira B (§6.8).
4. **Experimento 7.1** (fragments, descartável), já medindo a distância ao alvo dos handlers novos.
5. Se 7.5 e 7.1 passarem: **change no rv-android/gator** para F1 + F2, mais a correção das exclusões se C0 a
   justificar. A correção das exclusões muda a medição do `jca` congelado e do estudo 03; por isso
   entra como decisão explícita sua, e só para campanhas futuras.
6. **Compose entra no escopo** (decisão do Pedro, 05/10). O canal de activity e lançador precisa só
   do C1 (raiz `setContent` → activity hospedeira, distância por composable). O canal de widget
   precisa do E2 (7.4) e de uma decisão sobre o INV-RUN-06. A qualidade da distância em composables
   depende do C0 (saturação).
7. F3/F4 e o sinal de fragment em runtime (`dumpsys activity top`) ficam para quando houver pergunta
   que os peça.

---

## 9. Decisões que são suas

1. ~~Faço a **7.3**?~~ Feita em 05/10 (§6.4): a marca só carrega sinal quando é rara na tela.
   Ponderar o reforço pelo número de alvos marcados entra como candidata a mudança no consumidor?
2. Autoriza o **C0** (cópia do gator, patch das três constantes, 4 APKs, máquina livre)?
3. Autoriza o **experimento 7.1** (gator descartável com F1 + F2(b) nos 65 apps com fragment)?
4. Autoriza o **E2** (probe de classe de handler em um APK Compose, emulador gerido pela plataforma)?
5. Autoriza o **7.5** (distância ao alvo, gator descartável nos 21 APKs com sítio no app, validado
   contra o alinhamento passo × método do E6)?
6. Para a próxima campanha: o desfecho primário passa a ser a execução dos chamadores diretos e as
   violações de origem no app durante a interação (o que a orientação pode mover), com o total como
   secundário? É mudança no que se mede.
7. Se 7.1 e C0 passarem: abro **issue + change OpenSpec** no rv-android (`gh<N>-gator-fragments`) pelas
   skills? Ela revoga na prática a regra de julho "não mexer no gator salvo erro grosseiro", que
   valia para o prazo do E3.
8. A **correção das exclusões**: corrigir (e re-analisar o corpus para os próximos estudos) ou manter
   e documentar? Recomendo decidir só depois do C0.
9. O atalho MOP passa a **ordenar** os candidatos por inédito na activity antes da marca, mantendo o
   limite de 3 (§6.6)? É mudança no comportamento do braço com MOP.
10. O desenho da §6.7: agregação pelo mais próximo não aposentado, K = 3, Dmax = 6, aposentadoria
    por contador com N = 3, e a emenda do INV-DRV-06 para admitir o vetor de distâncias no artefato do
    dispositivo. Os parâmetros ficam provisórios até o 7.5.
11. Escopo (§7.6, revisto): re-análise estática no corpus inteiro (ou 81 + 11) quando for
    autorizada; re-execução nos 52 com chamador direto já executado mais os 8 com sítio de biblioteca
    durante a interação?
12. O conjunto de alvos passa a ser chamadores diretos ∪ fronteira app → biblioteca (§6.8)? Depende
    de o 7.5 mostrar que a fronteira não satura (okio/OkHttp é o caso de risco).

---

## 10. Método e proveniência

- **Leitura direta [conferido]**:
  - gator: `Main.java:224-234, 262-268`; `AnalysisEntrypoint.java:136-147`; `Hierarchy.java:360-367`;
    `gui/FixpointSolver.java:758-773`; `gui/wtg/algo/ExplicitForwardEdgeBuilder.java:320-334`;
    `xml/AndroidView.java:102,148`; `xml/PrerunXMLParser.java:53`;
    `client/.../RvsecAnalysisClient.java:955-1000, 1055-1095`; `client/pom.xml:46-57`;
    `lib/gator/libPackages.txt:98,110,1425`;
  - `derive_mop_artifact.py:367-375, 730-800`; `ape/.../MopData.java:690-694`;
  - FlowDroid 2.10.0 (`soot-infoflow-android-2.10.0-sources.jar`,
    `AbstractCallbackAnalyzer.java:484-559`; `javap` em `FragmentEntryPointCreator` e
    `AndroidEntryPointConstants`);
  - a série de seis documentos de julho/agosto; `20260828_cadeia_medicao_rvandroid.md` §4.2;
    `20260828_d9_colapso_denominador.md` §4.2; `doutorado-tese/.../20261003_compose-static-analysis.md`;
    proposta da change `rvsec-study03-artigo/openspec/changes/e3-data-compose-static`.
- **Medições minhas [conferido]**:
  - `docs/handoff/20261005_gator_fragments_compose/frag_coverage.py` (+ `.out`): listeners e alcance de
    fragments por app;
  - agregação do `apps.csv` do `compose-probe` (comando inline, `run 20261003T163209Z`);
  - inspeção de `com.gelakinetic.mtgfam_99.apk.json`.
  - `dexdump` (build-tools 37.0.0) dos DEX de `rvsec-dataset/head_apks/dev.itsvic.parceltracker_10501000.apk`:
    `AbstractClickableNode$applySemantics$1` (campo `this$0`) e `AbstractClickableNode` (campo
    `onClick: Function0`, `getOnClick()`), §6.3;
  - resultados do E6 lidos em `doutorado-tese/docs/estudo-03/analise/scripts/20261003_e6_dose_orientacao/`
    (`README.md`, `m4_power/a_signals.out`, `a_extra.out`), §6.1.
- **Medições de 05/10, segunda parte [conferido]**, em
  `doutorado-tese/docs/estudo-03/analise/scripts/20261005_e6_graduacao_marca/` (README na pasta):
  - `m6_extract.py`, `m6_productive.py`, `m8_*.py`: cópias do m6/m8 do E6, com `mopx`, `dec.ch` e o
    `[, UNVISITED]` por passo; reproduzem o original exceto no avare (excluído, incidente de 05/10);
  - `m9_graduation.py`, `m9_robust.py`, `m9_novelty.py`: a graduação da marca (§6.4);
  - `m10_novelty_grain.py`, `m10_analyze.py`: novidade por activity × por estado (§6.6);
  - `m11_payload.py`: tamanho do vetor de distâncias no artefato (§6.7);
  - `m12_rerun_sets.py`: conjuntos de APKs para a re-execução (§7.6);
  - `m13_library_sites.py`: sítios por origem × fase × chamador direto (§6.8);
  - `m17_launcher.py` (+ `.out`, `m17_launches.csv`): disparo, aceitação e chegada do lançador, e o
    rendimento contra a primeira visita orgânica (§6.9).
- **Relatórios de subagentes [relato]**:
  - estratos do corpus (§2.3; os scripts `measure_ui_strata.py`/`aggregate.py` e o
    `per_apk_ui_strata.tsv` ficaram no scratchpad da sessão, que foi apagado; a tabela precisa ser
    regenerada antes de ser citada);
  - código do gator (Fragment e Compose, contrato JSON, pontos de extensão);
  - consumidor APE-RV (campos lidos, decisões, chave de join, ausência de conceito de fragment,
    nada de Compose implementado depois de 01/08);
  - resultados do estudo 03 por estrato;
  - literatura (§5).

# Jetpack Compose e o substrato estático: por que a WTG está vazia em metade do corpus

**Data**: 2026-07-30
**Escopo**: relação entre Jetpack Compose e o analisador estático `rvsec/rvsec-android/rvsec-gator`; efeito no substrato consumido pelo APE-RV; consequências para o desenho do E3.
**Status**: análise — nenhuma decisão de implementação tomada aqui. Complementa `20260729_propostas_melhorias_e3.md` §8 (achados F6/F7, itens B9/N7) e obedece à regra vigente de não modificar o gator salvo erro grosseiro.

---

## 1. O que este documento estabelece

Três afirmações, todas medidas sobre os 181 `.apk.json` do experimento em 2026-07-30 (método reproduzível na §7):

1. **A camada GUI/WTG do analisador colapsa em apps Compose.** Metade dos apps Compose entrega uma WTG com janelas e *nenhum widget dentro*: mediana de 0 widgets, 74,3% com zero listeners, 89,5% com zero aresta cross-window. Esse estrato é a origem do achado F6 ("B9 sem substrato"): dos 74,0% de apps sem aresta cross-window no corpus inteiro, a concentração está em Compose.
2. **A camada de reachability *não* colapsa** — funções `@Composable` do próprio app são analisadas normalmente e alcançam alvos JCA em 97 de 103 apps. Mas o sinal é quase constante (96,1% de `reachesTarget=true` contra 28,8% do código não-composable), o que sugere super-aproximação e reduz seu poder discriminativo.
3. **Isso tem consequência direta para a corrida decisiva do E3**, não apenas para o B9 adiado: em 30% dos apps Compose *todas* as activities estão marcadas como MOP, então o `activity_has_mop` do item A4 é constante 1 nesse subconjunto e o braço guiado por MOP não tem contraste para exibir ali.

O ponto conceitual que atravessa as três: **isto não é um defeito do GATOR.** O GATOR lê layout XML, objetos `View` e transições por `Intent`. Compose eliminou os três deliberadamente. É incompatibilidade de categoria, e é por isso que "consertar o GATOR para Compose" significa construir uma análise diferente, não corrigir a existente.

---

## 2. O que é Jetpack Compose

Toolkit declarativo de UI da Google para Android, estável desde 2021, exclusivamente Kotlin. É o padrão para aplicativo novo — daí 103 dos 181 apps do corpus terem Compose compilado dentro.

A diferença relevante aqui não é de estilo de programação. É que **cada artefato que o analisador estático consome desapareceu**.

### Como era, no sistema de Views

```xml
<!-- res/layout/activity_main.xml -->
<Button android:id="@+id/btn_encrypt" android:text="Encrypt"/>
```

```kotlin
setContentView(R.layout.activity_main)
findViewById<Button>(R.id.btn_encrypt).setOnClickListener { doCrypto() }
startActivity(Intent(this, ResultActivity::class.java))
```

Existem quatro coisas que uma análise estática consegue agarrar: um **arquivo XML** declarando a árvore de UI antes de qualquer execução; um **objeto `Button`** com resource-id estável `btn_encrypt`; uma **chamada `setOnClickListener`** registrando um handler identificável; e uma **transição entre Activities** via `Intent` com a classe de destino literal no bytecode.

### Como é, em Compose

```kotlin
@Composable
fun MainScreen(onDone: () -> Unit) {
    Button(onClick = { doCrypto(); onDone() }) { Text("Encrypt") }
}

// na única Activity do app:
setContent {
    NavHost(nav, startDestination = "main") {
        composable("main")   { MainScreen(onDone = { nav.navigate("result") }) }
        composable("result") { ResultScreen() }
    }
}
```

Os quatro pontos de apoio somem:

- **Sem XML.** Não existe `res/layout`. A árvore de UI é o *resultado de executar* funções `@Composable` em tempo de execução — não há descrição declarativa a ser lida antes.
- **Sem objetos `View`.** A UI inteira do app vive dentro de **um único** `AndroidComposeView` na hierarquia Android. Os elementos são `LayoutNode`s da árvore interna do Compose, cuja identidade vem de *positional memoization* (a posição do call-site no código compilado, mais blocos `key()` explícitos), não de resource-id.
- **Sem listeners.** `onClick = { ... }` é um **lambda passado como parâmetro**, compilado como implementação de `Function0`. Não há chamada a `setOnClickListener` e não há classe implementando `View.OnClickListener` para o analisador encontrar.
- **Sem transição de Activity.** A arquitetura dominante é *single-activity*: navegar é `nav.navigate("result")` — uma string de rota resolvida em runtime — ou, com frequência, apenas *state hoisting* (`var tela by remember { mutableStateOf(...) }` com um `when` escolhendo o que compor). **Não existe janela para transicionar.** É a explicação direta dos 89,5% de apps Compose sem aresta cross-window: não é que a análise perdeu as arestas; é que as arestas não existem no sentido que a WTG modela.

Há ainda um agravante de forma. O plugin do compilador Compose reescreve cada função `@Composable`: acrescenta os parâmetros `$composer: Composer` e `$changed: Int` e embrulha o corpo em `startRestartGroup`/`endRestartGroup`, além da lógica de *skipping*. O bytecode não se parece com o fonte — o que, por outro lado, dá um detector barato e confiável de composable (§7).

### O que sobra: a árvore de semantics

Compose expõe, para acessibilidade e teste, uma árvore de `SemanticsNode` (via `Modifier.semantics`, `testTag`, `contentDescription`) que é mapeada para a árvore de nós de acessibilidade do Android. **É por isso que UIAutomator, e portanto o APE, continuam funcionando nesses apps apesar da WTG vazia** — o substrato de *runtime* existe; o de *análise estática* é que não.

Um detalhe dessa camada importa para o item N1: o `testTag` do Compose só aparece como resource-id na árvore de acessibilidade se o app ligar `testTagsAsResourceId`, que é **opt-in e raramente ligado**. Ou seja, em app Compose o resource-id tende a vir vazio e texto/content-description são frequentemente o *único* identificador disponível — exatamente o caso que o N1 conserta no prompt. O N1 vale mais nesse estrato do que a média do corpus sugere.

---

## 3. Onde exatamente a análise para

Dois sítios explicam o colapso, ambos verificados no worktree.

### 3.1 Compose está na lista de exclusão do Soot

`rvsec/rvsec-android/rvsec-gator/sootandroid/src/main/java/presto/android/Main.java:224-227`:

```java
"-no-bodies-for-excluded",
"-exclude", "kotlin.",
"-exclude", "kotlinx.",
"-exclude", "androidx.compose.",
```

É uma decisão deliberada de escalabilidade — o runtime do Compose é enorme e carregar seus corpos inflaria o call graph. O efeito colateral é que `setContent { }` (que é `androidx.compose.ui.platform.ComposeView`) passa a ser chamada para método *phantom*: a análise de fluxo entra num buraco e não volta. Nada popula o flowgraph de GUI.

Importante para não superinterpretar: a exclusão é do **framework**, não do app. As funções `@Composable` escritas no próprio app estão em `-process-dir` e *são* analisadas — o que a §4.3 confirma empiricamente.

### 3.2 Widgets e listeners nascem de estruturas que Compose não produz

`rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/RvsecAnalysisClient.java:902-949`: um widget só é emitido a partir de um `NObjectNode` do flowgraph — nó que veio do parser de XML (`presto.android.xml.DefaultXMLParser`) e do fluxo de `setContentView`/`findViewById`/`inflate`. E os listeners (`:936-947`) vêm de `output.getAllEventsAndTheirHandlers(objNode)`, o modelo de eventos do GATOR, ancorado em registro de listener no estilo `setOnClickListener`.

Em app Compose os dois conjuntos são vazios **por construção**: não há `NObjectNode` de UI para enumerar, e não há registro de listener para casar. A consequência em cascata é que o array `listeners[]` de cada widget — que é justamente o gancho onde os itens N6/F1 querem escrever `handlerReachesTarget`/`handlerDirectlyReachesTarget` — não tem onde existir nesses apps. **O N6 melhora o eixo direto/transitivo no estrato View; no estrato Compose não há widget para enriquecer.**

---

## 4. Medições no corpus do experimento

Corpus: os 181 `.apk.json` de `APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706_selected181/`. Dois detectores foram usados; a diferença entre eles é de 2 apps e não altera nenhuma conclusão. Cada tabela declara qual usou.

- **Detector A** (grosseiro): a string `androidx.compose` aparece em qualquer lugar do JSON → 105 apps.
- **Detector B** (preciso): `androidx.compose.runtime.Composer` aparece em *assinatura de método*, isto é, o app tem funções `@Composable` compiladas → 103 apps.

### 4.1 A camada GUI/WTG colapsa (detector A)

| | Compose (n=105) | Sem Compose (n=76) |
|---|---|---|
| mediana de janelas | 5 | 13 |
| mediana de widgets na WTG | **0** | 163 |
| apps com **zero** widgets | **55,2%** (58) | 2,6% (2) |
| apps com **zero** listeners | **74,3%** (78) | 14,5% (11) |
| apps com **zero** aresta cross-window | **89,5%** (94) | 52,6% (40) |

No corpus inteiro: **134/181 = 74,0%** com zero aresta cross-window, reproduzindo exatamente o F6 de `20260729_propostas_melhorias_e3.md` §8. A estratificação mostra que o número agregado esconde dois regimes distintos, e que o regime dominante é "Compose, sem substrato nenhum".

Nota sobre a natureza das arestas que existem: a maior parte das `transitions` é auto-laço. O primeiro registro de um JSON típico é
`{"sourceId": 1508, "targetId": 1508, "events": [{"type": "implicit_on_activity_newintent", ...}]}` — uma janela apontando para si mesma via `onNewIntent`. Contar `transitions` sem filtrar `sourceId != targetId` superestima grosseiramente a conectividade; foi o que exigiu a correção do número nesta análise.

### 4.2 Nível de activity: o sinal MOP perde poder discriminativo (detector B)

| | Compose (n=103) | Sem Compose (n=78) |
|---|---|---|
| mediana de activities | 5 | 7 |
| mediana da fração de activities com `reachesTarget` | **0,70** | 0,44 |
| apps com **100%** das activities marcadas | **30%** (31) | 9% (7) |
| apps com **0%** das activities marcadas | 6% (6) | 31% (24) |

Um sinal que vale para 100% das telas não distingue tela nenhuma. Em quase um terço dos apps Compose, "esta tela tem MOP" é tautologia.

### 4.3 A camada de reachability não colapsa, mas super-aproxima (detector B, 103 apps)

| | métodos | `reachesTarget` | `directlyReachesTarget` |
|---|---|---|---|
| `@Composable` (param `Composer`) | 80.673 (9,11%) | **96,1%** | **0,00%** |
| demais métodos | 804.633 | 28,8% | 0,02% |

E **97 de 103** apps Compose têm ao menos uma função `@Composable` com `reachesTarget=true`.

Duas leituras, ambas necessárias:

- **A boa notícia**: as funções `@Composable` do app estão no call graph e alcançam os alvos JCA. A cobertura de reachability não tem um buraco Compose-específico; o buraco é só na camada GUI.
- **A ressalva**: 96,1% contra 28,8% é diferença grande demais para ser real. A alcançabilidade transitiva satura, e o `reachesTarget` de código de UI Compose é aproximadamente a constante `true` — carrega pouca informação. **A causa está corrigida na §4.3.1**: não é CHA, é `all-reachable:true` sobre SPARK.
- E `directlyReachesTarget` é **0,00%** entre composables, o que é semanticamente correto e esperado: criptografia não mora em código de UI, mora em ViewModel/repository. Isso é consistente com o achado F1 (alcance direto 0-hop é raro em qualquer estrato) e reforça que o eixo "direto" precisa da redefinição do N6 para significar algo.

#### 4.3.1 Correção de 2026-08-06: não é CHA, é `all-reachable` — e não é o `-exclude`

A ressalva acima atribuía a super-aproximação a "CHA + `all-reachable:true`". **A metade "CHA" está errada.** O algoritmo efetivo é **SPARK**:

```java
// Configs.java:74
public static String cgAlgorithm = "spark"; // cha, rta, vta, spark — default per gh51 D5
```

e o `rv-static-analysis` fixa `cg_algorithm="spark"` por padrão (`config.py:104-109`), com a justificativa explícita *"full points-to gives accurate reachesTarget"*. O `"cha"` de `Main.java:73` só entra sob a flag `-withCHA`, que o pipeline não passa. O corpus inteiro foi analisado com SPARK. (O javadoc do `ReachabilityEngine` já dizia "SPARK call graph" — era este documento que estava desatualizado, não o código.)

**SPARK é inegociável** e não está em discussão: é a decisão D5 do gh51, e trocá-lo por um algoritmo mais barato pioraria a precisão em vez de melhorá-la.

O termo que sobra é o outro, aplicado incondicionalmente:

```java
// Main.java:234
args.addAll(Arrays.asList("-p", "cg", "all-reachable:true"));
```

**O mecanismo, e por que ele atinge Compose com força desproporcional.** `all-reachable` faz todo método do app virar entry point — necessário no Android, onde não existe um `main()` e os callbacks são invocados pelo framework. O efeito colateral é que **parâmetros de entry point ficam sem restrição de points-to**: são modelados como objetos arbitrários do tipo declarado. Uma chamada virtual sobre um parâmetro passa então a leque para todos os subtipos, e SPARK degrada para perto de CHA exatamente nesse ponto. Composables recebem lambdas como parâmetro (`Function2`), e `invoke()` sobre elas alcança toda implementação de `Function2` do app. Código não-composable passa muito menos por invocação de lambda parametrizada — daí 96,1% contra 28,8%.

**E não adianta mexer no `-exclude`.** `androidx.compose.`, `kotlin.` e `kotlinx.` já estão excluídos com `-no-bodies-for-excluded` (`Main.java:224-227`), o que já converte essas classes em *phantom* e corta qualquer aresta **através** delas. A saturação acontece apesar disso, porque os caminhos que saturam são internos ao app — `composable → lambda do app → ViewModel → repository → JCA` —, e esses não há como excluir sem excluir o objeto da análise.

**Status**: mecanismo inferido da leitura do código, e **continua não medido** depois do experimento de 2026-08-07. O experimento rodou, mas o contrafactual que ele constrói é degenerado: desligar `all-reachable` sozinho não produz "alcance real", produz *ausência de alcance*, porque no Android não há `main()` e o gator não alimenta nenhum entry point substituto. Os dois estratos vão a zero juntos, então a previsão diferencial desta seção — cair muito em Compose e pouco em View — não chega a ser testada. O relato completo está na §6.5.1. A hipótese permanece de pé como explicação plausível e **não confirmada**; nada abaixo nesta seção depende dela, porque a consequência prática (`reachesTarget` booleano não discrimina em Compose) é medida direta da §4.3, não inferência sobre a causa.

---

## 5. Consequências

### 5.1 Para B9/N7 (pathfinding na WTG)

O B9 já estava rebaixado por falta de substrato; esta análise identifica **por que** o substrato falta e mostra que o N7, como formulado, não resolve o caso Compose. O N7 varre bytecode em busca de `startActivity`/`Intent(this, X.class)` para inferir arestas componente→componente. Em app single-activity + `NavHost` **não há `startActivity` para encontrar** — a navegação é uma string de rota resolvida em runtime dentro da mesma Activity. O N7 recupera arestas no estrato View e no estrato híbrido; no estrato Compose puro ele acha pouco ou nada.

Isso não invalida o N7 — reduz seu alcance esperado e desfaz a expectativa de que ele seria "o caminho para dar substrato a B9 em Compose", registrada no F7(ii). O caminho para Compose seria o grafo de rotas (§6.2), que é análise diferente.

### 5.2 Para a corrida decisiva (A4 e a leitura do resultado)

Esta é a consequência de prazo curto, e é a razão de este documento existir agora e não depois da Fase 2.

O item A4 serializa `activity_has_mop` em cada `[APE-STEP]` para permitir atribuir causalmente a cadeia decisão → ação → tela-MOP → violação. Em 30% dos apps Compose esse campo será constante 1. Nesses apps, um Δ nulo entre braço guiado e braço MOP-off **não é evidência contra a hipótese central** — é ausência de contraste no instrumento. Ler esses apps junto com os demais dilui o efeito medido na direção do nulo.

Recomendação concreta: **pré-registrar o estrato de toolkit de UI como eixo de estratificação da análise da corrida decisiva**, com o detector B (barato, determinístico, roda offline sobre os JSONs que já existem), e reportar o Δ pareado por estrato além do agregado. Isso não muda nada do que está implementado nem das changes já criadas; é regra de análise.

### 5.3 Para o teto de 82,4% e a RQ-C4

O teto "82,4% das telas-MOP alcançáveis", usado como denominador candidato de C4, foi calculado com navegabilidade definida como *presença na WTG*. Num app single-activity Compose esse denominador é vazio de significado: há uma janela, ela é a main, e ela está sempre marcada. Qualquer texto da tese que cite esse teto precisa (a) recomputá-lo com navegabilidade por caminho e (b) reportá-lo por estrato. Já registrado como ameaça à validade documental no F3/F6; esta análise acrescenta o motivo estrutural.

### 5.4 Para o N1 e para o N6

- **N1 ganha peso**: em Compose, o resource-id da árvore de acessibilidade tende a vir vazio (`testTagsAsResourceId` é opt-in), então texto e content-description são frequentemente o único identificador. O fallback que o N1 introduz é mais valioso nesse estrato do que a média sugere.
- **N6 tem alcance limitado ao estrato View**: sem `listeners[]`, não há onde escrever `handlerReachesTarget`/`handlerDirectlyReachesTarget`. O N6 continua correto e vale a pena — mas seu efeito esperado deve ser contado sobre os apps que têm widgets, não sobre os 181.

---

## 6. Caminhos de correção

Quatro opções, com custo e ressalva honestos. Nenhuma cabe na janela até sexta; a §7 diz o que fazer agora.

### 6.1 Estratificar e reenquadrar o denominador — custo ~zero, offline

Não toca o gator nem o ape. Usa o detector B sobre os JSONs existentes para separar Compose/híbrido/View, e reformula os denominadores de C4 por estrato: no estrato Compose a unidade de análise não é "tela", é composable/método. Tratamento de ameaça à validade, necessário independentemente de qualquer decisão sobre B9.

**Veredito: fazer, como regra de análise pré-registrada.**

### 6.2 Grafo de rotas do Navigation-Compose — o único trabalho de gator que faria sentido

O análogo correto da WTG em Compose: nós = strings de rota, arestas = chamadas `navigate("x")` alcançáveis do corpo do composable registrado para a rota `y`. É tratável porque as rotas são **constantes de string no constant pool**, e "qual corpo de composable contém qual `navigate`" é pergunta de call graph que o Soot já responde. Reusaria o mesmo gancho que o N7 usaria (`RvsecAnalysisClient.java:513-558`, `scanInvokesInAppClasses`).

Três ressalvas que precisam estar na mesa antes de qualquer estimativa:
- Navigation-Compose 2.8+ oferece rotas **type-safe** (objetos `@Serializable` em lugar de strings) — nesses apps a varredura muda de constante de string para referência de classe.
- Muitos apps Compose **não usam Navigation-Compose nenhum**: navegam por state hoisting com `when`. Nesses não há grafo extraível por análise de rotas, ponto.
- É passe novo no produtor, não patch — e portanto entra em conflito com a regra do gator e com o custo de re-analisar o corpus.

**Veredito: só com justificativa de Fase 2 mostrando que alcance de telas é o gargalo dominante.**

### 6.3 Call graph de composables de verdade

Identificar composables pelo parâmetro `$composer` (o detector B já faz isso), montar o grafo de chamadas entre eles e definir "tela" como composable que é destino de `NavHost` ou corpo de `setContent`. É o conserto principiado — modela Compose nos termos do Compose, em vez de tentar mapeá-lo para janelas. É também projeto de pesquisa próprio, e provavelmente exige rever a lista de exclusão da §3.1, com o custo de escala que ela existe para evitar.

**Veredito: fora do escopo desta tese.**

### 6.4 Trocar substrato estático por observado — o substituto real do B9

Como a §2 estabelece, a árvore de semantics existe em runtime e é justamente o que faz o APE funcionar nesses apps. Para pathfinding rumo a telas não visitadas, **o grafo de estados que o APE já constrói é substrato estritamente melhor que uma WTG vazia**. Isso reformula o B9 de "faça BFS na WTG estática" para "navegue no modelo que eu já tenho", com zero mudança no gator e sem re-análise do corpus.

Ressalva: muda o mecanismo do B9, e portanto o que a RQ-C4 avaliaria como tratamento. É decisão de desenho, não de engenharia.

**Veredito: candidato preferido se o B9 voltar à mesa.**

### 6.5 Experimento registrado: `all-reachable:false`, para medir a causa da §4.3.1

**Pergunta**: quanto dos 96,1% de `reachesTarget` entre composables é artefato de `all-reachable:true`, e não alcance real? A hipótese da §4.3.1 prevê que o número caia muito no estrato Compose e pouco no estrato View — porque o mecanismo suspeito (parâmetro de entry point sem restrição de points-to, leque sobre `Function2.invoke`) é desproporcionalmente comum em composables.

**Desenho**: um APK Compose e um APK View do corpus, analisados duas vezes cada — `all-reachable:true` (linha de base, reproduzindo o `.apk.json` vigente) e `false`. Comparar `reachesTarget` por método, particionado pelo detector B (parâmetro `$composer`), mais o tamanho do call graph e o tempo de análise.

**O obstáculo**: `all-reachable:true` está **hardcoded** em `Main.java:234`, dentro de um `List<String>` fechado por `args.toArray(new String[0])` em `:254` e entregue direto a `soot.Main.main` em `:289`. Não há flag de CLI nem passthrough de argumentos Soot — o parser de `Main` reconhece `-cgAlgorithm`, `-withCHA` e ~20 outras opções, e o `else` final não acumula desconhecidos. Não se alcança este ponto por CLI do gator, por config do `rv-static-analysis` nem por variável de ambiente. **Logo o experimento não é executável "sem tocar no gator"** no sentido de deixar o bytecode intacto, ao contrário do que se supôs ao levantá-lo.

**Mas o custo é muito menor do que essa frase sugere**, por dois fatos verificados em 2026-08-06:

- **Os jars do gator não são versionados.** `lib/gator/.gitignore` lista `/rvsec-gator.jar` e `/rvsec-analysis-client.jar`. O que o git rastreia ali são scripts, `listeners.xml`, `libPackages.txt` e os `consts/`. Não há risco de binário entrar em commit por acidente. *(Corrige uma afirmação da primeira redação desta seção, que dizia o contrário.)*
- **O diretório do gator é configurável.** O `rv-static-analysis` expõe `--gator-dir` e `--analysis-client-jar`, ambos `Optional` com resolução para `lib/gator` só por omissão (`config.py:92-96, 216-220`). Um braço experimental pode apontar para uma **cópia** do gator, sem que nada em nenhum dos dois repositórios seja alterado.

**Rota preferida — patch de constant pool, sem recompilar:**

1. `presto/android/Main.class` mora em `rvsec-gator.jar`, e `all-reachable:true` está lá como **uma única entrada UTF-8** do constant pool (verificado por extração da classe). Entradas UTF-8 de class file carregam prefixo de comprimento explícito, e class files não contêm offsets absolutos de byte — trocar 18 por 19 caracteres é seguro desde que o prefixo seja atualizado. Nenhuma recompilação, nenhum build Maven.
2. Copiar `lib/gator/` para um diretório descartável e substituir apenas o jar pela versão corrigida.
3. Rodar os dois braços com `--gator-dir` apontando para cada cópia.

**A verificação é gratuita e obrigatória**: `Main.java:278` itera sobre `sootArgs` e os imprime antes de invocar o Soot. O log do braço experimental **tem** de mostrar `all-reachable:false`; se não mostrar, o patch não pegou e o resultado é descartado. É o que torna o patch binário defensável — a intervenção é de um literal só, e o próprio programa a confirma em execução.

**Rotas alternativas**, se o patch falhar:

1. **Build local descartável**: alterar a linha, recompilar, rodar, restaurar o jar do backup. Toca a árvore do repositório irmão (revertível por `git checkout`) e sobrescreve um jar gitignored (revertível por cópia). Não é mudança de produto.
2. **Flag `-cgAllReachable <bool>`**: ~4 linhas no parser + 1 na montagem, com `true` como padrão. É mudança no gator de verdade, e portanto sujeita à regra vigente — mas é a menor mudança concebível, puramente aditiva, e tornaria a questão investigável para sempre em vez de uma vez.

**Prioridade**: baixa, e o motivo **não** é o custo — é que o resultado **não altera o plano**. Se a hipótese se confirmar, o conserto (desligar `all-reachable` e alimentar entry points de verdade) continua sendo mudança no gator mais re-análise dos 348 APKs; se for refutada, a saturação tem outra causa e a conclusão prática — `reachesTarget` booleano não discrimina em Compose — permanece igual. A mitigação já escolhida, a tabela graduada `FQN → {reaches, minHops}` do doc 5 §6, contorna o problema sem depender desta resposta.

#### 6.5.1 Resultado de 2026-08-07: o contrafactual é degenerado

O experimento rodou com a máquina livre, pela rota preferida. O patch de constant pool funcionou como previsto: 18 bytes por 19, prefixo de comprimento corrigido, `javap -v -c` idêntico ao original exceto pela constante `#483` e pelo comentário do `ldc_w` que a carrega. Os quatro braços imprimiram a linha `[SOOT-ARG]` esperada, então nenhum foi descartado.

**A linha de base reproduziu exatamente**, que era o portão de entrada: os dois braços BASE devolveram os mesmos números do `.apk.json` vigente *e* o mesmo grafo dos logs de proveniência de junho — 130.036 vértices e 711.893 arestas no APK Compose, 69.791 e 269.279 no View. Reprodução em tamanho de grafo, não só em percentual, é evidência forte de que o pipeline foi replicado fielmente.

| braço | APK | vértices → | arestas → | `reachesTarget` composables | demais métodos | tempo |
|---|---|---|---|---|---|---|
| BASE | parceltracker (Compose) | 130.036 | 711.893 | 142/142 (**100,0%**) | 806/3.797 (21,2%) | 395s |
| EXP | parceltracker (Compose) | **7** | **12** | 0/142 (**0,0%**) | 0/3.797 (0,0%) | 33s |
| BASE | retrowars (View) | 69.791 | 269.279 | — (0 composables) | 628/2.933 (21,4%) | 181s |
| EXP | retrowars (View) | **1.009** | **2.445** | — | 0/2.933 (0,0%) | 96s |

A enumeração de classes e métodos é idêntica entre os braços (625/3.939 e 514/2.933), assim como `windows` e `transitions`: o JSON continua íntegro e a camada GUI não depende da flag. O que colapsa é só o que deriva do call graph.

**Por que isso não responde à pergunta.** A previsão da §4.3.1 era diferencial — Compose cai muito, View cai pouco. O que se observa é que **os dois caem até o chão**, porque `all-reachable:false` não deixa entry point nenhum: no Android não existe `main()`, os callbacks são chamados pelo framework, e o gator não gera um `dummyMain` que os substitua. Sem raiz, o grafo se desfaz (130.036 vértices viram 7) e `reachesTarget` vira constante `false` em toda parte. Um contrafactual que zera o construto medido não separa "artefato de modelagem de entry point" de "nenhuma modelagem de entry point": ele só mostra que a flag é *load-bearing*, o que já se sabia.

**Portanto a hipótese não foi confirmada nem refutada — ela segue não testada.** Testá-la de verdade exige `all-reachable:false` **mais** um conjunto real de entry points (callbacks de ciclo de vida à la FlowDroid), que é a rota alternativa 2 acima: mudança de verdade no gator, sujeita à regra vigente e a autorização explícita. Não foi feita.

**Uma observação secundária, e fraca.** O braço Compose colapsou para 7 vértices enquanto o View reteve 1.009 — ou seja, sobra algum esqueleto enraizado em código convencional no app de Views e quase nada no app Compose. Isso é *compatível* com a leitura de que em Compose praticamente toda a estrutura pende do leque de entry points, mas com n=2 e sem controle sobre o que exatamente o Soot ainda enraíza (inicializadores estáticos, o caminho de `-cgDelegation`), não sustenta conclusão. Fica registrado como pista, não como achado.

**O que muda no plano: nada**, exatamente como o parágrafo de prioridade acima previa. A consequência prática — `reachesTarget` booleano não discrimina em Compose — vem da medição direta da §4.3 e independe da causa. A mitigação escolhida, a tabela graduada `FQN → {reaches, minHops}` do doc 5 §6, continua sendo a resposta certa.

**Três correções operacionais**, para quem repetir isto:

- **A entrada da análise é o APK original, não o instrumentado.** Os `.apk.json` moram junto dos APKs instrumentados, mas a proveniência (`rvsec-dataset-sa/logs/*.log`) mostra `-project .../rvsec-dataset/head_apks/<apk>`. Rodar sobre o instrumentado mudaria o call graph e derrubaria o portão da linha de base.
- **A verificação prometida acima não é gratuita pela rota descrita.** `Logger.trace` é no-op por padrão e só liga sob `-verbose` (`Main.java:66`), que o `rv-static-analysis` nunca passa — as linhas `[SOOT-ARG]` exigem invocar o launcher do gator direto com `-v`. Todos os usos de `Configs.verbose` são de log e não alteram a análise, então os dois braços podem carregá-lo sem prejuízo.
- **Copiar `lib/gator/` não basta**: `pygator/unpacker.py:6` resolve o apktool como `<gator>/../../apktool/apktool.jar`, isto é, um irmão do diretório copiado.

**Veredito: executado, inconclusivo por desenho.** A pergunta continua aberta e barata de fechar apenas se alguém já for mexer em entry points no gator por outro motivo. Sozinha, ela não justifica a mudança.

---

## 7. O que fazer agora

Uma coisa só, e é de análise: **adotar o detector B como eixo de estratificação pré-registrado** da corrida decisiva, e reportar o Δ pareado de `mop_unique` por estrato de toolkit além do agregado. Motivo: sem isso, os ~30% de apps Compose com `activity_has_mop` constante diluem o efeito medido na direção do nulo, e um resultado nulo agregado ficaria ambíguo entre "a guia MOP não funciona" e "o instrumento não tem contraste nesses apps".

O detector, reproduzível sobre os JSONs que já existem:

```python
# app tem funcoes @Composable compiladas <=> o parametro $composer aparece
# em assinatura de metodo do proprio app (o plugin do compilador Compose
# injeta androidx.compose.runtime.Composer em toda funcao @Composable)
import json

def is_compose(apk_json_path: str) -> bool:
    with open(apk_json_path, encoding="utf-8", errors="replace") as fh:
        d = json.load(fh)
    for cl in d.get("reachability") or []:
        for me in cl.get("methods") or []:
            if "androidx.compose.runtime.Composer" in (me.get("signature") or ""):
                return True
    return False
```

Nada aqui exige mudança no gator, no ape, ou nas changes já criadas.

---

## 8. Fontes

- Código verificado (worktree, 2026-07-30): `rvsec/rvsec-android/rvsec-gator/sootandroid/src/main/java/presto/android/Main.java:224-227`; `rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/RvsecAnalysisClient.java:513-558`, `:902-949`.
- Dados: 181 `.apk.json` em `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706_selected181/`, medidos em 2026-07-30.
- Documentos relacionados: `20260729_propostas_melhorias_e3.md` (§0 registro de decisões; §8 achados F1/F6/F7, itens N6/N7, B9), `20260729_contexto_pesquisa_e3.md` (cadeia da tese, RQs candidatas C0–C5).
- Consumidor do substrato no APE-RV: `MopData.java:516-517,531-533` (precedência das flags de handler), `MopData.java:975-977` (`activityHasMop`, O(1)).

# Fazer o GATOR tratar Compose: o que é extraível, o que está bloqueado e onde

**Data**: 2026-07-31
**Escopo**: viabilidade técnica de estender o `rvsec/rvsec-android/rvsec-gator` para produzir substrato de UI em apps Jetpack Compose, e o que o consumidor (APE-RV, `workspace-rv/ape`) precisaria para usá-lo.
**Status**: investigação — nenhuma decisão de implementação tomada. Sucede `20260730_compose_gator_substrato_estatico.md`, que estabeleceu *por que* a WTG colapsa; este documento responde *o que dá para fazer a respeito*.
**Ressalva de governança**: contraria a regra vigente de "não mexer no gator salvo erro grosseiro" (2026-07-29) e a change aberta do APE-RV (`telemetry-proof-llm-efficacy`) exclui explicitamente do escopo "anything in rvsec-gator". Nada aqui deve ser executado sem revogar essas duas decisões de forma deliberada — ver §8.

---

## 1. O que este documento estabelece

Quatro afirmações, todas medidas ou verificadas em código nesta sessão (método na §9):

1. **A guia MOP em nível de widget é literalmente inerte em Compose.** Nos 812 traces do `experimento-cal/iter0`, os 22 APKs Compose acumulam **85.902 linhas `[APE-RV] MOP boost` e 0 ações impulsionadas em 629.417 avaliadas — 0,00%**. No estrato View, 94.163 de 738.628 (12,75%) recebem boost. O tratamento central da tese não age em metade do corpus. Isto é mais forte do que o "sem substrato" do documento anterior: não é que o sinal seja fraco, é que o mecanismo nunca dispara.
2. **As âncoras estáticas para reconstruir esse substrato existem no bytecode do app e sobrevivem à exclusão do Soot.** A exclusão `-exclude androidx.compose.` remove os *corpos* do framework, não os *sítios de chamada* nas classes do app. Verifiquei em bytecode real que `setContent`, o registro de destinos de navegação, as chamadas `navigate(rota)` e as fábricas de elementos (`Button`, `Text`, `OutlinedTextField`, `clickable`) estão todas presentes e são casáveis por um bytecode scan — exatamente o que o helper `scanInvokesInAppClasses` já existente faz. **Não é preciso levantar a exclusão**, e portanto o custo de escala que ela evita não volta.
3. **Mas o bloqueio decisivo não está no produtor — está no consumidor.** Todo o join estático→runtime do APE-RV é por `resourceID`: `getWidget(activity, extractShortId(node.getResourceID()))`, em seis sítios de chamada. Widgets sem `idName` são **descartados na carga** por invariante explícita (INV-MOP-20), que ainda declara: *"Matching such widgets by class/text/bounds is out of scope."* Em Compose o nó de runtime não tem resource-id. **Um inventário Compose perfeito no JSON não mudaria uma única decisão do APE-RV enquanto essa via de join não existir.**
4. **E não existe chave de join alternativa em nível de widget.** A única candidata que sobrevive dos dois lados seria texto/content-description — mas **76,4% dos elementos acionáveis em Compose não têm nenhum dos dois** (139.317 elementos medidos), e na classe dominante (`View` genérica, 54% do estrato, onde mora o `Modifier.clickable`) a cobertura é de **2,5%**, contra 94,3% da mesma classe em apps View. O déficit é do lado de **runtime**, não do estático, e por isso nenhuma melhoria no gator o alcança (§5.1).
5. **A guia em nível de activity não está morta** — `activityHasMop` é alimentada pelas seções `reachability`/`components` (INV-MOP-27, fontes 2 e 3), que não colapsam em Compose. É o sinal quase-constante já diagnosticado em `20260730` §4.2/§4.3: existe, mas discrimina pouco.

O corolário de desenho, e o ponto principal deste documento: **"fazer o gator tratar Compose" não recupera a guia MOP em nível de widget** — o gargalo é a ausência de identificador na árvore de acessibilidade do Compose, que nenhuma análise estática pode suprir. O que permanece tecnicamente aberto é a guia em nível de **tela** (§6, P2′), e ela compete de igual para igual com o substrato observado em runtime, que custa zero no produtor.

---

## 2. O achado que reenquadra o problema

O documento de 2026-07-30 mediu o *substrato* (mediana de 0 widgets, 89,5% sem aresta cross-window). O que faltava era medir o *efeito no mecanismo*. O `MopWidgetPass` do APE-RV registra, a cada estado, quantas ações candidatas receberam boost MOP:

```java
// ape/src/main/java/com/android/commands/monkey/ape/agent/scoring/MopWidgetPass.java:62-65
"[APE-RV] MOP boost: state=%s#%s, boosted=%d/%d, maxBoost=%d, containment=%d"
```

onde o denominador conta ações válidas, resolvidas e que exigem alvo. Varrendo os 812 traces `aperv` do experimento de calibração (40 APKs, 2026-07-23):

| estrato | APKs | linhas `MOP boost` | linhas com `boosted=0` | ações impulsionadas / avaliadas |
|---|---:|---:|---:|---:|
| **Compose** | 22 | 85.902 | **85.902 (100%)** | **0 / 629.417 (0,00%)** |
| View | 18 | 80.836 | 72.890 (90,2%) | 94.163 / 738.628 (12,75%) |

No estrato View o efeito se concentra em 7 dos 18 apps (de 0,31% em `org.prauga.messages` a 76,61% em `org.liberty.android.freeotpplus`); os outros 11 também ficam em zero — ou seja, o problema de substrato não é *exclusivo* de Compose. Mas em Compose ele é **universal e sem exceção**: nenhum dos 22 apps registrou um único boost.

Isto tem duas consequências imediatas, independentes de qualquer decisão sobre o gator:

- **Para a leitura da corrida decisiva.** Um Δ nulo agregado entre braço guiado e braço MOP-off é parcialmente *estrutural*: nos apps Compose o braço guiado é, no nível de widget, byte-idêntico ao braço sem guia. Isso reforça — e agora quantifica — a recomendação de estratificação pré-registrada de `20260730` §5.2. Note que a guia de activity ainda difere entre braços (§1.4), então os braços não são inteiramente idênticos; o que é idêntico é a camada de widget.
- **Para o denominador de qualquer RQ que meça eficácia da guia MOP.** Reportar eficácia sobre os 181 apps mistura um estrato onde o tratamento existe com um onde ele é provadamente inativo.

---

## 3. Por que a exclusão do Soot não é o obstáculo que parece

`Main.java:224-227` exclui `kotlin.`, `kotlinx.` e `androidx.compose.` com `-no-bodies-for-excluded`. A leitura intuitiva — "o Soot não enxerga nada de Compose" — está errada num detalhe que decide a viabilidade.

`-no-bodies-for-excluded` faz o Soot **não carregar os corpos** das classes excluídas; elas viram referências phantom. O que *não* é afetado é o corpo dos métodos do app, que continua contendo os sítios de chamada com assinatura completa para dentro do framework. Um `invoke-static ... androidx/compose/material3/ButtonKt;->Button(...)` dentro de uma função do app permanece integralmente visível e casável por `InvokeExpr.getMethodRef()`.

Ou seja: a análise de *fluxo* morre (não há corpo para propagar), mas a análise *sintática de sítios de chamada* sobrevive intacta. E o client já tem exatamente essa ferramenta, construída para outro propósito (recuperação de arestas em `IGNORED_CLASSES`, INV-ANA-22):

```java
// RvsecAnalysisClient.java:513
public static int[] scanInvokesInAppClasses(
        Map<SootClass, List<SootMethod>> appClasses, InvokeVisitor visitor, String passLabel)
```

Toda a extração proposta na §4 é implementável como um novo `InvokeVisitor` sobre esse helper, mais análise def-use local (o `JimpleDefUtils` do gator) para resolver os argumentos constantes. **Sem levantar a exclusão, sem novo algoritmo de call graph, sem custo de escala adicional.**

---

## 4. As âncoras extraíveis, verificadas em bytecode real

Decodifiquei `dev.itsvic.parceltracker_10501000.apk` (Compose puro, 0 widgets na WTG hoje) e inspecionei o smali. As quatro âncoras abaixo são o que uma passada Compose consumiria.

### 4.1 A raiz da árvore: `setContent`

```smali
# MainActivity.smali:227
invoke-static {...}, Landroidx/activity/compose/ComponentActivityKt;->setContent$default(
    Landroidx/activity/ComponentActivity;Landroidx/compose/runtime/CompositionContext;
    Lkotlin/jvm/functions/Function2;ILjava/lang/Object;)V
```

O `Function2` é a classe da lambda de conteúdo, no próprio app. Isso liga **Activity → composable raiz**, que é o par que a WTG hoje não consegue formar. Presente em **98,2%** dos apps Compose do corpus.

### 4.2 As telas: registro de destinos do Navigation-Compose

`composable<Rota> { }` é função `inline reified` — não sobrevive como chamada. Mas o que ela *inlina* é um padrão fixo e trivialmente reconhecível:

```smali
# MainActivityKt.smali:1496-1507
invoke-static {v7}, Lkotlin/jvm/internal/Reflection;->getOrCreateKotlinClass(Ljava/lang/Class;)Lkotlin/reflect/KClass;
new-instance v15, Landroidx/navigation/compose/ComposeNavigatorDestinationBuilder;
invoke-direct {v15, v3, v7, v4, v0}, Landroidx/navigation/compose/ComposeNavigatorDestinationBuilder;-><init>(
    Landroidx/navigation/compose/ComposeNavigator;Lkotlin/reflect/KClass;Ljava/util/Map;Lkotlin/jvm/functions/Function4;)V
```

Cada `<init>` é **uma tela**: o `KClass` (vindo de um `const-class` local) dá a identidade da rota; o `Function4` dá a classe da lambda que compõe a tela. Ambos resolvíveis por def-use intraprocedural.

Vale registrar que este app usa **navegação type-safe** (rotas como classes `@Serializable`, Navigation-Compose 2.8+) — a variante que `20260730` §6.2 listou como ressalva por não usar strings. Na prática ela é **mais fácil**, não mais difícil: uma referência de classe é um alvo estático exato, enquanto uma string de rota exige casar padrões de template (`"detalhe/{id}"`) contra os argumentos de `navigate`.

### 4.3 As arestas: `navigate(rota)`

```smali
# MainActivityKt$ParcelAppNavigation$6$1$1.smali:148,179,211
sget-object v1, Ldev/itsvic/parceltracker/AddParcelPage;->INSTANCE:...   # object
new-instance v2, Ldev/itsvic/parceltracker/ParcelPage;                   # data class
sget-object v1, Ldev/itsvic/parceltracker/SettingsPage;->INSTANCE:...
invoke-static/range {...}, Landroidx/navigation/NavController;->navigate$default(
    Landroidx/navigation/NavController;Ljava/lang/Object;...)V
```

Origem = a lambda que contém a chamada, encadeada de volta à tela que a criou; destino = a classe de rota do argumento. É o análogo direto da aresta cross-window da WTG — a estrutura cuja ausência em 89,5% dos apps Compose motivou este trabalho. Presente em **68,2%** dos apps Compose (`NavHostKt`).

**O terço restante não tem grafo extraível**: navega por *state hoisting* (`var tela by remember { ... }` com um `when`), onde a transição é um `if` sobre estado local, não uma chamada. A ressalva de `20260730` §6.2 se confirma, agora com número.

### 4.4 Os widgets: fábricas de elementos e seus rótulos

Contagem de sítios de chamada nas classes do app (`dev/itsvic/parceltracker`):

| fábrica | sítios |
|---|---:|
| `material3.TextKt->Text` | 53 |
| `material3.IconKt->Icon` | 15 |
| `material3.OutlinedTextFieldKt->OutlinedTextField` | 5 |
| `material3.IconButtonKt->IconButton` | 5 |
| `material3.ButtonKt->Button` | 5 |
| `material3.AndroidMenu_androidKt->DropdownMenuItem` | 6 |
| `foundation.ClickableKt->clickable` | 3 |
| `material3.SwitchKt->Switch` | 2 |

Cada `Button(...)` traz o handler no argumento 0 (`Function0` = `onClick`) e o rótulo no argumento 9 (`Function3` de conteúdo). O rótulo é resolvível:

```smali
# ...$AddEditParcelView$2$1$1$9$2.smali:162,208
invoke-static {v4, v0, v5}, Landroidx/compose/ui/res/StringResources_androidKt;->stringResource(ILandroidx/compose/runtime/Composer;I)Ljava/lang/String;
invoke-static/range {...}, Landroidx/compose/material3/TextKt;->Text--4IGK_g(Ljava/lang/String;...)V
```

O `int` é um id de `R.string` — e **o client já resolve nomes via a classe `R$string` do app, com cache** (`RvsecAnalysisClient.java:827, 1235`). A maquinaria de rótulo existe; falta apontá-la para cá.

Há ainda uma âncora de identidade barata que o plugin do compilador injeta:

```smali
const-string v4, "dev.itsvic.parceltracker.ui.views.AddEditParcelView (AddEditParcelView.kt:55)"
```

É o marcador de `traceEventStart`: **nome totalmente qualificado do composable + arquivo:linha**, como constante de string. Dá um identificador estável e legível para tela/elemento sem depender de nenhuma inferência.

### 4.5 Prevalência das âncoras no corpus (181 APKs)

Varredura do pool de strings dos `.dex` dos 181 APKs de `RV_ANDROID_NOVO_DATASET/APKS`:

| âncora | apps Compose (n=110) | % |
|---|---:|---:|
| `androidx.compose.runtime.Composer` (é Compose) | 110 | 100,0% |
| `ComponentActivityKt` (`setContent`) | 108 | 98,2% |
| `NavHostKt` (Navigation-Compose) | 75 | **68,2%** |
| `ComposeNavigatorDestinationBuilder` | 70 | 63,6% |
| `NavController` | 78 | 70,9% |
| `material3.ButtonKt` / `TextKt` / `OutlinedTextFieldKt` / `IconButtonKt` | 105 | 95,5% |
| `foundation.ClickableKt` | 110 | 100,0% |
| `StringResources_androidKt` (rótulo por recurso) | 110 | 100,0% |

Duas ressalvas de honestidade sobre esta tabela:

- **Presença do descritor no pool é condição necessária, não suficiente.** Ela prova que o tipo é referenciado em algum lugar do APK — não que a chamada esteja numa classe do app dentro do pacote filtrado. O número real de sítios extraíveis é ≤ estes percentuais. A inspeção da §4.1–4.4 confirma o caso positivo num app; generalizar exigiria rodar a passada.
- **O detector B subestima.** 110 apps têm Compose pelo pool de strings contra 103 pelo detector B sobre os JSONs (~6% de diferença). Se o estrato virar eixo de análise pré-registrado, vale reconciliar os dois.

### 4.6 `testTagsAsResourceId`: a hipótese de escape, medida e fechada

Um app que habilite `testTagsAsResourceId` dá resource-id aos seus nós Compose na árvore de acessibilidade — e funcionaria hoje, sem mudança alguma no gator ou no APE-RV. Era a única hipótese que devolveria chave de join ao estrato. Ela foi medida.

**Varredura por string pool não responde**: `testTagsAsResourceId` aparece em 110/110 apps Compose, mas isso é artefato — a própria `compose-ui` define a propriedade, e o nome está no pool de qualquer APK que a empacote. Distinguir "habilita" de "empacota" exige achar um *sítio de chamada* em classe que não seja de biblioteca, o que só a desmontagem responde.

**Método**: baksmali (embutido no `apktool.jar`) sobre os 110 APKs Compose, em três filtros — descarta o dex que não contém o nome; `baksmali list classes` enumera as classes; `baksmali d --classes` desmonta só as fora dos prefixos de biblioteca; `grep` procura a invocação de `setTestTagsAsResourceId`. Validação: (i) **controle positivo** — sem o filtro de biblioteca o pipeline encontra `androidx/compose/ui/semantics/SemanticsProperties_androidKt`, provando que um `False` significa ausência de chamador no app e não detector quebrado; (ii) o caminho rápido reproduz o caminho lento (desmontagem integral) em 3 casos, incluindo um positivo.

**Resultado: 5 de 110 apps (4,5%)**, zero erros de análise:

| app | classe chamadora |
|---|---|
| `at.techbee.jtx_216000015` | `at/techbee/jtx/MainActivity2` |
| `com.dessalines.habitmaker_5501` | `.../ui/components/common/DialogsKt` |
| `com.dessalines.rankmyfavs_44` | `.../ui/components/common/DialogsKt` |
| `com.dessalines.thumbkey_179` | `.../ui/components/common/DialogsKt` |
| `com.orgzlyrevived_284` | `com/orgzly/android/ui/savedsearch/SavedSearchContentKt` |

Três dos cinco são do mesmo autor com o mesmo arquivo — são 3 códigos-base independentes, não 5.

**E o *onde* importa mais que o quanto.** O opt-in vale apenas para a subárvore sob aquele `Modifier.semantics`; nos cinco casos é **um componente** (um diálogo, uma tela, uma activity), não o app. A confirmação é direta: `com.dessalines.habitmaker` está no corpus de calibração e, mesmo habilitando o opt-in, registrou **0 boosts MOP em 44.359 ações avaliadas** — e nos seus traces os únicos resource-ids não vazios são `android:id/button1/2/3`, os botões de `AlertDialog` do **framework**, não nós Compose (e ids de framework, que o lado estático do app nunca teria).

**Veredito: hipótese fechada.** O opt-in é raro (4,5%), e onde existe é pontual demais para produzir substrato.

---

## 5. O bloqueio real: o join do consumidor

Esta seção é a razão pela qual a §4, sozinha, não resolve nada.

O APE-RV consome o JSON em `MopData.java`. Widgets são indexados **por `idName`**, e os que não têm são descartados na carga:

```java
// MopData.java:435-444
if (wd.idName == null || wd.idName.isEmpty()) {
    if (flagged) { droppedFlaggedNoId[0]++; }
    continue;   // INV-MOP-20
}
```

E toda consulta em runtime parte do resource-id do nó da árvore de UI:

```java
String shortId = MopData.extractShortId(node.getResourceID());
MopData.Widget w = mopData.getWidget(activity, shortId);
```

— em `MopScorer`, `ApePromptBuilder`, `WtgPass`, `FrontierPass`, `MopFrontierPass` e `ApeAgent`. A spec `mop-guidance` fecha a porta explicitamente:

> **INV-MOP-20**: Widgets with an empty `idName` SHALL NOT be stored […] *Matching such widgets by class/text/bounds is out of scope.*

Em Compose o nó de runtime tipicamente **não tem** resource-id (o `testTag` só vira resource-id sob o opt-in `testTagsAsResourceId`). Logo: emitir widgets Compose no JSON com `idName` vazio faz com que **100% deles sejam descartados na carga**, e emiti-los com um `idName` sintético faz com que **nenhum case** com o que o runtime apresenta. Os dois caminhos terminam em zero.

Do lado positivo, o consumidor já tem duas costuras prontas para este trabalho:

- `MopData.isWidgetlessSubstrate()` (INV-MOP-28) — detecta exatamente o caso "nenhuma janela tem widget", com o comentário *"No consumer yet"*. É o gancho natural para ligar uma via alternativa de join.
- `activityHasMop` continua correta em Compose via a união de 3 fontes (INV-MOP-27), porque as fontes 2 e 3 vêm de `components`/`reachability` e não da camada GUI.

O único par de identificadores que **em princípio** sobrevive dos dois lados em Compose é **texto e content-description**: estático via `stringResource`/`const-string` (§4.4), runtime via a árvore de semantics que o UIAutomator lê. A §5.1 mede o teto dessa via — e o resultado é que ela não serve como mecanismo primário.

### 5.1 O teto da via de texto, medido

Se a chave de join tem de ser texto/content-description, a pergunta é quantos elementos de runtime a possuem. As linhas de elemento do prompt do LLM rendem essa medida diretamente: `ApePromptBuilder` monta cada linha com `safeGetDisplayText(node)` (texto, ou content-description como fallback), e uma linha sem string é um elemento sem nenhum dos dois. Sobre os mesmos 812 traces, 304.793 linhas de elemento:

| estrato | elementos acionáveis | com texto/content-desc | **sem identificador algum** |
|---|---:|---:|---:|
| **Compose** | 139.317 | 32.842 (23,6%) | **106.475 (76,4%)** |
| View | 165.476 | 113.049 (68,3%) | 52.427 (31,7%) |

E a distribuição por classe de elemento é pior que o agregado:

| classe (runtime) | Compose: total | com texto | % | apps View: % |
|---|---:|---:|---:|---:|
| `View` | 75.595 | 1.917 | **2,5%** | 94,3% |
| `TextView` | 14.461 | 14.461 | 100,0% | 98,9% |
| `EditText` | 12.992 | 8.604 | 66,2% | 93,7% |
| `ScrollView` | 10.030 | 4 | 0,0% | 0,0% |
| `Button` | 9.166 | 4.139 | **45,2%** | 95,1% |
| `Spinner` | 4.801 | 18 | 0,4% | 10,4% |
| `CheckBox` | 3.249 | 0 | **0,0%** | — |
| `RadioButton` | 383 | 0 | **0,0%** | 96,1% |

A linha `View` é um controle interno forte: **mesmo renderizador, mesmo caminho de código**, 94,3% em apps View contra 2,5% em Compose. A diferença não é artefato do builder — é propriedade da árvore de semantics do Compose, que mapeia para `android.view.View` genérica todo elemento sem `Role` declarado. E `View` genérica é **54% de todos os elementos acionáveis** do estrato Compose: é onde o Compose põe `Modifier.clickable` (linhas de lista, cards, ícones, áreas tocáveis). Mesmo os `Button` — que em app View trazem rótulo em 95,1% dos casos — ficam em 45,2%.

**Conclusão**: a via de texto tem teto de ~23,6% dos elementos e ~2,5% na classe dominante. Isso é pouco demais para sustentar guia MOP em nível de widget, e o déficit se concentra exatamente onde a guia precisaria agir. **Não existe chave de join em nível de widget para Compose entre as que sobrevivem dos dois lados.** Ver §6 para o que resta.

---

## 6. Desenho, se for para fazer

Duas partes acopladas. Nenhuma entrega valor sozinha; a ordem entre elas é indiferente, mas o *merge* de qualquer uma sem a outra é código morto.

### P1 — passada Compose no client do gator

Um `ComposeUiPass` novo em `presto.android.gui.clients`, rodando após a WTG e **acrescentando** ao `List<Map<String,Object>> windows` que `prepareWindows` já devolve (`RvsecAnalysisClient.java:168, 201`). Implementação: um `InvokeVisitor` sobre `scanInvokesInAppClasses`, mais def-use local para os argumentos constantes.

- **Janelas**: uma por `ComposeNavigatorDestinationBuilder.<init>` (nome = FQN da classe de rota), mais uma por `setContent` (a raiz). Ids sintéticos na faixa já reservada para janelas fora da WTG (`fallbackId >= 100000`).
- **Widgets**: um por sítio de fábrica de elemento alcançável a partir do corpo da tela, com `type` = nome da fábrica, `text` = rótulo resolvido, `listeners[]` = a classe da lambda `onClick` como `handler` — que é justamente a chave que o `ReachabilityEnricher` e o desempate de lambda sintética do `MopData` (`syntheticLambdaEnclosingClass`) já sabem cruzar.
- **Transições**: uma por `navigate(rota)`, origem = tela que contém a lambda, destino = classe de rota. Exige mudar `writeTransitionsSection(JsonWriter, WTG)` para aceitar arestas sintéticas — hoje ela lê a `WTG` diretamente (`RvsecAnalysisClient.java:1689`). É a única alteração de assinatura no writer.
- **Contrato JSON**: sem chaves novas, para não quebrar INV-ANA-32 (paridade `JsonSchema.Keys` ↔ `_JK` do Python). A única adição defensável seria uma marca de proveniência por janela (`"source": "compose"`), e ela custa uma atualização coordenada dos dois lados mais o teste de paridade.

**Rendimento esperado**: telas e arestas em ~68% dos apps Compose; widgets em ~95%; nada nos ~32% que navegam por state hoisting.

### P2 — o que *não* funciona: join por texto em nível de widget

O desenho natural seria levantar INV-MOP-20 sob condição — um índice paralelo `widgetsByText[activity][texto]`, consultado só em falha do resource-id e só quando `isWidgetlessSubstrate()` for verdadeiro. **A §5.1 mostra que isso não sustenta o mecanismo**: teto de 23,6% dos elementos, 2,5% na classe `View` genérica que responde por 54% do estrato. Some-se o risco de falso-positivo (textos como "OK"/"Salvar" repetem entre telas, e um casamento errado dá prioridade MOP à ação errada) e a relação custo-benefício fica ruim: paga-se emenda de invariante publicada para cobrir um quarto dos casos, com ruído.

Registrado como **descartado**, não como pendente. A guia MOP **em nível de widget** não é recuperável em Compose por join estático — não porque falte substrato estático, mas porque **o lado de runtime não expõe identificador algum** para a maioria dos elementos.

### P2′ — o que resta: join em nível de tela

A guia que continua possível é mais grossa: não "clique neste botão", mas "esta tela alcança alvo JCA, navegue até ela". Ela precisa de uma chave de tela, não de widget, e aí a aritmética inverte a favor: mesmo a 23,6% de cobertura por elemento, uma tela com 20 elementos exibe ~5 rótulos, e o *conjunto* de rótulos é uma impressão digital com redundância embutida — muito mais robusta que qualquer rótulo isolado.

- **Lado estático (P1)**: cada rota vira uma janela com o saco de textos dos elementos que seu composable compõe, e uma flag de alcance a alvo derivada dos handlers daquela subárvore.
- **Lado runtime**: o estado corrente do APE já é caracterizado pelo conjunto de elementos; casar por interseção de sacos de texto, com limiar.
- **Uso**: alimenta priorização de navegação (o que o B9/N7 queria e não teve por falta de arestas), não o boost de widget.

#### O gate desta via, medido — e reprovado

O experimento que decide P2′ é offline e roda sobre os traces existentes. Desenho *leave-one-out*: cada bloco de prompt dá um par (estado, saco de textos observado); o "lado estático" é aproximado pela **interseção** dos sacos de todas as *demais* observações daquele estado — isto é, os rótulos sempre presentes, que são exatamente os que `stringResource`/`const-string` produziriam; a sonda é a observação retida, e recupera-se o estado de maior similaridade de Jaccard. Rótulos gerados em runtime (`#a1b2c3d4`) foram excluídos do saco, porque nunca casariam com um literal estático.

| | Compose | View |
|---|---:|---:|
| sondas | 11.523 | 11.176 |
| estado de runtime **sem texto algum** | **42,7%** | 12,1% |
| estado verdadeiro **sem saco estável** (nada a casar) | **66,9%** | 20,8% |
| topo-1 **condicional** a haver o que casar | **31,3%** | 28,9% |
| **topo-1 global** | **10,4%** | 22,9% |

Duas leituras, e a segunda é a que encerra a questão:

1. **Compose perde dois terços dos casos antes de qualquer casamento.** Em 66,9% das sondas o estado verdadeiro não tem *nenhum* texto invariante entre suas próprias observações — não há impressão digital a produzir, por melhor que fosse a análise estática.
2. **E o casamento por texto é intrinsecamente fraco, mesmo onde é possível.** A taxa condicional é praticamente a mesma nos dois estratos (31,3% contra 28,9%): quando há o que casar, o saco de textos acerta a tela ~3 vezes em 10 — ou seja, **erra 7**. Isso não é um déficit de Compose que o gator pudesse cobrir; é uma propriedade da chave.

O melhor app Compose chega a 21,8% de topo-1 global; o pior, 1,3%.

**Ressalvas, com a direção do viés declarada.** A verdade-fundamental é a chave de estado abstrato do APE, que é fina (inclui hash e contagem de widgets): uma rota mapeia para vários estados, então "recuperar o estado exato" é mais difícil que "recuperar a rota certa" — isso **pessimiza** o topo-1. Mas agrupar estados em rotas **não** conserta o piso: a interseção sobre mais observações só encolhe, então o "sem saco estável" pioraria, não melhoraria. E se a naming em uso incorporar texto na identidade do estado, o topo-1 fica **otimista** por circularidade — o que só reforça a conclusão negativa.

**Veredito: P2′ reprovado.** O join estático→runtime em Compose não é viável em nenhuma granularidade — nem de widget (§5.1), nem de tela.

### O que resta: substrato observado

Com P2 e P2′ reprovados, a única via que sobra para Compose é a que `20260730` §6.4 já apontava e que **não passa por análise estática nenhuma**: o grafo de estados que o APE constrói em runtime. Ele não tem problema de join por construção — os nós *são* os estados observados, e a identidade é a própria chave de estado do APE, não uma inferência.

O preço é conhecido e deve ser dito: o modelo observado só conhece telas **já visitadas**, então ele guia exploração a partir do que viu, não em direção ao que nunca viu. Era exatamente essa a vantagem que o substrato estático teria — e é ela que as medições desta sessão mostram inalcançável em Compose. A troca, portanto, não é entre "estático melhor" e "observado pior": é entre "observado, com escopo limitado ao visitado" e "estático, que não casa".

Uma consequência que vale registrar para o texto da tese: em Compose, **a guia por análise estática não é uma alternativa disponível**. Isso é resultado, não limitação de implementação, e deve ser reportado como tal.

---

## 7. Custos e riscos

- **Re-análise do corpus.** Qualquer mudança no produtor invalida os `.apk.json` existentes. São 348 APKs no corpus e ~30 já re-analisados no gh91; é a razão declarada da regra de não mexer no gator, e ela continua válida.
- **Prazo.** A corrida decisiva do E3 está pré-registrada para esta semana, e a change aberta do APE-RV exclui o gator do escopo por decisão de prazo. P1+P2 não cabem nessa janela — nem parcialmente, porque o valor só aparece com as duas.
- **Superfície de teste.** P1 mexe no writer (assinatura de `writeTransitionsSection`) e no contrato consumido pelo parser Python; P2 mexe numa invariante publicada da spec `mop-guidance`. Ambas exigem change OpenSpec própria, nos respectivos repositórios.
- **Fragilidade a minificação.** A extração casa nomes de classe do AndroidX. Num app com R8 em modo agressivo esses nomes somem. No corpus atual isso não aparece (110/110 têm os descritores intactos), mas é uma premissa do corpus F-Droid, não uma garantia geral — e vale dizer isso em qualquer texto de tese que reporte a cobertura da passada.
- **Escopo real.** Mesmo com tudo funcionando, ~32% dos apps Compose (state hoisting) continuam sem grafo de navegação. A passada melhora o estrato, não o fecha.

---

## 8. Recomendação

**Não iniciar P1+P2 agora.** O custo é uma re-análise do corpus mais duas changes coordenadas, contra um prazo que já está fechado; e a decisão de 2026-07-29 sobre o gator foi tomada com esse mesmo trade-off à vista.

O que a investigação estabeleceu, em relação ao que se supunha em 2026-07-29:

1. O custo do lado do gator é **menor do que se supunha** — bytecode scan sobre helper existente, sem levantar a exclusão do Soot, sem passe de call graph novo (§3, §4).
2. O problema é **maior do que se supunha** — não é "sinal fraco", é 0 de 629.417 (§2).
3. Mas a conclusão de engenharia é **negativa e vale a pena registrar como tal**: a guia de widget não é recuperável, porque o déficit está na árvore de acessibilidade do Compose (76,4% dos elementos sem identificador; 2,5% na classe dominante — §5.1), e nenhuma análise estática supre ausência de identificador do lado de runtime. Isso encerra a leitura de que "consertar o gator resolveria" — e, mais importante, encerra também a leitura de que "consertar o consumidor resolveria".

4. O gate da guia em nível de **tela** foi executado nesta sessão e **reprovou** (§6, P2′): topo-1 de 10,4% em Compose, com 66,9% dos casos sem sequer uma impressão digital a produzir; e a taxa condicional (31,3%) é igual à de apps View, mostrando que a fraqueza é da chave, não do estrato.

**Nenhuma via de join estático→runtime sobrevive em Compose**, em nenhuma granularidade. A resposta para o estrato Compose é o substrato observado em runtime, que não depende de join — com o escopo limitado a telas já visitadas, e isso deve ser reportado como resultado, não como limitação de implementação.

5. A última hipótese de escape — apps que habilitem `testTagsAsResourceId`, cujos nós Compose teriam resource-id em runtime — foi medida por desmontagem e **fechada** (§4.6): 4,5% dos apps (5 de 110, sendo 3 do mesmo autor), e em todos eles o opt-in cobre **um componente**, não o app. O caso testável do corpus de calibração (`com.dessalines.habitmaker`) habilita o opt-in e ainda assim marca 0 boosts em 44.359 ações.

Resta uma única recomendação, e ela é de análise, não de engenharia:

- **Reportar o zero medido da §2 na análise da corrida decisiva**, junto com a estratificação por toolkit que `20260730` §7 já recomendou. É a diferença entre "a guia MOP não teve efeito" e "a guia MOP não pôde ter efeito em 55% do corpus" — e agora sabe-se que a segunda leitura é estrutural, com todas as saídas testadas e reprovadas.

---

## 9. Método e reprodutibilidade

- **Efeito no mecanismo (§2)**: regex `\[APE-RV\] MOP boost: .*?boosted=(\d+)/(\d+), maxBoost=(\d+)` sobre os 812 arquivos `*aperv*.trace` de `rv-android/experimento-cal/iter0/results/*/*/*/`, agregado por APK; estrato Compose por presença de `Landroidx/compose/runtime/Composer;` no pool de strings dos `.dex`. Semântica dos campos verificada em `MopWidgetPass.java:37-65` (denominador = ações válidas, resolvidas, que exigem alvo).
- **Prevalência das âncoras (§4.5)**: `scan_anchors.py`, varredura dos `.dex` dos 181 APKs de `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS` procurando descritores de tipo. Script e saída (`anchors.json`) no scratchpad da sessão.
- **`testTagsAsResourceId` (§4.6)**: `testtag_v2.py` (scratchpad). Para cada um dos 110 APKs Compose: dexes sem a string `setTestTagsAsResourceId` descartados; `baksmali list classes`; `baksmali d --classes` só das classes fora dos prefixos de biblioteca (`androidx/`, `kotlin*`, `com/google/`, …), em lotes de 800; `grep -rl` no smali resultante. Controle positivo: com o filtro de biblioteca desativado o pipeline encontra `androidx/compose/ui/semantics/SemanticsProperties_androidKt`. Concordância com a desmontagem integral verificada em 3 APKs (1 positivo, 2 negativos). 0 erros em 110.
- **Recuperação por saco de textos (§6, P2′)**: `bagmatch.py` (scratchpad da sessão). Blocos de prompt dos mesmos 812 traces; estado atribuído pelo `state=` do `[APE-STEP]` seguinte ao bloco; saco = strings renderizadas nas linhas de elemento, excluídos rótulos `#[0-9a-f]{6,}`; apenas estados com ≥2 observações; canônico = interseção das demais observações (leave-one-out); similaridade de Jaccard; topo-1 exige score > 0.
- **Cobertura de identificador em runtime (§5.1)**: regex `^\s+\d+\.\s+(\S+)\s+(.*)@\(\d+,\d+\)` sobre as linhas de elemento dos prompts nos mesmos 812 traces (304.793 linhas); um elemento conta como "com texto" quando a linha traz string entre aspas não vazia. Semântica verificada em `ApePromptBuilder.java:380-433` — a string renderizada é `safeGetDisplayText(node)`, que devolve texto ou, na falta, content-description. Estratificação por classe usa o `className` que o próprio nó de acessibilidade reporta.
- **Inspeção de bytecode (§4.1–4.4)**: `apktool d` de `dev.itsvic.parceltracker_10501000.apk`; leitura direta do smali nos sítios citados.
- **Código verificado (2026-07-31)**: gator — `Main.java:224-227`, `RvsecAnalysisClient.java:78-210, 513-558, 840-955, 1689-1739`. APE-RV — `MopData.java:243-289, 404-455, 464-519, 526-553, 561-598, 951-992`; `MopWidgetPass.java:37-65`; `openspec/specs/mop-guidance/spec.md:18, 30, 139-174, 773-774`; `openspec/changes/telemetry-proof-llm-efficacy/proposal.md`.

## 10. Documentos relacionados

- `20260730_compose_gator_substrato_estatico.md` — por que a WTG colapsa; taxonomia do problema; §6 com as quatro opções de correção que este documento instrumenta.
- `20260729_propostas_melhorias_e3.md` §0 (registro de decisões, incluindo a regra do gator), §8 (achados F1/F6/F7, itens N1/N6/N7, B9).
- `20260730_preregistro_corrida_decisiva.md` — o pré-registro em que a estratificação por toolkit deve entrar.
- `ape/openspec/changes/telemetry-proof-llm-efficacy/` — change aberta do APE-RV; exclui o gator do escopo e contém N1, que já opera na chave texto/content-description.

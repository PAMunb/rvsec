# Design: identidade de composable como chave de junção estático↔runtime em apps Jetpack Compose

**Data**: 2026-08-03
**Escopo**: desenho técnico completo da única via que sobreviveu à análise dos três documentos anteriores — usar a identidade de composable (FQN + arquivo:linha, emitida pelo plugin do compilador Compose) como chave de junção entre o substrato estático produzido pelo `rvsec-gator` e o modelo de UI que o APE-RV manipula em runtime.
**Status**: design doc. Contém um experimento decisivo (§9) que pode derrubar a via inteira antes de qualquer investimento. **Nenhuma decisão de implementação está tomada, e nenhuma das revogações de governança da §17 foi solicitada.**

**Quarto de uma série** sobre gator × Compose:

1. `20260730_compose_gator_substrato_estatico.md` — *por que* a WTG colapsa (diagnóstico).
2. `20260731_gator_compose_viabilidade.md` — *o que dá para fazer* no desenho atual (quatro vias testadas, todas reprovadas).
3. `20260731_sota_analise_estatica_compose.md` — *o que o mundo faz*, e a opção que isso reabriu.
4. **este** — *como essa opção seria construída*, o que a mataria, e a que custo.
5. `20260803_compose_d1_decisao_plano_rearch.md` — a decisão (D1), as verificações em código, e o plano integrado à rearquitetura do APE-RV. **Corrige dois pontos deste documento**: o canal da §13 (`applyXPathlets`) é deletado e proibido pela change `rearch-02-runspec`, e a change `telemetry-proof-llm-efficacy` (§17, §20) foi arquivada em 2026-08-02. A emenda de 2026-08-06 daquele documento (§11) **corrige um terceiro ponto deste**: a §11.2(c) abaixo.
6. `20260806_compose_e1_resultado.md` — **o E1 da §9 rodou, e a Via A passou**: 343 FQNs distintos em runtime, casando com a extração estática por igualdade de string, a 1,8 µs por composable. A Via B ficou em zero, como previsto. Aquele documento **corrige a emenda que corrigia a §11.2(c) deste**: o pré-passe `DexWeaver.weaveStaticInit` descarta em silêncio todo advice `staticinitialization` que não entregue Signature, então a costura por `<clinit>` não é expressável no descritor como a emenda supunha — mas também não é necessária, porque o advice `before` sobre o `call(setContent)` já precede a primeira composição.

---

## 1. Sumário executivo

O documento 3 identificou que a identidade de composable é **a primeira chave de junção que existe integralmente dos dois lados** — presente no bytecode e presente em runtime — depois que resource-id, texto, saco de textos e `testTag` falharam todos pela mesma razão estrutural: a chave não existia dos dois lados.

Este documento verifica essa afirmação no bytecode real e no código dos dois consumidores, e chega a três conclusões que refinam o que estava escrito:

- **A presença estática se confirma, e com margem maior que a medida antes.** Varredura de **348 APKs** (não os 181 do subconjunto anterior): 174 são Compose, e **174/174 (100%)** carregam informação de fonte, em release, sem exceção.
- **Não é uma família de strings, são duas, com destinos de runtime opostos.** A família rica (`traceEventStart`, que dá FQN + arquivo + linha) é emitida sob guarda de `isTraceInProgress()`; a família incondicional (`sourceInformation`) identifica o arquivo apenas por hash de package. Isso desdobra a validação nº 1 do documento 3 em duas perguntas distintas — e abre uma via de ativação (registrar um tracer) que aquele documento não considerou, porque olhou somente para `CompositionData`.
- **A cadeia tem dois elos, não um, e o segundo é o problema real.** O "lado runtime" da chave é a **composição**; o APE-RV não age sobre a composição, age sobre a **árvore de acessibilidade**. Entre os dois há um segundo join que nenhum dos três documentos examinou.

A consequência de desenho é que existem **três desenhos possíveis**, e o mais barato deles (§7, D1) **descarta o segundo join inteiro** — abrindo mão do impulso por widget (que é exatamente o que mede 0 de 629.417) em troca de um sinal por tela ~20× mais granular que o `activityHasMop` atual.

E existe um obstáculo que nenhum dos documentos anteriores registra: **não há canal em runtime entre o app instrumentado e o APE-RV, e a spec publicada do APE-RV proíbe o canal óbvio** (§13).

**A recomendação é executar o experimento E1 da §9 antes de qualquer decisão.** Ele custa um arquivo Java de ~80 linhas e um run, não toca no gator nem no APE-RV, não exige revogar nenhuma decisão vigente, e tem poder de refutação total: se falhar, a via cai inteira e o resultado negativo da série fica completo.

---

## 2. O que este documento assume como estabelecido

Para não re-litigar o que já foi medido, estes pontos entram como premissas, com ponteiro para a fonte:

| Premissa | Fonte |
|---|---|
| A WTG colapsa em Compose por incompatibilidade de categoria, não por defeito do GATOR | doc 1, §2–§3 |
| Mediana de 0 widgets, 55,2% dos apps Compose com zero widgets, 89,5% sem aresta cross-window | doc 1, §4.1 |
| A guia MOP em nível de widget é **inerte**: 0 ações impulsionadas em 629.417 avaliadas (22 APKs Compose), contra 12,75% no estrato View | doc 2, §2 |
| O produtor (gator) é barato: a exclusão do Soot remove corpos do framework, não sítios de chamada no app | doc 2, §3 |
| O consumidor (APE-RV) é a barreira **latente**: todo join é por `resourceID`; `idName` vazio → descarte, `idName` sintético → não casa. **Não é a barreira vinculante** — ver a linha seguinte | doc 2, §5 |
| A barreira **vinculante** é do produtor: o GATOR emite `flagged=0` em 22/22 apps Compose, e com o conjunto flagged vazio o `MopScorer.score` devolve 0 para qualquer par `(activity, shortId)` — o join por `resourceID` nunca é alcançado. `droppedNoId=0` nos mesmos 22: o filtro de id nunca perdeu um widget flagged, porque nenhum existiu | verificação, §1.2.1 |
| Join por texto (teto 23,6%; 2,5% na classe `View` genérica) e por saco de textos (topo-1 de 10,4%) reprovados | doc 2, §5.1 e §6 |
| `testTag` disponível sem opt-in, mas com prevalência de 0% / 1,8% — a via está aberta e vazia | doc 3, §3.3 e §6 |
| Grafo de rotas extraível (68,2%) mas com obsolescência anunciada pelo Navigation 3 | doc 3, §3.5 |
| Não existe, na literatura nem na indústria, ferramenta que extraia modelo de UI Compose a partir de APK | doc 3, §4.3 |

**Nada neste documento propõe reabrir essas conclusões.** O que ele faz é detalhar a única via que sobrou.

---

## 3. Correções factuais aos documentos anteriores

Três achados desta verificação corrigem números ou descritores dos documentos 2 e 3. São correções de precisão, não de conclusão — nenhuma delas muda um veredito.

**3.1 — O descritor de `CompositionData` está errado no doc 3, §6.** O documento reporta "`CompositionData` 110/110" usando `Landroidx/compose/runtime/CompositionData;`, que dá **zero ocorrências**. O descritor correto é `Landroidx/compose/runtime/tooling/CompositionData;`, com o subpacote `tooling`. A medição em si estava certa (o doc 3 §10 lista o descritor correto no Método); o erro está apenas na §6. Quem for reproduzir precisa do descritor com `tooling`.

**3.2 — A mediana de 424 composables está inflada.** O doc 3 conta FQNs "não-biblioteca" excluindo prefixos `androidx.`, `kotlin*`, `com.google.` etc. Mas bibliotecas Compose de terceiros — `coil3.compose`, `com.airbnb.lottie.compose`, `com.mikepenz.markdown`, `com.bumptech.glide.integration.compose`, `org.fossify.commons` — também emitem essas strings e atravessam qualquer filtro por prefixo conhecido. Filtrando pelo package do próprio código do app, a mediana cai para **~149** (p25 24, p75 343, máx 1.972 em `eu.darken.sdmse`).

Esse ~149 é um **piso**, não uma estimativa central: a atribuição casa o `applicationId` com o prefixo do FQN, e 34 APKs deram zero apenas porque o package do código difere do applicationId. Verifiquei dois: `com.geeksville.mesh` tem centenas de FQNs sob `org.meshtastic.app.*`; `info.metadude.android.fosdem.schedule`, sob `nerd.tuxmobil.fahrplan.congress.*`. É a mesma armadilha que motiva a remoção do `PackageDetector`, e o doc 3 §10 já a havia registrado como ressalva — aqui ela aparece do outro lado.

**A conclusão não muda**: 149 composables próprios por app continua sendo ~20× mais granular que a mediana de 5–7 activities que hoje sustenta o `activityHasMop`. Mas o número a citar em texto de tese é ~149, não 424.

**3.3 — A base da medição de presença é maior do que o doc 3 reporta.** O doc 3 mediu 110 APKs Compose de um subconjunto. A varredura completa do diretório dá **174 Compose em 348 APKs (50%)**, e a taxa de presença de informação de fonte é 174/174 — mesma conclusão, base 58% maior.

---

## 4. O que existe do lado estático, verificado no bytecode

Método na §18. Ferramenta: `apktool.jar` (que embute o baksmali) e um parser próprio do `string_ids`/`string_data` do DEX.

> **Nota metodológica que custou tempo e vale registrar**: `strings -n 8 classes.dex` "funciona", mas cada string do DEX é precedida por um ULEB128 de comprimento que costuma cair em byte imprimível. O `strings` cola esse byte no início (`randroidx.compose…`, `Aandroidx.compose…`), o que quebra qualquer regex ancorada em `^`. Toda medição desta série que use `strings` cru sobre DEX precisa dessa ressalva.

### 4.1 As duas famílias de string

**`sourceInformation`** — formato `C(<Nome>)` + opcional `P(índices)` ou `N(nomes)` + lista `linha@offsetLcomprimento` + `:<Arquivo>.kt#<hash-do-package>`:

```
C(AboutDialog)34@1429L7,36@1484L1973,36@1440L2017:AboutDialog.kt#m8j8xw
C(ParcelRow)P(1,2)34@1453L2993:ParcelRow.kt#m8j8xw
C(HomeView)P(3)51@2213L34,52@2266L34,…,55@2364L2295:HomeView.kt#abgzwg
C(CollectionSelectorDialog)N(module,presetCollectionId,allCollections,onCollectionConfirmed,onDismiss)41@1474L116,…:CollectionSelectorDialog.kt#tn1i6d
CC(rememberCoroutineScope)482@20332L144:Effects.kt#9igjgp
```

Duas variantes de assinatura: `P(índices)` em plugins antigos, `N(nomes de parâmetro)` em plugins novos. Prefixo `C(` = grupo de composable declarado; `CC(` = *call* de composable inline. O `#hash` deriva do **package**, não do arquivo — arquivos do mesmo package compartilham hash.

**`traceEventStart`** — formato `<FQN completo> (<Arquivo>.kt:<linha>)`:

```
dev.itsvic.parceltracker.ParcelAppNavigation (MainActivity.kt:138)
dev.itsvic.parceltracker.ui.views.HomeView (HomeView.kt:50)
dev.itsvic.parceltracker.ui.components.AboutDialog.<anonymous> (AboutDialog.kt:37)
dev.itsvic.parceltracker.ComposableSingletons$AboutDialogKt.lambda-1.<anonymous> (AboutDialog.kt:58)
at.techbee.jtx.database.properties.Role.Icon (Attendee.kt:265)
org.meshtastic.app.ComposableSingletons$MainActivityKt.lambda$437289526.<anonymous> (MainActivity.kt:193)
```

A granularidade desce até **lambda anônimo dentro do conteúdo de um widget** — que é exatamente a granularidade de um alvo de toque.

### 4.2 Os sítios de chamada, em smali

Este é o ponto que a §5 vai explorar, e é preciso ver o bytecode para entendê-lo.

```smali
# sourceInformation — const-string seguido de invoke-static, SEM guarda
const-string v3, "C(ParcelAppNavigation)140@4999L23,…:MainActivity.kt#qhwu66"
invoke-static {v15, v3}, Landroidx/compose/runtime/ComposerKt;->sourceInformation(Landroidx/compose/runtime/Composer;Ljava/lang/String;)V

# sourceInformationMarkerStart — carrega TAMBÉM a chave de grupo (const v5)
const v5, 0x2e20b340
const-string v6, "CC(rememberCoroutineScope)482@20332L144:Effects.kt#9igjgp"
invoke-static {v15, v5, v6}, Landroidx/compose/runtime/ComposerKt;->sourceInformationMarkerStart(Landroidx/compose/runtime/Composer;ILjava/lang/String;)V

# traceEventStart — SEMPRE guardado por isTraceInProgress()
invoke-static {}, Landroidx/compose/runtime/ComposerKt;->isTraceInProgress()Z
move-result v3
if-eqz v3, :cond_41
const/4 v3, -0x1
const-string v4, "dev.itsvic.parceltracker.ParcelAppNavigation (MainActivity.kt:138)"
invoke-static {v2, v10, v3, v4}, Landroidx/compose/runtime/ComposerKt;->traceEventStart(IIILjava/lang/String;)V
:cond_41
```

Três observações de desenho saem daí:

1. **`sourceInformationMarkerStart` carrega a chave de grupo junto com a string.** Isso permite recuperar estaticamente o par *(chave de grupo → composable)* — a ponte entre a camada §3.1 e a §3.2 da taxonomia do documento 3, que aquele documento tratou como camadas separadas.
2. **O sítio de `traceEventStart` é sintaticamente trivial de casar**: `const-string` imediatamente antes de um `invoke-static` para uma assinatura fixa. É exatamente a forma de varredura que o `scanInvokesInAppClasses` (`RvsecAnalysisClient.java:513`) já faz.
3. **A guarda de `isTraceInProgress()` é o fato mais importante deste documento** — ver §5.

### 4.3 Volumes

| | `dev.itsvic.parceltracker` | `at.techbee.jtx` |
|---|---:|---:|
| strings `sourceInformation` | 2.918 (2.880 distintas) | 5.991 |
| — em arquivos `.kt` do próprio app | 137 | 2.496 |
| strings `traceEventStart` | 2.357 | 4.726 |
| — **FQNs do próprio package** | **104** | **2.090** |
| — composables de topo (sem lambda/`<anonymous>`) | 18 | — |

Distribuição nos 174 APKs Compose (FQNs do próprio package, piso conforme §3.2): mediana **149**, p25 24, p75 343, máx 1.972.

### 4.4 O que ainda não foi medido

**Nenhum APK amostrado estava ofuscado** — o corpus é F-Droid. A expectativa é que as constantes de string sobrevivam ao R8 com os nomes **originais** do fonte enquanto as classes viram `a.b.c`, o que na verdade *favoreceria* a via (a identidade estaria preservada onde o nome de classe não está). Mas isso é **inferência, não medição**, e precisa constar em qualquer afirmação de generalidade — ver §14.

---

## 5. A refinação: duas famílias, dois destinos de runtime

O documento 3 formula a validação nº 1 como uma pergunta única: *"a informação de fonte é coletada na slot table em runtime, ou só existe como constante no dex?"*. O bytecode mostra que a pergunta se desdobra, porque as duas famílias têm mecanismos de runtime **opostos**:

| | `sourceInformation` | `traceEventStart` |
|---|---|---|
| Conteúdo | nome do composable, offsets, `#hash` de package | **FQN completo + arquivo + linha** |
| Chamada em runtime | **incondicional** | somente se `isTraceInProgress()` |
| Destino | slot table → `CompositionData` | consumidor de trace registrado |
| Risco conhecido | *side table* desligada por padrão desde Compose 1.6.0 (`collectParameterInformation()`) | nenhum tracer registrado por padrão |
| Como ativar | chamar `collectParameterInformation()` de dentro da composição | registrar um tracer no `Composer` |

A leitura que isso permite:

- A família **mais rica** é justamente a que **não flui por padrão** — mas o que a bloqueia é uma **guarda estática que um probe injetado pode satisfazer**, não uma informação ausente. É um interruptor, não uma lacuna.
- A família que **flui incondicionalmente** dá o nome do composable, mas identifica o arquivo só por hash de package. Para um join por identidade isso pode bastar (o par *nome + hash de package* é razoavelmente discriminativo dentro de um app), mas é uma chave mais fraca e precisa ser medida como tal.

**Consequência para o plano**: o experimento E1 (§9) precisa testar **as duas vias**, não uma. E há uma terceira possibilidade que o doc 3 não considerou por ter olhado apenas para `CompositionData`: ativar o tracer é potencialmente mais barato que ler a slot table, porque o tracer *empurra* a informação em vez de exigir que se percorra a árvore a cada passo.

---

## 6. O buraco: são dois joins, não um

Esta é a contribuição principal deste documento, e é uma **restrição**, não uma oportunidade.

O documento 3 afirma que a chave "existe integralmente dos dois lados". Isso é verdade — mas o "lado runtime" é a **composição**, e o APE-RV **não age sobre a composição**. Ele age sobre a árvore de acessibilidade, através de um funil único:

```java
// ape/src/main/java/com/android/commands/monkey/ape/tree/GUITreeBuilder.java:629
node.setResourceID(StringCache.cacheStringEmptyOnNull(info.getViewIdResourceName()));
```

`GUITreeNode` tem exatamente cinco campos (`GUITreeNode.java:45-49`): `resourceId`, `className`, `packageName`, `text`, `contentDesc`. Não há nada de Compose no Java do APE-RV — `grep -E "testTag|semantics|Compose"` no código Java devolve **apenas comentários** (`LlmRouter.java:776-777`, `ActionType.java:43`, `LlmTapAction.java:24`, `MopData.java:953`), nenhuma implementação.

A cadeia real é, portanto:

```
  dex                    composição              árvore de acess.        APE-RV
  (FQN + arquivo:linha) ──J1──► (CompositionData) ──J2──► (AccessibilityNodeInfo) ──► GUITreeNode
                          ▲                         ▲                                fillNode:629
                          │                         │
              igualdade de identificador     ??? não examinado
                    (forte)                  por nenhum dos 3 docs
```

- **J1** é o que o documento 3 mediu, e é forte: igualdade de identificador entre uma constante do dex e um valor lido do runtime.
- **J2 é o join que decide se a via serve para alguma coisa**, e ninguém o examinou.

**J2 é plausivelmente resolúvel em processo**, e é importante ser preciso sobre o grau de confiança aqui: as APIs de `ui.tooling.data` expõem `NodeGroup.node`, que é o `LayoutNode`; o `SemanticsNode` referencia seu `LayoutNode` via `layoutInfo`; e o `SemanticsNode.id` é o que vira *virtual view id* do `AccessibilityNodeInfo`. Encadeando, existiria um caminho `composição → LayoutNode → SemanticsNode.id → nó de acessibilidade`.

**Isso é afirmação de API, não medição.** Não verifiquei nenhum desses elos em execução, e cada um deles é um ponto de falha independente. J2 é o principal risco técnico desconhecido do plano, e é por isso que o desenho recomendado (§8) o evita.

---

## 7. Os três desenhos

### D1 — Sinal por tela, sem J2

**Ideia**: não tentar casar widget nenhum. O probe lê a composição ativa, extrai o **conjunto de FQNs de composable em execução**, consulta uma tabela estática `FQN → reachesTarget` produzida pelo gator, e emite um sinal por estado explorado: *"esta tela tem MOP, através destes composables"*.

**O que ganha**: substitui o `activityHasMop` — 5 a 7 activities por app, e **constante 1 em 30% dos apps Compose** (doc 1, §4.2), o que o torna tautológico — por um sinal derivado de ~149 composables. É o insumo que o B9 e o N7 queriam e não conseguiram obter da WTG.

**O que abre mão**: o impulso por widget. Mas o impulso por widget é precisamente o que mede **0 de 629.417** (doc 2, §2). Não se está abrindo mão de um efeito existente.

**Por que é o desenho barato**: descarta J2 inteiro. Não precisa saber qual nó de acessibilidade corresponde a qual composable — precisa apenas saber *quais composables estão na tela*.

> **WHEN** o APE-RV chega a um estado de um app Compose cujo `activityHasMop` é 1 para toda activity
> **THEN** hoje o sinal MOP não discrimina esse estado de nenhum outro do app
> **AND** com D1 o sinal passa a ser o subconjunto de composables ativos que alcançam alvo JCA — potencialmente distinto entre telas da mesma activity.

### D2 — Mapeamento completo (o desenho implícito no doc 3)

**Ideia**: o probe percorre a `CompositionData`, desce ao `LayoutNode`, obtém o `SemanticsNode.id` e exporta o mapa `semanticsId → FQN`. O APE-RV ganha um campo novo em `GUITreeNode`, populado em `fillNode:629` a partir do id de acessibilidade, e o `MopData` ganha um segundo índice paralelo ao `widgetData`.

**O que ganha**: impulso por widget de verdade, o mecanismo original restaurado no estrato Compose.

**O que custa**: J2 inteiro (§6), mais acoplamento em runtime (§13), mais mudança no contrato de carga do `MopData`. Depende de três elos de API não verificados.

### D3 — Escrita de volta (fazer Compose parecer View)

**Ideia**: o probe injeta o identificador **na própria árvore de acessibilidade** — `testTag` sintético derivado do FQN, com `testTagsAsResourceId` ligado. O APE-RV lê `getViewIdResourceName()` como sempre.

**O que ganha**: **zero mudança no consumidor**. O `fillNode:629` já lê exatamente esse campo; os seis sítios de join continuam funcionando sem uma linha alterada. É o desenho mais elegante do ponto de vista de arquitetura.

**O que custa**: é o mais invasivo no app sob teste — exige tocar a cadeia de modifiers de cada composable, não apenas ler a composição. É o pior caso de efeito observador (§14).

### Comparação

| | D1 (sinal por tela) | D2 (mapeamento) | D3 (escrita de volta) |
|---|---|---|---|
| Precisa de J2 | **não** | sim | não (contorna) |
| Mudança no APE-RV | pequena (novo sinal) | média (campo + índice) | **nenhuma** |
| Mudança no gator | tabela `FQN → reachesTarget` | idem | idem |
| Invasividade no app | leitura | leitura | **escrita na UI** |
| Efeito observador | baixo | baixo | **alto** |
| Recupera impulso por widget | não | **sim** | sim |
| Riscos de API não verificados | 1 (E1) | 4 (E1 + 3 elos de J2) | muitos |

---

## 8. Desenho recomendado

**D1 primeiro, e D2 apenas se D1 mostrar valor.**

O raciocínio é de ordem de refutação, não de ambição. D1 depende de **um** fato não verificado (E1: a informação de fonte chega ao runtime). D2 depende desse mesmo fato **mais três elos de API de J2**. D3 depende de tudo isso mais uma alteração na renderização do app.

E há um argumento mais forte: **D1 endereça o problema que realmente existe**. O documento 1 (§4.2) mostra que em 30% dos apps Compose o `activity_has_mop` é constante 1 — o instrumento não tem contraste. O documento 2 mostra que o impulso por widget é inerte. Entre "dar contraste ao sinal que existe" e "restaurar um mecanismo que mede zero", o primeiro é a intervenção com hipótese mais defensável.

D3 fica registrado como possibilidade arquitetural elegante e **não é recomendado**: o efeito observador de reescrever a árvore de acessibilidade de um app cujo desfecho medido é contagem de violações é uma ameaça à validade cara de neutralizar.

---

## 9. E1 — o experimento decisivo

**Este é o único item deste documento que se recomenda executar.** Ele não toca no gator, não toca no APE-RV, não exige revogar nenhuma decisão vigente (§17), e tem poder de refutação total sobre as três alternativas.

### Pergunta

A informação de fonte chega ao runtime em um app real do corpus — por qualquer das duas vias da §5 — e a que custo de tempo?

### Procedimento

1. Escolher **um** APK Compose do corpus com informação de fonte abundante. `dev.itsvic.parceltracker_10501000.apk` é o candidato natural (104 FQNs próprios, já desmontado, já usado como exemplo nos documentos 2 e 3).
2. Escrever `mop/ComposeProbe.java` (~80 linhas) — **inteiramente com reflexão**, sem nenhuma referência de compilação a `androidx.compose.*` (a razão é a §11.2, e é uma restrição dura). O probe tenta, em ordem:
   - **Via A**: registrar um tracer no `Composer` e capturar as strings de `traceEventStart`.
   - **Via B**: obter o `CompositionDataRecord` via `androidx.compose.ui.tooling` e percorrer os grupos, lendo `sourceInformation`.
3. Injetar via pipeline `dexlib2` (§11), disparando o probe de um ponto de entrada de ciclo de vida.
4. Rodar o app pela plataforma (`rv-experiment run` / `rv-platform run` — a gestão do emulador é da plataforma, sem exceção).
5. Registrar: quantos FQNs distintos aparecem, se batem com os 104 extraídos estaticamente, e o **tempo de parede de uma leitura completa da composição**.

### Critérios de decisão

> **WHEN** nenhuma das duas vias produz FQN algum em runtime
> **THEN** a via cai inteira — D1, D2 e D3 morrem juntos
> **AND** o resultado negativo da série fica completo, e a §16 vira o texto de tese.

> **WHEN** ao menos uma via produz FQNs que casam com os extraídos estaticamente
> **AND** o tempo de leitura fica abaixo de ~80 ms
> **THEN** D1 é implementável, e o gate seguinte é a §15, Fase 2.

> **WHEN** os FQNs aparecem mas a leitura custa ~800 ms ou mais
> **THEN** D1 é inviável para decisão por passo (o APE-RV decide a cada passo)
> **AND** resta avaliar se um instantâneo por estado *novo* — não por passo — cabe no orçamento, o que é uma pergunta diferente e mais frouxa.

Os limiares de 80 ms e 800 ms vêm da trajetória documentada do **bitdrift** (doc 3, §5.2): ~800 ms com `asTree()`, ~80 ms com `mapTree()`. São referências de ordem de grandeza obtidas em UIs de produção, provavelmente mais pesadas que a mediana do corpus F-Droid — usar como faixa, não como corte exato.

### Custo

Um arquivo Java, uma flag no CLI de instrumentação, um run. Nenhuma re-análise de corpus. Nenhuma mudança no gator.

---

## 10. O lado produtor: o que o gator emitiria

Aplicável somente se E1 passar.

**O algoritmo** é a varredura sintática que o documento 2 já estabeleceu como barata, aplicada a um sítio novo: casar `const-string` + `invoke-static` para `ComposerKt->traceEventStart` (ou `->sourceInformation`) nas classes do app, e associar cada FQN extraído ao resultado de alcance que o call graph já produz.

**O gancho existe**: `RvsecAnalysisClient.java:513` (`scanInvokesInAppClasses`), o mesmo usado pelas outras varreduras.

**A exclusão do Soot não atrapalha**, pelo motivo já estabelecido no documento 2, §3: `-exclude androidx.compose.` com `-no-bodies-for-excluded` remove os **corpos** do framework, não os **sítios de chamada** nas classes do app. Consequência de governança relevante: **isto não exige tocar em `INV-ANA-16`** nem revisitar a decisão D2 do `gh51`.

**A saída** seria uma seção nova no `.apk.json`, no formato `{fqn, arquivo, linha, reachesTarget, directlyReachesTarget}`. Isso implica: mudança no writer Java, paridade `JsonSchema.Keys` ↔ `_JK` no parser Python (`INV-ANA-32`), e **re-análise do corpus** — 348 APKs. É o item mais caro do plano inteiro, e é por isso que ele fica na Fase 3 (§15), depois de E1 e depois de um piloto.

---

## 11. Mecânica de injeção: o que o pipeline já sabe fazer

O custo de injeção é **baixo, porque o pipeline já faz exatamente isso duas vezes** — `mop/Coverage.java` e `mop/MonitorWrappers.java`.

### 11.1 Os mecanismos que já existem

| Necessidade | Mecanismo existente | Referência |
|---|---|---|
| Adicionar classe nova ao APK | escrever `.java` em `--monitor-src-dir`; o `MonitorBuilder` compila recursivamente **tudo** que estiver ali, sem filtro por nome | `MonitorBuilder.java:71-75` |
| Empacotar no APK | `MultidexMerger` anexa em slots `classes<N>.dex` acima do maior índice existente | `MultidexMerger.java:126-132` |
| Hook em entrada de método | `CoverageWeaver` já prepende `const-string` + `invoke-static` na entrada de todo método | `CoverageWeaver.java:106-192` |
| Alocação de registrador | `RegisterShifter.spillLowRegisters`, com fallback de skip por método | `CoverageWeaver.java:155-175` |
| Reempacotar e assinar | `repackZip` → `zipalign` → `apksigner`, preservando método de compressão | `MultidexMerger.java:61-73` |

O emissor da classe seria uma cópia de `CoverageSourceEmitter.java` (67 linhas, das quais `:40-65` é o texto-fonte). O hook seletivo seria uma cópia de `CoverageWeaver.java` com outro predicado — o `InheritanceResolver` já construído em `BatchRunner.java:191-195` responde "é subtipo de `android.app.Activity`?". **Repack e assinatura: zero mudança.**

A parte historicamente perigosa — `VerifyError` por alocação de registrador, que produziu a regressão do `gh54` — **já está resolvida** e não precisa ser reinventada.

### 11.2 As duas restrições duras

**(a) O probe tem que ser escrito com reflexão pura.** O javac do `MonitorBuilder` só enxerga `android.jar` mais os jars de `--classpath` (`MonitorBuilder.java:82-85`), e **todo jar do classpath é dexado para dentro do APK** (`:138-140`). Um probe que importasse `androidx.compose.runtime.*` em tempo de compilação arrastaria o Compose para dentro do APK e colidiria com o Compose do próprio app — `Type defined multiple times`, exatamente o modo de falha que motivou o allowlist de três artefatos em `dexlib_instrumentation.py:117-129`.

Isto não é um detalhe de implementação: **decide a forma do probe**. Reflexão pura sobre `Class.forName("androidx.compose.ui.tooling.CompositionDataRecord")` e afins, com degradação graciosa quando a classe não existe.

**(b) Tem que ser na variante `dexlib2`, não `ajc`.** Soltar um `.aj` novo em `monitor_output_dir` seria mecanicamente mais barato — o ajc o compila e tece automaticamente, que é como o `Coverage.aj` chega lá. Mas a cadeia `dex2jar → ajc → d8` é lossy em Kotlin/R8, e **todo app Compose é Kotlin**. Foi essa combinação que produziu os `VerifyError` do `gh54` e os 18 `IncompatibleClassChangeError` no `DrawScope` do `gh62`. O caminho barato é o caminho que já se sabe que quebra nesta população.

**(c) Seletividade do ponto de entrada.** O pointcut `execution(...)` é degenerado no matcher (`PointcutMatcher.java:509-515`, casa qualquer método no índice 0) e `within(...)` é no-op (`:134-136`).

> **Emenda de 2026-08-06 — a conclusão original desta alínea estava errada.** O texto seguia daí para *"o alvo não pode ser expresso no descritor JSON — tem que ser código Java em um weaver novo (~100-150 linhas no molde do `CoverageWeaver`)"*. A inferência não se sustenta: ela generaliza de dois pointcuts para todos, e há um terceiro com casamento real. **`staticinitialization(<typePattern>)` filtra de fato** — `PointcutMatcher.matchStaticInit` (`:517-529`) compara o FQN da classe contra o padrão e expande `T+` pela hierarquia via `InheritanceResolver`; e o `DexWeaver` tem um pré-passe dedicado (`weaveStaticInit`, `:569-654`) que prepende no `<clinit>` existente ou sintetiza um pelo `StaticInitSynthesizer` para classes que não têm. Com `args` vazio, `deliversSignature` é falso e o emissor cai no `MonitorInvokeBuilder.buildInvoke` genérico — um `invoke-static` limpo, sem `ClassSignature` nem registrador extra.
>
> Logo `staticinitialization(dev.itsvic.parceltracker.MainActivity)` dá **um único sítio de costura, expresso inteiramente no descritor**. A consequência é sobre o custo do E1, não sobre o desenho: os dois arquivos do lado do tool (`ComposeProbeSourceEmitter`, `ComposeProbeWeaver`) saem do plano, e com eles o rebuild do fat jar — ver a emenda de 2026-08-06 no doc 5, §11.
>
> Uma ressalva de ordem, específica da Via A: o `<clinit>` não é apenas *aceitável* como alternativa ao `onCreate`, é **obrigatório**. Ver doc 5, §11.2.

---

## 12. O lado consumidor: o que o APE-RV precisaria

### 12.1 O ponto de estrangulamento é único

A chave `(activityBase, shortResourceId)` está materializada em dois lugares:

- `MopData.extractShortId()` — `MopData.java:1031-1035`, faz `"com.ex:id/btn" → "btn"` e **devolve `""` quando não há `:id/`**. É a raiz de todo o acoplamento.
- `widgetData: Map<String activityBase, Map<String shortResourceId, Widget>>` — `MopData.java:70`.

Seis sítios consomem essa chave, mas **cinco deles passam por duas funções** (`MopScorer.score` / `containmentShortIds` e `MopData.getWidget`), o que torna a troca cirúrgica **do lado do consumidor**:

| Sítio | Linha | O que faz |
|---|---|---|
| `MopScorer` | `:41`, `:66-86`, `:108-122`, `:142-173` | pontuação MOP, contenção, WTG, densidade por estado |
| `ApePromptBuilder` | `:452-458`, `:474-476`, `:578-585`, `:859-860` | marcador `[DM]`/`[M]`, metadados, contexto, fallback de identificador |
| `WtgPass` | `:56-57` | impulso por transição WTG |
| `FrontierPass` | `:71-72` | impulso de fronteira |
| `MopFrontierPass` | `:75-80` | fronteira MOP (descarta `shortId` vazio em `:76`) |
| `ApeAgent` | `:243-248` | escolha de gerador de texto tipado |

`MopScorer.scoreOpenMenu` (`:95-100`) é o **único sítio MOP que não depende de resourceID** — usa apenas o eixo activity.

### 12.2 O que não é cirúrgico

- **O descarte é anterior ao índice.** `MopData.java:435-445` elimina do índice todo widget estático sem `idName`. Uma identidade de composable exigiria uma **segunda estrutura de índice**, não uma reinterpretação da existente. (Nota de desenho já correta no código: `:429-434` marca `mopActivities` **antes** do descarte, e é por isso que o `activityHasMop` continua correto mesmo perdendo todos os widgets.)

  Duas ressalvas, para que esta linha não seja lida como a causa do colapso Compose:

  **Ela não é o que quebra Compose.** `droppedNoId=0` em 22/22 apps Compose (verificação, §1.2.1): o filtro de id nunca perdeu um widget flagged, porque o GATOR nunca emitiu nenhum. A barreira vinculante é do produtor — com o conjunto flagged vazio, `MopScorer.score` devolve 0 para qualquer par `(activity, shortId)` e o join por `resourceID` nem chega a ser exercitado. O descarte é barreira **latente**: real, e nunca alcançada. A prova é negativa e decisiva — dez apps View com 53%–96% de `resourceID` presente pontuam identicamente zero, pelo mesmo `flagged=0`.

  **Ela também não é comportamento herdado do APE.** `MopData` é adição do RVSEC (2026-03-12, `5dd6c80e`, gh4 Fase 3); o APE upstream não tem conceito de MOP. O APE original faz o contrário de descartar: `GUITreeBuilder.fillNode:629` grava `""` via `cacheStringEmptyOnNull` e **mantém o nó**, que segue entrando na abstração de estado (o `TypeNamer` o nomeia como o par `className` + `resourceID`, isto é, `(classe, "")`), gerando ações e sendo explorado. `resourceID` no APE é um atributo entre vários, nunca requisito de existência. O descarte, portanto, não retira nada da exploração — retira apenas a possibilidade de **casar** um nó de runtime com uma flag MOP estática, que é uma camada que só o RVSEC introduziu.
- **Não há por onde a identidade entrar em runtime.** O funil é `fillNode:629`, que lê exclusivamente `getViewIdResourceName()`. Para D2 seria preciso um campo novo em `GUITreeNode` e o espelhamento no caminho de replay XML (`buildNodeFromXml:522-562`, `fillElement:592-612`).

### 12.3 Um achado colateral que vale corrigir de qualquer forma

`MopData.isWidgetlessSubstrate()` (`:951-965`) — o gancho marcado no javadoc como *"No consumer yet"*, apontado no documento 2 como a costura natural para uma via alternativa de join — **não capturaria o caso Compose real**.

O predicado testa `windows[].widgets` (populado em `:472-477`, **sem filtro**), ou seja, **antes** do descarte por `idName` vazio de `:435-445`. Um app cujo GATOR encontrou widgets *todos sem resourceID* tem `widgetData` vazio mas `windows[].widgets` **não** vazio — e o predicado devolve `false`.

O mesmo vale para o knob `Config.llmPercentageNoSubstrate` (`Config.java:208-213`, default `-1`), também descrito como *"Seam only — no consumer yet"*. **Existem o detector e o knob de reação, e nenhum dos dois está ligado a nada — e o detector, como escrito, detectaria a coisa errada.** Isso é independente de todo o resto deste documento e deveria ser corrigido antes de qualquer uso dessa seam.

---

## 13. O obstáculo do canal

**Nenhum dos três documentos anteriores registra isto, e é a restrição de arquitetura mais dura do plano.**

Não existe canal em runtime entre o app instrumentado e o APE-RV. E a spec publicada do APE-RV **proíbe o canal óbvio**:

> `ape/openspec/specs/action-selection/spec.md:60` — *"APE SHALL NOT read from or write to logcat"*

Confirmado por varredura: "logcat" aparece uma única vez no Java do APE-RV, e é num comentário (`StatefulAgent.java:1486`) que justifica justamente a ausência do acoplamento. `sendBroadcast` existe mas é sempre **saída**. `ServerSocket` só no `MonkeySourceNetwork` legado. A proibição é reafirmada como non-goal em `ape/docs/PRD.md:667` e o escopo foi removido em `archive/2026-03-12-phase3-mop-awareness/design.md:67`.

O join `clock↔logcat` do item A9 **é offline e post-hoc**: emissão de `[APE-STEP] … clock=…` em `StatefulAgent.java:1493` e `:1521`, consumido depois do run por `aperv-tool/analysis/clock_logcat_join.py`. Não serve para decisão por passo.

**Consequência**: o item 5 da lista de validações do documento 3 ("acoplamento com o APE-RV") não é uma tarefa de engenharia — **é uma revogação de invariante publicada**. Precisa entrar na §17 e ser decidida como tal.

**O ponto de extensão de menor atrito** que encontrei é `applyXPathlets` (`GUITreeBuilder.java:89-125`): carrega `/sdcard/ape.xpath` na inicialização estática e pós-processa nós do DOM já construído, sobrescrevendo `resetActions`, `setExtraThrottle`, `setInputText` por nó. Não é canal em tempo real, mas é o **precedente já existente** de "artefato externo modifica o modelo de UI", e não viola a proibição de logcat. Um probe que escrevesse um arquivo lido no início de cada passo caberia nesse molde sem revogar nada — a latência e a granularidade precisariam ser medidas.

---

## 14. Riscos e ameaças à validade

| Risco | Natureza | Mitigação |
|---|---|---|
| **A informação não chega ao runtime** | mata a via inteira | E1 (§9), antes de tudo |
| **Custo de tempo por passo** | mata D1/D2 para decisão por passo | E1 mede; fallback é instantâneo por estado novo |
| **Instabilidade entre versões do Compose** | a trajetória do bitdrift é uma sequência de quebras (1.0.0, 1.5.4, 1.6.0) que os levou a abandonar a rota | medir a variação no corpus, não supor; o probe degrada graciosamente por ser reflexivo |
| **J2 não fecha** | mata D2, **não** mata D1 | mais uma razão para D1 primeiro |
| **Canal proibido por spec** | bloqueio de governança, não técnico | §13, §17 |
| **Efeito observador** | ameaça à validade de um experimento cujo desfecho é contagem de violações | braço de controle obrigatório; é o argumento mais forte contra D3 |
| **Os 12,7% sem `ui.tooling.data`** | tratamento desigual entre apps | injetar a biblioteca amplia a mudança; a diferença precisa ser reportada |
| **Minificação agressiva** | ameaça à generalidade | o corpus F-Droid não sofre (§4.4); um corpus da Play Store sofreria — **tem que constar em qualquer afirmação de generalidade na tese** |
| **Navigation 3** | ortogonal a esta via | não afeta D1/D2/D3, que não dependem de grafo de rotas — é uma vantagem desta via sobre a do grafo de rotas |
| **Re-análise do corpus** | 348 APKs, custo real | Fase 3, só depois de piloto |

Vale registrar a assimetria favorável: **a ameaça do Navigation 3, que condena a via do grafo de rotas, não toca esta via.** A informação de fonte é emitida pelo plugin do compilador, não pela biblioteca de navegação.

---

## 15. Plano em fases, com gates

| Fase | O que | Custo | Gate para prosseguir |
|---|---|---|---|
| **1 — E1** | probe reflexivo em 1 APK; medir presença e tempo | 1 arquivo Java + 1 run | FQNs aparecem **e** tempo < ~80 ms |
| **2 — Piloto D1** | tabela `FQN → reachesTarget` gerada offline para ~5 APKs (sem mexer no gator: extração por script sobre o dex); probe emite conjunto de composables ativos por estado; medir se o sinal **discrimina** telas dentro da mesma activity | dias | o sinal discrimina em ≥1 app onde `activityHasMop` é constante 1 |
| **3 — Produtor** | passe no `RvsecAnalysisClient`, seção nova no `.apk.json`, paridade de schema, re-análise do corpus | change OpenSpec própria; 348 APKs | Fase 2 mostrou discriminação |
| **4 — Consumidor** | segundo índice no `MopData`, novo `ScoringPass`, canal (§13) | change OpenSpec própria no repo `ape`; revogações da §17 | Fase 3 completa |
| **5 — Avaliação** | braço experimental com controle de efeito observador | corrida própria | — |

**A Fase 2 é deliberadamente offline e não toca no gator.** A tabela `FQN → reachesTarget` pode ser aproximada por script sobre o dex mais os dados de `reachability[]` que o `.apk.json` já tem — o suficiente para testar a hipótese de discriminação sem pagar a re-análise do corpus. Só se a Fase 2 passar é que a mudança no produtor se justifica.

---

## 16. Se E1 falhar

Não é um plano de contingência — é um resultado.

Se nem a via do tracer nem a da `CompositionData` produzirem FQNs em runtime, então **todas as cinco camadas de identidade do Compose foram testadas e nenhuma serve como chave de junção**: chave de grupo (não exposta), informação de fonte (não chega), `testTag` (prevalência 1,8%), texto (falta em 76,4% dos nós), rota de navegação (não existe em runtime).

Isso completa a série com uma afirmação forte e defensável — *"a guia por análise estática não é uma alternativa disponível em Compose, e eis a medida exaustiva disso"* — sustentada por números que, conforme o levantamento do documento 3, ninguém publicou: 0 de 629.417 ações impulsionadas; 76,4% de elementos sem identificador; 1,8% de uso de `testTag`; e agora a informação de fonte presente em 174/174 APKs mas inacessível em execução.

Como o documento 3 já argumenta (§9), um resultado negativo medido é mais honesto que uma técnica que funcionasse só no estrato minoritário.

---

## 17. Governança: o que precisaria ser revogado

**Nenhuma revogação é solicitada por este documento.** A lista existe para que a decisão seja tomada com o custo à vista.

| Decisão vigente | Fonte | Afetada por |
|---|---|---|
| "Não mexer no gator, salvo erro grosseiro; melhorias de substrato só por via offline/consumidor" | `20260729_propostas_melhorias_e3.md` §0 (2026-07-29) | Fase 3 |
| A change aberta do APE-RV exclui do escopo "anything in rvsec-gator" | `ape/openspec/changes/telemetry-proof-llm-efficacy/` | Fase 3 |
| *"APE SHALL NOT read from or write to logcat"* | `ape/openspec/specs/action-selection/spec.md:60` | Fase 4, **se** o canal for logcat |
| `INV-MOP-20` — widgets com `idName` vazio não são armazenados; casar por classe/texto/bounds está fora de escopo | spec `mop-guidance` | Fase 4 (D2) |

**As Fases 1 e 2 não afetam nenhuma delas** — não tocam no gator, não tocam no APE-RV, não criam canal. É outra razão para a ordem proposta.

`INV-ANA-16` (a exclusão `androidx.compose.*` no Soot, decisão D2 do `gh51`) **não** precisa ser revogada, pelo motivo da §10. Registro isto explicitamente porque a leitura intuitiva é a oposta: a decisão que "cegou" o gator para o Compose não é a que bloqueia esta via.

Não existe change OpenSpec ativa sobre Compose/gator. Se este plano avançar além da Fase 2, precisa de uma — e, pela convenção do projeto, de uma issue GitHub correspondente (`gh<N>-<nome-curto>`).

---

## 18. Método

- **Presença e formato da informação de fonte** (§4): parser próprio das seções `string_ids`/`string_data` do DEX (não `strings`, pelo motivo da §4), aplicado a todos os `classes*.dex` de 348 APKs de `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS`. Detecção de Compose por `Landroidx/compose/runtime/Composer` no pool. Padrões: `C\(…\)…\.kt#[a-z0-9]{4,}` e `FQN \(Arquivo\.kt:\d+\)`. Zero erros de parsing em 348.
- **Contagem de FQNs próprios** (§4.3): prefixo do FQN casado com o `applicationId` derivado do nome do arquivo. **É um piso** — 34 APKs deram zero por divergência entre applicationId e package do código, e dois foram verificados manualmente como falsos zeros (§3.2).
- **Sítios de chamada em smali** (§4.2): `java -cp lib/apktool/apktool.jar com.android.tools.smali.baksmali.Main d classes6.dex`, leitura direta de `MainActivityKt.smali` e `ComposableSingletons$*.smali` em `dev.itsvic.parceltracker_10501000.apk`.
- **Consumidor APE-RV** (§6, §12, §13): leitura de `MopData.java`, `MopScorer.java`, `MopWidgetPass.java`, `ApePromptBuilder.java`, `GUITreeBuilder.java`, `StatefulAgent.java`, `LlmTapAction.java`, `Config.java` em `/home/pedro/…/workspace-rv/ape`, mais varredura por canais (`logcat`, `Runtime.exec`, `ServerSocket`, `sendBroadcast`) e pelas specs em `ape/openspec/specs/`.
- **Pipeline de instrumentação** (§11): leitura de `BatchRunner.java`, `MonitorBuilder.java`, `MultidexMerger.java`, `CoverageWeaver.java`, `CoverageSourceEmitter.java`, `PointcutMatcher.java` em `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`, e dos wrappers Python em `modules/rv-instrumentation-dexlib2/` e `modules/rv-instrumentation-ajc/`.
- **Ressalvas conhecidas**: (a) nenhum APK do corpus está ofuscado, então o comportamento sob R8 agressivo é inferência (§4.4); (b) os elos de J2 (§6) são afirmações de API, **não** verificadas em execução; (c) presença de descritor no pool prova referência, não uso — mas para uma biblioteca que *nós* chamaríamos, referência é condição suficiente.

---

## 19. Fontes

As fontes bibliográficas desta via estão consolidadas em `20260731_sota_analise_estatica_compose.md` §11 e não são repetidas aqui. As mais diretamente relevantes a este desenho:

- [Implementing Session Replay in Android for Jetpack Compose — bitdrift](https://blog.bitdrift.io/post/implementing-session-replay-android-compose) — origem dos limiares de 80 ms / 800 ms da §9 e do histórico de quebras de API da §14.
- [androidx.compose.ui.tooling.data](https://developer.android.com/reference/kotlin/androidx/compose/ui/tooling/data/package-summary) — `asTree`, `mapTree`, `Group`, `NodeGroup`; base das afirmações de API de J2 (§6).
- [Stack traces in Compose](https://developer.android.com/develop/ui/compose/tooling/stacktraces) — `traceEventStart` e o mecanismo de tracing.
- [How Composition Works (AOSP)](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/compose/runtime/design/how-compose-works.md) — slot table, chaves de grupo, e a relação com `sourceInformationMarkerStart` (§4.2).

---

## 20. Documentos relacionados

**A série gator × Compose**
- `20260730_compose_gator_substrato_estatico.md` — diagnóstico: por que a WTG colapsa; as quatro opções originais; a recomendação de estratificação.
- `20260731_gator_compose_viabilidade.md` — as quatro vias testadas e reprovadas; o zero de 629.417; a assimetria produtor/consumidor.
- `20260731_sota_analise_estatica_compose.md` — o estado do campo; as cinco camadas de identidade; a abertura desta via.

**Antecedentes empíricos**
- `20260708_investigacao_formas_guiar_mop.md` — primeira caracterização quantitativa do colapso do substrato.
- `20260708_invmop_compose_per_app.tsv` — dataset por app (219 linhas) que serve de base às medições posteriores.
- `20260731_analise_percepcao_e_telemetria.md` e `20260731_verificacao_analise_percepcao.md` — o lado runtime: cobertura de identificador, `flagged=0` em 22/22 apps Compose.

**Decisões e planejamento**
- `20260729_propostas_melhorias_e3.md` §0 — a regra vigente sobre o gator; §8 — F1/F6/F7, N1/N6/N7, B9.
- `20260730_preregistro_corrida_decisiva.md` §4 — a estratificação por toolkit como previsão registrada antes do dado.
- `20260802_resultados_corrida_decisiva.md` — a confirmação: 22 Compose / 18 View, zero pares discordantes no estrato Compose.
- `20260802_a9_atribuicao_temporal_violacoes.md` — o join `clock↔logcat` offline, referência da §13.

**Artefatos OpenSpec**
- `openspec/changes/archive/2026-05-05-gh51-gator-soot-upgrade/` — decisão D2 e `INV-ANA-16`; a exclusão `androidx.compose.*` e seu racional original.
- `openspec/changes/archive/2026-08-02-gh90-e3-decisive-run-setup/` — o detector de estrato Compose como eixo pré-registrado.
- `openspec/changes/gh78-state-identity-robustness/` — item S7, fallback perceptual para árvores degeneradas: o eixo runtime/percepção do mesmo problema.
- `ape/openspec/changes/telemetry-proof-llm-efficacy/` — change aberta do APE-RV; exclui o gator do escopo.

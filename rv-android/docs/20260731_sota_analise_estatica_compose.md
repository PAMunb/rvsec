# Estado da arte: análise estática de UI no Android moderno (Compose)

**Data**: 2026-07-31
**Escopo**: como o campo — pesquisa acadêmica, ferramentas industriais e o próprio Google — trata análise estática e identificação de elementos em UI declarativa; como (e se) identidades/IDs são criados em Jetpack Compose; e o que disso é aplicável ao `rvsec-gator` + APE-RV.
**Status**: revisão do estado da arte com medições próprias de confronto no corpus. Nenhuma decisão tomada.
**Terceiro de três documentos** sobre gator × Compose, para a decisão final:
1. `20260730_compose_gator_substrato_estatico.md` — *por que* a WTG colapsa (diagnóstico).
2. `20260731_gator_compose_viabilidade.md` — *o que dá para fazer* dentro do nosso desenho atual (quatro saídas testadas, todas reprovadas).
3. **este** — *o que o mundo faz*, e qual opção isso abre que não estava na mesa.

---

## 1. Sumário executivo

Sete achados, os de numeração ímpar vindos da literatura/documentação e os pares de medições próprias sobre os 110 APKs Compose do corpus:

1. **Não existe, na literatura nem na indústria, nenhuma ferramenta que extraia estrutura de UI Compose a partir de um APK.** Toda análise estática de Compose que existe opera sobre **código-fonte** — regras de lint (`compose-rules`), processadores de anotação (KSP: Compose Destinations, `compose-nav-graph`). O elo "APK → modelo de UI" simplesmente não foi construído para Compose por ninguém. Isso não é um atraso nosso; é uma lacuna do campo.
2. **O Compose não deixou de criar identidade — ele a moveu para fora do alcance da árvore de acessibilidade.** Medido: 110/110 apps do corpus carregam no bytecode o nome totalmente qualificado + arquivo:linha de uma **mediana de 424** composables próprios (`traceEventStart`/`sourceInformation` do plugin do compilador). A identidade existe, é rica e é estável — mas vive na *composição*, não no nó de acessibilidade.
3. **A ponte oficial entre as duas (`testTagsAsResourceId`) é um remendo de compatibilidade com ferramentas legadas**, e a documentação da AOSP diz isso com todas as letras: `testTag`s vão **sempre** para os `extras` do `AccessibilityNodeInfo`; o mapeamento para resource-id existe porque *"o UIAutomator foi escrito antes de `extras` existir"*.
4. **Mas no nosso corpus não há `testTag` para ler.** Medido por desmontagem: `Modifier.testTag` em **0 de 110** apps; a grafia alternativa `semantics { testTag = ... }` em **2 de 110 (1,8%)**. E os 5 apps que habilitam `testTagsAsResourceId` (§4 do doc 2) **não marcam nada** — o flag deles é inócuo. A via dos `extras`, apesar de sempre ligada, não tem o que ler.
5. **O campo, diante disso, seguiu três caminhos — nenhum deles estático-sobre-APK**: introspecção *dentro do processo* (Layout Inspector, session replay), a árvore de *semantics* via acessibilidade (UiAutomator/Appium), e **visão computacional/VLM**, explicitamente adotada para contornar árvores de acessibilidade "inconsistentes e incompletas".
6. **A rota de introspecção em processo está tecnicamente disponível no nosso corpus.** Medido: `CompositionData` (runtime) presente em **110/110**; `androidx.compose.ui.tooling.data` (as APIs `asTree`/`mapTree` que o Layout Inspector usa) embarcado em **96/110 (87,3%)**; arquivos de versão em `META-INF` em 104/110.
7. **E é a única rota que fecha o join que os documentos 1 e 2 mostraram impossível** — porque a identidade do composable (FQN + arquivo:linha) existe **dos dois lados**: no bytecode (achado 2) e na composição em runtime (achado 6). Nenhuma das chaves testadas até aqui — resource-id, texto, saco de textos — tinha essa propriedade.

A consequência de desenho é que a pergunta muda. Não é mais *"como fazer o gator entender Compose"* — é ***"o substrato de runtime certo é a árvore de acessibilidade ou a composição?"***. E, ao contrário de uma ferramenta de caixa-preta, **nós já reempacotamos o APK** no pipeline de instrumentação, o que torna a segunda opção arquiteturalmente acessível para nós. Riscos e o que precisa ser validado antes de qualquer decisão estão na §8.

---

## 2. O tamanho do problema

Vale fixar a escala, porque ela determina se isto é um nicho ou o caso central:

- **60% dos 1.000 apps mais baixados** da Play Store usam Compose (2025), contra 40% em maio/2024 e 16% em outubro/2022.
- **Mais de 75% dos novos apps** de produção nascem em Compose; **78% dos desenvolvedores profissionais** o usam como toolkit principal (contra 49% em 2023).
- No Google I/O 2026, o Google declarou-se **"Compose-first"**: todo desenvolvimento futuro de UI acontece em Compose, e o toolkit de Views entra em **modo de manutenção**.

No nosso corpus a proporção é 110/181 (60,8%) — coerente com o ecossistema. A conclusão para a tese é que o estrato Compose não é uma exceção a ser tratada à parte: é a trajetória do Android, e qualquer técnica que dependa do sistema de Views tem prazo de validade declarado pelo fornecedor da plataforma.

---

## 3. Como (e se) o Compose cria identidade

Esta é a pergunta central do pedido, e a resposta é que **existem cinco camadas de identidade**, com propriedades muito diferentes. Confundi-las é o que gera a impressão de que "Compose não tem ID".

### 3.1 Chave de grupo / memoização posicional — identidade interna do runtime

O plugin do compilador atribui a **cada sítio de chamada** de composable um inteiro único, passado ao `$composer`, e o runtime usa esse inteiro como chave de grupo na *slot table*. É literalmente um ID gerado pelo compilador — a identidade não vem do nome, vem da **posição na árvore de execução** ("positional memoization"), mais blocos `key()` explícitos quando o desenvolvedor precisa desambiguar itens de lista.

Propriedades: determinístico, estável entre execuções do mesmo binário, presente em 100% dos composables. **Mas é um inteiro sem semântica externa** — só faz sentido dentro da slot table daquele processo, e não é exposto a nada fora do runtime do Compose.

### 3.2 Informação de fonte — nome do composable + arquivo:linha

O mesmo plugin emite, junto, duas famílias de constantes de string:

- `sourceInformation`: `"C(AddEditParcelView)P(2)58@2485L52,…:AddEditParcelView.kt#abgzwg"`
- `traceEventStart`: `"dev.itsvic.parceltracker.ui.views.AddEditParcelView (AddEditParcelView.kt:55)"`

É a camada mais rica: dá **nome totalmente qualificado, arquivo e linha** de cada composable. É o que alimenta o Layout Inspector e os *stack traces* do Compose.

Ressalva importante do histórico da API: desde o Compose 1.5.4 a informação de fonte passou a ser controlada por flag do compilador, e no 1.6.0 a coleta migrou para uma *side table* desligada por padrão — o time do bitdrift documentou essa migração como o motivo de abandonarem a rota. **Medição própria contrariando a leitura pessimista disso: os marcadores estão presentes em 110/110 APKs do corpus**, com mediana de 424 composables não-biblioteca distintos por app (p25=294, p75=701, máx=1825). Ou seja: no material que analisamos, a informação está lá. O que a mudança de 1.6.0 afeta é se ela é *coletada na slot table em runtime* — questão separada, e que a §8 lista como o experimento que precisa ser feito.

### 3.3 `testTag` — identidade opcional, posta pelo desenvolvedor

`Modifier.testTag("x")` é o sucessor funcional do `android:id`, e a documentação de acessibilidade da AOSP é explícita sobre como ele é exposto:

> *"testTags are always provided in AccessibilityNodeInfo `extras`."*
> *"testTag's use in UIAutomator is also why testTag-only nodes aren't fully pruned from the AccessibilityNodeInfo tree, but marked unimportant instead."*

E sobre por que existe o `testTagsAsResourceId`:

> o UIAutomator *"was written before `extras` existed so unfortunately some versions of it have no matcher for this type of AccessibilityNodeInfo property"*.

Isto corrige uma premissa que carreguei no documento 2: **o `testTag` não depende do opt-in para existir na árvore de acessibilidade** — ele está sempre nos `extras`, com a chave `androidx.compose.ui.semantics.testTag`. O opt-in só o duplica no campo `viewIdResourceName` para clientes que não sabem ler `extras`. Como o APE-RV percorre `AccessibilityNodeInfo` diretamente, ele poderia ler os `extras` sem nenhum opt-in do app.

**O que anula essa saída é a prevalência, não o mecanismo** (§5): praticamente ninguém usa `testTag` em produção — e há um debate ativo na comunidade defendendo que *não se deve* usá-lo, por ser poluição de código de teste dentro do código de produção.

### 3.4 Semantics de acessibilidade — texto, content-description, `Role`

A camada que o UiAutomator enxerga: `text`, `contentDescription`, e o `Role`, que o Compose traduz para o campo `className` do `AccessibilityNodeInfo` (`Role.Button` → `android.widget.Button`, `Role.Checkbox` → `android.widget.CheckBox`). A razão é compatibilidade: *"o TalkBack ainda procura classes de View específicas, então o Compose simplesmente mapeia papéis para classes de View"*.

Isso explica exatamente a distribuição que medimos no documento 2: elementos **sem `Role` declarado** caem em `android.view.View` genérica — 54% dos elementos acionáveis do estrato Compose, com 2,5% de cobertura de texto. Não é uma anomalia do nosso corpus; é o comportamento documentado do mapeamento.

### 3.5 Rota de navegação — identidade de tela

Com Navigation-Compose, cada destino tem uma rota: string (`"detalhe/{id}"`) ou, desde a versão 2.8, uma **classe `@Serializable`** (type-safe). É a identidade de tela mais próxima do que a WTG modela — e a única das cinco camadas que o gator poderia extrair com o ferramental que já tem (documentado no doc 2, §4.2–4.3).

**Mas ela tem prazo de validade curto.** O **Navigation 3**, lançado no fim de 2025, abandona o modelo dirigido por grafo: `NavHost` vira `NavDisplay`, e navegar deixa de ser `NavController.navigate(rota)` para se tornar **mutação direta de uma lista de estado** gerenciada pelo desenvolvedor. Ou seja: a chamada que serviria de âncora estática deixa de existir. Qualquer investimento em extração de grafo de rotas nasce com data de obsolescência marcada pela própria plataforma.

### 3.6 Síntese: qual identidade existe de cada lado

| camada | existe no bytecode (estático) | existe em runtime | onde é legível em runtime |
|---|---|---|---|
| chave de grupo (inteiro do compilador) | sim (constantes) | sim | só dentro da slot table |
| **FQN + arquivo:linha** | **sim (110/110, mediana 424)** | **sim** | **composição, via `CompositionData` — em processo** |
| `testTag` | sim, se o app usar (**1,8%**) | sim | `AccessibilityNodeInfo.extras` — sempre |
| texto / content-description | parcial (`stringResource`) | parcial (**23,6%**) | árvore de acessibilidade |
| `Role` → `className` | sim | sim | árvore de acessibilidade (grosseiro) |
| rota de navegação | sim (**68,2%**, obsolescendo) | não diretamente | — |

A linha em negrito é a única com "sim" forte nas duas colunas. **É esse o achado que reabre o problema.**

---

## 4. Estado da arte da análise estática de GUI Android — e onde ela quebra

### 4.1 A linhagem em que o nosso gator está

O `rvsec-gator` descende do GATOR e da **WTG** (*Static Window Transition Graphs for Android*, ASE 2015 / journal 2018), que modela sequências de janelas com seus eventos e callbacks. A linhagem é bem estudada, e suas limitações também: análises baseadas nela herdam **call graph insensível a contexto**, e o GATOR usa *over-approximation* com **weak updates** ao associar IDs de widget a callbacks. O **ProMal** (ICSE 2022) é a resposta mais recente dentro do paradigma — WTGs mais precisas combinando análise estática, análise dinâmica e aprendizado de máquina.

### 4.2 O quanto essa família erra, medido por terceiros

Três resultados recentes delimitam o teto do paradigma, e nenhum deles depende de Compose:

- **Soundness de call graph** (ISSTA 2024, Samhi et al.): 13 ferramentas de análise estática sobre 1.000 apps deixam de capturar, em média, **61% dos métodos executados dinamicamente**. As causas apontadas incluem chamadas implícitas, callbacks do framework, reflexão e **lambdas de Kotlin** — precisamente o mecanismo em que o Compose registra handlers.
- **Geração de ATG** (TOSEM 2025, *Activity Transition Graph Generation: How Far Are We?*): benchmark manual de 98 apps contra 7 ferramentas; elas reportam transições incorretas **e** omitem transições, e não concordam entre si. A união das ferramentas reduz omissões ao custo de mais transições incorretas.
- **A "maldição dos 30%"** (ICSE 2025, Akinotcho et al.): mesmo as melhores técnicas de exploração dirigida por GUI cobrem cerca de **30%** de um app real, e o trabalho se dedica a investigar "os 70% restantes".

Ou seja: mesmo em apps de Views, o substrato estático de GUI já era um instrumento com erro grande e bem documentado. O Compose não introduz um problema novo em uma técnica sadia — ele leva ao limite uma técnica que já operava com folga estreita.

### 4.3 A afirmação que importa: ninguém analisa Compose a partir do APK

Buscando explicitamente por trabalho que extraia estrutura de UI Compose de binários, o resultado é negativo. O que existe é:

- **Análise estática de Compose sobre código-fonte**: `compose-rules` (regras ktlint/detekt para boas práticas), `detekt`, `konsist`. São *linters* de estilo e arquitetura, não extratores de modelo de UI.
- **Extração de grafo de navegação em tempo de build**: `Compose Destinations` (KSP, gera destinos tipados) e `skydoves/compose-nav-graph` (plugin Gradle + KSP que **extrai o grafo de navegação estaticamente** e renderiza miniaturas de cada tela sem emulador). Este último é o que mais se aproxima do que a WTG faz — **mas exige o código-fonte e anotações no app**, o que é inaplicável a APKs de terceiros.
- **Transpilação XML → Compose** (`GUIMigrator`, arXiv 2409.16656): faz o caminho inverso ao nosso — lê layouts XML e gera árvores declarativas.
- **Fora do Android**: o `ArkAnalyzer` (arXiv 2501.05798) é um framework de análise estática para ArkTS/OpenHarmony, cuja UI (ArkUI) é declarativa como o Compose — sinal de que o problema é reconhecido em outra plataforma, embora eu não tenha conseguido extrair do PDF os detalhes de como (ou se) ele modela a UI.

Nenhum desses fecha o elo APK → modelo de UI Compose. Isso é, ao mesmo tempo, uma justificativa para o esforço e um alerta: se ninguém fez, provavelmente não é porque ninguém pensou.

---

## 5. Como o campo realmente resolve o problema hoje

Quatro famílias, e é instrutivo que **nenhuma seja análise estática de binário**.

### 5.1 Instrumentação em tempo de build (fonte)

KSP/anotações geram metadados de navegação e telas antes de compilar. Preciso e barato — e **indisponível** para quem analisa APK de terceiros. É a solução de quem controla o código.

### 5.2 Introspecção dentro do processo

É como o **Layout Inspector** do Android Studio funciona: ele lê a hierarquia real de composables em execução, com atributos resolvidos e contagem de recomposições. O mecanismo é a `CompositionData` do runtime, interpretada pelas APIs de `androidx.compose.ui.tooling.data` (`asTree`, e depois `mapTree`, introduzida no 1.3.0-alpha02 com ganho de ~10× em desempenho).

O melhor relato público de aplicar isso **em produção** é o do **bitdrift**, implementando *session replay* para Compose. Vale ler a trajetória inteira porque ela é o mapa dos riscos:

1. Começaram com reflexão sobre `CompositionData.asTree()` — funcionava, mas **~800 ms** para UIs moderadamente complexas e frágil por depender de reflexão.
2. Migraram para `mapTree()` (~10× mais rápido).
3. Apanharam de três mudanças sucessivas da API: regra `-assumenosideeffects` do ProGuard removendo informação de fonte (1.0.0); flag de compilador tornando `sourceInformation` opt-in (1.5.4); migração para *side table* desligada por padrão (1.6.0), exigindo chamar `collectParameterInformation()` de dentro da composição.
4. **Abandonaram a rota** e passaram a usar a árvore de semantics (`AndroidComposeView.semanticsOwner.unmergedRootSemanticsNode`), que descreveram como *"significativamente mais simples e menos frágil"*, com desempenho de **milissegundos de um dígito**.

O veredito deles é honesto e precisa ser levado a sério — mas o caso de uso era diferente do nosso: replay contínuo de tela inteira em alta frequência, contra um instantâneo por estado explorado.

### 5.3 Árvore de semantics via acessibilidade

O caminho do UiAutomator, do Appium e — hoje — do APE-RV. É a via oficialmente suportada para automação externa, e a documentação do Google é direta sobre seu custo: *"por padrão, composables são acessíveis a partir do UiAutomator apenas por seus descritores convenientes (texto exibido, content description, etc.)"*. Para chegar ao `testTag` é preciso ou o opt-in `testTagsAsResourceId` (clientes legados) ou ler os `extras` (clientes modernos) — e o ecossistema de automação levou anos nisso: as issues do Appium sobre Compose vêm desde 2021 e a de expor `testTag` a partir dos `extras` seguia aberta.

### 5.4 Visão computacional / VLM

A tendência mais clara de 2025–2026, e a mais relevante para nós porque **é explicitamente motivada pelo nosso problema**. A literatura de teste de GUI com LLM adota reconhecimento visual de widget *em lugar* da extração por layout, justificando que "widgets em objetos Canvas ou páginas híbridas podem ser inacessíveis à análise de layout" e que se quer uma representação "*what-you-see-is-what-you-get*". O discurso da indústria é mais forte: a árvore de acessibilidade é "inconsistente, frequentemente incompleta e muda entre versões do SO", e modelos de visão a contornam por completo.

O APE-RV já tem um pé aqui: o `LlmTapAction` existe exatamente para agir sobre elementos fora da árvore, e o comentário no código já nomeia o caso — *"game canvas, Compose-without-semantics, custom view"*.

### 5.5 Nota lateral: deep links como substrato de alcance

Uma quinta via, ortogonal, que resolve *alcance de telas* sem modelo de GUI: o **Delm** (TOSEM 2024) integra deep links ao Monkey, usando ATG extraída com IC3/Soot para saltar direto a activities de difícil acesso. Mencionado porque é o tratamento mais barato para o problema que o B9 queria resolver — e porque, em app Compose single-activity, deep links de navegação são declarados no `NavHost` e continuam sendo um alvo estático plausível.

---

## 6. Confronto com o nosso corpus

O que a revisão obriga a medir, e o que a medição respondeu (110 APKs Compose; método na §9):

| pergunta levantada pela revisão | medição | resultado |
|---|---|---|
| O `testTag` está sempre nos `extras`? (§3.3) | documentação AOSP | **sim** — não precisa de opt-in |
| Então os apps usam `Modifier.testTag`? | desmontagem, sítios de chamada | **0 / 110 (0,0%)** |
| E a grafia `semantics { testTag = ... }`? | desmontagem | **2 / 110 (1,8%)** |
| Os 5 apps com `testTagsAsResourceId` marcam algo? | desmontagem, todas as classes | **nenhum** — flag inócuo |
| A informação de fonte sobrevive nos APKs? | pool de strings dos dex | **110 / 110 (100%)** |
| Quantos composables próprios são identificáveis? | FQNs não-biblioteca distintos | **mediana 424** (p25 294, p75 701) |
| As APIs de tooling estão embarcadas? | descritores no dex | `CompositionData` **110/110**; `ui.tooling.data` **96/110 (87,3%)** |

Três leituras:

- **A via dos `extras` está aberta e vazia.** Corrigi uma premissa errada do documento 2 (o `testTag` não depende do opt-in), e a correção não muda a conclusão: com 1,8% de apps marcando qualquer coisa, não há o que ler. O motivo é cultural, não técnico — `testTag` é afordância de teste, e a comunidade desaconselha seu uso em produção.
- **A informação de fonte, ao contrário, está presente em todo o corpus e é abundante.** Uma mediana de 424 composables identificáveis por app é substrato de sobra — é *mais* granular que a lista de activities que hoje sustenta o `activityHasMop`.
- **E o ferramental para lê-la em runtime já vem embarcado em 87,3% dos APKs**, sem precisarmos injetar biblioteca nenhuma nesses casos.

---

## 7. A opção que isto abre e que não estava na mesa

Os documentos 1 e 2 fecharam quatro vias, todas com a mesma estrutura de falha: **a chave de join não existia dos dois lados**. Resource-id não existe em Compose; texto existe estaticamente mas falta em 76,4% dos nós de runtime; saco de textos por tela não discrimina (topo-1 de 10,4%); `testTag` está disponível mas ninguém o usa.

A identidade de composable é a primeira chave que **existe integralmente dos dois lados**:

- **Lado estático**: o gator lê os `const-string` de `traceEventStart` e associa cada composable ao seu FQN, arquivo e linha — e, pelo call graph que já constrói, a quais alvos JCA ele alcança. É a mesma varredura de bytecode do doc 2, §3, sem levantar a exclusão do Soot.
- **Lado runtime**: um leitor da `CompositionData` devolve a árvore de composables em execução com nome e posição de fonte — a mesma informação que o Layout Inspector mostra.

O join deixa de ser inferência (casar texto com texto) e passa a ser **igualdade de identificador**.

E há uma assimetria a nosso favor que uma ferramenta de caixa-preta não tem: **o nosso pipeline já reempacota o APK**. Instrumentação (`rv-instrumentation-dexlib2`/`ajc`) é o núcleo do RVSEC — injetar um pequeno leitor de composição é a mesma classe de operação que já fazemos para injetar monitores. O que para o Appium seria impossível, para nós é uma variação do que já existe.

**Isto não é uma recomendação de implementar.** É a identificação da única via que sobrevive à análise, e ela vem com uma lista de coisas que precisam ser verificadas antes de qualquer decisão — §8.

---

## 8. O que precisa ser validado antes de decidir

Em ordem de poder de refutação. Os três primeiros são baratos e respondem "isto funciona?" antes de qualquer investimento.

1. **A informação de fonte é coletada na slot table em runtime, ou só existe como constante no dex?** É *a* pergunta. Medimos que as strings estão em 110/110 APKs, mas a mudança do Compose 1.6.0 (side table desligada por padrão) pode significar que elas nunca chegam à `CompositionData` em execução. Experimento: um app do corpus, leitura de `CompositionData` em runtime, verificar se os nomes aparecem. Se não aparecerem, **a via cai inteira** e não sobra nenhuma.
2. **Custo em tempo.** O bitdrift mediu ~800 ms com `asTree()` e ~80 ms com `mapTree()` para UIs moderadamente complexas. O APE-RV toma decisão por passo; 80 ms por estado é aceitável, 800 ms não é. E o número deles vem de UIs de produção, provavelmente mais pesadas que a mediana do corpus.
3. **Estabilidade entre versões do Compose.** A trajetória do bitdrift é uma sequência de quebras (1.0.0, 1.5.4, 1.6.0) que os levou a abandonar a rota. O corpus tem versões heterogêneas de Compose; a variação precisa ser medida, não suposta.
4. **Os 12,7% sem `ui.tooling.data`.** Nesses APKs seria preciso injetar a biblioteca no reempacotamento — factível, mas amplia a mudança de instrumentação e cria uma diferença de tratamento entre apps que precisa ser reportada.
5. **Acoplamento com o APE-RV.** O leitor rodaria dentro do processo do app; o APE-RV roda fora. Seria preciso um canal (log, arquivo, socket) e um join por instante de tempo com o passo de exploração — a mesma classe de problema do "clock↔logcat join" que já existe no A9.
6. **Efeito observador.** Injetar código que percorre a composição a cada passo altera o comportamento do app sob teste. Para um experimento cujo desfecho é contagem de violações, isso é ameaça à validade que precisa de braço de controle.

E duas ameaças estruturais, que valem para qualquer via:

- **Navigation 3** elimina `NavController.navigate()` em favor de mutação de estado (§3.5). Qualquer extração de grafo de rotas tem obsolescência anunciada.
- **Minificação agressiva** apaga tanto os nomes de classe do AndroidX quanto a informação de fonte. O corpus F-Droid não sofre disso (medimos 110/110 com descritores íntegros), mas um corpus de apps da Play Store sofreria — e isso precisa constar em qualquer afirmação de generalidade na tese.

---

## 9. A lacuna de pesquisa

Vale registrar explicitamente, porque é o enquadramento que o documento 3 acrescenta aos dois anteriores.

O campo tem: análise estática madura para UI baseada em Views (GATOR/WTG, IC3, FlowDroid) com limites bem medidos; análise estática de Compose **sobre código-fonte** (lint, KSP); e uma virada recente para **visão/VLM** motivada justamente pela insuficiência da árvore de acessibilidade. O que não tem é **qualquer ponte entre APK Compose e modelo de UI** — nem estática, nem híbrida.

Isso significa que a conclusão negativa dos documentos 1 e 2 **não é um fracasso local**: é o estado do campo, e nós o medimos com números que ninguém publicou (0 de 629.417 ações impulsionadas; 76,4% de elementos sem identificador; 1,8% de uso de `testTag`). Como resultado de tese, "a guia por análise estática não é uma alternativa disponível em Compose, e eis a medida disso" é uma contribuição defensável — e mais honesta que uma técnica que funcionasse só no estrato minoritário.

A via da §7, se validada, seria a primeira ponte. Se não for validada, o resultado negativo já está sustentado por medição, e a resposta de engenharia é o substrato observado, como o documento 2 concluiu.

---

## 10. Método

- **Revisão**: buscas na web em 2026-07-31 sobre análise estática de Compose, extração de modelo de GUI, identidade/IDs em UI declarativa, ferramentas de automação (UiAutomator/Appium), introspecção em runtime (Layout Inspector, `ui-tooling`), e literatura recente de teste de GUI (ISSTA 2024, ICSE 2025, TOSEM 2024/2025). Fontes na §11. Duas leituras ficaram bloqueadas por extração de PDF (`ArkAnalyzer`, ICSE 2025 "30% curse") e estão citadas apenas pelo que consta de páginas de resumo — marcadas como tal no texto.
- **`Modifier.testTag` e `semantics { testTag = }`** (§6): desmontagem com baksmali (embutido no `apktool.jar`) dos 110 APKs Compose; filtros em cascata (dex sem a agulha descartado → `baksmali list classes` → `baksmali d --classes` só das classes fora de prefixos de biblioteca); regex `^\s+invoke-\S+.*->testTag\(` e `->setTestTag\(`. Regex testada contra amostras sintéticas das duas formas de `invoke`; controle positivo real obtido em `com.nononsenseapps.feeder` (8 sítios, literais como `card_image`), o que prova que o zero da outra forma é zero de verdade. Script `needle_scan.py` no scratchpad.
- **Informação de fonte** (§3.2, §6): varredura dos pools de strings dos `.dex` com `C\([A-Za-z0-9_]+\)…\.kt#[a-z0-9]{4,}` (sourceInformation) e `FQN \(Arquivo\.kt:\d+\)` (traceEventStart); contagem de FQNs distintos após excluir prefixos de biblioteca (`androidx.`, `kotlin*`, `com.google.`, `coil*`, `org.jetbrains.`, `dagger.`, `okhttp3.`, `io.ktor.`, `com.squareup.`). **Ressalva**: uma primeira tentativa de atribuir FQNs ao pacote do app pelo nome do arquivo do APK deu 71,8% e foi descartada — o nome do arquivo não é o pacote de código (o mesmo problema que motiva a remoção do `PackageDetector`); os apps com "0 próprios" tinham centenas de FQNs não-biblioteca. A medida reportada usa "não-biblioteca", que não depende dessa atribuição.
- **Bibliotecas de tooling embarcadas** (§6): presença dos descritores `Landroidx/compose/ui/tooling/data/`, `Landroidx/compose/runtime/tooling/CompositionData;`, `Landroidx/compose/ui/semantics/SemanticsOwner;` no pool dos dex, e de arquivos `META-INF/androidx.compose*`. **Ressalva conhecida**: presença no pool prova referência, não uso — mas para uma biblioteca que *nós* chamaríamos, referência é a condição suficiente.
- Corpus: os 110 APKs Compose de `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS` (detecção por `Landroidx/compose/runtime/Composer;` no pool dos dex).

---

## 11. Fontes

**Identidade e semantics em Compose**
- [Compose accessibility implementation notes (AOSP)](https://android.googlesource.com/platform/frameworks/support/+/androidx-main/compose/ui/ui/src/androidMain/kotlin/androidx/compose/ui/platform/accessibility/android_a11y_implementation_notes.md) — fonte primária do "testTags are always provided in AccessibilityNodeInfo extras".
- [Interoperability | Jetpack Compose testing (Android Developers)](https://developer.android.com/develop/ui/compose/testing/interoperability) — `testTagsAsResourceId`, escopo e caveats de `By.res`.
- [testTag — Compose UI docs](https://composables.com/docs/androidx.compose.ui/ui/properties/testTag) — chave `androidx.compose.ui.semantics.testTag` nos extras.
- [Accessing Composables from UiAutomator (Android Developers)](https://medium.com/androiddevelopers/accessing-composables-from-uiautomator-cf316515edc2)
- [Semantics | Jetpack Compose](https://developer.android.com/develop/ui/compose/accessibility/semantics) · [Role Semantics in Jetpack Compose — Bryan Herbst](https://bryanherbst.com/2021/02/19/compose-role-semantics/) · [Deque: how accessibility services interact with Compose](https://www.deque.com/blog/building-accessible-android-apps-with-jetpack-compose-how-accessibility-service-interacts-with-jetpack-compose/) — mapeamento `Role` → `className`.
- [How Composition Works (AOSP design doc)](https://android.googlesource.com/platform/frameworks/support/+/refs/heads/androidx-main/compose/runtime/design/how-compose-works.md) · [Positional memoization — Jorge Castillo](https://newsletter.jorgecastillo.dev/p/positional-memoization-in-jetpack) — chaves de grupo e slot table.
- [Stop Using Test Tags in Production Code — Tomáš Repčík](https://tomasrepcik.dev/blog/2024/2024-02-13-test-tags-and-sematics/) — o debate que explica a prevalência de 1,8%.

**Introspecção em runtime**
- [Implementing Session Replay in Android for Jetpack Compose — bitdrift](https://blog.bitdrift.io/post/implementing-session-replay-android-compose) — o relato mais completo de `asTree`/`mapTree`, as quebras de API e a migração para semantics.
- [Debug your Compose UI / Layout Inspector](https://developer.android.com/develop/ui/compose/tooling/debug) · [androidx.compose.ui.tooling.data](https://developer.android.com/reference/kotlin/androidx/compose/ui/tooling/data/package-summary) · [Stack traces in Compose](https://developer.android.com/develop/ui/compose/tooling/stacktraces)

**Análise estática de GUI Android e seus limites**
- [Static Window Transition Graphs for Android (ASE 2015)](http://lilicoding.github.io/SA3Repo/papers/2015_yang2015static2.pdf) · [versão journal](https://link.springer.com/article/10.1007/s10515-018-0237-6) — a linhagem do nosso gator.
- [ProMal: Precise Window Transition Graphs for Android (ICSE 2022)](https://xusheng-xiao.github.io/papers/promal_icse_cr.pdf)
- [Call Graph Soundness in Android Static Analysis (ISSTA 2024)](https://arxiv.org/abs/2407.07804) — 61% dos métodos executados não capturados.
- [Activity Transition Graph Generation: How Far Are We? (TOSEM 2025)](https://dl.acm.org/doi/10.1145/3776553)
- [Mobile Application Coverage: The 30% Curse and Ways Forward (ICSE 2025)](https://conf.researchr.org/details/icse-2025/icse-2025-research-track/91/Mobile-Application-Coverage-The-30-Curse-and-Ways-Forward)
- [Enhancing GUI Exploration Coverage with Deep Link-Integrated Monkey (TOSEM 2024)](https://dl.acm.org/doi/full/10.1145/3664810)
- [ArkAnalyzer: The Static Analysis Framework for OpenHarmony](https://arxiv.org/pdf/2501.05798) — UI declarativa fora do Android.
- [GUIMigrator: XML → Compose/SwiftUI](https://arxiv.org/pdf/2409.16656)

**Análise estática de Compose (sobre fonte) e navegação**
- [Compose Rules — regras ktlint/detekt](https://www.linuxlinks.com/compose-rules-static-analysis-rules-jetpack-compose-project/)
- [skydoves/compose-nav-graph](https://github.com/skydoves/compose-nav-graph) — extração estática de grafo de navegação em tempo de build.
- [raamcosta/compose-destinations](https://github.com/raamcosta/compose-destinations) — KSP, destinos tipados.
- [Navigation 3 (Android Developers)](https://developer.android.com/guide/navigation/navigation-3) · [Announcing Jetpack Navigation 3](https://android-developers.googleblog.com/2025/05/announcing-jetpack-navigation-3-for-compose.html) — o fim de `NavController.navigate()`.

**Automação externa e a virada para visão**
- [Appium #19560 — expor testTag dos extras em UIA2](https://github.com/appium/appium/issues/19560) · [Appium #18081](https://github.com/appium/appium/issues/18081) · [Appium #15138](https://github.com/appium/appium/issues/15138)
- [Scenario-Guided LLM-based Mobile App GUI Testing](https://arxiv.org/html/2506.05079v4) · [LLMDroid](https://dl.acm.org/doi/pdf/10.1145/3715763) — reconhecimento visual em lugar de extração de layout.
- [Vision Language Models in Mobile App Testing (2026)](https://www.drizz.dev/post/vision-language-models-the-next-frontier-in-ai-powered-mobile-app-testing)
- [CovAgent (2026)](https://arxiv.org/html/2601.21253)

**Adoção**
- [Android UI Development is Compose First (Google, 2026)](https://android-developers.googleblog.com/2026/05/android-ui-development-is-compose-first.html) · [Celebrating 5 years of Jetpack Compose](https://android-developers.googleblog.com/2026/07/five-years-of-jetpack-compose.html) · [The State of Jetpack Compose in 2025](https://medium.com/dvt-engineering/the-state-of-jetpack-compose-in-2025-987145a773fb)

---

## 12. Documentos relacionados

- `20260730_compose_gator_substrato_estatico.md` — diagnóstico: por que a WTG colapsa em Compose.
- `20260731_gator_compose_viabilidade.md` — as quatro vias testadas e reprovadas; o zero de 629.417.
- `20260729_propostas_melhorias_e3.md` §0 — a regra vigente sobre o gator.
- `ape/openspec/changes/telemetry-proof-llm-efficacy/` — change aberta do APE-RV, que exclui o gator do escopo.

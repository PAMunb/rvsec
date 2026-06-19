# Relatório de Bug — Regressão do `aperv:sata_mop` (cobertura abaixo do baseline)

**Data:** 2026-06-19
**Autor:** investigação assistida (Claude Code) — análise de código + traces do smoke
**Status:** **causa-raiz confirmada** no produtor (gator) — ver §7. (Somente diagnóstico; nenhuma correção implementada.)
**Escopo:** somente diagnóstico. Nenhuma alteração de código foi feita.

---

## 0. Sumário executivo

Após (1) completar os JSONs de análise estática e (2) fazer o APE-RV "realmente usar" esses dados
(commit `138a161`, gh13), o arm `aperv:sata_mop` **regrediu**: no smoke de 2026-06-19 a mediana de
`cov_method` ficou **abaixo** do baseline.

```
cov_method (mediana, smoke 16 APKs):
  ape 25.3   |   sata 26.3   |   sata_mop 21.6   |   sata_mop_llm 21.5
```

> **ATUALIZAÇÃO (§10) — dados do experimento completo em andamento supersedem o smoke.** Com ~70–72
> tarefas **pareadas** por arm (vs. 16 não-pareadas do smoke), a "regressão" do `sata_mop` vs. `sata`
> **desaparece — é um EMPATE estatístico** (Δmediana=0; 41–46 de 72 são empates exatos). A queda
> catastrófica do smoke era artefato de n pequeno + agregação não-pareada (conjuntos de APK distintos
> por arm). A **única regressão real e reprodutível é o arm LLM** (`sata_mop_llm`: −3,2pp), e o
> mecanismo é **latência** (executa metade dos passos no orçamento de 300s), **não** B1/B2. Ver §10.

A investigação encontrou **dois problemas independentes**, que juntos produzem o pior cenário para o
claim central H2:

1. **O "tratamento" (scoring MOP por widget/atividade) está INERTE** — em 100% dos estados, de todos os
   16 APKs do smoke, o boost MOP é `0` (`maxBoost=0`). **Causa-raiz confirmada — é de ESCOPO, definida lá
   no início do pipeline:** o `package detector` do rv-experiment escolhe um *pacote de implementação*
   (`code_package`) a partir dos **componentes do manifesto**; esse pacote vira o `filterPackage` do gator
   (`isAppClass`), que **só exporta a `reachability[]` de classes sob esse prefixo**. O R8 mantém os
   componentes sob o pacote real (o detector "parece certo"), mas **reloca o código de implementação para
   fora** — sempre os lambdas sintéticos (`F5.a`, `n5.e`); às vezes pacotes inteiros (`-repackageclasses`).
   Como os event handlers resolvem para essas classes-lambda, eles ficam **fora** do índice e o *join*
   `handler`↔`signature` (downstream, `MopData.java:392`) nunca casa.
   **Medido nos 169 APKs do dataset: o scorer está efetivamente morto em 138/169 (82%)** — ver §7.2.
2. **A regressão de cobertura NÃO vem do MOP** — vem de um **confound de configuração**:
   `componentPercentage` está acoplado à presença do `mopDataPath` e só liga no arm `sata_mop`,
   gastando ~5% dos passos em disparos de broadcast/service que não rendem cobertura de GUI.

> **Achado mais amplo (§7.3–7.4):** o scorer inerte tem DUAS causas — o join-por-lambda (B1) e, ainda mais
> grave, o **colapso de escopo por obfuscação R8** (B8): em **51%** dos apps o `-repackageclasses` achata o
> código para fora do pacote detectado, e **46% têm escopo de reachability <1%** (mediana 1,12%). Reframe
> decisivo: a
> **detecção** MOP é obfuscação-imune, mas a **orientação** estática não é — então o `sata_mop` fica cego
> justamente onde a detecção funciona. É ameaça de validade fundamental, não só bug de wiring.

> **Terceiro achado, verificado em runtime (§9.6):** mesmo nos ~18% de apps onde o join CASA (ex. keepitup,
> 100%), o boost ainda é `maxBoost=0` — por um **segundo modo de falha independente**: a flag MOP cai no
> CardView estático, mas o APE clica o LinearLayout filho (descasamento de granularidade B-gran), cujo widget
> flag-false não-nulo curto-circuita o fallback `+100` (B4). **Consequência: consertar B1 é necessário mas
> NÃO suficiente** — B-gran+B4 mata o sinal mesmo com join perfeito.

**Consequência direta para a calibração planejada:** calibrar `mop_weight_*` é, hoje, **calibrar knobs
mortos** — eles multiplicam um boost que é sempre zero. A calibração, como escopada, produziria um NO-GO
cientificamente vazio (risco R1b').

---

## 1. Contexto

APE-RV usa um JSON de análise estática por APK (`ape.mopDataPath`) para enviesar a exploração rumo a
telas/widgets que alcançam operações monitoradas (MOP = propriedades JavaMOP; aqui, uso da API JCA).

Arms (mesmo binário, só muda config):

| Arm | MOP | LLM | Papel |
|-----|-----|-----|-------|
| `ape` | ❌ | ❌ | baseline AOSP-Monkey |
| `aperv:sata` | ❌ | ❌ | controle within-binary (APE-RV puro) |
| `aperv:sata_mop` | ✅ | ❌ | **contribuição central** |
| `aperv:sata_mop_llm` | ✅ | ✅ | MOP + LLM |

O par limpo é `sata` vs `sata_mop`: deveria diferir **apenas** na orientação MOP.

---

## 2. Metodologia

- Leitura do caminho de código MOP (Java) + git history do commit suspeito `138a161` (gh13).
- Análise dos **traces reais** do smoke (fonte da verdade), por arm, comparando `sata` vs `sata_mop`.
- Dissecação dos JSONs de análise estática (smoke + dataset completo 169 APKs).
- Múltiplos subagentes + MCP sequential-thinking para reconciliar evidências (houve conflito entre a
  hipótese teórica de "super-concentração" e a evidência de runtime; a evidência venceu — ver §4).

---

## 3. Telemetria semi-estruturada (tags do `.trace`)

```
[APE-RV] MOP boost: state=<activity>#<stateKey>@[W=N], boosted=<X>/<Y>, maxBoost=<Z>
[APE-RV] menu boost: state=..., +<N> on MODEL_MENU
[APE-RV] WTG boost: state=..., boosted=<X>/<Y>, maxBoost=<Z>
[APE-RV] Coverage boost: state=..., boosted=<X>/<Y>, gap=<G>
[APE-RV] Triggering broadcast|service: <componente>
GSTG(g0): activities (<A>), states (<S>), edges (<E>)
[APE]   ape.<chave>: <valor>          # dump da Config no início
MopData: ...                          # presente sse o JSON CARREGOU; ausente => load=null
```

`boosted=0/Y` + `maxBoost=0` em todas as linhas ⇒ scorer inerte.

---

## 4. Cadeia causal (cada elo verificado em código + trace)

### Elo 1 — O scorer MOP é inerte. Causa-raiz: *join* de namespaces incompatíveis.

O flag MOP do widget é derivado em `MopData.deriveWidgetMopFlags`
(`ape/.../utils/MopData.java:384-401`) cruzando `listener.handler` contra um índice de assinaturas de
métodos `bySignature` (linha **392**: `bySignature.get(l.handler)`). O caminho que evitaria o join
(`handlerReachesTarget`) é **`null` em todo listener** (linhas 373-374, 388 — "null on every listener
until C3 lands"), então o join é sempre executado.

**Os dois lados do join estão em representações de nome diferentes** (org.fossify.math_10, medido):

| Lado | Exemplo real | Forma |
|---|---|---|
| `listener.handler` (chave de busca) | `<F5.a: void onClick(android.view.View)>`, `<n5.e: boolean onLongClick(...)>` | ofuscação **achatada** (pacotes de 1 letra) |
| `reachability[].methods[].signature` (chaves do índice) | `<org.fossify.commons.views.MyDialogViewPager: void <init>(...)>` | nomes **com pacote preservado** (alguns ofuscados: `...activities.a`) |

Medições (org.fossify.math_10):
- reach: 56 classes / 333 métodos; **79 métodos** com `reachesTarget|directlyReachesTarget = true`.
- listeners: 14.658 (34 handlers distintos, 26 classes de handler).
- **`handler` (exato) ∈ `signature`: 0 / 14.658.**
- **classes-de-handler ∩ classes-da-reachability: 0** — as classes que implementam os listeners
  (`F5.a`, `n5.e`, …) **não aparecem na reachability sob nome nenhum**.

> ⚠️ **Ponto crítico para a correção:** a análise estática roda sobre o **APK já ofuscado**, então ambos
> os lados *deveriam* estar no mesmo namespace e casar. O fato de `signature` preservar pacote enquanto
> `handler` está achatado, **no mesmo JSON**, é incoerente — indica que os dois campos são produzidos por
> **passos/representações diferentes** dentro do produtor (gator/Soot/dexlib2), ou que a reachability não
> enumera as classes que implementam os listeners. **Esta é a causa-raiz a corrigir, e está sob
> investigação no cliente gator** (`rvsec/rvsec-android/rvsec-gator`). Ver §7.

**Efeito:** `bySignature.get(l.handler)` retorna sempre `null` ⇒ todo widget fica com
`directMop=transitiveMop=false` ⇒ `mopActivities` vazio ⇒ `activityHasMop=false` ⇒ os três ramos de
`MopScorer.score` retornam 0 (inclusive o fallback `+100` de atividade). Confirmado no trace
(passwordstore `sata_mop`): `boosted=0/2`, `boosted=0/13`, `maxBoost=0` em todas as 96 linhas `MOP boost`.

> **Por que passou nos testes unit/integration?** O APK de dev `test-apks/cryptoapp.apk.json` é
> debug-build não-ofuscado → handlers = nomes completos → o join casa (2 widgets recebem boost). Os apps
> reais (release-build minificado) quebram o join. Clássico "funciona no teste, morto em produção".

### Elo 2 — A regressão de `cov_method` vem do confound `componentPercentage`

`ape/.../utils/Config.java:169-170`:
```java
public static final double componentPercentage = Config.getDouble("ape.componentPercentage",
        mopDataPath != null ? 0.05 : 0.0);
```
`componentPercentage` está **acoplado à presença do `mopDataPath`** (não é propriedade do tool.py; não
está em `APERV_PROPERTY_MAPPING`). Ligar o MOP ⇒ liga o component-triggering (gh11). Verificado no trace:

| arm | `ape.componentPercentage` | linhas `Triggering` |
|---|---|---|
| `sata` | `0.0` | 0 |
| `sata_mop` | `0.05` | 9 (broadcasts p/ ProfileInstaller; services autofill/tile…) |

Esses disparos consomem ~5% dos passos com intents que **não rendem cobertura de GUI** e perturbam o
fluxo ⇒ `sata_mop` visita **menos estados/atividades**. GSTG (passwordstore): `sata` 7 ativ./22 estados
→ `sata_mop` 4 ativ./16 estados, **apesar de executar MAIS eventos** (718 vs 475) — churn puro. É isso
que derruba o `cov_method`.

`duress.keyboard_51` é a exceção que "ganhou" (+9.4) — onde disparos acidentalmente alcançam telas
component-gated; net-negativo no conjunto. (`duress` tem 0/11 atividades reachTarget ⇒ MOP boost
definitivamente 0 lá ⇒ o ganho é dos componentes/ruído, não do MOP.)

### Elo 3 — As "vitórias históricas" do `sata_mop` eram ilusórias

Antes de gh13 o parser lia chaves erradas → boost sempre 0 → `sata_mop` era **comportamentalmente
idêntico** a `sata`. gh13 "ligou" o consumo do JSON, mas (a) o scoring continua 0 (Elo 1) e (b) passou a
ativar o confound (Elo 2). As campanhas antigas onde "sata_mop venceu" eram, muito provavelmente,
empates/ruído de um no-op — não efeito MOP real.

---

## 5. Bugs e incoerências (priorizados)

| # | Severidade | Local | Problema |
|---|---|---|---|
| **B1** | **Crítico** | **produtor (gator)** `RvsecAnalysisClient.java:278,1319` + `MopData.java:392` | *Join* `handler`↔`signature` nunca casa porque o gator **exporta `reachability[]` apenas para classes do pacote do app** (`isAppClass`), e os handlers resolvem para **classes lambda sintéticas do R8** (`F5.a`, `n5.e`) fora desse pacote → excluídas do índice. Mata todo o scoring nos apps reais. Causa-raiz confirmada (§7). |
| **B2** | **Crítico (validade)** | `Config.java:169-170` | `componentPercentage` acoplado a `mopDataPath`. `sata` vs `sata_mop` **não isola** o efeito MOP. Confound que invalida H2. |
| **B3** | Alto (latente) | `StatefulAgent.java:1299,1367` vs `getActionBasePriority` | Escala: boost 300/500 vs prioridade-base ~8–52 em roleta proporcional. Consertar B1 ingenuamente troca no-op por **super-concentração** (re-clicar 1–2 botões). Pesos precisam ser re-escalados. |
| **B4** | **Alto (CONFIRMADO ativo)** | `MopScorer.java:40-53` + `MopData.getWidget` | Widget runtime não-nulo flag-false → **curto-circuita o fallback `+100`** de atividade (retorna 0 no ramo `w!=null` antes de checar `activityHasMop`). **Verificado empiricamente em keepitup (§9.6):** é o matador dos apps onde o join CASA — não é só latente. Combina com B-gran (granularidade estática CardView vs runtime LinearLayout). |
| **B5** | Médio (latente) | `MopScorer.eventTypeOf` vs JSON | Vocabulário divergente: JSON `long_click`/`enter_text`/`touch` vs código `longClick`/`scroll`. Per-eventType scoring degradaria; mitigado pelo fallback match-any. |
| **B6** | Baixo | `MopData.java:314-316` | `idName` duplicados colidem no `LinkedHashMap` (last-write-wins); empty-`idName` dropados. |
| **B7** | Higiene | `handlerReachesTarget` (gh60-C3) | Campo de bypass do join existe mas é `null` em todo listener. Se o produtor o preenchesse, B1 sumia sem depender de namespaces casarem. |
| **B8** | **Crítico (mais amplo que B1)** | `package_detector` → gator `isAppClass` (`:278`) | **Colapso de escopo sob R8 `-repackageclasses`:** 51% dos apps achatam o código em pacotes top-level; **46% têm escopo de reachability <1%** do código (mediana 1,12%; ex. 9/12.675 classes). Quebra MOP-guidance E denominador da cobertura MOP, além dos handlers (§7.3). Independe de B1. |
| **B9** | Médio (validade) | `StatefulAgent.java:162` vs `MopData.load` (`:148` 1-arg / `:161` 3-arg) | `mopStrictPackageMatch` está **morto em runtime**: o agente chama `MopData.load(path)` (1-arg), e o sanity-check de pacote/mainActivity só existe no overload de 3-arg (`:226-236`). O flag documentado no CLAUDE.md como ativo nunca dispara. (Achado opus, verificado.) |
| **B10** | Médio (oportunidade) | `MopData.java:317-318` (`mopActivities` só de widget) | O fallback de atividade (`activityHasMop` → `+100`) é derivado **somente** de flags de widget — que morrem com B1/B8. Se fosse derivado de `reachability[].className` (que sobrevive ao colapso de escopo nas poucas activities-shell do manifesto), daria orientação **obfuscação-robusta** sem depender do join por handler. (Achado deepseek, verificado — ver §9.) |

---

## 6. Implicações

### Para a calibração
- **Knobs mortos em ~82% por escopo E nos 18% restantes por granularidade-runtime:**
  `mop_weight_direct/transitive/activity` multiplicam um boost que é 0 em 138/169 apps (§7.2); e mesmo onde o
  join casa 100% (keepitup) o boost continua 0 em runtime por B-gran+B4 (§9.6). Calibrar antes de consertar
  B1 **e** B-gran/B4 é vazio (não há sinal a otimizar). Verificação de que o fix funcionou:
  `grep 'MOP boost' <trace> | grep -v 'maxBoost=0'` deve passar a retornar linhas, e o join no dataset
  (§8 receita) deve subir de ~18% para perto de 100% dos apps com listeners.
- Só **depois** de B1 **e** B-gran/B4 atacar **B3**: o boost útil é provavelmente da ordem de +5…+30 (não
  +300/+500), para guiar sem matar diversidade. É isso que a calibração deveria ajustar.

### Para o desenho experimental
- **B2 precisa ser resolvido no desenho**, não só no código: `sata` e `sata_mop` têm que diferir **apenas**
  no scoring MOP. Opções: fixar `componentPercentage` igual nos dois arms (ambos 0, ou ambos 0.05), ou
  tratar component-triggering como arm separado.

### Ordem recomendada
B1 (produtor gator) → **B-gran + B4** (granularidade estática↔runtime + fallback `+100`; §9.6 prova que sem
isto até os apps com join 100% ficam `maxBoost=0`) → B5 (wiring) → B2 (desenho) → B3 + calibração de pesos →
testar H2. **B1 é necessário mas não suficiente** — B-gran/B4 é gargalo paralelo, não opcional.

---

## 7. Causa-raiz CONFIRMADA — produtor da análise estática (gator)

**Veredito:** `handler` e `signature` vêm do **mesmo Soot Scene, mesmo esquema de nomes** — não há
deofuscação nem segundo namespace (Soot roda direto sobre o APK ofuscado, `Configs.java`
`set_src_prec(src_prec_apk)`). O bug é um **filtro de escopo na exportação da reachability**:

1. **A reachability é exportada SÓ para classes do pacote do app.**
   `RvsecAnalysisClient.writeReachabilitySection` itera apenas `appClasses`
   (`RvsecAnalysisClient.java:1319`), e `appClasses = extractClasses(filterPackage)` filtra por
   `isAppClass` (`:277-286`): `if (!className.startsWith(filterPackage)) return false;`
   (`filterPackage` = pacote do app, ex.: `org.fossify.math`).

2. **Os handlers resolvem para classes lambda sintéticas do R8, FORA do pacote do app.**
   `RvsecAnalysisClient.collectWidgets` emite `listener.put("handler", handler.getSignature())`
   (`:943`), e `handler` é o `SootMethod` resolvido por CHA (`ListenerInstance.computeConcreteHandlers`)
   — para um `OnClickListener` lambda compilado pelo R8, é a classe sintética (`F5.a`, `n5.e`, `j.B`),
   classes top-level que **não** começam com `org.fossify.math`. Logo `isAppClass` as rejeita e elas
   **nunca entram no índice `reachability[]`**.

3. **Resultado:** `handler-classes ∩ reachability-classes = 0` é consequência mecânica do filtro de
   pacote, não de naming. Downstream, `MopData.deriveWidgetMopFlags` → `bySignature.get(listener.handler)`
   (`MopData.java:392`) nunca acha o handler → todo flag de widget falso → scorer inerte.

   > Em apps Kotlin modernos os click listeners são quase sempre **lambdas** → ~100% dos handlers caem
   > fora do filtro de pacote → 0 matches. (Os fontes do F-Droid em
   > `/home/pedro/.../rvsec-testes-jca/sources/org.fossify.math_10.apk/` corroboram: listeners via lambda.)

4. **A informação necessária JÁ EXISTE no índice.** `complementWithCallbacks`
   (`RvsecAnalysisClient.java:704-720`) adiciona callbacks de event-handler (inclusive lambdas) ao
   `reachableSet`/`reachesTargetSet`. O `ReachabilityIndex` sabe se o método-handler alcança um target —
   isso só **não é exportado** por listener.

5. **O campo de bypass projetado para isso nunca foi implementado.** `handlerReachesTarget`/
   `handlerDirectlyReachesTarget` aparecem **só em javadoc** (`ReachabilityEnricher.java:21,68,77`); os
   hooks `enrichWidget`/`enrichTransition` retornam `EMPTY` (`:71-73, 80-82`); `writeWidget` emite só
   `eventType`+`handler` (`RvsecAnalysisClient.java:1416-1418`); não há chave `HANDLER_REACHES_TARGET`
   em `JsonSchema`. (Por isso o parser Java lê `handlerReachesTarget=null` em todo listener.)

### 7.1. Cadeia de escopo (visão ampla): package detector → gator → reachability

A causa-raiz não nasce no gator — nasce na **definição de escopo** feita quando o rv-experiment
instancia o App. Cadeia completa, verificada:

1. **rv-experiment/rv-platform instancia o App** e lê `App.code_package`
   (`rv-android-core/.../domain/app.py:119-132`), que chama
   `PackageDetector.detect_package(apk)` (`util/android/package_detector.py:514`).
2. **O detector NÃO é "extrai a 3 níveis" — é um algoritmo de 7 prioridades** sobre os componentes do
   manifesto (activities/services/receivers; providers excluídos), após filtrar framework/libs
   (`FRAMEWORK_PREFIXES`: `android.`, `androidx.`, `kotlin.`, …). Ordem (`detect_package`,
   `package_detector.py:514-684`):
   - **Fast-path `same_package`** (caso dominante, ~72,5%): se todos os componentes-app estão no namespace
     do `manifest_pkg` → `code_package = manifest_pkg`.
   - **P0 game engine** (Godot/Unity/Cocos2D/LibGDX): manifest é autoritativo.
   - **P2 single package**: um único pacote 3-níveis → usa-o.
   - **P3 common prefix** (multi-pacote): `find_common_prefix` se válido (≥2 níveis, relacionado ao
     manifest). Ex.: math declara `org.fossify.math.*` **+** `org.fossify.commons.*` → prefixo `org.fossify`.
   - **P4 most_common** (frequência): se um pacote cobre ≥60% dos componentes → usa-o.
   - **P5 similaridade** (Jaro-Winkler/Levenshtein/SequenceMatcher ≥0,85): captura variações/typos
     (`manifest ch.famoser.mensa` vs código `ch.florianfrauenfelder`).
   - **P6 fallback**: `manifest_pkg`.
   O resultado (`code_package`) é o `filterPackage` do gator. **Observação importante:** mesmo um detector
   "correto" (escolhe bem o pacote dos componentes) não resolve o problema — os lambdas do R8 são top-level
   por design, fora de QUALQUER pacote-app, então nenhuma escolha de prefixo os captura.

   **Medição empírica do escopo (138 apps c/ listeners do dataset):** inferindo o `filterPackage` pelo
   prefixo comum das classes da `reachability`, apenas **25% das handler-classes caem dentro do escopo**;
   **73% são top-level achatadas** (lambdas); **107 apps têm 100% dos handlers fora do escopo**.
   Contra-exemplo limpo: `app.notesr_59` (escopo `app.notesr`, 19 handler-classes, **todas dentro**, 0
   achatadas → join casa 40/40). Ou seja: onde os handlers são classes nomeadas sob o pacote-app, funciona;
   onde são lambdas (a maioria, apps Kotlin), não há o que casar.
3. **Esse `code_package` é passado ao gator** como argumento de pacote
   (`rv-static-analysis/.../static/static_analysis.py:255`: `code_package=self.app.code_package`).
4. **O gator usa como `filterPackage`** em `isAppClass` (`RvsecAnalysisClient.java:278`:
   `if (!className.startsWith(filterPackage)) return false;`) e **só exporta `reachability[]` de
   classes sob esse prefixo** (`:1319`).
5. **R8 quebra o pressuposto:** os componentes do manifesto mantêm o pacote real (porque o manifesto os
   referencia — R8 os preserva), então o detector acerta o pacote dos componentes; **mas o código de
   implementação obfuscado é relocado para fora desse prefixo** — *sempre* as classes lambda sintéticas
   (top-level `F5`, `n5`, `j`), e em apps com `-repackageclasses`/`-flattenpackagehierarchy`, pacotes
   inteiros achatados. Esse código sai do escopo da reachability.
6. **Downstream:** os handlers (que são justamente essas classes-lambda) não estão no índice → join falha →
   flags falsos → scorer inerte.

> **Implicação arquitetural (além do MOP):** todo o pipeline (escopo da instrumentação, da análise
> estática, da cobertura) é ancorado num **prefixo de pacote derivado do manifesto**. Quando o R8 reloca
> implementação para fora desse prefixo, o escopo encolhe **silenciosamente** — sem erro, sem warning. O
> detector dá a falsa sensação de "pacote correto" porque valida contra os componentes do manifesto (que o
> R8 preserva), não contra onde o código minificado realmente está.

### 7.2. Quantificação no dataset completo (169 APKs)

Medido diretamente nos 169 `.apk.json` de
`/home/pedro/.../APKS_FINAL_JCA_DEXLIB_20260604` (join `handler` ∈ `reachability.signatures`):

| Métrica | Valor |
|---|---|
| Total de JSONs | 169 |
| Sem nenhum listener (apps Compose etc. — nada a pontuar) | **31** |
| Com listeners, mas **0 handlers casam** a reachability (scorer morto) | **107** |
| Com ≥1 handler casando (scorer parcialmente vivo) | **31** |
| **Scorer efetivamente morto** (31 sem-listener + 107 zero-match) | **138 / 169 = 82%** |
| Classes-de-handler "achatadas" (lambda-like, ≤1 ponto) | **1.642 / 2.245 = 73%** |

**Leitura:** o join (estático) está morto em **~82%** dos apps; casa (parcial) em só **18%**. **Mas
"join casa" ≠ "boost dispara":** a verificação do keepitup (§9.6) — um app com join **100%** — mostra
`maxBoost=0` em runtime, porque a flag MOP cai no CardView estático enquanto o APE clica o LinearLayout filho
(B-gran), e esse widget flag-false não-nulo curto-circuita o fallback `+100` (B4). Ou seja, mesmo nos 18% o
sinal provavelmente **não chega ao runtime** — não por super-concentração (B3), mas por morte silenciosa
(B-gran+B4). O B3 só se materializa **depois** de B1 **e** B-gran/B4 estarem corrigidos. **`mop_weight_*` é
knob morto em ~82% por escopo (B1/B8) e, nos 18% restantes, provavelmente morto em runtime por B-gran+B4 —
não há regime medido em que ele esteja vivo.**

### 7.3. Risco MAIOR que os lambdas — colapso de escopo por repackaging agressivo (R8)

Investigando além dos handlers: muitos apps do dataset usam **`-repackageclasses`/`-flattenpackagehierarchy`**
do R8, que achata o código de implementação em pacotes top-level de 1 letra (`a.b`, `F5.a`). Como os
componentes do manifesto são preservados (R8 os mantém), o `package detector` acerta o pacote dos
componentes — mas a implementação real fica **fora** desse prefixo, e o filtro `isAppClass` do gator
exporta a reachability de quase nada.

**Evidência robusta (medida direta do JSON, NÃO depende de forma-de-nome)** — classes na `reachability[]`
÷ classes-app reais (Androguard) para os apps mais agressivamente repackaged:

| app | classes-app (dex) | classes na reachability | escopo |
|---|---|---|---|
| gizz.tapes.foss_63 | 12.675 | **9** | 0,1% |
| app.podiumpodcasts.podium | 8.271 | 10 | 0,1% |
| de.kitshn.android_20090 | 9.564 | 4 | 0,0% |
| com.yogeshpaliyal.deepr_28 | 7.103 | 8 | 0,1% |
| ru.stersh.youamp_36 | 6.589 | 5 | 0,1% |
| org.cis_india.wsreader_145 | 9.099 | 99 | 1,1% |
| com.maazm7d.termuxhub_3 | 5.658 | 19 | 0,3% |

A `reachability` cobre **~0,1% do código** desses apps. `reachesTarget>0` sobrevive só porque as poucas
classes-shell mantidas (activities do manifesto) alcançam um target — mas o denominador é uma casca da
realidade. **Isso quebra o MOP-guidance — e o denominador da cobertura MOP — independentemente do
join-por-lambda (B1), para grande parte do dataset.**

**Distribuição dataset-wide (scan Androguard dos 169 — `%scope` = `reachability.classes ÷ classes-app`,
medido, robusto):**

| Métrica | Valor |
|---|---|
| Apps com **repackaging agressivo** (≥50% das classes-app em pacote top-level ≤3 chars, ex. `a.b`) | **86/169 = 51%** |
| Apps com **escopo de reachability < 1%** do código | **78/169 = 46%** |
| Apps com escopo de reachability < 5% | **110/169 = 65%** |
| **Mediana do escopo de reachability** | **1,12%** |

Ou seja: **em metade do dataset a análise estática "vê" menos de ~1% das classes do app.** Contraste:
`com.zhangke.fread` (não-repackaged) tem escopo 53%; `app.notesr` (controle limpo) ~12% e join 40/40.

> **Ressalvas (validade):** (i) o denominador `classes-app` usa denylist de libs por `startswith` — pode
> super/sub-contar, mas mesmo com erro de 2× um escopo de 0,07% (gizz) continua catastrófico; (ii) o sinal
> "repackaging por forma-de-nome" tem falso-positivo "lib obfuscada contada como app". A **medida definitiva**
> de obfuscação no código de app é `source_file_idx` no DEX (`Foo.kt` real vs `SourceFile` vs
> `r8-map-id-<hex>`) + `@kotlin.Metadata`, **não** a forma do nome — ver o plano de validação
> `rvsec-testes-jca/docs/20260619_plano_obfuscacao_validacao.md` (§4.5), que documenta esse mesmo modo de
> falha do `package_detector` sob R8 (§3) de forma independente. **O número robusto aqui — escopo medido
> direto do JSON — não depende de forma-de-nome.**

### 7.4. Reframe decisivo: DETECÇÃO ≠ ORIENTAÇÃO

O plano de validação (`…/20260619_plano_obfuscacao_validacao.md`, §1) estabelece que **a detecção MOP é
obfuscação-imune** — o monitor JavaMOP observa o *callee* da API JCA, que o R8 não renomeia. Por isso o
experimento **continua detectando violações**. Mas a **orientação MOP estática do APE-RV depende de
reachability**, que **é** obfuscação-frágil (§7.3). Consequência: **a orientação fica cega exatamente onde a
detecção ainda funciona.** Não é só um bug de wiring corrigível — é uma **ameaça de validade fundamental** à
premissa do `sata_mop` neste dataset (≈100% dos apps com `minifyEnabled true`, por §4.5.1 do plano).

> **Pista esperançosa (a verificar no gator):** a *engine* de reachability roda BFS sobre o **call graph
> SPARK inteiro** (cobre as classes achatadas); só a **exportação** do JSON é filtrada por pacote
> (`isAppClass`). Logo, emitir `handlerReachesTarget` por listener — computado direto do `SootMethod`
> resolvido contra o índice — **driblaria tanto o join-por-lambda (B1) quanto o colapso de escopo (§7.3)**,
> pois o dado já existe no índice. **Pré-requisito a confirmar:** que o call graph / entry-points do gator
> inclua as classes achatadas e não esteja ele também limitado por pacote. Se estiver, a correção é maior
> (recompute de escopo de análise).

### Local de correção recomendado (NÃO implementar agora)
Calcular a reachability **diretamente do `SootMethod` handler** (já em mãos em
`RvsecAnalysisClient.java:940`) contra o `ReachabilityIndex` e **emitir `handlerReachesTarget` por
listener** — eliminando o join frágil por string. Concretamente: preencher o stub
`ReachabilityEnricher.enrichWidget`, adicionar a chave em `JsonSchema`, e emitir no loop de listeners de
`writeWidget`. (Alternativa de "afrouxar `isAppClass` para incluir lambdas" é **pior**: continua dependendo
do join exato por assinatura e infla o denominador de cobertura — o filtro é deliberado.)

> Do lado do APE-RV, isso também resolve B7: `deriveWidgetMopFlags` (`MopData.java:388-390`) **já prefere**
> `handlerReachesTarget` quando presente — basta o produtor passar a emiti-lo.

---

## 8. Apêndice — caminhos e receitas

**Código (raiz `/pedro/.../workspace-rv/ape`):**
- `src/main/java/com/android/commands/monkey/ape/utils/MopScorer.java`
- `src/main/java/com/android/commands/monkey/ape/utils/MopData.java` (derivação 384-401; join 392; getWidget/activityHasMop)
- `src/main/java/com/android/commands/monkey/ape/utils/Config.java` (componentPercentage 169-170; pesos 128-160)
- `src/main/java/com/android/commands/monkey/ape/agent/StatefulAgent.java` (aplicação do boost ~1352-1433)
- `src/main/java/com/android/commands/monkey/ape/agent/SataAgent.java`

**Tool/integração:** `/pedro/.../rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`

**Traces do smoke:** `/pedro/.../rvsec/rv-android/data/results/smoke_cmp_00..07/smoke_cmp_NN/<apk>.apk/`
(`.trace` por arm, `<apk>.apk.json` co-localizado, `coverage.csv`)

**JSONs dataset completo:** `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB_20260604` (169 `.apk` + 169 `.apk.json`)

**Produtor (gator):** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-gator`

**Receitas:**
```bash
# scorer aplica boost real?
grep -a 'MOP boost' <trace> | grep -v 'maxBoost=0' | wc -l        # 0 => inerte
# componentes disparados por arm
grep -ac 'Triggering' <trace>
# tamanho do grafo explorado (proxy de diversidade)
grep -a 'GSTG' <trace> | tail -1
# join handler->signature (deveria casar; mede 0)
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); \
 sig=set(m['signature'] for c in d['reachability'] for m in c.get('methods',[]) if m.get('signature')); \
 h=[l['handler'] for w in d['windows'] for wd in w.get('widgets',[]) for l in wd.get('listeners',[]) if l.get('handler')]; \
 print('match', sum(x in sig for x in h), '/', len(h))" <apk>.apk.json
```

---

## 9. Revisão cruzada (5 LLMs) — achados verificados e incorporados

Cinco análises independentes (`ape/docs/analise_{gemini,gpt5,mimo,opus,deepseek-v4-flash-free}.md`) foram
auditadas com subagentes, **reabrindo cada citação de código no fonte**. Síntese:

### 9.1. Meta-achado: convergência ≠ correção
As cinco concordam nos **sintomas** (scorer inerte + confound `componentPercentage`) e todas as citações
de código Java conferem. Mas **3 das 5 (gemini, mimo, deepseek) convergiram na MESMA causa-raiz ERRADA**
para o B1 — "mismatch de namespace/deofuscação" (signatures preservam pacote, handlers achatados, falta
processar `mapping.txt`). O fonte do gator **contradiz**: `handler` = `SootMethod.getSignature()`
(`RvsecAnalysisClient.java:943`) e `reachability` vêm da **mesma Soot Scene**, ambos ofuscados; o que mata
o join é o **filtro de escopo** `isAppClass` (`:278`), não naming (§7). Lição: convergência entre LLMs não é
evidência — todas fizeram a mesma inferência superficialmente plausível, e só quem raciocinou sobre o fonte
do produtor (opus + este relatório) acertou. **Consequência prática:** o fix headline do gemini (consumir
`mapping.txt`) **não funcionaria** — as classes-lambda estão *ausentes* do índice por escopo; não há para
onde mapear. Só opus e este relatório enxergam o **B8** (colapso de escopo); as outras quatro o perdem.

Ranking de confiabilidade na causa-raiz: **opus > gpt5 > mimo > deepseek > gemini**. (Mas deepseek e gpt5
contribuem achados úteis abaixo — "pior no root-cause" ≠ descartável.)

### 9.2. Insights novos verificados em código — incorporados
- **Fallback de atividade derivado de reachability (deepseek → B10).** Hoje `activityHasMop` deriva só de
  flags de widget (`MopData.java:317-318`), que morrem com B1/B8. Derivar de `reachability[].className`
  torna o `+100` **obfuscação-robusto**: sobrevive exatamente onde o join por handler e o escopo colapsam,
  pois as poucas activities-shell do manifesto mantêm `reachesTarget>0`. É o melhor salvamento parcial
  proposto. **Pré-condição:** interage com B4 — o `+100` precisa sair do ramo sombreado (`MopScorer.java:48`
  `return 0` antes do fallback `:50`) para disparar.
- **`mopStrictPackageMatch` morto (opus → B9).** `StatefulAgent.java:162` usa `load` de 1-arg; o check de
  pacote só roda no overload de 3-arg (`:226-236`). **O CLAUDE.md descreve o flag como ativo — a doc está
  enganosa.**
- **Correção de telemetria (gpt5).** Ausência do log `MopData:` **não** prova load nulo. A presença de
  linhas `[APE-RV] MOP boost` *prova* `_mopData != null`, pois a passada inteira é guardada por
  `if (_mopData != null)` (`StatefulAgent.java:1353`). Evita o diagnóstico falso "o JSON não carregou".
- **`scoreOpenMenu` boosta TODOS os MODEL_MENU do estado (deepseek).** `StatefulAgent.java:1377-1383` —
  latente, sem impacto enquanto o boost é 0, mas vira ruído quando B1 for corrigido.

### 9.3. Pistas falsificáveis a verificar (NÃO confirmadas — dados de trace fora do escopo de código)
- **Anomalia keepitup (deepseek): ✅ VERIFICADA E RESOLVIDA — ver §9.6.** É um **segundo modo de falha real**
  (granularidade estática vs runtime + B4), independente de B1/B8, que mata exatamente os apps onde o join
  CASA. As duas hipóteses do deepseek (load nulo; `getWidget` nulo) estavam **erradas**; o mecanismo correto
  é o **B-gran+B4** do opus.
- **`sata_mop_llm` com 0 chamadas LLM (mimo): ❌ REFUTADO — ver §9.7.** A varredura dos 16 traces do smoke
  mostra o LLM **ativo em todos** (decision ratio 61–100%, dezenas de chamadas/app, 0 falhas). A afirmação do
  mimo está incorreta.
- **Reversão "não há regressão" (opus):** opus afirma que a queda é ruído (n=1, p≈0,48–0,72) e que o B2 não a
  causa. Este relatório diz que o B2 causa. **Ambos repousam em dados de trace não auditáveis por código** —
  o código só confirma o *acoplamento* (`Config.java:169-170`), não o efeito numérico. Posição honesta: o
  smoke (16 APKs × 1 rep) é subdimensionado; o delta de cobertura **não é confiável de nenhum lado**. O B2
  deve ser removido por ser defeito de validade, independentemente de ter movido este número.

### 9.4. O que NÃO adotar
- ❌ Teoria "mismatch de namespace/deofuscação" (gemini/mimo/deepseek) — contradita pelo fonte do gator.
- ❌ Fix via `mapping.txt` (gemini) — não conserta (lambdas ausentes do índice por escopo).
- ❌ Afrouxar `isAppClass` para incluir lambdas — infla o denominador de cobertura (§7.4).
- ❌ Tratar o delta de cobertura do smoke como real em qualquer direção (n=1).

### 9.5. Design experimental (gpt5) — adotar
Decompor em braços que isolam um fator cada (`sata` / `sata`+JSON+`cp=0` / component-triggering isolado /
`sata_mop_gui` / `sata_mop_full`) e **gate de verificação**: exigir `maxBoost>0` no trace antes de confiar
em qualquer delta de cobertura. (Mesma direção da receita §8.)

### 9.6. Verificação da anomalia keepitup — SEGUNDO modo de falha confirmado (B-gran + B4)

A anomalia levantada pelo deepseek ("join 100% mas `maxBoost=0`, e log `MopData: loaded` ausente") foi
verificada nos artefatos reais do smoke
(`data/results/smoke_cmp_04/.../net.ibbaa.keepitup_19.apk/...sata_mop.trace` + `.apk.json` co-localizado). É
um **segundo modo de falha real, independente de B1/B8** — e atinge justamente os apps onde o join casa.

**Medições (keepitup, smoke):**

| Verificação | Resultado |
|---|---|
| Linhas `[APE-RV] MOP boost` no trace | 116 — **todas** `maxBoost=0` |
| Join `handler` ∈ assinaturas-alvo do JSON | **46/46 (100%)**; 179 métodos-alvo; `complete=true` |
| Widgets com `transitiveMop=true` derivados do JSON | **31** em 3 atividades |
| `mopActivities` derivado (via `baseActivity`) | `{DefaultsActivity, GlobalSettingsActivity, SystemActivity}` |
| Atividade mais visitada no runtime | `DefaultsActivity` (92/116 linhas) — **é** MOP-activity |
| Widgets flag-`true` em DefaultsActivity | os **9 `cardview_activity_defaults_*`** |
| Alvos reais das ações `MODEL_CLICK` | os **`linearlayout_activity_defaults_*`** (flag-FALSE) |
| Ações que tocaram um `cardview_*` (flag-true) | **0** |

**Mecanismo (causa-raiz da anomalia):** a análise estática atribui o listener MOP ao **CardView pai**
(`cardview_activity_defaults_port`, um `FrameLayout`); em runtime o nó clicável que o APE aciona é o
**LinearLayout filho** (`linearlayout_activity_defaults_port`, `clickable=true`), que existe no JSON como um
widget **separado e flag-false**. O trace mostra a hierarquia explicitamente: `Patching this node:
FrameLayout@...cardview_activity_defaults_port` → `Patching child node:
LinearLayout@...linearlayout_activity_defaults_port` → `MODEL_CLICK ... resource-id=...linearlayout_...`.
Logo `getWidget(activity, "linearlayout_...")` retorna **não-nulo flag-false** → `MopScorer.score` retorna 0
no ramo `w!=null` → **nunca alcança o fallback `+100` de `activityHasMop`** (B4). Resultado: `maxBoost=0`
mesmo numa MOP-activity com join 100%. (litube e opencloud também dão `maxBoost=0` em 100% das linhas, com
alvos distintos — webview / nav items —, padrão consistente.)

**O que isto refuta e o que confirma:**
- ❌ "Load retornou nulo" (deepseek hip. 2): **refutado.** As 116 linhas `MOP boost` provam `_mopData != null`
  (a passada é guardada por `if (_mopData != null)`, `StatefulAgent.java:1353`). O `load` só retorna não-nulo
  **após** emitir `MopData: loaded` (`MopData.java:240`); ambos os logs usam o mesmo `System.out`
  (`Logger.iformat`/`iprintln`). A ausência do log no `.trace` é **artefato de captura** (o stdout do
  construtor não cai neste arquivo), não evidência de falha.
- ❌ "`getWidget` retorna nulo por mismatch cardview/linearlayout" (deepseek hip.): **refutado.** O JSON
  contém **ambos**; `getWidget` retorna **não-nulo**.
- ✅ **B-gran + B4** (opus): **confirmado** como o mecanismo correto.

**Implicação decisiva para o plano de correção:** consertar **B1** (gator emitir `handlerReachesTarget`) é
**necessário mas NÃO suficiente.** Mesmo com o join perfeito, apps tipo keepitup continuam com `maxBoost=0`
por causa do descasamento de granularidade + B4. Portanto o fix **B4/B10** (deixar o `+100` de atividade
disparar mesmo quando `getWidget` devolve widget não-nulo flag-false) é o que recupera esses apps no nível de
atividade; e um fix **B-gran** mais profundo (propagar a flag MOP do ancestral estático para os descendentes
clicáveis em runtime, ou casar o clicável runtime ao ancestral MOP estático mais próximo) é necessário para
orientação por-widget. Crédito ao deepseek por **sinalizar** a anomalia (era real e importante), ainda que as
explicações propostas estivessem erradas.

### 9.7. Verificação do "`sata_mop_llm` com 0 chamadas LLM" (mimo) — REFUTADO

O mimo (P3) afirmou que o braço `sata_mop_llm` fez **0 chamadas LLM** em passwordstore e tubular, degradando
silenciosamente para `sata`+triggering. **Varredura dos 16 traces `sata_mop_llm` do smoke contradiz:** o LLM
está **ativo em todos**, com `ape.llmUrl=http://10.0.2.2:30000/v1` e o sumário `[APE-RV] LLM Summary` real em
cada um (decision ratio 61–100%, 12–62 respostas/app, **0 falhas / 0 null / 0 breaker-trips**). Os dois apps
citados:

| App | `LLM Summary` | Decision ratio |
|---|---|---|
| passwordstore | `calls=42 tokens_in=57714 tokens_out=1076 matched=33 no_match=9 null=0 breaker_trips=0` | **78,6% (33/42)** |
| tubular | `calls=56 tokens_in=84671 tokens_out=1363 matched=48 no_match=8 null=0 breaker_trips=0` | **85,7% (48/56)** |

O `LlmRouter` só é instanciado se `Config.llmUrl != null` (`StatefulAgent.java:165`); como o URL estava setado
e há centenas de linhas `[APE-LLM-PROMPT]`/`[APE-LLM-RESPONSE]` + sumário com `calls>0`, a afirmação de "0
chamadas" é **factualmente incorreta** para este smoke. (Provável causa do engano: grep por tag/arquivo
errado.) **Conclusão:** o braço LLM não é um modo de falha *por LLM inerte*. **[Refinado em §10:** o LLM
**está** ativo, mas o arm `sata_mop_llm` **regride mesmo assim** — não por B1/B2, e sim por **latência**:
cada passo gasta ~1,2 s no modelo e, com `llm_percentage=0.9`, o arm executa **metade** dos passos no
orçamento de 300 s. Há ainda 2 falhas app-específicas reais — ver §10.3.**]**

---

## 10. Verificação em escala — experimento completo (parcial, em andamento)

**Fonte:** `data/results/cmp_00..05/*/tasks.json` + traces `.trace`, lidos read-only em 2026-06-19 com a
corrida ainda em progresso. **~70–72 tarefas COMPLETED por arm** (vs. 16 não-pareadas do smoke), 300 s, até
3 reps. Dedup por `(apk, arm, rep)`. Esta seção **supersede** os números do smoke usados em §0/§3/§4 para a
comparação `sata_mop` × `sata`.

### 10.1. A "regressão" do `sata_mop` é um EMPATE (pareado)

Agregado **não-pareado** (medianas por arm, enganoso — conjuntos de APK distintos por arm pois a corrida
está parcial):

```
arm                 n   meth_med  mop_med  act_med
ape                88     28.2     31.8    100.0
aperv:sata         72     33.3     38.6    100.0
aperv:sata_mop     72     32.8     33.3    100.0
aperv:sata_mop_llm 71     29.0     30.9     60.0
```

Análise **pareada** (mesmo `apk`+`rep` nos dois arms; Δ = B − A; empate = |Δ|≤0,5pp):

| Comparação | métrica | n | Δ mediana | Δ média | win/tie/loss |
|---|---|---|---|---|---|
| `sata_mop` − `sata` | cov_method | 72 | **+0,00** | −0,61 | 14 / **41** / 17 |
| `sata_mop` − `sata` | cov_mop    | 72 | **+0,00** | −0,12 | 12 / **46** / 14 |
| `sata_mop` − `ape`  | cov_method | 71 | +0,00 | +0,27 | 18 / 38 / 15 |
| `sata` − `ape`      | cov_method | 71 | +0,00 | +0,90 | 17 / 44 / 10 |
| `sata_mop_llm` − `sata_mop` | cov_method | 71 | −0,08 | **−3,23** | 9 / 32 / **30** |
| `sata_mop_llm` − `sata_mop` | cov_mop    | 71 | +0,00 | **−3,22** | 5 / 40 / **26** |

**Leitura:** a queda do smoke (`26,3→21,6`) **não se reproduz** no experimento maior — `sata_mop` ≈ `sata`
(Δmediana=0; 41–46 de 72 são **empates exatos**). Era artefato de n=16 + agregação não-pareada.

#### Comparação dos 4 arms no MESMO conjunto (70 pares `apk`+`rep` com todos os 4 COMPLETED)

Apples-to-apples (apenas APK+rep onde os 4 arms terminaram — n=70 de 90):

| Arm | cov_method (med) | cov_mop (med) | cov_act (med) | passos/tarefa (med) |
|---|---|---|---|---|
| `ape` (baseline) | 33,0 | 32,6 | 100,0 | 46 |
| **`aperv:sata`** (sem MOP) | **33,3** | **38,6** | 100,0 | 43 |
| `aperv:sata_mop` (com MOP) | 32,8 | 33,3 | 100,0 | 45 |
| `aperv:sata_mop_llm` (LLM+MOP) | 30,5 | 31,4 | 80,0 | 38 |

Quem **vence sozinho** cada tarefa (n=70; "vence sozinho" = melhor estrito, sem empate):

| Arm | melhor estrito em cov_method | melhor estrito em cov_mop |
|---|---|---|
| `ape` | 7 | 4 |
| **`aperv:sata`** | **12** | **9** |
| `aperv:sata_mop` | 11 | 9 |
| `aperv:sata_mop_llm` | 4 | 4 |

**Ranking (parcial): `sata` ≳ `sata_mop` ≈ `ape` > `sata_mop_llm`.**

- **`aperv:sata` (sem MOP) lidera** ou empata no topo — mais vitórias estritas (12/9) e maior `cov_mop`
  mediana (38,6).
- **MOP não agrega.** `sata_mop` ≈ `sata` em `cov_method` (empate pareado, 46/70 idênticos). Em `cov_mop` a
  coluna favorece `sata` (38,6 vs 33,3), e o pareado dá empate-com-leve-vantagem-pro-`sata` (12 W vs 14 L do
  `sata_mop`). Coerente com o scorer 100% inerte (B1).
- **`ape` e `sata_mop` empatam no meio**; o fork sem MOP (`sata`) está marginalmente acima do `ape` original.
- **`sata_mop_llm` é o pior em tudo** (latência — §10.3).
- **Incômodo para H2:** os dois arms que são a *contribuição* (`sata_mop`, `sata_mop_llm`) **não superam o
  controle puro `sata`** — um empata, o outro perde. Hoje o melhor sistema é o SATA sem extras.

### 10.2. Os empates exatos são a *assinatura mecânica* do B1 (scorer inerte)

Não é coincidência que 46/72 pares de `cov_mop` sejam idênticos: **se o scorer não faz nada, `sata_mop` ≡
`sata`**. Confirmado em escala nos traces:

- **72/72** traces `sata_mop` emitem linhas `MOP boost:` → `_mopData != null` em todos (a máquina MOP carrega
  e roda em 100% dos apps).
- **21.088 linhas de boost no total; ZERO com `maxBoost>0`** → o scorer é **100% inerte em todo o
  experimento**. Nenhum widget jamais recebeu boost positivo. (Confirma B1 + B-gran/B4 de §7/§9.6 no dataset
  grande, não só no smoke.)
- `MopData: loaded` aparece em 0/72 traces (artefato de captura — stdout do construtor não vai pro `.trace`;
  as 21k linhas de boost provam que o dado **está** carregado).

→ O **claim central H2 não tem benefício mensurável hoje**, mas **também não causa dano** (`sata_mop` empata
com `sata`). A calibração de `mop_weight_*` continua sendo "calibrar knobs mortos" (R1b').

### 10.3. A única regressão real é o arm LLM — mecanismo: LATÊNCIA, não decisão ruim

`sata_mop_llm` perde de forma consistente (−3,2pp em ambas as métricas; 26–30 derrotas vs. 5–9 vitórias). O
mecanismo é **orçamento de ações**, não qualidade das decisões:

- **Throughput**: `sata_mop_llm` executa **metade** dos passos de `sata_mop` no mesmo 300 s — mediana 143 vs.
  294 linhas de boost/tarefa (proxy de passos), razão mediana **0,50**, **68/71** tarefas com menos passos.
- **O LLM consome mediana 49% (até 69%) dos 300 s** só esperando o modelo (`time_ms` med ≈ 148 s de 300 s).
- **As decisões são boas**: `calls` med 122, `matched` med 92, `breaker_trips` med 0 (máx 1). Não é o circuit
  breaker, não é null em massa. Simplesmente cada passo custa ~1,2 s → menos exploração → menos cobertura.
  Com `llm_percentage=0.9` (90% dos passos via LLM), o efeito é direto.
- **2 falhas app-específicas reais** (não sistêmicas):
  - `bim.app_1500.apk` (3/3 reps): `calls=0` — o LLM nunca foi invocado (app não progride de estado). Este
    **é** o caso "0 chamadas LLM" que o mimo descreveu — real, porém **app-específico**, não o padrão.
  - `app.notesr_59.apk` (3/3 reps): `calls≈167–185` mas `matched=0` — **167× `LLM screenshot capture
    failed`**; sem imagem, nenhuma ação válida. Falha de captura de framebuffer desse app (provável
    `FLAG_SECURE`/SurfaceView), não do LLM.

**Implicação de desenho:** comparar `sata_mop_llm` por orçamento de *tempo* (300 s) penaliza o LLM pela
latência. Para isolar a qualidade das decisões do LLM, comparar por **orçamento de passos/ações** (igualar nº
de eventos) ou usar timeout maior. Caso contrário, o "LLM piora cobertura" mede latência de GPU, não a tese.

### 10.5. Telemetria por chamada LLM — confirma "latência, não timeout"

Telemetria `[APE-LLM-TEL]` dos traces (`time_ms` = latência ponta-a-ponta incl. ponte `socat`→SGLang).
Origem: memo paralelo `docs/20260619_debug_aperv_cobertura.md`; **todos os números abaixo reproduzidos
exatamente contra os dados crus** (7.640 chamadas em 71 traces, snapshot ~14%).

| Métrica | Valor | | Gatilho (`mode=`) | Chamadas |
|---|---|---|---|---|
| mediana | **1.144 ms** | | `random` (rolagem `llmPercentage=0.9`) | 6.912 (90,5%) |
| média | 1.264 ms | | `new-state` | 727 |
| p95 | 2.092 ms | | `stagnation` | 1 |
| p99 | 2.728 ms | | **`result=matched`** | 6.456 (84,5%) |
| máx | 9.321 ms (1 outlier) | | **`result=no_match`** | 1.184 (15,5%) |
| **timeouts (≥15 s)** | **0 de 7.640** | | ≥8 s | 2 (0,03%) |

**Leitura — reforça §10.3:**
- O `llm_timeout_ms=15000` **nunca** dispara (0/7.640; apenas 2 chamadas passaram de 8 s). A hipótese
  "chamadas estouram 15 s e degradam para `sata_mop`" está **descartada** — o mecanismo é o **custo cumulativo**
  de ~1,1 s/chamada × ~142 chamadas ≈ 156 s dentro dos 300 s, não estouros isolados.
- Sem contenção de GPU efetiva nesta janela (`#running-req ≤ 1` no `sglang-server`) — o risco previsto para H3
  não se materializou ainda.
- A taxa de 90% (`llm_percentage=0.9`) funciona: 90,5% das chamadas são `mode=random`. O gap até a proporção
  efetiva (~87,5% das ações via LLM) é o **`no_match` de 15,5%** — coordenada do Qwen3-VL que não casa com
  widget e é descartada (cai no SATA naquele passo).
- **Custo de oportunidade (corroborado por contagem independente):** tasks LLM-ativas ~142 ações/300 s vs.
  ~325 em SATA puro → **~2,3× menos ações**, consistente com a razão 0,50 medida via linhas de boost (§10.3).

**Reconciliação da anomalia dos 2 apps (corrige a conflação do memo):** o memo agrupa `bim.app_1500` e
`app.notesr_59` como "0 chamadas LLM". A telemetria por chamada (`[APE-LLM-TEL]`) é 0 nos dois, mas o
contador `LLM Summary calls=` distingue **dois mecanismos diferentes**:

| App | `Summary calls` | `screenshot failed` | `[APE-LLM-TEL]` | Mecanismo |
|---|---|---|---|---|
| `bim.app_1500` | **0** | 0 | 0 | LLM **nunca invocado** (app não progride de estado) — SATA puro real |
| `app.notesr_59` | **167** | **167** | 0 | LLM **tentado 167×**, todas abortam na **captura de tela** (`null=167`, nunca chega ao modelo) — **`FLAG_SECURE`** (confirmado no fonte, §10.6) |

Ambos terminam SATA-like, mas só `bim.app` é "0 chamadas"; `app.notesr` é uma **falha de screenshot** repetida.
A distinção importa para não inflar artificialmente o "SATA dentro do arm LLM".

### 10.6. Causa-raiz da falha de screenshot: `FLAG_SECURE` (verificado no código-fonte dos apps)

A falha de captura **não é bug do APE-RV** — é **degradação correta** diante de apps que bloqueiam screenshots.
`ScreenshotCapture.capture()` usa `SurfaceControl.screenshot()` (reflexão, API 29+); quando a janela tem
`WindowManager.LayoutParams.FLAG_SECURE`, o `SurfaceControl` **exclui a surface segura e retorna `null`**.
O `LlmRouter` então loga `LLM screenshot capture failed, skipping LLM step`, incrementa `nullCount` e cai no
SATA naquele passo (`LlmRouter.java:245-249`; `ScreenshotCapture.java` retorna `null` em vez de lançar —
javadoc explícito). Não há tela → não há prompt multimodal → o LLM **não pode agir** nesses apps.

**Apenas 2 apps do dataset disparam a falha** — e ambos são apps de privacidade/segurança (categoria
**super-representada** num benchmark JCA/cripto). Causa-raiz confirmada lendo o fonte
(`rvsec-testes-jca/sources/`):

| App | Onde está o `FLAG_SECURE` | Escopo | 1ª tela (launcher) segura? | Efeito observado |
|---|---|---|---|---|
| `app.notesr_59` | `ActivityBase.onCreate()` linhas 25-26 — `getWindow().setFlags(FLAG_SECURE, FLAG_SECURE)`, **incondicional** | **App-wide: 18/18 activities** (todas estendem `ActivityBase`; `MainActivity`=LAUNCHER inclusa) | **SIM** | **100% das chamadas falham** (167/167); LLM totalmente cego no app |
| `app.passwordstore.agrahn_11602` | `BasePGPActivity.onCreate()` linha 156 + diálogos `PinDialog`/`PasswordDialog`/`TextInputDialog`, **incondicional** | **Parcial**: só telas que estendem `BasePGPActivity` (`DecryptActivity`, `PasswordCreationActivity`, `AutofillDecryptActivity`) + diálogos | **NÃO** (`LaunchActivity` estende só `AppCompatActivity`) | **Falha parcial** (26 no total); LLM funciona na tela inicial, cego ao navegar para decrypt/PIN |

A assimetria **explica exatamente os números**: `notesr` é seguro desde a LAUNCHER → todas as 167 tentativas
falham; `passwordstore` só protege telas profundas → falhas esporádicas (26), e a maioria das chamadas funciona.

**Implicação (3º modo de degradação do arm LLM, ao lado de latência e B1):** a modalidade LLM tem um **ponto
cego sistemático** justamente em apps que usam `FLAG_SECURE` — password managers, apps de notas seguras,
carteiras — que são **frequentes em um benchmark de cripto/JCA**. Nesses apps o `sata_mop_llm` degrada
silenciosamente para `sata_mop`/SATA, sem nenhum sinal do LLM. Não é budget (latência) — é **limite de
capacidade**: sem screenshot, não há entrada multimodal. Possíveis mitigações (não implementar agora):
(a) fallback para representação textual da `GUITree` quando a captura retorna `null` (o LLM ainda poderia
decidir por árvore de acessibilidade); (b) detectar `FLAG_SECURE` e marcar o app como "LLM-incompatível" no
relatório, para não contar essas tasks como evidência do arm LLM; (c) excluir/anotar esses apps na análise
H3. **Para a estatística:** anotar os apps `FLAG_SECURE` (≥1 falha de screenshot) e tratá-los à parte ao
avaliar H3 — senão eles diluem o efeito do LLM com tasks que são SATA disfarçado.

### 10.4. Caveats — estes números são PRELIMINARES (não concluir ainda)

> **A corrida ainda está em andamento.** Estes resultados cobrem **~70 de ~507 tarefas/arm** (≈14% do
> alvo 169×3). São **parciais e preliminares** — servem para *direção* e *mecanismo*, **não** para
> conclusão. O experimento deve fechar **na manhã de 2026-06-20**; só então rodar a análise final.

**Checklist de fechamento (executar quando a corrida terminar):**
- [ ] Reexecutar §10.1 + §10.3 com n cheio (~507/arm) e reconfirmar empate `sata_mop`≈`sata` e déficit LLM.
- [ ] **Wilcoxon pareado** (signed-rank) para cada par de arms em `cov_method` e `cov_mop`; reportar p e
      tamanho de efeito. A leitura atual "empate" se apoia só em Δmediana=0 + 57–64% de empates exatos.
- [ ] **gh58:** validar as métricas do `tasks.json` contra as linhas `Coverage update` dos logcats antes de
      publicar magnitudes (tasks recuperadas por resume podem zerar no `tasks.json`).
- [ ] Confirmar que B1 (scorer 100% inerte) e a latência do LLM (½ dos passos) se mantêm no dataset completo.
- [ ] **Apps `FLAG_SECURE` (§10.6):** varrer `LLM screenshot capture failed` em todos os traces LLM, listar os
      apps afetados e **anotá-los/tratá-los à parte** na análise H3 (são SATA disfarçado no arm LLM). Hoje: só
      `app.notesr` (100% cego) e `app.passwordstore` (parcial) — reverificar no dataset completo.

Direção esperada (a confirmar): `sata` ≳ `sata_mop` ≈ `ape` > `sata_mop_llm`; MOP-guidance sem ganho
mensurável (scorer inerte); regressão real apenas no arm LLM, por latência.

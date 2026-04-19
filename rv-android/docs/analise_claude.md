# Análise: Change gh50-improve-instrumentation

**Data**: 2026-04-18
**Modelo**: Claude Opus 4.7 (1M context)
**Metodologia**: análise multidimensional via 4 subagentes paralelos (consistência de artefatos, impacto MOP, dados históricos + código, SDK + estado da arte)
**Caminho da change**: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh50-improve-instrumentation/`

---

## 1. Resumo executivo

A change `gh50-improve-instrumentation` propõe três modificações no pipeline AspectJ/d8 para aumentar a taxa de instrumentação de APKs: (1) `--no-desugaring` em d8, (2) `-proceedOnError` em ajc, (3) `-xmlConfigured` + `aop.xml` para excluir pacotes de bibliotecas do weaving. Os artefatos estão **bem construídos, rastreáveis e tecnicamente fundamentados**, com pequenas inconsistências (drift do baseline da gh49, divergência textual de line numbers) que não comprometem a qualidade.

A análise quantitativa dos erros (557 APKs ASE journal + 400 APKs F-Droid 2026) mostra que **as três correções têm impacto desigual e parcial**:

| Fix | APKs resgatados (estimativa) | Principal limitação |
|-----|------------------------------|---------------------|
| `--no-desugaring` | ~7-15% | Só resolve o bucket `j$.` (27+28+28 casos no ASE); NÃO resolve d8 AIOOE (215+185+21 casos) |
| `-proceedOnError` | ~5-10% | Com risco de cobertura silenciosamente parcial |
| `-xmlConfigured` + aop.xml | **Maior potencial no dataset novo** — até 30-37% de failures são stack-map warnings | Pode inflar o bucket "zero-pointcut match" (já afeta 32.5% de generic_new) |

**Taxa realista pós-fix**: JCA passa de 17.5% → ~33% (2x), generic_new de 54% → ~59%. O gap restante é dominado por (a) bug interno do d8/R8 (AIOOE em código crypto/okio) e (b) weaving de zero matches (que aop.xml pode piorar) — **nenhum dos dois é endereçado por gh50**.

O impacto das exclusões sobre as 168 specs MOP analisadas (100% usando `call()` no site do caller) é **aceitável e favorável à pesquisa**, pois: (i) código de aplicação Android não reside nos pacotes excluídos, (ii) Coverage.aj já estabelece o mesmo escopo para cobertura, e (iii) o objetivo da tese é detectar misuse em código de app, não em bibliotecas.

**Recomendação final**: aprovar a change com **ajustes** (ver seção 10), mas **não** como silver bullet — gh50 reduz o gap mas não o fecha. Ações complementares necessárias (não cobertas por gh50): seleção dinâmica de android.jar, `--min-api` dinâmico, investigação do bug d8 AIOOE (issue separada), e fallback de pré-filtragem Python se `-xmlConfigured` não prevenir frame corruption (já antecipado no proposal).

---

## 2. Análise de consistência dos artefatos

### 2.1 Rastreabilidade proposal → spec → design → tasks

**Proposal → Delta Spec (capabilities)** — **PASS com nota**.

O proposal lista 5 mudanças (`proposal.md:7-11`): d8 `--no-desugaring`, ajc `-proceedOnError`, `-xmlConfigured`+aop.xml, YAML configurável, pre-filtering fallback (condicional). Os primeiros 4 mapeiam para INV-INS-13..16; o pre-filtering é explicitamente marcado como "conditional" (`design.md:52`, "Non-Goal") e não aparece na delta spec — decisão correta, pois está contingente em resultado empírico.

**Delta Spec → Design mapping table** — **PARTIAL PASS**.

| Invariant/Requirement | Design table row | Tasks |
|-----------------------|------------------|-------|
| INV-INS-13 (`--no-desugaring`) | row 1 | tasks.md:15 (2.1), 2.4 |
| INV-INS-14 (`-proceedOnError`) | row 2 | tasks.md:16 (2.2), 2.4 |
| INV-INS-15 (`_generate_aop_xml`) | row 3 | tasks.md:5, 17, 1.4 |
| INV-INS-16 (YAML default) | row 4 | tasks.md:3, 4, 1.4 |
| Backward compat | row 5 | tasks.md:22 |
| gh49 merge_support | row 6 | — ("already implemented") |

Os **8 cenários FR02 preservados** do baseline não aparecem explicitamente na mapping table. Aceitável (são unchanged from baseline) mas **recomendável** adicionar uma linha "Preserved FR02 scenarios (8) — unchanged from baseline" para rastreabilidade explícita.

Tasks 3.x (empirical validation) e 4.x (verification) não mapeiam a invariantes — são tasks de workflow padrão. OK.

### 2.2 Consistência com specs existentes

**Header do requirement MODIFIED** — **PASS**. Delta (`spec.md:17`) e baseline (`specs/instrumentation/spec.md:330`) batem exatamente: `### Requirement: APK Instrumentation with Monitors (FR02)`.

**Cenários FR02 completos** — **PASS na completude, MINOR FAIL textual**.

Os 8 cenários do baseline estão todos presentes na delta:
1. Successful single APK instrumentation (delta line 89)
2. Skip existing instrumented APK (line 96)
3. Force re-instrumentation (line 102)
4. Pipeline phase failure with accurate phase reporting (line 109)
5. Batch instrumentation with mixed results (line 118)
6. dex2jar conversion failure with phase from outer decorator (line 127)
7. Instrumentation verification detects unchanged APK (line 136)
8. Maven dependency resolution failure (line 141)

Plus 4 cenários novos (3 para INV-INS-13..15 + 1 backward compat).

**Divergência textual** encontrada: baseline scenario #6 cita `"propagates to instrument()'s except block (line 517), which re-raises"`; a delta remove `(line 517)`. Isto é uma **melhoria P4** (remover line numbers voláteis) mas cria diff silencioso não sinalizado. Decisão: aceitar como cleanup deliberado, ou restaurar line numbers para match exato.

**INV-INS-13..16 IDs** — **PASS**. Baseline tem INV-INS-01..12; os novos IDs (13..16) continuam sem colisão.

**Incorporação de gh49 (reraise=True, _error_phase, __merge_support_classes)** — **FAIL (do gh49, não de gh50)**.

- Delta spec (line 49) inclui `__merge_support_classes()` na enumeração de reraise=True — **correto**.
- Baseline spec (line 345) NÃO lista `__merge_support_classes()` — **deveria**, pois o commit `a05b5cfe docs(gh49): archive change, sync delta specs to main specs` declara que a sync foi feita.

**Ação recomendada**: antes de abrir PR da gh50, investigar se o `opsx:sync` do gh49 de fato aplicou completamente sobre FR02. A delta de gh50 está correta; o baseline é que está desatualizado.

`_error_phase` e `reraise=True` estão corretamente em ambos.

### 2.3 Consistência técnica

**`-xmlConfigured` aceita path direto** — **PASS**.

Fonte oficial: [AspectJ ajc manual](https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html):

> "There is no magical file name like aop.xml for LTW, i.e. an XML configuration file for CTW needs to be specified on the command line explicitly."

Isto confirma `design.md:68` e INV-INS-15: o arquivo pode estar em `tmp_dir/aop.xml` (sem `META-INF/`) desde que o path seja passado explicitamente.

**Complementaridade `aop.xml` vs `Coverage.aj`** — **PASS com nuance técnica importante**.

- **Pointcut-level exclusion** (Coverage.aj `within(...)`): o weaver lê a classe, avalia pointcuts, decide que não há match, reescreve. Stack map frames podem ser corrompidas nesse read-write cycle.
- **Weaver-level exclusion** (`aop.xml` `<exclude within="..."/>`): classes são totalmente puladas pelo weaver — não lidas, não processadas, não reescritas. Bytecode passa intocado.

O design assume que o weaver-level previne frame corruption onde o pointcut-level não preveniu. **Tecnicamente correto**, mas com ressalva: em algumas versões do ajc, classes excluídas ainda podem ser lidas do `-inpath` antes da regra de exclusão ser aplicada. Este risco está corretamente capturado em `design.md:140` (Risk 2) e como fallback condicional no proposal — **gestão de risco adequada**.

Fontes:
- [AspectJ ajc manual](https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html)
- [AspectJ LTW configuration](https://eclipse.dev/aspectj/doc/released/devguide/ltw-configuration.html)

### 2.4 Formato e completude

| Check | Status | Evidência |
|-------|--------|-----------|
| Cenários usam `####` | PASS | Verificado em lines 53, 59, 66, 83, 89, 96, 102, 109, 118, 127, 136, 141 |
| WHEN/THEN/AND com valores concretos | PASS | Ex.: scenario d8 inclui string exata `"Merging DEX file containing classes with prefix 'j$.'"` |
| Tasks `- [ ] X.Y` | PASS (com nota) | Sub-bullets sob 1.4/2.4 não usam `- [ ]` — aceitável mas inconsistente |
| Invariantes com testes | PASS | Os 4 novos invariants têm test explícito em mapping table |

### Veredicto da Seção 2: **PASS com minor issues**

Issues consolidadas (por severidade):

1. **MINOR (drift baseline da gh49)**: baseline `specs/instrumentation/spec.md:345` não lista `__merge_support_classes()` apesar de gh49 ter feito sync. **Ação**: verificar/reaplicar sync da gh49.
2. **MINOR (divergência textual)**: cenário dex2jar remove `(line 517)` — aceitar como cleanup ou restaurar para match exato.
3. **MINOR (estilo)**: sub-bullets em 1.4/2.4 sem `- [ ]`.
4. **OBSERVATION**: mapping table não lista cenários FR02 preservados. Recomenda-se adicionar linha "Preserved scenarios (8)".

Nenhum issue bloqueante. Os 4 novos invariantes são bem formados, rastreáveis e testados. A fundamentação técnica de `-xmlConfigured` está validada por documentação oficial.

---

## 3. Análise de impacto das exclusões sobre specs MOP

### 3.1 Levantamento das 168 specs nos 3 conjuntos

**JCA** (23 specs em `/rvsec/rvsec-mop/src/main/resources/jca/`):
- **100% pointcuts `call()`** (nenhum `execution()`)
- Exemplos (verbatim):
  - `CipherSpec.mop` g1: `call(public static Cipher Cipher.getInstance(String)) && args(transformation) && condition(isValid(transformation))`
  - `MessageDigestSpec.mop` update: `call(void MessageDigest.update(..)) && target(digest)`
  - `KeyGeneratorSpec.mop` gk1: `call(public SecretKey KeyGenerator.generateKey()) && target(k)`

**generic** (118 specs FSM1.mop .. FSM376.mop):
- **100% `call()`**
- Exemplos:
  - `FSM1.mop` (ReentrantLock): `call(* ReentrantLock.unlock()) && target(r)`
  - `FSM17.mop` (AbstractMap): `call(* AbstractMap.put(Object, Object)) && target(a) && args(o, o1)`
  - `FSM101.mop` (Future): `call(* Future.isDone()) && target(f)`
  - `FSM254.mop` (CountDownLatch): `call(* CountDownLatch.await(long, TimeUnit)) && target(c) && args(t)`

**generic_new** (27 specs com nomes descritivos):
- **100% `call()`**
- Exemplos:
  - `InputStream_ManipulateAfterClose.mop`: `(call(* InputStream+.read(..)) || call(* InputStream+.available(..))) && target(i) && !target(ByteArrayInputStream)`
  - `Closeable_MeaninglessClose.mop`: `call(* Closeable+.close()) && (target(ByteArrayInputStream) || target(ByteArrayOutputStream) || ...)`
  - `Map_UnsafeIterator.mop`: `call(Set Map+.keySet()) || call(Set Map+.entrySet())`

**Confirmação via grep sobre os 3 diretórios**:
- Specs com `execution()`: **0**
- Specs com `call()`: **168 (100%)**
- Specs com `within()` de exclusão explícita: **0**

### 3.2 Impacto das exclusões por spec set

A semântica `call()` intercepta no **caller site**. Se o chamador estiver em pacote excluído, a chamada não é monitorada.

| Padrão de exclusão | Invasividade | Justificativa |
|--------------------|--------------|---------------|
| `kotlin..*` | **ALTA** para generic_new | Stdlib Kotlin usa `Iterator`, `Map`, `Collection`, `Closeable` massivamente |
| `androidx..*` | **MÉDIA-ALTA** | Componentes usam `Future`, `ReentrantLock`, `InputStream` |
| `com.google..*` (Guava, Gson, Play) | **MÉDIA** | Guava chama `AbstractMap`/`TreeMap`; Play Services chama JCA |
| `com.squareup..*` (OkHttp/Retrofit) | **MÉDIA** | Usam `SSLContext`, `InputStream`, `URLConnection` |
| `org.apache..*` | **BAIXA-MÉDIA** | Legado; apps novos raramente dependem |
| `j$..*` | **IRRELEVANTE** | Stubs de desugaring, sem lógica |
| `com.android..*`, `android..*` | **BAIXA** | Já excluídos por Coverage.aj; essencialmente sistema |

**Estimativa quantitativa de perda de detecções**:
- **JCA**: ~<5% (APIs crypto raramente chamadas internamente por libs não-crypto; quando o são, não é alvo da pesquisa)
- **generic**: ~15-25% (muitas specs monitoram APIs usadas por frameworks)
- **generic_new**: ~25-40% (maior vulnerabilidade — monitora APIs de uso geral ubíquas em libs)

**Observação crucial sobre Kotlin**: código escrito pelo dev em Kotlin compila para o package do app (ex.: `com.example.myapp.*`), NÃO para `kotlin..*`. O namespace `kotlin..*` contém apenas a runtime library. Portanto, código de negócio em Kotlin permanece entrelaçado — as exclusões afetam apenas chamadas internas da stdlib.

### 3.3 Interação com Coverage.aj

`Coverage.aj` já exclui via `within(...)` em `excludedPackages()`: `java..*`, `javax..*`, `android..*`, `androidx..*`, `kotlin..*`, `com.google..*`, `com.google.android..*`, `com.android..*`, `com.facebook..*`, `org.apache..*`, `sun..*`, `libcore..*` e runtime JavaMOP.

**Sobreposição com aop.xml proposto**: `androidx..*`, `kotlin..*`, `com.google..*`, `com.android..*`, `com.facebook..*`, `org.apache..*` já estão em **ambos**.
**Novos padrões da aop.xml** (não no Coverage.aj): `com.squareup..*`, `j$..*`, específicos do YAML.

**Consequência semântica**: hoje, Coverage.aj não conta métodos de `androidx..*` como "cobertos", mas specs MOP **ainda detectam** violações nessas libs. Com a aop.xml, **nem cobertura nem detecção MOP** ocorrem para classes excluídas. **Comportamento fica consistente** — bibliotecas ficam totalmente fora do escopo de análise.

**Isso é desejável?** Para a pesquisa sim: há **inconsistência atual** (cobertura ignora libs, mas MOP detecta violações nelas). A mudança alinha ambos. O sinal perdido (violações em libs) já era descartado pelo filtro de cobertura, e bugs em `androidx`/`kotlin`/`com.google` não são responsabilidade do desenvolvedor do app.

### 3.4 Trade-off analysis

| Dimensão | Antes (sem aop.xml) | Depois (com aop.xml) |
|----------|---------------------|----------------------|
| Taxa de instrumentação JCA | 17.5% | ~33% (estimativa realista) |
| Taxa de instrumentação generic_new | 54% | ~59% |
| Detecções MOP em libs | Incluídas (mas ruído) | Excluídas |
| Consistência com Coverage.aj | Inconsistente | Alinhada |
| Escopo da análise | Misto | App-code-only |

O trade-off é **amplamente positivo**:
- **Ganho**: 2-4x mais APKs utilizáveis → validade estatística dos experimentos.
- **Perda**: detecções fora do escopo da pesquisa (ruído).
- **Consistência**: pipeline passa a ter semântica uniforme.

**Caveat metodológico (registrar na tese)**: as exclusões são uma **decisão de escopo explícita** — análise cobre código de aplicação, não bibliotecas. Isto é padrão em literatura de análise Android (CogniCrypt, CrySL) — limitação documentada, não defeito.

### Veredicto da Seção 3: **ACEITÁVEL**, fortemente favorável à pesquisa

Justificativas:
1. 100% das 168 specs usam `call()` — semântica de caller-site suporta a exclusão.
2. Código do app não está nos packages excluídos.
3. Coverage.aj já estabelece o mesmo padrão de escopo.
4. Objetivo da tese alinha com escopo "código do desenvolvedor".
5. Trade-off quantitativo favorável (+200-400% APKs vs. 5-40% detecções em libs fora do escopo).

**Ressalvas a registrar**:
- Tornar `weaving_excludes.yaml` configurável (já contemplado) para experimentos com escopo diferente.
- Documentar na tese/paper como threats to validity: `URLEncoder_EncodeUTF8` e `Closeable_MeaninglessClose` sofrem maior perda relativa.
- Se `-xmlConfigured` sozinho não prevenir frame corruption, o fallback Python de pré-filtragem (já previsto em proposal) é necessário.

---

## 4. Android SDK e compatibilidade

### 4.1 Inventário do SDK instalado

**Local**: `/home/pedro/desenvolvimento/aplicativos/android/sdk/`

| Componente | Versões instaladas | Projeto usa |
|------------|---------------------|-------------|
| platforms/ | android-4, 10, 14-19, 21-34 (sem 20, 35) | **android-29** (fixo) |
| build-tools/ | 25.0.2..35.0.1 (16 versões) | d8 de 35.0.1 (`D8 8.6.2-dev`) |
| cmdline-tools/ | 9.0, 10.0, 11.0 (latest) | - |

**Docker (`phtcosta/rvandroid_tools:0.8.0`)** — cadeia de 3 camadas:
1. `rvsec_base`: Python 3.12, JDK 25.0.2, Maven 3.9.14, **AspectJ 1.9.24**, uv
2. `rvsec_android`: Android SDK com `build-tools;35.0.1`, `platforms;android-10..35`, cmdline-tools `8512546_latest`, AVD "RVSec"
3. `rvandroid_tools`: droidbot, androguard 3.4.0a1

Docker e host **alinhados** em build-tools 35.0.1 / d8 8.6.2-dev.

### 4.2 Seleção dinâmica de `android.jar` por targetSdkVersion

**Situação**: `RVInstrumentationConfig` hardcoda `android_platform = "android-29"` (`config.py:444`). Também TODO(#23) em `rvandroid.py:1159` pede exatamente isto.

**Quando causa falha**:
- APK referencia classes novas do framework (ex.: `android.window.SplashScreen` em API 31+) → ajc compila "binary weaving" contra bootclasspath fornecido → classe ausente → erro.
- APIs Java ampliadas em API 30+ (`Duration.toSeconds()` etc.) podem disparar mismatches.

**Para d8, não importa**: `--lib` serve apenas como dicionário de desugaring ([d8 docs](https://developer.android.com/tools/d8), [dotnet/android D8andR8 guide](https://github.com/dotnet/android/blob/main/Documentation/guides/D8andR8.md)). AAPT2 não é invocado no pipeline (o APK é recompilado via substituição de classes.dex).

**Recomendação**: implementar seleção dinâmica baseada em `apk.targetSdkVersion` (já extraído por androguard). Fallback: `max(android-XX disponível)`. **Não requer rebuild Docker** — todos os platforms já estão instalados.

### 4.3 `--min-api` dinâmico

**Situação**: fixo em 26 (`rvandroid.py:1011-1012`).

**Efeito de `--min-api N`**: com N maior, d8 emite menos código de compatibilidade (menos desugaring code), DEX menor, potencialmente menos superfície para stack-map issues ([Jake Wharton — Android's Java 8 Support](https://jakewharton.com/androids-java-8-support/)).

**Se APK tem `minSdkVersion=30`, usar `--min-api 30`**:
- DEX menor
- Menos stack-map warnings (reduz incidência do padrão observado em [didi/DroidAssist#38](https://github.com/didi/DroidAssist/issues/38) e [growingio#90](https://github.com/growingio/growingio-sdk-android-autotracker/issues/90))

**Cuidado**: nunca regredir abaixo de 26 (preserva invariantes assumidos pelo AspectJ 1.9.24 weaver). Fórmula segura: `--min-api = max(26, apk.minSdkVersion)`.

### 4.4 Atualização de build-tools

- **Latest publicado**: build-tools 36.0.0 (AGP 9.0.1 default) / 36.1.0 (AGP 9.1).
- **Instalado**: 35.0.1 (jan/2025).
- **Release notes sobre stack maps**: **nenhuma referência explícita** em 35.0.x → 36.0.0. Mudanças em AGP 9.0/9.1 são sobre L8 desugaring e repackaging, não stack map handling.
- **Benefício vs atual**: **marginal**. d8 8.6.2-dev de 35.0.1 já é moderno. O problema de stack map é causado pelo bytecode **pré-d8** (gerado pelo ajc após weaving), não por regressão do d8.

**Recomendação**: **não** priorizar update. Considerar apenas se evidência empírica mostrar benefício.

### 4.5 Impacto na imagem Docker

| Mudança | Rebuild Docker? | Esforço |
|---------|------------------|---------|
| Seleção dinâmica de android.jar | **Não** (platforms já instalados) | Baixo (~1-2 dias código Python) |
| `--min-api` dinâmico | **Não** | Baixo (~0.5 dia) |
| dex2jar 2.4 | Talvez (pom ou script) | Baixo |
| build-tools 36.x | Sim (1 camada) | Médio (~15-30 min rebuild) |

---

## 5. Estado da arte

### 5.1 AspectJ + Android

**Ecosystem status (2026)**:
- [HujiangTechnology/gradle_plugin_android_aspectjx](https://github.com/HujiangTechnology/gradle_plugin_android_aspectjx) — **arquivado** (dependente de Transform API, removida no AGP 8.0).
- Fork ativo: [wurensen/gradle_plugin_android_aspectjx](https://github.com/wurensen/gradle_plugin_android_aspectjx) — migrou para ASM instrumentation API do AGP.
- [Ibotta/gradle-aspectj-pipeline-plugin](https://github.com/Ibotta/gradle-aspectj-pipeline-plugin) — mais moderno; usa ASM API.
- [JD Porterfield blog](https://jdvp.me/articles/Switching-AspectJ-Plugins-Android) confirma migração geral dos plugins "jx" para ASM API.

**Pipeline do RV-Android (dex2jar → ajc → d8)** é **fora da corrente principal**. A comunidade moderna integra-se ao build Gradle do app e atua sobre `.class` antes do d8. A escolha do RV-Android é **correta** para o caso de uso (sem acesso a source/build do app sob teste), mas tem pouco suporte da comunidade para resolver stack map issues.

**`-xmlConfigured` em CTW** ([AspectJ LTW chapter](https://eclipse.dev/aspectj/doc/released/devguide/ltw.html)): primariamente desenhado para LTW (load-time). Em CTW pode controlar precedência e escopo via `<include within>`/`<exclude within>`. **Não afeta stack map generation**.

**AspectJ 1.9.24** é a última versão (out/2024) — [Maven Central](https://mvnrepository.com/artifact/org.aspectj/aspectjtools/1.9.24). Nenhum issue aberto específico em [eclipse-aspectj/aspectj](https://github.com/eclipse-aspectj/aspectj) sobre stack map + Android. `StackMapAdder.java` ainda delega geração ao ASM após weaving — melhorias históricas pontuais.

### 5.2 d8/R8

**`--no-desugaring` com `--min-api 26`** — **seguro** no contexto do RV-Android:
- [d8 docs](https://developer.android.com/tools/d8): `--no-desugaring` força desugar off.
- Com `--min-api 24+`, lambdas já não são desugared nativamente ([Jake Wharton](https://jakewharton.com/androids-java-8-support/)).
- APKs processados pelo pipeline são **produtivos** (já dexificados antes) → raramente usam APIs Java 8+ não-desugaradas.

**`--debug` vs `--release`**: nenhuma documentação oficial descreve divergência em stack map validation. Empiricamente ([bazel #15751](https://github.com/bazelbuild/bazel/issues/15751)): d8 loga warnings em ambos modos mas tolera; aborta apenas em casos extremos.

**Tolerância recente de d8 a stack maps inválidos**: **sem release note específica**. A melhoria necessária é upstream no ajc, não no d8.

### 5.3 Alternativas ao dex2jar

- **google/enjarify**: **arquivado em 29/dez/2022** ([github.com/google/enjarify](https://github.com/google/enjarify)). Fork [Storyyeller/enjarify](https://github.com/Storyyeller/enjarify) também pouco ativo. **Não viável em 2026**.
- **pxb1988/dex2jar v2.4** (3/out/2024): [release notes](https://github.com/pxb1988/dex2jar/releases/tag/v2.4) — "bugfix". **Estado da arte**.
- **jadx, apktool**: decompiladores para engenharia reversa, não DEX→JAR para recompilação.

**Ação recomendada**: verificar versão atual do dex2jar usada pelo projeto. Se < 2.4, **atualizar é win barato**.

### 5.4 Runtime verification em Android (2024-2026)

- **AspectJ** é padrão histórico com limitações conhecidas: "restricted join point model and the inability of weaving certain classes, particularly the Java and Android class libraries" ([HAL paper](https://inria.hal.science/hal-03533152/document)).
- **DiSL**: "ensures weaving with complete bytecode coverage for Java and Android". Compilador AspectJ → DiSL existe, permitindo reuso das specs atuais. Alternativa viável se cobertura em libs tornar-se crítica.
- **BISM** ([Springer 2020](https://link.springer.com/chapter/10.1007/978-3-030-60508-7_18); DSL extension [Springer 2023](https://link.springer.com/chapter/10.1007/978-3-031-44267-4_17)): "bytecode-level instrumentation, lightweight, expressive high-level language". Outperforma DiSL e AspectJ em benchmarks. **Não nativo Android** — adaptar demandaria porta para DEX pipeline.
- **TraceMOP**: sem evidência de atividade em 2024-2026. JavaMOP/RV-Monitor continua sendo a base.

**Conclusão**: **nenhuma alternativa em 2026 é drop-in replacement** para o pipeline atual. BISM é a direção de ponta mas custo de adaptação é alto. Para deadline 2026-04-13, o caminho pragmático é a melhoria incremental proposta em gh50.

---

## 6. Análise quantitativa de impacto (dados históricos)

### 6.1 Dataset A — ASE journal (557 APKs, 2025)

| Categoria de erro | JCA | % | generic | % | generic_new | % | Fix alvo |
|-------------------|-----|---|---------|---|-------------|---|----------|
| d8 AIOOE (bug r8/d8 interno) | 215 | 59.1% | 185 | 52.6% | 21 | 11.1% | **NENHUM** |
| ajc Kotlin `Function3` paramtype | 62 | 17.0% | 62 | 17.6% | 63 | 33.3% | `-proceedOnError` (parcial) |
| ajc internal (SO, BCException) | 46 | 12.6% | 53 | 15.1% | 44 | 23.3% | `-proceedOnError` (parcial) |
| `j$.` desugared DEX merge | **27** | **7.4%** | **28** | **8.0%** | **28** | **14.8%** | `--no-desugaring` ✓ |
| d8 stack-map warnings | 11 | 3.0% | 16 | 4.5% | 24 | 12.7% | `-xmlConfigured` (parcial) |
| Outros | 3 | 0.8% | 8 | 2.3% | 9 | 4.8% | misto |
| **Total erros** | **364** | 100% | **352** | 100% | **189** | 100% | |
| **Sucesso (557 - erros)** | 193 | 34.6% | 205 | 36.8% | 368 | 66.1% | |

**Finding crítico**: dos 234 casos d8 AIOOE totais (215 JCA + 185 generic + 21 generic_new — não deduplicado entre specs), **nenhum** menciona `j$.` na mensagem de erro (verificado via grep). É um bug distinto de r8/d8 8.2.2-dev acionado em padrões de bytecode específicos. Concentração forte em classes crypto (okio HMAC, BouncyCastle, SpongyCastle, PBKDF2, AESObfuscator). **`--no-desugaring` NÃO resolve estes casos.**

Exemplos de mensagens (truncadas):
- d8 AIOOE: `Error in ...okio/Buffer.class at Lokio/Buffer;hmac(...): java.lang.ArrayIndexOutOfBoundsException: Index -1 out of bounds for length 0`
- j$.: `Error: com.android.tools.r8.internal.Sb: Merging DEX file containing classes with prefix 'j$.' with other classes, except classes with prefix 'java.', is not allowed`
- ajc Kotlin: `Type 'kotlin.jvm.functions.Function3' [error] Mismatch when building parameterization map`
- ajc code 255: `Internal compiler error: java.lang.StackOverflowError at org.aspectj.weaver.UnresolvedType.signatureToName(UnresolvedType.java:636) ABORT`

### 6.2 Dataset B — F-Droid 2026 (400 APKs)

| Categoria (tool, code) | JCA | % | generic_new | % | Fix alvo |
|------------------------|-----|---|-------------|---|----------|
| d8 code=0 (stack-map warnings) | 151 | 37.75% | 123 | 30.75% | `-xmlConfigured` (parcial) |
| d8 code=1 (hard fail — AIOOE/j$./lambda) | 122 | 30.5% | 48 | 12.0% | parte `--no-desugaring`; parte nenhum |
| ajc code=255 (abort interno) | 47 | 11.75% | 10 | 2.5% | `-proceedOnError` (parcial) |
| ajc code=2 | 6 | 1.5% | 1 | 0.25% | `-proceedOnError` (parcial) |
| ajc outros | 2 | 0.5% | 3 | 0.75% | `-proceedOnError` (parcial) |
| dex2jar fail | 3 | 0.75% | 1 | 0.25% | NENHUM |
| **instrumentation_verification = -1** (zero matches) | 0 | 0.0% | **130** | **32.5%** | aop.xml **irrelevante ou prejudicial** |
| **APK produzido (sucesso)** | **70** | 17.5% | **216** | 54.0% | |
| **Em pasta final (pós-filtro)** | **38** | 9.5% | **64** | 16.0% | |

Dataset F-Droid confirma APKs modernos: 379/400 updated in 2026, 21/400 in 2025.

**APKs em categorias NÃO endereçadas por gh50**:
- **NEW-JCA**: d8 code=1 hard fails (122 APKs, 30.5%) + dex2jar (3) → **~31% sem cobertura da fix**.
- **NEW-GENERIC_NEW**: instrumentation_verification=-1 (130 APKs, **32.5%**) + d8 code=1 parte (48) + dex2jar (1) → **~45% sem cobertura**. O bucket de "zero pointcut matches" **pode piorar** com aop.xml.

### 6.3 Estimativa de melhoria pós-fix

| Spec set | Baseline | Best case | Likely | Worst case |
|----------|----------|-----------|--------|------------|
| JCA | 17.5% (70/400) | ~48% (192/400) | **~33% (132/400)** | ~22% (88/400) |
| generic_new | 54% (216/400) | ~65% (260/400) | **~59% (236/400)** | ~54% (216/400) |

**Cenário "likely" (JCA)**:
- `--no-desugaring`: +27 APKs (bucket j$. do ASE — boa proxy)
- `-proceedOnError`: +20 APKs (ajc 255 quando um aspecto falha mas outros passam)
- `-xmlConfigured`: +15 APKs (subset dos 151 stack-map cujo warning origina de libs excluíveis)
- Ganho ≈ 62. Total: 132/400 = **33%** (2× baseline).

**Cenário "likely" (generic_new)**:
- `-proceedOnError`: +14 APKs (todas as 14 falhas ajc)
- `--no-desugaring` + `-xmlConfigured`: +10-20 APKs juntos
- Ganho ≈ 20. Total: 236/400 = **59%**.

**Comparação old vs new**:
- Proporção de falhas d8 aumentou drasticamente: OLD 69% / NEW 83% (JCA).
- Stack-map warnings saltaram de 3% → 37.75% (JCA). **`-xmlConfigured` é mais valioso para APKs modernos**.
- ajc failures diminuíram (bug Kotlin `Function3` sendo corrigido upstream). `-proceedOnError` é **menos valioso para dataset novo**.
- `--no-desugaring` é **mais valioso para modern** (mais surface de desugaring conflict com AGP 8.x+).

### 6.4 Código: integração e gaps

**`rvandroid.py` — integrações**:
- `__d8` (linhas 1004-1014): `--no-desugaring` entra limpo; semanticamente seguro com `--min-api 26` hardcoded.
- `__weave_monitors` (linhas 801-816): `-proceedOnError` mecanicamente trivial. **Concern**: com proceedOnError, ajc sai com código 0 mesmo tendo emitido errors. Safety net atual = `check_if_instrumented` (linhas 1217-1264) via hash. **Safety net permanece válido** (detecta no-op weaving) **mas não detecta cobertura semanticamente parcial** (weaver produz modified APK que passa o hash, mas os aspects de interesse falharam).
- `aop.xml` generation: não trivial (~50 LOC novo). Requer ler lista de globs do config, gerar `{tmp_dir}/META-INF/aop.xml` (ou path direto via `-xmlConfigured`), listar aspect names (dependência nova: rv-monitor-generator output). Integração limpa via novo `__prepare_aop_xml()` antes de ajc.

**`config.py` — campos novos necessários**:
1. `no_desugaring: bool = Field(default=True, ...)` — win puro com min-api ≥ 24.
2. `ajc_proceed_on_error: bool = Field(default=False, ...)` — default False pelo risco; opt-in per experiment.
3. `aop_xml_excluded_packages: List[str] = Field(default_factory=list, ...)` — empty default mantém backward compat.
4. `@validated_model` decorator: não precisa update (campos novos são bool/list sem path validation).
5. `ConfigurationSummary.get_configuration_summary()` (linha 679): deve expor novos flags para reprodutibilidade.

**TODOs pré-existentes em `rvandroid.py`** (todos referenciando issue #23):
- Linha 707: Classpath com Android SDK JAR dinâmico.
- Linha 887: zipalign optimization.
- Linha 1159: android.jar dinâmico por targetSdkVersion (comentado há implementação de referência).

**Gaps relevantes para gh50**:
- `--min-api 26` hardcoded → impede usar `--no-desugaring` condicionalmente se min-api < 24 (hipotético).
- `android_platform="android-29"` hardcoded → causa ajc fail em APKs com APIs novas.
- Sem mecanismo para injetar arquivos em `tmp_dir` antes de ajc (necessário para aop.xml).
- `__d8` não expõe error output → sem hook diagnóstico para distinguir "AIOOE não endereçável" de "j$. corrigível". Considerar adicionar `failure_category` classificador.
- `check_if_instrumented` usa hash de arquivo; com `-proceedOnError`, weaver que drop todos aspects para uma classe ainda muda bytecode (ajc reordena constants), fazendo o hash ainda mudar. **Detecção de cobertura semanticamente parcial exigiria grep por símbolos rv-monitor no classes.dex produzido** (não está no escopo de gh50 mas deve ser flagged).

---

## 7. Riscos e mitigações

### 7.1 Riscos por mudança proposta

| Mudança | Risco | Probabilidade | Impacto | Mitigação |
|---------|-------|---------------|---------|-----------|
| `--no-desugaring` | APK com `--min-api` < 24 usando API Java 8+ quebra em runtime | Muito baixa (hardcoded em 26) | Baixo (APKs produtivos já desugared antes) | Manter `--min-api` ≥ 26; adicionar assertion em `__d8` |
| `--no-desugaring` | Não resolve d8 AIOOE (234 casos no ASE, ~30% no novo) | **Alta** (evidência empírica) | **Alto** — fix resolve só ~7-15% | Documentar como limitação conhecida; abrir issue separada para d8 AIOOE |
| `-proceedOnError` | Cobertura silenciosamente parcial (ajc aborta aspects específicos mas continua) | **Média** | **Médio** — resultados experimentais podem ser degradados sem saber | Logar todos os errors do ajc; adicionar verificação de símbolos rv-monitor no DEX produzido |
| `-proceedOnError` | Bug ajc genuíno mascarado como "weave parcial" | Média | Médio | Limitar proceedOnError a bugs conhecidos (ex.: Function3); revisar stderr em cada run |
| `-xmlConfigured` + aop.xml | ajc ainda lê classes excluídas via `-inpath` antes de aplicar regra | Média | Alto se ocorrer | Fallback de pré-filtragem Python (já previsto em proposal.md:11) |
| `-xmlConfigured` + aop.xml | Pode inflar bucket "zero pointcut matches" (já 32.5% de generic_new) | **Média-alta** | **Alto para generic_new** | Configurar aop.xml conservadoramente por spec set; validar empiricamente por spec set |
| `-xmlConfigured` + aop.xml | Monitor aspects precisam ser listados explicitamente (nova dependência de rv-monitor-generator) | Baixa | Médio | Gerar lista de aspects dinamicamente em `__prepare_aop_xml` |
| YAML `weaving_excludes.yaml` configurável | Sem validação → padrões errados silenciam monitoramento do próprio app | Baixa | Alto | Validar em `_validate_configuration` que nenhum padrão cobre pacote do app sob teste |
| Não implementar pre-filtering | Se `-xmlConfigured` sozinho não prevenir frame corruption, gh50 não entrega | Média | Alto | Já previsto como fallback condicional — executar validação empírica em 3.x antes de fechar a change |

### 7.2 Riscos cruzados

- **`-proceedOnError` + `aop.xml`**: combinados, ajc pode silenciosamente ignorar aspects em classes de lib (OK) **e** em classes de app que dão problema (não OK). Diferença ficaria invisível. **Mitigação**: logar todos os errors separadamente por tipo (lib/app).

- **`--no-desugaring` + d8 AIOOE**: AIOOE não é causado por desugaring. Se o time acredita que `--no-desugaring` resolve AIOOE por confusão semântica, expectativa vai frustrar. **Mitigação**: documentar claramente que os 234 AIOOE cases são bug independente e exigem issue separada.

- **Dataset B (APKs modernos) + aop.xml conservadora**: 32.5% de APKs já têm zero pointcut matches em generic_new; aop.xml pode piorar. **Mitigação**: teste empírico por spec set antes de tornar exclusões default.

---

## 8. Pontos positivos

1. **Metodologia rigorosa**: proposta, spec delta, design e tasks são rastreáveis end-to-end. Os 4 invariantes novos (INV-INS-13..16) são bem formados e testados.
2. **Gestão de risco explícita**: design.md:140 antecipa o risco de `-xmlConfigured` sozinho não resolver frame corruption e prevê fallback Python.
3. **Alinhamento com Coverage.aj**: exclusões via aop.xml tornam a semântica do pipeline consistente (cobertura e MOP ambos restritos a app-code).
4. **Trade-off de escopo bem fundamentado**: análise de 168 specs (100% `call()`) confirma que exclusões preservam monitoramento do código do app.
5. **Fix de menor risco (`--no-desugaring`) vem primeiro**: pode ser entregue e validado antes das outras, reduzindo risk no path crítico.
6. **YAML configurável** (INV-INS-16) permite re-experimentos com escopo diferente sem code change — essencial para validade empírica do trade-off.
7. **Backward compatibility explícita**: cenário "No weaving_excludes.yaml" garante que ambiente sem YAML mantém comportamento atual.

## 9. Pontos negativos / gaps

1. **d8 AIOOE não endereçado**: maior categoria de falhas no ASE journal (234 casos, ~59% de JCA errors). gh50 resolve 0% destes. **Recomendar abrir issue separada** para investigar bug do r8/d8 8.2.2-dev em okio HMAC e crypto providers.

2. **Zero-pointcut matches (32.5% de generic_new no F-Droid)** não é addressed. Pior, `-xmlConfigured` pode piorar — aop.xml reduz superfície de matches. Este é um problema separado (ProGuard/R8 rename? app não usa APIs? spec misconfigured?) que gh50 não investiga.

3. **Baseline spec FR02 desatualizada**: `specs/instrumentation/spec.md:345` não lista `__merge_support_classes()`, apesar de gh49 ter supostamente feito sync. **Ação**: verificar opsx:sync do gh49 antes de abrir PR da gh50.

4. **Hardcoded SDK version** (android-29, --min-api 26) limita escopo dos fixes. Seleção dinâmica é TODO(#23), não prevista em gh50 mas é **complementar crítico** — sem ela, gh50 tem limite de upside.

5. **`-proceedOnError` pode mascarar cobertura parcial**: safety net atual (hash) detecta no-op total mas não no-op **dos aspects de interesse**. Fix exige detecção de símbolos rv-monitor no DEX — não escopado em gh50.

6. **Divergência textual silenciosa** na delta (remoção de `(line 517)` sem marcação).

7. **Sub-bullets em tasks 1.4 e 2.4** inconsistentes (sem `- [ ]`).

8. **aop.xml exige listar aspect names**: introduz dependência nova rv-monitor-generator → rv-instrumentation (para descobrir aspect names dinamicamente). Design aborda mas tasks poderiam ser mais explícitos nisso.

9. **Sem métrica de "cobertura semanticamente parcial"**: após `-proceedOnError`, não há forma de reportar "APK foi instrumentado com N/M aspects aplicados". Métrica útil para análise de threats to validity.

---

## 10. Sugestões de melhoria priorizadas

### P1 — ações complementares a gh50 (bloqueiam upside pleno)

1. **Implementar seleção dinâmica de `android.jar`** por `targetSdkVersion` (TODO(#23)). Benefício alto, risco baixo, esforço baixo (~1-2 dias), sem rebuild Docker. Sem isto, `-proceedOnError` continuará mascarando erros de classe ausente que seriam facilmente resolvidos.

2. **Implementar `--min-api` dinâmico** = `max(26, apk.minSdkVersion)`. Benefício médio (DEX menor, menos stack-map surface), risco baixo, esforço baixo (~0.5 dia).

3. **Verificar e corrigir sync da gh49 sobre FR02**: `__merge_support_classes()` falta no baseline. Bloqueia consistência da delta de gh50.

### P2 — melhorias diretas na gh50

4. **Adicionar detecção de cobertura semanticamente parcial**: pós-weaving, grep no classes.dex por símbolos rv-monitor (ex.: `MultiSpec_*MonitorAspect`). Reportar `coverage_fraction` no result. Essencial para validade dos experimentos com `-proceedOnError`.

5. **Pilotar `-xmlConfigured` primeiro em JCA (menos vulnerável)** antes de generic_new. O bucket de zero-matches em generic_new (32.5%) merece investigação separada antes de aplicar aop.xml massivamente lá.

6. **Logar errors completos do ajc** mesmo com `-proceedOnError`, categorizados por tipo (class not found / aspect internal / bytecode malformed). Permite medir o efeito real da mudança.

7. **Adicionar campo `failure_category` nos error models** da rv-instrumentation. Facilita análise quantitativa futura (hoje requer grep manual em strings).

### P3 — correções menores de qualidade

8. Restaurar line numbers no cenário dex2jar ou marcar explicitamente como P4 cleanup no proposal.
9. Adicionar checkbox `- [ ]` em sub-bullets de tasks 1.4 e 2.4.
10. Adicionar linha "Preserved FR02 scenarios (8) — unchanged from baseline" na mapping table do design.

### P4 — itens de trabalho futuro (fora de gh50)

11. **Abrir issue para d8 AIOOE**: investigar bug r8/d8 8.2.2-dev em okio HMAC e crypto providers (215+185+21 casos no ASE). Potencialmente: tentar r8 9.x (build-tools 36.0.0) **apenas para estes casos**.

12. **Abrir issue para zero-pointcut matches em generic_new**: investigar por que 130/400 APKs modernos não fazem match de specs. ProGuard/R8 renaming? Spec misconfig? APKs não usam APIs monitoradas?

13. **Atualizar dex2jar para v2.4** (3/out/2024) — bug-fix release. Win barato se projeto usa < 2.4.

14. **Atualizar build-tools 35.0.1 → 36.x**: baixa prioridade. Só se evidência empírica mostrar benefício. Requer rebuild Docker.

15. **Exploração de DiSL ou BISM** como alternativa de longo prazo: apenas se abordagem AspectJ + d8 se mostrar fundamentalmente limitada. Custo alto de mudança de stack. **Não é ação para deadline 2026-04-13**.

---

## Conclusão e recomendação final

A change `gh50-improve-instrumentation` está **bem estruturada e tecnicamente fundamentada**. A análise de consistência de artefatos (§2) indica PASS com minor issues corrigíveis. A análise de impacto sobre specs MOP (§3) conclui que as exclusões propostas são ACEITÁVEIS e favoráveis à pesquisa, dado que: (a) 100% das 168 specs usam `call()`, (b) código de aplicação Android não está nos pacotes excluídos, (c) Coverage.aj já estabelece o mesmo escopo.

Entretanto, a análise quantitativa (§6) expõe que **gh50 não é bala de prata**:
- `--no-desugaring` resolve ~7-15% das falhas (bucket `j$.` bem delimitado).
- `-proceedOnError` resolve ~5-10% com risco de cobertura silenciosamente parcial.
- `-xmlConfigured` tem maior potencial no dataset moderno (30-37% de failures são stack-map) mas pode inflar o bucket "zero pointcut match" em generic_new.
- **Taxa realista pós-fix**: JCA 17.5% → ~33%, generic_new 54% → ~59%. Dobra JCA, melhora marginal em generic_new.
- **Gap remanescente (40-60%)** é dominado por d8 AIOOE (bug r8/d8 interno) e zero-matches — **nenhum endereçado por gh50**.

**Recomendação final**: **aprovar gh50 com ajustes** (P2) e acompanhar de perto com as ações complementares P1 e P4. Especificamente:

1. **Aprovar a aplicar** `--no-desugaring` (baixo risco, baixo custo, fix seguro para ~15% das falhas).
2. **Aprovar a aplicar** `-proceedOnError` mas com detecção de cobertura parcial (P2#4) obrigatória antes de considerar completo.
3. **Aprovar pilotar** `-xmlConfigured` primeiro em JCA; validar empiricamente em generic_new antes de expandir (P2#5).
4. **Bloquear fechamento de gh50** até (a) sync gh49 ser verificada (P1#3), (b) métrica de cobertura parcial implementada (P2#4), (c) resultado empírico piloto confirmar que `-xmlConfigured` não piora zero-matches de generic_new.
5. **Abrir issues paralelas** para d8 AIOOE (P4#11) e zero-matches generic_new (P4#12). Sem estas, gh50 entrega apenas 1/3 do upside possível.
6. **Paralelo**: implementar P1#1 e P1#2 (android.jar dinâmico + --min-api dinâmico). Sem eles, o upside de gh50 é limitado — muitas das falhas ajc seriam resolvíveis apenas com bootclasspath correto.

Dado o deadline de tese (2026-04-13) e o foco em finalização (memória do projeto: "business code frozen"), as mudanças de código devem ser mínimas e focadas. gh50 atende a esse critério (3 pequenas mudanças + config). **Proceed with gh50, com disciplina nas mitigações**.

---

### Fontes citadas

- [AspectJ ajc manual](https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html)
- [AspectJ LTW configuration](https://eclipse.dev/aspectj/doc/released/devguide/ltw-configuration.html)
- [AspectJ 1.9.24 on Maven Central](https://mvnrepository.com/artifact/org.aspectj/aspectjtools/1.9.24)
- [AspectJ StackMapAdder.java](https://github.com/eclipse-aspectj/aspectj/blob/master/weaver/src/main/java/org/aspectj/weaver/bcel/asm/StackMapAdder.java)
- [Android d8 documentation](https://developer.android.com/tools/d8)
- [SDK Build Tools release notes](https://developer.android.com/tools/releases/build-tools)
- [AGP 9.0.1 release notes](https://developer.android.com/build/releases/agp-9-0-0-release-notes)
- [AGP 9.1.1 release notes](https://developer.android.com/build/releases/agp-9-1-0-release-notes)
- [Jake Wharton — Android's Java 8 Support](https://jakewharton.com/androids-java-8-support/)
- [Jake Wharton — D8 Library Desugaring](https://jakewharton.com/d8-library-desugaring/)
- [dotnet/android D8 and R8 guide](https://github.com/dotnet/android/blob/main/Documentation/guides/D8andR8.md)
- [HujiangTechnology/gradle_plugin_android_aspectjx (archived)](https://github.com/HujiangTechnology/gradle_plugin_android_aspectjx)
- [wurensen/gradle_plugin_android_aspectjx](https://github.com/wurensen/gradle_plugin_android_aspectjx)
- [Ibotta/gradle-aspectj-pipeline-plugin](https://github.com/Ibotta/gradle-aspectj-pipeline-plugin)
- [JD Porterfield — Switching AspectJ Plugins in Android](https://jdvp.me/articles/Switching-AspectJ-Plugins-Android)
- [google/enjarify (archived)](https://github.com/google/enjarify)
- [pxb1988/dex2jar v2.4](https://github.com/pxb1988/dex2jar/releases/tag/v2.4)
- [DiSL/AspectJ comparison (HAL)](https://inria.hal.science/hal-03533152/document)
- [BISM (Springer 2020)](https://link.springer.com/chapter/10.1007/978-3-030-60508-7_18)
- [BISM DSL (Springer 2023)](https://link.springer.com/chapter/10.1007/978-3-031-44267-4_17)
- [didi/DroidAssist #38 — stack map table D8](https://github.com/didi/DroidAssist/issues/38)
- [growingio #90 — stack map D8](https://github.com/growingio/growingio-sdk-android-autotracker/issues/90)
- [bazel #15751 — D8 excessive stack map warnings](https://github.com/bazelbuild/bazel/issues/15751)
- [AAPT2 × SDK 35 mismatch](https://medium.com/@tosebikan/fixing-the-aapt2-crash-after-moving-to-android-15-sdk-35-7bcff92a9800)

# Analise: Change gh50-improve-instrumentation

Data: 2026-04-18
Modelo: Claude Opus 4.6 (1M context)

## 1. Resumo executivo

A change gh50 propoe tres melhorias incrementais ao pipeline de instrumentacao AspectJ/d8 do rv-instrumentation para elevar a taxa de sucesso de 17.5% (JCA) e 54% (generic_new) em APKs modernos F-Droid. Os artefatos (proposal, delta spec, design, tasks) sao **internamente consistentes** com rastreabilidade completa e sem conflitos de IDs. A analise de impacto das exclusoes MOP revela que o trade-off e **favoravel**: como todos os pointcuts MOP usam semantica `call()` (interceptacao no caller), excluir bibliotecas do weaving preserva 100% do monitoramento de codigo do app --- o unico impacto e a perda de deteccao de violacoes *internas* a bibliotecas de terceiros, que nao sao alvo da pesquisa. O risco principal e que `-xmlConfigured` pode nao impedir corrupcao de stack frames se o ajc ainda carregar classes excluidas via `-inpath` para resolucao de tipos --- o design corretamente identifica isso como risco que requer validacao empirica. Recomendacao: **aprovar a change com as ressalvas documentadas abaixo**.

---

## 2. Analise de consistencia dos artefatos

### 2.1 Rastreabilidade

| Camada | Item | Rastreabilidade | Status |
|--------|------|----------------|--------|
| Proposal | Modified capability: instrumentation | 4 invariantes (INV-INS-13..16) + FR02 modificado na delta spec | PASS |
| Delta Spec | INV-INS-13 (d8 --no-desugaring) | Design mapping: `rvandroid.py:__d8()` -> Task 2.1 | PASS |
| Delta Spec | INV-INS-14 (ajc -proceedOnError) | Design mapping: `rvandroid.py:__weave_monitors()` -> Task 2.2 | PASS |
| Delta Spec | INV-INS-15 (-xmlConfigured + aop.xml) | Design mapping: `__weave_monitors()` + `_generate_aop_xml()` -> Tasks 1.3, 2.3 | PASS |
| Delta Spec | INV-INS-16 (default excludes YAML) | Design mapping: `assets/weaving_excludes.yaml` -> Task 1.1 | PASS |
| Delta Spec | Backward compat (no YAML = no flag) | Design mapping: `__weave_monitors()` conditional -> Task 2.4 (teste) | PASS |
| Design | `__merge_support_classes` reraise=True | Ja implementado em gh49 (commit `8a25e7ec`) -> N/A | PASS |
| Tasks | Empirical validation (3.1-3.6) | Validacao, nao implementacao -> N/A | PASS |
| Tasks | Verification (4.1-4.3) | QA gate -> N/A | PASS |

**Veredicto**: Rastreabilidade completa. Cada capability tem spec, cada spec tem design, cada design tem task. Nenhum orfao encontrado.

### 2.2 Consistencia com specs existentes

**Headers FR02**: O header "APK Instrumentation with Monitors (FR02)" na delta spec bate **exatamente** com o da spec principal (`/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/specs/instrumentation/spec.md`).

**Cenarios existentes preservados na delta**:

| # | Cenario (spec principal) | Presente na delta? |
|---|--------------------------|-------------------|
| 1 | Successful single APK instrumentation | SIM |
| 2 | Skip existing instrumented APK | SIM |
| 3 | Force re-instrumentation | SIM |
| 4 | Pipeline phase failure with accurate phase reporting | SIM |
| 5 | Batch instrumentation with mixed results | SIM |
| 6 | dex2jar conversion failure with phase from outer decorator | SIM |
| 7 | Instrumentation verification detects unchanged APK | SIM |
| 8 | Maven dependency resolution failure | SIM |

Todos os 8 cenarios existentes estao presentes na delta. 4 cenarios novos adicionados (d8 --no-desugaring, ajc -proceedOnError, aop.xml exclusion, backward compat).

**IDs de invariantes**: A spec principal define INV-INS-01 a INV-INS-12. A delta spec define INV-INS-13 a INV-INS-16. **Sem conflitos** --- IDs sao sequenciais.

**Incorporacao do gh49**: A delta spec inclui `__merge_support_classes` na lista de metodos com `reraise=True`, com a nota "(\_\_merge_support_classes was added in gh49.)". A spec principal ainda **nao** inclui essa alteracao (lista apenas `instrument()`, `__include_generated_monitors()`, `__weave_monitors()`, `__create_apk()`, `__sign_apk()`). Isso indica que a spec principal esta levemente desatualizada em relacao ao codigo (que ja tem `reraise=True` em `__merge_support_classes` desde o commit `8a25e7ec`). A delta spec corrige isso.

**Issue menor**: A spec principal precisa ser sincronizada com o gh49 antes ou durante o gh50 para evitar drift.

### 2.3 Consistencia tecnica

#### -xmlConfigured em CTW: verificacao na documentacao oficial

A pesquisa na documentacao oficial do AspectJ ([ajc reference](https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html)) confirma:

1. **`-xmlConfigured` aceita path direto**: O flag recebe o caminho do arquivo XML como argumento explicito na linha de comando. Ex: `ajc -xmlConfigured /path/to/aop.xml ...`. **Nao** depende de auto-descoberta em `META-INF/aop.xml` (que e comportamento LTW).

2. **Funciona em CTW**: O flag e suportado em compile-time weaving, mas com diferencas:
   - `<exclude within="..."/>` **funciona** em CTW
   - `<include within="..."/>` e **ignorado** em CTW (todas as classes visiveis sao implicitamente incluidas, a menos que explicitamente excluidas)
   - Opcoes de `<weaver>` especificas de LTW (ex: class-loader filtering) sao silenciosamente ignoradas

3. **A decisao D2 do design esta correta**: Escrever `aop.xml` em `tmp_dir` (sem `META-INF/`) e passar o path explicitamente e o uso correto para CTW.

**Fontes**: [AspectJ ajc documentation](https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html), [LTW configuration](https://eclipse.dev/aspectj/doc/released/devguide/ltw-configuration.html), [Mojo AspectJ Maven Plugin](https://www.mojohaus.org/aspectj-maven-plugin/ajc_reference/standard_opts.html)

#### Coverage.aj vs aop.xml: complementar ou redundante?

**Coverage.aj** (pointcut-level exclusion):
```java
pointcut excludedPackages() :
    within(androidx..*) || within(kotlin..*) || within(com.google..*) ||
    within(com.facebook..*) || within(org.apache..*) || ...
```
Efeito: **nao rastreia** execucoes de metodos dessas classes para cobertura. Mas os monitors MOP **ainda sao** woven nessas classes.

**aop.xml** (weaver-level exclusion):
```xml
<exclude within="androidx..*"/>
<exclude within="kotlin..*"/>
```
Efeito: o weaver **nao modifica o bytecode** dessas classes. Nenhum advice (nem MOP, nem Coverage) e inserido.

**Relacao**: Sao **complementares, nao redundantes**:
- Coverage.aj ja nao conta metodos de bibliotecas como "cobertos"
- Mas MOP monitors AINDA weavem nessas classes, corrompendo stack frames
- O aop.xml **impede** o weaving, eliminando a corrupcao
- Impacto adicional: perda de deteccao de violacoes MOP em chamadas *internas* de bibliotecas (analise detalhada na Secao 3)

### 2.4 Formato e completude

| Criterio | Status |
|----------|--------|
| Cenarios usam `####` (4 hashtags) | PASS |
| Cenarios usam WHEN/THEN/AND com valores concretos | PASS |
| Tasks usam formato `- [ ] X.Y` | PASS |
| Todos os invariantes tem cenario associado | PASS |
| Todos os requirements tem cenarios | PASS |
| Mermaid diagram presente e correto | PASS |
| Design mapping table completo | PASS |

### Veredicto Secao 2: **PASS** com 1 issue menor

- **Issue**: A spec principal (`openspec/specs/instrumentation/spec.md`) nao inclui `__merge_support_classes` na lista de metodos com `reraise=True` (alteracao do gh49). Sincronizar via `/opsx:sync` durante ou apos o gh50.

---

## 3. Analise de impacto das exclusoes MOP

### 3.1 Impacto por spec set

#### JCA (23 specs)

**Pointcuts analisados** (CipherSpec.mop, SecureRandomSpec.mop, etc.):

Todos os pointcuts JCA usam semantica **`call()`**, nao `execution()`.

Exemplos:
- `call(public static Cipher Cipher.getInstance(String))` --- intercepta no **caller**
- `call(public void Cipher.init(int, Key,..))` --- intercepta no **caller**
- `call(public byte[] SecureRandom.generateSeed(int))` --- intercepta no **caller**

**APIs monitoradas**: `javax.crypto.Cipher`, `java.security.SecureRandom`, `java.security.MessageDigest`, `javax.crypto.Mac`, `javax.crypto.KeyGenerator`, `java.security.KeyStore`, `java.security.Signature`, `javax.net.ssl.SSLContext`, etc.

**Analise de impacto por pacote excluido**:

| Pacote excluido | Conteria chamadas JCA? | Impacto da exclusao |
|-----------------|----------------------|---------------------|
| `com.google..*` | Possivelmente (Google Play Services usa crypto internamente) | Chamadas crypto internas do Google nao monitoradas. **Aceitavel**: nao e codigo do app. |
| `androidx..*` | Raro (AndroidX Security usa crypto) | Perda minima. AndroidX Security usa APIs corretamente. |
| `kotlin..*` | Nao (stdlib Kotlin nao usa JCA) | Zero impacto |
| `kotlinx..*` | Nao | Zero impacto |
| `j$..*` | Nao (classes de desugaring) | Zero impacto |
| `okhttp3..*` | Sim (TLS handshake usa SSLContext) | OkHttp3 usa TLS corretamente. Perda aceitavel. |
| `org.apache..*` | Possivelmente (Apache HTTP client) | Uso interno correto. Perda aceitavel. |

**Veredicto JCA**: Impacto **MINIMO**. As APIs criptograficas monitoradas (javax.crypto.*, java.security.*) nao estao nos pacotes excluidos. O weaving intercepta no caller --- chamadas a partir de codigo do app continuam 100% monitoradas. Apenas chamadas crypto internas de bibliotecas sao perdidas, e estas nao sao alvo da pesquisa.

#### generic_new (27 specs)

**Pointcuts analisados** (InputStream_ManipulateAfterClose.mop, Map_UnsafeIterator.mop, Closeable_MeaninglessClose.mop):

Todos usam semantica **`call()`**.

Exemplos:
- `call(* InputStream+.read(..)) && target(i)` --- intercepta no **caller**
- `call(* Map+.put*(..)) && target(m)` --- intercepta no **caller**
- `call(* Closeable+.close()) && target(...)` --- intercepta no **caller**

**APIs monitoradas**: `java.io.InputStream`, `java.io.OutputStream`, `java.util.Map`, `java.util.Iterator`, `java.io.Closeable`, `java.io.Reader`, `java.io.Writer`, `java.net.ServerSocket`, etc.

**Analise de impacto**:

| Pacote excluido | Usa APIs monitoradas? | Impacto |
|-----------------|----------------------|---------|
| `kotlin..*` | Sim, extensivamente (kotlin.collections usa Iterator, Map) | Violacoes em stdlib Kotlin nao detectadas. **Aceitavel**: Kotlin stdlib e maduro. |
| `androidx..*` | Sim (IO operations, collections) | Violacoes em AndroidX nao detectadas. **Aceitavel**: codigo Google maduro. |
| `com.google..*` | Sim | Idem |
| `okhttp3..*` | Sim (InputStream/OutputStream intensivo) | Idem |

**Veredicto generic_new**: Impacto **BAIXO**. Maior que JCA porque APIs de uso geral (IO, Collections) sao usadas extensivamente por bibliotecas. Mas:
1. Bibliotecas maduras raramente tem bugs de uso de API
2. O foco da pesquisa e detectar misuse em **codigo de app**
3. Coverage.aj ja nao conta metodos de bibliotecas como cobertos

#### generic (118 FSM specs)

Mesma analise que generic_new. Pointcuts tambem usam `call()`.

**Veredicto generic**: Impacto **BAIXO**, mesma justificativa.

### 3.2 Quantificacao

#### Dados historicos: ASE Journal dataset (557 APKs, 2025)

| Spec Set | Total APKs | Erros | Sucesso | Taxa |
|----------|-----------|-------|---------|------|
| JCA | 364 erros registrados | 364 | 193* | 34.6%* |
| Generic | 352 erros | 352 | 205* | 36.8%* |
| Generic_new | 189 erros | 189 | 368* | 66.1%* |

*Nota: O proposal diz "ASE journal 0% success (0/364)" para JCA. Os numeros acima sao dos arquivos de erro. A discrepancia sugere que 364 e o total de APKs que falharam, nao o total tentado.*

**Distribuicao de erros (ASE JCA, 364 entradas)**:

| Categoria | Contagem | % | Corrigido por |
|-----------|----------|---|---------------|
| AIOOBE (ArrayIndexOutOfBoundsException no d8) | 234 | 64% | aop.xml (impede corrupcao de frames) |
| ajc_other (erros de compilacao ajc) | 90 | 25% | -proceedOnError (weaving parcial) |
| j$_prefix (conflito de classes j$) | 33 | 9% | --no-desugaring |
| StackMap (erros explicitos de stack map) | 5 | 1% | aop.xml |
| dex2jar (falhas de conversao) | 2 | 1% | Nenhuma (problema pre-existente) |

**Distribuicao de erros (ASE generic_new, 189 entradas)**:

| Categoria | Contagem | % | Corrigido por |
|-----------|----------|---|---------------|
| ajc_other | 108 | 57% | -proceedOnError |
| j$_prefix | 38 | 20% | --no-desugaring |
| AIOOBE | 24 | 13% | aop.xml |
| StackMap | 14 | 7% | aop.xml |
| d8_other | 3 | 2% | Possivel --no-desugaring |
| dex2jar | 2 | 1% | Nenhuma |

#### Dados novos: F-Droid dataset (400 APKs, 2026)

| Spec Set | Total | Sucesso | Falha | Taxa |
|----------|-------|---------|-------|------|
| JCA | 400 | 70 | 330 | 17.5% |
| Generic_new | 400 | 216 | 184 | 54.0% |

**Erros FDROID JCA** (sem mensagens detalhadas, apenas tool+code):
- d8: 978 ocorrencias (multiplas por APK)
- pipeline: 326
- ajc: 159
- dex2jar: 9

**Erros FDROID generic_new**:
- d8: 546
- ajc: 33
- dex2jar: 3

#### Estimativa de melhoria

Baseado na distribuicao de erros do ASE dataset (que tem mensagens detalhadas):

| Mudanca | Erros corrigidos (JCA) | Erros corrigidos (generic_new) |
|---------|----------------------|-------------------------------|
| --no-desugaring | ~33 (9%) | ~38 (20%) |
| -proceedOnError | ~45-90 (12-25%)* | ~54-108 (29-57%)* |
| aop.xml exclusion | ~234 (64%) | ~24-38 (13-20%) |

*-proceedOnError nao corrige TODOS os ajc_other --- alguns sao erros de tipo que persistem. Estimativa conservadora: 50%.*

**Taxa estimada pos-mudanca**: Assumindo sobreposicao parcial entre categorias:
- JCA: de 17.5% para **~50-65%** (ganho principal via aop.xml)
- Generic_new: de 54% para **~70-80%** (ganho principal via -proceedOnError)

### 3.3 Interacao com Coverage.aj

| Aspecto | Coverage.aj (atual) | aop.xml (proposto) | Efeito combinado |
|---------|--------------------|--------------------|-----------------|
| Metodos de bibliotecas contados como cobertos? | NAO (pointcut exclui) | NAO (weaver exclui) | Sem mudanca |
| MOP monitors woven em bibliotecas? | SIM (Coverage.aj nao afeta MOP) | NAO (weaver exclui) | **Reducao**: MOP nao detecta violacoes em codigo de biblioteca |
| Stack frames de bibliotecas corrompidos? | SIM (ajc ainda weave) | NAO (weaver pula) | **Melhoria**: elimina corrupcao |

**Conclusao**: O aop.xml **complementa** o Coverage.aj. O Coverage.aj ja nao contava metodos de bibliotecas como cobertos, mas os monitors MOP ainda weaviam (e corrompiam) essas classes. Com aop.xml, a corrupcao e eliminada, ao custo de perder deteccao de violacoes MOP em chamadas internas de bibliotecas.

**A pergunta critica**: Se Coverage.aj ja nao conta metodos de bibliotecas como cobertos, mas MOP monitors AINDA detectam violacoes nessas bibliotecas, a exclusao via aop.xml REMOVE essa deteccao. Isso e desejavel?

**Resposta**: SIM, e desejavel para esta pesquisa:
1. O foco e detectar misuse em **codigo de app**, nao em bibliotecas maduras
2. A corrupcao de stack frames causada pelo weaving em bibliotecas impede a instrumentacao de **66-82%** dos APKs
3. O trade-off e claro: instrumentar mais APKs (com monitoramento de app code) vs monitorar menos bibliotecas internamente

### Veredicto Secao 3: **ACEITAVEL**

O impacto das exclusoes e favoravel para a pesquisa:
- Todos os pointcuts MOP usam `call()` (interceptacao no caller), preservando 100% do monitoramento em codigo de app
- A perda afeta apenas chamadas internas de bibliotecas de terceiros, que nao sao alvo da pesquisa
- O ganho em taxa de instrumentacao (estimado 3-4x para JCA) supera amplamente a perda marginal de cobertura MOP em bibliotecas

---

## 4. Android SDK e compatibilidade

### 4.1 API dinamica: analise

**Situacao atual**: O pipeline usa `android-29/android.jar` fixo (TODO #23 no codigo) e `--min-api 26` fixo.

**Plataformas instaladas localmente**: android-4, android-10 a android-34 (22 versoes).

**Plataformas no Docker**: android-10 a android-35 (26 versoes), build-tools 35.0.1.

**Devemos selecionar android.jar dinamicamente?**

Beneficios:
- APKs com targetSdkVersion >= 30 usam APIs nao presentes em android-29.jar
- ajc precisa resolver tipos no classpath --- tipos faltantes causam erros de compilacao
- Parte dos erros `ajc_other` (25% das falhas) pode ser devida a tipos nao resolvidos

Riscos:
- Precisa ler `AndroidManifest.xml` do APK para obter targetSdkVersion (dependencia adicional: aapt2 ou androguard)
- Se a plataforma nao estiver instalada, precisa fallback para a mais proxima disponivel

**Recomendacao**: Implementar em change separada (escopo do TODO #23). Nao incluir no gh50 para manter o escopo focado.

### 4.2 Build tools: atualizacao necessaria?

| Componente | Local | Docker | Mais recente |
|------------|-------|--------|--------------|
| build-tools | 35.0.1 | 35.0.1 | 35.0.x (estavel) |
| d8 | via build-tools 35.0.1 | via build-tools 35.0.1 | Atual |
| AspectJ | 1.9.24 (local) | 1.9.24 (Docker base) | **1.9.25.1** (Dec 2025) |
| cmdline-tools | 10.0 / latest | 8512546_latest | Atual |

**Fontes**: [AspectJ releases](https://github.com/eclipse-aspectj/aspectj/releases/), [Android Build Tools](https://developer.android.com/tools/d8)

**AspectJ upgrade**: A versao 1.9.25.1 (dezembro 2025) inclui melhorias de stack frame handling. Atualizar de 1.9.24 para 1.9.25.1 poderia reduzir erros de stack map independentemente das outras mudancas. Requer apenas alterar a URL no `docker/base/Dockerfile`. **Recomendacao**: considerar upgrade em change separada ou como complemento do gh50.

**d8**: O d8 de build-tools 35.0.1 e a versao mais recente estavel. Nao ha evidencia de que versoes mais novas tenham melhor tolerancia a stack maps invalidos --- d8 e intencionalmente estrito.

### 4.3 Compatibilidade retroativa

**APKs antigos (ASE dataset, Android 8-11)**:
- Usam APIs compativeis com android-29 --- sem impacto da mudanca
- --no-desugaring com --min-api 26 e seguro para esses APKs (Java 8 features nativas desde API 26)

**APKs novos (F-Droid 2026)**:
- Podem usar APIs ate android-35
- --no-desugaring com --min-api 26 e seguro para features Java 8
- Features Java 9+ (records, sealed classes) ainda precisam de desugaring e podem falhar com --no-desugaring
- Risco: **baixo**, pois a maioria dos APKs Android usa Java 8 ou Kotlin (que compila para Java 8 bytecode)

### 4.4 Docker image

A imagem Docker (`docker/rvandroid/Dockerfile`) usa `phtcosta/rvandroid_tools:0.8.0` como base. A cadeia de imagens:

```
phtcosta/rvsec_base:0.8.0 (Python 3.12, Java 25, Maven 3.9.14, AspectJ 1.9.24)
  -> phtcosta/rvsec_android:0.8.0 (Android SDK, platforms, build-tools 35.0.1)
    -> phtcosta/rvandroid_tools:0.8.0 (droidbot, etc.)
      -> phtcosta/rvandroid:0.8.0 (rvsec + rv-android)
```

**Mudancas necessarias para gh50**: Nenhuma na imagem Docker. As mudancas sao em codigo Python (rvandroid.py, config.py) e um novo arquivo YAML (assets/weaving_excludes.yaml), que sao instalados via `uv sync` no build da imagem final.

**Se decidir upgrade do AspectJ**: Alterar `docker/base/Dockerfile` (URL do aspectj-1.9.24.jar -> 1.9.25.1.jar). Requer rebuild de toda a cadeia de imagens.

### Recomendacao Secao 4

1. **Nao incluir** mudancas de SDK no gh50 (manter escopo focado)
2. **Considerar** change separada para TODO #23 (dynamic android.jar selection)
3. **Considerar** upgrade AspectJ 1.9.24 -> 1.9.25.1 como mudanca complementar (potencial melhoria adicional em stack frame handling)
4. Docker image **nao precisa** de rebuild para gh50

---

## 5. Estado da arte

### 5.1 AspectJ + Android

**AspectJ e d8**: O problema de stack frames corrompidos e bem conhecido e documentado no ecossistema Android. Projetos como [aspectjx](https://github.com/HujiangTechnology/gradle_plugin_android_aspectjx) (efetivamente abandonado desde ~2020) e Hugo (Jake Wharton) sofriam do mesmo problema. A transicao de `dx` para `d8` como compilador DEX obrigatorio no AGP 7.x+ tornou o problema mais agudo, pois d8 e mais estrito na validacao de stack maps.

A causa raiz e que o manipulador de bytecode BCEL do AspectJ nem sempre recomputa stack map frames corretamente apos weaving, especialmente em classes que usam try-with-resources, lambdas, ou switch expressions.

**AspectJ 1.9.24 vs latest**: O projeto usa 1.9.24 (abril 2025). A versao mais recente e **1.9.25.1** (dezembro 2025), com suporte a Java 25. Desde a versao 1.9.7, o AspectJ tem melhorado progressivamente o tratamento de stack frames. A 1.9.21 corrigiu corrupcao relacionada a lambdas; 1.9.24 continua essa trajetoria. Upgrade para 1.9.25.1 poderia reduzir erros adicionais.

**-xmlConfigured em CTW**: Documentado e funcional. Aceita path direto. `<exclude within>` funciona em CTW. `<include within>` e ignorado em CTW. O design do gh50 esta alinhado com o uso correto do flag.

**Fontes**: [AspectJ Releases](https://github.com/eclipse-aspectj/aspectj/releases/), [ajc documentation](https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html), [eclipse-aspectj/aspectj issues](https://github.com/eclipse-aspectj/aspectj/issues/175)

### 5.2 d8/R8

**--no-desugaring + --min-api 26**: Seguro para features Java 8 (lambdas, method references, default/static interface methods), que sao nativamente suportadas pelo ART desde API 26. Features Java 9+ (var, records, sealed classes) ainda requerem desugaring. A maioria dos APKs Android usa Java 8 ou Kotlin (que compila para Java 8 bytecode).

**d8 --debug vs --release**: Ambos validam stack maps identicamente. `--debug` preserva informacao de debug (line numbers, local vars); `--release` aplica otimizacoes menores. Nenhum modo relaxa a verificacao de stack maps.

**Versoes recentes de d8**: Nao ha evidencia de relaxamento na validacao de stack maps em versoes recentes. d8 e intencionalmente estrito --- ART e mais rigoroso que Dalvik.

**Fontes**: [d8 documentation](https://developer.android.com/tools/d8), [Jake Wharton D8 desugaring](https://jakewharton.com/d8-library-desugaring/), [Java 8 support](https://developer.android.com/studio/write/java8-support)

### 5.3 Alternativas ao dex2jar

| Ferramenta | Status | Adequacao para pipeline RV |
|------------|--------|---------------------------|
| **dex2jar** (pxb1988) | Ultima release ~2021 (v2.2-SNAPSHOT) | Em uso. Funcional mas sem manutencao ativa |
| **Enjarify** (Google) | Abandonado desde 2016-2017 | Nao viavel |
| **JADX** | Ativamente mantido | Decompila para **source** (nao .class). Nao serve para pipeline de weaving |
| **baksmali/smali** | Mantido | Opera no nivel DEX/Smali. Requer reimplementacao de weaving em Smali |

**Recomendacao**: Continuar usando dex2jar. Nenhuma alternativa viavel para o pipeline DEX->JAR->weave->DEX atual. No longo prazo, considerar instrumentacao direta no DEX (ReDex, JVMTI) para eliminar o pipeline fragil.

**Fontes**: [dex2jar releases](https://github.com/pxb1988/dex2jar/releases), [Enjarify](https://github.com/google/enjarify), [JADX](https://github.com/skylot/jadx)

### 5.4 RV em Android

**TraceMOP** (FSE 2025): Ferramenta de RV baseada em traces explicitos. Em vez de weaving inline, registra traces de chamadas de metodos e roda monitors offline. **Evita completamente** o problema de incompatibilidade com d8 porque nao faz weaving. Limitacao: apenas RV post-hoc, nao online.

**BISM** (Bytecode-Level Instrumentation for Software Monitoring): Usa ASM internamente com `COMPUTE_FRAMES`, produzindo bytecode com stack maps validos. Overhead menor que DiSL e AspectJ. **Potencialmente compativel** com d8 por produzir frames corretos. Status: prototipo de pesquisa.

**DiSL**: Framework de instrumentacao dinamica. Usa Java agents (`-javaagent:`), que ART nao suporta diretamente. Adaptacoes para Android via JVMTI (API 26+) existem em prototipos, mas nao ha porta producao-ready.

**JVMTI no ART**: Disponivel desde Android 8.0 (API 26). Permite interceptacao de class loading e modificacao de bytecode via `ClassFileLoadHook`. Usado pelo profiler do Android Studio. **Alternativa viavel** para RV online sem pre-instrumentacao. Evita todo o pipeline DEX->JAR->weave->DEX.

**Instrumentacao direta no DEX**: Ferramentas como **ReDex** (Meta) operam diretamente em bytecode DEX, eliminando a camada JVM. Requer reimplementacao dos monitors em formato DEX/Smali.

**ASM post-weaving pass**: Projetos como **BISM** demonstram que um pass de `ClassWriter.COMPUTE_FRAMES` apos o weaving do AspectJ corrige frames corrompidos antes de passar para d8. Esta pode ser a **solucao cirurgica mais adequada** para o problema --- manter AspectJ mas consertar os frames apos o weaving.

**Fontes**: [TraceMOP (FSE 2025)](https://conf.researchr.org/details/fse-2025/fse-2025-demonstrations/40/TraceMOP-An-Explicit-Trace-Runtime-Verification-Tool-for-Java), [BISM paper](https://link.springer.com/chapter/10.1007/978-3-030-60508-7_18), [TraceMOP (ACM)](https://dl.acm.org/doi/10.1145/3696630.3728613)

---

## 6. Riscos e mitigacoes

| # | Mudanca | Risco | Prob. | Impacto | Mitigacao |
|---|---------|-------|-------|---------|-----------|
| R1 | `--no-desugaring` | APKs com features Java 9+ falham compilacao d8 | Baixa | Baixo | Tornar flag condicional (baseado em target API) se validacao empirica revelar regressoes |
| R2 | `-proceedOnError` | Classes parcialmente woven com monitoramento inconsistente (advice inserido em metade dos metodos) | Media | Baixo-Medio | d8 rejeita bytecode invalido; monitoramento parcial > nenhum monitoramento. Validar em teste empirico. |
| R3 | `-xmlConfigured` + aop.xml | ajc ainda carrega classes excluidas via `-inpath` para resolucao de tipos e corrompe frames durante carregamento | **Media** | **Alto** | **Principal risco**. Design corretamente identifica pre-filtering como fallback. Validacao empirica (Task 3) e essencial. |
| R4 | Nao implementar pre-filtering | Se R3 se materializar, a melhoria por aop.xml e nula e toda a estimativa de ganho (64% das falhas) fica comprometida | Media | Alto | Design documenta pre-filtering como change separada se necessario |
| R5 | Padroes de exclusao muito amplos | Classes do app em pacotes como `com.google.*` (raro mas possivel --- ex: apps do Google) nao seriam monitoradas | Muito Baixa | Medio | Padroes YAML configuraveis; pesquisadores podem ajustar por experimento |
| R6 | -proceedOnError + aop.xml (cruzado) | Se ajc encontra erro em classe excluida (nao deveria acontecer) e -proceedOnError mascara | Muito Baixa | Baixo | Monitorar logs do ajc na validacao empirica |
| R7 | --no-desugaring + Java 9+ bytecode (cruzado) | APKs com Kotlin 2.x+ que geram bytecode Java 11+ podem falhar com --no-desugaring | Baixa | Medio | Monitorar em validacao empirica; reintroduzir desugaring seletivamente se necessario |
| R8 | Upgrade implicito (nao planejado) | Se decidir upgrade do AspectJ (1.9.24 -> 1.9.25.1), pode introduzir regressoes de comportamento | Baixa | Medio | Manter 1.9.24 no gh50; testar upgrade em change separada |

**Risco mais critico**: **R3** --- se `-xmlConfigured` com `<exclude>` nao impedir que o ajc corrompa frames de classes excluidas (porque ele ainda as carrega via `-inpath` para resolucao de tipos), o ganho estimado de 64% das falhas nao se materializa. O design corretamente preve isso e documenta pre-filtering como fallback.

---

## 7. Pontos positivos

1. **Artefatos de alta qualidade**: Rastreabilidade completa proposal -> spec -> design -> tasks. Todos os cenarios documentados com valores concretos.

2. **Abordagem incremental**: Tres mudancas independentes que atacam familias de erros distintas. Cada uma pode ser validada e revertida separadamente.

3. **Backward compatibility**: Quando `weaving_excludes.yaml` nao existe, o pipeline funciona identicamente a versao anterior. Nenhum breaking change.

4. **Configurabilidade**: Padroes de exclusao em YAML permitem que pesquisadores ajustem por experimento sem tocar codigo.

5. **Validacao empirica planejada**: Task 3 define validacao com 10 e 40 APKs antes de considerar a mudanca completa.

6. **Risco documentado**: O design explicitamente reconhece o risco de `-xmlConfigured` nao ser suficiente e planeja pre-filtering como fallback.

7. **Integracao com gh49**: A delta spec incorpora corretamente as mudancas do gh49 (`__merge_support_classes` com `reraise=True`).

8. **Correcao tecnica**: O uso de `-xmlConfigured` com path direto e `<exclude within>` em CTW e confirmado pela documentacao oficial do AspectJ.

---

## 8. Pontos negativos / gaps

1. **Spec principal desatualizada**: A spec `openspec/specs/instrumentation/spec.md` nao inclui a mudanca do gh49 (`__merge_support_classes` com `reraise=True`). Precisa ser sincronizada.

2. **Dados do F-Droid sem mensagens detalhadas**: O arquivo `instrument_and_sa_errors.json` do F-Droid contem apenas `tool` e `code`, sem `message`. Isso dificulta a classificacao precisa dos erros e a estimativa de impacto para o dataset mais relevante (2026).

3. **Comportamento de -proceedOnError nao especificado em detalhe**: O cenario "ajc proceeds on class-level errors" assume que "the problematic class MUST be included in the output with its original bytecode (not woven)". O comportamento exato do ajc com `-proceedOnError` para classes individuais precisa de verificacao empirica --- a documentacao oficial nao detalha se a classe original e preservada ou simplesmente omitida.

4. **Ausencia de analise de impacto no -proceedOnError por spec set**: O -proceedOnError afeta quais classes sao woven, mas o design nao analisa se classes parcialmente woven podem gerar falsos positivos ou negativos nos monitors MOP (ex: monitor FSM que espera sequencia de eventos, mas o advice de um evento nao foi inserido).

5. **Sem mention de upgrade do AspectJ**: O AspectJ 1.9.25.1 (dezembro 2025) inclui melhorias potencialmente relevantes, mas nao e mencionado nos artefatos.

6. **Nao aborda dex2jar como fonte de problemas**: 1-2% dos erros sao de dex2jar. O design explicita como non-goal ("Fixing dex2jar conversion issues"), mas nao menciona que dex2jar nao e mais mantido ativamente.

7. **Pre-filtering nao documentado como task**: O pre-filtering (mover fisicamente classes excluidas do `tmp/` antes do ajc) e mencionado como fallback, mas nao tem tasks definidas. Se a validacao empirica mostrar que aop.xml e insuficiente, as tasks precisarao ser criadas.

8. **Coverage.aj tem mais exclusoes que aop.xml**: O Coverage.aj exclui `sun..*`, `java..*`, `javax..*`, `jakarta..*`, `com.sun..*`, `android..*`, `com.android..*`, `net.sf.cglib..*` que NAO estao no aop.xml proposto. Embora o weaving dessas classes nao afete monitors MOP (as APIs monitoradas ja estao no classpath via android.jar, nao no -inpath), o ajc pode tentar weavear advice em classes `android..*` do -inpath, causando corrupcao. Considerar alinhar as exclusoes do aop.xml com as do Coverage.aj.

---

## 9. Sugestoes de melhoria (priorizadas)

### Alta prioridade

1. **Alinhar exclusoes do aop.xml com Coverage.aj**: Adicionar ao `weaving_excludes.yaml` os pacotes excluidos pelo Coverage.aj que faltam no aop.xml proposto: `android..*`, `com.android..*`. Esses pacotes podem ter classes no `-inpath` (vindas do dex2jar) e o weaving nelas causaria corrupcao de frames. O Coverage.aj ja os exclui do pointcut, mas o aop.xml nao os exclui do weaver.

2. **Sincronizar spec principal com gh49**: Antes de finalizar gh50, executar `/opsx:sync` para incorporar `__merge_support_classes` com `reraise=True` na spec principal.

3. **Melhorar dados do F-Droid**: Na validacao empirica (Task 3), capturar mensagens de erro completas (nao apenas tool+code) para permitir classificacao precisa.

### Media prioridade

4. **Documentar comportamento exato de -proceedOnError**: Adicionar nota no design especificando o que acontece com classes que falham compilacao --- sao incluidas com bytecode original? Omitidas? Substituidas por stubs? Verificar empiricamente.

5. **Considerar ASM post-weaving pass**: Alem de aop.xml, um pass de `ClassWriter.COMPUTE_FRAMES` apos o weaving do ajc poderia corrigir frames corrompidos em classes que nao foram excluidas. Isso complementaria o aop.xml e poderia aumentar ainda mais a taxa de sucesso. Documentar como sugestao futura no design.

6. **Preparar tasks para pre-filtering**: Mesmo que nao implementado no gh50, ter tasks draft para pre-filtering acelera a resposta se a validacao empirica mostrar que aop.xml e insuficiente.

7. **Considerar upgrade do AspectJ**: Testar AspectJ 1.9.25.1 em paralelo. Se melhorar stack frame handling, o ganho e cumulativo com as outras mudancas.

### Baixa prioridade

8. **Avaliar BISM como alternativa de longo prazo**: BISM usa ASM com `COMPUTE_FRAMES` e produz bytecode com frames validos. Para uma geracao futura do pipeline, poderia substituir o AspectJ e eliminar o problema de corrupcao de frames.

9. **Avaliar JVMTI como alternativa de longo prazo**: Para RV online sem pre-instrumentacao, JVMTI no ART (API 26+) poderia eliminar todo o pipeline DEX->JAR->weave->DEX. Requer pesquisa significativa.

10. **Implementar TODO #23 (dynamic android.jar)**: Em change separada, ler targetSdkVersion do APK e selecionar android.jar correspondente. Pode resolver parte dos erros ajc_other causados por tipos nao resolvidos.

---

## 10. Conclusao e recomendacao final

A change gh50-improve-instrumentation e **bem estruturada, tecnicamente correta, e aborda um problema critico** da pesquisa. A taxa de instrumentacao de 17.5% (JCA) e insuficiente para experimentos significativos, e as tres mudancas propostas atacam as familias de erros dominantes de forma complementar.

**Pontos fortes**:
- Artefatos com rastreabilidade completa e sem inconsistencias significativas
- Abordagem incremental com backward compatibility
- Uso correto de `-xmlConfigured` confirmado pela documentacao oficial
- Impacto das exclusoes MOP e aceitavel (todos os pointcuts usam `call()`)
- Validacao empirica planejada com criterio de aceitacao claro (>=5/10 APKs)

**Pontos de atencao**:
- O risco R3 (ajc corromper frames de classes excluidas mesmo com aop.xml) e o principal ponto de incerteza. A validacao empirica e essencial.
- Alinhar exclusoes do aop.xml com as do Coverage.aj (adicionar `android..*`, `com.android..*`)
- Sincronizar spec principal com gh49 antes de finalizar

**Recomendacao**: **APROVAR a change** e prosseguir para implementacao. A validacao empirica (Task 3) determinara se pre-filtering e necessario como complemento. Se R3 se materializar, implementar pre-filtering como change de acompanhamento.

---

*Analise realizada por Claude Opus 4.6 (1M context) em 2026-04-18.*
*Artefatos analisados: 8 arquivos de spec/design, 2 arquivos de codigo-fonte, 1 aspecto Coverage.aj, 8+ arquivos .mop, 5 arquivos de dados de erro, 5 Dockerfiles, 22 plataformas Android SDK.*
*Pesquisa web: 4 buscas realizadas (AspectJ -xmlConfigured, d8 --no-desugaring, dex2jar alternatives, RV Android state of art).*

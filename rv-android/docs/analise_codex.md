# Análise: Change gh50-improve-instrumentation
Data: 2026-04-18
Modelo: Codex (GPT-5)

## 1. Resumo executivo

A change `gh50-improve-instrumentation` ataca três famílias reais de falha do pipeline atual em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py`: falhas do d8 em classes já desugared/`j$`, abortos globais do ajc e weaving em bibliotecas com bytecode mais frágil. A direção técnica é boa e a hipótese de ganho de taxa de instrumentação é suportada pelos datasets, especialmente para JCA, mas o pacote ainda não está pronto para aprovação “as is”. Há três bloqueios claros: a rastreabilidade OpenSpec falha em pontos objetivos, o racional de `--no-desugaring` está mais forte do que a documentação oficial sustenta, e a exclusão via `aop.xml` reduz cobertura observável de MOP porque os três conjuntos de specs usam `call()` e não `execution()`. Minha recomendação é **aprovar a ideia, mas não a redação atual da change**: corrigir proposal/design/tasks, explicitar o trade-off de cobertura, e definir um critério de aceite empírico para decidir se `-xmlConfigured` basta ou se o pre-filtering precisará virar uma segunda change.

Nota de rigor:
- Neste relatório, chamo de **observação** o que foi diretamente lido em arquivos locais ou em documentação oficial consultada em 2026-04-18.
- Chamo de **inferência** o que decorre da combinação dessas fontes, especialmente quando extrapolo dos JSONs do ASE 2025 ou de amostras/visões parciais do dataset F-Droid 2026.

## 2. Análise de consistência dos artefatos

### 2.1 Rastreabilidade

Arquivos analisados:
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh50-improve-instrumentation/proposal.md`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh50-improve-instrumentation/specs/instrumentation/spec.md`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh50-improve-instrumentation/design.md`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh50-improve-instrumentation/tasks.md`

Achados:
- `proposal.md` cobre 4 itens em “What Changes”: `--no-desugaring`, `-proceedOnError`, `-xmlConfigured` + `aop.xml` e `Pre-filtering fallback`. A delta spec cobre só os três primeiros. O design rebaixa explicitamente o pre-filtering para non-goal/separate change. Isso quebra a rastreabilidade proposal -> spec -> design.
- O mapping table do design cobre `INV-INS-13..16`, backward compatibility sem YAML e a herança de `__merge_support_classes` do gh49, mas **não cobre todos os cenários** do FR02 modificado. A delta contém 12 cenários e a tabela cobre apenas um subconjunto.
- `tasks.md` cobre bem a implementação principal (`1.x` e `2.x`), mas `3.x` e `4.x` ficam sem ligação explícita a linhas do mapping table. Como plano operacional isso é aceitável; como rastreabilidade OpenSpec rigorosa, não.

### 2.2 Consistência com specs existentes

Arquivos baseline:
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/specs/instrumentation/spec.md`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/specs/core/spec.md`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/specs/experiment/spec.md`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/specs/tools/spec.md`

Checks:
- O header MODIFIED bate exatamente: `Requirement: APK Instrumentation with Monitors (FR02)` aparece igual na spec base e na delta.
- A spec base vai até `INV-INS-12`; a delta adiciona `INV-INS-13..16`. Não há conflito de IDs.
- A delta incorpora corretamente os efeitos do gh49: `reraise=True` para `instrument()`, `__include_generated_monitors()`, `__weave_monitors()`, `__create_apk()`, `__sign_apk()`, `__merge_support_classes()`; também preserva `_error_phase` e `getattr(ex, '_error_phase', fallback)`.
- Todos os 8 cenários herdados do FR02 base continuam na delta:
  1. `Successful single APK instrumentation`
  2. `Skip existing instrumented APK`
  3. `Force re-instrumentation`
  4. `Pipeline phase failure with accurate phase reporting`
  5. `Batch instrumentation with mixed results`
  6. `dex2jar conversion failure with phase from outer decorator`
  7. `Instrumentation verification detects unchanged APK`
  8. `Maven dependency resolution failure`

### 2.3 Consistência técnica

Código atual:
- `__weave_monitors()` hoje chama `ajc` sem `-proceedOnError` nem `-xmlConfigured` em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py:755`
- `__d8()` hoje chama `d8 monitored.jar --release --lib ... --min-api 26` sem `--no-desugaring` em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py:967`
- `RVInstrumentationConfig` fixa `android-29/android.jar` em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-instrumentation/src/rv_instrumentation/config.py:443`
- `__get_android_jar()` ainda devolve sempre `self.config.android_jar_path` e deixa o TODO(#23) aberto em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py:1155`

Validação externa:
- A documentação oficial do `ajc` confirma que `-xmlConfigured <files>` existe para CTW, exige o XML **explicitamente na linha de comando** e não faz autodiscovery de `aop.xml`: https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html
- A mesma documentação também traz a nuance mais importante para esta change: em CTW, `<include within="..."/>` é ignorado, mas `<exclude within="..."/>` funciona; ainda assim escopos/excludes afetam pointcuts regulares, **não ITDs**.
- O design está correto ao escrever `tmp_dir/aop.xml` sem `META-INF/`, porque a documentação do `ajc` diz que em CTW não existe “magical file name” e o caminho precisa ser passado no comando.
- A documentação oficial do `d8` confirma `--no-desugaring`, mas também o descreve como seguro **apenas** quando você não pretende compilar bytecode que use Java 8 language features: https://developer.android.com/tools/d8
- A documentação da Android Developers também confirma que o ecossistema Android moderno ainda depende de desugaring para vários casos; `minSdk >= 26` resolve `MethodHandle.invoke*`, mas não elimina genericamente toda necessidade de desugar, principalmente para APIs/libraries desugared: https://developer.android.com/studio/write/java8-support

Conclusão técnica:
- O argumento “`-xmlConfigured` aceita path explícito em CTW” está correto.
- O argumento “`tmp_dir/aop.xml` é válido” está correto.
- O argumento “`--min-api 26` torna desugaring desnecessário” é **forte demais**. O que os docs suportam é: algumas incompatibilidades desaparecem a partir de API 26, mas `--no-desugaring` continua dependendo do bytecode de entrada realmente não exigir desugaring ou desugared-library rewriting.

### 2.4 Formato e completude

Checks:
- Todos os cenários da delta usam `####`.
- Todos seguem `WHEN`/`THEN`/`AND`.
- Não encontrei requirement modificada sem cenário.
- O formato principal das tasks usa `- [ ] X.Y`.
- Há um desvio menor: sub-bullets dentro de `1.4` e `2.4` não seguem `- [ ] X.Y`. Isso não invalida o arquivo, mas falha sob leitura literal da regra.

### Veredicto: FAIL

Issues principais:
- Proposal inclui pre-filtering fallback, mas a delta spec não formaliza isso e o design o remove do escopo.
- O design não mapeia todos os cenários da delta.
- As tasks de validação/QA não estão rastreadas explicitamente no mapping table.
- O racional de `--no-desugaring` está formulado de forma mais forte do que a documentação oficial suporta.

## 3. Análise de impacto das exclusões MOP

Arquivos analisados:
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/*.mop`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/generic/*.mop`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/generic_new/*.mop`

### 3.1 Impacto por spec set

Fato estrutural mais importante:
- Em uma varredura dos 3 diretórios, encontrei `call(` em todos os conjuntos e **zero ocorrências de `execution(`**.
- Contagens agregadas:
  - `jca`: 23 arquivos, 142 usos de `call()`, 0 de `execution()`
  - `generic`: 118 arquivos, 436 usos de `call()`, 0 de `execution()`
  - `generic_new`: 27 arquivos, 89 usos de `call()`, 0 de `execution()`

Exemplos:
- JCA:
  - `CipherSpec.mop` monitora `call(public static Cipher Cipher.getInstance(String))`, `call(public void Cipher.init(..))`, `call(public byte[] Cipher.update(..))`, `call(public byte[] Cipher.doFinal(..))`
  - `KeyGeneratorSpec.mop` monitora `call(public static KeyGenerator KeyGenerator.getInstance(String))`, `call(public void KeyGenerator.init(..))`, `call(public SecretKey KeyGenerator.generateKey())`
  - `IvParameterSpec.mop` monitora construtores `call(public IvParameterSpec.new(..))`
- Generic:
  - `FSM1.mop` monitora `Condition.signalAll`, `Condition.await`, `ReentrantLock.lock/unlock/newCondition`
  - `FSM100.mop` monitora `TextArea.setEditable`, `TextArea.append`, `TextArea.setBounds`
  - `FSM111.mop` monitora `AbstractButton.setBorder`, `isSelected`, `isEnabled`
- Generic_new:
  - `Closeable_MeaninglessClose.mop` monitora `call(* Closeable+.close())`
  - `CharSequence_NotInSet.mop` monitora `call(* Set+.add(..))` e `call(* Set+.addAll(Collection))`
  - `InputStream_ManipulateAfterClose.mop` monitora `call(* InputStream+.close(..))`, `read`, `available`, `reset`, `skip`

Implicação:
- Como todos os specs usam `call()`, a instrumentação acontece no **caller**.
- Se `aop.xml` excluir `com.google..*`, `androidx..*`, `kotlin..*`, `kotlinx..*`, `okhttp3..*`, `okio..*` etc., chamadas feitas **a partir** dessas classes deixam de ser monitoradas, mesmo que o alvo seja `javax.crypto.*`, `java.io.*`, `java.util.*` ou outra API de interesse.

### 3.2 Quantificação

Baseline local observável no dataset novo:
- Em `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/preprocess_jca/`, os 10 lotes somam **70 APKs instrumentados** de 400.
- Em `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/preprocess_generic_new/`, os 10 lotes somam **216 APKs instrumentados** de 400.
- Esses números batem com os do proposal: 17.5% JCA e 54% generic_new.

Limite importante dos dados de 2026:
- Os diretórios `preprocess_jca/` e `preprocess_generic_new/` permitem recuperar a taxa agregada de sucesso por lote, mas os JSONs fornecidos em `APKS_JCA/errors/instrument_and_sa_errors.json` e `APKS_GENERIC_NEW/errors/instrument_and_sa_errors.json` não oferecem um catálogo completo e homogêneo de mensagens para todos os 400 APKs.
- Em particular, o JSON detalhado de JCA disponível descreve `preprocess_0` com 40 APKs; ele é suficiente para confirmar a predominância operacional de falhas `d8`/`ajc`, mas **não** para estimar com precisão estatística fina a composição de erros dos 400 APKs.
- Portanto, esta seção mistura duas camadas de evidência:
  - observação forte: taxas agregadas 70/400 e 216/400, mais contagens do ASE 2025;
  - inferência moderada: composição provável das famílias de falha no F-Droid 2026.

ASE journal 2025:
- Os JSONs fornecidos registram:
  - JCA: 364 falhas (`253 d8`, `109 ajc`, `2 dex2jar`)
  - generic: 352 falhas (`227 d8`, `123 ajc`, `2 dex2jar`)
  - generic_new: 189 falhas (`73 d8`, `114 ajc`, `2 dex2jar`)
- Classificação textual dos erros:
  - JCA: `ArrayIndexOutOfBoundsException` 234, `kotlin param map mismatch` 62, `BCException/Internal compiler error` 46, `j$` 27, `Expected stack map table` 30
  - generic: `ArrayIndexOutOfBoundsException` 197, `kotlin param map mismatch` 63, `BCException/Internal compiler error` 39, `j$` 28, `Expected stack map table` 28
  - generic_new: `kotlin param map mismatch` 64, `BCException/Internal compiler error` 30, `j$` 27, `Expected stack map table` 27, `ArrayIndexOutOfBoundsException` 24

Interpretação:
- `--no-desugaring` ataca principalmente a família `j$`.
- `-proceedOnError` ataca parte dos erros `ajc`/`BCException`/`kotlin param map mismatch`, mas não garante correção funcional da classe problemática.
- `-xmlConfigured` mira a família dominante de AIOOBE/stack map em classes de bibliotecas (`okio`, `com.google.*`, `androidx.*`, `android/support/*`).

Estimativa defensável:
- A proposta de ganho é plausível para **taxa de instrumentação** porque a maioria dos erros observados está concentrada exatamente nas três famílias-alvo.
- Não é possível, com os arquivos fornecidos, afirmar quantos APKs “certamente” passarão. O que posso afirmar é:
  - no ASE JCA, **291/364 falhas** têm assinatura textual diretamente compatível com `d8`/stack-map/`j$`;
  - no ASE generic, **253/352 falhas** idem;
  - no ASE generic_new, **78/189 falhas** idem, além de uma massa grande de erros `ajc` que `-proceedOnError` pode amortecer parcialmente.
- Para o F-Droid 2026, a evidência local mais forte é esta:
  - JCA recente: 34 falhas de instrumentação em 40 APKs do `preprocess_0`; dessas, 28 envolvem `d8 + pipeline`, 5 envolvem `ajc + d8 + pipeline` e 1 envolve `dex2jar`.
  - Isso não prova que os mesmos percentuais valem para os 400 APKs, mas reforça a tese de que o gargalo recente continua concentrado em `d8` e `ajc`, não em `dex2jar`.

### 3.3 Coverage.aj interação

`Coverage.aj` já exclui `androidx..*`, `kotlin..*`, `com.google..*`, `com.facebook..*`, `org.apache..*` etc. no pointcut `excludedPackages()` e só conta `execution(* *.*(..)) && !excludedPackages()`:
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj:22`

Diferença técnica:
- `Coverage.aj` faz exclusão **pointcut-level** para o aspecto de cobertura. Isso significa: métodos dessas bibliotecas já não entram na métrica `RVSEC-COV`.
- `aop.xml` faz exclusão **weaver-level** para todos os aspectos tecidos em CTW. Isso significa: além de não contar cobertura dessas classes, o sistema também para de inserir advice MOP nelas.

Impacto adicional real:
- Hoje já não se mede cobertura de métodos em `androidx`, `kotlin`, `com.google`, etc.
- Mas hoje os monitores MOP ainda podem detectar violações se uma biblioteca fizer a chamada e ela for tecida como caller.
- Com `aop.xml`, essa detecção some.

Avaliação:
- Para a pergunta de pesquisa focada em misuse no **código do app**, esse trade-off é defensável.
- Para generic/generic_new, o impacto é maior do que no JCA, porque boa parte dos patterns envolve APIs de uso geral (`InputStream`, `Set`, `Closeable`, coleções). Bibliotecas Kotlin/AndroidX/OkHttp fazem esse tipo de chamada o tempo todo.
- Em termos práticos, a change provavelmente aumenta o número de APKs “processáveis”, mas desloca o experimento de “monitorar o APK como um todo” para “monitorar o código do app e o que ele chama diretamente”.

### Veredicto: ACEITÁVEL COM RESSALVAS

Aceitável se a meta for explicitamente “monitorar misuse originado do código do app e não de bibliotecas de terceiros”. Problemático se a interpretação desejada for “detectar qualquer violação observável no APK inteiro”.

## 4. Android SDK e compatibilidade

### 4.1 API dinâmica: análise

Estado atual:
- `android.jar` é fixado em `android-29` em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv_instrumentation/config.py:444`
- `__get_android_jar()` ainda não usa `app.sdk_target` em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv_instrumentation/rvandroid.py:1159`
- `--min-api` é fixo em `26` em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv_instrumentation/src/rv_instrumentation/rvandroid.py:1004`

SDK instalado localmente:
- `platforms`: `android-4`, `android-10`, `android-14`..`android-19`, `android-21`..`android-34`
- `build-tools`: `25.0.2`, `26.0.2`, `27.0.1`, `27.0.3`, `28.0.3`, `29.0.2`, `29.0.3`, `30.0.0`, `30.0.2`, `30.0.3`, `32.0.0`, `33.0.0`, `33.0.1`, `34.0.0`, `35.0.0`, `35.0.1`
- `cmdline-tools`: `9.0`, `10.0`, `latest`, `tools`

Dataset novo 2026, amostra aleatória de 100/400 APKs:
- `minSdk`: mediana 26, p75 27, máximo 34
- `minSdk >= 30`: 7/100
- `targetSdk`: mediana 36, 99/100 com `targetSdk >= 33`
- `compileSdk`: mediana 36, 93/100 com `compileSdk >= 35`

Conclusões:
- O risco principal do `android-29/android.jar` fixo não é `minSdk`; é **compile/target API drift**. Apps recentes compilados contra API 35/36 podem referenciar stubs ausentes em `android-29`.
- Tornar `android.jar` dinâmico por APK é recomendável e o TODO(#23) está bem justificado.
- Tornar `--min-api` dinâmico é opcional. Para compatibilidade, usar `26` como piso conservador continua seguro; elevar para o `minSdk` real pode reduzir transformações desnecessárias em parte do conjunto, mas o ganho esperado parece menor do que a seleção dinâmica de `android.jar`.
- O dado observável aqui é assimétrico e importante: o `minSdk` da amostra não é tão alto quanto a hipótese inicial sugeria, mas `targetSdk` e `compileSdk` são muito mais novos. Isso favorece fortemente priorizar `android.jar` dinâmico antes de discutir `--min-api` dinâmico.

### 4.2 Build tools: atualização necessária?

Evidência local:
- O ambiente já tem `build-tools/35.0.1`.
- A documentação oficial recomenda manter Build Tools atualizadas e hoje mostra `36.0.0` como exemplo atual: https://developer.android.com/tools/releases/build-tools

Leitura prática:
- Atualizar de 29.x/30.x para 35.x/36.x faz sentido se o binário `d8` efetivamente em uso no PATH estiver antigo.
- Mas a release note pública de Build Tools não documenta melhorias específicas de stack map tolerance para d8/R8. Então não dá para prometer ganho de taxa de instrumentação só com update.

### 4.3 Compatibilidade retroativa

- Há baixo risco conceitual em usar build-tools mais novos para APKs do dataset antigo, porque d8 é um compilador forward-maintained e continua aceitando bytecode antigo.
- O maior risco de regressão vem de mudança de comportamento do próprio toolchain, não de incompatibilidade com Android 8-11.
- Portanto: atualizar build-tools é razoável, mas deve ser tratado como experimento controlado, não como correção garantida.

### 4.4 Impacto na imagem Docker

Observação verificável:
- O Dockerfile do projeto em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docker/rvandroid/Dockerfile` usa `FROM phtcosta/rvandroid_tools:0.8.0`.

Limite de evidência:
- Eu **não** inspecionei o conteúdo da imagem `phtcosta/rvandroid_tools:0.8.0`, então não posso afirmar com rigor qual versão de Android SDK, build-tools, cmdline-tools ou `d8` ela contém.
- Sem `docker inspect`, `docker run`, ou acesso ao Dockerfile da imagem-base, qualquer afirmação sobre “qual versão do Android SDK está nessa imagem” seria inferência fraca.

Conclusão rigorosa:
- Se a decisão for atualizar SDK tools para sustentar a gh50 em ambiente reprodutível, a consequência operacional mais provável é esta:
  - se o container-base já tiver build-tools suficientemente novos, a mudança pode ser só de configuração/uso;
  - se o container-base estiver preso a toolchain antiga, será necessário rebuild da imagem-base `phtcosta/rvandroid_tools:0.8.0` ou substituição por outra imagem-base.
- Portanto, o impacto na imagem Docker deve ser tratado como **pendência de verificação de ambiente**, não como fato já estabelecido.

### Recomendação

1. Implementar primeiro as três mudanças da gh50 sem misturar update de SDK/toolchain.
2. Em seguida, medir com o mesmo conjunto de APKs e só depois comparar com build-tools mais novos.
3. Priorizar `android.jar` dinâmico antes de `--min-api` dinâmico.
4. Antes de propor alteração em Docker, inspecionar a imagem-base `phtcosta/rvandroid_tools:0.8.0` e registrar explicitamente as versões reais de `d8`, build-tools e cmdline-tools.

## 5. Estado da arte

### 5.1 AspectJ + Android

- `ajc` documenta oficialmente `-xmlConfigured` para CTW e `-proceedOnError`: https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html
- AspectJ do projeto está em `1.9.24` via `${aspectj.version}` no pom pai `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/pom.xml:32`; o módulo `rv-android` herda essa versão ao declarar `aspectjrt`, `aspectjtools` e `aspectjweaver` sem versão local em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/pom.xml:37`
- Há release mais nova `1.9.25`, mas as release notes públicas de `1.9.24` e `1.9.25` dizem `No major improvements`; não encontrei evidência pública de correções específicas para stack maps Android:
  - https://github.com/eclipse-aspectj/aspectj/blob/master/docs/release/README-1.9.24.adoc
  - https://github.com/eclipse-aspectj/aspectj/blob/master/docs/release/README-1.9.25.adoc
- Ecossistema Android com AspectJ continua existindo via AspectJX/gradle plugins, mas a literatura/documentação pública recente está mais focada em integração de build do que em robustez contra bytecode moderno.

### 5.2 d8/R8

- `d8` oficial:
  - `--debug` inclui debug info; `--release` remove debug info mas preserva o necessário para stacktrace
  - `--no-desugaring` “Use this flag only if you don't intend to compile Java bytecode that uses Java 8 language features”
  - fonte: https://developer.android.com/tools/d8
- Android docs:
  - desugaring ainda é o mecanismo padrão para recursos Java 8+
  - `MethodHandle.invoke`/`invokeExact` exigem `minSdkVersion 26` ou superior
  - fonte: https://developer.android.com/studio/write/java8-support

Leitura:
- `--no-desugaring` é razoável como mitigação para conflitos com classes `j$.`, mas não deve ser tratado como universalmente seguro.

### 5.3 Alternativas

- dex2jar oficial mais recente: `v2.4`: https://github.com/pxb1988/dex2jar/releases
- Enjarify:
  - o repositório `google/enjarify` afirma explicitamente estar potencialmente desatualizado e redireciona o desenvolvimento futuro
  - fonte: https://github.com/google/enjarify
- Para análise estática/reverse engineering, ferramentas como JADX são mais modernas, mas não substituem diretamente o papel “DEX -> bytecode Java para weaving com ajc”.

### 5.4 RV em Android

- TraceMOP (FSE 2025 demo) mostra uma linha recente de RV para Java focada em reduzir overhead e memória; não resolve Android weaving, mas indica que a comunidade está se movendo para monitores mais seletivos e explícitos: https://conf.researchr.org/details/fse-2025/fse-2025-demonstrations/40/TraceMOP-An-Explicit-Trace-Runtime-Verification-Tool-for-Java
- RV-Droid é a referência Android clássica baseada em AspectJ, mas antiga: https://link.springer.com/chapter/10.1007/978-3-642-35632-2_11
- DiSL e BISM continuam alternativas tecnicamente interessantes para instrumentação, mas exigiriam mudança arquitetural de grande porte; não são substitutos plausíveis para uma change incremental da gh50.

## 6. Riscos e mitigações

| Mudança | Risco | Probabilidade | Impacto | Mitigação |
|---------|-------|---------------|---------|-----------|
| `--no-desugaring` | APKs que ainda dependem de desugaring falharem ou gerarem DEX incompatível | Média | Média/Alta | Validar em amostra representativa; se necessário, aplicar só quando houver sinal claro de conflito `j$` ou como flag configurável |
| `-proceedOnError` | APK “instrumenta”, mas classes críticas ficam sem weaving e a cobertura MOP real cai sem ficar visível | Alta | Alta | Logar classes ignoradas pelo ajc e reportar contagem por APK |
| `-xmlConfigured` + `aop.xml` | Perda de detecção em chamadas originadas de bibliotecas, porque os specs usam `call()` | Alta | Média/Alta | Documentar explicitamente que a meta é monitorar código do app; medir deltas em monitores generic/generic_new |
| `-xmlConfigured` + `aop.xml` | `ajc` ainda ler/corromper classes excluídas via `-inpath`, tornando o ganho parcial | Média | Alta | Tratar pre-filtering como fallback real em outra change, não como detalhe implícito |
| Não implementar pre-filtering | Se o `aop.xml` não bastar, a change pode entregar ganho abaixo do esperado | Média | Alta | Tornar o fallback uma follow-up change já prevista e com critério de gatilho |
| Atualizar build-tools junto com gh50 | Misturar variáveis e perder atribuição causal do ganho | Alta | Média | Medir gh50 isoladamente antes de mexer no SDK |
| `-proceedOnError` + `aop.xml` | Falso senso de sucesso: mais APKs produzidos, mas com cobertura MOP heterogênea e pouco comparável | Alta | Alta | Registrar por APK: classes excluídas, classes com erro no ajc, fase/tool, e se o APK final passou em verificação |
| `android.jar` fixo em 29 | APKs recentes compilados contra APIs 35/36 falharem por classpath/stubs desatualizados | Média | Alta | Priorizar seleção dinâmica de `android.jar` em change separada ou logo após gh50 |

## 7. Pontos positivos

- A change ataca exatamente as famílias de erro mais frequentes observadas nos datasets.
- O uso de `-xmlConfigured` em CTW foi descrito corretamente quanto ao path explícito.
- A delta preserva e incorpora corretamente o endurecimento do gh49 sobre `_error_phase` e `reraise=True`.
- O ambiente local já tem SDK suficiente para testar API dinâmica (`android-29` a `android-34`, build-tools até `35.0.1`).

## 8. Pontos negativos / gaps

- Proposal, delta spec e design não estão alinhados sobre o fallback de pre-filtering.
- O design subestima o trade-off de cobertura causado por excluir callers de biblioteca em um ecossistema 100% `call()`-based.
- O racional de `--no-desugaring` está mais categórico do que a documentação do d8 permite sustentar.
- Não há critério de observabilidade para “partial weaving”: faltam métricas de quantas classes ficaram sem advice por APK.

## 9. Sugestões de melhoria

1. Corrigir a rastreabilidade OpenSpec antes de qualquer implementação.
2. Reescrever o rationale de `--no-desugaring` como mitigação condicional, não como verdade geral.
3. Adicionar um invariant/cenário ou pelo menos uma nota explícita de trade-off: “exclusões preservam foco em código do app, mas removem detecção originada de bibliotecas”.
4. Adicionar telemetria por APK para classes excluídas e classes descartadas por `-proceedOnError`.
5. Planejar uma follow-up change para `android.jar` dinâmico por `targetSdk/compileSdk`.
6. Tratar pre-filtering como fallback formal separado com gatilho empírico objetivo.
7. Definir desde já um critério de sucesso mensurável para gh50: aumento da taxa de instrumentação em uma amostra fixa, nenhum aumento de falhas `dex2jar`, e log por APK com contagem de classes excluídas e classes puladas por `ajc`.

## 10. Conclusão e recomendação final

Minha recomendação final é **não implementar imediatamente do jeito que os artefatos estão, mas avançar com a change após uma revisão curta e obrigatória dos artefatos**. Em termos práticos:

1. Ajustar `proposal.md`, `design.md` e `tasks.md` para que o escopo fique inequívoco.
2. Assumir explicitamente que a meta da gh50 é melhorar **taxa de instrumentação** preservando monitoramento do **código do app**, e não necessariamente manter a mesma cobertura MOP sobre bibliotecas.
3. Implementar e medir a gh50 isoladamente, sem misturar update de build-tools ou refatoração de `android.jar`.
4. Se `-xmlConfigured` não reduzir materialmente as falhas `d8`/stack-map na amostra de validação, abrir imediatamente a change sucessora para pre-filtering.

Com essas condições, a gh50 deixa de ser uma proposta ambígua e passa a ser um experimento controlado, com risco técnico administrável e valor claro para a pesquisa.

## Fontes externas

- AspectJ `ajc` documentation: https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html
- Android `d8` documentation: https://developer.android.com/tools/d8
- Android Java 8/desugaring documentation: https://developer.android.com/studio/write/java8-support
- Android SDK Build Tools release notes: https://developer.android.com/tools/releases/build-tools
- AspectJ 1.9.24 release notes: https://github.com/eclipse-aspectj/aspectj/blob/master/docs/release/README-1.9.24.adoc
- AspectJ 1.9.25 release notes: https://github.com/eclipse-aspectj/aspectj/blob/master/docs/release/README-1.9.25.adoc
- dex2jar releases: https://github.com/pxb1988/dex2jar/releases
- Enjarify repository note: https://github.com/google/enjarify
- TraceMOP FSE 2025 demo: https://conf.researchr.org/details/fse-2025/fse-2025-demonstrations/40/TraceMOP-An-Explicit-Trace-Runtime-Verification-Tool-for-Java
- RV-Droid: https://link.springer.com/chapter/10.1007/978-3-642-35632-2_11

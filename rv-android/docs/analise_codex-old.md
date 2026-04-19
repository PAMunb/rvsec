# Análise: Change gh50-improve-instrumentation
Data: 2026-04-18
Modelo: GPT-5 Codex

## 1. Resumo executivo

A change `gh50-improve-instrumentation` é coerente com o objetivo de elevar a taxa de instrumentação, e há forte evidência local de que os três mecanismos propostos atacam famílias reais de falha: no dataset ASE/JCA, 220/364 erros caem na família `d8`/stack-map, 33/364 na família `j$`, e 109/364 em `ajc`; no dataset F-Droid 2026, o baseline local confirma 70/400 sucessos para JCA (17,5%) e 216/400 para `generic_new` (54,0%). A parte mais sólida do design é o uso de `ajc -xmlConfigured <path>` em CTW com `aop.xml` explícito, o que é confirmado pela documentação oficial do AspectJ. O principal gap técnico está na alegação de que excluir bibliotecas “preserva totalmente” o monitoramento MOP do código do app: a contagem global dos `.mop` mostra `call(...)` em 100% dos arquivos dos conjuntos `jca` (142 ocorrências, 0 `execution`), `generic` (436, 0) e `generic_new` (89, 0), então excluir classes de biblioteca do weaving remove observação sempre que o chamador está em pacote excluído. Isso pode ser aceitável para o objetivo experimental, mas é um trade-off real de cobertura, não apenas uma otimização sem perda.

## 2. Análise de consistência dos artefatos

### 2.1 Rastreabilidade

Artefatos lidos:
- Change: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh50-improve-instrumentation/{proposal.md,design.md,tasks.md,specs/instrumentation/spec.md}`
- Baseline: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/specs/{instrumentation/core/experiment/tools}/spec.md`
- Código: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-instrumentation/src/rv_instrumentation/{rvandroid.py,config.py}`

Rastreabilidade proposal -> delta spec:
- `--no-desugaring` -> `INV-INS-13` + cenário `Successful instrumentation with d8 --no-desugaring`
- `-proceedOnError` -> `INV-INS-14` + cenário `ajc proceeds on class-level errors`
- `-xmlConfigured` + `aop.xml` + YAML -> `INV-INS-15`, `INV-INS-16` + cenários `Weaving with class exclusion via aop.xml` e `No weaving_excludes.yaml (backward compatible)`

Rastreabilidade delta spec -> design:
- `INV-INS-13`, `INV-INS-14`, `INV-INS-15`, `INV-INS-16` aparecem no mapping table do design.
- Compatibilidade sem YAML e incorporação de `__merge_support_classes`/gh49 também aparecem no design.

Rastreabilidade design -> tasks:
- `_load_weaving_excludes()` -> tasks `1.2`, `1.4`
- `_generate_aop_xml()` -> tasks `1.3`, `1.4`
- `__d8()` com `--no-desugaring` -> tasks `2.1`, `2.4`
- `__weave_monitors()` com `-proceedOnError`/`-xmlConfigured` -> tasks `2.2`, `2.3`, `2.4`
- Validação empírica -> tasks `3.1` a `3.6`

Achados:
- Não encontrei capability do proposal sem cobertura na delta spec.
- Não encontrei entrada do mapping table sem ao menos uma task correspondente.
- Há tasks extra-operacionais (`4.1` a `4.3`) que não têm requirement específico na spec; isso não é inconsistência, mas são tarefas de verificação/QA, não de comportamento.

### 2.2 Consistência com specs existentes

Headers `MODIFIED`:
- O header da delta spec, `Requirement: APK Instrumentation with Monitors (FR02)`, bate exatamente com o header da spec principal.

Cenários FR02 da spec principal:
- `Successful single APK instrumentation` -> presente na delta
- `Skip existing instrumented APK` -> presente
- `Force re-instrumentation` -> presente
- `Pipeline phase failure with accurate phase reporting` -> presente
- `Batch instrumentation with mixed results` -> presente
- `dex2jar conversion failure with phase from outer decorator` -> presente
- `Instrumentation verification detects unchanged APK` -> presente
- `Maven dependency resolution failure` -> presente

Conclusão:
- A delta preserva todos os 8 cenários existentes de FR02 e adiciona 4 novos cenários específicos da change.

IDs de invariantes:
- Baseline existente usa `INV-INS-01` a `INV-INS-12`.
- Delta usa `INV-INS-13` a `INV-INS-16`.
- Não há conflito de IDs.

Incorporação de gh49:
- A spec base já menciona `_error_phase` e `getattr(ex, "_error_phase", fallback)`.
- A delta incorpora `__merge_support_classes()` na lista de métodos com `reraise=True`.
- O código atual em `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py` já mostra `instrument()`, `__include_generated_monitors()`, `__weave_monitors()`, `__create_apk()`, `__merge_support_classes()` e `__sign_apk()` com `reraise=True`, além de uso de `getattr(ex, "_error_phase", ...)`.

### 2.3 Consistência técnica

`ajc -xmlConfigured` em CTW:
- Evidência direta: a documentação oficial do AspectJ afirma que `-xmlConfigured <files>` configura CTW e que, em CTW, “there is no magical file name like aop.xml ... needs to be specified on the command line explicitly”.
- Fonte: https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html (linhas 63-90, consultado em 2026-04-18; página atualizada, crawl recente).
- Conclusão: o design está correto ao passar `-xmlConfigured <path-to-aop.xml>` explicitamente.

`tmp_dir/aop.xml` sem `META-INF/`:
- Evidência direta: a mesma documentação oficial diz que CTW não faz auto-discovery estilo LTW.
- Conclusão: escrever `aop.xml` em `tmp_dir/aop.xml` e passar o path direto é tecnicamente válido.

Limitações ignoradas no design:
- Evidência direta: a documentação oficial também diz que, em CTW, `<include within="..."/>` no bloco `<weaver>` é ignorado, e que scopes/excludes só afetam “regular pointcuts”, não ITDs.
- Fonte: https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html
- Implicação: o design está correto por usar `<exclude within="..."/>`, mas deveria registrar explicitamente essas limitações.

Coverage.aj vs `aop.xml`:
- Evidência direta local: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj` exclui `androidx..*`, `kotlin..*`, `com.google..*`, `com.facebook..*`, `org.apache..*`, etc. do pointcut `traced()` baseado em `execution(* *.*(..))`.
- Diferença técnica:
- `Coverage.aj` faz exclusão no nível do pointcut de cobertura, portanto evita logging de execuções desses métodos.
- `aop.xml` faz exclusão no nível do weaver, portanto impede que advice dos monitores seja inserido nessas classes.
- Veredicto: não é redundância simples. `Coverage.aj` reduz métricas de cobertura; `aop.xml` reduz a visibilidade dos monitores.

`--no-desugaring`:
- Evidência direta: a doc oficial do `d8` define `--no-desugaring` como “Disable Java 8 language features” e diz “Use this flag only if you don't intend to compile Java bytecode that uses Java 8 language features.”
- Fonte: https://developer.android.com/tools/d8 (atualizada em 2026-03-05 UTC).
- Conclusão: a formulação atual da delta spec, que o trata como MUST por causa de `--min-api 26`, é forte demais. O fato de `min-api 26` ser alto ajuda, mas não prova por si só que nenhum bytecode de entrada ou biblioteca de suporte precisa de desugaring.

### 2.4 Formato e completude

Checagens:
- Todos os cenários da delta usam `####`.
- Os cenários seguem o formato `WHEN/THEN/AND`.
- `tasks.md` segue consistentemente `- [ ] X.Y`.
- Não há requirement sem cenário em FR02 da delta.

Gap residual:
- As invariantes novas têm mapeamento para testes unitários no design, mas não há critérios explícitos de teste empírico de regressão de cobertura MOP por spec set. Para esta change, isso é um gap relevante.

### Veredicto: FAIL com issues

Issues principais:
- A afirmação “MOP monitoring of app code is fully preserved” não é sustentada pelos pointcuts reais dos `.mop`.
- `INV-INS-13` trata `--no-desugaring` como invariável universal, mas a doc oficial do `d8` o condiciona à ausência de necessidade de desugaring.
- O design não documenta explicitamente as limitações oficiais de `-xmlConfigured` em CTW.

## 3. Análise de impacto das exclusões MOP

### 3.1 Impacto por spec set

Evidência direta local:
- Contagem global nos `.mop`:
- `jca`: 23 arquivos, `call(` = 142, `execution(` = 0
- `generic`: 118 arquivos, `call(` = 436, `execution(` = 0
- `generic_new`: 27 arquivos, `call(` = 89, `execution(` = 0

JCA:
- Exemplos lidos: `CipherSpec.mop`, `CipherInputStreamSpec.mop`, `GCMParameterSpecSpec.mop`
- Todos usam `call(...)` em APIs como `Cipher.getInstance`, `Cipher.init`, `Cipher.update`, `Cipher.doFinal`, `CipherInputStream.read`, `GCMParameterSpec.<init>`.
- Impacto: se uma chamada a `javax.crypto.*` ou `javax.crypto.spec.*` ocorrer dentro de `com.google..*`, `androidx..*`, `kotlin..*` ou outro pacote excluído, o evento não será monitorado.
- Julgamento: para o objetivo experimental de detectar misuse no código do app, a perda de chamadas puramente internas de bibliotecas é provavelmente aceitável, mas não é zero.

Generic:
- Exemplos lidos: `FSM1.mop`, `FSM103.mop`, `FSM105.mop`
- Também usam `call(...)` em APIs gerais (`ReentrantLock`, `Condition`, `ConcurrentMap`, `Future`, `InetAddress`).
- Impacto: exclusões em bibliotecas removem observação de protocolos executados dentro dessas bibliotecas.
- Julgamento: risco moderado.

Generic_new:
- Exemplos lidos: `Closeable_MeaninglessClose.mop`, `InputStream_ManipulateAfterClose.mop`, `Map_UnsafeIterator.mop`
- Estes specs monitoram APIs extremamente difundidas (`Closeable.close`, `InputStream.read/available/reset/skip`, `Iterator.hasNext/next`, `Map.keySet/entrySet/values`, `Iterable.iterator`).
- Impacto: exclusões em `kotlin..*`, `androidx..*`, `com.google..*`, `okhttp3..*`, `okio..*` removem grande volume potencial de eventos, porque muitas chamadas a essas APIs ocorrem dentro de bibliotecas.
- Julgamento: entre os três conjuntos, `generic_new` é o mais sensível à exclusão.

### 3.2 Quantificação

Datasets locais:
- ASE 2025:
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal-jss-jca/dataset/results/instrument/exp01_jca_instrument_errors.json`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal-jss-jca/dataset/results/instrument/exp01_generic_instrument_errors.json`
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal-jss-jca/dataset/results/instrument/exp01_generic_new_instrument_errors.json`
- F-Droid 2026:
- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_JCA/errors/instrument_and_sa_errors.json`
- `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_GENERIC_NEW/errors/instrument_and_sa_errors.json`

Evidência direta:
- F-Droid 2026 JCA: 400 APKs, 330 falhas, 70 sucessos, taxa 17,5%
- F-Droid 2026 `generic_new`: 400 APKs, 184 falhas, 216 sucessos, taxa 54,0%
- ASE JCA: 364 erros, categorização por mensagem/ferramenta: `d8 stack-map family` 220, `j$ prefix/conflict` 33, `ajc/weaving class error` 109, `dex2jar` 2
- ASE Generic: 352 erros: `d8` 192, `j$` 37, `ajc` 120, `dex2jar` 2
- ASE Generic_new: 189 erros: `ajc` 111, `j$` 38, `d8` 35, `dex2jar` 2

Inferência:
- `--no-desugaring` ataca principalmente a família `j$` de 33 a 38 falhas nos datasets ASE e parte das falhas `d8` com conflito de classes pré-desugared.
- `-proceedOnError` ataca parte das falhas `ajc` e parte dos casos mistos `ajc` -> `d8`.
- `-xmlConfigured` tende a atacar a maior família nas bases ASE JCA/Generic, onde `d8` rejeita bytecode pós-weaving em classes de biblioteca.

O que não é possível afirmar com evidência direta aqui:
- Quantos APKs específicos passariam com a combinação das 3 mudanças sem rodar a change. A proposal estima 50-70% para JCA, mas isso ainda é projeção.
- Em quanto a cobertura MOP cairá por APK. Os datasets fornecem erro/sucesso, não taxa de eventos monitorados por classe/pacote.

### 3.3 Coverage.aj interação

Evidência direta:
- `Coverage.aj` já exclui os mesmos grandes pacotes de biblioteca no nível de `execution`.

Impacto adicional real do `aop.xml`:
- Antes da change:
- cobertura de métodos de biblioteca já não era contabilizada;
- mas monitores MOP ainda podiam observar chamadas originadas dessas bibliotecas, porque o bytecode delas ainda era tecido.
- Depois da change:
- essas mesmas bibliotecas deixam também de emitir eventos MOP.

Conclusão:
- Se a pesquisa quer modelar apenas o comportamento do código próprio do app, isso é defensável.
- Se a pesquisa quer capturar misuse efetivo em tempo de execução, independentemente de a origem ser app ou biblioteca embarcada, a change reduz a sensibilidade.

### Veredicto: ACEITÁVEL COM RISCO METODOLÓGICO

Aceitável porque:
- ataca a maior família observada de falhas de instrumentação;
- mantém o foco experimental no código do app mais alinhado com a exclusão já existente em `Coverage.aj`.

Problemático porque:
- a documentação da change trata a perda de monitoramento como inexistente, quando ela é real e maior em `generic_new`.

## 4. Android SDK e compatibilidade

### 4.1 API dinâmica: análise

Estado atual no código:
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-instrumentation/src/rv_instrumentation/config.py` fixa `android-29`.
- `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py` fixa `--min-api 26`.
- `__get_android_jar()` tem TODO explícito para seleção dinâmica por `app.sdk_target`.

SDK instalado localmente:
- Platforms: `android-4`, `android-10`, `android-14` a `android-34`, incluindo `android-29`, `android-30`, `android-31`, `android-32`, `android-33`, `android-34`
- Build-tools: `25.0.2`, `26.0.2`, `27.0.1`, `27.0.3`, `28.0.3`, `29.0.2`, `29.0.3`, `30.0.0`, `30.0.2`, `30.0.3`, `32.0.0`, `33.0.0`, `33.0.1`, `34.0.0`, `35.0.0`, `35.0.1`
- Cmdline-tools: `9.0`, `10.0`, `latest`, `tools`

Análise:
- Selecionar `android.jar` dinamicamente por `targetSdkVersion` ou por melhor aproximação superior é recomendável.
- Usar sempre `android-29/android.jar` para APKs que referenciam APIs mais novas pode causar problemas de resolução/classpath no `ajc` e no `d8`.
- Isso não parece ser o foco da change `gh50`, mas é uma limitação sistêmica real.

`--min-api` dinâmico:
- Evidência direta externa: a documentação oficial do `d8` trata `--min-api` como alvo do DEX resultante.
- Inferência: usar `minSdkVersion` real do APK tende a produzir saída mais fiel/eficiente e pode reduzir transformações desnecessárias.
- Risco: se o valor extraído do APK estiver inconsistente ou ausente, a instrumentação precisa de fallback robusto.

### 4.2 Build tools: atualização necessária?

Evidência direta externa:
- A documentação oficial de build-tools recomenda manter o componente atualizado e hoje exemplifica `buildToolsVersion "36.0.0"`.
- Fonte: https://developer.android.com/tools/releases/build-tools (atualizada em 2026-03-30 UTC)
- A página de notas, porém, só traz detalhe histórico até 34.0.0/33.x; não encontrei notas oficiais detalhadas sobre melhorias recentes de `d8` em stack maps inválidos.

Estado atual de `d8/R8`:
- Evidência direta primária: o repositório oficial do R8 continua ativo e aponta o Google Maven como canal estável.
- Fonte: https://r8.googlesource.com/r8/+/refs/heads/master
- Evidência secundária: repositórios de versões listam séries atuais `8.13.x`, `9.0.x` e `9.1.x` em 2026.
- Fonte secundária: https://mvnrepository.com/artifact/com.android.tools/r8/versions

Conclusão:
- Atualizar build-tools é recomendável, mas não há evidência oficial direta de que isso sozinho resolverá as falhas de stack map observadas.
- A atualização deve ser tratada como experimento complementar, não substituto das mudanças da `gh50`.

### 4.3 Compatibilidade retroativa

Inferência:
- Usar build-tools mais novos e `android.jar` mais alto tende a manter compatibilidade com APKs antigos, desde que `--min-api` permaneça compatível com o APK alvo.
- O maior risco de regressão não é “APK antigo parar de funcionar”, mas mudar a superfície de resolução do `ajc`/`d8` e introduzir novas incompatibilidades de toolchain.

### Recomendação

- Implementar a `gh50` sem acoplar, na mesma change, uma atualização ampla de SDK tools.
- Planejar uma change separada para:
- seleção dinâmica de `android.jar`
- seleção dinâmica de `--min-api`
- benchmark A/B entre build-tools `29.0.3`, `34.0.0`, `35.0.1`

## 5. Estado da arte

### 5.1 AspectJ + Android

Evidência direta:
- `ajc -xmlConfigured` em CTW com arquivo explícito é suportado oficialmente: https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html
- `-proceedOnError` é oficial e descrito como “Keep compiling after error, dumping class files with problem methods”: mesma fonte.
- AspectJ segue ativo: releases oficiais mostram `1.9.24` em 2025-04-11, `1.9.25` em 2025-11-04 e `1.9.25.1` em 2025-12-17: https://github.com/eclipse-aspectj/aspectj/releases/

Issues relevantes:
- Encontrei issue oficial recente sobre suporte a classfile major version 67, mostrando que o ecossistema continua lidando com compatibilidade de bytecode moderno, mas não achei uma issue oficial clara e específica sobre “Android + d8 + stack map tables” no tracker do AspectJ.
- Fonte: https://github.com/eclipse-aspectj/aspectj/issues/317 (aberta em 2024-09-28, fechada depois)

Inferência:
- Há evidência de manutenção do AspectJ para versões modernas do Java, mas não encontrei evidência primária de que versões mais novas do AspectJ resolvam especificamente as falhas Android/`d8` observadas aqui.

### 5.2 d8/R8

Evidência direta:
- `d8` oficial documenta `--no-desugaring` e condiciona seu uso à ausência de necessidade de Java 8 desugaring: https://developer.android.com/tools/d8
- A mesma doc diferencia `--debug` e `--release`; não encontrei afirmação oficial de que um modo seja mais tolerante a stack maps inválidos.
- O código/repo do R8 contém lógica explícita de verificação de stack maps e warnings para certos casos de ausência/invalidez, o que mostra atividade nessa área, mas não garantia de tolerância a bytecode corrompido por terceiro.
- Fonte: `CfCode.java` no repo oficial do R8 apareceu nos resultados com `StackMapStatus`/`CfFrameVerifier`.

Inferência:
- Build-tools recentes provavelmente trazem correções e robustez incremental, mas não encontrei release note oficial dizendo que `d8` ficou “mais tolerante” a stack map tables inválidos.

### 5.3 Alternativas ao dex2jar

Evidência direta:
- `dex2jar` segue ativo; release oficial mais recente encontrada: `v2.4` em 2025-10-03.
- Fonte: https://github.com/pxb1988/dex2jar/releases
- `google/enjarify` existe, mas o próprio README oficial diz que o repositório do Google pode estar desatualizado e que desenvolvimento futuro ocorreria em `Storyyeller/enjarify`.
- Fonte: https://github.com/google/enjarify
- O README oficial do Enjarify afirma explicitamente que ele foi projetado para lidar melhor com edge cases em que o dex2jar falha ou produz saída incorreta.

Inferência:
- Enjarify é tecnicamente promissor como conversor DEX -> bytecode Java, mas o status de manutenção oficial do repositório Google é fraco.
- Como `dex2jar` teve release recente e já está integrado ao pipeline atual, trocar de conversor deveria ser uma investigação separada, não parte desta change.

### 5.4 RV em Android

Evidência direta:
- Não encontrei, em fontes primárias 2024-2026, um novo tool/paper Android-specific comparável a RV-Android focado em weaving offline de APKs.
- Ferramentas recentes encontradas são Java-focused:
- TraceMOP (FSE 2025 demo): https://conf.researchr.org/details/fse-2025/fse-2025-demonstrations/40/TraceMOP-An-Explicit-Trace-Runtime-Verification-Tool-for-Java
- DiSL (projeto SPEC): https://research.spec.org/tools/overview/disl/

Leitura do estado do campo:
- Android-specific RV recente parece escasso nas fontes encontradas; as referências Android que apareceram continuam sendo mais antigas (`RV-Droid`, `RV-Android`, `ADRENALIN-RV`).
- DiSL é mais expressivo que AspectJ no nível de bytecode e evita algumas restrições estruturais de AspectJ, mas o material público encontrado sugere maturidade antiga, não foco recente em Android moderno.
- TraceMOP é promissor para RV em Java, mas não é solução pronta para APK weaving.

Seção de suficiência:
- Procurei trabalhos/ferramentas 2024-2026 focados em RV para Android; encontrei material recente para RV em Java e instrumentação bytecode, mas não uma alternativa Android madura claramente mais pronta que o pipeline atual. Isso limita a força de qualquer recomendação de substituição do AspectJ nesta análise.

## 6. Riscos e mitigações

| Mudança | Risco | Probabilidade | Impacto | Mitigação |
|---------|-------|---------------|---------|-----------|
| `--no-desugaring` | APK/monitor/runtime precisar de desugaring real | Média | Alto | Tratar como mudança empírica, não como MUST absoluto; validar em amostra com e sem flag |
| `--no-desugaring` | resolver `j$` mas expor novas falhas de compatibilidade Java 8 | Média | Médio | teste cruzado por spec set e por faixa de `minSdk` |
| `-proceedOnError` | gerar APK “sucesso” com monitoramento parcial silencioso | Alta | Alto | registrar classes/fases com erro do ajc; marcar resultado como sucesso parcial ou gerar relatório por classe |
| `-proceedOnError` | `check_if_instrumented()` passar mesmo com weaving muito incompleto | Alta | Médio | adicionar métrica mínima de classes/advice woven no relatório empírico |
| `-xmlConfigured` + `aop.xml` | queda real de cobertura MOP em chamadas originadas de bibliotecas | Alta | Alto | documentar trade-off; medir eventos RV antes/depois em subconjunto de APKs |
| `-xmlConfigured` + `aop.xml` | exclusões não bastarem se o `ajc` ainda processar classes problemáticas do `-inpath` | Média | Alto | manter fallback de pre-filtering como plano B, mas só após validação empírica |
| Não implementar pre-filtering | persistência de parte da família dominante de falhas | Média | Alto | deixar critério explícito de fallback: se ganho ficar abaixo do alvo, abrir change separada |
| `-proceedOnError` + `aop.xml` | combinação mascarar falhas residuais ao mesmo tempo em que reduz observabilidade | Alta | Alto | exigir relatório empírico com sucesso, sucesso parcial e regressão de cobertura |

## 7. Pontos positivos

- Forte alinhamento com os datasets locais de falha.
- Uso de `-xmlConfigured` está tecnicamente bem fundamentado por documentação oficial.
- A change preserva compatibilidade backward quando não houver YAML.
- A delta spec está bem conectada ao baseline e incorpora adequadamente as correções de `gh49`.

## 8. Pontos negativos / gaps

- O texto atual superestima preservação de cobertura MOP.
- `INV-INS-13` está redigida como certeza técnica onde a fonte oficial impõe condição.
- Falta critério formal para classificar “sucesso parcial” sob `-proceedOnError`.
- Falta plano explícito de medição da perda de cobertura por spec set, especialmente `generic_new`.
- O tema `android.jar`/`--min-api` dinâmicos continua como limitação estrutural fora da change.

## 9. Sugestões de melhoria (priorizadas)

1. Reescrever a claim central da proposal/design para: “preserva o monitoramento do código do app e reduz/descarta monitoramento originado em bibliotecas excluídas”.
2. Rebaixar `INV-INS-13` de afirmação absoluta para requisito condicionado por validação empírica do pipeline atual.
3. Adicionar no design/spec um conceito explícito de “instrumentação parcial” para `-proceedOnError`.
4. Incluir tarefa empírica obrigatória de regressão de cobertura/eventos RV em APKs já instrumentáveis, por conjunto `jca` e `generic_new`.
5. Planejar change separada para seleção dinâmica de `android.jar` e `--min-api`.
6. Se `-xmlConfigured` não for suficiente, implementar pre-filtering em change própria, não nesta.

## 10. Conclusão e recomendação final

Recomendação final: **aprovar conceitualmente a change, mas não aprovar o texto atual sem ajustes**.

Motivos:
- As três mudanças propostas atacam famílias reais de falha e têm plausibilidade alta de elevar a taxa de instrumentação.
- O desenho de `-xmlConfigured` em CTW está tecnicamente correto segundo a documentação oficial.
- O maior problema não é a implementação proposta, e sim a interpretação metodológica: excluir bibliotecas do weaving **não** preserva integralmente a cobertura MOP; isso é um trade-off explícito entre mais APKs instrumentados e menos observação dentro de bibliotecas excluídas.

Recomendação prática:
- seguir com a change após ajustar proposal/spec/design para refletir esse trade-off;
- exigir validação empírica em duas dimensões:
- ganho de taxa de instrumentação
- perda de eventos/violations observados por spec set

## Fontes externas

- AspectJ `ajc` dev guide: https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html
- AspectJ releases: https://github.com/eclipse-aspectj/aspectj/releases/
- AspectJ issue #317: https://github.com/eclipse-aspectj/aspectj/issues/317
- Android `d8` official doc: https://developer.android.com/tools/d8
- Android SDK Build Tools release notes: https://developer.android.com/tools/releases/build-tools
- R8 official repository: https://r8.googlesource.com/r8/+/refs/heads/master
- dex2jar releases: https://github.com/pxb1988/dex2jar/releases
- Enjarify official repository: https://github.com/google/enjarify
- TraceMOP (FSE 2025 demo): https://conf.researchr.org/details/fse-2025/fse-2025-demonstrations/40/TraceMOP-An-Explicit-Trace-Runtime-Verification-Tool-for-Java
- DiSL project page: https://research.spec.org/tools/overview/disl/
- R8 versions list (secondary): https://mvnrepository.com/artifact/com.android.tools/r8/versions

# Análise do Pré-plano: Atualização GATOR/Soot para APKs Modernos

**Data da análise**: 2026-04-19
**Documento analisado**: `docs/20260419_gator.md`
**Spec de referência**: `openspec/specs/analysis/spec.md`
**Modelo**: Claude Opus 4.6

---

## 1. Resumo Executivo

O pré-plano identifica corretamente a causa raiz (Soot 3.3.0 `InternalTypingException` em `ClassHierarchy.typeNode()`) e propõe três fixes complementares. A abordagem em camadas (opções defensivas + continue gracioso + upgrade Soot) é sólida e espelha com sucesso a estratégia da gh50. **Porém, a análise contém um erro crítico no diagnóstico do fluxo de crash**: a stack trace mostra que o crash ocorre durante a construção do call graph CHA (`CHATransformer.internalTransform()`), ANTES do GATOR `Flowgraph` executar — invalidando parcialmente o FIX 2 como descrito. Adicionalmente, o FIX 2 cobre apenas o `catch` de `createOpNode()` (Flowgraph.java:340), mas a chamada desprotegida a `retrieveActiveBody()` (Flowgraph.java:274) é igualmente vulnerável. O FIX 3 (upgrade Soot 4.7.0) é a intervenção de maior impacto e está empiricamente validada. A estimativa de 50-70% de taxa SA é plausível com os três fixes combinados, mas depende de evidência adicional sobre o comportamento do Soot 4.7.0 especificamente (os testes empíricos foram com 4.6.0 via CogniCrypt).

---

## 2. Análise de Consistência

### 2.1 Consistência interna

O documento é **largamente consistente**, mas apresenta as seguintes questões:

**Inconsistência crítica — Localização do crash**:
- A Seção 1.2 descreve o fluxo de crash como: `Flowgraph.build()` → `createOpNode()` → `retrieveActiveBody()` → crash
- Porém, a stack trace (Seção 1.1) mostra claramente: `CHATransformer.internalTransform()` → `CallGraphBuilder.build()` → `OnFlyCallGraphBuilder.processNewMethod()` → `SootMethod.retrieveActiveBody()` → `DexBody.jimplify()` → crash
- Isto significa que o crash ocorre durante a construção do call graph CHA, **antes** do `wjtp.gui` phase (GATOR) sequer executar
- O FIX 2 (continue no `Flowgraph.java`) não pode interceptar este crash

**Inconsistência menor — Linha do crash**:
- O FIX 2 altera o catch de `createOpNode()` (Flowgraph.java:340-343)
- Mas `Flowgraph.processApplicationClasses()` também chama `retrieveActiveBody()` na linha 274, **fora de qualquer try-catch**
- Mesmo que o CHA complete com sucesso, um método de aplicação que não foi resolvido durante CHA pode crashar na linha 274

**Consistência positiva**:
- A analogia gh50 (Seção 4.4) é internamente coerente e rastreável
- A tabela comparativa GATOR vs CryptoAnalysis vs FlowDroid (Seção 2.1) é factualmente correta
- A evidência empírica (Seção 4.7) suporta as conclusões sobre FIX 1 e FIX 3
- A numeração dos fixes corresponde entre todas as seções

### 2.2 Coerência com a spec `analysis/spec.md`

- O pré-plano é coerente com a spec. A spec define o pipeline como `GATOR → JSON → StaticAnalysisParser → StaticAnalysisData`, e os fixes não alteram este pipeline — apenas melhoram a robustez do GATOR
- INV-ANA-06 (parse parcial sem propagação de exceções) já suporta JSONs parciais, o que é coerente com o FIX 2
- INV-ANA-11 (caching inteligente) permanece intacto
- A spec não impõe requisitos sobre quais fases Soot devem estar ativas, então FIX 1 (desabilitar `jb.sils`/`jb.dae`) não viola nenhum invariante

### 2.3 Rastreabilidade

| Problema | Causa raiz | Fix | Validação |
|----------|-----------|-----|-----------|
| SA 27.6% | Soot 3.3.0 TypeResolver crash | FIX 1+2+3 | Teste com 10 APKs (proposto) |
| `InternalTypingException` | `ClassHierarchy.typeNode(null)` | FIX 1 (opções) + FIX 3 (upgrade) | CogniCrypt 4.6.0 não crasha (validado) |
| JSON nunca produzido | `throw RuntimeException` no Flowgraph | FIX 2 (continue) | Lógico, mas parcialmente incorreto (ver §3.2) |
| Soot fragmentado (3.3.0/4.3.0/4.4.1) | Evolução orgânica do projeto | FIX 3 (unificação) | Compilação + testes |

---

## 3. Análise Técnica dos Fixes

### 3.1 FIX 1: Opções Soot defensivas no Main.java

**Avaliação: SÓLIDO, com ressalvas**

As opções propostas baseiam-se na configuração do CryptoAnalysis 5.0.1 e FlowDroid 2.15+, que funcionam com APKs modernos. Análise de cada opção:

| Opção | Efeito real | Impacto na análise GATOR | Risco |
|-------|------------|--------------------------|-------|
| `jb.sils enabled:false` | Desabilita Static Inlining Local Splitter. Evita que o `LocalSplitter` tente dividir registros reutilizados entre tipos incompatíveis — exatamente o cenário que dispara o bug #1071 | **Positivo**: reduz incidência do crash. **Negativo**: bodies Jimple podem ter mais variáveis locais, levemente maior consumo de memória | Baixo |
| `jb.dae enabled:false` | Desabilita Dead Assignment Elimination. Preserva atribuições mortas no Jimple | **Positivo**: evita crash em cenários onde DAE recalcula tipos. **Negativo**: bodies levemente maiores, sem impacto na análise de GUI | Baixo |
| `-no-bodies-for-excluded` | Não jimplifica classes em pacotes excluídos | **Positivo**: evita crash em classes excluídas. **Cuidado**: GATOR precisa de bodies de `android.*` para análise de widgets | Médio — ver abaixo |
| `-exclude kotlin.` / `-exclude kotlinx.` | Exclui Kotlin stdlib da jimplificação | **Positivo**: evita crash no código mais problemático. **Negativo**: perde reachability em specs generic que monitoram APIs de uso geral usadas pelo Kotlin | Baixo para JCA, Médio para generic |
| `ignore_resolution_errors` | Ignora classes/métodos não resolvíveis em vez de lançar exceção | **Cuidado**: esta opção trata `ClassResolutionFailedException`, NÃO `InternalTypingException`. Pode não prevenir o crash específico | Baixo, mas eficácia incerta |
| `throw_analysis_dalvik` | Usa análise de exceções específica para Dalvik em vez da genérica Java | **Positivo**: semanticamente correto para APKs | Muito baixo |

**Ressalva importante sobre `no-bodies-for-excluded`**: O pré-plano corretamente nota que NÃO se deve excluir `android.*`/`androidx.*` do body loading porque o GATOR precisa analisar widgets e listeners do framework. No entanto, `-no-bodies-for-excluded` combinado com `-exclude kotlin.*` vai impedir a jimplificação da kotlin stdlib. Se o GATOR precisar iterar métodos de classes Kotlin base durante a análise WTG (por exemplo, classes `kotlin.jvm.functions.Function*` usadas como callbacks), poderá encontrar phantom refs. O `-allow-phantom-refs` (já presente) deve mitigar isto.

**Questão técnica**: O `ignore_resolution_errors` previne crashes de resolução de classes, mas NÃO de typing. O `InternalTypingException` ocorre durante jimplificação (`DexBody.jimplify()`), não durante resolução. Portanto, `ignore_resolution_errors` provavelmente NÃO resolve o crash principal. A redução de incidência viria principalmente de `jb.sils off` + `jb.dae off` + excludes, não de `ignore_resolution_errors`.

### 3.2 FIX 2: Continue em vez de throw no Flowgraph.java

**Avaliação: PARCIALMENTE INCORRETO — necessita ampliação**

O FIX 2 propõe alterar Flowgraph.java:340-343:
```java
// ANTES:
} catch (Exception e) {
    throw new RuntimeException(e);  // FATAL
}

// DEPOIS:
} catch (Exception e) {
    continue;  // parcial > nada
}
```

**Problema 1 — Localização errada do crash principal**:

A stack trace do crash (Seção 1.1 do pré-plano) mostra que `retrieveActiveBody()` é chamado por `OnFlyCallGraphBuilder.processNewMethod()` durante a construção do call graph CHA. Isto acontece na fase `cg` do Soot, ANTES da fase `wjtp.gui` (GATOR). O Flowgraph nunca executa se o CHA crashar. Portanto, FIX 2 sozinho **não resolve o crash mostrado na stack trace**.

**Problema 2 — `retrieveActiveBody()` desprotegido na linha 274**:

Mesmo que o CHA complete com sucesso (graças a FIX 1 + FIX 3), o `Flowgraph.processApplicationClasses()` chama `currentMethod.retrieveActiveBody()` na linha 274 **sem nenhum try-catch**:

```java
// Flowgraph.java:274 — DESPROTEGIDO
Body b = currentMethod.retrieveActiveBody();
```

Se o CHA com `all-reachable:true` já resolveu todos os bodies, a chamada na linha 274 retorna o body cacheado sem re-jimplificar. Porém, se algum body não foi resolvido durante CHA (por exemplo, porque as opções do FIX 1 evitaram sua resolução), a linha 274 tentará jimplificar e poderá crashar.

**O FIX 2 deveria ser expandido para incluir**:

```java
// Flowgraph.java:274 — PROPOSTA CORRIGIDA
Body b;
try {
    b = currentMethod.retrieveActiveBody();
} catch (Exception e) {
    Logger.warn(TAG, "Skipping method " + currentMethod.getSignature()
        + ": " + e.getMessage());
    continue;
}
```

**Análise de segurança do `continue` no createOpNode**:

O `continue` no catch de `createOpNode()` é seguro. O `createOpNode()` retorna um `NOpNode` que representa uma operação do framework Android (inflate, findViewById, etc.). Se falhar:
- O Flowgraph perde este OpNode específico
- Widgets ou transições associadas a este statement ficam ausentes
- Mas o loop continua processando os demais statements
- O JSON final terá dados parciais (windows/widgets incompletos) mas será produzido

Isto é coerente com INV-ANA-06 (parse parcial sem propagação de exceções) e com o princípio do pré-plano "parcial > nada".

### 3.3 FIX 3: Upgrade Soot 3.3.0 → 4.7.0

**Avaliação: SÓLIDO, risco gerenciável**

**Compatibilidade de API**:

A API core do Soot é preservada de 3.x para 4.x. Os pacotes Java (`soot.*`) mantêm o mesmo namespace apesar da mudança de groupId Maven (`ca.mcgill.sable` → `org.soot-oss`). As classes usadas pelo GATOR foram verificadas:

| API | Status em 4.7.0 | Risco |
|-----|-----------------|-------|
| `Scene.v()`, `Scene.v().getCallGraph()`, `Scene.v().getApplicationClasses()` | Preservada | Nenhum |
| `SootClass`, `SootMethod`, `SootMethod.retrieveActiveBody()` | Preservada | Nenhum |
| `Options.v()`, `Options.v().set_*()` | Preservada | Nenhum |
| `Transform`, `SceneTransformer`, `Pack`, `PackManager` | Preservada | Nenhum |
| `CallGraph`, `CHATransformer` | Preservada | Nenhum |
| `soot.jimple.toolkits.typing.integer.*` (TypeResolver, ClassHierarchy) | Preservada, com melhorias internas | Nenhum direto |
| `soot.dexpler.DexBody` | Preservada, com melhorias no Dexpler | Nenhum direto |
| `soot.jimple.toolkits.callgraph.OnFlyCallGraphBuilder` | Preservada | Nenhum |

**Possíveis breaks**:
- Classes internas de `soot.dexpler.*` (usadas indiretamente)
- Mudanças em assinaturas de métodos de classes utilitárias internas
- Conflitos transitivos de dependências (Guava, ASM, etc.)

**Sobre `ClassHierarchy.typeNode()`**:
O pré-plano afirma (Seção 3) que "`ClassHierarchy.typeNode()` é idêntico em Soot 3.3.0 e 4.8.0. O bug nunca foi corrigido." Isto é parcialmente verdadeiro — o mapa de tipos fixos (`boolean`, `byte`, `short`, `char`, `int`) permanece igual. Porém, as versões 4.x trazem melhorias no pipeline Dexpler que REDUZEM a frequência com que o `TypeResolver` recebe um tipo `null`:

1. Melhor `DexNullTransformer` — distingue `0` como inteiro vs `null` com mais precisão
2. Melhor `LocalSplitter` — trata reuso de registros Dalvik de forma mais robusta
3. Melhor tratamento de bytecode Kotlin (coroutines, inline functions)

A evidência empírica (CogniCrypt/Soot 4.6.0 não crasha em APKs que crasham Soot 3.3.0) confirma que estas melhorias incrementais são suficientes para evitar o crash na maioria dos casos.

**FlowDroid 2.10.0 vs Soot 4.7.0**:
O `rvsec-android/pom.xml` declara `flowdroid.version=2.10.0`, que traz transitivamente Soot ~4.3.0. Com o upgrade do Soot para 4.7.0 no parent pom, haverá um conflito de versões. Maven resolve isto pelo "nearest definition" — o Soot 4.7.0 declarado explicitamente no parent ganha sobre o transitivo ~4.3.0 do FlowDroid. Isto geralmente funciona porque FlowDroid 2.10.0 é compatível com Soot 4.x, mas deve ser testado.

### 3.4 Interação entre os três fixes

Os três fixes são **aditivos e não conflitantes**:

```
FIX 1 (opções defensivas)
  └─ Reduz a frequência do crash (jb.sils/jb.dae off) e o escopo (excludes)
  └─ Age no nível de PREVENÇÃO

FIX 2 (continue no Flowgraph)
  └─ Permite análise parcial quando crash individual não é evitado
  └─ Age no nível de RECUPERAÇÃO (necessita ampliação — ver §3.2)

FIX 3 (Soot 4.7.0)
  └─ Dexpler com melhorias que reduzem drasticamente a frequência do crash
  └─ Age no nível FUNDAMENTAL (raiz do problema)
```

Não há interação negativa entre eles. FIX 1 + FIX 3 juntos são mais eficazes do que separados. FIX 2 é a rede de segurança para os casos residuais.

---

## 4. Impacto na Análise Estática

### 4.1 Impacto das exclusões kotlin.*/kotlinx.*

| Spec Set | Impacto na reachability | Justificativa |
|----------|------------------------|---------------|
| **JCA** (`javax.crypto.*`, `java.security.*`) | **Mínimo** | APIs JCA são chamadas diretamente pelo código do app, não pela Kotlin stdlib. Excluir `kotlin.*` remove bodies da stdlib mas não afeta a cadeia app → JCA API |
| **generic** (`Iterator`, `InputStream`, `Map`) | **Moderado** | Kotlin stdlib usa `Iterator`, `Map`, `InputStream` internamente. Excluir bodies significa que o call graph não verá caminhos kotlin stdlib → API monitorada. Reachability indireto pode ser subestimado |
| **generic_new** | **Moderado** | Mesmo impacto que generic |

**Trade-off**: Perder reachability em stdlib Kotlin para specs generic é aceitável porque:
1. O coverage MOP foca em chamadas feitas pelo **código do app**, não pela stdlib
2. O `Coverage.aj` instrumenta apenas classes do app, não da stdlib
3. A analogia com gh50 é válida — na instrumentação, classes de dependência também são excluídas

### 4.2 Impacto do `ignore_resolution_errors`

O `ignore_resolution_errors` permite que Soot ignore classes/métodos que não podem ser resolvidos no classpath. Isto pode mascarar erros reais em dois cenários:

1. **Classe do app ausente**: Se uma classe do app depender de uma biblioteca não disponível no classpath, Soot criará phantom refs em vez de crashar. O call graph pode ter arestas faltando para esta classe.
2. **Inner classes Kotlin**: Classes como `$DefaultImpls`, `$Companion` podem não ser resolvidas se o body da classe mãe foi excluído. O call graph perde arestas para dispatches virtuais envolvendo estas classes.

**Na prática**, o impacto é mínimo porque:
- O GATOR já usa `-allow-phantom-refs` (que tem efeito similar)
- CryptoAnalysis e FlowDroid usam `ignore_resolution_errors` em produção sem degradação perceptível
- Classes de aplicação estão no classpath (o APK é o input direto)

### 4.3 Impacto do `throw_analysis_dalvik`

Esta opção muda a análise de exceções de Java genérico para Dalvik-específico. Para APKs, isto é **semanticamente correto** e **não muda o call graph** — apenas afeta a modelagem de fluxo excepcional. Nenhum impacto negativo na reachability ou MOP.

### 4.4 Impacto do Flowgraph parcial

Com FIX 2 (continue), o Flowgraph pode estar incompleto:
- **OpNodes faltando**: Widgets não detectados, listeners não modelados
- **WTG incompleto**: Transições entre windows podem estar ausentes
- **Reachability preservada**: A reachability é calculada pelo `RvsecAnalysisClient` usando `Scene.v().getCallGraph()` e BFS, INDEPENDENTE do Flowgraph. Portanto, dados de cobertura (método, MOP) não são afetados

| Consumidor | Dado | Impactado? |
|-----------|------|-----------|
| rv-coverage | reachability (cobertura) | **Não** — vem do call graph, não do Flowgraph |
| rv-agent (MOP prioritization) | reaches_mop / directly_reaches_mop | **Não** — vem do call graph |
| rv-agent (NavigationGuidance) | WTG transitions | **Parcialmente** — transições podem faltar |
| rv-agent (ScreenProcessor) | widgets | **Parcialmente** — widgets podem faltar |
| APE-RV | MopData | **Não** — usa reachability, não WTG |

---

## 5. Estado da Arte

### 5.1 Soot e o bug `InternalTypingException`

O bug `ClassHierarchy.typeNode(null)` é um problema **conhecido e nunca corrigido** no Soot. Issues relevantes:

- [soot-oss/soot#1071](https://github.com/soot-oss/soot/issues/1071) — `InternalTypingException for Integer1Type` (aberta desde 2019)
- [soot-oss/soot#1279](https://github.com/soot-oss/soot/issues/1279) — Mesmo erro em Soot 4.0.0 (fechada sem fix)
- [soot-oss/soot#262](https://github.com/soot-oss/soot/issues/262) — `Failed to apply jb` (aberta)
- [soot-oss/soot#743](https://github.com/soot-oss/soot/issues/743) — Variante com `.apk` gerado via `dx.jar`
- [soot-oss/soot#201](https://github.com/soot-oss/soot/issues/201) — `null_type` crash no Dexpler (aberta)

A causa raiz é o reuso de registros Dalvik entre tipos incompatíveis (inteiro vs objeto). O `LocalSplitter` e o `DexNullTransformer` falham em dividir corretamente estes usos, e o `TypeResolver` recebe `null` como tipo. Este bug é particularmente frequente em bytecode gerado pelo compilador Kotlin (coroutines, nullable types, inline functions).

Nenhum patch ou fork foi encontrado que corrija `ClassHierarchy.typeNode()` diretamente.

Referências:
- [Soot official site](http://soot-oss.github.io/soot/)
- [Soot GitHub](https://github.com/soot-oss/soot)
- [Soot 4.7.0 JavaDoc](https://javadoc.io/doc/org.soot-oss/soot/latest/index.html)
- [Maven: org.soot-oss:soot](https://mvnrepository.com/artifact/org.soot-oss/soot)
- [Maven: ca.mcgill.sable:soot](https://mvnrepository.com/artifact/ca.mcgill.sable/soot)

### 5.2 SootUp — Avaliação como alternativa

[SootUp](https://github.com/soot-oss/SootUp) (versão mais recente: 1.3.0) é o sucessor oficial do Soot, lançado em dezembro 2022 com arquitetura completamente redesenhada.

**Não é viável para o GATOR por várias razões**:

1. API incompatível — reescrita completa, não é um upgrade in-place
2. Suporte Android APK ainda incompleto — `ApkAnalysisInputLocation` tem limitações
3. Sem suporte a instrumentação (que o RVSEC usa)
4. Transformações incompletas e com bugs reportados
5. O GATOR depende fortemente da API singleton (`Scene.v()`, `PackManager.v()`, etc.) que foi eliminada no SootUp

O artigo "[SootUp vs. Soot - Is The New Static Analysis Library Ready For Use?](https://securitylab.servicenow.com/research/2024-11-12-sootup-vs-soot/)" (ServiceNow Security Lab, novembro 2024) conclui que SootUp ainda não é substituto completo do Soot para projetos existentes.

Referência: [SootUp paper (Springer 2024)](https://link.springer.com/chapter/10.1007/978-3-031-57246-3_13)

### 5.3 FlowDroid — Como lida com crashes do TypeResolver

O FlowDroid 2.14+ configura Soot com múltiplas opções defensivas (todas listadas na Seção 2.1 do pré-plano). Internamente:

1. Usa `set_ignore_resolution_errors(true)` para classes não resolvíveis
2. Usa `set_no_bodies_for_excluded(true)` com excludes amplos
3. Usa `throw_analysis_dalvik` para semântica correta
4. Usa `src_prec_apk_class_jimple` (mais robusto para input misto)
5. NÃO desabilita `jb.sils`/`jb.dae` (diferente do CryptoAnalysis)

A configuração do FlowDroid é detalhada em [`SootConfigForAndroid.java`](https://github.com/secure-software-engineering/FlowDroid/blob/develop/soot-infoflow-android/src/soot/jimple/infoflow/android/config/SootConfigForAndroid.java) e [`AbstractInfoflow.java`](https://github.com/secure-software-engineering/FlowDroid/blob/develop/soot-infoflow/src/soot/jimple/infoflow/AbstractInfoflow.java).

### 5.4 Androguard como alternativa para reachability

[Androguard](https://github.com/androguard/androguard) (Python, v4.1.2) lê DEX diretamente sem Jimple, eliminando o bug do TypeResolver. Oferece:
- `AnalyzeAPK()` → classes, métodos, cross-references
- Call graph via cross-references (XREF)
- Suporte a múltiplos DEX files
- Compatibilidade com APKs modernos (Kotlin, Compose)

Limitações para o caso GATOR:
- Sem análise de GUI (windows, widgets, listeners)
- Sem WTG (Window Transition Graph)
- Call graph baseado em referências estáticas (menos preciso que CHA/SPARK)
- Sem integração com MOP specs

O framework [GAPS](https://arxiv.org/html/2511.23213v2) (2025), baseado em Androguard + networkx, demonstrou desempenho superior ao FlowDroid e DroidReach em path reconstruction para Android. Porém, foca em path synthesis, não em GUI analysis.

Referências:
- [Androguard documentation](https://androguard.readthedocs.io/en/latest/api/androguard.core.analysis.html)
- [GAPS paper (2025)](https://arxiv.org/html/2511.23213v2)

### 5.5 Como outros projetos lidam com APKs modernos

| Projeto | Abordagem | Soot version |
|---------|-----------|-------------|
| CryptoAnalysis 5.0.1 | Opções defensivas + `jb.sils off` + `jb.dae off` | 4.6.0 |
| FlowDroid 2.15+ | Opções defensivas + SPARK CG + excludes amplos | 4.8.0-SNAPSHOT |
| JADX | Decompilação direta DEX → Java (sem Jimple) | N/A |
| APKTool | Decodificação de recursos (sem análise de programa) | N/A |
| Corax | Framework Java/Kotlin baseado em Soot (análise estática) | Custom |

Nenhum projeto encontrado usa um fork do Soot com patch para `ClassHierarchy.typeNode()`. A abordagem universal é: opções defensivas + versão recente + tratamento de erros gracioso.

---

## 6. Riscos e Mitigações

| # | Risco | Probabilidade | Impacto | Mitigação proposta |
|---|-------|--------------|---------|-------------------|
| R1 | FIX 3: API break durante compilação — classes internas do Soot usadas pelo GATOR podem ter mudado | Média | Médio | Compilar e corrigir pontualmente; a API core é preservada |
| R2 | FIX 3: Conflito transitivo FlowDroid 2.10.0 (Soot ~4.3.0) vs Soot 4.7.0 | Média | Médio | Maven resolve pelo "nearest definition"; testar módulos que usam FlowDroid |
| R3 | FIX 1: `jb.sils off` + `jb.dae off` podem gerar bodies Jimple com mais variáveis locais → consumo de memória | Baixa | Baixo | Monitorar heap; o GATOR já usa `-Xmx8g` |
| R4 | FIX 2 (como descrito): Crash na CHA não é interceptado | **Alta** | **Alto** | Ampliar FIX 2 para incluir `retrieveActiveBody()` (linha 274); mas crash CHA precisa de FIX 1+3 |
| R5 | FIX 1: `ignore_resolution_errors` pode causar `ConcurrentModificationException` (issue [Sable/soot#1199](https://github.com/Sable/soot/issues/1199)) | Baixa | Médio | Testar; se ocorrer, remover esta opção específica |
| R6 | FIX 3: Guava version conflict (GATOR pom: 27.1-jre; parent pom: 19.0; Soot 4.7.0: pode exigir versão mais recente) | Média | Médio | Verificar dependências transitivas; alinhar versão Guava |
| R7 | FIX 1: Excludes `kotlin.*` perdem reachability para specs generic | Baixa | Baixo | Aceitável para tese (JCA é o foco); documentar trade-off |
| R8 | Rollback necessário se upgrade falhar | Baixa | Baixo | Git permite reverter; modules deprecados já identificados para exclusão |

### Plano de rollback

1. FIX 1 e FIX 2: Revert simples — duas linhas em dois arquivos
2. FIX 3: Revert dos pom.xml (5-6 arquivos) + remover eventuais fixes de API; compilar para confirmar
3. O fat JAR `rvsec-analysis-client.jar` atual pode ser preservado como backup antes do upgrade

---

## 7. Pontos Positivos

1. **Diagnóstico completo**: A causa raiz (`ClassHierarchy.typeNode(null)`) está corretamente identificada, com stack trace, evidência empírica, e análise comparativa
2. **Abordagem em camadas**: Três fixes complementares que agem em prevenção, recuperação e resolução fundamental — estratégia robusta
3. **Analogia gh50**: A tabela comparativa (Seção 4.4) com a estratégia de instrumentação é convincente e fornece precedente
4. **Evidência empírica**: Teste com CogniCrypt/Soot 4.6.0 em 5 APKs valida a direção do FIX 3
5. **Análise de impacto por spec set**: Diferencia corretamente JCA vs generic, com trade-offs documentados
6. **Identificação de módulos deprecados**: Simplifica o upgrade ao excluir módulos não usados
7. **Tabela comparativa de configuração Soot** (Seção 2.1): Excelente — mostra claramente o gap entre GATOR e CryptoAnalysis/FlowDroid
8. **Fallback documentado** (Androguard): Plano B caso os fixes não atinjam a meta
9. **Estimativa realista**: 50-70% é conservadora e considera incerteza

---

## 8. Pontos Negativos / Gaps

### 8.1 Erro no diagnóstico do fluxo de crash (CRÍTICO)

O pré-plano assume que o crash ocorre em `Flowgraph.createOpNode()` → `retrieveActiveBody()`. A stack trace mostra que ocorre em `CHATransformer` → `CallGraphBuilder` → `retrieveActiveBody()`. Isto muda fundamentalmente a eficácia do FIX 2:
- FIX 2 não intercepta crashes durante CHA
- O crash CHA mata o processo ANTES do Flowgraph executar
- O JSON nunca é produzido não por causa do `throw` no Flowgraph, mas porque o CHA morre primeiro

### 8.2 `retrieveActiveBody()` desprotegido na linha 274 (IMPORTANTE)

Mesmo com FIX 2 no `createOpNode()` (linha 340), o `processApplicationClasses()` tem outra chamada desprotegida a `retrieveActiveBody()` na linha 274. Se CHA completar mas o body de algum método de aplicação não tiver sido resolvido, a linha 274 crashará sem ser capturada.

### 8.3 Ausência de teste com Soot 4.7.0 especificamente (IMPORTANTE)

Os testes empíricos foram feitos com CogniCrypt 5.0.1, que usa Soot **4.6.0** + FlowDroid **2.14.1**. O FIX 3 propõe Soot **4.7.0**. Não há teste direto com 4.7.0. As melhorias entre 4.6.0 e 4.7.0 são desconhecidas (changelogs detalhados não disponíveis para versões 4.x).

### 8.4 Falta de tratamento de crash na fase CHA (IMPORTANTE)

O pré-plano não discute como lidar com crashes durante a construção do call graph CHA. Opções possíveis:
- Interceptar `InternalTypingException` dentro do `OnFlyCallGraphBuilder` (requer modificação do Soot — inviável)
- Usar `TypeAssigner` com fallback para old resolver (Soot 4.x já faz isto internamente)
- Wrapping Soot em processo separado com timeout (o GATOR já é executado como processo separado pelo Python)

### 8.5 Falta de métricas de qualidade da análise parcial

O pré-plano não define como medir a **qualidade** da análise parcial (FIX 2):
- Quantos OpNodes são perdidos em média?
- Qual a degradação percentual do WTG?
- A reachability muda com Flowgraph parcial? (resposta: não, porque vem do call graph)

### 8.6 Versão alvo do Soot: 4.7.0 vs 4.6.0

A evidência empírica validou Soot **4.6.0** (via CogniCrypt). O pré-plano propõe **4.7.0** (mais recente estável). Seria mais conservador usar 4.6.0 (validado) e depois atualizar para 4.7.0 se necessário. Alternativamente, testar 4.7.0 diretamente pode funcionar dado que a API core é estável.

---

## 9. Sugestões de Melhoria Priorizadas

### P1 — Crítico (devem ser resolvidos antes da implementação)

**P1.1**: Corrigir o diagrama de fluxo de crash (Seção 1.2) para refletir que o crash ocorre durante CHA (`CHATransformer`), não no `Flowgraph.createOpNode()`. Documentar dois cenários de crash:
  - Cenário A: CHA crash (fase `cg`) — FIX 1+3 previnem
  - Cenário B: Flowgraph crash (fase `wjtp.gui`) — FIX 2 previne (se ampliado)

**P1.2**: Ampliar FIX 2 para incluir try-catch em `processApplicationClasses()` na linha 274:
```java
Body b;
try {
    b = currentMethod.retrieveActiveBody();
} catch (Exception e) {
    Logger.warn(TAG, "Skipping method " + currentMethod.getSignature()
        + ": " + e.getMessage());
    continue;
}
```

**P1.3**: Adicionar critério de aceitação para a qualidade da análise parcial: "JSON produzido deve conter seção `reachability` com ≥80% dos métodos de aplicação comparado com análise de APK que funciona (baseline NanoLedger ou cryptoapp)."

### P2 — Importante (devem ser resolvidos para maximizar eficácia)

**P2.1**: Testar Soot 4.7.0 diretamente (não apenas via CogniCrypt/4.6.0). O teste pode ser simples: compilar o GATOR com Soot 4.7.0, executar contra os 5 APKs do teste empírico, verificar se JSON é produzido.

**P2.2**: Verificar se `ignore_resolution_errors` efetivamente ajuda (pode não prevenir `InternalTypingException`). Se não ajudar, mantê-lo é inofensivo, mas não deve ser listado como fix para o crash principal.

**P2.3**: Adicionar contagem de métodos skippados (FIX 2) ao log, para monitorar degradação:
```java
int skippedMethods = 0;
// ... no catch:
skippedMethods++;
Logger.warn(TAG, "Skipped " + skippedMethods + " methods so far");
```

**P2.4**: Considerar desabilitar `all-reachable:true` nos argumentos Soot do GATOR. Com o sistema de entry points do `RvsecAnalysisClient` (Activity, Service, Receiver, Provider lifecycles), a reachability via BFS no call graph já cobre os métodos relevantes. Sem `all-reachable:true`, o CHA processará menos bodies, reduzindo a superfície de crash.

### P3 — Nice-to-have

**P3.1**: Após FIX 1+2+3, executar análise comparativa: taxa SA com Soot 3.3.0 (baseline) vs Soot 4.7.0 + opções vs Soot 4.7.0 + opções + continue. Isto quantifica a contribuição de cada fix.

**P3.2**: Documentar a versão específica do Guava necessária para Soot 4.7.0 e resolver o conflito proativamente no pom.xml.

**P3.3**: Avaliar se `src_prec_apk_class_jimple` (usado por CryptoAnalysis/FlowDroid) seria mais robusto que o `src_prec_apk` implícito do GATOR para APKs com múltiplos DEX files.

---

## 10. Conclusão e Recomendação Final

### Avaliação geral

O pré-plano é **bem fundamentado e tecnicamente sólido na direção proposta**. A abordagem em camadas (FIX 1+2+3) é a estratégia correta, espelhando com sucesso a gh50. A evidência empírica (CogniCrypt/Soot 4.6.0) fornece validação forte.

**O gap mais crítico** é o erro no diagnóstico do fluxo de crash: o crash ocorre durante CHA (fase `cg`), não no Flowgraph (fase `wjtp.gui`). Isto não invalida a estratégia — FIX 1 + FIX 3 atacam o crash CHA diretamente — mas o FIX 2 precisa ser ampliado para cobrir também a linha 274 do Flowgraph.

### Recomendação

**Prosseguir com FIX 1 + FIX 2 (ampliado) + FIX 3** via FF SDD, incorporando as correções P1.1-P1.3 antes de iniciar a implementação. A estimativa de 50-70% de taxa SA é **plausível**, especialmente com FIX 3 (evidenciado empiricamente).

**Ordem de implementação sugerida** (difere levemente do pré-plano):
1. FIX 1 (15 min) + FIX 2 ampliado (10 min) → testar com Soot 3.3.0 para medir ganho isolado
2. FIX 3 (4-8h) → testar com Soot 4.7.0 para medir ganho total
3. Comparar resultados dos dois passos

**Não recomendado neste momento**: Androguard fallback (esforço alto, benefício marginal se FIX 1+2+3 atingir 50%+), SootUp (imaturidade), upgrade FlowDroid (escopo creep).

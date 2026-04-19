# Análise Crítica do Pré-plano: Atualização GATOR/Soot para APKs Modernos

## 1. Resumo executivo

O pré-plano está bem estruturado, parte de um problema real e propõe uma direção tecnicamente plausível: endurecer a configuração do Soot, tolerar falhas parciais e sair do Soot 3.3.0. A rastreabilidade geral problema -> causa -> mitigação -> validação empírica existe e é um ponto forte do documento.

Há, porém, três fragilidades importantes. Primeiro, o **FIX 2 está superestimado**: no código atual, vários `retrieveActiveBody()` ocorrem fora do `catch` proposto, e o `RvsecAnalysisClient` só escreve JSON depois de construir o WTG; portanto, "continue em vez de throw" não garante JSON parcial por si só. Segundo, o **FIX 3 não é backward-compatible por hipótese**: a troca de `ca.mcgill.sable:soot:3.3.0` para `org.soot-oss:soot:4.7.0/4.7.1` mexe em dependências, mediação Maven e possivelmente em APIs e comportamentos internos usados pelo GATOR. Terceiro, a comparação com FlowDroid/CryptoAnalysis está na direção certa, mas algumas afirmações sobre opções defensivas do FlowDroid estão mais fortes do que as fontes públicas confirmam.

Minha recomendação final é: **seguir com a iniciativa**, mas **não implementar os três fixes como um bloco único sem faseamento**. O plano deve ser refinado para: (a) endurecimento defensivo do GATOR com telemetria; (b) tratamento de falha em nível de método/fase, não só em `createOpNode()`; (c) upgrade de dependências alinhando também FlowDroid, preferencialmente para a linha **2.15.1** com Soot **4.7.1**, ou então um piloto isolado do GATOR antes de unificar o RVSEC inteiro.

## 2. Análise de consistência

### 2.1 Consistência interna do pré-plano

O documento é majoritariamente consistente nos pontos centrais:

- O problema está claro: baixa taxa de análise estática em APKs modernos.
- A hipótese causal é plausível: Soot 3.3.0 + Dexpler + Kotlin moderno + tratamento fatal de exceções.
- A validação empírica com CogniCrypt/CryptoAnalysis reforça que a direção "Soot mais novo + configuração mais defensiva" é promissora.
- O vínculo com a spec de análise faz sentido: o sistema precisa preservar ao menos `reachability`, e idealmente `windows`, `transitions` e `components`.

Mas há inconsistências e simplificações que precisam ser corrigidas:

1. O pré-plano afirma que o `RvsecAnalysisClient` produzirá JSON parcial com o FIX 2. Isso não é garantido pelo código atual.
   O `RvsecAnalysisClient.run()` constrói `reachability`, depois chama `WTGBuilder.build(output)`, e só então chama `writeJson(...)`. Se o pipeline quebrar antes do WTG terminar, nenhum JSON é escrito, apesar de o `JsonWriter` dar `flush()` por seção.

2. O local do fix em `Flowgraph.java` está conceitualmente correto, mas a descrição do efeito é ampla demais.
   O `continue` proposto cobre apenas a exceção no trecho que envolve `createOpNode(currentStmt)`. Já o método `processApplicationClasses()` faz `Body b = currentMethod.retrieveActiveBody();` antes desse `try/catch`. Se o crash vier daí, o FIX 2 não atua.

3. A comparação GATOR vs FlowDroid/CryptoAnalysis está parcialmente apoiada, mas mistura fatos confirmados com inferências.
   A fonte pública atual de `FlowDroid` que consegui verificar (`SootConfigForAndroid.java`) mostra `exclude(...)` e `set_no_bodies_for_excluded(true)`, inclusive com comentário histórico sobre `android.*`, mas não confirma por si só que FlowDroid use exatamente `ignore_resolution_errors`, `throw_analysis_dalvik`, `jb.sils off` e `jb.dae off` da forma descrita.

4. Há uma ambiguidade importante entre "crash no pipeline Dexpler ao processar método corrente" e "crash disparado por análise de chamadas/operadores dentro de `createOpNode()`".
   O plano trata isso como se fosse a mesma superfície de correção, mas o código mostra múltiplos pontos de `retrieveActiveBody()` em `Flowgraph`, `FlowgraphRebuilder`, `ConstantAnalysis`, `CFGTraversal`, `JimpleUtil` e outras classes.

### 2.2 Coerência com a spec `analysis/spec.md`

O plano é coerente com a spec no objetivo macro: recuperar a capacidade de produzir dados estáticos úteis para:

- `reachability`, que define o universo de métodos e é o denominador da cobertura.
- `windows` e `transitions`, usados por exploração guiada.
- `components`, necessários para componentes não-Activity e MOP reachability.

Mas a spec também impõe um ponto que o plano precisa tornar explícito:

- A spec trata `reachability` como dado prioritário e admite valor diferenciado entre seções.
- O código do `RvsecAnalysisClient` escreve seções em ordem prioritária, mas apenas depois de montar tudo o que antecede o `writeJson`.
- Logo, a arquitetura atual **não implementa realmente o comportamento de degradação progressiva que a spec e o pré-plano pressupõem**.

### 2.3 Ambiguidades que podem levar a implementação incorreta

- "Trocar `throw` por `continue`" pode induzir a uma falsa sensação de resiliência total. Na prática, só cobre um ponto específico.
- "Upgrade Soot 3.3.0 -> 4.7.0 no RVSEC inteiro" pode induzir a ignorar o desalinhamento com `flowdroid.version=2.10.0` em `rvsec-android/pom.xml`.
- "Backward-compatible" está forte demais. A API pública básica do Soot é parecida, mas isso não equivale a compatibilidade de comportamento nem de empacotamento.
- "Excluir `kotlin.*`/`kotlinx.*`" precisa distinguir claramente:
  app code em Kotlin não será excluído se o package do app não começar por `kotlin`; o que se exclui é primariamente stdlib/coroutines.

### 2.4 Rastreabilidade

A rastreabilidade está boa, com uma ressalva:

- `Problema`: baixa taxa de SA.
- `Causa raiz`: crash de typing no Soot/Dexpler moderno + tratamento fatal.
- `Fix`: opções defensivas + tolerância a falhas + upgrade.
- `Teste`: CogniCrypt/CryptoAnalysis não crasha nos APKs problemáticos.

O elo mais fraco dessa cadeia é o FIX 2, porque a prova apresentada não demonstra que ele cubra o caminho real do crash em todos os casos.

## 3. Análise técnica dos fixes

### 3.1 FIX 1: opções Soot defensivas no `Main.java`

#### Julgamento geral

O FIX 1 é **razoável e de baixo custo**, mas **não previne de forma confiável** o `InternalTypingException`.

#### O que parece tecnicamente sólido

- `-no-bodies-for-excluded` é uma prática comum para reduzir superfície de jimplificação.
- Excluir `kotlin.*` e `kotlinx.*` pode reduzir crashes vindos da stdlib Kotlin e de coroutines.
- `throw_analysis_dalvik` é semanticamente apropriado para DEX e já aparece como precedente dentro do próprio repositório em `rvsec-taint`.
- `ignore_resolution_errors` tende a reduzir falhas de resolução e phantom types, o que pode estabilizar a análise em apps modernos e multidex.

#### O que está superestimado

1. `ignore_resolution_errors` não corrige o bug de typing em `ClassHierarchy.typeNode()`.
   Esse flag ajuda em resolução, não em um mapa interno que recebe tipo inesperado/nulo durante inferência.

2. `jb.sils off` e `jb.dae off` podem ajudar, mas a causalidade precisa ser tratada como hipótese, não como fato.
   O stack trace reportado aponta para `DexBody.jimplify()` e `TypeResolver`, isto é, a inferência de tipos acontece muito cedo. Desabilitar subfases de `jb` pode diminuir transformações subsequentes que reintroduzem typing problemático, mas não há garantia de que o crash principal esteja nelas.

3. O ganho de excluir `kotlin.*` depende do local real da falha.
   Se o crash surgir no body de uma classe do app compilada de Kotlin, isso não ajuda. Se surgir em chamadas/auxiliares da stdlib/coroutines, ajuda mais.

#### Efeitos colaterais na qualidade da análise

- Para **JCA**, o impacto tende a ser baixo. As APIs monitoradas estão em `javax.crypto.*` e `java.security.*`, geralmente chamadas a partir do código do app.
- Para **generic/generic_new**, o impacto pode ser relevante. A stdlib Kotlin e `kotlinx.coroutines` encapsulam bastante uso de coleções, iteração, fluxo e wrappers, o que pode esconder caminhos para MOPs genéricos.
- `ignore_resolution_errors` pode mascarar problemas reais de modelagem e produzir um call graph mais permissivo ou com buracos silenciosos.
- `throw_analysis_dalvik` tende a ser mais correto para Android, mas pode alterar detalhes do tratamento de exceções e, com isso, influenciar edges do call graph e da propagação de reachability.

#### Conclusão sobre FIX 1

Vale a pena implementar, mas com o seguinte enquadramento:

- é um **hardening**, não uma correção definitiva;
- precisa de **telemetria**;
- precisa de **avaliação separada por spec set**.

### 3.2 FIX 2: `continue` em vez de `throw` no `Flowgraph`

#### Julgamento geral

O FIX 2, como está descrito, é **útil, mas insuficiente e potencialmente enganoso**.

#### Evidência do código

Em `Flowgraph.processApplicationClasses()`:

- `Body b = currentMethod.retrieveActiveBody();` ocorre antes do bloco que envolve `createOpNode(currentStmt)`.
- o `catch` que hoje faz `throw new RuntimeException(e)` protege apenas a chamada `createOpNode(currentStmt)`.

Além disso, o mesmo `Flowgraph.java` tem outros `retrieveActiveBody()` em pelo menos mais dois pontos, e o restante do pipeline GATOR/WTG também tem várias chamadas equivalentes.

#### Risco principal

Se você trocar apenas:

```java
throw new RuntimeException(e);
```

por:

```java
continue;
```

você só torna tolerante um subconjunto pequeno dos erros. Os crashes ainda podem ocorrer:

- ao carregar o body do método corrente;
- ao reconstruir flowgraphs auxiliares;
- em análises do WTG posteriores ao `Flowgraph`.

#### Impacto sobre consistência do FlowGraph

Mesmo quando funcionar, esse `continue` pode introduzir:

- widgets sem listeners capturados;
- edges ausentes;
- transições incompletas;
- janelas presentes, mas com inventário de widgets degradado.

Isso não inviabiliza todo o pipeline, mas significa que:

- `reachability` pode continuar útil;
- `windows` e `transitions` podem ficar incompletos;
- o WTG pode degradar de forma difícil de observar sem métricas.

#### Impacto no JSON

O plano afirma que o JSON será produzido mesmo com Flowgraph parcial. No código atual isso é só parcialmente verdadeiro:

- `writeJson()` realmente faz `flush()` por seção.
- mas `writeJson()` só é chamado depois de `WTGBuilder.build(output)` concluir.
- logo, se o WTG quebrar, não há JSON algum.

#### Conclusão sobre FIX 2

Sozinho, o FIX 2 não entrega o benefício prometido. O mínimo tecnicamente seguro seria:

- capturar falha também em torno de `currentMethod.retrieveActiveBody()`;
- contabilizar métodos/statements ignorados;
- isolar falhas do `WTGBuilder`;
- separar geração de `reachability` da geração de `windows/transitions`.

Sem isso, o FIX 2 é mais um paliativo local do que um mecanismo robusto de análise parcial.

### 3.3 FIX 3: upgrade Soot 3.3.0 -> 4.7.0

#### Julgamento geral

A direção é correta, mas o plano está otimista demais quanto à compatibilidade e à escolha exata da versão.

#### O que favorece o upgrade

- O GATOR está preso em `ca.mcgill.sable:soot:3.3.0`, uma linhagem antiga e descontinuada.
- O parent já usa `org.soot-oss:soot:4.4.1`.
- Há evidência empírica local de que CogniCrypt/CryptoAnalysis com Soot 4.6.0 não reproduz o crash imediato nos APKs problemáticos.
- Em 2026, existe versão mais nova do Soot em Maven Central: **4.7.1**, publicada em **23 de fevereiro de 2026**. Portanto, `4.7.0` já não é a mais recente.

#### Onde o plano está subestimando o risco

1. O upgrade não é só "API core preservada".
   O problema real é o conjunto:
   - Maven mediation;
   - troca de groupId;
   - transitive dependencies;
   - diferenças comportamentais em Dexpler, call graph e resolução.

2. O `rvsec-gator-client` foi explicitamente desenhado para conviver com conflito de versões.
   O `client/pom.xml` exclui `ca.mcgill.sable:soot` e `org.soot-oss:soot` de dependências para empacotar um fat JAR compatível com o runtime atual. Isso mostra que o conflito é estrutural, não acidental.

3. O resto do RVSEC Android ainda referencia `flowdroid.version=2.10.0`.
   Mesmo que o GATOR vá para 4.7.x, o ecossistema local ainda está ancorado numa linha antiga do FlowDroid. Isso cria risco de mediação Maven imprevisível, principalmente em módulos que puxam Soot transitivamente.

4. Há risco de incompatibilidade de logging e dependências auxiliares.
   A linha recente do Soot usa dependências mais novas; o ecossistema do GATOR usa `slf4j` 1.7.26 em seus poms. Isso pode não quebrar tudo, mas é uma frente real de teste.

#### Classes/APIs com maior risco

Pelo código local, o GATOR usa amplamente:

- `Scene`, `SootClass`, `SootMethod`, `Transform`, `SceneTransformer`, `PackManager`, `Options`;
- `soot.jimple.*`;
- `soot.dexpler.Util` em parte da análise de intents;
- utilitários e classes de fluxo/CFG do Soot.

Ou seja, não parece um uso "mínimo" da API. Não vi dependência explícita em `TypeResolver` ou `ClassHierarchy` internos, mas o GATOR está bem acoplado ao comportamento do Soot e usa muitas APIs de análise, não apenas o núcleo superficial.

#### Conclusão sobre FIX 3

O upgrade é recomendável, mas **deve ser tratado como mini-migração de plataforma**, não como mera troca de versão.

### 3.4 Interações negativas entre os três fixes

As interações possíveis são:

1. FIX 1 + FIX 2
   Menos crashes aparentes, mas maior chance de análise "silenciosamente incompleta" sem observabilidade suficiente.

2. FIX 1 + FIX 3
   Boa sinergia. Soot mais novo + exclusões/flags defensivas é o caminho mais plausível para reduzir falhas em APKs modernos.

3. FIX 2 + FIX 3
   Pode esconder regressões estruturais do upgrade, convertendo falhas claras em resultados degradados sem alerta.

4. FIX 1 + FIX 2 + FIX 3
   É a combinação com maior chance de ganho líquido, mas também a mais difícil de depurar se aplicada toda de uma vez.

## 4. Impacto na análise estática

### 4.1 Impacto das exclusões em `kotlin.*` e `kotlinx.*`

#### JCA

Impacto provável: **baixo a moderado**.

- As chamadas de interesse normalmente ficam no código do app ou em APIs Java/Android diretamente invocadas.
- Excluir stdlib Kotlin tende a ter pouco efeito sobre a descoberta de chamadas criptográficas diretas.

#### generic / generic_new

Impacto provável: **moderado a alto**.

- Kotlin collections, coroutines e helpers encapsulam muito comportamento intermediário.
- Excluir esses pacotes pode cortar caminhos reais até MOPs genéricos.
- O efeito pode ser principalmente em `reaches_mop`, não necessariamente em `reachable`.

### 4.2 `ignore_resolution_errors`

Benefício:

- reduz abortos por classes/tipos não resolvidos;
- é particularmente útil em apps modernos, multidex e com mistura de bibliotecas.

Risco:

- pode mascarar problemas reais que deveriam virar alerta;
- pode gerar lacunas silenciosas no call graph.

Mitigação mínima:

- registrar contadores de classes/métodos com resolução degradada;
- incluir um campo de qualidade no artefato JSON ou no log do wrapper.

### 4.3 `throw_analysis_dalvik`

Essa opção é coerente com APK/DEX e tende a melhorar correção semântica no tratamento de exceções em Android. O risco principal não é "incorreção", mas mudança de comportamento observável:

- edges adicionais ou removidos no call graph;
- diferença em reachability para código que depende fortemente de caminhos excepcionais.

No contexto da spec, isso é aceitável se for:

- testado por regressão;
- comparado com baseline em APKs que já funcionam hoje.

### 4.4 Qualidade do resultado parcial

O plano precisa distinguir claramente três níveis de sucesso:

1. `reachability` confiável;
2. `reachability` útil, mas degradado;
3. `windows/transitions` degradados ou ausentes.

Hoje o documento fala em "análise parcial" como se fosse uma categoria única. Pela spec e pelo pipeline, isso é insuficiente. Para o RV-Android, uma análise parcial pode ser ótima para cobertura e ruim para navegação, ou o contrário.

## 5. Estado da arte

### 5.1 O que outros projetos fazem hoje

Pelas fontes verificadas:

- O `FlowDroid` atual continua ativo e recomenda usar versões recentes; o artefato `soot-infoflow-android` tem versão **2.15.1**, publicada em **23 de fevereiro de 2026**.
- O `SootConfigForAndroid.java` público do FlowDroid mostra uso explícito de:
  - exclusões (`java.*`, `javax.*`, `sun.*`, `android.*`, `androidx.*`, etc.);
  - `set_no_bodies_for_excluded(true)`.
- O próprio comentário do FlowDroid indica um trade-off histórico importante:
  excluir `android.*` pode quebrar análise baseada em layout callbacks, mas foi reintroduzido porque removê-lo quebrava stubs do Android.

Isso é relevante para o GATOR: não existe configuração "sem custo". Projetos maduros aceitam excluir partes do framework e compensam com modelagem específica.

### 5.2 Há alternativa melhor que Soot 4.7.0?

Para o seu cenário, sim, existem duas alternativas melhores que "subir cegamente para 4.7.0":

1. **Soot 4.7.1**, não 4.7.0.
   Em 2026-04-19, a versão mais recente disponível em Maven Central é 4.7.1, publicada em 2026-02-23.

2. **Alinhar também o FlowDroid para 2.15.1** em vez de deixar o ecossistema preso em 2.10.0.
   Isso reduz risco de incompatibilidade transiente e aproxima o RVSEC do que a cadeia moderna de análise Android realmente usa.

Alternativas conceituais:

- **SootUp 2.0.0** existe e é ativo, mas não é drop-in replacement para o GATOR legado. Para este projeto, é alternativa de pesquisa/reescrita, não de correção rápida.
- **Androguard** continua sendo a melhor alternativa de fallback para reachability quando a prioridade é robustez de parsing DEX e não WTG.

### 5.3 Como o FlowDroid lida com falhas e parcialidade

Pelas fontes públicas verificadas:

- o FlowDroid explicitamente trabalha com timeouts em etapas como callback collection e result collection;
- isso mostra uma filosofia de degradação controlada;
- o `SootConfigForAndroid` endurece o ambiente pela combinação de exclusões e `no_bodies_for_excluded`.

Não encontrei evidência pública suficiente para afirmar, com segurança, que o FlowDroid "resolve internamente" o bug específico do `TypeResolver`. O que as fontes sustentam é:

- ele endurece a configuração;
- ele usa versões mais novas da pilha;
- ele aceita operar com incompletude controlada em algumas fases.

### 5.4 Há patch específico para `ClassHierarchy.typeNode()`?

Não encontrei evidência confiável de patch oficial do Soot que corrija especificamente `ClassHierarchy.typeNode()` para esse caso.

O que há é:

- issue aberta desde **2018** para `InternalTypingException for Integer1Type` (`soot-oss/soot#1071`);
- outras issues em 4.x mostrando variantes próximas;
- evidência de que o problema foi mitigado em prática por versões mais novas e configurações defensivas, mas não claramente "consertado na raiz".

### 5.5 Fontes

- Soot 4.7.1 no Maven Central / MvnRepository:
  - https://repo1.maven.org/maven2/org/soot-oss/soot/4.7.1/
  - https://mvnrepository.com/artifact/org.soot-oss/soot/4.7.1
- Soot 4.7.0 e histórico de versões:
  - https://mvnrepository.com/artifact/org.soot-oss/soot/4.7.0
  - https://repo1.maven.org/maven2/org/soot-oss/soot/
- FlowDroid versões:
  - https://mvnrepository.com/artifact/de.fraunhofer.sit.sse.flowdroid/soot-infoflow-android
- FlowDroid `SootConfigForAndroid.java`:
  - https://github.com/secure-software-engineering/FlowDroid/blob/develop/soot-infoflow-android/src/soot/jimple/infoflow/android/config/SootConfigForAndroid.java
- FlowDroid README / configuração geral:
  - https://github.com/secure-software-engineering/FlowDroid
- Soot issues:
  - https://github.com/soot-oss/soot/issues/1071
  - https://github.com/soot-oss/soot/issues/1279
  - https://github.com/soot-oss/soot/issues/201
  - https://github.com/soot-oss/soot/issues/980
  - https://github.com/soot-oss/soot/issues/2085

## 6. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação proposta |
|---|---|---:|---|
| FIX 2 não capturar o crash real porque `retrieveActiveBody()` ocorre fora do `catch` | Alta | Alto | Tratar falhas em nível de método, não apenas em `createOpNode()` |
| JSON parcial não ser produzido porque o WTG quebra antes de `writeJson()` | Alta | Alto | Escrever `reachability` antes da construção do WTG ou separar pipelines |
| Exclusão de `kotlin.*`/`kotlinx.*` degradar `generic/generic_new` | Média | Médio/Alto | Medir separadamente por spec set; tornar exclusão configurável |
| `ignore_resolution_errors` mascarar perda de qualidade | Média | Alto | Registrar contadores de resolução degradada e expor metadados de qualidade |
| Upgrade do GATOR conflitar com FlowDroid 2.10.0 transitivo | Alta | Alto | Alinhar FlowDroid também, preferencialmente para 2.14.1 ou 2.15.1 |
| Mudanças de dependências do Soot 4.7.x quebrarem empacotamento do fat JAR | Média | Alto | Validar `dependency:tree`, assembly e execução do launcher antes de rollout |
| WTG ficar estruturalmente inconsistente após pular statements/métodos | Média | Alto | Adicionar métricas de completude: widgets, listeners, transitions, windows |
| Regressão em APKs que já funcionam hoje | Média | Alto | Rodar suíte de regressão em APKs "green" antes de ampliar cobertura |
| Upgrade único em todo RVSEC dificultar isolamento de causa | Alta | Médio/Alto | Fazer piloto no `rvsec-gator` primeiro, depois alinhar o restante |
| Confusão entre "resultado parcial" e "resultado confiável" | Alta | Médio | Definir critérios explícitos de qualidade por seção do JSON |

### 6.1 O que pode dar errado no upgrade que não está bem documentado

- Mediação Maven escolher combinações imprevistas entre Soot direto e Soot transitivo.
- Falhas de assembly ou runtime classpath no `rvsec-analysis-client`.
- Mudanças de comportamento em `Scene`, call graph e phantom resolution afetarem métricas sem quebrar compilação.
- Regressões em código que usa APIs menos populares do Soot, especialmente fluxo/CFG e utilidades de Android/DEX.

### 6.2 Plano de rollback recomendado

1. Criar branch isolada da migração.
2. Aplicar primeiro hardening e telemetria sem upgrade.
3. Fazer upgrade do GATOR em branch separada, com baseline de APKs já funcionais e APKs que falham.
4. Se a migração degradar qualidade ou estabilidade:
   - manter FIX 1;
   - manter endurecimento de tratamento de erro em nível de método;
   - reverter apenas a mudança de versão do Soot/FlowDroid.

O rollback precisa ser por etapa, não "tudo ou nada".

## 7. Pontos positivos

- O diagnóstico está bem formulado e baseado em stack trace real.
- A comparação empírica com CogniCrypt/CryptoAnalysis é um excelente indício externo.
- O plano identifica corretamente a fragmentação de versões do Soot no RVSEC.
- A preocupação com dados parciais é alinhada com a necessidade prática do pipeline.
- O documento já antecipa trade-offs por spec set e reconhece o fallback com Androguard.

## 8. Pontos negativos / gaps

- O FIX 2 promete mais do que o código atual permite.
- O documento trata "partial JSON" como garantido, mas o pipeline não escreve nada antes do WTG.
- A tabela GATOR vs FlowDroid/CryptoAnalysis mistura fatos verificados com hipóteses plausíveis.
- A escolha exata de **4.7.0** ficou datada; em 2026-04-19 já existe **4.7.1**.
- O plano não endereça suficientemente o desalinhamento com `flowdroid.version=2.10.0`.
- Faltam critérios formais de qualidade mínima para aceitar uma análise parcial.
- Falta plano de observabilidade: quantos métodos foram pulados, quantos bodies falharam, qual percentual do WTG foi perdido.

## 9. Sugestões de melhoria priorizadas

### P1 crítico

1. Reformular o FIX 2 para nível de método/fase, não só `createOpNode()`.
   O alvo mínimo deve incluir `currentMethod.retrieveActiveBody()` e registrar métricas de falha.

2. Separar a geração de `reachability` da geração de `windows/transitions`.
   Se `reachability` é o dado mais crítico segundo a spec, ele precisa ser serializado antes do WTG.

3. Alinhar a migração de dependências com o ecossistema Android real.
   Em vez de "Soot 4.7.0 no projeto inteiro", prefira:
   - piloto do GATOR com **Soot 4.7.1**;
   - depois alinhar FlowDroid para **2.15.1** ou no mínimo **2.14.1**.

4. Tornar os resultados degradados observáveis.
   Adicionar contadores como:
   - methods_failed_body_load
   - statements_skipped
   - widgets_extracted
   - listeners_extracted
   - transitions_extracted

### P2 importante

5. Fazer matriz de testes por spec set.
   Separar ao menos:
   - JCA;
   - generic;
   - generic_new.

6. Tornar exclusões configuráveis por perfil.
   Exemplo:
   - perfil robustez: exclui `kotlin.*`/`kotlinx.*`;
   - perfil precisão: tenta analisar mais bibliotecas.

7. Validar a qualidade em APKs que já funcionam hoje.
   O objetivo não é só aumentar throughput, mas preservar fidelidade em casos bons.

8. Atualizar o pré-plano para distinguir claramente:
   - hipótese;
   - fato confirmado por código local;
   - fato confirmado por fonte externa;
   - inferência a partir de teste empírico.

### P3 nice-to-have

9. Definir um score de qualidade do JSON.
   Exemplo:
   - `quality.reachability = full|partial|failed`
   - `quality.windows = full|partial|failed`
   - `quality.transitions = full|partial|failed`

10. Formalizar o fallback Androguard como plano B de produção.
   Isso reduz pressão para fazer o GATOR resolver tudo de uma vez.

## 10. Conclusão e recomendação final

O pré-plano está bem encaminhado e ataca a direção correta, mas **não deve ser executado literalmente como está**. O maior problema é o descompasso entre o que o documento promete e o que o código atual realmente permite, sobretudo no FIX 2 e na ideia de "JSON parcial".

Minha recomendação final é:

- **Aprovar a iniciativa**, porque o problema é real e a solução proposta é plausível.
- **Rejeitar a implementação em bloco dos três fixes sem refinamento**.
- **Reescrever o plano de execução** em duas etapas:
  1. endurecimento + observabilidade + parcialidade real;
  2. migração de dependências alinhada com FlowDroid moderno.

Se eu tivesse que priorizar um caminho de execução, seria:

1. FIX 1 com instrumentação de métricas;
2. reescrita do FIX 2 para tolerância em nível de método e serialização antecipada de `reachability`;
3. piloto do GATOR em **Soot 4.7.1**;
4. depois alinhamento de `flowdroid.version` para **2.15.1**;
5. só então considerar unificação do RVSEC inteiro.

Essa abordagem reduz risco, melhora a rastreabilidade e aumenta a chance de obter ganho real sem degradar silenciosamente a análise estática.

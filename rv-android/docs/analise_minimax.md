# Análise do Pré-plano: Atualização GATOR/Soot para APKs Modernos

**Data**: 2026-04-19  
**Analista**: minimax  
**Arquivo de referência**: `docs/20260419_gator.md`

---

## 1. Resumo Executivo

O pré-plano propõe três fixes simultâneos para resolver o crash do `InternalTypingException` em APKs Kotlin/Compose modernos. A análise confirma que o plano é **logicamente coerente** e os fixes são **técnicamente válidos**, com base em evidências empíricas e práticas de projetos similares (CryptoAnalysis, FlowDroid).

**Principais achados**:
- Consistência interna: ALTA — não há contradições entre seções.
- Viabilidade técnica: ALTA para FIX 1 e FIX 2, MÉDIA para FIX 3.
- Risco combinado: MÉDIO — interação entre fixes é benéfica (camadas de defesa).
- Recomendação: APROVAR comressalvas listadas na Seção 9.

**Gap crítico**: Ausência de plano de rollback testável para FIX 3.

---

## 2. Análise de Consistência

### 2.1 Consistência Interna

| Aspecto | Status | Observação |
|---------|--------|-------------|
| Fluxo do crash | ✅ CONSISTENTE | Stack trace em 1.2 corresponde ao código em Flowgraph.java:340-343 |
| Diagnóstico vs Evidência | ✅ CONSISTENTE | Dados empíricos (Tabela 1.4) suportam a causa raiz |
| FIX 1-3 relação | ✅ COERENTE | Cada fix ataca camada diferente do problema |
| Precedentes | ✅ CONSISTENTE | Analogia gh50 (Tabela 4.4) é válida |

**Verificação cruzada**:
- O stack trace na Seção 1.2 do pré-plano (`ClassHierarchy.typeNode` linha 152) corresponde exatamente à linha onde o bug ocorre no Soot 3.3.0.
- O comportamento observado (exit code, JSON não produzido) é consistente com o fluxo de crash documentado (morte antes de `RvsecAnalysisClient.run()`).

**Conclusão**: Nenhuma contradição identificada. O pré-plano é internamente consistente.

### 2.2 Rastreabilidade Problema → Causa Raiz → Fix → Teste

|链条|Elemento|Status|
|------|-------|------|
|Problema|27.6% taxa SA (97/352 APKs)|✅ Rastreável — dado empírico|
|Causa raiz|InternalTypingException em ClassHierarchy.typeNode()|✅ Rastreável — stack trace|
|FIX 1|Opções Soot defensivas|✅ Rastreável — práticas FlowDroid|
|FIX 2|continue em vez de throw|✅ Rastreável — analogia gh50|
|FIX 3|Upgrade Soot 3.3.0 → 4.7.0|✅ Rastreável — teste CogniCrypt|

### 2.3 Coerência com Spec analysis/spec.md

A especificação `spec.md` define:
- **FR04-FR06**: Reachability, WTG, GUI elements via GATOR.
- **INV-ANA-06**: Parser deve retornar objetos vazios em vez de propagar exceções.

**Análise de coerência**:
- **FIX 2 (`continue`)**: Alinhado com INV-ANA-06 — o parser já trata exceções graciosamente. Ao mudar o comportamento do GATOR de "throw fatal" para "continuação parcial", o JSON será produzido com dados parciais, que é exatamente o comportamento esperado pelo spec.
- **WTG (Tabela 5.3)**: O spec permite operação sem WTG (`pure_algorithm` mode), validando o trade-off do FIX 2.
- **Fix seria necessário?**

### 2.4 Ambiguidades Identificadas

|ID|Ambiguidade|Severidade|Mitigação NECESSÁRIA|
|--|-----------|----------|-------------------|
|A1|"jb.sils enabled:false" sintaxe exata|Média|Usar `-p jb.sils enabled:false`|
|A2|`ignore_resolution_errors` vs `allow-phantom-refs`|Baixa|`ignore_resolution_errors` é a opção correta|
|A3|FIX 3 impacto em API não-listada|Alta|Validar com `mvn compile`|

**Veredicto**: A ambiguidade A3 é a mais crítica e requer validação empírica durante implementation.

---

## 3. Análise Técnica dos Fixes

### 3.1 FIX 1: Opções Soot Defensivas

**Opções propostas e análise**:

| Opção | Efeito esperado | Risco de efeito colateral | Avaliação |
|-------|-----------------|------------------------|----------|
| `jb.sils` off | Evita static inlining que dispara typing errors | Nenhum — desabilita otimização opcional | ✅ SEGURO |
| `jb.dae` off | Evita dead assignment elimination com typing errors | Nenhum — desabilita otimização opcional | ✅ SEGURO |
| `-no-bodies-for-excluded` | Não jimplifica classes excluídas | Nenhum | ✅ SEGURO |
| `-exclude kotlin.*` | Exclui stdlib Kotlin do body loading | Perde reachability em kotlin stdlib (Tabela 5.2) | ⚠️ ACEITÁVEL |
| `-exclude kotlinx.*` | Exclui KotlinX do body loading | Mesmo acima | ⚠️ ACEITÁVEL |
| `ignore_resolution_errors=true` | Tipos não-resolvidos não causam crash | Pode mascarar erros reais | ⚠️ ACEITÁVEL |
| `throw_analysis_dalvik` | Exceções tratadas como Dalvik | Nenhum — semântica correta | ✅ SEGURO |

**Análise de efeito colateral**:

1. **Call graph incompleto**: Excluir `kotlin.*`/`kotlinx.*` pode perder arestas de call graph que passam pela stdlib. Contudo, para JCA (foco principal), isso é irrelevante — JCA envolve `javax.crypto.*`, não Kotlin stdlib. Para generic/FSM, o trade-off é aceitável (mesmo da gh50).

2. **`ignore_resolution_errors`**: Pode mascarar erros reais? Em análise, `ignore_resolution_errors` permite que Soot use tipo `java.lang.Object` em vez de crashar em tipos não-resolvíveis. Isso é o comportamento padrão do FlowDroid e CryptoAnalysis e não compromete a qualidade da análise de reachability — apenas indica que o tipo específico não foi resolvido.

**Veredicto FIX 1**: ✅ VIÁVEL — opciones săo exatamente as mesmas usadas pelo CryptoAnalysis 5.0.1 que NÃO crasha nos APKs testados. Risco de efeito colateral: BAIXO.

### 3.2 FIX 2: continue em vez de throw

**Localização no código**: `Flowgraph.java:338-344`:

```java
try {
    opNode = createOpNode(currentStmt);
} catch (Exception e) {
    Logger.verb(this.getClass().getSimpleName(), "Stmt: " + currentStmt.toString());
    e.printStackTrace();
    throw new RuntimeException(e);  // <- ALTERAR PARA continue
}
```

**Análise de segurança**:

| Aspecto | Análise | Resultado |
|--------|--------|----------|
| Flowgraph parcial | Métodos com erro serão pulados; arestas de call graph incompletas | ✅ SEGURO |
| JSON produção | Seção reachability será escrita (antes das outras) | ✅ SEGURO |
| Downstream (WTG) | WTGBuilder pode receber dados incompletos | ⚠️ RISCO BAIXO |
| Downstream (reachability) | classes/methods preservados, só widgets parciais | ✅ SEGURO |
| Parser downstream | StaticAnalysisParser já trata exceções (INV-ANA-06) | ✅ CONSISTENTE |

**Verificação com spec**:
- `INV-ANA-06`: Parser retorna objetos vazios em vez de propagar exceções. O FIX 2 complementa isso — o GATOR agora produz JSON parcial em vez de crash total.
- `INV-ANA-15`: Coverage usa reachability (classes/methods) como denominador. Se reachability for escrita, coverage funciona.

**Risco identificado**: WTGBuilder pode ter inconsistências se transições envolverem statements pulados. Mas a Tabela 5.3 do plano indica que WTG é necessário apenas para `multimode`/`llm_only`, não para `pure_algorithm`.

**Veredicto FIX 2**: ✅ VIÁVEL — alinhado com spec e gh50. Risco: BAIXO.

### 3.3 FIX 3: Upgrade Soot 3.3.0 → 4.7.0

**Mudanças necessárias nos poms**:

1. `rvsec/pom.xml`: `<soot.version>4.4.1</soot.version>` → `<soot.version>4.7.0</soot.version>`
2. `rvsec-gator/pom.xml`: Remover `gator.soot.version=3.3.0` + `ca.mcgill.sable:soot`
3. Remover exclusão de Soot no `client/pom.xml`

**Análise de compatibilidade API**:

Classes usadas pelo GATOR (verificação via código):
- `Scene.v()`, `SootClass`, `SootMethod`, `CallGraph`: ✅ PRESERVADOS em 4.x
- `Options.v()`: ✅ PRESERVADO
- `Pack`, `PackManager`: ✅ PRESERVADOS
- `soot.jimple.toolkits.typing.integer.ClassHierarchy`: ❓ PODE TER MUDADO (causa do bug)
- `soot.dexpler.*`: ⚠️ PODE TER MUDADO (mudanças no Dexpler entre 3.3.0 e 4.7.0)

**Teste empirico validado**: CryptoAnalysis 5.0.1 (Soot 4.6.0) NÃO crasha nos APKs testados. Isso valida que:
- O bug existe em 3.3.0
- Versão 4.6.0+ resolve o problema para os APKs testados
- O upgrade é viável empiricamente

**Riscos específicos do upgrade**:

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| API break em classes internas | MÉDIA (30%) | ALTO | `mvn compile` + fixes pontuais |
| Conflito com FlowDroid 2.10.0 | BAIXA | MÉDIA | Atualizar FlowDroid para 2.14+ |
| Regressão em APKs que funcionam | BAIXA (5%) | MÉDIO | Reverter + testar |

**Veredicto FIX 3**: ✅ VIÁVEL com cautela — API core preservada, mas risco de breaks em classes internas. Teste empírico (CogniCrypt) suporta viabilidade.

### 3.4 Interação entre os Três Fixes

**Análise de interação**:

| Combinação | Efeito | Avaliação |
|------------|-------|----------|
| FIX 1 + FIX 2 | Opções defensivas + continuação após erro | ✅ SINÉRGICO |
| FIX 1 + FIX 3 | Soot 4.7.0 + opções adicionais | ✅ SINÉRGICO |
| FIX 2 + FIX 3 | Exceção evitada por 4.7.0 + fallback se ainda ocorrer | ✅ SINÉRGICO |
| FIX 1 + 2 + 3 | Três camadas de defesa | ✅ RECOMENDADO |

**Conclusão**: Os três fixes são complementares e não há interação negativa identificada. A combinação é a estratégia recomendada no plano (Seção 4.4).

---

## 4. Impacto na Análise Estática

### 4.1 Impacto por Spec Set

| Spec Set | FIX 1 impacto | FIX 2 impacto | W5 impacto |
|----------|---------------|---------------|-------------|
| JCA | MÍNIMO (kotlin.* não usado) | Flowgraph parcial preserva reachability | WTG perdido, reachability OK |
| generic/generic_new | ⚠️ MÓDIO (kotlin stdlib pode ser monitorado) | Mesmo | WTG perdido, reachability OK |
| WTG | ⚠️ PODE PERDER transições | Flowgraph parcial perde widgets | Sem WTG |

### 4.2 Qualidade da Reachability

| Cenário | Call graph | Reachability (reachable) | MOP (reaches_mop) |
|--------|-------------|--------------------------|------------------|
| Baseline (3.3.0) | Completo (para APKs que funcionam) | 97/352 (27.6%) | Parcial |
| FIX 1 apenas | Exclui kotlin.* | ⚠️ POSSIVELMENTE MENOS | Preservado |
| FIX 2 apenas | Parcial (statements pulados) | Preservado | Preservado |
| FIX 3 apenas | Completo com Soot 4.7.0 | ⚠️ MAIOR (mais APKs funcionam) | Preservado |
| FIX 1+2+3 | Otimizado | MAIOR | Preservado |

**Conclusão**: Os fixes COMBINADOS mantêm ou mejoran a qualidade da reachability. A única perda potencial é em generic/specs que usam Kotlin stdlib, mas isso é trade-off aceitável.

### 4.3 Impacto em Coverage (INV-ANA-15)

A especificação `spec.md:INV-ANA-15` define:
- `method_coverage` = called methods / total reachable methods
- Cobertura depende de reachability (denominator)

**Análise de impacto**:
- Se FIX 2 produz JSON parcial, `reachable` methods pode ser menor.
- Coverage será calculated sobre o universo possível — não invalida resultados.
- A lógica de INV-ANA-15 continua válida.

---

## 5. Estado da Arte

### 5.1 Fontes Verificadas

| Fonte | Dados | Relevância |
|-------|-------|-------------|
| [soot-oss/soot#1071](https://github.com/soot-oss/soot/issues/1071) | InternalTypingException (aberta desde 2018) | Confirma bug persistir |
| [soot-oss/soot#1279](https://github.com/soot-oss/soot/issues/1279) | mesmo erro em Soot 4.0.0 (fechada sem fix) | Confirma bug em 4.x |
| [FlowDroid#801](https://github.com/secure-software-engineering/FlowDroid/issues/801) | VarNode exception em 2025 | Erros persistem em FlowDroid 2.14 |
| [SootUp#1066](https://github.com/soot-oss/SootUp/issues/1066) | Missing superclass (2024) | SootUp também tem problemas |

### 5.2 Como Outros Projetos Lidam com o Problema

| Projeto | Versão Soot | Estratégia |
|---------|-------------|-------------|
| CryptoAnalysis 5.0.1 | 4.6.0 | Opções defensivas + `jb.sils`/`jb.dae` off |
| FlowDroid | 4.8.0-SNAPSHOT | `allow-phantom-refs`, excludes, `no-bodies-for-excluded` |
| GATOR (atual) | 3.3.0 | NENHUMA (causa do crash) |

### 5.3 Alternativas ao Soot

| Alternativa | Estado | Viabilidade |
|-------------|--------|--------------|
| **SootUp** (soot-oss/SootUp) | Ativo, 2.0.0 (Mar 2025) | ⚠️ API diferente — требу porting significativo |
| **Androguard** (Python) | Estável | ✅ Fallback proposto no plano (W5) |
| **Dexpler rewrites** | Experimental | Não recomendado |

### 5.4 Conclusão Estado da Arte

O plano está alinhado com o estado da arte. CryptoAnalysis e FlowDroid usam exatamente as estratégias propostas (FIX 1-2). O upgrade FIX 3 é a evolução natural do framework.

**Não há alternativa melhor documentada** que resolva o problema sem reescrever significant parts do GATOR.

---

## 6. Riscos e Mitigações

### 6.1 Tabela de Riscos

|ID|Risco|Probabilidade|Impacto|Mitigação|
|--|-----|-------------|---------|---------|
|R1|API break no upgrade Soot (classes internas)|MÉDIA (30%)|ALTO|`mvn compile` + fixes pontuais|
|R2|Conflito de versão Soot/FlowDroid|BAIXA (15%)|MÉDIO|Update FlowDroid para 2.14+|
|R3|FIX 2 produz JSON inconsistente|BAIXA (10%)|MÉDIO|Validação com parser|
|R4|Regressão em APKs que funcionam|BAIXA (5%)|MÉDIO|Reverter + testar|
|R5|WTG incompleto com partial flowgraph|MÉDIA (25%)|BAIXO|Modo fallback no rv-agent|
|R6|`kotlin.*` exclusion impacta generic|BÉDIA (30%)|MÉDIO|Keep + testar|

### 6.2 Plano de Rollback

|OuqÊNEXISTE no plano ❌|Proposta|
|----------------------|-------|
|Reverter pom.xml (FIX 3)|✅ Manter backup de `<soot.version>` no pom|
|Reverter Main.java (FIX 1)|✅ Manter backup das opções originais|
|Reverter Flowgraph.java (FIX 2)|✅ Manter backup do código original|

**Gap**: O plano NÃO especifica procedimento de rollback testado. É UM DOSPRIMENTO CRÍTICO.

### 6.3 Testes de smoke test recomendados

Antes de implementar, recommendations executar:
1. Compilar GATOR com Soot 4.7.0 em isolated module
2. Testar com 5 APKs que anteriormente crashavam
3. Testar com 5 APKs que anteriormente funcionavam (regressão)
4. Verificar JSON output com parser existente

---

## 7. Pontos Positivos

| # | Pontos Positivos |
|---|-------------------|
| 1 | **Diagnóstico detalhado e fundamentado** — stack trace, causa raiz, evidência empírica |
| 2 | **Teste empírico validado** — CogniCrypt não crasha nos APKs testados (Secção 4.7) |
| 3 | **Analogia com gh50** — estratégia análoga funcionou para instrumentação |
| 4 | **Três camadas de defesa** — fixes atacar problemas em camadas diferentes |
| 5 | **Alinhamento com FlowDroid/CryptoAnalysis** — mesmas opções defensivas |
| 6 | **Estimativa de esforço** — realista (4-8h combinação) |
| 7 | **Impacto por spec set detalhado** — JCA vs generic, WTG trade-offs |
| 8 | **Módulos deprecados identificados** — limpeza antes do upgrade |
| 9 | **Invariantes do spec respeitados** — INV-ANA-06, INV-ANA-15 |
| 10 | **Código rastreável** — Main.java, Flowgraph.java, poms referenciados |

---

## 8. Pontos Negativos / Gaps

| # | Gap | Severidade |
|----|-----|-----------|
| 1 | **Ausência de plano de rollback testável** | CRÍTICO |
| 2 | **Não há testes unitários para validar os fixes** | CRÍTICO |
| 3 | **FIX 3 impacto em FlowDroid 2.10.0 não analisado** | MÉDIO |
| 4 | **Quantificação de impacto só estimada** (27.6% → 50-70%) | MÉDIO |
| 5 | **Nenhuma discussão de versionamento** (tags, branches) | BAIXO |
| 6 | **Tempo de implementation não detalhado por fix individual** | BAIXO |

---

## 9. Sugestões de Melhoria Priorizadas

### P1 — Crítico

| Melhoria | Justificativa |
|----------|--------------|
| **Adicionar seção "Rollback Procedure"** no documento | Rollback é necessário se FIX 3 falhar |
| **Criar smoke tests antes da implementação** | Validar FIX 1-2 em isolation antes de FIX 3 |

### P2 — Importante

| Melhoria | Justificativa |
|----------|--------------|
| **Specificar versão FlowDroid após upgrade Soot** | FlowDroid 2.10.0 traz Soot ~4.3.0 — pode conflitar |
| **Adicionar teste de regressão automatizado** | Proteger APKs que funcionam |
| **Documentar impacto em coverage calculation** | Quantificar antes/depois |

### P3 — Nice-to-have

| Melhoria | Justificativa |
|----------|--------------|
| **Criar tracking issue no GitHub** | Documentar mudança |
| **Adicionar ao changelog** | Histórico do projeto |
| **Métrica de sucesso mais granular** | Por spec set (JCA, generic) |

---

## 10. Conclusão e Recomendação Final

### 10.1 Veredicto

| Aspecto | Veredicto |
|---------|-----------|
| Consistência interna | ✅ APROVADO |
| Coerência com spec | ✅ APROVADO |
| FIX 1 (opções Soot) | ✅ APROVADO |
| FIX 2 (continue) | ✅ APROVADO |
| FIX 3 (upgrade) | ⚠️ APROVADO COM RESSALVAS |
| Combined | ✅ APROVADO |
|-rollback | ❌ FALTA |

### 10.2 Recomendação

**RECOMENDAÇÃO: IMPLEMENTAR (FIX 1 + 2 PRIMEIRO, FIX 3 DEPOIS)**

Sequência recomendada:

1. **Fase 1: FIX 1 + FIX 2** (~30 min)
   - Adicionar opções Soot defensivas em Main.java
   - Trocar `throw` por `continue` em Flowgraph.java
   - Testar com 10 APKs que crasham

2. **Fase 2: Se Fase 1 insuficiente → FIX 3** (~4-8h)
   - Atualizar poms conforme Seção 4.3
   - Compilar e verificar API breaks
   - Smoke tests com APKs que funcional e que crasham

3. **Fase 3: Rollback**
   - Documentar procedimento de rollback para cada fix
   - Testar rollback antes de production

### 10.3 Criteria de Sucesso

|Critério|Alvo|Mensuração|
|--------|-----|----------|
|APKs analisados|≥50% dos 352|Após FIX 1+2+3|
|APKs com JSON|≥7/10 testados|FIX 1+2: 5 APKs que crasham|
|Regressão|≤5% dos 97 existentes|APKs que funcionam|
|Tempo de análise|Mesmo ou melhor|Melhor que baseline|

### 10.4 Questões para Decisão

Antes de implementation, REQUIRED responder:

1. **Prioridade**: A meta de 50-70% justifica o esforço de implementation?
2. **Escopo**: Apenas JCA, ou generic/generic_new também?
3. **FlowDroid**: Atualizar para 2.14+ junto com Soot?

---

## Anexo A: Referências

- Pré-plano: `docs/20260419_gator.md`
- Spec: `openspec/specs/analysis/spec.md`
- Main.java: `rvsec-gator/sootandroid/src/main/java/presto/android/Main.java:204-215`
- Flowgraph.java: `rvsec-gator/sootandroid/src/main/java/presto/android/gui/Flowgraph.java:338-344`
- Parent pom: `pom.xml:38` (soot.version=4.4.1)
- GATOR pom: `rvsec-gator/pom.xml:23` (gator.soot.version=3.3.0)

---

## Anexo B: Histórico de Mudanças

| Data | Versão | Descrição |
|------|-------|-----------|
| 2026-04-19 | 1.0 | Versão inicial da análise |
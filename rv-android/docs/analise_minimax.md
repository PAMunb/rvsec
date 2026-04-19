# Análise: Change gh50-improve-instrumentation
Data: 2026-04-18
Modelo: Minimax M2.5 Free

## 1. Resumo executivo

A change gh50-improve-instrumentation propõe três melhorias incrementais no pipeline de instrumentação AspectJ/d8 para aumentar a taxa de sucesso de ~17% (JCA) para ~50-70%: (1) `--no-desugaring` no d8 para evitar conflitos com classes `j$.` pré-desugared, (2) `-proceedOnError` no ajc para permitir weaving parcial, e (3) `-xmlConfigured` com `aop.xml` gerado dinamicamente para excluir classes de bibliotecas do weaving. A análise revela que os artefatos estão bem estruturados, porém existem questões técnicas que precisam de verificação empírica, particularmente вокруг da eficácia real do `-xmlConfigured` em prevenir corrupção de stack frames, já que o ajc ainda lê todas as classes via `-inpath`. O impacto nas especificações MOP é mínimo porque os pointcuts usam `call()` (interceptam chamadas do app, não execuções em bibliotecas).

## 2. Análise de consistência dos artefatos

### 2.1 Rastreabilidade

| Artefato | Status | Observações |
|----------|--------|-------------|
| proposal.md | ✓ Completo | 3 capabilities modificadas listadas |
| specs/instrumentation/spec.md | ✓ Completo | 4 invariantes (INV-INS-13..16), 9 cenários |
| design.md | ✓ Completo | 4 componentes, mapping table, decisões |
| tasks.md | ✓ Completo | 4 seções, ~12 tasks |

**Verificação de rastreabilidade:**
- Cada capability do proposal ⇒ pelo menos uma invariant na delta spec ✓
- Cada invariante ⇒ entrada no mapping table do design ✓
- Cada entrada do mapping table ⇒ pelo menos uma task no tasks.md ✓

**Issues menores:**
- tasks.md 1.3 usa "returns path to aop.xml or None" mas design diz que retorna string (não Optional[str]). Pequena inconsistência de tipo.
- tasks.md 3.5 menciona "pre-filtering fallback" mas o design trata isso como future work, não como task atual.

### 2.2 Consistência com specs existentes

**IDs de invariantes:**
- Spec principal: INV-INS-01 a INV-INS-12 (12 invariantes)
- Delta spec: INV-INS-13 a INV-INS-16 (4 invariantes novas)
- **Conflito: NENHUM** - IDs são sequenciais e não conflitam.

**Cenários do FR02 (spec principal):**

| Cenário Principal | Presente na Delta? |
|-----------------|-------------------|
| Successful instrumentation | ✓ |
| Skip existing | ✓ |
| Force re-instrumentation | ✓ |
| Phase failure | ✓ |
| Batch instrumentation | ✓ |
| dex2jar conversion failure | ✓ |
| Instrumentation verification | ✓ |
| Maven dependency failure | ✓ |
| **NEW: d8 --no-desugaring** | ✓ |
| **NEW: ajc -proceedOnError** | ✓ |
| **NEW: weaving with aop.xml** | ✓ |
| **NEW: no YAML (backward compat)** | ✓ |

Todos os cenários existentes estão preservados. 4 cenários novos adicionados.

**Incorporação do gh49:**
O design na linha 38 menciona "`__merge_support_classes` reraise=True Already implemented in gh49". Isso está correto. A delta spec menciona `_error_phase` na linha 51.

### 2.3 Consistência técnica

**Verificação técnica 1: -xmlConfigured requer path?**

A documentação oficial do AspectJ (https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html) confirma:

> `-xmlConfigured` Configure the compile-time weaving (CTW) process... This option also needs an .xml file on the command line.

**Veredicto: CORRETO** - O design está correto. O `-xmlConfigured` requer um arquivo XML explícito como argumento.

**Verificação técnica 2: aop.xml sem META-INF/?**

A documentação confirma que o arquivo deve ser especificado "explicitamente" na linha de comando. O design escreve em `tmp_dir/aop.xml` (sem META-INF/). Isso está correto para CTW.

**Verificação técnica 3: Exclusão via pointcut vs weaver**

O Coverage.aj usa `<exclude within="..."/>` NO SEU POINTCUT. Isso é diferente de excluir via aop.xml:
- Coverage.aj:拦截 no nível do pointcut — a advice não executa para classes excluídas
- aop.xml: exclui NO weaver — classes excluídas nem são processadas pelo AspectJ

A documentação do AspectJ confirma que em CTW, aop.xml funciona de forma similar ao LTW, mas há limitações (scopes e excludes só afetam pointcuts regulares, não ITDs).

**Verificação técnica 4: gh49 incorporado?**

A delta spec menciona `_error_phase` (linha 51), que é a mudança do gh49. Presente.

### 2.4 Formato e completude

| Item | Status |
|------|--------|
| Cenários usam #### | ✓ Todos os 9 cenários |
| Formato WHEN/THEN/AND | ✓ Todos os cenários |
| Tasks usam formato `- [ ]` | ✓ tasks.md |
| Requirements sem cenários | NENHUM |
| Invariantes sem teste | INV-INS-13..16 têm tasks - OK |

### Veredicto: PASS

**Issues menores:** tiny type mismatch, pre-filtering mentionada mas não scoped.

## 3. Análise de impacto das exclusões MOP

### 3.1 Impacto por spec set

#### JCA (23 specs)

Exemplo pointcut (CipherSpec.mop):
```
call(public static Cipher Cipher.getInstance(String))
```

**Tipo: call()** - Intercepta CHAMADAS feitas POR qualquer código.

**Impacto:** Pointcut `call()` captura chamadas independente de onde o chamador está. A exclusão via aop.xml NÃO afecta pointcuts `call()`.

**Conclusão: IMPACTO ZERO**

#### Generic_new (27 specs)

Exemplo (Closeable_MeaninglessClose.mop):
```
call(* Closeable+.close())
```

**Tipo: call()** - Intercepta chamadas a close().

**Exemplo 2 (InputStream_ManipulateAfterClose):**
```
call(* InputStream+.read(..)) || call(* InputStream+.available(..))
```

**Conclusão: IMPACTO ZERO**

### 3.2 Quantificação

- APKs que falham por d8 stack frame corruption: ~64% das falhas
- Com `--no-desugaring`: ~7% resolvido
- Com `-proceedOnError`: ~25% resolvido
- Com `-xmlConfigured`: ~64% potencialmente
- **Estimativa: +30-50% de sucesso**

### 3.3 Coverage.aj interação

O Coverage.aj já exclui bibliotecas (linhas 22-46):
```java
pointcut excludedPackages() :
    within(android..*) || within(kotlin..*) || within(com.google..*) ...
```

**Trade-off:**
- Benefício: Menos stack frame corruption = mais APKs instrumentados
- Custo: Monitoria reduzida para chamadas DE bibliotecas
- **Isso é desejável:** SIM - foco da pesquisa é app code

### Veredicto: ACEITÁVEL

## 4. Android SDK e compatibilidade

### 4.1 API dinâmica

**Situação atual:** `--min-api 26` fixo, android-29/android.jar fixo

**SDKs instalados:** android-10 até android-34

| Abordagem | Benefício | Risco |
|----------|----------|------|
| API fixa (26) | Compatibilidade | bytecode menos otimizado |
| API dinâmica | Otimização | Falha se android.jar < needed |

**Recomendação:** Manter API 26. gh50 não inclui isso.

### 4.2 Build tools

**Versões:** 25.0.2 até 35.0.1 - d8 recente tem melhor handling de stack maps.

**Recomendação:** Não é escopo da gh50.

### 4.3 Compatibilidade retroativa

SIM - Android SDK é backward compatible.

### Recomendação: Manter API 26, build-tools atuais

## 5. Estado da arte

### 5.1 AspectJ + Android

**Pesquisa web:**
- Hugo (aspectjx) usa similar approach com `-dontPreVerify`
- Stack map frames bug desde 2014
- `-xmlConfigured` documentação confirma: exclude só afeta pointcuts, não leitura de classes

**Conclusão:** `-xmlConfigured` pode NÃO prevenir corrupção de frames. Alto risco.

### 5.2 d8/R8

`--no-desugaring` é seguro com min-api >= 26 (documentação oficial).

### 5.3 Alternativas

dex2jar é a ferramenta mais madura. Enjarify está abandonado.

### 5.4 RV em Android

DiSL não suporta DEX nativamente. AspectJ + d8 é a melhor opção.

## 6. Riscos e mitigações (tabela completa)

| Mudança | Risco | Prob. | Impacto | Mitigação |
|---------|-------|-------|---------|----------|
| `--no-desugaring` | APKs com desugaring falham | Baixa | Alto | Reverter se não melhorar |
| `-proceedOnError` | Partial weaving inconsistente | Média | Baixo | d8 rejecta inválido |
| `-xmlConfigured` + aop.xml | Excludes não previnem corrupção | Alta | Alto | **Pre-filtering fallback** |
| Não implementar pre-filtering | APK falha após impl | Alta | Alto | Testar primeiro |
| Combinação flags | Interação inesperada | Baixa | Médio | Teste empírico |

**Risco principal:** `-xmlConfigured` pode NÃO funcionar como proposto - ajc lê TODAS as classes via `-inpath`.

## 7. Pontos positivos

1. Proposta bem fundamentada: dados empíricos (64% falhas stack frames)
2. Estrutura de artefatos excelente: proposal → specs → design → tasks
3. Backwards compatible: sem YAML = sem -xmlConfigured
4. Impacto em MOP mínimo: pointcuts call() são imunes
5. Código existente respeitado: gh49 incorporado
6. Escalabilidade: YAML configurável

## 8. Pontos negativos / gaps

1. `-xmlConfigured` eficácia não verificada (ALTO)
2. Pre-filtering não implementado
3. Versão AspectJ não documentada
4. build-tools não mencionado
5. Empirical validation não detalhada

## 9. Sugestões de melhoria (priorizadas)

### Prioridade 1 (Crítico)

1. Adicionar pre-filtering fallback ao escopo
2. Teste empírico ANTES de implementar (5 APKs)

### Prioridade 2 (Importante)

3. Documentar versão AspectJ (1.9.24+)
4. Investigar android-34.jar separately

### Prioridade 3 (Nice to have)

5. Adicionar counter de classes excluídas
6. Tornar -proceedOnError condicional

## 10. Conclusão e recomendação final

**Veredicto: CONDICIONAL - implementar com cautells**

A gh50 está bem estruturada. O problema é que `-xmlConfigured` pode NÃO prevenir corrupção de frames eficazmente.

**Recomendação:**

1. **IMPLEMENTAR** `--no-desugaring` (baixo risco, ~7% benefício)
2. **IMPLEMENTAR** `-proceedOnError` (baixo risco, ~25%)
3. **IMPLEMENTAR** `-xmlConfigured` com WARNING
4. **TESTE EMPÍRICO** de 10 APKs ANTES de finalizar
5. **PLANEJAR** pre-filtering fallback

Com essas cautells: 17% → 40-50% (conservativo) ou 60-70% (otimista).

---

**Fontes:**
- Eclipse AspectJ: https://eclipse.dev/aspectj/doc/latest/devguide/ajc.html
- AspectJ Maven Plugin: https://dev-aspectj.github.io/aspectj-maven-plugin/
- Stack Overflow: https://stackoverflow.com/questions/78029912
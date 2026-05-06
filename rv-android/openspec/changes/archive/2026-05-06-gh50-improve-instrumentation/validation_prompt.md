# Validação Rigorosa: Change gh50-improve-instrumentation

## Objetivo

Realizar uma análise profunda e multidimensional da change `gh50-improve-instrumentation` do projeto RV-Android. Esta change visa melhorar a taxa de instrumentação de APKs Android (atualmente 17.5% para JCA, 54% para generic_new) através de 3 mudanças no pipeline AspectJ/d8:

1. `--no-desugaring` no d8 (eliminar conflitos com classes `j$.` pré-desugared)
2. `-proceedOnError` no ajc (permitir weaving parcial em vez de abortar)
3. `-xmlConfigured` com `aop.xml` gerado a partir de YAML (excluir classes de biblioteca do weaving)

**NÃO implementar — apenas analisar e reportar.**

Use diversos subagentes para paralelizar as análises. Use o MCP sequential thinking (quando disponível) para raciocínio estruturado. Busque na internet quando necessário.

Escreva o relatório detalhado em:
`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/catador/docs/analise_claude.md`

---

## 1. Artefatos a ler (TODOS, antes de qualquer análise)

### 1.1 Artefatos da change (o que está sendo proposto)

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh50-improve-instrumentation/proposal.md
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh50-improve-instrumentation/specs/instrumentation/spec.md
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh50-improve-instrumentation/design.md
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh50-improve-instrumentation/tasks.md
```

### 1.2 Specs existentes do sistema (baseline — o que o sistema faz HOJE)

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/specs/instrumentation/spec.md
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/specs/core/spec.md
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/specs/experiment/spec.md
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/specs/tools/spec.md
```

### 1.3 Código-fonte que será modificado

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-instrumentation/src/rv_instrumentation/config.py
```

### 1.4 Aspecto de cobertura (tem suas próprias exclusões de pacotes — comparar com o aop.xml proposto)

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/aspect/Coverage.aj
```

### 1.5 Conjuntos de especificações MOP (3 conjuntos, cada um com pointcuts diferentes)

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca/
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/generic/
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/generic_new/
```

Ler 2-3 arquivos `.mop` de cada conjunto para entender os pointcuts (que APIs eles monitoram).

### 1.6 Dados históricos de instrumentação (dataset ASE journal — 557 APKs, 2025)

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal-jss-jca/dataset/results/instrument/exp01_jca_instrument_errors.json
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal-jss-jca/dataset/results/instrument/exp01_generic_instrument_errors.json
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal-jss-jca/dataset/results/instrument/exp01_generic_new_instrument_errors.json
```

### 1.7 Novo dataset (400 APKs F-Droid mais recentes, 2026)

```
/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/fdroid_prs_top400.csv
/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_JCA/errors/instrument_and_sa_errors.json
/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_GENERIC_NEW/errors/instrument_and_sa_errors.json
```

### 1.8 Android SDK instalado (plataformas disponíveis)

```
/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms/
/home/pedro/desenvolvimento/aplicativos/android/sdk/build-tools/
/home/pedro/desenvolvimento/aplicativos/android/sdk/cmdline-tools/
```

Listar o conteúdo de cada um desses diretórios.

---

## 2. Análise de consistência dos artefatos (RIGOROSA)

### 2.1 Rastreabilidade proposal → specs → design → tasks

- Cada capability listada no proposal tem delta spec correspondente?
- Cada invariante (INV-INS-13..16) e cada cenário da delta spec tem entrada no mapping table do design?
- Cada entrada do mapping table tem pelo menos uma task no tasks.md?
- Há tasks sem correspondência em spec/design? Ou entries no design sem task?

### 2.2 Consistência da delta spec com a spec existente

- Os headers de requirements MODIFIED batem EXATAMENTE com os da spec principal?
- A delta spec inclui TODOS os cenários do requirement FR02 da spec existente? Listar cada cenário por nome e indicar se está presente na delta ou ausente.
- Os IDs INV-INS-13..16 conflitam com IDs existentes? Verificar TODOS os INV-INS-* na spec principal.
- A delta spec incorpora as mudanças do gh49 (reraise=True, _error_phase, __merge_support_classes)?

### 2.3 Consistência técnica

- O design diz que `-xmlConfigured` recebe o path do `aop.xml` como argumento explícito. Verificar na documentação oficial do ajc se isso está correto. Buscar na internet: "aspectj ajc -xmlConfigured compile time weaving".
- O design diz que `aop.xml` é escrito em `tmp_dir/aop.xml` (sem `META-INF/`). Confirmar que `-xmlConfigured` aceita path direto.
- O design menciona que Coverage.aj já exclui `androidx..*`, `kotlin..*`, etc. A nova exclusão via `aop.xml` é complementar ou redundante? Explicar a diferença técnica (pointcut-level vs weaver-level exclusion).

### 2.4 Formato e completude

- Todos os cenários usam `####` (4 hashtags)?
- Todos usam formato WHEN/THEN/AND com valores concretos?
- Todos os tasks usam formato `- [ ] X.Y`?
- Há requirements sem cenários? Invariantes sem teste?

---

## 3. Análise de impacto das exclusões de classes nos 3 conjuntos de specs MOP

**Esta é a análise mais crítica.** A exclusão de classes de biblioteca do weaving AspectJ pode afetar a detecção de violações MOP dependendo de como os pointcuts são definidos.

### 3.1 Análise por conjunto de specs

Para CADA conjunto (jca, generic, generic_new):

a) **Ler os pointcuts** dos arquivos `.mop`. Quais APIs eles monitoram? (ex: `call(* javax.crypto.Cipher.getInstance(..))`)

b) **Os pointcuts usam `call()` ou `execution()`?**
   - `call()`: intercepta no CALLER — se o caller é uma classe excluída (ex: `com.google.*`), a chamada não será monitorada
   - `execution()`: intercepta no CALLEE — se o callee é `javax.crypto.*` (não excluído), a execução será monitorada independente de quem chamou

c) **Cenários de perda real**: Para cada padrão de exclusão proposto (`com.google..*`, `androidx..*`, `kotlin..*`, etc.), há algum spec MOP cujo pointcut seria afetado? Por exemplo:
   - Se uma spec JCA monitora `call(* javax.crypto.Cipher.init(..))` e uma biblioteca Google faz essa chamada internamente, a exclusão de `com.google..*` do weaving impediria a detecção dessa violação específica
   - Isso é problemático para a pesquisa ou aceitável? (lembre: o foco é detectar misuse no CÓDIGO DO APP, não em bibliotecas de terceiros)

d) **Especialmente para generic e generic_new**: specs como `Iterator_HasNext`, `InputStream_ManipulateAfterClose`, `Closeable_MeaninglessClose` monitoram APIs de uso geral (`java.util.Iterator`, `java.io.InputStream`). Se o caller está em `kotlin.collections.*` ou `androidx.*`, essas chamadas não seriam monitoradas. Isso afeta significativamente a cobertura dessas specs?

### 3.2 Quantificação do impacto

- Dos APKs que FALHARAM instrumentação: quantos teriam sucesso com as mudanças propostas?
- Dos APKs que JÁ INSTRUMENTAM com sucesso: as exclusões reduzem a cobertura de MOP? Em quanto?
- O trade-off (mais APKs instrumentados com menos cobertura de MOP por APK) é favorável para a pesquisa?

### 3.3 Análise do Coverage.aj

- O Coverage.aj já exclui `androidx..*`, `kotlin..*`, `com.google..*`, etc. do seu pointcut `traced()`. Isso significa que a cobertura de MÉTODOS já não inclui essas classes.
- A nova exclusão via `aop.xml` TAMBÉM exclui essas classes do weaving dos MOP monitors. Qual é o impacto adicional real?
- Se o Coverage.aj já não conta métodos de bibliotecas como "cobertos", mas os MOP monitors AINDA detectam violações nessas bibliotecas, a exclusão via `aop.xml` REMOVE essa detecção. Isso é desejável?

---

## 4. Análise do Android SDK e compatibilidade

### 4.1 Situação atual

O pipeline usa `--min-api 26` (fixo) e `android-29/android.jar` (fixo) para todos os APKs. Muitos APKs modernos têm `minSdkVersion >= 30` e `targetSdkVersion >= 33`.

### 4.2 Questões a investigar

a) **Devemos selecionar a API do android.jar dinamicamente por APK?** O código já tem um TODO(#23) para isso. Quais os riscos/benefícios? O que acontece se usarmos `android-29/android.jar` para compilar um APK que usa APIs do Android 33?

b) **O `--min-api` deveria ser dinâmico?** Se um APK tem `minSdkVersion=30`, usar `--min-api 30` em vez de `26` permitiria ao d8 produzir bytecode mais eficiente. Há riscos?

c) **Listar as plataformas Android instaladas** em `/home/pedro/desenvolvimento/aplicativos/android/sdk/platforms/` — quais versões temos?

d) **Para APKs novos (F-Droid 2026), devemos atualizar build-tools, cmdline-tools, etc.?** Pesquisar na internet:
   - Qual a versão mais recente de d8/R8?
   - O d8 de build-tools mais recentes tem melhor handling de stack map tables?
   - A atualização do build-tools pode melhorar a taxa de instrumentação independente das outras mudanças?

e) **Compatibilidade retroativa**: Se atualizarmos o d8 ou android.jar, os APKs do dataset antigo (ASE journal, 557 APKs, Android 8-11) continuam funcionando?

### 4.3 Impacto na imagem Docker

- A imagem Docker (`docker/rvandroid/Dockerfile`) usa `phtcosta/rvandroid_tools:0.8.0` como base. Qual versão do Android SDK está nessa imagem?
- Se decidirmos atualizar SDK tools, precisamos rebuild da imagem base? Qual o esforço?

---

## 5. Pesquisa na internet: estado da arte

### 5.1 AspectJ + Android

Buscar e reportar:
- Como projetos Android que usam AspectJ (aspectjx, Hugo, etc.) lidam com incompatibilidade de d8?
- Issues conhecidas no GitHub do AspectJ (eclipse-aspectj/aspectj) sobre stack map tables
- `-xmlConfigured` em CTW: casos de uso documentados, limitações conhecidas
- Versão do AspectJ usada no projeto (1.9.24) vs mais recente — há melhorias em stack map handling?

### 5.2 d8/R8 e desugaring

Buscar:
- `--no-desugaring` com `--min-api 26`: é seguro em todos os casos?
- d8 `--debug` vs `--release`: diferença na validação de stack maps
- Versões recentes de d8: melhoraram tolerância a stack maps inválidos?

### 5.3 Alternativas ao dex2jar

Buscar:
- Google Enjarify: produziria bytecode mais limpo? Status do projeto?
- Ferramentas modernas de DEX → JAR conversion
- O dex2jar que o projeto usa é a versão mais recente?

### 5.4 Runtime verification em Android

Buscar:
- Papers recentes (2024-2026) sobre RV em Android — quais ferramentas usam?
- TraceMOP, DiSL, BISM — são alternativas viáveis ao AspectJ para weaving?
- Como outros projetos de RV lidam com a incompatibilidade de bytecode moderno?

---

## 6. Análise de riscos e mitigações

Para CADA mudança proposta, avaliar:

| Mudança | Risco | Probabilidade | Impacto | Mitigação |
|---------|-------|---------------|---------|-----------|
| `--no-desugaring` | ? | ? | ? | ? |
| `-proceedOnError` | ? | ? | ? | ? |
| `-xmlConfigured` + aop.xml | ? | ? | ? | ? |
| Não implementar pre-filtering | ? | ? | ? | ? |

Incluir riscos cruzados (ex: `-proceedOnError` + `aop.xml` juntos podem ter efeito inesperado).

---

## 7. Formato do relatório

Escrever em:
```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/catador/docs/analise_claude.md
```

### Estrutura esperada do relatório

```markdown
# Análise: Change gh50-improve-instrumentation
Data: 2026-04-18
Modelo: <nome do modelo>

## 1. Resumo executivo (1 parágrafo)

## 2. Análise de consistência dos artefatos
### 2.1 Rastreabilidade
### 2.2 Consistência com specs existentes
### 2.3 Consistência técnica
### 2.4 Formato e completude
### Veredicto: [PASS/FAIL com lista de issues]

## 3. Análise de impacto das exclusões MOP
### 3.1 Impacto por spec set (jca, generic, generic_new)
### 3.2 Quantificação
### 3.3 Coverage.aj interação
### Veredicto: [ACEITÁVEL/PROBLEMÁTICO com justificativa]

## 4. Android SDK e compatibilidade
### 4.1 API dinâmica: análise
### 4.2 Build tools: atualização necessária?
### 4.3 Compatibilidade retroativa
### Recomendação: [lista de ações]

## 5. Estado da arte
### 5.1 AspectJ + Android
### 5.2 d8/R8
### 5.3 Alternativas
### 5.4 RV em Android

## 6. Riscos e mitigações (tabela completa)

## 7. Pontos positivos

## 8. Pontos negativos / gaps

## 9. Sugestões de melhoria (priorizadas)

## 10. Conclusão e recomendação final
```

---

## Regras para a análise

1. **Evidências > opiniões**: toda afirmação deve ser suportada por dados (contagem de APKs, conteúdo de arquivos, documentação oficial)
2. **Caminhos absolutos**: sempre usar caminhos completos ao referenciar arquivos
3. **Citar fontes**: para pesquisas na internet, incluir URLs
4. **Não implementar**: apenas analisar e reportar. Não modificar nenhum arquivo exceto o relatório de saída
5. **Ser específico**: "a exclusão afeta X specs" é melhor que "pode afetar algumas specs"
6. **Conflitos de interesse**: se uma mudança beneficia JCA mas prejudica generic, reportar ambos os lados
```

---

Esse prompt cobre todas as dimensões que você mencionou. Os pontos-chave que adicionei vs. o seu rascunho:

- **Seção 3 inteira** (impacto das exclusões nos MOP specs) — a mais crítica, especialmente `call()` vs `execution()` e o efeito nos 3 conjuntos de specs
- **Seção 4** (Android SDK) — API dinâmica, build-tools atualização, compatibilidade retroativa
- **Seção 5.3/5.4** — alternativas ao dex2jar e estado da arte em RV Android
- **Regras explícitas** — caminhos absolutos, evidências, sem implementação
- **Estrutura do relatório** — com veredictos por seção

Quer que eu ajuste algo ou está pronto para enviar às LLMs?
# Análise da change gh55-env-purity-avd-api30

**Modelo**: gemini-2.0-flash-thinking-exp
**Data**: 2026-05-06
**Veredito geral**: APROVADA COM RESSALVAS

## 1. Sumário executivo
- **Consolidação γ**: A decisão de consolidar o refator de Env Vars e o bump de AVD é tecnicamente sound, dado que compartilham artefatos Docker e infraestrutura de CI.
- **Rigor Empírico**: A claim de "0 regressões" e ganho de 35% em APKs modernos (API 30) foi verificada e confirmada via auditoria dos CSVs de investigação (n=80).
- **Layer Purity**: A mudança impõe uma disciplina arquitetural necessária (env reads só em L5/L1), eliminando silent failures documentados.
- **Divergência Menor**: Identificada discrepância quantitativa entre a proposta (10 novas constantes) e as tarefas/plano real (13 novas constantes).
- **Rastreabilidade**: Excelente mapeamento entre Invariantes, Especificação, Design e Testes.

## 2. Pontos fortes
- **Aderência Estrita a P3**: A change não hesita em remover código morto e variáveis obsoletas (`RV_MEMORY_FILE`, `RV_JCA_SPEC`), seguindo o princípio de "No Backward Compatibility" (tasks 1.3, 5.3, 8.8).
- **Garantias de Runtime**: O uso de `ConfigDict(extra="forbid")` (INV-CORE-32) em conjunto com a validação do entrypoint (INV-EXP-31) cria uma barreira robusta contra typos e configurações zumbis.
- **Infraestrutura de Teste**: A criação de um lint específico (`check_env_vars_drift.py`) garante que a pureza de camadas não seja degradada por novos commits (INV-EXP-30/INV-TOOL-20).
- **Evidência Empírica**: A refutação do diagnóstico anterior (OverlayFS como bloqueador) baseia-se em dados frescos e reproduzíveis (`results/avd_compat_investigation/`).

## 3. Pontos fracos / Problemas

- **Problema 1**:
    - **Severidade**: Baixa
    - **Categoria**: estrutural
    - **Descrição**: Inconsistência quantitativa no inventário de constantes.
    - **Evidência**: `proposal.md` cita "10 new constants", enquanto `tasks.md:1.2` e a conta matemática baseada em `plano_env.md` §3.1 indicam 13 constantes novas.
    - **Impacto**: Confusão menor durante a conferência manual do commit.
    - **Sugestão**: Atualizar `proposal.md` para refletir o número correto (13).

- **Problema 2**:
    - **Severidade**: Média
    - **Categoria**: completude
    - **Descrição**: Violations de Layer Purity adicionais detectadas em ferramentas além da `humanoid`.
    - **Evidência**: `modules/rv-tools/src/rv_tools/builtin/{ape,droidmate,fastbot}/tool.py` contêm leituras de `TOOLS_DIR` via `os.environ.get`.
    - **Impacto**: Se não corrigidas, estas ferramentas continuam violando o INV-TOOL-20, mantendo dependências ocultas do ambiente.
    - **Sugestão**: Expandir a Task 4.8 para citar explicitamente a migração de `TOOLS_DIR` para o canal `parameters` ou registrá-la como exceção L1 (não recomendado).

- **Problema 3**:
    - **Severidade**: Baixa
    - **Categoria**: rastreabilidade
    - **Descrição**: Critérios de aceitação detalhados (Grupos A-H) estão ausentes dos artefatos SDD.
    - **Evidência**: `openspec/changes/gh55-.../` não contém a lista A-H presente em `docs/20260506_plano_env.md` §7.
    - **Impacto**: O auditor/revisor do PR precisa saltar para documentos de Phase 0 para entender o critério de sucesso final.
    - **Sugestão**: Referenciar explicitamente os 8 grupos A-H no `design.md` §7.

## 4. Análise por dimensão

### 4.1 CONSISTÊNCIA INTERNA
A change é altamente consistente. Os Invariantes declarados nas Specs (INV-CORE-30 a INV-TOOL-21) estão perfeitamente mapeados na tabela de Design e refletidos em tarefas unitárias em `tasks.md`. A única falha é a contagem de constantes em `proposal.md` vs `tasks.md`.

### 4.2 COERÊNCIA COM PHASE 0
O alinhamento com `docs/20260506_plano_env.md` é total. As decisões tomadas em Phase 0 (cleanup de mortas, Layer Purity, Opção B para AVD) foram transpostas sem distorções para a change SDD.

### 4.3 AMBIGUIDADES
O texto é técnico e direto. O uso de "Audit" na Task 4.8 é aceitável pois é seguido de um "migrate similarly", embora a detecção de `TOOLS_DIR` durante a auditoria gemini sugira que a lista de infratores poderia ser pré-populada para evitar escapes.

### 4.4 RASTREABILIDADE
Exemplar. Cada requisito técnico tem um teste correspondente planejado. A estrutura segue rigorosamente o schema `rv-sdd`.

### 4.5 TESTABILIDADE
Os critérios de aceitação definidos no plano (e referenciados) são determinísticos (exit codes, counts, grep matches). Não há termos subjetivos como "melhorado" sem métrica associada.

### 4.6 SOUNDNESS
A inferência de que API 30 é viável baseia-se em n=80 com 0 regressões. Isso é estatisticamente robusto o suficiente para o estágio atual, especialmente com o gate de n=200 planejado antes do merge final.

### 4.7 COMPLETUDE
A change cobre o ciclo de vida completo: backups, implementação, testes unitários, testes de integração, lint e documentação. A inclusão do ADR 0001 fecha a lacuna de "por quê".

### 4.8 ESCOPO
A consolidação em uma única change γ é correta. Separar Env Var de AVD exigiria dois ciclos de build de imagem Docker e modificações conflitantes em `docker-entrypoint.sh`.

### 4.9 RISCOS
Os riscos de incompatibilidade (especialmente `ape`) são mitigados pelo Gate H4 (Task 6.5). O risco de quebra de composes externos é mitigado pelo erro fatal (exit 64) no entrypoint.

### 4.10 PRINCÍPIOS (P1-P4)
- **P1**: Design simples, aproveitando Pydantic nativo.
- **P2**: Specs narrativas explicam o problema do "silent failure".
- **P3**: Remoção agressiva de legado (`JCA_SPEC`) com backups explícitos.
- **P4**: Task 6.2 limpa histórico de rollback, mantendo foco no estado atual.

### 4.11 BREAKING CHANGES
Claramente listadas e documentadas. O impacto no `docker-entrypoint.sh` é a maior breaking change, mas o benefício da unificação justifica o custo.

### 4.12 INFRAESTRUTURA DE LINT
O script `check_env_vars_drift.py` é o "herói não cantado" desta change, pois automatiza a manutenção da Layer Purity, transformando uma regra arquitetural em um gate de CI.

## 5. Riscos + mitigação
| Risco | Probabilidade | Impacto | Mitigação proposta | Já contemplado? |
|-------|---------------|---------|--------------------|-----------------|
| Incompatibilidade de ferramentas (ape/fastbot) em API 30 | Média | Alta | Smoke matrix (Gate H4) com 5 APKs/60min | Sim (Task 6.5) |
| Regressão em dataset maior (n=200) | Baixa | Média | Rodar investigação ampliada antes de merge | Sim (Task 6.6) |
| Quebra de scripts externos que usam vars removidas | Média | Baixa | Exit 64 com mensagem de erro clara e sugestão | Sim (INV-EXP-31) |
| TOOLS_DIR continuar lida via env em L2 | Alta | Baixa | Incluir TOOLS_DIR no saneamento de env vars | Parcial (via task 4.8) |

## 6. Auditoria de critérios de aceitação
(Baseado em `docs/20260506_plano_env.md` §7)
- **Grupo A (Inventário)**: Verificável? Sim. Determinístico? Sim. (Via lint).
- **Grupo B (Cleanup)**: Verificável? Sim. Determinístico? Sim. (Via grep hits=0).
- **Grupo C (Centralização)**: Verificável? Sim. Determinístico? Sim. (Via grep strings=0).
- **Grupo D (Flags)**: Verificável? Sim. Determinístico? Sim. (Via testes de precedência).
- **Grupo E (Layer Purity)**: Verificável? Sim. Determinístico? Sim. (Via lint/grep).
- **Grupo F (Validação Strict)**: Verificável? Sim. Determinístico? Sim. (Via testes de saída 64).
- **Grupo G (Sem Backcompat)**: Verificável? Sim. Determinístico? Sim. (Inspecção de tasks).
- **Grupo H (Doc Canônica)**: Verificável? Sim. Determinístico? Sim. (Checklist de arquivos).

## 7. Sugestões de melhoria
- **O quê**: Corrigir contagem de constantes (10 -> 13).
  - **Onde**: `proposal.md` seção "Env var / Layer Purity".
  - **Por quê**: Precisão documental.
- **O quê**: Listar explicitamente `TOOLS_DIR` como variável a ser migrada para `parameters`.
  - **Onde**: `tasks.md` seção 4.8.
  - **Por quê**: Detectadas violations em `ape`, `droidmate` e `fastbot` durante auditoria.
- **O quê**: Incluir seção de Acceptance Criteria referenciando Phase 0.
  - **Onde**: `design.md` após a tabela de Mapping.
  - **Por quê**: Centralizar critérios de sucesso no artefato de design.
- **O quê**: Reescrita de comentário histórico em `android.py:151`.
  - **Onde**: `modules/rv-android-core/src/rv_android_core/util/android/android.py`.
  - **Por quê**: Conformidade P4 (remover menção a commit de rollback gh50).

## 8. Riscos NÃO mitigados / open questions
- **Performance**: O bump para API 30 x86_64 pode exigir mais recursos de CPU do host (NDK Translation em runtime, embora não estejamos usando a imagem playstore). Não há teste de performance planejado.
- **Arm-only APKs**: A change decide manter `google_apis` (sem NDK Translation total). APKs que dependem exclusivamente de bibliotecas nativas ARM não-emuladas continuarão falhando.

## 9. Aprovação condicional
O veredito passará a **APROVADA** se:
1. A Task 4.8 for atualizada para tratar especificamente a variável `TOOLS_DIR` encontrada em múltiplos plugins.
2. A discrepância de contagem (10 vs 13) for resolvida.
3. Os critérios de aceitação (A-H) forem referenciados ou incluídos no Design.

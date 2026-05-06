# Análise da change gh55-env-purity-avd-api30

**Modelo**: Codex High
**Data**: 2026-05-06
**Veredito geral**: BLOQUEADA

## 1. Sumário executivo

- A estrutura mínima OpenSpec passa no validador local (`openspec validate gh55-env-purity-avd-api30 --strict` retornou `Change 'gh55-env-purity-avd-api30' is valid`), mas a change tem falhas semânticas e de rastreabilidade que o validador não captura.
- O contrato do Humanoid está contraditório entre proposal/specs/design/tasks: parte da change exige `parameters["url"]`, outra exige `parameters["humanoid_url"]` (`proposal.md:21`, `specs/platform/spec.md:40-42`, `specs/tools/spec.md:42,49`, `design.md:227-228`, `tasks.md:37-38`).
- A regra de Layer Purity não está operacionalizada de forma robusta: o lint prometido não detecta todos os padrões (`os.getenv`, `os.environ[...]`) e a própria baseline atual já tem leituras fora do escopo anunciado (`modules/rv-android-core/.../validation/config.py:72,77,82`, `modules/rv-instrumentation-ajc/.../config.py:397`, `modules/rv-tools/.../ape/tool.py:278`, `.../droidmate/tool.py:113`, `.../fastbot/tool.py:401`).
- A frente empírica sustenta apenas uma afirmação limitada: no sample `n=80`, houve 7 ganhos e 0 regressões; ela não sustenta a refutação forte do rollback `07179eb6` no caminho Docker, nem fecha os gates H4 e `>=100 APKs/dataset` (`docs/20260506_plano_env.md:529`, `:566-568`, `:596-611`, `proposal.md:32`, `tasks.md:63-64`).
- Há inconsistências entre o design e o código real atual em pontos-chave de implementação referenciada, inclusive `PlatformConfig.tool_configs` vs `PlatformConfig.tools` e `rv-platform.tool.factory.ToolFactory.create()` vs `rv_tools.registry.factory.ToolFactory.create_tool()` (`specs/platform/spec.md:5,31`, `design.md:60,77,179-185`, `modules/rv-platform/.../platform_config.py:49-50`, `modules/rv-tools/.../factory.py:37,77-78,127-133`).

## 2. Pontos fortes

- A change é coesa o suficiente para auditoria conjunta porque concentra duas mudanças que tocam a mesma superfície Docker e explicitam o racional de consolidação em γ (`proposal.md:11`, `design.md:12`, `design.md:116-119`).
- Os artefatos narram bem o problema principal de drift entre env vars, entrypoint e módulos; o propósito das specs é autocontido e legível, especialmente em `core` e `experiment` (`specs/core/spec.md:1-27`, `specs/experiment/spec.md:1-34`).
- A change preserva gates explícitos para a decisão do AVD, em vez de esconder risco residual: smoke matrix H4 e amostra maior continuam em aberto (`proposal.md:32`, `design.md:265-266`, `tasks.md:63-64`).
- Várias referências concretas usadas pela change batem com o estado atual do código, por exemplo `rv_experiment/config.py:745,748`, `rv_tools/builtin/humanoid/tool.py:13,89`, `scripts/run_emulator.sh:4` (`tasks.md:25`, `tasks.md:37`, `tasks.md:61`).

## 3. Pontos fracos / Problemas

- **Severidade**: Crítica
- **Categoria**: semântica
- **Descrição**: O contrato da chave de configuração do Humanoid é inconsistente entre os artefatos.
- **Evidência**: `proposal.md:21`, `specs/platform/spec.md:40-42`, `specs/tools/spec.md:42,49`, `design.md:227-228`, `tasks.md:37-38`
- **Impacto**: Implementação e testes podem convergir para contratos incompatíveis; a change deixa ambíguo o comportamento correto de `HumanoidTool.configure()`.
- **Sugestão**: Escolher uma única chave canônica e reescrever proposal, specs, design e tasks para o mesmo nome, com um cenário único end-to-end.

- **Severidade**: Crítica
- **Categoria**: testabilidade
- **Descrição**: O lint prometido não consegue impor `INV-CORE-31`, `INV-EXP-30` e `INV-TOOL-20` como escritos.
- **Evidência**: `specs/core/spec.md:26`, `specs/tools/spec.md:25`, `design.md:72,74`; leituras reais que escapam ao grep: `modules/rv-android-core/src/rv_android_core/util/validation/config.py:72,77,82`, `modules/rv-instrumentation-ajc/src/rv_instrumentation_ajc/config.py:397`
- **Impacto**: A change promete uma garantia arquitetural que o CI não consegue verificar de forma confiável; regressões reais podem passar.
- **Sugestão**: Especificar o lint em termos de AST/padrões abrangentes (`os.environ.get`, `os.environ[...]`, `os.getenv`) e listar explicitamente o universo de exceções permitidas.

- **Severidade**: Alta
- **Categoria**: estrutural
- **Descrição**: O delta `REMOVED` em `experiment/spec.md` não corresponde a um requirement autônomo da baseline e ainda viola a regra local de requirement com scenario.
- **Evidência**: `openspec/specs/experiment/spec.md:429-456`, `openspec/changes/gh55-env-purity-avd-api30/specs/experiment/spec.md:143-147`
- **Impacto**: A operação delta fica semanticamente ambígua; revisores e implementadores não sabem se removem um requirement inteiro ou apenas um cenário/comportamento dentro de `Docker Execution Mode`.
- **Sugestão**: Reescrever como `MODIFIED Requirement: Docker Execution Mode`, com bloco completo substituto e cenários cobrindo a remoção da tradução env→flag.

- **Severidade**: Alta
- **Categoria**: estrutural
- **Descrição**: `Strict Configuration Validation` foi modelado como requirement novo, mas a baseline já define normativamente `extra='forbid'` em `Pydantic Validation`.
- **Evidência**: `openspec/specs/core/spec.md:305-325`, `openspec/changes/gh55-env-purity-avd-api30/specs/core/spec.md:59-71`
- **Impacto**: A delta infla escopo e pode gerar duplicação normativa sobre o mesmo comportamento.
- **Sugestão**: Converter para `MODIFIED` do requirement existente ou explicar claramente o novo recorte se houver diferença real.

- **Severidade**: Alta
- **Categoria**: rastreabilidade
- **Descrição**: A change ancora parte da implementação em superfícies erradas ou inexistentes no repositório atual.
- **Evidência**: `specs/platform/spec.md:5,31`, `design.md:60,77,179-185`, `tasks.md:39`; código real: `modules/rv-platform/src/rv_platform/config/platform_config.py:49-50`, `modules/rv-tools/src/rv_tools/registry/factory.py:37,77-78,127-133`
- **Impacto**: A rastreabilidade Spec→Design→Tasks→Código quebra justamente onde deveria orientar a implementação.
- **Sugestão**: Reancorar o design e as tasks nos símbolos reais do repo atual, ou declarar explicitamente quais paths/nomes serão introduzidos como parte da change.

- **Severidade**: Alta
- **Categoria**: empírica
- **Descrição**: A change sobredeclara a refutação do commit `07179eb6`; os dados disponíveis são host-side e não reproduzem o cenário Docker citado no rollback.
- **Evidência**: `proposal.md:9`, `design.md:7`, `docs/20260506_plano_env.md:529`, `:604-611`, `results/avd_compat_investigation/20260506_133454/boot_smoke.csv:1-7`, `git show 07179eb6`
- **Impacto**: A decisão do AVD pode parecer mais fechada do que realmente está; isso reduz a clareza do gate pré-merge.
- **Sugestão**: Trocar “refutes” por linguagem mais precisa (“host-side evidence challenges the previous diagnosis”) ou anexar evidência Docker específica.

- **Severidade**: Média
- **Categoria**: rastreabilidade
- **Descrição**: O design e as tasks apontam para vários arquivos de teste/lint/doc que hoje não existem e, em parte, para uma árvore `.github/workflows/` inexistente.
- **Evidência**: `design.md:71,74-77`, `tasks.md:13,18-20,30,50,53,70,72`; estado atual: `.github` ausente, `tests/` top-level ausente
- **Impacto**: Parte da mudança fica não verificável no estado atual do repo e a revisão perde precisão sobre “arquivo existe vs NEW”.
- **Sugestão**: Marcar explicitamente esses caminhos como NEW em design/tasks e separar referências existentes de referências a criar.

- **Severidade**: Média
- **Categoria**: escopo
- **Descrição**: A regra de Layer Purity parece desenhada com foco excessivo no caso Humanoid e subestima outras leituras de env já existentes em L2/L3.
- **Evidência**: `proposal.md:7,21`, `tasks.md:42-43`; código atual: `modules/rv-tools/src/rv_tools/builtin/ape/tool.py:278`, `.../droidmate/tool.py:113`, `.../fastbot/tool.py:401`, `modules/rv-static-analysis/src/rv_static_analysis/config.py:109,124`
- **Impacto**: A implementação pode “cumprir” o texto narrativo e ainda deixar violações relevantes no sistema.
- **Sugestão**: Transformar o inventário completo de reads atuais em requisito explícito ou adicionar um cenário/critério cobrindo todas as classes detectadas pelo grep inicial.

## 4. Análise por dimensão

### 4.1 Consistência interna

A change não é internamente consistente em pontos centrais. O caso mais claro é o Humanoid: proposal e parte do design falam em canal por `PlatformConfig.tool_configs["humanoid"]["url"]` (`proposal.md:21`), a spec de platform fala em `parameters={"humanoid_url": ...}` (`specs/platform/spec.md:40-42`), e a spec de tools exige `configure({"url": ...})` (`specs/tools/spec.md:40-49`). Essa contradição atravessa proposal, specs, design e tasks, então não é um detalhe editorial; é quebra de contrato.

### 4.2 Coerência com Phase 0

Há boa aderência à motivação do Phase 0 na parte de env vars e no reconhecimento explícito dos gates do AVD (`docs/20260506_plano_env.md:397-452`, `proposal.md:15-32`). O problema é a extrapolação empírica: o plano diz que o teste foi no host e recomenda validar Docker antes de mudar o Dockerfile de produção (`docs/20260506_plano_env.md:604-611`), enquanto proposal/design falam em refutação mais categórica do rollback (`proposal.md:9`, `design.md:7`).

### 4.3 Ambiguidades

Há ambiguidades materiais, não só de redação. `PlatformConfig.tool_configs` é tratado como estrutura existente em `specs/platform/spec.md:5,31`, mas o código atual usa `tools: List[ToolConfig]` (`modules/rv-platform/.../platform_config.py:49-50`). Também há “ou sem decisão” em `tasks.md:38`, que permite resolver `RV_HUMANOID_URL` em `__main__.py` “ou `ExecutionController.setup`”, o que deixa a origem canônica da injeção indefinida.

### 4.4 Rastreabilidade

Os invariantes aparecem nas specs e quase todos entram na tabela de mapping do design (`design.md:71-79`), mas a trilha até o código falha em pontos relevantes. `INV-PLT-25` está mapeado para uma factory no namespace errado e para um campo que não existe na configuração atual. Além disso, vários destinos de teste/lint são NEW e não estão sempre distinguidos como tal na linguagem do design, o que enfraquece a auditoria “arquivo existe em disco?”.

### 4.5 Testabilidade

Os critérios A-H do Phase 0 são em geral bem formulados e tendem a ser verificáveis (`docs/20260506_plano_env.md:401-452`), mas a testabilidade cai quando a change define mecanismos insuficientes. Exemplo: `C3/C4`, `E1/E2` e `INV-CORE-31/EXP-30/TOOL-20` dependem de grep simples que não cobre `os.getenv` e nem todo cross-layer read. Outro problema é que alguns critérios pedem “message useful/clear”, que é verificável só parcialmente se o texto mínimo esperado não for especificado.

### 4.6 Soundness

A inferência “7 ganhos, 0 regressões” é sound apenas para o sample `n=80`, e os dados disponíveis sustentam isso. Já a inferência “o diagnóstico de OverlayFS do rollback foi refutado” não é sound com os artefatos atuais, porque o rollback era especificamente sobre boot no container e o próprio Phase 0 admite que essa confirmação em Docker ainda falta (`docs/20260506_plano_env.md:604-611`).

### 4.7 Completude

A change cobre o eixo principal de env vars, mas ainda não trata completamente o universo real de leituras fora de L5. O próprio repositório atual tem leituras em built-ins além do Humanoid e em módulos de instrumentação/static analysis. Sem transformar esse inventário em requisito verificável, a change fica incompleta para a promessa de “Layer Purity rule” global.

### 4.8 Escopo

O escopo γ é defensável, porque a consolidação evita conflitos em superfícies Docker e foi uma decisão consciente do Phase 0 (`docs/20260506_plano_env.md:95-104`, `design.md:116-119`). Mesmo assim, a parte AVD precisa ser apresentada como mudança condicionada por gates ainda abertos, não como decisão praticamente encerrada. O problema aqui não é tanto o bundling, mas o grau de fechamento atribuído à evidência.

### 4.9 Riscos

Os riscos listados no plano e no design são razoáveis (`docs/20260506_plano_env.md:501-509`, `design.md:244-250`), porém a mitigação para drift checker é fraca porque depende de um lint subespecificado. O risco “algum módulo L2/L3/L4 lê env não detectada no grep inicial” já está materializado no estado atual do repo, o que deveria subir sua criticidade.

### 4.10 Princípios

Há aderência parcial a P1/P2/P3/P4. P2 é forte na narrativa dos propósitos e decisões. P3 aparece bem na intenção de backups e remoção dura (`proposal.md:39-43`, `tasks.md:5-12,47-53`). Já P1 sofre com duplicação normativa em `Strict Configuration Validation`, e P2/P3 sofrem onde as operações delta não correspondem bem à baseline. P4 ainda é afrontado pelo estado atual referenciado em `scripts/run_emulator.sh:8-25`, que mantém comentários históricos justamente onde a change promete reescrever.

### 4.11 Breaking Changes

Os principais breaking changes estão listados: remoção de `RV_MEMORY_FILE`, `RV_RVANDROID_URL`, `RV_SKIP_EXPERIMENT`, `RV_JCA_SPEC`; reescrita do entrypoint; bump do AVD (`proposal.md:18,23,29-32,80-84`). O ponto fraco é a comunicação de impacto sobre compose files e sobre snapshots/configs externos: o design menciona o risco, mas não explicita uma matriz de impacto por artefato consumidor.

### 4.12 Infraestrutura de lint

A infraestrutura de lint proposta não é robusta o suficiente. O texto promete detectar string literals e cross-layer reads, mas os exemplos normativos se baseiam em greps que não cobrem todas as variantes sintáticas. Além disso, `INV-CORE-30` fala em `modules/`, `docker/` e `scripts/`, enquanto `INV-EXP-30` e `INV-TOOL-20` restringem escopo de forma diferente; falta uma definição única de universo auditado por regra.

## 5. Riscos + mitigação

| Risco | Probabilidade | Impacto | Mitigação proposta | Já contemplado? |
|---|---|---|---|---|
| Implementação do Humanoid divergir entre `url` e `humanoid_url` | Alta | Alto | Unificar contrato em todos os artefatos e adicionar cenário único ponta a ponta | Não |
| Lint deixar passar regressões reais de Layer Purity | Alta | Alto | Especificar detecção abrangente para `os.environ.get`, `os.environ[...]` e `os.getenv`, com allow-list explícita | Parcial |
| Revisão aprovar “refutação” do rollback sem evidência Docker | Média | Alto | Rebaixar a claim ou anexar teste Docker reproduzível | Não |
| Tasks apontarem para superfícies erradas do código | Média | Alto | Reancorar mapping/task nos símbolos reais do repo atual | Não |
| Gates H4 e `>=100` serem esquecidos no merge | Média | Alto | Promover gates a checklist de bloqueio no proposal/design/tasks com linguagem inequívoca | Parcial |

## 6. Auditoria de critérios de aceitação

### A — Inventário e Doc Truth

- É verificável? `parcial` — A1-A3 são verificáveis por contagem/grep, mas A4 (“CLAUDE.md cita o ADR”) depende de arquivo novo ainda inexistente.
- É determinístico? `sim`
- Sugestão de melhoria: especificar o comando de contagem de entradas do README e o formato exato esperado da tabela.

### B — Dead Code Cleanup

- É verificável? `sim`
- É determinístico? `sim`
- Sugestão de melhoria: explicitar que hits em `backup/` são excluídos do grep final, senão o critério conflita com B3.

### C — Centralização via `ENV_*`

- É verificável? `parcial` — C1-C2 dependem de um inventário correto; C3-C4, como escritos, não cobrem `os.getenv`.
- É determinístico? `sim`
- Sugestão de melhoria: ampliar o critério para todas as formas de leitura de ambiente e listar exceções permitidas.

### D — Flags Faltantes

- É verificável? `sim`
- É determinístico? `sim`
- Sugestão de melhoria: fixar os comandos de teste dos 6 cenários e os valores esperados do config resultante.

### E — Layer Purity

- É verificável? `parcial` — E1/E2 dependem de lint insuficiente; E3 ainda introduz exceção adicional que não aparece consistentemente nas specs.
- É determinístico? `sim`
- Sugestão de melhoria: alinhar a exceção de `rv-static-analysis` com `INV-EXP-30` e com o universo real de leituras atuais.

### F — Validação Strict

- É verificável? `sim`
- É determinístico? `sim`
- Sugestão de melhoria: em F3, fixar o exit code esperado como `64`, não apenas `!= 0`, para manter simetria com F1.

### G — Sem Backward Compat

- É verificável? `parcial` — G1-G3 são verificáveis; G4 (“uma commit = um estado consistente”) depende de estratégia de commits, não de propriedade estática do artefato.
- É determinístico? `não` para G4; `sim` para os demais
- Sugestão de melhoria: mover G4 para política de implementação/PR, não para critério de aceitação do artefato.

### H — Documentação Canônica

- É verificável? `sim`
- É determinístico? `sim`
- Sugestão de melhoria: explicitar se a fonte de verdade é README, `.env.example` ou ambos, para evitar drift bidirecional.

## 7. Sugestões de melhoria

- **O quê**: Unificar o contrato do Humanoid em um único nome de chave e um único fluxo L5→L4→L2.
- **Onde**: `proposal.md:21`, `specs/platform/spec.md:40-42`, `specs/tools/spec.md:40-49`, `design.md:227-228`, `tasks.md:37-38`
- **Por quê**: Elimina a contradição mais crítica da change.

- **O quê**: Reescrever o delta de `Docker Execution Mode` como `MODIFIED` completo, absorvendo explicitamente a remoção da tradução env→flag.
- **Onde**: `specs/experiment/spec.md:38-97`, `:143-147`
- **Por quê**: Corrige a operação delta e a ausência de scenario no bloco removido.

- **O quê**: Reclassificar `Strict Configuration Validation` como modificação da baseline de `Pydantic Validation`, ou justificar claramente a novidade normativa.
- **Onde**: `specs/core/spec.md:59-71`
- **Por quê**: Evita duplicação e melhora a fidelidade estrutural ao OpenSpec.

- **O quê**: Tornar o lint normativo realmente abrangente e alinhado com as exceções aceitas.
- **Onde**: `specs/core/spec.md:25-27,35-37`, `specs/experiment/spec.md:32-34,127-140`, `specs/tools/spec.md:25-26,53-57`, `design.md:71-79`
- **Por quê**: Sem isso, a principal garantia arquitetural da change não é auditável.

- **O quê**: Ajustar o mapping e as tasks para os símbolos reais do repo atual (`PlatformConfig.tools`, `ToolFactory.create_tool`, paths de teste existentes ou explicitamente NEW).
- **Onde**: `specs/platform/spec.md:5,31`, `design.md:60,77,179-185`, `tasks.md:39,41,53`
- **Por quê**: Recupera a rastreabilidade Spec→Design→Tasks→Código.

- **O quê**: Rebaixar a claim de “refutação” do rollback ou anexar evidência Docker específica.
- **Onde**: `proposal.md:9`, `design.md:7`, `docs/20260506_plano_env.md:529,604-611`
- **Por quê**: Mantém a change epistemicamente correta e alinhada aos dados disponíveis.

## 8. Riscos NÃO mitigados / open questions

- A exceção de `rv-static-analysis` standalone em `docs/20260506_plano_env.md:431` não aparece de forma consistente nas specs da change; ela é regra real ou apenas hipótese de implementação?
- O universo “3 exceções L1” é suficiente? O código atual ainda lê `RV_PYDANTIC_STRICT` e `RV_PYDANTIC_LOG` em L1 (`modules/rv-android-core/.../validation/config.py:77,82`).
- A change pretende migrar apenas env vars `RV_*` ou também `TOOLS_DIR`/`APERV_LLM_BASE_URL`, que hoje aparecem em tools/plugins?
- Os testes propostos devem viver em diretórios por módulo ou em um topo `tests/` novo? O design e as tasks misturam os dois modelos.

## 9. Aprovação condicional

1. Unificar o contrato do Humanoid em todos os artefatos, incluindo nome da chave, local de resolução e cenários de teste.
2. Corrigir as operações delta da spec de experiment e core para refletirem a baseline real.
3. Especificar um lint capaz de detectar todas as leituras de ambiente relevantes e listar explicitamente as exceções autorizadas.
4. Reancorar design/tasks nos símbolos e paths reais do repositório atual, distinguindo claramente arquivos existentes de arquivos NEW.
5. Reescrever a narrativa empírica do AVD para não ultrapassar a evidência disponível, mantendo H4 e `>=100 APKs/dataset` como bloqueios explícitos de merge.

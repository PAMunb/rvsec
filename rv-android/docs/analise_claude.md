# Análise da change gh55-env-purity-avd-api30

**Modelo**: Claude Opus 4.7 (1M context)
**Data**: 2026-05-06
**Veredito geral**: **APROVADA COM RESSALVAS**

A change é coesa, empiricamente bem fundamentada e estruturalmente válida pelo `openspec validate --strict`. Porém possui **erros estruturais críticos** sobre nome de campo (`tool_configs` vs `tools` em `PlatformConfig`), localização da `ToolFactory` (rv-tools L2 — não rv-platform L4 como afirmado), **subdimensionamento severo de escopo** (37 compose files reais vs "~12" declarados; 25 setam `RV_JCA_SPEC` que será removido), **buracos de cobertura no lint** (`os.getenv` não é capturado, `aperv-tool` fora do escopo, `RV_PYDANTIC_STRICT/LOG` não estão no registro nem são removidos) e **violações de Layer Purity não endereçadas** (`dexlib2:525` faz `dict(os.environ)`, instrumentation L3 com literais `RVSEC_HOME`). Antes de mergear, as ressalvas §9 devem ser tratadas — caso contrário a allow-list do entrypoint fará 25+ compose files e código L1 existente falharem com exit 64.

---

## 1. Sumário executivo

- **Empírica é sólida**: `results/avd_compat_investigation/20260506_133454/` confirma todos os 6 boots OK, exatamente os 7 ganhos nominais listados em proposal.md/design.md/§10.3 do plano, e 0 regressões verificadas no `apk_compat.csv` (n=80). A refutação do diagnóstico OverlayFS de gh50 §17 está ancorada em código (`docker/android/scripts/start-emulator.sh:76-87` não passa `-writable-system`).
- **Erros de nomenclatura estrutural** se propagam por proposal/design/4 specs/tasks: `PlatformConfig.tool_configs` não existe — o campo se chama `tools` e é **obrigatório** (não `default_factory=list`). `ToolFactory.create_tool()` (não `create`) vive em `rv_tools.registry.factory` (L2), não em `rv-platform.tool.factory` (L4 inexistente).
- **Escopo P3 subdimensionado**: 37 compose files (não "~12") em `docker/`, dos quais **25 setam `RV_JCA_SPEC=true`** que a change remove. Sem atualização explícita, a validação exit-64 do novo entrypoint quebra esses 25 arquivos no momento do merge.
- **Buracos de cobertura no lint INV-CORE-31**: o grep proposto (`os\.environ\.get("RV_`) não captura `os.getenv("RV_*")` nem `os.environ["RV_*"]`. Há 3 leituras `os.getenv("RV_PYDANTIC*")` em L1 que ficam invisíveis; e duas dessas vars (`RV_PYDANTIC_STRICT`, `RV_PYDANTIC_LOG`) não estão no registry nem são removidas.
- **Layer Purity incompleta**: `dexlib_instrumentation.py:525` faz `return dict(os.environ)` em L3 (vazamento total); `aperv-tool` (L2 separado) lê `APERV_LLM_BASE_URL`/`TOOLS_DIR`/`RVSEC_HOME` mas está fora do escopo da INV-TOOL-20 (que só cobre `modules/rv-tools/src/rv_tools/builtin/`). `TOOLS_DIR` é lido em 5+ pontos sem entrar no registry.

---

## 2. Pontos fortes

- **Validação OpenSpec estrita passa**: `openspec validate gh55-env-purity-avd-api30 --strict` retorna `is valid` (verificado).
- **Estrutura sintática perfeita**: 23 cenários todos com 4 hashtags; 9 Requirements todos com 3 hashtags; cada Requirement tem ≥1 Scenario; REMOVED tem `**Reason**` explícito (`experiment/spec.md:147`) — conforme P3.
- **Phase 0 autoritativo e empírico**: `docs/20260506_plano_env.md` §10 traz CSVs reais (`boot_smoke.csv`, `apk_compat.csv`) com exatos 80 testes; os 7 ganhos nominais batem 1-para-1 com a lista do plano §10.3 e do proposal §27 (verificado via `summary.md`).
- **Design.md tem mapeamento Spec→Impl→Test**: tabela em `design.md:67-79` cobre todas as 9 invariantes (INV-CORE-30/31/32, INV-EXP-30/31/32, INV-PLT-25, INV-TOOL-20/21) com triplete (declaração + ponto de implementação + teste).
- **D1-D7 documentam alternativas com justificativa**: cada decisão arquitetural lista 2-3 alternativas e por que foram rejeitadas (ex: D2 — env→flag translation cria duas paths paralelas; D5 — `RVSec` vs `RVSec30` evita renaming a cada bump).
- **Backup procedure P3-conforme**: cada task group começa com `Backup … to backup/2026-05-06_env_var_cleanup/` (1.1, 4.1, 5.1, 6.1) — um diretório dedicado, gitignored, antes de overwrites.
- **Refutação do gh50 §17 ancorada empiricamente**: o diagnóstico antigo de "OverlayFS multi-step required" é desafiado por (a) `docker/android/scripts/start-emulator.sh:76-87` que **não passa** `-writable-system`, (b) commit `c0274def` ("drop dead Phase 3") que invalida a heurística stderr-vazio, e (c) boot smoke 6/6 success na investigação `20260506_133454/`.
- **Risco table abrangente**: `design.md:243-250` enumera 6 riscos com mitigações concretas (rebuild image rotulado `phtcosta/rvandroid:0.9.0-api30`, gate H4 hard-bloqueante, allow-list por-rule no script).
- **Distinção L5 vs L1 cross-layer bem articulada**: as 3 exceções (`RV_PYDANTIC`, `RVSEC_HOME`, `ANDROID_HOME`) são citadas literalmente em proposal §20, design §44, experiment/spec §3, e tools/spec §7.

---

## 3. Pontos fracos / Problemas

### Problema 1 — `PlatformConfig.tool_configs` não existe (campo se chama `tools`)

- **Severidade**: **Crítica**
- **Categoria**: estrutural
- **Descrição**: Em todos os 5 artefatos da change, o campo é referido como `PlatformConfig.tool_configs`. O código real (`modules/rv-platform/src/rv_platform/config/platform_config.py:50`) define `tools: List[ToolConfig] = Field(description="List of tools to execute")` (obrigatório, sem `default_factory=list`). O campo `tool_configs` existe sim em `ExperimentConfig` (`modules/rv-experiment/src/rv_experiment/config.py:108`) — a change está confundindo os dois modelos.
- **Evidência**:
  - `proposal.md:21,89`, `design.md:30,60,183-185,227-228`, `platform/spec.md:12,25,40,52`, `tasks.md:38` — todos citam `PlatformConfig.tool_configs`.
  - `modules/rv-platform/src/rv_platform/config/platform_config.py:50`: `tools: List[ToolConfig] = Field(description=...)` (sem default).
  - `modules/rv-experiment/src/rv_experiment/config.py:108`: `tool_configs: List[ToolConfig] = Field(default_factory=list)`.
  - `modules/rv-experiment/src/rv_experiment/factories/configuration_factory.py:92`: `tools=tools` (a fábrica traduz `tool_configs` em `tools`).
- **Impacto**: A INV-PLT-25 e o Scenario "PlatformConfig rejects malformed tool_configs" (`platform/spec.md:52-55`) estão verificáveis num campo que não existe. Tarefa 4.3 ("inject into the appropriate ToolConfig.parameters['humanoid_url'] for any `tool_configs` entry") implementaria a coisa errada se seguida literalmente em PlatformConfig.
- **Sugestão**: Decidir entre (a) renomear o campo de PlatformConfig para `tool_configs` (P3-friendly: uma migração explícita) ou (b) corrigir todos os artefatos para `PlatformConfig.tools` e mover INV-PLT-25 para mencionar `tools`. A opção (b) é mais simples e não introduz mudança comportamental.

### Problema 2 — `ToolFactory` está em rv-tools (L2), não em rv-platform (L4)

- **Severidade**: **Crítica**
- **Categoria**: rastreabilidade
- **Descrição**: `tasks.md:39` cita `rv-platform.tool.factory.ToolFactory.create()`. A classe real está em `modules/rv-tools/src/rv_tools/registry/factory.py:37`, e o método é `create_tool(tool_config)` (não `create`). `rv-platform/platform.py:29` apenas importa: `from rv_tools import ToolFactory`. Não existe `modules/rv-platform/src/rv_platform/tool/factory.py`.
- **Evidência**:
  - Tasks 4.4: `In rv-platform.tool.factory.ToolFactory.create() (verifies INV-PLT-25)`.
  - Design `design.md:60`: `ToolConfig.parameters` (`Dict[str, Any]`)... `ToolFactory.create(tool_config)`.
  - Real: `modules/rv-tools/src/rv_tools/registry/factory.py:73 def create_tool(self, tool_config)`.
  - `modules/rv-platform/src/rv_platform/platform.py:29 from rv_tools import ToolFactory`.
- **Impacto**: A invariante **INV-PLT-25** está nominalmente em "platform" (L4) mas a implementação da regra ("ToolFactory forwards `tool_config.parameters`") vive em L2. Se um auditor seguir o caminho citado, não encontra o código. O teste `test_tool_factory_parameters_channel.py` planejado para `modules/rv-platform/tests/` (tasks 4.6) testaria o comportamento certo em módulo errado.
- **Sugestão**: Renomear INV-PLT-25 → INV-TOOL-25 (vive em rv-tools); ajustar tabela de mapping em design.md:77 e tarefa 4.4/4.6 para `rv_tools.registry.factory.ToolFactory.create_tool`. O teste pode ficar em rv-platform OU rv-tools — ambos fazem sentido funcionalmente, mas o lint deve cobrir o repo do tool factory.

### Problema 3 — Escopo de compose files subdimensionado em ~3x

- **Severidade**: **Crítica**
- **Categoria**: escopo
- **Descrição**: Proposal/design/tasks consistentemente dizem "~12 docker-compose.*.yml". A contagem real é **37 arquivos** em `docker/`. Pior: **25 deles setam `RV_JCA_SPEC=true`**, que será uma das 4 vars removidas (proposal §18 / tasks 1.3). Após a change, o entrypoint allow-list vai exitar 64 nesses 25 compose files no merge, sem que tenham sido tocados pela change.
- **Evidência**:
  - `proposal.md:31` "All `docker-compose.*.yml` files in `docker/` updated explicitly in the same change (P3 — no shims/aliases)" — promessa coberta.
  - `proposal.md:71` "All ~12 compose files audited and updated explicitly" — número errado.
  - `tasks.md:52` "Update all ~12 docker/docker-compose.*.yml files explicitly".
  - `ls docker/docker-compose*.yml | wc -l` = 37.
  - `grep -l '^\s*RV_JCA_SPEC' docker/docker-compose*.yml | wc -l` = 25.
- **Impacto**: Promessa P3 ("uma change = um estado consistente") quebrada. Risco de regressão silenciosa para 25 fluxos experimentais. Subestimativa de esforço para a fase 5 (entrypoint refactor).
- **Sugestão**: (1) Substituir "~12" por "all 37 (verificar `ls docker/docker-compose*.yml`)" em proposal/design/tasks. (2) Adicionar tarefa 5.4-bis explicitando os 25 compose files que setam `RV_JCA_SPEC` e migrando para `RV_SPEC_SET`. (3) Aumentar smoke matrix de 3 → ≥5 compose files representativos.

### Problema 4 — `RV_PYDANTIC_STRICT` e `RV_PYDANTIC_LOG` invisíveis para a change

- **Severidade**: **Crítica**
- **Categoria**: completude / soundness
- **Descrição**: `modules/rv-android-core/src/rv_android_core/util/validation/config.py:77,82` lê `os.getenv("RV_PYDANTIC_STRICT", "false")` e `os.getenv("RV_PYDANTIC_LOG", "false")`. Estas duas vars `RV_*` estão **vivas em produção** (também referenciadas em `.hypothesis/constants/45f7fd1d47b9505d`) mas:
  - Não constam do plano §3.1 (inventário "26+ env vars distintas").
  - Não constam de proposal §17 (lista de 13 novas constants), de tasks 1.2, nem do registro proposto.
  - Não são listadas como removidas (proposal §18 lista apenas 4).
  - Após o merge, qualquer compose ou comando que as configure fará o entrypoint exitar 64 (silent breaking).
- **Evidência**:
  - `modules/rv-android-core/src/rv_android_core/util/validation/config.py:71-82`:
    ```python
    def _read_pydantic_env_var(self) -> bool:
        env_value = os.getenv("RV_PYDANTIC", "false").lower()
        ...
    def _read_pydantic_strict_env_var(self) -> bool:
        env_value = os.getenv("RV_PYDANTIC_STRICT", "false").lower()
    def _read_pydantic_log_env_var(self) -> bool:
        env_value = os.getenv("RV_PYDANTIC_LOG", "false").lower()
    ```
  - `grep -E "PYDANTIC_STRICT|PYDANTIC_LOG" openspec/changes/gh55-env-purity-avd-api30/ docs/20260506_plano_env.md -r` retorna **0 hits**.
- **Impacto**: Inventário incompleto contradiz a INV-CORE-30 ("Every `RV_*` environment variable consumed anywhere in the project ... MUST have a corresponding `ENV_*` constant"). Se INV-CORE-30 vale como spec, ela está sendo violada já no momento de criação porque essas duas vars não foram catalogadas.
- **Sugestão**: Decidir explicitamente: (a) adicionar `ENV_PYDANTIC_STRICT` e `ENV_PYDANTIC_LOG` ao registro (junto com `ENV_PYDANTIC`); (b) remover as duas como dead code se a feature não está em uso (aplicar P3); (c) listar como exceções L1-cross-layer junto com `RV_PYDANTIC`. A escolha não pode ser "nada".

### Problema 5 — Lint INV-CORE-31 não captura `os.getenv` nem `os.environ[`

- **Severidade**: **Alta**
- **Categoria**: testabilidade / lint robustness
- **Descrição**: `core/spec.md:26` define a verificação como `grep -rn 'os\.environ\.get("RV_' modules/`. Esse padrão **não captura**:
  - `os.environ["RV_X"]` (forma subscript) — o plano §7-C4 menciona, a spec não.
  - `os.getenv("RV_X")` — não há mention em spec, plan, ou tasks. Existem 3 ocorrências reais.
- **Evidência**:
  - `core/spec.md:26`: lint só com `os.environ.get("RV_`.
  - `tasks.md:18`: drift checker faz "(a) every `os.environ.get`/`os.environ[` reference uses an `ENV_*` symbol" — menciona subscript mas omite `os.getenv`.
  - `docs/20260506_plano_env.md:418-419`: critério C3+C4 cita `os.environ.get("RV_` E `os.environ["RV_` mas nada sobre `os.getenv`.
  - Confirmado em código: `grep -rnE 'os\.getenv\("RV_' modules/` retorna 3 hits em `validation/config.py`.
- **Impacto**: Drift checker falha em 3 pontos hoje; gera falso negativo em CI; ataca a credibilidade da promessa "single, lint-enforced contract".
- **Sugestão**: Padronizar em **três** verificações: `grep -rnE 'os\.environ\.get\("RV_|os\.environ\["RV_|os\.getenv\("RV_' modules/`. Atualizar core/spec.md:26, tasks.md:18, plan §7-C, e o teste `tests/lint/test_env_vars_drift.py` (planted-violation fixture deve cobrir as três formas).

### Problema 6 — INV-TOOL-20 lint scope não cobre `aperv-tool` nem `rvagent-tool`

- **Severidade**: **Alta**
- **Categoria**: escopo / soundness
- **Descrição**: `tools/spec.md:25` diz INV-TOOL-20 é verificada por `grep -rnE 'os\.environ' modules/rv-tools/src/rv_tools/builtin/`. Mas `aperv-tool` e `rvagent-tool` são módulos L2 separados (`modules/aperv-tool/`, `modules/rvagent-tool/`) — **fora do scope do grep**. `aperv-tool` tem 3 leituras de env reais. A própria tools/spec.md:7 diz "external plugins (e.g., `aperv-tool`, `rvagent-tool`, future plugins) MUST also follow Layer Purity" — mas o lint não cobre.
- **Evidência**:
  - `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py:329` `os.environ.get("APERV_LLM_BASE_URL")`.
  - `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py:352` `os.environ.get("RVSEC_HOME", "")`.
  - `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py:355` `os.environ.get("TOOLS_DIR", "")`.
  - `tools/spec.md:25`: scope `modules/rv-tools/src/rv_tools/builtin/` apenas.
  - Architecture doc (`docs/rv_android_architecture.md:104-110`) confirma `aperv-tool` e `rvagent-tool` são L2.
  - tasks.md:43: "Audit `modules/rv-tools/src/rv_tools/builtin/**/`" — não menciona aperv-tool/rvagent-tool.
- **Impacto**: Layer Purity claim ("L2 não lê env") é falsa para 2 módulos L2 que ficam invisíveis ao lint. INV-TOOL-20 dá impressão de cobertura completa quando é parcial.
- **Sugestão**: Ampliar scope INV-TOOL-20 para `modules/{rv-tools,aperv-tool,rvagent-tool}/src/`, ou criar INV-TOOL-22 cobrindo plugins externos. Adicionar tarefa 4.8-bis migrando os 3 reads em `aperv-tool/tool.py:329,352,355`. tasks.md:43 já fala de "audit" mas é vago demais — precisa enumerar os arquivos.

### Problema 7 — `dexlib_instrumentation.py:525` faz `dict(os.environ)` (vazamento total) e há literais `"RVSEC_HOME"` em L3

- **Severidade**: **Alta**
- **Categoria**: princípios (P1, Layer Purity) / soundness
- **Descrição**: A change promete Layer Purity ("L2/L3/L4 não leem env") mas ignora 3 violações em rv-instrumentation:
  1. `modules/rv-instrumentation-dexlib2/.../dexlib_instrumentation.py:525` — `return dict(os.environ)` (dump completo do ambiente em L3).
  2. `modules/rv-instrumentation-dexlib2/.../dexlib_instrumentation.py:592` — `os.environ.get("RVSEC_HOME")` (literal, deveria usar `ENV_RVSEC_HOME`).
  3. `modules/rv-instrumentation-ajc/.../ajc_instrumentation.py:419` — `os.environ.get("RVSEC_HOME")` (literal).
  
  Plano §3.2 diz "Demais L2/L3/L4 — OK (não lêem env)" — empiricamente falso.
- **Evidência**:
  - Comando: `grep -rnE 'os\.environ' modules/rv-instrumentation*/src/`.
  - 3 hits acima, todos persistirão após a change.
- **Impacto**: INV-EXP-30 ("rv-experiment is the only Python module under `modules/` that reads user-facing `RV_*` environment variables") é tecnicamente OK (esses são `RVSEC_HOME`, não `RV_*`), mas a *promessa* de Layer Purity ampla na proposal §20 e design §39 é violada. Ainda: `dict(os.environ)` em L3 é incompatível com qualquer auditoria automática.
- **Sugestão**: Triagem explícita: (a) corrigir os 2 literais `"RVSEC_HOME"` para `ENV_RVSEC_HOME` (cumprindo INV-CORE-31); (b) decidir se `RVSEC_HOME` em L3 conta como exceção L1-cross-layer ou se deve ser propagado via config; (c) eliminar `dict(os.environ)` em dexlib2:525 ou justificar como "ambiente de subprocess execvpe-style".

### Problema 8 — `TOOLS_DIR` lido em 5+ pontos sem entrar no registro

- **Severidade**: **Alta**
- **Categoria**: escopo / completude
- **Descrição**: `TOOLS_DIR` é uma env var lida em:
  - `modules/rv-android-core/src/rv_android_core/util/jar_resolver.py:300`
  - `modules/rv-tools/src/rv_tools/builtin/ape/tool.py:278`
  - `modules/rv-tools/src/rv_tools/builtin/droidmate/tool.py:113`
  - `modules/rv-tools/src/rv_tools/builtin/fastbot/tool.py:401`
  - `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py:355`
  
  Não é `RV_*` (foge ao regex `^RV_[A-Z_]+` da INV-EXP-31), mas a proposal §20 diz "Layer Purity rule: only rv-experiment (L5) and rv-android-core (L1, restricted to cross-layer infra exceptions: RV_PYDANTIC, RVSEC_HOME, ANDROID_HOME) may read environment variables". `TOOLS_DIR` cabe na descrição ("environment variables") mas não nas 3 exceções listadas. Ambíguo.
- **Evidência**: greps acima.
- **Impacto**: A "lista canônica de exceções L1" é incompleta. Lint passa porque o nome não é `RV_*`. Promessa "Layer Purity" tem furo.
- **Sugestão**: Incluir `TOOLS_DIR` explicitamente: (a) como 4ª exceção L1-cross-layer junto com RV_PYDANTIC/RVSEC_HOME/ANDROID_HOME, OR (b) migrar os 5 reads para config-passed pattern, OR (c) declarar fora-de-escopo desta change com nota em design.md "Open Questions".

### Problema 9 — Proposal §17 diz "10 new constants" mas tudo o resto diz 13

- **Severidade**: **Média**
- **Categoria**: consistência interna
- **Descrição**: Inconsistência numérica.
- **Evidência**:
  - `proposal.md:17`: "(10 new constants for currently-uncovered variables)".
  - `proposal.md:64` (tabela Impact): "+13 ENV_* constants, −4 dead constants".
  - `tasks.md:10` (tarefa 1.2): lista 13 nomes explícitos.
  - `docs/20260506_plano_env.md:216-232` (§6.1): lista 13 nomes (`ENV_APKS_DIR`, `ENV_SPEC_SET`, ..., `ENV_PYDANTIC` total 13).
- **Impacto**: Leitores casuais podem confiar em "10" e produzir um patch incompleto.
- **Sugestão**: Trocar `proposal.md:17` para "13 new constants for currently-uncovered variables".

### Problema 10 — Tasks.md não cita 6 das 9 invariantes por ID

- **Severidade**: **Média**
- **Categoria**: rastreabilidade
- **Descrição**: Apenas 3 invariantes (INV-CORE-32, INV-EXP-32, INV-PLT-25) têm citação textual em tasks.md. As outras 6 (INV-CORE-30, INV-CORE-31, INV-EXP-30, INV-EXP-31, INV-TOOL-20, INV-TOOL-21) só aparecem na tabela de mapping de design.md, não em tasks.md.
- **Evidência**: `grep -nE 'INV-(CORE|EXP|PLT|TOOL)-' tasks.md` retorna 4 hits em 3 IDs distintos (32, 32, 25, 25).
- **Impacto**: Auditor que lê só tasks.md (sem cruzar com design.md) pode achar que algumas invariantes não têm cobertura de implementação.
- **Sugestão**: Em cada tarefa adicionar parêntese `(verifies INV-XX-NN)` quando cabível, conforme já feito nas tarefas 3.5, 3.6, 4.4, 4.6.

### Problema 11 — Tarefa 7.3 cria ADR mas não menciona criar `docs/adr/`

- **Severidade**: **Baixa**
- **Categoria**: completude
- **Descrição**: `docs/adr/` não existe (`ls docs/adr/` retorna ENOENT). Tarefa 7.3 diz "Create ADR `docs/adr/0001-env-var-pattern.md`" mas não cria o diretório nem registra um padrão para ADRs futuros.
- **Evidência**: `ls docs/adr/ 2>&1` → "Arquivo ou diretório inexistente".
- **Sugestão**: Adicionar sub-tarefa 7.3a "Create `docs/adr/` directory + `docs/adr/README.md` documenting the ADR numbering convention" antes de 7.3.

### Problema 12 — Tarefa 7.5 ambígua sobre seção do architecture doc

- **Severidade**: **Baixa**
- **Categoria**: ambiguidade
- **Descrição**: Tarefa 7.5: "Update `docs/rv_android_architecture.md` Section 8 (or §9 NFR Support)". `or` denota indecisão.
- **Evidência**: `docs/rv_android_architecture.md:384` "## 8. Module Descriptions"; `:426` "## 9. NFR Support".
- **Sugestão**: Decidir antes do merge; conceptualmente Layer Purity é uma NFR (Maintainability NFR01), portanto §9 é a casa natural.

### Problema 13 — Dois compose files de teste estarão simultaneamente em backup e em modo "removed"

- **Severidade**: **Baixa**
- **Categoria**: P3 (No Backward Compat)
- **Descrição**: P3 exige uma commit = um estado consistente. Migrar 25 compose files num único commit junto com entrypoint refactor + AVD bump pode resultar em commit gigante. Tasks.md não enuncia se 5.4 e 6.x devem ser commits separados ou um único.
- **Evidência**: `tasks.md:52, 5.6, 6.5, 6.6` — todos sem orientação de commit boundary.
- **Sugestão**: Adicionar nota em design.md sobre boundary de commit ("each task group → one commit, all-tests-pass at boundary"). Ou abrir uma sub-tarefa explícita.

---

## 4. Análise por dimensão

### 4.1 CONSISTÊNCIA INTERNA — proposal vs specs vs design vs tasks

A consistência sintática é alta (mesmos IDs INV-XX, mesmos nomes de cenário, mesmas referências cruzadas). A consistência *semântica*, porém, tem 5 furos:

1. `tool_configs` vs `tools` (Problema 1) — 5 artefatos com nome de campo errado.
2. `ToolFactory` em rv-platform vs rv-tools (Problema 2) — `tasks.md:39` cita path inexistente.
3. "10 vs 13 constants" (Problema 9) — `proposal.md:17` divergente do resto.
4. "~12 compose files" vs 37 reais (Problema 3) — proposal.md:71 / tasks.md:52.
5. INV-CORE-31 lint string `os\.environ\.get` vs descrição "every `os.environ.get`/`os.environ[` reference" em tasks 2.1 — três versões circulando do mesmo padrão.

Os princípios e o desenho de alto nível são internamente coerentes. Os erros são de detalhamento.

### 4.2 COERÊNCIA COM PHASE 0 — alinhamento com docs/20260506_plano_env.md

A change segue Phase 0 com fidelidade alta:
- §6 Plano §6.1 lista exatas 13 constantes adicionadas; tasks 1.2 reproduz as 13 ipsis litteris.
- §6.4 Plano descreve entrypoint reduzido (~30 linhas, sem env→flag); design D2 recapitula com argumentos idênticos.
- §10 Plano fornece evidência empírica que proposal §27 referencia.
- §7 Plano enumera 8 grupos de critérios (A-H); proposal não contradiz nenhum, embora não os reproduza textualmente.

**Drift identificado**: Phase 0 §3.1 inventário diz "26+ env vars" mas omite `RV_PYDANTIC_STRICT/LOG`. A change herdou essa lacuna (Problema 4). Phase 0 §3.2 afirma "Demais L2/L3/L4 — OK (não lêem env)" — também falso (Problemas 6, 7, 8). A change herdou esses gaps de inventário.

Recomendação: re-rodar grep de auditoria mais amplo (`grep -rnE 'os\.environ\.|os\.getenv\(' modules/`) e atualizar Phase 0 antes de mergear.

### 4.3 AMBIGUIDADES — termos vagos, escopos imprecisos, "ou" sem decisão

- **"~12 compose files"** (proposal.md:71, tasks.md:52) — quantificador vago e numericamente errado (37 reais).
- **"all tool plugins, not just humanoid"** (tasks.md:43) — "similarly" sem enumerar arquivos. Tools afetados conhecidos: ape:278 (TOOLS_DIR), droidmate:113, fastbot:401 — não enumerados.
- **"Section 8 (or §9 NFR Support)"** (tasks.md:74) — ambiguidade pelo `or`.
- **"or running `python -c "..."` if the Python environment is already available — to be decided in implementation"** (design.md:212) — decisão postergada para implementação. Pode levar a duas implementações divergentes.
- **"`rvagent-tool` and `aperv-tool` ... need audit too"** (design.md:272 Open Questions) — não decide; vira tarefa difusa.

Cada ambiguidade pequena por si só é tolerável; o agregado erode a precisão prometida pelo princípio P2.

### 4.4 RASTREABILIDADE — todo INV/Requirement tem teste? toda task referencia spec?

**INV → Test**: A tabela `design.md:67-79` mapeia 9 invariantes para 9 testes (1:1). Todas as 9 invariantes têm um teste declarado. ✓

**INV → Task**: tasks.md cita por ID apenas INV-CORE-32 (3.5), INV-EXP-32 (3.6), INV-PLT-25 (4.4 e 4.6). As outras 6 (CORE-30, CORE-31, EXP-30, EXP-31, TOOL-20, TOOL-21) **não são citadas por ID** em nenhuma tarefa. Embora estejam *cobertas* pelas tarefas 1.2, 2.1, 4.2, 4.7, 4.9, 5.2 implicitamente, a falta de citação textual é um furo de rastreabilidade que viola a expectativa do auditor (§3.3 do prompt) — Problema 10.

**File:line → existence**:
- `humanoid/tool.py:89` (proposal §22, design D Mapping, tasks 4.2): existe ✓ — verificado.
- `config.py:745, :748` (tasks 3.1): existe ✓ — `sa_timeout` em :745, `jvm_memory` em :748.
- `humanoid/tool.py:13` (tasks 4.2): existe ✓ — `from rv_android_core.constants import ENV_HUMANOID_URL`.
- `scripts/run_emulator.sh:4` (tasks 6.3): existe ✓ — `EMULATOR_NAME="RVSec29"`.
- `Dockerfile` ARG `API_LEVEL=29 / ARCHITECTURE=x86`: existe ✓ — linhas 15, 17.
- `start-emulator.sh:76-87` (plano §3.4): existe ✓ — sem `-writable-system`.
- `rv-platform.tool.factory.ToolFactory.create()` (tasks 4.4): **NÃO existe** — Problema 2.
- `PlatformConfig.tool_configs` (5 referências): **NÃO existe** — Problema 1.

### 4.5 TESTABILIDADE — critérios de aceitação são executáveis?

A maioria dos cenários WHEN/THEN/AND tem valores concretos e exits codes específicos:
- "exit code 64" + nome de variável (experiment/spec.md:67-69) ✓
- `ExperimentConfig.analysis_timeout` MUST be `600` (experiment/spec.md:108-113) ✓
- "0 hits" em greps (core/spec.md:26, tools/spec.md:25) ✓

Áreas frágeis:
- "the message MUST point the developer at..." (`core/spec.md:51`) — testar texto da mensagem é flaky.
- "the message MAY suggest the replacement (`RV_SPEC_SET`) when a known mapping exists" (experiment/spec.md:75) — `MAY` torna não-testável; é UX nice-to-have.
- "running `grep ...` MUST return 0 hits" — esse grep tem buracos (Problema 5), portanto pode passar com violações reais.
- Smoke matrix gates H4 / n=100 (tasks 6.5, 6.6) — verificáveis mas custam horas; o plano cita ~5h paralelizado. Critérios qualitativos do tipo "0 regressões trend" deveriam fixar limiar (ex: ≤2% regressão).

### 4.6 SOUNDNESS — as inferências do relatório de Phase 0 sustentam as decisões?

**Empírica AVD**: n=80 sustenta tendência mas é estatisticamente modesto. O design reconhece (`design.md:248`) e cria gate H4 + sample n≥100 antes de merge — bom raciocínio.

**Refutação OverlayFS**: três linhas de evidência (start-emulator.sh sem flag; commit `c0274def`; boot smoke 6/6) convergem. Inferência sólida.

**Layer Purity claim**: tem 5 contraexemplos não endereçados (Problemas 6, 7, 8). A inferência "L2/L3/L4 não lêem env" foi derivada de um grep que ignora `os.getenv` e ignora aperv-tool/rvagent-tool — por isso o "soundness" é local: vale para os locais varridos, não para toda a base.

**Gain claim ("recovers ~17%")**: design.md:88 diz "API 30 x86_64 as the new default Docker AVD, recovering ~17% of modern APKs lost to ABI/SDK mismatches". 7/20 = 35% no dataset moderno; 7/40 = 17.5% global. A claim é defensável só se "modern APKs" = total combinado dos 2 datasets, o que não está explicitado. Risco de leitor confundir.

### 4.7 COMPLETUDE — algum cenário relevante foi esquecido?

Lacunas:
- **`bash`/`shell` shortcut no entrypoint**: cenário existe (experiment/spec.md:78) mas não testa que `RV_DELAY` é IGNORADO em modo interativo. Atualmente o entrypoint atual processa `RV_DELAY` antes de detectar `bash` — o novo deveria documentar.
- **Comportamento quando `RV_DELAY` é negativo ou não-numérico**: nenhum cenário.
- **Compose file usando var removida**: o cenário "Docker Entry Point Rejects Removed Variable" (experiment/spec.md:71) é um caso isolado — não cobre que **toda a frota de 25 compose files** quebra simultaneamente sem alerta CI prévio.
- **Tool sem `--analysis-timeout` flag, mas com `RV_SA_TIMEOUT` setado**: cenário existe (experiment/spec.md:115). Mas o caso simétrico "flag setada mas sem env" não tem cenário (apenas o caso default vs flag-only).
- **Pydantic `extra="forbid"` quando o input vem de JSON file de compose**: nenhum cenário cobrindo carregamento via `from_file` (`platform_config.py:138`) com extra fields.

### 4.8 ESCOPO — change é coesa (γ correto) ou deveria ser dividida?

A escolha γ (uma change consolidada) tem justificativa válida em D3: ambos os tópicos tocam `Dockerfile` e `docker-entrypoint.sh`; bundling reduz overhead de revisão. Discordo parcialmente: bundling cria uma **change de ~30 arquivos** que aumenta para ~80+ se incluirmos os 25 compose files reais que precisam ser atualizados.

Sugestão alternativa: γ **interno** (mesma issue, mesma branch) mas dividida em **commits sequenciais** por task group. tasks.md já ordena 1→8; basta adicionar boundaries de commit explícitas (Problema 13).

A change é coesa funcionalmente (env vars + AVD) mas frágil para revisão linha-a-linha em PR único. Recomendo manter γ na issue e expandir tasks.md para enumerar commits.

### 4.9 RISCOS — cada decisão técnica tem mitigação? gates obrigatórios estão claros?

Riscos cobertos com mitigação (`design.md:243-250`): 6 itens (compose externo, image rebuild, ape API 30, extra="forbid" rejeitando snapshots, lint complexity, n=80 modesto). Cada um com mitigação concreta.

**Riscos não mitigados** (vide §8):
- Boot Docker vs host (plano §10.6.e flagou; design.md não nomeia mitigação além de "validar boot em Docker antes de produção" — sem teste planejado).
- 25 compose files com `RV_JCA_SPEC=true` (Problema 3) — sem mitigação.
- `aperv-tool`/`rvagent-tool` env reads (Problema 6) — sem mitigação.
- `dexlib2:525 dict(os.environ)` (Problema 7) — sem mitigação nem reconhecimento.
- TOOLS_DIR como exceção L1 não declarada (Problema 8) — sem mitigação.

Gates H4 (smoke matrix tools) e n=100 ressample são citados explicitamente em proposal §32, design.md:248, tasks 6.5/6.6 — cumpre o checklist da §3.4 do prompt. ✓

### 4.10 PRINCÍPIOS — P1/P4 violations explícitas ou veladas?

**P1 (Simplicidade)**: A proposta reduz entrypoint de 150 → 30 linhas (D2). Boa simplificação. Bem.

**P2 (Documentação narrativa)**: As Purpose sections em todos os specs são parágrafos longos com *por quê*. ✓

**P3 (Sem Backward Compat)**: Cumprido em macro (sem aliases, sem warnings). Subdimensionamento de compose files (Problema 3) **rompe P3 na prática**: deixar 25 arquivos quebrados após o merge é um shim implícito ("o usuário descobre quando rodar"). P3 *forte* exige todos atualizados na mesma change.

**P4 (Comentários presente)**: Tarefa 6.2 menciona "rewrite the gh50 §17 historical comment block per P4" — bom. Mas o `Dockerfile` atual também tem narrativa histórica em comentário (`commit 07179eb6`, "trade-off: lose 19/400 APKs"); reescrever só o bloco da tarefa pode deixar resíduo. Recomendo grep amplo "rolled back\|gh50 §17\|historical" no momento da implementação.

### 4.11 BREAKING CHANGES — todas listadas? impacto em compose files claro?

Lista no proposal §82-84:
- 4 vars removidas (`RV_MEMORY_FILE`, `RV_RVANDROID_URL`, `RV_SKIP_EXPERIMENT`, `RV_JCA_SPEC`).
- Image label muda → rebuild necessário.
- entrypoint não traduz mais env→flag.

**Não listado** mas é breaking:
- `extra="forbid"` em `ExperimentConfig` rejeita JSON files antigos com campos extras.
- `RV_PYDANTIC_STRICT`/`LOG` não estão no allow-list → exit 64 silencioso (Problema 4).
- `RV_HUMANOID_URL` antes funcionava como fallback em humanoid/tool.py:89 — depois falha com KeyError se L5 não propagar (cenário tools/spec.md:47-51 cobre, mas o **migration note** falta).

Sugestão: Adicionar em proposal §82 um item por breaking change não óbvio.

### 4.12 INFRAESTRUTURA DE LINT — drift checker é robusto? cobre todos os casos?

Cobertura prometida do `scripts/check_env_vars_drift.py` (tasks 2.1):
- (a) `os.environ.get/os.environ[` referencia `ENV_*` symbol.
- (b) RV_* em README/`.env.example` está no registry.
- (c) `ENV_*` constant tem entry em README/`.env.example`.

Cobertura real:
- (a) **omite `os.getenv`** (Problema 5) — 3 falsos negativos hoje.
- (b) e (c) dependem de README ainda inexistente em tasks 7.2 — `.env.example` em 7.1; ordem está OK.

Robustez:
- Allow-list explícita para 3 exceções L1 mencionada em design.md:249 — bom.
- Mas não há **teste integration** que falhe se as 3 exceções forem violadas (tasks 2.2 só tem "planted-violation fixture" genérica).
- Não há lint para `dict(os.environ)`, `os.environ.copy()`, ou `subprocess.run(env={**os.environ, ...})` — formas indiretas de leakage.

Sugestão: Adicionar tarefa 2.2-bis "Test that lint catches `os.getenv("RV_X")`, `os.environ["RV_X"]`, e `dict(os.environ)`".

---

## 5. Riscos + mitigação

| Risco | Probabilidade | Impacto | Mitigação proposta | Já contemplado? |
|-------|---------------|---------|---------------------|-----------------|
| 25 compose files com `RV_JCA_SPEC=true` quebram após merge | Alta | Alto | Audit + replace antes do PR; smoke matrix de 5+ compose files | Parcial (P1) |
| `RV_PYDANTIC_STRICT/LOG` viram exit-64 silencioso | Média | Médio | Adicionar ao registry OU remover OU listar como exceção L1 | Não |
| `aperv-tool`/`rvagent-tool` continuam lendo env L2 | Alta | Médio | Ampliar scope INV-TOOL-20; auditar 3+ files concretos | Não |
| `dict(os.environ)` em dexlib2:525 mascara violations | Média | Médio | Eliminar ou justificar (subprocess env) | Não |
| Compose count "~12" subestimado leva a esforço errado | Alta | Médio | Trocar para 37; enumerar arquivos afetados | Não |
| Lint INV-CORE-31 falha em capturar `os.getenv` | Alta | Médio | Padronizar grep com 3 formas | Não |
| ToolFactory `create()` não existe (real: `create_tool`) | Alta | Baixo | Corrigir caminhos em tasks.md/design.md | Não |
| INV-PLT-25 nomeada errado (vive em rv-tools) | Alta | Baixo | Renomear para INV-TOOL-25 | Não |
| `tools` vs `tool_configs` campo errado | Alta | Médio | Decidir rename ou correção dos artefatos | Não |
| Boot Docker não validado (só host) | Média | Alto | Adicionar tarefa 6.4-bis "boot smoke em Docker container" | Parcial (texto em §10.6.e) |
| `extra="forbid"` rejeita configs JSON antigos | Baixa | Médio | Listar como breaking + grep configs em uso | Parcial (`design.md:248`) |

---

## 6. Auditoria de critérios de aceitação

Avaliação dos 8 grupos da §7 do plano (e proposal/design correspondentes):

### A — Inventário e Doc Truth
- **A1** "tabela com N=25 entradas": **Verificável** (count linhas). **Determinístico**. Sugestão: corrigir N para 27 se RV_PYDANTIC_STRICT/LOG forem incluídos.
- **A2** colunas `Name, CLI Flag, Default, Read By, Description`: **Verificável** parcialmente (regex de cabeçalhos). **Determinístico** se schema fixo. Pode adicionar JSON schema canônico.
- **A3** lint `check_env_vars_drift.py`: **Parcial** (Problema 5). **Determinístico** se padrão for completo.
- **A4** CLAUDE.md cita ADR: **Verificável** (grep). **Determinístico**.

### B — Dead Code Cleanup
- **B1** 4 constantes removidas: **Verificável** (`grep -c "ENV_MEMORY_FILE\|..." constants.py` = 0). **Determinístico**.
- **B2** 0 hits em todo o repo: **Verificável**. **Determinístico**. ✓
- **B3** backups em `backup/2026-05-06_env_var_cleanup/`: **Verificável** (existência de arquivo). **Determinístico**.

### C — Centralização via `ENV_*`
- **C1** 25 ENV_* constantes: **Verificável**. **Determinístico**. (A renumerar se RV_PYDANTIC_STRICT/LOG entrar.)
- **C2** "Todo código usa constante" — **Subjetivo** se "todo código" inclui tests/scripts. Plano §7-C2 não fixa scope.
- **C3+C4** greps: **Verificável** mas **incompleto** (Problema 5 — falta `os.getenv`). **Determinístico** após correção.

### D — Flags Faltantes
- **D1, D2** flags adicionadas: **Verificável** (`--help` output ou inspeção argparse). **Determinístico**.
- **D3** "3 modos × 2 flags = 6 cenários": **Verificável**. **Determinístico**. tasks 3.6 cobre.

### E — Layer Purity
- **E1** "Apenas L5+L1-exc leem": **Verificável via lint** (com Problema 5/6 corrigidos). **Determinístico** após correção.
- **E2** L2/L3/L4 não leem RV_*: **Verificável**. **Determinístico**. **Mas hoje tem violações** (Problemas 6, 7).
- **E3** rv-static-analysis exceção temporária: **Subjetivo** ("exceção temporária"). Plano não fixa quando expira. Sugestão: data de fim ou issue aberta tracking.
- **E4** `RV_HUMANOID_URL` migrada: **Verificável** (`grep ENV_HUMANOID_URL modules/rv-tools/` → 0). **Determinístico**.

### F — Validação Strict
- **F1** entrypoint exit 64: **Verificável** via integration test. **Determinístico**.
- **F2** Pydantic `extra="forbid"`: **Verificável** via unit test. **Determinístico**.
- **F3** E2E test: **Verificável**. **Determinístico**.
- **F4** unit test: **Verificável**. **Determinístico**.

### G — Sem Backward Compat (P3)
- **G1** "todos ~12 compose files updated": **Verificável** (grep) **mas number errado** (37). **Determinístico** após renumeração.
- **G2** entrypoint antigo em backup: **Verificável**. **Determinístico**.
- **G3** "Nenhum alias/warning/legacy/_old": **Verificável** via grep. **Determinístico**.
- **G4** "Uma commit = um estado consistente": **Subjetivo**. Sugestão: definir explicitamente que ao final de cada task group todos os tests passam.

### H — Documentação Canônica
- **H1** `.env.example` com 25 vars: **Verificável**. **Determinístico**.
- **H2** ADR `0001-env-var-pattern.md`: **Verificável** (existência). **Determinístico**.
- **H3** seção "Adicionando uma nova env var": **Verificável** (grep cabeçalho). **Determinístico**.

**Veredito agregado**: 30/35 critérios são determinísticos e verificáveis com correções menores; 4/35 são subjetivos (C2, E3, G4, "tabela com N entradas" se N flutuar); 1/35 está incorreto na lista (compose count). Após aplicar as correções dos Problemas 1-13, todos os 35 ficam executáveis.

---

## 7. Sugestões de melhoria

Ordenadas por prioridade (CRÍTICA → BAIXA):

1. **CRÍTICA — Corrigir nome de campo** `tool_configs` → `tools` em `PlatformConfig`, OR adicionar tarefa de rename. **Onde**: `proposal.md:21,89`; `design.md:30,60,183-185,227-228`; `platform/spec.md:12,25,40,52`; `tasks.md:38,41`. **Por quê**: Spec e design referenciam um campo inexistente — INV-PLT-25 nominalmente verificável, na prática falsa.

2. **CRÍTICA — Corrigir caminho `ToolFactory`**. **Onde**: `tasks.md:39` ("rv-platform.tool.factory" → `rv_tools.registry.factory`); `design.md:60,77,190` (todas as menções). Método: `create_tool` (não `create`). **Por quê**: Tarefa 4.4/4.6 atinge módulo errado se seguida literalmente.

3. **CRÍTICA — Renomear INV-PLT-25 para INV-TOOL-25**. **Onde**: `platform/spec.md:25`, design `:77`. **Por quê**: ToolFactory vive em rv-tools (L2), não rv-platform (L4); o ID atual implica camada errada.

4. **CRÍTICA — Auditar 37 compose files (não ~12)** e enumerar os 25 com `RV_JCA_SPEC=true` no escopo da task 5.4. **Onde**: `proposal.md:31,71`; `tasks.md:52`; `design.md` "Risks". **Por quê**: P3 promete consistência atomic; sem auditoria, 25 compose files quebram silenciosamente no merge.

5. **CRÍTICA — Decidir destino de `RV_PYDANTIC_STRICT` e `RV_PYDANTIC_LOG`**. **Onde**: `proposal.md` impact table; `tasks.md` 1.2 ou 1.3; `docs/20260506_plano_env.md` §3.1 inventário. **Por quê**: Inventário incompleto viola INV-CORE-30 desde criação.

6. **ALTA — Padronizar lint para `os.environ.get` + `os.environ[` + `os.getenv`**. **Onde**: `core/spec.md:26`; `tasks.md:18`; teste `tests/lint/test_env_vars_drift.py` planted-violation. **Por quê**: 3 ocorrências reais hoje invisíveis ao grep proposto.

7. **ALTA — Ampliar scope INV-TOOL-20 para `aperv-tool` e `rvagent-tool`**. **Onde**: `tools/spec.md:25` (regex scope); `tasks.md:43,44`. **Por quê**: 3 violações conhecidas em `aperv-tool/.../tool.py:329,352,355`; scope atual não captura.

8. **ALTA — Endereçar `dexlib_instrumentation.py:525 dict(os.environ)` e literais `RVSEC_HOME`**. **Onde**: nova tarefa em `tasks.md` §3 ou §4. **Por quê**: 3 violações de Layer Purity em rv-instrumentation persistem após change e mascaram drift.

9. **ALTA — Decidir tratamento de `TOOLS_DIR`**. **Onde**: design D7 ou novo D8; mention em `core/spec.md` exceções. **Por quê**: 5 leituras reais não cobertas pela INV-EXP-30 (não é RV_*) nem pelas 3 exceções L1.

10. **MÉDIA — Reconciliar "10 vs 13 constantes"**. **Onde**: `proposal.md:17`. **Por quê**: Inconsistência interna leitura-confundente.

11. **MÉDIA — Citar invariantes por ID em cada task aplicável**. **Onde**: `tasks.md` 1.2 → INV-CORE-30; 2.1 → INV-CORE-31, INV-EXP-30; 4.7 → INV-TOOL-20; 4.5 → INV-TOOL-21; 5.2/5.3 → INV-EXP-31. **Por quê**: Rastreabilidade auditável sem cruzar com design.md.

12. **MÉDIA — Adicionar boot smoke em Docker container** (não só host). **Onde**: nova sub-tarefa 6.4-bis. **Por quê**: §10.6.e plano explicita risco; design.md o reconhece mas não testa.

13. **BAIXA — Criar `docs/adr/` com README de convenção** antes da tarefa 7.3. **Onde**: nova sub-tarefa 7.3a.

14. **BAIXA — Resolver "Section 8 or §9"** em tasks 7.5 — fixar §9 NFR Support.

15. **BAIXA — Definir boundaries de commit explícitas**. **Onde**: nota em `design.md` "Implementation Strategy" antes de "Open Questions". **Por quê**: G4 "uma commit = estado consistente" hoje é claim sem operacionalização.

---

## 8. Riscos NÃO mitigados / open questions

- **Boot Docker em hardware de produção** com nova imagem — testado só em host. §10.6.e do plano flagou; design.md §11 reconhece mas não testa.
- **`RV_PYDANTIC` no allow-list do entrypoint** — `RV_PYDANTIC` é exceção L1-cross-layer reconhecida, mas se o usuário setar via `docker run -e RV_PYDANTIC=true`, o entrypoint validate_env_vars.sh deve aceitá-la. Tasks 5.2 não enuncia que as 3 exceções L1 estão no allow-list — só fala em "ENV_*" derivado de constants.py.
- **Crash do humanoid container quando `tool_configs` falta `humanoid_url`**: novo cenário tools/spec.md:47-51 manda tool falhar com KeyError. Mas a UX para o operador (mensagem clara, dica de como passar via CLI) não é spec'd.
- **Cumulative coverage da migração**: `aperv-tool` audit (Problema 6) seria uma 2ª change, ou parte desta? design.md:272 deixa em "open questions" — sem decisão.
- **Decisão sobre `extra="forbid"` em modelos não-top-level**: D7 explicitamente decide aplicar só em top-level. Não há teste/lint que detecte se algum dev inadvertidamente aplicar em modelo intermediário.
- **Compatibilidade reversa para `phtcosta/rvandroid:0.8.0` taggeado**: usuários puxando latest após merge ganham API 30 sem aviso. Não há changelog visível ao docker pull.
- **O que acontece se `--analysis-timeout 0` é passado**: cenário sem cobertura. Click `type=int` aceita 0; `RVStaticAnalysisConfig` provavelmente quebra.
- **Backwards-removal trail**: Phase 0 plano §8 task group 1 promete "grep removendo qualquer referência residual" — mas grep over `docs/`, `backup/`, `.hypothesis/` pode achar muitas referências históricas que não são "residuais". Falta critério de inclusão/exclusão.

---

## 9. Aprovação condicional

A change passará para **APROVADA** se aplicadas, no mínimo:

1. **Corrigir Problema 1**: Decidir entre rename `tools` → `tool_configs` em PlatformConfig OU corrigir todos os 5 artefatos para `PlatformConfig.tools`. Atualizar specs, design.md, tasks.md, proposal.md.
2. **Corrigir Problema 2 + 3**: Atualizar caminho de `ToolFactory` para `rv_tools.registry.factory.ToolFactory.create_tool(tool_config)` em design.md:60,77,190 e tasks.md:39. Renomear INV-PLT-25 → INV-TOOL-25 em platform/spec.md e design.md mapping table.
3. **Corrigir Problema 3**: Substituir "~12 compose files" por contagem real (37) em proposal.md e tasks.md. Adicionar tarefa explícita 5.4-bis enumerando os 25 compose files com `RV_JCA_SPEC=true` que precisam migrar para `RV_SPEC_SET`. Ampliar smoke matrix de 3 → ≥5 compose files representativos.
4. **Corrigir Problema 4**: Decidir e documentar destino de `RV_PYDANTIC_STRICT` e `RV_PYDANTIC_LOG` (adicionar ao registry / remover / declarar exceção L1). Atualizar inventário em plano §3.1, lista de constantes em proposal §17 e tasks 1.2.
5. **Corrigir Problema 5**: Padronizar lint pattern para 3 formas (`os.environ.get("RV_`, `os.environ["RV_`, `os.getenv("RV_`) em core/spec.md:26, tasks 2.1, e teste 2.2.
6. **Corrigir Problema 6**: Ampliar scope INV-TOOL-20 e tarefa 4.8 para incluir `modules/aperv-tool/` e `modules/rvagent-tool/`. Enumerar concretamente as 3 leituras em `aperv-tool/tool.py:329,352,355` para migração.
7. **Corrigir Problema 7**: Adicionar tarefa endereçando `dexlib_instrumentation.py:525 dict(os.environ)` (eliminar ou justificar) e os 2 literais `"RVSEC_HOME"` em `ajc_instrumentation.py:419` e `dexlib_instrumentation.py:592` (substituir por `ENV_RVSEC_HOME`).
8. **Corrigir Problema 8**: Decidir tratamento de `TOOLS_DIR` em D7/D8 ou novo open question com decisão (não "open"); listar entre as exceções L1 em proposal §20 se for o caso.
9. **Corrigir Problema 9**: `proposal.md:17` "10" → "13".
10. **Corrigir Problema 10**: Citar IDs de invariantes nas tarefas relevantes de tasks.md (lista no Sugestão #11).

Os Problemas 11-13 (severidade Baixa) não são bloqueadores mas reduzem fricção operacional se tratados na mesma rodada.

Após essas 10 correções, a change está alinhada com Phase 0, com os princípios P1-P4, com o esquema rv-sdd, e com a base de código real — recomendaria aprovação para implementação.

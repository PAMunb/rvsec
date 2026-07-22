# Proposal: Consolidação Pós gh50/gh51/gh52

**GitHub Issue**: #53
**Schema**: rv-sdd (Full SDD)
**Phase 0 (ideação)**: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260428_plano_consolidacao_pos_gh50_gh51_gh52.md`
**ADR**: `ADR-INSTRUMENTER-ABC.md` (mesmo diretório)

## Why

As changes gh50 (resiliência ajc/d8), gh51 (Soot 4.7.1) e gh52 (pipeline DEX-native dexlib2) já estão todas commitadas em `modules` (gh52 mergeado via `fd8b503c`), mas a branch carrega débito técnico cruzado que precisa ser resolvido **antes** de poder gerar uma imagem Docker `phtcosta/rvandroid:0.8.0` adequada para rodar as validações experimentais finais (Phase 5 gh52, safety gate gh50, reexecução 400-APK).

Especificamente:

1. **Não há imagem única adequada para validações**. Hoje a tag `phtcosta/rvandroid:0.8.0` precede gh52, e o variant dexlib2 só existe em uma tag temporária `phtcosta/rvandroid:0.8.0-dexlib2` construída via `--build-arg RVSEC_BRANCH=gh52-instr-dexlib2` em `docker/rvandroid_dexlib2/Dockerfile`. As validações precisam de **uma imagem única** carregando simultaneamente: gh51 (Soot 4.7.1), gh50 (resiliências ajc/d8) e gh52 (variant dexlib2 disponível via flag).

2. **Pinos Docker temporários acumulam dívida**. As tags `0.8.0-dexlib2`, `0.8.0-dexlib2-base`, o build-arg override `RVSEC_BRANCH=gh52-instr-dexlib2` e o `docker/rvandroid_dexlib2/Dockerfile` (53 linhas) existem porque a integração foi feita em duas etapas — quando gh52 ainda estava em branch separada. Após o merge, são redundantes (a imagem `0.8.0` rebuildada de `modules` já contém o módulo dexlib2 e Maven auto-copia o jar via Design D9).

3. **Acoplamento `dexlib2 → ajc` em tipos compartilhados**. `DexlibInstrumentation` importa `InstrumentationResults` e `InstrumentationError` de `rv_instrumentation.config` (módulo ajc atual) em `dexlib_instrumentation.py:11-14` (top-level) e `:122-125` (escopo local em `instrument_apks`). Direção errada: o módulo "novo" depende do "legado" para tipos que são contrato compartilhado. Mesma situação ocorre com o **keystore** (`modules/rv-instrumentation/assets/keystore.jks`) — usado por ambos variants para assinar APKs (`apksigner` no dexlib2, `jarsigner` no ajc), mas vive no módulo ajc por inércia histórica (`rv-experiment/config.py:661-692` aponta o `keystore_file` do dexlib2 para esse path).

4. **Coexistência ajc/dexlib2 implementada de forma não-canônica**. O dispatch hoje é `if/else` em `rv-experiment/.../pre_processor.py:188-207`, importando `RVInstrumentation` ou `DexlibInstrumentation` diretamente. Não há contrato público compartilhado entre as duas implementações — cada novo consumidor precisa replicar a lógica de seleção. Pattern inconsistente com o resto do projeto, onde domínios cross-implementação têm contrato via ABC + factory (ex: `AbstractTool` em `rv-android-core/src/rv_android_core/tools/abstract_tool.py`).

5. **Tarefa gh52 15.4 deferida**. `openspec/changes/gh52-instr-dexlib2/tasks.md:207`:
   > "15.4 Update `rv-android/CLAUDE.md` to mention dexlib2 variant — DEFERRED; CLAUDE.md can be updated after Phase 5 once the variant is the default."

   gh53 destrava ao documentar a **arquitetura** sem antecipar o **flip de default** (esse continua aguardando Phase 5 gh52).

6. **Cleanup operacional pendente**. 22 arquivos `ajcore.20260421.*.txt` no repo root (crash dumps AspectJ da validação JCA-557 do gh50) precisam ser gitignorados e removidos.

**Esta change não executa as validações experimentais e não arquiva as changes gh50/gh51/gh52.** Archives são consequência das validações posteriores.

## Decisão arquitetural — 4 módulos para resolver dependência circular

Phase 0 §3.1 escolheu Option A: parent canônico em `rv-instrumentation` com ABC + factory + tipos compartilhados, `rv-instrumentation-ajc` renomeado a partir do impl ajc atual, `rv-instrumentation-dexlib2` existente.

**Refinamento crítico identificado durante design**: se o parent `rv-instrumentation` declara o `Instrumenter` ABC + tipos compartilhados E a factory que dispatcha para `-ajc` e `-dexlib2`, há **dependência circular**:

- `rv-instrumentation-ajc/pyproject.toml` declara dep em `rv-instrumentation` (precisa importar `Instrumenter` ABC + tipos)
- `rv-instrumentation/pyproject.toml` precisaria declarar dep em `rv-instrumentation-ajc` (factory importa `AjcInstrumentation`)
- → **ciclo direto** que `uv workspace` recusa ou resolve mal

Workaround com lazy import sem declarar dep no `pyproject.toml` do parent funciona em runtime mas é **dependência implícita não-declarada** (anti-padrão): testes do factory no parent quebram, consumidores em isolamento descobrem `ImportError` em runtime, futuros contribuidores não veem a dep.

**Solução**: separar abstrações puras (sem deps em impls) em módulo dedicado `rv-instrumentation-core`. Quatro módulos:

```
modules/
├── rv-instrumentation-core/             # NOVO — abstrações puras (types + ABC)
│                                        # deps: pydantic, rv-android-core (NÃO impls)
├── rv-instrumentation/                  # PARENT — factory + shared keystore
│                                        # deps: rv-instrumentation-core, -ajc, -dexlib2
├── rv-instrumentation-ajc/              # RENOMEADO de rv-instrumentation impl
│                                        # deps: rv-instrumentation-core (NÃO parent)
└── rv-instrumentation-dexlib2/          # EXISTENTE
                                         # deps: rv-instrumentation-core (NÃO parent)
```

Grafo de dependências (sem ciclo):
```
rv-android-core
       ↑
rv-instrumentation-core  ←  rv-instrumentation-ajc
       ↑                 ←  rv-instrumentation-dexlib2
       ↑
rv-instrumentation (parent — factory) → ajc, dexlib2
       ↑
rv-experiment (consumer)
```

Cada módulo declara honestamente o que importa. Sem truques.

**API pública canônica permanece estável**:

```python
from rv_instrumentation import (
    Instrumenter,           # re-exportado de -core
    InstrumentationResults, # re-exportado de -core
    InstrumentationError,   # re-exportado de -core
    get_instrumenter,       # vive no parent
)
```

Consumidor importa de `rv_instrumentation` indiferente de onde os símbolos vivem fisicamente. `-core` é detalhe interno que resolve a topologia de dependências.

ADR `ADR-INSTRUMENTER-ABC.md` documenta o trade-off com alternativas consideradas (Option B sem `-core`, Option C com Protocol em vez de ABC).

**gh52 task §17.2** (rename `rv-instrumentation-dexlib2` → `rv-instrumentation` quando default flipar) continua em conflito com o nome `rv-instrumentation` ocupado pelo parent. Não é responsabilidade de gh53 antecipar gh52 Phase 6.

## What Changes

### Estrutura de módulos (4 módulos)

Estado atual (2 módulos):
```
modules/rv-instrumentation/             # ajc impl + tipos compartilhados + keystore + weaving_excludes
modules/rv-instrumentation-dexlib2/     # dexlib2 impl, importa tipos de rv_instrumentation.config
```

Estado final (4 módulos):
```
modules/rv-instrumentation-core/        # NOVO — abstrações puras
│   src/rv_instrumentation_core/
│       __init__.py                     # re-exporta tudo
│       results.py                      # InstrumentationResults + InstrumentationError
│       instrumenter.py                 # ABC Instrumenter (sole @abstractmethod: instrument_apks)
│
modules/rv-instrumentation/             # PARENT — factory + shared assets (NOVO papel)
│   src/rv_instrumentation/
│       __init__.py                     # re-exporta de -core + expõe factory
│       factory.py                      # get_instrumenter(variant, config) -> Instrumenter
│   assets/
│       keystore.jks                    # SHARED (apksigner + jarsigner)
│
modules/rv-instrumentation-ajc/         # RENOMEADO de rv-instrumentation impl
│   src/rv_instrumentation_ajc/
│       __init__.py
│       __main__.py                     # CLI ajc (renomeado entry point)
│       ajc_instrumentation.py          # AjcInstrumentation(Instrumenter) — era RVInstrumentation
│       config.py                       # AjcInstrumentationConfig — era RVInstrumentationConfig
│   assets/
│       weaving_excludes.yaml           # AJC-ESPECÍFICO
│
modules/rv-instrumentation-dexlib2/     # EXISTENTE
    src/rv_instrumentation_dexlib2/
        dexlib_instrumentation.py       # DexlibInstrumentation(Instrumenter)
                                        # imports ABC + types de rv_instrumentation_core
```

### `rv-instrumentation-core` — escopo mínimo

```python
# modules/rv-instrumentation-core/src/rv_instrumentation_core/instrumenter.py
from abc import ABC, abstractmethod
from typing import List, Optional

from rv_instrumentation_core.results import InstrumentationResults


class Instrumenter(ABC):
    """Contract every instrumentation variant MUST satisfy."""

    @abstractmethod
    def instrument_apks(
        self,
        apks_dir,
        results_dir,
        force_instrumentation: bool = False,
        apk_paths: Optional[List[str]] = None,
    ) -> InstrumentationResults:
        ...
```

`pyproject.toml` deps: `pydantic` + `rv-android-core`. **Não** depende de nenhum impl.

### `rv-instrumentation` parent — factory + re-exports

```python
# modules/rv-instrumentation/src/rv_instrumentation/__init__.py
from rv_instrumentation_core import (
    Instrumenter,
    InstrumentationResults,
    InstrumentationError,
)
from rv_instrumentation.factory import get_instrumenter

__all__ = [
    "Instrumenter",
    "InstrumentationResults",
    "InstrumentationError",
    "get_instrumenter",
]
```

```python
# modules/rv-instrumentation/src/rv_instrumentation/factory.py
from rv_instrumentation_core import Instrumenter


def get_instrumenter(variant: str, config) -> Instrumenter:
    if variant == "ajc":
        from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation
        return AjcInstrumentation(config)
    if variant == "dexlib2":
        from rv_instrumentation_dexlib2 import DexlibInstrumentation
        return DexlibInstrumentation(config)
    raise ValueError(
        f"unknown instrumentation_variant {variant!r}; valid: 'ajc', 'dexlib2'"
    )
```

`pyproject.toml` deps: `rv-instrumentation-core`, `rv-instrumentation-ajc`, `rv-instrumentation-dexlib2`. Lazy imports na factory mantêm scenarios onde só uma variant está disponível em runtime (cada branch só importa quando chamada).

`assets/keystore.jks` permanece — shared resource.

### Migração de tipos compartilhados (P3 — atômico, sem aliases)

`InstrumentationResults` (atualmente `modules/rv-instrumentation/src/rv_instrumentation/config.py:127`) e `InstrumentationError` (em `config.py:102`) **movem** para `modules/rv-instrumentation-core/src/rv_instrumentation_core/results.py`. Bytes copiados intactos preservando `Field(default="ajc")` em `variant`.

`config.py` original (sem essas classes) é renomeado e movido para `modules/rv-instrumentation-ajc/src/rv_instrumentation_ajc/config.py` com `RVInstrumentationConfig` → `AjcInstrumentationConfig`.

### Atualização de consumidores

**Imports** (4 arquivos):

- `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py:188-207` — substitui `if/else` por `instrumenter = get_instrumenter(variant, instr_config)`. Add `from rv_instrumentation import get_instrumenter`.
- `modules/rv-experiment/src/rv_experiment/config.py:33-34` — atualiza imports. Realidade verificada (2026-05-01): linha 33 importa `from rv_instrumentation.config import ConfigurationError as InstrumentationConfigError`; linha 34 importa `RVInstrumentationConfig`. Pós-rename: ambos passam para `from rv_instrumentation_ajc.config import ...` (`ConfigurationError` re-exportado de `rv_android_core.util.error.exceptions` via `rv_instrumentation_ajc.config`; `RVInstrumentationConfig` → `AjcInstrumentationConfig`).
- `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py:11-14` e `:122-125` — `from rv_instrumentation.config import ...` → `from rv_instrumentation_core import (InstrumentationError, InstrumentationResults)`. Add herança `class DexlibInstrumentation(Instrumenter)`.
- `scripts/validation/fase_a_preprocess.py:98, 148` — `from rv_instrumentation import RVInstrumentation` → `from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation` (precisa dos métodos ajc-específicos `prepare_instrumentation(results_dir)`, `check_if_instrumented`).

**Mocks** (1 arquivo): `modules/rv-experiment/tests/test_pre_processor_variant.py` — `patch("rv_instrumentation.RVInstrumentation")` → `patch("rv_experiment.experiment.workflow.pre_processor.get_instrumenter")`.

**Path keystore** (`rv-experiment/config.py:669`): inalterado — `modules/rv-instrumentation/assets/keystore.jks` continua válido (parent canônico mantém o asset compartilhado).

**Path weaving_excludes** (`scripts/jca557_quarantine_impact.py:14, 44`): muda de `modules/rv-instrumentation/assets/weaving_excludes.yaml` para `modules/rv-instrumentation-ajc/assets/weaving_excludes.yaml` (asset AspectJ-específico vai junto com ajc).

### Flag e default preservados

`--instrumentation-variant ajc|dexlib2` (`rv-experiment/__main__.py:340`) e env `RV_INSTRUMENTATION_VARIANT` (`docker/rvandroid/docker-entrypoint.sh:97-103`) continuam ativos. Default `ajc`. Mudança do default fica para change posterior.

### Reversão de pinos Docker temporários

- **Deletar** `docker/rvandroid_dexlib2/Dockerfile` + diretório vazio
- **Reescrever** `docker/docker-compose.dexlib2-validation.template.yml` para `phtcosta/rvandroid:0.8.0` em ambos serviços com `RV_INSTRUMENTATION_VARIANT` distinto
- **Verificar** `docker/docker-compose.jca400-aperv.yml` — confirmado no-op (não referencia `0.8.0-dexlib2*`)
- **Manter** `ARG RVSEC_BRANCH=modules` em `docker/rvandroid/Dockerfile`
- **Atualizar** comentário-exemplo em `docker/rvandroid/Dockerfile:8-9` (P4)
- **Adicionar gate** no `docker/rvandroid/Dockerfile`: `RUN test -f /opt/rvsec/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar`
- **Versão da imagem permanece `0.8.0`**
- **Rebuild local** + 1-APK por variant smoke

### Cleanup operacional

- Remover 22× `ajcore.20260421.*.txt` do repo root
- Adicionar `ajcore.*.txt` ao `.gitignore`

### Atualização de documentação

- `CLAUDE.md` (root) — §System Modules adicionar `rv-instrumentation-core` E `rv-instrumentation-ajc`; §Module Dependencies refletir o grafo (parent ← `-core`, `-ajc`, `-dexlib2`; `-ajc` e `-dexlib2` ← `-core`)
- `README.md` (root) — tabela de módulos. **Canonical count post-change = 16 production modules** (excluindo `aperv-llm-validation` per memory). PRD `docs/PRD.md:127` dizia "14 uv workspace modules" pré-change; pós-change são 16 (+`-core` +`-ajc`)
- `openspec/config.yaml:8` — context "14 uv workspace modules" → "16 uv workspace modules"
- `modules/rv-instrumentation-core/CLAUDE.md` — criar (~25 linhas; pure abstractions module)
- `modules/rv-instrumentation/CLAUDE.md` — recriar (parent canonical: factory + re-exports + shared keystore)
- `modules/rv-instrumentation-ajc/CLAUDE.md` — criar (mover/adaptar conteúdo do CLAUDE.md ajc atual)
- `modules/rv-instrumentation-dexlib2/CLAUDE.md` — criar (não existe hoje)
- `modules/rv-experiment/CLAUDE.md` — atualizar §"Three-Phase Workflow" mencionando `get_instrumenter()` e `Instrumenter` ABC; mencionar fechamento de gh52 §15.4
- `modules/rv-instrumentation/docs/architecture.md` — recriar focado em parent (factory + assets)
- `modules/rv-instrumentation-ajc/docs/architecture.md` — migrar do antigo `rv-instrumentation/docs/architecture.md` (689 linhas)
- `modules/rv-instrumentation-core/docs/architecture.md` — criar mínimo (~30 linhas)

### Reconciliação de specs autoritativas — fora do escopo

`openspec/specs/instrumentation/spec.md` e `openspec/specs/experiment/spec.md` ainda descrevem o estado pré-gh50/gh52. gh53 **não toca** essas specs, apenas registra delta em `openspec/changes/gh53-consolidacao-instrumentation/specs/instrumentation/spec.md`. Reconciliação via `/opsx:sync` quando todas as changes (gh50, gh51, gh52, gh53) forem arquivadas.

### Dívida herdada gh52 INV-INS-55 — fora do escopo (supersession explícita)

A spec gh52 INV-INS-55 textualmente exige (a) `variant` required (sem default) E (b) `model_validator(mode="before")` em `InstrumentationResults` para retrocompat de JSONs antigos sem `variant`. **O código real implementa via `variant: str = Field(default="ajc")`** — campo `str` sem `Literal` e sem validator. Verificado em `modules/rv-instrumentation/src/rv_instrumentation/config.py:153-162` (2026-05-01).

**Decisão de supersession formal**:

1. **gh53 carrega o estado real (`Field(default="ajc")`) byte-identical** para `rv-instrumentation-core/results.py`. Não introduz `Literal[...]`, não adiciona validator. A delta spec da gh53 (`specs/instrumentation/spec.md` §INV-INS-39 e Migration Requirements) descreve esse mecanismo como o contrato de retrocompat.
2. **gh52 INV-INS-55 permanece in-flight com texto divergente**. Para evitar duas specs in-flight contraditórias após archive, **uma das duas rotas deve ser executada antes do archive de gh52**:
   - **(α)** gh52 implementa o requisito original em Phase 5/6 (promove para `Literal["ajc","dexlib2"]` + adiciona `model_validator`), substituindo o `Field(default="ajc")` que gh53 carrega forward.
   - **(β)** gh52 amenda INV-INS-55 para descrever o estado real (`Field(default="ajc")`), reconhecendo que o validator nunca foi necessário (o `default` cobre o caso retrocompat funcionalmente).
3. **gh53 NÃO escolhe entre (α) e (β)**. A escolha pertence à gh52 com mais informação (resultados Phase 5).
4. **Tarefa de saída**: o archive de gh52 (futuro) deve resolver o estado de INV-INS-55 antes de `/opsx:archive`. Esta nota é o ponteiro autoritativo para essa dependência cruzada.

Documentação adicional em design.md §"Dívida herdada gh52 INV-INS-55" e RISKS.md §RISK-003.

## Capabilities

### New Capabilities

Nenhuma capability nova.

### Modified Capabilities

- `instrumentation`: contrato público passa a ser `Instrumenter` ABC em `rv_instrumentation_core` (re-exportado por `rv_instrumentation`), com `get_instrumenter(variant, config) -> Instrumenter` em `rv_instrumentation.factory` como ponto de entrada canônico. Implementações `AjcInstrumentation` (`rv-instrumentation-ajc`) e `DexlibInstrumentation` (`rv-instrumentation-dexlib2`) herdam de `Instrumenter` (importado de `-core`). Tipos compartilhados e ABC vivem em `-core`; factory + keystore vivem em `rv-instrumentation` parent. Acoplamento `dexlib2 → ajc` eliminado. Comportamento funcional inalterado. Flag `--instrumentation-variant` e default `ajc` preservados.

## Impact

### Módulos do workspace afetados

**Novos módulos** (criados):
- `rv-instrumentation-core` — types + ABC. Source files: `__init__.py`, `results.py`, `instrumenter.py`. Deps: `pydantic`, `rv-android-core`.
- `rv-instrumentation-ajc` — recebe a impl ajc do antigo `rv-instrumentation`. Source files: `__init__.py`, `__main__.py`, `ajc_instrumentation.py` (era `rvandroid.py`), `config.py` (sem types compartilhados, com `AjcInstrumentationConfig`). Deps: `rv-instrumentation-core`, `rv-android-core`, `pyyaml`. `assets/weaving_excludes.yaml`.

**Mudança de papel**:
- `rv-instrumentation` — deixa de ser impl ajc. Vira parent canônico com factory + shared keystore. Source files: `__init__.py`, `factory.py`. Deps: `rv-instrumentation-core`, `rv-instrumentation-ajc`, `rv-instrumentation-dexlib2`. `assets/keystore.jks` permanece.

**Modificado**:
- `rv-instrumentation-dexlib2` — `DexlibInstrumentation` herda de `Instrumenter`; imports apontam para `rv-instrumentation-core` (NÃO mais `rv-instrumentation`). `pyproject.toml`: dep `rv-instrumentation` → `rv-instrumentation-core`.
- `rv-experiment` — substitui `if/else` por `get_instrumenter()`; atualiza mocks; atualiza imports `RVInstrumentationConfig` → `AjcInstrumentationConfig`. Path keystore em `config.py:669` inalterado.

**Apenas atualizações de import / path**:
- `scripts/validation/fase_a_preprocess.py:98, 148` — imports `RVInstrumentation` → `AjcInstrumentation` (de `rv_instrumentation_ajc.ajc_instrumentation`).
- `scripts/jca557_quarantine_impact.py:14, 44` — path `weaving_excludes.yaml` para `-ajc/assets/`.

**Sem mudanças**: `rvsec/javamop/`, `rvsec/pom.xml`.

### Infraestrutura Docker

- `docker/rvandroid/Dockerfile` — atualizar comentário 8-9, adicionar gate `instr-cli.jar`
- `docker/rvandroid_dexlib2/` — deletar diretório
- `docker/docker-compose.dexlib2-validation.template.yml` — reescrever
- `docker/docker-compose.jca400-aperv.yml` — verificado, no-op

### APIs e dependências

- API pública canônica: `from rv_instrumentation import Instrumenter, InstrumentationResults, InstrumentationError, get_instrumenter`
- API pública removida (P3, sem alias):
  - `from rv_instrumentation.config import InstrumentationResults, InstrumentationError` — types movidos
  - `from rv_instrumentation.config import RVInstrumentationConfig` — renomeado + movido
  - `from rv_instrumentation import RVInstrumentation` — classe renomeada + movida
- `pyproject.toml` raiz: novos workspace members `rv-instrumentation-core` + `rv-instrumentation-ajc`
- `pyproject.toml` `rv-instrumentation-core`: deps `pydantic`, `rv-android-core`
- `pyproject.toml` `rv-instrumentation` (parent): deps `rv-instrumentation-core`, `rv-instrumentation-ajc`, `rv-instrumentation-dexlib2`
- `pyproject.toml` `rv-instrumentation-ajc`: deps `rv-instrumentation-core`, `rv-android-core`, `pyyaml`
- `pyproject.toml` `rv-instrumentation-dexlib2`: substituir dep `rv-instrumentation` → `rv-instrumentation-core`
- `pyproject.toml` `rv-experiment`: adicionar deps explícitas `rv-instrumentation-dexlib2` E `rv-instrumentation-ajc` (verificado 2026-05-01: ambas ausentes hoje; `rv-instrumentation-ajc` agora também é necessária porque `config.py` importa `AjcInstrumentationConfig` diretamente)
- `modules/clean.sh`, `modules/lock.sh`, `modules/test.sh`: adicionar `rv-instrumentation-core` E `rv-instrumentation-ajc` à lista

### NFRs do PRD

- **NFR01 (manutenibilidade)**: melhora — contrato público estável (ABC) em módulo dedicado (`-core`); acoplamento circular eliminado; deps explícitas no pyproject de cada módulo
- **NFR05 (extensibilidade)**: melhora — adicionar 3ª variant (LSPatch) requer apenas: criar `rv-instrumentation-lspatch` (depende de `-core`) implementando `Instrumenter`, adicionar branch na factory do parent, estender `Literal["ajc","dexlib2"]` em `ExperimentConfig`

### Out of scope

- Phase 5 gh52 (validação 400-APK paired)
- Safety gate gh50 (task 8.5.2-5)
- Reexecução 400-APK das 44 tasks pendentes gh50
- Archives `gh50-improve-instrumentation`, `gh51-gator-soot-upgrade`, `gh52-instr-dexlib2`
- Default flip ajc → dexlib2 (deferido para change posterior)
- Mover `rv-instrumentation-ajc` para `backup/` (somente quando default flipar)
- Bump de versão Docker
- Reconciliação de specs autoritativas com gh50+gh52 (esperar archives)
- Upstream do patch javamop
- Fechar dívida gh52 INV-INS-55 (`Field` vs `model_validator`)
- gh52 task §17.2 (rename `rv-instrumentation-dexlib2` → `rv-instrumentation`) — colide com este change; gh52 Phase 6 resolve
- Promover ABC `Instrumenter` para registry pattern (deferido). Threshold canônico: 3ª variant concreta materializando é gatilho para revisão; 4ª variant é sinal definitivo

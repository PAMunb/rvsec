# Design — gh53 consolidação pós gh50/gh51/gh52

GitHub Issue: #53
ADR: `ADR-INSTRUMENTER-ABC.md` (mesmo diretório)

## Sumário do design

gh53 implementa Phase 0 Option A com refinamento crítico: 4 módulos em vez de 3, separando abstrações puras (`rv-instrumentation-core`) do parent canônico (`rv-instrumentation` com factory). Esse split resolve uma **dependência circular** que surgiria se o parent declarasse simultaneamente o ABC + tipos compartilhados E a factory que dispatcha para os impls. As 9 seções abaixo cobrem: (D1) layout dos 4 módulos e grafo de dependências; (D2) ABC vs Protocol — por que ABC; (D3) por que `-core` separado em vez de tudo no parent; (D4) migração atômica + rename; (D5) factory pública e dispatch; (D6) unificação Docker; (D7) estratégia de testes + critérios de aceitação mecânicos; (D8) trade-off com gh52 task §17.2 e LSPatch futuro; (D9) riscos residuais. Mais uma seção dedicada (§"Dívida herdada gh52 INV-INS-18") explica `Field(default="ajc")` vs `model_validator(mode="before")`.

## D1 — Layout de 4 módulos

```
modules/
├── rv-instrumentation-core/             # NOVO — abstrações puras
│   ├── pyproject.toml                   # deps: pydantic, rv-android-core
│   ├── src/rv_instrumentation_core/
│   │   ├── __init__.py                  # re-exports
│   │   ├── results.py                   # InstrumentationResults + InstrumentationError
│   │   └── instrumenter.py              # ABC Instrumenter
│   └── tests/
│       ├── test_results.py              # round-trip Pydantic + variant tag retrocompat
│       └── test_instrumenter.py         # ABC contract: subclass missing instrument_apks fails
│
├── rv-instrumentation/                  # PARENT — factory + shared assets
│   ├── pyproject.toml                   # deps: -core, -ajc, -dexlib2
│   ├── src/rv_instrumentation/
│   │   ├── __init__.py                  # re-exports de -core + factory
│   │   └── factory.py                   # get_instrumenter(variant, config) -> Instrumenter
│   ├── assets/
│   │   └── keystore.jks                 # SHARED (apksigner + jarsigner)
│   ├── tests/
│   │   └── test_factory.py              # ajc, dexlib2, invalid variant + lazy import
│   └── docs/architecture.md             # parent canonical
│
├── rv-instrumentation-ajc/              # RENAMED de rv-instrumentation impl
│   ├── pyproject.toml                   # deps: rv-instrumentation-core, rv-android-core, pyyaml
│   ├── src/rv_instrumentation_ajc/
│   │   ├── __init__.py
│   │   ├── __main__.py                  # CLI ajc
│   │   ├── ajc_instrumentation.py       # AjcInstrumentation(Instrumenter) — was RVInstrumentation
│   │   └── config.py                    # AjcInstrumentationConfig — was RVInstrumentationConfig
│   ├── assets/
│   │   └── weaving_excludes.yaml        # AJC-ESPECÍFICO
│   ├── tests/                           # migrated/adapted from current rv-instrumentation/tests/
│   └── docs/architecture.md             # migrated (~689 lines, paths updated)
│
└── rv-instrumentation-dexlib2/          # EXISTING
    ├── pyproject.toml                   # deps: rv-instrumentation-core (was rv-instrumentation)
    └── src/rv_instrumentation_dexlib2/
        ├── dexlib_instrumentation.py    # DexlibInstrumentation(Instrumenter)
        │                                #   from rv_instrumentation_core import (...)
        └── ...
```

**Grafo de dependências** (sem ciclo):

```
rv-android-core
        ↑
rv-instrumentation-core  ← rv-instrumentation-ajc
        ↑                ← rv-instrumentation-dexlib2
        ↑
rv-instrumentation (parent)  → rv-instrumentation-ajc       (declared, lazy import in factory)
                             → rv-instrumentation-dexlib2   (declared, lazy import in factory)
        ↑
rv-experiment (consumer)  → rv-instrumentation
                          → rv-instrumentation-ajc          (precisa de AjcInstrumentationConfig)
                          → rv-instrumentation-dexlib2      (precisa de DexlibInstrumentationConfig)
```

Setas só vão para baixo no grafo (em direção a `rv-android-core` na base). Cada módulo declara honestamente todas as suas deps no `pyproject.toml`. Sem deps implícitas.

## D2 — ABC `Instrumenter`, não Protocol

**Decisão**: ABC nominal (`abc.ABC` + `@abstractmethod`), em `rv-instrumentation-core/src/rv_instrumentation_core/instrumenter.py`. Razões:

- **Pattern do projeto**: `AbstractTool` em `modules/rv-android-core/src/rv_android_core/tools/abstract_tool.py` segue mesmo modelo. Inheritance é o sinal canônico de "implementação de variant".
- **Contrato fail-fast**: subclasse sem `instrument_apks` falha **na instanciação** (`TypeError`), não em runtime tardio durante experimento.
- **Test integration trivial**: `tests/test_instrumenter.py` cria subclasse incompleta, confirma `TypeError`. Subclasse concreta com `instrument_apks` instancia OK.
- **Compatibilidade com type-checkers**: `def get_instrumenter(...) -> Instrumenter` produz tipo nominal que IDEs e mypy entendem direto.

**ABC contém apenas `instrument_apks`** como `@abstractmethod`. Métodos divergentes entre as duas impls (`prepare_instrumentation`, `instrument` single-APK, `check_if_instrumented`, `clear`, `create_temp_directories`) **não** entram. Consumidores que precisam de métodos ajc-específicos importam `AjcInstrumentation` direto (ex: `scripts/validation/fase_a_preprocess.py`).

## D3 — Por que `-core` separado em vez de tudo no parent

**O problema do parent monolítico (3 módulos)**:

Se o parent `rv-instrumentation` contém ABC + tipos + factory:
- `rv-instrumentation-ajc/pyproject.toml` declara dep em `rv-instrumentation` (precisa do ABC para herdar)
- `rv-instrumentation/pyproject.toml` precisa declarar dep em `rv-instrumentation-ajc` (factory importa `AjcInstrumentation`)
- → **ciclo direto** que `uv workspace` recusa ou resolve mal

**Workaround com lazy imports sem dep declarada**: factory faz `from rv_instrumentation_ajc... import` dentro do branch da função. Funciona em runtime, mas:
- Testes do factory no parent quebram (impls não instaladas)
- Consumidor que use só `rv-instrumentation` em isolamento descobre `ImportError` em runtime
- Dependência implícita não-declarada (anti-padrão) — futuros contribuidores não veem

**Solução com `-core` (4 módulos)**: separar abstrações puras (ABC + tipos) em módulo dedicado:

- `rv-instrumentation-core` — ABC + tipos. Deps: `pydantic`, `rv-android-core`. **Não** depende de impls.
- `rv-instrumentation-ajc` e `-dexlib2` — depende de `-core` (precisa do ABC). **Não** depende do parent.
- `rv-instrumentation` parent — factory + assets. Depende de `-core` (re-exports) E de `-ajc`/`-dexlib2` (factory dispatch).

Cada módulo declara honestamente o que importa. Setas só vão para baixo. **Zero ciclos**.

**Custo**: +1 módulo no workspace (16 produção pós-change vs 14 atual; +`-core` +`-ajc`).
**Benefício**: corretude topológica + deps explícitas + factory testável + impls testáveis em isolamento + `-core` reutilizável por outros consumidores futuros.

## D4 — Migração atômica + rename (P3)

**Estado de partida** (verificado 2026-05-01):
- `modules/rv-instrumentation/src/rv_instrumentation/config.py:102-124` — `class InstrumentationError(BaseValidatedModel)`
- `modules/rv-instrumentation/src/rv_instrumentation/config.py:127-175` — `class InstrumentationResults(BaseValidatedModel)`
- `modules/rv-instrumentation/src/rv_instrumentation/config.py:194+` — `class RVInstrumentationConfig` (~196 linhas após o split)
- `modules/rv-instrumentation/src/rv_instrumentation/__init__.py` (17 linhas) — re-exports
- `modules/rv-instrumentation/src/rv_instrumentation/__main__.py` (479 linhas) — CLI
- `modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py` (1686 linhas) — `class RVInstrumentation`
- `modules/rv-instrumentation/assets/keystore.jks` (shared)
- `modules/rv-instrumentation/assets/weaving_excludes.yaml` (ajc-specific)

**Estado de chegada** (P3 atômico — sem aliases):

A. `modules/rv-instrumentation-core/` (NOVO):
- `src/rv_instrumentation_core/__init__.py` — re-exports
- `src/rv_instrumentation_core/results.py` — `InstrumentationError` + `InstrumentationResults` (copiados byte-a-byte de `config.py:102-175`, preservando `Field(default="ajc")`)
- `src/rv_instrumentation_core/instrumenter.py` — ABC `Instrumenter` (NOVO)
- `pyproject.toml` — `name = "rv-instrumentation-core"`, deps `pydantic`, `rv-android-core`
- `tests/`, `docs/architecture.md`, `CLAUDE.md`

B. `modules/rv-instrumentation/` (parent canônico, papel mudou):
- `src/rv_instrumentation/__init__.py` — `from rv_instrumentation_core import (Instrumenter, InstrumentationResults, InstrumentationError)`; `from rv_instrumentation.factory import get_instrumenter`; `__all__ = [...]`
- `src/rv_instrumentation/factory.py` — `get_instrumenter` (NOVO)
- `assets/keystore.jks` (permanece — shared)
- `pyproject.toml` — `name = "rv-instrumentation"`, deps `rv-instrumentation-core`, `rv-instrumentation-ajc`, `rv-instrumentation-dexlib2`. **Remove** `[project.scripts]` (CLI move para `-ajc`).
- `tests/test_factory.py` (NOVO)
- `docs/architecture.md` (RECRIADO — parent scope, ~50 linhas)
- `CLAUDE.md` (RECRIADO — parent scope)

C. `modules/rv-instrumentation-ajc/` (RENAMED de impl atual):
- `src/rv_instrumentation_ajc/__init__.py`
- `src/rv_instrumentation_ajc/__main__.py` (era `rv_instrumentation/__main__.py`); imports atualizados
- `src/rv_instrumentation_ajc/ajc_instrumentation.py` (era `rvandroid.py`); `class AjcInstrumentation(Instrumenter)` — herança adicionada; rename `RVInstrumentation` → `AjcInstrumentation`; imports atualizados (`from rv_instrumentation_core import Instrumenter, InstrumentationResults, InstrumentationError`)
- `src/rv_instrumentation_ajc/config.py` (era `rv_instrumentation/config.py` MINUS as classes migradas para `-core`); rename `RVInstrumentationConfig` → `AjcInstrumentationConfig`; `ConfigurationError` permanece como re-export de `rv_android_core.util.error.exceptions`
- `assets/weaving_excludes.yaml` (movido)
- `pyproject.toml` — `name = "rv-instrumentation-ajc"`, deps `rv-instrumentation-core`, `rv-android-core`, `pyyaml`. `[project.scripts]` `rv-instrumentation-ajc = "rv_instrumentation_ajc.__main__:main"`.
- `tests/`, `docs/architecture.md` (migrado), `CLAUDE.md` (migrado)

D. `modules/rv-instrumentation-dexlib2/` (existente, modificado):
- `src/rv_instrumentation_dexlib2/dexlib_instrumentation.py:11-14` — `from rv_instrumentation.config import (InstrumentationError, InstrumentationResults)` → `from rv_instrumentation_core import (Instrumenter, InstrumentationError, InstrumentationResults)`
- `dexlib_instrumentation.py:122-125` — mesma mudança no escopo local
- `class DexlibInstrumentation:` → `class DexlibInstrumentation(Instrumenter):`
- `pyproject.toml` — substituir dep `rv-instrumentation` por `rv-instrumentation-core`

**P3 — sem aliases retrocompatíveis**:
- `from rv_instrumentation.config import InstrumentationResults` → quebra
- `from rv_instrumentation.config import RVInstrumentationConfig` → quebra
- `from rv_instrumentation import RVInstrumentation` → quebra
- API válida pós-change: `from rv_instrumentation import (Instrumenter, InstrumentationResults, InstrumentationError, get_instrumenter)`. Para `AjcInstrumentation`/`AjcInstrumentationConfig`: `from rv_instrumentation_ajc.{ajc_instrumentation,config} import ...`.

**Risco de retrocompat de `instrument_errors.json`**: Pydantic `model_dump_json()` não embute `__module__`. Mover entre módulos não quebra deserialização. Retrocompat de JSONs sem `variant` é via `Field(default="ajc")` em `InstrumentationResults.variant` (verificado em `modules/rv-instrumentation/src/rv_instrumentation/config.py:153-162`); copiado byte-a-byte para `rv-instrumentation-core/results.py`. Ver §"Dívida herdada gh52 INV-INS-18" abaixo.

### Dívida herdada gh52 INV-INS-18 — `Field(default="ajc")` em vez de `model_validator(mode="before")`

A spec gh52 INV-INS-18 (`openspec/changes/gh52-instr-dexlib2/specs/instrumentation/spec.md:103`) textualmente exige: (a) `variant` MUST ser required (sem default); (b) retrocompat de JSON legacy via `model_validator(mode="before")` que injeta `variant="ajc"`. **O código real implementa via `variant: str = Field(default="ajc")`** — campo `str` sem `Literal` e sem validator (verificado byte-a-byte em `modules/rv-instrumentation/src/rv_instrumentation/config.py:153-162`, 2026-05-01).

**Decisão de escopo do gh53 (supersession formal)**: descrever a realidade — copiar `variant: str = Field(default="ajc")` byte-identical para `rv-instrumentation-core/results.py`. Promover para `Literal[...]` + `model_validator` é dívida da gh52 (Phase 5/6), **fora do escopo do gh53**.

**Resolução obrigatória antes do archive de gh52** — gh52 deve escolher uma das rotas (gh53 não escolhe):

- **(α)** Implementa o requisito original em Phase 5/6: promove para `Literal["ajc","dexlib2"]` + adiciona `model_validator(mode="before")`, substituindo o `Field(default="ajc")` que gh53 carrega forward em `-core/results.py`.
- **(β)** Amenda INV-INS-18 (delta + sync da gh52) para descrever o estado real (`Field(default="ajc")`), reconhecendo que o `default` cobre funcionalmente o caso retrocompat sem validator.

Esta supersession está documentada também em `proposal.md` §"Dívida herdada gh52 INV-INS-18 — fora do escopo (supersession explícita)" e em RISK-003. Implementadores da gh53 NÃO devem fechar INV-INS-18 mid-gh53 (RISK-003 indicator: `grep -n 'model_validator' modules/rv-instrumentation-core/src/` → Red se não-zero).

**Verificação**: `tests/test_results.py` em `-core` inclui `test_legacy_json_without_variant_defaults_to_ajc` que carrega JSON sem `variant` e confirma deserialização com `variant=="ajc"`. Robusto à escolha de mecanismo (passa com `Field` hoje; passaria com `model_validator` se a spec fosse fechada).

## D5 — Factory pública `get_instrumenter` e dispatch em `pre_processor.py`

```python
# modules/rv-instrumentation/src/rv_instrumentation/factory.py
from __future__ import annotations

from rv_instrumentation_core import Instrumenter


def get_instrumenter(variant: str, config) -> Instrumenter:
    """Return the configured instrumenter for the given variant.

    Lazy imports keep variant modules optional at import time. Selecting "ajc"
    does NOT force importing rv_instrumentation_dexlib2, and vice versa.
    """
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

**Lazy imports** garantem que `from rv_instrumentation import get_instrumenter` não puxa transitivamente os 2 módulos de impl. Pyproject do parent declara as deps (impls instaladas no workspace), mas o módulo Python só carrega quando a factory é chamada com a variant correspondente.

**Site único de dispatch em `pre_processor.py`** (substitui `if/else` em `:188-207`):

```python
from rv_instrumentation import get_instrumenter

# ... dentro de _instrument_apks() ...
variant = getattr(self.config, "instrumentation_variant", "ajc")
instr_config = (
    self.config.get_dexlib_instrumentation_config()
    if variant == "dexlib2"
    else self.config.get_rv_instrumentation_config()
)
instrumenter = get_instrumenter(variant, instr_config)
```

A escolha de qual config method chamar fica no `pre_processor` (que conhece `ExperimentConfig`). Factory é variant-agnostic em termos de qual config foi escolhido — só aceita o config preparado.

**Atualização de mocks** (`test_pre_processor_variant.py`): `patch("rv_instrumentation.RVInstrumentation")` (e equivalente dexlib2) → `patch("rv_experiment.experiment.workflow.pre_processor.get_instrumenter")` — testa o site único de decisão.

## D6 — Unificação Docker

**Estado atual**:
- `docker/rvandroid/Dockerfile` (42 linhas) — base. Tag: `phtcosta/rvandroid:0.8.0`. Falta gate.
- `docker/rvandroid_dexlib2/Dockerfile` (53 linhas) — herda da base, flipa env, valida jar via `RUN test -f "$RVSEC_INSTR_DEXLIB2_JAR"` (linha 50-51). Tag: `phtcosta/rvandroid:0.8.0-dexlib2`. **A ser deletado.**

**Estado final**:
- `docker/rvandroid/Dockerfile` carrega ambos variants, verifica `instr-cli.jar`. Tag: `phtcosta/rvandroid:0.8.0`.
- Compose template usa essa única tag.

**Gate equivalente em `docker/rvandroid/Dockerfile`**:

```dockerfile
RUN test -f /opt/rvsec/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar \
    || (echo "ERROR: instr-cli.jar missing — Maven D9 auto-copy did not run; check rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/pom.xml" && exit 1)
```

Path verificado em `docker/rvandroid_dexlib2/Dockerfile:46`: `RVSEC_INSTR_DEXLIB2_JAR=/opt/rvsec/rv-android/modules/...` (base usa `WORKDIR /opt/rvsec` + `git clone ... .`).

**Comentário-exemplo em `docker/rvandroid/Dockerfile:8-9`**: cita `RVSEC_BRANCH=gh52-instr-dexlib2` e tag `0.8.0-dexlib2-base` — obsoletos pós-merge. Substituir por exemplo neutro ou remover (P4).

**Validação**: AC-DOC-01 (`docker compose config --quiet`); AC-IMG-01 (rebuild + 1-APK por variant smoke).

## D7 — Estratégia de testes + Critérios de aceitação mecânicos

### Tests por módulo

**`rv-instrumentation-core`**:
- `tests/test_results.py`: round-trip dexlib2/ajc; `test_legacy_json_without_variant_defaults_to_ajc`; invalid variant raises
- `tests/test_instrumenter.py`: synthetic subclass missing `instrument_apks` raises `TypeError`; concrete subclass instanciates OK; `inspect.signature` of `instrument_apks` matches both real impls

**`rv-instrumentation` (parent)**:
- `tests/test_factory.py`: `get_instrumenter("ajc", config)` returns `AjcInstrumentation`, NOT imports dexlib2 (`sys.modules` snapshot); `get_instrumenter("dexlib2", config)` returns `DexlibInstrumentation`, NOT imports ajc; `get_instrumenter("lspatch", config)` raises `ValueError`; both variants `isinstance(returned, Instrumenter)`

**`rv-instrumentation-ajc`**: tests migrados de `modules/rv-instrumentation/tests/` (todos os imports atualizados de `rv_instrumentation` → `rv_instrumentation_ajc` e tipos de `rv_instrumentation_core`).

**`rv-instrumentation-dexlib2`**: tests existentes; imports atualizados.

**`rv-experiment`**: `test_pre_processor_variant.py` mocks atualizados; novo test para `ValueError` propagar.

### Critérios de aceitação (ACs)

#### Imports e topologia

| ID | Comando | Resultado esperado |
|----|---------|---------------------|
| AC-IMP-01 | `grep -rnE 'from rv_instrumentation\.config import (InstrumentationResults\|InstrumentationError\|RVInstrumentationConfig)' modules/ scripts/` | 0 hits (ajustado 2026-05-01: removido `tests/` do glob — `./tests/` no root não existe; `modules/*/tests/` cobertos pelo glob `modules/`) |
| AC-IMP-02 | `grep -rnE '^class (InstrumentationResults\|InstrumentationError)\b' modules/rv-instrumentation*/src/` | hits **somente** sob `modules/rv-instrumentation-core/src/` (INV-INS-33) |
| AC-IMP-03 | `grep -rnE 'from rv_instrumentation[^_]\|^import rv_instrumentation[^_]' modules/rv-instrumentation-dexlib2/src/ modules/rv-instrumentation-ajc/src/` | 0 hits — impls importam só de `rv_instrumentation_core`, não do parent (INV-INS-34) |
| AC-IMP-04 | `grep -rnE 'from rv_instrumentation import RVInstrumentation\|from rv_instrumentation\.rvandroid import RVInstrumentation\|RVInstrumentation\(' modules/ scripts/` | 0 hits — classe renomeada (ajustado 2026-05-01: padrão expandido para cobrir `from rv_instrumentation.rvandroid import RVInstrumentation` que existe em `scripts/validation/fase_a_preprocess.py:98,148`; removido `tests/` do glob pelo motivo acima) |
| AC-IMP-05 | `python -c "from rv_instrumentation import Instrumenter, InstrumentationResults, InstrumentationError, get_instrumenter"` | exit 0 |
| AC-IMP-06 | `python -c "from rv_instrumentation_core import Instrumenter, InstrumentationResults, InstrumentationError"` | exit 0 |
| AC-IMP-07 | `python -c "from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation; from rv_instrumentation_ajc.config import AjcInstrumentationConfig"` | exit 0 |
| AC-IMP-08 | `python -c "from rv_instrumentation_dexlib2 import DexlibInstrumentation; from rv_instrumentation_core import Instrumenter; assert issubclass(DexlibInstrumentation, Instrumenter)"` | exit 0 |
| AC-IMP-09 | `grep -rnE 'def get_instrumenter\|def make_instrumenter\|def _select_instrumenter' modules/ scripts/` | hits **somente** em `modules/rv-instrumentation/src/rv_instrumentation/factory.py` (INV-INS-36) |
| AC-IMP-10 | `grep -rnE 'from rv_android_core\.util\.error\.exceptions import.*\bInstrumentationError\b' modules/` AND `python -c "from rv_android_core.util.error.exceptions import InstrumentationError as Exc; from rv_instrumentation_core import InstrumentationError as Pyd; assert Exc is not Pyd"` | grep retorna apenas hits em `modules/rv-instrumentation-ajc/src/rv_instrumentation_ajc/ajc_instrumentation.py` (era `rvandroid.py`) e seus testes; python exit 0. Garante que call sites continuam usando a Exception (`rv_android_core.util.error.exceptions.InstrumentationError`) sem confusão com a Pydantic homônima (`rv_instrumentation_core.InstrumentationError` — name collision pré-existente, não-bloqueante) |

#### Comportamento

| ID | Comando | Resultado esperado |
|----|---------|---------------------|
| AC-BHV-01 | `pytest modules/rv-instrumentation-core/tests/ --import-mode=importlib -o "addopts="` | exit 0 |
| AC-BHV-02 | `pytest modules/rv-instrumentation/tests/ --import-mode=importlib -o "addopts="` | exit 0 (parent: factory) |
| AC-BHV-03 | `pytest modules/rv-instrumentation-ajc/tests/ --import-mode=importlib -o "addopts="` | exit 0 |
| AC-BHV-04 | `pytest modules/rv-instrumentation-dexlib2/tests/ --import-mode=importlib -o "addopts="` | exit 0 |
| AC-BHV-05 | `pytest modules/rv-experiment/tests/test_pre_processor_variant.py --import-mode=importlib -o "addopts="` | exit 0 |
| AC-BHV-06 | `pytest modules/rv-experiment/tests/ --import-mode=importlib -o "addopts="` | exit 0 |
| AC-BHV-07 | `for m in modules/*/; do uv run pytest "$m/tests" --import-mode=importlib -o "addopts=" -m "not (slow or online or sglang or performance or dataset)" || break; done` | exit 0 |

#### Workspace e packaging

| ID | Comando | Resultado esperado |
|----|---------|---------------------|
| AC-WSP-01 | `rm -rf .venv && uv sync` (root) | exit 0; `.venv` contém `rv_instrumentation_core`, `rv_instrumentation_ajc` |
| AC-WSP-02 | `python -c "import rv_instrumentation_core; import rv_instrumentation_ajc; print(rv_instrumentation_core.__file__, rv_instrumentation_ajc.__file__)"` | paths apontam para `modules/rv-instrumentation-core/src/` e `modules/rv-instrumentation-ajc/src/` |
| AC-WSP-03 | Os 4 módulos `rv-instrumentation*` listados em cada script: `for f in modules/{clean,lock,test}.sh; do for m in rv-instrumentation rv-instrumentation-core rv-instrumentation-ajc rv-instrumentation-dexlib2; do grep -q "\"$m\"" "$f" \|\| fail; done; done` | 4/4 módulos presentes em cada script (ampliado 2026-05-01 para incluir `-dexlib2` — task 7.5 fecha dívida pré-existente da gh52) |
| AC-WSP-04 | `grep -n 'rv-instrumentation-dexlib2\|rv-instrumentation-ajc' modules/rv-experiment/pyproject.toml` | 2+ hits em `dependencies` |
| AC-WSP-05 | Parent `rv-instrumentation/pyproject.toml` `[project] dependencies` MUST include `rv-instrumentation-core`, `rv-instrumentation-ajc`, `rv-instrumentation-dexlib2`. MUST NOT include impl deps from outside the workspace. `pydantic` is permitted (as transitive convenience or explicit). MUST NOT include `rv-android-core` directly (transitive via `-core`). Verify via `python -c "import tomllib; ..."` | matches |
| AC-WSP-06 | `rv-instrumentation-core/pyproject.toml` deps EXATAMENTE `pydantic, rv-android-core` | sim |

#### Docker

| ID | Comando | Resultado esperado |
|----|---------|---------------------|
| AC-DOC-01 | `docker compose -f docker/docker-compose.dexlib2-validation.template.yml config --quiet` | exit 0; ambos serviços usam tag `0.8.0`, diferem só em `RV_INSTRUMENTATION_VARIANT` |
| AC-DOC-02 | `find docker -name 'rvandroid_dexlib2*'` | empty |
| AC-DOC-03 | `grep -rn '0\.8\.0-dexlib2' docker/ scripts/ docs/` | 0 hits em código funcional |
| AC-IMG-01 | `docker build -t phtcosta/rvandroid:0.8.0 docker/rvandroid/` em clone limpo | exit 0; gate `instr-cli.jar` passa |
| AC-IMG-02 | Smoke 1-APK por variant: `RV_INSTRUMENTATION_VARIANT=ajc` produz `instrument_errors.json` com `variant: "ajc"`; `=dexlib2` produz `variant: "dexlib2"` | ambos exit 0 |

#### Cleanup

| ID | Comando | Resultado esperado |
|----|---------|---------------------|
| AC-CLN-01 | `find . -maxdepth 2 -name 'ajcore.*.txt'` | empty |
| AC-CLN-02 | `grep -nE 'ajcore' .gitignore` | 1+ hit |

#### Documentação

| ID | Comando | Resultado esperado |
|----|---------|---------------------|
| AC-DCM-01 | `grep -n 'rv-instrumentation-core\|rv-instrumentation-ajc' CLAUDE.md` | 2+ hits em §System Modules |
| AC-DCM-02 | Existência de CLAUDE.md em todos os 4 módulos `rv-instrumentation*/` | true |
| AC-DCM-03 | `grep -n '16 uv workspace modules\|16 production modules' openspec/config.yaml CLAUDE.md README.md` | 1+ hit per file |
| AC-DCM-04 | `[ -f openspec/changes/gh53-consolidacao-instrumentation/ADR-INSTRUMENTER-ABC.md ]` | true |

#### Asset migration

| ID | Comando | Resultado esperado |
|----|---------|---------------------|
| AC-AST-01 | `[ -f modules/rv-instrumentation/assets/keystore.jks ]` | true (parent canônico — shared) |
| AC-AST-02 | `[ -f modules/rv-instrumentation-ajc/assets/weaving_excludes.yaml ]` | true (movido) |
| AC-AST-03 | `[ ! -f modules/rv-instrumentation/assets/weaving_excludes.yaml ]` | true (sem duplicata) |
| AC-AST-04 | `grep -n 'rv-instrumentation/assets/weaving_excludes' scripts/jca557_quarantine_impact.py` | 0 hits |
| AC-AST-05 | `grep -n 'rv-instrumentation-ajc/assets/weaving_excludes' scripts/jca557_quarantine_impact.py` | 1+ hits |
| AC-AST-06 | `grep -n 'rv-instrumentation/assets/keystore' modules/rv-experiment/src/rv_experiment/config.py` | 1+ hit (path inalterado, parent canônico) |

## D8 — Trade-off com gh52 task §17.2 e LSPatch futuro

**gh52 task §17.2** propõe renomear `rv-instrumentation-dexlib2` → `rv-instrumentation` quando default flipar. **gh53 ocupa `rv-instrumentation` com o parent canônico**, criando colisão direta.

Resolução: gh53 não antecipa gh52 Phase 6. Quando gh52 Phase 6 executar §17.2, opções de saída:

- (a) renomear dexlib2 → outro nome canônico (ex: `rv-instrumentation-default`); parent fica
- (b) refatorar parent para outro nome (ex: `rv-instrumentation-shared`) e dexlib2 vira `rv-instrumentation`
- (c) manter `rv-instrumentation-dexlib2` no nome (sem flip de nome); o flip default fica só semântico

Decisão fica para gh52 com mais informação (resultados Phase 5 + considerações de naming). gh53 não bloqueia nenhuma.

**LSPatch** (`docs/20260422_lspatch.md`, sem ETA): se materializar como 3ª variant, caminho:

1. Criar `modules/rv-instrumentation-lspatch/` (deps: `rv-instrumentation-core`); classe `LspatchInstrumentation(Instrumenter)`
2. Adicionar branch `lspatch` em `rv_instrumentation.factory.get_instrumenter`
3. Estender `Literal["ajc","dexlib2"]` → `Literal["ajc","dexlib2","lspatch"]` em `ExperimentConfig`
4. Adicionar `rv-instrumentation-lspatch` como dep do parent

Custo: 1 módulo novo + 1 import + 1 branch + 1 Literal extension. **Threshold canônico**: 3ª variant é gatilho para revisar; 4ª é sinal definitivo de pressão para registry pattern.

## D9 — Riscos residuais e mitigações

Detalhamento completo em `RISKS.md` (mesmo diretório, 14 riscos: 5 High, 6 Medium, 3 Low). Resumo executivo dos 5 High + 3 Medium consequentes (8 linhas; demais Medium e todos Low só em RISKS.md):

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Rename `rv-instrumentation` (impl ajc) → `-ajc` deixa referência órfã em código não coberto pelos greps | Média | Alto | AC-IMP-01..04; subagent dispatch em Phase 4 com grep amplo `RVInstrumentation\b` outside parent |
| ABC `Instrumenter` muda contrato pra DexlibInstrumentation existente, quebra silenciosamente | Baixa | Alto | `tests/test_instrumenter.py` em `-core`; `inspect.signature` test |
| Maven D9 auto-copy regredir silenciosamente | Baixa | Alto | Gate `RUN test -f` em Dockerfile; AC-IMG-01 |
| Test mocks de `RVInstrumentation` quebram em outros módulos não cobertos pela varredura | Média | Médio | AC-BHV-07 (suite completa CI); subagent grep amplo |
| `rv-experiment/pyproject.toml` ainda não declara `rv-instrumentation-dexlib2` nem `rv-instrumentation-ajc` (verificado 2026-05-01) | Média | Médio | task explícita adiciona ambas; AC-WSP-04 verifica |
| Reescrita do compose template quebra paired-comparison futuro do gh52 Phase 5 | Baixa | Médio | AC-DOC-01 + revisão visual |
| Coordenação 4 módulos: implementador "fixa" gh52 INV-INS-18 dívida adicionando `model_validator` mid-gh53 | Baixa | Catastrófico | Documentado em design + ADR; `/rv-code-reviewer` flagga |
| gh52 task §17.2 colide com parent canônico criado aqui | N/A — esperado | Baixo | Documentado como consequência aceita; gh52 Phase 6 escolhe rota |

## Referências

- ADR: `ADR-INSTRUMENTER-ABC.md` (mesmo diretório)
- Phase 0: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260428_plano_consolidacao_pos_gh50_gh51_gh52.md`
- gh52 ADR (precedente): `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh52-instr-dexlib2/ADR-DEX-NATIVE.md`
- gh52 INV-INS-18 (variant tag): `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh52-instr-dexlib2/specs/instrumentation/spec.md`
- gh52 task §17.2 (rename trade-off): `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/openspec/changes/gh52-instr-dexlib2/tasks.md`
- LSPatch: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/20260422_lspatch.md`
- PRD NFR01, NFR05: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docs/PRD.md`
- Project pattern (`AbstractTool` ABC): `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-android-core/src/rv_android_core/tools/abstract_tool.py`

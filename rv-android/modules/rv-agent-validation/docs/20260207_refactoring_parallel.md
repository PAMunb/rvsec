# Refactoring: Paralelismo e --skip-execution

**Data**: 2026-02-07
**Status**: Partes 1-9 implementadas e validadas.
**Objetivo**: Implementar suporte a paralelismo (6 emuladores) e --skip-execution para viabilizar o plano de validacao (~12.5 dias com 6 emuladores)

## Diretrizes de Implementacao

1. **Simplicidade**: Codigo simples e direto. Sem abstrações desnecessarias, sem over-engineering. A complexidade minima necessaria para a tarefa atual.
2. **Sem codigo legado**: Todas as alteracoes devem ser completas. Sem adapters, shims ou wrappers de compatibilidade. Codigo antigo deve ser removido ou sobrescrito. Arquivos substituidos devem ser movidos para `backup/`.
3. **Comentarios refletem o estado atual**: Comentarios nao devem mencionar migracoes, fases, legado, "o que era antes", ou "o que foi feito". Devem descrever apenas o estado atual do codigo.
4. **Sem linguagem promocional**: Nao usar termos como "moderno", "sofisticado", "elegante", "robusto", "poderoso", etc. Publico-alvo: desenvolvedores e pesquisadores. Linguagem tecnica e objetiva.
5. **Todas as referencias atualizadas**: Imports, chamadas, testes e documentacao devem apontar para as novas implementacoes. Nenhuma referencia a codigo removido.

---

## Context

O plano de validacao (`20260207_rvagent_validacao.md`) assume 6 emuladores paralelos (~12.5 dias), mas o sistema **nao tem suporte a paralelismo**. Alem disso, falta `--skip-execution` para rodar apenas pre-processamento (Fase A). Cada processo paralelo precisa de seu proprio output_dir e results_dir para nao sobrescrever resultados.

### O que ja existe (suporte parcial)

| Componente | O que ja tem | Arquivo |
|------------|-------------|---------|
| `EmulatorManager.start_emulator()` | Aceita `device_port` (5554, 5556, ...) | `rv-android-core/.../emulator_manager.py:52` |
| `EmulatorComponent.start_emulator()` | Le `device_port` de `additional_params` | `rv-platform/.../emulator.py:110-114` |
| `EmulatorComponent.install_app()` | Le `device_serial` de `additional_params` | `rv-platform/.../emulator.py:172-176` |
| `PlatformConfig.max_parallel_tasks` | Campo existe (default=1, "future feature") | `rv-platform/.../platform_config.py:55` |
| `CalibrationOptimizer` | SQLite storage (process-safe) | `rv-agent-validation/.../optimizer.py:124` |
| `CalibrationRunner` | Subprocess por trial, output_dir unico por trial | `rv-agent-validation/.../runner.py:97` |

### Implementacao

| # | Feature | Status | Arquivos |
|---|---------|--------|----------|
| 1 | `--skip-execution` | ✅ Implementado | config.py, __main__.py, experiment_controller.py |
| 2 | `--device-port` | ✅ Implementado | config.py, __main__.py, execution_controller.py |
| 3 | `--apks-filter` (execucao) | ✅ Implementado | config.py, __main__.py, platform_config.py, platform.py |
| 4 | `n_jobs` + EmulatorPool | ✅ Implementado | emulator_pool.py (novo), runner.py, optimizer.py, cli.py |
| 5 | `--name` | ✅ Implementado | __main__.py |
| 6 | `parallel_run.py` | ✅ Implementado | scripts/parallel_run.py (novo) |
| 7 | `--apks-filter` (preprocessing) | ✅ Implementado | rvandroid.py, pre_processor.py |
| 8 | Fix `kill_emulator` paralelismo | ✅ Implementado | android.py, test_android.py — ver Parte 8 |
| 9 | Fase A: Preprocessing paralelo | ✅ Implementado | scripts/validation/fase_a_preprocess.py, filter_apks_static_analysis.py |

---

## Parte 1: --skip-execution (Fase A)

**Objetivo**: Rodar apenas pre-processamento (monitores + instrumentacao + static analysis) sem executar tasks.

### Arquivos

| Arquivo | Mudanca |
|---------|---------|
| `modules/rv-experiment/src/rv_experiment/config.py` | Adicionar `run_execution: bool = True` |
| `modules/rv-experiment/src/rv_experiment/__main__.py` | Adicionar `--run-execution/--skip-execution` flag |
| `modules/rv-experiment/src/rv_experiment/experiment/experiment_controller.py` | Condicionar `_run_execution()` a `config.run_execution` |

### Detalhes

**config.py** (linha ~111, junto aos outros booleans):
```python
run_execution: bool = Field(default=True, description="Execute tasks after preprocessing")
```

**__main__.py** (linha ~326, junto aos outros skip flags):
```python
@click.option('--run-execution/--skip-execution', default=True,
              help='Execute tasks after preprocessing (default: enabled)')
```
E passar o parametro na criacao do ExperimentConfig.

**experiment_controller.py** (linha ~130, no metodo `run()`):
```python
# Phase 2: Execution
if self.config.run_execution:
    self.logger.info("Starting execution phase")
    execution_success = self._run_execution()
    if not execution_success:
        self.logger.warning("Execution phase completed with issues")
        success = False
else:
    self.logger.info("Execution phase skipped (--skip-execution)")
```

---

## Parte 2: --device-port passthrough

**Objetivo**: Permitir que rv-experiment receba um device_port e passe ate o EmulatorComponent (que ja sabe usa-lo).

### Arquivos

| Arquivo | Mudanca |
|---------|---------|
| `modules/rv-experiment/src/rv_experiment/config.py` | Adicionar `device_port: Optional[int] = None` |
| `modules/rv-experiment/src/rv_experiment/__main__.py` | Adicionar `--device-port` option |
| `modules/rv-experiment/src/rv_experiment/experiment/workflow/execution_controller.py` | Injetar `device_port` nos `additional_params` de cada ToolConfig |

### Detalhes

**config.py**:
```python
device_port: Optional[int] = Field(default=None, description="Emulator port for parallel execution")
```

**__main__.py**:
```python
@click.option('--device-port', type=int, default=None,
              help='Emulator port for parallel execution (default: 5554)')
```

**execution_controller.py** (`_create_platform_config`, linha ~200):
```python
# Inject device_port into tool additional_params for parallel execution
if self.config.device_port is not None:
    for tool_config in platform_tools:
        tool_config.parameters['device_port'] = self.config.device_port
        tool_config.parameters['device_serial'] = f"emulator-{self.config.device_port}"
```

Isso funciona porque:
- `ToolConfig.parameters` vira `additional_params` em `TaskToolConfig` (platform.py:154)
- `EmulatorComponent.start_emulator()` le `device_port` de `additional_params` (emulator.py:114)
- `EmulatorComponent.install_app()` le `device_serial` de `additional_params` (emulator.py:176)

---

## Parte 3: --apks-filter

**Objetivo**: Permitir que rv-experiment processe apenas um subset de APKs (necessario para baseline/validacao paralela e para filtrar cal/holdout).

### Arquivos

| Arquivo | Mudanca |
|---------|---------|
| `modules/rv-experiment/src/rv_experiment/config.py` | Adicionar `apks_filter: Optional[str] = None` |
| `modules/rv-experiment/src/rv_experiment/__main__.py` | Adicionar `--apks-filter` option |
| `modules/rv-platform/src/rv_platform/config/platform_config.py` | Adicionar `apks_filter_file: Optional[str] = None` |
| `modules/rv-platform/src/rv_platform/platform.py` | Filtrar APKs em `_discover_apks()` |
| `modules/rv-experiment/src/rv_experiment/experiment/workflow/execution_controller.py` | Passar apks_filter ao PlatformConfig |

### Detalhes

O filtro precisa ser aplicado em dois niveis:
1. **Pre-processamento**: `ExperimentConfig.get_apk_list()` filtra APKs antes da instrumentacao
2. **Execucao**: `Platform._discover_apks()` filtra APKs antes da execucao de tasks

**config.py**:
```python
apks_filter: Optional[str] = Field(default=None,
    description="Path to text file listing APK filenames to process (one per line)")
```

**config.py** (`get_apk_list()`):
```python
def get_apk_list(self) -> List[str]:
    apks = [str(p) for p in Path(self.apks_dir).glob("*.apk")]
    if self.apks_filter:
        allowed = set(Path(self.apks_filter).read_text().strip().splitlines())
        apks = [a for a in apks if Path(a).name in allowed]
    if not apks:
        raise ConfigurationError(f"No APKs found after filtering")
    return apks
```

**platform_config.py**:
```python
apks_filter_file: Optional[str] = Field(default=None,
    description="Path to text file listing APK filenames to process")
```

**platform.py** (`_discover_apks()`):
```python
def _discover_apks(self) -> List[Path]:
    apks_dir = Path(self.config.apks_dir)
    apk_files = list(apks_dir.glob("*.apk"))
    if not apk_files:
        raise ValueError(f"No APK files found: {self.config.apks_dir}")

    # Filter APKs if filter file provided
    if self.config.apks_filter_file:
        allowed = set(Path(self.config.apks_filter_file).read_text().strip().splitlines())
        apk_files = [f for f in apk_files if f.name in allowed]
        if not apk_files:
            raise ValueError(f"No APKs match filter: {self.config.apks_filter_file}")
        self.logger.info(f"Filtered to {len(apk_files)} APKs from filter file")

    return sorted(apk_files)
```

**execution_controller.py** (`_create_platform_config`):
```python
platform_config = PlatformConfig(
    apks_dir=apks_dir,
    tools=platform_tools,
    ...,
    apks_filter_file=self.config.apks_filter
)
```

---

## Parte 4: Calibracao Paralela (Fases C/D)

**Objetivo**: Optuna roda N trials em paralelo, cada um em seu proprio emulador.

### Arquivos

| Arquivo | Mudanca |
|---------|---------|
| `modules/rv-agent-validation/src/rv_agent_validation/calibration/emulator_pool.py` | **NOVO** - Pool thread-safe de portas |
| `modules/rv-agent-validation/src/rv_agent_validation/calibration/runner.py` | Adicionar `device_port` param + `--name` unico |
| `modules/rv-agent-validation/src/rv_agent_validation/calibration/optimizer.py` | Adicionar `n_jobs` + EmulatorPool |
| `modules/rv-agent-validation/src/rv_agent_validation/calibration/cli.py` | Adicionar `--n-jobs` flag |

### EmulatorPool (novo, ~30 linhas)

```python
# calibration/emulator_pool.py
import queue

class EmulatorPool:
    """Thread-safe pool of emulator ports for parallel calibration."""

    def __init__(self, n_emulators: int, base_port: int = 5554):
        self._ports = queue.Queue()
        for i in range(n_emulators):
            self._ports.put(base_port + 2 * i)

    def acquire(self, timeout: float = None) -> int:
        """Acquire a port. Blocks until one is available."""
        return self._ports.get(timeout=timeout)

    def release(self, port: int) -> None:
        """Release a port back to the pool."""
        self._ports.put(port)
```

### CalibrationRunner

Adicionar `device_port` ao `run_trial()` e `--name` + `--device-port` ao `_build_command()`:

```python
def run_trial(self, trial_id: int, params: Dict[str, Any],
              device_port: Optional[int] = None) -> float:
    # ... existing code, mas passa device_port ao _build_command ...
    cmd = self._build_command(tool_spec, str(output_dir), trial_id, device_port)

def _build_command(self, tool_spec: str, output_dir: str,
                   trial_id: int, device_port: Optional[int] = None) -> List[str]:
    cmd = [
        "uv", "run", "rv-experiment", "run",
        "--tools", tool_spec,
        "--apks-dir", str(self.dataset_dir),
        "--skip-monitors", "--skip-instrument", "--skip-static",
        "--timeout", str(self.timeout),
        "--output-dir", output_dir,
        "--no-window",
        "--repetitions", "1",
        "--name", f"trial_{trial_id}",  # results_dir unico por trial
    ]
    if device_port is not None:
        cmd.extend(["--device-port", str(device_port)])
    if self.apks_filter:
        cmd.extend(["--apks-filter", str(self.apks_filter)])
    return cmd
```

**results_dir isolation**: Sem `--name`, rv-experiment cria `results/cli_experiment_TIMESTAMP/` que pode colidir em execucao paralela. Com `--name trial_{trial_id}`, cada trial cria `results/trial_42/` — isolamento garantido.

### CalibrationOptimizer

```python
def optimize(self, n_trials: int, timeout: Optional[int] = None,
             n_jobs: int = 1) -> Dict[str, Any]:
    # ...
    self.study.optimize(
        self._objective,
        n_trials=remaining,
        timeout=timeout,
        n_jobs=n_jobs,
        show_progress_bar=True
    )

def _objective(self, trial: optuna.Trial) -> float:
    # Acquire emulator port from pool
    device_port = None
    if self.emulator_pool:
        device_port = self.emulator_pool.acquire()

    try:
        score = self.trial_runner(trial.number, combined_params, device_port=device_port)
    finally:
        if self.emulator_pool and device_port is not None:
            self.emulator_pool.release(device_port)

    return score
```

### Calibration CLI

```python
@click.option('--n-jobs', type=int, default=1,
              help='Number of parallel trials (each uses 1 emulator)')
```

---

## Parte 5: --name no rv-experiment

**Objetivo**: Permitir definir nome do experimento via CLI para results_dir unico.

### Arquivos

| Arquivo | Mudanca |
|---------|---------|
| `modules/rv-experiment/src/rv_experiment/__main__.py` | Adicionar `--name` option |

**__main__.py**:
```python
@click.option('--name', type=str, default=None,
              help='Experiment name (used for results directory naming)')
```
E na criacao do ExperimentConfig: `name=name or auto_generated_name`.

O campo `name` ja existe no ExperimentConfig. So precisamos passar o valor do CLI.

---

## Parte 6: Script de Baseline/Validacao Paralela (Fases B/E)

**Objetivo**: Rodar baseline e validacao final com N emuladores em paralelo.

### Arquivo

| Arquivo | Mudanca |
|---------|---------|
| `scripts/parallel_run.py` | **NOVO** - Script para execucao paralela |

### Funcionamento

```bash
python scripts/parallel_run.py \
    --tools ape,fastbot,rvagent:pure_algorithm \
    --apks-dir ./data/calibration_dataset_v2 \
    --n-emulators 6 \
    --timeout 300 \
    --output-base ./results/baseline_v2 \
    --skip-preprocessing
```

O script:
1. Lista todos os APKs no diretorio
2. Divide em N grupos (round-robin)
3. Cria N arquivos temporarios de filtro (group_0.txt, group_1.txt, ...)
4. Lanca N processos rv-experiment em paralelo:
   ```bash
   uv run rv-experiment run \
       --tools ape,fastbot,rvagent:pure_algorithm \
       --apks-dir ./data/calibration_dataset_v2 \
       --apks-filter /tmp/group_0.txt \
       --device-port 5554 \
       --name baseline_v2_worker_0 \
       --skip-monitors --skip-instrument --skip-static \
       --timeout 300 \
       --output-dir ./results/baseline_v2/worker_0
   ```
5. Espera todos completarem
6. Cada worker gera resultados em diretorio separado (`worker_0/`, `worker_1/`, ...)
7. Opcional: agrega summary.csv de todos os workers

---

---

## Parte 7: Fix --apks-filter no Preprocessing (BUG)

**Status**: Pendente
**Descoberto em**: Mini-validation test (2026-02-07)

### Problema

O `--apks-filter` funciona na execucao (Platform._discover_apks()) mas **nao funciona no preprocessing**. Ao executar:

```
rv-experiment run --apks-dir /dir_557_apks/ --apks-filter 107_apks.txt --skip-execution
```

A instrumentacao processou TODOS os 557 APKs ao inves dos 107 filtrados.

### Causa raiz

```
get_apk_list() → 107 APKs filtrados (CORRETO, mas ignorado)
                     ↓ (descartado)
instrument_apks(apks_dir="/557_apks/") → utils.get_apks() → 557 APKs
                     ↓
instrumented_dir/ agora tem 557 APKs instrumentados
                     ↓
_get_target_apks_for_analysis() → lista 557 do instrumented_dir
                     ↓
static analysis roda em 557 APKs (deveria ser 107)
```

Em `PreProcessor._instrument_apks()` (pre_processor.py:158-167):
- Linha 158: `apk_list = self.config.get_apk_list()` — retorna 107 filtrados
- Linha 167: `instrumenter.instrument_apks(apks_dir=self.config.apks_dir)` — passa o diretorio RAW (557 APKs)
- A variavel `apk_list` e computada mas **descartada** — so usada para checar se vazia.

`RVInstrumentation.instrument_apks()` (rvandroid.py:179) so aceita `apks_dir: str` e chama `utils.get_apks(apks_dir)` que descobre TUDO no diretorio.

### Fix: 2 arquivos, ~15 linhas

**Arquivo 1**: `modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py`

Adicionar parametro opcional `apk_paths` ao `instrument_apks()`:

```python
def instrument_apks(self, apks_dir: str, results_dir: str,
                    force_instrumentation: bool = False,
                    apk_paths: Optional[List[str]] = None) -> InstrumentationResults:
```

Na linha 179, onde faz discovery:
```python
# ANTES:
apks = utils.get_apks(apks_dir)

# DEPOIS:
if apk_paths is not None:
    apks = [App(p) for p in apk_paths]
    self._logger.info(f"Using {len(apks)} APKs from provided list")
else:
    apks = utils.get_apks(apks_dir)
```

Backward-compatible: `apk_paths=None` por default.

**Arquivo 2**: `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py`

Mudanca 1 — `_instrument_apks()` (L166-168): Passar lista filtrada:

```python
# ANTES:
success = instrumenter.instrument_apks(
    apks_dir=self.config.apks_dir,
    results_dir=instrumented_dir
)

# DEPOIS:
success = instrumenter.instrument_apks(
    apks_dir=self.config.apks_dir,
    results_dir=instrumented_dir,
    apk_paths=apk_list
)
```

Mudanca 2 — `_get_target_apks_for_analysis()` (L303-318): Filtrar pelo set esperado:

```python
def _get_target_apks_for_analysis(self) -> List[str]:
    target_apks = []
    instrumented_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)
    expected_names = {os.path.basename(p) for p in self.config.get_apk_list()}

    if os.path.exists(instrumented_dir):
        for file in os.listdir(instrumented_dir):
            if file.endswith(EXTENSION_APK) and file in expected_names:
                target_apks.append(os.path.join(instrumented_dir, file))

    if not target_apks:
        target_apks.extend(self.config.get_apk_list())

    return target_apks
```

### Efeito cascata

Se a instrumentacao so produz 107 APKs no instrumented_dir, a static analysis automaticamente so analisa 107. A mudanca 2 e protecao extra para APKs de runs anteriores no diretorio.

---

## Resumo de Arquivos

| Arquivo | Acao | Parte |
|---------|------|-------|
| `rv-experiment/config.py` | EDIT: +3 campos (run_execution, device_port, apks_filter) | 1,2,3 |
| `rv-experiment/__main__.py` | EDIT: +4 opcoes (--skip-execution, --device-port, --apks-filter, --name) | 1,2,3,5 |
| `rv-experiment/experiment_controller.py` | EDIT: condicionar execucao | 1 |
| `rv-experiment/workflow/execution_controller.py` | EDIT: injetar device_port e apks_filter | 2,3 |
| `rv-platform/config/platform_config.py` | EDIT: +1 campo (apks_filter_file) | 3 |
| `rv-platform/platform.py` | EDIT: filtrar APKs em _discover_apks() | 3 |
| `rv-agent-validation/calibration/emulator_pool.py` | **NOVO**: ~30 linhas | 4 |
| `rv-agent-validation/calibration/runner.py` | EDIT: device_port + name + apks_filter | 4 |
| `rv-agent-validation/calibration/optimizer.py` | EDIT: n_jobs + EmulatorPool | 4 |
| `rv-agent-validation/calibration/cli.py` | EDIT: --n-jobs | 4 |
| `scripts/parallel_run.py` | **NOVO**: ~100 linhas | 6 |
| `rv-instrumentation/rvandroid.py` | EDIT: +apk_paths param | 7 |
| `rv-experiment/workflow/pre_processor.py` | EDIT: passar apk_list + filtrar static analysis | 7 |
| `scripts/validation/fase_a_preprocess.py` | **NOVO**: ~300 linhas | 9 |
| `scripts/filter_apks_static_analysis.py` | EDIT: +`--apks-list` | 9 |

## Ordem de Implementacao

1. ✅ **Parte 1**: --skip-execution (3 arquivos, ~15 linhas) — desbloqueia Fase A
2. ✅ **Parte 5**: --name (1 arquivo, ~5 linhas) — prerequisito das partes 4 e 6
3. ✅ **Parte 2**: --device-port (3 arquivos, ~15 linhas) — prerequisito das partes 4 e 6
4. ✅ **Parte 3**: --apks-filter execucao (4 arquivos, ~25 linhas) — prerequisito da parte 6
5. ✅ **Parte 4**: Calibracao paralela (4 arquivos, ~60 linhas) — desbloqueia Fases C/D
6. ✅ **Parte 6**: Script paralelo (1 arquivo novo, ~100 linhas) — desbloqueia Fases B/E
7. ✅ **Parte 7**: Fix apks-filter preprocessing (2 arquivos, ~15 linhas) — fix critico para Fase A
8. ✅ **Parte 8**: Fix kill_emulator paralelismo (2 arquivos, ~20 linhas) — fix critico para execucao paralela
9. ✅ **Parte 9**: Fase A preprocessing paralelo (1 novo + 1 edit) — desbloqueia Fase A paralela

## Verificacao

### Testes unitarios (Partes 1-6)
1. rv-experiment: 7/7 passed
2. rv-platform: 44/44 passed
3. rv-agent-validation: 3/3 non-LLM passed

### Mini-validation test (Parte 7 + end-to-end)

```bash
export RVSEC_HOME="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec"
APKS_DIR="/home/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS"

# Step 1: Preprocessing (testa --skip-execution + --apks-filter no preprocessing)
uv run rv-experiment run \
  --tools monkey \
  --apks-dir $APKS_DIR \
  --apks-filter ./results/mini_validation/filter_2apks.txt \
  --specification-set jca \
  --timeout 60 \
  --skip-execution \
  --name mini_preprocess \
  --no-window

# Validar: apenas 2 APKs instrumentados
ls results/mini_preprocess/instrumented_apks/*.apk | wc -l  # deve ser 2

# Step 2: Execucao paralela (testa parallel_run.py + --device-port + --name)
python scripts/parallel_run.py \
  --tools monkey \
  --apks-dir ./results/mini_preprocess/instrumented_apks \
  --n-emulators 2 \
  --timeout 60 \
  --output-base ./results/mini_parallel \
  --skip-preprocessing

# Validar: 2 workers, cada um com 1 APK, portas diferentes
```

Checklist de validacao:
1. `instrumented_apks/` contem EXATAMENTE 2 APKs (nao 557)
2. Static analysis rodou nos 2 APKs (.gesda, .wtg, .reach)
3. Cada worker usou porta diferente (5554, 5556)
4. Cada worker processou 1 APK
5. summary.csv existe em cada worker
6. Sem colisao de results_dir

## Parte 8: Fix kill_emulator para paralelismo

**Status**: ✅ Implementado
**Descoberto em**: Mini-validation test — Worker 1 falhou com monkey exit code 255

### Problema

`Android.kill_emulator()` executava 3 operacoes:
1. `adb -s {device} emu kill` — device-specific (correto)
2. `adb -s {device} kill-server` — **GLOBAL** (ignora `-s`, mata o ADB server do host inteiro)
3. `rm ~/.android/avd/{avd}.avd/*.lock` — **shared** (afeta AVD compartilhado em modo `-read-only`)

Quando Worker 0 terminava primeiro e executava `kill-server`, o ADB server era morto globalmente,
desconectando o emulator do Worker 1 → monkey exit code 255.

### Fix

**android.py**:
- `kill_emulator`: Remover `kill-server` e `rm *.lock`. Manter apenas `emu kill` (device-specific).
- `create_emulator`: Adicionar `device_port` param, propagar `device_name` para `kill_emulator`.

**test_android.py**:
- `test_kill_emulator`: Usar serial nao-default (`emulator-5556`) para provar propagacao.
- `test_create_emulator_*`: Testar com `device_port=5556`, verificar que `kill_emulator` recebe `"emulator-5556"`.

### Arquivos

| Arquivo | Mudanca |
|---------|---------|
| `rv-android-core/util/android/android.py` | `kill_emulator`: -kill-server -rm-locks. `create_emulator`: +device_port |
| `rv-android-core/tests/util/android/test_android.py` | 3 testes atualizados |

---

## Parte 9: Script Paralelo para Fase A (Preprocessing)

**Status**: ✅ Implementado
**Objetivo**: Paralelizar instrumentacao e analise estatica da Fase A (~14h → ~2.5h com 6 workers)

### Arquivos

| Arquivo | Mudanca |
|---------|---------|
| `scripts/validation/fase_a_preprocess.py` | **NOVO**: Script com 3 fases macro, ProcessPoolExecutor para instrumentacao |
| `scripts/filter_apks_static_analysis.py` | EDIT: adicionar `--apks-list` como alternativa ao `--csv` |

### Arquitetura

```
Fase 1: Gerar monitores (sequencial, ~2 min)
    ↓
Fase 2: Instrumentar APKs (ProcessPoolExecutor, N workers, ~55 min)
    ↓
Fase 3: Analise estatica nos originais (subprocess → filter_apks_static_analysis.py, N workers, ~90 min)
```

### Isolamento de Workers (Fase 2)

Cada worker usa um `working_dir` unico para evitar race conditions:
- `working_dir = output_dir/workers/worker_{id}/` — CWD para d8 (classes.dex)
- `tmp_dir = working_dir/tmp` — isolado por worker
- `rvm_tmp_dir = working_dir/rvm_tmp` — isolado por worker
- `lib_tmp_dir` — compartilhado (read-only apos Maven)
- `monitors_dir` — compartilhado (read-only)
- `instrumented_dir` — compartilhado (filenames unicos por APK)
- `dex2jar_home` — compartilhado (read-only)

### Uso

```bash
python scripts/validation/fase_a_preprocess.py \
  --apks-dir /home/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS \
  --apks-filter ./out/static_analysis_filter/passed_apks.txt \
  --specification-set jca \
  --output-dir ./results/preprocessing_v2 \
  --max-workers 6
```

### Flags de skip

- `--skip-monitors`: Reutiliza monitores existentes em `output-dir/monitors`
- `--skip-instrumentation`: Reutiliza APKs instrumentados existentes
- `--skip-static`: Pula analise estatica

---

## Notas

- **Simplicidade**: Paralelismo EXTERNO (processos independentes) em vez de threading interno no Platform. Cada rv-experiment e isolado.
- **Sem mudanca no Platform._execute_tasks()**: A execucao sequencial dentro de cada processo esta OK. O paralelismo e entre processos.
- **SQLite do Optuna**: Ja suporta acesso concorrente. Nao precisa de mudanca.
- **AVDs**: Precisam de 5 AVDs adicionais (clones do RVSec) OU usar `emulator -read-only` para compartilhar a mesma imagem.
- **SA files flat**: O `StaticAnalysisComponent` do rv-platform busca `.gesda`, `.wtg`, `.reach` no **mesmo diretorio dos APKs** (flat, sem subdiretorios). O arquivo `.methods` nao e utilizado — o REACH fornece a estrutura de classes/metodos para cobertura.
- **Output/Results dirs**: Cada processo paralelo DEVE ter output_dir e name unicos para evitar sobrescrita.

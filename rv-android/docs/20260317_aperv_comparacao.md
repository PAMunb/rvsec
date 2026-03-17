# Experimento 3: APE-RV LLM Baseline — Comparação com Todas as Ferramentas

**Data**: 2026-03-17
**Janela de execução**: 2026-03-17 ~14:30 → 2026-03-18 09:00 (~18.5h)
**Objetivo**: Medir o efeito da integração LLM no APE-RV (gh6) com parâmetros default, sem calibração, e comparar com todos os resultados anteriores.

---

## 1. Contexto

### 1.1 Resultados Anteriores (169 APKs, 600s, JCA, mesma infraestrutura)

| Experimento | Ferramenta | Method Cov | Activity Cov | MOP Cov | Violation Types | APKs c/ Violação |
|-------------|-----------|-----------|-------------|---------|-----------------|------------------|
| exp1 (03-13) | **aperv:sata_mop_v1** (500/300/100) | **28.35%** | — | **37.02%** | **23** | **80/169 (47.3%)** |
| exp1 (03-13) | ape (original) | 27.82% | — | 37.08% | 23 | 76/169 (45.0%) |
| exp1 (03-13) | aperv:sata (sem MOP) | 27.28% | — | 35.49% | 20 | 76/169 (45.0%) |
| exp2 (03-15) | aperv:sata_mop_v2 (100/60/20) | 27.35% | — | 36.35% | 20 | 79/169 (46.7%) |
| exp2 (03-15) | rvsmart:mvp | 24.24% | — | 31.53% | 23 | 72/169 (42.6%) |

**Ranking atual (method coverage)**: aperv:sata_mop_v1 > ape > aperv:sata_mop_v2 ≈ aperv:sata > rvsmart:mvp

### 1.2 O Que Mudou (gh6 APE-RV LLM Integration)

O APE-RV Java recebeu integração LLM via SGLang (Qwen3-VL-4B-Instruct):
- **2 modos de roteamento**: new-state (LLM na primeira visita a cada estado) e stagnation (LLM quando o grafo estagna)
- **6 classes copiadas do rvsmart**: SglangClient, ScreenshotCapture, ImageProcessor, ToolCallParser, CoordinateNormalizer, LlmCircuitBreaker
- **ApePromptBuilder + LlmRouter**: prompt adaptado para GUITree do APE, mapeamento de coordenadas com bounds containment + Euclidean fallback
- **MOP weights revertidos para v1** (500/300/100) — os melhores pesos dos experimentos anteriores
- O `aperv-tool` Python (gh41) registra 2 novos variants e gera 9 chaves `ape.llm*` no `ape.properties`

### 1.3 Hipóteses

- **H1 — LLM melhora cobertura**: `aperv:sata_mop_llm` > `aperv:sata_mop_v1` em method coverage, porque o LLM quebra padrões determinísticos do SATA e identifica elementos de UI semanticamente relevantes
- **H2 — Overhead aceitável**: LLM adiciona no máximo 30% de overhead temporal (60-110 chamadas × 3-5s = 180-550s em 600s de run)
- **Null hypothesis**: LLM PODE piorar cobertura se o overhead de latência reduzir o throughput de exploração além do que o LLM compensa com decisões melhores (como ocorreu com rvsmart af17 hybrid em 03-10)

---

## 2. Configuração do Experimento

### 2.1 Parâmetros

| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| Dataset | 169 APKs | Mesmo set dos exp1/exp2 para comparação direta |
| Ferramentas | `aperv:sata_mop_llm` | LLM + MOP v1 (500/300/100) — melhor config + LLM |
| Timeout | 600s | Padrão dos experimentos anteriores |
| Repetições | 3 | Mesma base estatística dos exp anteriores |
| Containers | 8 | ~21 APKs cada, carga confortável no SGLang |
| Specification set | JCA | Padrão dos experimentos anteriores |
| Skip flags | monitors, instrument, static analysis | APKs pré-instrumentados em `data/apks/` |
| Docker image | `phtcosta/rvandroid:0.8.0` (rebuild) | Inclui novo ape-rv.jar com LLM |

### 2.2 Total de Tasks

```
169 APKs × 1 ferramenta × 3 reps = 507 tasks
8 containers → ~64 tasks/container
~64 × 680s ÷ 3600 = ~12.1h
```

### 2.3 Parâmetros LLM (defaults do gh6, sem calibração)

| Chave `ape.properties` | Valor | Origem |
|------------------------|-------|--------|
| `ape.llmUrl` | `http://10.0.2.2:30000/v1` | Variant config (emulador → host via socat) |
| `ape.llmOnNewState` | `true` | LLM na primeira visita a cada estado (~50-100 calls/run) |
| `ape.llmOnStagnation` | `true` | LLM quando grafo estagna (~5-10 calls/run) |
| `ape.llmModel` | `default` | SGLang usa o modelo carregado |
| `ape.llmTemperature` | `0.3` | Baixa temperatura para ações determinísticas |
| `ape.llmTopP` | `0.6` | Sampling conservador |
| `ape.llmTopK` | `50` | Padrão |
| `ape.llmTimeoutMs` | `15000` | 15s timeout por chamada LLM |
| `ape.llmMaxCalls` | `200` | Máximo 200 chamadas LLM por run |

**Estimativa de overhead LLM**: 60-110 chamadas × 3-5s = 180-550s de tempo LLM em 600s de run. Restam 50-420s para exploração pura. O overhead é significativo mas aceitável para baseline.

---

## 3. Infraestrutura

### 3.1 Rede LLM (Socat Bridge)

O emulador Android conecta via `10.0.2.2:30000` (host do container). O `docker-entrypoint.sh` já possui um socat bridge (linhas 117-125) ativado por `RVSMART_LLM_MODE=true`:

```bash
# docker-entrypoint.sh (existente)
if [ "${RVSMART_LLM_MODE:-false}" = "true" ]; then
    socat TCP-LISTEN:30000,bind=127.0.0.1,fork,reuseaddr TCP:sglang:30000 &
fi
```

**Fluxo**: emulador → `10.0.2.2:30000` → container `127.0.0.1:30000` (socat) → Docker network `sglang:30000` → SGLang server

O env var `RVSMART_LLM_MODE=true` é genérico — funciona para qualquer ferramenta. Usamos ele no compose.

### 3.2 SGLang Server

SGLang roda como serviço no compose (mesmo padrão do `docker-compose.comparacao.yml`):
- Imagem: `lmsysorg/sglang:latest`
- Modelo: `Qwen/Qwen3-VL-4B-Instruct` (~8GB VRAM)
- GPU: 1× NVIDIA
- Healthcheck: `curl http://localhost:30000/health` (120s start_period)
- Capacidade: ~2-4 req/s com batch inference → 8 containers × 0.15 req/s = 1.2 req/s (confortável)

### 3.3 Docker Compose

**Arquivo**: `docker/docker-compose.exp3-aperv-llm.yml`

```yaml
# Experiment 3: APE-RV LLM baseline — aperv:sata_llm + aperv:sata_mop_llm
# 10 containers, 169 APKs, 600s timeout, 2 reps, JCA specs.
# Requires GPU for SGLang (Qwen3-VL-4B-Instruct).
#
# Usage:
#   docker compose -f docker/docker-compose.exp3-aperv-llm.yml up -d
#   bash scripts/monitor_exp3.sh
#   docker compose -f docker/docker-compose.exp3-aperv-llm.yml down

x-rvandroid: &rvandroid-base
  image: phtcosta/rvandroid:0.8.0
  environment: &rvandroid-env
    RV_TOOLS: "aperv:sata_llm,aperv:sata_mop_llm"
    RV_TIMEOUTS: "600"
    RV_REPETITIONS: "2"
    RV_NO_WINDOW: "true"
    RV_JCA_SPEC: "true"
    RV_SKIP_MONITORS: "true"
    RV_SKIP_INSTRUMENT: "true"
    RV_SKIP_STATIC_ANALYSIS: "true"
    RV_APKS_DIR: "/opt/rvsec/rv-android/apks"
    RV_DEVICE_PORT: "5554"
    RVSMART_LLM_MODE: "true"
  devices:
    - /dev/kvm:/dev/kvm
  deploy:
    resources:
      limits:
        cpus: "4"
        memory: "10g"
  depends_on:
    sglang:
      condition: service_healthy

services:
  sglang:
    image: lmsysorg/sglang:latest
    container_name: sglang-server
    volumes:
      - ${HF_CACHE:-/pedro/desenvolvimento/.cache/huggingface}:/root/.cache/huggingface
    ipc: host
    shm_size: "16g"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    command: >
      python3 -m sglang.launch_server
      --model-path Qwen/Qwen3-VL-4B-Instruct
      --host 0.0.0.0
      --port 30000
      --trust-remote-code
      --attention-backend flashinfer
      --tool-call-parser qwen
      --enable-multimodal
      --context-length 8192
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:30000/health"]
      interval: 30s
      timeout: 10s
      retries: 10
      start_period: 120s

  exp3_00:
    <<: *rvandroid-base
    container_name: exp3_00
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: exp3_00
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/exp3_batch_00.txt"
      RV_DELAY: "0"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/exp3_00:/opt/rvsec/rv-android/results

  exp3_01:
    <<: *rvandroid-base
    container_name: exp3_01
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: exp3_01
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/exp3_batch_01.txt"
      RV_DELAY: "10"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/exp3_01:/opt/rvsec/rv-android/results

  exp3_02:
    <<: *rvandroid-base
    container_name: exp3_02
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: exp3_02
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/exp3_batch_02.txt"
      RV_DELAY: "20"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/exp3_02:/opt/rvsec/rv-android/results

  exp3_03:
    <<: *rvandroid-base
    container_name: exp3_03
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: exp3_03
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/exp3_batch_03.txt"
      RV_DELAY: "30"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/exp3_03:/opt/rvsec/rv-android/results

  exp3_04:
    <<: *rvandroid-base
    container_name: exp3_04
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: exp3_04
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/exp3_batch_04.txt"
      RV_DELAY: "40"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/exp3_04:/opt/rvsec/rv-android/results

  exp3_05:
    <<: *rvandroid-base
    container_name: exp3_05
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: exp3_05
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/exp3_batch_05.txt"
      RV_DELAY: "50"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/exp3_05:/opt/rvsec/rv-android/results

  exp3_06:
    <<: *rvandroid-base
    container_name: exp3_06
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: exp3_06
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/exp3_batch_06.txt"
      RV_DELAY: "60"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/exp3_06:/opt/rvsec/rv-android/results

  exp3_07:
    <<: *rvandroid-base
    container_name: exp3_07
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: exp3_07
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/exp3_batch_07.txt"
      RV_DELAY: "70"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/exp3_07:/opt/rvsec/rv-android/results

  exp3_08:
    <<: *rvandroid-base
    container_name: exp3_08
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: exp3_08
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/exp3_batch_08.txt"
      RV_DELAY: "80"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/exp3_08:/opt/rvsec/rv-android/results

  exp3_09:
    <<: *rvandroid-base
    container_name: exp3_09
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: exp3_09
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/exp3_batch_09.txt"
      RV_DELAY: "90"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/exp3_09:/opt/rvsec/rv-android/results
```

### 3.4 Setup Script

**Arquivo**: `scripts/setup_exp3.sh`

```bash
#!/bin/bash
# Setup for experiment 3: APE-RV LLM baseline.
# Generates batch files for 10 containers from 169 APKs already in data/apks/.
#
# Usage:
#   cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
#   bash scripts/setup_exp3.sh

set -e

DATA_DIR="data"
APK_DIR="$DATA_DIR/apks"
CONTAINERS=10
APK_LIST="$APK_DIR/available_169.txt"

echo "=== Experiment 3: APE-RV LLM Baseline ==="
echo "APKs: $(wc -l < "$APK_LIST") (from $APK_LIST)"
echo "Containers: $CONTAINERS"
echo "Tools: aperv:sata_llm, aperv:sata_mop_llm"
echo "Reps: 2"
echo ""

# 1. Create result directories
echo "[1/3] Creating result directories..."
for i in $(seq 0 $((CONTAINERS - 1))); do
    dir=$(printf "$DATA_DIR/results/exp3_%02d" $i)
    mkdir -p "$dir"
done

# 2. Generate batch files (round-robin split for balanced distribution)
echo "[2/3] Generating batch files..."
rm -f "$APK_DIR"/exp3_batch_*.txt

cd "$APK_DIR"
split -n r/$CONTAINERS -d -a 2 --additional-suffix=.txt \
    "available_169.txt" exp3_batch_
cd ../..

# 3. Verify
echo ""
echo "[3/3] Verification"
echo "  APKs:  $(ls "$APK_DIR"/*.apk 2>/dev/null | wc -l)"
echo "  JSONs: $(ls "$APK_DIR"/*.apk.json 2>/dev/null | wc -l)"
echo ""
echo "  Batches:"
total_apks=0
for b in "$APK_DIR"/exp3_batch_*.txt; do
    n=$(wc -l < "$b")
    total_apks=$((total_apks + n))
    echo "    $(basename $b): $n APKs"
done
echo "  Total: $total_apks APKs across $CONTAINERS batches"
echo ""

tasks=$((total_apks * 2 * 2))
echo "  Expected tasks: $tasks (${total_apks} APKs × 2 tools × 2 reps)"
est_hours=$(echo "scale=1; ($tasks / $CONTAINERS + 1) * 680 / 3600" | bc)
echo "  Estimated wall time: ~${est_hours}h (com overhead LLM)"

echo ""
echo "=== Setup Complete ==="
echo "Next:"
echo "  1. Rebuild Docker image:"
echo "     cd docker/rvandroid && bash build.sh"
echo "  2. Run experiment:"
echo "     docker compose -f docker/docker-compose.exp3-aperv-llm.yml up -d"
echo "  3. Monitor:"
echo "     watch -n 60 bash scripts/monitor_exp3.sh"
```

### 3.5 Monitor Script

**Arquivo**: `scripts/monitor_exp3.sh`

```bash
#!/bin/bash
# Monitor progress of experiment 3: APE-RV LLM baseline.
#
# Usage:
#   bash scripts/monitor_exp3.sh
#   watch -n 60 bash scripts/monitor_exp3.sh

RESULTS_DIR="${1:-data/results}"
CONTAINERS="exp3_00 exp3_01 exp3_02 exp3_03 exp3_04 exp3_05 exp3_06 exp3_07 exp3_08 exp3_09"
EXPECTED=676  # 169 APKs × 2 tools × 2 reps

echo "=== Experiment 3: APE-RV LLM Baseline ($(date '+%Y-%m-%d %H:%M:%S')) ==="
echo ""

printf "%-10s %-12s %5s %5s %5s %5s  %s\n" \
    "Container" "Status" "Done" "Fail" "Total" "%" "Last tool"
printf "%-10s %-12s %5s %5s %5s %5s  %s\n" \
    "----------" "------" "----" "----" "-----" "---" "---------"

total_completed=0
total_failed=0
total_tasks=0

for c in $CONTAINERS; do
    dir="$RESULTS_DIR/$c"
    status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null || echo "gone")

    tasks_file="$dir/$c/tasks.json"
    completed=0
    failed=0
    ntasks=0
    last_tool="-"
    if [ -f "$tasks_file" ]; then
        read completed failed ntasks last_tool < <(python3 -c "
import json
with open('$tasks_file') as f:
    data = json.load(f)
tasks = data.get('tasks', [])
c = sum(1 for t in tasks if t.get('result',{}).get('state') == 'COMPLETED')
f = sum(1 for t in tasks if t.get('result',{}).get('state') in ('FAILED', 'ERROR'))
last = '-'
for t in reversed(tasks):
    if t.get('result',{}).get('state') in ('COMPLETED','FAILED','ERROR'):
        last = t.get('tool','?')
        break
print(c, f, len(tasks), last)
" 2>/dev/null || echo "0 0 0 -")
    fi

    total_completed=$((total_completed + completed))
    total_failed=$((total_failed + failed))
    total_tasks=$((total_tasks + ntasks))

    done_count=$((completed + failed))
    if [ "$ntasks" -gt 0 ]; then
        pct=$((100 * done_count / ntasks))
    else
        pct=0
    fi

    printf "%-10s %-12s %5d %5d %5d %4d%%  %s\n" \
        "$c" "$status" "$completed" "$failed" "$ntasks" "$pct" "$last_tool"
done

echo ""
remaining=$((EXPECTED - total_completed - total_failed))
if [ $remaining -lt 0 ]; then remaining=0; fi
pct_total=0
if [ $EXPECTED -gt 0 ]; then
    pct_total=$((100 * (total_completed + total_failed) / EXPECTED))
fi

echo "Overall: $total_completed completed, $total_failed failed, $remaining remaining [$pct_total%]"

# ETA calculation
if [ $total_completed -gt 0 ]; then
    start_ts=$(python3 -c "
import json, os
from pathlib import Path
earliest = None
for i in range(10):
    tf = Path('$RESULTS_DIR') / f'exp3_{i:02d}' / f'exp3_{i:02d}' / 'tasks.json'
    if tf.exists():
        ts = os.path.getmtime(tf)
        if earliest is None or ts < earliest:
            earliest = ts
if earliest:
    print(f'{earliest:.0f}')
else:
    print('0')
" 2>/dev/null)
    if [ "$start_ts" != "0" ] && [ -n "$start_ts" ]; then
        now=$(date +%s)
        elapsed=$((now - ${start_ts%.*}))
        done_count=$((total_completed + total_failed))
        if [ $done_count -gt 0 ] && [ $remaining -gt 0 ]; then
            secs_per_task=$((elapsed / done_count))
            eta_secs=$((secs_per_task * remaining / 10))
            eta_hours=$(echo "scale=1; $eta_secs / 3600" | bc 2>/dev/null || echo "?")
            eta_time=$(date -d "+${eta_secs} seconds" '+%H:%M' 2>/dev/null || echo "?")
            echo "Pace: ${secs_per_task}s/task | ETA: ~${eta_hours}h (finish ~${eta_time})"
        fi
        elapsed_h=$(echo "scale=1; $elapsed / 3600" | bc 2>/dev/null || echo "?")
        echo "Elapsed: ${elapsed_h}h"
    fi
fi

# SGLang health check
echo ""
sglang_status=$(docker inspect --format='{{.State.Status}}' sglang-server 2>/dev/null || echo "not running")
echo "SGLang: $sglang_status"
if [ "$sglang_status" = "running" ]; then
    sglang_health=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:30000/health 2>/dev/null || echo "unreachable")
    echo "SGLang health: $sglang_health"
fi
```

### 3.6 Consolidation Script

**Arquivo**: `scripts/consolidate_exp3.py`

```python
"""Consolidate experiment 3 results and merge with exp1+exp2 for 7-tool comparison.

Exp1 (2026-03-13): ape, aperv:sata, aperv:sata_mop_v1 (500/300/100)
Exp2 (2026-03-15): aperv:sata_mop_v2 (100/60/20), rvsmart:mvp
Exp3 (2026-03-17): aperv:sata_llm, aperv:sata_mop_llm (LLM baseline, 2 reps)

Output: 7 tools in one CSV for comparative analysis.

Usage:
    cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
    uv run python scripts/consolidate_exp3.py
"""

import json
from pathlib import Path

import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "data" / "results"

EXP1_CSV = RESULTS_DIR / "aperv_comparacao_consolidated.csv"
EXP2_CONTAINERS = [f"exp2_{i:02d}" for i in range(10)]
EXP3_CONTAINERS = [f"exp3_{i:02d}" for i in range(10)]
OUTPUT_CSV = RESULTS_DIR / "exp3_consolidated.csv"

COLUMN_MAP = {
    "cov_act": "activity_coverage",
    "cov_method": "method_coverage",
    "cov_rv_method": "mop_coverage",
    "errors": "total_errors",
}

UNIFIED_COLS = ["apk", "tool", "rep", "status", "duration_s",
                "method_coverage", "activity_coverage", "mop_coverage", "total_errors"]


def load_containers(containers: list[str], rename_map: dict | None = None) -> pd.DataFrame:
    """Load results from a set of containers."""
    frames = []
    for container in containers:
        base = RESULTS_DIR / container / container
        summary_path = base / "summary.csv"
        tasks_path = base / "tasks.json"

        if not summary_path.exists():
            print(f"  WARN: {summary_path} not found, skipping")
            continue

        df = pd.read_csv(summary_path)

        if tasks_path.exists():
            with open(tasks_path) as f:
                tasks_data = json.load(f)
            status_map = {}
            duration_map = {}
            for task in tasks_data["tasks"]:
                cfg = task["config"]
                tc = cfg["tool_config"]
                tool_name = f"{tc['name']}:{tc['variant']}" if tc.get("variant") else tc["name"]
                key = (cfg["apk_name"], tool_name, cfg["repetition"])
                status_map[key] = task["result"]["state"]
                duration_map[key] = task["result"].get("execution_time_seconds", 0)

            df["status"] = df.apply(
                lambda r: status_map.get((r["apk"], r["tool"], r["rep"]), "UNKNOWN"),
                axis=1,
            )
            df["duration_s"] = df.apply(
                lambda r: duration_map.get((r["apk"], r["tool"], r["rep"]), 0),
                axis=1,
            )

            completed_keys = set(zip(df["apk"], df["tool"], df["rep"]))
            for (apk, tool, rep), state in status_map.items():
                if state != "COMPLETED" and (apk, tool, rep) not in completed_keys:
                    frames.append(pd.DataFrame([{
                        "apk": apk, "rep": rep, "timeout": 600, "tool": tool,
                        "cov_act": 0.0, "cov_method": 0.0, "cov_rv_method": 0.0,
                        "errors": 0, "status": state,
                        "duration_s": duration_map.get((apk, tool, rep), 0),
                    }]))
        else:
            df["status"] = "COMPLETED"
            df["duration_s"] = 600

        frames.append(df)

    result = pd.concat(frames, ignore_index=True)
    result = result.rename(columns=COLUMN_MAP)

    if rename_map:
        for old, new in rename_map.items():
            result.loc[result["tool"] == old, "tool"] = new

    return result[UNIFIED_COLS]


def load_exp1() -> pd.DataFrame:
    """Load exp1 consolidated results."""
    df = pd.read_csv(EXP1_CSV)
    df.loc[df["tool"] == "aperv:sata_mop", "tool"] = "aperv:sata_mop_v1"
    return df


def print_summary(df: pd.DataFrame) -> None:
    """Print per-tool summary statistics."""
    completed = df[df["status"] == "COMPLETED"]
    metrics = ["method_coverage", "activity_coverage", "mop_coverage"]

    print("=" * 100)
    print("EXPERIMENT 3 + EXP1 + EXP2 — CONSOLIDATED SUMMARY (7 tools)")
    print("=" * 100)

    print("\n--- Task Counts ---")
    for tool in sorted(df["tool"].unique()):
        g = df[df["tool"] == tool]
        total = len(g)
        ok = (g["status"] == "COMPLETED").sum()
        err = total - ok
        apks = g["apk"].nunique()
        reps = g["rep"].max()
        print(f"  {tool:25s}: {total:4d} tasks ({ok} ok, {err} fail) | {apks} APKs × {reps} reps")

    print("\n--- Per-APK Mean Coverage (averaged across reps, then APKs) ---")
    apk_means = completed.groupby(["tool", "apk"])[metrics].mean().groupby("tool").mean()
    for tool in sorted(apk_means.index):
        row = apk_means.loc[tool]
        print(f"  {tool:25s}  method={row['method_coverage']:.2f}%  "
              f"activity={row['activity_coverage']:.2f}%  mop={row['mop_coverage']:.2f}%")

    print("\n--- Wilcoxon Signed-Rank Tests (method_coverage, paired by APK) ---")
    apk_tool = completed.groupby(["tool", "apk"])["method_coverage"].mean().reset_index()

    pairs = [
        ("aperv:sata_mop_v1", "aperv:sata_mop_llm"),
        ("aperv:sata", "aperv:sata_llm"),
        ("ape", "aperv:sata_mop_llm"),
        ("aperv:sata_mop_llm", "aperv:sata_llm"),
        ("aperv:sata_mop_llm", "rvsmart:mvp"),
        ("aperv:sata_mop_v1", "aperv:sata_llm"),
    ]

    for t1, t2 in pairs:
        d1 = apk_tool[apk_tool["tool"] == t1].set_index("apk")["method_coverage"]
        d2 = apk_tool[apk_tool["tool"] == t2].set_index("apk")["method_coverage"]
        common = d1.index.intersection(d2.index)
        if len(common) < 10:
            print(f"  {t1:25s} vs {t2:25s}: too few pairs ({len(common)})")
            continue
        v1, v2 = d1.loc[common], d2.loc[common]
        delta = v2 - v1
        try:
            stat, pval = stats.wilcoxon(v1, v2, alternative="two-sided")
            direction = ">" if delta.mean() > 0 else "<" if delta.mean() < 0 else "="
            sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else "ns"
            print(f"  {t1:25s} vs {t2:25s}: p={pval:.4f} {sig:3s}  "
                  f"delta={delta.mean():+.2f}pp  {t2}{direction}{t1}  (N={len(common)})")
        except ValueError as e:
            print(f"  {t1:25s} vs {t2:25s}: {e}")


def main():
    print("Loading experiment 1...")
    exp1 = load_exp1()
    print(f"  {len(exp1)} rows ({exp1['tool'].nunique()} tools)")

    print("Loading experiment 2...")
    exp2 = load_containers(EXP2_CONTAINERS, rename_map={"aperv:sata_mop": "aperv:sata_mop_v2"})
    print(f"  {len(exp2)} rows ({exp2['tool'].nunique()} tools)")

    print("Loading experiment 3...")
    exp3 = load_containers(EXP3_CONTAINERS)
    print(f"  {len(exp3)} rows ({exp3['tool'].nunique()} tools)")

    all_df = pd.concat([exp1, exp2, exp3], ignore_index=True)
    print(f"\nTotal: {len(all_df)} rows, {all_df['tool'].nunique()} tools")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved to {OUTPUT_CSV}\n")

    print_summary(all_df)


if __name__ == "__main__":
    main()
```

---

## 4. Pré-requisitos de Execução

### 4.1 Checklist

```
[ ] 1. Push do commit gh41 (SSH fix: ssh-add ~/.ssh/id_ed25519)
       git push

[ ] 2. Rebuild Docker image (inclui novo ape-rv.jar com LLM)
       cd docker/rvandroid && bash build.sh

[ ] 3. Setup: batch files + result directories
       bash scripts/setup_exp3.sh

[ ] 4. Validação rápida (1 container + 1 APK + 1 tool)
       docker compose -f docker/docker-compose.exp3-aperv-llm.yml run --rm \
         -e RV_TOOLS="aperv:sata_mop_llm" \
         -e RV_APKS_FILTER="" \
         -e RV_REPETITIONS="1" \
         -e RV_TIMEOUTS="120" \
         -e RV_DELAY="0" \
         exp3_00

       # Verificar nos logs:
       # - "Socat bridge started" (socat ativo)
       # - "ape.llmUrl=" no ape.properties (chaves LLM presentes)
       # - LLM calls nos logs do ape-rv (evidência de chamadas)
       # - SGLang respondendo (sem timeouts massivos)

[ ] 5. Lançar experimento completo
       docker compose -f docker/docker-compose.exp3-aperv-llm.yml up -d
```

### 4.2 Notas sobre a Imagem Docker

O Dockerfile faz `git clone --branch modules` + `mvn clean install` + `uv sync`. Portanto:
- O commit gh41 PRECISA estar pushed antes do build
- O `mvn install` dentro do Dockerfile compila o ape-rv.jar a partir do source
- O `uv sync` instala o aperv-tool Python com os novos variants

---

## 5. Execução

```bash
# 1. Setup
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
bash scripts/setup_exp3.sh

# 2. Launch
docker compose -f docker/docker-compose.exp3-aperv-llm.yml up -d

# 3. Monitor (a cada minuto)
watch -n 60 bash scripts/monitor_exp3.sh

# 4. Quando completar (~12-13h)
docker compose -f docker/docker-compose.exp3-aperv-llm.yml down

# 5. Consolidar resultados
uv run python scripts/consolidate_exp3.py
```

---

## 5.1 Verificação de Traces (Sanity Check LLM)

Após as primeiras tarefas completarem (~30-60 min), verificar os arquivos `.trace` para confirmar que o LLM está funcionando e não há anomalias/bugs. Rodar o script abaixo ou inspecionar manualmente.

### O que verificar nos traces

1. **LLM está sendo chamado**: procurar por `LlmRouter` ou `SglangClient` nos traces — devem aparecer logs de chamadas LLM
2. **LLM está respondendo**: procurar por `LLM action` ou `tool_call` — indica que o modelo retornou uma ação válida
3. **Sem timeout massivo**: se >50% das chamadas LLM dão timeout (15s), o SGLang está sobrecarregado
4. **Circuit breaker não ativou permanentemente**: se `CircuitBreaker OPEN` aparece muito cedo e nunca fecha, o LLM falhou
5. **Exploração continua após LLM**: o APE-RV deve continuar explorando mesmo quando o LLM falha (fallback para SATA)
6. **Trace não vazio**: arquivos .trace com >0 bytes indicam que o APE-RV executou

### Script de verificação

```bash
#!/bin/bash
# Quick sanity check on first completed traces
# Usage: bash scripts/check_exp3_traces.sh

RESULTS_DIR="${1:-data/results}"
echo "=== Exp3 Trace Sanity Check ($(date '+%H:%M:%S')) ==="

for i in $(seq 0 7); do
    dir=$(printf "$RESULTS_DIR/exp3_%02d/exp3_%02d" $i $i)
    [ -d "$dir" ] || continue

    traces=$(find "$dir" -name "*.trace" -size +0c 2>/dev/null | head -3)
    for trace in $traces; do
        apk=$(basename $(dirname "$trace"))
        size=$(stat -c%s "$trace" 2>/dev/null || echo 0)
        llm_calls=$(grep -c "LlmRouter\|SglangClient\|LLM action" "$trace" 2>/dev/null || echo 0)
        timeouts=$(grep -c "LLM.*timeout\|llm.*timed out" "$trace" 2>/dev/null || echo 0)
        circuit=$(grep -c "CircuitBreaker.*OPEN" "$trace" 2>/dev/null || echo 0)
        errors=$(grep -c "LLM.*error\|LLM.*fail\|SglangClient.*error" "$trace" 2>/dev/null || echo 0)

        echo ""
        echo "  $apk ($(( size / 1024 ))KB)"
        echo "    LLM calls: $llm_calls | Timeouts: $timeouts | Circuit OPEN: $circuit | Errors: $errors"

        if [ "$llm_calls" -eq 0 ]; then
            echo "    ⚠ ALERTA: Nenhuma chamada LLM detectada!"
        elif [ "$timeouts" -gt "$((llm_calls / 2))" ]; then
            echo "    ⚠ ALERTA: >50% das chamadas deram timeout — SGLang sobrecarregado?"
        elif [ "$circuit" -gt 5 ]; then
            echo "    ⚠ ALERTA: Circuit breaker abriu múltiplas vezes"
        else
            echo "    ✓ OK"
        fi
    done
    # Only check first container with traces
    [ -n "$traces" ] && break
done

echo ""
echo "=== Empty traces ==="
empty=$(find "$RESULTS_DIR"/exp3_*/exp3_*/ -name "*.trace" -size 0 2>/dev/null | wc -l)
total=$(find "$RESULTS_DIR"/exp3_*/exp3_*/ -name "*.trace" 2>/dev/null | wc -l)
echo "  $empty/$total traces vazios"
[ "$empty" -gt "$((total / 3))" ] && echo "  ⚠ ALERTA: Muitos traces vazios (>33%)"
```

### Red flags (parar e investigar)

- **0 chamadas LLM** em todos os traces → ape.properties não foi gerado corretamente ou socat não está funcionando
- **100% timeout** → SGLang caiu ou não iniciou
- **Traces vazios em >50% dos APKs** → crash no APE-RV (problema no JAR, não no LLM)
- **Coverage 0% em todos** → APKs não estão instrumentados (verificar skip flags)

---

## 6. Análise Planejada

### 6.1 Perguntas Principais

1. **LLM melhora cobertura?** `aperv:sata_mop_llm` vs `aperv:sata_mop_v1` (Wilcoxon, paired)
2. **Overhead aceitável?** Comparar duration_s entre LLM e non-LLM variants
3. **Viola mais?** APKs com violações e tipos de violação por ferramenta
4. **Ranking geral?** Posição do `sata_mop_llm` entre as 6 ferramentas

### 6.2 Tabela Final Esperada (6 ferramentas)

| # | Ferramenta | Method | Activity | MOP | Fonte |
|---|-----------|--------|----------|-----|-------|
| 1 | aperv:sata_mop_v1 | 28.35% | — | 37.02% | exp1 |
| 2 | ape (original) | 27.82% | — | 37.08% | exp1 |
| 3 | aperv:sata_mop_v2 | 27.35% | — | 36.35% | exp2 |
| 4 | aperv:sata | 27.28% | — | 35.49% | exp1 |
| 5 | rvsmart:mvp | 24.24% | — | 31.53% | exp2 |
| 6 | **aperv:sata_mop_llm** | **?** | **?** | **?** | **exp3** |

### 6.3 Cenários Possíveis

- **Best case**: `sata_mop_llm` > 30% method coverage → LLM é o caminho, calibração pode melhorar mais
- **Neutral**: `sata_mop_llm` ≈ `sata_mop_v1` (28-29%) → LLM overhead anula o ganho, precisa calibrar
- **Worst case**: `sata_mop_llm` < `sata_mop_v1` → como o af17 hybrid no rvsmart, latência domina. Precisa reduzir chamadas ou otimizar tempos

---

## 7. Paths e Artefatos

### 7.1 Dados de Entrada

| Artefato | Path |
|----------|------|
| APKs + JSONs (169) | `data/apks/*.apk` + `data/apks/*.apk.json` |
| Lista de APKs | `data/apks/available_169.txt` |
| Batch files (gerados) | `data/apks/exp3_batch_00.txt` .. `exp3_batch_09.txt` |

### 7.2 Resultados Anteriores

| Artefato | Path | Conteúdo |
|----------|------|----------|
| Exp1 consolidado | `data/results/aperv_comparacao_consolidated.csv` | ape, aperv:sata, aperv:sata_mop (1015 rows) |
| Exp2 consolidado | `data/results/exp2_consolidated.csv` | 5 tools merged (exp1+exp2) |
| Exp2 raw | `data/results/exp2_00/` .. `exp2_09/` | aperv:sata_mop_v2 + rvsmart:mvp |
| Exp1 raw | `data/results/aperv_00/` .. `aperv_09/` | ape + aperv:sata + aperv:sata_mop |

### 7.3 Saída deste Experimento

| Artefato | Path |
|----------|------|
| Raw results | `data/results/exp3_00/` .. `exp3_07/` |
| Consolidado (6 tools) | `data/results/exp3_consolidated.csv` |

### 7.4 Scripts

| Script | Path | Ação |
|--------|------|------|
| Setup | `scripts/setup_exp3.sh` | Gera batch files + result dirs |
| Monitor | `scripts/monitor_exp3.sh` | Acompanha progresso |
| Consolidação | `scripts/consolidate_exp3.py` | Merge exp1+exp2+exp3 → 6 tools CSV |
| Docker compose | `docker/docker-compose.exp3-aperv-llm.yml` | 8 containers + SGLang |

### 7.5 Scripts Anteriores (referência)

| Script | Path | Reusado? |
|--------|------|----------|
| Setup exp2 | `scripts/setup_exp2.sh` | Template para setup_exp3.sh |
| Monitor exp2 | `scripts/monitor_exp2.sh` | Template para monitor_exp3.sh |
| Consolidação exp2 | `scripts/consolidate_exp2.py` | Template para consolidate_exp3.py |
| Docker exp2 | `docker/docker-compose.exp-aperv-rvsmart.yml` | Template base (sem SGLang) |
| Docker comparação | `docker/docker-compose.comparacao.yml` | Template SGLang + socat |

---

## 8. Riscos e Fallbacks

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| SGLang OOM (GPU) | Baixa | Alto | Qwen3-VL-4B usa ~8GB VRAM, cabe em 24GB |
| SGLang overload (8 containers) | Baixa | Médio | Reduzir para 6 containers se latência > 10s |
| LLM timeout cascata | Média | Médio | Circuit breaker no Java (3 falhas → 60s block) |
| Tempo insuficiente (>18.5h) | Baixa | Médio | 507 tasks / 8 containers × 680s = 12.1h, margem de 6.4h |
| SSH push falha | Já ocorreu | Alto | `ssh-add` antes, ou copiar JAR manualmente |
| Emulador→socat falha | Baixa | Alto | Validação rápida (step 4.1) antes do full run |

**Fallback geral**: Se LLM falha sistematicamente (SGLang down, timeouts), verificar logs e reiniciar. O resume automático do rv-experiment retoma de onde parou.

---

## 9. Estimativa de Tempo

| Etapa | Tempo |
|-------|-------|
| Push + rebuild imagem | ~15-20 min |
| Setup (batch files) | ~1 min |
| Validação rápida (1 APK) | ~5-10 min |
| Experimento completo | ~12.1h |
| Consolidação + análise | ~15 min |
| **Total** | **~12.5-13h** |

**Janela disponível**: ~18.5h → margem confortável de ~6h.

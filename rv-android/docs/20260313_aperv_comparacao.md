# Experimento Comparativo: APE-RV vs APE Original

**Data**: 2026-03-13
**Status**: Planejamento
**Objetivo**: Comparar o APE-RV (fork modernizado com suporte a MOP) contra o APE original, validando duas hipóteses: (1) equivalência de performance do port, e (2) ganho do MOP-guided scoring.

---

## Caminhos Absolutos (Referência)

```
RVSEC_HOME  = /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
PROJECT     = /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
APE_SRC     = /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape
DATA_DIR    = /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/data
DOCKER_DIR  = /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docker/rvandroid
APERV_JAR   = /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar
APK_DIR     = /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/data/apks
RESULTS_DIR = /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/data/results
```

---

## 1. Hipóteses

### H1 — Equivalência do Port
O APE-RV (`aperv:sata`) tem performance estatisticamente equivalente ao APE original (`ape`) em method coverage, activity coverage e MOP coverage. A modernização do build (Maven + d8, Java 11) e as mudanças de integração não introduziram regressão.

**Critério**: Wilcoxon signed-rank test p > 0.05 para method coverage (paired, por APK).

### H2 — Superioridade do MOP-Guided
O APE-RV com MOP guidance (`aperv:sata_mop`) supera o APE original (`ape`) em MOP coverage, pois utiliza dados de análise estática para priorizar ações que exercitam operações monitoradas.

**Critério**: Wilcoxon signed-rank test p < 0.05 para MOP coverage, com efeito positivo.

### H3 — Exploratória
Análise head-to-head das 3 ferramentas em todas as métricas, identificando padrões por categoria/tamanho de APK.

---

## 2. Configuração do Experimento

### 2.1 Parâmetros

| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| Dataset | 169 APKs instrumentados (JCA) + 169 SA JSONs | Mesmo dataset do exp. 2026-03-11 |
| Ferramentas | `ape`, `aperv:sata`, `aperv:sata_mop` | 3 ferramentas |
| Timeout | 600s (10 minutos) | Padrão dos experimentos anteriores |
| Repetições | **2** por APK por ferramenta | Janela de execução de ~21h |
| Specification set | JCA | |
| Skip flags | `--skip-monitors --skip-instrument --skip-static` | APKs pré-instrumentados |
| Containers | **10** | |
| Total de tasks | 169 × 3 tools × 2 reps = **1.014 tasks** | |

### 2.2 Estimativa de Tempo

Dados empíricos (exp. 2026-03-11): **641s/task** (600s timeout + 41s overhead médio).

| Métrica | Valor |
|---------|-------|
| Tasks totais | 1.014 |
| Containers | 10 |
| Tasks/container (max) | 102 (9 containers com 17 APKs × 3 × 2) |
| Tasks/container (min) | 96 (1 container com 16 APKs × 3 × 2) |
| Wall time estimado | 102 × 641s = 65.382s ≈ **18.2h** |
| Margem na janela de 21h | **~2.8h** |

### 2.3 Dataset

Reutiliza os 169 APKs já instrumentados e JSONs de análise estática unificada (gh27):
- Localização: `DATA_DIR/apks/` (338 arquivos: 169 `.apk` + 169 `.apk.json`)
- Lista completa: `DATA_DIR/apks/available_169.txt`
- Nenhuma instrumentação ou análise estática adicional necessária

### 2.4 Ferramentas

| Ferramenta | Módulo | JAR | Estratégia | MOP Data |
|------------|--------|-----|------------|----------|
| `ape` | rv-tools (builtin) | `ape.jar` | SATA | — |
| `aperv:sata` | aperv-tool (externo) | `ape-rv.jar` | SATA | — |
| `aperv:sata_mop` | aperv-tool (externo) | `ape-rv.jar` | SATA | SA JSON → device |

Diferenças de runtime entre `ape` e `aperv:sata`:
- JAR diferente (`ape.jar` vs `ape-rv.jar`)
- Working directory diferente (`/data/local/tmp/` vs `/system/bin`)
- `aperv` injeta `ape.properties` com `ape.defaultGUIThrottle=200`
- `aperv:sata_mop` adicionalmente faz push do SA JSON e configura `ape.mopDataPath`

### 2.5 Recursos da Máquina

| Recurso | Total | Alocado (10 containers) | Livre |
|---------|-------|------------------------|-------|
| CPUs | 64 | 40 (4/container) | 24 |
| RAM | 123GB | 100GB (10GB/container) | 23GB |
| KVM | sim | compartilhado | — |

---

## 3. Infraestrutura Docker

### 3.1 Imagem Docker — Rebuild da Tag 0.8.0

A imagem atual (`phtcosta/rvandroid:0.8.0`) não inclui o módulo `aperv-tool` nem o `ape-rv.jar`. Precisamos fazer rebuild da **mesma tag 0.8.0**, adicionando apenas o COPY do JAR.

**IMPORTANTE**: Não criar nova tag. Usar o script de build existente (`docker/rvandroid/build.sh`) que já gera a tag `0.8.0`.

**Mudança no Dockerfile** (`docker/rvandroid/Dockerfile`): adicionar uma linha COPY antes dos ENVs.

```dockerfile
FROM phtcosta/rvandroid_tools:0.8.0

ENV RVSEC_HOME=/opt/rvsec

WORKDIR /opt/rvsec
RUN git clone --branch modules https://github.com/PAMunb/rvsec.git . && \
    mvn clean install -DskipTests -DskipMopAgent && \
    mvn clean compile -f $RVSEC_HOME/rv-android/pom.xml && \
    cd $RVSEC_HOME/rv-android && \
    uv sync --no-dev

# APE-RV: copiar JAR pré-compilado para o módulo aperv-tool
COPY ape-rv.jar /opt/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar

# Default environment variables
ENV RV_TOOLS=monkey
ENV RV_TIMEOUTS=300
ENV RV_REPETITIONS=1
ENV RV_NO_WINDOW=true
ENV RV_JCA_SPEC=true

# Volumes for APKs, artifacts, and results
VOLUME /opt/rvsec/rv-android/apks
VOLUME /opt/rvsec/rv-android/out
VOLUME /opt/rvsec/rv-android/results

# Entry point script translates env vars to CLI arguments
COPY docker-entrypoint.sh /opt/docker-entrypoint.sh
RUN chmod +x /opt/docker-entrypoint.sh

WORKDIR /opt/rvsec/rv-android

ENTRYPOINT ["/opt/docker-entrypoint.sh"]
CMD ["run"]
```

### 3.2 Build da Imagem

Passos sequenciais — todos com caminhos absolutos:

```bash
# -------------------------------------------------------------------
# PASSO 1: Build do ape-rv.jar a partir do código-fonte
# -------------------------------------------------------------------
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape
mvn clean install \
    -Drvsec_home=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec

# Verificar que o JAR foi gerado e copiado pelo Maven install
ls -lh /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar

# -------------------------------------------------------------------
# PASSO 2: Copiar JAR para o diretório de build Docker
# -------------------------------------------------------------------
cp /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar \
   /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docker/rvandroid/ape-rv.jar

# -------------------------------------------------------------------
# PASSO 3: Rebuild da imagem Docker (mesma tag 0.8.0)
# Usa o build.sh existente — NÃO criar nova tag
# -------------------------------------------------------------------
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docker/rvandroid
bash build.sh

# -------------------------------------------------------------------
# PASSO 4: Verificar que a imagem foi criada
# -------------------------------------------------------------------
docker images | grep rvandroid
# Deve mostrar phtcosta/rvandroid:0.8.0 e phtcosta/rvandroid:latest
```

O script `build.sh` existente:
```bash
VERSION=0.8.0
IMAGE=phtcosta/rvandroid
docker build --no-cache -t $IMAGE:$VERSION $(dirname $0)
# ... tags 0.8.0 e latest
```

### 3.3 Verificação da Imagem (Pré-voo)

Teste rápido com 1 APK e as 3 ferramentas antes de lançar o experimento completo:

```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

# Criar filtro com 1 APK de teste
echo "byrne.utilities.hashpass_2.apk" > data/apks/test_1apk.txt

# Limpar resultados anteriores do preflight
rm -rf data/results/preflight

# Rodar teste (1 APK × 3 tools × 1 rep × 120s = ~6min)
docker run --rm \
  --device /dev/kvm:/dev/kvm \
  -e RV_TOOLS="ape,aperv:sata,aperv:sata_mop" \
  -e RV_TIMEOUTS=120 \
  -e RV_REPETITIONS=1 \
  -e RV_NO_WINDOW=true \
  -e RV_JCA_SPEC=true \
  -e RV_SKIP_MONITORS=true \
  -e RV_SKIP_INSTRUMENT=true \
  -e RV_SKIP_STATIC_ANALYSIS=true \
  -e RV_APKS_DIR=/opt/rvsec/rv-android/apks \
  -e RV_APKS_FILTER=/opt/rvsec/rv-android/apks/test_1apk.txt \
  -e RV_EXPERIMENT_NAME=preflight \
  --cpus 4 --memory 10g \
  -v /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/data/apks:/opt/rvsec/rv-android/apks:ro \
  -v /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/data/results/preflight:/opt/rvsec/rv-android/results \
  phtcosta/rvandroid:0.8.0

# Validar resultados
python3 -c "
import json
with open('data/results/preflight/preflight/tasks.json') as f:
    data = json.load(f)
for t in data['tasks']:
    cfg = t['config']
    res = t['result']
    cov = res.get('coverage', {})
    print(f\"{cfg['tool']:20s} rep={cfg['repetition']} state={res['state']} time={res.get('execution_time_seconds',0):.0f}s method_cov={cov.get('method_coverage',0):.1f}%\")
"
```

**Checklist pré-voo** (todos devem passar):
- [ ] 3 tasks COMPLETED (1 por ferramenta)
- [ ] `ape` executa normalmente
- [ ] `aperv:sata` executa com `ape-rv.jar` (sem `ape-rv.jar not found`)
- [ ] `aperv:sata_mop` executa com push do SA JSON ao device
- [ ] Coverage > 0% para as 3 ferramentas
- [ ] Nenhum erro `RVToolExecutionError` nos logs

---

## 4. Docker Compose

### 4.1 Arquivo

**Path**: `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docker/docker-compose.aperv-comparacao.yml`

```yaml
# Experiment: ape vs aperv:sata vs aperv:sata_mop on 169 APKs.
# 10 containers, ~17 APKs each, 600s timeout, 2 reps, JCA specs.
# Estimated wall time: ~18h.
#
# Usage:
#   cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
#   bash scripts/setup_aperv_comparacao.sh
#   docker compose -f docker/docker-compose.aperv-comparacao.yml up -d
#   watch -n 60 bash scripts/monitor_aperv_comparacao.sh
#   docker compose -f docker/docker-compose.aperv-comparacao.yml down

x-rvandroid: &rvandroid-base
  image: phtcosta/rvandroid:0.8.0
  environment: &rvandroid-env
    RV_TOOLS: "ape,aperv:sata,aperv:sata_mop"
    RV_TIMEOUTS: "600"
    RV_REPETITIONS: "2"
    RV_NO_WINDOW: "true"
    RV_JCA_SPEC: "true"
    RV_SKIP_MONITORS: "true"
    RV_SKIP_INSTRUMENT: "true"
    RV_SKIP_STATIC_ANALYSIS: "true"
    RV_APKS_DIR: "/opt/rvsec/rv-android/apks"
    RV_DEVICE_PORT: "5554"
  devices:
    - /dev/kvm:/dev/kvm
  deploy:
    resources:
      limits:
        cpus: "4"
        memory: "10g"

services:
  aperv_00:
    <<: *rvandroid-base
    container_name: aperv_00
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: aperv_00
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/aperv_batch_00.txt"
      RV_DELAY: "0"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/aperv_00:/opt/rvsec/rv-android/results

  aperv_01:
    <<: *rvandroid-base
    container_name: aperv_01
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: aperv_01
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/aperv_batch_01.txt"
      RV_DELAY: "10"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/aperv_01:/opt/rvsec/rv-android/results

  aperv_02:
    <<: *rvandroid-base
    container_name: aperv_02
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: aperv_02
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/aperv_batch_02.txt"
      RV_DELAY: "20"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/aperv_02:/opt/rvsec/rv-android/results

  aperv_03:
    <<: *rvandroid-base
    container_name: aperv_03
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: aperv_03
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/aperv_batch_03.txt"
      RV_DELAY: "30"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/aperv_03:/opt/rvsec/rv-android/results

  aperv_04:
    <<: *rvandroid-base
    container_name: aperv_04
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: aperv_04
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/aperv_batch_04.txt"
      RV_DELAY: "40"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/aperv_04:/opt/rvsec/rv-android/results

  aperv_05:
    <<: *rvandroid-base
    container_name: aperv_05
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: aperv_05
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/aperv_batch_05.txt"
      RV_DELAY: "50"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/aperv_05:/opt/rvsec/rv-android/results

  aperv_06:
    <<: *rvandroid-base
    container_name: aperv_06
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: aperv_06
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/aperv_batch_06.txt"
      RV_DELAY: "60"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/aperv_06:/opt/rvsec/rv-android/results

  aperv_07:
    <<: *rvandroid-base
    container_name: aperv_07
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: aperv_07
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/aperv_batch_07.txt"
      RV_DELAY: "70"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/aperv_07:/opt/rvsec/rv-android/results

  aperv_08:
    <<: *rvandroid-base
    container_name: aperv_08
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: aperv_08
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/aperv_batch_08.txt"
      RV_DELAY: "80"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/aperv_08:/opt/rvsec/rv-android/results

  aperv_09:
    <<: *rvandroid-base
    container_name: aperv_09
    environment:
      <<: *rvandroid-env
      RV_EXPERIMENT_NAME: aperv_09
      RV_APKS_FILTER: "/opt/rvsec/rv-android/apks/aperv_batch_09.txt"
      RV_DELAY: "90"
    volumes:
      - ${BASE_DIR:-../data}/apks:/opt/rvsec/rv-android/apks:ro
      - ${BASE_DIR:-../data}/results/aperv_09:/opt/rvsec/rv-android/results
```

### 4.2 Distribuição de Batches

169 APKs / 10 containers (round-robin via `split -n r/10`):

| Container | Batch | APKs | Tasks (3 tools × 2 reps) |
|-----------|-------|------|--------------------------|
| aperv_00 | aperv_batch_00.txt | 17 | 102 |
| aperv_01 | aperv_batch_01.txt | 17 | 102 |
| aperv_02 | aperv_batch_02.txt | 17 | 102 |
| aperv_03 | aperv_batch_03.txt | 17 | 102 |
| aperv_04 | aperv_batch_04.txt | 17 | 102 |
| aperv_05 | aperv_batch_05.txt | 17 | 102 |
| aperv_06 | aperv_batch_06.txt | 17 | 102 |
| aperv_07 | aperv_batch_07.txt | 17 | 102 |
| aperv_08 | aperv_batch_08.txt | 17 | 102 |
| aperv_09 | aperv_batch_09.txt | 16 | 96 |
| **Total** | | **169** | **1.014** |

---

## 5. Scripts

### 5.1 Setup — `scripts/setup_aperv_comparacao.sh`

Gera batch files para 10 containers a partir dos 169 APKs já presentes em `data/apks/`.

```bash
#!/bin/bash
# Setup for APE-RV vs APE comparison experiment.
# Generates batch files for 10 containers from 169 APKs already in data/apks/.
#
# Usage:
#   cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
#   bash scripts/setup_aperv_comparacao.sh

set -e

DATA_DIR="data"
APK_DIR="$DATA_DIR/apks"
CONTAINERS=10
APK_LIST="$APK_DIR/available_169.txt"

echo "=== APE-RV Comparison Experiment Setup ==="
echo "APKs: $(wc -l < "$APK_LIST") (from $APK_LIST)"
echo "Containers: $CONTAINERS"
echo "Tools: ape, aperv:sata, aperv:sata_mop"
echo "Reps: 2"
echo ""

# 1. Create result directories
echo "[1/3] Creating result directories..."
for i in $(seq 0 $((CONTAINERS - 1))); do
    dir=$(printf "$DATA_DIR/results/aperv_%02d" $i)
    mkdir -p "$dir"
done

# 2. Generate batch files (round-robin split for balanced distribution)
echo "[2/3] Generating batch files..."
rm -f "$APK_DIR"/aperv_batch_*.txt

cd "$APK_DIR"
split -n r/$CONTAINERS -d -a 2 --additional-suffix=.txt \
    "available_169.txt" aperv_batch_
cd ../..

# 3. Verify
echo ""
echo "[3/3] Verification"
echo "  APKs:  $(ls "$APK_DIR"/*.apk 2>/dev/null | wc -l)"
echo "  JSONs: $(ls "$APK_DIR"/*.apk.json 2>/dev/null | wc -l)"
echo ""
echo "  Batches:"
total_apks=0
for b in "$APK_DIR"/aperv_batch_*.txt; do
    n=$(wc -l < "$b")
    total_apks=$((total_apks + n))
    echo "    $(basename $b): $n APKs"
done
echo "  Total: $total_apks APKs across $CONTAINERS batches"
echo ""

tasks=$((total_apks * 3 * 2))
echo "  Expected tasks: $tasks (${total_apks} APKs × 3 tools × 2 reps)"

echo ""
echo "=== Setup Complete ==="
echo "Next:"
echo "  cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
echo "  docker compose -f docker/docker-compose.aperv-comparacao.yml up -d"
echo "  watch -n 60 bash scripts/monitor_aperv_comparacao.sh"
```

### 5.2 Monitoramento — `scripts/monitor_aperv_comparacao.sh`

```bash
#!/bin/bash
# Monitor progress of APE-RV comparison experiment containers.
#
# Usage:
#   cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
#   bash scripts/monitor_aperv_comparacao.sh
#   watch -n 60 bash scripts/monitor_aperv_comparacao.sh

RESULTS_DIR="${1:-data/results}"
CONTAINERS="aperv_00 aperv_01 aperv_02 aperv_03 aperv_04 aperv_05 aperv_06 aperv_07 aperv_08 aperv_09"

echo "=== APE-RV Comparison Progress ($(date '+%Y-%m-%d %H:%M:%S')) ==="
echo ""

printf "%-10s %-12s %-10s %-10s %-6s %-6s %s\n" \
    "Container" "Status" "Completed" "Failed" "Done" "Total" "Last activity"
printf "%-10s %-12s %-10s %-10s %-6s %-6s %s\n" \
    "----------" "------" "---------" "------" "----" "-----" "-------------"

total_completed=0
total_failed=0
total_tasks=0

for c in $CONTAINERS; do
    dir="$RESULTS_DIR/$c"
    status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null || echo "not found")

    if [ ! -d "$dir" ]; then
        printf "%-10s %-12s %-10s %-10s %-6s %-6s %s\n" \
            "$c" "$status" "0" "0" "0" "?" "no results dir"
        continue
    fi

    tasks_file="$dir/$c/tasks.json"
    completed=0
    failed=0
    ntasks=0
    if [ -f "$tasks_file" ]; then
        read completed failed ntasks < <(python3 -c "
import json
with open('$tasks_file') as f:
    data = json.load(f)
tasks = data.get('tasks', [])
c = sum(1 for t in tasks if t.get('result',{}).get('state') == 'COMPLETED')
f = sum(1 for t in tasks if t.get('result',{}).get('state') in ('FAILED', 'ERROR'))
print(c, f, len(tasks))
" 2>/dev/null || echo "0 0 0")
    fi

    total_completed=$((total_completed + completed))
    total_failed=$((total_failed + failed))
    total_tasks=$((total_tasks + ntasks))

    last=$(find "$dir" -type f -newer "$dir" -printf '%T+ %f\n' 2>/dev/null \
        | sort -r | head -1 | cut -d' ' -f2)
    [ -z "$last" ] && last="-"

    printf "%-10s %-12s %-10s %-10s %-6s %-6s %s\n" \
        "$c" "$status" "$completed" "$failed" "$((completed+failed))" "$ntasks" "$last"
done

echo ""

expected=1014  # 169 APKs × 3 tools × 2 reps
remaining=$((expected - total_completed - total_failed))
pct=0
if [ $expected -gt 0 ]; then
    pct=$((100 * (total_completed + total_failed) / expected))
fi
echo "Overall: $total_completed completed, $total_failed failed, $remaining remaining (of $expected expected) [$pct%]"
```

### 5.3 Consolidação — `scripts/consolidate_aperv_comparacao.py`

Lê resultados dos 10 containers e produz CSV unificado. Sem merge com baseline — todas as ferramentas estão no mesmo experimento.

```python
"""Consolidate APE-RV comparison experiment results from 10 Docker containers.

Usage:
    cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
    uv run python scripts/consolidate_aperv_comparacao.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "data" / "results"
OUTPUT_CSV = RESULTS_DIR / "aperv_comparacao_consolidated.csv"
CONTAINERS = [f"aperv_{i:02d}" for i in range(10)]

COLUMN_MAP = {
    "cov_act": "activity_coverage",
    "cov_method": "method_coverage",
    "cov_rv_method": "mop_coverage",
    "errors": "total_errors",
}

OUTPUT_COLUMNS = [
    "apk", "tool", "rep", "status", "duration_s",
    "method_coverage", "activity_coverage", "mop_coverage", "total_errors",
]


def load_container_data(container: str) -> pd.DataFrame:
    """Load results from a single container."""
    base = RESULTS_DIR / container / container
    tasks_path = base / "tasks.json"
    summary_path = base / "summary.csv"

    if not tasks_path.exists():
        print(f"  WARNING: {tasks_path} not found, skipping {container}")
        return pd.DataFrame()

    with open(tasks_path) as f:
        tasks_data = json.load(f)

    status_map = {}
    duration_map = {}
    tool_map = {}
    for task in tasks_data["tasks"]:
        cfg = task["config"]
        key = (cfg["apk_name"], cfg["tool"], cfg["repetition"])
        status_map[key] = task["result"]["state"]
        duration_map[key] = task["result"].get("execution_time_seconds", 0)
        tool_map[key] = cfg["tool"]

    frames = []

    if summary_path.exists():
        df = pd.read_csv(summary_path)
        df["status"] = df.apply(
            lambda r: status_map.get((r["apk"], r["tool"], r["rep"]), "UNKNOWN"),
            axis=1,
        )
        df["duration_s"] = df.apply(
            lambda r: duration_map.get((r["apk"], r["tool"], r["rep"]), 0),
            axis=1,
        )
        frames.append(df)

        completed_keys = set(zip(df["apk"], df["tool"], df["rep"]))
    else:
        completed_keys = set()

    for (apk, tool, rep), state in status_map.items():
        if state != "COMPLETED" and (apk, tool, rep) not in completed_keys:
            frames.append(pd.DataFrame([{
                "apk": apk, "rep": rep, "timeout": 600, "tool": tool,
                "cov_act": 0.0, "cov_method": 0.0, "cov_rv_method": 0.0,
                "errors": 0, "status": state,
                "duration_s": duration_map.get((apk, tool, rep), 0),
            }]))

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename to unified schema."""
    df = df.rename(columns=COLUMN_MAP)
    return df[OUTPUT_COLUMNS]


def print_summary(df: pd.DataFrame) -> None:
    """Print per-tool summary statistics."""
    completed = df[df["status"] == "COMPLETED"]
    metrics = ["method_coverage", "activity_coverage", "mop_coverage", "total_errors"]

    print("\n" + "=" * 80)
    print("APE-RV COMPARISON EXPERIMENT — CONSOLIDATED SUMMARY")
    print("=" * 80)

    print("\n--- Task Counts ---")
    for tool, g in df.groupby("tool"):
        total = len(g)
        ok = (g["status"] == "COMPLETED").sum()
        err = total - ok
        apks = g["apk"].nunique()
        print(f"  {tool:20s}: {total:4d} tasks "
              f"({ok} completed, {err} failed) | {apks} unique APKs")

    print("\n--- Coverage Statistics (COMPLETED tasks only) ---")
    header = f"  {'tool':20s} {'metric':22s} {'mean':>8s} {'median':>8s} {'std':>8s}"
    print(header)
    print("  " + "-" * len(header.strip()))
    for tool, g in completed.groupby("tool"):
        for m in metrics:
            vals = g[m]
            print(f"  {tool:20s} {m:22s} "
                  f"{vals.mean():8.2f} {vals.median():8.2f} {vals.std():8.2f}")
        print()


def main():
    frames = []
    for container in CONTAINERS:
        df = load_container_data(container)
        if not df.empty:
            print(f"  {container}: {len(df)} rows")
            frames.append(df)

    if not frames:
        print("ERROR: No data found in any container")
        return

    all_df = normalize_columns(pd.concat(frames, ignore_index=True))
    print(f"\nTotal consolidated: {len(all_df)} rows")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved to {OUTPUT_CSV}")

    print_summary(all_df)


if __name__ == "__main__":
    main()
```

---

## 6. Sequência Completa de Execução

Todos os comandos assumem working directory:
```
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

### Fase 1 — Preparação (~30min)

```bash
# 1.1 Garantir que não há containers anteriores rodando
docker compose -f docker/docker-compose.exp-rvsmart-ape.yml down 2>/dev/null
docker compose -f docker/docker-compose.aperv-comparacao.yml down 2>/dev/null

# 1.2 Build ape-rv.jar
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape
mvn clean install \
    -Drvsec_home=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec

# 1.3 Verificar JAR
ls -lh /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar

# 1.4 Copiar JAR para Docker build context
cp /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar \
   /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docker/rvandroid/ape-rv.jar

# 1.5 Rebuild imagem Docker (tag 0.8.0 — usar build.sh existente)
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/docker/rvandroid
bash build.sh

# 1.6 Voltar ao diretório do projeto
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

### Fase 2 — Pré-voo (~10min)

```bash
# 2.1 Rodar teste com 1 APK, 3 tools, 1 rep, 120s timeout
echo "byrne.utilities.hashpass_2.apk" > data/apks/test_1apk.txt
rm -rf data/results/preflight

docker run --rm \
  --device /dev/kvm:/dev/kvm \
  -e RV_TOOLS="ape,aperv:sata,aperv:sata_mop" \
  -e RV_TIMEOUTS=120 \
  -e RV_REPETITIONS=1 \
  -e RV_NO_WINDOW=true \
  -e RV_JCA_SPEC=true \
  -e RV_SKIP_MONITORS=true \
  -e RV_SKIP_INSTRUMENT=true \
  -e RV_SKIP_STATIC_ANALYSIS=true \
  -e RV_APKS_DIR=/opt/rvsec/rv-android/apks \
  -e RV_APKS_FILTER=/opt/rvsec/rv-android/apks/test_1apk.txt \
  -e RV_EXPERIMENT_NAME=preflight \
  --cpus 4 --memory 10g \
  -v $(pwd)/data/apks:/opt/rvsec/rv-android/apks:ro \
  -v $(pwd)/data/results/preflight:/opt/rvsec/rv-android/results \
  phtcosta/rvandroid:0.8.0

# 2.2 Validar: 3 tasks COMPLETED, coverage > 0%
python3 -c "
import json
with open('data/results/preflight/preflight/tasks.json') as f:
    data = json.load(f)
ok = 0
for t in data['tasks']:
    cfg, res = t['config'], t['result']
    state = res['state']
    tool = cfg['tool']
    print(f\"  {tool:20s} state={state}\")
    if state == 'COMPLETED': ok += 1
print(f\"\n  Result: {ok}/3 COMPLETED\")
assert ok == 3, f'PREFLIGHT FAILED: only {ok}/3 completed'
print('  PREFLIGHT PASSED')
"
```

### Fase 3 — Setup + Launch (~2min)

```bash
# 3.1 Gerar batch files
bash scripts/setup_aperv_comparacao.sh

# 3.2 Lançar experimento
docker compose -f docker/docker-compose.aperv-comparacao.yml up -d

# 3.3 Verificar que todos os containers iniciaram
docker ps --filter "name=aperv_" --format "table {{.Names}}\t{{.Status}}"
```

### Fase 4 — Monitoramento (~18h)

```bash
# Monitoramento contínuo (refresh a cada 60s)
watch -n 60 bash scripts/monitor_aperv_comparacao.sh

# Verificação pontual
bash scripts/monitor_aperv_comparacao.sh

# Logs de um container específico
docker logs --tail 50 aperv_00

# Verificar após 1h: primeiras tasks COMPLETED para as 3 ferramentas
python3 -c "
import json
from pathlib import Path
tools_seen = set()
for i in range(10):
    p = Path(f'data/results/aperv_{i:02d}/aperv_{i:02d}/tasks.json')
    if p.exists():
        data = json.load(open(p))
        for t in data['tasks']:
            if t['result']['state'] == 'COMPLETED':
                tools_seen.add(t['config']['tool'])
print(f'Tools with COMPLETED tasks: {tools_seen}')
missing = {'ape', 'aperv:sata', 'aperv:sata_mop'} - tools_seen
if missing:
    print(f'WARNING: no completed tasks yet for: {missing}')
else:
    print('All 3 tools have completed tasks')
"
```

### Fase 5 — Pós-processamento (~5min)

```bash
# 5.1 Parar containers (se ainda rodando)
docker compose -f docker/docker-compose.aperv-comparacao.yml down

# 5.2 Consolidar resultados
uv run python scripts/consolidate_aperv_comparacao.py
# Saída: data/results/aperv_comparacao_consolidated.csv

# 5.3 Análise (reutilizar analyze_comparacao.py adaptado ou rodar ad-hoc)
uv run python scripts/analyze_comparacao.py
# Se precisar adaptar paths, editar TOOLS e INPUT_CSV no script
```

---

## 7. Resume após Interrupção

Cada container usa `--name aperv_XX`, habilitando resume automático via `tasks.json`.

```bash
# Restart de container individual (continua de onde parou)
docker compose -f docker/docker-compose.aperv-comparacao.yml up -d aperv_03

# Restart de todos os containers
docker compose -f docker/docker-compose.aperv-comparacao.yml up -d

# Verificar estado após restart
bash scripts/monitor_aperv_comparacao.sh
```

---

## 8. Troubleshooting

| Problema | Diagnóstico | Solução |
|----------|-------------|---------|
| `ape-rv.jar not found` | JAR não incluído na imagem | Verificar COPY no Dockerfile, rebuild |
| `aperv:sata_mop` coverage = 0% | SA JSON não encontrado | Verificar que `.apk.json` está junto do `.apk` no volume |
| Container parado prematuramente | OOM ou crash | `docker logs aperv_XX`, verificar RAM |
| Tasks stuck (>15min sem progresso) | Emulador travado | `docker restart aperv_XX` |
| Todos os containers param juntos | Disco cheio | `df -h`, limpar `/tmp` ou results antigos |

---

## 9. Análise Estatística (Pós-resultados)

### H1 (equivalência ape vs aperv:sata)
```python
from scipy.stats import wilcoxon
# Per-APK mean method_coverage (averaged across reps)
stat, p = wilcoxon(ape_means, aperv_sata_means)
# H1 aceita se p > 0.05 (não se pode rejeitar equivalência)
```

### H2 (superioridade aperv:sata_mop)
```python
stat, p = wilcoxon(ape_means_mop, aperv_sata_mop_means, alternative='greater')
# H2 aceita se p < 0.05 e direção positiva (aperv > ape)
```

### H3 (exploratória)
- Head-to-head 3-way por APK (threshold ±2pp)
- Distribuição de diferenças (histograma)
- Análise por tamanho/categoria de APK
- Top 10 APKs onde cada ferramenta vence

---

## 10. Protocolo de Validação (10 Áreas)

Configuração: 169 APKs × 3 ferramentas (ape, aperv:sata, aperv:sata_mop) × 2 reps × 600s.
Todas as ferramentas executadas no mesmo experimento — sem baseline externo.

---

### Área 1 — Resumo Executivo

**Objetivo**: Visão geral da completude e métricas agregadas.

| Verificação | Formato |
|-------------|---------|
| Completion rate global | `X/1014 tasks (Y%)` |
| Completion rate por ferramenta | Tabela: tool × (completed, failed, error, total) |
| Métricas agregadas por ferramenta | Tabela: tool × (mean, median, stdev, min, max) para method_cov, activity_cov, mop_cov |
| Head-to-head resumido (threshold ±2pp) | Tabela: comparação × (tool_A vence, tool_B vence, empate) |
| Total de violations RV por ferramenta | Sum de total_errors por tool |

**Tabela principal** (por ferramenta):

```
| Ferramenta       | Tasks | OK  | Fail | Meth% mean | Meth% med | Act% mean | MOP% mean | Errors |
|------------------|-------|-----|------|------------|-----------|-----------|-----------|--------|
| ape              | 338   | ... | ...  | ...        | ...       | ...       | ...       | ...    |
| aperv:sata       | 338   | ... | ...  | ...        | ...       | ...       | ...       | ...    |
| aperv:sata_mop   | 338   | ... | ...  | ...        | ...       | ...       | ...       | ...    |
```

**Critério de saúde**: completion rate ≥ 98% por ferramenta.

---

### Área 2 — Equivalência do Port (H1)

**Objetivo**: Validar que `aperv:sata` é estatisticamente equivalente ao `ape` original.

| Verificação | Método |
|-------------|--------|
| Per-APK mean coverage (averaged across 2 reps) | Tabela: apk × (ape_mean, aperv_sata_mean, delta) para method_cov |
| Wilcoxon signed-rank test (paired, por APK) | `scipy.stats.wilcoxon(ape_means, aperv_sata_means)` |
| Teste por métrica | Wilcoxon para method_cov, activity_cov, mop_cov separadamente |
| Effect size | Rank-biserial correlation (r = Z / sqrt(N)) |
| Distribuição dos deltas (aperv:sata - ape) | Histograma com faixas: <-20, [-20,-10), [-10,-5), [-5,-1), [-1,+1), [+1,+5), [+5,+10), [+10,+20), ≥+20 pp |
| Outliers de divergência | Top 10 APKs com maior |delta| — investigar causa |

**Critérios H1**:
- p > 0.05 → não se pode rejeitar equivalência (H1 aceita)
- p ≤ 0.05 → regressão detectada (H1 rejeitada — investigar)
- Se rejeitada: verificar se regressão é uniforme ou concentrada em poucos APKs

---

### Área 3 — MOP Guidance (H2)

**Objetivo**: Validar se `aperv:sata_mop` supera o `ape` em cobertura de operações monitoradas.

| Verificação | Método |
|-------------|--------|
| Per-APK mean MOP coverage | Tabela: apk × (ape_mean, aperv_mop_mean, delta) |
| Wilcoxon signed-rank test (one-sided) | `wilcoxon(..., alternative='greater')` para aperv:sata_mop > ape |
| Comparação com aperv:sata (isolar efeito MOP) | Wilcoxon aperv:sata_mop vs aperv:sata para MOP coverage |
| SA JSON utilization | Para cada APK: verificar via logcat/trace que aperv:sata_mop fez push do JSON |
| APKs com SA JSON rico vs pobre | Correlação entre tamanho/riqueza do JSON e ganho de MOP coverage |

**Critérios H2**:
- p < 0.05 e direção positiva → superioridade confirmada (H2 aceita)
- p ≥ 0.05 → sem evidência de ganho (H2 rejeitada)
- Se rejeitada: verificar se sata_mop de fato usou os dados (pode ser bug no push)

**Verificação crítica**: `aperv:sata_mop` deve ter resultados DIFERENTES de `aperv:sata`. Se forem idênticos, o MOP data não está sendo usado — verificar:
1. Logs do aperv-tool: "Pushing static analysis JSON" presente?
2. `ape.properties` no device contém `ape.mopDataPath`?
3. O JSON foi encontrado pelo APE-RV no device?

---

### Área 4 — Cobertura de Código (Detalhada)

**Objetivo**: Análise profunda de cobertura por todas as dimensões disponíveis.

| Verificação | Formato |
|-------------|---------|
| Distribuição de method coverage por ferramenta | Faixas: 0%, (0,10], (10,20], (20,30], (30,50], >50% — contagem de APKs |
| Distribuição de activity coverage por ferramenta | Idem |
| Distribuição de MOP coverage por ferramenta | Idem |
| Zero-coverage APKs | Lista por ferramenta: APKs com method_cov = 0% (possível crash/timeout antes de exploração) |
| APKs com cobertura discrepante entre ferramentas | APKs onde max_tool - min_tool > 20pp em method_cov |
| Cobertura por tamanho de APK | Agrupar APKs por size_bucket (tiny/small/medium/large/xlarge), comparar médias |
| MOP violations detectadas | Total de errors por ferramenta; APKs com errors > 0 em apenas 1 ferramenta |

**Tabela per-APK** (Top 20 com maior variância entre ferramentas):
```
| APK | ape Meth% | aperv:sata Meth% | aperv:mop Meth% | max-min | Vencedor |
```

---

### Área 5 — Anomalias e Falhas

**Objetivo**: Identificar e categorizar problemas de execução.

| Verificação | Método |
|-------------|--------|
| Tasks FAILED/ERROR por ferramenta | Contagem e lista de APKs afetados |
| Falhas exclusivas de uma ferramenta | APKs que falharam em UMA ferramenta mas completaram nas outras |
| Coverage = 0% com status COMPLETED | Indica crash logo após início — listar APKs e ferramentas |
| Categorização de falhas (via docker logs) | OOM, ClassNotFoundException, NullPointerException, ANR, timeout prematuro |
| APKs problemáticos recorrentes | APKs que falharam em ≥2 ferramentas — possível incompatibilidade do APK |

**Para cada anomalia documentar**:
1. **Sintoma**: o que foi observado (métrica, status)
2. **APK(s) afetado(s)**: lista
3. **Ferramenta(s)**: qual/quais
4. **Causa provável**: baseado em logs
5. **Impacto**: afeta interpretação dos resultados? Excluir do teste estatístico?

---

### Área 6 — Determinismo (Variância Intra-APK)

**Objetivo**: Avaliar consistência entre as 2 repetições de cada APK.

| Verificação | Método |
|-------------|--------|
| Desvio absoluto entre rep 0 e rep 1 por APK | `|cov_rep0 - cov_rep1|` para method_cov |
| Desvio médio por ferramenta | Mean dos desvios absolutos; ferramenta mais determinística |
| APKs com alta variância (desvio > 10pp) | Lista por ferramenta — possível comportamento não-determinístico do APK |
| Comparação de determinismo: ape vs aperv | As ferramentas devem ter variância semelhante (mesmo algoritmo SATA) |

**Nota**: Com apenas 2 repetições, não é possível calcular CV%. Usar desvio absoluto entre reps.

---

### Área 7 — Tempo de Execução

**Objetivo**: Verificar que o overhead de cada ferramenta é comparável.

| Verificação | Método |
|-------------|--------|
| Duração média por ferramenta | Mean, median, stdev de duration_s |
| Distribuição de duração | Faixas: <300s, [300,590), [590,660), [660,720), >720s |
| Early finishers (duration < 300s) | Indica crash/exit prematuro — listar APKs e ferramentas |
| Overhead comparison | `aperv` deve ter overhead semelhante ao `ape` (ambos usam app_process + Monkey) |
| Outliers de duração | Tasks com duração > 700s ou < 100s — investigar |

**Expectativa**: duração próxima de 600s + overhead (~40-60s). Todas as ferramentas devem ter distribuição semelhante, pois o timeout é o mesmo.

---

### Área 8 — Comparação Head-to-Head (3-way)

**Objetivo**: Análise detalhada de quem vence onde.

| Verificação | Método |
|-------------|---------|
| Per-APK winner (method_cov, threshold ±2pp) | 3-way: melhor ferramenta por APK (ou empate se todos dentro de 2pp) |
| Win/Tie/Loss por par | ape vs aperv:sata, ape vs aperv:sata_mop, aperv:sata vs aperv:sata_mop |
| Top 10 APKs onde `ape` vence | Ordenado por delta (ape - melhor_aperv), com valores |
| Top 10 APKs onde `aperv:sata` vence | Idem |
| Top 10 APKs onde `aperv:sata_mop` vence | Idem |
| Padrão por tamanho de APK | Alguma ferramenta domina em APKs grandes? Ou pequenos? |
| Padrão por cobertura base | Ferramentas convergem em APKs fáceis (alta cov) e divergem nos difíceis? |
| Scatter plot | ape_cov vs aperv:sata_cov; ape_cov vs aperv:sata_mop_cov (diagonal = equivalência) |

---

### Área 9 — Critérios de Validação

**Objetivo**: Checklist binário — o experimento é válido?

| Critério | Esperado | Resultado | Status |
|----------|----------|-----------|--------|
| Completion rate global | ≥ 98% (≥ 994/1014) | | |
| Completion rate por ferramenta | ≥ 95% cada | | |
| Mean method coverage ape | > 0% (sanity check) | | |
| Mean method coverage aperv:sata | > 0% | | |
| Mean method coverage aperv:sata_mop | > 0% | | |
| aperv:sata_mop ≠ aperv:sata em MOP coverage | Diferença detectável (não idênticos) | | |
| Nenhuma ferramenta com 100% de falhas em um APK | 0 APKs com todas as tasks FAILED | | |
| Duração média entre 600-720s | Todas as ferramentas | | |
| H1 avaliável | ≥ 150 APKs com dados completos para Wilcoxon | | |
| H2 avaliável | ≥ 150 APKs com dados completos para Wilcoxon | | |

**Se um critério falhar**: investigar antes de prosseguir com análise estatística. Documentar a causa e decidir se o experimento precisa ser re-executado (parcial ou total).

---

### Área 10 — Conclusão e Veredito

**Formato da conclusão**:

1. **H1 — Equivalência do Port**
   - Veredito: ACEITA / REJEITADA / INCONCLUSIVO
   - Evidência: p-value, effect size, N pares válidos
   - Se rejeitada: direção da regressão, magnitude, APKs mais afetados

2. **H2 — MOP Guidance**
   - Veredito: ACEITA / REJEITADA / INCONCLUSIVO
   - Evidência: p-value, effect size, delta médio em MOP coverage
   - Se rejeitada: verificar se MOP data foi de fato utilizado (Área 3 SA JSON check)

3. **Achados exploratórios (H3)**
   - Padrões de cobertura por ferramenta
   - Categorias de APKs onde cada ferramenta se destaca
   - Anomalias relevantes

4. **Problemas encontrados**
   - Bugs em ferramentas (a corrigir)
   - APKs problemáticos (a excluir em futuros experimentos?)
   - Limitações do protocolo experimental

5. **Próximos passos**
   - Re-executar com 3 reps se necessário para validação estatística mais forte
   - Investigar APKs com alta divergência
   - Ajustar sata_mop se MOP guidance não mostrou efeito

---

## 11. Artefatos

| Artefato | Path Absoluto |
|----------|---------------|
| Este plano | `.../rv-android/docs/20260313_aperv_comparacao.md` |
| Docker Compose | `.../rv-android/docker/docker-compose.aperv-comparacao.yml` |
| Setup script | `.../rv-android/scripts/setup_aperv_comparacao.sh` |
| Monitor script | `.../rv-android/scripts/monitor_aperv_comparacao.sh` |
| Consolidation script | `.../rv-android/scripts/consolidate_aperv_comparacao.py` |
| Batch files | `.../rv-android/data/apks/aperv_batch_{00..09}.txt` |
| CSV consolidado | `.../rv-android/data/results/aperv_comparacao_consolidated.csv` |
| Relatório de resultados | `.../rv-android/docs/20260313_aperv_comparacao_resultados.md` |

Todos os paths com `.../rv-android/` referem-se a:
`/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/`

---

## 12. Checklist de Execução

### Preparação
- [ ] `ape-rv.jar` compilado (`mvn clean install` no repo ape)
- [ ] JAR copiado para `docker/rvandroid/ape-rv.jar`
- [ ] Dockerfile atualizado com linha COPY
- [ ] Imagem `phtcosta/rvandroid:0.8.0` rebuilded via `build.sh`
- [ ] Pré-voo PASSED: 3/3 tools COMPLETED
- [ ] 169 APKs + 169 JSONs em `data/apks/` verificados

### Execução
- [ ] Setup executado: batch files gerados (`aperv_batch_00..09.txt`)
- [ ] Containers lançados: `docker compose up -d`
- [ ] 10 containers running: `docker ps --filter name=aperv_`
- [ ] Após 1h: todas as 3 ferramentas com tasks COMPLETED

### Pós-processamento
- [ ] Todos os 10 containers finalizados (exited)
- [ ] Consolidação: `aperv_comparacao_consolidated.csv` gerado
- [ ] 1.014 rows no CSV (ou próximo, descontando falhas)
- [ ] Análise e testes estatísticos (H1, H2) executados
- [ ] Relatório de resultados arquivado

#!/usr/bin/env bash
# Ciclo de acompanhamento da gh104: monitora, repara o que terminou curto, e resume.
#
# COPIA de ../../experimento-comp162/scripts/cycle.sh. Mudaram o NAME e o glob dos
# tasks.json; a ordem das etapas e a regra de admissibilidade embutida ficam como estavam.
#
# A ordem e deliberada. O monitor roda primeiro porque ele so REPORTA; o reparo so toca
# containers que NAO estao rodando, porque reescrever o tasks.json de um container vivo
# perde a corrida com a escrita atomica dele. O `up -d` no fim e o resume: identidade
# COMPLETED e pulada, ERROR e re-executada. Ele sobe qualquer container Exited, entao
# serve tanto para o que o reparo devolveu a fila quanto para as falhas transientes de
# `adb install` que ja estavam em ERROR.
#
# Uso:
#   bash scripts/cycle.sh            # uma passada
#   watch -n 1800 bash scripts/cycle.sh
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

NAME=gh104
COMPOSE=docker-compose.yml
IMAGE=$(python3 -c "import json;print(json.load(open('manifest.json'))['image']['tag'])")
TOTAL=$(python3 -c "import json;print(json.load(open('manifest.json'))['predicted_identities'])")

echo "===== ciclo ${NAME}: $(date '+%F %T') ====="

echo "--- monitor ---"
bash scripts/monitor.sh 2>&1 | tail -16

mapfile -t STOPPED < <(
  docker ps -a --filter "name=${NAME}_0" --format '{{.Names}} {{.State}}' |
    awk '$2 != "running" {print $1}' | sort
)

if [ ${#STOPPED[@]} -gt 0 ]; then
  echo "--- reparo em containers parados: ${STOPPED[*]} ---"
  docker run --rm -u 0 -v "$PWD:/w" -w /w --entrypoint python3 "$IMAGE" \
    scripts/repair.py --apply "${STOPPED[@]}" 2>&1 | tail -20
  echo "--- resume (up -d) ---"
  docker compose -f "$COMPOSE" up -d 2>&1 | tail -3
else
  echo "--- nenhum container parado; sem reparo nem resume ---"
fi

echo "--- admissibilidade (C1/C2/C5 por identidade) ---"
python3 - "$TOTAL" <<'PY'
import json, glob, sys
from collections import Counter

FLOOR = 255  # 300 s de orcamento menos APERV_TEARDOWN_GRACE_S
total = int(sys.argv[1])
c = Counter()
pend = []
for f in sorted(glob.glob('results/gh104_0*/gh104_0*/tasks.json')):
    cid = f.split('/')[1]
    doc = json.load(open(f))
    recs = doc['tasks'] if isinstance(doc, dict) else doc
    seen = {}
    for t in recs:
        cfg = t.get('config') or {}
        tc = cfg.get('tool_config') or {}
        k = (cfg.get('apk_name'), tc.get('name'), tc.get('variant'),
             cfg.get('repetition'), cfg.get('timeout'))
        r = t.get('result') or {}
        # o melhor registro da identidade manda: o resume acrescenta, nao sobrescreve
        if k not in seen or r.get('state') == 'COMPLETED':
            seen[k] = r
    for k, r in seen.items():
        cm = r.get('coverage_metrics') or {}
        ok_c1 = r.get('state') == 'COMPLETED' and not r.get('error_message')
        ok_c2 = (r.get('execution_time_seconds') or 0) >= FLOOR
        ok_c5 = (cm.get('method_coverage') or 0) > 0 and (cm.get('activities_coverage') or 0) > 0
        if ok_c1 and ok_c2 and ok_c5:
            c['admissivel'] += 1
        elif ok_c1 and ok_c2:
            # cobertura nula com orcamento cheio: nao volta para a fila, e decisao de
            # analise (exclusao por aplicacao), nao falha de execucao
            c['C5'] += 1
        else:
            c['pendente'] += 1
            pend.append((cid, k[0], k[2] or k[1], f"rep{k[3]}", r.get('state'),
                         r.get('execution_time_seconds')))

print(f"admissiveis={c['admissivel']}  reprova-C5={c['C5']}  pendentes={c['pendente']}  alvo={total}")
for p in pend[:20]:
    print("   pendente:", p)
if len(pend) > 20:
    print(f"   ... e mais {len(pend) - 20}")
if c['admissivel'] + c['C5'] == total and c['pendente'] == 0:
    print("TUDO_COMPLETO")
PY

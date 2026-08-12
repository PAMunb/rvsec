#!/bin/bash
# Progresso da comp162, por container.
#
# Uso:
#   cd .../rv-android/experimento-comp162
#   bash scripts/monitor.sh
#   watch -n 300 bash scripts/monitor.sh
#
# O total esperado e 1458 = 162 APKs x 3 bracos x 3 repeticoes. A particao e herdada
# da cmp163, entao os lotes nao sao iguais: dois containers levam 21 APKs (189 runs)
# e seis levam 20 (180 runs). Um container em 180 com os outros dois em 189 esta
# pronto, nao atrasado — a coluna Alvo diz o que cada um deve.
#
# A contagem e por IDENTIDADE (apk, tool, variant, rep, timeout), nunca por registro:
# o resume ACRESCENTA um registro para a identidade que re-tenta, entao contar
# registros reporta mais trabalho do que existe. E nunca `grep COMPLETED tasks.json`,
# que conta em dobro por causa de state_transitions.

cd "$(dirname "$0")/.." || exit 1

RESULTS_DIR="${1:-results}"
CONTAINERS="comp162_00 comp162_01 comp162_02 comp162_03 comp162_04 comp162_05 comp162_06 comp162_07"
EXPECTED=1458

echo "=== comp162 — progresso ($(date '+%Y-%m-%d %H:%M:%S')) ==="
echo ""

printf "%-14s %-11s %-10s %-7s %-6s %-6s %s\n" \
    "Container" "Status" "Completed" "Failed" "Total" "Alvo" "Ultima atividade"
printf "%-14s %-11s %-10s %-7s %-6s %-6s %s\n" \
    "-------------" "----------" "---------" "------" "-----" "-----" "----------------"

total_completed=0
total_failed=0

for c in $CONTAINERS; do
    dir="$RESULTS_DIR/$c/$c"

    # O alvo do container e derivado do filtro dele: lotes desiguais por heranca da
    # particao da cmp163. Ler o arquivo evita uma constante que desalinha em silencio.
    idx="${c##*_}"
    napks=$(wc -l < "filters/batch_${idx}.txt" 2>/dev/null || echo 0)
    target=$((napks * 3 * 3))

    # docker inspect emite uma linha vazia antes de falhar em container inexistente,
    # entao um `|| echo` produziria status de duas linhas e quebraria as colunas.
    status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null | head -1)
    [ -z "$status" ] && status="not-found"

    completed=0; failed=0; ntasks=0; last="-"

    tasks_file="$dir/tasks.json"
    if [ -f "$tasks_file" ]; then
        read -r completed failed ntasks < <(python3 -c "
import json
try:
    with open('$tasks_file') as f:
        data = json.load(f)
    tasks = data if isinstance(data, list) else data.get('tasks', [])
    states = {}
    for t in tasks:
        cfg = t.get('config') or {}
        tc = cfg.get('tool_config') or {}
        ident = (cfg.get('apk_name'), tc.get('name'), tc.get('variant'),
                 cfg.get('repetition'), cfg.get('timeout'))
        state = (t.get('result') or {}).get('state')
        # uma identidade que ja completou conta como completa mesmo que um registro
        # posterior dela tenha falhado
        if states.get(ident) != 'COMPLETED':
            states[ident] = state
    c = sum(1 for s in states.values() if s == 'COMPLETED')
    f = sum(1 for s in states.values() if s in ('FAILED', 'ERROR'))
    print(c, f, len(states))
except Exception:
    print(0, 0, 0)
" 2>/dev/null)
    fi

    if [ -d "$dir" ]; then
        last=$(find "$dir" -type f -printf '%T+ %f\n' 2>/dev/null | sort -r | head -1 | awk '{print $2}')
        [ -z "$last" ] && last="-"
    fi

    total_completed=$((total_completed + completed))
    total_failed=$((total_failed + failed))

    printf "%-14s %-11s %-10s %-7s %-6s %-6s %s\n" \
        "$c" "$status" "$completed" "$failed" "$ntasks" "$target" "$last"
done

echo ""
done_total=$((total_completed + total_failed))
pct=$((100 * done_total / EXPECTED))
remaining=$((EXPECTED - done_total))
echo "Total: $total_completed completas, $total_failed falhas, $remaining pendentes de $EXPECTED [$pct%]"
echo ""
echo "Atraso aparente nao e travamento: o tasks.json so e gravado quando a task FECHA,"
echo "entao a task seguinte ja esta em voo e invisivel. O atraso normal chega a ~2 ciclos"
echo "(~12 min a 300 s). Acima disso, confirmar com 'docker logs <container>'."

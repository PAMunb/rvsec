#!/bin/bash
# stage_apks_exp_ape_gh59.sh
#
# Coleta os 190 APKs instrumentados (v3 — pós fix gh59 PointcutMatcher +
# MonitorInvokeBuilder) de data/results/instrument_jca190_*/.../instrumented_apks/
# e copia (sobrescrevendo) para /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB/.
#
# Os SA JSONs (.apk.json) já existem nesse destino desde a v1 — não são tocados.
#
# Owner dos APKs origem é root (containers Docker), então usa container Alpine
# descartável pra cópia (evita sudo).

set -euo pipefail

DEST=/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB
PROJECT_ROOT=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

echo "[$(date)] === stage APKs exp_ape_gh59 ==="

# 1) Inventário origem
SRC_COUNT=$(find "$PROJECT_ROOT/data/results/instrument_jca190_"*/instrument_jca190_*/instrumented_apks -name '*.apk' 2>/dev/null | wc -l)
echo "APKs novos disponíveis: $SRC_COUNT"
if [ "$SRC_COUNT" -ne 190 ]; then
  echo "ERROR: esperado 190 APKs, encontrei $SRC_COUNT — abortar"
  exit 1
fi

# 2) Inventário destino antes
DEST_APK_BEFORE=$(ls "$DEST"/*.apk 2>/dev/null | wc -l)
DEST_JSON_BEFORE=$(ls "$DEST"/*.apk.json 2>/dev/null | wc -l)
echo "Destino antes: $DEST_APK_BEFORE APKs + $DEST_JSON_BEFORE JSONs"

# 3) Cópia via container Alpine (proprietário origem = root)
echo "Copiando APKs novos (sobrescrevendo)..."
docker run --rm \
  -v "$PROJECT_ROOT/data/results":/src:ro \
  -v "$DEST":/dst \
  alpine sh -c '
    set -e
    for d in /src/instrument_jca190_*/instrument_jca190_*/instrumented_apks; do
      [ -d "$d" ] || continue
      for apk in "$d"/*.apk; do
        [ -f "$apk" ] || continue
        cp -f "$apk" /dst/
      done
    done
    chmod 644 /dst/*.apk
  '

# 4) Inventário destino depois
DEST_APK_AFTER=$(ls "$DEST"/*.apk 2>/dev/null | wc -l)
DEST_JSON_AFTER=$(ls "$DEST"/*.apk.json 2>/dev/null | wc -l)
echo "Destino depois: $DEST_APK_AFTER APKs + $DEST_JSON_AFTER JSONs"

# 5) Sanity — todo APK tem JSON correspondente
MISSING_JSON=0
for apk in "$DEST"/*.apk; do
  name=$(basename "$apk")
  [ -f "$DEST/$name.json" ] || { echo "MISSING JSON for $name"; MISSING_JSON=$((MISSING_JSON+1)); }
done
if [ "$MISSING_JSON" -gt 0 ]; then
  echo "WARN: $MISSING_JSON APKs sem JSON correspondente"
fi

echo "[$(date)] done."

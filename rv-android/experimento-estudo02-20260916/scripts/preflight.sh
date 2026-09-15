#!/bin/bash
# Preflight da re-execução da estudo02. Nada aqui sobe emulador ou container de campanha — só
# confere o que a corrida assume. Cada linha FAIL é bloqueante.
#
#   experimento-estudo02-20260916/scripts/preflight.sh [smoke|campanha]   (default: smoke)
#
# `smoke` confere tudo menos o sweep de tecelagem e o veredito do smoke; `campanha` exige os dois.
set -u
EXP="$(cd "$(dirname "$0")/.." && pwd)"
cd "$EXP/.."
source "${CAMPANHA_ENV:-$EXP/scripts/campanha.env}"
FASE="${1:-smoke}"
RVSEC_REPO="$(cd .. && pwd)"
fails=0
ok()   { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; fails=$((fails + 1)); }

# --- Imagens ------------------------------------------------------------------
for img in "$IMAGE" "$HUMANOID_IMAGE" phtcosta/ares:latest phtcosta/qtesting:latest; do
  docker image inspect "$img" >/dev/null 2>&1 && ok "imagem $img" || fail "imagem ausente no host: $img"
done

# A tag não é evidência: a imagem clona o rvsec do GitHub, e um commit não empurrado some sem
# erro. O que discrimina é o commit assado em /opt/rvsec, lido da própria imagem.
if [ -z "$RVSEC_MIN_COMMIT" ]; then
  fail "RVSEC_MIN_COMMIT vazio em campanha.env — preencher com o commit da gh115 (que vem depois da gh114)"
else
  baked=$(timeout 120 docker run --rm --entrypoint git "$IMAGE" -C /opt/rvsec rev-parse HEAD 2>/dev/null | tr -d '\r\n')
  if [ -z "$baked" ]; then
    fail "não consegui ler o commit rvsec assado em $IMAGE (/opt/rvsec)"
  elif ! git -C "$RVSEC_REPO" cat-file -e "$baked^{commit}" 2>/dev/null; then
    fail "commit $baked da imagem não existe no repo local — rodar 'git fetch' e conferir"
  elif git -C "$RVSEC_REPO" merge-base --is-ancestor "$RVSEC_MIN_COMMIT" "$baked" 2>/dev/null; then
    ok "imagem carrega rvsec $(git -C "$RVSEC_REPO" log -1 --format='%h %ad' --date=short "$baked") (contém $RVSEC_MIN_COMMIT)"
  else
    fail "imagem carrega rvsec $(git -C "$RVSEC_REPO" log -1 --format='%h %ad %s' --date=short "$baked") — NÃO contém $RVSEC_MIN_COMMIT"
  fi
fi

db=$(timeout 120 docker run --rm --entrypoint git "$IMAGE" -C /opt/droidbot rev-parse --short HEAD 2>/dev/null | tr -d '\r\n')
[ "$db" = "$DROIDBOT_COMMIT" ] && ok "droidbot $db (pin de docker/tools/Dockerfile)" \
  || fail "droidbot da imagem é '${db:-ilegível}', esperado $DROIDBOT_COMMIT"

# As duas metades da gh114 que a campanha lê. Sem a parte Python, o `unique_msg` passa a incluir
# `vfp`/`vcls` e o mop_unique infla; sem a coluna `label`, os códigos novos não têm significado.
timeout 120 docker run --rm --entrypoint /opt/rvsec/rv-android/.venv/bin/python "$IMAGE" -c \
  'from rv_android_core.domain.log import RvErrorLog; assert hasattr(RvErrorLog, "identity_message")' \
  >/dev/null 2>&1 && ok "imagem: RvErrorLog.identity_message presente (gh114, INV-CORE-25)" \
  || fail "imagem sem RvErrorLog.identity_message — a parte Python da gh114 não está na imagem"
hdr=$(timeout 120 docker run --rm --entrypoint head "$IMAGE" -1 \
      /opt/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv 2>/dev/null | tr -d '\r')
[[ ",$hdr," == *",label,"* ]] && ok "imagem: jca_android/codes.csv com a coluna label" \
  || fail "imagem: codes.csv sem a coluna label (cabeçalho: '${hdr:-ilegível}')"

[ -e /dev/kvm ] && ok "/dev/kvm" || fail "/dev/kvm ausente"
[ -S /var/run/docker.sock ] && ok "docker.sock (ares/qtesting como irmãos)" || fail "docker.sock ausente"

# --- Corpus -------------------------------------------------------------------
CORPUS="data/${NAME}_filters/corpus.txt"
if [ ! -f "$CORPUS" ]; then
  fail "$CORPUS ausente — rodar exportar_corpus.py --apply e gerar_campanha.sh"
else
  n_corpus=$(grep -c . "$CORPUS")
  n_apk=$(ls "$DATASET" | grep -c '\.apk$'); n_json=$(ls "$DATASET" | grep -c '\.apk\.json$')
  [ "$n_apk" -eq "$n_corpus" ] && [ "$n_json" -eq "$n_corpus" ] \
    && ok "dataset $n_apk .apk + $n_json .apk.json = corpus.txt ($n_corpus)" \
    || fail "dataset: $n_apk apk / $n_json json, corpus.txt tem $n_corpus"
  missing=0; while read -r a; do [ -f "$DATASET/$a" ] && [ -f "$DATASET/$a.json" ] || missing=$((missing+1)); done < "$CORPUS"
  [ "$missing" -eq 0 ] && ok "todo APK do corpus tem .apk e .apk.json" || fail "$missing APK(s) do corpus sem par no dataset"
  (cd "$DATASET" && sha256sum --quiet -c MANIFEST.sha256 >/dev/null 2>&1) \
    && ok "dataset íntegro contra MANIFEST.sha256 da exportação" || fail "dataset diverge do MANIFEST.sha256"
  for a in ${SMOKE_APKS//,/ }; do grep -qx "$a" "$CORPUS" || fail "APK do smoke fora do corpus: $a"; done
fi

# --- Tecelagem (gh114) --------------------------------------------------------
# O sweep da gh114 (scripts/gh114_weave_sweep.py) só roda sobre os APKs do smoke dela; a
# campanha exige o sweep sobre o corpus inteiro, gravado em docs/ (README, passo 5).
SWEEP="$EXP/docs/tecelagem_sweep.csv"
if [ "$FASE" = campanha ]; then
  [ -s "$SWEEP" ] && ok "sweep de tecelagem sobre o corpus: $SWEEP (conferir o veredito em docs/tecelagem.md)" \
    || fail "sweep de tecelagem ausente: $SWEEP"
  [ -s "$EXP/docs/smoke.md" ] && ok "veredito do smoke registrado em docs/smoke.md" || fail "docs/smoke.md ausente — o smoke não foi julgado"
fi

# --- Host ---------------------------------------------------------------------
live=$(docker ps --format '{{.Names}}' | grep -E "^(${NAME}_|${SMOKE_NAME}_)" | tr '\n' ' ')
[ -z "$live" ] && ok "nenhum container desta campanha vivo" || fail "containers vivos: $live"
old=$(docker ps --format '{{.Names}}' | grep -E '^estudo02(smoke)?_' | tr '\n' ' ')
[ -z "$old" ] && ok "nenhum container da estudo02 vivo" || fail "containers da estudo02 vivos: $old"
# Irmãos que o ares/qtesting deixaram de campanhas anteriores: o portão 4 do smoke reprova
# qualquer órfão, sem saber de quem é. Em 15/09 havia cinco da estudo02 no host.
orf=$(docker ps -a --format '{{.Names}}' | grep -E '^(ares|qtesting)_[0-9a-f]{8}$' | tr '\n' ' ')
[ -z "$orf" ] && ok "nenhum irmão ares_*/qtesting_* remanescente" \
  || fail "irmãos remanescentes (conferir e 'docker rm' à mão): $orf"
if docker ps -a --format '{{.Names}}' | grep -qx rv-humanoid; then
  echo "[INFO] container rv-humanoid já existe (container_name fixo): 'docker rm -f rv-humanoid' antes do up, se for de outro compose"
fi
for f in "docker-compose.$SMOKE_NAME.yml" "docker-compose.$NAME.yml"; do
  if [ -f "$EXP/$f" ]; then
    docker compose -f "$EXP/$f" config -q && ok "compose válido: $f" || fail "compose inválido: $f"
  else
    fail "compose ausente: $EXP/$f — rodar gerar_campanha.sh"
  fi
done

# Teto de memória: a soma N × MEMORY tem de caber na RAM total. O teto do cgroup não reserva nada
# e a máquina fica dedicada à campanha; se os containers baterem no teto ao mesmo tempo, o OOM
# continua sendo do container, e o Docker religa.
mem_g=${MEMORY%g}; n_max=$(( CONTAINERS > SMOKE_CONTAINERS ? CONTAINERS : SMOKE_CONTAINERS ))
need_g=$(( n_max * mem_g ))
total_g=$(free -g | awk '/^Mem/{print $2}'); avail_g=$(free -g | awk '/^Mem/{print $7}')
[ "$total_g" -ge "$need_g" ] && ok "RAM total ${total_g}g ≥ ${n_max} × ${MEMORY}" || fail "RAM total ${total_g}g < ${need_g}g"
# A disponível é conferida contra o uso medido, não contra o teto: na estudo02 o container ficou
# em ~4 g de emulador + ~3 g de Python em média (plano §4), ~7 g × N.
use_g=$(( n_max * 7 + 8 ))
[ "$avail_g" -ge "$use_g" ] && ok "RAM disponível ${avail_g}g ≥ ${n_max} × 7g + 8g" || fail "RAM disponível ${avail_g}g < ${use_g}g — algo mais está ocupando memória"
free_t=$(df -BG --output=avail /pedro | tail -1 | tr -dc 0-9); [ "$free_t" -ge 300 ] && ok "disco livre ${free_t}G" || fail "disco livre ${free_t}G (< 300G)"

# O HDD é compartilhado por leitura de APK e escrita de resultado. Pressão alta ANTES de começar
# quer dizer outro processo no disco, e o overhead por task (boot + install) sobe junto.
io=$(awk '/^some/{for(i=1;i<=NF;i++) if($i ~ /^avg300=/){sub("avg300=","",$i); print int($i)}}' /proc/pressure/io)
[ "${io:-0}" -lt 20 ] && ok "pressão de I/O (some avg300) ${io}%" || fail "pressão de I/O ${io}% (≥ 20%) — outro processo usando o disco"

echo; [ "$fails" -eq 0 ] && echo "PREFLIGHT ($FASE) OK" || { echo "PREFLIGHT ($FASE): $fails FAIL"; exit 1; }

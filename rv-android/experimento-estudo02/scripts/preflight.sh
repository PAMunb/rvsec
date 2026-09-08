#!/bin/bash
# Preflight do estudo02: nada aqui sobe emulador ou container — só confere o que a corrida
# assume. Cada linha e' um FAIL bloqueante.
set -u
cd "$(dirname "$0")/../.."
DATASET=/home/pedro/desenvolvimento/RV_ANDROID_DATASET_FINAL/APKS_INSTRUMENTED_jca_android_dexlib2
fails=0
ok()   { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; fails=$((fails + 1)); }

RVANDROID_IMG=phtcosta/rvandroid:0.9.3
# O commit que a imagem TEM de conter. `278883ec` e' a gh113, o ultimo do branch `modules`;
# tudo o que a campanha mede (gh104/gh111/gh113) esta' nele ou antes dele.
RVSEC_MIN_COMMIT=278883ec
RVSEC_REPO="$(cd .. && pwd)"

for img in "$RVANDROID_IMG" phtcosta/humanoid:1.0 phtcosta/ares:latest phtcosta/qtesting:latest; do
  docker image inspect "$img" >/dev/null 2>&1 && ok "imagem $img" || fail "imagem ausente no host: $img"
done

# A tag `0.9.3` nao e' evidencia de nada: ela ja' existiu no host desde 12/08 carregando
# `e0e6b8fb`, anterior a' gh104. Uma tag reaproveitada passaria no teste de existencia e
# rodaria ~6 dias sobre o codigo errado, em silencio. O que discrimina e' o commit assado em
# /opt/rvsec dentro da imagem, lido da propria imagem.
baked=$(timeout 120 docker run --rm --entrypoint git "$RVANDROID_IMG" \
          -C /opt/rvsec rev-parse HEAD 2>/dev/null | tr -d '\r\n')
if [ -z "$baked" ]; then
  fail "nao consegui ler o commit rvsec assado em $RVANDROID_IMG (/opt/rvsec)"
elif ! git -C "$RVSEC_REPO" cat-file -e "$baked^{commit}" 2>/dev/null; then
  fail "commit $baked da imagem nao existe no repo local — rodar 'git fetch' e conferir"
elif git -C "$RVSEC_REPO" merge-base --is-ancestor "$RVSEC_MIN_COMMIT" "$baked" 2>/dev/null; then
  ok "imagem carrega rvsec $(git -C "$RVSEC_REPO" log -1 --format='%h %ad' --date=short "$baked") (contem $RVSEC_MIN_COMMIT)"
else
  fail "imagem carrega rvsec $(git -C "$RVSEC_REPO" log -1 --format='%h %ad %s' --date=short "$baked") — NAO contem $RVSEC_MIN_COMMIT (gh113); rebuildar a $RVANDROID_IMG"
fi
# O droidbot serve 5 dos 11 bracos (as 4 politicas + humanoid) e vinha de um clone sem SHA:
# o rebuild de 08/09 o moveu de 52aeea4 (2023) para cc4cc93 (2026) sozinho. O pin esta' em
# docker/tools/Dockerfile; aqui se confere que a imagem de fato o carrega.
DROIDBOT_COMMIT=52aeea4
db=$(timeout 120 docker run --rm --entrypoint git "$RVANDROID_IMG" \
       -C /opt/droidbot rev-parse --short HEAD 2>/dev/null | tr -d '\r\n')
[ "$db" = "$DROIDBOT_COMMIT" ] && ok "droidbot $db (pin de docker/tools/Dockerfile)" \
  || fail "droidbot da imagem e' '${db:-ilegivel}', esperado $DROIDBOT_COMMIT — rebuildar tools+rvandroid"

[ -e /dev/kvm ] && ok "/dev/kvm" || fail "/dev/kvm ausente"
[ -S /var/run/docker.sock ] && ok "docker.sock (ares/qtesting como irmaos)" || fail "docker.sock ausente"

n_apk=$(ls "$DATASET" | grep -c '\.apk$'); n_json=$(ls "$DATASET" | grep -c '\.apk\.json$')
[ "$n_apk" -eq 163 ] && [ "$n_json" -eq 163 ] && ok "dataset 163 .apk + 163 .apk.json" || fail "dataset: $n_apk apk / $n_json json (esperado 163/163)"
ls "$DATASET" | grep -q stardroid && fail "stardroid ainda no dataset (movido para RV_ANDROID_DATASET_FINAL/excluidos/ em 08/09)" || ok "stardroid fora do dataset"
n_corpus=$(grep -c . data/estudo02_filters/corpus.txt)
[ "$n_corpus" -eq 163 ] && ok "corpus.txt = 163" || fail "corpus.txt = $n_corpus (esperado 163)"
grep -q stardroid data/estudo02_filters/corpus.txt && fail "stardroid ainda no corpus" || ok "stardroid fora do corpus"
sha=$(sha256sum data/estudo02_filters/corpus.txt | cut -c1-16)
[ "$sha" = "84a03578f0c7203b" ] && ok "corpus sha256 84a03578… (== cal163)" || fail "corpus sha256 mudou: $sha"
missing=0; while read -r a; do [ -f "$DATASET/$a" ] && [ -f "$DATASET/$a.json" ] || missing=$((missing+1)); done < data/estudo02_filters/corpus.txt
[ "$missing" -eq 0 ] && ok "todo APK do corpus tem .apk e .apk.json" || fail "$missing APK(s) do corpus sem par no dataset"

live=$(docker ps --format '{{.Names}}' | grep -E '^(estudo02_|rv-humanoid$)' | tr '\n' ' ')
[ -z "$live" ] && ok "nenhum estudo02_*/rv-humanoid vivo" || fail "containers vivos: $live"
docker compose -f docker/docker-compose.estudo02.yml config -q && ok "compose valido" || fail "compose invalido"

avail_g=$(free -g | awk '/^Mem/{print $7}'); [ "$avail_g" -ge 100 ] && ok "RAM disponivel ${avail_g}g" || fail "RAM disponivel ${avail_g}g (< 100g)"
free_t=$(df -BG --output=avail /pedro | tail -1 | tr -dc 0-9); [ "$free_t" -ge 300 ] && ok "disco livre ${free_t}G" || fail "disco livre ${free_t}G (< 300G)"

echo; [ "$fails" -eq 0 ] && echo "PREFLIGHT OK" || { echo "PREFLIGHT: $fails FAIL"; exit 1; }

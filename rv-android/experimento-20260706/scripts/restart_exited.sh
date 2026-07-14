#!/usr/bin/env bash
# Reinicia containers exp_00..03 mortos por OOM (ExitCode 137) — e SOMENTE esses.
#
# IMPORTANTE: NÃO reiniciar containers que saíram com exit 0 (fim limpo de uma
# passada). run_experiment.sh avança de uma passada para a próxima (60s→180s→300s)
# via `docker wait exp_00..03`, que só retorna quando os 4 containers saem. Um
# container que terminou a passada sai com exit 0 e fica `exited` aguardando os
# irmãos. Se o cron reiniciar esse container (exit 0), ele re-executa a passada
# inteira e nunca fica `exited` → `docker wait` nunca retorna → a próxima passada
# nunca inicia (livelock observado na m4 em 2026-07-08, transição 180s→300s).
#
# ExitCode 137 = SIGKILL (128+9) = OOM-kill. É o único caso a recuperar.
# (Kill do `compose down` na transição também dá 137, mas o container está sendo
# removido nesse instante, então `docker start` falha inócuo.)
for c in exp_00 exp_01 exp_02 exp_03; do
  st=$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null)
  code=$(docker inspect -f '{{.State.ExitCode}}' "$c" 2>/dev/null)
  if [ "$st" = "exited" ] && [ "$code" = "137" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') restarting $c (OOM exit 137)"
    docker start "$c"
  fi
done

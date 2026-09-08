# `estudo02smoke` — smoke do `estudo02`

**Data:** 20260908 · **Compose:** `docker/docker-compose.estudo02smoke.yml` · **Imagem:** `phtcosta/rvandroid:0.9.3`

2 APKs × 11 ferramentas × 1 rep × 60 s = **22 tasks** em 2 containers (~40 min). Gerado pela skill com
`--only com.tananaev.passportreader_22.apk,app.michaelwuensch.bitbanana_79.apk` sobre o mesmo
dataset da campanha (sem cópia). Os seis portões, todos bloqueantes, estão em
`docs/20260908_estudo02.md` §7; o smoke existe para provar as três ferramentas que dependem de
infraestrutura fora da imagem (`humanoid` → sidecar, `ares`/`qtesting` → containers irmãos) antes
de comprometer ~6 dias de máquina.

```bash
bash experimento-estudo02/scripts/preflight.sh
docker compose -f docker/docker-compose.estudo02smoke.yml up -d
.claude/skills/rv-experiment-compare/scripts/monitor_compare.sh estudo02smoke --no-resume
uv run python experimento-estudo02/scripts/smoke_gates.py        # os seis portões, bloqueantes
docker compose -f docker/docker-compose.estudo02smoke.yml down   # libera o rv-humanoid antes da campanha
```

Os portões são conferidos por `experimento-estudo02/scripts/smoke_gates.py`, que conta por
identidade `(apk, ferramenta, variante, rep, timeout)` e sai com código 1 se algum reprovar.
Ele lê o `docker logs rv-humanoid` e o `docker ps -a`, então tem de rodar **antes** do `down`.
O veredito vai para `experimento-estudo02/docs/20260908_smoke.md`.

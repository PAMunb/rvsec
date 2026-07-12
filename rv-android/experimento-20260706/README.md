# Experimento 2026-07-06 — re-run JCA no dataset novo (sem obfuscação)

Re-execução do desenho experimental do `experimento-20260604`, agora sobre o **dataset
novo** (`rvsec-dataset`), construído para eliminar os problemas de **obfuscação** que
afetaram os datasets anteriores. **Mesmo desenho**; mudam apenas o dataset e a tag da
imagem.

## O que muda vs 20260604

| | 20260604 | **20260706** |
|---|---|---|
| Dataset | 169 APKs | **219 APKs** instrumentados (dexlib2) |
| Origem do dataset | `APKS_FINAL_JCA_DEXLIB_20260604` | `RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706` |
| Imagem | `phtcosta/rvandroid:0.9.0` | **`phtcosta/rvandroid:0.9.1`** (fix `--frozen --no-dev` do entrypoint baked, commit `14013b60`) |
| Tasks totais | 16 731 | **21 681** (219 × 11 × 3 reps × 3 timeouts) |

Tudo o mais é idêntico ao 20260604.

## Configuração

| Parâmetro | Valor |
|-----------|-------|
| APKs | **219** (dataset instrumentado dexlib2, com `.apk.json` de análise estática ao lado) |
| Tools (11) | `monkey, droidbot:{dfs_greedy,bfs_greedy,dfs_naive,bfs_naive}, ape, droidmate, humanoid, ares, fastbot, qtesting` |
| Timeouts | 60, 180, 300 s (3 passes sequenciais, auto-resume) |
| Repetições | 3 |
| Spec set | `jca` |
| Variante instrumentação | `dexlib2` (APKs já instrumentados → `RV_SKIP_INSTRUMENT=true`) |
| Imagem | `phtcosta/rvandroid:0.9.1` |
| Topologia | 4 VMs × 4 containers = 16 batches (`.env.m1-m4`) |
| Tasks totais | 219 × 11 × 3 reps × 3 timeouts = **21 681** |

Alvos por VM (COMPLETED distintos): **m1 5544 · m2 5544 · m3 5445 · m4 5148**.

## Pré-processing (LOCAL, antes das VMs)

> As VMs do gcloud já existem, **paradas**. Só inicie-as e dispare quando for a hora.

### Fase 1 — Construir + publicar imagens 0.9.1
```bash
cd experimento-20260706
git -C .. status                     # confirme que o HEAD está pushado em origin/modules
docker login -u phtcosta
DRY_RUN=1 bash scripts/build_and_push_091.sh   # revisar o que vai rodar
bash scripts/build_and_push_091.sh             # rebuild rvandroid:0.9.1 + retag ares/qtesting + push
```
Publica `rvandroid:0.9.1` (+latest), `ares:0.9.1`/`latest`, `qtesting:0.9.1`/`latest`.
`humanoid:1.0` já está no hub, inalterada. As VMs puxam do Docker Hub — imagens **não**
são copiadas por scp.

### Fase 2 — (Re)gerar filtros — só se o dataset ou a topologia mudarem
```bash
bash scripts/make_batches.sh
# → filters/experiment_apks.txt (219) + batch_00..15.txt + smoke_batch.txt
```
Os filtros já estão versionados neste diretório; rode apenas se precisar regenerar.

### Fase 3 — Copiar dataset + experimento pras VMs
```bash
bash scripts/copy_dataset_to_vms.sh user@vm1 user@vm2 user@vm3 user@vm4
# ou: USE_GCLOUD=1 GCLOUD_ZONE=<zona> bash scripts/copy_dataset_to_vms.sh inst-m1 ... inst-m4
```
Cada VM recebe:
- `/home/pedro/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/` (219 `.apk` + 219 `.apk.json`)
- `/home/pedro/experimento-20260706/` (compose, filters, scripts)

## Execução (nas VMs)

```bash
cd /home/pedro/experimento-20260706
bash scripts/run_smoke.sh                 # 1º: smoke (2 APKs × 11 tools, T=60→120) — ABORTA se falhar
./scripts/run_experiment.sh m1            # depois: m1 / m2 / m3 / m4 conforme a VM
```

Cada VM roda 3 passes (T=60→180→300); `tasks.json` acumula combos sem duplicar
(auto-resume entre falhas e entre passes, mesmo `RV_EXPERIMENT_NAME` por container).

## Monitoramento

```bash
bash scripts/monitor.sh                    # snapshot (progresso REAL, não só container up/down)
bash scripts/monitor.sh --watch 30         # atualiza a cada 30s
bash scripts/monitor.sh --json             # snapshot estruturado (coleta/automação)
```

Genérico (qualquer experimento):
```bash
python3 scripts/rv_status.py --results results --prefix exp_ \
    --apks 219 --tools 11 --reps 3 --timeouts 60,180,300 [--watch 30] [--json]
```

O `health_check.py` (cron horário) anexa a cada ciclo no `MONITORAMENTO.md` o
**formato-padrão de progresso (v2.1, definido 2026-07-08)**: **uma tabela curta por
VM** (`### mN`) com granularidade por **container** + linha `**total**`, seguidas de uma
**tabela-resumo geral** (1 linha por VM + `TOTAL`). Tabelas curtas evitam a quebra de
tabelas altas em alguns visualizadores.

Tabela por VM (`### mN`):

| container | docker | timeout 60·180·300 | ok | err | feito | alvo | % |
|-----------|--------|--------------------|----:|----:|------:|-----:|--:|

- **container** = `exp_00..03`; **docker** = estado do container (`Up`, `exit`=OOM a recuperar, `gone`/`dead`). A linha `**total**` agrega a VM.
- **timeout 60·180·300** = `feito` (ok+err) de cada uma das 3 passadas de timeout, SEMPRE nas 3 posições (uma passada não iniciada aparece como `0`). Como as passadas rodam **sequenciais**, esta célula revela onde o container está no ciclo. Alvo por passada = `alvo/3`.
- **ok** = COMPLETED; **err** = ERROR (a maioria transitória: `emulator/boot`, `install/adb`, esperam mop-up); **feito** = ok+err.
- **alvo** = APKs do container × 11 tools × 3 reps × 3 passadas (lista autoritativa). Container com 14 APKs → 1.386; com 13 → 1.287.
- **%** = feito ÷ alvo. Consistência: por container, `p60+p180+p300 = feito`.

Tabela-resumo geral (visão agregada de sempre):

| VM | estado | timeout 60·180·300 | ok | err | feito | alvo | % |
|----|--------|--------------------|----:|----:|------:|-----:|--:|

- 1 linha por VM (`timeout` = soma das passadas dos containers) + linha `TOTAL`. Totais por VM: m1=5.544, m2=5.544, m3=5.445, m4=5.148 → **21.681** no `TOTAL`.

Fonte: `rv_status.py` exporta por container `by_timeout` já reduzido a `{ok, err, done}`
(lido do `tasks.json`, no host — sem `docker exec`).

## Coleta + consolidação (LOCAL, após as VMs)

1. Copiar os resultados das 4 VMs para o layout esperado:
   `RESULTADOS_experimento-20260706/m<i>/results/exp_<j>/...` (com os `.logcat` preservados).
2. Consolidar **offline** a partir dos `.logcat` (os CSVs do container são zerados pelo
   resume — gotcha do `result_processor`):
   ```bash
   bash scripts/consolidate_offline.sh
   ```
   Três fases: validação (dedup COMPLETED + gate VerifyError) → regen (logcats → CSVs)
   → auditoria (`verify.py --full`, C1-C4). Consolidados em
   `RESULTADOS_.../summary,coverage,errors_regen.csv`; auditoria em `verification_report.md`.

## Estrutura

```
experimento-20260706/
├── README.md
├── docker-compose.{gcp,smoke}.yml
├── .env.m{1,2,3,4}
├── configs/smoke.json
├── filters/  (experiment_apks.txt=219, batch_00..15, smoke_batch, minismoke_batch)
└── scripts/
    ├── make_batches.sh            # (re)gera os filtros a partir do dataset
    ├── build_and_push_091.sh      # Fase 1 — imagens 0.9.1 + push
    ├── copy_dataset_to_vms.sh     # Fase 3 — scp dataset + experimento pras VMs
    ├── run_smoke.sh  run_experiment.sh
    ├── rv_status.py  monitor.sh   # monitoramento unificado
    └── consolidate_offline.sh     # coleta offline via logcats
```

## Notas
- **Não** gerenciar emuladores manualmente — `rv-platform` cuida (start/boot/install/cleanup).
- `ares`/`qtesting` sobem como containers-irmãos e puxam `phtcosta/{ares,qtesting}:latest`
  (default em `tool.py`) — por isso o push publica também a tag `latest`.
- OOM conhecido do 20260508: `ares`/`qtesting` estouravam a memória; `rv_status.py`
  classifica `oom/killed` no breakdown para detecção precoce.
- `preflight.sh` (patch androguard res1) só é necessário se a imagem pinar androguard
  3.4.0a1; na 0.9.1 (androguard 4.x) não deve ser preciso — mantido por precaução.
- O dataset já vem instrumentado + com `.apk.json`: `RV_SKIP_MONITORS`, `RV_SKIP_INSTRUMENT`
  e `RV_SKIP_STATIC_ANALYSIS` = `true`. **Gotcha:** `RV_APKS_DIR` DEVE apontar para os APKs
  instrumentados (é o caso), senão a cobertura sai 0%.

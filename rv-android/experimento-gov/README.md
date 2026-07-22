# experimento-gov — RV JCA sobre apps gov.br (local, APE)

Diretório de **execução** do experimento. O **dataset** e a memória de condução ficam em
`/home/pedro/desenvolvimento/RV_ANDROID_DATASET_GOV/` (`REGISTRO.md`, `dataset_gov_play.csv`).

**Plano/roadmap detalhado:** [`docs/20260718_experimento_gov.md`](docs/20260718_experimento_gov.md)

## Config
34 APKs (não-PAIRIP) · tool `ape` · instrumentação **dexlib2** · specs **JCA** · **8 containers** ·
timeout **3600s** · reps **1** · **sem análise estática** · imagem `phtcosta/rvandroid:0.9.2`.

## Fases (comandos)
```bash
# 1. Pré-instrumentar os 34 (host, 8 workers, resume-safe) -> APKS_INSTRUMENTADOS/
uv run python scripts/instrument_gov.py \
  --apks-dir /home/pedro/desenvolvimento/RV_ANDROID_DATASET_GOV/APKS \
  --filter filters/gov_all_34.txt --out instrumentation/out \
  --dest /home/pedro/desenvolvimento/RV_ANDROID_DATASET_GOV/APKS_INSTRUMENTADOS --workers 8

# 2. Smoke de execução (gate): 1 APK instrumentado, timeout curto — validar cov>0, 0 VerifyError

# 3. Run 8× (timeout 3600s)
EXP_TIMEOUT=3600 bash scripts/run_gov.sh

# 4. Monitorar
bash scripts/monitor_gov.sh          # progresso por container (COMPLETED distintos)

# 5. Resume final: re-rodar run_gov.sh 1× (recupera ERROR transitório); depois consolidar via logcats
```

## Gates
G1 34/34 instrumentados · G2 smoke exec (COMPLETED, cov>0, 0 VerifyError, roda sem `.apk.json`) ·
G3 34 COMPLETED distintos · G4 consolidação MOP/cov + relatório de violações JCA.

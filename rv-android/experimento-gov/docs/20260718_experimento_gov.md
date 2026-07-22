# Plano / Roadmap — Experimento RV JCA sobre apps gov.br (local, APE)

**Data:** 2026-07-18 · **Status:** pré-instrumentação em curso · **Dir execução:** `experimento-gov/`
**Dataset/dados:** `/home/pedro/desenvolvimento/RV_ANDROID_DATASET_GOV/` (exclusivo do dataset)
**Memória de condução:** `RV_ANDROID_DATASET_GOV/REGISTRO.md` (ler para o histórico das decisões)

---

## 1. Objetivo e hipótese

Detectar **erros MOP de JCA** (violações de uso da Java Cryptography Architecture) em uma
amostra de **apps do governo brasileiro (gov.br)**, via runtime verification do RV4Android,
usando o explorador **APE** para dirigir a UI. É uma **demonstração** (a pedido do orientador),
não uma comparação estatística de ferramentas.

- **H (informal):** apps gov.br exercitam JCA em runtime e ao menos alguns exibem **misuse**
  observável (violações RVSEC). Medimos por logcats `RVSEC`/`RVSEC-COV` não-vazios.
- **Métrica primária:** violações MOP JCA (`mop_unique` / `mop_total`) por app; secundária:
  cobertura de operações monitoradas (`cov_mop`).

## 2. Configuração (fechada)

| Parâmetro | Valor | Nota |
|---|---|---|
| APKs | **34** (não-PAIRIP) | 37 do dataset − 3 PAIRIP (§4). Todos têm superfície JCA > 0 (§3) |
| Tool | **`ape`** (vanilla, builtin) | exploração pura; não usa dado de análise estática |
| Instrumentação | **dexlib2** | `--instrumentation-variant dexlib2` (default do CLI é `ajc`!) |
| Specs | **JCA** | `--specification-set jca` |
| Containers | **8** (local) | `exp_00..07`, 4 cpus / 10g cada (32 cpus / 80g de 64/125) |
| Timeout | **3600 s** (1 h) | APE roda o timeout inteiro (nunca sai antes) |
| Repetições | **1** | 34 tasks totais |
| Análise estática | **PULADA** | GATOR é pesado; `ape` vanilla não precisa do `.apk.json` |
| Pré-proc | monitores JCA + instrumentação dexlib2 | **1× no host** (resume-safe) |
| Imagem | `phtcosta/rvandroid:0.9.2` | já publicada (`e19e7de67124`) |

**Tasks = 34 APKs × 1 tool × 1 rep × 1 timeout = 34.** Partição round-robin: `[5,5,4,4,4,4,4,4]`
→ container mais cheio = **5 tasks**.

## 3. Decisão do conjunto — superfície JCA (martelo batido)

O `instrument_verdict` herdado (13 candidate / 24 reject) rejeitava por **framework**
(Flutter/RN = "cripto em Dart/JS"). **Refutado por evidência:** o monitor RV4Android dispara em
**qualquer** chamada JCA no bytecode Java que executa — inclusive de **libs Java empacotadas**.

Scan de **call-sites JCA** (androguard, `invoke-*` → classe JCA de plataforma, em todos os dex;
sólido sob ofuscação — a classe alvo não é ofuscável). Resultado: **os 34 têm superfície JCA > 0**;
vários "reject" RN/Flutter têm as **maiores** (identidadenacional 649, antt 511, valid.rnm 463).
→ **nenhum corte por JCA.** Planilha atualizada (`dataset_gov_play.csv`, colunas `jca_*` agora são
call-sites; `.grep.bak` guarda os valores antigos). Detalhe em `REGISTRO.md §2`.

Reachability real (alcance de entry point) foi **descartada**: exige call graph (a SA que pulamos)
e é indecidível por prefixo de pacote sob ofuscação. **O runtime é o oráculo de reachability.**

## 4. Exclusões (PAIRIP) — instrumentabilidade, não JCA

3 apps com anti-tamper **PAIRIP** (`libpairipcore.so`): `carteiradigital`, `cnhe`, `exercitobr`.
A instrumentação dexlib2 **modifica o DEX e re-assina** → o PAIRIP detecta em runtime e **crasha
no launch**. **Descartados sem smoke** (justificativa sólida; não gastar a janela). Registrados como
exclusão por instrumentabilidade.

## 5. Pipeline (fases)

```
(1) PRÉ-INSTRUMENTAÇÃO  →  (2) SMOKE DE EXECUÇÃO  →  (3) RUN 8×  →  (4) RESUME FINAL  →  (5) CONSOLIDAÇÃO
   host, 8 workers            1-2 APKs, T curto      3600s/task        recupera ERROR       offline via logcats
   monitores+dexlib2          valida gates                              transitório         (dedup + MOP)
   NO static
```

### Fase 1 — Pré-instrumentação (host, resume-safe)
`scripts/instrument_gov.py`: N workers Docker rodam `rv-experiment run --skip-execution --skip-static
--instrumentation-variant dexlib2 --specification-set jca` sobre os 34 originais; coleta os `.apk`
instrumentados em `APKS_INSTRUMENTADOS/`. Monitores JCA gerados 1×/worker (~80s); dexlib2 ~80s+/APK.
```bash
uv run python experimento-gov/scripts/instrument_gov.py \
  --apks-dir /home/pedro/desenvolvimento/RV_ANDROID_DATASET_GOV/APKS \
  --filter   experimento-gov/filters/gov_all_34.txt \
  --out      experimento-gov/instrumentation/out \
  --dest     /home/pedro/desenvolvimento/RV_ANDROID_DATASET_GOV/APKS_INSTRUMENTADOS \
  --workers  8
```
**Gate 1:** 34/34 `.apk` instrumentados em `APKS_INSTRUMENTADOS/` (senão, ver `instrument_missing.txt`).

### Fase 2 — Smoke de execução (gate antes da run completa)
Rodar 1-2 APKs instrumentados, timeout curto (ex. 120s), 1 container, e validar:
- task **COMPLETED**; `.logcat` não-vazio; **cobertura > 0**; **0 VerifyError**;
- confirma que **`ape` + skip-static roda sem `.apk.json`** (risco conhecido — validar aqui).

### Fase 3 — Run (8 containers, 3600s)
```bash
EXP_TIMEOUT=3600 bash experimento-gov/scripts/run_gov.sh
# (up -d -> docker wait exp_00..07 -> down)
```

### Fase 4 — Resume final
Ao terminar, ~5% de ERROR transitório (`adb install`/boot). Re-rodar `run_gov.sh` **uma vez** — o
resume pula COMPLETED e re-executa ERROR. **NÃO** dar `down` antes de extrair os traces.

### Fase 5 — Consolidação (offline, via logcats)
Consolidar dos `.logcat` (CSVs de resume podem zerar — gotcha gh58). Reusar o consolidador da skill
`.claude/skills/rv-experiment-compare/scripts/consolidate_compare.py` (ou adaptar para single-tool),
extraindo por app: `mop_unique`, `mop_total`, `cov_mop`, e a lista de violações RVSEC.

## 6. Tempo e janela

Cada task APE ≈ **~62 min** (3600s + ~65s overhead: boot ~20-35s + install + teardown; static ≈0).
Container mais cheio = 5 tasks → **run ≈ 5,2 h**. Pré-proc ~0,5-1 h + smoke ~0,25 h.

| Marco | ETA (aprox., start pré-proc ~22:00) |
|---|---|
| Pré-instrumentação (34) | ~22:45 |
| Smoke execução | ~23:00 |
| Run 8× (5,2h) | **~04:15** |
| Resume final | ~05:00 |

Janela até **19/07 09:00** (~11h) → **folga ~4h**. Confortável.

## 7. Gates

- **G1 (pré-proc):** 34/34 instrumentados.
- **G2 (smoke exec):** COMPLETED · logcat não-vazio · cov > 0 · 0 VerifyError · roda sem `.apk.json`.
- **G3 (run):** 34 identidades distintas COMPLETED (dedup por `(apk,tool,variant,rep,timeout)`).
- **G4 (dados):** consolidação reconstrói MOP/cov dos logcats; reportar apps com violação JCA.

## 8. Riscos

| Risco | Mitigação |
|---|---|
| `ape` + skip-static exige `.apk.json` e erra | validar no **smoke G2**; se errar, gerar `.apk.json` mínimo ou re-incluir static só p/ gerar o json |
| Resume força skip-instrument → roda APK original (cov 0) | **pré-instrumentar** (feito) elimina o risco |
| 8 emuladores no mesmo host (KVM/RAM) | 80g/32cpu de 125g/64; `RV_DELAY` escalonado evita boot-storm |
| ERROR transitório (`adb install`) ~5% | passada de resume (Fase 4) |
| RN/Flutter sem misuse → MOP 0 | esperado p/ alguns; é resultado válido (superfície ≠ execução) |
| Arquivos de saída root-owned (container) | coleta lê (world-readable); limpeza pós com `sudo` se preciso |

## 9. Artefatos em `experimento-gov/`

```
experimento-gov/
├── docker-compose.gov.yml         # run: 8 containers, ape, dexlib2, jca, skips, T=3600
├── filters/
│   ├── gov_all_34.txt             # os 34 (não-PAIRIP)
│   ├── batch_00..07.txt           # partição round-robin p/ os 8 containers
│   └── smoke_1.txt                # 1 APK p/ smoke
├── scripts/
│   ├── instrument_gov.py          # Fase 1 — pré-instrumentação (dexlib2, skip-static)
│   ├── run_gov.sh                 # Fase 3/4 — up + wait + down (+ resume)
│   └── monitor_gov.sh             # Fase 3 — progresso por container
├── instrumentation/               # saídas da pré-instrumentação (efêmero)
├── docs/20260718_experimento_gov.md   # este plano
└── results/exp_00..07/            # resultados da run (tasks.json + .logcat)
```

## 10. Checklist / roadmap

- [x] Scan de call-sites JCA (34/34 com superfície) · CSV + schema atualizados · REGISTRO
- [x] Decisão: dataset = 34 (PAIRIP fora) · reps=1 · 8 containers · pré-instrumentar
- [x] Artefatos: filtros, compose, scripts, plano
- [ ] **G1** Pré-instrumentação 34/34 (em curso)
- [ ] **G2** Smoke de execução (gates)
- [ ] **G3** Run 8× completa (34 COMPLETED)
- [ ] **G4** Resume final + consolidação + relatório de violações JCA

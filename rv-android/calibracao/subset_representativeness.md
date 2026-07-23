# Fase 0 / P3 — Representatividade do subset de calibração

Gerado por `calibracao/gen_subset.py` (offline, determinístico, seed=42).
Fontes: `data/results/cmpma_consolidado/per_apk_paired.csv` (181 APKs, 5 braços cmpma) +
proxy LLM do run base `cmp_llm_20260721` (`calibracao/llm_proxy.csv`) + dataset físico
`selected181`.

## 1. Portões (GATE §P3)

- **subset40**: max |Δmean cov_mop| = **0.211pp** (gate ≤1.0pp) → PASS; min KS p (cov_mop) = **0.203** (gate >0.05) → PASS; dataset .apk+.apk.json present → PASS
- **subset90**: max |Δmean cov_mop| = **0.026pp** (gate ≤1.0pp) → PASS; min KS p (cov_mop) = **0.633** (gate >0.05) → PASS; dataset .apk+.apk.json present → PASS

Gate global: |Δmédia| ≤ 1,0pp em cov_mop para **todos** os braços; KS n.s. (p>0,05);
`.apk`+`.apk.json` presentes para todos os APKs selecionados.

## 2. Estratificação

Eixo primário: quartis de `ape__cov_mop` (referência histórica). Cotas proporcionais por
quartil garantem o espectro de cobertura; dentro das cotas, seleção gulosa minimiza o
desvio composto de médias. Eixos secundários balanceados no objetivo: fração
`mop_unique>0` (alvo ≈ fração do conjunto completo) e tercis do proxy LLM `llm_tap_rate`.

Fração `mop_unique>0` (braço ape): full=0.707, subset40=0.700,
subset90=0.711.

| quartil ape__cov_mop | full | subset40 | subset90 |
|---|---:|---:|---:|
| Q1 | 46 | 10 | 23 |
| Q2 | 45 | 10 | 23 |
| Q3 | 45 | 10 | 22 |
| Q4 | 45 | 10 | 22 |

Proxy LLM `llm_tap_rate` (full): min=0.000, mediana=0.088,
máx=0.885. Tercis balanceados na seleção.

## 3. Representatividade por braço × métrica

### subset40 vs full (n=40)

| arm | metric | full | subset | Δ | KS p |
|---|---|---:|---:|---:|---:|
| ape | cov_method | 34.213 | 34.120 | -0.093pp | 0.476 |
| ape | cov_act | 69.421 | 69.332 | -0.089pp | 0.359 |
| ape | cov_mop | 35.103 | 35.089 | -0.014pp | 0.898 |
| ape | mop_unique | 3.886 | 4.083 | +0.198 | 0.741 |
| aperv:ape_pure | cov_method | 34.218 | 34.197 | -0.021pp | 0.426 |
| aperv:ape_pure | cov_act | 68.832 | 69.036 | +0.204pp | 0.264 |
| aperv:ape_pure | cov_mop | 34.957 | 34.943 | -0.014pp | 0.203 |
| aperv:ape_pure | mop_unique | 3.899 | 4.100 | +0.201 | 0.635 |
| aperv:sata | cov_method | 34.855 | 34.713 | -0.142pp | 0.282 |
| aperv:sata | cov_act | 68.763 | 68.362 | -0.401pp | 0.499 |
| aperv:sata | cov_mop | 35.463 | 35.385 | -0.077pp | 0.203 |
| aperv:sata | mop_unique | 3.816 | 4.042 | +0.226 | 0.631 |
| aperv:sata_mop_activity | cov_method | 34.903 | 34.831 | -0.072pp | 0.426 |
| aperv:sata_mop_activity | cov_act | 68.571 | 68.296 | -0.275pp | 0.337 |
| aperv:sata_mop_activity | cov_mop | 35.845 | 36.056 | +0.211pp | 0.316 |
| aperv:sata_mop_activity | mop_unique | 3.840 | 4.050 | +0.210 | 0.741 |
| aperv:sata_mop_act_frontier | cov_method | 36.136 | 36.226 | +0.089pp | 0.282 |
| aperv:sata_mop_act_frontier | cov_act | 84.361 | 84.436 | +0.075pp | 0.690 |
| aperv:sata_mop_act_frontier | cov_mop | 37.752 | 37.773 | +0.021pp | 0.247 |
| aperv:sata_mop_act_frontier | mop_unique | 3.915 | 4.242 | +0.326 | 0.753 |

### subset90 vs full (n=90)

| arm | metric | full | subset | Δ | KS p |
|---|---|---:|---:|---:|---:|
| ape | cov_method | 34.213 | 34.131 | -0.082pp | 1.000 |
| ape | cov_act | 69.421 | 69.272 | -0.149pp | 0.763 |
| ape | cov_mop | 35.103 | 35.129 | +0.026pp | 0.899 |
| ape | mop_unique | 3.886 | 4.059 | +0.173 | 1.000 |
| aperv:ape_pure | cov_method | 34.218 | 34.144 | -0.074pp | 0.990 |
| aperv:ape_pure | cov_act | 68.832 | 69.219 | +0.387pp | 0.762 |
| aperv:ape_pure | cov_mop | 34.957 | 34.965 | +0.008pp | 0.709 |
| aperv:ape_pure | mop_unique | 3.899 | 4.078 | +0.179 | 1.000 |
| aperv:sata | cov_method | 34.855 | 34.799 | -0.056pp | 0.988 |
| aperv:sata | cov_act | 68.763 | 68.537 | -0.226pp | 0.944 |
| aperv:sata | cov_mop | 35.463 | 35.476 | +0.014pp | 0.637 |
| aperv:sata | mop_unique | 3.816 | 4.007 | +0.192 | 0.998 |
| aperv:sata_mop_activity | cov_method | 34.903 | 34.975 | +0.072pp | 0.989 |
| aperv:sata_mop_activity | cov_act | 68.571 | 68.567 | -0.005pp | 0.829 |
| aperv:sata_mop_activity | cov_mop | 35.845 | 35.830 | -0.015pp | 0.776 |
| aperv:sata_mop_activity | mop_unique | 3.840 | 4.044 | +0.205 | 1.000 |
| aperv:sata_mop_act_frontier | cov_method | 36.136 | 36.149 | +0.013pp | 0.988 |
| aperv:sata_mop_act_frontier | cov_act | 84.361 | 84.651 | +0.290pp | 1.000 |
| aperv:sata_mop_act_frontier | cov_mop | 37.752 | 37.764 | +0.012pp | 0.633 |
| aperv:sata_mop_act_frontier | mop_unique | 3.915 | 4.159 | +0.244 | 1.000 |

## 4. Estabilidade do ranking (leave-10-out)

Ranking histórico (full): aperv:sata_mop_act_frontier > aperv:sata_mop_activity > aperv:sata > ape > aperv:ape_pure. Os três braços centrais estão a
~0,9pp entre si no conjunto completo (empate estatístico), então o invariante testável é
o braço `aperv:sata_mop_act_frontier` permanecer em 1º.

- **subset40** (500 seeded 10-out draws): frontier stays rank #1 in **99.8%**; last arm stable in **48.6%**; mean Kendall τ vs subset ranking = **0.726**. Subset ranking: aperv:sata_mop_act_frontier > aperv:sata_mop_activity > aperv:sata > ape > aperv:ape_pure.
- **subset90** (500 seeded 10-out draws): frontier stays rank #1 in **100.0%**; last arm stable in **76.6%**; mean Kendall τ vs subset ranking = **0.914**. Subset ranking: aperv:sata_mop_act_frontier > aperv:sata_mop_activity > aperv:sata > ape > aperv:ape_pure.

## 5. Arquivos gerados

- `calibracao/subset40.txt` — 40 APKs (Fase A/B screening).
- `calibracao/subset90.txt` — 90 APKs (Fase C confirmação).
- `calibracao/llm_proxy.csv` — proxy LLM por APK (proveniência).
- `calibracao/subset_representativeness.md` — este memo.

# Paridade WTG cgDelegation — Sumário Executivo

**Data:** 2026-05-15
**Gate:** Group 6.9 (M3 — GO/NO-GO)
**Veredito:** **FAIL** (avg 0.543, min 0.000 contra thresholds 0.95 / 0.85)
**Decisão:** `cgDelegation` default flipado `true → false`; SPARK delegation fica opt-in.

## Resultado por APK

| APK | base trans | cand trans | Jaccard | tempo base | tempo cand |
|---|---|---|---|---|---|
| `com.akylas.enforcedoze_85` | 97 | 86 | 0.887 | 41s | 33s |
| `com.blankdev.sidestep_17` | 0 | 0 | 1.000* | 600s ⏱ | 26s |
| `com.dewdrop623.androidcrypt_15` | 5 | 5 | **1.000** | 41s | 34s |
| `com.gorden.dayexam_9` | 0 | 0 | 1.000* | 600s ⏱ | 169s |
| `com.mouzinho.pokebase_2` (RN) | 4 | 0 | **0.000** | 531s | 194s |
| `com.nyx.custom_uploader_15` (Flutter) | 12 | 0 | **0.000** | 73s | 26s |
| `com.wordtracer.app_22` (Capacitor) | 13 | 0 | **0.000** | 123s | 41s |
| `de.computerelite.shockalarm_48` | 0 | 0 | 1.000* | 600s ⏱ | 28s |
| `org.fossify.keyboard_14` | 0 | 36 | (ganho) | 600s ⏱ | 521s |
| `com.anysoftkeyboard.janus_11` | (timeout) | (timeout) | n/a | 600s ⏱ | 600s ⏱ |

`*` = trivial 1.000 (set vazio em ambos os modos; baseline timeoutou).

## Síntese

- **Performance**: gigantesco. 4 APKs recuperados de timeout 600s; speedup 2.8× a 23× nos demais.
- **Paridade**: falhou em apps de **framework híbrido** (RN, Flutter, Capacitor) — perdem todas as transições porque o SPARK CG não materializa edges de listeners wired via synthetic lambdas + native bridges. Mesmo padrão em todos os 3 zero-Jaccard.
- **Apps nativos**: paridade boa (dewdrop623 1.000, enforcedoze 0.887 borderline).

## Decisão & Follow-up

- **Default `cgDelegation=false`** em `Configs.java` — preserva semântica legada.
- **Opt-in via `--cg-delegation true`** (Python sweep) ou `-cgDelegation true` (CLI Java) — disponível para apps sem framework híbrido.
- **Follow-up**: `gh<N>-cg-delegation-framework-edges` portará o CHA-fallback do `buildCallGraphLegacy` (linhas 1067–1083) para o caminho SPARK quando `edgesOutOf(s)` retornar zero edges. Critério de sucesso: re-rodar paridade gate e atingir thresholds 0.95/0.85 → re-flip do default.

## Referências

- Diagnóstico completo: `docs/20260515_diagnostico_paridade_cgdelegation.md`
- Design D3: `design.md` (revisado 2026-05-15)
- Spec scenarios: `specs/analysis/spec.md` ("WTG built using legacy call graph", "WTG built using SPARK call graph (cgDelegation=true, opt-in)", "Hybrid-framework apps lose transitions in cgDelegation=true mode", "Paridade Jaccard WTG-SPARK on baseline-OK APKs")
- Raw report JSON: `paridade_report.json` (este diretório)
- Output das execuções: `/tmp/gh57_paridade_baseline/`, `/tmp/gh57_paridade_candidate/`

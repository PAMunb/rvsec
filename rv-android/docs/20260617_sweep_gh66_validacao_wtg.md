# Sweep de validação gh66 — diff-zero da WTG nos 169 APKs

**Data:** 2026-06-17
**Change:** `gh66-gator-wtg-flowcontainer-perf` (otimização de `FlowgraphRebuilder.buildFlowThroughContainer`)
**Relacionado:** `docs/20260609_sweep_wtg_completo_169.md` (sweep que gerou a baseline), `docs/20260613_relatorio_sweep_wtg_jca_169.md` (relatório da baseline), `docs/20260613_wtg_timeout_buildflowthroughcontainer.md` (diagnóstico)

## 1. Objetivo

Provar empiricamente, no corpus de 169 APKs JCA do `experimento-20260604`, que a otimização do gh66:

1. **§4.1 — diff-zero (gate de correção):** produz um conjunto de transições **idêntico** ao da baseline nos **72 APKs** que já tinham `transitions>0` (INV-ANA-39). Qualquer aresta a mais ou a menos **reprova** a change.
2. **§4.2 — recuperação (medição de benefício):** mede quantos dos **97** APKs que antes davam timeout em `buildFlowThroughContainer` agora completam a WTG e emitem `transitions[]`.

Mais: **§4.3** jstack re-probe (o gargalo saiu de `getReadContainerField`), **§4.4** NFR04 (timeout ainda preserva reachability+windows+components), **§4.5** clean-rebuild reproduz o JAR validado.

## 2. Regra de ouro: espelhar a config da baseline

O diff-zero só vale se o sweep candidato usar a **mesma** config que gerou `out/sweep_20260604_wtg_spark`. O que **afeta o conteúdo** das transitions e portanto é **obrigatório** casar:

- `--cg-algorithm spark`
- `--cg-delegation true`
- **WTG ligada** — ou seja, **NUNCA** passar `--skip-wtg` (essa flag PULA a construção da WTG; o dataset do experimento `out/sweep_20260604` foi rodado com ela, mas a baseline de transitions é um run separado **sem** a flag).

O que **não** afeta o conteúdo de um APK que completa (só throughput/quais completam): `--workers`, `--timeout`, `--jvm-memory`. Espelhamos mesmo assim, por higiene metodológica.

**Script:** é o mesmo `scripts/static_analysis_sweep.py` que gerou a baseline — não há script dedicado de WTG. A WTG é construída por padrão (quando `--skip-wtg` está ausente).

## 3. Config por estágio (espelha o relatório da baseline)

Máquina: 64 cores / 125 GB RAM. Constante em todos: `--cg-algorithm spark --cg-delegation true`, **sem `--skip-wtg`**. Saída única `out/sweep_gh66_wtg_spark/` (consolidação por resume).

| Estágio | APKs | workers | timeout | jvm | RAM pico | Papel no gh66 |
|---------|------|---------|---------|-----|----------|---------------|
| **A** bulk | 169 | 8 | 1800s | 12g | ~96 GB | Fecha as 72 (→ §4.1) e recupera parte das 97 (→ §4.2) |
| **C** alta-mem | os `failed_no_json` (OOM) de A (≈5) | 2 | 3600s | 60g | ~120 GB | **Inalterado** — o OOM é da fase de reachability (FixpointSolver/meet), que o gh66 NÃO toca; ainda precisa de 60g |
| **B** tempo↑ | timeouts restantes de A | 8 | 3600s | 14g | ~112 GB | Mede recuperação extra (gh66 + tempo). Na baseline o yield foi nulo (timeout era fútil pelo laço quadrático); com o gh66 é o teste interessante |

> Na baseline: A=1800s/8w/12g (~7h26m; 164 complete, 68 tr>0, 5 OOM), C=3600s/2w/60g (5/5 recuperados), B=3600s/8w/14g (yield ~nulo). Final: 169/169 complete, 72 com tr>0.

## 4. Comandos

```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
# Java 25 é o default da máquina/Docker; lib/gator já tem o JAR gh66 (rebuild 2026-06-17).
# NÃO exportar JAVA_HOME para 21.

# --- Estágio A — bulk, 169 (WTG construída; SEM --skip-wtg) ---
uv run python scripts/static_analysis_sweep.py \
    --apks-dir out/sweep_20260604_apks \
    --output ./out/sweep_gh66_wtg_spark \
    --planilha /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/PLANILHA_dexlib2.csv \
    --cg-algorithm spark --cg-delegation true \
    --timeout 1800 --workers 8 --jvm-memory 12g

# --- Construir o subset de pendentes entre estágios ---
# O resume normal PULA status `complete`, e um timeout de WTG deixa `complete` com
# transitions vazio. Por isso B/C usam um dir de symlinks SÓ com os pendentes:
#   - C: os APKs que saíram de A como failed_no_json (OOM)
#   - B: os APKs `complete` mas com transitions==0 (timeout de WTG)
# (montar o dir de symlinks a partir de out/sweep_gh66_wtg_spark/_progress/*.json,
#  apontando para out/sweep_20260604_apks — NÃO copiar APKs.)

# --- Estágio C — os OOM, alta memória ---
uv run python scripts/static_analysis_sweep.py \
    --apks-dir out/sweep_gh66_wtg_pending_oom \
    --output ./out/sweep_gh66_wtg_spark \
    --planilha /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/PLANILHA_dexlib2.csv \
    --cg-algorithm spark --cg-delegation true \
    --timeout 3600 --workers 2 --jvm-memory 60g
#   (se infomaniak.meet reaparecer pior: --workers 1 --jvm-memory 100g)

# --- Estágio B — timeouts restantes, tempo estendido ---
uv run python scripts/static_analysis_sweep.py \
    --apks-dir out/sweep_gh66_wtg_pending_timeout \
    --output ./out/sweep_gh66_wtg_spark \
    --planilha /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/PLANILHA_dexlib2.csv \
    --cg-algorithm spark --cg-delegation true \
    --timeout 3600 --workers 8 --jvm-memory 14g
```

## 5. Validação pós-sweep

### Regra de comparação (o que muda e o que não pode mudar)

O gh66 só toca `buildFlowThroughContainer` (alimenta as transitions). Logo, comparando cada APK baseline × gh66:

- **`reachability`, `windows`, `components`, `package`, `mainActivity` → 100% IDÊNTICOS.** Qualquer diferença reprova (seria efeito colateral inesperado do gh66). Esses campos vêm de partes do pipeline que o gh66 não toca (reachability do CG do SPARK; windows/components da análise de GUI).
- **`transitions` → único campo com diferença aceitável:** diff-zero nas 72 (mesmo conjunto de arestas); nas 97, só **adições** (recuperação), nunca remoções.

A comparação é **independente de ordem e de IDs**: GATOR não garante ordem dos arrays e os IDs numéricos de janela/widget não são estáveis entre builds. O comparador canonicaliza (ordena) tudo e remove os `id` antes de comparar; transitions são resolvidas a nomes estáveis.

```bash
# §4.1 (GATE PRINCIPAL) — invariância completa: reachability/windows/components idênticos
#                         + transitions diff-zero nas 72 + adições nas recuperadas.
python3 scripts/wtg_sweep_invariance.py \
    out/sweep_20260604_wtg_spark out/sweep_gh66_wtg_spark \
    --report out/gh66_invariance_report.json
#   verdict PASS = nenhum campo invariante difere E transitions diff-zero em toda APK tr>0.

# §4.1 (sub-gate de transitions, detalhe aresta-a-aresta) — opcional, mais verboso:
python3 scripts/wtg_edge_diff.py \
    out/sweep_20260604_wtg_spark out/sweep_gh66_wtg_spark \
    --show-edges --report out/gh66_diffzero_report.json
#   verdict PASS = INV-ANA-39 vale nas 72. QUALQUER aresta divergente reprova.

# §4.2 — recuperação: contar transitions>0 no sweep gh66 e subtrair 72.
python3 - <<'PY'
import json, glob
js=[p for p in glob.glob("out/sweep_gh66_wtg_spark/*/*.apk.json") if "_backup" not in p]
tr=sum(1 for p in js if len(json.load(open(p)).get("transitions",[]))>0)
print(f"gh66 tr>0 = {tr}  (baseline 72)  →  recuperados = {tr-72}")
PY

# §4.3 — jstack re-probe: o `main` não deve mais estar dominado por getReadContainerField.
bash scripts/jstack_wtg_probe.sh ch.famoser.mensa

# §4.4 — NFR04: num APK que AINDA dá timeout, conferir que o JSON parcial mantém
#         reachability+windows+components (transitions[] vazio).

# §4.5 — clean-rebuild: mvn clean install -DskipTests -pl sootandroid,client -am
#         (no rvsec-gator), re-rodar o §4.1 → ainda PASS (fresh clone reproduz o artefato).
```

## 6. Caveats

1. **Identidade de config** (§2): só `spark`+`cgDelegation=true`+WTG-ligada afetam o conteúdo. **Nunca `--skip-wtg`.**
2. **As 5 OOM são reachability, não WTG** — gh66 não as muda; continuam exigindo 60g (Estágio C).
3. **NÃO usar `--succ-depth`** — provado alavanca errada (recuperação de 24/97 com sDepth=3 deu 0).
4. **Aperto de RAM no Estágio C**: 2×60g = 120 de 125 GB. Garantir que nada pesado rode junto.
5. **Resume/estágios**: tudo na mesma saída `out/sweep_gh66_wtg_spark/`; B/C usam dir de symlinks dos pendentes (resume pula `complete`).
6. **Comparadores** (ambos em `scripts/`, validados 2026-06-17):
   - `wtg_sweep_invariance.py` — **gate principal**. Por APK: reachability/windows/components/package/mainActivity têm de ser idênticos (canonicalização ordena dicts/listas → independe de ordem; remove `id` numéricos → independe de IDs); transitions classificado (diff-zero nas tr>0, adições nas tr==0). Verdict FAIL se qualquer campo invariante diferir ou houver add/remove de transition numa APK tr>0.
   - `wtg_edge_diff.py` — sub-gate de transitions (chave estável de 6 campos: janela origem/destino, tipo do evento, nome+classe do widget, handler; IDs resolvidos via `windows[]`; `_backup/` excluído; set-equality).
   - **Validação do comparador (antes do sweep):** baseline-vs-baseline → PASS (169/169, 72 no conjunto diff-zero). Teste de mutação (5 casos): ordem trocada → PASS; IDs remapeados consistentemente → PASS; flip de bool de reachability → FAIL (reachability); aresta extra numa APK tr>0 → FAIL (transitions); tr 0→>0 → recovery (não falha). Confirma: **ordem/ID não falham; dado real falha; transitions é o único campo com diferença sancionada.**

## 7. Pré-requisitos — verificados 2026-06-17 (PRONTO PARA EXECUTAR)

| # | Item | Estado |
|---|------|--------|
| 1 | `out/sweep_20260604_apks` — 169 symlinks → `JOAO/APKs` | ✅ 169 symlinks, 0 quebrados, batem 1:1 com `experiment_apks.txt` (sem cópia de APK) |
| 2 | JAR gh66 em `lib/gator/rvsec-gator.jar` | ✅ 3 símbolos novos, bytecode v65 (build Java 25, 2026-06-17) |
| 3 | Baseline `out/sweep_20260604_wtg_spark` | ✅ 169 JSONs, 72 com `transitions>0` (conjunto do gate) |
| 4 | Tooling | ✅ `wtg_edge_diff.py`, `jstack_wtg_probe.sh`, `static_analysis_sweep.py` |
| 5 | Saída `out/sweep_gh66_wtg_spark` | ✅ não existe (sem risco de clobber) |
| 6 | Planilha `PLANILHA_dexlib2.csv` | ✅ presente |
| 7 | Recursos | ✅ 64 cores / 125 GB RAM (93 livres) / 2.2 TB em disco |

**Estimativa:** Estágio A provavelmente mais rápido que as 7h26m da baseline (o gh66 corta o gargalo quadrático). Total ~8–12h, quase tudo desatendido.

**Falta só o "vai".** Como é job de horas, não disparar sem autorização explícita. Opção de gate rápido: rodar primeiro só as 72 (subset de symlinks) para o diff-zero (~1h) antes de comprometer o sweep completo dos 169.

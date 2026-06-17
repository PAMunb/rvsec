# Sweep estático completo (com WTG) nos 169 APKs — plano de execução

**Data:** 2026-06-09
**Objetivo:** produzir os 169 JSONs do `experimento-20260604` com **todas as seções
preenchidas**, incluindo `transitions[]` (a única que faltou no run anterior, que
usou `--skip-wtg`).

## 1. Ponto de partida

| Item | Valor |
|------|-------|
| Script | `scripts/static_analysis_sweep.py` (resume + cross-validation com PLANILHA) |
| Run anterior | `out/sweep_20260604/` — **169/169 `complete`, mas `--skip-wtg`** |
| Lacuna | `transitions[]` vazia em todos os 169 (`transitions_count: 0`) |
| Dir de APKs (169 symlinks) | `out/sweep_20260604_apks/` |
| Filtro 169 | `experimento-20260604/filters/experiment_apks.txt` |
| PLANILHA | `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/PLANILHA_dexlib2.csv` |
| Máquina | 125 GB RAM / 64 cores |
| Output NOVO | `out/sweep_20260604_wtg/` (preserva o run skip-wtg, que é fonte do dataset) |

No run anterior, `reachability`, `windows` e `components` já vêm completos —
`windows[]` é extraída por parse direto de XML, **não** depende da WTG. Só
`transitions[]` exige `WTGBuilder.build()`, a fase que foi pulada.

## 2. Decisões tomadas (2026-06-09)

1. **SPARK em tudo:** `--cg-algorithm spark` (já é default da reachability) **+
   `--cg-delegation true`** (acelera a fase WTG via `Scene.v().getCallGraph()`).
   - ⚠️ **Caveat de paridade M3 (2026-05-15):** SPARK pode perder nós/transições da
     WTG em apps híbridos (React Native / Flutter / Capacitor). Decisão do usuário:
     seguir SPARK assim mesmo; os híbridos são **marcados na triagem** (Estágio D)
     como "transitions aproximadas", não re-processados com o caminho legado.
2. **Wall-clock equilibrado:** escada A (900s) → B (1800s) → C (60g). Para na maioria;
   teimosos remanescentes ficam com `transitions[]` vazio, rotulados na triagem.
3. **Triagem por log** para `transitions==0`: inspecionar `_logs/<apk>.log` —
   `WTG construction failed` / kill por timeout = **falha** (pendência); ausência de
   erro + WTG concluída = **genuíno-0** (app sem navegação, conta como sucesso).

## 3. Gotchas que moldam o plano

1. **`complete:true` no JSON NÃO indica WTG executada.** Verificado: os 169 JSONs
   skip-wtg têm `complete=True` com `transitions=[]`. É só sentinela de integridade
   (JSON não-truncado). **Único sinal confiável de WTG real: `transitions_count > 0`.**
2. **`transitions==0` é ambíguo:** WTG concluída com 0 transições genuínas **vs.**
   timeout/OOM (write-first deixa vazio). Resolve-se via log (Estágio D).
3. **O resume normal PULA esses APKs:** timeout de WTG deixa status `complete` (seção
   `transitions` presente, só vazia) → fora de `DEFAULT_RETRY_STATUSES` → não
   reprocessa. Por isso os Estágios B/C usam **dir de symlinks só com os
   `transitions==0`** + `--retry-statuses complete` para forçar o re-run apenas neles
   (os com `transitions>0` ficam de fora do symlink dir e não são tocados).

## 4. Escada de execução

Todos os estágios escrevem no MESMO `out/sweep_20260604_wtg/` (consolidação por resume).

### Estágio A — bulk (todos os 169)
```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
uv run python scripts/static_analysis_sweep.py \
    --apks-dir out/sweep_20260604_apks \
    --output ./out/sweep_20260604_wtg \
    --planilha /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/PLANILHA_dexlib2.csv \
    --cg-algorithm spark --cg-delegation true \
    --timeout 900 --workers 8 --jvm-memory 12g
```
Apps simples fecham a WTG em ~30–60 s. Com SPARK, a estimativa do doc WTG é
`~30 s–2 min/APK` → bulk pode terminar em poucas horas (ou <2 h).

### Construir o subconjunto `transitions==0` (entre estágios)
```bash
python3 - <<'EOF'
import csv, os
src="/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs"
out="out/sweep_20260604_wtg_pending_apks"; os.makedirs(out, exist_ok=True)
rows=list(csv.DictReader(open("out/sweep_20260604_wtg/progress.csv")))
pend=[r["apk_name"] for r in rows if int(r["transitions_count"] or 0)==0]
for f in os.listdir(out): os.unlink(os.path.join(out,f))
for name in pend:
    s=os.path.join(src,name)
    if os.path.exists(s): os.symlink(s, os.path.join(out,name))
print(f"pending (transitions==0): {len(pend)} → {out}")
EOF
```

### Estágio B — timeout↑ (só os pendentes)
```bash
uv run python scripts/static_analysis_sweep.py \
    --apks-dir out/sweep_20260604_wtg_pending_apks \
    --output ./out/sweep_20260604_wtg \
    --planilha /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/PLANILHA_dexlib2.csv \
    --cg-algorithm spark --cg-delegation true \
    --retry-statuses complete \
    --timeout 1800 --workers 4 --jvm-memory 24g
```
Rebuild do subconjunto e repetir.

### Estágio C — memória↑ (patológicos)
```bash
uv run python scripts/static_analysis_sweep.py \
    --apks-dir out/sweep_20260604_wtg_pending_apks \
    --output ./out/sweep_20260604_wtg \
    --planilha /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/PLANILHA_dexlib2.csv \
    --cg-algorithm spark --cg-delegation true \
    --retry-statuses complete \
    --timeout 3600 --workers 2 --jvm-memory 60g
```
(`com.infomaniak.meet` precisou de 100g na fase reachability — se reaparecer,
`--workers 1 --jvm-memory 100g`.)

### Estágio D — triagem por log
Para cada APK ainda com `transitions==0`, classificar via `_logs/<apk>.log`:
- `WTG construction failed` ou kill por timeout → **falha** (pendência real).
- Sem erro + "Analysis complete" após a fase WTG → **genuíno-0** (sucesso).
- App híbrido (RN/Flutter/Capacitor) → marcar **transitions aproximadas** (caveat SPARK M3).

## 5. Critério de sucesso

- 169/169 com `reachability`, `windows`, `components` (já garantido) **+**
- `transitions[]` populada em todos exceto os rotulados **genuíno-0** ou
  **híbrido-aproximado** na triagem (Estágio D).
- 0 JSON truncado (`complete=true` em todos).

## 5b. Bug do SPARK encontrado e corrigido (2026-06-09)

O Estágio A (8w/900s/12g, `cgDelegation=true`) revelou que SPARK **não** era um
ajuste de config — era um bug. Balanço do Estágio A (169):
- 34 `transitions>0` (SPARK funcionou)
- **72 crash determinístico** `ArrayIndexOutOfBoundsException: Index 1 out of bounds for length 1` (~2 s)
- 63 timeout mid-WTG (900s)
- 8 `failed_no_json` (pesados)

**Causa-raiz** (stack trace via build diagnóstico):
`FlowgraphRebuilder.processFlowAtCall` (`sootandroid/.../wtg/flowgraph/FlowgraphRebuilder.java:221`)
faz binding actual→formal dirigido por `callee.getParameterCount()` mas indexa o
callsite `ie.getArg(i-1)`. Com `cgDelegation=true`, `buildCallGraphFromSparkCg`
adiciona **todo** target de `Scene.v().getCallGraph().edgesOutOf(s)` sem filtrar por
arity nem por *kind* — incluindo edges sintéticas/bridge cujo alvo tem mais
parâmetros que o callsite. Quando `num_param(target) > args(callsite)`, o `getArg`
estoura. O legado usa `hier.virtualDispatch` (preserva arity) → nunca quebra.

**Fix** (`FlowgraphRebuilder.java`, +28 linhas, em `processFlowAtCall` e `removeFlowAtCall`):
guard de arity que pula pares (callsite, callee) incompatíveis — edges sintéticas
sem fluxo real de parâmetros:
```java
int availableActuals = (ie instanceof InstanceInvokeExpr) ? ie.getArgCount() + 1 : ie.getArgCount();
if (num_param > availableActuals) { return; }
```

**Verificação** (build limpo, `lib/gator/*.jar` 2026-06-09 19:02):
- Crash AIOOBE eliminado (0 em todos os logs de teste).
- Crasher vira sucesso: `app.dumdum_14` tr 0→**360** (107 s).
- Anti-regressão: 3 que já funcionavam (`duress.keyboard_51`=102, `com.xmission...todo`=640,
  `com.destructo.botox`=56) saem **byte-idênticos** (transitions e windows).
- Timeouts remanescentes = problema separado (lentidão WTG) → escada B/C continua válida.

Rebuild do gator: `cd rvsec/rvsec-android/rvsec-gator && mvn clean install -DskipTests -pl sootandroid,client -am`
(copia as 2 JARs para `rv-android/lib/gator/` via maven-resources-plugin no install).

**Próximo:** re-rodar Stage A nos 169 com a JAR corrigida (categoria "crash" some;
sobra sucesso-rápido vs timeout, tratada pela escada B/C).

## 5c. Execução real e resultado (2026-06-10/11)

Após o diagnóstico, decidiu-se rodar **SPARK em tudo** (`cg_algorithm=spark` +
`cgDelegation=true`, com o fix do §5b). Output: `out/sweep_20260604_wtg_spark/`.

**Estágio A** (169 · 8w · 1800s · 12g · ~7h26min): 164 complete (68 com transitions),
5 `failed_no_json`, **0 crashes** (fix confirmado em produção).

**Estágio C** (5 falhas · 2w · 60g · 3600s): **5/5 recuperados**, 0 falhas.
`infomaniak.meet` fechou com 60g (não precisou dos 100g históricos). 3 dos 5 ainda
ganharam transitions (syncthingfork=317, fossify.calendar=60, nerdcalci=3).

**Estágio B** (96 timeouts · 8w · 3600s · 14g): **PARADO aos 65/96** — yield
desprezível (**1 transition novo em 65**, `com.opennotes`=5). Confirmou que dobrar
1800→3600s **não** resgata os apps presos na explosão combinatória da WTG (até apps
de 2 telas / 4 métodos re-timeout a 3600s). Não vale o wall-clock.

**Resultado final do dataset (`out/sweep_20260604_wtg_spark/`):**
- **169/169 complete, 0 falhas** — todos com reach+windows+components íntegros (≥ skip-wtg).
- **72/169 com `transitions>0`** (total ~5.959 transições).
- 97 com `transitions==0` (timeout WTG; write-first preservou o resto).

### Resume do Estágio B (se quiser retomar)
31 pendentes (registro 1800s, ainda não reprocessados a 3600s) já linkados em
`out/_stageB_resume_apks/`. Para retomar **sem refazer** os 65 já feitos:
```bash
uv run python scripts/static_analysis_sweep.py \
    --apks-dir out/_stageB_resume_apks --output ./out/sweep_20260604_wtg_spark \
    --planilha /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/PLANILHA_dexlib2.csv \
    --cg-algorithm spark --cg-delegation true \
    --retry-statuses complete --timeout 3600 --workers 8 --jvm-memory 14g
```
(Regenerar a lista de pendentes filtrando `timeout_used_seconds<3500` no `_progress/`.)

### Pendência: fix do SPARK não commitado
`FlowgraphRebuilder.java` (+28 linhas, guard de arity) está **só no working tree** do
repo `rvsec` e **já compilado** em `rv-android/lib/gator/*.jar` (build 2026-06-09 19:02).
Quem rebuildar o gator sem commitar perde o fix → crashes voltam no caminho
`cgDelegation=true`. Decidir commit depois.

## 6. Notas

- **Não** sobrescrever `out/sweep_20260604/` nem o dataset `APKS_FINAL_JCA_DEXLIB_20260604/`.
- Monitorar: `tail -f out/sweep_20260604_wtg/_logs/*.log` e `progress.csv`.
- Parar com segurança: `kill -INT $(cat out/sweep_20260604_wtg/sweep.pid)`.

# Logcats sem RVSEC-COV — execuções sem dado útil de RV

Data da análise: 2026-07-12 (validação local pós-campanha, cópia em `RV_ANDROID_NOVO_DATASET/RESULTS/`).
Lista completa das 235 identidades: `nocov_235.csv` (neste diretório).

## Balanço final de dados da campanha

| | Tasks | % das previstas |
|---|---:|---:|
| Previstas (219 APKs × 11 tools × 3 reps × 3 timeouts) | 21.681 | 100,00% |
| Executadas com logcat não-vazio (cross-check remoto×local, diff 0) | 21.681 | 100,00% |
| **Com dado de RV (≥1 linha RVSEC-COV)** | **21.446** | **98,92%** |
| **Sem dado de RV (perda real da campanha)** | **235** | **1,08%** |

A perda real do experimento são estas **235 execuções** — nenhuma outra. Em particular, as tasks
que terminaram em estado ERROR no `tasks.json` (residual monkey, ~612) **têm** logcat com RVSEC-COV
e eventos MOP utilizáveis (estado e dado são desacoplados; a consolidação reparsa todo logcat), e
por isso **não** contam como perda de dado. Das 235: 189 são irrecuperáveis por re-run
(determinísticas, Classe 1 abaixo) e 46 seriam recuperáveis (transitórias, Classe 2).

## Contexto e critério

A campanha fechou **21.681/21.681** logcats não-vazios (>0 byte), cross-check remoto×local com diff 0
nas 4 VMs. Porém o critério ">0 byte" superconta: um logcat pode conter apenas os cabeçalhos de stream
do logcat (`--------- beginning of main/system/kernel`) sem nenhuma linha de dado. O sinal correto de
execução útil é a presença de linhas `RVSEC-COV` — a instrumentação de coverage dispara já na
inicialização do app, então **0 linhas RVSEC-COV = o app nunca subiu naquela execução**.

Contagem real (varredura `grep -L 'RVSEC-COV'` sobre os 21.681):

- **21.446 logcats com RVSEC-COV** (98,92%) — dado de execução real.
- **235 logcats sem RVSEC-COV** (1,08%) — todos com 88–117 bytes (só cabeçalhos), zero dado de RV.

Estes 235 são **disjuntos** do residual monkey (`RESIDUAL_MONKEY.md`): lá o app roda e o logcat é rico
até o OOM-kill mid-run; aqui o app **nunca inicia**. São os dois modos de perda do experimento.

## Composição: duas classes de causa

| Classe | N | Tools | Natureza |
|---|---:|---|---|
| `no_launchable_activity` | 189 | qtesting | **Determinística** (tool×APK): 21 APKs × 9/9 execuções |
| `transient_infra` | 46 | droidmate 19, ares 17, droidbot 6, humanoid 2, qtesting 1 | Transitória: emulador/adb indisponível na janela da task |

### Classe 1 — qtesting × APK sem `launchable-activity` (189; determinística)

**Causa-raiz (fechada com evidência):** o qtesting resolve a main activity do APK via parsing do
manifest (`aapt dump badging`). **21 dos 219 APKs do dataset não expõem `launchable-activity` no
badging** porque o intent-filter `MAIN`/`LAUNCHER` está declarado apenas em elementos
**`activity-alias`** (padrão usado p.ex. pelos apps Fossify para ícones tematizados — verificado no
`AndroidManifest.xml` de `org.fossify.notes_13.apk` via `aapt dump xmltree`). Com `activity_info`
vazio, o qtesting monta o launch intent com o placeholder literal `noactivityname`:

```
Starting: Intent { cmp=org.fossify.notes.debug/noactivityname }
Error type 3
Error: Activity class {org.fossify.notes.debug/noactivityname} does not exist.
```

e repete isso em loop ("get stuck in an error state that cannot launch main target activity") até o
timeout, em todas as execuções. O `.trace` do qtesting registra o loop completo; o logcat fica com 88 B.

**Verificação 1:1:** o conjunto dos 21 APKs em que o qtesting falha 9/9 (3 reps × 3 timeouts) é
**exatamente igual** ao conjunto dos 21 APKs sem `launchable-activity` no `aapt dump badging` dos 219
instrumentados (`diff` vazio). Todos os 21 traces amostrados contêm `noactivityname`.

**Contraprova:** os mesmos 21 APKs têm logcats saudáveis (90 KB–600 KB, com RVSEC-COV) sob as outras
10 tools na mesma VM/janela — as demais tools lançam o app por outros mecanismos (monkey `-p`,
resolução própria do launcher) e não dependem do `launchable-activity` do badging.

**Os 21 APKs (e a VM que os executou):**

| APK | VM |
|---|---|
| app.michaelwuensch.bitbanana_79.apk | m1 |
| com.apps.adrcotfas.goodtime_348.apk | m1 |
| com.celzero.bravedns_619.apk | m1 |
| com.daniebeler.pfpixelix_40.apk | m1 |
| com.dede.android_eggs_76.apk | m1 |
| com.gaurav.avnc_51.apk | m1 |
| com.sakethh.linkora_50.apk | m2 |
| com.tk.quicksearch_65.apk | m2 |
| dev.leonlatsch.photok_62.apk | m3 |
| inc.flide.vi8_170500.apk | m3 |
| org.fossify.calendar_20.apk | m4 |
| org.fossify.keyboard_14.apk | m4 |
| org.fossify.math_10.apk | m4 |
| org.fossify.messages_20.apk | m4 |
| org.fossify.musicplayer_14.apk | m4 |
| org.fossify.notes_13.apk | m4 |
| org.fossify.paint_7.apk | m4 |
| org.fossify.voicerecorder_18.apk | m4 |
| org.isoron.uhabits_20301.apk | m4 |
| org.wikipedia_50595.apk | m4 |
| ua.com.radiokot.lnaddr2invoice_8.apk | m4 |

(11 são da família `org.fossify.*`. Distribuição por VM: m4=11, m1=6, m2=2, m3=2 — os APKs são
particionados por VM, então cada APK tem suas 9 execuções na mesma VM; a concentração em m4 reflete o
particionamento do dataset, não um problema da VM.)

**Consequência para a análise:** o qtesting tem **zero dado útil para 21/219 APKs (9,6% do dataset)**.
Re-run não recupera nada — a falha é determinística (9/9, inclusive em 60s). É limitação do qtesting
(parser de manifest), não do harness nem da instrumentação dexlib2. Threat to validity a documentar
no artigo: qualquer métrica per-tool do qtesting cobre efetivamente 198 APKs.

### Classe 2 — infraestrutura transitória (46)

Falhas avulsas na janela da task: o emulador/adb não estava disponível ou responsivo quando a tool
iniciou, e o app nunca chegou a ser lançado. Evidências amostradas nos `.trace`:

- **ares** (17): Appium aborta com `adbExec ... timed out after 30000ms` (device não responde) e
  desiste ("Too Many Times tried ... iteration: 0").
- **droidbot** (6) e **humanoid** (2): `adb: device 'emulator-5554' not found` em loop, ou trace
  truncado logo na inicialização (~343 B) — emulador morto/reiniciando na janela.
- **droidmate** (19): a exploração roda mas com o alvo ausente (estratégia `handleTargetAbsence`
  dominante; UIAutomator daemon inacessível) — o app nunca sobe.
- **qtesting** (1, `com.google.android.stardroid_1678.apk`, único caso 1/9 da tool): trace termina em
  `- waiting for device -` — emulador indisponível. Não é o bug de manifest da Classe 1.

Perfil estatístico consistente com transitoriedade: 40 dos 46 são casos isolados 1/9 por (APK,tool);
únicos mini-clusters: ares×`info.metadude.android.hope.schedule_110` (3/9) e
droidmate×`com.sakethh.linkora_50` (3/9). Distribuição por VM equilibrada (m2=17, m3=16, m4=7, m1=6)
e por timeout flat — assinatura de janela ruim de infraestrutura, não de app ou duração.

Estes 46 **seriam recuperáveis por re-run** (ao contrário da Classe 1), mas representam 0,21% das
21.681 execuções, espalhados por 40 (APK,tool) distintos.

## Plano de recuperação por re-run (Classe 2)

Decisão (2026-07-12): **vamos tentar re-rodar as 46 transitórias nas VMs** para recuperar dado. As
189 determinísticas (Classe 1) ficam de fora — re-run reproduz o `Error type 3`, é teto estrutural.

**Teto de recuperação:** o piso de dado útil subiria de **21.446 (98,92%)** para no máximo
**21.492 (99,08%)** — os 189 são irrecuperáveis por construção.

**Alvos, agrupados por célula `(apk, tool, timeout)` × 3 reps** (o critério real de transitoriedade —
se outra rep do mesmo combo tem dado, a falha é flake de janela, não do combo):

| Confiança | Células | Execuções | Descrição |
|---|---:|---:|---|
| **Alta** (aposta segura) | 36 × 1/3 + 2 × 2/3 = 38 | 40 | ≥1 rep do mesmo combo já rodou com dado → flake de infra puro |
| **A inspecionar antes** | 2 × 3/3 | 6 | trio inteiro sem dado → isolar infra vs. interação apk×tool sistemática |

As 2 células a 3/3 (0 de 3 reps com dado) a validar antes de re-rodar:

- `info.metadude.android.hope.schedule_110.apk` × `ares` × 300s
- `com.sakethh.linkora_50.apk` × `droidmate` × 60s

Se qualquer delas voltar a falhar 3/3 no re-run, reclassificar como determinística (interação
apk×tool), não como perda transitória.

**Distribuição das 46 por tool / VM / timeout** (para dimensionar o re-run):

| tool | N | | VM | N | | timeout | N |
|---|---:|---|---|---:|---|---|---:|
| droidmate | 19 | | m2 | 17 | | 60s | 23 |
| ares | 17 | | m3 | 16 | | 300s | 16 |
| droidbot (3 var.) | 7 | | m4 | 7 | | 180s | 7 |
| humanoid | 2 | | m1 | 6 | | | |
| qtesting | 1 | | | | | | |

Lista exata das 46 identidades `(apk, tool, rep, timeout, vm)`: filtrar `nocov_235.csv` por
`reason == transient_infra`.

```bash
awk -F, '$NF=="transient_infra"' experimento-20260706/docs/residual/nocov_235.csv
```

**Ainda não executado** — VMs paradas; re-run a agendar (VMs gcloud têm IP efêmero, reconferir com
`gcloud compute instances list`). A recuperação será medida pelo mesmo critério: `grep 'RVSEC-COV'`
no logcat re-gerado da identidade.

## Distribuição agregada dos 235

- Por tool: qtesting 190 (189 + 1 transitório), droidmate 19, ares 17, droidbot 6 (dfs_naive 3,
  dfs_greedy 2, bfs_naive 1), humanoid 2.
- Por VM: m4=106, m1=60, m2=35, m3=34 (dominada pelo particionamento dos 21 APKs da Classe 1).
- Por timeout: 60s=86, 180s=70, 300s=79 — flat, consistente com falha de launch (independe da duração).

## Efeito na consolidação

A consolidação offline reparsa todo logcat; estes 235 entram como linhas de **coverage zero e zero
eventos MOP** no `summary_regen.csv` (não são excluídos automaticamente). Como tratá-los na análise
(zero legítimo vs. exclusão do denominador per-tool) é decisão de análise do artigo — os dados para
qualquer dos dois tratamentos estão em `nocov_235.csv`.

**Nota (achado da consolidação 2026-07-12):** o `summary_regen.csv` tem **334** linhas totalmente
zero, não 235. As **99** adicionais **lançaram** (têm RVSEC-COV) mas fecharam com coverage/MOP zero —
98 do `com.google.android.stardroid` (defeito determinístico do `PackageFilter`, que exclui
`Lcom/google/` e engole o namespace próprio do app) + 1 execução avulsa transitória do
`org.wikipedia`. Fenômeno **distinto** destes 235 (aqui o app nunca lança; lá lança e não é
instrumentado). Detalhe e causa-raiz: `ZEROCOV_STARDROID.md`.

## Reprodução

```bash
# Lista dos sem-COV (na cópia local):
cd /home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET
find RESULTS/m*/results/exp_* -name '*.logcat' -size +0c \
  | xargs -P12 -d '\n' grep -L 'RVSEC-COV'

# APKs sem launchable-activity (usa aapt do build-tools):
for apk in APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/*.apk; do
  aapt dump badging "$apk" | grep -q launchable-activity || basename "$apk"
done
```

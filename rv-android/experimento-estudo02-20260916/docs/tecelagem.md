# Sweep de tecelagem sobre o corpus inteiro — veredito

**Data:** 16/09/2026
**Escopo:** os 163 APKs de `APKS_INSTRUMENTED_jca_android_dexlib2`, reinstrumentados em 15–16/09
com a imagem `phtcosta/rvandroid:0.9.4` (rvsec `fc51ab64`, gh114 dentro).
**Portão:** plano §7.2. O preflight de campanha exige este arquivo e o `tecelagem_sweep.csv`.

## Como foi medido

```
uv run python scripts/gh114_weave_sweep.py \
    /home/pedro/desenvolvimento/RV_ANDROID_DATASET_FINAL/APKS_INSTRUMENTED_jca_android_dexlib2 \
    <rvsec-dataset>/jca_android/instrument_results/instrument_00/instrument_00/monitors/MultiSpec_1MonitorAspect.json \
    experimento-estudo02-20260916/docs/tecelagem_sweep.csv \
    --sites experimento-estudo02-20260916/docs/tecelagem_sweep_sites.csv --jobs 6
```

O descritor é o `MultiSpec_1MonitorAspect.json` que o gerador escreveu durante a
reinstrumentação. Os oito lotes escreveram o **mesmo** descritor (md5 `541b6a46…` nos oito), então
qualquer um serve e o `instrument_00` foi o escolhido.

`dexdump` de `build-tools/37.0.0`, `android.jar` de `platforms/android-37.0` — a mesma escolha
numérica do sweep da gh114 (`newest_under`, que ordena por número e não por texto).

## Os quatro números (plano §7.2)

| medida | aceite | medido | veredito |
|---|---|---|---|
| (a) pares de aridade disparados | 0 | **0** (`arity_pairs`, `arity_call_sites` e `arity_inline_hooks` zerados em 163/163) | PASSA |
| (b) chamadas a subtipo do framework sem wrapper | 0 | **0** de 163 APKs | PASSA |
| (c) ganchos em destino de desvio | 0 | **0** de **7 951** ganchos `before` | PASSA |
| (d) `KeyStore.getEntry`/`setEntry` tecidos onde existem | todos | **23 de 23**, em 13 APKs | PASSA |

Nenhum APK reportou `error`. `wrappers = 141` em todos os 163 — o mesmo 141 que o
`sweep_after.csv` da gh114 mediu depois dos consertos (eram 135 antes; os seis novos são os alvos
herdados que o A2 resolve).

Os 13 APKs com `getEntry`/`setEntry`, todos tecidos: `app.pachli_50` (3), `com.afkanerd.deku_83`
(4), `com.ivanovsky.passnotes_11700` (3), `org.fedorahosted.freeotp_48` (3),
`com.craxiom.networksurvey_114` (2), e um cada em `ch.rmy.android.http_shortcuts_1104060001`,
`com.arslan.shizuwall_40`, `com.darkrockstudios.app.securecamera_31`, `com.defname.localshare_14`,
`com.etesync.syncadapter_20700`, `com.leekleak.trafficlight_38`, `eu.faircode.email_2322` e
`me.diamondforge.tokn_19`.

## Os dois portões que vêm do `rvsec-dataset`

Lidos dos `instrument_results/instrument_*/…/instrumented_apks/instrument_*.json`:

- **`instrument_errors` vazio para o corpus.** Houve 6 falhas na reinstrumentação
  (`app.podiumpodcasts.podium_1000008`, `com.ismartcoding.plain_598`, `info.dvkr.screenstream_44000`,
  `org.fossify.phone_22`, `org.owntracks.android_420509001`, `org.tasks_150702`) e **nenhuma delas
  está no corpus** — são parte dos 170 tentados, não dos 163 do N₄.
- **`wrappersSubstituted > 0` em todo APK.** 163/163 com `success: true`; substituições de 2 a
  1 256, mediana 74. `wrapperTargetsUnresolved = 0` em todos.

## Resíduo

Nenhum. Não há APK a listar.

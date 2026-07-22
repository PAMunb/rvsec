# `dataset.csv` — data dictionary (gov.br experiment dataset)

Manifest of the dataset **actually executed** in the gov.br runtime-verification
experiment (RV4Android / JCA misuse detection driven by APE). One row per app,
**33 apps** — the set that ran to `COMPLETED` (see `filters/gov_final_33.txt`).

Holds **app identity + APK build/SDK metadata only**. Columns describing the JCA
surface, the collection provenance, and the instrumentation-pipeline decision were
**dropped on purpose** (see "Dropped columns" below): they describe *how* the
dataset was assembled/triaged, not the apps themselves.

## Origin and how it was generated
- Source: `RV_ANDROID_DATASET_GOV/dataset_gov_play.csv` (static-triage +
  provenance sheet; 37 candidates, 34 columns).
- Collection: Google Play + `adb pull` on the `RVSecPlay` AVD
  (API 30 / google_apis_playstore / x86_64). One APK per app.
- Manifest fields via `aapt dump badging`; framework detected from `.so` libs +
  dex strings.
- This `dataset.csv` = source **filtered by `gov_final_33.txt`** and **projected**
  onto the 15 columns below (script: `scratchpad/filter_dataset.py`).

**All 33 apps came from the official Google Play channel** — that is why the
provenance columns (`in_playstore`, `provenance`, `source_stamp`) were dropped:
they were constant / irrelevant for characterizing the apps.

## Columns (15)

### Identity / manifest
| Column | Type | Meaning |
|--------|------|---------|
| `apk` | string | Actual APK file name (join key with results / logcats). |
| `manifest_package` | string | `package` from the `AndroidManifest` (`aapt`). |
| `playstore_url` | string | Google Play listing link, derived from the package: `https://play.google.com/store/apps/details?id=<manifest_package>`. Valid because the APKs were collected via `adb pull` from Play itself, so `manifest_package` **is** the listing `id=`. |
| `version_code` | int | `versionCode`. |
| `version_name` | string | `versionName`. **Empty for 1 app** (Sinesp Cidadão does not declare it). |
| `main_activity` | string | `launchable-activity` (used for launch). **Empty for 4 apps** (calculadoracidadao, receita.eprocesso, receita.mei, foraareabrasileira — no launchable-activity resolvable via `aapt`; launch used a package fallback). |

### Build / SDK
| Column | Type | Meaning |
|--------|------|---------|
| `apk_size_mb` | float | Final file size (MB). Range: **5.4–107.5**, mean ~39.9. |
| `dex_count` | int | Number of `classes*.dex` in `base.apk`. Range: **1–9**. |
| `min_sdk` | int | `minSdkVersion`. Observed range: 19–29. |
| `target_sdk` | int | `targetSdkVersion`. Range: 33–36. |
| `compile_sdk` | int | `compileSdkVersion`. Range: 33–36. |
| `native_code_abis` | string | ABIs present **in the collected artifact** (`\|`-joined), or `none`. ⚠️ Reflects the splits pulled onto the **x86_64** AVD — **not** the set of ABIs the app publishes on the store. 30 apps `none`; 3 carry `arm64-v8a\|armeabi-v7a\|x86\|x86_64` (the `single_apk` ones: SouGov, Sinesp, MedSUSAPP). |

### Packaging
| Column | Type | Meaning |
|--------|------|---------|
| `n_splits` | int | Number of APKs delivered by Play (1 = single-APK). Range: 1–6. |
| `apk_type` | enum | How the APK was delivered/prepared. `single_apk` (5 apps): Play delivered one APK (`n_splits=1`), pulled as-is — original Play signature preserved bit-for-bit. `remerged_bundle` (28 apps): Play delivered an App Bundle (multiple split APKs), remerged via `APKEditor m` + `zipalign` + re-signed with `debug.keystore` to be installable/instrumentable — same content, our debug signature. |
| `framework` | enum | Detected UI/app stack: `react-native` (11), `flutter` (9), `native` (6), `cordova` (5), `capacitor` (2). |

## Dropped columns (and why)
Present in the source `dataset_gov_play.csv`, **excluded** from this `dataset.csv`:

- **JCA surface** (the inclusion "hammer" — static triage, does not characterize
  the app): `jca_cipher`, `jca_secretkeyspec`, `jca_ivparameterspec`,
  `jca_pbekeyspec`, `jca_gcm`, `jca_mac`, `jca_messagedigest`, `jca_securerandom`,
  `jca_keystore`, `jca_keygenparameterspec`, `jca_total`, `jca_callsites_any`.
- **Provenance** (collection channel — constant: all Play Store): `in_playstore`,
  `source_stamp`, `provenance`.
- **Pipeline decision** (triage heuristic, not an app fact): `anti_tamper`,
  `instrument_verdict`, `dest_file`, `obs`.
- **`max_sdk`**: empty for all 33 apps (none declares `maxSdkVersion`), so dropped
  as noise.

## Scope: what got in and what was left out
Of the **37 collected candidates**, **4 were excluded** from the experiment (they
are not in this dataset):

| Excluded APK | Reason |
|--------------|--------|
| `br.gov.dataprev.carteiradigital_8.9.10.apk` | **PAIRIP** anti-tamper (`libpairipcore.so`) — breaks a re-instrumented / re-signed APK. |
| `br.gov.serpro.cnhe_7.2.1.apk` | **PAIRIP** anti-tamper. |
| `com.goodbarber.exercitobr_2.4.apk` | **PAIRIP** anti-tamper. |
| `br.gov.economia.receita.rfb_4.10.0.apk` | **65536 method-ref ceiling** per DEX (uint16): instrumentation adds a `Coverage.log` ref to an already-saturated dex (`classes3.dex` at exactly 65536 methods) → truncated output. |

Forensic detail in `docs/20260719_relatorio_gov.md` (exclusions section) and in
`RV_ANDROID_DATASET_GOV/REGISTRO.md` (§9).

## Caveats (P5 — do not claim beyond the evidence)
- `native_code_abis` is from the artifact collected on the x86_64 AVD, **not**
  from the store publication.
- `framework` does not imply absence of a JCA surface in Java: Flutter /
  React-Native apps frequently bundle Java libs (networking / security) that call
  JCA — which is why they still triggered MOP violations in the experiment.
  App-vs-library attribution is undecidable under obfuscation and irrelevant to
  the monitor (it fires on any JCA call in the executed Java bytecode).
- `apk_type=remerged_bundle` means re-signing with `debug.keystore` (installable
  on the AVD), **not** the original store artifact bit-for-bit.

# Device validation — tasks 10.4 and 10.5

Tasks 10.4 and 10.5 are closed from runs that already happened, not from the four-APK Monkey
pilot of `experimento-gh104/PRONTIDAO.md` P6, which was not run (researcher decision,
2026-09-14). Every number below was measured on 2026-09-14 over recorded artefacts; no emulator,
monitor generation or weaving was started for this file.

## Sources

| label | what | where |
|---|---|---|
| **comp162** | baseline, frozen `jca`, pre-envelope | `experimento-comp162/results/comp162_0*/comp162_0*/errors.csv` (8 files, 19 664 rows) |
| **gh104** | joint campaign, 2026-09-06/07: 164 APKs of `RV_ANDROID_DATASET_FINAL/APKS_INSTRUMENTED_jca_android_dexlib2` × `ape`, `aperv:mop_off_llm_off`, `aperv:mop_on_llm_off` × 3 reps × 300 s | `data/results/gh104_0*/gh104_0*/` (8 containers); message gates `experimento-gh104/consolidado/gh104_gates.json`; verdict `experimento-gh104/VEREDICTO.md` |
| **estudo02** | 2026-09-08/14: 163 APKs of the same corpus × 11 tool configurations (Monkey among them) × 3 reps × 60/180/300 s | `data/results/estudo02_consolidado/errors.csv` (139 657 rows); `data/results/estudo02_regen/*/summary.csv` (16 137 identities); `experimento-estudo02/README.md` |
| **weave** | the instrumentation that produced the campaign corpus | `rvsec-dataset/jca_android/instrument_results/instrument_0*/instrument_0*/instrumented_apks/instrument_results.json`; `rvsec-dataset/jca_android/manifests/instrumented.sha256` |

`experimento-smk111/` is not a source: other APKs, none of the three 10.5 lines, and a corpus
woven with the 48-`.mop` set before `RandomStringPassword.mop` left (`wrappersGenerated=137`).

Scripts (session scratchpad, not versioned): a CSV scanner that parses every message against
the envelope `^v=1 code=(\S+) ev=(\S*) obj=(\S*) val='(.*?)' exp='(.*?)' msg='(.*)'$` and
aggregates by `(spec, code, val)`; a second pass for sha256, `weaveCounts`, `summary.csv`
columns and per-site records. Two independent executions of the scanner produced byte-identical
output over all three corpora.

## Declared deviations from the pilot shape

- **(a) Weaving.** The corpus was woven by the dataset funnel inside Docker, not with `lib/` jars
  rebuilt on the host.
- **(b) Static analysis.** It did not run on device. Both campaigns ran with
  `run_static_analysis=false` over the funnel's `.apk.json`, produced over the 47-`.mop`
  `jca_android` set. The directory task 10.0 resolves is therefore **not exercised on device**;
  10.0's own test (`test_static_analysis_config_uses_selected_set`) remains its evidence.
- **(c) Monkey.** estudo02 runs Monkey with `ignore_crashes`/`ignore_timeouts`.
- **(d) Parser counters.** The `ParserDiagnostics` counters (INV-ANA-62) live in memory on
  `LogcatRepository.parser_diagnostics`; no writer persists them to a result artefact. Only the
  `unmatched_out_of_scope`/`unmatched_in_scope` columns of `summary.csv` are observable. **This is
  a declared gap, not a pass.**

## 10.4 — the message, the weave, the pilot APKs

### `unknown` and `but found .`

| corpus | rows | `unknown` | `but found .` | rows not matching the envelope | empty `ev` |
|---|---:|---:|---:|---:|---:|
| comp162 (baseline) | 19 664 | **15 714** (79.91 %) | **98** | 19 664 | — |
| gh104 | 21 720 | **0** | **0** | 0 | 0 |
| estudo02 | 139 657 | **0** | **0** | 0 | 0 |

gh104's message gates agree: `gh104_gates.json` = 9 PASS / 0 FAIL / 1 SKIP, `errors.csv` and
logcat both 21 720 violation lines, 0 codes outside `jca_android/codes.csv` (253 codes). The SKIP
is G10, which reads `instrument_results.json` from the results tree; the campaign skipped weaving,
and the weave counters are read from the dataset below instead.

### Envelope fields

`ev` is never empty. `val` and `exp`, per kind, in the two campaigns:

| kind | gh104 rows | empty `val` | empty `exp` | estudo02 rows | empty `val` | empty `exp` |
|---|---:|---:|---:|---:|---:|---:|
| ALG | 3 129 | 0 | 0 | 18 239 | 0 | 0 |
| KEYSIZE | 110 | 0 | 0 | 970 | 0 | 0 |
| PROTO | 21 | 0 | 0 | 96 | 0 | 0 |
| CONSTR | 39 | 0 | 0 | 242 | 17 | 0 |
| NOBS | 9 222 | 2 627 | 0 | 62 480 | 20 014 | 0 |
| FORB | 9 | 9 | 0 | 6 | 6 | 0 |
| ORDER | 9 190 | 9 190 | 9 190 | 57 624 | 57 624 | 57 624 |

Every empty `val` or `exp` is written as the empty literal by the `.mop` itself — the value is
not a scalar the event holds:

- **ORDER** — `@fail` of every specification writes `val='' exp=''` (e.g. `KeyStoreSpec.mop:128`).
- **FORB** — `SSLCONTEXT-FORB-00`, `SSLContextSpec.mop:133`: the value is a forbidden overload, named in `exp`.
- **NOBS/CONSTR over a byte array or a key object**, all 100 % empty in both corpora:
  - `CIPHER-NOBS-00` (`CipherSpec.mop:232`) and `CIPHER-CONSTR-00` (`:228`, estudo02 only);
  - `GCMPARAMETERSPEC-NOBS-00/01` (`GCMParameterSpecSpec.mop:79,133`);
  - `IVPARAMETERSPEC-NOBS-00` (`IvParameterSpec.mop:75`);
  - `PBEKEYSPEC-NOBS-01` (`PBEKeySpecSpec.mop:156`);
  - `SECRETKEYSPEC-NOBS-00/01` (`SecretKeySpecSpec.mop:118,184`);
  - `SECURERANDOM-NOBS-00/01` (`SecureRandomSpec.mop:237,106`);
  - `X509ENCODEDKEYSPEC-NOBS-00` (`X509EncodedKeySpecSpec.mop:50`).

No code outside those families carries an empty `val` or `exp`.

### Weave counters

- `instrument_results.json` holds 170 results: 164 `success=true`, which are exactly the campaign corpus. The corpus directory holds 163 of them today, having lost `com.google.android.stardroid_1678`, which the gh104 verdict excluded (A-4). The other 6 failed with `phase=uncaught` and none of them is in the corpus (`info.dvkr.screenstream_44000` among them).
- All 164 successful results carry the same 20 `weaveCounts` fields, with **`wrappersGenerated=135`** and **`advicesExcludedByArity=10`** in every one.

| pilot APK | `advices` | `wrappersGenerated` | `advicesExcludedByArity` | `matchesApplied` | sha256 (corpus = dataset = `instrumented.sha256`) |
|---|---:|---:|---:|---:|---|
| `com.owncloud.android_48000100` | 191 | 135 | 10 | 59 | `7db83436307b…5132a6f69d0f` |
| `eu.opencloud.android_9` | 191 | 135 | 10 | 57 | `9556522fd6f2…4753b2bfcff7` |
| `de.luhmer.owncloudnewsreader_196` | 191 | 135 | 10 | 20 | `2ff2a02138a6…326c21d3f265` |
| `com.etesync.syncadapter_20700` | 191 | 135 | 10 | 78 | `ab4e1e9490e2…a06053a840cb` |

For each of the four, the sha256 of the APK the campaigns ran equals the dataset's
`instrumented_apks/` copy and the line in `manifests/instrumented.sha256`.

### The four pilot APKs under Monkey (estudo02)

Every Monkey identity of the four is `measured=true`. The table gives `errors.csv` rows per identity; each value equals that identity's `mop_errors_total` in `summary.csv`.

| APK | 60 s (rep 1/2/3) | 180 s | 300 s |
|---|---|---|---|
| `com.owncloud.android_48000100` | 7 / 0 / 7 | 7 / 7 / 7 | 14 / 7 / 14 |
| `eu.opencloud.android_9` | 0 / 7 / 0 | 7 / 7 / 7 | 7 / 7 / 7 |
| `de.luhmer.owncloudnewsreader_196` | 4 / 4 / 4 | 4 / 4 / 4 | 4 / 4 / 4 |
| `com.etesync.syncadapter_20700` | 0 / 26 / 0 | 0 / 0 / 0 | 26 / 0 / 26 |

At 180 s the codes are the TrustManagerFactory and SSLContext families:
- owncloud and opencloud: `TRUSTMANAGERFACTORY-ORDER-00`, `TRUSTMANAGERFACTORY-NOBS-00`, `SSLCONTEXT-NOBS-00/01/02`;
- owncloudnewsreader: `TRUSTMANAGERFACTORY-ORDER-00`, `-NOBS-00`.

`com.etesync` reaches no violation at 180 s in any of the three repetitions, as in gh101 task 8.1. At 60 s and 300 s it does reach one (26 rows, the `CertUtils.kt:22` site), so its silence at 180 s is exploration, not a dead monitor.

### Parser counters

- **Observable:** `unmatched_out_of_scope` and `unmatched_in_scope` are populated in 1 470/1 470 gh104 identities and 16 137/16 137 estudo02 identities.
- **Not observable:** the `ParserDiagnostics` counters. See deviation (d).

### 10.4 verdict

Passes on `unknown`, `but found .`, envelope, weave counters and pilot identities, with
deviations (a)–(c) declared. The parser-counter criterion is a **declared gap** (d).

## 10.5 — the three lines under D-15

The criterion is whether a record accusing the value exists, and whether the call site was reached. Counts do not decide it, because APE and Monkey are stochastic.

- **Reach is direct** when another record of the same specification exists at the same source line.
- **Reach is indirect** when only the enclosing application method was covered (`RVSEC-COV`).

### `TrustManagerFactorySpec` `X509` — not reported; reach direct at all three sites

- **comp162:** `expecting one of … but found X509` at exactly 3 sites in 3 APKs (61 rows):
  - `com.etesync.syncadapter_20700` `CertUtils.kt:22`;
  - `de.luhmer.owncloudnewsreader_196` `MemorizingTrustManager.java:282`;
  - `org.openhab.habdroid_589` `MemorizingTrustManager.java:310`.
- **gh104 and estudo02:** zero `TRUSTMANAGERFACTORY-ALG` records. At all three sites the monitor emits `TRUSTMANAGERFACTORY-NOBS-00` with `val='X509'`, plus `TRUSTMANAGERFACTORY-ORDER-00`:
  - gh104: 78 NOBS rows, 3 APKs;
  - estudo02: 414 rows, 3 APKs;
  - under Monkey: 3, 9 and 17 rows at the three sites.
- **Reading:** the event carrying `X509` fired and the value check did not accuse, which is the normalisation rule of task 2.5 resolving `X509` to `PKIX`.

### `SSLContextSpec` `TLS` — not reported; reach direct

- **comp162:** `but found TLS` at 68 sites in 62 APKs (1 446 rows).
- **gh104 and estudo02:** zero `SSLCONTEXT-PROTO-00` records with `val='TLS'`. The same specification emits `SSLCONTEXT-NOBS-00/01` with `val='TLS'` at the `init` event in 62 APKs (gh104, 1 444 rows each) and 59 APKs (estudo02, 9 135 rows).
- **Reading:** the `platform-value` entry of task 11.4 admits it.

### `KeyStoreSpec` `AndroidKeyStore` — not reported; reach direct at 1 of 14 sites, indirect at 3 more (caveat)

**comp162:** `but found AndroidKeyStore` at 14 sites in 13 APKs (265 rows):
- 9 sites in library classes: Tink `AndroidKeystoreAesGcm.java:58/59` and `AndroidKeystore.java:137`;
- 5 sites in application classes:
  - `com.owncloud.android_48000100` and `eu.opencloud.android_9`, both `BiometricViewModel.kt:74`;
  - `github.paroj.dsub2000_217` `KeyStoreUtil.java:74`;
  - `com.darkrockstudios.app.securecamera_31` `SecurityLevel.kt:67`;
  - `org.css_apps_m3.password_manager_16` `UnlockScreen.kt:131`.

**gh104 and estudo02:** zero `KEYSTORE-KSTYPE-00` records.

**Direct reach at one site.**
- In `KeyStoreSpec.mop:114-120` the type accusation is emitted **inside `gk1`'s body**, for any store whose `getType()` is not admitted, independently of the automaton's state.
- gh104 records `KEYSTORE-ORDER-00` with `ev=gk1` at `eu.opencloud.android_9` `BiometricViewModel.kt:74` (3 rows, `aperv:mop_on_llm_off`). That is the very site where comp162 accused `AndroidKeyStore` for the same APK.
- So `gk1` fired there with that store and its body emitted no `KSTYPE`: the `platform-value` entry admitted the type.
- The `ORDER` accusation at the same event is a separate verdict on the call sequence and is not part of this criterion.

**Indirect reach only** (the enclosing application method covered, no `KeyStoreSpec` record):

| site | gh104 identities | estudo02 identities | of which Monkey |
|---|---:|---:|---:|
| `dsub2000` `KeyStoreUtil.getKey` | 9 | 99 | 9 |
| `securecamera` `SecurityLevelDetector.isKeyInHardware` | 9 | 98 | 9 |
| `password_manager` `UnlockScreenKt.getOrCreateBiometricSecretKey` | 1 | 8 | 0 |

- `com.owncloud`'s `initCipher` was covered in neither campaign.
- The 9 library sites are outside the coverage scope, so their reach is unmeasured.

**Caveat, recorded rather than resolved.** Across the whole `KeyStoreSpec`, messages fall from 22 APKs (comp162, most of them `unknown`) to 1 (gh104) and 0 (estudo02).
- On the four sites with only indirect reach, silence is consistent with the repair and equally consistent with the store never reaching `gk1`. The recorded artefacts cannot separate the two: `weaveCounts` has no per-specification breakdown, and `RVSEC-COV` records application methods, not monitored calls.
- The `opencloud` site is the one observation where the monitor demonstrably saw an `AndroidKeyStore` store at `gk1` and did not accuse it.

### The bilateral half

These are the accusations D-15 gives back relative to the archived api30 set, counted as distinct APKs with an accusing record. The comp162 column counts only messages that were legible; its 15 714 `unknown` rows can hide more, so each value there is a **lower bound**.

| accusation | comp162 (legible only) | gh104 | estudo02 |
|---|---:|---:|---:|
| `MessageDigestSpec` `MD5` | ≥ 22 | 22 | 21 |
| `MessageDigestSpec` `SHA-1` | ≥ 16 | 17 | 16 |
| `MessageDigestSpec` `SHA1` | ≥ 3 | 4 | 4 |
| `SSLContextSpec` `SSL` (`SSLCONTEXT-PROTO-00`) | ≥ 1 | 1 | 1 (`nextcloudcookbook` `OkHttpClientProvider.kt:74`, Monkey included) |
| `CipherSpec` `AES/ECB/NoPadding` (`CIPHER-ALG-01`) | none legible | 8 | 8 |
| `CipherSpec` `RSA/ECB/OAEPWithSHA1AndMGF1Padding` (still accused, task 11.5) | ≥ 1 | 1 | 1 |

- **`NOBS` family:** in gh104 it spans 21 codes in 16 specifications (9 222 rows); in estudo02, 62 480 rows.
- **`SHA256WITHRSA`:** appears only as `SIGNATURE-NOBS-02`, never as an ALG accusation. That matches the case-insensitive comparison.
- **`MD5`, `SHA-1` and `SSL`:** the frozen `jca` already accused them. "Given back" is relative to the archived api30 set, not to `jca`.

### 10.5 verdict

- **`X509` and `TLS`:** not reported, reach direct.
- **`AndroidKeyStore`:** not reported. Reach is direct at one site (`opencloud`), indirect at three and unmeasured at nine; the shortfall is recorded as the caveat above.
- **Bilateral half:** present in both campaigns.

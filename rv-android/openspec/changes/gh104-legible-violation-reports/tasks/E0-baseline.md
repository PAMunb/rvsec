# Group 1 — E0 baseline and definitions

Tracked checkboxes: `tasks.md` §1. This file is the execution brief. Wave 1; no dependency; disjoint from every other group.

## Subagent brief

You measure; you do not repair. Read `design.md` D-9 and `docs/20260815_gh103_analysis_layer.md:10-22,62-84,88-112` (freeze items, `Envelope`, "cmp162 is a fixture"). Every number you write leaves with numerator, denominator and the definition id that produced it. Reproduce first, compare with the expected values second; where you disagree, the artefact decides and you record the disagreement.

## Files (create; nothing else is edited)

- `scripts/gh104_baseline.py` — the measurement script (declares its **own frozen 11-column reader** for comp162 and its own 10-column reader for the article dataset; it does not import `aperv_tool.analysis.violations.read_errors_csv`, because that reader checks one in-place literal, `ERRORS_CSV_HEADER` at `violations.py:63-75`, which Group 5 task 5.6 changes to 13 columns — after that the shared reader raises `ValueError` on every comp162 file, `:242-246`, and an import path pins nothing).
- `data/gh104/baseline.md`, `data/gh104/baseline.json` — the numbers with envelopes; the JSON is what the byte-identical test compares.
- `data/gh104/definitions.md` — the freeze items.
- `tests/parity/test_gh104_baseline.py`.

## Definitions (freeze items — the script raises `FreezeItemUnset` if any is missing)

| id | definition |
|---|---|
| `mute` | `message.strip() == 'unknown'` |
| `site_comp162` | `(spec, class, method, source)` — comp162 has 11 columns |
| `site_article` | `(spec, class, method)` — the article dataset (`/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv`) has 10 columns and **no `source`**; the lineage's twin numbers reproduce only under this |
| `third_party_prefixes` | nine: `okhttp3.`, `com.google.`, `kotlin.`, `io.ktor.`, `org.bouncycastle.`, `androidx.`, `org.conscrypt.`, `okio.`, `org.spongycastle.` — the seven-vendor list gives 78.49 %, +`okio.` 82.67 %, all nine 85.44 % |
| `shards` | `experimento-comp162/results/*/*/errors.csv` are 8 **disjoint** shards (112 distinct APKs, zero overlap, 3 tools × 3 repetitions each) — never "replicas" |
| `identity5` | `(apk, rep, tool, spec, class, method, source, message)` for repetition; `ErrorSummary` identity is `(spec, error, class, method, location)` |
| `error_type` | from `unique_msg.split(':::')[3]` (comp162), never from `message` |

## Expected values (measured 2026-08-16; the script must reproduce them exactly)

| quantity | value |
|---|---|
| article rows / distinct messages / `unknown` | 97,018 / 19 / 70,760 = 72.93 % |
| article `but found .` | 8,843 = TMF 8,371 + Signature 234 + MessageDigest 156 + SSLContext 51 + Mac 31 |
| article columns | `apk,rep,timeout,tool,time,spec,class,method,message,unique_msg` |
| comp162 rows / mute / mute sites | 19,664 / 15,714 (79.91 %) / 296 |
| comp162 mute-legible twins | 3,950 rows in 101 sites (= total legible rows; zero legible-only sites) |
| comp162 mute-mute twins | 838 rows in 12 sites (all `IvParameterSpecSpec`, 419 + 419) |
| comp162 mute-only remainder | 10,926 rows in 183 sites |
| comp162 per-spec mute (top 8) | SSLContext 2,916 · SecureRandom 2,882 · TMF 2,855 · MessageDigest 2,008 · Cipher 1,461 · KeyStore 1,136 · IvParameterSpec 838 · SecretKeySpecSpec 820 |
| comp162 `but found .` | 98 |
| comp162 identities (`identity5`) | 6,344 for 19,664 rows; 67.74 % repetition; max 49; 0 % from replication (each identity in exactly one shard) |
| third-party (article) | 76,154 = 78.49 % · 80,204 = 82.67 % · 82,890 = 85.44 % |
| `UnsafeAlgorithm` MD5/SHA-1 (article) | 5,892 of 15,444 `UnsafeAlgorithm` rows = 38.15 %, all `MessageDigestSpec`; against that specification's own 6,048 `UnsafeAlgorithm` rows = 97.4 % (36.4 % of all its 16,183 rows), and 6.1 % of the 97,018-row corpus (3,552 `MD5` + 2,340 `SHA-1`/`SHA1`/`SHA`) — the three denominators are different questions, report all three, because Group 2 task 2.4 quotes the second and third as the declared cost of accepting what api30 admits |
| four spec-set directories | jca 23 files/21 `addError`/0 `Log.v`; the reproved derived set 23/21/0 (directory `jca_android/` until Group 2 task 2.1's `git mv`, `jca_android_bug_predicate/` after — record which name you measured under); generic 118/0/118; generic_new 27/0/27 |
| `new ErrorDescription` in jca | 51 = 25 three-arg + 26 four-arg |

Reproduction commands are in `docs/20260816_javamop_mensagens_change_handoff_prompt.md:252-313` (read-only python one-liners). Copy them into the script as functions; do not paste numbers.

## The Android tier this change is aimed at (task 1.4)

The pivot to Android rests on a publishable tier with primary-source evidence: **11,409 events / 84 misuses of 454 = 18.5 %**, from `ase-journal/docs/20260806_owasp_cwe_mapping_report.md`. Record it in `data/gh104/baseline.md` as its own section, because it is the denominator against which Group 2's allow-list transcription and Group 10 task 10.5's device reading are judged.

| spec / ErrorType / observed value | events | apps | misuses |
|---|---|---|---|
| `SSLContextSpec / UnsafeProtocol / TLS` | 8,648 | 60 | 65 |
| `KeyStoreSpec / InvalidKeyStoreType / AndroidKeyStore` | 2,005 | 11 | 12 |
| `TrustManagerFactorySpec / UnsafeAlgorithm / X509` | 643 | 3 | 5 |
| `CipherSpec / UnsafeAlgorithm / RSA/ECB/OAEPWithSHA1AndMGF1Padding` | 109 | 1 | 1 |
| `SignatureSpec / UnsafeAlgorithm / SHA256WITHRSA` | 4 | 1 | 1 |

With it, record the context fixation the whole change inherits: **API 30 / Android 11**, Conscrypt branch `android11-release` (`ase-journal/dataset.tex:5`; `20260806_owasp_cwe_mapping_report.md:622-648`). This is what makes `MetaCrySL/generated/api30/*.cryptsl` the oracle and not one option among several.

## Acceptance

- Two consecutive runs produce byte-identical `baseline.json` (`test_baseline_reproduces_byte_identical`).
- Removing any freeze item raises `FreezeItemUnset` (`test_freeze_items_required`).
- `data/gh104/baseline.md` states, per number, numerator, denominator, definition id, input file(s) and sha256 of the inputs.
- The Android tier table and the API-30 / Conscrypt `android11-release` context fixation are in `data/gh104/baseline.md` with their sources.
- The instrument discontinuity is written: comp162 through the declared frozen 11-column reader, the article through the declared 10-column reader; parity ≠ correctness sentence quoted from the gh103 doc.
- The measured footprint of two structural facts Group 8 records but does not repair is in `baseline.md` as ratios, per specification, on both corpora: `InvalidSequenceOfMethodCalls` against the specification's own labelled type (article: `SSLContextSpec` 17,510 vs 8,802 `UnsafeProtocol`; `TrustManagerFactorySpec` 9,015 vs 9,014 `UnsafeAlgorithm`; comp162: `TrustManagerFactorySpec` 2,855 vs 61, `SecureRandomSpec` 2,882 vs 0) — the first pair is the second `@fail` report every clause-encoding orphan emits, the comp162 pair the DEX-path `g1`+`g2` double fire (design D-1, task 8.12).

# Group 10 — Integration and verification

Tracked checkboxes: `tasks.md` §10. Last; after every other group.

## Brief

- 10.1 Freeze and divergence: `uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh101_specset_gates.py tests/parity/test_gh104_specset_gates.py tests/parity/test_gh104_structural_gates.py tests/parity/test_gh104_baseline.py tests/parity/test_gh104_unique_msg_built_once.py -q` — all green. In the Java git root, `git diff 7e7acb69 -- rvsec/rvsec-mop/src/main/resources/jca rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/CipherTransformationUtil.java` must be empty; `git diff 7e7acb69 --find-renames -- rvsec/rvsec-mop/src/main/resources/jca_android rvsec/rvsec-mop/src/main/resources/jca_android_bug_predicate` must show the 23 files as pure renames (`R100`) plus the successor set as additions, with **zero** content hunks on the renamed side; and `.../jca/util/AndroidCipherTransformationUtil.java` must be unmodified. In the MetaCrySL tree, `git status` must be clean — this change reads `generated/api30/` and writes nothing there. (The freeze is on the specification *sources*: a generated monitor that differs because Group 3 changed the generator is not a freeze violation; old measurements reproduce by pinning the toolchain, per design D-4.)
- 10.2 / 10.3 the skills run per module as listed in `tasks.md`; record outputs.
- 10.4 Device validation — the only device task. Command shape (the platform manages the emulator; never run `emulator`/`adb` by hand): `uv run rv-experiment run --tools monkey --specification-set jca_android --timeouts 180 --apks-dir <dir>` with the four APKs gh101 task 8.1 used (`com.owncloud.android_48000100`, `eu.opencloud.android_9`, `de.luhmer.owncloudnewsreader_196`, `com.etesync.syncadapter_20700` — sources: the published campaign's APK store; `com.etesync` reached no monitored call in 8.1 and is reported rather than dropped). Record in `evidence/device_validation.md`: rows, `unknown` count (expect 0), `but found .` count (expect 0), envelope fields populated (`ev`, `val`, `exp`), `advicesExcludedByArity` and `wrappersGenerated` from the results JSON, parser counters from `parser_diagnostics`. Monkey is stochastic; read shapes, not counts.
- 10.5 Read the device evidence against the pivot's publishable tier (Group 1 task 1.4). Three of its five rows are what the api30 transcription of task 2.4 plus the normalisation rule of task 2.5 are supposed to settle, and the device run is the first place that can be observed end to end:

  | row | seen on the frozen set | expected on `jca_android` | which task settles it |
  |---|---|---|---|
  | `SSLContextSpec / UnsafeProtocol / TLS` (8,648 ev / 65 misuses) | reported | not reported — `TLS` is in the api30 `SSLContext` list | 2.4 |
  | `KeyStoreSpec / InvalidKeyStoreType / AndroidKeyStore` (2,005 ev / 12) | reported | not reported — `AndroidKeyStore` is in the api30 `KeyStore` list | 2.4 |
  | `TrustManagerFactorySpec / UnsafeAlgorithm / X509` (643 ev / 5) | reported as `expecting one of PKIX,SunX509 but found X509.` at `MemorizingTrustManager.java:282` (gh101 8.2) | not reported — `X509` is a Conscrypt alias of `PKIX` (`OpenSSLProvider.java:90`) | 2.5 (alias table), **not** 2.4 |
  | `CipherSpec / UnsafeAlgorithm / RSA/ECB/OAEPWithSHA1AndMGF1Padding` (109 ev / 1) | reported | **still reported** — the observed spelling has no hyphen in `SHA1`, api30 and Conscrypt both register only the hyphenated form (`:338`, `:339-340`), so neither case normalisation nor the alias table closes it; the row is carried in `divergence_record.csv` with behavioural evidence until the provider that resolves it is identified | none (execution item) |
  | `SignatureSpec / UnsafeAlgorithm / SHA256WITHRSA` (4 ev / 1) | reported | not reported — api30 lists `SHA256withRSA` and case normalisation settles the spelling | 2.4 + 2.5 |

  Record the **shape** of each line, not counts. If Monkey does not reach one of the five call sites in this run, say so — an unreached site is not evidence of a repair.
- 10.8 (before 10.4) `get_static_analysis_config()` passes the resolved set directory as `mop_dir` — today `RVStaticAnalysisConfig` defaults it to `resources/jca` (`rv_static_analysis/config.py:198-207`) and `rv_experiment/config.py:942-951` overrides nothing, so a `jca_android` campaign's static view (targets, reachability, coverage denominator) is the `jca`'s (audit G12). Reuse the resolution of `get_monitored_operations_config()` (`config.py:685-700`) rather than duplicating the mapping; one test in `tests/test_config_jit.py`; 10.4 records the directory the static analysis used.
- 10.6 `/rv-code-reviewer` via the Skill tool over the whole change (Java + Python).
- 10.7 `/rv-docs-sync` per module whose CLAUDE.md/architecture.md describes the parser, the collectors' line, `errors.csv` columns or the spec-set enumeration; at archive/sync time also fix `openspec/specs/experiment/spec.md:87` (`# "jca", "generic", or "custom"` sample comment) and the CLAUDE.md paragraph on specification sets, which must now name three predefined sets (`jca`, `jca_android`, `generic`) plus `custom` — `jca_android` naming the successor set, and the reproved derived set living at `jca_android_bug_predicate/` where nothing selects it.

## Commit and close

- Final commit message carries `closes #104`; PR body `Closes #104`.
- Archive via `/opsx:archive gh104-legible-violation-reports` (syncs the six deltas; INV-INS-118..129, INV-ANA-62/63, INV-CORE-56/57, INV-PLT-30, INV-CAN-25/26 land in the main specs).

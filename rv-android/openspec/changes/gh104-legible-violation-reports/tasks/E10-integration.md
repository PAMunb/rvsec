# Group 11 — Integration and verification

Tracked checkboxes: `tasks.md` §11. Last; after every other group.

## Brief

- 11.1 Gates: `uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh101_specset_gates.py tests/parity/test_gh104_specset_gates.py tests/parity/test_gh104_structural_gates.py tests/parity/test_gh104_baseline.py tests/parity/test_gh104_unique_msg_built_once.py -q` — all green; `git diff 7e7acb69 -- rvsec/rvsec-mop/src/main/resources/jca rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/CipherTransformationUtil.java` empty (run in the Java git root).
- 11.2 / 11.3 the skill runs per module as listed in `tasks.md`; record outputs.
- 11.4 Device validation — the only device task. Command shape (the platform manages the emulator; never run `emulator`/`adb` by hand): `uv run rv-experiment run --tools monkey --specification-set jca_v2 --timeouts 180 --apks-dir <dir>` with the four APKs gh101 task 8.1 used (`com.owncloud.android_48000100`, `eu.opencloud.android_9`, `de.luhmer.owncloudnewsreader_196`, `com.etesync.syncadapter_20700` — sources: the published campaign's APK store; `com.etesync` reached no monitored call in 8.1 and is reported rather than dropped). Record in `evidence/device_validation.md`: rows, `unknown` count (expect 0), `but found .` count (expect 0), envelope fields populated (`ev`, `val`, `exp`), `advicesExcludedByArity` and `wrappersGenerated` from the results JSON, parser counters from `parser_diagnostics`, and the shape of the `TrustManagerFactorySpec` line at `MemorizingTrustManager.java:282` (gh101 8.2 read `expecting one of PKIX,SunX509 but found X509.` on the frozen set). Monkey is stochastic; read shapes, not counts.
- 11.5 `/rv-code-reviewer` via the Skill tool over the whole change (Java + Python).
- 11.6 `/rv-docs-sync` per module whose CLAUDE.md/architecture.md describes the parser, the collectors' line, `errors.csv` columns or the spec-set enumeration; at archive/sync time also fix `openspec/specs/experiment/spec.md:87` (`# "jca", "generic", or "custom"` sample comment).

## Commit and close

- Final commit message carries `closes #104`; PR body `Closes #104`.
- Archive via `/opsx:archive gh104-legible-violation-reports` (syncs the six deltas; INV-INS-118..126, INV-ANA-62/63, INV-CORE-56/57, INV-PLT-30, INV-CAN-25/26 land in the main specs).

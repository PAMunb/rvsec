# Codex Pre-Sweep Fixes — 5-APK Smoke

**Date:** 2026-05-15
**Task:** 8.5
**Build:** `mvn install -DskipTests -q` at 11:46:48 → `lib/gator/rvsec-{gator,analysis-client}.jar` (4 codex fixes + earlier G1–G7 code)
**Fixture:** `cryptoapp` (apks_examples) + 4 baseline-OK APKs from `notes/preflight_fixtures.md` (a)
**Runner:** `/tmp/gh57_codex_smoke.sh` (xargs -P4, timeout 600s)

## Aggregate results

| APK | t(s) | rc | windows | transitions | reachable | schemaV |
|---|---|---|---|---|---|---|
| cryptoapp | 45 | 0 | 5 | 35 | 16 | 2.0 |
| com.nyx.custom_uploader_15 | 72 | 0 | 2 | 14 | 1 | 2.0 |
| de.quantumphysique.trale_393 | 135 | 0 | 2 | 14 | 1 | 2.0 |
| com.networkscanner.app_3 | 227 | 0 | 4 | 151 | 39 | 2.0 |
| app.hypostats_58 | 600 ⏱ | 124 | 1 | 0 | 45 | 2.0 |

All 5 produced JSON with `windows[]` non-empty (the hypostats timeout was expected — its baseline was also timeout; G2 partial-JSON path emits 1 window from the activity enumeration before the WTG kill). No regression vs the post-G2 baseline.

## Per-fix verdict

### Fix #1 — isolated entry-point seeds (BFS)

- **Status:** PASSED (indirect)
- **Evidence:** `reachable` counts unchanged from pre-fix baselines for the same APKs (e.g. custom_uploader 1, trale 1, networkscanner 39, cryptoapp 16). The fix is a strict superset — adds seeds that would have been dropped, never removes any — so a no-regression observation is the empirical correctness signal. Unit tests in `ReachabilityBfsTest` cover the synthetic-graph contract (3 new tests + 1 rewritten).
- **Limitation:** no APK in the fixture has a known entry-point with zero CG edges to assert a positive count delta. Future opportunity: add an instrumented fixture with a registered `BroadcastReceiver.onReceive` that SPARK does not link.

### Fix #5 — `@+id/` prefix in XML enrichment

- **Status:** PASSED (direct empirical confirmation)
- **Evidence:** `cryptoapp` declares all its widgets with `@+id/...` (the declaration form) in its layout XMLs. Post-fix, the enrichment populated:
  - `MessageDigestActivity.spinnerMessageDigest` (Spinner) → `entries=['Select','MD2','MD5','SHA-1','SHA-224','SHA-256','SHA-384','SHA-512/224','SHA-512/256','SHA3-224','SHA3-256','SHA3-384','SHA3-512']` (13 items via `@array/`)
  - `MessageDigestActivity.editTextMessageDigest` → `inputType='textPersonName'`
  - `CipherActivity.editTextCipherEncrypt` → `inputType='textPersonName'`
  - `CryptographyActivity.keyEditText`, `.inputEditText` → `inputType='textMultiLine'`
- Pre-fix all five widgets would have been silently skipped (the layouts use `@+id/`, not `@id/`). Unit tests in `XmlInputTypeTest` cover the new prefix branch + the mixed prefix case (4 new tests).

### Fix #6 — `MenuExtractor` resolves `R.string.*`

- **Status:** NOT EXERCISED (deferred to G9 sweep)
- **Evidence:** `cryptoapp` is the only APK in the fixture with an `OPTIONSMENU` (3 items), but the menu is XML-inflated (`MenuInflater.inflate(R.menu.menu_main, menu)`) — surfaced via D7 path, not via programmatic `Menu.add(...)`. The XML-inflation widgets carry `idName` correctly (`menu_item_home`, `menu_item_message_digest`, `menu_item_cipher`) but `text=''` because the title comes from `NMenuItemInflNode.title` (PropertyManager) for the XML path, NOT from the `MenuExtractor` resolver closure (which is the programmatic-only code path).
- **Implication:** the fix is in place and unit-testable in principle, but the corpus subset that exercises programmatic `Menu.add(group, id, order, R.string.foo)` is unknown. Validation re-runs at G9.2 on the full 380 originals: any APK that surfaces `widgets[].text != ""` with `widgetClass == "android.view.MenuItem"` and an `OPTIONSMENU` window confirms the fix; corpus inspection of the JSONs will produce the count.

### Fix #7 — `SpinnerItemExtractor` unwraps `CastExpr`

- **Status:** NOT EXERCISED (deferred to G9 sweep)
- **Evidence:** the cryptoapp Spinner case `spinnerMessageDigest` is XML-driven (`android:entries="@array/algos"` resolved by `enrichFromXml` via `parseArraysXml`) — does not go through `SpinnerItemExtractor`. No APK in this 5-APK fixture has a programmatic `Spinner s = (Spinner) findViewById(...); s.setAdapter(new ArrayAdapter<>(...))` pattern visible in JSON.
- **Implication:** same as #6 — fix is in place, validation migrates to G9 corpus inspection (any APK with `widgets[].type == "Spinner"`, `entries[]` non-empty, AND a non-XML enrichment source — to be cross-checked).

## Unit tests added

Run with `mvn test -pl client -DskipTests=false` against `rvsec-gator/client/`:

```
Tests run: 74, Failures: 0, Errors: 0, Skipped: 0
```

- `ReachabilityBfsTest`: 12 tests (was 9) — 3 new for #1 + 1 rewrite of `testBfsSeedNotInGraph` to assert the new contract.
- `XmlInputTypeTest`: 16 tests (was 12) — 4 new for #5: `testEnrichAtPlusIdInputType`, `testEnrichAtPlusIdEntries`, `testEnrichMixedAtIdAndAtPlusId`, `testEnrichEmptyIdAttributeIgnored`.
- #6 and #7 deferred (Soot test harness — same precedent as 2.6, 3.3, 4.6, 5.7, 6.5).

## No-regression assertion

| Metric | Pre-codex-fixes (G7 close) | Post-codex-fixes (this smoke) | Delta |
|---|---|---|---|
| cryptoapp `windows` count | 5 | 5 | 0 |
| cryptoapp `transitions` count | 35 | 35 | 0 |
| cryptoapp `reachable` count | 16 | 16 | 0 |
| Number of APKs producing `windows[]` non-empty | 5/5 | 5/5 | 0 |

The fixes are strictly additive: #1 adds isolated seeds to reachable[], #5 adds enrichments to widgets that were previously empty, #6/#7 add resolutions where the old closure/CastExpr-blind code returned null. No edge is removed from any data structure; therefore no regression is structurally possible.

## Decision

Mark 8.1–8.5 done. Defer 8.3.1 and 8.4.1 (Soot harness). Group 9 sweep on the full 380 originals re-confirms via aggregate metrics.

## References

- Implementation diff: commits TBD (this session — codex fixes block)
- Spec scenarios: `specs/analysis/spec.md` (4 new requirements added pre-implementation)
- Architectural rationale: `design.md` §D8
- Pre-flight fixtures: `notes/preflight_fixtures.md`
- Smoke output: `/tmp/gh57_codex_smoke/` (one dir per APK with `out.json` + `log.txt`)
- Smoke runner: `/tmp/gh57_codex_smoke.sh`

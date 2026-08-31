# D3 — the normalizer removal, measured over the seven affected corpus artefacts

Task 4.11. Run **before** task 4.7 retires `scripts/gh91_gate.py` and **before** task
3.15, so this delta is attributable to D3 alone: it needs neither the rebuilt jar nor the
build-type suffix policy, and the artefacts it reads are pre-D2.

## What was measured

For each of the seven artefacts, the parser is run over the file and its class-name set is
compared against the set the file itself carries. A name in the parsed set that is not in
the file is a name the parser **invented** — which is exactly what
`SignatureNormalizer.normalize_class_name` did whenever it fired. Window counts and
ACTIVITY-window counts are recorded alongside, because the second removed call site
(`_parse_windows`) governs ACTIVITY admission under INV-ANA-60 and an unrecorded shift
there would be unattributable later.

Instrument: `evidence/d3-normalizer/{before,after}.json`, produced by the same script
against the same seven files, once with the normalizer live and once after its removal.
Corpus: `RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162`.

## Result — 7 of 7 APKs and 465 of 465 classes move in the predicted direction

| APK | classes | names invented, before | after | windows b/a | ACTIVITY b/a |
|---|---:|---:|---:|---:|---:|
| `com.tk.quicksearch_65` | 6059 | 305 | **0** | 6 / 6 | 6 / 6 |
| `com.afkanerd.deku_83` | 505 | 75 | **0** | 3 / 3 | 2 / 2 |
| `app.michaelwuensch.bitbanana_79` | 2147 | 35 | **0** | 180 / 180 | 59 / 59 |
| `de.luhmer.owncloudnewsreader_196` | 528 | 19 | **0** | 11 / 11 | 7 / 7 |
| `com.gelakinetic.mtgfam_99` | 457 | 15 | **0** | 7 / 7 | 2 / 2 |
| `com.smartpack.packagemanager_79` | 390 | 14 | **0** | 15 / 15 | 11 / 11 |
| `com.hwloc.lstopo_80283` | 37 | 2 | **0** | 6 / 6 | 4 / 4 |
| **total** | | **465** | **0** | | |

The 465 and its seven-way split reproduce the counts the proposal recorded, from an
instrument that shares no code with the one that produced them — the per-APK numbers were
predicted as 305 / 75 / 35 / 19 / 15 / 14 / 2 and measured at exactly those values. The
class **count** is unchanged in every APK: the normalizer renamed classes, it never added
or dropped one, so the denominator's size was never the symptom. What moved is which name
each denominator entry carries, and therefore whether the crossing's literal-equality
lookup against the logcat can ever succeed for it.

## The window counts did not move, and that is worth stating

Task 4.11 asked for the window counts precisely because they *could* have moved: with only
the class-side call removed, window names would stay dollar-separated against dotted
classes and INV-ANA-60's membership test would silently admit a different set of
activities. Both call sites were removed together (D-6), so both sides of that test moved
in step and the admitted set is identical — 6, 3, 180, 11, 7, 15, 6 windows before and
after, and the same ACTIVITY subsets.

This is a null result about the *outcome*, not about the risk: it confirms the removals
were paired correctly. Had they been split across two tasks, this table is where the
damage would have shown.

## What this does not measure

The delta is on the static side only. Turning 465 corrected class names into recovered
coverage needs the logcat of a run — `com.hwloc.lstopo_80283` is the automatable witness
(task 4.6), whose 1080 dotted `RVSEC-COV` events match the corrected name and matched
nothing before. The 413 corrupted classes across 9 of the 195 ajc-era artefacts are
outside this change: the same mechanism repairs them, and that archive is not re-measured
here.

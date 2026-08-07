# Verification report — experimento-rearch-aperv

**Verdict: ADMISSIBLE**

Tasks: 369 | identities (deduped): 360 | Tasks audited: 360

## Gate 6 — admissibility (100% of identities, before any aggregation)

Criteria, applied blind to arm and to the direction of the effect:

- **C1** — state == COMPLETED with an empty error_message
- **C2** — execution_time_seconds >= timeout
- **C3** — the trace carries at least one step beyond RUN_START
- **C4** — at least 1 distinct RVSEC-COV signature in the logcat
- **C5** — cov_method > 0 and cov_act > 0
- **C6** — admissible identities == the manifest's predicted_identities

Admissible: 360 / 360 identities | manifest predicts 360

PASS — every identity is admissible and the count is as predicted.

Failures per criterion (an identity may fail more than one): C1=0, C2=0, C3=0, C4=0, C5=0, C6=0

Distinct RVSEC-COV signatures per identity — n=360, min=46, median=4414.5, max=23711, at or below the floor of 1: 0

## Gate 7 — control arm `mop_off_llm_off` carries no MOP guidance

Control runs audited: 120 | steps: 214448

PASS — no step was selected by a MOP-derived source and no MOP-widget boost was applied.

`mop_frontier` non-zero steps in the control arm: 0 (reported, not gated)

## Gate 1 — RUN_START == manifest (100% of tasks)

PASS — every task's config matched the manifest.

Declared keys left at the jar's own value (absent from `params`, so not compared):
- `aperv:mop_off_llm_off`: ape.mopWeightOpenMenu, ape.mopWeightWtg

## Gate 2 — identity collisions (must be 0)

PASS — no identity maps to more than one arm.

## Gate 3 — paired completeness (100%)

Arms in the design: ['aperv:mop_on_llm_off', 'aperv:mop_off_llm_off', 'aperv:mop_on_llm_70']
Paired APKs (present in every arm): 40 — ['at.linuxtage.Eventfahrplan_1700028.apk', 'be.digitalia.fosdem_2300230.apk', 'ch.digitale_gesellschaft.winterkongress.schedule_118.apk', 'com.beemdevelopment.aegis_81.apk', 'com.cointrend_10304.apk', 'com.darkrockstudios.app.securecamera_31.apk', 'com.darkrockstudios.apps.hammer.android_303020000.apk', 'com.defname.localshare_14.apk', 'com.dessalines.habitmaker_5501.apk', 'com.faltenreich.diaguard_68.apk', 'com.flauschcode.broccoli_1040400.apk', 'com.hegocre.nextcloudpasswords_38.apk', 'com.kin.easynotes_14.apk', 'com.manimarank.spell4wiki_21.apk', 'com.ominous.quickweather_112.apk', 'com.owncloud.android_48000100.apk', 'com.rastislavkish.vscan_24.apk', 'com.smartpack.packagemanager_79.apk', 'com.starry.greenstash_440.apk', 'de.blau.android_3404.apk', 'de.lukasneugebauer.nextcloudcookbook_62.apk', 'de.saschahlusiak.freebloks_181.apk', 'fr.gaulupeau.apps.InThePoche_234.apk', 'info.metadude.android.clt.schedule_117.apk', 'info.metadude.android.datenspuren.schedule_110.apk', 'info.metadude.android.fosdem.schedule_117.apk', 'info.metadude.android.fossgis.schedule_118.apk', 'info.metadude.android.gpn.schedule_119.apk', 'info.metadude.android.protocolberg.schedule_109.apk', 'io.github.samolego.canta_225.apk', 'jwtc.android.chess_283.apk', 'net.pfiers.osmfocus_1009013.apk', 'net.phbwt.paperwork_1003007.apk', 'org.cry.otp_31.apk', 'org.liberty.android.fantastischmemo_241.apk', 'org.liberty.android.freeotpplus_26.apk', 'org.prauga.messages_8.apk', 'rocks.poopjournal.metadataremover_20020.apk', 'ua.acclorite.book_story_14.apk', 'ua.com.radiokot.lnaddr2invoice_8.apk']

No exclusions — every observed APK is present in every arm.

## Gate 4 — per-arm median time_ms <= 2x global median

Global median time_ms: 645175.0
PASS — no arm exceeds 2x the global median.

## Gate 5 — re-derivation divergence vs per_apk_paired.csv

Integer metrics (mop_total, mop_unique, crashes): exact; percentage metrics (cov_method, cov_act, cov_mop): <= 0.01pp.

PASS — independent re-derivation matches the consolidated CSV.

## Hand-count sample (seed=42, 10 tasks)

Independent per-identity re-derivation vs the consolidated (rep-averaged) CSV cell:

- identity `('org.prauga.messages_8.apk', 'aperv', 'mop_on_llm_70', 1, 1800)` (arm `aperv:mop_on_llm_70`, RVSEC-COV distinct methods=11058)
    re-derived: {'mop_total': 0.0, 'mop_unique': 0.0, 'crashes': 0.0, 'cov_method': 45.773014977752716, 'cov_act': 100.0, 'cov_mop': 46.7439293598234}
    csv cell:   {'mop_total': '0.0', 'mop_unique': '0.0', 'crashes': '0.0', 'cov_method': '46.0717', 'cov_act': '100.0', 'cov_mop': '45.8057'}
- identity `('com.darkrockstudios.apps.hammer.android_303020000.apk', 'aperv', 'mop_on_llm_70', 1, 1800)` (arm `aperv:mop_on_llm_70`, RVSEC-COV distinct methods=22354)
    re-derived: {'mop_total': 57.0, 'mop_unique': 9.0, 'crashes': 0.0, 'cov_method': 43.58777607259625, 'cov_act': 100.0, 'cov_mop': 41.70572480749916}
    csv cell:   {'mop_total': '61.6667', 'mop_unique': '9.0', 'crashes': '0.0', 'cov_method': '42.9917', 'cov_act': '100.0', 'cov_mop': '41.0194'}
- identity `('be.digitalia.fosdem_2300230.apk', 'aperv', 'mop_on_llm_70', 1, 1800)` (arm `aperv:mop_on_llm_70`, RVSEC-COV distinct methods=4482)
    re-derived: {'mop_total': 20.0, 'mop_unique': 5.0, 'crashes': 0.0, 'cov_method': 61.512278142475076, 'cov_act': 100.0, 'cov_mop': 63.92857142857142}
    csv cell:   {'mop_total': '26.6667', 'mop_unique': '5.0', 'crashes': '0.0', 'cov_method': '61.8527', 'cov_act': '100.0', 'cov_mop': '64.246'}
- identity `('com.owncloud.android_48000100.apk', 'aperv', 'mop_on_llm_70', 3, 1800)` (arm `aperv:mop_on_llm_70`, RVSEC-COV distinct methods=3546)
    re-derived: {'mop_total': 32.0, 'mop_unique': 7.0, 'crashes': 0.0, 'cov_method': 12.438230685790044, 'cov_act': 70.83333333333334, 'cov_mop': 12.575757575757576}
    csv cell:   {'mop_total': '47.0', 'mop_unique': '7.0', 'crashes': '0.0', 'cov_method': '12.2273', 'cov_act': '69.4444', 'cov_mop': '12.3737'}
- identity `('com.manimarank.spell4wiki_21.apk', 'aperv', 'mop_on_llm_off', 3, 1800)` (arm `aperv:mop_on_llm_off`, RVSEC-COV distinct methods=4646)
    re-derived: {'mop_total': 30.0, 'mop_unique': 5.0, 'crashes': 0.0, 'cov_method': 32.61211644374508, 'cov_act': 75.0, 'cov_mop': 44.680851063829785}
    csv cell:   {'mop_total': '30.0', 'mop_unique': '5.0', 'crashes': '0.0', 'cov_method': '31.9827', 'cov_act': '75.0', 'cov_mop': '56.0284'}
- identity `('com.kin.easynotes_14.apk', 'aperv', 'mop_on_llm_off', 1, 1800)` (arm `aperv:mop_on_llm_off`, RVSEC-COV distinct methods=2848)
    re-derived: {'mop_total': 0.0, 'mop_unique': 0.0, 'crashes': 0.0, 'cov_method': 54.968492486669895, 'cov_act': 50.0, 'cov_mop': 57.11845102505695}
    csv cell:   {'mop_total': '0.0', 'mop_unique': '0.0', 'crashes': '0.0', 'cov_method': '54.9362', 'cov_act': '50.0', 'cov_mop': '57.0805'}
- identity `('com.defname.localshare_14.apk', 'aperv', 'mop_on_llm_off', 3, 1800)` (arm `aperv:mop_on_llm_off`, RVSEC-COV distinct methods=4523)
    re-derived: {'mop_total': 17.0, 'mop_unique': 1.0, 'crashes': 0.0, 'cov_method': 42.860520094562645, 'cov_act': 100.0, 'cov_mop': 47.820429407937546}
    csv cell:   {'mop_total': '16.6667', 'mop_unique': '1.0', 'crashes': '0.0', 'cov_method': '43.5776', 'cov_act': '100.0', 'cov_mop': '48.2759'}
- identity `('com.darkrockstudios.app.securecamera_31.apk', 'aperv', 'mop_on_llm_off', 2, 1800)` (arm `aperv:mop_on_llm_off`, RVSEC-COV distinct methods=936)
    re-derived: {'mop_total': 50.0, 'mop_unique': 4.0, 'crashes': 0.0, 'cov_method': 10.840156639373442, 'cov_act': 100.0, 'cov_mop': 9.950248756218906}
    csv cell:   {'mop_total': '53.3333', 'mop_unique': '4.0', 'crashes': '0.0', 'cov_method': '10.8758', 'cov_act': '100.0', 'cov_mop': '10.0498'}
- identity `('ua.acclorite.book_story_14.apk', 'aperv', 'mop_on_llm_70', 2, 1800)` (arm `aperv:mop_on_llm_70`, RVSEC-COV distinct methods=5431)
    re-derived: {'mop_total': 0.0, 'mop_unique': 0.0, 'crashes': 0.0, 'cov_method': 40.6283323763432, 'cov_act': 100.0, 'cov_mop': 41.46772767462423}
    csv cell:   {'mop_total': '0.0', 'mop_unique': '0.0', 'crashes': '0.0', 'cov_method': '39.0725', 'cov_act': '100.0', 'cov_mop': '40.1857'}
- identity `('net.pfiers.osmfocus_1009013.apk', 'aperv', 'mop_off_llm_off', 1, 1800)` (arm `aperv:mop_off_llm_off`, RVSEC-COV distinct methods=8108)
    re-derived: {'mop_total': 45.0, 'mop_unique': 5.0, 'crashes': 0.0, 'cov_method': 60.243760882182244, 'cov_act': 50.0, 'cov_mop': 60.10673782521682}
    csv cell:   {'mop_total': '50.0', 'mop_unique': '5.0', 'crashes': '0.0', 'cov_method': '55.3879', 'cov_act': '50.0', 'cov_mop': '56.5933'}

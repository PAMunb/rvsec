# gh122 task 5.1: real-data check on gh120 documents

- **Run:** 2026-10-08, `uv run python -I real_data_check.py <dir>`, derive at the working tree of this change (groups 1–3).
- **Source:** the Study 03 v2 static analysis, round A (Cloud Batch, gh120 GATOR), in
  `rvsec-study03-replication-package/data/raw/e6-static-analysis/A/<apk>/<apk>.json`.
  Round A has 92 documents that are complete and final, according to the `rep-pack-e03` session.
- **Sample:** 23 of the 92, every fourth by file size, from 83 KB to 55 MB. The 700 MB `com.celzero.bravedns_619` is not in the sample.
  The files were copied to a scratch directory and derived from the copies. Nothing was written next to the originals.
  The sha256 of each copy matched its source; the hashes are listed at the end.

## Result

- `targets > 0` on all 23 documents.
- INV-DRV-10 holds on every pair list: 0 violations over the widget `dist`, `activityDist` and handler `dist` lists.
- The source-3 constructor exclusion shrinks `mopActivitiesAugmented` in 8 of the 23 apps; the per-app sizes are the "aug (excl)" and "aug (no excl)" columns. The widest gap is owncloud, 25 → 18.
- `handlers`: 3,567 records, 787 of them carrying `dist`.
- Flagged emitted widgets: 380.
  - 266 (70.0 %) carry a `click` pair, the measure the task names.
  - 372 (97.9 %) carry a pair on at least one of their flagged events. The 106 between the two counts are widgets flagged only on `entertext`, `select`, `itemselected`, `itemclick` or `drag`, and each has its pairs under that event.
- The remaining 8 are all in `dev.spiegl.flyingcarpet_21`, flagged on `click` with no pair. There the producer marks 23 of the 48 reaching methods `reachesTarget: true` with no `targetDistances`; one of them is the click wrapper `MainActivity$$ExternalSyntheticLambda10.onClick`. Over the whole sample, 34 of 11,777 reaching methods carry no pairs. This is producer output, so the derive cannot give those methods a distance, and the jar scores those widgets without one. The cause on the GATOR side is not verified; the 10-call `DIST_MAX` of gh120 is a candidate.

## Output

```
apk | targets | DRV-10 bad | aug (excl) | aug (no excl) | mopActivities | handlers | handlers w/ dist | flagged widgets | w/ click pair | w/ pair on a flagged event | reaching methods | reaching w/o pairs
---|---|---|---|---|---|---|---|---|---|---|---|---
be.digitalia.fosdem_2300230.apk.json | 434 | 0 | 7 | 9 | 0 | 178 | 61 | 0 | 0 | 0 | 888 | 0
com.beemdevelopment.aegis_81.apk.json | 364 | 0 | 14 | 15 | 8 | 64 | 21 | 62 | 62 | 62 | 1062 | 0
com.gelakinetic.mtgfam_99.apk.json | 32 | 0 | 1 | 1 | 0 | 85 | 0 | 0 | 0 | 0 | 61 | 0
com.github.gotify_35.apk.json | 40 | 0 | 6 | 7 | 1 | 45 | 8 | 1 | 1 | 1 | 223 | 8
com.iyps_158.apk.json | 103 | 0 | 3 | 3 | 2 | 97 | 30 | 110 | 32 | 110 | 280 | 0
com.kolktech.linxshare_22.apk.json | 1 | 0 | 0 | 0 | 0 | 49 | 0 | 0 | 0 | 0 | 2 | 0
com.manimarank.spell4wiki_21.apk.json | 7 | 0 | 6 | 6 | 2 | 92 | 1 | 3 | 2 | 3 | 47 | 0
com.ominous.quickweather_112.apk.json | 2 | 0 | 0 | 0 | 0 | 49 | 0 | 0 | 0 | 0 | 7 | 0
com.owncloud.android_48000100.apk.json | 1471 | 0 | 18 | 25 | 12 | 509 | 221 | 63 | 52 | 63 | 2969 | 0
com.quantum_prof.phantalandwaittimes_5.apk.json | 2 | 0 | 0 | 0 | 0 | 55 | 0 | 0 | 0 | 0 | 8 | 0
com.rtbishop.look4sat_410.apk.json | 1 | 0 | 0 | 0 | 0 | 325 | 0 | 0 | 0 | 0 | 4 | 0
com.tananaev.passportreader_22.apk.json | 11 | 0 | 5 | 6 | 1 | 2 | 2 | 3 | 3 | 3 | 18 | 0
com.vermont.possin_8.apk.json | 220 | 0 | 11 | 15 | 7 | 80 | 29 | 65 | 60 | 65 | 433 | 0
com.vrem.wifianalyzer_71.apk.json | 2 | 0 | 0 | 0 | 0 | 57 | 0 | 0 | 0 | 0 | 12 | 0
dev.spiegl.flyingcarpet_21.apk.json | 5 | 0 | 1 | 1 | 1 | 12 | 0 | 8 | 0 | 0 | 48 | 23
fr.corenting.traficparis_34.apk.json | 69 | 0 | 2 | 2 | 0 | 22 | 9 | 0 | 0 | 0 | 157 | 0
github.paroj.dsub2000_217.apk.json | 13 | 0 | 4 | 4 | 3 | 52 | 2 | 11 | 11 | 11 | 679 | 0
it.danieleverducci.nextcloudmaps_9.apk.json | 1 | 0 | 0 | 0 | 0 | 26 | 0 | 0 | 0 | 0 | 6 | 0
me.rosuh.easywatermark_21000.apk.json | 301 | 0 | 4 | 4 | 3 | 227 | 42 | 11 | 11 | 11 | 681 | 3
org.glpi.inventory.agent_39469.apk.json | 34 | 0 | 7 | 7 | 4 | 22 | 3 | 5 | 5 | 5 | 59 | 0
org.isoron.uhabits_20301.apk.json | 144 | 0 | 4 | 8 | 1 | 96 | 28 | 12 | 12 | 12 | 376 | 0
org.openhab.habdroid_589.apk.json | 499 | 0 | 18 | 19 | 13 | 109 | 41 | 15 | 15 | 15 | 1379 | 0
ua.com.radiokot.photoprism_67.apk.json | 964 | 0 | 21 | 21 | 4 | 1314 | 289 | 11 | 0 | 11 | 2378 | 0

documents: 23
documents with targets == 0: 0 []
INV-DRV-10 violations: 0
handlers: 3567, with dist: 787
flagged emitted widgets: 380, with a click pair: 266 (70.0%), with a pair on a flagged event: 372 (97.9%)
reaching methods: 11777, without targetDistances: 34
```

## Sample (sha256 of the copies)

```
8fd22f157a98b2e500648bb5239b0c6bbde9c896c37bde8fc6e6fa60c7049861  be.digitalia.fosdem_2300230.apk.json
7975a84e080076bb5abaf9b2485756b8485915c5165d3cdea93f8fcb3fe1e971  com.beemdevelopment.aegis_81.apk.json
076b99498d8572a143079ef09efe8707afbd47f637f801e191281101b06e0148  com.gelakinetic.mtgfam_99.apk.json
d1f03603f4d53b6d13cbbaf16e5e139ebf38c4812f8b34386c2f531870f9c379  com.github.gotify_35.apk.json
81e3fa4ea08ca07193660e51604a48fa26e6c00e535c5180fa3548b454387b86  com.iyps_158.apk.json
7a55aefb55b8ee16871aeeee3f88b4e944093a673660975bb1a3d6cc140b9dc9  com.kolktech.linxshare_22.apk.json
4e1c14578a5db7e5a4a169e49b27a59d67c0b9a42fe7b89aa3df0e67941d8975  com.manimarank.spell4wiki_21.apk.json
f6f31b1d8c51db2adba962fa5a42e5953888637501dfbac1a0d5b70ff197c134  com.ominous.quickweather_112.apk.json
ffd5738b07f62f359a5108ba7805b2cc5fef407ad01678072f5d68cd6b4d57fe  com.owncloud.android_48000100.apk.json
4f415c6bce2f133805af803dac5534d451ab6ab2c389edc357a07bbda7d003ba  com.quantum_prof.phantalandwaittimes_5.apk.json
56572dfb65f34eb6c503d066502fca605982f407c7847b4df0719590528b718d  com.rtbishop.look4sat_410.apk.json
0d973af09551a7c03b412c7ad315f5b03bf9580024232a5d7d9e11d80e7aa547  com.tananaev.passportreader_22.apk.json
600e03908c143f36365b14273efb262ae725fb34f82333f55243f05be76e80bb  com.vermont.possin_8.apk.json
e7273936b1040c96b99d574b14193b8c6e3b840a98498ff033acec801005047d  com.vrem.wifianalyzer_71.apk.json
54260ba8a3d1f84f2000c822aef998ee4f8c5624d79df4ed3ba5a7661caaf70f  dev.spiegl.flyingcarpet_21.apk.json
62cad47349e83b654c128fdb5f39b1efab945676fca8c2bd0a40de65bfc3dc79  fr.corenting.traficparis_34.apk.json
aafad46d0e11d4ddf19473d5596d1712ea1a785f31246dfde161c12a3cd87eda  github.paroj.dsub2000_217.apk.json
29c1f2a4df1552a275181f9602731cbf7d6188e9bb2783a3e3b5a254528fa1cd  it.danieleverducci.nextcloudmaps_9.apk.json
884ce8e8c80bbb772f4be4727177e56ea148d4a7a62c3fa3ff7590ce4825a252  me.rosuh.easywatermark_21000.apk.json
786416f7b5686bad74dbe6b313c6281b2dd1ebed4debe62d9755ee9a7c836922  org.glpi.inventory.agent_39469.apk.json
ae83e2acdad95a405fed44da68f1131ac25ecb8f3aebd0dda82dfdd8a15b0911  org.isoron.uhabits_20301.apk.json
7f65ec25d9e8a6334d7f3200878e83dc04dedcd6bcab2839dee95f453238cf5b  org.openhab.habdroid_589.apk.json
2cfcb37b2ee6273000abb8f44510a5334aafe69e330051393bebf3969d68db24  ua.com.radiokot.photoprism_67.apk.json
```

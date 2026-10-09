# gh122 tasks 5.1 and 7.6: real-data check on gh120 documents

- **Run:** 2026-10-09 (task 7.6), `uv run python -I real_data_check.py <dir>`. The derive is the working tree of this change after task 7.4: format 2 with the two cuts of design D9 (widget and handler lists keep every pair at `d <= 3`, `activityDist` the three nearest) and the streamed source read of design D10. The first run, on 2026-10-08 (task 5.1), used the three-pair cut on every list.
- **Source:** the Study 03 v2 static analysis, round A (Cloud Batch, gh120 GATOR). The documents are now flat files in
  `rvsec-study03-replication-package/data/raw/e6-static-analysis/final/<apk>.apk.json`.
- **Sample:** the same 23 documents as on 2026-10-08, every fourth of the 92 complete round-A documents by file size, from 83 KB to 55 MB (119 MB in all). The 700 MB `com.celzero.bravedns_619` is not in the sample.
  The files were copied to a scratch directory and derived from the copies. Nothing was written next to the originals.
  The sha256 of each copy matched the list at the end, so these are byte for byte the documents of the first run.

## Result

- `targets > 0` on all 23 documents.
- INV-DRV-10 holds on every pair list, 0 violations. On widget and handler lists every pair is at `d <= 3`; every `activityDist` list holds at most three pairs; every list is non-empty, sorted by `(d, i)`, with distinct indices below `targets`.
- The source-3 constructor exclusion shrinks `mopActivitiesAugmented` in 8 of the 23 apps; the per-app sizes are the "aug (excl)" and "aug (no excl)" columns. The widest gap is owncloud, 25 → 18. The cut does not touch these columns, which are the same as on 2026-10-08.
- `handlers`: 3,567 records, 675 of them carrying `dist` (18.9 %). With the three-pair cut, 787 did (22.1 %). The 112 records that lost their `dist` reach every target in four calls or more. They keep their `mop` flags, so a stamp still resolves to the class.
- Flagged emitted widgets: 380, as before.
  - 180 (47.4 %) carry a `click` pair, against 266 (70.0 %) with the three-pair cut.
  - 286 (75.3 %) carry a pair on at least one of their flagged events, against 372 (97.9 %).
- The 94 flagged widgets with no pair on a flagged event split into two groups:
  - 86 had a pair before. Their nearest target on every flagged event lies at `d >= 4`, a distance the jar gives no weight (`ape` D18), so the cut removes nothing the jar used. The flag still marks them as reaching.
  - 8 are in `dev.spiegl.flyingcarpet_21`, flagged on `click` with no pair, as on 2026-10-08. There the producer marks 23 of the 48 reaching methods `reachesTarget: true` with no `targetDistances`; one of them is the click wrapper `MainActivity$$ExternalSyntheticLambda10.onClick`.
- Over the whole sample, 34 of 11,777 reaching methods (0.3 %) carry no pairs. This is producer output, so the derive cannot give those methods a distance. The cause is the `DIST_MAX = 10` cut of gh120: those methods reach every target in more than 10 calls, which gives no weight under `distance` scoring either way. This 23-document sample has no affected Compose app and understates the case; `reach_without_distance.out.md` measures all 92 documents and gives the cause in full (design, Risks).

## Output

```
apk | targets | DRV-10 bad | aug (excl) | aug (no excl) | mopActivities | handlers | handlers w/ dist | flagged widgets | w/ click pair | w/ pair on a flagged event | reaching methods | reaching w/o pairs
---|---|---|---|---|---|---|---|---|---|---|---|---
be.digitalia.fosdem_2300230.apk.json | 434 | 0 | 7 | 9 | 0 | 178 | 58 | 0 | 0 | 0 | 888 | 0
com.beemdevelopment.aegis_81.apk.json | 364 | 0 | 14 | 15 | 8 | 64 | 12 | 62 | 43 | 43 | 1062 | 0
com.gelakinetic.mtgfam_99.apk.json | 32 | 0 | 1 | 1 | 0 | 85 | 0 | 0 | 0 | 0 | 61 | 0
com.github.gotify_35.apk.json | 40 | 0 | 6 | 7 | 1 | 45 | 1 | 1 | 0 | 0 | 223 | 8
com.iyps_158.apk.json | 103 | 0 | 3 | 3 | 2 | 97 | 30 | 110 | 32 | 110 | 280 | 0
com.kolktech.linxshare_22.apk.json | 1 | 0 | 0 | 0 | 0 | 49 | 0 | 0 | 0 | 0 | 2 | 0
com.manimarank.spell4wiki_21.apk.json | 7 | 0 | 6 | 6 | 2 | 92 | 0 | 3 | 0 | 1 | 47 | 0
com.ominous.quickweather_112.apk.json | 2 | 0 | 0 | 0 | 0 | 49 | 0 | 0 | 0 | 0 | 7 | 0
com.owncloud.android_48000100.apk.json | 1471 | 0 | 18 | 25 | 12 | 509 | 195 | 63 | 25 | 36 | 2969 | 0
com.quantum_prof.phantalandwaittimes_5.apk.json | 2 | 0 | 0 | 0 | 0 | 55 | 0 | 0 | 0 | 0 | 8 | 0
com.rtbishop.look4sat_410.apk.json | 1 | 0 | 0 | 0 | 0 | 325 | 0 | 0 | 0 | 0 | 4 | 0
com.tananaev.passportreader_22.apk.json | 11 | 0 | 5 | 6 | 1 | 2 | 2 | 3 | 3 | 3 | 18 | 0
com.vermont.possin_8.apk.json | 220 | 0 | 11 | 15 | 7 | 80 | 22 | 65 | 38 | 43 | 433 | 0
com.vrem.wifianalyzer_71.apk.json | 2 | 0 | 0 | 0 | 0 | 57 | 0 | 0 | 0 | 0 | 12 | 0
dev.spiegl.flyingcarpet_21.apk.json | 5 | 0 | 1 | 1 | 1 | 12 | 0 | 8 | 0 | 0 | 48 | 23
fr.corenting.traficparis_34.apk.json | 69 | 0 | 2 | 2 | 0 | 22 | 9 | 0 | 0 | 0 | 157 | 0
github.paroj.dsub2000_217.apk.json | 13 | 0 | 4 | 4 | 3 | 52 | 0 | 11 | 0 | 0 | 679 | 0
it.danieleverducci.nextcloudmaps_9.apk.json | 1 | 0 | 0 | 0 | 0 | 26 | 0 | 0 | 0 | 0 | 6 | 0
me.rosuh.easywatermark_21000.apk.json | 301 | 0 | 4 | 4 | 3 | 227 | 38 | 11 | 9 | 9 | 681 | 3
org.glpi.inventory.agent_39469.apk.json | 34 | 0 | 7 | 7 | 4 | 22 | 3 | 5 | 5 | 5 | 59 | 0
org.isoron.uhabits_20301.apk.json | 144 | 0 | 4 | 8 | 1 | 96 | 6 | 12 | 12 | 12 | 376 | 0
org.openhab.habdroid_589.apk.json | 499 | 0 | 18 | 19 | 13 | 109 | 28 | 15 | 13 | 13 | 1379 | 0
ua.com.radiokot.photoprism_67.apk.json | 964 | 0 | 21 | 21 | 4 | 1314 | 271 | 11 | 0 | 11 | 2378 | 0

documents: 23
documents with targets == 0: 0 []
INV-DRV-10 violations: 0
handlers: 3567, with dist: 675
flagged emitted widgets: 380, with a click pair: 180 (47.4%), with a pair on a flagged event: 286 (75.3%)
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

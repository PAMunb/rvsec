# gh122: reaching methods without a distance, all 92 round-A documents

- **Run:** 2026-10-08, `uv run python -I reach_without_distance.py <dir>` (25 s, 2.8 GB RSS), derive at `c7da2cec`.
- **Why:** follow-up to task 5.1, raised by the gh121 session. On parceltracker, 31.9 % of the app's stamp lines name Compose handlers that reach a target and carry no distance. The 23-document sample of 5.1 had no affected Compose app, so its 34 of 11,777 understated the case.
- **Source:** all 92 complete documents of round A, `rvsec-study03-replication-package/data/raw/e6-static-analysis/A/<apk>/<apk>.json`. They were copied to a scratch directory and derived from the copies; every sha256 matched its source.
- **Compose:** an app counts as Compose when a `reachability[]` signature takes an `androidx.compose.runtime.Composer` parameter.

## Result

| | Compose (21 apps) | View-only (71 apps) |
|---|---|---|
| apps with any reaching method lacking `targetDistances` | 8 | 15 |
| reaching methods without `targetDistances` | 4,935 / 15,621 (31.6 %) | 1,298 / 47,046 (2.8 %) |
| reaching handler methods (D4) without `targetDistances` | 686 / 1,314 (52.2 %) | 101 / 3,955 (2.6 %) |
| flagged emitted widgets with a flagged event lacking a pair | 0 / 0 | 91 / 15,414 (0.6 %) |

- **The Compose case is bimodal.** Where it hits, it hits most of the app's handlers: nerdcalci 299/328, stutter 76/77, canta 89/97, maskan.chat 124/148, untracker 29/37, parceltracker 25/39, mensinator 33/71, openbible 11/42. The other 13 Compose apps have a distance on all of their 475 reaching handler methods.
- In Compose apps no widget is flagged, because GATOR's window tree holds no Compose widget. The `handlers` table, read through a gh121 stamp, is the only route by which a Compose click gets a MOP weight, and that route is the one losing its distance.
- **View-only:** small, and concentrated in two apps: treehouses (67 of 71 handlers, 47 of 62 widgets) and keepalive (21/22, 31/31).
- **Cause: the `DIST_MAX = 10` cut of gh120, not a derive defect.** `reachesTarget` comes from an unbounded reverse search, and `targetDistances` from one reverse search per target cut at 10 calls, over the same call graph (`ReachabilityEngine`, `TargetDistances.java:50,176`). A reaching method with no pair is therefore one whose every target is more than 10 calls away. The minimum-distance histogram shows the cut, with the affected apps piling up at d = 9–10:

  | app | targets | reaching | no pair | d=7 | d=8 | d=9 | d=10 |
  |---|---|---|---|---|---|---|---|
  | nerdcalci (Compose) | 2 | 2,829 | 1,943 | 32 | 98 | 250 | 453 |
  | canta (Compose) | 1 | 1,167 | 1,041 | 2 | 3 | 12 | 90 |
  | stutter (Compose) | 1 | 660 | 533 | 2 | 12 | 24 | 80 |
  | parceltracker (Compose) | 28 | 952 | 187 | 198 | 101 | 101 | 103 |
  | aegis (View) | 364 | 1,062 | 0 | 5 | 1 | 0 | 0 |
  | fosdem (View) | 434 | 888 | 0 | 0 | 0 | 0 | 0 |

- **No decision of the jar changes.** Under `mop_scoring: distance` a target at d ≥ 4 gives no weight and the launcher counts d ≤ 6 only, so "no pair" and the exact distance (≥ 11) give the same score. What is lost is the difference between "farther than 10" and "unknown". In the 8 affected Compose apps the `mopd_*` arms give almost no click a MOP weight, while the flag arms give +300; the Study 03 analysis must read that contrast with this in mind.

## Output

```
apk | compose | reaching | reaching_np | handler_m | handler_m_np | handlers_flagged | handlers_flagged_np | widgets_flagged | widgets_flagged_np
---|---|---|---|---|---|---|---|---|---
app.maskan.chat_90.apk.json | yes | 1508 | 625 | 148 | 124 | 148 | 124 | 0 | 0
app.plugbrain.android_154.apk.json | yes | 130 | 0 | 7 | 0 | 7 | 0 | 0 | 0
be.digitalia.fosdem_2300230.apk.json | no | 888 | 0 | 61 | 0 | 61 | 0 | 0 | 0
ch.joshuah.bibleverseapp_8.apk.json | no | 44 | 19 | 0 | 0 | 0 | 0 | 0 | 0
co.epitre.aelf_lectures_86.apk.json | no | 62 | 0 | 0 | 0 | 0 | 0 | 0 | 0
com.absinthe.libchecker_2671.apk.json | no | 3152 | 0 | 204 | 0 | 204 | 0 | 62 | 0
com.afkanerd.deku_83.apk.json | yes | 1089 | 0 | 85 | 0 | 85 | 0 | 0 | 0
com.antony.muzei.pixiv_327.apk.json | no | 61 | 21 | 1 | 1 | 1 | 1 | 1 | 1
com.arslan.shizuwall_40.apk.json | no | 721 | 0 | 24 | 0 | 24 | 0 | 35 | 0
com.beemdevelopment.aegis_81.apk.json | no | 1062 | 0 | 21 | 0 | 21 | 0 | 62 | 0
com.celzero.bravedns_619.apk.json | no | 11584 | 0 | 1526 | 0 | 1526 | 0 | 14090 | 0
com.etesync.syncadapter_20700.apk.json | no | 302 | 15 | 7 | 4 | 7 | 4 | 4 | 4
com.faltenreich.diaguard_68.apk.json | no | 66 | 42 | 1 | 0 | 1 | 0 | 1 | 0
com.flauschcode.broccoli_1040400.apk.json | no | 55 | 0 | 0 | 0 | 0 | 0 | 0 | 0
com.floflacards.app_14.apk.json | yes | 2068 | 0 | 148 | 0 | 148 | 0 | 0 | 0
com.fredhappyface.ewesticker_20250217.apk.json | no | 67 | 23 | 6 | 6 | 6 | 6 | 1 | 0
com.gasperpintar.smokingtracker_12.apk.json | no | 419 | 0 | 50 | 0 | 50 | 0 | 49 | 0
com.gaurav.avnc_51.apk.json | no | 627 | 0 | 50 | 0 | 50 | 0 | 1 | 0
com.gelakinetic.mtgfam_99.apk.json | no | 61 | 0 | 0 | 0 | 0 | 0 | 0 | 0
com.github.cvzi.screenshottile_148.apk.json | no | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0
com.github.gotify_35.apk.json | no | 223 | 8 | 8 | 0 | 8 | 0 | 1 | 0
com.github.livingwithhippos.unchained_60.apk.json | no | 1882 | 0 | 209 | 0 | 209 | 0 | 29 | 0
com.hwloc.lstopo_80283.apk.json | no | 6 | 0 | 1 | 0 | 1 | 0 | 0 | 0
com.iyps_158.apk.json | no | 280 | 0 | 30 | 0 | 30 | 0 | 110 | 0
com.kolktech.linxshare_22.apk.json | yes | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0
com.kylecorry.trail_sense_145.apk.json | no | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0
com.luk.saucenao_27.apk.json | yes | 364 | 0 | 35 | 0 | 35 | 0 | 0 | 0
com.manimarank.spell4wiki_21.apk.json | no | 47 | 0 | 1 | 0 | 1 | 0 | 3 | 0
com.mateusrodcosta.apps.share2storage_34.apk.json | yes | 425 | 0 | 14 | 0 | 14 | 0 | 0 | 0
com.mensinator.app_24.apk.json | yes | 1105 | 239 | 71 | 33 | 71 | 33 | 0 | 0
com.micoyc.speakthat_58.apk.json | no | 2521 | 0 | 166 | 0 | 166 | 0 | 272 | 0
com.ominous.quickweather_112.apk.json | no | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0
com.owncloud.android_48000100.apk.json | no | 2969 | 0 | 221 | 0 | 221 | 0 | 63 | 0
com.password.monitor_102.apk.json | no | 182 | 0 | 24 | 0 | 24 | 0 | 53 | 0
com.quantum_prof.phantalandwaittimes_5.apk.json | yes | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0
com.rastislavkish.vscan_24.apk.json | no | 483 | 0 | 13 | 0 | 13 | 0 | 24 | 0
com.rtbishop.look4sat_410.apk.json | yes | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0
com.schwegelbin.openbible_46.apk.json | yes | 492 | 171 | 42 | 11 | 42 | 11 | 0 | 0
com.serwylo.beatgame_35.apk.json | no | 271 | 0 | 17 | 0 | 17 | 0 | 0 | 0
com.serwylo.retrowars_70.apk.json | no | 641 | 0 | 41 | 0 | 41 | 0 | 0 | 0
com.shatteredpixel.shatteredpixeldungeon_896.apk.json | no | 1883 | 428 | 0 | 0 | 0 | 0 | 0 | 0
com.smartpack.packagemanager_79.apk.json | no | 104 | 0 | 10 | 0 | 10 | 0 | 14 | 0
com.surfaceocean.nexttraceroute_16.apk.json | yes | 545 | 0 | 74 | 0 | 74 | 0 | 0 | 0
com.tananaev.passportreader_22.apk.json | no | 18 | 0 | 2 | 0 | 2 | 0 | 3 | 0
com.trianguloy.urlchecker_47.apk.json | no | 18 | 0 | 1 | 0 | 1 | 0 | 0 | 0
com.vermont.possin_8.apk.json | no | 433 | 0 | 29 | 0 | 29 | 0 | 65 | 0
com.vishaltelangre.nerdcalci_490.apk.json | yes | 2829 | 1943 | 328 | 299 | 328 | 299 | 0 | 0
com.vrem.wifianalyzer_71.apk.json | no | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0
de.luhmer.owncloudnewsreader_196.apk.json | no | 93 | 0 | 0 | 0 | 0 | 0 | 0 | 0
de.markusfisch.android.binaryeye_174.apk.json | no | 462 | 0 | 27 | 0 | 27 | 0 | 38 | 0
de.markusfisch.android.shadereditor_93.apk.json | no | 88 | 0 | 3 | 0 | 3 | 0 | 8 | 0
de.stephanlindauer.criticalmaps_104.apk.json | no | 72 | 0 | 1 | 0 | 1 | 0 | 2 | 0
dev.itsvic.parceltracker_10501000.apk.json | yes | 952 | 187 | 39 | 25 | 39 | 25 | 0 | 0
dev.patri9ck.a2ln_25.apk.json | no | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0
dev.sebaubuntu.athena_17.apk.json | yes | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0
dev.spiegl.flyingcarpet_21.apk.json | no | 48 | 23 | 1 | 1 | 1 | 1 | 8 | 8
dev.ukanth.ufirewall_20260301.apk.json | no | 27 | 0 | 0 | 0 | 0 | 0 | 0 | 0
eu.opencloud.android_9.apk.json | no | 3263 | 0 | 221 | 0 | 221 | 0 | 49 | 0
fr.corenting.traficparis_34.apk.json | yes | 157 | 0 | 9 | 0 | 9 | 0 | 0 | 0
github.paroj.dsub2000_217.apk.json | no | 679 | 0 | 2 | 0 | 2 | 0 | 11 | 0
io.github.jd1378.otphelper_52000.apk.json | yes | 1532 | 0 | 100 | 0 | 100 | 0 | 0 | 0
io.github.samolego.canta_225.apk.json | yes | 1167 | 1041 | 97 | 89 | 97 | 89 | 0 | 0
io.keepalive.android_133.apk.json | no | 248 | 218 | 22 | 21 | 22 | 21 | 31 | 31
io.treehouses.remote_6098.apk.json | no | 537 | 461 | 71 | 67 | 71 | 67 | 62 | 47
it.danieleverducci.nextcloudmaps_9.apk.json | no | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0
jwtc.android.chess_283.apk.json | no | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0
me.hackerchick.sharetoinputstick_26.apk.json | no | 16 | 0 | 0 | 0 | 0 | 0 | 2 | 0
me.rosuh.easywatermark_21000.apk.json | no | 681 | 3 | 43 | 1 | 43 | 1 | 11 | 0
me.testcase.ognarviewer_25.apk.json | no | 33 | 0 | 2 | 0 | 2 | 0 | 0 | 0
me.timschneeberger.rootlessjamesdsp_51.apk.json | no | 1091 | 3 | 125 | 0 | 125 | 0 | 19 | 0
me.zhanghai.android.untracker_9.apk.json | yes | 535 | 196 | 37 | 29 | 37 | 29 | 0 | 0
net.adhikary.mrtbuddy_24.apk.json | yes | 46 | 0 | 3 | 0 | 3 | 0 | 0 | 0
net.christianbeier.droidvnc_ng_60.apk.json | no | 23 | 0 | 1 | 0 | 1 | 0 | 0 | 0
net.gaast.giggity_769.apk.json | no | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0
net.osmtracker_73.apk.json | no | 12 | 0 | 1 | 0 | 1 | 0 | 0 | 0
org.cry.otp_31.apk.json | no | 13 | 0 | 3 | 0 | 3 | 0 | 3 | 0
org.fedorahosted.freeotp_48.apk.json | no | 38 | 0 | 1 | 0 | 1 | 0 | 3 | 0
org.glpi.inventory.agent_39469.apk.json | no | 59 | 0 | 3 | 0 | 3 | 0 | 5 | 0
org.hwyl.sexytopo_93.apk.json | no | 299 | 21 | 6 | 0 | 6 | 0 | 16 | 0
org.isoron.uhabits_20301.apk.json | no | 376 | 0 | 28 | 0 | 28 | 0 | 12 | 0
org.liberty.android.fantastischmemo_241.apk.json | no | 58 | 0 | 0 | 0 | 0 | 0 | 0 | 0
org.musicbrainz.picard.barcodescanner_38.apk.json | no | 62 | 11 | 4 | 0 | 4 | 0 | 6 | 0
org.openhab.habdroid_589.apk.json | no | 1379 | 0 | 42 | 0 | 41 | 0 | 15 | 0
org.piepmeyer.gauguin_75.apk.json | no | 1207 | 0 | 175 | 0 | 175 | 0 | 78 | 0
org.prauga.messages_8.apk.json | no | 1917 | 2 | 132 | 0 | 132 | 0 | 49 | 0
org.tomasino.stutter_29.apk.json | yes | 660 | 533 | 77 | 76 | 77 | 76 | 0 | 0
se.arctosoft.vault_41.apk.json | no | 451 | 0 | 13 | 0 | 13 | 0 | 15 | 0
swati4star.createpdf_110.apk.json | no | 238 | 0 | 13 | 0 | 13 | 0 | 11 | 0
systems.sieber.droid_scep_7.apk.json | no | 19 | 0 | 2 | 0 | 2 | 0 | 6 | 0
ua.com.radiokot.lnaddr2invoice_8.apk.json | no | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0
ua.com.radiokot.photoprism_67.apk.json | no | 2378 | 0 | 289 | 0 | 289 | 0 | 11 | 0
uk.org.ngo.squeezer_158.apk.json | no | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0

Compose: 21 apps, 8 with any reaching method lacking pairs
  reaching methods without targetDistances: 4935/15621 (31.6%)
  reaching handler methods without targetDistances: 686/1314 (52.2%)
  flagged handler records with a flagged event lacking a pair: 686/1314 (52.2%)
  flagged emitted widgets with a flagged event lacking a pair: 0/0
View-only: 71 apps, 15 with any reaching method lacking pairs
  reaching methods without targetDistances: 1298/47046 (2.8%)
  reaching handler methods without targetDistances: 101/3955 (2.6%)
  flagged handler records with a flagged event lacking a pair: 101/3954 (2.6%)
  flagged emitted widgets with a flagged event lacking a pair: 91/15414 (0.6%)
```

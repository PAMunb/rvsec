# Batch L1_okhttp_conscrypt: NOBS sites to read

## okhttp3.internal.platform.Platform.platformTrustManager
- NOBS lines: 7909; APKs (54): app.eduroam.geteduroam_2685.apk, app.maskan.chat_90.apk, app.michaelwuensch.bitbanana_79.apk, app.pachli_50.apk, be.digitalia.fosdem_2300230.apk, cc.sovellus.vrcaa_300007.apk, ch.joshuah.bibleverseapp_8.apk, ch.rmy.android.http_shortcuts_1104060001.apk, co.epitre.aelf_lectures_86.apk, com.absinthe.libchecker_2671.apk, com.antony.muzei.pixiv_327.apk, com.celzero.bravedns_619.apk, com.craxiom.networksurvey_114.apk, com.daniebeler.pfpixelix_40.apk, com.etesync.syncadapter_20700.apk, com.flxrs.dankchat_40038.apk, com.github.livingwithhippos.unchained_60.apk, com.ivanovsky.passnotes_11700.apk, com.jerboa_87.apk, com.manimarank.spell4wiki_21.apk, com.matedroid_178120864.apk, com.micoyc.speakthat_58.apk, com.ominous.quickweather_112.apk, com.password.monitor_102.apk, com.quantum_prof.phantalandwaittimes_5.apk, com.rtbishop.look4sat_410.apk, com.sakethh.linkora_50.apk, com.starry.myne_500.apk, com.vermont.possin_8.apk, de.lukasneugebauer.nextcloudcookbook_62.apk, de.stephanlindauer.criticalmaps_104.apk, dev.dettmer.simplenotes_41.apk, dev.itsvic.parceltracker_10501000.apk, dev.sebaubuntu.athena_17.apk, eu.darken.sdmse_10705000.apk, fr.corenting.traficparis_34.apk, io.github.garemat.lunachron_23201.apk, io.treehouses.remote_6098.apk, jwtc.android.chess_283.apk, me.mudkip.moememos_48.apk, me.timschneeberger.rootlessjamesdsp_51.apk, net.pfiers.osmfocus_1009013.apk, net.phbwt.paperwork_1003007.apk, org.jellyfin.mobile_2060499.apk, org.liberty.android.fantastischmemo_241.apk, org.musicbrainz.picard.barcodescanner_38.apk, org.nqmgaming.aneko_34.apk, org.openhab.habdroid_589.apk, org.quantumbadger.redreader_117.apk, org.tomasino.stutter_29.apk, org.totschnig.myexpenses_858.apk, org.wikipedia_50595.apk, ua.com.radiokot.lnaddr2invoice_8.apk, ua.com.radiokot.photoprism_67.apk
- **TRUSTMANAGERFACTORY-NOBS-00** (spec `TrustManagerFactorySpec`, event `init`), lines 7909, source lines {'Platform.kt:80': np.int64(4127), 'Platform.kt:83': np.int64(3577), 'Platform.kt:84': np.int64(124), 'Platform.kt:85': np.int64(81)}
  - expects: a KeyStore this instrumentation observed being loaded
  - msg: no loading of the KeyStore given to TrustManagerFactory.init was observed
  - observed val(s): ['PKIX']

## okhttp3.internal.platform.Platform.newSslSocketFactory
- NOBS lines: 21875; APKs (52): app.eduroam.geteduroam_2685.apk, app.maskan.chat_90.apk, app.michaelwuensch.bitbanana_79.apk, app.pachli_50.apk, be.digitalia.fosdem_2300230.apk, cc.sovellus.vrcaa_300007.apk, ch.joshuah.bibleverseapp_8.apk, ch.rmy.android.http_shortcuts_1104060001.apk, com.absinthe.libchecker_2671.apk, com.antony.muzei.pixiv_327.apk, com.celzero.bravedns_619.apk, com.craxiom.networksurvey_114.apk, com.daniebeler.pfpixelix_40.apk, com.etesync.syncadapter_20700.apk, com.flxrs.dankchat_40038.apk, com.github.livingwithhippos.unchained_60.apk, com.ivanovsky.passnotes_11700.apk, com.jerboa_87.apk, com.manimarank.spell4wiki_21.apk, com.matedroid_178120864.apk, com.micoyc.speakthat_58.apk, com.ominous.quickweather_112.apk, com.password.monitor_102.apk, com.quantum_prof.phantalandwaittimes_5.apk, com.rtbishop.look4sat_410.apk, com.sakethh.linkora_50.apk, com.starry.myne_500.apk, com.vermont.possin_8.apk, de.lukasneugebauer.nextcloudcookbook_62.apk, de.stephanlindauer.criticalmaps_104.apk, dev.dettmer.simplenotes_41.apk, dev.itsvic.parceltracker_10501000.apk, dev.sebaubuntu.athena_17.apk, eu.darken.sdmse_10705000.apk, fr.corenting.traficparis_34.apk, io.github.garemat.lunachron_23201.apk, io.treehouses.remote_6098.apk, jwtc.android.chess_283.apk, me.mudkip.moememos_48.apk, me.timschneeberger.rootlessjamesdsp_51.apk, net.pfiers.osmfocus_1009013.apk, org.jellyfin.mobile_2060499.apk, org.liberty.android.fantastischmemo_241.apk, org.musicbrainz.picard.barcodescanner_38.apk, org.nqmgaming.aneko_34.apk, org.openhab.habdroid_589.apk, org.quantumbadger.redreader_117.apk, org.tomasino.stutter_29.apk, org.totschnig.myexpenses_858.apk, org.wikipedia_50595.apk, ua.com.radiokot.lnaddr2invoice_8.apk, ua.com.radiokot.photoprism_67.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 7291, source lines {'Platform.kt:168': np.int64(3631), 'Platform.kt:194': np.int64(2320), 'Platform.kt:197': np.int64(1116), 'Platform.kt:180': np.int64(124)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 7293, source lines {'Platform.kt:168': np.int64(3632), 'Platform.kt:194': np.int64(2320), 'Platform.kt:197': np.int64(1117), 'Platform.kt:180': np.int64(124)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-02** (spec `SSLContextSpec`, event `init`), lines 7291, source lines {'Platform.kt:168': np.int64(3631), 'Platform.kt:194': np.int64(2319), 'Platform.kt:197': np.int64(1117), 'Platform.kt:180': np.int64(124)}
  - expects: a SecureRandom this instrumentation observed being created
  - msg: the SecureRandom given to SSLContext.init was not observed coming from a randomized source
  - observed val(s): ['TLS']

## org.conscrypt.SSLParametersImpl.createDefaultX509KeyManager
- NOBS lines: 278; APKs (3): app.pachli_50.apk, ch.rmy.android.http_shortcuts_1104060001.apk, com.etesync.syncadapter_20700.apk
- **KEYMANAGERFACTORY-NOBS-00** (spec `KeyManagerFactorySpec`, event `init`), lines 278, source lines {'SSLParametersImpl.java:536': np.int64(278)}
  - expects: a KeyStore this instrumentation observed being loaded
  - msg: no loading of the KeyStore given to KeyManagerFactory.init was observed
  - observed val(s): ['PKIX']

## org.conscrypt.SSLParametersImpl.createDefaultX509TrustManager
- NOBS lines: 30; APKs (2): ch.rmy.android.http_shortcuts_1104060001.apk, com.etesync.syncadapter_20700.apk
- **TRUSTMANAGERFACTORY-NOBS-00** (spec `TrustManagerFactorySpec`, event `init`), lines 30, source lines {'SSLParametersImpl.java:606': np.int64(30)}
  - expects: a KeyStore this instrumentation observed being loaded
  - msg: no loading of the KeyStore given to TrustManagerFactory.init was observed
  - observed val(s): ['PKIX']

## okhttp3.tls.HandshakeCertificates.sslContext
- NOBS lines: 1266; APKs (2): co.epitre.aelf_lectures_86.apk, net.phbwt.paperwork_1003007.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 633, source lines {'HandshakeCertificates.kt:94': np.int64(486), 'HandshakeCertificates.kt:97': np.int64(147)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 633, source lines {'HandshakeCertificates.kt:94': np.int64(486), 'HandshakeCertificates.kt:97': np.int64(147)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']

## okhttp3.internal.Util.platformTrustManager
- NOBS lines: 323; APKs (2): com.cointrend_10304.apk, com.faltenreich.diaguard_68.apk
- **TRUSTMANAGERFACTORY-NOBS-00** (spec `TrustManagerFactorySpec`, event `init`), lines 323, source lines {'Util.java:640': np.int64(323)}
  - expects: a KeyStore this instrumentation observed being loaded
  - msg: no loading of the KeyStore given to TrustManagerFactory.init was observed
  - observed val(s): ['PKIX']

## okhttp3.OkHttpClient.newSslSocketFactory
- NOBS lines: 969; APKs (2): com.cointrend_10304.apk, com.faltenreich.diaguard_68.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 323, source lines {'OkHttpClient.java:264': np.int64(323)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 323, source lines {'OkHttpClient.java:264': np.int64(323)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-02** (spec `SSLContextSpec`, event `init`), lines 323, source lines {'OkHttpClient.java:264': np.int64(323)}
  - expects: a SecureRandom this instrumentation observed being created
  - msg: the SecureRandom given to SSLContext.init was not observed coming from a randomized source
  - observed val(s): ['TLS']

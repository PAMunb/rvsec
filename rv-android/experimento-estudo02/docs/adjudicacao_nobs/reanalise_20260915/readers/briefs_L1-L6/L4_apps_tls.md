# Batch L4_apps_tls: NOBS sites to read

## ch.rmy.android.http_shortcuts.http.HttpClientFactory.configureTLS
- NOBS lines: 72; APKs (1): ch.rmy.android.http_shortcuts_1104060001.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 24, source lines {'HttpClientFactory.kt:211': np.int64(24)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 24, source lines {'HttpClientFactory.kt:211': np.int64(24)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-02** (spec `SSLContextSpec`, event `init`), lines 24, source lines {'HttpClientFactory.kt:211': np.int64(24)}
  - expects: a SecureRandom this instrumentation observed being created
  - msg: the SecureRandom given to SSLContext.init was not observed coming from a randomized source
  - observed val(s): ['TLS']

## at.bitfire.cert4android.CertUtils.getTrustManager
- NOBS lines: 6; APKs (1): com.etesync.syncadapter_20700.apk
- **TRUSTMANAGERFACTORY-NOBS-00** (spec `TrustManagerFactorySpec`, event `init`), lines 6, source lines {'CertUtils.kt:22': np.int64(6)}
  - expects: a KeyStore this instrumentation observed being loaded
  - msg: no loading of the KeyStore given to TrustManagerFactory.init was observed
  - observed val(s): ['X509']

## com.etesync.syncadapter.HttpClient$Builder.build
- NOBS lines: 18; APKs (1): com.etesync.syncadapter_20700.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 6, source lines {'HttpClient.kt:233': np.int64(6)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 6, source lines {'HttpClient.kt:233': np.int64(6)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-02** (spec `SSLContextSpec`, event `init`), lines 6, source lines {'HttpClient.kt:233': np.int64(6)}
  - expects: a SecureRandom this instrumentation observed being created
  - msg: the SecureRandom given to SSLContext.init was not observed coming from a randomized source
  - observed val(s): ['TLS']

## com.nononsenseapps.jsonfeed.OkHttpBuilderExtensionsKt.trustAllCerts
- NOBS lines: 429; APKs (1): com.nononsenseapps.feeder.play_4025.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 143, source lines {'OkHttpBuilderExtensions.kt:32': np.int64(143)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 143, source lines {'OkHttpBuilderExtensions.kt:32': np.int64(143)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-02** (spec `SSLContextSpec`, event `init`), lines 143, source lines {'OkHttpBuilderExtensions.kt:32': np.int64(143)}
  - expects: a SecureRandom this instrumentation observed being created
  - msg: the SecureRandom given to SSLContext.init was not observed coming from a randomized source
  - observed val(s): ['TLS']

## eu.opencloud.android.lib.common.network.AdvancedX509TrustManager.<init>
- NOBS lines: 32; APKs (1): eu.opencloud.android_9.apk
- **TRUSTMANAGERFACTORY-NOBS-00** (spec `TrustManagerFactorySpec`, event `init`), lines 32, source lines {'AdvancedX509TrustManager.java:57': np.int64(32)}
  - expects: a KeyStore this instrumentation observed being loaded
  - msg: no loading of the KeyStore given to TrustManagerFactory.init was observed
  - observed val(s): ['PKIX']

## eu.opencloud.android.lib.common.http.HttpClient.getOkHttpClient
- NOBS lines: 96; APKs (1): eu.opencloud.android_9.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 32, source lines {'HttpClient.java:79': np.int64(32)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLSv1.3']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 32, source lines {'HttpClient.java:79': np.int64(32)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLSv1.3']
- **SSLCONTEXT-NOBS-02** (spec `SSLContextSpec`, event `init`), lines 32, source lines {'HttpClient.java:79': np.int64(32)}
  - expects: a SecureRandom this instrumentation observed being created
  - msg: the SecureRandom given to SSLContext.init was not observed coming from a randomized source
  - observed val(s): ['TLSv1.3']

## com.owncloud.android.lib.common.network.AdvancedX509TrustManager.<init>
- NOBS lines: 24; APKs (1): com.owncloud.android_48000100.apk
- **TRUSTMANAGERFACTORY-NOBS-00** (spec `TrustManagerFactorySpec`, event `init`), lines 24, source lines {'AdvancedX509TrustManager.java:59': np.int64(24)}
  - expects: a KeyStore this instrumentation observed being loaded
  - msg: no loading of the KeyStore given to TrustManagerFactory.init was observed
  - observed val(s): ['PKIX']

## com.owncloud.android.lib.common.http.HttpClient.getOkHttpClient
- NOBS lines: 72; APKs (1): com.owncloud.android_48000100.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 24, source lines {'HttpClient.java:81': np.int64(24)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLSv1.3']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 24, source lines {'HttpClient.java:81': np.int64(24)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLSv1.3']
- **SSLCONTEXT-NOBS-02** (spec `SSLContextSpec`, event `init`), lines 24, source lines {'HttpClient.java:81': np.int64(24)}
  - expects: a SecureRandom this instrumentation observed being created
  - msg: the SecureRandom given to SSLContext.init was not observed coming from a randomized source
  - observed val(s): ['TLSv1.3']

## net.osmtracker.layout.TLSSocketFactory.<init>
- NOBS lines: 9; APKs (1): net.osmtracker_73.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 3, source lines {'TLSSocketFactory.java:23': np.int64(3)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 3, source lines {'TLSSocketFactory.java:23': np.int64(3)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-02** (spec `SSLContextSpec`, event `init`), lines 3, source lines {'TLSSocketFactory.java:23': np.int64(3)}
  - expects: a SecureRandom this instrumentation observed being created
  - msg: the SecureRandom given to SSLContext.init was not observed coming from a randomized source
  - observed val(s): ['TLS']

## github.paroj.dsub2000.service.RESTMusicService.<init>
- NOBS lines: 605; APKs (1): github.paroj.dsub2000_217.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 303, source lines {'RESTMusicService.java:138': np.int64(303)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 302, source lines {'RESTMusicService.java:138': np.int64(302)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']

## com.ivanovsky.passnotes.data.repository.file.webdav.HttpClientFactory.createHttpClient
- NOBS lines: 2; APKs (1): com.ivanovsky.passnotes_11700.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 1, source lines {'HttpClientFactory.kt:38': np.int64(1)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 1, source lines {'HttpClientFactory.kt:38': np.int64(1)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']

## com.matedroid.di.TeslamateApiFactory.configureInsecureTls
- NOBS lines: 2; APKs (1): com.matedroid_178120864.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 1, source lines {'NetworkModule.kt:216': np.int64(1)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 1, source lines {'NetworkModule.kt:216': np.int64(1)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']

## de.luhmer.owncloudnewsreader.ssl.MemorizingTrustManager.getTrustManager
- NOBS lines: 194; APKs (1): de.luhmer.owncloudnewsreader_196.apk
- **TRUSTMANAGERFACTORY-NOBS-00** (spec `TrustManagerFactorySpec`, event `init`), lines 194, source lines {'MemorizingTrustManager.java:282': np.int64(194)}
  - expects: a KeyStore this instrumentation observed being loaded
  - msg: no loading of the KeyStore given to TrustManagerFactory.init was observed
  - observed val(s): ['X509']

## de.duenndns.ssl.MemorizingTrustManager.getTrustManager
- NOBS lines: 214; APKs (1): org.openhab.habdroid_589.apk
- **TRUSTMANAGERFACTORY-NOBS-00** (spec `TrustManagerFactorySpec`, event `init`), lines 214, source lines {'MemorizingTrustManager.java:310': np.int64(214)}
  - expects: a KeyStore this instrumentation observed being loaded
  - msg: no loading of the KeyStore given to TrustManagerFactory.init was observed
  - observed val(s): ['X509']

## org.openhab.habdroid.core.connection.ConnectionFactory.updateHttpClientForClientCert
- NOBS lines: 605; APKs (1): org.openhab.habdroid_589.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 200, source lines {'ConnectionFactory.kt:324': np.int64(200)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 202, source lines {'ConnectionFactory.kt:324': np.int64(202)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-02** (spec `SSLContextSpec`, event `init`), lines 203, source lines {'ConnectionFactory.kt:324': np.int64(203)}
  - expects: a SecureRandom this instrumentation observed being created
  - msg: the SecureRandom given to SSLContext.init was not observed coming from a randomized source
  - observed val(s): ['TLS']

## org.openhab.habdroid.core.connection.ConnectionFactory.<init>
- NOBS lines: 642; APKs (1): org.openhab.habdroid_589.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 214, source lines {'ConnectionFactory.kt:172': np.int64(214)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 214, source lines {'ConnectionFactory.kt:172': np.int64(214)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['TLS']
- **SSLCONTEXT-NOBS-02** (spec `SSLContextSpec`, event `init`), lines 214, source lines {'ConnectionFactory.kt:172': np.int64(214)}
  - expects: a SecureRandom this instrumentation observed being created
  - msg: the SecureRandom given to SSLContext.init was not observed coming from a randomized source
  - observed val(s): ['TLS']

## de.lukasneugebauer.nextcloudcookbook.core.util.OkHttpClientProvider.configureTrustAllCertificates
- NOBS lines: 192; APKs (1): de.lukasneugebauer.nextcloudcookbook_62.apk
- **SSLCONTEXT-NOBS-00** (spec `SSLContextSpec`, event `init`), lines 96, source lines {'OkHttpClientProvider.kt:74': np.int64(96)}
  - expects: a KeyManager[] an observed KeyManagerFactory returned
  - msg: the KeyManager[] given to SSLContext.init was not observed coming from a KeyManagerFactory
  - observed val(s): ['SSL']
- **SSLCONTEXT-NOBS-01** (spec `SSLContextSpec`, event `init`), lines 96, source lines {'OkHttpClientProvider.kt:74': np.int64(96)}
  - expects: a TrustManager[] an observed TrustManagerFactory returned
  - msg: the TrustManager[] given to SSLContext.init was not observed coming from a TrustManagerFactory
  - observed val(s): ['SSL']

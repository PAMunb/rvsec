# Dossiê G1: okhttp (Platform, OkHttpClient 3.x, okhttp-tls) e Conscrypt empacotado

| id | classe.método | código | categoria | mecanismo | confiança |
|---|---|---|---|---|---|
| 13 | OkHttpClient.newSslSocketFactory (3.14.9) | SSLCONTEXT-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_keymanager | alta |
| 13 | idem | SSLCONTEXT-NOBS-01 | LEGIT_UNOBSERVABLE | copy_loses_identity | alta |
| 13 | idem | SSLCONTEXT-NOBS-02 | LEGIT_UNOBSERVABLE | null_default_securerandom | alta |
| 14 | internal.Util.platformTrustManager (3.14.9) | TRUSTMANAGERFACTORY-NOBS-00 | LEGIT_UNOBSERVABLE | null_default_truststore | alta |
| 15 | internal.platform.Platform.newSslSocketFactory | SSLCONTEXT-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_keymanager | alta |
| 15 | idem | SSLCONTEXT-NOBS-01 | LEGIT_UNOBSERVABLE | copy_loses_identity | alta |
| 15 | idem | SSLCONTEXT-NOBS-02 | LEGIT_UNOBSERVABLE | null_default_securerandom | alta |
| 16 | internal.platform.Platform.platformTrustManager | TRUSTMANAGERFACTORY-NOBS-00 | LEGIT_UNOBSERVABLE | null_default_truststore | alta |
| 17 | tls.HandshakeCertificates.sslContext | SSLCONTEXT-NOBS-00 | LEGIT_UNOBSERVABLE | copy_loses_identity | alta |
| 17 | idem | SSLCONTEXT-NOBS-01 | LEGIT_UNOBSERVABLE | copy_loses_identity | média |
| 60 | org.conscrypt.SSLParametersImpl.createDefaultX509KeyManager | KEYMANAGERFACTORY-NOBS-00 | LEGIT_UNOBSERVABLE | null_default_keystore | alta |
| 61 | org.conscrypt.SSLParametersImpl.createDefaultX509TrustManager | TRUSTMANAGERFACTORY-NOBS-00 | LEGIT_UNOBSERVABLE | null_default_truststore | alta |

Resultado: 12 sites, todos LEGIT_UNOBSERVABLE. Nenhum MISUSE, nenhum SPEC_DEFECT, nenhum UNDETERMINED.
Todas as fontes estão em `$SP/src/`.

## Leituras e produtores (comum a todos os sites)

- `SSLContextSpec.mop:214-248`, evento `init`, lê três predicados, cada um com `validate` sobre o
  argumento vinculado: `GENERATED_KEY_MANAGERS` sobre `kms` (:222, NOBS-00),
  `GENERATED_TRUST_MANAGER` sobre `tms` (:231, NOBS-01) e `RANDOMIZED` sobre `random` (:240, NOBS-02).
  Com `null` o store responde NOT_OBSERVED (`PredicateStore.java:343-345`). O próprio `.mop`
  registra essa decisão em :176-208.
- Produtores. `KeyManagerFactorySpec.gkm1` (:173-176) e `TrustManagerFactorySpec.gtm1` (:215-218)
  fazem `ensure` **no corpo do evento, sobre o array que `getKeyManagers()`/`getTrustManagers()`
  retornou**. O ensure não depende de veredito: o gerador do RV-Monitor emite a ação do evento
  antes da transição (`rv-monitor BaseMonitor.java:538-551`), então ele roda mesmo quando o
  autômato falha. Por isso nenhuma NOBS-01 deste grupo é cascata de TRUSTMANAGERFACTORY-NOBS-00.
  O terceiro produtor é `SecureRandomSpec.mop:384`.
- `TrustManagerFactorySpec.mop:146-155` e `KeyManagerFactorySpec.mop:121-130` leem
  `GENERATED_KEY_STORE` sobre o argumento `KeyStore`. Esse predicado tem um único produtor,
  `KeyStoreSpec.mop:196`.

## Versões do okhttp (por assinatura de linhas `__LOC`)

As linhas registradas foram conferidas contra os `-sources.jar`:

| newSslSocketFactory | platformTrustManager (init) | versão | APKs |
|---|---|---|---|
| OkHttpClient.java:264 | Util.java:640 | 3.14.9 (via retrofit) | com.cointrend, com.faltenreich.diaguard |
| Platform.kt:160 | :80 | 4.8.x (etesync declara 4.8.1) | etesync, dettmer.simplenotes, rootlessjamesdsp |
| Platform.kt:168 | :80 | 4.9.x–4.12.0 (layout idêntico) | 24 APKs (geteduroam 4.12.0 etc.) |
| Platform.kt:180 | :84 | 5.0.0-alpha.12 (okhttp-jvm) | com.antony.muzei.pixiv |
| Platform.kt:191 | :85 | 5.0.0-alpha.14 | dev.itsvic.parceltracker |
| Platform.kt:194 | :83 | 5.3.2 | 19 APKs (fosdem, wikipedia, pachli, http_shortcuts…) |
| Platform.kt:197 | :83 | 5.4.0 | libchecker, dankchat, look4sat, criticalmaps |
| (sem) HandshakeCertificates.kt:94 | :80 | 4.12.0 + okhttp-tls 4.12.0 | co.epitre.aelf_lectures |
| (sem) HandshakeCertificates.kt:97 | :83 | 5.3.2 + okhttp-tls 5.3.2 | net.phbwt.paperwork |

O código nas duas chamadas é o mesmo em todas as versões, só a formatação muda:
`init(null, arrayOf<TrustManager>(trustManager), null)` e `factory.init(null as KeyStore?)`.
Para 5.3.2, os `Platform.kt` de `okhttp`, `okhttp-android` e `okhttp-jvm` têm o mesmo md5.

## id 15/16: Platform.newSslSocketFactory e Platform.platformTrustManager

```kotlin
// okhttp-5.3.2/commonJvmAndroid/okhttp3/internal/platform/Platform.kt:78-88
open fun platformTrustManager(): X509TrustManager {
  val factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm())
  factory.init(null as KeyStore?)                       // :83  TRUSTMANAGERFACTORY-NOBS-00
  val trustManagers = factory.trustManagers!!           // :84  gtm1 garante GENERATED_TRUST_MANAGER neste array
  ...
  return trustManagers[0] as X509TrustManager
}
// :190-194
open fun newSslSocketFactory(trustManager: X509TrustManager): SSLSocketFactory {
  return newSSLContext().apply {
      init(null, arrayOf<TrustManager>(trustManager), null)  // :194  NOBS-00/-01/-02
  }.socketFactory
```

Rastreando para trás: o único chamador de `Platform.newSslSocketFactory`, no okhttp e nos 52 apps,
é `OkHttpClient.init` (`OkHttpClient.kt:290-292` em 5.3.2, `:236-238` em 4.12.0). Ele só é
alcançado quando o builder **não** recebeu `sslSocketFactory`, e nesse ramo o `trustManager` vem
de `Platform.get().platformTrustManager()` na linha anterior. `AndroidPlatform` e
`Android10Platform` sobrescrevem só `newSSLContext`, e `ConscryptPlatform` não é escolhida no
Android. Um grep em cada um dos 56 repositórios não achou nenhuma chamada direta a
`Platform.get().newSslSocketFactory`. Os trust managers próprios dos apps entram todos por
`builder.sslSocketFactory(sf, tm)`, que desvia deste método: os trust-all de passnotes, matedroid,
nextcloudcookbook, pixiv, linkora e bitbanana, o UnsafeTrustManager do http_shortcuts e o
MemorizingTrustManager do openhab. Esses casos pertencem aos `SSLContext.init` do próprio app,
não a este site.

- **NOBS-00**: KeyManager[] literal `null`. É um cliente sem certificado de cliente → LEGIT.
- **NOBS-01**: o array lido é `arrayOf(trustManager)`, criado no próprio site. O array que
  carrega o predicado é o de `factory.trustManagers`, e só o elemento [0] passa adiante. É o trust
  manager padrão do sistema, correto, e perdeu a identidade por re-embrulho → LEGIT
  (`copy_loses_identity`).
- **NOBS-02**: SecureRandom literal `null`, ou seja, o gerador padrão do provedor → LEGIT.
- **TRUSTMANAGERFACTORY-NOBS-00 (id 16)**: `init(null as KeyStore?)`, o trust store do sistema →
  LEGIT. São 54 APKs: os 52 acima mais aelf e paperwork, que chegam por
  `HandshakeCertificates.Builder.addPlatformTrustedCertificates()`
  (`okhttp-tls-5.3.2/.../HandshakeCertificates.kt:146`).

## id 13/14: okhttp 3.14.9

```java
// okhttp-3.14.9/okhttp3/OkHttpClient.java:224-229, 261-264
} else {
  X509TrustManager trustManager = Util.platformTrustManager();
  this.sslSocketFactory = newSslSocketFactory(trustManager);
...
private static SSLSocketFactory newSslSocketFactory(X509TrustManager trustManager) {
  SSLContext sslContext = Platform.get().getSSLContext();
  sslContext.init(null, new TrustManager[] { trustManager }, null);   // :264
// okhttp-3.14.9/okhttp3/internal/Util.java:640
  trustManagerFactory.init((KeyStore) null);
```

O método é `private static` e só é chamado nesse ramo. Os vereditos são os mesmos dos ids 15/16.
A versão foi confirmada pelas linhas: 3.12.13 teria 290/667.

## id 17: HandshakeCertificates.sslContext (okhttp-tls)

```kotlin
// okhttp-tls-5.3.2/okhttp3/tls/HandshakeCertificates.kt:95-98 (4.12.0: :92-96)
fun sslContext(): SSLContext =
  Platform.get().newSSLContext().apply {
    init(arrayOf<KeyManager>(keyManager), arrayOf<TrustManager>(trustManager), SecureRandom())
  }
```

- `keyManager` vem de `TlsUtil.newKeyManager` (5.3.2 :88-112). Ele cria um KeyStore vazio
  (`load(null, password)`), faz `KeyManagerFactory.init(keyStore, password)` e devolve
  `keyManagers[0]`. O `arrayOf` é outro array → **NOBS-00 LEGIT `copy_loses_identity`**. No aelf
  (`EpitreApi.java:124-129`) nunca há heldCertificate. No paperwork
  (`Repository.kt:174-190`) só há heldCertificate depois de um pareamento. Em ambos os casos, sem
  chave, não há autenticação de cliente.
- `trustManager` vem de `TlsUtil.newTrustManager` (:50-75): um KeyStore montado com as raízes
  dadas, `TrustManagerFactory.init(trustStore)` e `trustManagers[0]`. O `arrayOf` é outro array →
  **NOBS-01 LEGIT `copy_loses_identity`**. No aelf as raízes são ISRG Root X1 mais as da
  plataforma. No paperwork, via Repository, são a CA do servidor ou as raízes da plataforma.
- **Divisão (confiança média)**: o fluxo de pareamento do paperwork (`PairingRunner.kt:139-152`)
  usa `.addInsecureHost(address)`. Com isso o trust manager vira `InsecureAndroidTrustManager` e
  aceita qualquer certificado daquele host. A impressão digital é conferida num `EventListener`,
  mas o pedido com o segredo Basic sai antes de a flag ser verificada (`:170-190`). Esse caminho
  depende do conteúdo de um QR code e é improvável sob as ferramentas automáticas. O caminho
  dominante é `buildOkHttpClientWithoutCache`, chamado a partir de `Repository.kt:64`. Se alguma
  linha vier do pareamento, o objeto seria trust-all por host (MISUSE de fato), mas a NOBS
  continuaria sendo perda de identidade.
- Não há NOBS-02 neste site porque `SecureRandom()` é construído em código tecido e
  `SecureRandomSpec` o credita.

## id 60/61: Conscrypt empacotado, SSLParametersImpl.createDefault*

```java
// conscrypt-android-2.5.3/org/conscrypt/SSLParametersImpl.java:532-537, 601-606 (2.5.0 idêntico)
KeyManagerFactory kmf = KeyManagerFactory.getInstance(algorithm);
kmf.init(null, null);                         // :536  KEYMANAGERFACTORY-NOBS-00
...
TrustManagerFactory tmf = TrustManagerFactory.getInstance(algorithm);
tmf.init((KeyStore) null);                    // :606  TRUSTMANAGERFACTORY-NOBS-00
```

Quem chama: pachli, http_shortcuts e etesync fazem `Security.insertProviderAt(Conscrypt.newProvider(), 1)`
(`PachliApplication.kt:89`, `Application.kt:41`, `CustomCertService.kt:61`). Com isso todo
`SSLContext.getInstance("TLS")` vira `OpenSSLContextImpl`, e `engineInit(kms, tms, sr)` constrói
`SSLParametersImpl`, que com `kms == null` chama `getDefaultX509KeyManager()` →
`createDefaultX509KeyManager()` e com `tms == null` chama `getDefaultX509TrustManager()`
(:122-144). `SSLParametersImpl.getDefault()` (:196-204) passa `null, null`, e
`Conscrypt.getDefaultX509TrustManager()` (Conscrypt.java:211-213) leva ao segundo. Chamadores
concretos:

- KMF: `Platform.newSslSocketFactory` (`init(null, …)`, id 15) nos três apps, etesync
  `HttpClient.kt:233` sem certificado, http_shortcuts `HttpClientFactory.kt:211` com
  `keyManagers` null.
- TMF: http_shortcuts `SSLUtil.kt:19` (`Conscrypt.getDefaultX509TrustManager()`). No etesync o
  chamador exato não foi fixado (getDefault ou init com tms null). O pachli sempre passa TM não
  nulo e não tem o site.

Em todos os caminhos o argumento lido é o literal `null` do próprio Conscrypt: o key manager
padrão sem chaves e o trust store do sistema → **LEGIT_UNOBSERVABLE**.

## Padrões observados

1. **Re-embrulho de array**: okhttp (3.x, 4.x, 5.x) e okhttp-tls sempre chamam `SSLContext.init`
   com um `arrayOf(x)` novo em volta do elemento [0] do array que a fábrica retornou. Como o store
   é por identidade, a NOBS-01 de trust manager padrão e a NOBS-00 de HandshakeCertificates são
   estruturais: nenhuma versão do okhttp jamais satisfaz a leitura. Isso sozinho responde por
   cerca de 8,2 mil linhas.
2. **Literais null** (`init(null, tm, null)`, `TMF.init(null)`, `KMF.init(null, null)`) cobrem as
   demais NOBS do grupo, por decisão documentada no `.mop` (SSLContextSpec.mop:176-208).
3. **ORDER-00 em toda chamada de fábrica** (fora do censo, mas relevante): todas as linhas de TMF
   e KMF desses métodos também levam `*-ORDER-00`, inclusive na linha do `getInstance`, e em
   `TlsUtil.kt:64` com multiplicidade 2 por chamada. Hipótese não verificada: `g2`
   (`getInstance(String, ..)`) casa também `getInstance(String)` porque `..` admite zero
   argumentos, então `g1` e `g2` disparam juntos e o segundo leva a `fail`. Isso não altera as NOBS
   acima, porque o ensure de `gtm1`/`gkm1` roda antes da transição.

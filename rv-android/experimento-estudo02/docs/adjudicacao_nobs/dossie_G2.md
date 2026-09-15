# Dossiê G2 — configuração TLS no código dos apps (SSLContext / TrustManagerFactory)

37 sites, 17 métodos, 12 APKs. Todo o código está no próprio app (`app@HEAD`, diretório `repos/`),
exceto a origem do TrustManager do http_shortcuts, que passa pelo Conscrypt empacotado
(`org.conscrypt:conscrypt-android:2.5.3`, fontes em `src/conscrypt-android-2.5.3/`).

## Tabela de veredictos

| id | método | código | categoria | mecanismo |
|---|---|---|---|---|
| 19 | cert4android `CertUtils.getTrustManager` | TMF-NOBS-00 | LEGIT_UNOBSERVABLE | null_default_truststore |
| 20 | http_shortcuts `configureTLS` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 20 | http_shortcuts `configureTLS` | SSL-NOBS-01 | LEGIT_UNOBSERVABLE | copy_loses_identity |
| 20 | http_shortcuts `configureTLS` | SSL-NOBS-02 | LEGIT_UNOBSERVABLE | null_default_securerandom |
| 28 | etesync `HttpClient$Builder.build` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 28 | etesync `HttpClient$Builder.build` | SSL-NOBS-01 | LEGIT_UNOBSERVABLE | custom_validating_trust_manager |
| 28 | etesync `HttpClient$Builder.build` | SSL-NOBS-02 | LEGIT_UNOBSERVABLE | null_default_securerandom |
| 33 | passnotes `createHttpClient` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 33 | passnotes `createHttpClient` | SSL-NOBS-01 | **MISUSE** | trust_all_manager (debug + opt-in) |
| 35 | matedroid `configureInsecureTls` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 35 | matedroid `configureInsecureTls` | SSL-NOBS-01 | **MISUSE** | trust_all_manager (opt-in) |
| 41 | feeder/jsonfeed `trustAllCerts` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 41 | feeder/jsonfeed `trustAllCerts` | SSL-NOBS-01 | **MISUSE** | trust_all_manager (sem opt-in) |
| 41 | feeder/jsonfeed `trustAllCerts` | SSL-NOBS-02 | LEGIT_UNOBSERVABLE | null_default_securerandom |
| 42 | owncloud `HttpClient.getOkHttpClient` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 42 | owncloud `HttpClient.getOkHttpClient` | SSL-NOBS-01 | LEGIT_UNOBSERVABLE | custom_validating_trust_manager |
| 42 | owncloud `HttpClient.getOkHttpClient` | SSL-NOBS-02 | LEGIT_UNOBSERVABLE | null_default_securerandom |
| 43 | owncloud `AdvancedX509TrustManager.<init>` | TMF-NOBS-00 | LEGIT_UNOBSERVABLE | null_default_truststore |
| 44 | openhab `MemorizingTrustManager.getTrustManager` | TMF-NOBS-00 | LEGIT_UNOBSERVABLE | null_default_truststore |
| 45 | newsreader `MemorizingTrustManager.getTrustManager` | TMF-NOBS-00 | LEGIT_UNOBSERVABLE | null_default_truststore |
| 46 | nextcloudcookbook `configureTrustAllCertificates` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 46 | nextcloudcookbook `configureTrustAllCertificates` | SSL-NOBS-01 | **MISUSE** | trust_all_manager (opt-in) |
| 52 | opencloud `HttpClient.getOkHttpClient` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 52 | opencloud `HttpClient.getOkHttpClient` | SSL-NOBS-01 | LEGIT_UNOBSERVABLE | custom_validating_trust_manager |
| 52 | opencloud `HttpClient.getOkHttpClient` | SSL-NOBS-02 | LEGIT_UNOBSERVABLE | null_default_securerandom |
| 53 | opencloud `AdvancedX509TrustManager.<init>` | TMF-NOBS-00 | LEGIT_UNOBSERVABLE | null_default_truststore |
| 54 | dsub2000 `RESTMusicService.<init>` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 54 | dsub2000 `RESTMusicService.<init>` | SSL-NOBS-01 | **MISUSE** | trust_all_manager (uso gated por opt-in) |
| 59 | osmtracker `TLSSocketFactory.<init>` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 59 | osmtracker `TLSSocketFactory.<init>` | SSL-NOBS-01 | LEGIT_UNOBSERVABLE | null_default_truststore |
| 59 | osmtracker `TLSSocketFactory.<init>` | SSL-NOBS-02 | LEGIT_UNOBSERVABLE | null_default_securerandom |
| 69 | openhab `ConnectionFactory.<init>` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 69 | openhab `ConnectionFactory.<init>` | SSL-NOBS-01 | LEGIT_UNOBSERVABLE | custom_validating_trust_manager |
| 69 | openhab `ConnectionFactory.<init>` | SSL-NOBS-02 | LEGIT_UNOBSERVABLE | null_default_securerandom |
| 70 | openhab `updateHttpClientForClientCert` | SSL-NOBS-00 | LEGIT_UNOBSERVABLE | null_no_client_auth |
| 70 | openhab `updateHttpClientForClientCert` | SSL-NOBS-01 | LEGIT_UNOBSERVABLE | custom_validating_trust_manager |
| 70 | openhab `updateHttpClientForClientCert` | SSL-NOBS-02 | LEGIT_UNOBSERVABLE | null_default_securerandom |

Total: 32 LEGIT_UNOBSERVABLE, 5 MISUSE, 0 SPEC_DEFECT, 0 UNDETERMINED.

## As leituras e seus produtores

- `SSLContextSpec.init` (`SSLContextSpec.mop:214-248`) lê, sempre com `validate`, três predicados sobre
  os três argumentos: `GENERATED_KEY_MANAGERS` sobre `kms` (:222, NOBS-00 em :229),
  `GENERATED_TRUST_MANAGER` sobre `tms` (:231, NOBS-01 em :238) e `RANDOMIZED` sobre `random`
  (:240, NOBS-02 em :247). Um `null` em qualquer posição dá NOT_OBSERVED por construção.
- Produtores: `KeyManagerFactorySpec.gkm1` (:173-176) grava sobre o array devolvido por
  `getKeyManagers()`; `TrustManagerFactorySpec.gtm1` (:215-218) grava sobre o array devolvido por
  `getTrustManagers()`; `SecureRandomSpec @match1` (:384) grava sobre o gerador criado por
  `new SecureRandom()`/`getInstance`. Os três gravam no corpo do evento, sem depender do veredito do
  produtor. Como a identidade é a do **array**, qualquer `arrayOf(tm)` / `new TrustManager[]{tm}`
  feito pelo app nunca é creditado, mesmo quando `tm` saiu de um TMF.
- `TrustManagerFactorySpec.init` (:118-171) lê `GENERATED_KEY_STORE` sobre o argumento
  (:147, NOBS-00 em :154); `(KeyStore) null` dá NOT_OBSERVED. O produtor é `KeyStoreSpec`
  (`load` before em :96-99, `@match` ensure em :194-196).
- Os apps que passam `new SecureRandom()` (passnotes, matedroid, nextcloudcookbook, dsub2000) não
  têm NOBS-02 — a leitura `RANDOMIZED` foi satisfeita, o que confirma que o produtor funciona.
- Deduplicação: o `ErrorCollector` do logger logcat
  (`rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java:51-55`) só registra uma vez por
  processo cada par (local, mensagem). Quando duas chamadas saem do mesmo local, uma com `null` e
  outra com objeto creditado, a linha registrada é a do `null`.

## Por método

### 19 — `at.bitfire.cert4android.CertUtils.getTrustManager` (etesync)

```kotlin
// cert4android/.../CertUtils.kt:20-24
fun getTrustManager(keyStore: KeyStore?): X509TrustManager? {
    val tmf = TrustManagerFactory.getInstance("X509")
    tmf.init(keyStore)
```
Chamadores: `CustomCertManager.kt:73-74` → `getTrustManager(null)` (TrustManager do sistema,
`trustSystemCerts` = `!DISTRUST_SYSTEM_CERTIFICATES`, padrão true, `HttpClient.kt:108-109`) e
`CustomCertService.kt:103` → `getTrustManager(trustedKeyStore)`, com `KeyStore.getInstance(getDefaultType())`
e `load` observados (:75, :90/:96). As 6 linhas vêm do caminho `null` (cada `HttpClient.Builder`
cria um `CustomCertManager`). **LEGIT_UNOBSERVABLE / null_default_truststore.** Nota: `__LOC`
aponta :22 para o `init` da linha 23, e o mesmo local recebe as linhas ORDER de `g2`/`init`.

### 20 — `ch.rmy.android.http_shortcuts.http.HttpClientFactory.configureTLS`

```kotlin
// HttpClientFactory.kt:207-212
val trustManager = hostVerificationConfig.getTrustManager()
val sslContext = SSLContext.getInstance("TLS", "Conscrypt")
val keyManagers = clientCertParams?.getKeyManagers(context)
sslContext.init(keyManagers, arrayOf(trustManager), null)
```
- `trustManager` (`SSLUtil.kt:17-22`): `Default` → `Conscrypt.getDefaultX509TrustManager()`, que
  dentro do Conscrypt 2.5.3 faz `TrustManagerFactory.init((KeyStore) null)` e extrai o primeiro
  `X509TrustManager` (`SSLParametersImpl.java:591-610`); `SelfSigned(fp)` → `UnsafeTrustManager(fp)`, que
  fixa a impressão digital do certificado folha; `TrustAll` → `UnsafeTrustManager()`, que aceita
  tudo, com `hostnameVerifier { _, _ -> true }` (:215-221). `TrustAll` só existe se o usuário marcar
  "aceitar todos os certificados" no atalho (`Shortcut.kt:203-207`, `SecurityPolicy.AcceptAll`).
- Qual caminho produziu as linhas: as 23 execuções com o site são **exatamente** as 23 com
  `org.conscrypt.SSLParametersImpl.createDefaultX509TrustManager`, que aqui só é alcançado por
  `Conscrypt.getDefaultX509TrustManager` (o okhttp aparece em 25 execuções, logo não é ele). Então o
  caminho dominante é `Default`: um TrustManager do sistema, colocado num array novo.
- NOBS-00: `keyManagers` null sem certificado cliente; com `File`, o array vem direto de
  `KeyManagerFactory.getKeyManagers` e seria creditado; com `Alias`, `ClientCertKeyManager` sobre `KeyChain`.
- NOBS-02: `null`.

Veredictos: NOBS-00 **LEGIT/null_no_client_auth**; NOBS-01 **LEGIT/copy_loses_identity**
(confiança média, porque a deduplicação esconderia um atalho TrustAll na mesma execução); NOBS-02
**LEGIT/null_default_securerandom**.

### 28 — `com.etesync.syncadapter.HttpClient$Builder.build`

```kotlin
// HttpClient.kt:232-236
val sslContext = SSLContext.getInstance("TLS")
sslContext.init(
        if (keyManager != null) arrayOf(keyManager) else null,
        arrayOf(trustManager),
        null)
```
`trustManager` = `certManager` (sempre definido em :108) = `CustomCertManager`, que valida pelo
sistema e, se falhar, consulta o `CustomCertService`: aceita só certificado já na loja do app ou
aprovado pelo usuário via notificação (`CustomCertService.kt:214-260`). O hostname verifier embrulha o
`OkHostnameVerifier` (`CustomCertManager.kt:216-242`). `keyManager` nunca é não-nulo:
`certificateAlias` (:70) nunca é atribuído. Veredictos: NOBS-00 **LEGIT/null_no_client_auth**, NOBS-01
**LEGIT/custom_validating_trust_manager**, NOBS-02 **LEGIT/null_default_securerandom**.

### 33 — `com.ivanovsky.passnotes...webdav.HttpClientFactory.createHttpClient`

```kotlin
// HttpClientFactory.kt:27,36-41
if (BuildConfig.DEBUG && type == HttpClientType.UNSECURE) {
    val unsecuredTrustManager = createUnsecuredTrustManager()   // check* vazios (:48-67)
    sslContext.init(null, arrayOf(unsecuredTrustManager), SecureRandom())
    builder.hostnameVerifier { _, _ -> true }
```
Opt-in duplo: build DEBUG **e** caixa "ignorar validação SSL" no login WebDAV
(`ServerLoginViewModel.kt:148-151, 329-331` → `WebDavNetworkLayer.kt:51-57`). O ramo rodou (1 linha), então
o APK é debug e a exploração marcou a caixa. NOBS-00 **LEGIT/null_no_client_auth**; NOBS-01
**MISUSE/trust_all_manager**.

### 35 — `com.matedroid.di.TeslamateApiFactory.configureInsecureTls`

```kotlin
// NetworkModule.kt:209-219
val trustAllCerts = arrayOf<TrustManager>(object : X509TrustManager { ...vazios... })
sslContext.init(null, trustAllCerts, SecureRandom())
builder.hostnameVerifier { _, _ -> true }
```
Chamado só se `acceptInvalidCerts` (:200-202), que vem da configuração do usuário (padrão false,
`SettingsViewModel.kt:42,163`). NOBS-00 **LEGIT**; NOBS-01 **MISUSE/trust_all_manager** (opt-in).

### 41 — `com.nononsenseapps.jsonfeed.OkHttpBuilderExtensionsKt.trustAllCerts` (Feeder)

```kotlin
// OkHttpBuilderExtensions.kt:31-36
sslContext.init(null, arrayOf<TrustManager>(trustManager), null)   // trustManager com check* vazios
sslSocketFactory(sslSocketFactory, trustManager)
    .hostnameVerifier(HostnameVerifier { _, _ -> true })
```
`cachingHttpClient(trustAllCerts: Boolean = true)` (`JsonFeedParser.kt:14-35`), e o singleton
`OkHttpClient` do app o chama sem o parâmetro (`FeederApplication.kt:117-123`). **Sem opt-in**: todo o
tráfego de feeds e imagens aceita qualquer certificado e hostname. NOBS-00 **LEGIT**, NOBS-01
**MISUSE/trust_all_manager**, NOBS-02 **LEGIT/null_default_securerandom**.

### 42 / 52 — `HttpClient.getOkHttpClient` (ownCloud :81 / openCloud :79; código idêntico)

```java
final X509TrustManager trustManager = new AdvancedX509TrustManager(
        NetworkUtils.getKnownServersStore(mContext));
final SSLContext sslContext = buildSSLContext();
sslContext.init(null, new TrustManager[]{trustManager}, null);
```
`AdvancedX509TrustManager.checkServerTrusted`: se o certificado não está no known-servers store
(aprovado pelo usuário), exige `checkValidity` e o TrustManager do sistema e lança
`CertificateCombinedException`, que a UI mostra para decisão. O hostname usa
`KnownServersHostnameVerifier` (`OkHostnameVerifier`, ou certificado aprovado). Veredictos: NOBS-00
**LEGIT/null_no_client_auth**, NOBS-01 **LEGIT/custom_validating_trust_manager**, NOBS-02
**LEGIT/null_default_securerandom**.

### 43 / 53 — `AdvancedX509TrustManager.<init>` (ownCloud :59 / openCloud :57)

```java
TrustManagerFactory factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
factory.init((KeyStore) null);
```
**LEGIT/null_default_truststore**.

### 44 — `de.duenndns.ssl.MemorizingTrustManager.getTrustManager` (openHAB :310)

```java
// MemorizingTrustManager.java:144-148, 308-311
this.appTrustManager = getTrustManager(appKeyStore);
this.defaultTrustManager = getTrustManager(null);
...
TrustManagerFactory tmf = TrustManagerFactory.getInstance("X509");
tmf.init(ks);
```
`appKeyStore` sai de `loadAppKeyStore` (:326-345: `getInstance(getDefaultType())` + `load` observados,
e nenhuma linha KeyStoreSpec no APK), então deve ler SATISFIED; a chamada `null` garante a linha
(mesmo local, deduplicado). **LEGIT/null_default_truststore**.

### 45 — `de.luhmer.owncloudnewsreader.ssl.MemorizingTrustManager.getTrustManager` (:282)

Mesma estrutura: `init(Context)` faz `getTrustManager(null)` e `getTrustManager(appKeyStore)` (:132-134),
e `appKeyStore` é carregado com `load(null, null)` observado (:295-310). **LEGIT/null_default_truststore.**
Este MTM valida primeiro pelo sistema, depois pelo appKeyStore, e por fim pergunta ao usuário
(:358-389). O único `SSLContext.init` com ele (`OkHttpSSLClient.java:58`) está comentado.

### 46 — `de.lukasneugebauer.nextcloudcookbook.core.util.OkHttpClientProvider.configureTrustAllCertificates`

```kotlin
// OkHttpClientProvider.kt:56-78
val trustAllCerts = arrayOf<TrustManager>(object : X509TrustManager { ...vazios... })
val sslContext = SSLContext.getInstance("SSL")
sslContext.init(null, trustAllCerts, SecureRandom())
builder.sslSocketFactory(...).hostnameVerifier { _, _ -> true }
```
Ativado quando a preferência "permitir certificados autoassinados" muda para true (:34-46; padrão
false, `Constants.kt:12`; toggle na tela inicial, `StartScreenViewModel.kt:43,117-119`). O nome engana:
aceita qualquer certificado, não só autoassinados. NOBS-00 **LEGIT**; NOBS-01
**MISUSE/trust_all_manager** (opt-in). O mesmo `init` também gera SSLCONTEXT-PROTO-00 ("SSL").

### 54 — `github.paroj.dsub2000.service.RESTMusicService.<init>`

```java
// RESTMusicService.java:123-139
TrustManager[] trustAllCerts = new TrustManager[]{ new X509TrustManager() { ...vazios... } };
SSLContext insecureSslContext = SSLContext.getInstance("TLS");
insecureSslContext.init(null, trustAllCerts, new java.security.SecureRandom());
```
O contexto trust-all é criado incondicionalmente em todo construtor. A fábrica e o
`selfSignedHostnameVerifier` (que devolve true) só são instalados numa conexão se a opção por
servidor "allow insecure" estiver ligada (padrão false, `Util.java:480-483` → :1967-1972;
`RemoteController.java:48,124`). NOBS-00 **LEGIT**; NOBS-01 **MISUSE/trust_all_manager** (o `init`
não depende do opt-in, o uso depende).

### 59 — `net.osmtracker.layout.TLSSocketFactory.<init>`

```java
// TLSSocketFactory.java:22-24
SSLContext context = SSLContext.getInstance("TLS");
context.init(null, null, null);
```
Tudo padrão; a classe só força TLSv1.1/1.2 nos sockets. Os três códigos **LEGIT** (null_no_client_auth,
null_default_truststore, null_default_securerandom).

### 69 / 70 — `org.openhab.habdroid.core.connection.ConnectionFactory`

```kotlin
// ConnectionFactory.kt:162, 171-173 (<init>)
trustManager = MemorizingTrustManager(context)
SSLContext.getInstance("TLS").apply {
    init(null, MemorizingTrustManager.getInstanceList(context), null)
// ConnectionFactory.kt:304-308, 323-324 (updateHttpClientForClientCert)
val keyManagers = if (clientCertAlias != null) arrayOf<KeyManager>(ClientKeyManager(context, clientCertAlias)) else null
sslContext.init(keyManagers, arrayOf<TrustManager>(trustManager), null)
```
`getInstanceList` devolve `new X509TrustManager[]{ new MemorizingTrustManager(c) }` (:185-187). O MTM
valida pelo appTrustManager, depois pelo sistema e por fim pergunta ao usuário
(`MemorizingTrustManager.java:420-456, 697-708`); o hostname verifier embrulha o `OkHostnameVerifier`
(:738-768). Os `KeyManager` são null, ou um `ClientKeyManager` sobre `KeyChain` quando o usuário
configurou certificado cliente. Todos os seis códigos **LEGIT** (NOBS-01 =
custom_validating_trust_manager).

## Padrões

1. **Todo NOBS-00 e NOBS-02 deste grupo é um `null` literal** (ou quase literal) — "sem certificado
   cliente" e "gerador padrão". A regra CrySL trata `null` como não observado, e o próprio `.mop` diz
   isso (SSLContextSpec.mop:176-186 e 204-208). É o volume dominante de ruído.
2. **NOBS-01 não separa trust-all de validação customizada.** Os cinco MISUSE e os cinco
   custom_validating têm a mesma forma sintática (`arrayOf(tm)` em volta de um `X509TrustManager` do
   app), e o monitor emite o mesmo código para os dois. Distinguir exige olhar o corpo de
   `checkServerTrusted`, algo que nenhuma leitura de predicado vê.
3. Quatro dos cinco MISUSE ficam atrás de opt-in do usuário (passnotes com debug + caixa, matedroid,
   nextcloudcookbook, dsub2000 no uso); o Feeder é trust-all em uso normal.
4. Fora do escopo NOBS, mas sistemático: toda chamada `TrustManagerFactory.getInstance(String)`
   deste grupo gera `TRUSTMANAGERFACTORY-ORDER-00` com `ev=g2`, seguido de ORDER em `init` e `gtm1`.
   O pointcut `g2` (`TrustManagerFactorySpec.mop:87-90`, `getInstance(String, ..)`) casa com a
   sobrecarga de um argumento no weaver dexlib2. `KeyManagerFactorySpec.mop:55-58` tem o mesmo
   pointcut, e o http_shortcuts mostra KEYMANAGERFACTORY-ORDER-00 no Conscrypt. Só `SSLContextSpec.g2`
   usa `Object+`, pelo motivo que o próprio comentário registra. Os corpos `init`/`gtm1` rodam mesmo assim, então isso não
   altera os NOBS.

# Dossiê G3 — caminhos AEAD do tink (AES-GCM, Android Keystore, streaming HKDF)

Grupo G3, 13 métodos, 18 sítios. Todos os veredictos são `LEGIT_UNOBSERVABLE`; nenhum `MISUSE`,
nenhum `SPEC_DEFECT`, nenhum `UNDETERMINED`.

## Tabela de veredictos

| id | método | código | categoria | mecanismo | raiz |
|---|---|---|---|---|---|
| 76 | `aead.internal.AesGcmJceUtil.getSecretKey` | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_keyset | — |
| 77 | `aead.internal.InsecureNonceAesGcmJce.<init>` | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_keyset | — |
| 78 | `InsecureNonceAesGcmJce.decrypt` | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ `InsecureNonceAesGcmJce.<init>` |
| 78 | `InsecureNonceAesGcmJce.decrypt` | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | cascade | GCMPARAMETERSPEC-NOBS-01 @ `InsecureNonceAesGcmJce.getParams` |
| 79 | `InsecureNonceAesGcmJce.encrypt` | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ `InsecureNonceAesGcmJce.<init>` |
| 80 | `InsecureNonceAesGcmJce.getParams` | GCMPARAMETERSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 81 | `integration.android.AndroidKeystore$AeadImpl.decrypt` | GCMPARAMETERSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 81 | `AndroidKeystore$AeadImpl.decrypt` | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | cascade | GCMPARAMETERSPEC-NOBS-01 @ `AndroidKeystore$AeadImpl.decrypt` |
| 82 | `integration.android.AndroidKeystoreAesGcm.decryptInternal` | GCMPARAMETERSPEC-NOBS-01 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 82 | `AndroidKeystoreAesGcm.decryptInternal` | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | cascade | GCMPARAMETERSPEC-NOBS-01 @ `AndroidKeystoreAesGcm.decryptInternal` |
| 86 | `subtle.AesGcmHkdfStreaming.deriveKeySpec` | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_derived_hkdf_from_keyset | — |
| 87 | `subtle.AesGcmHkdfStreaming.paramsForSegment` | GCMPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | nonce_prefix_counter_composed | — |
| 88 | `AesGcmHkdfStreamDecrypter.decryptSegment` | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ `AesGcmHkdfStreaming.deriveKeySpec` |
| 88 | `AesGcmHkdfStreamDecrypter.decryptSegment` | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | cascade | GCMPARAMETERSPEC-NOBS-00 @ `AesGcmHkdfStreaming.paramsForSegment` |
| 89 | `AesGcmHkdfStreamEncrypter.encryptSegment` | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ `AesGcmHkdfStreaming.deriveKeySpec` |
| 89 | `AesGcmHkdfStreamEncrypter.encryptSegment` | IVCHAINJUNCTION-NOBS-01 | LEGIT_UNOBSERVABLE | cascade | GCMPARAMETERSPEC-NOBS-00 @ `AesGcmHkdfStreaming.paramsForSegment` |
| 90 | `subtle.AesGcmJce.<init>` | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_keyset | — |
| 91 | `subtle.AesGcmJce.encrypt` | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ `AesGcmJce.<init>` |

Os caminhos de biblioteca abaixo são relativos a `$SP/src/`; os `.mop` estão em
`rvsec-mop/src/main/resources/jca_android/`.

## 1. Qual tink cada APK carrega

Nenhum dos nove apps importa `com.google.crypto.tink` no próprio código (grep nos repositórios;
no deku, também nas classes do APK convertido). O tink chega sempre por transitividade:

| APK | dependência declarada | tink resolvido (POM) | confirmado pelas linhas |
|---|---|---|---|
| app.maskan.chat_90 | `security-crypto:1.1.0-alpha06` (libs.versions.toml:10) | tink-android **1.8.0** | InsecureNonceAesGcmJce :66/:93/:136/:159; AndroidKeystoreAesGcm :113/:116 |
| app.michaelwuensch.bitbanana_79 | `security-crypto-ktx:1.1.0-beta01` → `security-crypto:1.1.0-beta01` | **1.8.0** | idem |
| com.afkanerd.deku_83 | `security-crypto:1.1.0` | **1.8.0** | idem |
| com.tk.quicksearch_65 | `security-crypto:1.1.0-alpha06` | **1.8.0** | :66; :113/:116 |
| dev.dettmer.simplenotes_41 | `security-crypto:1.1.0` | **1.8.0** | idem |
| org.css_apps_m3.password_manager_16 | `security-crypto:1.1.0` | **1.8.0** | idem + AesGcmHkdfStreaming :183/:192/:234/:299 |
| com.celzero.bravedns_619 | `security-crypto:1.1.0` | **1.8.0** | AndroidKeystoreAesGcm :113/:116 |
| org.openhab.habdroid_589 | `security-crypto:1.0.0` | tink-android **1.5.0** | AndroidKeystoreAesGcm :110/:113; AesGcmJce :54/:73 |
| com.hegocre.nextcloudpasswords_38 | `dev.spght:encryptedprefs-ktx:1.1.1` → `encryptedprefs-core:1.1.1` | tink-android **1.19.0** | AesGcmJceUtil :57; AndroidKeystore :175/:178 |

POMs: `security-crypto-1.0.0.pom` → tink 1.5.0; `1.1.0-alpha06`, `1.1.0-beta01` e `1.1.0` → tink
1.8.0; `encryptedprefs-core-1.1.1.pom` → tink 1.19.0 (arquivos em `$SP/src/poms/`). Todas as
linhas `sources` caem exatamente sobre a chamada monitorada nessas versões.

## 2. Como os apps usam o tink

- **EncryptedSharedPreferences** (maskan.chat `EncryptedPrefsFactory.kt:30`, bitbanana
  `PrefsUtil.java:119`, quicksearch `BasePreferences.kt:237`, simplenotes `CredentialStore.kt:40`,
  password_manager `UnlockScreen.kt:47`/`SetupActivity.kt:137`/`SqlSyncManager.kt:337`, openhab
  `OpenHabApplication.kt:78`, nextcloudpasswords `PreferencesManager.kt:32` pelo fork dev.spght). No
  deku o uso está na biblioteca jitpack `lib_smsmms_android`,
  `SecurityKt.settingsGetDbPassword` (preferências `com.afkanerd.deku.security`, senha do banco) —
  **veredito apoiado em bytecode** (dex2jar + javap), pois a biblioteca não está no repositório.
- **EncryptedFile** com `AES256_GCM_HKDF_4KB`: password_manager
  (`PasswordRepository.kt:42` e `:57`) e bravedns (`EncryptedFileManager.kt:160`, `:278`).

Fiação comum (`security-crypto-1.1.0/.../EncryptedSharedPreferences.java:165-177`): dois
`AndroidKeysetManager` — AES256_SIV para os nomes, AES256_GCM para os valores —, ambos com chave
mestra `android-keystore://<alias>`. O keyset é guardado **cifrado** nas SharedPreferences. A chave
mestra é gerada dentro do Android Keystore (`MasterKeys.java:142`, `KeyGenerator` AndroidKeyStore)
e seus bytes nunca saem do framework.

## 3. De onde vêm as chaves (sítios 76, 77, 90 e as cascatas CIPHER-NOBS-00)

`SecretKeySpecSpec.c1` (`SecretKeySpecSpec.mop:97`) lê `PREPARED_KEY_MATERIAL` sobre o `byte[]`
(`:110`) e emite NOBS-00 (`:118`). Os produtores de `PREPARED_KEY_MATERIAL` no conjunto são só
`Key.getEncoded()` (`KeySpec.mop:75/105`, `SecretKeySpec.mop:119/145`, os dois condicionados à
origem observada da chave) e `KeyAgreement.generateSecret` (`KeyAgreementSpec.mop:298/315`).
Com NOBS, `conforms=false`, `spec` fica nulo (`:121-124`) e o `ensure(GENERATED_KEY, spec, …)` do
`@match` (`:256`) é um no-op — por isso toda leitura posterior de `CipherSpec.i2`
(`CipherSpec.mop:168`, `:199-214`, NOBS em `:232`) sobre essa chave cai em cascata.

**tink 1.8.0** (`tink-android-1.8.0/com/google/crypto/tink/`):

```java
// aead/AesGcmKeyManager.java:52 — construção do primitivo a partir do keyset
return new AesGcmJce(key.getKeyValue().toByteArray());
// subtle/AesGcmJce.java:41
this.insecureNonceAesGcmJce = new InsecureNonceAesGcmJce(key, /*prependIv=*/ true);
// aead/internal/InsecureNonceAesGcmJce.java:66
this.keySpec = new SecretKeySpec(key, "AES");
```

Rastro para trás: `key` ← `AesGcmKey.getKeyValue().toByteArray()` (cópia de ByteString) ← `Keyset`
← dois caminhos:

1. **Leitura do armazenamento** — `AndroidKeysetManager.build()` encontra o keyset serializado
   (`AndroidKeysetManager.java:287`) e o decifra (`:297` → `:381` → `KeysetHandle.java:918-919`,
   `Keyset.parseFrom(masterKey.decrypt(...))`). Os bytes saem de `Cipher.doFinal` com a chave do
   Android Keystore e passam pelo parser protobuf: nenhuma identidade observável.
2. **Geração** — na primeira abertura (instalação limpa: pode ter acontecido nesta execução ou numa
   anterior), `generateKeysetAndWriteToPrefs` (`:342`) chama `AesGcmKeyManager.createKey`:
   `ByteString.copyFrom(Random.randBytes(format.getKeySize()))` (`AesGcmKeyManager.java:100`). O
   array de `Random.randBytes` recebe `RANDOMIZED` de `SecureRandomSpec` (é código tecido), mas não
   `PREPARED_KEY_MATERIAL`, e é copiado duas vezes (ByteString.copyFrom, toByteArray) antes de chegar
   ao `SecretKeySpec`.

Nos dois caminhos a chave é material secreto legítimo (256 bits de SecureRandom, protegidos pela
chave mestra do Keystore). O NOBS é limite de alcance → `LEGIT_UNOBSERVABLE`, `key_from_keyset`.

**Sítio 76 (tink 1.19.0, nextcloudpasswords)**: mesma história com as classes novas —
`AesGcmKeyManager.java:60` (`AesGcmJce::create`), `subtle/AesGcmJce.java:79`
(`key.getKeyBytes().toByteArray(...)`) → `:59` → `AesGcmJceUtil.java:57`
`new SecretKeySpec(key, "AES")`; geração em `AesGcmKeyManager.java:127`
(`SecretBytes.randomBytes`, que faz `Bytes.copyFrom(Random.randBytes(n))`, `SecretBytes.java:47`),
e `toByteArray` copia de novo (`SecretBytes.java:59`, `Bytes.java:68-70`). Nesse APK não há linha
alguma de encrypt/decrypt de `AesGcmJce`: o primitivo é construído e nenhum valor é lido ou escrito
nas execuções; só o AES-SIV dos nomes (fora do G3) roda.

**Sítio 90 (tink 1.5.0, openhab)**: `AesGcmKeyManager.java:47` `new AesGcmJce(key.getKeyValue().toByteArray())`
→ `subtle/AesGcmJce.java:54` `keySpec = new SecretKeySpec(key, "AES")`; geração em
`AesGcmKeyManager.java:95`; leitura em `AndroidKeysetManager.java:311`
(`KeysetHandle.read(reader, masterKey)`).

Cascatas de chave: **78/CIPHER** (`InsecureNonceAesGcmJce.java:136`), **79/CIPHER** (`:93`),
**91/CIPHER** (`AesGcmJce.java:73`, tink 1.5.0, uma única linha no corpus e zero execuções só-NOBS).

## 4. Quem fornece o nonce a `InsecureNonceAesGcmJce` (sítios 78, 79, 80)

Na 1.8.0 há exatamente dois chamadores: `subtle.AesGcmJce` e `hybrid.internal.AesGcmHpkeAead` (HPKE,
não alcançado por security-crypto). `AesGcmJce`:

```java
// subtle/AesGcmJce.java:51-52 — cifração
byte[] iv = Random.randBytes(InsecureNonceAesGcmJce.IV_SIZE_IN_BYTES);
return insecureNonceAesGcmJce.encrypt(iv, plaintext, associatedData);
// subtle/AesGcmJce.java:62-63 — decifração
byte[] iv = Arrays.copyOf(ciphertext, InsecureNonceAesGcmJce.IV_SIZE_IN_BYTES);
return insecureNonceAesGcmJce.decrypt(iv, ciphertext, associatedData);
```

```java
// aead/internal/InsecureNonceAesGcmJce.java:145-159
private static AlgorithmParameterSpec getParams(final byte[] iv) { return getParams(iv, 0, iv.length); }
...
return new GCMParameterSpec(8 * TAG_SIZE_IN_BYTES, buf, offset, len);   // :159
```

`Random.randBytes` (`subtle/Random.java:41-45`) usa um `SecureRandom` por thread criado com
`new SecureRandom()` e chama `nextBytes(rand)` — tudo em código tecido, então
`SecureRandomSpec.next2` (`SecureRandomSpec.mop:289`) e `@match2` (`:398`) marcam o próprio array
`iv` como `RANDOMIZED`. `GCMParameterSpecSpec.c2` (`GCMParameterSpecSpec.mop:116`, leitura `:125`,
NOBS-01 `:133`) fica SATISFIED e o `@match` grava `PREPARED_GCM` (`:180`), que
`IvChainJunctionSpec.use` (`IvChainJunction.mop:138`, `:194`, NOBS-01 `:201`) aceita.

Os dados confirmam a separação: em cada APK a contagem de `getParams:159 GCMPARAMETERSPEC-NOBS-01`
é igual à de `decrypt:136` e diferente da de `encrypt:93` (maskan 204/204 vs 144; deku 215/215 vs
168; password_manager 35/35 vs 34; simplenotes 8/8 vs 10; bitbanana 1/1 vs 1), e `encrypt:93` nunca
emite IVCHAINJUNCTION-NOBS-01. Logo:

- **80 GCMPARAMETERSPEC-NOBS-01** — só no caminho de decifração, nonce = cópia dos 12 primeiros
  bytes do texto cifrado armazenado → `iv_from_ciphertext`.
- **78 IVCHAINJUNCTION-NOBS-01** — cascata do sítio 80.
- Na cifração o nonce é aleatório por mensagem e é visto como tal. O nome `InsecureNonce` só
  diz que quem chama escolhe o nonce; nesses APKs quem chama sorteia. Não há reuso nem nonce fixo.

## 5. `AndroidKeystoreAesGcm` / `AndroidKeystore$AeadImpl` (sítios 81, 82)

```java
// tink-android-1.8.0 integration/android/AndroidKeystoreAesGcm.java:111-116
private byte[] decryptInternal(final byte[] ciphertext, final byte[] associatedData) ... {
  GCMParameterSpec params =
      new GCMParameterSpec(8 * TAG_SIZE_IN_BYTES, ciphertext, 0, IV_SIZE_IN_BYTES);   // :113
  Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
  cipher.init(Cipher.DECRYPT_MODE, key, params);                                    // :116
```

(1.5.0: as mesmas instruções em `:110`/`:113`; 1.19.0: `AndroidKeystore.java:175`/`:178`, para onde
`AndroidKeystoreAesGcm` delega.)

O `ciphertext` tem duas origens, ambas legítimas:

1. **Autoteste** — toda obtenção da chave mestra passa por `AndroidKeystoreKmsClient.getAead` →
   `validateAead` (1.8.0 `:293-299`; 1.5.0 `:243-249`; 1.19.0 `:155`), que cifra 10 bytes
   aleatórios e em seguida os decifra. A cifração faz `cipher.init(ENCRYPT_MODE, key)` sem
   parâmetros: o IV é gerado **dentro do Android Keystore** e copiado de `cipher.getIV()` para o
   início do cifrado (`AndroidKeystoreAesGcm.java:90`). É o que explica a decifração aparecer em
   todas as execuções, até nas que só criam o keyset (bravedns, quicksearch).
2. **Keyset cifrado** lido das SharedPreferences (`AndroidKeysetManager.java:381`,
   `KeysetHandle.java:919`).

→ **82 e 81 GCMPARAMETERSPEC-NOBS-01**: `iv_from_ciphertext`. **82 e 81 IVCHAINJUNCTION-NOBS-01**:
cascata. A chave desse `init` (`KeyStore.getKey` no AndroidKeyStore, `AndroidKeystoreAesGcm.java:51`)
é creditada por `KeyStoreSpec` (`KeyStoreSpec.mop:200`): não existe CIPHER-NOBS-00 nessas linhas em
nenhum dos 8 APKs, nem no `init` de cifração (`:85`).

## 6. `AesGcmHkdfStreaming` (sítios 86–89, só password_manager, EncryptedFile)

```java
// tink-android-1.8.0 subtle/AesGcmHkdfStreaming.java
private static GCMParameterSpec paramsForSegment(byte[] prefix, long segmentNr, boolean last) ... {
  ByteBuffer nonce = ByteBuffer.allocate(NONCE_SIZE_IN_BYTES);   // :178
  nonce.order(ByteOrder.BIG_ENDIAN);
  nonce.put(prefix);                                              // :180
  SubtleUtil.putAsUnsigedInt(nonce, segmentNr);
  nonce.put((byte) (last ? 1 : 0));
  return new GCMParameterSpec(8 * TAG_SIZE_IN_BYTES, nonce.array());   // :183
}
private SecretKeySpec deriveKeySpec(byte[] salt, byte[] aad) ... {
  byte[] key = Hkdf.computeHkdf(hkdfAlg, ikm, salt, aad, keySizeInBytes);   // :191
  return new SecretKeySpec(key, "AES");                                      // :192
}
```

- **Chave (86)**: `ikm` = bytes do keyset `AES256_GCM_HKDF_4KB`
  (`AesGcmHkdfStreamingKeyManager.java:55`, `key.getKeyValue().toByteArray()`); `salt` =
  `Random.randBytes(keySizeInBytes)` na cifração (`:173`, `:211`) ou lido do cabeçalho do arquivo na
  decifração (`:288`). `Hkdf.computeHkdf` monta um array novo `result` por `System.arraycopy` de
  saídas de `Mac.doFinal` (`Hkdf.java:61-77`). É HKDF correto com salt aleatório por arquivo;
  a raiz (ikm) é do keyset e a cópia final é inobservável. O conjunto tampouco tem produtor de
  `PREPARED_KEY_MATERIAL` para saída de Mac, mas isso não mudaria o veredito, porque a raiz continua
  inobservável → `LEGIT_UNOBSERVABLE`, `key_derived_hkdf_from_keyset`.
- **Nonce (87)**: prefixo de 7 bytes aleatório (`randomNonce`, `:187`, guardado no cabeçalho em
  `:216`; na decifração lido em `:289`) + número do segmento + flag de último. É a construção
  STREAM (nonce-based OAE) do tink: o nonce não é aleatório por segmento, e não precisa ser. É
  único por segmento, sob uma chave derivada nova por arquivo. O `ByteBuffer` copia o prefixo,
  então nem na cifração a identidade do array aleatório sobrevive → `LEGIT_UNOBSERVABLE`,
  `nonce_prefix_counter_composed`. As linhas vêm dos dois caminhos (encryptSegment 34 execuções,
  decryptSegment 14).
- **88/89 CIPHER-NOBS-00** (`:299`, `:234`): cascata de 86. **88/89 IVCHAINJUNCTION-NOBS-01**:
  cascata de 87.

## 7. Padrões

- Os 18 sítios se reduzem a **quatro raízes**, todas limite de alcance: chave vinda de keyset
  (76, 77, 90), chave derivada por HKDF de keyset (86), IV/nonce lido do cifrado (80, 81, 82) e
  nonce composto por prefixo+contador (87). Os outros 10 são cascatas.
- A cascata GCMParameterSpec → IvChainJunction duplica cada acusação de IV em decifração GCM
  (é o custo que `IvChainJunction.mop:127-137` já documenta).
- O próprio conjunto de specs dá uma boa notícia: o nonce aleatório de cifração do tink **é**
  observado (Random.randBytes → SecureRandomSpec). O caminho de encrypt não emite acusação de IV,
  o que confirma que o produtor funciona através de bibliotecas tecidas.
- O autoteste `validateAead` do tink gera uma decifração GCM por construção de keyset. É por isso
  que `AndroidKeystoreAesGcm.decryptInternal` é o sítio com mais APKs (8) e mais linhas (1 268),
  mesmo em apps que nunca leem um valor cifrado.

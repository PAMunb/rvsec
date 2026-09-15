# Dossiê G4 — tink: AES-SIV, AES-CMAC e HKDF

Métodos 83, 84, 85, 92–98. São 19 sítios, e todos batem com `census_sites.csv`. Os caminhos de biblioteca são relativos a `$SP/src/`; os de aplicativo, ao diretório `repos/`.

## Veredictos

| id | classe.método | código | categoria | mecanismo | raiz |
|---|---|---|---|---|---|
| 83 | prf.internal.PrfAesCmac.`<init>` | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_keyset | — |
| 84 | prf.internal.PrfAesCmac.compute | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ 83 |
| 85 | prf.internal.PrfAesCmac.generateSubKeys | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ 83 |
| 92 | subtle.AesSiv.decryptDeterministically | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ 92 |
| 92 | subtle.AesSiv.decryptDeterministically | IVPARAMETERSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | iv_from_ciphertext | — |
| 92 | subtle.AesSiv.decryptDeterministically | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_keyset | — |
| 93 | subtle.AesSiv.encryptDeterministically | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ 93 |
| 93 | subtle.AesSiv.encryptDeterministically | IVCHAINJUNCTION-NOBS-00 | SPEC_DEFECT | cascade | IVPARAMETERSPEC-NOBS-00 @ 93 |
| 93 | subtle.AesSiv.encryptDeterministically | IVPARAMETERSPEC-NOBS-00 | SPEC_DEFECT | siv_synthetic_iv_by_design | — |
| 93 | subtle.AesSiv.encryptDeterministically | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_keyset | — |
| 94 | subtle.AesSiv.encryptInternal | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ 94 |
| 94 | subtle.AesSiv.encryptInternal | IVCHAINJUNCTION-NOBS-00 | SPEC_DEFECT | cascade | IVPARAMETERSPEC-NOBS-00 @ 94 |
| 94 | subtle.AesSiv.encryptInternal | IVPARAMETERSPEC-NOBS-00 | SPEC_DEFECT | siv_synthetic_iv_by_design | — |
| 94 | subtle.AesSiv.encryptInternal | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_keyset | — |
| 95 | subtle.Hkdf.computeHkdf | MAC-NOBS-00 | SPEC_DEFECT | cascade | SECRETKEYSPEC-NOBS-00 @ 95 |
| 95 | subtle.Hkdf.computeHkdf | SECRETKEYSPEC-NOBS-00 | SPEC_DEFECT | producer_missing_in_specset | — |
| 96 | subtle.PrfAesCmac.`<init>` | SECRETKEYSPEC-NOBS-00 | LEGIT_UNOBSERVABLE | key_from_keyset | — |
| 97 | subtle.PrfAesCmac.compute | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ 96 |
| 98 | subtle.PrfAesCmac.generateSubKeys | CIPHER-NOBS-00 | LEGIT_UNOBSERVABLE | cascade | SECRETKEYSPEC-NOBS-00 @ 96 |

No total, 13 sítios são LEGIT_UNOBSERVABLE, 6 são SPEC_DEFECT, e não há MISUSE nem UNDETERMINED.

## Versões

A versão de cada APK foi identificada pelos arquivos de build e pelos POMs. Depois, confirmei que as linhas de `sources` caem exatamente na chamada monitorada.

| APK | dependência direta | tink resolvido | linhas que confirmam |
|---|---|---|---|
| app.maskan.chat_90 | security-crypto 1.1.0-alpha06 | tink-android 1.8.0 | PrfAesCmac:57/69/110, AesSiv:119, AesSiv:143 |
| com.tk.quicksearch_65 | security-crypto 1.1.0-alpha06 | 1.8.0 | idem |
| app.michaelwuensch.bitbanana_79 | security-crypto-ktx 1.1.0-beta01 → security-crypto 1.1.0-beta01 | 1.8.0 | idem |
| com.afkanerd.deku_83 | security-crypto 1.1.0 | 1.8.0 | idem |
| dev.dettmer.simplenotes_41 | security-crypto 1.1.0 | 1.8.0 | idem |
| org.css_apps_m3.password_manager_16 | security-crypto 1.1.0 | 1.8.0 | idem + Hkdf:59/65 |
| org.openhab.habdroid_589 | security-crypto 1.0.0 | tink-android 1.5.0 | PrfAesCmac:50/62/103, AesSiv:109 |
| com.hegocre.nextcloudpasswords_38 | dev.spght:encryptedprefs-ktx 1.1.1 → encryptedprefs-core 1.1.1 | tink-android 1.19.0 | prf.internal.PrfAesCmac:76/106/155, AesSiv:191 |

Nos três pontos que importam — a origem da chave, a do IV e a construção CMAC — o código de 1.5.0 e o de 1.8.0 são idênticos; só as linhas mudam, por 7 a 10. Em 1.19.0 o código foi reorganizado: `create(AesSivKey)`, `ThreadLocal<Cipher>`, `encryptInternal`. A semântica é a mesma.

## Como os apps chegam ao tink

Todos os oito APKs usam `EncryptedSharedPreferences` com `PrefKeyEncryptionScheme.AES256_SIV`. Os arquivos:

- `app/src/main/java/app/maskan/chat/data/repository/EncryptedPrefsFactory.kt:30-35`
- `PrefsUtil.java:119-124` (bitbanana)
- `BasePreferences.kt:237-242` (quicksearch)
- `CredentialStore.kt:40-45` (simplenotes)
- `UnlockScreen.kt:47-52` e `SettingsScreen.kt:698-703` (password_manager)
- `OpenHabApplication.kt:78-83` (openhab)
- `PreferencesManager.kt:32-37` (nextcloudpasswords, pelo fork dev.spght)

O password_manager também usa `EncryptedFile` com `AES256_GCM_HKDF_4KB`, em `PasswordRepository.kt:42-49,57-64`. É esse uso que alcança o `Hkdf`.

O `EncryptedSharedPreferences` cifra o **nome** de cada preferência com o AEAD determinístico. O valor é cifrado com AES-GCM:

```java
// security-crypto-1.1.0/androidx/security/crypto/EncryptedSharedPreferences.java:604-606
byte[] encryptedKeyBytes = mKeyDeterministicAead.encryptDeterministically(
        key.getBytes(UTF_8),
        mFileName.getBytes());
```

O keyset do DAEAD fica em SharedPreferences, cifrado pela master key AES-GCM do Android Keystore (`EncryptedSharedPreferences.java:165-177`; `tink-android-1.8.0/.../integration/android/AndroidKeysetManager.java:287-297`). Se não existe, é gerado uma vez com `Random.randBytes(64)` (`AesSivKeyManager.java:117`).

## Métodos 93 e 94 — AesSiv.encryptDeterministically / encryptInternal

```java
// tink-android-1.8.0/com/google/crypto/tink/subtle/AesSiv.java:113-122
Cipher aesCtr = EngineFactory.CIPHER.getInstance("AES/CTR/NoPadding");
byte[] computedIv = s2v(associatedData, plaintext);
byte[] ivForJavaCrypto = computedIv.clone();
ivForJavaCrypto[8] &= (byte) 0x7F; // 63th bit from the right
ivForJavaCrypto[12] &= (byte) 0x7F; // 31st bit from the right
aesCtr.init(
    Cipher.ENCRYPT_MODE,
    new SecretKeySpec(this.aesCtrKey, "AES"),
    new IvParameterSpec(ivForJavaCrypto));
```

Em 1.19.0 o trecho equivalente está em `AesSiv.java:183-194`, com `s2v(s)` sobre `associatedDatas ‖ plaintext`. Em 1.5.0, em `AesSiv.java:103-112`.

**A chave (`aesCtrKey`).** O caminho de volta é este:

1. `AesSiv(byte[] key)` faz `this.aesCtrKey = Arrays.copyOfRange(key, 32, 64)` (`AesSiv.java:69-71`).
2. `key` vem de `AesSivKeyManager.java:53`, `new AesSiv(key.getKeyValue().toByteArray())`. Em 1.19.0 vem de `AesSiv.create`, com `key.getKeyBytes().toByteArray(...)` (`AesSiv.java:75-78`).
3. Esse `ByteString` é desserializado do keyset, que o `AndroidKeysetManager` lê de SharedPreferences e decifra com a master key do Keystore.

Não há `getEncoded()` no caminho, e há pelo menos duas cópias. **SECRETKEYSPEC-NOBS-00 → LEGIT_UNOBSERVABLE (key_from_keyset).** O mesmo vale para a primeira execução, em que a chave é gerada: bytes de SecureRandom levariam `RANDOMIZED`, não `PREPARED_KEY_MATERIAL`, e ainda passam por `ByteString.copyFrom`.

O **CIPHER-NOBS-00** é cascata. Como a construção não conformou (`SecretKeySpecSpec.mop:116-124`), o `@match` não grava `GENERATED_KEY` (`:256`), e `CipherSpec.i2` (`:199-233`) responde NOT_OBSERVED. A raiz é o SECRETKEYSPEC-NOBS-00 do mesmo método.

**O IV.** `computedIv = S2V(K1, AD, P)` é a cadeia de CMACs do RFC 5297 §2.4, feita com `PrfAesCmac.compute` (AES-ECB por bloco). O valor é clonado e tem os bits 63 e 31 zerados, exatamente como o §2.6 manda para formar o contador Q do CTR. É **determinístico por projeto**. O AES-SIV é um AEAD determinístico, resistente a reuso de nonce: o IV sintético é um PRF de (AD, P) e só revela quando dois pares (nome do arquivo, nome da preferência) são idênticos. O `EncryptedSharedPreferences` precisa exatamente disso para achar a preferência pelo nome cifrado. A exigência genérica `randomized[iv]` (`IvParameterSpec.mop:68`) e o `preparedIV` para CTR em cifração (`IvChainJunction.mop:155-160`) não descrevem o que a construção requer.

O IV sai de computação em código tecido (`Cipher.doFinal` + `clone`), mas nenhuma especificação poderia creditá-lo como produtor sem absolver também IVs derivados num CTR comum, onde seriam uso indevido. O reparo cabível é uma exceção para o CTR interno do SIV, não um produtor novo. Por isso: **IVPARAMETERSPEC-NOBS-00 → SPEC_DEFECT (siv_synthetic_iv_by_design)**, e **IVCHAINJUNCTION-NOBS-00 → SPEC_DEFECT (cascata dele)**. `PREPARED_IV` só é gravado quando `RANDOMIZED` foi SATISFIED (`IvParameterSpec.mop:77-79,153`).

A confiança é alta em "não é misuse" e média na escolha entre SPEC_DEFECT e LEGIT_UNOBSERVABLE.

## Método 92 — AesSiv.decryptDeterministically (só maskan, 1.8.0)

```java
// AesSiv.java:137-146
byte[] expectedIv = Arrays.copyOfRange(ciphertext, 0, AesUtil.BLOCK_SIZE);
byte[] ivForJavaCrypto = expectedIv.clone();
...
aesCtr.init(Cipher.DECRYPT_MODE, new SecretKeySpec(this.aesCtrKey, "AES"), new IvParameterSpec(ivForJavaCrypto));
```

O IV sai dos 16 primeiros bytes do texto cifrado, a string Base64 guardada como nome da preferência. Depois ele é recomputado por S2V e comparado como tag (`:156-161`). **IVPARAMETERSPEC-NOBS-00 → LEGIT_UNOBSERVABLE (iv_from_ciphertext).** Não há IVCHAINJUNCTION aqui porque o spec exige `encmode == 1`.

A chave é a mesma dos métodos 93 e 94. **SECRETKEYSPEC-NOBS-00 → LEGIT_UNOBSERVABLE (key_from_keyset)**, e **CIPHER-NOBS-00 → cascata**.

## Métodos 96–98 (subtle, 1.8.0/1.5.0) e 83–85 (prf.internal, 1.19.0) — PrfAesCmac

```java
// tink-android-1.8.0/com/google/crypto/tink/subtle/PrfAesCmac.java:54-58, 68-69, 108-112
public PrfAesCmac(final byte[] key) ... { keySpec = new SecretKeySpec(key, "AES"); generateSubKeys(); }
Cipher aes = instance();            // AES/ECB/NoPadding
aes.init(Cipher.ENCRYPT_MODE, keySpec);
...
byte[] zeroes = new byte[AesUtil.BLOCK_SIZE];
byte[] l = aes.doFinal(zeroes);
```

Em 1.19.0: `prf/internal/PrfAesCmac.java:73-77, 105-106, 153-157`.

A chave é `k1 = Arrays.copyOfRange(key, 0, 32)` da chave AES-SIV do keyset (`AesSiv.java:69-71`). Em 1.19.0 ela ainda passa por `SecretBytes.copyFrom` e por `toByteArray` (`AesSiv.java:94-99,123-125`; `PrfAesCmac.java:80-82`). **SECRETKEYSPEC-NOBS-00 → LEGIT_UNOBSERVABLE (key_from_keyset).**

Os **CIPHER-NOBS-00** de `compute` e `generateSubKeys` usam o campo `keySpec` construído no `<init>`. São cascata do SECRETKEYSPEC-NOBS-00 do construtor.

O uso de AES-ECB sobre um bloco é o próprio CMAC do RFC 4493, e cifrar o bloco zero é a derivação das subchaves (§2.3). Isso rende CIPHER-ALG-01 nesses sítios, que não é código NOBS e fica fora deste grupo.

Em openhab (1.5.0), o construtor aparece em 214 execuções e `compute` em só 1. O primitivo é criado quando o `EncryptedSharedPreferences` é aberto, mas quase nenhuma execução chega a cifrar um nome.

## Método 95 — Hkdf.computeHkdf (password_manager, 1.8.0, EncryptedFile)

```java
// tink-android-1.8.0/com/google/crypto/tink/subtle/Hkdf.java:54-65
if (salt == null || salt.length == 0) {
  mac.init(new SecretKeySpec(new byte[mac.getMacLength()], macAlgorithm));   // :57, sem linhas
} else {
  mac.init(new SecretKeySpec(salt, macAlgorithm));                           // :59
}
byte[] prk = mac.doFinal(ikm);
...
mac.init(new SecretKeySpec(prk, macAlgorithm));                              // :65
```

Quem chama é `AesGcmHkdfStreaming.deriveKeySpec` (`:190-193`), no mesmo segundo das linhas `AesGcmHkdfStreaming.deriveKeySpec:192` e `AesGcmHkdfStreamEncrypter.encryptSegment:234`. A cadeia vem de `EncryptedFile.openFileOutput()`/`openFileInput()` em `PasswordRepository.kt`.

- **Linha 59 (salt).** Na cifração, `salt = randomSalt()` = `Random.randBytes(32)` (`AesGcmHkdfStreaming.java:172-174, 211, 218`; `Random.java:41-45`): aleatório e novo por arquivo. Na decifração, o salt é lido do cabeçalho (`:287-290`). As 34 execuções com Hkdf coincidem com as 34 do encrypter; o decrypter aparece em 14. O caminho dominante, portanto, é o do salt aleatório. No HKDF (RFC 5869 §2.2, §3.1) o salt é a chave HMAC do passo extract e não é secreto.
- **Linha 65 (PRK).** `prk = mac.doFinal(ikm)` é pseudoaleatório. O `ikm` é a chave do keyset do EncryptedFile, copiada em `AesGcmHkdfStreaming.java:105`.

Os dois objetos estão corretos para a construção e nascem em código tecido: `SecureRandom.nextBytes` e `Mac.doFinal`. Mas nenhuma especificação faz de bytes aleatórios ou de uma saída de Mac um produtor de `PREPARED_KEY_MATERIAL`, e `SecretKeySpecSpec.mop:79-91` registra essa escolha. **SECRETKEYSPEC-NOBS-00 → SPEC_DEFECT (producer_missing_in_specset).** O caminho de decifração da linha 59 seria LEGIT (salt do cabeçalho).

O **MAC-NOBS-00** (`MacSpec.mop:179,184-187`, via `validateAny(GENERATED_KEY)`) é cascata do SecretKeySpec não conforme das mesmas linhas.

## Padrões

1. **Tudo passa pelo EncryptedSharedPreferences/EncryptedFile.** Nenhum dos oito apps chama o tink diretamente. As chaves sempre vêm de um keyset protegido pelo Android Keystore e perdem a identidade em `toByteArray`/`copyOfRange`. Cada primitivo AES-SIV instanciado produz 4 SECRETKEYSPEC/CIPHER-NOBS: o construtor do CMAC, as subchaves, `compute` e o CTR.
2. **O IV do SIV é um falso positivo estrutural da regra de Cipher.** Ele aparece em todo app com `AES256_SIV`: 8 dos 8 APKs, 1 230 linhas em cada um dos dois códigos de IV, somando 93 e 94. O falso positivo não vem de alcance da instrumentação: nenhum produtor o curaria sem abrir brecha para CTR com IV derivado.
3. **As cascatas CIPHER-NOBS-00 e MAC-NOBS-00 herdam integralmente o SECRETKEYSPEC-NOBS-00 do mesmo objeto.** Um reparo na raiz — por exemplo, preparar mesmo sob NOT_OBSERVED — elimina metade das linhas deste grupo.

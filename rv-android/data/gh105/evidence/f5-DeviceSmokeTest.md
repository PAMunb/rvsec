# Tarefa 8.5 — a passagem de dispositivo

**Data**: 2026-08-23 · **Commit da árvore**: `519f2ff8` · **Conjunto**: `jca_android` (24 `.mop`)
**Variante de instrumentação**: `dexlib2` (caminho de host) · **APK**: `apks_examples/cryptoapp.apk`
**Emulador**: gerido inteiramente pelo `rv-experiment`/`rv-platform`, `--no-window`. Nenhum comando
de emulador foi dado à mão.

A tarefa pede três medições: (a) o probe R4 sobre `equals` de `OpenSSLRSAPublicKey`/`BCRSAPublicKey`;
(b) a junção do idioma `Object` disparando num trace real pelo caminho dexlib2; (c) o co-disparo
junção × `CipherSpec` no mesmo joinpoint de `Cipher.init`, com as contagens de report commitadas.

**Duas foram respondidas, e uma delas de forma mais forte do que o enunciado pedia. A terceira
tem a metade estrutural provada e a metade dinâmica não alcançada, e isso está escrito como
limite de alcance da exploração, não como resultado.**

---

## 1. As quatro passagens

| passagem | ferramenta | tempo | violações | métodos cobertos |
|---|---|---|---|---|
| 1 | `monkey` | 120 s | **3** | 47 |
| 2 | `ape` | 300 s | **9** | 62 |
| 3 | `monkey`, rep 1 | 300 s | 0 | 17 |
| 3 | `monkey`, rep 2 | 300 s | 0 | 7 |
| 4 | `droidbot:dfs_greedy` | 300 s | — | logcat vazio (a ferramenta não produziu sessão; defeito dela, não do conjunto) |

A passagem 1 gerou monitores e instrumentou; as demais reusaram o APK instrumentado
(`--skip-monitors --skip-instrument`). A instrumentação: **126 advices, 36 matches aplicados,
88 wrappers gerados, 6 dex tecidos + 1 dex de monitor, 0 planos pulados**.

### As 12 acusações, por código

| código | n | onde |
|---|---|---|
| `SECRETKEYSPEC-NOBS-00` | 4 | `CryptographyActivity.executeSecretKeyOperation`/`executeHmacOperation`, `CipherUtil.aes` |
| `CIPHER-NOBS-00` | 3 | `CryptographyActivity.encryptWithSecretKey`, `CipherUtil.aes`/`des` |
| `CIPHER-ORDER-00` | 2 | `CipherUtil.des` |
| `KEYGENERATOR-ORDER-00` | 1 | `CipherUtil.des` |
| `KEYGENERATOR-ALG-00` | 1 | `CipherUtil.des` — `val='DES'` contra a lista da api30 |
| `CIPHER-ALG-01` | 1 | `CipherUtil.des` — `val='DES'` contra `Api30CipherTransformationUtil` |

**Sete das doze são leituras de predicado do armazém novo** (`*-NOBS-*`), que é a cadeia que esta
change fia: num dispositivo real, `PredicateStore.validate` devolveu `NOT_OBSERVED` e a acusação
saiu com envelope `v=1` completo, código, valor observado e expectativa. Todas as doze linhas
carregam o envelope; **nenhuma diz `unknown`**.

## 2. (a) O probe R4 — respondido, e por construção

A pergunta aberta (design, Open Question 1) é se `OpenSSLRSAPublicKey`/`BCRSAPublicKey`
sobrescrevem `equals` por valor, porque isso mudaria a análise identidade-vs-valor das leituras
de `GENERATED_KEY`.

**A premissa é real.** `AndroidKeyStoreRSAPublicKey` estende `AndroidKeyStorePublicKey`, cujo
`equals` é **por valor** — compara os bytes do certificado e da cadeia, mais o `super`
(fonte na SDK deste host: `sources/android-33/android/security/keystore2/AndroidKeyStorePublicKey.java:72-86`).
Chaves públicas de `AndroidKeyStore` são, portanto, iguais por valor.

**E não muda nada.** O `PredicateStore` **nunca consulta `equals` do objeto ligado**:

```java
private static final class BoundKey extends WeakReference<Object> {
    private BoundKey(Object referent) { super(referent); hash = System.identityHashCode(referent); }
    @Override public int hashCode() { return hash; }
    @Override public boolean equals(Object other) {
        …
        Object mine = get();
        return mine != null && mine == ((BoundKey) other).get();   // identidade, não equals
    }
}
```

O javadoc da classe registra a razão, e é exatamente a do R4: *"A store keyed by `equals` answers
about a different object whenever the API defines value equality — two `SecretKeySpec`s over the
same bytes are `equals`, and one of them being securely generated said nothing about the other."*
Só posições de valor cujo tipo declarado é `String`, `int` ou `Integer` são comparadas por valor;
**toda outra posição, e o objeto ligado, por identidade**.

Logo o R4 está fechado: qualquer que seja o `equals` das duas classes, o veredicto do conjunto
fiado é o mesmo. Isso é mais forte do que a medição pediria — a medição diria o que as classes
fazem; isto diz que o que elas fazem não alcança o conjunto.

**Limite de alcance, escrito e não subentendido**: as classes `com.android.org.conscrypt.OpenSSLRSAPublicKey`
e `org.bouncycastle.jcajce.provider.asymmetric.rsa.BCRSAPublicKey` **não existem em disco neste
host** (a SDK não traz fontes do Conscrypt; o `android.jar` não expõe o pacote), e nenhuma das
quatro passagens ligou uma chave RSA — o caminho `encryptWithPublicKey` do APK não foi
alcançado. A resposta acima é sobre o consumidor, não sobre as duas classes.

## 3. (b) A junção tecida pelo caminho dexlib2

Lido do APK instrumentado com `dexdump`, **nas classes da aplicação e não no dex do monitor**:

```
classes4.dex  →  4 × invoke-static IvChainJunctionSpec_useEvent
                 em CryptoUtils.encryptWithSecretKey / .decryptWithSecretKey
                 e CryptographyActivity.encryptWithSecretKey / .decryptWithSecretKey
```

com a assinatura **inteira preservada**:

```
Lmop/MultiSpec_1RuntimeMonitor;.IvChainJunctionSpec_useEvent:(ILjava/security/spec/AlgorithmParameterSpec;Ljavax/crypto/Cipher;)V
```

Três parâmetros, na ordem e nos tipos que o `.mop` declara. **É a medida que importa**: o colapso
de lista de parâmetros que o D-10 documenta (e que G-PARAM guarda) não aconteceu no caminho de
host — nem na geração, nem na tecelagem. Os quatro sítios batem exatamente com as quatro chamadas
de `Cipher.init(int, Key, AlgorithmParameterSpec)` que o APK original tem (contadas com `dexdump`
no APK de partida).

**O que não foi alcançado, e por quê.** O `use` só executa no ramo CBC/IV de
`encryptWithSecretKey`. A passagem 1 **executou esse método** — o `RVSEC-COV` registra
`CryptographyActivity.encryptWithSecretKey` e o `CipherSpec` acusou lá —, mas pelo **outro ramo**:
o método tem duas rotas, uma com `Cipher.init(int, Key)` e outra com
`Cipher.init(int, Key, AlgorithmParameterSpec)`, e o grupo de rádio de modo do app decide qual.
Nenhuma das quatro ferramentas virou esse rádio. É limite da exploração aleatória sobre este APK,
não da cadeia: o sítio está tecido, o método foi executado, e o ramo não foi escolhido.

**E um disparo do `use` não produziria linha de log por si só.** O corpo só acusa quando
`encmode == 1`, o modo está em `ivModes` e `preparedIV` não foi observado; com
`new IvParameterSpec(...)` imediatamente antes no mesmo método — o `IvParameterSpecSpec_c1Event`
está tecido três instruções acima —, a cadeia compõe e o silêncio é a resposta certa. Observar o
disparo pediria um APK cujo IV não passe pelo produtor, e escrevê-lo é fabricar o sujeito da
medição.

## 4. (c) O co-disparo junção × `CipherSpec`, no mesmo joinpoint

Provado no bytecode tecido. Em cada um dos quatro sítios, a sequência é:

```
003c: invoke-static {v7, v3}, …IvParameterSpecSpec_c1Event:([BLjavax/crypto/spec/IvParameterSpec;)V
003f: invoke-static {v1, v3, v2}, …IvChainJunctionSpec_useEvent:(ILjava/security/spec/AlgorithmParameterSpec;Ljavax/crypto/Cipher;)V
0042: invoke-static {v1, v5, v2}, …CipherSpec_i2Event:(ILjava/security/Key;Ljavax/crypto/Cipher;)V
0045: invoke-virtual {v2, v1, v5, v3}, Ljavax/crypto/Cipher;.init:(ILjava/security/Key;Ljava/security/spec/AlgorithmParameterSpec;)V
```

**Duas especificações no mesmo joinpoint**, ambas `before`, uma imediatamente após a outra e
ambas antes da chamada monitorada — que é a forma que o risco do design descreve: o nome próprio
da junção abre um balde de má utilização única novo no mesmo `(classe, método)` que o
`CipherSpec` já ocupa. A ordem é determinada pela tecelagem e é estável no artefato commitado.

**As contagens de report** estão na tabela da secção 1 e nos logcats sob
`results/gh105_smoke_85*/cryptoapp.apk/`. O co-disparo **dinâmico** neste joinpoint não foi
observado, pela mesma razão da secção 3: o ramo não foi escolhido. O que se observou foi o
`CipherSpec.i2` acusando no ramo de duas posições — `CIPHER-NOBS-00`, três vezes.

## 5. O que fica para o experimento conjunto

Duas coisas, e nenhuma bloqueia esta change:

1. **O disparo dinâmico da junção** pede um APK cujo caminho de IV seja alcançável por exploração
   automática, ou um cujo IV não venha de um `IvParameterSpec` recém-construído. A campanha da
   gh104 roda sobre um corpus de APKs reais, que é onde essa forma aparece sem ser fabricada.
2. **Uma chave RSA ligada num dispositivo**, que fecharia o R4 pelo lado das duas classes — hoje
   fechado pelo lado do consumidor, que é o lado que decide.

## 6. O que esta passagem prova, em uma linha cada

- O conjunto fiado **instrumenta, tece e roda** num dispositivo pelo caminho dexlib2, com 126
  advices e zero planos pulados.
- As leituras de predicado do armazém novo **funcionam num dispositivo real**: sete das doze
  acusações são `*-NOBS-*`, com envelope completo.
- A junção está **tecida em sítios reais da aplicação com a lista de parâmetros intacta** — o
  colapso que motivou G-PARAM não ocorre no caminho de host.
- A junção e o `CipherSpec` estão **co-tecidos no mesmo joinpoint de `Cipher.init`**.
- O R4 **não pode mudar veredicto**, porque o armazém chaveia por identidade e nunca chama
  `equals` do objeto ligado.

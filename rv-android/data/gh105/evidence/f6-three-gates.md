# Tarefa 9.7 — G-SIG, G-FORB e G-BIND, com o caminho vermelho de cada um

**Data**: 2026-08-25 · **Commit da árvore**: `70877f67`
**Instrumento**: `scripts/gh105_spec_gates.py` · **universo**: os 5 conjuntos enumerados em
`SPECIFICATION_SETS` · **oráculos**: `RVSec-replication-package/tools/rules/` (expert) e
`MetaCrySL/generated/api30/` · **plataforma**: `$ANDROID_HOME/platforms/android-30/android.jar`

## 1. O resultado

```
G-SIG:  416 checked,  1 failed,  7 allow-listed,  7 skipped, 16 notes
G-FORB:  18 checked,  2 failed, 12 allow-listed, 14 skipped,  0 notes
G-BIND: 843 checked,  0 failed,  3 allow-listed, 24 skipped,  0 notes
```

Os três achados vivos são, **todos**, defeitos de tarefas do bloco 9.B que aguardam decisão do
pesquisador: o único do G-SIG é a 9.1 e os dois do G-FORB são a 9.9 (um por oráculo). Nenhum é
novo e nenhum é surpresa; o que os gates entregam é que a partir de agora eles falham sozinhos.

## 2. G-SIG — a assinatura contra a plataforma

O defeito de origem: `SSLContextSpec.mop` declarava
`call(public void SSLContext.createSSLEngine(..))` onde o android-30 declara
`public final SSLEngine createSSLEngine()`. Ambos os tecelões filtram o tipo de retorno
exatamente, então o advice é gerado e **nunca disparou** — evento presente no autômato,
presente no monitor, morto. Nove grupos de tarefas leram o arquivo sem ver.

### As três guardas de desenho, e o que cada uma custa se faltar

1. **Presença de classe vem das entradas do zip, nunca do `javap`.** Medido: `javap` resolve
   `javax.xml.crypto.dsig.spec.HMACParameterSpec` **dos módulos do próprio JDK** com `-cp`
   apontando só para o android.jar, e nem `--system none` nem `-bootclasspath` impedem num JDK
   modular. O android-30.jar tem **zero** entradas sob `javax/xml/crypto`. Um G-SIG ingênuo
   declararia presente exatamente a classe que o registro sabe ausente
   (`conformance_record.csv:73`).
2. **Membro herdado resolve pela hierarquia.** Sem isso, três achados que são código correto:
   `SecretKey.getEncoded` vem de `Key`; `SecureRandom.nextInt` e `ints` vêm de `Random`.
   Saem como notas, não como falhas.
3. **Tipo aninhado compara por nome simples dos dois separadores.** `KeyStore.getEntry` devolve
   `java.security.KeyStore$Entry` e o pointcut escreve `Entry`; sem isso, o segundo achado de
   tipo de retorno do conjunto seria falso.

Uma quarta correção veio da primeira execução: `javap` imprime construtor sob o **nome
qualificado da própria classe** (`public javax.crypto.spec.PBEKeySpec(char[]);`) e método sob o
nome nu. Tratar os dois igual reportava **15** pointcuts de construtor como não-teceíveis —
todos código correto.

### Escopo

O gate compara assinatura contra um jar, então um conjunto escrito contra outra plataforma está
fora do seu alcance e diz isso. `generic` (118 `.mop`) e `generic_new` (27) são
especificações JSE — Swing, JMX, `java.util` — e a plataforma delas é o JDK; este gate
**deliberadamente não tem oráculo de JDK**, porque o `javap` resolvendo dos módulos do JDK é
justamente o fallback que ele existe para recusar. São skips declarados e contados. Sem esse
escopo o gate produzia 275 achados que não são defeitos.

### Caminho vermelho, e o que ele encontrou por conta própria

Mutação num pointcut que passava (`MacSpec.g1`/`g3`, `Mac` → `Cipher`):

```
G-SIG: 139 checked, 3 failed     (o da 9.1 + os dois mutados)
```

Revertido, volta a 1. Mas o gate também é **vermelho por si só sobre o conjunto congelado**, e
o que ele acha lá é a prova mais forte de que funciona — três defeitos reais que esta change já
tinha reparado, encontrados sem que ninguém lhe dissesse onde olhar:

| conjunto | sítio | pointcut | android-30 |
|---|---|---|---|
| `jca` | `SignatureSpec.s1:99` | `public byte Signature.sign()` | `byte[] sign()` |
| `jca` | `SignatureSpec.s2:106` | `public byte Signature.sign(byte[], int, int)` | `int sign(...)` |
| `jca` | `TrustManagerFactorySpec.gtm1:63` | `public KeyManager[] ...getTrustManagers()` | `TrustManager[]` |

O terceiro é o defeito pontual que a `proposal.md` nomeia em F4 — e o mesmo evento ainda liga
`returning(TrustManager[][] trustManager)` e escreve `GENERATED_KEY_MANAGERS`. Os três estão
reparados no sucessor. Como o `jca` é byte-congelado (INV-INS-109/118), viram linhas de
`gate_allowlist.csv` com a razão e o reparo correspondente nomeados; o mesmo para os três que
o arquivado `jca_android_bug_predicate` herdou.

## 3. G-FORB — a cláusula FORBIDDEN sem acusador

### A contagem que a tarefa trazia estava errada, e o escopo é o que a salva

Cada oráculo tem **quatro** regras com seção `FORBIDDEN`, não duas: além de `PBEKeySpec` (dois
construtores) e `SSLContext` (`getDefault()`), também `DigestInputStream` e
`DigestOutputStream` declaram `FORBIDDEN on(...)`. Nenhuma das duas últimas tem `.mop` em
conjunto algum — estão entre as 27 regras fora do escopo desta change. Sem escopo, o gate
nasceria vermelho em cláusula que tarefa nenhuma possui. Com escopo, são **skips declarados e
contados** (4 por conjunto do universo JCA).

O gate também exige aridade: `PBEKeySpec` proíbe dois dos seus quatro construtores e mantém o
de quatro argumentos como o evento sobre o qual a ORDER da regra é escrita. Casar só por nome
creditaria o `c1` conforme com acusar o construtor proibido, e o gate passaria num conjunto
que não proíbe nada.

### Os dois achados vivos

```
[G-FORB] jca_android/SSLContextSpec.getDefault: expert forbids getDefault() => Get ...
[G-FORB] jca_android/SSLContextSpec.getDefault: api30  forbids getDefault() => Gets ...
```

É a 9.9, exatamente. **O gate fica vermelho até que a 9.9 seja decidida** — ou a tarefa é
aprovada e ele fecha, ou o adiamento ganha a sua linha de `gate_allowlist.csv`, como as nove
divergências de ordenação que esta change já mantém de propósito. Não há terceira via honesta.

### Caminho vermelho

Mutação: `PBEKeySpecSpec.f1` deixa de levantar `ErrorType.ForbiddenMethod`.

```
G-FORB: 6 checked, 4 failed   (os dois da 9.9 + os dois do f1 mutado, um por oráculo)
```

Revertido, volta a 2. E de novo o conjunto congelado paga por si: o `jca` declara `f1` e `f2`
sobre exatamente os dois construtores proibidos, mas os corpos levantam
`InvalidSequenceOfMethodCalls` — uma construção proibida é reportada como sequência errada e
nunca como método proibido. Allow-listado por congelamento, com o reparo do sucessor
(`PBEKEYSPEC-FORB-00/01`) nomeado na razão.

## 4. G-BIND — evento paramétrico sem objeto ligado

```
G-BIND: 843 checked, 0 failed, 3 allow-listed, 24 skipped
```

Verde sobre o universo depois da 9.3. Vermelho sobre o instantâneo pré-9.3, com exatamente os
dois sítios e nenhum outro. Detalhe completo em `f6-PBEKeySpecSpec-binding.md`.

Uma especificação **não-paramétrica** é skip, não passe: o gerador emite um monitor único por
declaração, então "não liga objeto" é o que todos os seus eventos fazem, e um achado ali seria
ruído. São 24 — as duas de `Cipher*Stream` em cada conjunto JCA e 16 do `generic_new`, mais
dois arquivos com erro de parse.

## 5. O que ficou por verificar

- `jca/SecretKeySpecSpec.mop:30` e a sua cópia arquivada não são varridos: o parser
  compartilhado (`gh105_predicate_graph.read_mop`) recusa o arquivo por **parêntese
  desbalanceado** — há um `)` a mais no `condition(` do `c1`. É defeito real do conjunto
  congelado, não artefato do gate, e sai como skip nomeado. Não é reparável (freeze) e não
  pertence a esta tarefa.
- Nada foi rodado em emulador nem com o classpath Android completo. G-SIG lê o jar da
  plataforma; ele **não** prova o que o tecelão DEX faz, e as duas afirmações sobre o portão de
  tipo de retorno no caminho dexlib2 continuam aceitas do registro
  (`conformance_record.csv:62,:73`), não reproduzidas.

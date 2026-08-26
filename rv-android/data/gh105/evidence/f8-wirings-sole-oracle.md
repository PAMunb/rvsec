# Tarefa 11.5 — as fiações que o oráculo único restaura ou abre

**Data**: 2026-08-26 · **Grupo**: 11 (F8, D-16) · **Espécie**: decisão do pesquisador, por cláusula
**Oráculo único**: `RVSec-replication-package/tools/rules/` (49 regras, sha256 `d7bcc019…`)
**Disciplina**: 9.B — par de arnês, linha de divergência e go/no-go por cláusula

Este documento cresce por alínea. Cada seção fecha uma alínea da 11.5, diz o que foi **medido**
antes de propor, e diz qual das duas coisas a decisão foi: **fiar** (um sítio novo, acusação nova,
par de arnês devido) ou **registrar** (nenhum sítio, nenhuma acusação, nenhum par devido).

A decisão de 26/08 que rege todas elas, na formulação do pesquisador: **manter aderência à regra
CrySL como está na regra**. Isso não resolve as alíneas todas para o mesmo lado, e é essa a razão
de a tarefa ser por cláusula. Onde os dois lados da cláusula existem no conjunto, aderir é *fiar*.
Onde o oráculo não tem produtor que este conjunto possa observar, aderir é *registrar* — fiar ali
acrescentaria uma acusação que a regra não licencia, porque o único veredito alcançável seria
`NOT_OBSERVED`, que é a forma dos dezessete acusadores órfãos que o grupo 3 removeu.

---

## 1. As três alíneas que se registram (c, d, e2)

Um commit só, sem par de arnês: nenhum `.mop` ganha ou perde sítio, nenhuma acusação muda de
classe. O que se move é o ledger, a prosa que o cita, e o comentário ao lado de cada sítio que a
decisão nomeia.

### 1.1 (c) `TrustManagerFactory generatedManagerFactoryParameters[params]`

`TrustManagerFactory.crysl:29` · ledger #56 · **`unmonitored-producer`, derivado** · **registrar**

A derivação, por enumeração e não por suposição: o predicado é `ENSURES` por exatamente **duas**
regras do oráculo,

```
CertPathTrustManagerParameters.crysl:17   ENSURES generatedManagerFactoryParameters[this]   (ledger #61)
KeyStoreBuilderParameters.crysl:14        ENSURES generatedManagerFactoryParameters[this]   (ledger #98)
```

e **nenhuma das duas tem `.mop`** neste conjunto — as duas linhas do ledger leem
`unmonitored-producer-side`. O instrumento chega a `unmonitored-producer` sozinho; não há
*override*.

O que torna a alínea necessária é a **baratice do sítio**, não a sua dificuldade. O
`TrustManagerFactorySpec.init` já funde `init(KeyStore)` e `init(ManagerFactoryParameters)` num
evento e já discrimina por tipo em tempo de execução; a leitura caberia em três linhas, no ramo
que o `if (arg == null || arg instanceof KeyStore)` deixa vazio. É exatamente por caber que a
conclusão tinha de ser derivada: uma leitura ali responde `NOT_OBSERVED` para todo programa do
mundo, sempre, porque o objeto que a satisfaria só pode vir de duas classes que este conjunto não
observa.

A cláusula gêmea em `KeyManagerFactory.crysl:32` (ledger #29) carrega a mesma disposição pelas
mesmas duas regras produtoras. A simetria não é coincidência a ser arrumada: é a mesma cláusula
escrita em duas regras irmãs.

Onde ficou escrito: o comentário acima do `if` em `TrustManagerFactorySpec.mop`, a linha #56 do
`predicate_ledger.csv`, e a seção *The clauses task 11.5 records instead of wiring* do
`predicate_ledger.md`.

### 1.2 (d) `SecureRandom randomized[lSeed]` — a disposição que se move

`SecureRandom.crysl:46` · ledger #51 · **`wireable` → `vacuous`** · **registrar**

Esta é a única disposição que a 11.5 move, e ela se move por medição. Duas razões independentes,
cada uma suficiente sozinha.

**Por tipo.** Varri as 49 regras atrás de toda cláusula que garante `randomized`. São cinco, todas
em `SecureRandom.crysl`, e **nenhuma sobre um `long`**:

```
SecureRandom.crysl:49   ENSURES randomized[this] after Ins              this            SecureRandom
SecureRandom.crysl:50   ENSURES randomized[genSeed] after gS            genSeed         byte[]
SecureRandom.crysl:51   ENSURES randomized[bytes] after nB              bytes           byte[]
SecureRandom.crysl:52   ENSURES randomized[randInt] after nI            randInt         int
SecureRandom.crysl:53   ENSURES randomized[randIntInRange] after nIR    randIntInRange  int
```

Nenhum produtor do catálogo poderia marcar o argumento que `s2: setSeed(lSeed)` binda. Não é uma
lacuna de `.mop`: é uma lacuna do próprio oráculo, e por isso a disposição é `vacuous` e não
`unmonitored-producer`.

**Por substrato.** O `PredicateStore` chaveia o objeto bindado por **identidade**, e um `long`
chega ao *advice* boxado. Medido em Temurin 21 (`LongProbe`):

```
in-cache  identity 42L vs 42L      : true      <- dois setSeed(42L) sem relação partilham UM objeto
out-cache identity 1234567L twice  : false     <- fora da faixa, cada chamada boxa um objeto novo
boxed type                         : java.lang.Long
cache bound low/high               : true/true   next=false     <- a faixa e -128..127
byte[] identity (contraste)        : true
```

O boxing erra nos dois sentidos: **fora** da faixa, nenhuma escrita pode ter nomeado o objeto que
a leitura recebe; **dentro** dela, uma marca feita para uma semente responde pela outra. É a
medição do cache de `Integer` dos grupos anteriores, re-derivada sobre `Long` e não copiada.

Consequência para a aritmética, dita em voz alta porque a 11.7 a confere: **135 cláusulas antes e
depois**; `wireable` 25 → 24 e `vacuous` 1 → 2. Uma linha atravessando, nenhuma aparecendo ou
saindo. O censo do `--emit census` acompanha: a metade requerida passa de 10 cláusulas / 9
predicados para **11 / 10**, porque uma cláusula positiva que nunca pode ser satisfeita é
precisamente uma cláusula que o conjunto não pode observar. A metade **negada** continua fora do
censo, e a distinção está escrita no instrumento: para `!pred[..]` a ausência *é* conformidade,
então uma cláusula que nada satisfaz é uma cláusula que nada viola.

A cláusula irmã `randomized[seed]` (`:45`, ledger #50) é outra linha e **é lida**, em dois sítios —
`c2` e `setSeed2` —, ambos sobre `byte[]`, onde a identidade vale. Ter as duas lado a lado é o que
mostra que a disposição desta é sobre o tipo e não sobre a regra.

Onde ficou escrito: o comentário acima do `setSeed1` em `SecureRandomSpec.mop`, o
`VACUITY_OVERRIDES` do `scripts/gh105_expert_ledger.py` (com a sua própria etiqueta, porque não é
carry-over da api30 e sim derivação desta tarefa), a linha #51 do CSV e o `predicate_ledger.md`.

### 1.3 (e2) `Cipher wrappedKey[wrappedKeyBytes, wrappedKey]`

`Cipher.crysl:148` · ledger #67 · **`unread`, derivado** · **registrar**

A regra do oráculo **garante** a cláusula onde o catálogo retirado não garantia nada — foi por isso
que o sítio voltou à mesa. Mas **nenhuma das 49 regras REQUIRES `wrappedKey`**, então uma escrita
em `CipherSpec.wkb1` produziria algo que nada pode consumir.

O veredito da 4.1 fica; o que muda é o chão. A 4.1 apagou a escrita porque o catálogo retirado não
nomeava o evento em `ENSURES` alguma; ela fica apagada porque o oráculo o nomeia numa cláusula cujo
predicado ninguém lê. É a D-17 outra vez: a frase caiu, o veredito não.

Fica na metade recíproca do censo, ao lado das outras oito cláusulas que o oráculo garante e que
regra nenhuma das 49 requer.

Onde ficou escrito: o comentário do `wkb1` em `CipherSpec.mop` — que apontava para "task 11.5(e)"
como pendência e agora nomeia a decisão —, a linha #67 do CSV e o `predicate_ledger.md`.

### 1.4 Portões, depois deste commit

```
G-ORACLE ................................ 30 file(s) read, 0 finding(s), 10 skipped
gh105_expert_conformance.py --check ..... exit 0
gh105_expert_ledger.py --check .......... exit 0   (135; REQUIRES 57 = 24+21+9+2+1)
gh105_expert_alphabet.py --check ........ exit 0
gh104_divergence_record.py --check ...... 307 hunk(s), all recorded
gh104_message_gate.py ................... ok (9 âncoras do codes.csv movidas e reconferidas)
gh104_mop_lint.py ....................... ok
gh105_predicate_graph.py ................ 24 read, 70 sites, 0 failing
gh105_spec_gates.py ..................... G-SIG 0 failed · G-FORB 0 failed · G-BIND 0 failed
```

Três hunks re-chavearam por posição (`rekey2.py`) e foram re-anotados: dois porque um bloco de
comentário vizinho reagrupou o diff (`CipherSpec`, `SecureRandomSpec`) e um porque o bloco novo
cresceu o próprio hunk pela primeira linha (`TrustManagerFactorySpec`).

---

## 2. (a) `Mac generatedKey[key,_]` — a cláusula volta, e não é reversão da 4.9

`Mac.crysl:54` · ledger #39 · **`wireable`** · **fiar** · par de arnês `harness/f8a-MacSpec.md`

### 2.1 A cláusula, e por que ela não existia

A regra `Mac` do oráculo tem **quatro** REQUIRES. O catálogo retirado declarava três —
`preparedHMAC[params]` e as duas `!encrypted[...]` — e nenhuma sobre a chave. A quarta é
`generatedKey[key,_]`, e ela binda exatamente o que os dois `init` bindam. O ledger a dispõe
`wireable` com três produtores especificados neste conjunto: `KeyGeneratorSpec`, `KeyStoreSpec` e
`SecretKeySpecSpec`.

A 4.9 apagou uma leitura desse mesmo predicado escrevendo que ela "não traduzia cláusula alguma".
Contra o catálogo retirado, era verdade. Contra o oráculo, é falsa — e é a D-17 outra vez: a frase
caiu, e desta vez a premissa que ela sustentava era o trabalho que **não** tinha sido feito.

### 2.2 O que volta é a cláusula, não a forma

O que a 4.9 apagou era um **guarda em `condition(...)`**, e um guarda compila no monitor gerado
como `if (!(leitura)) return false;` antes do `handleEvent`. Com ele de pé, o `init` não tomava
transição sempre que a chave vinha de gerador não observado, o `doFinal` chegava num estado que a
ORDER não admite, e o arquivo acusava o programa de `MAC-ORDER-00` — enquanto o `MAC-ALG-00`, que
mora no corpo, ficava calado porque o corpo não rodava.

**A leitura de agora está no corpo.** Ela reporta e não suprime. As duas traces que a 4.9 mediu
dizem isso no par de arnês desta passagem: `MacSpec-guard-on-field` (`init(null)`) passa de
`i1:MAC-ORDER-00` para `i1:MAC-NOBS-00, i1:MAC-ORDER-00`, e `MacSpec-hmacpbesha1` passa de nada
para `i1:MAC-NOBS-00`.

Da argumentação da 4.9 sobrevive a metade que era sobre a forma e não sobre a cláusula: a leitura
antiga não propagava nada — computava um veredito, descartava, e o único efeito que lhe restava era
a transição suprimida. Esta tem acusador próprio, que é o que o guarda nunca teve.

### 2.3 O lugar anônimo lido como anônimo — e o método que não existia

`Mac.crysl:54` escreve `generatedKey[key,_]`. Os três produtores escrevem **duas** posições. O
`PredicateStore.validate` compara a **tupla inteira**:

```java
return state.tuples.contains(new ValueTuple(values)) ? SATISFIED : VIOLATED;
```

Uma leitura sem valores compara contra a tupla vazia, que produtor nenhum registra — e responde
**`VIOLATED`** para toda chave conforme. Isto é, *evidência positiva de mau uso* sobre um programa
que não cometeu nenhum. O teste `aReadOfDifferentArityThanTheRecordIsAMismatchAndNotAMatch` já
documentava a armadilha desde o grupo 5.

Preencher o `_` no sítio de chamada **também não é a mesma cláusula**, e foi medido que não
funciona: os três produtores não concordam sobre o que escrevem ali.

```
KeyGeneratorSpec.mop:172,215   ensure(GENERATED_KEY, generatedKey, currentAlgorithmInstance)
                               ^ a string que o programa passou ao getInstance
KeyStoreSpec.mop:193           ensure(GENERATED_KEY, generatedKey, generatedKey.getAlgorithm())
SecretKeySpecSpec.mop:242      ensure(GENERATED_KEY, spec, specAlgorithm)
                               ^ o algoritmo da própria chave, nos dois
```

Um leitor que chutasse uma das grafias acusaria o programa que usasse a outra — e na Conscrypt as
duas convivem (`HmacSHA256` e `HMAC-SHA256` são a mesma coisa e não são a mesma `String`).

Então a tarefa acrescentou ao `PredicateStore` a leitura que a cláusula pede e nada mais larga:

```java
public PredicateVerdict validateAny(Property p, Object bound)
```

Ela **nomeia a propriedade** e é cega só para as posições que a própria regra deixa anônimas.
Não é o retorno da consulta ampla que o store recusa de propósito ("este objeto carrega algum
predicado?"), e a javadoc diz isso onde a recusa está escrita. O flag de retirada é honrado como no
`validate`: um predicado explicitamente negado é `VIOLATED` e não mera ausência.

Quatro testes novos no `PredicateStoreTest` (24/24 passam): o lugar anônimo satisfeito por qualquer
lista registrada; a cegueira à grafia do produtor; a retirada distinguida da não-observação; e que
a leitura continua sendo sobre **um** predicado e não sobre qualquer um.

### 2.4 O par de arnês

`data/gh105/evidence/harness/f8a-MacSpec.md` — **169 `unchanged` / 2 `moved` / 2 `introduced`** em
173 pares trace×spec. Só o `MacSpec` se move; os outros 23 relatórios do par leem `unchanged`
inteiros e não se commitam.

| trace | classe | o que muda |
|---|---|---|
| `MacSpec-hmacpbesha1` | introduced | `i1:MAC-NOBS-00` — `init(null)` |
| `MacSpec-ungenerated-key` | introduced | `i1:MAC-NOBS-00` — chave de um `bind new SecretKeySpec`, que o arnês produz sem despachar |
| `MacSpec-d15-hmacpbesha1` | moved | `i1:MAC-NOBS-00` ao lado do `MAC-ORDER-00` que já havia |
| `MacSpec-guard-on-field` | moved | idem |
| `MacSpec-decrypt-buffer`, `-encrypted-buffer`, `-fresh-buffer` | **unchanged** | a chave vem de `KeyGenerator.generateKey()` |
| `MacSpec`, `-unsafe-generated-key`, `-mac-then-encrypt`, `-update-then-encrypt` | unchanged | idem |

As três traces de buffer são a prova de que a leitura anônima faz o que se pediu dela: elas gravam
`generatedKey` com uma segunda posição e leem `SATISFIED`. Com um `validate` de tupla inteira elas
teriam virado `MAC-CONSTR-01` — sete acusações falsas onde o par mede zero.

### 2.5 O instrumento que não via o sítio

O `gh105_predicate_graph.py` monta a alternação de operações a partir das chaves do
`GRAPH_OPERATIONS`, e a alternação do `re` do Python é **leftmost-first**, não maior-casamento:
com `validate` antes de `validateAny`, o nome curto ganhava a alternativa, o `(` que tem de segui-lo
nunca chegava, e o sítio **não casava com nada** — sumia do inventário em silêncio. Está ordenada
por comprimento decrescente, com a razão escrita ao lado, e o censo passa de 70 para 72 sítios.
Um censo que não enxerga um sítio o reporta como ausente, que é o modo de falha que essa suíte
existe para pegar.

### 2.6 Contagens que se movem, ditas em voz alta

```
predicate_graph.csv .......... 70 -> 72 linhas   (read:body 33 -> 35, round-trip idêntico)
codes.csv .................... +4 códigos        (MAC-CONSTR-01/-02, MAC-NOBS-00/-01)
paridade ..................... read+read-absent 38 -> 40; read:body 33 -> 35
                               read:condition-guard fica em 0 -- e é essa a asserção que importa,
                               porque o sítio que a 4.9 apagou ERA um condition-guard
divergence_record.csv ........ 307 -> 306 hunks; 4 re-chaveados por posição, 1 absorvido
```

O hunk absorvido é o `b41d2fa9eab5` — o `}` que fecha o corpo do `i1`, a que a 11.4 tinha dado
linha própria quando o `difflib`, a `n=0`, partiu a corrida em duas. Pôr instruções de volta no
corpo fechou a partição, que é o inverso exato do que a 11.4 registrou. O `rekey3.py` recusa
contagens diferentes de propósito e trata do sentido que ele conhece; o `rekey4.py` desta passagem
trata do outro, imprime o alinhamento antes de aplicar e dobra a razão da linha que sumiu para
dentro da que a absorveu.

Paridade: **185 passed / 3 failed**, as três pré-existentes de outras frentes. Nenhuma quarta.

---

## 3. (b) `SSLContext randomized[random]` — a vacuidade era do catálogo, não do mundo

`SSLContext.crysl:34` · ledger #47 · **`wireable`** · **fiar** · par de arnês `harness/f8b-SSLContextSpec.md`

### 3.1 A derivação que a 11.1 fez e esta alínea executa

A regra `SSLContext` tem três REQUIRES. Duas já eram lidas desde a 5.9. A terceira carregava
`vacuous`, e a delta da 11.1 mostrou por quê:

```
api30    Init: init(kms, tms, _)          <- terceira posição anônima; `sr` bindado por evento nenhum
expert   i1:   init(km, tm, random)       <- bindado
```

`bindable api30=False expert=True`. A vacuidade era **artefato da regra gerada**: a cláusula
existia nos dois catálogos, e só num deles havia variável para ela falar a respeito. Com o oráculo
único, o sítio existe.

### 3.2 O que o `.mop` ganha

O curinga sai da terceira posição do `args`:

```java
-  args(kms, tms, *) &&
+  args(kms, tms, random) &&
```

e o evento passa a declarar `SecureRandom random`. O pointcut agora **não tem curinga nenhum**, o
que é estritamente mais seguro para o resolvedor do arnês de traces do que o curinga final que ele
substitui. O `call(...)` já escrevia a assinatura por extenso, então o autômato não vê diferença
alguma: nenhum símbolo se move, nenhum estado muda.

A leitura é três-valorada, com `SSLCONTEXT-CONSTR-02` e `SSLCONTEXT-NOBS-02`, e o produtor é o hub
`RANDOMIZED` — o `SecureRandomSpec` grava o predicado sobre o próprio gerador no seu ponto de
aceitação.

### 3.3 O que ela acusa, dito em voz alta

`init(km, tm, null)` é a forma **documentada** de pedir o `SecureRandom` da própria plataforma, e
sob a regra como está escrita ela não satisfaz `randomized[random]`: um `null` não é um random que
esta instrumentação viu ser produzido. Todas as traces do corpus que chegam ao evento passam `null`
ali, então todas ganham um relatório `NOBS`.

Isso não é uma escolha nova desta alínea: é **a mesma leitura que as duas cláusulas irmãs já
carregam**, pela decisão de 22/08 — *"a cláusula exige managers que esta instrumentação viu uma
fábrica produzir, e nenhum argumento não é um deles"*. Ler a terceira de outro jeito faria um
evento só responder a duas regras ao mesmo tempo. O código `NOBS` é o que diz "limite de alcance"
em vez de "defeito", e ele diz isso aqui pela mesma razão que diz lá.

### 3.4 O par de arnês

`harness/f8b-SSLContextSpec.md` — **164 `unchanged` / 8 `moved` / 1 `introduced`**. Nenhuma outra
specification do conjunto se move; os outros 23 relatórios leem `unchanged` inteiros.

- **8 `moved`**: as traces que já acusavam alguma coisa no `init` ganham o `SSLCONTEXT-NOBS-02` ao
  lado (`-d15-ssl`, `-d15-tlsv1`, `-guard-on-field`, `-provider-object`, `-provider-sslv3`,
  `-sslv3`, `-tls`, `SSLContextSpec.txt`).
- **1 `introduced`**: `SSLContextSpec-tls-chain.txt`, a cadeia TLS conforme — `KeyStore` carregado,
  as duas fábricas, os dois arrays observados — que passa `null` no terceiro argumento e agora diz
  isso. É a trace que mostra o custo da decisão com mais clareza do que qualquer outra.
- **`-getdefault`, `-getdefault-engine`, `-sslv3-no-init`**: `unchanged`, porque nenhuma chega ao
  `init`.

### 3.5 Contagens

```
predicate_graph.csv .......... 72 -> 73 linhas   (read:body 35 -> 36, round-trip idêntico)
codes.csv .................... +2 códigos        (SSLCONTEXT-CONSTR-02, SSLCONTEXT-NOBS-02)
paridade ..................... read+read-absent 40 -> 41; read:body 35 -> 36; condition fica 0
divergence_record.csv ........ 306 hunks, 4 re-chaveados por posição
```

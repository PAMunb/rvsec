# Lote B2 — tarefas 5.4, 5.5 e 5.8: o hub `randomized`, as duas guardadas do Cipher, e três registros

**Data**: 2026-08-22 · **Grupo 5, terceira passagem** · cláusulas #11, #24, #25, #13, #33, #6, #30,
#10, #17, #20 do ledger de 36
**Arquivos editados**: `IvChainJunction.mop`, `KeyGeneratorSpec.mop`, `SecureRandomSpec.mop`,
`PBEKeySpecSpec.mop`, `KeyPairGeneratorSpec.mop`
**A décima nona forma de passagem**: a que **apaga** um acusador, e a primeira em que o gerador e
o harness de traces decidiram, entre eles, quantos eventos uma cláusula precisa.

---

## O que o lote pediu, e o que a árvore respondeu

**A 5.4 já estava fiada.** As três cláusulas que ela pede — `randomized[src]` do
`GCMParameterSpec` (#11), `randomized[salt]` do `PBEKeySpec` (#24) e do `PBEParameterSpec` (#25)
— já tinham leitor: `GCMParameterSpecSpec.c1/c2`, `PBEKeySpecSpec.c1` e `PBEParameterSpecSpec.c1/c2`
leem `RANDOMIZED` do store desde as passagens por arquivo do Grupo 4 (4.6, 4.7, 4.8). É o mesmo que
a 5.1 achou da #12. O que a 5.4 tinha para fazer era outra coisa, e ela veio da medição.

**A #17 não compõe.** O ledger a classificava *wireable* porque as duas pontas têm `.mop`. Medido
na Temurin 21:

```
KeyPairGenerator.getInstance("DH").initialize(new DHGenParameterSpec(2048, 0))
  -> InvalidAlgorithmParameterException: Inappropriate parameter type
AlgorithmParameterGenerator.getInstance("DH").init(new DHGenParameterSpec(2048, 0))   OK
KeyPairGenerator.getInstance("DH").initialize(<DHParameterSpec>)                      OK
```

O `DHGenParameterSpec` é o **único** produtor de `preparedDH` em todo o oráculo api30 — o
`AlgorithmParameters` **exige** o predicado e garante `preparedAlg`, outro. E o consumidor natural
da classe é o `AlgorithmParameterGenerator`, que não tem `.mop` no conjunto. Um par de chaves DH é
inicializado a partir de um `DHParameterSpec`, que regra nenhuma garante. **Uma leitura em
`KeyPairGeneratorSpec.init3/init4` acusaria todo programa DH conforme** de uma preparação que ele
não tem como obter. É a terceira espécie de registro que a #21 inaugurou (achado 73), e a segunda
ocorrência dela nesta change: **ter `.mop` das duas pontas é necessário e não suficiente**.

**A leitura do `password` no `PBEKeySpecSpec.c1` era um acusador falso.** A regra exige
`randomized[salt]` e não diz nada sobre a senha — sua única cláusula CONSTRAINTS a respeito é
`neverTypeOf(password, java.lang.String)`, que é outra afirmação. Medido contra o oráculo e contra
o conjunto:

| medida | valor |
|---|---|
| ENSURES `randomized[...]` em todo o api30 | 4, e só: `this`(SecureRandom), `genSeed`, `next`, `numB` |
| deles sobre um `char[]` | **0** |
| escritas de `RANDOMIZED` no conjunto | 6, nenhuma sobre um `char[]` |

Logo a leitura só podia responder `NOT_OBSERVED`, **em qualquer programa**, e o
`PBEKEYSPEC-NOBS-00` disparava em **toda** construção de `PBEKeySpec`, a conforme inclusive. E há
uma segunda consequência que ninguém tinha medido: a leitura zerava o mesmo `conforms` que guarda a
escrita de `speccedKey`, de modo que **essa escrita nunca correu para programa nenhum, em conjunto
nenhum**. Os dois códigos saem com ela; os irmãos ficam com os números que têm, porque um código é
identificador em medição já publicada.

---

## As três medições que decidiram o desenho, e não a cláusula

A #6 (`randomized[ranGen]` do Cipher) e a #13 (do KeyGenerator) ligam um argumento que o
`CipherSpec` não pode ligar — ele está em 17/17 eventos (INV-INS-145) — e que o
`KeyGeneratorSpec.init` não ligava, por cobrir as cinco sobrecargas de `init` sem ligar nenhum
argumento. Escrever a leitura pareceu simples e não é: **três formas mais curtas foram medidas e as
três são piores.**

| forma | o que acontece |
|---|---|
| `( call(A) && args(x) \|\| call(B) && args(*,x) )` | o javamop escreve `null` no stderr e **não emite aspecto nenhum** — e os 24 `.rvm` geram antes, então a falha parece defeito de ambiente. Bissectado contra o conjunto do HEAD e contra a pré-imagem, que geram limpos |
| `call(...init(..)) && args(.., ranGen)` | gera, e é pior que errada: medida em três traces-sonda contra o monitor que produz, **casa todo `init`** qualquer que seja o tipo do último argumento, não liga SecureRandom nenhum e responde `NOT_OBSERVED` para todos — inclusive para um `init` cujo SecureRandom acabara de ser observado |
| `call(...init(int, *, SecureRandom))` | gera aspecto **correto** — o AspectJ resolve a assinatura estaticamente — mas derrota o resolvente do harness de traces, que aceita qualquer chamada **a partir do primeiro curinga** (`TraceRunner.fitsPointcut`). Medido no corpus: as traces conformes da 5.1 passaram a tirar relato |

Daí as sete posições escritas por extenso: quatro eventos no `IvChainJunction` (i2, i6, i7, i8 da
regra) e três no `KeyGeneratorSpec` (i2, i4, i5). **Um curinga só é seguro depois de todo tipo
discriminante** — que é por que a leitura da #9, em `use`, pode manter o `..` final dela.

Duas cláusulas em sete sítios é a contagem da medição, não a da cláusula. A forma — um sítio por
posição de argumento, um código por sítio — é a que `IvParameterSpec.c1/c2` e
`GCMParameterSpecSpec.c1/c2` já carregam.

---

## Por que nenhum arquivo novo

A #10 (`{GCM} => preparedGCM[params]`, `Cipher.cryptsl:184`) tem **exatamente o mesmo pointcut** da
#9: as duas ligam o `params` de `Cipher.init(int, Key, AlgorithmParameterSpec, ..)`. Uma
especificação nova sobre a mesma chamada poria um segundo monitor nela para perguntar sobre o mesmo
objeto. A leitura entra como segunda no corpo do `use`, e o universo enumerado **fica em 215**.

O nome `IvChainJunction.mop` fica, e o arquivo passa a dizer o que é: o consumidor das três
cláusulas do `Cipher` que o `CipherSpec` não pode ligar. Renomear reescreveria três traces
commitadas, o relatório de harness publicado `f2-IvChainJunctionSpec.md` e a evidência da 5.1 —
vinte e três arquivos, vários deles medição já publicada — e um nome de arquivo não é do que
aquelas medições tratam (decisão do pesquisador, 2026-08-22).

---

## As traces, e a sonda auditável

Sete traces novas, escritas antes da edição. Duas que o corpus já tinha bastaram para a #33 e não
foram duplicadas: `SecureRandomSpec-seeded-constructor.txt` satisfaz e
`SecureRandomSpec-unrandomised-constructor.txt` não.

| trace | pré-imagem | árvore editada |
|---|---|---|
| `IvChainJunctionSpec-gcm.txt` | 1 relato (artefato de ordenação da pré-imagem) | **silêncio** |
| `IvChainJunctionSpec-gcm-unprepared.txt` | silêncio | `GCMPARAMETERSPEC-NOBS-00` + `IVCHAINJUNCTION-NOBS-01` |
| `IvChainJunctionSpec-rangen.txt` | silêncio | **silêncio** |
| `IvChainJunctionSpec-rangen-unobserved.txt` | `SECURERANDOM-ALG-00` | `ALG-00` + `IVCHAINJUNCTION-NOBS-02` |
| `KeyGeneratorSpec-rangen.txt` | silêncio | **silêncio** |
| `KeyGeneratorSpec-rangen-unobserved.txt` | `SECURERANDOM-ALG-00` | `ALG-00` + `KEYGENERATOR-NOBS-01` |
| `PBEKeySpecSpec-conforming.txt` | 1 relato | **silêncio** |

O par de cada leitura difere **numa coisa só** e roda **no mesmo carregador**. O caminho para um
SecureRandom que o conjunto não marcou é o `g4`: um algoritmo que as CONSTRAINTS rejeitam mantém o
autômato em `start`, o alias `match1` é `init`, e `randomized[this]` nunca é escrito. No campo o
mesmo veredito tem causa mais comum e que trace nenhuma deste corpus carrega — um SecureRandom vindo
de biblioteca que a instrumentação não teceu — e é por isso que o veredito é `NOT_OBSERVED` e não
`VIOLATED`.

---

## O harness diferencial

114 traces contra `backup/gh105-preimage/jca_android`, cumulativo:
**71 inalteradas · 25 movidas · 8 introduzidas · 10 removidas**.

Contra o checkpoint anterior (107 traces: 67 · 23 · 9 · 8), as **`introduced` caem de 9 para 8**, e
a composição é o que diz o que a passagem fez: **duas fecharam** e uma chegou.

- `RandomStringPasswordSpec-bytes-route.txt` e `-int-route.txt`: `introduced` → **`unchanged`**. As
  duas estavam abertas pelo `PBEKeySpecSpec.c1`, e o que as fechou foi apagar a leitura do
  `password`. Uma janela aberta em 2026-08-21 fecha por remoção de acusador, não por reparo dele.
- `IvChainJunctionSpec-gcm-unprepared.txt` entra `introduced`, e é uma trace escrita para ser
  acusada.
- `PBEKeySpecSpec-salt-only.txt`: `moved` → **`removed`**. O salt dela é randomizado; só a senha
  acusava.
- `SecureRandomSpec-unrandomised-constructor.txt`: `removed` → **`moved`**. É a metade do
  construtor da #33 funcionando.

E a asserção mais barata e mais forte: `git diff --stat -- data/gh105/evidence/harness/` mexe em
**cinco** dos 24 relatórios, e os cinco são de arquivos que esta passagem tocou —
`IvChainJunctionSpec`, `KeyGeneratorSpec`, `PBEKeySpecSpec`, `SecureRandomSpec`, e
`RandomStringPasswordSpec`, que é consumidor estrutural das duas escritas autoboxed apagadas.
Nenhum relatório novo: nenhuma especificação nova.

---

## Os portões e os censos

| medida | antes | depois |
|---|---|---|
| achados G-PRED2 | 6 | **4** |
| `structural_findings` na baseline | 6 | **4** |
| linhas no `predicate_graph.csv` | 47 | **53** |
| `read` + `read-absent` no censo | 16 | **24** |
| `read:body` / `write:body` | 15 / 7 | **23 / 5** |
| `write:acceptance` | 23 | 23 |
| `disposition=omission` | 9 | **10** |
| linhas com `clause` vazia | 3 | **1** |
| códigos no `codes.csv` | 72 | **88** |
| traces do corpus | 107 | **114** |
| hunks no `divergence_record.csv` | 275 | **280**, todos registrados |
| universo enumerado (`.mop`, 5 conjuntos) | 215 | **215** |

As duas linhas G-PRED2 que caem fecham por caminhos diferentes, e vale nomear os dois:
`GCMParameterSpecSpec match/PREPARED_GCM` fecha **por leitura**, que é o que o próprio arquivo
previa em comentário desde a 4.8; `DHGenParameterSpecSpec match/PREPARED_DH` fecha **por registro
de omissão deliberada**, como o `PREPARED_HMAC` (achado 78) e pela mesma razão que ele.

A única linha do grafo que continua com `clause` vazia não é desta passagem: é o
`SecretKeySpec.mop/e1`, a leitura de propagação que a 4.12 registrou, cuja regra tem ENSURES e
nenhuma secção REQUIRES.

---

## As escritas que saíram, e o registro dos becos sem saída

`SecureRandomSpec.next1` e `next3` marcavam `RANDOMIZED` sobre um `int` autoboxed, como
substitutos de `randomized[numB]` — cláusula sobre `ne: next(numB)`, e `next(int)` é `protected` em
`java.util.Random`, evento que sobrecarga nenhuma de `nextInt` é. **Escrita que não traduz cláusula
se apaga** (decisão 2), e nenhuma das duas poderia levar predicado a lugar algum de todo modo: o
store chaveia por identidade e um `int` é autoboxed na chamada, então um primitivo encaixotado só
sobrevive a uma leitura posterior dentro do cache de `Integer` (-128..127). Os dois eventos ficam:
removê-los tornaria as chamadas não modeladas em vez de não marcadas.

Os **nove becos sem saída ENSURES-only** que a 5.8 devia dispor **já estavam dispostos**: as sete
predicates com escrita no conjunto (`preparedPBE`, `generatedSSLContext`, `generatedSSLEngine`,
`signed`, `verified`, `digested`, `generatedKeypair`) carregam `disposition=omission` desde as
passagens 4.13 e 4.14, e as duas de stream (`cipheredInputStream`, `cipheredOutputStream`) não têm
escrita nenhuma e não precisam de registro. A 5.8 mede isso e o afirma, em vez de acrescentar linha.

A #20 (`preparedEC`) fica `unclosable`: api30 a nomeia neste REQUIRES e em ENSURES de regra nenhuma,
então sítio nenhum poderia jamais escrevê-la. A #30 (`SSLContext randomized[sr]`) fica `vacuous`
como o ledger já dizia: `Init: init(kms, tms, _)` não liga `sr` em evento nenhum, logo ela não pode
ter sítio de leitura e não tem linha no grafo, que é inventário de sítios.

---

## O custo, por inteiro

1. **A `#17` fica sem leitor, e a regra continua a exigi-la.** Um programa que passe um
   `DHParameterSpec` conforme ao `initialize` não é medido por esta change. O que o registro diz é
   que fabricar a leitura acusaria *todos* eles, o que é pior; o reparo de verdade é dar `.mop` ao
   `AlgorithmParameterGenerator`, que é mudança de escopo e não se decide aqui.
2. **A `#6` e a `#13` custam sete sítios e sete pares de código** para duas cláusulas. Cada sítio é
   uma sobrecarga que a regra nomeia, mas o conjunto ganha 14 códigos por duas cláusulas, e isso é
   contagem que a 5.11 vai ter de varrer.
3. **A leitura do `password` deixa de acusar.** É mudança comportamental deliberada e medida: ela
   acusava toda construção de `PBEKeySpec`. O que entra no lugar é a escrita de `speccedKey`, que
   passa a acontecer — e cujo leitor é a #31, roteada para a 5.10 como `unmonitored-consumer`. Ou
   seja: a partir daqui `SPECCED_KEY` é escrito e não lido, que é a linha G-PRED2 que o
   `PBEKeySpecSpec` já carrega.
4. **A cascata do GCM é a mesma da do IV**: `GCMParameterSpecSpec.@match` só prepara uma construção
   cuja própria leitura de `randomized[src]` respondeu `SATISFIED`, então material que a
   instrumentação não viu randomizar é relatado **duas vezes** — `GCMPARAMETERSPEC-NOBS-00` na
   construção e `IVCHAINJUNCTION-NOBS-01` no `init`. Medido na trace não preparada.
5. **O `TraceRunner.fitsPointcut` aceita qualquer chamada a partir do primeiro curinga.** É defeito
   do instrumento, não do conjunto, e não foi reparado aqui: nenhum pointcut do conjunto tem curinga
   antes de tipo discriminante depois desta passagem, e mudar o resolvente no meio de uma medição é
   mudança de instrumento. Registrado.

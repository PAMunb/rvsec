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

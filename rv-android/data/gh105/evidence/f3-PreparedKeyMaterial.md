# F3 — `preparedKeyMaterial`: a conflação desfeita, o registro das dez, e o que a 6.5 verificou

**Lote B5** · tarefas **5.10**, **6.1** e **6.5** · um commit · 2026-08-22

Este lote fecha a última cláusula folha do Grupo 5 e a passagem de registro que ela carrega. O
que ele faz cabe em uma frase e o que ele custa não: as duas pontas da cláusula #32 passam a
nomear o predicado que o api30 nomeia, e com isso **dezoito das 128 traces do corpus mudam de
resposta**. Todas as respostas novas são as que o oráculo enuncia. Este documento é o registro
delas, uma a uma, porque um lote que muda o que o conjunto acusa deve o número inteiro.

---

## 1. A cláusula, e por que ela era um defeito

api30 diz, nos dois lados de uma cópia:

| regra | cláusula | arquivo |
|---|---|---|
| `javax.crypto.SecretKey` | `ENSURES preparedKeyMaterial[keyMaterial] after ge` | `SecretKey.cryptsl:25` |
| `java.security.Key` | `ENSURES preparedKeyMaterial[keyMaterial] after ge` | `Key.cryptsl:23` |
| `javax.crypto.spec.SecretKeySpec` | `REQUIRES preparedKeyMaterial[keyMaterial]` | `SecretKeySpec.cryptsl:34` |

A semente escrevia `randomized` no produtor (`SecretKeySpec.mop`, o `@match` do `getEncoded`) e
lia `randomized` no consumidor (`SecretKeySpecSpec.mop`, o `c1`). Os dois predicados existem no
oráculo, são distintos, e **um programa conforme satisfaz um sem satisfazer o outro** — que é a
frase que o javadoc de `Property.PREPARED_KEY_MATERIAL` já trazia desde o Grupo 1. É o ledger
**#32**, registrado na tarefa 4.10 do lado da leitura e na 4.12 do lado da escrita, e desfeito
aqui.

**As duas metades tinham de mover juntas**, e isso não é preferência: mover só uma deixa
`PREPARED_KEY_MATERIAL` escrito e não lido, ou lido e não escrito, e o G-PRED2 acusa qualquer um
dos dois. Trocar-se-ia o achado que se repara por outro.

## 2. O que foi medido antes de escrever a edição

**A composição roda, e a plataforma não a recusa** (achados 73 e 87). `key.getEncoded()` seguido
de `new SecretKeySpec(enc, alg)` executa; nenhuma exceção da JCA fica no caminho da leitura. A
resposta é "a leitura tem programa para acusar", e é a favorável.

**A leitura não custa símbolo** (achado 94). Os dois sítios já existiam e já ligavam o `byte[]`;
a #32 é uma troca de `Property` nos dois lados. `PREPARED_KEY_MATERIAL` **já existia** no enum
(`Property.java:68`, posto pelo Grupo 1), então nenhum build do reator entrou no lote. Nenhum
alfabeto cresceu, nenhum `fsm` mudou, nenhuma linha entrou no `gate_allowlist.csv`, nenhum arquivo
entrou no universo.

**Os leitores do predicado, contados nos cinco conjuntos** (achado 88). Em `jca_android`,
`RANDOMIZED` tinha 4 escritas e 17 leituras; `PREPARED_KEY_MATERIAL` tinha **zero de ambas**. As
leituras de `randomized` sobre `byte[]` que **ficam** são as que o oráculo enuncia sobre salt e
IV — `PBEKeySpecSpec.c1`, `PBEParameterSpecSpec` (2), `GCMParameterSpecSpec` (2),
`IvParameterSpec` (2). A única que muda é a de material de chave.

**As quatro configurações, medidas com harnesses concorrentes contra a árvore de antes:**

| config | o que era | traces alterados |
|---|---|---|
| **C1** un-conflação dos dois lados | a opção da tarefa | **17** (9 `introduced` + 8 `moved`) |
| **C2** = C1 **sem a guarda** no `e1` | a tradução literal do ENSURES sem REQUIRES | **17 — idênticos ao C1** |
| **C3** = C1 + a leitura no `c2` | a sobrecarga de quatro argumentos | 18 |
| **C4** = C1 **sem a cascata** | `c1` acusa mas ainda escreve `generatedKey` | **17 — os mesmos traces** |

O **C4** é o que mata a única mitigação plausível: suprimir a cascata não reduz o alcance, porque
o relato do próprio `SecretKeySpecSpec.c1` já move as mesmas traces. Só apagaria o relato do
`CipherSpec` **dentro** de traces que já mudaram — comprando nada e custando fidelidade, já que em
CrySL o ENSURES é condicional à regra estar satisfeita, e é isso que faz o CogniCrypt encadear.

O **C2** é o que reabre a decisão da guarda, e está na secção 4.

## 3. O que a un-conflação custa, dito por inteiro

`preparedKeyMaterial` é ENSURED por `Key.getEncoded()` e `SecretKey.getEncoded()` e **por mais
nada em todo o oráculo**. Consequência: o idioma sobre o qual o corpus foi construído — encher um
`byte[]` de um `SecureRandom` observado e construir um `SecretKeySpec` a partir dele — **não
satisfaz a cláusula**, e o idioma que satisfaz é `generateKey()` → `getEncoded()` → o construtor.

Medido, o lote inteiro contra a árvore imediatamente anterior, 128 traces:

```
unchanged 110 · moved 8 · introduced 10
```

Dezoito traces, e a cascata por dentro: **quinze** ganham `SecretKeySpecSpec.c1`, **onze** ganham
`CipherSpec.i2` a jusante (porque uma construção que quebra a cláusula não escreve `generatedKey`),
**quatro** ganham `IvParameterSpecSpec.c1` (porque uma codificação deixou de ser bytes
randomizados), e **uma** ganha `SecretKeySpecSpec.c2`, o sítio novo.

### As dezoito, uma a uma

| trace | antes | depois | o que a mudança diz |
|---|---|---|---|
| `SecretKeySpecSpec.txt` | silenciosa | `c1` | o rótulo "legítimo" era sobre o algoritmo e a ordenação |
| `SecretKeySpecSpec-cipher-chain.txt` | silenciosa | `c1`, `CipherSpec.i2` | a metade Cipher continua conforme; a construção da chave não |
| `SecretKeySpecSpec-offset.txt` | silenciosa | `c2` | a única que mede o sítio novo |
| `SecretKeySpec-encoded-iv.txt` | silenciosa | `c1`, `IvParameterSpecSpec.c1` | duas cláusulas distintas que a semente fizera uma |
| `SecretKeySpec-keygen-iv.txt` | silenciosa | `IvParameterSpecSpec.c1` | um IV feito de material de chave não é um IV randomizado |
| `KeyStoreSpec-getkey-iv.txt` | silenciosa | `IvParameterSpecSpec.c1` | o mesmo, pela rota do key store |
| `IvChainJunctionSpec.txt` | silenciosa | `c1`, `CipherSpec.i2` | a cadeia do IV continua conforme; a chave não |
| `IvChainJunctionSpec-gcm.txt` | silenciosa | `c1`, `CipherSpec.i2` | idem, GCM |
| `IvChainJunctionSpec-rangen.txt` | silenciosa | `c1`, `CipherSpec.i2` | idem |
| `MacSpec-fresh-buffer.txt` | silenciosa | `c1`, `CipherSpec.i2` | a cláusula negada do Mac continua satisfeita por ausência |
| `IvChainJunctionSpec-decrypt.txt` | `IvParameterSpecSpec.c1` | `+ c1`, `+ CipherSpec.i2` | acrescenta, não substitui |
| `IvChainJunctionSpec-gcm-unprepared.txt` | `GCM.c1`, `use` | `+ c1`, `+ CipherSpec.i2` | idem |
| `IvChainJunctionSpec-rangen-unobserved.txt` | `g4`, `useRandomKey` | `+ c1`, `+ CipherSpec.i2` | idem |
| `IvChainJunctionSpec-unprepared.txt` | `IvParam.c1`, `use` | `+ c1`, `+ CipherSpec.i2` | idem |
| `MacSpec-decrypt-buffer.txt` | `MacSpec.f2` | `+ c1`, `+ CipherSpec.i2` | idem |
| `MacSpec-encrypted-buffer.txt` | `MacSpec.f2` | `+ c1`, `+ CipherSpec.i2` | idem |
| `MacSpec-mac-then-encrypt.txt` | `finalInput` | `+ c1`, `+ CipherSpec.i2` | idem |
| `MacSpec-update-then-encrypt.txt` | `finalInput` | `+ c1`, `+ CipherSpec.i2` | idem |

**Oito cabeçalhos de trace afirmavam conformidade que já não é verdade** e foram corrigidos, não
apagados (achado 98): o rótulo era sobre a ordenação e o algoritmo, e a cláusula nova é outra. As
traces em si ficam byte a byte como estavam — o que elas testemunham é justamente a diferença
entre os dois predicados.

**E a trace que faltava foi escrita.** `SecretKeySpecSpec-prepared-material.txt` é a cadeia que o
api30 admite, observada ponta a ponta, e é **silenciosa dos dois lados** — antes por causa da
conflação, agora por causa da regra. É a auditoria da sonda no sentido que a disciplina pede: um
controle que sabidamente não acusa, ao lado de quinze que sabidamente acusam.

## 4. As quatro decisões, e o número que decidiu cada uma

### 68. A un-conflação move os dois lados, e o colateral é declarado, não mitigado
As alternativas foram medidas e recusadas: mover metade troca um achado G-PRED2 por outro
(secção 1); suprimir a cascata não reduz o alcance (C4) e custa a semântica condicional do ENSURES,
que é o que faz o CogniCrypt encadear; adiar deixa o ledger #32 sendo um defeito conhecido e não
reparado dentro da change cujo objeto é exatamente esse. Dezoito traces mudam e cada relato novo é
um que o api30 enuncia (pesquisador, 2026-08-22).

### 69. A guarda no `SecretKeySpec.e1` fica, com razão nova
**A razão antiga dissolveu-se.** A tarefa 4.12 manteve a leitura porque uma escrita incondicional
entregava a codificação de uma chave hard-coded como *randomised* e o IV construído dela deixava de
ser acusado (`f2-SecretKeySpec.md`, configuração D). Com a escrita nomeando `preparedKeyMaterial`,
esse argumento está gasto: o `IvParameterSpec` pergunta por `randomized`, então a cadeia hard-coded
é acusada com a guarda ou sem ela. **Medido: sobre as 128 traces, a árvore guardada e a
desguardada respondem igual em todas menos uma.**

**A razão nova é a lavagem.** Sem a leitura, uma chave cuja origem o conjunto nunca observou
entrega a sua codificação como material preparado, e um segundo `SecretKeySpec` construído dela
fica em silêncio. `SecretKeySpec-laundered-material.txt` é a trace escrita para medir isso, e é o
único programa que pode: com a guarda acusa, sem a guarda não acusa
(`{'unchanged': 127, 'removed': 1}`).

**Ela precisou de duas versões, e a primeira não servia** — achado 14 na prática. A versão inicial
construía a primeira chave por evento, então as duas construções disparavam `SecretKeySpecSpec.c1`
e o harness, que classifica pelo **conjunto** de eventos acusadores e não pelo número, dava
`unchanged` nas duas árvores. Ligar a primeira chave com `bind` — o mesmo recurso que a
`MacSpec-ungenerated-key.txt` usa, pela mesma razão — deixa só a segunda construção falar, e aí o
controle discrimina.

### 70. O `c2` ganha a leitura que o `c1` sempre teve
api30 liga `keyMaterial` nos dois eventos de `Cons := c1 | c2` e enuncia um único REQUIRES sobre
ele, então a obrigação é do construtor e não de uma sobrecarga. A tarefa 4.10 deixara o sítio de
fora porque a cláusula que ele traduziria era a conflada, e nomeara a 5.10 como onde seria
decidido. Custa **zero símbolo** (o evento existe e já liga o array) e dois códigos,
`SECRETKEYSPEC-CONSTR-02` e `SECRETKEYSPEC-NOBS-01`, **números novos e não os do `c1`**, porque um
código nomeia um sítio. Uma trace mede: `SecretKeySpecSpec-offset.txt`.

### 71. O G-PRED2 fecha e é aposentado na 5.11, não aqui
O dossiê de contabilidade levantou o que não estava escrito em lado nenhum: `unmonitored-consumer`
é vocabulário de **leitura** no portão, e uma escrita sem leitor só fecha com `omission` ou
`propagation` (`gh105_predicate_graph.py:1189`). Pôr `omission` na linha
`PBEKeySpecSpec c1/SPECCED_KEY` levaria o G-PRED2 a zero — e `gh105_gate_baseline.py:75-84`
constrói `gates` **só a partir de achados**, então a chave sumiria do baseline e
`test_a_retired_gate_leaves_the_baseline_and_stays_out` (`:2039`) ficaria vermelho.

Ou seja: **a suíte obriga o portão a ser aposentado no mesmo commit em que zera**, o que é o
achado 58 com um mecanismo por trás. A 5.11 já reivindica textualmente o registro do lado da
escrita ("every write has its reader or its deliberate-omission record") e a aposentadoria. Então
a 5.10 registra a **cláusula** onde uma cláusula sem sítio pode ser registrada, e a 5.11 escreve a
**disposição** e aposenta o portão juntas. O G-PRED2 fica em **1** depois deste lote, de propósito
(pesquisador, 2026-08-22).

## 5. A passagem de registro (5.10)

As dez cláusulas não-fiáveis do ledger, cada uma com a sua categoria, cada uma exatamente uma vez:

| # | regra consumidora | cláusula | categoria |
|---|---|---|---|
| 1 | AlgorithmParameters | `preparedAlg[parAr]` | `unmonitored-consumer` **e** `unmonitored-producer` |
| 2 | AlgorithmParameters | `{AES,DESede} => preparedIV[params]` | `unmonitored-consumer` |
| 3 | AlgorithmParameters | `{DiffieHellman} => preparedDH[params]` | `unmonitored-consumer` |
| 4 | CertPathTrustManagerParameters | `generatedCertPathParameters[params]` | `unmonitored-consumer` e `-producer` |
| 7 | Cipher | `preparedAlg[param, part(0,"/",transformation)]` | `unmonitored-producer` |
| 18 | KeyPairGenerator | `{DSA} => preparedDSA[params]` | `unmonitored-producer` |
| 19 | KeyPairGenerator | `{RSA} => preparedRSA[params]` | `unmonitored-producer` |
| 26 | PKIXBuilderParameters | `generatedKeyStore[keyStore]` | `unmonitored-consumer` |
| 27 | PKIXParameters | `generatedKeyStore[keyStore]` | `unmonitored-consumer` |
| 31 | SecretKeyFactory | `speccedKey[keySpec, _]` | `unmonitored-consumer` |

Sobre a **#31**, que é a que ainda sustenta a linha G-PRED2: o `SecretKeyFactory` não tem `.mop`
neste conjunto, e **os dois produtores do oráculo estão aqui** — o `PBEKeySpec`, que escreve, e o
`SecretKeySpec`, que deliberadamente não escreve — e nenhum tem para onde mandar o predicado.
Nenhum consumidor é fabricado para dar leitor à escrita, e a escrita não é apagada, porque apagar
a tradução fiel de uma cláusula que o oráculo enuncia seria a fabricação a correr no outro sentido.
O registro está no `PBEKeySpecSpec.mop` (o comentário do `c2`) e na coluna `reason` do grafo.

**Mais o registro que a 4.13 alimentou**: api30 `KeyPair.cryptsl:39` enuncia
`generatedKeypair[this, _] after co` e o `KeyPairSpec.c1` não tem escrita para ele. Nenhuma foi
fabricada — o predicado não é exigido por regra nenhuma do oráculo, o outro sítio produtor é o
`KeyPairGeneratorSpec.mop` (tarefa 4.14), que já carrega o registro de omissão, e **uma cláusula
sem sítio não tem linha no `predicate_graph.csv` para carregar o registro, porque esse inventário é
de sítios e não de cláusulas**. O registro vive no ledger, no comentário do `KeyPairSpec.mop` e
aqui.

## 6. O que a 6.5 verificou (e não executou)

A tarefa é de verificação por construção, e as três coisas que ela verifica estão verdes:

1. **A nona retirada** — a única cláusula `NEGATES` real do conjunto, `speccedKey[this, _] after cP`
   — foi traduzida para `PredicateStore.negate`, com escopo de objeto, pela tarefa 4.6. Está em
   `PBEKeySpecSpec.mop`, no evento `c2` que a regra nomeia. **Medido: `negate:body == 1` no grafo e
   `remove + negate == 1` no leitor, e nenhum dos dois se moveu neste lote** — que é exatamente o
   que verificar significa aqui.
2. **A retirada do `@fail` do `MacSpec`**, que a 4.9 apagou junto com as duas escritas de
   `GENERATED_MAC` que ela retirava. **Medido: `grep -c "remove(" MacSpec.mop` devolve zero**, e o
   `@fail` do arquivo (`:322-336`) não contém retirada nenhuma.
3. **O `NEGATES generatedKey[this, _] after d` sem sítio**, registrado como `unclosable`: o
   conjunto não declara evento para `destroy()`, e inventar um fabricaria a evidência que esta
   change existe para remover. A medição que sustenta o registro é da tarefa 4.12 e está no
   `SecretKeySpec.mop:67-75`: `destroy()` levanta `DestroyFailedException` nas duas implementações
   de `SecretKey` que o conjunto pode observar — a que o próprio arquivo constrói e a que o
   `KeyGenerator.generateKey()` devolve, que são a mesma classe — então uma advice
   `after ... returning` sobre ele não teria caminho de execução mesmo que o evento fosse
   declarado. Declará-lo também acrescentaria um símbolo a um autômato cujo mapeamento de `ORDER` a
   7.1 ainda possui: o `SecretKeySpec` é uma das treze não mapeadas, e o G-ORDER a pula.

## 7. Os portões, e o que não se moveu

`verify_all.sh` depois de fechar os registros:

```
baseline 0 · divergence 0 · message-gate 0 · mop-lint 0
suite-gh101 0 · suite-gh104-specset 0 · suite-gh104-structural 0 · suite-gh105 0
achados por portão: 1 [G-PRED2]
```

**94 asserções nas quatro suítes** (6 + 2 + 16 + 70), como antes.

`gh104_gates.py` sobre o monitor gerado, **idêntico antes e depois**:
`G-2 0 · G-2a 11/3 falhas (pré-existentes, achado 70) · G-2b' 18 · G-2c 2 · G-2d 3 · G-6' 0 ·
G-ERE 0 · G-CONF 0 · G-PRED 23`.

`G-ORDER`: **6 passed, 4 failed, 14 skipped of 24** — as mesmas quatro divergências
(`CipherSpec f2`, `SSLContextSpec g1 Init se1 se1`, `SecureRandomSpec c1 c1`,
`TrustManagerFactorySpec g1 i1 gtm`), todas da 7.1.

Estrutura, tudo igual: eventos `CipherSpec 17` (INV-INS-145), `IvChainJunction 7`, `MacSpec 12`,
`SecretKeySpec 1`, `SecretKeySpecSpec 2`, `PBEKeySpecSpec 4`, `KeyPairSpec 3`; universo **215**;
`gate_allowlist.csv` **14**; `conformance_record.csv` **74**; `order_alphabet_map.csv` intocado.

O que se moveu, e só isto: `codes.csv` 110 → **112** (os dois códigos do `c2`);
`predicate_graph.csv` 69 → **70** sítios; censo do leitor `read + read-absent` 37 → **38**; censo
do grafo `read:body` 32 → **33**; corpus 126 → **128** traces; `divergence_record.csv` **278**
hunks, todos gravados (9 novos, 9 `stale` absorvidas).

**`unresolved`: quatro arquivos, seis linhas — as mesmas seis** (`MessageDigestSpec-reset` 2,
`SSLContextSpec` 2, `TrustManagerFactorySpec` 1, `SSLContextSpec-tls-chain` 1). Conte linhas, não
arquivos (achado 96).

**`git diff --stat` sobre `data/gh105/evidence/harness/`: cinco arquivos** —
`f2-IvChainJunctionSpec`, `f2-KeyStoreSpec`, `f2-MacSpec`, `f2-SecretKeySpec`,
`f2-SecretKeySpecSpec`. São exatamente as especificações que o lote toca, e é a afirmação mais
forte de que ele não tocou em mais nada.

## 8. O que este lote não tocou

O `fsm` e o `ere` de nenhum arquivo; o `order_alphabet_map.csv`; o `gate_allowlist.csv`; o
`conformance_record.csv`; o `alias_table.csv`; o `constraint_table.csv`; o `Property.java`
(a constante já existia); o `ExecutionContext.java`, que continua byte-idêntico; e as cinco
divergências de autômato, que são da 7.1. Nenhum arquivo `.mop` foi criado nem apagado.

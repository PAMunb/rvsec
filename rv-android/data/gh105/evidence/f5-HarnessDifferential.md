# Tarefa 8.4 — o diferencial completo do harness, e a quem cada mudança pertence

**Data**: 2026-08-23 · **Commit da árvore**: `519f2ff8`
**A** `backup/gh105-preimage/jca_android` (o conjunto que a 2.11 arquivou) ·
**B** `rvsec/rvsec-mop/src/main/resources/jca_android` · **corpus** `data/gh104/traces` (131)

Rodar o harness custa 8–10 s em cache. O trabalho desta tarefa não é rodar: é **atribuir cada
classificação não-`unchanged` a uma tarefa**, que é o que separa "o conjunto mudou" de "o
conjunto mudou pelas razões que a change declarou".

---

## 1. O resultado

```
131 traces:  61 unchanged · 31 moved · 32 introduced · 7 removed
```

**70 classificações não-`unchanged`**, e nelas **130 deltas de acusação** — uma classificação
pode carregar mais de um evento, e carrega: a cadeia do `IvChainJunction` move quatro de uma vez.

Todas as 130 têm tarefa. **Zero sem atribuição.**

### O harness é determinístico, e isto foi medido e não presumido

Três passagens independentes, duas em cache e uma com o cache do monitor **removido** (geração
completa dos dois lados, 87 s): os relatórios saíram **byte a byte iguais** nas três. Sem essa
medida, a atribuição abaixo estaria a explicar ruído.

## 2. Por tarefa

| tarefa(s) | deltas | o que a tarefa fez |
|---|---|---|
| 5.6;5.7 | 28 | a família `generated*key`: os produtores no acceptance point e o consumidor `CipherSpec.i2` |
| 5.10;6.1 | 19 | `preparedKeyMaterial` desconflado de `randomized` no `SecretKeySpecSpec` |
| 4.4 | 8 | `IvParameterSpec` lê `randomized[iv]` com três saídas em vez de duas |
| 4.5 | 7 | o estado `end` do `SecureRandomSpec` ganha `next2`, fechando a omissão de `Ends*` |
| 3.6 | 7 | os gêmeos negados fundidos em `g1` (`Signature`, `SSLContext`) e `initError` absorvido |
| 3.5 | 7 | os grupos de Kleene do `ere` do `PBEKeySpecSpec` absorvem `f1`/`f2` e os `err*` |
| 3.6;4.7 | 6 | o `PBEParameterSpecSpec` por cláusula, com o gêmeo apagado no mesmo hunk |
| 4.8 | 5 | `GCMParameterSpecSpec`: `c1` e `c2` perdem `condition(...)` inteiro |
| 5.1;5.5;5.8 | 5 | o `IvChainJunction`, arquivo novo — o consumidor das três cláusulas que o `CipherSpec` não liga |
| 6.6 | 5 | `f2` estreitado para `doFinal(byte[], ..)`, disjunto de `f1` |
| 3.3 | 5 | os gêmeos órfãos `c3`/`c4` do `IvParameterSpec` apagados |
| 3.2;5.9;7.1 | 4 | o `TrustManagerFactorySpec`: `g3` retirado, `init` fundido, a rota `taken` |
| 4.13;5.10;6.1 | 3 | `generatedPubkey`/`generatedPrivkey` do `KeyPairSpec` no armazém novo |
| 3.4;4.10 | 3 | o gêmeo órfão `c3` do `SecretKeySpecSpec` apagado |
| 4.6 | 3 | `c2` retira `speccedKey` por `PredicateStore.negate` |
| 5.9 | 2 | a cadeia TLS: as duas cláusulas REQUIRES do `SSLContext.init` |
| 4.9 | 2 | `MacSpec.i1` perde `condition(...)` inteiro |
| 3.5;4.6 | 2 | `c1` do `PBEKeySpecSpec` lê o salt com três saídas e garante `speccedKey` |
| 3.1;5.5 | 2 | o gêmeo órfão `c3` do `SecureRandomSpec` e a leitura que `c2` passa a carregar |
| 3.2 | 2 | o gêmeo `g3` do `TrustManagerFactorySpec` retirado |
| 5.9;7.1 | 1 | o `KeyManagerFactorySpec.init` |
| 7.1 | 1 | `gtm1 -> taken`, e `alias match2 = taken` |
| 5.5 | 1 | um evento por sobrecarga do `KeyGenerator.init` que liga `SecureRandom` |
| 3.1;4.5 | 1 | `setSeed2` lê `randomized[seed]` no armazém novo |
| 3.1 | 1 | o laço benigno que absorve `g4` no autômato do `SecureRandomSpec` |

**Nenhum delta pertence à gh104.** Isto foi conferido e não presumido, porque a coluna `task` do
`divergence_record.csv` **mistura as duas changes** — o registro mora em `data/jca_android/` e é
compartilhado, então `2.4`, `8.4`, `8.5` e `8.16` nele são tarefas da **gh104**, não desta. Dois
candidatos foram testados contra a fonte e caíram: as remoções de `SignatureSpec.s1` e
`.update` pareciam ser da tarefa 8.5 da gh104 (o `sign()` que declarava devolver `byte`), mas os
dois pointcuts já estão corrigidos **na própria pré-imagem** — o reparo é anterior ao ponto A e
não pode aparecer neste diferencial. A causa real é o arraste da fusão de `g3` (tarefa 3.6).

## 3. As três formas de arraste

Nem toda mudança é a acusação que a tarefa escreveu. Três das 70 são **efeito** de uma tarefa
sobre um evento que ela não tocou, e vale nomeá-las porque uma leitura ingênua as atribuiria ao
arquivo errado:

1. **`SignatureSpec-sha512withdsa.txt`** — A acusa `g3`, `i1`, `update` e `s1`, todas
   `SIGNATURE-ORDER-00`; B acusa só `i1`, e por `SIGNATURE-NOBS-00`. Com `g3` fundido em `g1`
   (3.6) o autômato fica na trilha, e as três acusações de ordem que vinham atrás dele somem. O
   que sobra é a leitura da cláusula REQUIRES (5.6;5.7).
2. **`KeyPairGeneratorSpec-rsa3072.txt`** — A acusa `initError` (tamanho de chave) e `gen`
   (ordem); B acusa só `initError`. `initError` foi absorvido no grupo `Inits` do `ere` (3.6),
   que é a única posição onde a api30 admite um `initialize`, então a chamada seguinte deixa de
   estar fora da ordem.
3. **`MacSpec-fresh-buffer.txt`** — `f2` deixa de acusar enquanto os dois irmãos
   (`-decrypt-buffer`, `-encrypted-buffer`) passam a acusar `MAC-CONSTR-00` no mesmo evento. É a
   leitura negada de `encrypted` (5.6;5.7) a fazer o trabalho que a ordem fazia mal.

## 4. Os 70, um a um

### `introduced` — 32 traces

| trace | delta de acusação | tarefa |
|---|---|---|
| `CipherSpec-keygen-key-mismatch.txt` | `+CipherSpec.i2` | 5.6;5.7 |
| `GCMParameterSpecSpec-badtaglen.txt` | `+GCMParameterSpecSpec.c1` | 4.8 |
| `GCMParameterSpecSpec-second-overload-badtaglen.txt` | `+GCMParameterSpecSpec.c2` | 4.8 |
| `GCMParameterSpecSpec-second-overload-unrandomised.txt` | `+GCMParameterSpecSpec.c2` | 4.8 |
| `GCMParameterSpecSpec-unrandomised.txt` | `+GCMParameterSpecSpec.c1` | 4.8 |
| `IvChainJunctionSpec-gcm-unprepared.txt` | `+CipherSpec.i2` `+GCMParameterSpecSpec.c1` `+IvChainJunctionSpec.use` `+SecretKeySpecSpec.c1` | 5.6;5.7, 4.8, 5.1;5.5;5.8, 5.10;6.1 |
| `IvChainJunctionSpec-rangen.txt` | `+CipherSpec.i2` `+SecretKeySpecSpec.c1` | 5.6;5.7, 5.10;6.1 |
| `KeyManagerFactorySpec.txt` | `+KeyManagerFactorySpec.init` | 5.9;7.1 |
| `KeyPairSpec-private-cipher.txt` | `+KeyPairSpec.c1` | 4.13;5.10;6.1 |
| `KeyPairSpec-public-cipher.txt` | `+KeyPairSpec.c1` | 4.13;5.10;6.1 |
| `KeyPairSpec.txt` | `+KeyPairSpec.c1` | 4.13;5.10;6.1 |
| `KeyStoreSpec-getkey-iv.txt` | `+IvParameterSpecSpec.c1` | 4.4 |
| `MacSpec-guard-on-field.txt` | `+MacSpec.i1` | 4.9 |
| `MacSpec-mac-then-encrypt.txt` | `+CipherSpec.i2` `+IvChainJunctionSpec.finalInput` `+SecretKeySpecSpec.c1` | 5.6;5.7, 5.1;5.5;5.8, 5.10;6.1 |
| `MacSpec-update-then-encrypt.txt` | `+CipherSpec.i2` `+IvChainJunctionSpec.finalInput` `+SecretKeySpecSpec.c1` | 5.6;5.7, 5.1;5.5;5.8, 5.10;6.1 |
| `PBEParameterSpecSpec-threearg-lowiter.txt` | `+PBEParameterSpecSpec.c2` | 3.6;4.7 |
| `PBEParameterSpecSpec-threearg.txt` | `+PBEParameterSpecSpec.c2` | 3.6;4.7 |
| `SSLContextSpec-tls.txt` | `+SSLContextSpec.init` | 5.9 |
| `SSLContextSpec.txt` | `+SSLContextSpec.init` | 5.9 |
| `SecretKeySpec-encoded-iv.txt` | `+IvParameterSpecSpec.c1` `+SecretKeySpecSpec.c1` | 4.4, 5.10;6.1 |
| `SecretKeySpec-keygen-iv.txt` | `+IvParameterSpecSpec.c1` | 4.4 |
| `SecretKeySpecSpec-cipher-chain.txt` | `+CipherSpec.i2` `+SecretKeySpecSpec.c1` | 5.6;5.7, 5.10;6.1 |
| `SecretKeySpecSpec-offset.txt` | `+SecretKeySpecSpec.c2` | 5.10;6.1 |
| `SecretKeySpecSpec.txt` | `+SecretKeySpecSpec.c1` | 5.10;6.1 |
| `SignatureSpec-ecdsa.txt` | `+SignatureSpec.i1` | 5.6;5.7 |
| `SignatureSpec-initsign-after-sign.txt` | `+SignatureSpec.i1` | 5.6;5.7 |
| `SignatureSpec.txt` | `+SignatureSpec.i1` | 5.6;5.7 |
| `TrustManagerFactorySpec-managers-taken-twice.txt` | `+TrustManagerFactorySpec.gtm1` | 7.1 |
| `TrustManagerFactorySpec-pkix-init.txt` | `+TrustManagerFactorySpec.init` | 3.2;5.9;7.1 |
| `TrustManagerFactorySpec-unloaded-keystore.txt` | `+TrustManagerFactorySpec.init` | 3.2;5.9;7.1 |
| `TrustManagerFactorySpec-x509.txt` | `+TrustManagerFactorySpec.init` | 3.2;5.9;7.1 |
| `TrustManagerFactorySpec.txt` | `+TrustManagerFactorySpec.init` | 3.2;5.9;7.1 |

### `moved` — 31 traces

| trace | delta de acusação | tarefa |
|---|---|---|
| `CipherSpec-guard-on-field.txt` | `+CipherSpec.i2` | 5.6;5.7 |
| `CipherSpec-nofinal-arg.txt` | `+CipherSpec.i2` `-CipherSpec.f2` | 5.6;5.7, 6.6 |
| `CipherSpec-unsafe.txt` | `+CipherSpec.i2` | 5.6;5.7 |
| `CipherSpec-update-chain.txt` | `+CipherSpec.i2` `-CipherSpec.f1` `-CipherSpec.f2` `-CipherSpec.u1` | 5.6;5.7, 6.6 |
| `CipherSpec.txt` | `+CipherSpec.i2` `-CipherSpec.f2` | 5.6;5.7, 6.6 |
| `IvChainJunctionSpec-decrypt.txt` | `+CipherSpec.i2` `+IvParameterSpecSpec.c1` `+SecretKeySpecSpec.c1` `-IvParameterSpecSpec.c3` | 5.6;5.7, 4.4, 5.10;6.1, 3.3 |
| `IvChainJunctionSpec-gcm.txt` | `+CipherSpec.i2` `+SecretKeySpecSpec.c1` `-SecureRandomSpec.next2` | 5.6;5.7, 5.10;6.1, 4.5 |
| `IvChainJunctionSpec-rangen-unobserved.txt` | `+CipherSpec.i2` `+IvChainJunctionSpec.useRandomKey` `+SecretKeySpecSpec.c1` | 5.6;5.7, 5.1;5.5;5.8, 5.10;6.1 |
| `IvChainJunctionSpec-unprepared.txt` | `+CipherSpec.i2` `+IvChainJunctionSpec.use` `+IvParameterSpecSpec.c1` `+SecretKeySpecSpec.c1` `-IvParameterSpecSpec.c3` | 5.6;5.7, 5.1;5.5;5.8, 4.4, 5.10;6.1, 3.3 |
| `IvChainJunctionSpec.txt` | `+CipherSpec.i2` `+SecretKeySpecSpec.c1` `-SecureRandomSpec.next2` | 5.6;5.7, 5.10;6.1, 4.5 |
| `IvParameterSpecSpec-offset-unrandomised.txt` | `+IvParameterSpecSpec.c2` `-IvParameterSpecSpec.c4` | 4.4, 3.3 |
| `IvParameterSpecSpec-unrandomised.txt` | `+IvParameterSpecSpec.c1` `-IvParameterSpecSpec.c3` | 4.4, 3.3 |
| `KeyGeneratorSpec-rangen-unobserved.txt` | `+KeyGeneratorSpec.initRandomSize` | 5.5 |
| `KeyPairGeneratorSpec-rsa3072.txt` | `-KeyPairGeneratorSpec.gen` | 3.6 |
| `MacSpec-decrypt-buffer.txt` | `+CipherSpec.i2` `+SecretKeySpecSpec.c1` `-SecureRandomSpec.next2` | 5.6;5.7, 5.10;6.1, 4.5 |
| `MacSpec-encrypted-buffer.txt` | `+CipherSpec.i2` `+SecretKeySpecSpec.c1` `-SecureRandomSpec.next2` | 5.6;5.7, 5.10;6.1, 4.5 |
| `MacSpec-fresh-buffer.txt` | `+CipherSpec.i2` `+SecretKeySpecSpec.c1` `-MacSpec.f2` `-SecureRandomSpec.next2` | 5.6;5.7, 5.10;6.1, 4.5 |
| `MacSpec-hmacpbesha1.txt` | `+MacSpec.f1Input` `+MacSpec.i1` `-MacSpec.f1` | 5.6;5.7, 4.9 |
| `MacSpec-unsafe-generated-key.txt` | `+MacSpec.f1Input` `-MacSpec.f1` | 5.6;5.7 |
| `PBEKeySpecSpec-lowiter.txt` | `+PBEKeySpecSpec.c1` `-PBEKeySpecSpec.err1` `-PBEKeySpecSpec.err2` `-PBEKeySpecSpec.err3` | 3.5;4.6, 3.5 |
| `PBEKeySpecSpec.txt` | `+PBEKeySpecSpec.c1` `-PBEKeySpecSpec.c2` `-PBEKeySpecSpec.err2` `-PBEKeySpecSpec.err3` | 3.5;4.6, 4.6, 3.5 |
| `PBEParameterSpecSpec-lowiter.txt` | `+PBEParameterSpecSpec.c1` `-PBEParameterSpecSpec.c3` | 3.6;4.7 |
| `PBEParameterSpecSpec.txt` | `+PBEParameterSpecSpec.c1` `-PBEParameterSpecSpec.c3` | 3.6;4.7 |
| `SSLContextSpec-sslv3.txt` | `-SSLContextSpec.unsafe_protocol` | 3.6 |
| `SecretKeySpec-hardcoded-iv.txt` | `+IvParameterSpecSpec.c1` `+SecretKeySpecSpec.c1` `-IvParameterSpecSpec.c3` `-SecretKeySpecSpec.c3` | 4.4, 5.10;6.1, 3.3, 3.4;4.10 |
| `SecretKeySpec-laundered-material.txt` | `+SecretKeySpecSpec.c1` `-SecretKeySpecSpec.c3` | 5.10;6.1, 3.4;4.10 |
| `SecretKeySpecSpec-badalg.txt` | `+SecretKeySpecSpec.c1` `-SecretKeySpecSpec.c3` | 5.10;6.1, 3.4;4.10 |
| `SecureRandomSpec-unrandomised-constructor.txt` | `+SecureRandomSpec.c2` `-SecureRandomSpec.c3` | 3.1;5.5 |
| `SecureRandomSpec-unrandomised-seed.txt` | `+SecureRandomSpec.setSeed2` `-SecureRandomSpec.next2` `-SecureRandomSpec.setSeed3` | 3.1;4.5, 4.5, 3.1 |
| `SignatureSpec-sha512withdsa.txt` | `-SignatureSpec.g3` `-SignatureSpec.s1` `-SignatureSpec.update` | 3.6 |
| `TrustManagerFactorySpec-sunx509.txt` | `-TrustManagerFactorySpec.g3` | 3.2 |

### `removed` — 7 traces

| trace | delta de acusação | tarefa |
|---|---|---|
| `MacSpec-ungenerated-key.txt` | `-MacSpec.f1` | 5.6;5.7 |
| `PBEKeySpecSpec-conforming.txt` | `-PBEKeySpecSpec.c2` `-PBEKeySpecSpec.err2` | 4.6, 3.5 |
| `PBEKeySpecSpec-salt-only.txt` | `-PBEKeySpecSpec.c2` `-PBEKeySpecSpec.err2` | 4.6, 3.5 |
| `SSLContextSpec-sslv3-no-init.txt` | `-SSLContextSpec.unsafe_protocol` | 3.6 |
| `SecureRandomSpec-nextbytes-twice.txt` | `-SecureRandomSpec.next2` | 4.5 |
| `SignatureSpec-sha512withdsa-no-init.txt` | `-SignatureSpec.g3` | 3.6 |
| `TrustManagerFactorySpec-sunx509-no-init.txt` | `-TrustManagerFactorySpec.g3` | 3.2 |

---

## 5. Um achado que a tarefa não pedia: dez relatórios commitados não reproduziam

A regeneração de hoje difere dos relatórios `f2-*.md` commitados em **17 linhas de envelope,
espalhadas por 10 arquivos**. Zero linhas de tabela mudaram: as classificações, as contagens
`61/31/32/7` e as listas de eventos acusados são as mesmas. O que mudou é a mensagem colada a
algumas acusações.

E a mensagem commitada era a **inconsistente**. Dois exemplos:

```
commitado: CipherSpec-nofinal-arg.txt (B) ev=f1 … type=UnsatisfiedConstraint  code=CIPHER-NOBS-00  ev=i2
hoje:      CipherSpec-nofinal-arg.txt (B) ev=f1 … type=InvalidSequenceOfMethodCalls code=CIPHER-ORDER-00 ev=f1

commitado: CipherSpec-guard-on-field.txt (B) ev=i2 … code=CIPHER-ORDER-00 ev=i1
hoje:      CipherSpec-guard-on-field.txt (B) ev=i2 … code=CIPHER-ORDER-00 ev=i2
```

Uma acusação rotulada `ev=f1` carregava um envelope carimbado `ev=i2` — a mensagem de **outra**
acusação do mesmo trace. Hoje cada envelope nomeia o seu próprio evento, que é o que a gramática
`v=1 code=… ev=…` do conjunto diz que deve acontecer.

O item 27 da receita foi aplicado antes de acusar a passagem de hoje, e a cadeia inteira de
entradas foi conferida:

| entrada | estado |
|---|---|
| `jca_android/` e `backup/gh105-preimage/` | árvore de trabalho **limpa** contra o `HEAD` |
| `scripts/gh104_diff_harness.py` entre `f010cb92` e `HEAD` | só `black` e docstrings; **nenhuma mudança de comportamento** |
| `TraceRunner` compilado | 2026-08-23 01:58, **anterior** aos três commits e inalterado desde |
| classpath em cache | 2026-08-23 02:00, idem |
| monitor em cache (impressão digital do conteúdo do conjunto) | idêntico ao regenerado do zero, conferido |
| duas passagens em cache + uma sem cache | **byte a byte iguais** |

A regeneração de hoje reproduz exatamente o estado **anterior** ao commit `f010cb92`, que é
quem introduziu as 17 linhas. Ou seja: `f010cb92` commitou relatórios que a árvore, no seu
próprio estado, não produz. A regra vale — *quando o artefato discordar da árvore, a árvore
ganha* —, e os dez relatórios são substituídos pelo que o harness produz hoje.

### O mecanismo, que vale mais que o reparo

`TraceRunner.envelope(...)` devolve **um** envelope por evento acusador, e escolhe-o assim:

```java
private String envelope(Set<ErrorDescription> errors, String spec, String event) {
    for (ErrorDescription error : errors) {
        if (spec.equals(error.getSpec())) { return "spec=… ,ev=" + event + ",type=" + …; }
    }
```

O laço varre **o conjunto acumulado do trace inteiro** e devolve o primeiro cujo `spec` bate — que
não é necessariamente o que este evento acabou de levantar. Duas consequências, ambas medidas:

1. **Quando um corpo de evento levanta duas acusações, só uma aparece.** Provado com uma sonda
   sobre o mesmo classpath: o `ErrorCollector` fica com as duas (`tamanho=2`) e itera
   `SSLCONTEXT-NOBS-01` antes de `SSLCONTEXT-PROTO-00`. O relatório mostra a primeira.
2. **Quando um evento anterior do mesmo `spec` já deixou uma acusação no conjunto, um evento
   posterior pode exibir a mensagem dela** — que é exatamente a forma das 17 linhas: uma acusação
   rotulada `ev=f1` com o envelope carimbado `ev=i2`.

O rótulo `ev=` de fora do envelope (`spec=…,ev=f1,…`) é do evento certo — é escrito pelo
`TraceRunner` a partir de `monitorCall.eventId`. O `ev=` de dentro vem da mensagem escolhida.
Quando os dois discordam, é este mecanismo, e não a especificação.

**Nada disto move a classificação.** `classify` compara conjuntos de **eventos acusadores**, que
o `TraceRunner` monta a partir de `accusingEvents`, e não os envelopes: os `61/31/32/7` e as 130
atribuições acima são sobre a acusação, não sobre a mensagem. O que o mecanismo afeta é a leitura
de *qual código* uma acusação emitiu — e é por isso que a tarefa 8.3 não lê os veredictos daqui.

**É o item 26 outra vez, de outro ângulo**: as quatro suítes estavam verdes com os relatórios
errados commitados, porque nenhuma delas compara relatório regenerado com relatório commitado.

---

# Re-execução sob o instrumento reparado — tarefa 10.9 (2026-08-25)

**Por que reexecutar.** Tudo acima foi medido em 23/08 sob o harness **pré-11.11**, cujo
`classify()` comparava **nomes de eventos acusadores**. Sob esse instrumento, uma acusação
*acrescentada num evento que já acusava* era invisível por construção: o conjunto de eventos não
mudava, e o traço saía `unchanged`. A atribuição "130/130, zero sem dono" é, portanto, uma
afirmação do instrumento de antes do reparo — verdadeira sobre o que ele podia ver, e não sobre o
conjunto. O harness de hoje compara **(evento, código)**, e esta seção refaz a varredura com ele.

**A varredura.** `A = backup/gh105-preimage/jca_android` (a pré-imagem que a 2.11 arquivou),
`B = rvsec/rvsec-mop/src/main/resources/jca_android` (a árvore de hoje), corpus
`data/gh104/traces` inteiro. Os 24 relatórios por especificação estão commitados em
`data/gh105/evidence/harness/f7-sweep/`, um por arquivo, com a linha de cada traço e os
envelopes dos dois lados — é ali que se audita qualquer classificação individual.

```
173 traços:  46 unchanged · 52 moved · 48 introduced · 27 removed
```

**127 classificações não-`unchanged`**, contra 70 em 131 traços na passagem de 23/08. As duas
medições não são comparáveis traço a traço, e a razão é tripla, o que precisa ficar dito em vez de
escondido numa diferença de números:

1. **O corpus cresceu de 131 para 173.** Os 42 traços novos entraram com as tarefas dos grupos 8,
   9 e 10 que os escreveram para medir os próprios reparos, cada um com a sua evidência.
2. **O lado B mudou.** Entre 23/08 e hoje aterrissaram o grupo 9 inteiro (19 tarefas, dez delas
   mudando o que é acusado, todas com par de arnês e decisão do pesquisador) e o grupo 10. Um
   diferencial contra a mesma pré-imagem mede a change acumulada, não o que ela era em 23/08.
3. **O instrumento mudou**, que é o ponto desta tarefa: acusações somadas a eventos já acusadores
   agora aparecem.

**O que a varredura verifica hoje.** A propriedade que ela existe para checar não é o número, é a
posse: *nenhuma classificação não-`unchanged` pertence a uma especificação que esta change não
editou*. Ela vale — as vinte especificações com delta são exatamente as vinte que o
`divergence_record.csv` registra com hunks desta change, e as quatro sem delta nenhum
(`CipherOutputStreamSpec`, `DHGenParameterSpecSpec`, `HMACParameterSpecSpec`,
`RandomStringPassword`) são as que só receberam migração de substrato ou, no caso do último, a
retirada de escritas que não acusam nada.

| especificação | traços | não-`unchanged` | moved | introduced | removed | unchanged |
|---|---|---|---|---|---|---|
| `CipherSpec` | 19 | **17** | 11 | 6 | 0 | 2 |
| `SSLContextSpec` | 12 | **11** | 6 | 4 | 1 | 1 |
| `SignatureSpec` | 12 | **11** | 2 | 6 | 3 | 1 |
| `MacSpec` | 11 | **10** | 4 | 3 | 3 | 1 |
| `TrustManagerFactorySpec` | 10 | **9** | 3 | 5 | 1 | 1 |
| `IvChainJunctionSpec` | 7 | **7** | 5 | 2 | 0 | 0 |
| `PBEKeySpecSpec` | 7 | **7** | 5 | 0 | 2 | 0 |
| `SecureRandomSpec` | 11 | **7** | 2 | 0 | 5 | 4 |
| `KeyPairSpec` | 6 | **6** | 0 | 3 | 3 | 0 |
| `MessageDigestSpec` | 10 | **6** | 0 | 6 | 0 | 4 |
| `SecretKeySpecSpec` | 7 | **6** | 3 | 3 | 0 | 1 |
| `KeyStoreSpec` | 9 | **5** | 0 | 1 | 4 | 4 |
| `GCMParameterSpecSpec` | 6 | **4** | 0 | 4 | 0 | 2 |
| `KeyPairGeneratorSpec` | 8 | **4** | 1 | 0 | 3 | 4 |
| `PBEParameterSpecSpec` | 6 | **4** | 2 | 2 | 0 | 2 |
| `SecretKeySpec` | 5 | **4** | 2 | 2 | 0 | 1 |
| `KeyGeneratorSpec` | 8 | **3** | 2 | 0 | 1 | 5 |
| `KeyManagerFactorySpec` | 5 | **3** | 2 | 1 | 0 | 2 |
| `IvParameterSpecSpec` | 4 | **2** | 2 | 0 | 0 | 2 |
| `CipherInputStreamSpec` | 3 | **1** | 0 | 0 | 1 | 2 |
| `CipherOutputStreamSpec` | 2 | **0** | 0 | 0 | 0 | 2 |
| `DHGenParameterSpecSpec` | 1 | **0** | 0 | 0 | 0 | 1 |
| `HMACParameterSpecSpec` | 1 | **0** | 0 | 0 | 0 | 1 |
| `RandomStringPasswordSpec` | 3 | **0** | 0 | 0 | 0 | 3 |
**A granularidade da atribuição, dita com franqueza.** A passagem de 23/08 atribuiu **delta a
delta**, 130 de 130. Esta atribui **por especificação**: cada arquivo com delta tem, no
`divergence_record.csv`, as tarefas desta change que o editaram, e cada relatório por
especificação está commitado para que a leitura traço a traço seja possível sem reexecutar nada.
Uma reatribuição delta a delta sobre a árvore de hoje mediria a change acumulada dos grupos 1 a
10 de uma vez, e não é o que esta tarefa pede: o que ela pede é que a afirmação de 23/08 deixe de
ser a única, e que a que fica seja de um instrumento que enxerga o que o outro não enxergava.

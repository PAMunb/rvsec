# Tarefa 9.15 — as duas `Cipher*Stream`, e um reparo cuja massa medida é zero

**Data**: 2026-08-25 · **Decisão**: GO fraco — reparar em vez de registrar (pesquisador, 25/08)
**Par**: `A = pós-9.11` · `B = A + 9.15` · `~/tmp-gh104/g9b/pair-915.json`

## O reparo é maior do que a tarefa dizia

A tarefa falava só do cabeçalho: as duas specs declaravam `CipherInputStreamSpec()` e
`CipherOutputStreamSpec()`, sem parâmetro, então cada uma era **uma instância por processo**.

Declarar o parâmetro, porém, é metade. Lido o arquivo, **nenhum dos eventos ligava objeto algum** —
nem `returning`, nem `target`:

```
event c1  after(): call(public CipherInputStream.new(InputStream, Cipher)) { }
event r1  after(): call(public int CipherInputStream.read()) || ...
event cl1 after(): call(public void CipherInputStream.close()) { }
```

Uma spec paramétrica cujo evento não liga objeto recebe do gerador o mapa sem parâmetro e roda no
monitor raiz **e em todo monitor vivo da especificação** — a difusão que a task 9.3 fechou no
`PBEKeySpecSpec`. Então o reparo é: declarar o parâmetro **e** ligar em cada evento — o construtor
por `returning` (precedente `PBEKeySpecSpec.f1`, que faz isso sobre um `new`), os demais por
`target`.

Nove eventos ao todo (4 + 5). O `r1`/`w1` foram quebrados em linhas para que o `target` se aplique
à disjunção inteira e não só à última `call`.

## O G-BIND deixou de pular as duas

Uma especificação **não-paramétrica é skip declarado** do G-BIND, não passe: se ela não tem
parâmetro, "não liga objeto" é o que todos os seus eventos fazem. Enquanto estas duas eram
não-paramétricas, o gate **não olhava para elas**. Depois do reparo:

```
antes:  G-BIND 843 checked, 0 failed, 3 allow-listed, 24 skipped
depois: G-BIND 854 checked, 0 failed, 3 allow-listed, 22 skipped
```

Onze verificações a mais, dois skips a menos. É o efeito colateral que mais vale a pena registrar:
o reparo não só corrige o comportamento, como põe os dois arquivos sob um gate que os ignorava.

## O medido

```
pair-915: 172 traces  {"unchanged": 171, "removed": 1}
```

| | `CipherInputStreamSpec-two-streams.txt` |
|---|---|
| **A** | `c1:CIPHERINPUTSTREAM-ORDER-00`, `r1:CIPHERINPUTSTREAM-ORDER-00`, `cl1:CIPHERINPUTSTREAM-ORDER-00` |
| **B** | *(nada)* |

Três acusações num programa conforme, em três sítios: o segundo construtor chega onde o autômato
espera a sequência do primeiro stream, e depois disso o monitor único está no sumidouro `fail`, de
onde `read` e `close` acusam de novo. Depois: um monitor por stream, e cada
`c1 (r1|r2)+ cl1` é aceito por si.

## Massa: zero, e o que isso significa

**0 linhas de 97.018** (`conformance_record.csv` item (b)). O reparo é **livre de consequência de
corpus**: nenhum número publicado se move. A tarefa oferecia explicitamente as duas saídas —
reparar ou deixar registrado — e a escolha foi reparar, porque consertar o `KeyStoreSpec` na 9.14 e
deixar estas duas manteria no conjunto exatamente a inconsistência que esta change existe para
tirar.

A evidência diz isso em vez de alegar delta: a única testemunha do reparo é o trace escrito para
ele.

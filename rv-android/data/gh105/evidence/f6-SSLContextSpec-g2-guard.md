# Tarefa 9.17 — a guarda de protocolo do `g2`, e o que o arnês mostrou que o texto não previa

**Data**: 2026-08-25 · **Decisão**: GO (pesquisador, 25/08, `docs/20260825_dossie_decisao_9b_gh105.md`)
**Par**: `A = jca_android` (pré-9.B) · `B = A + 9.17` · `~/tmp-gh104/g9b/pair-917.json`

## O reparo

`SSLContextSpec.mop` tinha, no `g2`, a guarda que a task 3.6 tirou do `g1`:

```
condition(ConscryptAliasTable.matches("SSLContext", protocol, protocols))
```

Ela saiu. A api30 ordena `Gets, Init, Engine?` com o protocolo em CONSTRAINTS
(`SSLContext.cryptsl:39,:43`), então `getInstance` é um `Gets` seja qual for o protocolo pedido —
o mesmo argumento com que a 3.6 fundiu o `unsafe_protocol` no `g1`.

## O corpus não carregava o caso, e essa é a primeira medição

A primeira passagem do par deu **159/159 `unchanged`**. Não porque o reparo não faça nada: porque
**nenhum dos 159 traces exercitava `SSLContext.getInstance(String, String)`**. Os oito traces de
`SSLContextSpec` usam todos a forma de um argumento.

O trace `data/gh104/traces/SSLContextSpec-provider-sslv3.txt` foi escrito para o caso, na mesma
convenção dos `SSLContextSpec-d15-*.txt` ("o corpus não pode fornecer o caso, então ele é
reproduzido aqui"). Conferido antes no JVM: `SSLContext.getInstance("SSLv3", "SunJSSE")` produz
mesmo o contexto e `getProtocol()` responde `SSLv3`, então a guarda vê nos dois lados o valor que
o trace nomeia.

## O medido — e o texto da tarefa estava errado por metade

```
pair-917: 172 traces  {"unchanged": 171, "moved": 1}
```

A única linha que se move é o trace novo:

| | `SSLContextSpec-provider-sslv3.txt` |
|---|---|
| **A** | `init:SSLCONTEXT-NOBS-00`, `init:SSLCONTEXT-NOBS-01`, **`init:SSLCONTEXT-ORDER-00`**, `init:SSLCONTEXT-PROTO-00` |
| **B** | `init:SSLCONTEXT-NOBS-00`, `init:SSLCONTEXT-NOBS-01`, `init:SSLCONTEXT-PROTO-00` |

A tarefa dizia que o protocolo rejeitado era "reported as a wrong call sequence **instead of** a
rejected protocol". **Falso**: o `init` já acusava PROTO-00 no lado A. O corpo do evento roda
independentemente do autômato, então o defeito era **relato duplicado**, não substituição — uma
acusação de sequência errada empilhada sobre a acusação certa. O que o reparo remove é a primeira.

O comentário do `.mop` e o texto do trace foram corrigidos para o medido. As duas linhas `NOBS`
são sobre os arrays de manager nulos do trace e não se movem: elas isolam o delta.

## O resíduo, que agora tem linha própria

Um `getInstance` cujo protocolo a regra rejeita e que **nunca é `init`-ado** fica sem acusação
nenhuma, porque a acusação vive no corpo do `init`. É o mesmo resíduo da 3.6, e a verificação de
25/08 mediu que ele **não tinha** linha `behavioural` própria no `divergence_record.csv` (as nove
linhas `behavioural` não o incluíam) — vivia no comentário do arquivo e na prosa dos hunks
`:211,:213`. Agora tem: o hunk `SSLContextSpec.mop 16e3bbdd917c`.

## Precondição da 9.1

Este reparo fecha uma das três origens de `SSLContext` que o conjunto não observa nascer. Com a
guarda, o despachante rodava `FindOrCreateEntry` e deixava o objeto com monitor em estado 0 —
exatamente o estado de onde a 9.1, ao reviver o `engine`, acusaria `SSLCONTEXT-ORDER-00`. Por isso
a 9.17 vem antes.

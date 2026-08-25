# Tarefa 9.14 — o `KeyStoreSpec` deixa de ser um monitor por processo

**Data**: 2026-08-25 · **Decisão**: GO (pesquisador, 25/08), sequenciada com a 9.16 como uma só
**Par**: `A = pós-9.17` · `B = A + 9.14` · `~/tmp-gh104/g9b/pair-914.json`

## O reparo é um token, e é isso que o torna difícil de ver

`KeyStoreSpec(KeyStore ks)` → `KeyStoreSpec(KeyStore k)`.

O arquivo declarava o parâmetro `ks` e **nenhum dos sete eventos o ligava**: os dois `getInstance`
ligam `returning(KeyStore k)` e os outros cinco `target(k)`. Conferido por grep: `ks` aparecia
**uma vez no arquivo inteiro**, na própria declaração. Um nome que evento nenhum liga não faz o
arquivo não-paramétrico de um jeito que o leitor veja, e não quebra a compilação — o gerador
simplesmente emite **um monitor por processo**. O precedente correto está ao lado:
`KeyGeneratorSpec(KeyGenerator k)`, cujos eventos ligam `k`.

## O medido

O corpus não tinha trace com dois key stores vivos ao mesmo tempo. Escrito:
`data/gh104/traces/KeyStoreSpec-two-stores.txt`.

```
pair-914: 172 traces  {"unchanged": 171, "removed": 1}
```

| | `KeyStoreSpec-two-stores.txt` |
|---|---|
| **A** | `g1:KEYSTORE-ORDER-00`, `load:KEYSTORE-ORDER-00` |
| **B** | *(nada)* |

Duas acusações num programa conforme, em dois sítios: no segundo `getInstance` (que chega onde o
`ere` espera um `load`) e no `load` seguinte (o monitor já está no sumidouro `fail`). Depois: um
monitor por store, e cada `g1 load` é aceito por si.

## Massa, e o efeito de segunda ordem que precisa ser dito

**8.655 `InvalidSequenceOfMethodCalls` + 2.005 `InvalidKeyStoreType` sobre 22 apps**
(`conformance_record.csv` item (a)) — a maior massa do bloco. É **teto do que o reparo poderia
mover, nunca atribuição causal**: foi medida na campanha publicada, sobre o `jca` congelado, e o
tecelão foi reparado entre aquela campanha e hoje.

O efeito de segunda ordem vale declarar porque contraria a intuição de "menos linhas": hoje o
monitor único, uma vez em `fail` (sumidouro), **absorve tudo o que vem depois numa acusação só**;
parametrizado, cada store acusa por si. Então a **contagem bruta de linhas pode subir** enquanto o
conjunto de programas acusados encolhe. As linhas novas são corretas; a contagem bruta não é a
métrica. É a mesma lição que a dedup por sítio do `ErrorCollector` deu nas tarefas 9.2 e 9.3 —
contar sítios, nunca emissões.

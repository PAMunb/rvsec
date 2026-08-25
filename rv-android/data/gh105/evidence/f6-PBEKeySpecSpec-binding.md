# Tarefa 9.3 — os dois últimos eventos que não ligavam o objeto monitorado

**Data**: 2026-08-25 · **Commit da árvore**: `70877f67`
**A** `~/tmp-gh104/g9impl/B2` (o conjunto após a 9.2, antes da 9.3) ·
**B** `~/tmp-gh104/g9impl/B3` · **corpus** `data/gh104/traces` (159)

## 1. O reparo

`PBEKeySpecSpec.mop`: `f1` e `f2` ganham `returning(PBEKeySpec s)`.

Antes ligavam `char[] password` e nenhum `PBEKeySpec`. A especificação é paramétrica —
`PBEKeySpecSpec(PBEKeySpec s)` — e o gerador indexa os monitores por esse parâmetro; um evento
que não o nomeia recebe o mapa **sem parâmetro** (`PBEKeySpecSpec__Map`,
`stateTransitionedSet.event_f1`) e roda o corpo no monitor-raiz **e em todo monitor vivo da
especificação**. É difusão para o conjunto onde a regra fala de um objeto.

Numa `call` a construtor o valor retornado é o próprio objeto em construção — o mesmo idioma
que o `c1` do arquivo já usava, e o que o `MacSpec.f2` recebeu na task 5.3.

## 2. O autômato não se move

`(f1 | f2)*` é o laço benigno que a task 3.5 instalou; os dois eventos estão absorvidos nos
grupos de Kleene do `ere`, em toda posição, porque a ordenação nada tem a dizer sobre uma
chamada que a regra recusa. Nada no `ere` muda.

## 3. A ligação existiu e foi perdida na semeadura

O conjunto arquivado `jca_android_bug_predicate/PBEKeySpecSpec.mop:26,32` **já declarava**
`returning(PBEKeySpec s)` nos dois eventos. O congelado `jca/PBEKeySpecSpec.mop:21,27` não.
Como a task 2.1 resemeou o sucessor a partir do congelado, a ligação saiu junto. Não é uma
omissão que ninguém tinha visto: é uma que tinha sido feita e foi desfeita por herança.

## 4. O arnês, e por que `unchanged` era a previsão

```
A=g9impl/B2  B=g9impl/B3   →   {"unchanged": 159}
```

Os sete traces de `PBEKeySpecSpec`, sítio a sítio, idênticos nos dois lados:

| trace | A | B |
|---|---|---|
| `PBEKeySpecSpec-forbidden.txt` | `f1:PBEKEYSPEC-FORB-00` | idem |
| `PBEKeySpecSpec-forbidden3.txt` | `f2:PBEKEYSPEC-FORB-01` | idem |
| `PBEKeySpecSpec-forbidden-then-clear.txt` | `c2:PBEKEYSPEC-ORDER-00`, `f1:PBEKEYSPEC-FORB-00` | idem |
| `PBEKeySpecSpec-lowiter.txt` | `c1:PBEKEYSPEC-CONSTR-00`, `c1:PBEKEYSPEC-NOBS-01` | idem |
| `PBEKeySpecSpec.txt` | `c1:PBEKEYSPEC-NOBS-01` | idem |
| `PBEKeySpecSpec-conforming.txt` | — | — |
| `PBEKeySpecSpec-salt-only.txt` | — | — |

`unchanged` era a previsão escrita na tarefa, e pela mesma razão da 9.2: a difusão multiplica
**emissões**, não linhas. Todas as cópias compartilham `(spec, código, evento, sítio)` e o
`ErrorCollector` as deduplica. O que o reparo compra é semântica de traço por objeto, o fim
da difusão ao conjunto, e a classe que o G-BIND agora tranca — não menos relatórios.

## 5. O gate que fecha a classe

`scripts/gh105_spec_gates.py --gate G-BIND`, sobre o universo enumerado (5 conjuntos):

```
G-BIND: 843 checked, 0 failed, 3 allow-listed, 24 skipped
```

Caminho vermelho medido sobre o instantâneo pré-reparo (`g9impl/B2`):

```
G-BIND: 125 checked, 2 failed
  [G-BIND] B2/PBEKeySpecSpec.f1:33 ...
  [G-BIND] B2/PBEKeySpecSpec.f2:40 ...
```

Exatamente os dois sítios, e nenhum outro. Os 3 `allow-listed` são do congelado `jca`
(`PBEKeySpecSpec.f1`/`f2` — este mesmo defeito, num arquivo que não pode ser editado — e
`SSLContextSpec.unsafe_protocol`, evento que a task 3.6 removeu do sucessor). Os 24 `skipped`
são especificações não-paramétricas, para as quais um monitor único é a declaração e não um
defeito.

Isto fecha o item (c) do `conformance_record.csv`, a classe `empty-binding broadcast`:
`MacSpec.f2` reparado na 5.3, `SSLContextSpec.unsafe_protocol` removido na 3.6,
`TrustManagerFactorySpec.g3/gtm1` reparados desde, e estes dois agora.

## 6. O comentário do arquivo

Reescrito para a ligação nova. A acusação de "past tense" que uma redação anterior da tarefa
fazia não procedia: `:27-29` descrevia o despacho ao conjunto **no presente**, corretamente;
o que estava no passado era só a linha all-`fail` que a 3.5 removeu.

## 7. Registro

`divergence_record.csv`: hunks `71771552287b` (automaton), `2d1f754de24c` e `3b34a3d65b42`
(message), task 9.3, absorvendo `4d4ebb2e0523`, `3d043f090b09`, `de44d903848c` e
`57cd8e7772b7`. `codes.csv` re-ancorado nas linhas novas de `PBEKEYSPEC-FORB-00/01`.

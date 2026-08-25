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

## O segundo resíduo, achado pela 9.18: o portão perdeu a cláusula de vista

A verificação do grupo (9.18) achou o G-CONF vermelho com uma cláusula sem lastro:

```
SSLContextSpec | SSLContext.crysl:29 | CRYSL-NAO-IMPLEMENTADO |  | protocol in {"TLSv1.2","TLSv1.3"} | unbacked
```

O veredito é **falso**, e vale ler por quê antes de qualquer coisa: a cláusula continua
implementada, em `SSLContextSpec.mop:195`, dentro do corpo do `init`, contra a mesma lista
`protocols` do campo `:43`. Nenhum programa muda o que é acusado por causa deste achado — é o
portão que deixou de enxergar, não a especificação que deixou de acusar.

A causa é o casador. O `_list_guarding` do `gh104_gates.py` liga uma cláusula de CONSTRAINTS ao
`.mop` **pelo pointcut**: acha o evento cujo `call(...)` corresponde ao evento CrySL, usa
`args(...)` para achar a posição, a posição dá o objeto, e procura a lista na guarda **daquele
evento**. O objeto `protocol` é ligado pelo `getInstance` — isto é, pelo `g1` e pelo `g2`. A 3.6
tirou a guarda do `g1` e esta tarefa tirou a do `g2`; o `init`, que é onde a lista ficou, não liga
`protocol` nenhum (seu pointcut liga `kms`, `tms` e `ctx`). Sem guarda no evento que liga o objeto,
o casador não achava nada e o veredito caía para "a cláusula não alcança guarda alguma".

Medido contra o snapshot `~/tmp-gh104/g9b/A0-baseline`: era o `SSLContextSpec.mop:97` do `g2` —
`condition(ConscryptAliasTable.matches("SSLContext", protocol, protocols))` — o sítio que o portão
lia. Com ele, o veredito era diferença de lista, e as duas linhas de registro que já existiam
davam conta dela: a narrativa `spelling-variant` do `divergence_record.csv` e a linha
`transcription` do `conformance_record.csv` (`mop_literals: TLSV1.2, TLSV1.3, TLS` contra
`rule_literals: TLSv1.2, TLSv1.3`). Ao virar `CRYSL-NAO-IMPLEMENTADO`, o veredito saiu de
`LIST_DIFFERENCE_VERDICTS` e as duas linhas deixaram de servir de lastro — não porque o registro
piorasse, mas porque um registro sobre listas que diferem não responde por uma cláusula que não
seria implementada.

**Decisão (pesquisador, 25/08): estender o casador, não registrar.** Registrar exigiria uma linha
lastreando a afirmação de que a cláusula não alcança guarda alguma, que é falsa, e que perdoaria em
silêncio a remoção real da guarda no dia em que ela acontecesse. O reparo está em
`scripts/gh104_gates.py`, `_list_guarding`: depois que a ligação por pointcut falha — e só depois —
o casador procura a forma migrada, a lista testada contra `<objeto>.get<Objeto>()` em qualquer
evento da mesma especificação.

Isso compara **um** identificador, o nome do getter contra o nome do objeto CrySL, onde o docstring
da função diz que ali nada compara identificadores. A exceção está escrita no próprio docstring com
a razão: `ctx.getProtocol()` nomeia o objeto `protocol` da `SSLContext.crysl`, e nada mais fraco
serviria, porque uma guarda sobre outro getter do mesmo objeto seria outra cláusula.

Medido sobre as 80 cláusulas do conjunto, a extensão move exatamente uma linha:

```
- SSLContextSpec | SSLContext.crysl:29 | CRYSL-NAO-IMPLEMENTADO |            | unbacked
+ SSLContextSpec | SSLContext.crysl:29 | MOP-MAIS-PERMISSIVO   | ...mop:43  | divergence_record.csv: spelling-variant
```

`MOP-MAIS-PERMISSIVO` é a relação verdadeira: o `.mop` admite `TLS`, que o expert não lista, pela
razão que o comentário `:36-39` carrega — o Conscrypt liga `SSLContext.TLS` à implementação
TLSv1.2/TLSv1.3 (`OpenSSLProvider.java:81`).

O que este achado ensina, e que a 9.17 não previu: **tirar uma guarda de um evento pode cegar um
portão sem mudar uma acusação sequer.** Ao mover uma cláusula para outro evento, confira o que o
portão que a lia passa a ler.

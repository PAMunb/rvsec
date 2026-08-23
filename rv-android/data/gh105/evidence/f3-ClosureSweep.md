# F3 — a varredura de fecho, a aposentadoria do G-PRED2, e a verificação das oito remoções

**Lote B6** · tarefas **5.11** e **6.4** · um commit · 2026-08-22

Este é o lote que não edita nenhuma especificação. A 5.11 varre o que o conjunto escreve e o que
ele lê, escreve a disposição da última aresta aberta e aposenta o portão que a media; a 6.4
verifica oito apagamentos que outras passagens já tinham feito. Nenhum `.mop` muda, nenhuma trace
muda, e o corpus responde exatamente o que respondia antes. O que muda é o que o conjunto **diz
sobre si mesmo** — e uma das coisas que ele dizia estava errada por um.

---

## 1. A varredura: 22 valores escritos, 12 lidos, uma aresta aberta

A 5.11 pede a varredura sobre "todos os valores de `Property` escritos, não só os nomeados". O
enunciado dizia **21**. Medido contra a fonte (`grep -o "Property\.[A-Z_]*"` sobre os 23 `.mop` de
`jca_android`, e conferido contra as 70 linhas do `predicate_graph.csv`), são **22**.

A diferença é medida, não estimada: reconstituído o conjunto em `06b321f2~1`, dá exatamente 21, e
o 22º entra no próprio B5 — a 5.10 **renomeou** a escrita de `SecretKeySpec.mop:125` de
`RANDOMIZED` para `PREPARED_KEY_MATERIAL`, e como `RANDOMIZED` continua escrito em
`SecureRandomSpec.mop:315,325,329`, o conjunto distinto cresce em um sem mover nenhum censo de
operações. O enunciado da 5.11 estava certo quando foi escrito e ficou defasado em um pelo commit
anterior a este.

**Os 22, e como cada um fecha:**

| fecha por | valores |
|---|---|
| **leitor no conjunto** (12) | `ENCRYPTED`, `GENERATED_KEY`, `GENERATED_KEY_MANAGERS`, `GENERATED_KEY_STORE`, `GENERATED_PRIVATE_KEY`, `GENERATED_PUBLIC_KEY`, `GENERATED_TRUST_MANAGER`, `MACED`, `PREPARED_GCM`, `PREPARED_IV`, `PREPARED_KEY_MATERIAL`, `RANDOMIZED` |
| **registro `omission`** (9) | `DIGESTED`, `GENERATE_SSL_CONTEXT`, `GENERATE_SSL_ENGINE`, `GENERATED_KEY_PAIR`, `PREPARED_DH`, `PREPARED_HMAC`, `PREPARED_PBE`, `SIGNED`, `VERIFIED` |
| **aberta até esta tarefa** (1) | `SPECCED_KEY` |

Do outro lado, os **12 valores lidos** têm todos produtor no conjunto: nenhuma leitura órfã
sobrou, e a lacuna que a 5.11 nomeia — `GENERATED_PRIVATE_KEY`, lida e escrita por ninguém —
fechou na 4.13, que deu à chave privada a escrita que `generatedPrivkey[retPriv] after pr` nomeia.
Hoje ela tem duas escritas (`KeyPairSpec.mop:122`, `KeyStoreSpec.mop:156`) e quatro leituras.

Duas linhas do grafo carregam `omission` sobre predicados que **têm** leitor — 
`KeyManagerFactorySpec match1/GENERATED_KEY_MANAGERS` e
`TrustManagerFactorySpec match1/GENERATED_TRUST_MANAGER`. Não é resíduo: o portão acumula por
nome de predicado e não as levantaria, mas o registro é do **sítio**, e o que ele diz é que a
metade ligada à fábrica não tem leitor próprio — o consumidor do api30
(`SSLContext.cryptsl:48,50`) pede o predicado sobre o **array**, que é o sítio irmão no mesmo
arquivo. Fabricar leitor para a metade da fábrica acusaria programa conforme.

---

## 2. A cláusula #31, e por que a disposição é `omission` e não `unmonitored-consumer`

`PBEKeySpecSpec.mop c1` escreve `SPECCED_KEY` e nada no conjunto o lê. A razão pela qual nada o lê
já estava escrita pela 5.10, na coluna `reason` da mesma linha: o único `REQUIRES` que o api30
enuncia sobre o predicado é `SecretKeyFactory`, e essa regra **não tem `.mop` no conjunto** — a
cláusula #31 do ledger, categoria `unmonitored-consumer`.

Mas a disposição que fecha a linha não é essa palavra, e a distinção custou a forma do lote:

- `RECORDED_READ_DISPOSITIONS` (`scripts/gh105_predicate_graph.py:1179`) — `unclosable`,
  `unmonitored-producer`, **`unmonitored-consumer`**, `vacuous`, `propagation`;
- `RECORDED_WRITE_DISPOSITIONS` (`:1189`) — **`omission`**, `propagation`.

`unmonitored-consumer` é vocabulário de **leitura**. Uma escrita sem leitor fecha com `omission` e
com mais nada. O ledger categoriza a **cláusula**; esta coluna categoriza o **sítio**; e as duas
não são o mesmo vocabulário. A linha recebeu `disposition=omission` e a `reason` ganhou o
parágrafo que diz isso — e o número que a varredura mediu, para que a próxima passagem não tenha
de re-medi-lo.

**Medido depois da edição**: `gh105_predicate_graph.py --sets jca_android` → `findings: 0 failing`.
O round-trip do `--emit` devolve o arquivo byte a byte idêntico.

---

## 3. A aritmética do ledger estava errada por um — e a #17 é a que faltava sair

O enunciado da 5.11 declara o alvo: **24 fiadas + 11 registradas + `preparedEC` `unclosable`** =
36. O `design.md:489` já dizia **22 fiadas**, depois de a 5.2 e a 5.3 tirarem a #21 e a #23 da
coluna. Nenhum dos dois fecha com a árvore.

Contadas as cláusulas que **têm sítio de leitura** no `predicate_graph.csv` — que é o que "fiada"
quer dizer — são **21**. A que faltava sair da coluna é a **#17**,
`KeyPairGenerator {DH} => preparedDH[params]`, que a **5.8** registrou como
`unreachable-composition` e que nunca foi subtraída do total.

**Medição** (contra a fonte, não contra o artefato): `grep -rn "PREPARED_DH"` sobre o conjunto
inteiro devolve **uma** linha — `DHGenParameterSpecSpec.mop:37`, uma escrita. Zero leituras. A
cláusula é registrada, não fiada.

**A aritmética correta, e ela fecha em 36:**

| categoria | n | cláusulas |
|---|---|---|
| fiadas (têm sítio de leitura) | **21** | #5, #6, #8, #9, #10, #11, #12, #13, #14, #15, #16, #22, #24, #25, #28, #29, #32, #33, #34, #35, #36 |
| registradas `unmonitored-*` | 10 | #1, #2, #3, #4, #7, #18, #19, #26, #27, #31 |
| registradas `vacuous` | 2 | #23 (5.3), #30 (5.5) |
| registradas `unreachable-composition` | 2 | #17 (5.8), #21 (5.2) |
| `unclosable` | 1 | #20 (`preparedEC`) |
| **total** | **36** | |

Corrigido em cinco sítios pela skill: `design.md:104` (Goals), `design.md:489` (totais do ledger),
`tasks.md:471` (título do Grupo 5), `tasks.md:783` (enunciado da 5.11) e o cenário
*Closure over the wired set* em `specs/instrumentation/spec.md:833`. **Não** se tocou em
`spec.md:9`, que descreve a pré-imagem: lá "21 written `Property` values" continua sendo o número
certo, porque é o que o conjunto escrevia antes desta change.

---

## 4. A aposentadoria, e por que as três coisas viajam no mesmo commit

Escrita a disposição, o G-PRED2 vai a zero. E `gh105_gate_baseline.py:75-84` constrói `gates`
**só a partir de achados**, com `setdefault`: zero achados, nenhuma chave. A chave some do
baseline, e `test_a_retired_gate_leaves_the_baseline_and_stays_out` tinha uma asserção
(`assert "G-PRED2" in recorded["gates"]`) que existia exatamente para exigir que ninguém deixasse
o portão cair sozinho.

Confirmado contra o código antes de editar, simulando a disposição sobre uma cópia do grafo:

```
achados por portão APÓS a omission: {}
structural_findings: 0
chaves de gates: ['G-ORDER']
G-PRED2 presente? False
```

Então as três coisas foram no mesmo commit: a disposição, a entrada em `retired`, e a remoção da
asserção — que é o ato deliberado que o achado 58 descreve ("um portão que chega a zero não fica
protegido por isso"). Entre duas delas a suíte ficaria vermelha.

**`was: 36`, e não 1 nem 10.** As quatro aposentadorias já gravadas — G-ACC 17, INV-INS-133 27,
INV-INS-134 42, INV-INS-130 23 — batem todas com o **primeiro** `gate_baseline.json`
(`01a1373d`, antes da primeira edição da change), onde o G-PRED2 reportava **36**; e o docstring
do próprio teste diz que `was` é o que o portão reportava na árvore não modificada. O "ten rows"
que o docstring dizia era o estado do portão quando o Grupo 5 começou, e saiu (decisão do
pesquisador, 2026-08-22).

**E havia uma quarta obrigação, que nenhum registro previa.** Fechada a aresta, a suíte reprovou
em `test_the_suite_skips_the_frozen_sets_declaredly_rather_than_failing_them` — que afirma de onde
os achados podem vir com uma **igualdade** de conjuntos:

```
assert {finding.spec_set for finding in run.findings} == {"jca_android"}
E   AssertionError: assert set() == {'jca_android'}
```

A igualdade exigia, sem dizer, que existisse pelo menos um achado para poder afirmar de onde ele
vem. Virou subconjunto (`<=`), com a razão escrita no docstring: o que o teste afirma é que **nada
chega de um conjunto que estes portões não governam**, e isso é verdade do conjunto vazio e
continua verdade se um achado voltar. É a terceira face do achado 58 — um portão que chega a zero
não fica protegido por isso, e nem a suíte que o mede fica.

---

## 5. A 6.4: verificação por construção, e as âncoras do enunciado não resolvem na árvore

A 6.4 verifica que as oito remoções de predicado dentro de `@fail` (INV-INS-142) sumiram. Ela não
executa nenhuma: cada uma saiu com a passagem de arquivo que migrou a escrita que ela retirava — a
4.9 levou a do `MacSpec` e a 4.14 as outras sete.

**Medido sobre o conjunto inteiro:**

| medição | resultado |
|---|---|
| `remove(` em `jca_android/*.mop` | **0** |
| operações de predicado dentro de bloco `@fail` (varredura por chaves) | **0** |
| `ExecutionContext` em `jca_android/*.mop` | **0** |
| `negate(` | **1** — `PBEKeySpecSpec.mop:167`, a nona, que é tradução e a 6.5 já verificou |
| censo de colocação | `remove:fail == 0`, `negate:body == 1` |

**Os oito carregam hunk**, em seis entradas do `divergence_record.csv` — duas cobrem duas remoções
cada:

| remoção | hunk | linha |
|---|---|---|
| `MacSpec` (a que a 4.9 levou) | `3667658f9cf7` | `:245` |
| `TrustManagerFactorySpec` — `GENERATED_TRUST_MANAGER` e `GENERATED_TRUST_MANAGERS` | `0fd4fb92f7f3` | `:199` |
| `KeyStoreSpec` — `GENERATED_KEY` e `GENERATED_KEY_STORE` | `a92ed5c42e2d` | `:196` |
| `KeyManagerFactorySpec` — `GENERATED_KEY_MANAGERS` | `eaa0801a5e33` | `:181` |
| `KeyPairGeneratorSpec` — `GENERATED_KEY_PAIR` | `ee86d177e08f` | `:188` |
| `KeyGeneratorSpec` | `b22fbfe58fb8` | `:227` |

**Uma correção ao enunciado.** As âncoras que a 6.4 cita (`MacSpec.mop:99`,
`TrustManagerFactorySpec.mop:124,125`, `KeyStoreSpec.mop:92,93`, `KeyManagerFactorySpec.mop:104`,
`KeyPairGeneratorSpec.mop:133`, `KeyGeneratorSpec.mop:89`) **não resolvem na árvore atual nem no
seed `jca`** — resolvem no conjunto arquivado `jca_android_bug_predicate/`, que é onde o defeito
está preservado. Verificar "a contagem é zero" na árvore e "o hunk existe" no registro é o que a
tarefa pode verificar; as âncoras são endereços do arquivo morto.

---

## 6. Seis âncoras derivadas no `codes.csv`, achadas pela varredura

Reancorado o `codes.csv` inteiro por script (a âncora é a linha do `addError`, achado 83), **seis**
das 112 linhas apontavam para linha errada:

| código | era | é |
|---|---|---|
| `KEYPAIR-CONSTR-00` | `KeyPairSpec.mop:59` | `:64` |
| `KEYPAIR-NOBS-00` | `:63` | `:68` |
| `KEYPAIR-CONSTR-01` | `:68` | `:73` |
| `KEYPAIR-NOBS-01` | `:72` | `:77` |
| `KEYPAIR-ORDER-00` | `:128` | `:133` |
| `PBEKEYSPEC-ORDER-00` | `PBEKeySpecSpec.mop:175` | `:185` |

Deriva pré-existente das passagens que inseriram prosa acima do `addError` sem reancorar (as cinco
do `KeyPairSpec` derivam +5, a do `PBEKeySpecSpec` +10). Nenhum portão lê essa coluna, e é por isso
que a deriva sobreviveu — **fica registrado como matéria do endurecimento do Grupo 7**: uma âncora
que ninguém confere é uma âncora que a próxima passagem quebra de novo.

**Duas derivas de prosa ficam registradas e não reparadas aqui**, porque reparar comentário de
trace é mexer no corpus e este lote não mexe: `data/gh104/traces/PBEKeySpecSpec-salt-only.txt:2`
nomeia `PBEKEYSPEC-CONSTR-01`, código que não existe na árvore (o arquivo emite `CONSTR-00` em
`:105` e `CONSTR-02` em `:131`, saltando o `01`), e descreve uma leitura sobre a senha que a 5.4
removeu; e essa trace tem **corpo idêntico** ao de `PBEKeySpecSpec-conforming.txt`, diferindo só
no cabeçalho. Matéria da 7.x, junto com as âncoras.

---

## 7. O que NÃO se moveu, e a medida disso

| medida | antes | depois |
|---|---|---|
| linhas no `predicate_graph.csv` | 70 | 70 |
| verdicts (`read:body`/`read-absent`/`write:acceptance`/`write:body`/`negate:body`) | 33/5/26/5/1 | idênticos |
| censo do leitor (`read`+`read-absent` / `write`) | 38 / 31 | idênticos |
| hunks no `divergence_record.csv` | 278 (+5 narrativas) | idênticos |
| traces do corpus | 128 | 128 |
| evidência do harness (`git diff --stat`) | — | **zero arquivos** |
| `structural_findings` na baseline | 1 | **0** |
| achados dos gates | 1 (G-PRED2) | **0** |

O harness não foi re-rodado para gerar evidência nova, e a razão é a medida acima: nenhum `.mop`
mudou, então nenhuma trace pode ter mudado de resposta. A confirmação de abertura da sessão
(pré-imagem × árvore) deu os mesmos **60 unchanged · 30 moved · 31 introduced · 7 removed** do B5.

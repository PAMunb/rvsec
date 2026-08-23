# Tarefa 8.1 — a suíte de portões sobre o universo enumerado

**Data**: 2026-08-23 · **Commit da árvore**: `519f2ff8`
**Raiz dos conjuntos**: `rvsec/rvsec-mop/src/main/resources`

A tarefa pede sete portões sobre o universo inteiro — G-ORDER, G-PRED2, G-ACC, G-PARAM, as
regras de junção, a disciplina de import e a genericidade —, com **relatório de pulos
commitado**, os portões da gh104 ainda verdes e `test_jca_android_hunks_all_recorded` incluído.
Um portão que pula em silêncio não é um portão verde, e é por isso que o relatório de
skip-and-count é a metade que faltava: as contagens já corriam pelo `verify_all`.

---

## 1. O universo, enumerado

**215 arquivos `.mop` em cinco conjuntos.** O leitor lê 213 e **pula 2, ambos com razão
escrita**:

| conjunto | arquivos | lidos | pulados | sítios de predicado |
|---|---|---|---|---|
| `jca` (congelado) | 23 | 22 | **1** | 106 |
| `jca_android` (o conjunto desta change) | 24 | 24 | 0 | **70** |
| `jca_android_bug_predicate` (arquivado) | 23 | 22 | **1** | 147 |
| `generic` | 118 | 118 | 0 | 0 |
| `generic_new` | 27 | 27 | 0 | 0 |
| **total** | **215** | **213** | **2** | — |

Os dois pulos são o mesmo arquivo em dois conjuntos: `SecretKeySpecSpec.mop`, *unbalanced
parenthesis: unmatched `)` at line 30*. O sítio é o `condition(` que abre na linha 27 e fecha
numa linha só sua antes do `{` do corpo — um idioma de formatação que o leitor recusa em vez de
ler pela metade (`test_an_unbalanced_file_is_reported_and_not_half_read` é o teste que fixa essa
escolha). Os dois conjuntos onde ele aparece são **congelado** e **arquivado**: nenhum dos dois
pode ser reformatado por esta change, e o sucessor do mesmo arquivo, em `jca_android`, lê.

## 2. Os portões, contados e com os pulos nomeados

### G-ORDER — `gh105_order_gate.py --sets all`

```
13 passed · 0 failed · 9 allow-listed · 193 skipped  de 215
```

Os 193 pulos são de dois tipos, e nenhum é silencioso:

| razão | quantos |
|---|---|
| `the alphabet mapping covers the migrated set only` | **191** |
| `no rows in the alphabet mapping for X; G-ORDER never infers one` | **2** |

Os dois últimos são `jca_android/IvChainJunction` e `jca_android/RandomStringPassword` — as duas
especificações do conjunto migrado que não têm linha no mapeamento de alfabeto. O portão
**nunca infere** um mapeamento: a frase está no próprio relatório, e é a diferença entre um
portão que pula e um portão que inventa. As nove permitidas estão em
`data/jca_android/gate_allowlist.csv` com `event_or_state=order`.

Sobre o conjunto migrado sozinho: **13 / 0 / 9 / 2 de 24, exit 0**.

### G-PRED2, INV-INS-130 (import), INV-INS-133 e INV-INS-134 (colocação)

`gh105_predicate_graph.py --sets all`: **213 passaram, 0 falharam, 0 permitidas, 21
informativas**, e **16 pulos de portão**, que são quatro portões × quatro conjuntos, todos com a
mesma razão escrita:

> *the import, placement and closure contract governs the migrated set only; `<conjunto>` is
> frozen or predicate-free*

Os quatro conjuntos pulados são `jca` (congelado), `jca_android_bug_predicate` (arquivado),
`generic` e `generic_new` (sem substrato de predicado — 0 sítios nos dois). Sobra `jca_android`,
onde os quatro correm: **0 achados**.

### G-ACC — os órfãos, nas duas direções

**21 informativos, e zero em `jca_android`.** É o número que vale a pena ler duas vezes: o
conjunto migrado tem zero acusadores órfãos nas duas direções, que é INV-INS-135 fechado, e os
21 estão todos fora dele.

| onde | quantos | o que são |
|---|---|---|
| `jca` (congelado) | 18 | 16 eventos declarados que o autômato nunca nomeia; 1 transição que nomeia um evento inexistente; 1 evento declarado duas vezes |
| `jca_android_bug_predicate` (arquivado) | 2 | os dois do `GCMParameterSpecSpec` que o conjunto congelado também tem |
| `generic` | 1 | `FSM246.mop event_2` |
| `jca_android` | **0** | — |

Informativo e não falha porque congelado e arquivado não se reparam: o relatório os conta para
que a ausência deles em `jca_android` seja uma medida, e não um silêncio.

### G-PARAM — sobre `.rvm` regenerados, não sobre a fixação parada

```
24 passed · 0 failed · 0 skipped · 0 findings
```

Este é o número que a tarefa não tinha. Uma passagem completa de `generate` **não deixa `.rvm`
nenhum** — o passo do `rv-monitor` os apaga como intermediários
(`runtime_verification_generator.py:275`) —, e a suíte compara por isso contra
`results/gh51_e2e_test/monitors`, uma fixação gerada **antes** desta change, onde
`IvChainJunction` não tem `.rvm`. A suíte declara o pulo em vez de o tolerar
(`test_gparam_is_green_over_the_set_as_it_stands`: 23 comparados, 1 pulado, nomeado).

Para fechar o portão sobre o conjunto inteiro, os 24 `.rvm` foram preservados **entre** o passo
javamop e o passo rv-monitor, chamando os dois passos privados na ordem em que o método público
os chama, e G-PARAM correu sobre eles: **24 comparados, 0 pulados**. O pulo da suíte é artefato
da fixação parada, não da especificação — e o arquivo que ela pulava passa.

O diretório de especificações ficou **limpo** depois da passagem (`git status` vazio, zero
`.rvm` deixados para trás): o javamop escreve os `.rvm` no diretório-fonte antes de os mover, e
isso foi conferido e não presumido.

### Regras de junção e genericidade

Executáveis por teste nomeado, todos verdes:
`test_inv_ins_136_junction_rules` (com os três negativos do piloto: `CreationConsumerJunction`,
`PartialLoopJunction`, `HandlerParameterJunction`), `test_the_conforming_junction_trips_nothing`,
`test_the_junction_rules_do_not_govern_typestate_specifications`.

A genericidade é `test_inv_ins_140_genericity`, e o que ele fixa é exatamente a disciplina deste
relatório: os arquivos são **contados dos diretórios** e não escritos à mão (uma contagem
literal falharia no dia em que a primeira junção entrasse), todo arquivo é lido ou pulado com
razão, e um portão que não governa um conjunto **diz isso com uma razão** em vez de não correr
ali em silêncio. O irmão dele, `test_the_predicate_free_sets_read_as_predicate_free`, fixa os
145 arquivos de `generic` + `generic_new` como livres de substrato — os mesmos 145 que a
enumeração acima conta com 0 sítios.

## 3. Os portões da gh104, ainda verdes

`gh104_gates.py` sobre o monitor do conjunto migrado:

```
G-2 0 · G-2a 11 · G-2b' 18 · G-2c 2 · G-2d 3 · G-6' 0 · G-ERE 0 · G-CONF 0 · G-PRED 23
```

**Idênticos desde o lote B4.** A saída do processo é 1 e esse é o estado normal: os nove
contadores não são zero por construção, então `ok:false` — o que se compara são os contadores.
`skipped: []`.

`gh104_mop_lint.py`, `gh104_message_gate.py` e `gh104_divergence_record.py --check`: **exit 0**
nos três.

## 4. `test_jca_android_hunks_all_recorded`

Verde, dentro de `tests/parity/test_gh104_specset_gates.py` (2 testes, ambos passam). É o
teste que apanharia um hunk do conjunto migrado sem linha no `divergence_record.csv` — 287
linhas hoje, 282 hunks e 5 narrativas, zero `stale`.

## 5. As quatro suítes

```
gh101_specset_gates      6 passed
gh104_specset_gates      2 passed
gh104_structural_gates  16 passed  (78 s)
gh105_predicate_gates   67 passed
                        ---------
                        91 passed, 0 failed, 0 skipped
```

---

## 6. O que este relatório mede que a suíte não media

Três coisas:

1. **Os pulos passam a ser contados com razão**, e a contagem mostra que os 193 pulos de G-ORDER
   e os 16 de portão não escondem cobertura: são conjuntos congelados, arquivados ou sem
   substrato, mais duas especificações do conjunto migrado que o mapeamento de alfabeto
   deliberadamente não cobre.
2. **G-PARAM fecha sobre 24 e não sobre 23.** A suíte compara contra uma fixação anterior à
   change e declara o pulo; a regeneração compara tudo.
3. **Os 21 órfãos do G-ACC estão todos fora do conjunto migrado.** É a forma medida de dizer que
   os 17 do Grupo 3 saíram e nenhum entrou.

# Tarefa 8.2 — a prova de congelamento do conjunto `jca`

**Data**: 2026-08-23 · **Commit da árvore**: `519f2ff8` · **Commit-base do congelamento**: `7e7acb69`

A tarefa pede quatro coisas: que `jca/` e `ExecutionContext.java` estejam byte a byte iguais ao
que eram quando a change abriu, que `FROZEN_PATHS` cubra o arquivo, que
`test_property_append_only` esteja verde, e que a suíte corra com `RVSEC_HOME` setado — porque o
portão de congelamento dá `pytest.skip` sem ele, e um portão pulado não prova nada.

---

## 1. A identidade byte a byte

`git diff 7e7acb69 -- <caminho>` é a medida certa e não `git status`: o `status` só enxerga o
que a árvore de trabalho tem de diferente do `HEAD`, e o congelamento é contra o commit que
abriu a change, oitenta e tantos commits atrás. Os dois foram medidos.

| caminho | `git diff` contra `7e7acb69` | árvore de trabalho contra `HEAD` |
|---|---|---|
| `rvsec/rvsec-mop/src/main/resources/jca/` (24 entradas) | **vazio** | **vazio** |
| `rvsec/rvsec-core/.../jca/util/CipherTransformationUtil.java` | **vazio** | **vazio** |
| `rvsec/rvsec-core/.../ExecutionContext.java` | **vazio** | **vazio** |

Um diff vazio cobre por construção as duas exigências que o enunciado destaca — nenhuma anotação
e nenhum espaço em branco — porque não há hunk nenhum que as pudesse conter.

`7e7acb69` foi conferido como ancestral de `HEAD` (`git merge-base --is-ancestor`), sem o que a
comparação compararia dois ramos e não um antes com um depois.

## 2. `FROZEN_PATHS` cobre o arquivo

`tests/parity/test_gh101_specset_gates.py:62-66` lista três caminhos, e
`ExecutionContext.java` é o terceiro. O comentário que o acompanha registra por que ele entrou:
uma tentativa anterior re-chaveou a classe por identidade para reparar o conjunto derivado, e o
reparo mudou em silêncio o que o conjunto **congelado** acusa, porque um portão que lê `.mop`
não vê as classes Java que eles chamam. O conjunto derivado tem hoje o seu próprio armazém, e
uma classe de um conjunto só se congela com esse conjunto.

## 3. A suíte, com `RVSEC_HOME` setado

```
tests/parity/test_gh101_specset_gates.py::test_frozen_paths_byte_identical_to_base_commit PASSED
tests/parity/test_gh101_specset_gates.py::test_frozen_set_predicate_inventory_matches_baseline PASSED
tests/parity/test_gh101_specset_gates.py::test_every_divergence_between_the_sets_is_recorded  PASSED
tests/parity/test_gh101_specset_gates.py::test_every_written_constant_is_read_or_recorded     PASSED
tests/parity/test_gh101_specset_gates.py::test_conformance_record_covers_all_twenty_three     PASSED
tests/parity/test_gh101_specset_gates.py::test_property_append_only                           PASSED
6 passed in 0.34s
```

**Seis passaram, zero pulados** (`-rs` não imprimiu razão de skip nenhuma). É esta linha que
transforma a suíte em prova: com `RVSEC_HOME` ausente, `_rvsec_home()` pula os seis, e a saída
continua sendo `exit 0`.

---

## 4. O que a prova não cobria, e por que continua a valer

Os 23 `.mop` congelados escrevem `import br.unb.cic.mop.eh.*;`. Esse pacote **não** está em
`FROZEN_PATHS`, não tem teste append-only, e **mudou** desde `7e7acb69`: 147 linhas em três
arquivos. É exatamente a forma de falha que motivou a entrada de `ExecutionContext.java` na
tupla — um portão que lê `.mop` não enxerga o Java que eles chamam —, então a mudança foi lida
inteira em vez de presumida inócua.

| arquivo | o que mudou | alcance sobre o conjunto congelado |
|---|---|---|
| `eh/ErrorType.java` | a constante `ForbiddenMethod` **acrescentada ao fim** do enum | nenhum `.mop` do `jca` a nomeia; o acréscimo no fim preserva o `ordinal()` de todas as anteriores |
| `eh/ErrorSummary.java` | campos `code` e `event`, que entram no `equals`/`hashCode` | ver abaixo |
| `eh/ErrorDescription.java` | lê `code`/`event` do envelope `v=1 ` da mensagem | ver abaixo |

**A medida que decide**: `ErrorDescription.envelopeValue()` devolve `UNSPECIFIED` quando a
mensagem não contém o marcador `v=1 `. Contados os arquivos que escrevem esse marcador:

- `jca/*.mop` — **0 de 23**
- `jca_android/*.mop` — **22 de 24**

Logo, para todo relatório do conjunto congelado os dois campos novos valem a mesma constante.
Dois campos de valor constante acrescentados a um `equals` não podem partir nem fundir nenhum
balde: a relação de equivalência entre sumários do `jca` é a de antes, e a contagem de má
utilização única que dela se deriva também. E `ErrorSummary.toString()` continua emitindo os
**mesmos seis campos** — a própria docstring do método registra a decisão de não os emitir uma
segunda vez —, de modo que a linha que o `ErrorCollector` escreve no logcat tem o formato
posicional de sempre.

**Decisão do pesquisador (2026-08-23)**: registrar a medição e **não** criar portão novo. A 8.2
pede congelamento byte a byte de `jca/` e de `ExecutionContext.java`, e isso está provado; o
pacote `eh` é compartilhado de propósito, como `Property`, e criar um portão para ele é escopo
novo. Estender `FROZEN_PATHS` para cobri-lo foi medido e recusado na mesma rodada: o teste
falharia hoje mesmo, sobre 147 linhas que são da gh104 e não desta change — congelar
retroativamente troca uma medição por uma suíte vermelha sem defeito nenhum por trás.

## 5. O que fica escrito para quem vier depois

O `Property` tem um teste append-only e o `eh` não, e a diferença não é de princípio: é que
`Property` foi lido por um lote e o `eh` não tinha sido. A neutralidade provada acima é sobre a
árvore de **hoje** e vale enquanto nenhum `.mop` do `jca` passar a escrever `v=1 ` — o que
mudaria os dois campos de constantes para variáveis e tornaria o `equals` estendido observável
no conjunto congelado. Nada nesta change o faz, e nada o impede.

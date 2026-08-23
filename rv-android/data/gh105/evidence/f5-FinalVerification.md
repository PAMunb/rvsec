# Tarefas 8.6 e 8.7 — a sequência final do esquema rv-sdd

**Data**: 2026-08-23 · **Base**: `519f2ff8` (fim da 7.5) → `c21b5808`
A sequência que o esquema fixa: **lint-fix → verify → suíte de paridade → code-reviewer.**

---

## 1. O escopo, recontado antes de ser executado

A tarefa diz *"tudo que a change tocou desde a 7.5"*. Recontado:

```
git diff --name-only 519f2ff8..HEAD  →  16 .md, 4 .logcat, 1 .json
```

**Zero arquivos de código.** Os três commits do Grupo 8 até aqui são evidência, logcats e o
`tasks.md`. Se o escopo fosse lido ao pé da letra, a 8.6 não teria o que limpar.

Lido pelo espírito — *a change acaba com o seu código limpo* —, há o que limpar, e num lugar que
a 7.5 tinha deliberadamente deixado de fora. A 7.5 cobriu **todo `scripts/gh10*.py` menos três**
(`gh105_predicate_graph.py`, `gh105_order_gate.py`, `gh105_param_gate.py`), porque a tarefa 2.12
já os cobriria. Medido hoje, não cobria:

| ferramenta | sobre os 14 da 7.5 | sobre os 3 excluídos |
|---|---|---|
| `black --check` | limpo | **3 de 3 reformatariam** |
| `isort --check-only` | limpo | **1 arquivo fora de ordem** |
| `flake8` fora de `E501` | **0** | **2** |
| `autoflake` | nenhuma mudança | nenhuma mudança |

Os três foram editados depois da 2.12 — o `gh105_order_gate.py` no `012f9dbe`, dois commits
antes da 7.5 —, e é aí que a limpeza se desfez.

**E não eram só eles.** O `/rv-verify` apanhou o que este recontar tinha deixado passar: os
**quatro arquivos de teste** que a change escreveu ou reescreveu (`test_gh101_specset_gates.py`,
`test_gh104_specset_gates.py`, `test_gh104_structural_gates.py`,
`test_gh105_predicate_gates.py`) também estavam fora do `black`, e o
`test_gh105_predicate_gates.py` carregava um **`import json` morto** — a única falha real de
lint no escopo inteiro. Um teste é código da change tanto quanto um portão.

## 2. O que a 8.6 mudou

`autoflake` → `isort` → `black`, na ordem que a skill fixa, sobre os três arquivos:

```
3 arquivos, 54 hunks, +242 / -73 linhas    (3.167 → 3.336 linhas)
```

Mais dois resíduos que as três ferramentas não alcançam, tirados à mão:

1. **`gh105_order_gate.py`, `parse_cat()`** declarava `nonlocal position` e **nunca atribui** a
   variável — só a lê, indiretamente, através de `parse_postfix()` e `peek()`, que têm as suas
   próprias declarações. É o mesmo defeito que o lote B10 achou em `gh104_gates.py:481`, e a
   terceira vez nesta change que um `nonlocal` de leitura aparece: vale como padrão, não como
   caso.
2. **`gh105_predicate_graph.py`** terminava com linha em branco (`W391`), que o `black` fechou.

E os quatro arquivos de teste, na mesma ordem de ferramentas:

```
4 arquivos, +226 / -73 linhas    (o `import json` morto sai com o autoflake)
```

Resíduo fora de `E501` ao fim: **0**, nos 17 scripts e nos 4 testes. As passagens de
`black --check` e `isort --check-only` sobre `scripts/gh10*.py` e sobre os quatro testes saem
limpas.

## 3. A prova de que a reformatação não mudou nada

Item 26 da receita: a suíte verde não prova que um formatador não mexeu em nada. As cinco saídas
dos três portões foram capturadas **antes** e **depois** e comparadas:

| saída | resultado |
|---|---|
| `gh105_predicate_graph --sets all --json` (215 arquivos) | **idêntica** |
| `gh105_order_gate --sets all --json` (215 arquivos) | **idêntica** |
| `gh105_param_gate --sets jca_android --monitors <24 .rvm>` | **idêntica** |
| `gh105_predicate_graph --sets jca_android` (texto) | **idêntica** |
| `gh105_order_gate --sets jca_android` (texto) | **idêntica** |

`diff -r` sobre os dois diretórios: sem diferença.

E as quatro suítes, depois da reformatação dos próprios arquivos de teste:
**`6 + 2 + 16 + 67 = 91 passed`**, em 85 s. Os mesmos 91 de antes.

## 4. Uma medida que fica registrada e não foi executada

Os três arquivos têm **18 itens sem docstring**, contra **0** nos catorze da 7.5. Os dezoito são
fechos de uma linha dentro de funções já documentadas — `peek`, `key`, `total`, `universe`,
`read`, `skipped` — e as cinco funções do descendente recursivo (`parse_seq`, `parse_alt`,
`parse_cat`, `parse_postfix`, `parse_atom`), cuja função-mãe já documenta a gramática inteira e
o `ParseError` que levantam.

**Não foram escritas**, e a razão é P1: uma docstring sobre `def key(row): return ...` é cerimônia
que o próximo leitor pula. A medição fica aqui para que a diferença entre 0 e 18 seja uma escolha
registrada e não um esquecimento.

## 5. A suíte de paridade

```
uv run pytest tests/parity --import-mode=importlib -o "addopts="
→ 3 failed, 149 passed em 238 s
```

**Os três que falham são anteriores a esta change e estão fora do seu escopo.** Nenhum dos cinco
arquivos de teste envolvidos menciona `gh105`, e os três caminhos que causam as falhas estão
limpos na árvore ou pertencem a outro lote:

| teste | causa medida | de quem é |
|---|---|---|
| `test_baseline_freshness::test_baseline_not_older_than_jar` | os jars do gator são de **2026-08-23 01:58** e a baseline `cryptoapp.apk.json` é de **2026-05-29**: o jar foi reconstruído sem regenerar a baseline | build do reator anterior a esta sessão; a própria mensagem manda regenerar por gh60 11.8 |
| `test_no_legacy_mop::test_repo_is_clean` | seis ocorrências do token `reachesMop` em `modules/aperv-tool/` | o `aperv-tool` está modificado na árvore por outro lote |
| `test_sentinel_emission::test_real_gator_json_parses_with_complete_true` | `StaticAnalysisParser.parse_file()` recebe 1 argumento e o teste passa 2 | `bd10fb0f fix(analysis): o artefato define o próprio escopo, e o parser para de refiltrá-lo` tirou o parâmetro `package` e o teste da gh60 não acompanhou |

**Uma armadilha de ambiente, medida**: sem `ANDROID_SDK_HOME` exportado, sete testes **erram**
(não falham) com `KeyError: 'ANDROID_SDK_HOME'` levantado de dentro do `lib/gator/gator`, e um
oitavo falha por arrasto. Com a variável, os oito passam. É a mesma classe de armadilha do
`RVSEC_HOME` que a 8.2 registra: um portão que não corre não é um portão verde.

**Nenhuma das três falhas foi reparada aqui**, e isso é decisão de escopo: a terceira é um reparo
de uma linha noutra change, e corrigi-la dentro do commit de verificação final da gh105 misturaria
duas coisas que o próximo leitor precisa separar. As três estão relatadas ao pesquisador.

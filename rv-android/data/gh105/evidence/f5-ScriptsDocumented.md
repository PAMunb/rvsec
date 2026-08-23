# F5 — os catorze portões passam a dizer por que decidem o que decidem

Lote B10, tarefa **7.5**. Nenhuma especificação foi editada e nenhum artefato de dados mudou:
os cinco documentos que os instrumentos deste conjunto escrevem reproduzem **byte a byte**
depois da passagem.

---

## 1. O escopo, e por que o enunciado não o produzia

A tarefa diz *"enumere-os pelo `git status` neste ponto, para que 'qualquer script' seja
decidível"*. Nesta árvore o `git status` não decide nada: ela carrega ~180 arquivos não
rastreados de outra campanha e uma dúzia de modificações alheias. O critério que decide é de
caminho — **todo `scripts/gh10*.py` menos os três que a 2.12 já cobriu**
(`gh105_predicate_graph.py`, `gh105_order_gate.py`, `gh105_param_gate.py`).

Recontado no `HEAD` de hoje, antes de executar: **14 scripts, 7.096 linhas, 92 funções e 6
classes sem docstring = 98 itens.** Bate com o orçado no handoff, e os dois maiores respondem
por 59 dos 98.

---

## 2. O que o `/rv-qa-lint-fix` mudou

As três ferramentas da skill, na ordem que ela fixa:

| ferramenta | efeito medido |
|---|---|
| `autoflake --remove-all-unused-imports` | **nenhuma mudança** |
| `isort` | **2 arquivos** — reordenação dentro do bloco de imports, mesma contagem de linhas |
| `black` | **13 de 14 arquivos, 96 hunks** |

Uma segunda passagem do `black` foi precisa depois das docstrings, por três arquivos: uma
docstring de classe `@dataclass` pede uma linha em branco antes do primeiro campo, e o
inseridor não a escrevia.

**A armadilha que o handoff apontava não se materializou.** O aviso era que reformatar um
portão move a linha de onde um código é emitido e o portão `code-anchor` acusa. As âncoras do
`codes.csv` apontam para `.mop` (`CipherInputStreamSpec.mop:25`), não para os scripts, e o
`black` só toca `.py`. O `message-gate` saiu 0 nas quatro passagens de verificação; nenhuma
linha do `codes.csv` foi reancorada.

### Dois resíduos que as três ferramentas não alcançam

O `flake8` caiu de **505** para **353** avisos. Todos os 353 são `E501` em strings e
comentários, que o `black` deliberadamente não quebra. Fora de `E501` sobravam três, os
**mesmos três do `HEAD`** — conferidos rodando o `flake8` sobre as versões extraídas do
`HEAD`, não presumidos:

1. **`gh104_message_gate.py:80-81`** importava `_call_signature` e `_crysl_params` do
   `gh104_gates` e não usava nenhum dos dois. O `autoflake` não os remove porque o bloco
   carrega `# noqa: E402`. Nenhum outro arquivo da árvore os alcança por este módulo
   (`grep` sobre todos os `.py`, `backup/` fora), então saíram.
2. **`gh104_gates.py:481`** declarava `nonlocal buffer, buffer_line` num `flush()` que só
   atribui `buffer`. Ler a variável da closure não precisa de `nonlocal`; a declaração a mais
   saiu.

Resíduo fora de `E501` depois disso: **0**.

---

## 3. As 98 docstrings

Escritas item a item, com o código de cada uma lido antes. A regra de conteúdo é a P2: a
docstring diz **por que a função decide assim**, e não o que a assinatura já diz. As que
custaram mais são as que registram uma assimetria deliberada — por que `_compare` devolve
quatro veredictos e não um booleano, por que `check` do pairing verifica a obsolescência do
inventário antes de tudo, por que o `code-bijection` é pulado no `jca` em vez de reportar
cinquenta ausências, por que `measure_harness` decide o E6 sobre o número conservador.

A inserção passou por um script próprio, `docins.py`, e não pelo `edit.py`. A razão é a
pós-condição: ele localiza o alvo por posição estrutural no AST, insere, **reparseia o arquivo
e compara o AST com todas as docstrings removidas contra o de antes**. Uma inserção que
mexesse em qualquer outra coisa falha alto. Uma substituição de texto não teria como afirmar
isso, e `def main() -> int:` aparece em catorze arquivos.

Cinco linhas de docstring minhas passaram de 88 colunas e foram encurtadas. As sete linhas
longas que restam no diff são strings pré-existentes que o `black` reindentou.

**Itens sem docstring ao fim: 0.** As 14 linhas subiram de 7.096 para 8.560.

---

## 4. Como se verificou que nada mudou de comportamento

Reformatar 96 hunks em catorze portões é a espécie de passagem que passa nos testes e muda um
número. A verificação não foi a suíte:

| oráculo | resultado |
|---|---|
| `gh104_baseline.py --out <scratch>` × `data/gh104/` | **`baseline.json`, `baseline.md`, `definitions.md` idênticos** |
| `gh104_identity_discontinuity.py --out <scratch>` × `data/gh104/` | **`identity_discontinuity.json` e `.md` idênticos** |
| `gh101_predicate_inventory.py` × `data/gh101/predicate_inventory_jca_android.csv` | **idêntico** |
| `gh101_conformance_check.py` × `data/gh101/conformance_record.csv` | **idêntico** |
| harness (131 traces) × a passagem de antes da edição | **relatórios idênticos**, 61/31/32/7 |
| os nove contadores do `gh104_gates.py` | **`G-2 0 · G-2a 11 · G-2b' 18 · G-2c 2 · G-2d 3 · G-6' 0 · G-ERE 0 · G-CONF 0 · G-PRED 23`** — idênticos desde o B4 |
| `verify_all` (portões + quatro suítes) | todos exit 0, **6 + 2 + 16 + 67 = 91** |
| `--help` dos catorze | exit 0 nos catorze (vários derivam a descrição de `__doc__.splitlines()[0]`) |
| `gh104_regen_diff` — funções puras e o caminho `EXIT_CANNOT_RUN` | `by_category`, `strip_lines`/`raw_lines`, controle ausente → exit 2 |

**Um artefato não reproduz, e a diferença é anterior a este lote.** O
`data/gh101/predicate_edges.csv` difere em 44 linhas da regeneração de hoje — arestas que os
Grupos 3 a 5 desta change fecharam e que o CSV, sendo registro histórico do gh101, ainda
declara `missing`. Provado rodando **a versão do `HEAD` do próprio script**, extraída por
`git show`: a saída dela e a saída de agora são byte a byte iguais. A deriva é do dado, não
da passagem.

---

## 5. O que o lote aprendeu

**O `gh104_regen_diff.py` não foi exercitado de ponta a ponta.** Ele regenera um conjunto
contra um controle sob `results/`, que é gitignorado, e a §8.2 do handoff registra que apontar
o `generate` para lá destrói o oráculo do G-PARAM sem recuperação. Foi exercitado pelo
`--help`, pelas três funções puras que ganharam docstring e pelo caminho de controle ausente;
a passagem cara não foi feita e **isto fica escrito em vez de subentendido**.

**Um `# noqa` num bloco de import cega o `autoflake`.** Dois imports mortos sobreviveram a
todas as passagens anteriores do lint-fix por causa de um `# noqa: E402` que existe por outra
razão inteiramente — o `sys.path.insert` que tem de vir antes. A ferramenta não erra: ela
respeita o pedido de silêncio que a linha faz, e o pedido era sobre outra coisa.

**A prova de que um formatador não mudou nada não está na suíte.** As quatro suítes estavam
verdes antes e depois, e teriam ficado verdes se o `parse_crysl` tivesse passado a devolver
outra coisa: nenhuma delas compara artefato regenerado contra artefato commitado. O que prova
é reproduzir os cinco documentos byte a byte e reconferir os nove contadores.

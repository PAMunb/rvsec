# F5 — o pipeline real mede o próprio heap, e nove expectativas anônimas passam a ter dono

Lote B9, tarefas **7.4** e **7.6**. Nenhuma especificação foi editada: a pegada do harness contra
a regeneração do `HEAD` é **zero arquivo**, sobre os 24 relatórios e as 131 traces.

---

## 1. A 7.4: gerar pelo pipeline real, e o que a geração revelou

O comando é `uv run rv-monitor-generator generate --specs-dir $SPECS/jca_android --output <dir>`.
Duas passagens completas:

| medição | passagem 1 | passagem 2 |
|---|---|---|
| tempo de parede | 79 s | 77 s |
| pico de RSS na árvore de processos | 5,4 GB | 4,5 GB |
| `MultiSpec_1RuntimeMonitor.java` | 17.087 linhas | 17.087 linhas |

Os dois monitores são **byte a byte iguais**: a geração é determinística.

### A alavanca de heap documentada quebra o pipeline

O handoff dizia que, como nenhum launcher passa `-Xmx`, a alavanca é `_JAVA_OPTIONS`. Medido, ela
**aborta a geração**. A JVM escreve `Picked up _JAVA_OPTIONS: -Xmx4g` em **stderr**, e
`rv_android_core.util.utils.execute_command` levanta `CommandException` sempre que o stderr não é
vazio — **mesmo com `code=0`**:

```
CommandException[tool=javamop ::: code=0 ::: message=Picked up _JAVA_OPTIONS: -Xmx4g]
```

O alcance da variável está correto e foi conferido por leitura: `command.py:180` chama `Popen` sem
`env=`, e o filho que o `LogicRepositoryConnector.java:149-154` dispara vai com `envp=null`, então
a variável chega às duas JVMs. O que não funciona é o que a plataforma faz com o banner.

É o **INV-INS-145 virado ao contrário**. O invariante existe porque o exit code fica verde quando o
filho estoura a memória (`Logic Engine Error: null`, exit 0, sem monitor); aqui ele fica vermelho
quando nada falhou. As duas metades dizem a mesma coisa: **inspecione o artefato**.

**Decisão do pesquisador (2026-08-23): registrar, não reparar.** Alargar o `execute_command` é
mudança comportamental no `rv-android-core`, que é caminho de produção de todo experimento, e a
saída óbvia — `skip_stderr=True` — cegaria o gerador justamente para o erro que o INV-INS-145
protege. Trocaria "falha por banner benigno" por "silêncio sobre erro real".

### A geração falhada suja o conjunto de specs

Efeito colateral medido, e que ninguém tinha registrado: o `_execute_javamop` escreve os `.rvm`
**dentro do `$SPECS/<conjunto>/`** e só depois os move para a saída
(`runtime_verification_generator.py:221-223`). Quando o passo falha, os 24 `.rvm` ficam lá. Eles
são gitignorados, então nem `git status` nem nenhum portão os acusa — mas o `fingerprint` do cache
do harness soma **todos** os arquivos do diretório, de modo que uma passagem falhada troca a chave
de cache do conjunto inteiro em silêncio. Uma passagem bem-sucedida os move para fora e a chave
volta ao lugar.

### Os literais que o pipeline confirmou

| | antes | medido hoje |
|---|---|---|
| `.mop` no `jca_android` | 23 | **24** (o Grupo 5 acrescentou o `IvChainJunction`) |
| universo enumerado | 214 | **215** (`generic` 118 · `generic_new` 27 · `jca` 23 · `jca_android` 24 · `jca_android_bug_predicate` 23) |
| `new ErrorDescription(` no conjunto | 50 | **112**, todos de quatro argumentos, zero comentado |
| linhas no `codes.csv` | 50 | **112** |
| `ExecutionContext` no conjunto | 134 linhas | **0** |
| `setProperty(` / `.remove(` | 49 / 9 | **0** / **0** |
| `validate(` | — | **38** |

O `validate(` merece nota: o handoff dizia **39**, e o número vivo é **38**. Não é erro do handoff —
é deriva. O próprio `f010cb92` comentou uma linha no `KeyPairGeneratorSpec`, e `git grep -oh` por
commit mostra 39 em `82508306`, 39 em `9cb15b44`, 38 no `HEAD`.

O "21" que aparece quatro vezes no README **não é obsoleto**, contra o que o handoff supunha: são
as **21 especificações pareadas com uma regra api30** — os `mop_file` únicos do
`conformance_record.csv` — e não o tamanho do conjunto. A frase de `:108` foi reformulada para
dizer isso; os números ficaram.

### O teto do INV-INS-145 continua respeitado, com folga zero

O `CipherSpec` declara exatamente **17** eventos. O segundo maior é o `SecureRandomSpec`, com 13,
e o `IvChainJunction` entrou com 7. Nenhum arquivo do conjunto encosta em 18, que é onde o parser
de enable-set do processo pai estoura a pilha com qualquer heap.

### Inspeção do artefato, e um achado sobre o cache do harness

O monitor do pipeline real **difere** do que o harness estava a usar: as tabelas de transição estão
renumeradas. Não é diferença de linguagem — é um isomorfismo. No `CipherInputStreamSpec`, os
estados 2 e 3 estão trocados e o `fail` continua no 4:

```
pipeline real:  c1={2,4,4,4,4}  r1={4,1,1,4,4}  cl1={4,3,4,4,4}
cache antigo:   c1={3,4,4,4,4}  r1={4,1,4,1,4}  cl1={4,2,4,4,4}
```

Rastreado em três medições:

| comparação | resultado |
|---|---|
| duas passagens do pipeline real | monitor **idêntico** |
| harness com cache frio × pipeline real | monitor **idêntico** |
| harness com cache frio × cache antigo | monitor **difere** (a renumeração acima) |
| relatórios do harness frio × relatórios do harness com cache | **0 arquivos diferem**, 61/31/32/7 nos dois |

Ou seja: o cache de monitores (`~/tmp-gh104/monitor-cache`) guarda artefato de uma toolchain
anterior, porque o `fingerprint` cobre o conjunto de specs e **não a toolchain**. Ele está velho e
é **comprovadamente inócuo** — a renumeração não muda nenhum relatório, e os nove contadores do
`gh104_gates.py` são idênticos contra os dois monitores.

**Isso fecha metade do achado 115.** A deriva de dez relatórios entre a evidência commitada e a
regeneração do `HEAD` **não vem do monitor**: uma passagem de cache frio, com monitores recém
gerados nas duas pernas e byte a byte iguais aos do pipeline real, reproduz exatamente a passagem
com cache. A causa continua a jusante do monitor, nas classes compiladas do `TraceRunner`.

---

## 2. A 7.6: a baseline sai, e as nove divergências ganham dono

A tarefa dizia "todo portão passa a afirmar zero achados por si" e apagava a `gate_baseline.json`.
Medido antes de executar, o arquivo tinha **um** portão — G-ORDER, com nove linhas — e cinco
entradas `retired`. Os outros oito já comparavam contra o conjunto vazio, e os docstrings dos
próprios wrappers diziam isso por escrito: *"`_no_regression` therefore compares against the empty
set and the subset assertion **is** the zero assertion"*. **O mecanismo já estava morto para oito
dos nove.**

Apagar sem mais transformaria nove registros em nove reprovações. **Decisão do pesquisador
(2026-08-23): mover as nove para o `gate_allowlist.csv` e ensinar o portão a lê-lo.**

O argumento é sobre **procedência**, que é o que a tarefa acusa quando diz "uma allow-list em que
ninguém votou". As nove linhas da baseline eram três campos — `["jca_android", "CipherSpec.mop",
"order"]` — sem razão, sem tarefa, sem direção, eleitas por aquilo que um `--write` calhou de
medir. Cada linha do `gate_allowlist.csv` carrega a testemunha, a medição, a razão e a tarefa dona.
Mover as nove para lá é **levá-las a voto**, e o `gh105_gate_baseline.py:27-29` já sabia a
diferença: *"That file records findings that are deliberately permanent, each with the measurement
and the reason behind it."*

### Por que não reparar os autômatos

Duas das nove **não são reparáveis editando o `.mop`**. No `CipherInputStreamSpec` (`c1 r1 c`) e no
`SecretKeySpec` (`d`), o excesso está do lado da **regra**: a api30 ordena um símbolo que nenhum
programa monitorado produz — um construtor que o android-30 declara `protected`, e um `destroy()`
que o `.mop` deliberadamente não observa porque lança nas duas implementações que o conjunto vê
(INV-INS-137). O `order_alphabet_map.csv` só tem disposição do lado do `.mop`: `order-unmapped`
apaga evento da especificação, nunca símbolo da regra. Fechar essas duas exigiria mudar o formato
do mapa. **O reparo dos nove terminaria na allow-list de qualquer modo, depois de um grupo
inteiro.** E duas outras — `KeyGeneratorSpec` e `KeyStoreSpec` — são herdadas do `jca` congelado,
cujo congelamento a tarefa 8.2 tem de provar.

### O que o portão aprendeu

`gh105_order_gate.py` ganhou uma lista `allowed` ao lado de `findings`, um `--allowlist`, e um
leitor próprio de 20 linhas. Ele **não** reusa o `read_allowlist` do `gh105_predicate_graph.py`, e
a razão é a única regra que importa aqui: **uma linha com `reason` vazia não permite nada**. O
leitor partilhado ignora a coluna, e reusá-lo teria feito o portão aceitar exatamente a coisa que a
7.6 remove — uma exceção sem razão escrita. O `gh104_gates.py:1242-1244` já lia a sua allow-list
assim.

Duas larguras de chave, e não três: `(set, spec, "order")` e `(set, "*", "*")`. O `subject` de uma
linha de G-ORDER é a constante `order`, porque o achado é sobre a linguagem inteira da
especificação — uma permissão por evento seria uma chave que este portão nunca produz.

### O portão novo, auditado por mutação

Três mutações sobre uma cópia da allow-list, cada uma esperando exatamente um achado:

| mutação | resultado |
|---|---|
| `reason` esvaziada no `CipherSpec` | **1 failed, 8 allow-listed** |
| linha do `KeyStoreSpec` removida | **1 failed, 8 allow-listed** |
| `gate` trocado para `G-2a` no `SecretKeySpec` | **1 failed, 8 allow-listed** |

O portão discrimina nas três. Sem mutação: `13 passed, 0 failed, 9 allow-listed, 2 skipped of 24`,
**exit 0**.

### As nove, com testemunha e classe

| spec | testemunha | quem aceita | classe |
|---|---|---|---|
| `CipherInputStreamSpec` | `c1 r1 c` | a regra | alfabeto da regra — construtor `protected`, sem reparo no `.mop` |
| `SecretKeySpec` | `d` | a regra | alfabeto da regra — `destroy()` não observável (INV-INS-137) |
| `KeyGeneratorSpec` | `g1 g1 gk` | a spec | folga do `g1+`, **herdada do `jca` congelado** |
| `KeyStoreSpec` | `g2 l1` | a regra | **acusa programa conforme**, e é **herdada do congelado** |
| `CipherSpec` | `g1 i1 u1` | a spec | folga do `ere` — aceita Cipher não finalizado |
| `CipherOutputStreamSpec` | `c2 c` | a spec | folga do `ere` — `fl` no grupo obrigatório |
| `KeyPairSpec` | a sequência vazia | a regra | spec estrita demais — `co?` é opcional na regra |
| `SSLContextSpec` | `g1 Init se1 se1` | a spec | folga — o `end` admite um segundo `engine` |
| `SecureRandomSpec` | `c1 c1` | a spec | folga — auto-laço de `init` sobre o construtor |

Nenhuma foi reparada: cinco são mudanças comportamentais que a decisão 7 desta change mantém fora
sem medição própria, duas atravessam o congelamento, e duas não têm reparo do lado do `.mop`.

### O que foi apagado, e o que se preservou

`scripts/gh105_gate_baseline.py` (279 linhas), `data/jca_android/gate_baseline.json` (91) e
`data/jca_android/evidence/gate_baseline_report.md` (76) foram para
`backup/gh105-retired/gate-baseline/`, com um `RETIREMENT.md`.

**A condição que a execução impôs a si mesma**: os 3.549 caracteres das cinco notas `retired` —
G-ACC, INV-INS-130, INV-INS-133, INV-INS-134 e G-PRED2 — são **registro de decisão**, não medição,
e cada uma diz o que uma acusação futura daquele portão significaria. Elas morriam com o JSON. Estão
preservadas verbatim no `RETIREMENT.md`, senão a 7.6 teria trocado nove expectativas sem
procedência por cinco retiradas sem procedência, que é o mesmo defeito do avesso.

Na suíte: quatro testes de mecanismo morreram inteiros (14 asserções), os helpers `BASELINE`,
`_recorded`, `_no_regression_over` e `_no_regression` e a fixture `measured` saíram, e seis
wrappers passaram a `_no_findings`. Cinco dessas seis inversões são troca de nome — já comparavam
contra o vazio. A sexta, o `test_inv_ins_138_gorder`, é a única com conteúdo, e ela afirma as duas
metades: **zero achados** e **allow-list não vazia**, porque um run que reportasse zero dos dois
significaria que o portão parou de comparar, e não que o conjunto convergiu.

---

## 3. Um achado que a passagem não procurava: `tests/parity/` não roda no CI

`rvsec/.github/workflows/ci.yml:79-97` itera `for module in modules/*/` e roda
`uv run pytest "$module/tests"`. O `rv-android/tests/parity` fica de fora, e não há `testpaths` no
`pyproject.toml` nem script que o inclua. O "contrato de CI" que a D-13 invoca para justificar a
baseline — *"uma suíte que se espera vermelha deixa de ser lida"* — é, na prática, o `/rv-verify`
local e a tarefa 8.1.

Isso não invalida a D-13: o argumento sobre a suíte deixar de ser lida vale igual para quem roda a
verificação à mão. Mas muda o risco de qualquer mudança nesses portões, e **estava por escrever**.

---

## 4. Estado ao fim do lote

| medida | valor |
|---|---|
| G-ORDER | **13 passa · 0 acha · 9 na allow-list · 2 pulos**, exit 0 |
| achados dos gates estruturais | 0 |
| portões em `gates` da baseline | o mecanismo não existe |
| `gh104_gates.py` | `G-2 0 · G-2a 11 · G-2b' 18 · G-2c 2 · G-2d 3 · G-6' 0 · G-ERE 0 · G-CONF 0 · G-PRED 23` — **idênticos desde o B4** |
| linhas no `gate_allowlist.csv` | 14 → **23** |
| linhas no `predicate_graph.csv` | 70 (inalterado) |
| traces do corpus | 131 · **61 unchanged · 31 moved · 32 introduced · 7 removed** |
| pegada no harness contra o `HEAD` | **0 arquivos** |
| testes nas quatro suítes | 6 + 2 + 16 + **67** = **91** (eram 95; os quatro de mecanismo morreram) |

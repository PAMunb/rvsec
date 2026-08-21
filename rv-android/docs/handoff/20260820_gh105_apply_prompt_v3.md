# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 20/74)

**Data**: 2026-08-20 · **Branch**: `modules` · **Último commit**: `f464d604`
**Progresso**: 20 de 74 tarefas (Grupo 1 inteiro, Grupo 2 inteiro, tarefas 3.1 e 3.2)
**Estado da árvore**: verde — 91 asserções nas quatro suítes de gates passam.

---

## O que estamos fazendo

Aplicando a change **gh105-predicate-wiring** (GitHub issue #105) pelo workflow OpenSpec.
A change fia as predicates CrySL (`ENSURES`/`REQUIRES`/`NEGATES`) no conjunto `jca_android`,
que hoje não as fia: das 19 predicates conectáveis contra as 33 regras api30, o conjunto
realiza 3 elos; as leituras de predicate vivem dentro de `condition(...)`, onde uma guarda
falsa suprime a transição e converte "origem de chave não modelada" num
`InvalidSequenceOfMethodCalls` errado; e os acusadores órfãos sustentam no máximo 39.682
eventos = 56,1 % daquela categoria publicada (teto medido sobre a campanha `jca`, não
atribuição causal).

O gh104 fez o handler `@fail` falar (envelope, códigos, nomes de evento). Esta change faz ele
parar de disparar quando não deve, e faz um `REQUIRES` violado se acusar.

### REGRA NÃO NEGOCIÁVEL DE WORKFLOW

Seguir `docs/WORKFLOW.md` rigorosamente. **NUNCA** escrever ou reescrever artefatos OpenSpec
com `Write`/`Edit` — invocar as skills (`openspec-apply-change`, `openspec-update-change`)
pela ferramenta `Skill`. A única edição manual permitida em `tasks.md` é marcar `- [ ]` →
`- [x]` imediatamente ao concluir cada tarefa, antes de começar a próxima.

Commits **nunca** levam `Co-Authored-By` nem trailer de coautoria. Mensagens em português com
acentuação correta, no estilo narrativo dos commits recentes (explicam *por quê*). Sufixo
`refs #105`; `closes #105` só no commit final.

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente. O rv-platform
gerencia o ciclo de vida inteiro. Vale para as tarefas 4.3 e 8.5.

---

## Artefatos da change (leitura obrigatória)

Em `openspec/changes/gh105-predicate-wiring/`:

| Arquivo | O que contém |
|---|---|
| `proposal.md` | o porquê, o escopo, o que é BREAKING |
| `design.md` | D-1 a D-14, o **ledger de 36 cláusulas**, o **censo dos 17 órfãos (corrigido em 2026-08-20)** |
| `specs/instrumentation/spec.md` | INV-INS-130 a INV-INS-148, Data Contracts, cenários WHEN/THEN |
| `tasks.md` | as 74 tarefas, com o comentário HTML de despacho no topo |

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
openspec instructions apply --change gh105-predicate-wiring --json
openspec validate gh105-predicate-wiring          # note: `validate` NÃO aceita --change
```

---

## O que foi feito

### Grupo 1 — substrato (rvsec-core) — 6/6, commit `b55a61a2`

`PredicateVerdict`, `PredicateStore` (chave de identidade fraca com `ReferenceQueue`,
posições `String`/`int`/`Integer` sem distinguir caixa, aridade N, `ensure/validate(Property,
Object bound, Object... values)`, `negate`, `validateAbsent`, `reset`), 19 testes JUnit,
reset do substrato no `TraceRunner.replay()` (provado por um caso cross-trace),
`ExecutionContext.java` byte-idêntico em `FROZEN_PATHS`, `Property` append-only.

**Decisão ainda a confirmar com o pesquisador**: `bound == null` é tolerado (no-op /
`NOT_OBSERVED` / `SATISFIED`) em vez de lançar, porque uma NPE dentro de advice tecido
derruba a app sob teste. Documentado no javadoc.

### Grupo 2 — camada de gates — 12/12, commits `acec89ea`, `84c72976`, `70ef5ab8`, `3f3bdd1c`, `01a1373d`, `25cfc590`

- **2.1-2.5** `scripts/gh105_predicate_graph.py` (leitor + alfabeto + emissor + G-ACC +
  colocação + G-PRED2 + regras de junção) e `scripts/gh105_param_gate.py` (G-PARAM).
- **2.6** `gate_import` (INV-INS-130) sobre texto cru, como o `grep -rlw` da invariante.
- **2.7** reescopo do G-PRED para o cadeado do `jca` — veio junto da 3.1, não da 4.1.
- **2.8** `data/jca_android/order_alphabet_map.csv`; 13 especificações restantes sob a 7.1.
- **2.9** `scripts/gh105_order_gate.py` (G-ORDER).
- **2.10/2.11** `scripts/gh105_gate_baseline.py`, `data/jca_android/gate_baseline.json`,
  `data/jca_android/evidence/gate_baseline_report.md`, e a pré-imagem em
  `backup/gh105-preimage/jca_android/` (o lado `--a` da tarefa 8.4).
- **2.12** `/rv-doc-code` nos três scripts.

### Grupo 3 — órfãos — 2/7

**3.1 `SecureRandomSpec`** (commit `25cfc590`): `c3`→`c2` e `setSeed3`→`setSeed2` fundidos,
`g4` absorvido com laço benigno nos três estados. Nove hunks `automaton`. Três traces novas.

**3.2 `TrustManagerFactorySpec`** (commit `f464d604`): `g3` **fundido** em `g1`, não absorvido
— ver a correção de censo abaixo. `codes.csv` segue o sítio (`:92`, `:121`). Linha do `g3`
apagada do `order_alphabet_map.csv` (evento fundido deixa de existir; não ganha exemption).
Linha `34977248ae45` do registro de divergência retirada com o evento que ela justificava,
três hunks novos como `automaton`. Duas traces novas. G-ACC 14 → 13.

---

## A correção de censo de 2026-08-20 (ratificada pelo pesquisador)

O `design.md` classificava **três** órfãos como absorções puras que na verdade são gêmeos
negados. Descoberto ao ler os corpos durante a 3.2, ratificado pelo pesquisador, e aplicado
aos quatro artefatos pela skill `openspec-update-change`.

**O critério que separa os dois tratamentos é o corpo do órfão, não o formato da guarda:**

| órfão | corpo acusa? | tratamento |
|---|---|---|
| `SecureRandomSpec.g4` | sim — `SECURERANDOM-ALG-00` | **absorção** (feita na 3.1) |
| `KeyPairGeneratorSpec.initError` | sim — `KEYPAIRGENERATOR-KEYSIZE-00` | **absorção** (tarefa 3.6) |
| `PBEKeySpecSpec.f1`, `f2` | sim — `PBEKEYSPEC-FORB-00` | **absorção** (tarefa 3.5) |
| `TrustManagerFactorySpec.g3` | não — só religa campo | **fusão** →`g1` (feita na 3.2) |
| `SignatureSpec.g3` | não — só religa campo | **fusão** →`g1` (tarefa 3.6) |
| `SSLContextSpec.unsafe_protocol` | não — só religa campo | **fusão** →`g1` (tarefa 3.6) |

Partição corrigida, mesmos 17: **12 gêmeos (11 setas) + `err1` + 4 absorções**.

Três oráculos concordam: (1) a regra api30 ordena `Gets, Init, …` com `Gets := g1 | g2` e põe
o algoritmo em CONSTRAINTS, logo o algoritmo não pode governar a transição; (2) a INV-INS-135
define gêmeo negado como "mesma `call`/`args`, condição diferindo só na polaridade", o que
casa os três literalmente; (3) a medição abaixo.

**A medição que decidiu, e que é o achado mais forte da 3.2.** Em
`TrustManagerFactorySpec-sunx509.txt`, contra a pré-imagem:

- **antes**: `TRUSTMANAGERFACTORY-ORDER-00` **duas vezes** (no `g3` e no `init` que o segue) e
  **nenhuma** acusação de algoritmo. O `__RESET` do `g3` devolve o monitor a `start`, onde
  `init` não está declarado, e a transição que falha toma o caminho do `@fail` em vez do corpo
  do evento — que é onde mora a checagem de algoritmo.
- **depois**: um relato só, `TRUSTMANAGERFACTORY-ALG-00 val='SunX509' exp='PKIX'`.

Ou seja: **o órfão não estava acrescentando ruído a um achado, estava suprimindo o achado.**

---

## Números medidos (estado atual, reproduzidos da fonte)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **13** | 0 |
| leituras em `condition(...)` | 27 | 23 | 0 |
| leituras em corpo | 0 | 1 | todas |
| escritas em corpo de evento | 42 | 42 | 0 sem motivo |
| escritas no ponto de aceitação | 7 | 7 | 49 |
| chamadas de estado de aceitação | 25 | 25 | 0 |
| `remove()` em `@fail` | 8 | 8 | 0 |
| menções a `ExecutionContext` (INV-INS-130) | 23 arquivos | 23 | 0 |
| divergências de ordenação (G-ORDER) | 4 | 4 | 0 |
| achados estruturais falhando | 145 | **137** | 0 |
| hunks no registro de divergência | — | **140, todos registrados** | — |
| traces do corpus | 63 | **68** | — |

Harness sobre as 68 traces contra `backup/gh105-preimage/jca_android`: **64 inalteradas,
2 removidas, 2 movidas** (duas de cada são da 3.1, cumulativas contra a pré-imagem).

Universo enumerado: **214 `.mop`** (jca 23, jca_android 23, jca_android_bug_predicate 23,
generic 118, generic_new 27), 2 pulados com motivo. Nenhuma gate guarda esse número como
literal.

G-ORDER, as quatro divergências (inalteradas por 3.1 e 3.2, endereçadas por 7.1 e Grupo 6):
- `CipherSpec`: `f2` aceito pelo ORDER, rejeitado pela especificação.
- `SSLContextSpec`: `g1 Init se1 se1` aceito pela especificação, rejeitado pelo ORDER.
- `SecureRandomSpec`: `c1 c1` aceito pela especificação, rejeitado pelo ORDER.
- `TrustManagerFactorySpec`: `g1 i1 gtm` aceito pelo ORDER, rejeitado pela especificação
  (o `gtm1 -> start` do fsm; o estado de aceitação é `final`).

---

## Duas pendências levantadas e ainda não endereçadas

### 1. A guarda do `g2` tem o mesmo defeito e não pertence a nenhuma tarefa

Em `TrustManagerFactorySpec`, `SignatureSpec` e `SSLContextSpec`, o `g2` (sobrecarga de dois
argumentos) carrega a mesma `condition(ConscryptAliasTable.matches(...))` que o `g1` acabou de
perder. `getInstance("SunX509", provider)` não dispara evento nenhum: a guarda positiva suprime
a transição pela mesma razão, o monitor fica sem observar a fábrica, e o `init` seguinte cai em
`fail`. O `g2` **está** no autômato, então o G-ACC não o vê, e nenhuma tarefa dos Grupos 3-6 o
cobre. **Não é** o `guard-on-field` da tarefa 8.16 do gh104 — aquele é sobre a mensagem ler
campo do monitor, não sobre a guarda suprimir transição. Vale abrir tarefa; não foi feito para
não expandir escopo por conta própria.

### 2. Arquivos `selftest-*.md` modificados e não commitados na árvore

`data/gh104/evidence/harness/selftest-*.md` estão modificados desde antes desta sessão. A
versão da árvore contradiz a commitada — troca `UnsafeAlgorithm` por
`InvalidSequenceOfMethodCalls,msg=unknown` e faz `getTrustManagers()` deixar de resolver
pointcut. **Não confiar nessas versões como evidência**; ler `git show HEAD:<caminho>`. Foi
essa divergência que produziu uma leitura errada no início da 3.2. Não foram tocados.

---

## Próximos passos, na ordem

### 3.3 `IvParameterSpec` — fundir `c3`→`c1` e `c4`→`c2` (o `c4` não é complemento exato: ignora as restrições de offset/length do `c2`, então o corpo fundido guarda as duas verificações)
### 3.4 `SecretKeySpecSpec` — fundir `c3`→`c1` e `c4`→`c2`; **apagar** a linha `SecretKeySpecSpec.c3` do `gate_allowlist.csv` (ela já diz que sai aqui)
### 3.5 `PBEKeySpecSpec` — **absorver** `f1`, `f2`; fundir `err2` e `err3` em `c1` (uma seta, dois órfãos) e `err1` como o décimo terceiro fundido; decompor a verificação por cláusula, um relato cada. Declarar o resíduo de prefixo Kleene. Dona da linha `err2` do allowlist
### 3.6 `PBEParameterSpecSpec` (fundir `c3`→`c1`); `KeyPairGeneratorSpec` (**absorver** `initError`); `SSLContextSpec` (**fundir** `unsafe_protocol`→`g1`); `SignatureSpec` (**fundir** `g3`→`g1`) — os dois últimos com o mesmo resíduo registrado da 3.2
### 3.7 G-ACC verde sobre o `jca_android`, linhas da baseline retiradas, evidência de harness dos 17

**Receita por tarefa do Grupo 3** (a da 3.1 e 3.2, que funcionou):

1. Editar o `.mop` no reator irmão. **Fusão** = apagar o gêmeo e tirar a guarda do irmão,
   levando a acusação (se houver) para o corpo. **Absorção** = laço benigno em todo estado
   onde a chamada é legal + linha `order-unmapped` com motivo.
2. `codes.csv` segue o sítio (coluna `event` e `file_line`) — **os números de linha mudam
   quando você acrescenta comentário**; reconferir com `grep -n` no fim, não no meio.
3. Remover do `order_alphabet_map.csv` as linhas dos eventos fundidos; conferir que o evento
   absorvido tem linha `order-unmapped` com motivo.
4. Traces satisfaz/viola em `data/gh104/traces/`.
5. Regerar o grafo: `--emit` (pode não mudar nada se o órfão não carregava sítio de predicate).
6. `gh104_divergence_record.py --check` → registrar cada hunk novo com kind e motivo
   (`automaton` para edições de autômato). Linha obsoleta de hunk que sumiu tem que **sair**.
7. Rodar o harness diferencial contra `backup/gh105-preimage/jca_android` (background, ~10 min).
8. Atualizar os censos em `tests/parity/test_gh105_predicate_gates.py` com uma linha de
   docstring dizendo qual tarefa moveu o número.
9. Rodar as quatro suítes de gates. Commitar. Marcar o checkbox.

**Ordem importa**: edite o `.mop` **inteiro** (comentários incluídos) antes de sincronizar
`codes.csv` e antes de registrar hunks — o digest do hunk é do conteúdo, então mexer no
comentário depois re-chaveia a linha do registro e obriga a refazer os passos 2 e 6.

### Depois: Grupo 4 (um passe por arquivo)

**A change pode parar na 4.3.** A sonda de alcance (design D-12) faz a pergunta que anula a
change: se `UnsatisfiedConstraint` ficar em zero no caminho de produção, o weaver é
pré-requisito e os grupos de fiação **não podem** começar. Ela roda logo depois do primeiro
arquivo migrado do Grupo 4, via `rv-experiment`/`rv-platform` (a plataforma gerencia o
emulador), e o veredito é commitado de qualquer jeito.

---

## Arquivos relacionados

**Java (reator irmão, `.../workspace-rv/rvsec/rvsec/`)**
- `rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java`, `PredicateVerdict.java`, `Property.java`
- `rvsec-core/src/test/java/br/unb/cic/mop/PredicateStoreTest.java`
- `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/ConscryptAliasTable.java` (a tabela de alias; 158 linhas espelhadas em `data/jca_android/alias_table.csv`)
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java`, `TraceRunnerTest.java`
- `rvsec-mop/src/main/resources/jca_android/*.mop` + `codes.csv` ← o conjunto que a change edita

**Python (`.../rvsec/rv-android/`)**
- `scripts/gh105_predicate_graph.py` (leitor + grafo + G-ACC + colocação + G-PRED2 + junção)
- `scripts/gh105_order_gate.py` (G-ORDER), `scripts/gh105_param_gate.py` (G-PARAM)
- `scripts/gh105_gate_baseline.py` (mecanismo D-13 — **tem data de demolição: tarefa 7.6**)
- `scripts/gh104_gates.py`, `scripts/gh104_divergence_record.py`, `scripts/gh104_diff_harness.py`
- `tests/parity/test_gh105_predicate_gates.py`, `test_gh104_specset_gates.py`,
  `test_gh104_structural_gates.py`, `test_gh101_specset_gates.py`
- `data/jca_android/`: `predicate_graph.csv`, `order_alphabet_map.csv`, `gate_baseline.json`,
  `gate_allowlist.csv`, `divergence_record.csv`, `alias_table.csv`,
  `evidence/gate_baseline_report.md`
- `data/gh104/traces/` (68 traces), `data/gh105/evidence/harness/f1-*.md`
- `backup/gh105-preimage/jca_android/` (pré-imagem), `backup/gh105-retired/`

**Oráculo (somente leitura)**: `/home/pedro/.../workspace-rv/MetaCrySL/generated/api30/*.cryptsl`

---

## Comandos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
SPECS=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources

# as quatro suítes de gates (contrato de CI obrigatório) — hoje 91 passando, ~75 s
uv run pytest tests/parity/test_gh101_specset_gates.py tests/parity/test_gh104_specset_gates.py \
    tests/parity/test_gh104_structural_gates.py tests/parity/test_gh105_predicate_gates.py \
    --import-mode=importlib -o "addopts=" -q

# suíte estrutural gh105 pela CLI
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets all
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets jca_android --emit

# G-ORDER
uv run python scripts/gh105_order_gate.py --specs-root $SPECS --sets jca_android

# baseline (comparar; --write só quando a tarefa mandar)
uv run python scripts/gh105_gate_baseline.py --specs-root $SPECS

# registro de divergência
uv run python scripts/gh104_divergence_record.py --check
uv run python scripts/gh104_divergence_record.py --refresh   # imprime as linhas vivas

# harness diferencial (~10 min: gera os dois lados e replaya as traces) — rodar em background
# NÃO canalizar para `tail`: o resumo JSON com as contagens fica no TOPO da saída
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
uv run python scripts/gh104_diff_harness.py \
    --a backup/gh105-preimage/jca_android --b $SPECS/jca_android \
    --traces data/gh104/traces --out data/gh105/evidence/harness --group f1

# build do reator Java (JDK 21 no prefixo; recurso serializado)
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
mvn clean install -DskipMopAgent -DskipTests
mvn -o test -pl rvsec-core,rvsec-mop -DskipMopAgent
```

---

## Aprendizados que custaram tempo (não redescobrir)

1. **O critério gêmeo-vs-absorção é o corpo do órfão**, não a guarda. Ver a tabela acima. Foi
   isso que corrigiu o censo do `design.md` na 3.2.
2. **A tabela de alias do gh104 muda quais traces exercitam um órfão.** `X509` resolve para
   `PKIX` no `jca_android` (`alias_table.csv:2`), então a trace `-x509` do corpus **não**
   alcança o `g3`. Antes de escrever uma trace de violação, conferir se o valor escolhido tem
   linha na tabela de alias — se tiver, ele não viola nada.
3. **Um órfão pode suprimir o achado, não só somar ruído.** Quando o `__RESET` do órfão devolve
   o monitor a um estado onde o evento seguinte não está declarado, a transição que falha toma
   o `@fail` em vez do corpo do evento — e a checagem de CONSTRAINTS que mora no corpo nunca
   roda. Medido na 3.2. Procurar esse padrão nas outras fusões.
4. **A evidência de self-test do gh104 na árvore está modificada e não commitada** e contradiz
   a versão commitada. Ler sempre `git show HEAD:<caminho>`.
5. **O digest de hunk é do conteúdo.** Mexer no comentário do `.mop` depois de registrar os
   hunks re-chaveia a linha e força refazer `codes.csv` e o registro. Terminar o arquivo antes.
6. **`openspec validate` não aceita `--change`** — a sintaxe é `openspec validate <nome>`.
7. **O `)` sobrando** em `jca/SecretKeySpecSpec.mop:30` (e no arquivo arquivado). Congelado:
   o leitor detecta o desbalanceamento, pula com motivo e conta. Bate com `JCA_LINT`.
8. **`creation event <nome>`** existe em 10 declarações (todas em `generic_new`). Um leitor
   que só casa `\bevent\s+(\w+)` perde essas declarações.
9. **`TraceRunnerTest` tem 2 falhas pré-existentes** (`everyTraceLineResolvesToAnAdvice` e
   `theFrozenSetAccusesALegitimateGetTrustManagersThroughABindingDefect`). Verificado com
   `git stash` que são anteriores à change. Não confundir com regressão.
10. **`mvn clean install` deixa `tests/parity/test_baseline_freshness.py` vermelho** (compara
    mtime do `lib/gator/rvsec-analysis-client.jar` com o baseline do rv-static-analysis). É o
    tripwire funcionando. As outras falhas da suíte completa são de ambiente (árvore suja,
    `ANDROID_SDK_HOME` ausente) e pré-existentes.
11. **Caminhos**: o alias `/pedro/...` não resolve na JVM. Usar sempre `/home/pedro/...`.
12. **`rvsec` e `rv-android` são o mesmo repositório git** (raiz em `.../workspace-rv/rvsec`,
    branch `modules`). Um commit cobre os dois lados.
13. **`bind buf = bytes(16)`** é a forma que faz uma trace satisfazer uma predicate: o mesmo
    array é randomizado por uma chamada e lido pela seguinte. Sem o `bind`, cada `bytes` é um
    array novo e a chave de identidade nunca casa. Cuidado: `bind` no *retorno* de um
    `getInstance` faz o advice de criação **não** disparar (é o que a família de traces
    `*-guard-on-field.txt` explora).
14. **Os testes de censo do gh105 são atualizados a cada grupo**, por decisão dos próprios
    docstrings. Depois da 3.2 eles pinam 13 órfãos, 24 leituras (23 guardas + 1 corpo),
    G-ACC 13, INV-INS-133 23.
15. **A baseline (`gate_baseline.json`) não precisa ser regerada quando um grupo aterrissa**:
    as envoltórias afirmam *subconjunto*, então achados que somem passam. As linhas saem da
    baseline quando a tarefa de fechamento do grupo manda (3.7 para o G-ACC).

---

## Como retomar

```
Continue aplicando a change gh105-predicate-wiring a partir da tarefa 3.3.
Leia primeiro docs/handoff/20260820_gh105_apply_prompt_v3.md, depois os quatro artefatos em
openspec/changes/gh105-predicate-wiring/, e siga docs/WORKFLOW.md rigorosamente —
invoque a skill openspec-apply-change, não escreva artefatos à mão.
```

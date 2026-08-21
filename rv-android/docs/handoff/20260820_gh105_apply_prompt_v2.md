# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 17/74)

**Data**: 2026-08-20 · **Branch**: `modules` · **Último commit**: `25cfc590`
**Progresso**: 17 de 74 tarefas (Grupo 1 inteiro, Grupo 2 inteiro, tarefa 3.1)
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
| `design.md` | D-1 a D-14, o **ledger de 36 cláusulas**, o censo dos 17 órfãos |
| `specs/instrumentation/spec.md` | INV-INS-130 a INV-INS-148, Data Contracts, cenários WHEN/THEN |
| `tasks.md` | as 74 tarefas, com o comentário HTML de despacho no topo |

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
openspec instructions apply --change gh105-predicate-wiring --json
```

---

## O que foi feito

### Grupo 1 — substrato (rvsec-core) — 6/6, commit `b55a61a2`

`PredicateVerdict`, `PredicateStore` (chave de identidade fraca com `ReferenceQueue`,
posições `String`/`int`/`Integer` sem distinguir caixa, aridade N, `ensure/validate(Property,
Object bound, Object... values)`, `negate`, `validateAbsent`, `reset`), 19 testes JUnit,
reset do substrato no `TraceRunner.replay()` (provado por um caso cross-trace),
`ExecutionContext.java` byte-idêntico em `FROZEN_PATHS`, `Property` append-only.

**Decisão a confirmar com o pesquisador**: `bound == null` é tolerado (no-op /
`NOT_OBSERVED` / `SATISFIED`) em vez de lançar, porque uma NPE dentro de advice tecido
derruba a app sob teste. Documentado no javadoc.

### Grupo 2 — camada de gates — 12/12, commits `acec89ea`, `84c72976`, `70ef5ab8`, `3f3bdd1c`, `01a1373d`, `25cfc590`

- **2.1-2.5** `scripts/gh105_predicate_graph.py` (leitor + alfabeto + emissor + G-ACC +
  colocação + G-PRED2 + regras de junção) e `scripts/gh105_param_gate.py` (G-PARAM).
- **2.6** `gate_import` (INV-INS-130) sobre texto cru, como o `grep -rlw` da invariante — pega
  `MessageDigestSpec.mop:37`, que cita `ExecutionContext` só em comentário. Oito envoltórias
  pytest sob o contrato de CI.
- **2.7** reescopo do G-PRED para o cadeado do `jca` — **veio junto da 3.1**, não da 4.1
  (ver "Decisão reagendada" abaixo).
- **2.8** `data/jca_android/order_alphabet_map.csv`: 86 linhas, 10 especificações (as 9 do
  Grupo 3 + `CipherSpec` da 5.1); 13 especificações restantes enumeradas no cabeçalho, sob a
  tarefa 7.1. Não é bijeção nos dois sentidos: `CipherSpec.i2` é um evento sobre seis
  sobrecargas `init(int, Key, ...)`; `SignatureSpec.update` é o agregado `Updates` inteiro.
  12 linhas `order-unmapped` com motivo.
- **2.9** `scripts/gh105_order_gate.py` (G-ORDER): parser de expressão comum ao `ORDER` e ao
  `ere`, expansão de agregados, Thompson → subconjuntos → produto em largura, testemunha
  mínima. Pula sem regra, sem linhas ou com mapeamento incompleto.
- **2.10/2.11** `scripts/gh105_gate_baseline.py`, `data/jca_android/gate_baseline.json`,
  `data/jca_android/evidence/gate_baseline_report.md`, e a pré-imagem em
  `backup/gh105-preimage/jca_android/` (o lado `--a` da tarefa 8.4).
- **2.12** `/rv-doc-code` nos três scripts (docstrings Google-style; equivalência de AST
  verificada — só documentação).

### Grupo 3 — órfãos — 1/7 (tarefa 3.1), commit `25cfc590`

`SecureRandomSpec`: `c3`→`c2` e `setSeed3`→`setSeed2` fundidos, `g4` absorvido com laço
benigno nos três estados. `codes.csv` segue o sítio (`ev=setSeed3` → `ev=setSeed2`).
Três traces novas. Nove hunks no `divergence_record.csv` (kind `automaton`). A linha
`SecretKeySpecSpec.c3` do `gate_allowlist.csv` foi re-justificada e agora aponta para a 3.4,
que a apaga.

---

## Números medidos (estado atual, reproduzidos da fonte)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **14** | 0 |
| leituras em `condition(...)` | 27 | **23** | 0 |
| leituras em corpo | 0 | **1** | todas |
| escritas em corpo de evento | 42 | 42 | 0 sem motivo |
| escritas no ponto de aceitação | 7 | 7 | 49 |
| chamadas de estado de aceitação | 25 | 25 | 0 |
| `remove()` em `@fail` | 8 | 8 | 0 |
| menções a `ExecutionContext` (INV-INS-130) | 23 arquivos | 23 | 0 |
| divergências de ordenação (G-ORDER) | 4 | 4 | 0 |
| achados estruturais falhando | 145 | ~127 | 0 |

Universo enumerado: **214 `.mop`** (jca 23, jca_android 23, jca_android_bug_predicate 23,
generic 118, generic_new 27), 2 pulados com motivo. Nenhuma gate guarda esse número como
literal.

G-ORDER, as quatro divergências e suas testemunhas mínimas:
- `CipherSpec`: `f2` aceito pelo ORDER, rejeitado pela especificação (precedência do `|` no
  ORDER da regra deixa `doFinal` sozinho legal).
- `SSLContextSpec`: `g1 Init se1 se1` aceito pela especificação, rejeitado pelo ORDER (`Engine?`).
- `SecureRandomSpec`: `c1 c1` aceito pela especificação, rejeitado pelo ORDER.
- `TrustManagerFactorySpec`: `g1 i1 gtm` aceito pelo ORDER, rejeitado pela especificação.

Sobre o caso âncora do `SecureRandom`, o plano registrava que o estado `end` omite `next2`; a
medição mostrou algo pior e está fixado em teste: **o autômato não aceita nem um
`nextBytes()`**, porque o único estado de aceitação é `init` (o que o `alias match1` nomeia) e
`next2` sai dele para `end`, que não aceita.

---

## Decisão reagendada (já ratificada pelo pesquisador)

O `tasks.md` mandava a 2.7 aterrissar no commit da 4.1. Mas o gatilho que a INV-INS-141
enuncia é "quando o primeiro arquivo migrado aterrissa", e o primeiro arquivo migrado é do
Grupo 3. Deixar como estava manteria `test_jca_android_predicates_preserved` vermelho de 3.1
até 4.1 — o cenário que a D-13 existe para evitar. **A 2.7 foi reagendada para a 3.1 e
executada inteira**; o `tasks.md` foi corrigido nos quatro pontos que repetiam o acoplamento
(linhas 20, 32, 130, 206). `proposal.md`, `design.md` e o spec não foram tocados.

---

## Aprendizados que custaram tempo (não redescobrir)

1. **O `)` sobrando** em `jca/SecretKeySpecSpec.mop:30` (e no arquivo arquivado). Congelado:
   o leitor detecta o desbalanceamento, pula com motivo e conta. Bate com `JCA_LINT`.
2. **`creation event <nome>`** existe em 10 declarações (todas em `generic_new`). Um leitor
   que só casa `\bevent\s+(\w+)` perde essas declarações.
3. **`TraceRunnerTest` tem 2 falhas pré-existentes** (`everyTraceLineResolvesToAnAdvice` e
   `theFrozenSetAccusesALegitimateGetTrustManagersThroughABindingDefect`). Verificado com
   `git stash` que são anteriores à change. Não confundir com regressão.
4. **`mvn clean install` deixa `tests/parity/test_baseline_freshness.py` vermelho** (compara
   mtime do `lib/gator/rvsec-analysis-client.jar` com o baseline do rv-static-analysis). É o
   tripwire funcionando. As outras falhas da suíte completa são de ambiente (árvore suja,
   `ANDROID_SDK_HOME` ausente) e pré-existentes.
5. **Caminhos**: o alias `/pedro/...` não resolve na JVM. Usar sempre `/home/pedro/...`.
6. **`rvsec` e `rv-android` são o mesmo repositório git** (raiz em `.../workspace-rv/rvsec`,
   branch `modules`). Um commit cobre os dois lados.
7. **O harness diferencial leva ~10 min** para gerar os dois lados e replayar 66 traces.
   Rodar em background; a ferramenta Bash corta em 2 min por padrão.
8. **`bind buf = bytes(16)`** é a forma que faz uma trace satisfazer uma predicate: o mesmo
   array é randomizado por uma chamada e lido pela seguinte. Sem o `bind`, cada `bytes` é um
   array novo e a chave de identidade nunca casa.
9. **Os testes de censo do gh105 são atualizados a cada grupo**, por decisão dos próprios
   docstrings ("this test is what says which group moved them"). Depois da 3.1 eles pinam 14
   órfãos, 24 leituras (23 guardas + 1 corpo), G-ACC 14, INV-INS-133 23.
10. **A baseline (`gate_baseline.json`) não precisa ser regerada quando um grupo aterrissa**:
    as envoltórias afirmam *subconjunto*, então achados que somem passam. As linhas saem da
    baseline quando a tarefa de fechamento do grupo manda (3.7 para o G-ACC).

---

## Próximos passos, na ordem

### 3.2 `TrustManagerFactorySpec` — absorver `g3` (assinatura de co-emissão 9.015/9.014)
### 3.3 `IvParameterSpec` — fundir `c3`→`c1` e `c4`→`c2` (o `c4` não é complemento exato: ignora as restrições de offset/length do `c2`, então o corpo fundido guarda as duas verificações)
### 3.4 `SecretKeySpecSpec` — fundir `c3`→`c1` e `c4`→`c2`; **apagar** a linha `SecretKeySpecSpec.c3` do `gate_allowlist.csv` (ela já diz que sai aqui)
### 3.5 `PBEKeySpecSpec` — absorver `f1`, `f2`; fundir `err2` e `err3` em `c1` (uma seta, dois órfãos) e `err1` como o décimo; decompor a verificação por cláusula, um relato cada. Declarar o resíduo de prefixo Kleene. Dona da linha `err2` do allowlist
### 3.6 `PBEParameterSpecSpec` (`c3`→`c1`), `KeyPairGeneratorSpec` (`initError`), `SSLContextSpec` (`unsafe_protocol`), `SignatureSpec` (`g3`)
### 3.7 G-ACC verde sobre o `jca_android`, linhas da baseline retiradas, evidência de harness dos 17

**Receita por tarefa do Grupo 3** (a da 3.1, que funcionou):

1. Editar o `.mop` no reator irmão. Fusão = apagar o gêmeo e levar a acusação para o corpo do
   irmão, sem guarda. Absorção = laço benigno em todo estado onde a chamada é legal.
2. `codes.csv` segue o sítio (coluna `event` e `file_line`).
3. Remover do `order_alphabet_map.csv` as linhas dos eventos fundidos; conferir que o evento
   absorvido tem linha `order-unmapped` com motivo.
4. Traces satisfaz/viola em `data/gh104/traces/`.
5. Regerar o grafo: `--emit`.
6. `gh104_divergence_record.py --check` → registrar cada hunk novo com kind e motivo
   (`automaton` para edições de autômato; os quatro kinds novos já existem no `KINDS`).
7. Rodar o harness diferencial contra `backup/gh105-preimage/jca_android` (background).
8. Atualizar os censos em `tests/parity/test_gh105_predicate_gates.py` com uma linha de
   docstring dizendo qual tarefa moveu o número.
9. Rodar as quatro suítes de gates. Commitar. Marcar o checkbox.

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
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java`, `TraceRunnerTest.java`
- `rvsec-mop/src/main/resources/jca_android/*.mop` + `codes.csv` ← o conjunto que a change edita

**Python (`.../rvsec/rv-android/`)**
- `scripts/gh105_predicate_graph.py` (leitor + grafo + G-ACC + colocação + G-PRED2 + junção)
- `scripts/gh105_order_gate.py` (G-ORDER), `scripts/gh105_param_gate.py` (G-PARAM)
- `scripts/gh105_gate_baseline.py` (mecanismo D-13 — **tem data de demolição: tarefa 7.6**)
- `scripts/gh104_gates.py`, `scripts/gh104_divergence_record.py`, `scripts/gh104_diff_harness.py`
- `tests/parity/test_gh105_predicate_gates.py` (67 asserções), `test_gh104_specset_gates.py`,
  `test_gh104_structural_gates.py`, `test_gh101_specset_gates.py`
- `data/jca_android/`: `predicate_graph.csv`, `order_alphabet_map.csv`, `gate_baseline.json`,
  `gate_allowlist.csv`, `divergence_record.csv`, `evidence/gate_baseline_report.md`
- `data/gh104/traces/` (66 traces), `data/gh105/evidence/harness/f1-*.md`
- `backup/gh105-preimage/jca_android/` (pré-imagem), `backup/gh105-retired/`

**Oráculo (somente leitura)**: `/home/pedro/.../workspace-rv/MetaCrySL/generated/api30/*.cryptsl`

---

## Comandos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
SPECS=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources

# as quatro suítes de gates (contrato de CI obrigatório) — hoje 91 passando, ~85 s
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

# harness diferencial (~10 min: gera os dois lados e replaya 66 traces) — rodar em background
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

## Como retomar

```
Continue aplicando a change gh105-predicate-wiring a partir da tarefa 3.2.
Leia primeiro docs/handoff/20260820_gh105_apply_prompt_v2.md, depois os quatro artefatos em
openspec/changes/gh105-predicate-wiring/, e siga docs/WORKFLOW.md rigorosamente —
invoque a skill openspec-apply-change, não escreva artefatos à mão.
```

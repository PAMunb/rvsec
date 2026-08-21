# Handoff — aplicação da change gh105-predicate-wiring

**Data do checkpoint**: 2026-08-20 · **Branch**: `modules` · **Último commit**: `84c72976`
**Progresso**: 11 de 74 tarefas concluídas (Grupo 1 inteiro + tarefas 2.1 a 2.5)

---

## O que estamos fazendo

Aplicando a change **gh105-predicate-wiring** (GitHub issue #105) via o workflow OpenSpec.
A change fia as predicates CrySL (`ENSURES`/`REQUIRES`/`NEGATES`) no conjunto de
especificações `jca_android`, que hoje não as fia: das 19 predicates conectáveis contra as 33
regras api30, o conjunto realiza 3 elos; as 27 leituras de predicate estão todas dentro de
`condition(...)`, onde uma guarda falsa suprime a transição e converte "origem de chave não
modelada" num `InvalidSequenceOfMethodCalls` errado; e 17 acusadores órfãos sustentam no máximo
39.682 eventos = 56,1 % daquela categoria publicada (um teto medido sobre a campanha `jca`, não
uma atribuição causal).

O gh104 fez o handler `@fail` falar (envelope, códigos, nomes de evento). Esta change faz ele
parar de disparar quando não deve, e faz um `REQUIRES` violado se acusar.

### REGRA NÃO NEGOCIÁVEL DE WORKFLOW

Seguir `docs/WORKFLOW.md` rigorosamente. **NUNCA** escrever ou reescrever artefatos OpenSpec com
`Write`/`Edit` diretamente — invocar as skills (`openspec-apply-change`, `openspec-update-change`,
etc.) via a ferramenta `Skill`. A única edição manual permitida em `tasks.md` é marcar
`- [ ]` → `- [x]` imediatamente ao concluir cada tarefa, antes de começar a próxima
(regra de checkpoint declarada no próprio `tasks.md`).

Commits **nunca** levam `Co-Authored-By` nem qualquer trailer de coautoria. Mensagens em
português com acentuação correta, no estilo narrativo dos commits recentes (explicam *por quê*,
não só *o quê*). Sufixo `refs #105` durante o trabalho; `closes #105` só no commit final.

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente. O rv-platform gerencia o
ciclo de vida inteiro. Isso vale para as tarefas 4.3 e 8.5.

---

## Artefatos da change (leitura obrigatória antes de continuar)

Todos em `openspec/changes/gh105-predicate-wiring/`:

| Arquivo | Linhas | O que contém |
|---|---|---|
| `proposal.md` | 42 | o porquê, o escopo, o que é BREAKING |
| `design.md` | 556 | D-1 a D-14, o **ledger de 36 cláusulas** (§ "The 36-Clause Ledger"), o censo dos 17 órfãos, as questões abertas |
| `specs/instrumentation/spec.md` | 876 | INV-INS-130 a INV-INS-148, Data Contracts, cenários WHEN/THEN |
| `tasks.md` | 418 | as 74 tarefas, com o comentário HTML de despacho no topo (ordem, paralelismo, acoplamentos) |

Comandos de estado:

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
openspec status --change gh105-predicate-wiring --json
openspec instructions apply --change gh105-predicate-wiring --json
```

---

## O que já foi feito

### Grupo 1 — F0, substrato (rvsec-core) — COMPLETO (6/6)

Commit `b55a61a2`.

- **1.1** `PredicateVerdict` (`SATISFIED`/`VIOLATED`/`NOT_OBSERVED`) em
  `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/PredicateVerdict.java`.
- **1.2** `PredicateStore` no mesmo pacote. Holder singleton; chave de identidade fraca com
  `ReferenceQueue`; posições de valor de tipo `String`/`int`/`Integer` comparadas sem distinguir
  caixa, o resto por identidade; aridade N; assinatura `ensure/validate(Property p, Object bound,
  Object... values)` com o objeto ligado **antes** dos varargs; `negate` (escopo de objeto),
  `validateAbsent` (cláusulas negadas, tabela invertida), `reset` (só teste).
  Não oferece `hasEnsuredPredicate` nem remoção por propriedade.
  - **Decisão tomada e a registrar**: `bound == null` é tolerado (no-op / `NOT_OBSERVED` /
    `SATISFIED`), não lança. O design diz "Preconditions: bound non-null"; uma NPE dentro de
    advice tecido derruba a app sob teste e destrói a medição. Está documentado no javadoc da
    classe. **Confirmar com o pesquisador.**
  - `negate` grava marca de retirada (não apaga a entrada), porque D-4 exige que uma predicate
    retirada dê `VIOLATED` e não `NOT_OBSERVED`.
  - `boundObjectCount()` é package-private e existe só para o teste de purga.
- **1.3** `PredicateStoreTest` (JUnit 4), 19 testes, verdes.
- **1.4** `TraceRunner.replay()` passa a resetar `PredicateStore` e `ExecutionContext` ao lado do
  `ErrorCollector` (`rvsec/rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java`).
  Teste novo `aReplayStartsFromAnEmptySubstrateSoOneTraceCannotSatisfyTheNext` em
  `TraceRunnerTest`. **Verificado empiricamente que o teste falha quando os resets saem** — é o
  que o torna prova e não decoração.
- **1.5** `ExecutionContext.java` byte-idêntico (zero edições, confirmado por
  `git diff 7e7acb69`) e adicionado a `FROZEN_PATHS` em
  `tests/parity/test_gh101_specset_gates.py`. `Property` ganhou `PREPARED_KEY_MATERIAL` em modo
  append-only, sob `test_property_append_only` (assere as 25 constantes anteriores e a **ordem
  relativa** entre elas — a árvore tem precedente de inserção no meio do enum).
- **1.6** Reator buildado (`BUILD SUCCESS`, 69 s), rvsec-core 71/71 verde, gates gh101/gh104
  24/24 verdes.

### Grupo 2 — camada de gates — 5 de 12 (2.1 a 2.5)

Commits `acec89ea` e `84c72976`.

- **2.1–2.3** `scripts/gh105_predicate_graph.py` — o leitor, o alfabeto, o emissor.
- **2.4** G-ACC, gates de colocação (INV-INS-133/134), G-PRED2, regras de junção (a)(b)(d).
- **2.5** `scripts/gh105_param_gate.py` (G-PARAM) + fixtures `.mop`/`.rvm` versionadas.
- Todos os testes em `tests/parity/test_gh105_predicate_gates.py`: **49 passando**.

---

## Censo medido pelo leitor (linha de base, confere com a Fase 0)

Reproduzido a partir da fonte, não copiado do plano:

| Medida | `jca_android` hoje | Alvo da migração |
|---|---|---|
| leituras dentro de `condition(...)` | 27 (todas) | 0 |
| escritas em corpo de evento | 42 de 49 | 0 sem motivo registrado |
| escritas no ponto de aceitação | 7 | 49 |
| `remove()` em `@fail` | 8 | 0 |
| `remove()` em corpo (o `NEGATES` real) | 1 | 1, traduzido para `negate` |
| chamadas de estado de aceitação | 25 (19 set + 6 unset) | 0 |
| acusadores órfãos | 17 em 9 arquivos | 0 |
| achados falhando da suíte de gates | 122 | 0 |

Universo enumerado: **214 `.mop`** (jca 23, jca_android 23, jca_android_bug_predicate 23,
generic 118, generic_new 27). Nenhuma gate guarda esse número como literal — ele cresce quando
o Grupo 5 adicionar as especificações de junção.

Os 17 órfãos, por arquivo, batem exatamente com o censo do `design.md`:
`IvParameterSpec{c3,c4}`, `KeyPairGeneratorSpec{initError}`,
`PBEKeySpecSpec{f1,f2,err1,err2,err3}`, `PBEParameterSpecSpec{c3}`,
`SSLContextSpec{unsafe_protocol}`, `SecretKeySpecSpec{c3,c4}`,
`SecureRandomSpec{c3,g4,setSeed3}`, `SignatureSpec{g3}`, `TrustManagerFactorySpec{g3}`.

---

## Aprendizados que custaram tempo (não redescobrir)

1. **`jca/SecretKeySpecSpec.mop` tem um `)` sobrando** depois da condição de `c1` (linha 30). O
   arquivo arquivado tem o mesmo defeito. Está **congelado**, então não se repara: o leitor
   detecta o desbalanceamento e o arquivo é pulado com motivo e contado. Isso bate com
   `JCA_LINT = {..., "unbalanced": 1}` em `tests/parity/test_gh104_structural_gates.py`.

2. **`creation event <nome>`** existe em 10 declarações (todas em `generic_new`). Um leitor que
   só casa `\bevent\s+(\w+)` perde essas declarações e reporta 10 eventos "não declarados" que
   estão declarados. O modificador também é a matéria da regra INV-INS-136(a).

3. **`TraceRunnerTest` já tinha 2 falhas pré-existentes** — `everyTraceLineResolvesToAnAdvice`
   (658 linhas de trace que nenhum pointcut do snapshot congelado resolve) e
   `theFrozenSetAccusesALegitimateGetTrustManagersThroughABindingDefect`. **Verificado com
   `git stash` que são anteriores a esta change.** Não confundir com regressão.

4. **`mvn clean install` no reator torna `tests/parity/test_baseline_freshness.py` vermelho**,
   porque ele compara mtime do `lib/gator/rvsec-analysis-client.jar` com o baseline
   `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json`. É o tripwire funcionando
   como projetado, não um defeito desta change. As outras falhas da suíte completa
   (`test_no_legacy_mop::test_repo_is_clean`, `test_signature_file_subset`,
   `test_reachability_parity`, `test_sentinel_emission`) são de ambiente (árvore suja com ~200
   arquivos não rastreados, `ANDROID_SDK_HOME` ausente) e pré-existentes.

5. **Caminhos**: o alias `/pedro/...` não resolve na JVM. Usar sempre
   `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/...` para
   qualquer coisa que a JVM abra.

6. **`rvsec` e `rv-android` são o mesmo repositório git** (raiz em `.../workspace-rv/rvsec`,
   branch `modules`). Um commit cobre os dois lados.

---

## Decisão de interpretação que precisa de ratificação

O contrato de saída do `predicate_graph.csv` (spec, § Output) nomeia 15 colunas mas não diz onde
mora a **operação** do sítio (leitura/escrita/remoção) — e as gates precisam dela ("toda leitura
tem produtor", "toda escrita tem leitor"), enquanto INV-INS-133 exige perguntar separadamente
"este sítio é uma leitura?" e "sua classificação é `condition`?".

Resolvi assim, documentado no docstring de `COLUMNS`:

- `site_kind` = a **colocação** (`condition` / `body` / `@match` / `@fail`), que é o vocabulário
  em que os invariantes de colocação estão escritos;
- `verdict` = `<operação>:<classe>` (`read:condition-guard`, `write:acceptance`,
  `remove:fail-handler`, `bookkeeping:match`), que é o julgamento do analisador sobre o sítio.

Cinco colunas são **julgamento carregado**, não derivação — `guard`, `clause`, `mechanism`,
`disposition`, `reason` — preenchidas pelas tarefas dos Grupos 4-6 e preservadas em toda
regeração (`carry_judgments`, chaveado por `(arquivo, evento, predicate, operação, ordinal)`,
**nunca por número de linha**).

**Se o pesquisador preferir outra leitura, é mudança de uma linha em `COLUMNS` + regeração.**

---

## Próximos passos, na ordem

### 2.6 — gate de disciplina de import + fiação pytest
`grep -rlw 'ExecutionContext'` sobre `jca_android/*.mop` vazio (INV-INS-130). Registrar as gates
2.1-2.5 em `tests/parity/test_gh105_predicate_gates.py` sob o contrato de CI. Nomes exigidos:
`test_inv_ins_130_import_discipline`, `test_inv_ins_133_no_condition_reads`,
`test_inv_ins_134_write_placement`, `test_inv_ins_135_gacc`, `test_inv_ins_136_junction_rules`,
`test_inv_ins_137_gpred2`, `test_inv_ins_139_gparam`, `test_inv_ins_140_genericity`.
Dependência para a frente: cada uma se registra contra a baseline de 2.10.

### 2.7 — reescopar G-PRED para o cadeado do `jca` (INV-INS-141)
**Não fazer agora**: `tasks.md` manda esta tarefa aterrissar no **mesmo commit** que a 4.1.
Colateral enumerado na própria tarefa (todos com arquivo:linha): `gh104_gates.py`
(`accept_requires` em `:1189-1190`, `PREDICATE_CALL` em `:516`), o pytest INV-INS-128
(`test_gh104_specset_gates.py:91` e as constantes de censo em `:41-52`),
`test_gh104_structural_gates.py:229`, `gh104_message_gate.py::_clause_family:153`,
`experimento-gh104/scripts/preflight.py::check_no_predicates:158-179`, e — crítico —
**`scripts/gh104_divergence_record.py`: acrescentar os quatro kinds novos
(`predicate-store`, `placement`, `junction`, `predicate-removal`) a `KINDS:46-55`**, senão toda
linha dos Grupos 3-6 falha com `unknown kind`.

### 2.8 / 2.9 — `order_alphabet_map.csv` e G-ORDER
2.8 antes do Grupo 3. 2.9 escreve `scripts/gh105_order_gate.py` (equivalência de DFA contra o
`ORDER` da regra, sob o mapeamento de 2.8; pula declaradamente sem regra ou sem mapeamento,
nunca infere). Caso âncora: SecureRandom `Ins, Seeds?, Ends*`.

### 2.10 / 2.11 — baseline esperada e snapshot pré-mudança
**2.11 é bloqueante**: tem de aterrissar antes de qualquer edição `.mop` dos Grupos 3-6. Ela
arquiva o **diretório do conjunto** em `backup/gh105-preimage/jca_android/` — é o lado `--a` que
a tarefa 8.4 entrega ao `gh104_diff_harness.py`, que regenera os monitores sozinho.

### 2.12 — `/rv-doc-code` nos três scripts

### Depois: Grupo 3 (órfãos), Grupo 4 (um passe por arquivo)

**A change pode parar na 4.3.** A sonda de alcance (design D-12) faz a pergunta que anula a
change: se `UnsatisfiedConstraint` ficar em zero no caminho de produção, o weaver é
pré-requisito e os grupos de fiação **não podem** começar. Ela roda logo depois do primeiro
arquivo migrado, via `rv-experiment`/`rv-platform` (a plataforma gerencia o emulador), e o
veredito é commitado de qualquer jeito.

---

## Arquivos tocados até aqui

**Java (reator irmão, `.../workspace-rv/rvsec/rvsec/`)**
- `rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java` (novo, ~420 linhas)
- `rvsec-core/src/main/java/br/unb/cic/mop/PredicateVerdict.java` (novo)
- `rvsec-core/src/main/java/br/unb/cic/mop/Property.java` (append-only)
- `rvsec-core/src/test/java/br/unb/cic/mop/PredicateStoreTest.java` (novo, 19 testes)
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` (+resets)
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunnerTest.java` (+1 teste)

**Python (`.../rvsec/rv-android/`)**
- `scripts/gh105_predicate_graph.py` (novo, ~1300 linhas: leitor + alfabeto + emissor + gates)
- `scripts/gh105_param_gate.py` (novo)
- `tests/parity/test_gh105_predicate_gates.py` (novo, 49 testes)
- `tests/parity/test_gh101_specset_gates.py` (FROZEN_PATHS + `test_property_append_only`)
- `tests/parity/fixtures/gh105/` (4 fixtures de junção + `gparam/` com 4 pares `.mop`/`.rvm`)
- `data/jca_android/predicate_graph.csv` (novo, 110 linhas de sítio)

**Docs**
- `docs/20260820_validacao_gh105.md` (a revisão externa consolidada, agora rastreada)

---

## Comandos

```bash
# raiz Python
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec

# testes gh105 (contrato de CI obrigatório: --import-mode=importlib -o "addopts=")
uv run pytest tests/parity/test_gh105_predicate_gates.py --import-mode=importlib -o "addopts=" -q

# gates gh101/gh104 (têm de continuar verdes: 24 passando)
uv run pytest tests/parity/test_gh101_specset_gates.py tests/parity/test_gh104_specset_gates.py \
    tests/parity/test_gh104_structural_gates.py --import-mode=importlib -o "addopts=" -q

# suíte estrutural gh105 pela CLI (hoje: 122 achados falhando, 21 informativos)
uv run python scripts/gh105_predicate_graph.py --sets all
uv run python scripts/gh105_predicate_graph.py --sets all --json

# regerar o grafo (round-trip byte a byte sobre árvore não editada)
uv run python scripts/gh105_predicate_graph.py --emit

# G-PARAM
uv run python scripts/gh105_param_gate.py --sets jca_android --monitors results/gh51_e2e_test/monitors

# build do reator Java (JDK 21 no prefixo; recurso serializado — rodar só entre ondas)
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem
export PATH=$JAVA_HOME/bin:$PATH
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
mvn clean install -DskipMopAgent -DskipTests
mvn -o test -pl rvsec-core,rvsec-mop -DskipMopAgent
```

---

## Como retomar

```
Continue aplicando a change gh105-predicate-wiring a partir da tarefa 2.6.
Leia primeiro docs/handoff/20260820_gh105_apply_prompt.md, depois os quatro artefatos em
openspec/changes/gh105-predicate-wiring/, e siga docs/WORKFLOW.md rigorosamente —
invoque a skill openspec-apply-change, não escreva artefatos à mão.
```

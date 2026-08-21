# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 23/74)

**Data**: 2026-08-20 · **Branch**: `modules` · **Último commit**: `e5c5c140`
**Progresso**: 23 de 74 tarefas (Grupo 1 inteiro, Grupo 2 inteiro, 3.1 a 3.5)
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

`scripts/gh105_predicate_graph.py` (leitor + alfabeto + emissor + G-ACC + colocação +
G-PRED2 + junção), `scripts/gh105_param_gate.py` (G-PARAM), `gate_import` (INV-INS-130),
reescopo do G-PRED para o cadeado do `jca`, `data/jca_android/order_alphabet_map.csv`,
`scripts/gh105_order_gate.py` (G-ORDER), `scripts/gh105_gate_baseline.py` +
`gate_baseline.json` + `evidence/gate_baseline_report.md`, pré-imagem em
`backup/gh105-preimage/jca_android/` (o lado `--a` da tarefa 8.4), `/rv-doc-code` nos três
scripts.

### Grupo 3 — órfãos — 5/7 (faltam 3.6 e 3.7)

| tarefa | commit | o que fez |
|---|---|---|
| 3.1 `SecureRandomSpec` | `25cfc590` | `c3`→`c2`, `setSeed3`→`setSeed2` fundidos; `g4` absorvido com laço benigno nos três estados do `fsm` |
| 3.2 `TrustManagerFactorySpec` | `f464d604` | `g3` **fundido** em `g1`; correção do censo (três "absorções" eram gêmeos) |
| 3.3 `IvParameterSpec` | `b28540ef` | `c3`→`c1`, `c4`→`c2` |
| 3.4 `SecretKeySpecSpec` | `428fd238` | `c3`→`c1`, `c4`→`c2`; linha do allow-list retirada |
| 3.5 `PBEKeySpecSpec` | `e5c5c140` | `err1`/`err2`/`err3` fundidos em `c1` numa seta; `f1`/`f2` absorvidos por grupos de Kleene; resíduo declarado; linha do allow-list retirada |

---

## Achados desta sessão que valem mais que as tarefas

### 1. O veredito do harness é um **piso**, não uma contagem

`gh104_diff_harness.py` registra **um** envelope e **um** evento acusador **por chamada de
dispatcher** (`TraceRunner.replay`: `if (after.size() > before)` acrescenta uma entrada só, e
`envelope(...)` devolve o primeiro erro daquela especificação que achar num `HashSet`). Uma
chamada que acrescenta **dois** erros aparece como um.

É exatamente a forma de todo órfão que (a) carrega acusação própria e (b) está fora do
autômato: o corpo acusa e a linha de transição toda-`fail` acusa de novo, os dois na mesma
chamada. Resultado: um veredito `moved` (ou até `unchanged`) esconde "dois relatos viraram
um".

**Como medir de verdade** (usado nas 3.3, 3.4 e 3.5, ~30 s): o harness deixa os dois
snapshots compilados no diretório que o resumo JSON nomeia em `"scratch"`. Carregue
`mop.MultiSpec_1RuntimeMonitor` de cada lado com um `URLClassLoader`, chame os dispatchers da
chamada em questão, e conte o `ErrorCollector` inteiro. O programa está em
`data/gh105/evidence/f1-IvParameterSpec-report-count.md`; o classpath é
`rvsec/rvsec-mop/target/gh104-classpath.txt`.

Medido até agora — **todos** 2 → 1:

| arquivo | construção |
|---|---|
| `IvParameterSpec` | `new IvParameterSpec(iv)` e `new IvParameterSpec(iv, 0, 16)` com `iv` não randomizado |
| `SecretKeySpecSpec` | `new SecretKeySpec(km, "AES")` com `km` não randomizado |
| `PBEKeySpecSpec` | `new PBEKeySpec(chars)` (construtor proibido) |

**Faça isso nas 3.6 e 3.7.** Um `moved` sem essa contagem não diz o que a fusão fez.

### 2. Cláusulas que a própria API já impõe são inalcançáveis no `after ... returning`

Em `IvParameterSpec.c2` (`offset >= 0 && len >= 0 && iv.length >= offset + len`) e em
`SecretKeySpecSpec.c4` (`keyMaterial.length < offset + len`, que é a **única** cláusula
CONSTRAINTS da regra), o construtor do JDK rejeita com exceção **antes de retornar** todo caso
que a cláusula rejeita — então o advice nunca dispara e `SECRETKEYSPEC-CONSTR-01` é um código
do `codes.csv` que nenhuma execução emite.

Consequências que já foram registradas e devem ser respeitadas: a metade acusadora **fica**
(transcreve a cláusula que o oráculo enuncia); a tarefa fecha com a metade que satisfaz mais
uma **impossibilidade medida**, no lugar do par da INV-INS-144; e a auditoria de 2026-08-08
já tinha chegado ao mesmo por harness JVM
(`audit/20260808_validacao_jca_android/batchA/alfa_claims.csv`, ALFA-IVP-02), com a ressalva
de que ART/libcore não foi executado.

Evidência: `data/gh105/evidence/f1-SecretKeySpecSpec-unreachable-constraint.md`.

### 3. Um evento que não liga o parâmetro da especificação vai para **todos** os monitores

`PBEKeySpecSpec.f1`/`f2` são `after(char[] password)` — não nomeiam `PBEKeySpec`. O gerador
despacha para o conjunto inteiro (`PBEKeySpecSpec__Map`, `stateTransitionedSet.event_f1`),
não para uma instância. Fora do autômato, com linha toda-`fail`, **uma** construção proibida
em qualquer ponto do programa empurrava **todo** monitor PBEKeySpec vivo para `fail`. Procure
esse padrão nos órfãos restantes: um `after(...)` sem `returning`/`target` do tipo da
especificação é o sinal.

### 4. Colateral inevitável: gates que leem `condition(...)`

O casador de limites numéricos do **G-CONF** em `gh104_gates.py` lia só `event.condition` e
declarou `length(keyMaterial) >= off + len` sem respaldo assim que a 3.4 desceu a cláusula
para o corpo. Corrigido para ler condição **e** corpo, no mesmo padrão que `_clause_family`
já usava logo acima. **Espere mais casos assim** a cada arquivo migrado — a proposal já previa
isso para `_clause_family`; o G-CONF não estava na lista.

### 5. Uma cadeia de produtor que o harness não consegue replayar

A única cadeia do conjunto que marca um `char[]` como randomizado é a do
`RandomStringPasswordSpec`: `String.valueOf(obj)` sobre objeto randomizado → `String`
randomizada → `toCharArray()` → `char[]` randomizado. O harness **não resolve pointcut** para
`String.valueOf(n)`: o resolvedor casa tipo declarado de parâmetro (`Object`) e não
atribuibilidade. Por isso `PBEKEYSPEC-CONSTR-01` não tem trace que a satisfaça, e a trace que
tentava a cadeia inteira foi descartada em vez de commitada com linhas não resolvidas. É a
mesma sutileza do idioma `Object` que a INV-INS-136(c) nomeia pelo outro lado.

---

## Números medidos (estado atual, reproduzidos da fonte)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **4** | 0 |
| leituras em `condition(...)` | 27 | **13** | 0 |
| leituras em corpo | 0 | **6** | todas |
| escritas em corpo de evento | 42 | 42 | 0 sem motivo |
| escritas no ponto de aceitação | 7 | 7 | 49 |
| chamadas de estado de aceitação | 25 | 25 | 0 |
| `remove()` em `@fail` | 8 | 8 | 0 |
| menções a `ExecutionContext` (INV-INS-130) | 23 arquivos | 23 | 0 |
| divergências de ordenação (G-ORDER) | 4 | 4 | 0 |
| hunks no registro de divergência | — | **142, todos registrados** | — |
| traces do corpus | 63 | **73** | — |
| linhas do `gate_allowlist.csv` | 7 | **5** | — |

Harness sobre as 73 traces contra `backup/gh105-preimage/jca_android`: **63 inalteradas,
8 movidas, 2 removidas** (cumulativas contra a pré-imagem).

Os quatro órfãos que restam, todos da 3.6: `KeyPairGeneratorSpec{initError}` (absorção),
`PBEParameterSpecSpec{c3}`, `SSLContextSpec{unsafe_protocol}`, `SignatureSpec{g3}` (fusões).

G-ORDER, as quatro divergências (inalteradas por 3.1 a 3.5, endereçadas por 7.1 e Grupo 6):
- `CipherSpec`: `f2` aceito pelo ORDER, rejeitado pela especificação.
- `SSLContextSpec`: `g1 Init se1 se1` aceito pela especificação, rejeitado pelo ORDER.
- `SecureRandomSpec`: `c1 c1` aceito pela especificação, rejeitado pelo ORDER.
- `TrustManagerFactorySpec`: `g1 i1 gtm` aceito pelo ORDER, rejeitado pela especificação.

---

## Pendências levantadas e ainda não endereçadas

### 1. A guarda do `g2` tem o mesmo defeito e não pertence a nenhuma tarefa

Em `TrustManagerFactorySpec`, `SignatureSpec` e `SSLContextSpec`, o `g2` (sobrecarga de dois
argumentos) carrega a mesma `condition(ConscryptAliasTable.matches(...))` que o `g1` perdeu na
fusão. `getInstance("SunX509", provider)` não dispara evento nenhum: a guarda positiva suprime
a transição, o monitor fica sem observar a fábrica, e o `init` seguinte cai em `fail`. O `g2`
**está** no autômato, então o G-ACC não o vê, e nenhuma tarefa dos Grupos 3-6 o cobre. **Não
é** o `guard-on-field` da tarefa 8.16 do gh104. Vale abrir tarefa — a 3.6 toca dois desses
três arquivos, então é a hora de decidir. Não foi feito para não expandir escopo sozinho.

### 2. Arquivos `selftest-*.md` modificados e não commitados na árvore

`data/gh104/evidence/harness/selftest-*.md` estão modificados desde antes destas sessões. A
versão da árvore contradiz a commitada. **Não confiar nessas versões como evidência**; ler
`git show HEAD:<caminho>`. Não foram tocados.

### 3. `PBEKEYSPEC-CONSTR-01` e `SECRETKEYSPEC-CONSTR-01` são códigos sem execução possível

Por motivos diferentes (achados 2 e 5 acima). Nenhum dos dois foi reparado — reparar muda o
que o conjunto acusa. Ambos estão registrados no `divergence_record.csv` e nos arquivos de
evidência. Quem auditar os códigos do conjunto (Grupo 8) precisa saber.

---

## Próximos passos, na ordem

### 3.6 — quatro arquivos num commit (ou quatro, se preferir granularidade)

- `PBEParameterSpecSpec`: fundir `c3`→`c1` (gêmeo de 2 args; a leitura do `c2` de 3 args
  **fica sem acusador** até o passe de Grupo 4 daquele arquivo).
- `KeyPairGeneratorSpec`: **absorver** `initError` (acusa `InvalidKeySize` por conta própria).
  Já tem linha `order-unmapped` no `order_alphabet_map.csv`. Cuidado: o arquivo tem um
  `validate(int)` helper que **não** é sítio de predicate (o discriminador `(Property` do
  leitor existe por causa dele).
- `SSLContextSpec`: **fundir** `unsafe_protocol`→`g1`.
- `SignatureSpec`: **fundir** `g3`→`g1`.

Os dois últimos são os gêmeos que a correção de censo da 3.2 reclassificou: corpo que só
religa campo, mesmo tratamento e **mesmo resíduo registrado** da 3.2 (um algoritmo rejeitado
cuja fábrica nunca é inicializada passa a não ser acusado por nada).

### 3.7 — fechamento do grupo

G-ACC verde sobre o `jca_android` (zero órfãos, nas duas direções), linhas do G-ACC retiradas
da baseline (`gate_baseline.json` — a 2.15 do "aprendizados" explica por que só saem aqui),
evidência de harness commitada para os 17.

### Depois: Grupo 4 (um passe por arquivo)

**A change pode parar na 4.3.** A sonda de alcance (design D-12) faz a pergunta que anula a
change: se `UnsatisfiedConstraint` ficar em zero no caminho de produção, o weaver é
pré-requisito e os grupos de fiação **não podem** começar. Ela roda logo depois do primeiro
arquivo migrado do Grupo 4 (4.1 `CipherSpec` + 4.2 `codes.csv`, um commit atômico), via
`rv-experiment`/`rv-platform` (a plataforma gerencia o emulador), e o veredito é commitado de
qualquer jeito.

Nota para a 4.4: a tarefa diz `IvParameterSpec (4 reads / 1 write / 1 call)` — esse é o censo
**pré-change**. Depois da 3.3 o arquivo tem 2 leituras, já no corpo. O mesmo vale para 4.6
(`PBEKeySpecSpec`, 4 → 2) e para o `SecretKeySpecSpec`.

---

## Receita por tarefa do Grupo 3 (a que funcionou nas 3.1 a 3.5)

1. **Ler a regra api30 primeiro** e o corpo do órfão. **Fusão** = apagar o gêmeo e tirar a
   guarda do irmão, levando a acusação para o corpo. **Absorção** = laço benigno em todo
   estado onde a chamada é legal (num `fsm`, linhas novas; num `ere`, grupos de Kleene) +
   linha `order-unmapped` com motivo.
2. **A escrita continua guardada.** `spec = s` (e o `setProperty` que o segue) só acontece
   quando a leitura passa — o `@match` transforma isso em `ENSURES`, e o CrySL só garante
   predicate para um uso que satisfez a regra. Tirar a guarda da escrita enfraquece a detecção
   rio abaixo.
3. Editar o `.mop` **inteiro, comentários incluídos**, antes de tudo. **O digest do hunk é do
   conteúdo**: mexer no comentário depois re-chaveia a linha do registro e obriga a refazer
   `codes.csv` e o registro.
4. `codes.csv` segue o sítio (colunas `event` e `file_line`) — os números de linha mudam
   quando você acrescenta comentário; reconferir com `grep -n 'addError'` no fim.
5. Remover do `order_alphabet_map.csv` as linhas dos eventos **fundidos** (evento fundido
   deixa de existir e não ganha isenção); conferir que o **absorvido** tem `order-unmapped`
   com motivo.
6. Traces satisfaz/viola em `data/gh104/traces/`. Se um dos lados for impossível, **declarar e
   medir** a impossibilidade em vez de assumir.
7. Regerar o grafo: `--emit`. Conferir round-trip.
8. `gh104_divergence_record.py --check` → registrar cada hunk novo com kind `automaton` e
   motivo. **Linhas `stale` têm que sair**, e as razões que elas carregavam (allow-list da 2.4,
   `message` da 7.5, reparos da 8.x) precisam ser **absorvidas** na razão do hunk novo, com a
   coluna `task` acumulando (`2.4;7.5;3.4`).
9. Rodar o harness diferencial (background, ~10 min) **e** a sonda de contagem de relatos.
10. Atualizar os censos em `tests/parity/test_gh105_predicate_gates.py` com uma linha de
    docstring dizendo qual tarefa moveu o número. São **seis** lugares: censo de órfãos
    (nomes + soma), censo do leitor (reads/condition), censo de colocação
    (`read:condition-guard`/`read:body`), sítios órfãos do grafo, contagem do G-ACC, contagem
    do INV-INS-133.
11. Rodar as quatro suítes. Commitar. Marcar o checkbox.

---

## Arquivos relacionados

**Java (reator irmão, `.../workspace-rv/rvsec/rvsec/`)**
- `rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java`, `PredicateVerdict.java`, `Property.java`
- `rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java` (**congelado, byte-idêntico**)
- `rvsec-core/src/main/java/br/unb/cic/mop/eh/ErrorDescription.java`, `ErrorSummary.java` (identidade do relato = o `ErrorSummary`, que inclui `code` e `ev`)
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` (gramática das traces; a limitação do envelope está em `replay`)
- `rvsec-mop/src/main/resources/jca_android/*.mop` + `codes.csv` ← o conjunto que a change edita
- `rvsec-mop/target/gh104-classpath.txt` (classpath para a sonda de contagem)

**Python (`.../rvsec/rv-android/`)**
- `scripts/gh105_predicate_graph.py`, `gh105_order_gate.py`, `gh105_param_gate.py`
- `scripts/gh105_gate_baseline.py` (mecanismo D-13 — **tem data de demolição: tarefa 7.6**)
- `scripts/gh104_gates.py` (G-CONF agora lê condição **e** corpo), `gh104_divergence_record.py`, `gh104_diff_harness.py`
- `tests/parity/test_gh105_predicate_gates.py` + as três suítes gh101/gh104
- `data/jca_android/`: `predicate_graph.csv`, `order_alphabet_map.csv`, `gate_baseline.json`,
  `gate_allowlist.csv`, `divergence_record.csv` (**CRLF** — preserve), `alias_table.csv`,
  `constraint_table.csv` (oráculo do G-CONF, só para o `jca`)
- `data/gh104/traces/` (73 traces)
- `data/gh105/evidence/harness/f1-*.md` (gerados pelo harness) e, ao lado,
  `f1-IvParameterSpec-report-count.md`, `f1-SecretKeySpecSpec-unreachable-constraint.md`,
  `f1-PBEKeySpecSpec-fusion.md` (escritos à mão, com o programa que reproduz)
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

# suíte estrutural gh105 pela CLI (--json dá as contagens por gate)
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets all
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets jca_android --emit

# G-ORDER (filtre `skipped`; só as 4 divergências conhecidas devem aparecer)
uv run python scripts/gh105_order_gate.py --specs-root $SPECS --sets jca_android

# baseline (comparar; --write só quando a tarefa mandar)
uv run python scripts/gh105_gate_baseline.py --specs-root $SPECS

# registro de divergência
uv run python scripts/gh104_divergence_record.py --check
uv run python scripts/gh104_divergence_record.py --refresh   # imprime as linhas vivas

# harness diferencial (~10 min) — rodar em background
# NÃO canalizar para `tail`: o resumo JSON (inclusive o "scratch") fica no TOPO da saída
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

1. **O critério gêmeo-vs-absorção é o corpo do órfão**, não a guarda. Corpo que acusa por
   conta própria (algoritmo rejeitado, tamanho de chave, construtor proibido) → **absorve**.
   Corpo que só religa campo, ou cuja acusação é a negação exata da guarda do irmão →
   **funde**. Foi isso que corrigiu o censo do `design.md` na 3.2.
2. **O veredito do harness é piso, não contagem.** Ver o achado 1 acima. Sempre rode a sonda.
3. **Um órfão pode suprimir o achado, não só somar ruído** (medido na 3.2: o `__RESET` do
   órfão devolve o monitor a um estado onde o evento seguinte não está declarado, a transição
   que falha toma o `@fail` em vez do corpo, e a checagem de CONSTRAINTS nunca roda).
4. **A tabela de alias do gh104 muda quais traces exercitam um órfão.** `X509` resolve para
   `PKIX` (`alias_table.csv:2`), então a trace `-x509` **não** alcança o `g3`. Antes de
   escrever trace de violação, confira se o valor tem linha na tabela de alias.
5. **O digest de hunk é do conteúdo.** Terminar o `.mop` (comentários incluídos) antes de
   sincronizar `codes.csv` e antes de registrar hunks.
6. **`openspec validate` não aceita `--change`** — a sintaxe é `openspec validate <nome>`.
7. **`csv.writer` escreve `\r\n` por padrão.** O `divergence_record.csv` **é** CRLF (preserve);
   o `gate_allowlist.csv` é LF (passe `lineterminator="\n"`, ou o diff vira o arquivo inteiro).
8. **O `)` sobrando** em `jca/SecretKeySpecSpec.mop:30` (e no arquivo arquivado). Congelado:
   o leitor detecta o desbalanceamento, pula com motivo e conta.
9. **`creation event <nome>`** existe em 10 declarações (todas em `generic_new`).
10. **`TraceRunnerTest` tem 2 falhas pré-existentes** (`everyTraceLineResolvesToAnAdvice` e
    `theFrozenSetAccusesALegitimateGetTrustManagersThroughABindingDefect`). Verificado com
    `git stash` que são anteriores à change. Não confundir com regressão.
11. **`mvn clean install` deixa `tests/parity/test_baseline_freshness.py` vermelho** (compara
    mtime do `lib/gator/rvsec-analysis-client.jar` com o baseline do rv-static-analysis). É o
    tripwire funcionando.
12. **Caminhos**: o alias `/pedro/...` não resolve na JVM. Usar sempre `/home/pedro/...`.
13. **`rvsec` e `rv-android` são o mesmo repositório git** (raiz em `.../workspace-rv/rvsec`,
    branch `modules`). Um commit cobre os dois lados. A árvore tem **muita** modificação
    pré-existente não relacionada (docs, `data/apks/`, `scripts/` novos) — **stage por
    caminho explícito**, nunca `git add -A`.
14. **Os testes de censo do gh105 são atualizados a cada grupo**, por decisão dos próprios
    docstrings. Depois da 3.5 eles pinam 4 órfãos, 19 leituras (13 guardas + 6 corpo),
    G-ACC 4, INV-INS-133 13, INV-INS-130 23.
15. **A baseline (`gate_baseline.json`) não precisa ser regerada quando um grupo aterrissa**:
    as envoltórias afirmam *subconjunto*, então achados que somem passam. As linhas saem da
    baseline quando a tarefa de fechamento do grupo manda (3.7 para o G-ACC).
16. **O `ere` suporta `*`, `+`, `|` e agrupamento**, e a árvore já usa o idioma de prefixo
    Kleene para absorver acusador (`g3* g1 | g3* g2` no CipherSpec e no MessageDigestSpec da
    semente). Foi o que a 3.5 usou.

---

## Como retomar

```
Continue aplicando a change gh105-predicate-wiring a partir da tarefa 3.6.
Leia primeiro docs/handoff/20260820_gh105_apply_prompt_v4.md, depois os quatro artefatos em
openspec/changes/gh105-predicate-wiring/, e siga docs/WORKFLOW.md rigorosamente —
invoque a skill openspec-apply-change, não escreva artefatos à mão.
```

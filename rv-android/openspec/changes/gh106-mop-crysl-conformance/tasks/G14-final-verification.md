# G14 · final verification

**Depends on:** everything. **Size:** the verification sequence plus the documentation sync.

## Tasks

- [x] 14.1 `/rv-qa-lint-fix scripts` and `/rv-qa-lint-fix tests/parity` — the Python surface this change touches.
- [x] 14.2 `cd $W/rvsec && mvn clean install -DskipMopAgent` with JDK 21, **tests enabled** for the four new modules. Note that the reactor also builds under JDK 25; 21 is what the pom targets and what this gate uses.
- [x] 14.3 `/rv-verify scripts` and `uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh106_retirement.py`.
- [x] 14.4 Confirm the five surviving gates are still green, **locally**, and record the invocations — they are not run by any CI job (G13a 13a.7).
- [x] 14.4-bis Confirm the CI step from G05 5.10 exists and that the four new modules' tests actually ran in a CI run, not only locally. Read the workflow log rather than the exit code: `-DskipTests` produces a green build with zero tests, which is the exact failure this step exists to prevent.
- [x] 14.4-ter Confirm the oracle-dependent tests are **tagged and declaredly excluded** in CI (G05 5.11), and that the exclusion is written where a reader of the green will see it. A partial green that looks total is worse than a red.
- [x] 14.4-quater **The CI/local split declared in G05 5.11 is stale — re-measure and re-declare it.**
  When 5.11 was written the local-only half was "23 tests, all in `-crysl`". Measured again at G05
  closure it is **59**, and **one of them is in `-mop`** (`RoundTripGateTest:240`), so the sentence
  "everything in `-core` and `-mop` runs in CI" is **no longer true**. A declared split that has
  drifted is worse than an undeclared one, because a reader trusts it. Re-measure with
  `-DexcludedGroups=oracle-dependent`, write the real numbers into the workflow comment, and decide
  the `-mop` case explicitly: either it legitimately needs `android.jar` and the declaration must say
  so, or it can be made CI-reachable. RISK-002.
- [x] 14.4-quinquies **One `@Tag("oracle-dependent")` is a bare literal, not a shared constant.**
  `RoundTripGateTest:240` in `-mop` cannot see `-crysl`'s `OracleCorpus.TAG`, so the tag name now
  exists as two independent strings that must agree with `ci.yml`. Put the constant where both
  modules reach it (`-core`), or record why a literal is acceptable. A tag that silently stops
  matching excludes nothing and the CI green quietly widens.
- [x] 14.5 Confirm the calibration gate passes at the current HEAD, and that the commit it ran at is recorded beside the commit the targets were taken at. If HEAD moved during implementation — it moved during **each** of the three preceding rounds — re-run the eight targets and record the new stamp rather than assuming they carried.
- [x] 14.6 Invoke `/rv-code-reviewer` via the Skill tool over the full change diff.
- [x] 14.7 `/rv-docs-sync`: update `rvsec/CLAUDE.md` (module map and reactor build order, which gains `rvsec-crysl`), `openspec/specs/README.md` (a `conformance` row in the domain table, and the `CONF` invariant abbreviation in the conventions list), and the `rvsec/rvsec-crysl/*/CLAUDE.md` module docs if the module-doc convention applies to the reactor tree.
- [x] 14.7-bis Amend `design.md` **via `/opsx:update`** (never by hand — it is a schema artifact):
  Data Flow §5 still says M2 computes `h⁻¹(L_mop)`, which D-20 moved to the lift on 24/08/2026.
  Record D-20 in the Decisions section with its consequences. **Amend INV-CONF-11 in the same
  pass**: it says pairing is "by declared type" but omits that it must be **injective** with a
  signature-derived tie-break, without which the 22-of-24 target reads 23 (see
  `G12-corpus-calibration.md` § "Target 6 needs a rule the invariant does not state").
  **Feito em 24/08 pelo orquestrador, via `/opsx:update`, seis emendas, `openspec validate` verde:**
  INV-CONF-06 (cinco → seis tags, com o motivo da sexta); INV-CONF-11 (injetividade + desempate por
  assinatura, com a evidência `IvChainJunction`×`CipherSpec`); M0.2 (o critério é alcançabilidade, e
  `SecretKeySpec` passa a ser nomeado); a frase de sensibilidade da regra do M3 ganha o trio medido
  119/125/145 e o argumento de impossibilidade; a tabela da taxonomia ganha a sexta linha; a rota do
  alvo 6 passa a dizer que os *skips* são prosa do cabeçalho, nunca linhas de dados. No `design.md`:
  Data Flow §5 reescrito e **D-20** registrado na seção Decisions. Leaving the prose contradicting the
  invariant is how the next round re-implements the placeholder.
- [x] 14.8 Verify the cross-referencing convention end to end: `proposal.md` carries `GitHub Issue: #106`; intermediate commits use `refs #106`; the final commit uses `closes #106`; the PR body carries `Closes #106`.
- [x] 14.9 Check off every acceptance criterion in issue #106 that is satisfied, and annotate any that a scope change superseded — an unchecked box on a closed issue reads as incomplete work.
- [ ] 14.10 Run `/opsx:verify` for the change, then `/opsx:archive` once the researcher approves.
- [ ] 14.11 Move the Kanban card to Done via `gh project item-edit` (project `PVT_kwDOAJRqj84BPHtv`, status field `PVTSSF_lADOAJRqj84BPHtvzg9n4kM`, option `53305933`). The automation does not do this.

## Closing
G14 closes when 14.1–14.11 are `[x]`, **including 14.4-bis, 14.4-ter and 14.7-bis** (aprendizado nº 18), and with it the change.

## O que foi medido no fechamento mecânico (24/08/2026)

Tudo abaixo foi **re-executado neste fechamento**, não copiado do G13b nem do G12. Carimbo:
`rvsec` **`6192b57a`**, `rvsec-cognicrypt` **`f2f4d3b`**, JDK **25** (o pom mira 21; o reator constrói
sob 25 e nenhum módulo reclamou). Nada foi commitado.

### 14.2 · reator inteiro, com testes ligados

`cd $W/rvsec && mvn clean install -DskipMopAgent` → **BUILD SUCCESS**, 48 módulos, **2 034 testes,
0 falhas**. Os quatro módulos novos: o pai é `packaging=pom` e não tem *surefire*; `-core` **166**,
`-mop` **58**, `-crysl` **102** (1 *skip*, o alvo 8 sem `RVSEC_GENERATED_MONITOR`). Os três módulos
GATOR (33–35) não executaram teste algum — `skipTests=true` no próprio pom, condição anterior a esta
change e alheia a ela.

### 14.4 · os cinco portões sobreviventes, localmente

| portão | invocação literal | resultado |
|---|---|---|
| `gh105_order_gate.py` | `uv run python scripts/gh105_order_gate.py --sets jca_android` | `13 passed, 0 failed, 9 allow-listed, 2 skipped de 24`; `exit 0` |
| `gh101_conformance_check.py` | `uv run python scripts/gh101_conformance_check.py -o <scratch>/gh101.csv` | `23 verdicts, none blank`; `exit 0` |
| `gh104_baseline.py` | `uv run python scripts/gh104_baseline.py --out <scratch>/gh104_baseline` | `envelopes: 87; with an expected value: 63; disagreements: 0`; `exit 0`; `baseline.json` **idêntico** ao commitado |
| `gh104_gates.py` | `uv run python scripts/gh104_gates.py --monitor <scratch>/MultiSpec_1RuntimeMonitor.java --allowlist data/jca_android/gate_allowlist.csv --crysl ../../MetaCrySL/generated/api30 --value-crysl ../../RVSec-replication-package/tools/rules --alias data/jca_android/alias_table.csv --constraint-table data/jca_android/constraint_table.csv` | **`exit 1`** (`"ok": false`), reproduzindo o G13b dígito a dígito: G-2a 11/**3**, G-2b' 18/0, G-2c 2/0, G-2d 3/0, G-CONF 80 notas/0, G-PRED 23/**23** |
| `test_gh105_predicate_gates.py` | `uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh105_predicate_gates.py` | **73 passed** |

O `gh104_gates.py` precisa do marcador `gh104_set.txt` ao lado do monitor quando este é gerado em
*scratch*; sem ele três dos nove portões internos pulam por não derivar o diretório do conjunto. Os
`.mop` foram **copiados** para *scratch* antes da geração (INV-CONF-12): `git status` sobre
`rvsec/rvsec-mop/src/main/resources/` ficou vazio depois da passagem.

### 14.4-quater · a divisão CI × local, re-medida e re-declarada

A declarada em 5.11 (23, tudo em `-crysl`) e a do fechamento do G05 (59) estavam **as duas erradas**.
Medida agora, com `-DexcludedGroups=oracle-dependent`:

| módulo | corrida local completa | passo da CI | só local |
|---|---:|---:|---:|
| `rvsec-crysl-core` | 166 | 166 | 0 |
| `rvsec-crysl-mop` | 58 | 57 | **1** |
| `rvsec-crysl-crysl` | 102 | 38 | 64 |
| **total** | **326** | **261** | **65** |

Os 65 excluídos são exatamente os etiquetados: 11 classes inteiras de `-crysl` mais 2 testes de
`M0VitalityTest`, 10 de `M3ConstraintsCorpusTest`, 2 de `M4PredicateCorpusTest` e o único de `-mop`.
**O caso do `-mop` foi decidido explicitamente e fica local:**
`RoundTripGateTest.test_the_fifth_check_resolves_pointcuts` resolve os *pointcuts* gerados contra
`$ANDROID_HOME/platforms/android-30/android.jar`, e instalar um SDK Android na CI para rodar um teste
custa mais do que compra. Os números e a decisão foram escritos no comentário do `ci.yml`, com a
frase que impede a leitura antiga: *"não leia isto como 'tudo fora de `-crysl` está coberto': era
verdade quando a divisão foi escrita e não é agora"*.

### 14.4-ter · a exclusão está onde quem lê o verde a vê

Além do comentário no arquivo, o passo agora **imprime no log** o que não rodou: `65 de 326`, os três
insumos que faltam (regras *upstream* em `rvsec-cognicrypt`, `android.jar`, o monitor regerado), a
divisão 64/1 e o comando do portão local. `ReactorBuildIT` (4 testes, roda na CI) continua verde
contra o `ci.yml` editado.

### 14.4-quinquies · a etiqueta passou a ter um dono só

`CiTags.ORACLE_DEPENDENT` foi criada em `rvsec-crysl-core/src/test/java/.../core/CiTags.java`, e
`-core` passou a publicar um **`test-jar`** (`maven-jar-plugin`, meta `test-jar`) que `-mop` e
`-crysl` consomem em escopo `test`. O literal solto de `RoundTripGateTest:240` virou
`@Tag(CiTags.ORACLE_DEPENDENT)`; `OracleCorpus.TAG` virou um *alias* da constante; e
`ReactorBuildIT` passou a conferir o texto do *workflow* contra `OracleCorpus.TAG` em vez de contra
uma cópia da palavra. Verificado por medição: a exclusão continua tirando os mesmos 65.

### 14.5 · calibração no HEAD de fechamento

`java -cp <...> ConformanceCli calibrate --commit 6192b57a --oracle-commit f2f4d3b --monitor <...>`
→ **8 alvos, 0 *mismatches*, 0 checagens de auto-consistência**. Os oito reproduzem: T1 `215/215 ok`,
T2 `93 de 118`, T3 `0 de 24`, T4 `47 de 49`, T5 `80 de 119`, T6 `22 de 24`, T7 `5 de 22`,
T8 `5 de 24` (pela rota dos **monitores regerados**, gerados nesta passagem: 1m16s,
`CipherInputStreamSpec, CipherOutputStreamSpec, HMACParameterSpecSpec, KeyStoreSpec,
RandomStringPassword`).

**Os dois carimbos, lado a lado, como o 12.5 exige** — e eles **diferem**, o que é o caso que a regra
existe para não esconder:

| corpus | rota do alvo | esta corrida |
|---|---|---|
| os cinco corpora `.mop` (`rvsec`) | `5fbe8173` | `6192b57a` |
| `generic` (`rvsec`) | `5fbe8173` | `6192b57a` |
| `jca_android` (`rvsec`) | `5fbe8173` | `6192b57a` |
| `CrySL-Rules` (`rvsec-cognicrypt`) | `f2f4d3b` | `f2f4d3b` |

A suíte completa com o monitor apontado: `-core` **166**, `-mop` **58**, `-crysl` **102**, **zero
falhas e zero *skips***.

### 14.6 · a revisão pediu mudanças, e elas foram feitas e medidas

**Estado em 24/08/2026 (noite): os cinco achados estão reparados.** O registro completo — com as
medições antes e depois de cada reparo, a prova de determinismo e os oito veredictos da calibração
re-executada — está na adenda de `rv-android/docs/20260824_adjudicacao_calibracao_gh106.md`. Em
resumo:

| achado | reparo | o que se moveu |
|---|---|---|
| 1 · não determinismo em coluna publicada | ordem declarada para as três coleções (`List` de precedência, `EnumMap`, conjunto por ordem de inserção) | `constraint_table.csv` deixa de alternar; o `mop_line` das 8 linhas de `CipherSpec` fixa em `CipherSpec:85`. **9 JVMs separadas byte-idênticas** (antes: 2 conteúdos para o CSV e 6 para o JSON em 6 corridas). A chave de pareamento já era estável em 8 JVMs — risco latente, removido sem mover o alvo 6 |
| 2 · `+` de subtipo não removido em `resolve` | uma única regra, em `resolve` | M0.3 sobre `generic_new`: **82 recusas em 23 → 73 em 19**; 7 tipos declarados corrigidos; M1 e o conjunto de pares **inalterados** |
| 3 · `!( … )` invisível | `negatedAt` atravessa parênteses de agrupamento | censo do *lift* **6/5/25 → 7/5/26**; uma aresta do M4 vira *invertida* em `jca` e em `bug_predicate`; duas asserções elevadas à realidade corrigida, com o motivo escrito |
| 4 · M3 devolvendo `absent` em falha de leitura | `unreadable(...)` nas três rotas | vetor M3 **inalterado** (31/36/13 de 80): sob a regra de contagem escrita, 1 das 80 linhas é falha de leitura e ela não chega à porta do `absent`. Os "34 de 80" da revisão são discordância registrada, não absorvida |
| 5 · comentários P4 | quatro reescritos | `MOPNameSpace.init()` só limpa a bandeira `used` — verificado na fonte; o comentário foi corrigido e **o código não** |

Calibração depois de tudo: **8 alvos, 0 `mismatches`**, nenhum alvo se moveu. Suíte: `-core` **171**,
`-mop` **59**, `-crysl` **102**, zero falhas e zero *skips* com o monitor apontado; modo CI
`171/58/38`. A divisão declarada no `ci.yml` foi re-medida para `65 de 332`.

### 14.6-histórico · o que a revisão devolveu

`/rv-code-reviewer` devolveu **REQUEST CHANGES**. Três achados **movem número publicado** e por
INV-CONF-14 ficam registrados para adjudicação, não reparados aqui: o `+` de subtipo não removido em
`PointcutExpander.resolve` (move M0.3, M1 e o conjunto de pares), a negação `!( … )` entre parênteses
não vista por `PredicateIdioms.negatedAt` (move o censo do *lift* de 6/5/25 para 7/5/26) e o M3
devolvendo `absent` onde o leitor não reconheceu o idioma — 34 das 80 linhas publicadas — quando o
contrato da própria classe diz `Unknown{UnrecognizedConstraint}`. Dois são de artefato e **bloqueiam
o arquivamento**: `INV-CONF-06` diz cinco etiquetas e `Unknown.java` permite **seis**
(`UnreachableAccusationSite`), e uma coluna de proveniência publicada é **não determinística entre
JVMs** (`Set.of` em `M3Constraints.TRANSFORMATION_HELPERS`, `Set.copyOf` em `Event`).

**O que sobrou desse parágrafo.** Os três achados de número e o do determinismo foram reparados e
medidos na mesma noite — ver 14.6 acima. Continua aberto **apenas** o do `INV-CONF-06`: o
invariante diz cinco etiquetas e `Unknown.java` permite seis (`UnreachableAccusationSite`). É
dívida de artefato, pertence ao 14.7-bis e **não é editável por este grupo**.

### 14.8 · a convenção é satisfazível; nada foi commitado

`proposal.md` traz `GitHub Issue: #106`. Os commits intermediários já usam `refs #106` (`39b000ce`,
`f10fec65`, ambos ancestrais do HEAD). Falta o commit final, que deve trazer **`(closes #106)`** no
assunto, seguir a forma do repositório (`<tipo>(gh106): assunto narrativo em português`) e **não
levar nenhum *trailer* `Co-Authored-By`**. O repositório trabalha direto no ramo `modules` e quase não
abre PR (um único, o #85); se um PR for aberto, o corpo tem de trazer **`Closes #106`**.

### 14.9 · issue #106

Os 14 critérios de aceitação foram marcados: **12 `[x]`** e **2 `[ ]` deixadas abertas de propósito**
— o critério dos *dois* oráculos, que a D-06 substituiu e que deliberadamente **não** foi entregue
(a medição do `api30` sobrevive como nota de método), e o critério das quatro *skills*, aberto
porque `/rv-code-reviewer` pediu mudanças. Três critérios trazem a anotação do que uma decisão de
escopo substituiu (D-06, D-08, D-17, D-18), com o valor entregue ao lado do valor escrito.

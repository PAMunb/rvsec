# Fase 0 — Estado das changes GH100 e GH101

Auditoria formal das 23 especificações JavaMOP `jca_android`. Data: 2026-08-08.
Modo de leitura: **todo item `[x]` é tratado como alegação, não como fato** — nada
aqui valida evidência; este documento inventaria o que as changes alegam, onde a
evidência apontada mora, e onde ela não foi localizada. O oráculo da auditoria são
as regras CrySL; a GH101 é hipótese de implementação.

Caminhos-base usados abaixo:

- `CH` = `rv-android/openspec/changes/`
- `DATA` = `rv-android/data/gh101/`
- `SCRIPTS` = `rv-android/scripts/`
- `MOP` = `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources` (reator Java irmão)

---

## 1. Status real de cada change

### GH100 — weaver-emission-fidelity (`CH/gh100-weaver-emission-fidelity/`)

Repara três defeitos do weaver DEX-nativo (`rvsec-instrumentation-dexlib2`):
truncamento de emissão em advices fundidos (advice com N `monitorCalls` emitia só
o primeiro invoke — 9 eventos nunca chegavam ao DEX, 8 deles emissores de erro),
colisão do registro de wrappers (12 wrappers silenciosamente descartados; reparo
final por **merge** no `WrapperEmitter`, não por alargamento da chave — D-B1), e
parse de pointcut fail-open. Torna a Camada 3 executável com oráculos derivados
(L3-b, L3-c) e conserta o comparador de traces, que desde a gh52 lia um formato de
linha que nada no pipeline emite.

**Contagem de tarefas: 55 `[x]` e 3 `[ ]`** — a change **não** está integralmente
concluída:

- A tarefa **7.4 aparece duplicada** em `tasks.md` (linhas 96–97): uma instância
  `[x]` com resultado registrado (`/rv-verify rv-instrumentation-dexlib2` — lint
  FAIL em 3 E501 pré-existentes) e uma instância `[ ]` idêntica logo abaixo.
  Contradição interna do artefato.
- **7.5** (`/rv-code-reviewer`) e **7.6** (`/rv-docs-sync`) estão `[ ]`.
- 7.7 (notificar a GH101 de que a task 5.3 aterrissou) está `[x]`.

O núcleo técnico (grupos 1–6, o reparo em si e a evidência red→green) está todo
`[x]`. Evidência apontada: `CH/gh100-weaver-emission-fidelity/evidence/` com 15
arquivos — `census_pre_repair.json` / `census_post_repair.json` (censo mecânico do
truncamento: 3 sítios→0, 9 eventos perdidos→0), `v0_red_emission_cardinality.txt`
(V0 vermelho, 4/5 asserções falham), `v2_red_cryptoapp.{json,txt}` e
`v2_green_cryptoapp.{json,txt}` (V2 vermelho→verde sobre os mesmos bytes pinados,
`v2_pinned_inputs.md`), `green_deltas.md`, `l3_verdicts.md` +
`l3b_verdict.json`/`l3c_verdict.json`, e `inv_ins_105_cryptoapp_*`.

Ponto de leitura obrigatório: `l3_verdicts.md` declara os vereditos L3-b/L3-c como
**caracterização, não certificação** — os dois lados de cada oráculo derivado são
gravações pré-reparo congeladas; L3-b dá `passed: false` (4/8 oráculos passam, 10
FP concentrados em `TrustManagerFactorySpec` — a assinatura da colisão de
wrapper). O braço de runtime L3-a não rodou (nenhum emulador foi iniciado). V0/V2
provam emissão e chegada **no DEX tecido**, não chegada no logcat.

Commit da evidência vermelha: `e29c3694`; reparo do wrapper (task 5.3, a única
dependência da GH101): `48b57fc5`.

### GH101 — jca-spec-conformance (`CH/gh101-jca-spec-conformance/`)

**84/84 tarefas `[x]` confirmadas por contagem** (`grep -c '^- \[x\]'` = 84;
`[ ]` = 0), distribuídas em 11 grupos: 1 (registros), 2 (tabelas de Cipher), 3
(as duas specs quentes), 3b (os 16 eventos all-fail restantes), 4 (grafo de
predicados em `.mop`), 4b (re-chaveamento do `ExecutionContext` por identidade),
5 (vocabulário novo), 6 (`jca_android` selecionável por nome), 7 (guardas e
registros), 8 (verificação empírica, dependente da GH100) e 9 (verificação).

Os grupos 3b, 4b e as tarefas 4.6–4.13, 5.1b–5.1d foram **inseridos durante a
implementação** (numeração "3b"/"4b" deliberada para não deslocar referências
externas), quando as verificações da própria change ampliaram o achado: 2 eventos
all-fail viraram **18**; o grafo revelou pointcuts fundidos que impedem bindings;
o `ExecutionContext` chaveava por `equals` contra um índice de monitores por
identidade.

Premissa estrutural (D-S0): o conjunto `jca` está **congelado** no commit
`7e7acb69` (nem um byte de `MOP/jca` nem de `CipherTransformationUtil.java` muda);
toda correção aterrissa em `jca_android`. Consequência assumida: os dois conjuntos
deixam de diferir por um único eixo (allow-list), e nenhuma medição pós-hoc separa
allow-list de reparo — por isso o antigo parity check virou freeze check +
enumeração (D-S7).

Estado no reator irmão (verificado por listagem, não validado): `MOP/jca_android/`
tem 23 `.mop`; `rvsec-core/.../jca/util/` contém `CipherTransformationUtil.java`
**e** `AndroidCipherTransformationUtil.java`. Em `rv-android`,
`config.py`/`__main__.py` carregam `jca_android` (`click.Choice` em
`__main__.py:443`).

Ambas as changes estão **abertas** (não arquivadas) no branch `modules`; os
artefatos aparecem modificados no working tree.

---

## 2. Registros que a GH101 alega ter produzido

Todos localizados, exceto onde anotado. "Alegação central" = o que o artefato diz
de si mesmo; nada abaixo foi reproduzido nesta fase.

| Registro | Caminho real | Existe? | Formato | Alegação central |
|---|---|---|---|---|
| Conformance record | `DATA/conformance_record.csv` (23 linhas + header) | sim | CSV | Veredito para cada um dos 23 `.mop` contra as regras API 30: 10 `anchored`, 11 `uncontradicted`, 2 `no-anchor` (`CipherSpec` — constraint mora em Java; `RandomStringPassword` — sem contraparte CrySL). Colunas extras para aliases e variantes de grafia (questão aberta ao usuário). Produzido por `SCRIPTS/gh101_conformance_check.py` |
| Predicate inventory (congelado) | `DATA/predicate_inventory_jca.csv` (85 sítios) | sim | CSV | Baseline do freeze: 49 writes, 27 reads, 9 removals; deve ser idêntico a si mesmo no fim da change (alegado idêntico byte a byte na tarefa 7.4). Script: `SCRIPTS/gh101_predicate_inventory.py` |
| Predicate inventory (derivado) | `DATA/predicate_inventory_jca_android.csv` (127 sítios) | sim | CSV | Pós-reparo: 58 writes, 56 reads, 13 removals; 3 arestas vivas viraram 14; cada diferença atribuída a uma tarefa (tabela em `DATA/README.md`) |
| Edge map / contagens por arquivo | `DATA/predicate_edges.csv` (84 cláusulas), `DATA/edge_counts_per_file.csv` | sim | CSV | 84 cláusulas CrySL (46 ENSURES, 36 REQUIRES, 2 NEGATES) ancoradas ao **CrySL 1.5.2** (não às regras API 30 — decisão explícita: semântica não varia com API level); 36 arestas a fechar. Mantido como baseline do Grupo 1, deliberadamente não regenerado. Script: `SCRIPTS/gh101_predicate_edges.py` |
| Deliberate omissions | `DATA/predicate_omissions.csv` (20 linhas) | sim | CSV, escrito à mão e verificado por script | 11 `constant-write-no-read` + 9 `predicate-no-constant`, cada um com a razão mecânica (ver §5) |
| Divergence record | `DATA/divergence_record.csv` (106 hunks + header) | sim | CSV | Todo hunk pelo qual `jca_android` difere de `jca`, chaveado por digest das linhas alteradas: 12 `allow-list`, 51 `layer-2-repair`, 42 `predicate-graph`, 1 `cipher-import`. Script/checagem: `SCRIPTS/gh101_divergence_record.py` (`--check` falha em hunk sem entrada e em entrada sem hunk) |
| Freeze check | `tests/parity/test_gh101_specset_gates.py::test_frozen_paths_byte_identical_to_base_commit` (+ `::test_frozen_set_predicate_inventory_matches_baseline`) | sim | teste pytest (gate) | `git diff 7e7acb69 -- MOP/jca CipherTransformationUtil.java` vazio; baseline hardcoded de propósito ("um freeze cuja baseline se move não é um freeze"). **Não é um script avulso** — mora no gate de testes; skip se `RVSEC_HOME` ausente |
| Write/read guard | `SCRIPTS/gh101_predicate_pairing_check.py` + gate `::test_every_written_constant_is_read_or_recorded` | sim | script + gate | Recomputa o pareamento dos `.mop` (não confia no CSV commitado; falha se o inventário estiver stale); 3 classes de falha: escrito-nunca-lido-não-registrado, **lido-nunca-escrito** (a armadilha de falso positivo do D-S14, além do texto do INV-INS-111), e registro que deixou de ser verdade. Saída alegada: 25 constantes escritas, 14 lidas, 11 registradas |
| Transition check (INV-INS-110) | `SCRIPTS/gh101_monitor_transition_check.py` | sim | script sobre o monitor **gerado** | Nenhum evento com linha de transição all-`fail`; lê os dois tipos de monitor (`AbstractAtomicMonitor` **e** `AbstractSynchronizedMonitor` — a versão que lia só o primeiro tipo passava no conjunto sabidamente defeituoso, e foi por isso corrigida). Rodado contra o congelado primeiro, onde a resposta conhecida é 18 |
| Divergence/conformance gates | `tests/parity/test_gh101_specset_gates.py` (5 testes) | sim | pytest | INV-INS-109(a), 109(b), 111, 113. **INV-INS-110 e 115 não têm gate em pytest** — só o script manual e os números registrados em prosa |

Registros em prosa: `DATA/README.md` (narrativa mestra dos sete CSVs, com os
números pós-reparo) e `DATA/frozen_set_debt.md` (dívida do conjunto congelado,
ver §5), mais `DATA/algorithm_naming.md` (lacuna caso/grafia/alias, aberta).

**Evidência do Grupo 8** (verificação empírica pós-GH100): diretórios
`results/gh101_group8_jca_android/` e `results/gh101_group8_jca_frozen_control/`
(4 APKs, dois braços, monkey 180 s), com a medição narrada em
`frozen_set_debt.md` §"What Group 8 measured".

### Alegações sem artefato dedicado localizável

1. **Saída commitada do transition check**: os "18 eventos all-fail no congelado"
   e o "0 no derivado" existem como alegação em prosa
   (`frozen_set_debt.md`, `tasks.md` 3b.10) e como script re-executável, mas
   nenhum arquivo de saída da execução foi encontrado em `DATA/` ou
   `evidence/`. Reprodução obrigatória na fase seguinte.
2. **"Replication package"** (tarefa 7.5: "Record in the replication package
   that the published numbers reproduce exactly…"): não existe pacote de
   replicação nomeado; o conteúdo aterrissou como as consequências 1–3 do
   cabeçalho de `frozen_set_debt.md` (e tarefas 7.6/7.7 idem). Interpretação, não
   localização direta.
3. **Números do INV-INS-115** (teto de 17 eventos, `n × (2ⁿ − 1)`, 53 s/3,3 GB,
   `StackOverflowError` a 18): registrados em prosa com comandos de reprodução
   (`DATA/README.md`) e harnesses em `.claude/skills/rv-analyze-spec/` (commit
   `3d093592`); sem saída bruta commitada.
4. Tarefas de processo do Grupo 9 (9.1 build do reator, 9.4–9.7 lint/verify/
   review/docs-sync) estão `[x]` sem artefato apontado nos arquivos da change;
   rastros possíveis nos handoffs `docs/2026080*_handoff_gh101_sessao*.md` (não
   auditados nesta fase).

---

## 3. Decisões D-S9 a D-S14 (numeração real confirmada)

A numeração real em `design.md` é: D-S0–D-S5, D-S7, D-S8, D-S9–D-S14 e, **fora de
ordem no arquivo, D-S6 aparece por último** (após D-S14; é a decisão de deixar a
verificação empírica para o fim, dependente da GH100). Não existe D-S6 na posição
sequencial. Os itens pedidos pela auditoria mapeiam assim: reparo all-fail = D-S9;
resíduo que desloca acusação = parágrafo interno de D-S9 + tarefa 3b.11b (não é
decisão numerada própria); remoção de `MessageDigest.reset` = parágrafo interno de
D-S9; orçamento de Cipher = D-S11 + D-S12; `!macced` = D-S13; edges abertos =
D-S14; constraints fora de escopo = tarefa 4.11 (registrada dentro de D-S11).
D-S10 (store por identidade) está no intervalo e é incluída.

### D-S9 — "all eighteen all-`fail` events are repaired, not only the two that were visible"

Specs afetadas: as 10 — `TrustManagerFactorySpec`, `SSLContextSpec` (Grupo 3) e
`IvParameterSpecSpec.c3/c4`, `KeyPairGeneratorSpec.initError`,
`MessageDigestSpec.reset`, `PBEKeySpecSpec.f1/f2/err1/err2/err3`,
`PBEParameterSpecSpec.c3`, `SecretKeySpecSpec.c3/c4`,
`SecureRandomSpec.c3/g4/setSeed3`, `SignatureSpec.g3` (Grupo 3b).

> "**Decision: repair all sixteen, in the derived set, as Group 3b.** The repair
> is not new work — it is the `unsafeAlg` idiom Group 3 already established,
> applied sixteen more times […] **INV-INS-110 is not weakened.**"

Forma do reparo: prefixo de Kleene no ramo violador para os 14 em `ere`
("Fourteen take the Kleene prefix the set already uses for a violating branch,
three take rows in the `fsm` `SecureRandomSpec` already has"), com a alternativa
(estado absorvente) **rejeitada** por ser mais estrita que o reparo do Grupo 3 e
por trocar falso positivo por falso negativo.

**O resíduo (deslocamento da acusação)** — texto exato:

> "What this leaves standing is a residue, and it is recorded rather than
> repaired: in every specification of the set, the state reached by a violating
> branch does not admit the calls that legitimately follow it, so the accusation
> is removed from the violating call itself and reappears one call later."

Set-wide, pré-existente, registrado em `frozen_set_debt.md` (tarefa 3b.11b) — o
Grupo 3b "does not widen it and does not narrow it". Afeta 13 especificações.

**Remoção de `MessageDigestSpec.reset`** — texto exato:

> "**`MessageDigestSpec.reset` is removed rather than placed.** It is the one of
> the sixteen that is not a violating branch. No generated rule models it:
> `MessageDigest.cryptsl` for API 30 declares `getInstance`, `update` and
> `digest` and nothing else […] Removing the event restores exactly the
> generated rule's behaviour, and it is entered in the divergence record as a
> removal with the rule as its reason."

Contexto quantitativo (do proposal, restado no design): os 10 arquivos portadores
dos 18 eventos respondem por 49.817 de 70.760 `InvalidSequenceOfMethodCalls`
(70,4% da categoria; 51,3% dos 97.018 erros publicados) — declarado
explicitamente como **teto do explicável, não medição do causado** (o `@fail` não
nomeia o evento gatilho).

### D-S10 — "the predicate store is keyed by identity, in the shared class"

Spec afetada: nenhuma diretamente — `ExecutionContext.java` em `rvsec-core`,
compartilhado pelos **dois** conjuntos (efeito enumerado sobre 8 dos 27 reads do
congelado). Mais o reparo dos 4 `remove(Property)` de um argumento, esse sim
confinado ao derivado (`KeyManagerFactorySpec:91`, `MacSpec:87`,
`TrustManagerFactorySpec:117-118`).

> "**Decision: re-key `ExecutionContext` by identity, in the shared class.**"
> "**This is not a deviation from D-S0.** D-S0 freezes the specification set —
> the `.mop` content and the transformation tables the frozen `CipherSpec` calls
> — […] It does not freeze the runtime the instrument executes on."
> "The criterion it should state is the one it was actually protecting: **shared
> code MUST NOT branch on the active specification set.**"
> "**A blind spot this exposes, named rather than closed.** […] Byte-identity of
> the frozen paths and of the generated monitor therefore does not establish
> that the frozen set *behaves* as it did."

Atenção da auditoria: a tabela de D-S10 no design está **corrigida em
`DATA/README.md`** — os seed reads de `SecureRandomSpec` são sobre `byte[]` (não
`long` boxed) e portanto **não** mudam de resposta; a composição correta dos 8 é
3×`CipherSpec.i2`, `MacSpec.i1`, `MacSpec.i2`, `SecretKeySpec.e1`,
`RandomStringPasswordSpec.gb` e `.vo`. O design **não foi atualizado** com a
correção (contradição interna documentada pelo próprio README: "The count of 8 is
right; the composition was not"). Direção alegada uniforme: reportar **mais**.

### D-S11 — "event granularity follows the rule's bindings, not its signatures"

Specs afetadas: `CipherSpec` (17→**14** eventos; a transcrição literal precisaria
de 24 e "cannot be built"), `KeyGeneratorSpec` (init 1→5), `KeyManagerFactorySpec`
(init 1→2), `TrustManagerFactorySpec` (init 1→2, retrofit da 3.1).

> "**Decision: one event per distinct binding profile, not one event per rule
> signature.** An event earns a place in a specification's alphabet when it
> carries a binding or a body no other event carries."
> "**The ceiling is 17 events, and `CipherSpec` is already standing on it.**"
> "**What this costs, stated plainly, because the earlier decision rejected
> it.** Discrimination between overloads moves out of the pointcut and into an
> `instanceof` in the event body […] what is lost is a static guarantee about
> *which* overload was called, not any clause of the rule."

É uma **revisão declarada** ("This is a revision. The decision first written here
was to transcribe 1:1 with the rule"). Registra também que o evento arity-3 de
init cobre membros de `IWOIV` **e** `IWIV`, o que `noCallTo(IWOIV)` exigiria
recuperar via o mesmo `instanceof`. Dois defeitos fechados de graça: o disparo
duplo `f1`+`f2` para `doFinal()` (com `f4` sem evento próprio) e
`getInstance(String, provider)` que não disparava nada.

**Constraints fora de escopo (tarefa 4.11, registrada em `DATA/README.md`)**:
`noCallTo(IWOIV)` e `callTo(iv)` do `Cipher` (a segunda exigiria evento `getIV()`
inexistente), e `neverTypeOf(password, java.lang.String)` de `KeyManagerFactory`,
`KeyStore` (×3) **e `PBEKeySpec`** — este último ausente da enumeração da tarefa,
apontado pelo próprio README ("this one is **not** in the task's enumeration,
which named two rules and not three"). São `CONSTRAINTS`, não arestas do grafo.

### D-S12 — "the generator is not repaired; the alphabet is budgeted against its ceiling"

Spec afetada: nenhuma — decisão sobre `rv-monitor` (não tocá-lo) e sobre INV-INS-115.

> "**Decision: do not repair `rv-monitor`.** It is out of this change's scope, it
> would raise the ceiling only to roughly 20 events — still short of the 24 a
> literal transcription needs, since the `String` limit is a separate wall — and
> it enlarges the blast radius of a change whose whole discipline is that the
> frozen set's instrument does not move."

Números: `n × (2ⁿ − 1)` coenable sets exatos a 17 (2.228.207) e 18 (4.718.574);
53 s/3,3 GB a 17; `StackOverflowError` em `EnableSet.parseSets` a 18; ~1,5×10¹⁰
caracteres a 24 (> `String` máximo). `ere`/`ltl`/`ptltl` reescritos em `fsm`,
mesmo `FSMCoenables`. Harnesses: `CoenableProbe` e `PointcutBudget` em
`.claude/skills/rv-analyze-spec/`.

### D-S13 — "`!macced[_, plainText]` is transcribed, and the projection is faithful"

Specs afetadas: `MacSpec` (escreve `MACED`; 8→11 eventos para bindar os pontos de
entrada de dados) e `CipherSpec` (lê em `f2`/`f5`). Constante nova: `MACED`.

> "**Decision: transcribe it.** A new `Property` over the MACed data, written
> where the data enters `MacSpec` and read in `CipherSpec`."
> "**The projection is faithful, which is why this is a transcription rather
> than an approximation.** The clause's first place is anonymous, so the
> one-place projection onto the *second* argument is exactly what it asks for."
> "**Two residues, recorded rather than mitigated.** `Mac.update(java.nio.ByteBuffer)`
> is not among the rule's events, so data entering through it is never marked
> […] a false negative. And `update(byte)` marks a boxed primitive […] one MACed
> byte marks every equal literal in the process."

Decisão do usuário em 2026-08-07, com duas alternativas declinadas e registradas
(inexprimível; ou ler `!validate(GENERATED_MAC, plainText)`, que enuncia "do not
encrypt a MAC" — cláusula diferente).

### D-S14 — "Group 5 adds one constant; the rest of its bucket is recorded"

Specs afetadas: `CipherSpec` (escreve `GENERATED_CIPHER`),
`CipherInputStreamSpec` e `CipherOutputStreamSpec` (leem). Constante nova:
`GENERATED_CIPHER`.

> "One is fully expressible: **`generatedCipher`**, produced by `Cipher` and
> required by both stream rules, all three modelled here. **Decision: Group 5
> adds `GENERATED_CIPHER` alone**, and the remaining eight predicates are
> recorded with the mechanical reason above."
> "**This reopens task 4.3's deliberate omission, and must** […] the `ENSURES`
> becomes a real write of `GENERATED_CIPHER` and task 4.3's record keeps only
> `generatedMessageDigest`."

Critério: fechável ⟺ produtor **e** consumidores da aresta têm `.mop` neste
conjunto de 23. Seis predicados sem produtor (leitor reportaria em toda execução
— "not a recorded gap; it is a new defect of the same family this change exists
to remove"); dois sem consumidor em regra alguma (write sem leitor). Detalhe de
âncora registrado: **nenhuma** regra API 30 nomeia `generatedCipher` — a adição é
ancorada no CrySL 1.5.2, com o fato registrado em `DATA/README.md`.

### D-S6 (fora de ordem) — verificação empírica por último, sem relaxamento

> "**Decision: place that verification in the final task group**, and if #100
> has not landed, record the task as blocked citing the artefact rather than
> substituting a weaker check."

---

## 4. Dependência GH100 → GH101

**O que a GH101 assume da GH100 — uma coisa só, declarada nos dois lados:**

- GH101 `proposal.md`: "**Depends on** issue #100, for one thing only: the
  empirical verification of `TrustManagerFactorySpec` and `SSLContextSpec` needs
  the wrapper-collision fix (its task 5.3) integrated […] Every other part of
  this change is independent of #100 and does not wait for it."
- GH100 `tasks.md` 5.3 `[x]`: o reparo real foi o **merge de wrappers** (a chave
  não podia ser alargada); "**Issue #101 depends on this task**"; GH100 7.7 `[x]`
  notificou a GH101.

**Tarefas da GH101 que dependiam de validação empírica pós-GH100: 8.1 e 8.2**
(Grupo 8, D-S6). Ambas `[x]`, com evidência apontada:

- Commit citado do reparo: `48b57fc5` ("every emission path emits every monitor
  call" — visível no log recente do branch).
- Artefatos: `results/gh101_group8_jca_android/` e
  `results/gh101_group8_jca_frozen_control/` (4 APKs escolhidos do próprio
  `errors.csv` da campanha; dois braços idênticos exceto o conjunto de specs;
  monkey, 180 s, 1 repetição — lido como **forma de mensagem em sítio nomeado**,
  não como taxa).
- Registro narrado: `DATA/frozen_set_debt.md` §"What Group 8 measured".

**Resultado registrado do Grupo 8 — com uma correção de atribuição relevante
para a auditoria**: 8.2 confirmada por observável diferente do previsto — o
allow-list corrigido aparece (`expecting one of PKIX` vs `PKIX,SunX509` no mesmo
sítio). Já 8.1 **falsificou uma atribuição que a própria change vinha
registrando desde o Grupo 3**: o rótulo vazio (`but found .`; 8.371 + 51 eventos
na campanha) não vinha do defeito de binding das specs, e sim da colisão de
wrapper do weaver — o rótulo vazio sumiu **também no braço congelado**. O defeito
de binding é real, mas seu custo é outro (valor do *último* factory vivo, visível
só com dois factories vivos). A distribuição da campanha fecha sem resto sob essa
explicação.

Além da dependência declarada, há um **acoplamento operacional** registrado dos
dois lados: a GH100 pinou descritor e fontes de monitores para V2 (task 4.3,
`evidence/v2_pinned_inputs.md`) precisamente porque a GH101 editava os `.mop` em
paralelo; e a GH101 9.1 coordena o build do reator compartilhado com a sessão
gh100. A GH100 usa o conjunto `jca_android` (pinado em 2026-08-06, pré-edições)
para V2, e o descritor `jca` congelado para o censo — declarando que "neither is
the other's baseline".

---

## 5. Omissões e divergências declaradas — lista integral

### 5.1 `DATA/predicate_omissions.csv` — 20 entradas

**Kind `constant-write-no-read` (11)** — constante existe, é escrita, sem leitor:

| Constante | Spec(s) que escrevem | Razão declarada (síntese; cláusula CrySL citada no CSV) |
|---|---|---|
| `DIGESTED` | MessageDigestSpec | Terminal: `digested[out,…]` ensured nos dois anchors, nenhum rule REQUIRES |
| `GENERATED_KEY_PAIR` | KeyPairGeneratorSpec; KeyPairSpec | Terminal: consumidores pedem as metades (`generatedPrivkey`/`generatedPubkey`), ambas lidas |
| `GENERATED_MAC` | MacSpec | Primeiro lugar de `macced[M,D]`; o único consumidor (`!macced[_, plainText]`) deixa esse lugar anônimo — `MACED` carrega o segundo (D-S13) |
| `GENERATED_TRUST_MANAGER` | TrustManagerFactorySpec | API 30 ensures do factory e do array; SSLContext requer só o array (`GENERATED_TRUST_MANAGERS`) |
| `GENERATE_SSL_CONTEXT` | SSLContextSpec | Terminal: nada consome um SSLContext configurado |
| `GENERATE_SSL_ENGINE` | SSLContextSpec | Terminal |
| `PREPARED_PBE` | PBEParameterSpecSpec | Consumidor (`AlgorithmParameters`, 1.5.2) não tem `.mop` aqui; API 30 dropa o REQUIRES |
| `SIGNED` | SignatureSpec | Terminal |
| `SPECCED_KEY` | PBEKeySpecSpec; SecretKeySpecSpec | Consumidores (`SecretKeyFactory`, `KeyFactory`) sem `.mop` aqui |
| `VERIFIED` | SignatureSpec | Terminal |
| `WRAPPED_KEY` | CipherSpec | `wrappedKey` sem consumidor em anchor algum; API 30 dropa até o ENSURES |

**Kind `predicate-no-constant` (9)** — nenhuma constante adicionada:

| Predicado | Produtor ausente / razão |
|---|---|
| `preparedAlg` | `AlgorithmParameters` sem `.mop` (leitor reportaria em toda execução — D-S14) |
| `preparedRSA` | `RSAKeyGenParameterSpec` sem `.mop` |
| `preparedDSA` | `DSAGenParameterSpec` sem `.mop` |
| `generatedManagerFactoryParameters` | `CertPathTrustManagerParameters`/`KeyStoreBuilderParameters` sem `.mop` (2 arestas) |
| `preparedEC` | `ECGenParameterSpec` sem `.mop` e sem regra API 30 |
| `preparedOAEP` | `OAEPParameterSpec` sem `.mop` e sem regra API 30 — âncora irrelevante |
| `cipheredInputStream` | Produzido aqui, **sem consumidor em regra alguma** dos dois anchors |
| `cipheredOutputStream` | Idem |
| `generatedMessageDigest` | Consumidores (`DigestInputStream`/`DigestOutputStream`) sem `.mop`; fica com o marcador accepting-state, **inerte** (19 escritas, 0 leitores de `isInAcceptingState` em qualquer conjunto) — tarefa 4.3 |

Saldo declarado: dos 11 edges do bucket capability-absent, **2 fechados
(`generatedCipher` ×2 REQUIRES) e 9 abertos e atribuíveis**; o terceiro edge de
`generatedCipher` (o ENSURES) veio do bucket de omissão deliberada reaberto.
Fechar os 6 sem produtor exigiria **7 especificações novas** — nomeada como
change própria.

**Inexprimível (1, tarefa 4.4)**: `randomized[lSeed]` — proveniência sobre
primitivo; sob identidade falha nas duas direções conforme a magnitude (cache de
`Long`), e um terceiro fato o fecha independentemente: a spec nunca marca um
`long` (as escritas primitivas são sobre `int`). Unsoundness residual da escrita
confinada ao cache de `Integer`, direção **sub-reporte**.

### 5.2 `DATA/divergence_record.csv` — divergências jca ↔ jca_android

106 hunks, cada um com digest, kind, razão e tarefa: 12 `allow-list`
(pré-existentes, a derivação agindo como pode), 51 `layer-2-repair`, 42
`predicate-graph`, 1 `cipher-import`. Os 94 não-allow-list são os reparos
confinados ao derivado — a razão de ser do D-S7.

### 5.3 `DATA/frozen_set_debt.md` — o que o `jca` congelado retém, sabendo

1. Tabelas de Cipher: cobertura de 2 famílias contra 8 da regra; auto-contradição
   com `KeyGeneratorSpec` (ChaCha20/DESede/BLOWFISH/ARC4); rejeita `AES/ECB`;
   2 defeitos de higiene (`PKCS5PADDING` duplicado; bloco `rsaECBPaddings`
   comentado) — tarefa 2.7.
2. Os **18 eventos acusadores incondicionais**, com a tabela de 70,4%/51,3% lida
   como teto — tarefas 3.5 e 3b.11.
3. O **resíduo dos dois conjuntos** (acusação deslocada uma chamada adiante, 13
   especificações, sem issue aberta — decisão do usuário) — tarefa 3b.11b.
4. A medição do Grupo 8 com a **correção da atribuição do rótulo vazio** (§4).
5. As três consequências de leitura obrigatória (reproduzível ≠ correto; os dois
   conjuntos confundem allow-list com reparo; perfil derivado modela
   **disponibilidade, não recomendação** — `MD5`/`SHA-1` admitidos).

Questões deixadas **abertas ao usuário** (design "Open Questions" + README):
variantes de grafia/aliases da tradução de 2022 (verdito por grupo pendente);
desvios deliberados do upstream (OAEP com MD5; `NoPadding`/`PKCS1Padding` para
RSA); e `algorithm_naming.md` com dois gaps de regra.

---

## 6. Lacunas, contradições internas e pontos de atenção

1. **GH100 não está 100%**: 7.4 duplicada (`[x]` e `[ ]` simultâneos), 7.5 e 7.6
   abertas. A GH101 declarou-se completa (84/84) **dependendo de uma change que
   ainda tem tarefas de verificação abertas** — nada disso toca a task 5.3, que
   está `[x]` com commit nomeado, mas o estado formal é esse.
2. **Colisão de numeração de invariantes entre os dois deltas**: o delta
   `instrumentation` da GH100 define **INV-INS-109** (chave do oráculo L3 =
   `(apk, class, method, spec)`) e **INV-INS-110** (parser lê o formato do
   `ErrorCollector`); o delta `instrumentation` da GH101 define **INV-INS-109**
   (freeze + enumeração) e **INV-INS-110** (pertinência do evento ao autômato)
   com conteúdos completamente diferentes. As duas changes modificam a mesma
   capability; no sync/arquivamento, uma das numerações terá de ceder. Hoje,
   qualquer citação nua de "INV-INS-109/110" é ambígua.
3. **D-S10 com composição desatualizada**: o design ainda lista os seed reads de
   `SecureRandomSpec` como afetados (boxed `long`); `DATA/README.md` corrige
   (são `byte[]`, inafetados; entra `RandomStringPasswordSpec.vo` sobre
   `Object`). A contagem 8 se sustenta; a composição do design, não.
4. **Proposal desatualizado quanto às constantes**: o proposal fala em "one new
   `Property` constant" (`generatedCipher`) e não menciona `MACED`/D-S13 nem o
   re-orçamento 17→14 do `CipherSpec` (D-S11 revisado); o design e a API Design
   dizem **2 constantes** (23→25). O design é o artefato mais atual; o proposal
   ficou para trás nesses dois pontos.
5. **INV-INS-110 e INV-INS-115 sem gate automatizado**: os cinco gates de
   `test_gh101_specset_gates.py` cobrem 109(a), 109(b), 111 e 113; a checagem de
   transição e o teto do gerador dependem de execução manual do script/harness.
   A alegação "frozen = 18, derived = 0" não tem saída commitada.
6. **Rótulo vazio: atribuição corrigida tardiamente** — registros anteriores da
   própria change (Grupo 3, e a prosa que motivou o proposal) atribuíam o
   `but found .` ao defeito de binding; o Grupo 8 mediu e corrigiu (era a colisão
   de wrapper, GH100). Exemplo concreto, dentro da própria change, de alegação
   `[x]` que só a medição desfez — reforça o protocolo da auditoria.
7. **Terminologia do conformance record**: o contrato de dados do delta fala
   `adapted / verbatim-uncontradicted / no-anchor`; o CSV usa
   `anchored / uncontradicted / no-anchor`. Deriva menor, sem efeito, mas é o
   tipo de deslize que um verificador textual pegaria.
8. **`neverTypeOf` de `PBEKeySpec`** fora da enumeração da tarefa 4.11 (que
   nomeou duas regras, não três) — corrigido só no README.
9. **A âncora dupla é decisão, não acidente**: allow-lists conferidas contra API
   30; grafo de predicados conferido contra CrySL 1.5.2. `generatedCipher` não
   existe em regra API 30 alguma — a adição se sustenta apenas sob a âncora
   1.5.2, com o fato registrado. A auditoria da Fase seguinte precisa tratar as
   duas âncoras como oráculos distintos, como a change fez.
10. **O freeze é byte-a-byte, não comportamental** — dito pela própria change
    (D-S10, INV-INS-109, tarefa 4b.4): o re-chaveamento por identidade muda o que
    o conjunto congelado **reporta** (8 reads) com todos os checks mecânicos
    passando. Qualquer comparação futura com os números publicados tem de saber
    que o runtime mudou por baixo (GH100 idem, pelo weaver).

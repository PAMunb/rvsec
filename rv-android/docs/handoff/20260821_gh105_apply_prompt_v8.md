# Handoff — aplicação da change gh105-predicate-wiring (checkpoint 29/74, o Grupo 4 em marcha)

**Data**: 2026-08-21 · **Branch**: `modules` · **Último commit**: `a9d8f2bd`
**Progresso**: 29 de 74 tarefas (Grupos 1, 2 e 3 inteiros; 4.1 a 4.4 fechadas)
**Estado da árvore**: verde — 94 asserções nas quatro suítes de gates passam.
**Predecessor deste documento**: `docs/handoff/20260821_gh105_apply_prompt_v7.md` (checkpoint 28/74).

---

## O que estamos fazendo

Aplicando a change **gh105-predicate-wiring** (GitHub issue #105) pelo workflow OpenSpec.
A change fia as predicates CrySL (`ENSURES`/`REQUIRES`/`NEGATES`) no conjunto `jca_android`,
que não as fiava: das 19 predicates conectáveis contra as 33 regras api30, o conjunto realizava
3 elos; as leituras de predicate viviam dentro de `condition(...)`, onde uma guarda falsa
suprime a transição e converte "origem de chave não modelada" num `InvalidSequenceOfMethodCalls`
errado; e os acusadores órfãos sustentavam no máximo 39.682 eventos = 56,1 % daquela categoria
publicada (teto medido sobre a campanha `jca`, não atribuição causal).

O gh104 fez o handler `@fail` falar. Esta change faz ele parar de disparar quando não deve.
O Grupo 3 fechou essa segunda metade para os 17 acusadores órfãos; a 4.3 provou que o mecanismo
chega ao dispositivo e liberou o Grupo 5; o Grupo 4 está migrando o conjunto arquivo por arquivo.

### REGRA NÃO NEGOCIÁVEL DE WORKFLOW

Seguir `docs/WORKFLOW.md` rigorosamente. **NUNCA** escrever ou reescrever artefatos OpenSpec
com `Write`/`Edit` — invocar as skills (`openspec-apply-change`, `openspec-update-change`)
pela ferramenta `Skill`. A única edição manual permitida em `tasks.md` é marcar `- [ ]` →
`- [x]` imediatamente ao concluir cada tarefa, antes de começar a próxima.

Commits **nunca** levam `Co-Authored-By` nem trailer de coautoria. Mensagens em português com
acentuação correta, no estilo narrativo dos commits recentes (explicam *por quê*). Sufixo
`refs #105`; `closes #105` só no commit final.

**Emuladores**: nunca iniciar, parar ou gerenciar emulador manualmente. O rv-platform gerencia
o ciclo de vida inteiro. Vale para a 8.5, a única tarefa de dispositivo que resta.

**Decisões de projeto vão ao pesquisador antes de editar.** A 4.1 tinha três, a 4.3 tinha três,
a 4.4 tinha duas; as oito foram levadas em opções com recomendação **e medição**, e as oito
recomendações foram ratificadas. Faça o mesmo — e leve **medição** junto com a opção, não só
argumento. Se a medição disser que duas opções são indistinguíveis, diga isso: é o que faz a
escolha ser preservação literal em vez de mudança comportamental disfarçada.

**Não derive projeto do conjunto reprovado.** `jca_android_bug_predicate` foi reprovado 22/22 pela
auditoria de 2026-08-08 e está arquivado como *registro*, nunca como semente (design, Constraints).
Ele aparece legitimamente em duas situações e só nelas: os gates rodam sobre o universo enumerado
inteiro (INV-INS-140), e um `grep` de medição sobre os cinco conjuntos pode acertá-lo. Quando
acertar, **diga que acertou e por que não conta** — foi exatamente essa a correção que o
pesquisador cobrou na 4.4, e ela pegou uma afirmação factualmente errada no
`divergence_record.csv` antes do commit.

**Vocabulário.** Neste projeto "especificação" é o objeto formal (`.mop`/`.rvm`, autômato
paramétrico, monitor tecido), avaliado pela eficácia empírica em achar defeitos no sentido de
Legunsen et al. (ASE'16), de quem o artigo do próprio grupo é continuação. A seção 3 do
`WORKFLOW.md` cita literatura de *spec-driven development* assistido por IA, onde "spec" é o
documento de requisitos que precede a geração de código — **não é o sentido em uso aqui**. O
`WORKFLOW.md` é autoridade sobre cerimônia de trilha, não sobre o que uma especificação é.

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
openspec validate gh105-predicate-wiring          # note: `validate` NÃO aceita --change
```

E, além dos artefatos, **leia antes de tocar em qualquer arquivo do Grupo 4**:
`data/gh105/evidence/f2-CipherSpec.md` (4.1/4.2), `data/gh105/evidence/f2-reach-probe.md` (4.3)
e `data/gh105/evidence/f2-IvParameterSpec.md` (4.4) — as três formas que uma passagem de arquivo
pode ter: a que move tudo, a que vai ao dispositivo, e a que não move sítio nenhum.

---

## O que foi feito

### Grupo 1 — substrato (rvsec-core) — 6/6, commit `b55a61a2`

`PredicateVerdict`, `PredicateStore` (chave de identidade fraca com `ReferenceQueue`, posições
`String`/`int`/`Integer` sem distinguir caixa, aridade N, `ensure/validate(Property, Object
bound, Object... values)`, `negate`, `validateAbsent`, `reset`), 19 testes JUnit, reset do
substrato no `TraceRunner.replay()`, `ExecutionContext.java` byte-idêntico em `FROZEN_PATHS`,
`Property` append-only.

**Decisão ainda a confirmar com o pesquisador**: `bound == null` é tolerado (no-op /
`NOT_OBSERVED` / `SATISFIED`) em vez de lançar, porque uma NPE dentro de advice tecido derruba a
app sob teste. Documentado no javadoc. A 4.4 já se apoiou nessa tolerância (o `@match` do
`IvParameterSpec` chama `ensure` sem guarda de nulo) — se a decisão mudar, aquele sítio muda junto.

### Grupo 2 — camada de gates — 12/12, commits `acec89ea` a `25cfc590`

`scripts/gh105_predicate_graph.py`, `gh105_param_gate.py`, `gate_import` (INV-INS-130), reescopo
do G-PRED, `data/jca_android/order_alphabet_map.csv`, `gh105_order_gate.py`,
`gh105_gate_baseline.py` + `gate_baseline.json` + `evidence/gate_baseline_report.md`, pré-imagem
em `backup/gh105-preimage/jca_android/`, `/rv-doc-code` nos três scripts.

### Grupo 3 — os 17 órfãos — 7/7, fechado (`25cfc590` … `8fdf73fd`)

12 gêmeos negados fundidos + `PBEKeySpecSpec.err1` + 4 absorções. G-ACC verde nas duas direções,
17 linhas aposentadas da baseline. **O ledger completo, uma linha por órfão com tratamento,
tarefa, trace e medição, está em `data/gh105/evidence/f1-group-three-the-seventeen.md`.**

### Grupo 4 — 4.1 + 4.2, um commit atômico (`d71c8e64`)

`CipherSpec` é o primeiro arquivo migrado, e o mais difícil: 17/17 eventos (headroom zero),
3 leituras, 12 escritas, 1 chamada de estado de aceitação. A tricotomia de origem de chave do
`i2` sai de `condition(...)` para o corpo como **um** sítio composto com veredito de três valores
(`CIPHER-CONSTR-00` para `VIOLATED`, `CIPHER-NOBS-00` para `NOT_OBSERVED`); onze escritas de
`ENCRYPTED` sobem para os **dois** pontos de aceitação (`alias match2 = s3` e o `match1`
existente); a décima segunda, `WRAPPED_KEY`, foi apagada. A 4.2 acrescentou a família `NOBS` ao
`codes.csv` e uma quinta propriedade ao `gh104_message_gate.py`.

Evidência com a tabela de contagem exata dos dois lados: **`data/gh105/evidence/f2-CipherSpec.md`**.

### 4.3 — a sonda de alcance, commit `4881b557`

**Veredito: a change NÃO está bloqueada. O Grupo 5 está liberado. O weaver não é pré-requisito.**

O veredito foi construído em três camadas, porque "não chegou" esconde três defeitos diferentes
e só o primeiro bloqueia:

| camada | pergunta | oráculo | resultado |
|---|---|---|---|
| **L1** | a leitura está no APK entregue? | `dexdump` sobre o APK instrumentado | ✅ `PredicateStore` + as 5 classes internas + `PredicateVerdict` em `classes7.dex`; **14 sítios de `Cipher.init(int,Key,..)` → 14 invocações de `CipherSpec_i2Event`**, um para um; `CIPHER-NOBS-00` no dex e no `.rvm` |
| **L2** | o sítio executou? | `RVSEC-COV` no logcat | ✅ `CipherUtil.des`, `encryptWithSecretKey`, `executeHmacOperation` |
| **L3** | o relato chegou ao CSV? | `errors.csv` | ✅ **3 linhas `code=CIPHER-NOBS-00 ev=i2`**, colunas `code` e `event` preenchidas pelo envelope do gh104 |

Foram **duas** execuções, e a primeira é evidência de método: `ape` 60 s deu L1 verde e **L2
vermelho** (o APE apertou executar com os campos vazios e o `validateInputs()` recusou) — **sonda
inconclusiva, que é leitura diferente de change bloqueada**; `aperv:sata_mop` 300 s alcançou.

Evidência completa: **`data/gh105/evidence/f2-reach-probe.md`**; artefatos pequenos dos dois runs
em `data/gh105/evidence/reach-probe/` (`results/` é ignorado pelo git).

### 4.4 — `IvParameterSpec`, commit `a9d8f2bd` — a passagem que não move sítio nenhum

Primeira passagem do Grupo 4 em que **o censo de colocação não se mexe**. A 3.3 já tinha trazido
as duas leituras para o corpo ao fundir os gêmeos, e `preparedIV[this]` não tem qualificação
`after L`, então o ponto de aceitação da regra é o estado de aceitação e a escrita já estava no
`@match`. O que sobrou para a F2 é o que o censo não enxerga: substrato, veredito de três valores,
escrituração de estado de aceitação fora.

Quatro códigos onde havia dois: um código nomeia um **sítio**, não uma cláusula (o `codes.csv` é
chaveado por evento e linha), então `IVPARAMETERSPEC-{CONSTR,NOBS}-00` são do `c1` e `-01` do `c2`.

Evidência: **`data/gh105/evidence/f2-IvParameterSpec.md`**.

---

## Decisões ratificadas pelo pesquisador (2026-08-21)

### Na 4.1

1. **As escritas de `ENSURES` aterrissam em handler de estado**, não no corpo com razão
   registrada. O custo que o plano atribuía a essa forma — "vence o último par" — **foi medido e
   não existe**: o despachante recomputa a categoria de estado depois de *todo* evento e chama o
   handler sempre que ela vale.
2. **A escrita sem cláusula é apagada, não registrada como omissão.** `WRAPPED_KEY` não traduz
   cláusula nenhuma. `Property.WRAPPED_KEY` fica no enum — INV-INS-132 é append-only.
3. **Aridade 2 com `null`** onde o pointcut não liga o texto claro (`f1`,`f2`,`f3`), em vez de
   estreitar para aridade 1 — que arquivaria uma predicate sob duas formas.

### Na 4.3

4. **APK e driver**: `cryptoapp.apk` com `ape` 60 s como primeira tentativa, escalando para
   `aperv:sata_mop` 300 s. O `monkey` foi **medido não alcançar** — em 600 s só produz
   `SSLContextSpec`/`TrustManagerFactorySpec`, do okhttp na inicialização.
5. **Veredito em três camadas**, com oráculo e desfecho próprios por camada.
6. **Build do reator rodado assim mesmo**, embora a medição dissesse que o jar instalado já
   bastava. Seguro barato: o veredito da sonda decidia o destino da change.

### Na 4.4

7. **`NOT_OBSERVED` não prepara.** A semente ligava `spec` só no `else` de um booleano; com três
   valores esse ramo se divide, e a alternativa (deixar o não observado preparar, para que um
   limite de alcance custe um relato em vez de cascatear num segundo) tem o D-4 a favor. Medido
   antes de escolher: **as duas são indistinguíveis** — nenhuma especificação viva lê
   `PREPARED_IV`, e o leitor planejado (ledger #9) é um junction, que consulta o monitor
   paramétrico e não o store. Escolha: **preservação literal**, com a alternativa registrada no
   comentário do `.mop` e no `divergence_record.csv`. *Mudança comportamental sem medição que a
   decida não entra em migração de substrato.*
8. **O grafo descreve o artefato, não o plano.** As linhas do `c1`/`c2` no `predicate_graph.csv`
   levam `mechanism=store` porque é o que o código faz; a escolha de mecanismo da aresta #12 é da
   5.1, e a colisão foi registrada na evidência endereçada a ela.

---

## Achados que valem mais que as tarefas

### Continuam valendo

1. **O sumidouro `unsafeAlg` do `CipherSpec`** — `g3` leva a um estado cujas únicas saídas são
   outros `getInstance`, então qualquer chamada legítima seguinte tira `CIPHER-ORDER-00` sobre uma
   ordenação que a regra **aceita**. Está no `fsm`, então o G-ACC não o vê e nenhuma tarefa dos
   Grupos 3-6 o alcança. **Registrado, não reparado. Vale tarefa própria.**
2. **A guarda do `g2`** em `TrustManagerFactorySpec`, `SignatureSpec` e `SSLContextSpec` carrega a
   mesma supressão que o `g1` perdeu na fusão. Registrado na 3.6, não reparado.
3. **`s3` não tem laços `u* -> s3`.** `update(); update(); doFinal()` é aceito pelo ORDER e
   recusado pelo autômato. Defeito pré-existente. Grupo 6 / 7.1.
4. **Três traces do corpus nomeavam um programa que não compila** (`c.init(1, null)` é ambíguo).
   **Antes de usar uma trace como evidência, confira que ela descreve um programa que compila.**
5. **O dispositivo confirmou o que só o harness tinha mostrado** (4.3): em `CipherUtil.java:54`
   sai `CIPHER-ALG-01 val='DES'` — a acusação que a guarda do `i2` suprimia inteira. E na mesma
   chamada saem `CIPHER-NOBS-00`, `CIPHER-ALG-01` **e** `CIPHER-ORDER-00`: o corpo acusou e só
   então o autômato recusou a transição.
6. **Precisão sobre o que é evidência de quê**: o run da 4.3 também emitiu dois
   `SECRETKEYSPEC-CONSTR-00`, mas esses leem o substrato **velho** (`SecretKeySpecSpec.mop:45`
   ainda chama `ExecutionContext`; migração é a 4.10).

### Novos, da 4.4

7. **A janela F2→F3 da cadeia do IV fecha na 4.5, não na 5.1.** `SecureRandomSpec.next2`
   (`:131-136`) marca o próprio `byte[]` de `nextBytes(byte[])`. Quando a 4.5 migrar esse sítio, a
   leitura do `c1`/`c2` do `IvParameterSpec` acha a entrada pela chave de identidade (as traces
   ligam o mesmo array com `bind iv = bytes(16)`). **A aresta #12 do ledger fica fiada por
   mecanismo A como efeito colateral de duas passagens de arquivo que nunca foram sobre a
   cadeia** — e as duas verdicts `introduced` que a 4.4 produziu se aposentam sozinhas ali.
   **Consequência que a 5.1 tem de resolver**: se ela fiar #12 dentro do `IvChainJunction.mop`
   também, uma cláusula ganha dois acusadores, o que o design proíbe ("o ledger roteia cada
   cláusula para exatamente um acusador"). Ou a 5.1 estreita o junction à cláusula guardada #9, ou
   move #12 para o junction e tira os acusadores das duas leituras.
8. **`IVPARAMETERSPEC-CONSTR-00` e `-01` não têm caminho de execução e não vão ganhar um deste
   oráculo.** `VIOLATED` na aridade 1 sem posições de valor só vem de `negate`, e a api30 tem
   exatamente duas cláusulas `NEGATES` — `SecretKey: generatedKey[this,_] after d` e
   `PBEKeySpec: speccedKey[this,_] after cP`. Nenhuma retira `randomized`. É indisponibilidade
   **mais forte** que a do `CIPHER-CONSTR-00`, que a 5.6 torna alcançável ao subir aquela leitura
   para a aridade 2 da regra; aqui não há aridade a subir. Escrevem-se assim mesmo porque o
   INV-INS-133 exige que a leitura falha e a não observada levem códigos distintos.
9. **Uma passagem de arquivo pode não mover nada e ainda assim mudar o que o conjunto acusa.** O
   censo de colocação da 4.4 é idêntico antes e depois; o harness ganhou duas verdicts
   `introduced`. Se você olhar só o censo, conclui que a tarefa não fez nada.

### Três defeitos de pipeline, fora do escopo desta change — **relatório escrito, decisão pendente**

`docs/20260821_relatorio_analise_estatica_defeitos.md` (709 linhas, Fase 0 do WORKFLOW.md,
commits `e366dd1b` + `b0e98d9c`). Resumo:

| # | Defeito | Já conhecido? | Impacto medido |
|---|---|---|---|
| D1 | O caminho de experimento não fornece `ANDROID_SDK_HOME`, e `lib/gator/gator:64` lê a variável com subscrito nu | **Sim**, desde a gh91, em seis lugares; Docker e `gh91_sa_rerun.py::_gator_env()` já corrigidos | **Total**: `coverage.csv` sem uma linha, `called_methods: 0`, num run que cobriu 27 métodos |
| D2 | A análise estática mira `resources/jca` mesmo sob `--specification-set jca_android` | **Sim**, bloqueador **B4** do `experimento-gh104/CONTEXTO.md:147` | **Zero neste corpus** — medido: os conjuntos diferem em **um** par (`MessageDigest.reset`) |
| D3 | O INV-EXP-16 não é aplicado: um APK sem `.apk.json` é executado assim mesmo | **Não** — achado da sessão da 4.3 | É o multiplicador: converte a falha do D1 em run silenciosamente degradado |

**Nada disso bloqueia a gh105, e nada disso deve ser reparado dentro dela.** Mas **D2 interage com
o Grupo 5**: as junction specs nascem só no `jca_android`, então cada uma aumenta o delta que hoje
é de um alvo — e aumenta exatamente na campanha que vai medir se a gh105 funcionou. Se o
pesquisador abrir a change do relatório, reparar D2 **antes** do Grupo 5 faz as junction specs
nascerem já contadas.

---

## Números medidos (estado atual, reproduzidos da fonte em 2026-08-21 após a 4.4)

| Medida | no início | agora | alvo |
|---|---|---|---|
| acusadores órfãos (G-ACC) | 17 | **0** ✅ | 0 |
| leituras em `condition(...)` | 27 | **8** | 0 |
| leituras em corpo | 0 | **10** | todas |
| escritas em corpo de evento | 42 | **30** | 0 sem motivo |
| escritas no ponto de aceitação | 7 | **9** | todas |
| chamadas de estado de aceitação (`bookkeeping:match` + `:fail`) | 25 | **23** | 0 |
| `remove()` em `@fail` | 8 | 8 | 0 |
| menções a `ExecutionContext` (INV-INS-130) | 23 arquivos | **21** | 0 |
| divergências de ordenação (G-ORDER) | 4 | 4 | 0 |
| sítios no `predicate_graph.csv` | — | **89** | — |
| achados dos gates estruturais | — | G-PRED2 26, INV-INS-130 21, INV-INS-133 8, INV-INS-134 30 | 0 |
| traces do corpus | 63 | **79** | — |
| asserções nas quatro suítes | — | **94** | — |

Harness sobre as 79 traces contra `backup/gh105-preimage/jca_android`: **56 inalteradas,
17 movidas, 2 introduzidas, 4 removidas** (cumulativas contra a pré-imagem). As duas
`introduced` são do `IvParameterSpec` e são a janela F2 — elas se fecham na 4.5.

G-ORDER, as quatro divergências (inalteradas; endereçadas por 7.1 e Grupo 6):
`CipherSpec` (`f2`), `SSLContextSpec` (`g1 Init se1 se1`), `SecureRandomSpec` (`c1 c1`),
`TrustManagerFactorySpec` (`g1 i1 gtm`).

---

## Censo por arquivo — o **estado real**, não o de `tasks.md`

**Os censos escritos nas tarefas 4.5-4.14 são pré-change e estão desatualizados**: o Grupo 3 moveu
leituras para o corpo ao fundir gêmeos. Esta tabela saiu do `predicate_graph.csv` em 2026-08-21,
depois da 4.4, e é a que vale. Reconfira com `--emit` antes de citar qualquer número numa evidência.

| arquivo | `read:condition` | `read:body` | `write:body` | `write:acceptance` | bookkeeping | `remove` | tarefa |
|---|---|---|---|---|---|---|---|
| `CipherSpec.mop` | 0 | 3 | 0 | 2 | 0 | 0 | ✅ 4.1 |
| `IvParameterSpec.mop` | 0 | 2 | 0 | 1 | 0 | 0 | ✅ 4.4 |
| `SecureRandomSpec.mop` | 0 | 1 | 5 | 1 | 1 | 0 | **4.5** |
| `PBEKeySpecSpec.mop` | 0 | 2 | 1 | 0 | 1 | 1 | 4.6 |
| `PBEParameterSpecSpec.mop` | 1 | 1 | 0 | 1 | 1 | 0 | 4.7 |
| `GCMParameterSpecSpec.mop` | 2 | 0 | 0 | 1 | 1 | 0 | 4.8 |
| `MacSpec.mop` | 2 | 0 | 2 | 0 | 1 | 1 | 4.9 |
| `SecretKeySpecSpec.mop` | 0 | 1 | 0 | 1 | 1 | 0 | 4.10 |
| `RandomStringPassword.mop` | 2 | 0 | 2 | 0 | 0 | 0 | 4.11 |
| `SecretKeySpec.mop` | 1 | 0 | 1 | 0 | 0 | 0 | 4.12 |
| `SignatureSpec.mop` | 0 | 0 | 4 | 0 | 1 | 0 | 4.13 |
| `MessageDigestSpec.mop` | 0 | 0 | 3 | 0 | 2 | 0 | 4.13 |
| `SSLContextSpec.mop` | 0 | 0 | 2 | 0 | 2 | 0 | 4.13 |
| `KeyPairSpec.mop` | 0 | 0 | 2 | 0 | 1 | 0 | 4.13 |
| `KeyStoreSpec.mop` | 0 | 0 | 2 | 0 | 2 | 2 | 4.14 |
| `KeyManagerFactorySpec.mop` | 0 | 0 | 2 | 0 | 2 | 1 | 4.14 |
| `TrustManagerFactorySpec.mop` | 0 | 0 | 2 | 0 | 2 | 2 | 4.14 |
| `KeyGeneratorSpec.mop` | 0 | 0 | 1 | 0 | 2 | 1 | 4.14 |
| `KeyPairGeneratorSpec.mop` | 0 | 0 | 1 | 0 | 1 | 1 | 4.14 |
| `DHGenParameterSpecSpec.mop` | 0 | 0 | 0 | 1 | 1 | 0 | 4.14 |
| `HMACParameterSpecSpec.mop` | 0 | 0 | 0 | 1 | 1 | 0 | 4.14 |

Reproduzir:

```bash
python3 -c "
import csv,collections
rows=list(csv.DictReader(open('data/jca_android/predicate_graph.csv')))
per=collections.defaultdict(collections.Counter)
for r in rows: per[r['file']][r['verdict']]+=1
for f in sorted(per): print(f, dict(per[f]))
"
```

---

## Próximo passo: 4.5 — `SecureRandomSpec`

### O que a tarefa diz, e o que o arquivo diz

`tasks.md:235`: *"`SecureRandomSpec` (4 reads / 6 writes / 1 call); o `end`-state `next2` omission
é reparado aqui"*. **O censo está desatualizado** — a 3.1 fundiu `c3`→`c2` e `setSeed3`→`setSeed2`.
O estado medido é **1 leitura em corpo, 5 escritas em corpo, 1 escrita em aceitação, 1
escrituração**, e o arquivo tem **9 menções a `ExecutionContext`**, o maior número do conjunto.

Pontos que a 4.5 tem de resolver, e que a 4.4 deixou preparados:

* **Este é o arquivo que fecha a janela F2 da cadeia do IV.** O `next2`
  (`SecureRandomSpec.mop:131-136`) marca o `byte[]` de `nextBytes(byte[])`. Quando ele passar ao
  `PredicateStore`, as duas verdicts `introduced` da 4.4 se aposentam e a aresta #12 do ledger
  fica de fato fiada por mecanismo A. **Meça isso e registre**, porque é o que a 5.1 vai precisar
  para escolher o mecanismo do `IvChainJunction.mop` (achado 7 acima).
* **A regra tem `randomized[this] after Ins`** (`SecureRandom.cryptsl`, seção ENSURES) — uma
  cláusula `after L`, que é o segundo tipo de ponto de aceitação que o INV-INS-134 conhece.
  O `CipherSpec` já tem o precedente ratificado: `alias match2 = <estado>`. Leia a api30 antes de
  decidir onde cada uma das cinco escritas em corpo aterrissa.
* **As escritas de argumento autoboxado** (`next1`/`next3` marcam o `int`) são **da 5.5**, não
  desta tarefa — a tarefa 5.5 diz "drop the autoboxed argument writes". Não antecipe.
* **O `end`-state `next2` omission** é reparo pontual desta tarefa (está no enunciado da 4.5).
* **G-ORDER lista `SecureRandomSpec` como divergente** (`c1 c1` aceito pela especificação e
  recusado pela ORDER). É uma das 4 divergências conhecidas, endereçada pela 7.1 — não a repare
  aqui, mas não a piore.

### Depois da 4.5

4.6 a 4.14 são um passo por arquivo, paralelizáveis por subagente. A 4.15 fecha o grupo (gates de
colocação verdes, baselines aposentadas pelo bloco `retired`) e a 4.16 roda `/rv-test-run
tests/parity`. Só então o Grupo 5, que a 4.3 liberou.

---

## Receita por tarefa (a que funcionou nas 3.1 a 4.4)

1. **Ler a regra api30 primeiro**, depois o corpo do evento. A regra decide onde a coisa vai.
2. **Medir o mecanismo no artefato antes de escrever a edição** quando a decisão depender dele.
   A 4.1 leu o monitor gerado e derrubou o custo que o plano atribuía à forma escolhida; a 4.3
   mediu o corpus de runs anteriores e descartou o `monkey`; a 4.4 mediu que `PREPARED_IV` não
   tem leitor vivo e com isso transformou uma discussão de projeto em preservação literal.
3. Editar o `.mop` **inteiro, comentários incluídos**, antes de tudo. **O digest do hunk é do
   conteúdo**: mexer no comentário depois re-chaveia a linha do registro.
4. `codes.csv` segue o **sítio** (colunas `event` e `file_line`), não a cláusula; reconferir com
   `grep -n 'addError'`. Nenhum código do arquivo é reusado em dois sítios — medido: 0 repetições
   em 52 linhas.
5. `order_alphabet_map.csv`: evento **fundido** perde a linha; evento **absorvido** fica com
   `order-unmapped` **ou** `mapped` ao símbolo que a regra dá à chamada. Uma passagem F2 que não
   mexe no alfabeto não mexe neste arquivo (foi o caso da 4.4).
6. Traces satisfaz/viola em `data/gh104/traces/`. Dentro da janela F2 o lado "satisfaz" é
   impossível — declare e **meça** a impossibilidade em vez de assumir. Se as traces já existirem
   de uma tarefa do Grupo 3, não as reescreva: o par é o mesmo programa, o que muda é o veredito.
7. Regerar o grafo: `--emit`. Conferir round-trip (`cp` antes, `diff` depois — tem de ser
   byte-idêntico). Preencher `clause`/`mechanism` à mão nas linhas novas (o `--emit` seguinte
   preserva as colunas de julgamento).
8. `gh104_divergence_record.py --check` → registrar cada hunk novo. **Linhas `stale` têm que
   sair**, e as razões que elas carregavam precisam ser **absorvidas** na razão do hunk novo
   ("This hunk absorbs the reason of the retired `<digest>`: …"), com a coluna `task` acumulando
   (`7.5;3.3;4.4`). O arquivo é **CRLF** — `csv.writer` com `lineterminator="\r\n"`.
9. Rodar o harness diferencial (background, ~15 min) **e**, onde os dois relatos saem da mesma
   chamada, a sonda de contagem do `ErrorCollector`. Quando cada chamada emite no máximo um
   relato e o evento está no `ere`, o piso do harness **é** a contagem — diga isso em vez de
   rodar a sonda à toa (4.4).
10. Conferir o diff da baseline (`--write` quando um sítio mudar de chave; ele preserva `retired`).
11. Atualizar os censos em `tests/parity/test_gh105_predicate_gates.py` com uma linha de docstring
    dizendo qual tarefa moveu o número. **Se a tarefa não moveu nenhum, escreva isso também** —
    "task 4.4: no placement moves" é informação, não ruído.
12. Escrever a evidência em `data/gh105/evidence/f2-<Spec>.md`.
13. Rodar as quatro suítes. Commitar (stage por caminho explícito). Marcar o checkbox.

---

## Arquivos relacionados

**Java (reator irmão, `.../workspace-rv/rvsec/rvsec/`)**
- `rvsec-core/src/main/java/br/unb/cic/mop/PredicateStore.java`, `PredicateVerdict.java`,
  `Property.java`, `eh/ErrorType.java`, `eh/ErrorDescription.java`
- `rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java` (**congelado, byte-idêntico**)
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` (gramática das traces; o
  `match()` casa por tipo dinâmico e o `envelope()` devolve um relato por chamada)
- `rvsec-mop/src/main/resources/jca_android/*.mop` + `codes.csv` ← o conjunto que a change edita
- `rvsec-mop/target/gh104-classpath.txt` (classpath para a sonda de contagem)

**Python (`.../rvsec/rv-android/`)**
- `scripts/gh105_predicate_graph.py`, `gh105_order_gate.py`, `gh105_param_gate.py`
- `scripts/gh105_gate_baseline.py` (mecanismo D-13 + `retire()`; **data de demolição: 7.6**)
- `scripts/gh104_gates.py`, `gh104_divergence_record.py`, `gh104_diff_harness.py`,
  `gh104_message_gate.py` (a 4.2 acrescentou a propriedade `not-observed-family`)
- `tests/parity/test_gh105_predicate_gates.py` + as três suítes gh101/gh104
- `data/jca_android/`: `predicate_graph.csv`, `order_alphabet_map.csv`, `gate_baseline.json`,
  `gate_allowlist.csv`, `divergence_record.csv` (**CRLF** — preserve), `alias_table.csv`,
  `constraint_table.csv`, `evidence/gate_baseline_report.md`
- `data/gh104/traces/` (79 traces)
- `data/gh105/evidence/`: `f1-group-three-the-seventeen.md`, `f2-CipherSpec.md`,
  `f2-reach-probe.md`, **`f2-IvParameterSpec.md`**, `reach-probe/` (artefatos das duas execuções
  de dispositivo), `f1-IvParameterSpec-report-count.md`, `f1-PBEParameterSpecSpec-report-count.md`,
  `f1-SecretKeySpecSpec-unreachable-constraint.md`, `f1-PBEKeySpecSpec-fusion.md`,
  `f1-KeyPairGeneratorSpec-absorption.md`, e `harness/f{1,2}-*.md`
- `backup/gh105-preimage/jca_android/` (pré-imagem), `backup/gh105-retired/`
- `docs/20260821_relatorio_analise_estatica_defeitos.md` (Fase 0, fora do escopo da change)

**Oráculo (somente leitura)**: `/home/pedro/.../workspace-rv/MetaCrySL/generated/api30/*.cryptsl`

---

## Comandos

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
export RVSEC_HOME=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
SPECS=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources

# as quatro suítes de gates (contrato de CI obrigatório) — hoje 94 passando, ~80 s
uv run pytest tests/parity/test_gh101_specset_gates.py tests/parity/test_gh104_specset_gates.py \
    tests/parity/test_gh104_structural_gates.py tests/parity/test_gh105_predicate_gates.py \
    --import-mode=importlib -o "addopts=" -q

# suíte estrutural gh105 pela CLI (--json dá as contagens por gate)
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets all
uv run python scripts/gh105_predicate_graph.py --specs-root $SPECS --sets jca_android --emit

# G-ORDER (filtre `skipped`; só as 4 divergências conhecidas devem aparecer)
uv run python scripts/gh105_order_gate.py --specs-root $SPECS --sets jca_android

# gate de mensagens (a quinta propriedade da 4.2 vive aqui)
uv run python scripts/gh104_message_gate.py $SPECS/jca_android \
    --crysl /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30

# baseline (comparar; --write quando um sítio mudar de chave — ele preserva `retired`)
uv run python scripts/gh105_gate_baseline.py --specs-root $SPECS

# registro de divergência
uv run python scripts/gh104_divergence_record.py --check
uv run python scripts/gh104_divergence_record.py --refresh   # imprime as linhas vivas

# harness diferencial (~15 min) — rodar em background
# NÃO canalizar para `tail`: o resumo JSON (inclusive o "scratch") fica no TOPO da saída
export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH
uv run python scripts/gh104_diff_harness.py \
    --a backup/gh105-preimage/jca_android --b $SPECS/jca_android \
    --traces data/gh104/traces --out data/gh105/evidence/harness --group f2

# build do reator Java (JDK 21 no prefixo; recurso serializado) — ~50 s, BUILD SUCCESS em 21/08
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
mvn clean install -DskipMopAgent -DskipTests
mvn -o test -pl rvsec-core,rvsec-mop -DskipMopAgent
```

**Execução de dispositivo** (só a 8.5 ainda precisa; o rv-platform gerencia o emulador inteiro):

```bash
export RVSEC_HOME=/home/pedro/.../rvsec
export ANDROID_HOME=/home/pedro/desenvolvimento/aplicativos/android/sdk
export ANDROID_SDK_HOME=$ANDROID_HOME     # obrigatório: sem ele o GATOR morre (defeito D1)
uv run rv-experiment run --tools aperv:sata_mop --timeouts 300 --repetitions 1 \
    --apks-dir ./apks_examples --specification-set jca_android \
    --instrumentation-variant dexlib2 --name <nome> --no-window
```

---

## Aprendizados que custaram tempo (não redescobrir)

1. **O critério gêmeo-vs-absorção é o corpo do órfão**, não a guarda. Corpo que acusa por conta
   própria → absorve. Corpo que só religa campo → funde.
2. **E o critério de qual absorção é a regra**, não o formato do autômato.
3. **O veredito do harness é piso, não contagem** onde os dois relatos saem da mesma chamada.
   `TraceRunner.envelope()` devolve o primeiro erro do `Set` por chamada de dispatcher. Onde cada
   chamada emite no máximo um relato e o evento está no `ere`, o piso **é** a contagem.
4. **Um órfão pode suprimir o achado, não só somar ruído.** Medido na 3.2, na 3.6, na 4.1 e em
   produção na 4.3: a guarda do `i2` suprimia `CIPHER-ALG-01 val='DES'` inteiro.
5. **A tabela de alias do gh104 muda quais traces exercitam um órfão.** `X509` resolve para
   `PKIX` (`alias_table.csv:2`).
6. **O digest de hunk é do conteúdo.** Terminar o `.mop` antes de sincronizar `codes.csv`.
7. **`openspec validate` não aceita `--change`** — a sintaxe é `openspec validate <nome>`.
8. **`csv.writer` escreve `\r\n` por padrão.** `divergence_record.csv` **é** CRLF (preserve);
   `gate_allowlist.csv`, `predicate_graph.csv` e `codes.csv` são LF (passe `lineterminator="\n"`).
9. **Dois hunks com as mesmas linhas mudadas colidem num digest** — mas o registro é chaveado por
   `(file, hunk)`, então o mesmo digest em dois arquivos são duas linhas. O hunk do import
   (`c9fe4844152e`) é literalmente o mesmo em todo arquivo migrado.
10. **O `)` sobrando** em `jca/SecretKeySpecSpec.mop:30`. Congelado; o leitor pula com motivo.
11. **`TraceRunnerTest` tem 2 falhas pré-existentes.** Verificado com `git stash`. Não é regressão.
12. **`mvn clean install` deixa `tests/parity/test_baseline_freshness.py` vermelho** (mtime do
    `lib/gator/rvsec-analysis-client.jar`). É o tripwire funcionando.
13. **Caminhos**: o alias `/pedro/...` não resolve na JVM. Usar sempre `/home/pedro/...`.
14. **`rvsec` e `rv-android` são o mesmo repositório git** (raiz em `.../workspace-rv/rvsec`,
    branch `modules`). Um commit cobre os dois lados. A árvore tem **muita** modificação
    pré-existente não relacionada — **stage por caminho explícito**, nunca `git add -A`.
15. **A baseline não precisa ser regerada quando um grupo aterrissa** — mas **precisa** quando um
    sítio muda de chave (relocação = chave nova = `NEW`). O `--write` preserva `retired`.
16. **O `ere` suporta `*`, `+`, `|` e agrupamento.** Mas laço não avança o autômato.
17. **O corpo do evento roda antes do `handleEvent`**, e o handler de estado dispara a cada evento
    cujo `nextstate` cai no estado — inclusive laços.
18. **Um handler de ponto de aceitação precisa se chamar `@match<N>`** —
    `_ACCEPTANCE_HANDLERS = ^@match\d*$` no `gh105_predicate_graph.py`.
19. **`PredicateStore.validateAbsent` é name-only** (`:339`): ignora as posições de valor.
20. **`c.init(1, null)` não compila** (ambíguo). Uma trace com `null` numa posição que discrimina
    sobrecarga faz o harness despachar para todas as que casam.
21. **Quando escritas viram handler compartilhado, N sítios viram 1 linha no grafo.** Os censos
    mudam de forma, não só de número.
22. **Os censos de `tasks.md` para o Grupo 4 estão desatualizados.** Use a tabela deste documento
    ou regenere do `predicate_graph.csv`. O Grupo 3 moveu leituras ao fundir gêmeos.
23. **`ANDROID_SDK_HOME` precisa estar exportado** para qualquer run no host. Sem ele a análise
    estática morre inteira, o run **continua**, e a saída sai com `cov_*` zerados e
    `✅ Experiment completed successfully!`. Nunca leia cobertura zero como medição sem conferir
    o logcat.
24. **Nem toda ferramenta alcança o `Cipher.init` do `cryptoapp`.** `aperv:sata_mop` 300 s alcança
    de forma confiável, `ape` 60 s é estocástico, `monkey` não chega lá em 600 s. Antes de gastar
    um run, procure em `results/*/**.logcat` que ferramenta já alcançou o que você precisa.
25. **`results/` é ignorado pelo git.** Evidência de dispositivo tem que ser copiada para
    `data/gh105/evidence/` para sobreviver.
26. **O `lib_tmp/` da raiz é velho e não é o que a instrumentação usa** — o `Instrumenter` passa
    `-DoutputDirectory=results/<run>/lib_tmp`, um diretório por execução.
27. **Uma sonda com uma pergunta binária não é auditável.** As três camadas da 4.3 são o que
    permitiu ler o primeiro run como "inconclusivo" em vez de "bloqueado".

### Novos, da 4.4

28. **`gh105_gate_baseline.py` e `gh105_predicate_graph.py` saem com código 1 quando há achados**,
    o que é o comportamento correto — mas quebra um encadeamento `cmd && diff && echo OK`. Rode o
    `--emit` e o `diff` como comandos separados, senão você conclui que o round-trip falhou.
29. **Um código pode ser escrito sabendo que nada o executa**, desde que a razão esteja registrada.
    Já são quatro: `CIPHER-CONSTR-00` (alcançável na 5.6), `PBEKEYSPEC-CONSTR-01`,
    `SECRETKEYSPEC-CONSTR-01` (construtor lança antes do `after ... returning`) e agora
    `IVPARAMETERSPEC-CONSTR-00`/`-01` (nenhuma cláusula `NEGATES` da api30 retira `randomized`).
    **Três razões distintas** — não trate como uma só.
30. **Ao medir com `grep` sobre os cinco conjuntos, diga onde os acertos caíram.** O conjunto
    reprovado vai aparecer; filtrar em silêncio produz afirmação falsa ("nenhum dos cinco
    conjuntos lê X"), e foi assim que uma linha errada quase entrou no `divergence_record.csv`.
31. **Quando as traces do par já existem de uma tarefa do Grupo 3, não as reescreva.** O par é o
    mesmo programa; o que a passagem F2 muda é o veredito, e a evidência registra o veredito novo.

---

## Como retomar

```
Continue aplicando a change gh105-predicate-wiring a partir da tarefa 4.5.
Leia primeiro docs/handoff/20260821_gh105_apply_prompt_v8.md, depois os quatro artefatos em
openspec/changes/gh105-predicate-wiring/ e as três evidências do Grupo 4
(data/gh105/evidence/f2-CipherSpec.md, f2-reach-probe.md e f2-IvParameterSpec.md), e siga
docs/WORKFLOW.md rigorosamente — invoque a skill openspec-apply-change, não escreva artefatos
à mão. A sonda de alcance já respondeu: a change não está bloqueada e o Grupo 5 está liberado.
Os censos por arquivo do Grupo 4 em tasks.md estão desatualizados — use a tabela do handoff.
A 4.5 fecha a janela F2 da cadeia do IV que a 4.4 abriu: meça e registre, porque a 5.1 precisa
disso para escolher o mecanismo do IvChainJunction.mop.
Traga as decisões de projeto ao pesquisador antes de editar, com medição junto.
```

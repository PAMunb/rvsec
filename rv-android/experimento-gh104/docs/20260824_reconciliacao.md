# Reconciliação de 2026-08-24 — o que o plano afirmava e o que está medido

Este arquivo é o registro da passagem que reconciliou `experimento-gh104/` com o estado real das
changes. Ele existe para que a próxima pessoa não precise refazer a medição para saber **o que
mudou e por quê** — e para que qualquer número corrigido tenha um comando ao lado.

**Base de medição:** `rv-android` no HEAD `6192b57a`, reator `rvsec` no branch `modules`, em
2026-08-24. Nada foi executado: nenhum emulador, nenhuma instrumentação, nenhuma campanha.

**Regra que este arquivo adota, emprestada da `gh106`:** um escalar sem data, sem commit e sem
regra de contagem não é verificável. Onde a regra não é óbvia, ela está escrita.

---

## 1. Estado das changes

| change | plano dizia (18/08) | medido (24/08) |
|---|---|---|
| `gh104-legible-violation-reports` | 0/96 | **106/109** — abertas: 10.4, 10.5, 10.8 |
| `gh105-predicate-wiring` | não existia no plano | **72/74** — 8.8 e 8.9 bloqueadas pelo arquivamento da gh104 |
| `gh106-mop-crysl-conformance` | não existia | **15/16** — só a 16.1 (fechamento do G14) |
| `gh100-weaver-emission-fidelity` | não citada | **57/57** |

```bash
for c in gh100-weaver-emission-fidelity gh104-legible-violation-reports \
         gh105-predicate-wiring gh106-mop-crysl-conformance; do
  echo "$c: $(grep -c '^- \[x\]' openspec/changes/$c/tasks.md)/$(grep -c '^- \[' openspec/changes/$c/tasks.md)"
done
```

---

## 2. Afirmações do plano que ficaram falsas

Cada linha tem um comando ou um `caminho:linha`. Sem ponteiro, a linha não entra.

| # | afirmação do plano | valor antigo | valor medido em 24/08 | corrigido em |
|---|---|---|---|---|
| 1 | cardinalidade do `jca_android` | 21 `.mop` | **24** `.mop` + `codes.csv` | `PRONTIDAO.md:30`, `CONTEXTO.md` §3/§3.1, `README.md:6,46`, `docs/…:223`, `instrumentacao/README.md:47,300` |
| 2 | `RandomStringPassword.mop` e `SecretKeySpec.mop` seriam deletados | deletados | **ficam** — a **D-11** retirou a deleção (`gh104/proposal.md:58`) | `CONTEXTO.md` §3.1, `docs/…` §5 |
| 3 | membro novo do conjunto | — | **`IvChainJunction.mop`**, da gh105 (commit `889da829`, tarefa 5.1) | idem |
| 4 | vocabulário `KIND` do envelope | 7 valores | **8** — entra `NOBS` (30 dos 114 códigos) | `CONTEXTO.md` §6, `docs/…` §1 |
| 5 | sítios de report do sucessor | 45, "A RECALCULAR" | **114** | `docs/…` §5 |
| 6 | `predicate_removal.csv` = 30 linhas | previsto | **não existe** — está em `backup/gh104-predicate-revert/`. O que existe é `predicate_graph.csv`, 70 linhas | `docs/…` §5 |
| 7 | oráculo das listas de valor | api30 gerada | **49 regras expert**, pinadas por sha256 (**D-15**, `gh104/design.md:346`) | `CONTEXTO.md` §6, `docs/…` §5 |
| 8 | MD5/SHA-1 deixam de ser acusados | "custo declarado" | **voltam a ser acusados** — 5.892 linhas | `docs/…` §5, `PRONTIDAO.md` P9 |
| 9 | `AES/ECB` | não citado | **volta a ser acusado** (tarefa 11.3, commit `5bc5c893`) | `docs/…` §5 |
| 10 | tabela-alvo da tarefa 10.5 | 5 linhas, justificadas pela api30 | **3 linhas**, justificadas por lista expert + `platform-value` + normalização da 2.5 | `PRONTIDAO.md` P6, `docs/…` §7 |
| 11 | B1 (specs novas) | PENDENTE | **FECHADO** | `CONTEXTO.md` §3 |
| 12 | B2 (reator instalado) | PENDENTE, jar de 11/08 | **FECHADO em 24/08 20:26** (jar posterior ao `.mop` mais novo, 11:51) | `CONTEXTO.md` §3, `instrumentacao/README.md` |
| 13 | B4 (`mop_dir` fixo em `jca`) | "NÃO MORDE" | **RESOLVIDO** por `86a8f178`; `config.py:982` | `CONTEXTO.md` §3/B4 |
| 14 | B5 (leitores de 13 colunas) | PENDENTE | **RESOLVIDO** — `violations.py:64-78` | `CONTEXTO.md` §3 |
| 15 | B6 (leitor congelado de 11 colunas) | PENDENTE | **RESOLVIDO** — `scripts/gh104_baseline.py:371` | `CONTEXTO.md` §3 |
| 16 | B8 (`instr-cli.jar`) | de 11/08 | **24/08 20:28** | `CONTEXTO.md` §3 |
| 17 | branch à frente de `origin/modules` | 4 commits | **124 commits** | `CONTEXTO.md` §4, `PRONTIDAO.md` P5 |
| 18 | "a tag `0.9.3` é a imagem que reproduz a `comp162`" | — | **falso**: a `comp162` roda em `0.9.3-comp162` (`811d3ef3ad5b`); `0.9.3` e `latest` são `9cca8e617c7c` | `CONTEXTO.md` §4, `PRONTIDAO.md` P5 |
| 19 | `weaveCounts` tem 19 campos | 19 | **20** — `advicesExcludedByArity` entrou em 19/08 (`b43f500e`) | `instrumentacao/README.md`, `PRONTIDAO.md` P3 |
| 20 | "`advicesExcludedByArity` não existe ainda" | não existe | **existe** — e o nosso `scripts/gh104_gates.py:179` já o exigia; o script estava certo e o README, velho | `instrumentacao/README.md:298` |
| 21 | risco 9 (análise estática com o conjunto errado) | risco vivo | **resolvido** | `docs/…` §8 |

### Confirmadas, não invalidadas

| afirmação | verificação |
|---|---|
| freeze do `jca` intacto | `git diff 7e7acb69 -- rvsec/rvsec-mop/src/main/resources/jca` vazio |
| `ExecutionContext` = 0 no sucessor (G-PRED) | `grep -ro ExecutionContext jca_android/ \| wc -l` → 0 |
| `admissibility.py` byte-idêntico ao da `comp162` | `md5sum` igual nos dois (`d505e62c821a1a55975f992523c66ccc`) |
| `wrappersGenerated = 84` no `jca` | é o valor **pós-gh100** (96 → 84 pela fusão de wrappers), e o plano já o registrava |
| `wrappersSubstituted` é a métrica de superfície | inalterada em nome, semântica e valor pela gh100 |
| o portão da campanha reproduz as baselines | rodado em 24/08 contra a `comp162`: 19.664 linhas, 15.714 mudas (79,91 %), 98 `but found .`, **3 PASS / 6 FAIL / 1 SKIP**, exit 1 |

---

## 3. Defeitos achados no ferramental desta campanha

Nenhum deles foi corrigido nesta passagem — corrigir muda o que o instrumento mede, e essa é
decisão do pesquisador.

### F1 — `gh104_gates.py` reprovaria uma campanha correta

`scripts/gh104_gates.py:140-142` congela
`ENVELOPE_KINDS = {ORDER, ALG, CONSTR, KEYSIZE, KSTYPE, PROTO, FORB}`. O `codes.csv` vivo tem
**30 códigos `NOBS` de 114**. Como `well_formed = … and code_match.group("kind") in ENVELOPE_KINDS`
(`:278`), toda mensagem `*-NOBS-NN` conta como `envelope_malformed` e o **G5 falha**.

**Correção proposta:** ler o vocabulário do `codes.csv` do conjunto sob medição, em vez de congelar
uma lista. Congelar é o que fez o portão envelhecer; congelar de novo o faria envelhecer de novo.

**Feito em 25/08**, por essa via: `--codes-csv` alimenta `load_code_vocabulary`, e a lista
congelada (já com `NOBS`) só responde quando o arquivo não é passado. De brinde, o portão passou a
verificar se o código **existe** no catálogo, e não só se o KIND é plausível.

### F2 — `msg_diff.py` é cego a uma segunda acusação no mesmo sítio

`scripts/msg_diff.py:196` chaveia por `(apk, spec, classe, método, tipo_erro)` e **não inclui
`code`**; o `code=` do envelope não é parseado em lugar nenhum do arquivo. As mensagens vão para um
`Counter` ao lado, e `_representative` (`:304-308`) devolve **a mais frequente** — a minoritária
desaparece da comparação.

O colapso é real e demonstrável no `codes.csv`: `SIGNATURE-CONSTR-00` e `SIGNATURE-NOBS-00` são o
**mesmo evento `i1`, o mesmo `error_type` `UnsatisfiedConstraint`, códigos diferentes**. A separação
violação × não-observado que a INV-INS-143 existe para garantir é destruída pela identidade.

É o mesmo defeito que custou **treze traces** à tarefa 11.9 da gh104 — lá o arnês passou a comparar
pares `(evento, código)` (commit `9cba65ee`, `scripts/gh104_diff_harness.py:197-219`) e a registrar
toda acusação que o evento acrescenta, diffando o sink contra um snapshot tirado antes do advice
(commit `21aa1b66`, lado Java).

**Correção mínima proposta:** extrair `code=` do campo 7 com o mesmo regex do arnês e acrescentá-lo
à tupla de `:196`, com o sentinela `UNSPECIFIED` para a era antiga — senão todo o lado A vira
`so_A`.

**Essa correção não funciona, e o reparo de 25/08 é outro.** O sentinela não evita o efeito que o
próprio parágrafo teme: com o código dentro da chave, o lado A fica `(…, UNSPECIFIED)` e o lado B
`(…, SIGNATURE-CONSTR-00)`, tuplas que nunca casam — 100 % `so_A` e 100 % `so_B`, zero `ambos`, a
comparação destruída em silêncio. O que foi feito é **juntar por sítio e comparar por código**:
`viol[apk][sítio][code]`, uma linha por par `(sítio, código)`, e o registro sem envelope da era
antiga respondendo por cada código do lado novo. Detalhe em `../CONTEXTO.md` §7.

### F3 — colisão de nome com armadilha de `sys.path`

Existem dois `gh104_gates.py`, de propósitos disjuntos e zero funções em comum:

| arquivo | insumo | portões |
|---|---|---|
| `scripts/gh104_gates.py` (raiz, 83 KB) | monitor gerado + diretório `.mop` | G-2, G-2a, G-2b′, G-2c, G-2d, G-6′, G-ERE, G-CONF, G-PRED |
| `experimento-gh104/scripts/gh104_gates.py` (40 KB) | campanha gravada (`errors.csv`, `.logcat`, `instrument_results.json`) | G1…G10 |

`scripts/gh104_mop_lint.py:47` e `scripts/gh104_message_gate.py:76` fazem `sys.path.insert(0, …)`
seguido de `from gh104_gates import MopSpec, parse_mop, …`. Com o nosso diretório antes no
`sys.path`, o import estoura.

**Proposta, a decidir:** renomear o nosso para `campaign_message_gates.py`. O nome aparece em
`PRONTIDAO.md`, `README.md` e `CONTEXTO.md`.

### F4 — prosa defasada no `preflight.py`

`experimento-gh104/scripts/preflight.py:137-139` diz "the gh104 successor is planned at 21". **Não
há hardcode** — `--expect-specs` é opcional e o default só imprime a contagem — então o script não
quebra. Mas o número induz o operador a passar `--expect-specs 21`, o que reprovaria um run
correto. (`--expect 21`, na linha de uso, é outra coisa: é a contagem de APKs do shard `s0`, e está
certa.)

O mesmo arquivo **já retirou** corretamente o seu segundo `G-PRED` (`check_no_predicates`), de
polaridade oposta ao da change: depois da fiação da gh105 ele avisaria em toda corrida correta.
`preflight.py:13-19` documenta a retirada.

---

## 4. O que não mudou, e por que isso importa

O raciocínio que sustenta as decisões **D-a a D-e** continua válido, e nenhuma delas foi
reaberta:

- **D-a** (mesmos 162 APKs) e **D-b** (mesmos 3 braços, R=3, T=300 s, 1458 identidades) — o
  pareamento é a razão de a campanha existir.
- **D-c** (reusar os `.apk.json`) — continua correta; mudou o **estatuto**, de necessidade técnica
  para escolha de método, porque o defeito B4 foi corrigido.
- **D-d** (imagem própria) — continua correta; mudou a **justificativa**, que estava factualmente
  errada.
- **D-e** (piloto 10.4 antes da campanha) — ficou **mais** forte: a 10.4 é uma das três tarefas
  abertas da change, e a 10.5 declara "Runs only after Group 11", que fechou em 24/08.

A `gh106` **não** substitui nem duplica o ferramental desta campanha. Ela mede o contrato `.mop` ×
`.crysl` estaticamente (M0–M4) e declara que não muda o que os monitores acusam; nunca menciona
`experimento-gh104/`. A divisão que ela própria escreve: é a metade estrutural de um projeto de
dois instrumentos cuja metade comportamental já existe — e a metade comportamental é esta.

---

## 5. Pendências herdadas da reconciliação

| item | quem decide |
|---|---|
| ~~corrigir F1 (`NOBS` no G5)~~ — **feito em 25/08**, pela via do `codes.csv` | — |
| ~~corrigir F2 (`code` na identidade do `msg_diff`)~~ — **feito em 25/08**, juntando por sítio e comparando por código | — |
| renomear o portão da campanha (F3) | pesquisador |
| ajustar a prosa do `preflight.py` (F4) | trivial, mas é edição de instrumento |
| `docs/20260824_auditoria_specs_jca_android.md` é a fonte da D-15 e vale a leitura antes do P6 | — |

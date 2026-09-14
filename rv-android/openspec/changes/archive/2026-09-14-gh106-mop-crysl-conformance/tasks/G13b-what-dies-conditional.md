# G13b · what dies, conditional part

**Depends on:** G12. **Blocks:** G14.
**Size:** ~2 documents. **No file is deleted in this group.**

The five surviving artifacts are load-bearing CI gates. The criterion for retiring them is *the
ad-hoc dies when the component reproduces its verdict, not when it compiles* — so this group's job is
to **produce the reproduction evidence** and hand the deletion to a follow-up change.

Retiring a gate before the replacement reproduces it loses coverage silently, which is the same class
of failure the gh104 harness exists to catch and which this lineage has already shipped twice.

## The five survivors

| Artifact | Lines | Why it survives this change |
|---|---:|---|
| `scripts/gh105_order_gate.py` | 1 171 | live gate; G10 must reproduce its verdicts first |
| `scripts/gh101_conformance_check.py` | — | live gh101/gh105 gate |
| `scripts/gh104_baseline.py` | — | live gh104 gate |
| `scripts/gh104_gates.py` | — | live gh104 gate |
| `tests/parity/test_gh105_predicate_gates.py` | 2 507 | live pytest gate; its green is the cut criterion |

(The three `gh10{1,4}_*.py` total 4 340 lines.)

## Tasks

- [x] 13b.1 Run `scripts/gh105_order_gate.py` and the component's M2 over the same corpus at the same commit, and produce a **verdict-by-verdict** comparison table for all 22 mapped specifications.
- [x] 13b.2 Adjudicate every disagreement with evidence and record the outcome. The gate reads the `ORDER` with inverted precedence in its own history, so a disagreement is at least as likely to be the gate's as the component's — and deciding by measurement rather than by seniority is the point.
- [x] 13b.3 Run `tests/parity/test_gh105_predicate_gates.py` and the component's M4 over the same corpus, and produce the same verdict-by-verdict table for the predicate gates.
- [x] 13b.4 Do the same for the three `gh10{1,4}_*.py` scripts that read `.cryptsl`, restricted to the checks that fall inside the component's scope. Here "reproduce their verdict" means reproducing it over the **same historical `.cryptsl` input** they read, stamped as such — not re-deriving it from the upstream oracle, which would compare two different measurements. Some of what they do is outside the component's scope, and saying which is part of the deliverable.
- [x] 13b.5 Write `docs/<date>_reproducao_portoes_ci_gh106.md`: the tables, the adjudications, and an explicit verdict per gate — *reproduced* or *not yet*.
- [x] 13b.6 Open the follow-up cleanup issue for the gates marked *reproduced*, citing the evidence document by commit. **Do not delete them here**, even the ones that reproduce cleanly: the deletion is a separate change with its own verification, and bundling it hides it inside a change about something else.
- [x] 13b.7 Record in `divergence_record.csv` any gate verdict the component **deliberately** does not reproduce, with the reason. A gate that measures something the component decided not to measure is not a failure; it is a scope boundary, and it needs to be written down as one.

## Medido (2026-08-24)

**Evidência:** `docs/20260824_reproducao_portoes_ci_gh106.md`. **Continuação:** issue
[PAMunb/rvsec#107](https://github.com/PAMunb/rvsec/issues/107). **Nenhum arquivo foi apagado.**

Carimbos: `.mop` `jca_android` em `rvsec@6192b57a` (árvore limpa), oráculo do componente
`rvsec-cognicrypt@f2f4d3b`, oráculo dos portões `MetaCrySL/generated/api30`, oráculo de valor do
`gh104_gates.py` `RVSec-replication-package/tools/rules` (D-15), `android.jar` API 30. O `compare`
reproduziu dígito por dígito as figuras de registro do G05 5.8: `24 lifted, 0 did not lift` ·
`47 rules lifted, 2 did not` · `22 pairs` · `2 refused by M0, 21 received M1-M4`.

**Resultado: nenhum dos cinco portões está reproduzido. Nenhum pode ser apagado.**

| Portão | Rodou? | Veredito | Números |
|---|---|---|---|
| `scripts/gh105_order_gate.py` | sim, `exit 0` | **ainda não** | 15 pleno · 3 parcial · 6 discorda (de 24) |
| `tests/parity/test_gh105_predicate_gates.py` | sim, 73 passed | **ainda não** | 60/60 sítios nos 21 arquivos compartilhados |
| `scripts/gh101_conformance_check.py` | sim, `exit 0` | **ainda não** | 9 de 23 vereditos alcançáveis |
| `scripts/gh104_gates.py` | sim, **`exit 1`** | **ainda não** | G-CONF 7/20 (17/19 projetado); 7 dos 9 portões internos fora de escopo |
| `scripts/gh104_baseline.py` | sim, `exit 0` | **não aplicável** | 0 verificações em escopo |

**O fato transversal, medido e não suposto.** Copiando os 33 `.cryptsl` do `api30` para `.crysl` e
levantando o diretório com o levantador do componente: **`OK 20 / FAILED 13`**. Treze das regras
geradas estão fora da gramática CrySL — entre elas `Cipher`, `KeyGenerator`, `KeyPairGenerator`,
`KeyStore`, `Mac`, `SSLContext`, `Signature`, `SecretKeySpec`, `PBEKeySpec`, `KeyManagerFactory` —
por duas causas lidas do erro do leitor: `alg` usado como nome de objeto (mesmo defeito do
`OAEPParameterSpec` do *upstream*) e argumentos de predicado entre parênteses onde a gramática pede
colchetes. Enquanto os portões forem a única coisa que mede o `api30`, apagá-los perde cobertura.

**Adjudicações que mudaram de lado ao serem medidas** (13b.2). Uma execução de controle — o mesmo
`compare` com `--rules-dir` no `api30` — é o que tornou cada uma decidível:

- **`KeyPairSpec`**: o componente com o oráculo do portão emite `MOP_MORE_RESTRICTIVE` com testemunha
  **ε**, que é o achado do portão letra por letra. `api30` escreve `ORDER co?, …` e o *upstream*
  escreve `ORDER Con, …`. **A discordância é o oráculo**; os dois estão certos sobre o seu.
- **`CipherInputStreamSpec`**: controle `EQUIVALENT under N2`. O `c1` do `api30` é o construtor de um
  argumento, `protected` no android-30, e o *upstream* nem o declara. **Fato reproduzido; o veredito
  difere porque o componente internaliza a exceção (`Observability` + N2) que o portão guarda em
  `gate_allowlist.csv`.**
- **`MessageDigestSpec`**: sob o `api30` o componente **também** diz `MOP_MORE_RESTRICTIVE`. Logo o
  oráculo não é a causa: é D-20 — a letra recusada como `Unknown{OverlappingDispatch}` sai de
  `SpecModel.order`. Projetando-a para fora da regra também, volta a `EQUIVALENT`, o `pass` do portão.
  Mesma causa em `KeyPairGeneratorSpec` e `MacSpec`.
- **`KeyGeneratorSpec`** e **`SecureRandomSpec`**: a diferença é **N1**, que apaga exatamente as
  palavras com dois eventos criadores (`g1 g1`, `c1 c1`) que o portão exibe. Sob o `api30` o
  `SecureRandomSpec` sai `INCOMPARABLE`, isto é, com a direção do portão viva.
- **`CipherSpec`**: a testemunha do lado `.mop` do componente é
  `getInstance · init · update` — o `g1 i1 u1` do portão, letra por letra.

**13b.4 · o que fica fora do escopo do componente, dito explicitamente.** Sete dos nove portões
internos do `gh104_gates.py` (`G-2`, `G-2a`, `G-2b'`, `G-2c`, `G-2d`, `G-6'`, `G-ERE`) leem as linhas
de transição do **monitor gerado**; o componente lê o `.mop` e diz, na própria nota de M0, que
`M0.1` é um *proxy* de AST. Do `gh101`, `spelling_variants` (censo intralista, sem regra nenhuma) e
`changed_from_jca` (diff contra a semente congelada) não têm contraparte. O `gh104_baseline.py`
inteiro está fora: mede legibilidade de relatório de violação sobre CSVs de resultado de experimento
— e roda verde, byte a byte idêntico ao `data/gh104/baseline.json` commitado.

**13b.7 · cinco linhas acrescentadas a `data/jca_android/divergence_record.csv`**, `kind =
gate-scope`, `task = 13b.7`, nenhuma linha existente alterada (`git diff --stat`: `5 +++++`):
`SecretKeySpec.mop` (recusada por M0, INV-CONF-09 lhe nega M1–M4), `IvChainJunction.mop` (sem par),
`predicate_graph.csv` × 2 (a divisão `body`/`acceptance` com o nome do evento; a asserção
`read:condition-guard == 0`, que é a **única perda de cobertura** e não de refinamento) e
`MetaCrySL/generated/api30/` (as 13 regras ilegíveis). O `kind` novo foi acrescentado a `KINDS` e
`NARRATIVE_KINDS` de `scripts/gh104_divergence_record.py` — o vocabulário é fechado de propósito, e o
próprio arquivo diz que a resposta certa a uma categoria nova é nomeá-la, não forçá-la num nome
alheio. `data/jca_android/README.md` descreve esses *kinds* e não conhece `gate-scope`; é
somente-leitura aqui (INV-CONF-12) e a atualização ficou na issue #107.

**Suites depois das mudanças.** `uv run pytest --import-mode=importlib -o "addopts="` sobre os sete
arquivos `gh10*` de `tests/parity/`: **130 passed**. `tests/parity` inteiro: 176 passed, 3 failed, 7
errors — todas pré-existentes e alheias (tokens `reachesMop` do `aperv-tool`, um jar de baseline do
gator desatualizado, `ANDROID_SDK_HOME` ausente); nenhuma toca o `divergence_record.csv` nem o
`gh104_divergence_record.py`.

## Closing
G13b closes when 13b.1–13b.7 are `[x]`. Closing it with a gate marked *reproduced* but no follow-up
issue open means the retirement will be forgotten.

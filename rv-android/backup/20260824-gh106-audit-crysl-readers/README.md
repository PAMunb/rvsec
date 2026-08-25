# Leitores de CrySL da auditoria — aposentados pela gh106

**Retirados em** 2026-08-24, na change `gh106-mop-crysl-conformance`, tarefa G13a (13a.3).
**Origem** `audit/20260808_validacao_jca_android/` e `audit/20260820_verificacao_plano_predicados_v2/`.

## O que estes arquivos eram

São sete programas Python que consultavam as regras CrySL `api30` (`MetaCrySL/generated/api30/*.cryptsl`)
para decidir alguma coisa durante as auditorias de agosto de 2026. Cada um leu o oráculo do seu
jeito, e é exatamente essa multiplicidade que a gh106 encerra: um componente, um oráculo, um
mapeamento — em vez de sete leituras ad-hoc que ninguém consegue confrontar entre si.

| Arquivo (caminho de origem, relativo a `audit/`) | Linhas | O que fazia com a regra |
|---|---:|---|
| `20260808_validacao_jca_android/batchA/juiz_build_csv.py` | 129 | ancorava as resoluções do juiz do lote A em cláusulas de `.cryptsl` citadas |
| `20260808_validacao_jca_android/batchC/juiz_build_csv_batchC.py` | 297 | idem, lote C (`KeyStore.cryptsl:47` etc.) |
| `20260808_validacao_jca_android/batchD/juiz_build_csv_batchD.py` | 319 | idem, lote D (`Mac.cryptsl`, `MessageDigest.cryptsl`, `Signature.cryptsl`) |
| `20260808_validacao_jca_android/global/juizglobal_build.py` | 327 | a matriz de portões G0–G13 do juízo global, com o pareamento 22-para-22 regra↔spec |
| `20260808_validacao_jca_android/set/set_cons_build.py` | 828 | o consolidador da fase SET: registro de fenômenos e grafo de predicados |
| `20260820_verificacao_plano_predicados_v2/agentA/parse_cryptsl.py` | 116 | o único que **abre** os arquivos: `glob("*.cryptsl")` e extrai `ENSURES`/`REQUIRES` |
| `20260808_validacao_jca_android/batchD/alfa_language_check.py` | 361 | **fisicamente em `../20260824-gh106-audit-comparators/`** — é também comparador |
| **total** | **2 377** | |

A última linha é a duplicação anunciada no censo da G13a: `batchD/alfa_language_check.py` conta como
comparador e como leitor, mas existe uma vez só e mora no diretório irmão. Doze arquivos distintos
foram movidos ao todo (6 + 7 − 1).

## Sobre a regra de contagem — uma diferença que importa

A tarefa 13a.1 define *leitor* como "um arquivo Python que **abre** um `.crysl`/`.cryptsl`". Sob essa
leitura literal, **um só** dos sete qualifica: `parse_cryptsl.py`. Os outros seis não abrem regra
nenhuma — eles **citam** trechos de regra (`Mac.cryptsl:33-37`, `SSLContext.cryptsl`, `KeyStore.cryptsl:47`)
como fundamento textual do veredito que gravam em CSV. A regra foi lida por um humano ou por outro
agente, e o script carrega a leitura já consumada.

A regra operativa que reproduz o censo publicado (7 arquivos, 2 377 linhas por `wc -l`) é a mais
larga: *arquivo Python que nomeia um arquivo `.cryptsl`/`.crysl` como fonte da sua decisão*. Foi essa
que aplicamos, e a soma fecha exatamente. Ela é declarada aqui porque a diferença entre "abre" e
"cita" muda quais arquivos se movem, e RISK-013 do `risk-register.md` já antecipava essa ambiguidade.

Uma consequência dessa regra larga: `pilot/alfa_automata_check.py` também nomeia um `.cryptsl`
(`MetaCrySL/generated/api30/Cipher.cryptsl`) e, portanto, também seria leitor. Ele não muda o
resultado — já foi movido como comparador, para `../20260824-gh106-audit-comparators/`. Nenhum
arquivo ficou para trás por causa da ambiguidade; ela afeta apenas quem aparece em qual lista.

## Por que morreram

Vale o critério de `design.md` D-14: **o ad-hoc morre quando o componente reproduz o seu veredito,
não quando ele compila**. Aqui ele se aplica **vaziamente**, porque nada consome estes sete
arquivos — nenhum import, nenhum `workflow` do GitHub Actions, nenhum outro script os chama. São a
fotografia de auditorias encerradas, e as suas entradas (CSVs de rodada fechada, diretórios `gen_*`
regenerados por manifesto de hash) pertencem ao momento em que rodaram.

Os relatórios e CSVs que eles produziram continuam em `audit/`, e continuam citando estes scripts
pelo nome. Essas citações **não foram reescritas**: reescrever a proveniência de um registro de
auditoria congelado o faria mentir sobre como foi produzido. Quem seguir uma citação encontra o
arquivo aqui, com a estrutura de diretórios de origem preservada.

## Leitores e comparadores que ficaram de fora (13a.7-bis)

A regra da G13a é escopada a `audit/`. O varrimento pedido por 13a.7-bis encontrou, **fora** de
`audit/20260808_*`, os seguintes arquivos que satisfazem uma das duas definições. Nenhum foi movido;
a disposição de cada um fica registrada aqui.

### Leitores (abrem, de fato, um `.crysl`/`.cryptsl`)

| Arquivo | Linhas | Disposição e motivo |
|---|---:|---|
| `scripts/gh104_gates.py` | 1 900 | **mantido** — portão vivo (`RULE_EXTENSIONS = (".cryptsl", ".crysl")`); só morre sob o critério D-14, na G13b |
| `scripts/gh101_conformance_check.py` | 401 | **mantido** — portão vivo (`rules_dir / f"{rule}.cryptsl"`); mesmo critério |
| `scripts/gh101_predicate_edges.py` | 359 | **mantido** — portão vivo (`args.rules / f"{rule}.crysl"`); mesmo critério |
| `docs/handoff/20260822_arnes_verificacao_r6/scripts/ev.py` | 17 | **mantido** — evidência congelada de um handoff; não é código de produção nem portão |
| `docs/handoff/20260822_arnes_verificacao_r6/scripts/r1.py` | 33 | **mantido** — idem |
| `docs/handoff/20260824_arnes_adjudicacao/scripts/normalize_api30.py` | 48 | **mantido** — idem; é a normalização léxica `.cryptsl` → `.crysl` da adjudicação de 24/08 |

`scripts/gh104_message_gate.py` recebe um diretório de regras por `--crysl`, mas quem abre os
arquivos é `gh104_gates.py`, de quem ele importa o classificador. É consumidor de leitor, não leitor.

### Comparadores (analisam uma `ORDER` ou um `ere`/`fsm` e decidem)

| Arquivo | Linhas | Disposição e motivo |
|---|---:|---|
| `scripts/gh105_order_gate.py` | 1 171 | **mantido** — portão vivo; analisa a seção `ORDER` e o `fsm`/`alias match`; destino decidido na G13b |
| `scripts/gh104_gates.py` | 1 900 | **mantido** — analisa `^(ere\|fsm)\s*:`; portão vivo |
| `experimento-gh104/scripts/gh104_gates.py` | 1 087 | **mantido** — cópia congelada dos portões aplicada a uma campanha já gravada; o seu `"ORDER"` é um rótulo de categoria de resultado, não uma `ORDER` de CrySL analisada |
| `scripts/gh101_monitor_transition_check.py` | 109 | **mantido** — verifica INV-INS-110 sobre as linhas de transição do monitor **gerado**; não confronta CrySL |
| `audit/20260820_verificacao_plano_predicados_v2/agentB/analyze_mop.py` | 360 | **mantido** — localiza o bloco `fsm:`/`ere:` para análise **estrutural** do `.mop`; não decide conformidade contra `ORDER` |
| `backup/gh105-retired/gate-baseline/gh105_gate_baseline.py` | 279 | **sem ação** — já aposentado para `backup/` por uma change anterior |

## Como estes arquivos foram medidos

Contagem de linhas: `wc -l` sobre cada arquivo, no `HEAD` `39b000ce`, antes de qualquer movimento.
Predicado de leitor (regra larga, a que reproduz o censo):
`grep -rl -E "\.(cryptsl|crysl)\b" --include='*.py' audit/`.
Predicado de leitor (regra literal, "abre"): busca por `open`/`glob`/`read_text` cuja expressão de
caminho termina em `.cryptsl`/`.crysl`.

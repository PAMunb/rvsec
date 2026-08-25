# Comparadores de `ORDER` da auditoria de 2026-08-08 — aposentados pela gh106

**Retirados em** 2026-08-24, na change `gh106-mop-crysl-conformance`, tarefa G13a (13a.2).
**Origem** `audit/20260808_validacao_jca_android/` — a auditoria da tradução `jca_android`, encerrada.

## O que estes arquivos eram

São seis programas Python de uso único, escritos durante a auditoria de agosto de 2026 para
responder a uma pergunta que naquele momento não tinha ferramenta: *a linguagem que o monitor
JavaMOP aceita é a mesma que a `ORDER` da regra CrySL descreve?*

Cada um codifica, à mão, o autômato de referência de um punhado de regras `api30` sob a leitura A
(D-piloto-1, vírgula mais externa), transcreve o `fsm` da especificação `.mop` pareada, e compara as
duas linguagens em busca de um traço separador. O veredito de cada comparação virou uma linha dos
relatórios `alfa_report.md` de cada lote.

| Arquivo (caminho de origem, relativo a `audit/`) | Linhas | O que decidia |
|---|---:|---|
| `20260808_validacao_jca_android/batchA/alfa_automata_check.py` | 155 | cinco regras de construtor (DHG, HMC, PBE, IVP, SKS) |
| `20260808_validacao_jca_android/batchB/alfa_automata_check.py` | 328 | CIS, COS, KPR, SKY, PBK, incluindo os modelos multi-instância |
| `20260808_validacao_jca_android/pilot/alfa_automata_check.py` | 253 | o piloto: `Cipher` e `GCMParameterSpec`, com as leituras A e B da `ORDER` |
| `20260808_validacao_jca_android/batchC/alfa_language_check.py` | 303 | KGN, KMF, TMF, SSL, KST |
| `20260808_validacao_jca_android/batchD/alfa_language_check.py` | 361 | MAC, MDG, KPG, SRD, SIG |
| `20260808_validacao_jca_android/batchB/juiz_walk_batchB.py` | 130 | a caminhada do juiz sobre as tabelas de transição congeladas do lote B |
| **total** | **1 530** | |

`batchD/alfa_language_check.py` conta duas vezes no censo da G13a: além de comparador, ele é um dos
sete leitores de CrySL. Ele foi movido uma vez só, para cá; o `README.md` do diretório irmão
`../20260824-gh106-audit-crysl-readers/` o lista e aponta para este diretório.

## Por que morreram

O critério escrito em `design.md` D-14 é este: **o ad-hoc morre quando o componente reproduz o seu
veredito, não quando ele compila**. A gh106 constrói um componente de conformidade MOP–CrySL que
decide a mesma pergunta a partir de um oráculo único, versionado e testado, em vez de um autômato
transcrito à mão por lote.

Aqui, porém, o critério se aplica **de forma vaziamente satisfeita**: nada consome estes seis
arquivos. Eles não são importados por nenhum módulo, não aparecem em nenhum `workflow` do
GitHub Actions, não são chamados por nenhum outro script. São a fotografia de uma auditoria que
fechou — o registro de como um veredito foi obtido uma vez, em agosto de 2026, sobre artefatos
congelados por hash. Mantê-los em `audit/` sugeriria que ainda são executáveis contra a árvore
atual, e não são: as suas premissas (os `sha256` dos `*RuntimeMonitor.java` da rodada, os
diretórios `gen_<Spec>/out` regenerados a partir do `generation_manifest.md`) pertencem àquele
momento.

Movê-los para cá cedo, e não no fim da change, mantém o diff final da gh106 falando do componente
em vez de falar de remoções.

## O que continua valendo, e onde

Os **relatórios** da auditoria continuam em `audit/20260808_validacao_jca_android/` — os
`alfa_report.md`, os `alfa_claims.csv`, os pareceres do juiz e da refutação, os manifestos de hash.
Eles citam estes scripts pelo nome, como proveniência do número que publicam, e essas citações
**não foram reescritas**: um registro de auditoria congelado que passa a mentir sobre como foi
produzido vale menos que um registro que aponta para um arquivo mudado de lugar. Quem seguir uma
citação encontra o arquivo aqui, com o caminho de origem preservado na estrutura de diretórios.

Um comparador de `ORDER` continua vivo e em uso: `scripts/gh105_order_gate.py`. Ele não é fotografia
de auditoria — é um portão que se roda, e a G13b decide o seu destino quando o componente da gh106
reproduzir o seu veredito.

## Ressalva sobre o censo (registrada, não corrigida)

Sob a regra literal declarada em 13a.1 — *comparador = arquivo Python que analisa uma `ORDER` ou um
`ere`/`fsm` e decide sobre isso* —, os outros três `juiz_walk` da auditoria
(`batchA/juiz_walk.py`, `batchC/juiz_walk_batchC.py`, `batchD/juiz_walk_batchD.py`) também
qualificariam: os três analisam as tabelas `Prop_1_transition_*` dos monitores gerados e decidem
`PASS`/`FAIL` sobre elas; os de C e D chegam a rotular cada traço com o seu estado sob a `ORDER` da
regra pareada. O censo da G13a nomeia apenas `juiz_walk_batchB`, e a soma de 1 530 linhas fecha
exatamente com essa lista. Movemos a lista nomeada, não a lista que a regra literal produziria —
alargar o conjunto por conta própria seria improvisar sobre um censo que a tarefa manda conferir e
reportar. A divergência fica escrita aqui.

## Como estes arquivos foram medidos

Contagem de linhas: `wc -l` sobre cada arquivo, no `HEAD` `39b000ce`, antes de qualquer movimento.

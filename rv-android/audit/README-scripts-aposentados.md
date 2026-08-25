# Scripts de auditoria aposentados em 2026-08-24 (gh106, G13a)

Doze arquivos Python que viviam sob `audit/` foram movidos para `backup/` na change
`gh106-mop-crysl-conformance`. Nenhum relatório, CSV, parecer ou manifesto de hash desta árvore foi
reescrito por causa disso: um registro de auditoria encerrada que passa a mentir sobre como foi
produzido vale menos que um registro que aponta para um arquivo mudado de lugar. Este arquivo existe
para que qualquer citação daquelas peças continue resolvendo.

## Onde cada um foi parar

Os diretórios de destino espelham a estrutura abaixo de `audit/`, então o caminho citado nos
relatórios (`batchC/juiz_build_csv_batchC.py`, `global/juizglobal_build.py`, …) é o mesmo, só que sob
outra raiz.

**Comparadores de `ORDER` → `backup/20260824-gh106-audit-comparators/`**

- `20260808_validacao_jca_android/batchA/alfa_automata_check.py`
- `20260808_validacao_jca_android/batchB/alfa_automata_check.py`
- `20260808_validacao_jca_android/pilot/alfa_automata_check.py`
- `20260808_validacao_jca_android/batchC/alfa_language_check.py`
- `20260808_validacao_jca_android/batchD/alfa_language_check.py`
- `20260808_validacao_jca_android/batchB/juiz_walk_batchB.py`

**Leitores de CrySL → `backup/20260824-gh106-audit-crysl-readers/`**

- `20260808_validacao_jca_android/batchA/juiz_build_csv.py`
- `20260808_validacao_jca_android/batchC/juiz_build_csv_batchC.py`
- `20260808_validacao_jca_android/batchD/juiz_build_csv_batchD.py`
- `20260808_validacao_jca_android/global/juizglobal_build.py`
- `20260808_validacao_jca_android/set/set_cons_build.py`
- `20260820_verificacao_plano_predicados_v2/agentA/parse_cryptsl.py`

`batchD/alfa_language_check.py` conta nos dois censos — é comparador e leitor —, mas existe uma vez
só e está entre os comparadores.

## Por que foram aposentados

O critério está em `openspec/changes/gh106-mop-crysl-conformance/design.md`, decisão D-14: *o
comparador ad-hoc morre quando o componente de conformidade reproduz o seu veredito, não quando ele
compila*. Aqui o critério se cumpre de forma vazia — nada consome estes doze arquivos: nenhum
`import`, nenhum `workflow` do GitHub Actions, nenhum outro script. Eles decidiam, à mão e por lote,
a pergunta que a gh106 passa a responder a partir de um oráculo único.

O `README.md` de cada diretório de destino conta a história completa: o que cada arquivo decidia,
como o censo foi contado, e quais leitores e comparadores **não** foram movidos (os portões vivos em
`scripts/`, cujo destino a G13b decide).

## O que a integridade dos manifestos ainda garante

Os `sha256` publicados em `global/juizglobal_hashes.txt`, `batchD/alfa_hashes.txt`,
`set/set_cons_hashes.txt` e afins continuam válidos: os arquivos foram movidos com `git mv`, byte por
byte, sem uma linha alterada. Para reconferir um hash, calcule-o sobre o arquivo no seu novo caminho.

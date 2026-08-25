#!/usr/bin/env python3
"""O único lugar onde o corpus e os monitores desta campanha são nomeados.

NOVO nesta campanha, e a razão de ele existir é a mesma que a `comp162-ajc` registrou: os
caminhos do corpus e dos monitores **ainda não existem** quando o andaime do estágio 2 é
escrito. Eles nascem no fim dos estágios 0 e 1. Repetir um caminho que ainda não se conhece
em quatro scripts seria quatro lugares para o pesquisador editar e três para esquecer — e
um esquecido não falha: ele lê o corpus errado em silêncio.

Então cada caminho aparece aqui uma vez, marcado como PLACEHOLDER, e todo script o importa.

## O `corpus_basis` precisa de identificador próprio, e o digest sozinho não basta

O `corpus_basis` que o `RUN_START` ecoa tem duas partes, `<id>:<sha256>`, e o sha256 é o do
**conteúdo da lista de nomes** — não dos binários. Os 162 nomes desta campanha são
exatamente os 162 da `comp162`; o que muda são os bytes dos APKs, porque foram tecidos com
as specs novas. Ou seja: as duas listas podem ser byte-idênticas, e **o digest sozinho não
distingue as duas campanhas**. Quem distingue é o identificador.

Por isso `CORPUS_ID` é `selected162gh104` e não `selected162`, mesmo com o arquivo mantendo
o nome `selected162.txt` (decisão D-a do `CONTEXTO.md`, e o layout que o estágio 1 entrega).
Sem isso, as duas campanhas ficariam indistinguíveis na proveniência e o portão de corpus
do smoke passaria assim mesmo — foi exatamente o risco que a `comp162-ajc` registrou.

## Por que a resolução é por padrão, e não um literal fixo

O estágio 1 pode perder aplicações. Já perdeu uma na produção do corpus `dexlib2` da
`comp162` (`info.dvkr.screenstream_44000.apk`: `classes28.dex` com 65.521 dos 65.536
`method_ids`, e os wrappers não cabem), e o conjunto novo tem contagem de wrappers
diferente, então essa fronteira se move. O sufixo `selected<S>` do diretório é o que o
estágio 1 descobre. `dataset_dir()` casa o padrão e exige **exatamente um** resultado:
zero significa que o estágio 1 não terminou; mais de um significa que sobrou diretório
parcial de tentativa anterior, e nesse caso a escolha tem de ser do pesquisador e não de
um `sorted()[0]`.
"""

from __future__ import annotations

from pathlib import Path

# A raiz dos datasets. `APKS/` guarda os 348 originais não instrumentados — é a entrada do
# estágio 1, e é contra eles que se prova por sha256 que a tecelagem de fato aconteceu.
DATASET_ROOT = Path("/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET")
ORIGINAL_APKS = DATASET_ROOT / "APKS"

# PLACEHOLDER — o corpus da campanha de referência, tecido com as specs `jca`. Não é o
# nosso corpus; entra aqui porque duas coisas o usam: a herança da partição (os nomes vêm
# de lá) e a cópia dos `.apk.json`, que esta campanha reusa para manter o denominador de
# `cov_mop` idêntico nos dois lados.
REFERENCE_DATASET = (
    DATASET_ROOT / "APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162"
)

# PLACEHOLDER — o corpus desta campanha. O diretório só existe depois do estágio 1; o
# `<S>` final é o número de sobreviventes, que é justamente o que o estágio 1 descobre.
CORPUS_GLOB = "APKS_INSTRUMENTED_jca_android_gh104_selected*"
CORPUS_DIR_ESPERADO = DATASET_ROOT / "APKS_INSTRUMENTED_jca_android_gh104_selected162"

# A lista de nomes vive dentro do próprio diretório do corpus. O nome do ARQUIVO é o mesmo
# da `comp162` porque é o layout que o estágio 1 entrega; o que dá identidade própria ao
# corpus é o `CORPUS_ID` abaixo, que entra no `corpus_basis` antes do digest.
CORPUS_LIST_NAME = "selected162.txt"
CORPUS_ID = "selected162gh104"

# Os monitores gerados no estágio 0 a partir das specs novas, congelados com digest e
# consumidos pelas fatias do estágio 1 por cópia. A geração NÃO é paralelizável: o JavaMOP
# estagia os `.rvm` num diretório compartilhado e o gerador os MOVE de lá, então N gerações
# concorrentes se roubam e o lote sai tecido sem monitores, reportando sucesso. Gerar uma
# vez e congelar aqui é o que impede isso.
#
# O diretório mora dentro da própria campanha (e não no dataset) porque é o layout que o
# runbook do estágio 0 entrega — ver `instrumentacao/README.md`.
MONITORS_DIR = Path(__file__).resolve().parents[1] / "monitores" / "monitors_master" / "monitors"


class CorpusPending(RuntimeError):
    """O estágio 1 ainda não produziu o corpus, ou produziu mais de um candidato."""


def dataset_dir(explicit: str | Path | None = None) -> Path:
    """O diretório do corpus. Levanta `CorpusPending` enquanto não houver exatamente um.

    Um caminho explícito (`--corpus`) vence o padrão, mas ainda tem de existir: passar um
    diretório inexistente é erro do operador, não pendência do estágio 1, e a mensagem
    distingue os dois casos.
    """
    if explicit is not None:
        p = Path(explicit)
        if not p.is_dir():
            raise CorpusPending(f"o corpus passado em --corpus não existe: {p}")
        return p
    hits = sorted(p for p in DATASET_ROOT.glob(CORPUS_GLOB) if p.is_dir())
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise CorpusPending(
            f"nenhum diretório casa {DATASET_ROOT}/{CORPUS_GLOB} — o corpus instrumentado "
            f"com as specs novas ainda não existe.\n"
            f"       O estágio 1 (instrumentação dexlib2 no host) precisa rodar antes; ver "
            f"CONTEXTO.md §2 e instrumentacao/.\n"
            f"       Esperado, quando os 162 sobreviverem: {CORPUS_DIR_ESPERADO}"
        )
    raise CorpusPending(
        "mais de um candidato a corpus gh104; escolher qual e remover os outros:\n  "
        + "\n  ".join(str(h) for h in hits)
    )


def corpus_list(dataset: Path) -> Path:
    """A lista de nomes do corpus: `selected162.txt` dentro do próprio diretório."""
    p = dataset / CORPUS_LIST_NAME
    if p.is_file():
        return p
    raise CorpusPending(
        f"{CORPUS_LIST_NAME} ausente em {dataset} — o estágio 1 a escreve ao montar o "
        f"corpus de entrega, e sem ela não há `corpus_basis` a calcular"
    )


def read_names(listing: Path) -> list[str]:
    """Os nomes de APK de uma lista, ignorando linhas de comentário.

    A lista pode abrir com uma linha `#` declarando a origem do corpus. Ela é inerte para
    o `--apks-filter`, que casa por basename, mas quem lê a lista como conjunto de nomes
    precisa descartá-la — do contrário o comentário viraria um APK inexistente.
    """
    return [
        ln.strip()
        for ln in listing.read_text().splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]

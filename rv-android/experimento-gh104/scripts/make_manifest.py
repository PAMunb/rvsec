#!/usr/bin/env python3
"""Gera o `manifest.json` da gh104 a partir da fonte de verdade, nunca por transcrição.

    uv run python experimento-gh104/scripts/make_manifest.py
    uv run python experimento-gh104/scripts/make_manifest.py --image-id sha256:...

ADAPTADO de `../../experimento-comp162/scripts/make_manifest.py`, com a mecânica de
`get_variants()` **inalterada**. O que mudou: o nome da campanha, o `compared_against`
(agora a `comp162`, que é o lado "antes" do par), o `spec_set`, o
`instrumentation_variant`, o bloco `monitors` (aqui os monitores são NOVOS, gerados no
estágio 0), e a tolerância a corpus e monitores ainda inexistentes.

A mecânica dos braços não pode mudar uma linha. As definições vêm de
`ApeRVTool.get_variants()` — o módulo é a autoridade sobre o que cada braço é, e
transcrever os pesos à mão para um JSON criaria uma segunda cópia que envelhece em
silêncio. Como as duas campanhas serão pareadas braço a braço, as definições têm de ser
byte-a-byte as mesmas nos dois manifestos; do contrário o pareamento compararia braços
diferentes com o mesmo nome.

O manifesto existe para que o pre-flight e a verificação possam perguntar "o run que
aconteceu é o run que foi planejado?" contra um artefato, e não contra a memória de quem
escreveu o compose. `smoke_gates.py` lê dele o `corpus_basis` e a tag da imagem;
`consolidate.py` lê dele os braços e o número de containers; `cycle.sh` lê dele o total de
identidades.

## O que nasce nulo, e por quê

- `image.id` — só existe depois do `docker build`. Esta campanha **constrói imagem nova**
  (`0.9.3-gh104`), então não há id de outra campanha para herdar: a gh104 mexe em Java
  (`rvsec-core`, `rv-monitor`), em Python (parser, transporte, `result_processor`) e nas
  specs, e só o rebuild completo cobre os três.
- `corpus.*` — o corpus é produto do estágio 1. Enquanto não existir, os campos saem
  marcados `pendente-estagio-1` e `predicted_identities` sai nulo.
- `monitors.digest` — os monitores são produto do estágio 0.

Rodar o script de novo depois de cada estágio preenche o que faltava.

## O `corpus_basis` impresso é o que vai para os composes

Os dois `docker-compose*.yml` carregam `SUBSTITUIR_APOS_MONTAR_CORPUS` no `@corpus_basis=`
do `RV_TOOLS` até que este script imprima o valor real.

Ele tem duas partes, `<id>:<sha256>`, e o sha256 é o do **conteúdo da lista de nomes**.
Como os 162 nomes são exatamente os da `comp162`, as duas listas podem ser byte-idênticas
e o digest **não** distingue as campanhas. Quem distingue é o identificador, que aqui é
`selected162gh104` (`corpus.CORPUS_ID`, decisão D-a do `CONTEXTO.md`). Trocar isso por
`selected162` faria as duas campanhas se passarem uma pela outra na proveniência que o
`RUN_START` ecoa, com o portão de corpus do smoke passando assim mesmo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parent

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "modules" / "aperv-tool" / "src"))
from aperv_tool.tools.aperv.tool import ApeRVTool  # noqa: E402
from corpus import (  # noqa: E402
    CORPUS_ID,
    MONITORS_DIR,
    CorpusPending,
    corpus_list,
    dataset_dir,
    read_names,
)

# A campanha de referência: o lado "antes", com as specs `jca`. O CSV é o de aplicações
# ADMISSÍVEIS, e não o `per_apk_paired.csv` cru, porque é ele que já passou pela regra de
# admissibilidade — e é a mesma regra, byte-idêntica, que julga este lado.
COMPARED_AGAINST = "experimento-comp162/consolidado/per_apk_admissivel.csv"

# Imagem NOVA. Não sobrescrever a tag `0.9.3`: ela é a identidade da imagem que reproduz a
# comp162, e apagá-la tornaria a campanha de referência irreproduzível.
IMAGE_TAG = "phtcosta/rvandroid:0.9.3-gh104"

REPS = 3
TIMEOUT = 300
CONTAINERS = 8
SPEC_SET = "jca_android"
INSTRUMENTATION_VARIANT = "dexlib2"

# Mapeia a chave Python do `overrides` para a chave `ape.properties` que o RUN_START ecoa.
# É a mesma tabela de `APERV_PROPERTY_MAPPING`, restrita ao que estes dois braços usam;
# importá-la inteira traria 40 chaves irrelevantes para o manifesto.
PROPERTY_KEY = {
    "mop_activity_source_components": "ape.mopActivitySourceComponents",
    "frontier_boost_weight": "ape.frontierBoostWeight",
    "mop_frontier_weight": "ape.mopFrontierWeight",
    "activity_trigger_enabled": "ape.activityTriggerEnabled",
    "mop_weight_direct": "ape.mopWeightDirect",
    "mop_weight_transitive": "ape.mopWeightTransitive",
    "mop_weight_open_menu": "ape.mopWeightOpenMenu",
    "mop_weight_wtg": "ape.mopWeightWtg",
}

ARM_ROLE = {
    "mop_on_llm_off": "reference",
    "mop_off_llm_off": "control",
}


def aperv_arm(variant: str, role: str) -> dict:
    v = ApeRVTool.get_variants()[variant]
    return {
        "role": role,
        "tool": "aperv",
        "variant": variant,
        "preset": v["preset"],
        "strategy": v["strategy"],
        "mop_data": v.get("mop_data"),
        "expected_params": {
            PROPERTY_KEY[k]: val
            for k, val in v["overrides"].items()
            if k in PROPERTY_KEY
        },
    }


def monitors_block(explicit: str | None) -> dict:
    """Os monitores do estágio 0, com digest por arquivo e um digest do conjunto.

    Aqui os monitores são **novos**, gerados das specs `jca_android` — a `comp162` reusou
    os do `jca`, e é justamente essa diferença que a campanha estuda. Registrar os digests
    transforma "a campanha foi tecida destes monitores" de afirmação em fato verificável,
    e é o que permite provar depois que o corpus do estágio 1 e o piloto do gate de
    dispositivo saíram do MESMO conjunto.

    O `dexlib2` consome o descritor `MultiSpec_1MonitorAspect.json` e o
    `MultiSpec_1RuntimeMonitor.java`; o `.aj` fica no diretório sem ser usado por esta
    rota, e é registrado assim mesmo porque o digest do conjunto tem de descrever o
    diretório inteiro que as fatias copiaram.
    """
    d = Path(explicit) if explicit else MONITORS_DIR
    if not d.is_dir():
        return {"dir": str(d), "digest": None, "files": {}, "pendencia": "estagio-0"}
    files = sorted(p for p in d.iterdir() if p.is_file())
    per_file = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    joint = hashlib.sha256(
        "".join(f"{per_file[n]}  {n}\n" for n in sorted(per_file)).encode()
    ).hexdigest()
    return {"dir": str(d), "digest": joint, "files": per_file}


def corpus_block(explicit: str | None) -> tuple[dict, int | None]:
    """O bloco `corpus` e o número de APKs — ou os marcadores de pendência."""
    try:
        dataset = dataset_dir(explicit)
        listing = corpus_list(dataset)
    except CorpusPending as e:
        return {
            "dataset_dir": "pendente-estagio-1",
            "subset_file": "pendente-estagio-1",
            "apk_count": None,
            "corpus_basis": "pendente-estagio-1",
            "pendencia": str(e),
        }, None

    apks = sorted(p.name for p in dataset.glob("*.apk"))
    listed = read_names(listing)
    if sorted(listed) != apks:
        raise SystemExit(f"FALHA: {listing.name} não descreve o conteúdo de {dataset}")
    digest = hashlib.sha256(listing.read_bytes()).hexdigest()
    # `CORPUS_ID`, e não `listing.stem`: o arquivo se chama `selected162.txt` nas duas
    # campanhas e pode ter bytes idênticos, então o stem não daria identidade nenhuma.
    return {
        "dataset_dir": str(dataset),
        "subset_file": str(listing),
        "apk_count": len(apks),
        "corpus_basis": f"{CORPUS_ID}:{digest}",
    }, len(apks)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(EXP / "manifest.json"))
    ap.add_argument("--image-id", default=None, help="sha256:... da imagem construída")
    ap.add_argument("--corpus", default=None, help="diretório do corpus instrumentado novo")
    ap.add_argument("--monitors", default=None, help="diretório dos monitores do estágio 0")
    args = ap.parse_args()

    corpus, n_apks = corpus_block(args.corpus)
    monitors = monitors_block(args.monitors)

    manifest = {
        "campaign": "gh104",
        "purpose": (
            "A grade da comp162 sobre o conjunto de especificações novo (jca_android) da "
            "change gh104. Corrida pareada em que o conjunto de specs é o único fator que "
            "varia. Mede se a violação passou a dizer o que aconteceu; NÃO é o experimento "
            "final do Estudo 03."
        ),
        "compared_against": COMPARED_AGAINST,
        "instrumentation_variant": INSTRUMENTATION_VARIANT,
        "image": {"tag": IMAGE_TAG, "id": args.image_id},
        "build": {"rvsec_branch": "modules", "ape_rv_jar": "bind-mount local"},
        "corpus": corpus,
        "monitors": monitors,
        "reps": REPS,
        "timeout": TIMEOUT,
        "containers": CONTAINERS,
        "spec_set": SPEC_SET,
        "arms": [
            # O braço `ape` é o builtin do rv-tools, servido pelo `ape.jar` comitado no
            # repositório — não pelo `ape-rv.jar`. Ele não emite RUN_START, então nada
            # nele é verificável por manifesto; entra aqui para que a contagem de
            # identidades feche e para declarar de onde vem o binário.
            {"role": "baseline", "tool": "ape", "variant": None,
             "jar": "modules/rv-tools/src/rv_tools/builtin/ape/ape.jar"},
            aperv_arm("mop_off_llm_off", ARM_ROLE["mop_off_llm_off"]),
            aperv_arm("mop_on_llm_off", ARM_ROLE["mop_on_llm_off"]),
        ],
        "predicted_identities": (n_apks * 3 * REPS) if n_apks else None,
    }

    Path(args.out).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"escrito {args.out}")
    print(f"  corpus_basis = {manifest['corpus']['corpus_basis']}")
    print(f"  identidades previstas = {manifest['predicted_identities']}")
    print(f"  monitores (digest do conjunto) = {manifest['monitors']['digest']}")
    if n_apks is None:
        print("  corpus pendente — rodar de novo depois do estágio 1")
    else:
        print("  COLAR o corpus_basis acima no @corpus_basis= de docker-compose.yml e")
        print("  docker-compose.smoke.yml, no lugar de SUBSTITUIR_APOS_MONTAR_CORPUS")
    if manifest["monitors"]["digest"] is None:
        print("  monitores pendentes — rodar de novo depois do estágio 0")
    if args.image_id is None:
        print("  image.id = null — preencher após o `docker build` da 0.9.3-gh104")
    return 0


if __name__ == "__main__":
    sys.exit(main())

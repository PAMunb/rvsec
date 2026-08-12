#!/usr/bin/env python3
"""Gera o `manifest.json` da comp162 a partir da fonte de verdade, nunca por transcrição.

As definições dos braços vêm de `ApeRVTool.get_variants()` — o módulo é a autoridade sobre
o que cada braço é, e transcrever os pesos à mão para um JSON criaria uma segunda cópia
que envelhece em silêncio. O manifesto existe para que o pre-flight e a verificação possam
perguntar "o run que aconteceu é o run que foi planejado?" contra um artefato, e não contra
a memória de quem escreveu o compose.

Duas chaves nascem nulas e são preenchidas depois, porque dependem de coisas que ainda não
existem no momento em que o manifesto é gerado:

- `image.id` — só existe depois do `docker build`.
- `corpus_basis` — o sha256 da lista, recomputado aqui a cada geração.

Uso:
    python3 scripts/make_manifest.py --out manifest.json
    python3 scripts/make_manifest.py --out manifest.json --image-id sha256:...
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

sys.path.insert(0, str(ROOT / "modules" / "aperv-tool" / "src"))
from aperv_tool.tools.aperv.tool import ApeRVTool  # noqa: E402

DATASET = Path(
    "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET"
    "/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162"
)
CORPUS_LIST = DATASET / "selected162.txt"
CORPUS_ID = "selected162"
IMAGE_TAG = "phtcosta/rvandroid:0.9.3-comp162"

REPS = 3
TIMEOUT = 300
CONTAINERS = 8

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(EXP / "manifest.json"))
    ap.add_argument("--image-id", default=None, help="sha256:... da imagem construída")
    args = ap.parse_args()

    apks = sorted(p.name for p in DATASET.glob("*.apk"))
    listed = [ln.strip() for ln in CORPUS_LIST.read_text().splitlines() if ln.strip()]
    if sorted(listed) != apks:
        print("FALHA: selected162.txt não descreve o conteúdo do diretório", file=sys.stderr)
        return 1

    digest = hashlib.sha256(CORPUS_LIST.read_bytes()).hexdigest()

    manifest = {
        "campaign": "comp162",
        "purpose": (
            "Ensaio da instrumentação nova (experimento-FINAL_selected162) na grade do "
            "cmp163. NÃO é o experimento final do Estudo 03."
        ),
        "compared_against": "data/results/cmp163_consolidado/per_apk_paired.csv",
        "image": {"tag": IMAGE_TAG, "id": args.image_id},
        "build": {"rvsec_branch": "modules", "ape_rv_jar": "bind-mount local"},
        "corpus": {
            "dataset_dir": str(DATASET),
            "subset_file": str(CORPUS_LIST),
            "apk_count": len(apks),
            "corpus_basis": f"{CORPUS_ID}:{digest}",
        },
        "reps": REPS,
        "timeout": TIMEOUT,
        "containers": CONTAINERS,
        "spec_set": "jca",
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
        "predicted_identities": len(apks) * 3 * REPS,
    }

    Path(args.out).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"escrito {args.out}")
    print(f"  corpus_basis = {manifest['corpus']['corpus_basis']}")
    print(f"  identidades previstas = {manifest['predicted_identities']}")
    if args.image_id is None:
        print("  image.id = null — preencher após o `docker build`")
    return 0


if __name__ == "__main__":
    sys.exit(main())

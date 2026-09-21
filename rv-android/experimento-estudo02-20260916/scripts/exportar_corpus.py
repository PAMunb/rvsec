#!/usr/bin/env python3
"""Monta a pasta de APKs que a campanha monta nos containers, a partir do rvsec-dataset.

    uv run python experimento-estudo02-20260916/scripts/exportar_corpus.py           # só confere
    uv run python experimento-estudo02-20260916/scripts/exportar_corpus.py --apply   # confere e copia

Com DATASET já povoado, o `--apply` não copia: confere cada arquivo que está lá contra os
manifestos da fonte e regrava o `MANIFEST.sha256`. Foi esse o caminho de 16/09, quando a cópia
foi feita à mão antes deste script rodar.

Nenhuma change dos dois repositórios é dona desta etapa. A change `reinstrument-jca-android`
termina em `rvsec-dataset/jca_android/` (`instrumented_apks/`, `static_analysis/`, manifestos,
`dataset.csv`); a estudo02 montou uma cópia feita à mão desses arquivos. Este script faz a mesma
cópia, com as conferências que a mão não fazia.

## Por que cópia, e não o diretório do rvsec-dataset direto

O rvsec-dataset apaga `instrumented_apks/` antes de reinstrumentar. Montar o diretório de lá
amarraria uma campanha de quatro dias a um diretório que outra change pode regravar no meio
dela. Hardlink tem o mesmo defeito quando a regravação é feita no mesmo inode. A cópia custa
cerca de 4 GB no mesmo disco.

## O que reprova (cada item bloqueia o --apply)

1. O corpus é a lista `funnel_stage == harvested` do `dataset.csv` (N₄). Se ela diferir da
   estudo02, o script mostra quem entrou e quem saiu e reprova: mudar a composição do corpus é
   um segundo fator, e a decisão é do responsável pela campanha (`--aceitar-corpus`).
2. Cada APK tem o seu `.apk` em `instrumented_apks/` e o seu `.apk.json` em `static_analysis/`,
   e o sha256 de cada um bate com `manifests/instrumented.sha256` e
   `manifests/static_analysis.sha256`. Manifesto desatualizado quer dizer reinstrumentação
   pela metade.
3. **Todo `.apk` difere do da estudo02.** Os consertos da gh114 mudam o tecido de todo APK
   (o runtime `rvsec-core` embarcado ganha a classe `Evidence`); um APK byte-idêntico é APK
   que não foi reinstrumentado. A referência **não são os arquivos**: a cópia de 16/09 caiu na
   mesma pasta que a estudo02 montou e sobrescreveu os `.apk` dela. O que compara é o
   `manifests/instrumented.sha256` daquela instrumentação, lido do git do rvsec-dataset na
   revisão `ESTUDO02_MANIFEST_REV`.
4. **Todo `.apk.json` é igual ao da estudo02.** A análise estática não é refeita (ela lê o APK
   original). Um JSON diferente mudaria a covariável do modelo e o denominador de cobertura
   em silêncio. Também se confere por manifesto: o `static_analysis.sha256` de hoje tem de ser
   igual ao daquela mesma revisão.
5. O commit do rvsec gravado em `manifests/instrument_provenance.json` contém
   `RVSEC_MIN_COMMIT` (a gh115, que vem depois da gh114).
"""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campanha import ENV, ROOT  # noqa: E402

SRC = Path(ENV["DATASET_SRC"])
DST = Path(ENV["DATASET"])
OLD_CORPUS = ROOT / ENV["ESTUDO02_CORPUS"]
OLD_REV = ENV["ESTUDO02_MANIFEST_REV"]
RVSEC_REPO = ROOT.parent

fails = []


def check(ok, msg, detail=()):
    print(f"[{'PASS' if ok else 'FAIL'}] {msg}")
    for d in detail:
        print(f"        {d}")
    if not ok:
        fails.append(msg)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_git(rev: str, path: str) -> dict:
    """Manifesto de uma revisão do rvsec-dataset, sem tocar na árvore de trabalho."""
    r = subprocess.run(["git", "-C", str(SRC.parent), "show", f"{rev}:{path}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return {}
    out = {}
    for line in r.stdout.splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            out[name.strip()] = digest
    return out


def manifest(path: Path) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            out[name.strip()] = digest
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="copia para DATASET se tudo passar")
    ap.add_argument("--aceitar-corpus", action="store_true",
                    help="aceita um N₄ com composição diferente da estudo02 (decisão registrada)")
    args = ap.parse_args()

    rows = list(csv.DictReader((SRC / "dataset.csv").open(newline="")))
    corpus = sorted(r["apk"] for r in rows if r["funnel_stage"] == "harvested")
    old = sorted(OLD_CORPUS.read_text().split())
    entrou, saiu = sorted(set(corpus) - set(old)), sorted(set(old) - set(corpus))
    mesmo = not entrou and not saiu
    check(mesmo or args.aceitar_corpus,
          f"corpus N₄ = {len(corpus)} ({'mesma composição da estudo02' if mesmo else 'composição MUDOU'})",
          [f"entrou: {a}" for a in entrou] + [f"saiu:   {a}" for a in saiu])

    prov_path = SRC / "manifests" / "instrument_provenance.json"
    prov = json.loads(prov_path.read_text())
    commit = prov.get("rvsec_commit_in_image", "")
    minimo = ENV["RVSEC_MIN_COMMIT"]
    if not minimo:
        check(False, "RVSEC_MIN_COMMIT vazio em campanha.env — preencher com o commit da gh115")
    else:
        r = subprocess.run(["git", "-C", str(RVSEC_REPO), "merge-base", "--is-ancestor", minimo, commit],
                           capture_output=True)
        check(r.returncode == 0,
              f"proveniência da instrumentação: rvsec {commit[:8]} ({prov.get('image_tag')}) contém {minimo}",
              [f"gravada em {prov.get('recorded_at')} por {prov.get('task')}"])

    inst = manifest(SRC / "manifests" / "instrumented.sha256")
    sa = manifest(SRC / "manifests" / "static_analysis.sha256")
    faltam, sha_apk, sha_json = [], [], []
    for apk in corpus:
        a, j = SRC / "instrumented_apks" / apk, SRC / "static_analysis" / f"{apk}.json"
        if not a.exists() or not j.exists():
            faltam.append(apk)
            continue
        da, dj = sha256(a), sha256(j)
        if inst.get(apk) != da:
            sha_apk.append(apk)
        if sa.get(f"{apk}.json") != dj:
            sha_json.append(apk)
    check(not faltam, f"todo APK tem .apk e .apk.json na fonte ({len(corpus) - len(faltam)}/{len(corpus)})",
          faltam[:10])
    check(not sha_apk, f".apk bate com manifests/instrumented.sha256 ({len(sha_apk)} divergentes)", sha_apk[:10])
    check(not sha_json, f".apk.json bate com manifests/static_analysis.sha256 ({len(sha_json)} divergentes)",
          sha_json[:10])

    # Portões 3 e 4 por manifesto. Os .apk da estudo02 foram sobrescritos pela cópia de 16/09,
    # então o que discrimina é o manifesto daquela instrumentação, que o git do rvsec-dataset
    # guarda em ESTUDO02_MANIFEST_REV. O .apk.json não foi tocado e o manifesto dele nem mudou
    # de revisão: a igualdade dos dois manifestos é a própria garantia do portão 4.
    old_inst = manifest_git(OLD_REV, "jca_android/manifests/instrumented.sha256")
    old_sa = manifest_git(OLD_REV, "jca_android/manifests/static_analysis.sha256")
    if not old_inst or not old_sa:
        check(False, f"não consegui ler os manifestos da estudo02 em {OLD_REV} (git do rvsec-dataset)")
    else:
        iguais_old = [a for a in corpus if inst.get(a) == old_inst.get(a)]
        json_mudou = [a for a in corpus if sa.get(f"{a}.json") != old_sa.get(f"{a}.json")]
        check(not iguais_old,
              f"todo .apk difere do da estudo02 ({len(iguais_old)} byte-idênticos, contra {OLD_REV})",
              iguais_old[:10])
        check(not json_mudou,
              f"todo .apk.json é igual ao da estudo02 ({len(json_mudou)} diferentes, contra {OLD_REV})",
              json_mudou[:10])

    listing = "\n".join(corpus) + "\n"
    print(f"\ncorpus sha256 (mesma regra do corpus.txt do gen_compare): "
          f"{hashlib.sha256(listing.encode()).hexdigest()[:16]}")

    if fails:
        print(f"\nEXPORTAÇÃO REPROVADA — {len(fails)} FAIL; nada copiado")
        return 1
    if not args.apply:
        print("\nconferência OK — rode com --apply para copiar")
        return 0
    # DST povoado quer dizer cópia já feita (foi o caso de 16/09, à mão). Não se copia por cima:
    # confere o que está lá contra os manifestos da fonte e regrava o MANIFEST.sha256.
    ja_existe = DST.exists() and any(DST.iterdir())
    DST.mkdir(parents=True, exist_ok=True)
    linhas, corrompidos, ausentes = [], [], []
    esperado = {**inst, **sa}
    for apk in corpus:
        for src in (SRC / "instrumented_apks" / apk, SRC / "static_analysis" / f"{apk}.json"):
            alvo = DST / src.name
            if ja_existe:
                if not alvo.exists():
                    ausentes.append(src.name)
                    continue
            else:
                shutil.copy2(src, alvo)
            digest = sha256(alvo)
            if digest != esperado[src.name]:
                corrompidos.append(src.name)
            linhas.append(f"{digest}  {src.name}")
    if ausentes:
        print(f"!! {len(ausentes)} arquivo(s) do corpus faltando em {DST}: {ausentes[:10]}")
        return 1
    (DST / "MANIFEST.sha256").write_text("\n".join(linhas) + "\n")
    verbo = "conferidos em" if ja_existe else "copiados para"
    print(f"\n{len(corpus)} .apk + {len(corpus)} .apk.json {verbo} {DST}")
    if corrompidos:
        print(f"!! {len(corrompidos)} arquivo(s) com sha256 diferente na cópia: {corrompidos[:10]}")
        return 1
    print(f"sha256 da cópia bate com os manifestos da fonte: {DST / 'MANIFEST.sha256'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

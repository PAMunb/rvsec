#!/usr/bin/env python3
"""REPAIR — devolve à fila as identidades que a admissibilidade reprovou. Não toca em APK.

    # 1. ver o que seria feito (não muta nada)
    uv run python experimento-estudo02-20260916/scripts/repair.py estudo02-20260916_00

    # 2. aplicar (o tasks.json é escrito como root pelo container; daí o docker)
    docker run --rm -u 0 -v "$PWD:/w" -w /w --entrypoint python3 \
        phtcosta/rvandroid:0.9.4 experimento-estudo02-20260916/scripts/repair.py --apply estudo02-20260916_00

A regra de julgamento **não mora aqui**: vem inteira de `admissibility.py`. Uma identidade
julgada por regra diferente entre o relatório e o reparo viraria diferença de spec na leitura
final, sem ninguém notar. Este script só executa a consequência.

## O que ele faz, e só

Reescreve o estado de uma identidade inadmissível para `ERROR` **depois** de preservar os
artefatos dela, para que o resume comum a re-execute. É o que faz o resume, que já recupera a
falha barulhenta, recuperar também a silenciosa: um emulador que morreu no meio é gravado
`COMPLETED` com `error_message` vazio, e sem isto chegaria ao consolidador indistinguível de um
run íntegro.

A preservação vem **antes** da reescrita porque a re-execução escreve nos mesmos nomes de
arquivo: sem ela, consertar o defeito destruiria a evidência dele no mesmo ato.

## O que ele nunca faz

- **Nunca exclui, remove ou filtra APK.** Reparo é sobre identidade, e a decisão de tirar uma
  aplicação da análise é do responsável pela campanha. O `admissibility.py` reporta candidatas;
  ninguém age sobre elas sem aprovação.
- **Nunca devolve à fila o zero estrutural do `qtesting`.** São 19 APKs cujo `aapt` não emite
  `launchable-activity`, e repetir produz o mesmo zero — 171 identidades entrando em laço e o C6
  jamais fechando.
- **Nunca devolve à fila o lançamento fora do app.** A família droidbot que entrou por uma
  activity de outro app (o LeakCanary da `org.wikipedia_50595`) escolhe a mesma entrada em todo
  run (`admissibility.py`, cabeçalho).
- **Nunca devolve à fila a parada da ferramenta.** Célula em que as três réplicas pararam abaixo
  do piso com o marcador da própria ferramenta no traço: repetir reproduz a parada. Fica na
  análise como categoria declarada (`admissibility.py`, cabeçalho).
- **Nunca repara a mesma identidade duas vezes por conta própria.** Identidade com dois ou mais
  registros já passou por re-execução; repará-la de novo arriscaria laço infinito se a causa for
  determinística do par (APK, braço). Esses casos saem como `REVISAR`. A decisão humana de tentar
  outra vez entra por `--rerun apk,braço,rep,orçamento` (repetível): só as identidades nomeadas
  são tocadas, e só se continuarem inadmissíveis fora de categoria declarada. Os artefatos de cada
  tentativa ficam lado a lado em `backup/` (`<nome>`, `<nome>.2`, …).

      uv run python experimento-estudo02-20260916/scripts/repair.py estudo02-20260916_00 \
          --rerun com.gelakinetic.mtgfam_99.apk,ares,1,300
- **Nunca escreve no `tasks.json` de container vivo.** A escrita do container é atômica
  (tmp→fsync→rename) e reescrever por fora perde a corrida com ela. O script confere e recusa.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import admissibility as adm  # noqa: E402  (precisa do sys.path acima)

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "data" / "results"
BACKUP_DIR = ROOT / "backup" / f"{adm.campanha.NAME}-inadmissiveis"
HOST_UID, HOST_GID = 1000, 1000


def identity(cfg: dict) -> tuple:
    """A identidade do resume: `platform.py` usa apk/name/variant/rep/timeout, e só."""
    tc = cfg.get("tool_config") or {}
    return (cfg.get("apk_name"), tc.get("name"), tc.get("variant"),
            cfg.get("repetition"), cfg.get("timeout"))


def verdict_key(cfg: dict) -> tuple:
    """A chave do `admissibility.judge()`: o braço já colapsado."""
    tc = cfg.get("tool_config") or {}
    return (cfg.get("apk_name"), adm.arm_label(tc.get("name"), tc.get("variant")),
            cfg.get("repetition"), cfg.get("timeout"))


def is_running(cid: str) -> bool | None:
    """`True`/`False`, ou `None` quando não dá para saber (docker fora de alcance)."""
    try:
        r = subprocess.run(["docker", "inspect", cid, "--format", "{{.State.Running}}"],
                           capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() == "true"


def preserve(result: dict, cid: str, apply: bool) -> list[str]:
    """Copia logcat/trace para `backup/`. Devolve o que foi (ou seria) copiado.

    A re-execução escreve nos mesmos nomes, então a cópia de uma tentativa posterior ganha
    sufixo `.2`, `.3`, … em vez de apagar a evidência da anterior."""
    saved, dest = [], BACKUP_DIR / cid
    for key in ("logcat_file", "trace_file"):
        rel = result.get(key)
        if not rel:
            continue
        base = adm.artifact(cid, rel)
        for src in (base, base.with_name(base.name + ".ndjson.gz")):
            if not src.exists():
                continue
            target, n = dest / src.name, 2
            while target.exists():
                target, n = dest / f"{src.name}.{n}", n + 1
            saved.append(target.name)
            if apply:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
    return saved


def chown_tree(path: Path) -> None:
    """Devolve ao usuário do host o que foi escrito como root dentro do container."""
    if os.geteuid() != 0 or not path.exists():
        return
    for p in [path, *path.rglob("*")]:
        try:
            os.chown(p, HOST_UID, HOST_GID)
        except OSError:
            pass


def repair_container(cid: str, verdicts: dict, apply: bool, rerun: set[tuple]) -> dict:
    """Com `rerun` vazio, julga o container inteiro; com `rerun`, toca só as identidades nomeadas
    (chave do `verdict_key`) e dispensa para elas a regra dos dois registros."""
    tasks_file = RESULTS / cid / cid / "tasks.json"
    if not tasks_file.exists():
        return {"cid": cid, "missing": True}

    doc = json.loads(tasks_file.read_text())
    records = doc["tasks"] if isinstance(doc, dict) else doc

    by_identity: dict[tuple, list[dict]] = {}
    for rec in records:
        by_identity.setdefault(identity(rec.get("config") or {}), []).append(rec)

    repaired, review, already, structural, refused = [], [], [], [], []
    for ident, recs in by_identity.items():
        key = verdict_key(recs[0].get("config") or {})
        if rerun and key not in rerun:
            continue
        v = verdicts.get(key)
        if v is None or v.admissible:
            if rerun:
                refused.append((key, "admissível" if v else "sem veredicto"))
            continue
        if v.structural or v.tool_stop or v.foreign_launcher:
            structural.append(ident)
            if rerun:
                refused.append((key, "em categoria declarada"))
            continue

        completed = [r for r in recs if (r.get("result") or {}).get("state") == "COMPLETED"]
        if not completed:
            already.append(ident)   # já está ERROR; o resume comum alcança
            continue
        if len(recs) >= 2 and not rerun:
            review.append((ident, v))
            continue

        best = completed[-1]
        result = best["result"]
        saved = preserve(result, cid, apply)
        if apply:
            result["state"] = "ERROR"
            result["error_message"] = (
                f"inadmissível ({'+'.join(v.fails)}): {v.tool_seconds}s de ferramenta num "
                f"orçamento de {v.timeout}s; devolvida à fila por experimento-estudo02-20260916/scripts/repair.py"
            )
        repaired.append((ident, v, len(saved)))

    if apply and repaired:
        tmp = tasks_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, indent=2))
        os.replace(tmp, tasks_file)
        chown_tree(BACKUP_DIR)

    return {"cid": cid, "repaired": repaired, "review": review,
            "already": already, "structural": structural, "refused": refused}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("containers", nargs="+")
    ap.add_argument("--apply", action="store_true", help="sem isto, nada é mutado")
    ap.add_argument("--assume-stopped", action="store_true",
                    help="segue mesmo sem conseguir consultar o docker (use com cuidado)")
    ap.add_argument("--rerun", action="append", default=[], metavar="APK,BRAÇO,REP,ORÇAMENTO",
                    help="decisão humana: devolve à fila só esta identidade, mesmo com dois ou mais registros")
    args = ap.parse_args()
    rerun = set()
    for spec in args.rerun:
        apk, arm, rep, timeout = spec.split(",")
        rerun.add((apk, arm, int(rep), int(timeout)))

    # Recusa antes de qualquer leitura pesada: container vivo reescreve por baixo.
    for cid in args.containers:
        st = is_running(cid)
        if st is True:
            print(f"!! {cid} está RODANDO — pare o container antes de reparar. Nada foi feito.")
            return 2
        if st is None and args.apply and not args.assume_stopped:
            print(f"!! não consegui consultar o docker sobre {cid}. Confirme que ele está "
                  f"parado e repita com --assume-stopped. Nada foi feito.")
            return 2

    verdicts = adm.judge(args.containers, read_artifacts=True)
    if not verdicts:
        print("!! nenhuma identidade lida — confira os containers e os caminhos de resultado")
        return 1

    n_rep = n_rev = n_alr = n_str = 0
    for cid in args.containers:
        out = repair_container(cid, verdicts, args.apply, rerun)
        if out.get("missing"):
            print(f"{cid}: sem tasks.json")
            continue
        for key, why in out["refused"]:
            print(f"{cid}: RECUSADA {key[0]} {key[1]} rep{key[2]} {key[3]}s — {why}; nada feito")
        for ident, v, n_saved in out["repaired"]:
            verb = "reparada" if args.apply else "reparável"
            arm = adm.arm_label(ident[1], ident[2])
            print(f"{cid}: {verb} {ident[0]} {arm} rep{ident[3]} {ident[4]}s — "
                  f"{'+'.join(v.fails)}, {v.tool_seconds}s de ferramenta "
                  f"({n_saved} artefatos preservados)")
        for ident, v in out["review"]:
            arm = adm.arm_label(ident[1], ident[2])
            print(f"{cid}: REVISAR {ident[0]} {arm} rep{ident[3]} {ident[4]}s — "
                  f"{'+'.join(v.fails)} após {v.records} tentativas")
        n_rep += len(out["repaired"])
        n_rev += len(out["review"])
        n_alr += len(out["already"])
        n_str += len(out["structural"])

    print()
    print(f"resumo: {n_rep} {'reparadas' if args.apply else 'a reparar'}, "
          f"{n_rev} para revisar, {n_alr} já em ERROR (o resume alcança), "
          f"{n_str} em categoria declarada — zero estrutural, parada da ferramenta, "
          f"lançamento fora do app (não voltam à fila)")
    print("nenhum APK foi excluído, filtrado ou removido — isso não é atribuição deste script")
    return 0


if __name__ == "__main__":
    sys.exit(main())

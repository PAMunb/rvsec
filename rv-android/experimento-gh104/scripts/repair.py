#!/usr/bin/env python3
"""REPAIR — rede de segurança para tasks da gh104 que terminaram antes do orçamento.

CÓPIA de `../../experimento-comp162/scripts/repair.py`. Mudaram o diretório de backup e a
tag da imagem no exemplo de uso; a lógica é a mesma, e tem de ser, porque um run truncado
julgado por regra diferente entre as duas campanhas viraria diferença de spec na leitura.

Aqui o script é uma **rede de segurança, não o mecanismo**. A imagem `0.9.3-gh104` carrega
a guarda
INV-APV-60 (`c1d28365`): uma exploração que volta mais de `APERV_TEARDOWN_GRACE_S` antes
do orçamento levanta `RVToolExecutionError` no momento em que trunca, o `rv-platform`
grava `ERROR`, e o resume comum recupera a identidade sem operador nenhum. Antes da guarda,
truncamento chegava ao consolidador indistinguível de run íntegro, e este script era o
único caminho de recuperação.

Ele continua aqui por duas razões. A guarda cobre o caminho de retorno da ferramenta; ela
não cobre um run cujo emulador morreu de um jeito que ainda produz retorno limpo. E se ela
falhar, o silêncio é o mesmo de antes — uma checagem redundante que nunca dispara custa
uma passada de leitura por ciclo.

Julga **por identidade** `(apk, tool, variant, rep, timeout)`, nunca por registro: o resume
ACRESCENTA um registro em vez de sobrescrever, então uma varredura por registro recontaria
toda recuperação já feita.

Uma identidade é reparada **no máximo uma vez**. Se já tem dois ou mais registros, já passou
por re-execução; repará-la de novo arriscaria laço infinito caso a causa seja determinística
do par (APK, braço) — que foi exatamente o caso do `com.starry.myne_500` na cmp163, truncando
aos 168 s e aos 169 s em duas execuções separadas por nove horas. Esses casos saem como
`REVISAR` e ficam para decisão humana.

Só processa containers passados na linha de comando, e o chamador passa apenas os que **não
estão rodando**: reescrever o `tasks.json` de um container vivo perde a corrida com a escrita
atômica dele.

Uso (o `tasks.json` é escrito como root; daí o docker):
    python3 scripts/repair.py gh104_00 gh104_01          # dry run
    docker run --rm -u 0 -v "$PWD:/w" -w /w --entrypoint python3 \
        phtcosta/rvandroid:0.9.3-gh104 scripts/repair.py --apply gh104_00
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# 300 s de orçamento menos APERV_TEARDOWN_GRACE_S (45 s) — o mesmo piso que a guarda
# INV-APV-60 aplica de dentro da ferramenta, lido aqui do lado de fora.
BUDGET_S = 300
TEARDOWN_GRACE_S = 45
COMPLETION_FLOOR_S = BUDGET_S - TEARDOWN_GRACE_S

EXP = Path(__file__).resolve().parents[1]
RESULTS = EXP / "results"
BACKUP_DIR = EXP.parent / "backup" / "gh104-truncated"
HOST_UID, HOST_GID = 1000, 1000


def identity(cfg: dict) -> tuple:
    tc = cfg.get("tool_config") or {}
    return (
        cfg.get("apk_name"),
        tc.get("name"),
        tc.get("variant"),
        cfg.get("repetition"),
        cfg.get("timeout"),
    )


def host_path(container_path: str, cid: str) -> Path:
    """Traduz `results/<cid>/...` (visão do container) para o caminho no host.

    O volume mapeia `results/<cid>` sobre `/opt/rvsec/rv-android/results`, e o experimento
    escreve em `results/<cid>/...` relativo ao workdir — daí o `<cid>` aparecer duas vezes
    no host e o prefixo `results/` sair fora.
    """
    rest = container_path.removeprefix("results/")
    return RESULTS / cid / rest


def preserve(result: dict, cid: str, apply: bool) -> list[str]:
    """Copia logcat/trace/ndjson para backup/. Devolve o que foi (ou seria) copiado.

    A preservação vem ANTES da reescrita porque a re-execução escreve nos mesmos nomes de
    arquivo: sem isto, consertar o defeito destruiria a evidência dele no mesmo ato.
    """
    saved = []
    dest = BACKUP_DIR / cid
    for key in ("logcat_file", "trace_file"):
        p = result.get(key)
        if not p:
            continue
        for src in (host_path(p, cid), host_path(p + ".ndjson.gz", cid)):
            if not src.exists():
                continue
            saved.append(src.name)
            if apply:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest / src.name)
    return saved


def chown_tree(path: Path) -> None:
    """Devolve ao usuário do host o que foi escrito como root dentro do container."""
    if os.geteuid() != 0 or not path.exists():
        return
    for p in [path, *path.rglob("*")]:
        os.chown(p, HOST_UID, HOST_GID)


def repair_container(cid: str, apply: bool) -> dict:
    tasks_file = RESULTS / cid / cid / "tasks.json"
    if not tasks_file.exists():
        return {"cid": cid, "missing": True}

    doc = json.loads(tasks_file.read_text())
    records = doc["tasks"] if isinstance(doc, dict) else doc

    by_identity: dict[tuple, list[dict]] = {}
    for rec in records:
        by_identity.setdefault(identity(rec.get("config") or {}), []).append(rec)

    repaired, review, errors = [], [], []
    for ident, recs in by_identity.items():
        completed = [r for r in recs if (r.get("result") or {}).get("state") == "COMPLETED"]
        if not completed:
            errors.append(ident)  # o resume comum já alcança estes
            continue
        best = completed[-1]
        result = best["result"]
        elapsed = result.get("execution_time_seconds") or 0
        if elapsed >= COMPLETION_FLOOR_S and not result.get("error_message"):
            continue
        if len(recs) >= 2:
            review.append((ident, elapsed, len(recs)))
            continue
        saved = preserve(result, cid, apply)
        if apply:
            result["state"] = "ERROR"
            result["error_message"] = (
                f"C2: run returned after {elapsed}s of a {BUDGET_S}s budget "
                f"(floor {COMPLETION_FLOOR_S}s); requeued by scripts/repair.py"
            )
        repaired.append((ident, elapsed, len(saved)))

    if apply and repaired:
        tmp = tasks_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, indent=2))
        os.replace(tmp, tasks_file)
        chown_tree(BACKUP_DIR)

    return {"cid": cid, "repaired": repaired, "review": review, "errors": errors}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("containers", nargs="+")
    ap.add_argument("--apply", action="store_true", help="sem isto, nada é mutado")
    args = ap.parse_args()

    total_repaired = total_review = total_errors = 0
    for cid in args.containers:
        out = repair_container(cid, args.apply)
        if out.get("missing"):
            print(f"{cid}: sem tasks.json")
            continue
        for ident, elapsed, n_saved in out["repaired"]:
            verb = "reparada" if args.apply else "reparável"
            arm = ident[2] or ident[1]
            print(f"{cid}: {verb} {ident[0]} {arm} rep{ident[3]} — {elapsed}s "
                  f"({n_saved} artefatos preservados)")
        for ident, elapsed, n in out["review"]:
            arm = ident[2] or ident[1]
            print(f"{cid}: REVISAR {ident[0]} {arm} rep{ident[3]} — {elapsed}s após {n} tentativas")
        total_repaired += len(out["repaired"])
        total_review += len(out["review"])
        total_errors += len(out["errors"])

    print(
        f"resumo: {total_repaired} truncadas {'reparadas' if args.apply else 'a reparar'}, "
        f"{total_review} para revisar, {total_errors} já em ERROR (o resume alcança)"
    )
    if total_repaired == 0 and total_review == 0:
        print("(zero é o resultado esperado: a guarda INV-APV-60 na imagem já requeue "
              "truncamento no ato)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

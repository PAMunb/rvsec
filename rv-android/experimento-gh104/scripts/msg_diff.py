#!/usr/bin/env python3
"""Compara violações E mensagens entre duas campanhas — a era antiga e a era gh104.

    uv run python experimento-gh104/scripts/msg_diff.py \
        --run-a experimento-comp162     --prefix-a comp162 \
        --run-b experimento-gh104-piloto --prefix-b gh104p \
        --label-a jca --label-b jca_android \
        --specs-a "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca" \
        --specs-b "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android"

## A pergunta

O `mop_diff.py` da comp162ajc pergunta se dois substratos de instrumentação encontram as
mesmas violações, e para isso joga a mensagem fora de propósito: lá a mensagem carrega o
valor concreto observado (`but found TLS`), que varia com a execução e não com o sítio, e
mantê-la na identidade transformaria uma violação em duas.

Aqui a mensagem é **o objeto de estudo**. A change gh104 existe porque 72,93 % dos registros
publicados dizem literalmente `unknown` e mais 8.843 terminam em `but found .` — sem valor
observado. A pergunta desta comparação é dupla:

1. **o conjunto de violações mudou?** (a pergunta antiga, herdada do `mop_diff.py`)
2. **para as violações que os dois lados enxergam, o relato ficou legível?** (a nova)

Por isso a mensagem entra como **dimensão separada** da identidade, e não dentro dela: a
identidade continua sendo o sítio, e a mensagem é um atributo que se compara *dado* o sítio.
Sem essa separação as duas perguntas se contaminam — uma mensagem reescrita apareceria como
violação nova, que é exatamente o falso positivo que arruinaria a leitura.

## A identidade de uma violação

    (apk, spec, classe, método, tipo_de_erro)

Sem descritor de assinatura: o runtime resolve o sítio por `StackTraceElement`, que não
carrega descritor, então assinatura não é observável no logcat. União sobre braços e
réplicas — a pergunta é "o substrato chegou a expor esta violação alguma vez", não "expõe
por run".

## Por que o logcat, e não o `errors.csv`

O `errors.csv` muda de esquema entre as duas eras (11 → 13 colunas, task 5.6 da gh104) e
qualquer leitor único ou rejeita um dos lados ou mente sobre o outro. O logcat cru é o
mesmo artefato nas duas eras: `RVSEC: spec,classe,classeSimples,metodo,fonte,tipo,mensagem`,
com a mensagem ocupando tudo depois da sexta vírgula (o envelope v1 da gh104 também contém
vírgulas, e o corte em 6 é o que os quatro consumidores canônicos já fazem).

## Legibilidade

`ilegível` == a mensagem é `unknown` ou termina em `but found .`. São os dois modos de falha
que a gh104 mede e promete eliminar. Um envelope `v=1 code=… val='TLS' exp='TLSv1.2'` não
casa com nenhum dos dois e conta como legível.

Um mesmo sítio pode emitir mensagens diferentes ao longo de braços e réplicas (valores
observados distintos). O representante do lado é a mensagem **mais frequente** — desempate
lexicográfico —, e o número de sítios com mais de uma mensagem distinta é impresso, para
que essa variação seja vista em vez de absorvida em silêncio.

## Atribuição de causa

Uma violação vista de um lado e não do outro, na gh104, tem quatro explicações — uma a mais
que no `mop_diff.py`, porque aqui **quatro coisas mudam ao mesmo tempo** (allow-lists,
mensagens, autômatos e regime de predicados):

- **exploracao** — o lado cego nunca executou aquele (classe, método). Não diz nada sobre o
  conjunto de specs; é a variabilidade normal de teste aleatório. Árbitro: `RVSEC-COV`.
- **instrumentacao** — o lado cego executou o método e mesmo assim não acusou, com a spec
  inalterada entre os dois conjuntos. Sobra o substrato.
- **spec** — executou, não acusou, **e** a spec mudou (nova, removida ou redefinida). É a
  causa que a gh104 espera ver, e desde a reancoragem D-15 (2026-08-24) ela vai nas duas
  direções: uma allow-list que deixou de acusar `TLS`, `X509` ou `AndroidKeyStore` produz
  isto, e uma que **voltou** a acusar `MD5`, `SHA-1`, `SSL`, `NONEwithRSA` ou `AES/ECB`
  produz o simétrico. Ambos são `spec`, e o lado que muda diz qual.
- **indeterminado** — o método é `<init>`/`<clinit>`. A cobertura diverge entre `ajc` e
  `dexlib2` justamente aí (0 % contra 27,2 %), então "não aparece na cobertura" é vacuamente
  verdadeiro e não distingue nada.

`spec` só é atribuída quando `--specs-a`/`--specs-b` são informados; sem eles todo
`spec_status` é `desconhecida` e a causa nunca aparece. Limite conhecido: a cobertura é
consultada **antes** da mudança de spec, então uma spec removida cujo método ninguém
executou sai como `exploracao`. É a ordem conservadora — cobertura é observação, mudança de
spec é hipótese.

O diretório do run A é tratado como **somente leitura**: este script nunca escreve lá.
"""

from __future__ import annotations

import argparse
import csv
import glob
import gzip
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# `RVSEC: <Spec>,<classe>,<classeSimples>,<metodo>,<fonte>,<TipoErro>,<mensagem>`.
# A âncora `Spec,` é a do mop_diff.py e vale para `jca` e `jca_android` (o conjunto novo é
# semeado byte a byte do frozen, logo herda os nomes). Linhas `RVSEC:` que NÃO casam são
# contadas e reportadas, para que uma renomeação de spec falhe alto em vez de sumir.
VIOL = re.compile(r"\bRVSEC\s*:\s*([A-Za-z0-9_$]+Spec,.+)$")
# A tag sozinha, para reconhecer uma linha de violação que o `VIOL` NÃO decompôs.
RVSEC_TAG = re.compile(r"\bRVSEC\s*:")
# `RVSEC-COV: <pacote.Classe: tipoRetorno metodo(args)>`
COV = re.compile(r"<([^:>]+):\s*\S+\s+([^(\s]+)\(")
# The payload's 7th field (the message) contains commas of its own — every
# `String.join(",", allowList)` produces some, and so does the v1 envelope. Splitting at
# most this many times keeps the message verbatim.
PAYLOAD_SPLITS = 6
CTOR = ("<init>", "<clinit>")

# The two failure modes gh104 measures and promises to remove.
MUTE_MESSAGE = "unknown"
MUTE_SUFFIX = "but found ."

# Declarations whose divergence between the two campaigns threatens comparability. The
# `spec_set` is here to be *seen* diverging: it is the factor under study.
GUARD_FACTS = ("spec_set", "image_id", "reps", "timeout", "corpus_basis", "arms")
# The spec set is expected to differ; warning about it as if it were an accident would
# train the reader to ignore the whole block.
EXPECTED_TO_DIFFER = ("spec_set",)

# `<apk>__<rep>__<timeout>__<braco>.logcat`
ARM_FIELD = 3
ARM_FIELDS_MIN = 4

# The spec declaration opens at column 0: `TrustManagerFactorySpec(TrustManagerFactory mf) {`
SPEC_DECL = re.compile(r"^([A-Za-z_$][A-Za-z0-9_$]*)\s*\(", re.MULTILINE)


# --------------------------------------------------------------------------- leitura


def _open_text(path: str):
    """Abre o logcat, transparente a gzip.

    Runs arquivados são às vezes comprimidos no lugar, mantendo o sufixo `.logcat`, então o
    discriminador é o número mágico e não o nome.
    """
    with open(path, "rb") as probe:
        gz = probe.read(2) == b"\x1f\x8b"
    if gz:
        return gzip.open(path, "rt", errors="ignore")
    return open(path, errors="ignore")


def _logcats(run: Path, prefix: str) -> list[str]:
    return sorted(glob.glob(f"{run}/results/{prefix}_*/{prefix}_*/*.apk/*.logcat"))


def _apks_of(files: list[str]) -> set[str]:
    return {os.path.basename(os.path.dirname(f)) for f in files}


def _read_side(files: list[str], apks: set[str]):
    """-> (viol, cov, nfiles, unmatched)

    `viol[apk][ident] = {"arms": {braço}, "msgs": Counter(mensagem)}` — a mensagem fica FORA
    da identidade e ao lado dela, que é a diferença desta comparação para o `mop_diff.py`.
    `cov[apk] = {(classe, metodo)}`.
    """
    viol: dict = defaultdict(lambda: defaultdict(lambda: {"arms": set(), "msgs": Counter()}))
    cov: dict = defaultdict(set)
    nfiles = 0
    unmatched = 0
    for lc in files:
        apk = os.path.basename(os.path.dirname(lc))
        if apk not in apks:
            continue
        parts = os.path.basename(lc)[: -len(".logcat")].split("__")
        if len(parts) < ARM_FIELDS_MIN:
            continue
        arm = parts[ARM_FIELD]
        nfiles += 1
        with _open_text(lc) as fh:
            for ln in fh:
                if "RVSEC" not in ln:
                    continue
                if "RVSEC-COV" in ln:
                    m = COV.search(ln)
                    if m:
                        cov[apk].add((m.group(1), m.group(2)))
                    continue
                m = VIOL.search(ln.rstrip("\n"))
                if not m:
                    if RVSEC_TAG.search(ln):
                        unmatched += 1
                    continue
                f = m.group(1).split(",", PAYLOAD_SPLITS)
                if len(f) <= PAYLOAD_SPLITS:
                    unmatched += 1
                    continue
                rec = viol[apk][(f[0], f[1], f[3], f[5])]
                rec["arms"].add(arm)
                rec["msgs"][f[6].strip()] += 1
    return viol, cov, nfiles, unmatched


# ------------------------------------------------------------------- guarda / manifesto


def _load_meta(run: Path, prefix: str) -> dict | None:
    """`manifest.json`, ou o `*_compare_meta.json` que o rv-platform escreve."""
    man = run / "manifest.json"
    if man.exists():
        return json.loads(man.read_text())
    for cand in sorted(run.glob(f"{prefix}*_compare_meta.json")) or sorted(
        run.glob("*_compare_meta.json")
    ):
        return json.loads(cand.read_text())
    return None


def _facts(meta: dict | None) -> dict:
    """Normaliza os dois esquemas de manifesto para os mesmos seis fatos.

    O `manifest.json` das campanhas declara tudo explicitamente; o `*_compare_meta.json` do
    rv-platform embute o `corpus_basis` dentro da string da ferramenta e não declara
    `spec_set` nem `image.id`. O que falta vira `None` e não gera aviso — ausência de
    declaração não é divergência.
    """
    if not meta:
        return dict.fromkeys(GUARD_FACTS)
    arms = meta.get("arms")
    if isinstance(arms, list) and arms and isinstance(arms[0], dict):
        arms = [a["tool"] if not a.get("variant") else f"{a['tool']}:{a['variant']}" for a in arms]
    elif isinstance(meta.get("tools"), list):
        arms = [str(t).split("@", 1)[0] for t in meta["tools"]]
    basis = (meta.get("corpus") or {}).get("corpus_basis")
    if basis is None:
        found = re.search(r"corpus_basis=(\S+)", json.dumps(meta))
        basis = found.group(1) if found else None
    return {
        "spec_set": meta.get("spec_set"),
        "image_id": (meta.get("image") or {}).get("id"),
        "reps": meta.get("reps"),
        "timeout": meta.get("timeout"),
        "corpus_basis": basis,
        "arms": "|".join(sorted(arms)) if arms else None,
    }


def _guard(fa: dict, fb: dict, la: str, lb: str) -> None:
    """Avisa alto sobre divergência de declaração. Nunca aborta: quem aborta é o corpus."""
    print("=== guarda de comparabilidade ===")
    for k in GUARD_FACTS:
        a, b = fa[k], fb[k]
        if a is None or b is None:
            print(f"  {k:14s} {la}={a if a is not None else '(não declarado)'}  "
                  f"{lb}={b if b is not None else '(não declarado)'}")
        elif a == b:
            print(f"  {k:14s} = {a}")
        elif k in EXPECTED_TO_DIFFER:
            print(f"  {k:14s} DIVERGE (esperado — é o fator em estudo): {la}={a}  {lb}={b}")
        else:
            print(f"  !!! {k:14s} DIVERGE: {la}={a}  {lb}={b}")
    print("  Divergência fora do fator em estudo confunde a leitura: o que mudar além do")
    print("  conjunto de specs entra como causa rival de toda diferença abaixo.")


# ------------------------------------------------------------------------ diff de specs


def _spec_names(specs_dir: Path) -> dict[str, str]:
    """`nome declarado da spec -> sha256 do arquivo`.

    O nome vem do corpo do `.mop`, não do arquivo: `IvParameterSpec.mop` declara
    `IvParameterSpecSpec`, e é esse nome que aparece no logcat.
    """
    out: dict[str, str] = {}
    for p in sorted(specs_dir.glob("*.mop")):
        raw = p.read_bytes()
        m = SPEC_DECL.search(raw.decode("utf-8", errors="ignore"))
        out[m.group(1) if m else p.stem] = hashlib.sha256(raw).hexdigest()
    return out


def _spec_status(sa: dict[str, str] | None, sb: dict[str, str] | None) -> dict[str, str]:
    """`spec -> {inalterada, nova, removida, redefinida}`; vazio quando não há os dois lados."""
    if sa is None or sb is None:
        return {}
    status = {}
    for name in set(sa) | set(sb):
        if name not in sb:
            status[name] = "removida"
        elif name not in sa:
            status[name] = "nova"
        else:
            status[name] = "inalterada" if sa[name] == sb[name] else "redefinida"
    return status


# ------------------------------------------------------------------------- mensagens


def _mute(msg: str) -> bool:
    m = msg.strip()
    return m == MUTE_MESSAGE or m.endswith(MUTE_SUFFIX)


def _representative(msgs: Counter) -> str:
    """A mensagem mais frequente do sítio; desempate lexicográfico para ser determinístico."""
    if not msgs:
        return ""
    return min(msgs.items(), key=lambda kv: (-kv[1], kv[0]))[0]


def _msg_status(a: str, b: str) -> str:
    if a == b:
        return "igual"
    if _mute(a) and not _mute(b):
        return "ilegivel_para_legivel"
    if not _mute(a) and _mute(b):
        return "legivel_para_ilegivel"
    return "so_texto_mudou"


# ------------------------------------------------------------------------------ saída


def _table(title: str, counts: Counter, width: int = 26) -> None:
    print(f"\n=== {title} ===")
    for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {k:{width}s} {v:6d}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-a", required=True, type=Path)
    ap.add_argument("--prefix-a", required=True)
    ap.add_argument("--run-b", required=True, type=Path)
    ap.add_argument("--prefix-b", required=True)
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--specs-a", type=Path, help="diretório de .mop do lado A")
    ap.add_argument("--specs-b", type=Path, help="diretório de .mop do lado B")
    ap.add_argument("--out", type=Path, help="default: <run-b>/consolidado/")
    args = ap.parse_args()

    run_a, run_b = args.run_a.resolve(), args.run_b.resolve()
    la, lb = args.label_a, args.label_b
    out = (args.out or run_b / "consolidado").resolve()
    # Run A is an already-published campaign: writing anything into it would silently
    # rewrite the artefact this comparison is measured against.
    if out == run_a or run_a in out.parents:
        sys.exit(f"FALHA: --out {out} cairia dentro do run A ({run_a}), que é somente leitura")

    # A guarda vem antes de tudo: se as duas campanhas não são comparáveis, ler 85 mil
    # linhas de cobertura para descobrir isso é desperdício e, pior, produz um CSV que
    # parece bom.
    fa, fb = _facts(_load_meta(run_a, args.prefix_a)), _facts(_load_meta(run_b, args.prefix_b))
    _guard(fa, fb, la, lb)

    files_a, files_b = _logcats(run_a, args.prefix_a), _logcats(run_b, args.prefix_b)
    apks_a, apks_b = _apks_of(files_a), _apks_of(files_b)
    apks = apks_a & apks_b
    if not apks:
        sys.exit(
            f"FALHA: corpus disjunto — {la} tem {len(apks_a)} APK(s), {lb} tem {len(apks_b)}, "
            "interseção vazia. Não há o que comparar."
        )
    print(f"\nAPKs: {la}={len(apks_a)}  {lb}={len(apks_b)}  no escopo (nos dois)={len(apks)}")

    a_viol, a_cov, a_n, a_bad = _read_side(files_a, apks)
    b_viol, b_cov, b_n, b_bad = _read_side(files_b, apks)
    print(f"logcats lidos: {la}={a_n}  {lb}={b_n}")
    if a_bad or b_bad:
        print(f"!!! linhas RVSEC não reconhecidas: {la}={a_bad}  {lb}={b_bad} — o formato do "
              "payload ou o nome das specs mudou; a leitura abaixo está incompleta")

    specs = _spec_status(
        _spec_names(args.specs_a) if args.specs_a else None,
        _spec_names(args.specs_b) if args.specs_b else None,
    )
    if not specs:
        print("spec_status: desconhecida (sem --specs-a/--specs-b) — a causa `spec` não será "
              "atribuída, e divergências causadas por mudança de spec sairão como "
              "`instrumentacao`")

    rows = []
    multi_msg_a = multi_msg_b = 0
    for apk in sorted(apks):
        ra, rb = a_viol.get(apk, {}), b_viol.get(apk, {})
        for v in sorted(set(ra) | set(rb)):
            lado = "ambos" if (v in ra and v in rb) else ("so_A" if v in ra else "so_B")
            st = specs.get(v[0], "desconhecida")
            if lado == "ambos":
                causa = "-"
            elif v[2] in CTOR:
                causa = "indeterminado"
            else:
                # Quem NÃO viu a violação: executou o método?
                blind = b_cov if lado == "so_A" else a_cov
                if (v[1], v[2]) not in blind.get(apk, set()):
                    causa = "exploracao"
                elif st in ("nova", "removida", "redefinida"):
                    causa = "spec"
                else:
                    causa = "instrumentacao"

            ma = _representative(ra[v]["msgs"]) if v in ra else ""
            mb = _representative(rb[v]["msgs"]) if v in rb else ""
            if v in ra and len(ra[v]["msgs"]) > 1:
                multi_msg_a += 1
            if v in rb and len(rb[v]["msgs"]) > 1:
                multi_msg_b += 1

            rows.append(dict(
                apk=apk, spec=v[0], classe=v[1], metodo=v[2], tipo_erro=v[3],
                lado=lado, causa=causa, spec_status=st,
                msg_status=_msg_status(ma, mb) if lado == "ambos" else "-",
                msg_a=ma, msg_b=mb,
                arms_a="|".join(sorted(ra[v]["arms"])) if v in ra else "",
                arms_b="|".join(sorted(rb[v]["arms"])) if v in rb else "",
            ))

    if not rows:
        sys.exit("FALHA: nenhuma violação nos dois lados — nada a comparar")

    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "msg_diff.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    n = Counter(r["lado"] for r in rows)
    print(f"\n=== identidades (apk, spec, classe, metodo, tipo) — so_A={la}, so_B={lb} ===")
    print(f"  {la}={n['ambos'] + n['so_A']}  {lb}={n['ambos'] + n['so_B']}  "
          f"ambos={n['ambos']}  so_A={n['so_A']}  so_B={n['so_B']}")

    for lado in ("so_A", "so_B"):
        sub = [r for r in rows if r["lado"] == lado]
        c = Counter(r["causa"] for r in sub)
        detalhe = "  ".join(f"{k}={v}" for k, v in sorted(c.items())) or "(nenhuma)"
        print(f"  causa {lado} ({len(sub)}): {detalhe}")

    _table("spec_status das identidades", Counter(r["spec_status"] for r in rows))
    _table("msg_status (só identidades em ambos)",
           Counter(r["msg_status"] for r in rows if r["lado"] == "ambos"))
    print(f"  sítios com >1 mensagem distinta: {la}={multi_msg_a}  {lb}={multi_msg_b} "
          "(representante = a mais frequente)")

    mute_a = sum(1 for r in rows if r["msg_a"] and _mute(r["msg_a"]))
    mute_b = sum(1 for r in rows if r["msg_b"] and _mute(r["msg_b"]))
    tot_a = sum(1 for r in rows if r["msg_a"])
    tot_b = sum(1 for r in rows if r["msg_b"])
    print(f"\nidentidades com mensagem ilegível (`{MUTE_MESSAGE}` ou `{MUTE_SUFFIX}`): "
          f"{la}={mute_a}/{tot_a} ({100 * mute_a / tot_a:.1f} %)  "
          f"{lb}={mute_b}/{tot_b} ({100 * mute_b / tot_b:.1f} %)")

    gained = Counter(r["spec"] for r in rows if r["lado"] == "so_B")
    lost = Counter(r["spec"] for r in rows if r["lado"] == "so_A")
    _table(f"specs que GANHARAM violações (só em {lb})", gained)
    _table(f"specs que PERDERAM violações (só em {la})", lost)

    # Regressão: nenhuma identidade deveria sair de legível para ilegível. A lista é
    # nominal porque cada linha aqui é um relato que a gh104 piorou, e agregado ninguém
    # consegue ir consertar.
    reg = [r for r in rows if r["msg_status"] == "legivel_para_ilegivel"]
    print(f"\n=== REGRESSÃO legivel_para_ilegivel: {len(reg)} ===")
    if not reg:
        print("  nenhuma — nenhum relato legível virou ilegível")
    for r in sorted(reg, key=lambda r: (r["spec"], r["apk"])):
        print(f"  {r['apk'][:34]:34s} {r['spec']:24s} {r['classe'][:38]:38s} "
              f"{r['metodo'][:18]:18s} {r['tipo_erro']}")
        print(f"      {la}: {r['msg_a']}")
        print(f"      {lb}: {r['msg_b']}")

    print(f"\nCSV: {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

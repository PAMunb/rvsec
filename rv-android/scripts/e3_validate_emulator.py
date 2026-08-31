#!/usr/bin/env python3
"""Valida em emulador os APKs instrumentados do Estudo 03 (pendência P7).

Para cada APK do corpus, em série: instala, lança a activity principal, lê o
logcat, classifica, desinstala. O emulador **não** é gerenciado aqui — ele sobe
uma vez antes e cai uma vez depois, fora deste script, como faz o precedente
`validate_ajc_apks_install.py`.

O critério pedido pelo pesquisador é **2 ou mais linhas `RVSEC-COV` do código do
próprio app** — o mesmo universo que a análise estática usa como denominador de
100% de cobertura.

**Esse universo é a `reachability` do `.apk.json`, e lê-lo não pede chave nenhuma**
(INV-ANA-59/61, gh102). O GATOR foi invocado com `-clientParam codePackage=<chave>`
e descartou tudo fora dela antes de escrever, então o artefato já chega escopado;
uma linha `RVSEC-COV` é do app quando sua classe **pertence** à `reachability`.
Perguntar o escopo de novo aqui só poderia discordar do produtor — e num APK
construído com `applicationIdSuffix` esvazia o universo inteiro, que foi o defeito
que a gh102 corrigiu no `StaticAnalysisParser` (75 dos 162 mediam zero).

Duas armadilhas medidas na campanha de julho obrigam a separar as causas de falha:

1. APKs cujo `MAIN`/`LAUNCHER` está declarado só em `<activity-alias>` não
   emitem `launchable-activity` no `aapt dump badging` (19 dos 162 deste
   corpus). Lançar por nome falha com `Error type 3` e o logcat sai sem
   `RVSEC-COV` — falha de lançamento, não de instrumentação. Por isso a
   resolução da activity tem três degraus: `aapt` → `cmd package
   resolve-activity` (que enxerga o alias, porque consulta o PackageManager do
   device já com o APK instalado) → `monkey -p ... -c LAUNCHER`.
2. Há casos com `RVSEC-COV` presente mas só de infraestrutura de injeção de
   dependência (`dagger.hilt.*`), sem nenhum evento do namespace do app —
   cobertura real nula apesar do marcador. É exatamente por isso que o critério
   olha o pacote do app; o total de linhas fica registrado como informação.

Estado por APK vai para um CSV append-only; reexecutar retoma de onde parou.

Uso:
    uv run python scripts/e3_validate_emulator.py --limit 3
    uv run python scripts/e3_validate_emulator.py
    uv run python scripts/e3_validate_emulator.py --only org.fossify.notes_13.apk
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("e3-validate")

CORPUS = Path(
    "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/"
    "APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162"
)
OUT_DIR = Path(
    "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/E3_VALIDACAO_EMULADOR_162"
)
COV_TAG = "RVSEC-COV"
COV_MIN = 2  # critério do pesquisador: 2+ linhas do código do app

# Sinais de erro a procurar no logcat. `Error type 3` é o do lançamento que não
# resolve; os demais são falha em runtime do app já lançado.
ERROR_PATTERNS = {
    "fatal_exception": re.compile(r"FATAL EXCEPTION"),
    "anr": re.compile(r"ANR in "),
    "verify_error": re.compile(r"VerifyError"),
    "error_type_3": re.compile(r"Error type 3"),
    "force_stop": re.compile(r"force-stop"),
}

# Extrai a classe da linha `RVSEC-COV: <pacote.Classe: assinatura>`.
COV_CLASS = re.compile(r"RVSEC-COV:\s*<([^:]+):")

CSV_FIELDS = [
    "apk",
    "package",
    "sa_classes",
    "status",
    "activity",
    "launch_method",
    "cov_total",
    "cov_app",
    "cov_classes",
    "fatal_exception",
    "anr",
    "verify_error",
    "error_type_3",
    "force_stop",
    "install_s",
    "launch_s",
    "total_s",
    "detail",
]


@dataclass
class Result:
    apk: str
    package: str = ""
    sa_classes: int = 0  # tamanho do universo do artefato (denominador)
    status: str = ""
    activity: str = ""
    launch_method: str = ""
    cov_total: int = 0
    cov_app: int = 0  # linhas cuja classe pertence a esse universo
    cov_classes: int = 0
    fatal_exception: int = 0
    anr: int = 0
    verify_error: int = 0
    error_type_3: int = 0
    force_stop: int = 0
    install_s: float = 0.0
    launch_s: float = 0.0
    total_s: float = 0.0
    detail: str = ""


# --- adb ---


def adb(device: str, *args: str, timeout: int = 120) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            ["adb", "-s", device, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"


def single_device() -> str:
    p = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=60)
    devices = [
        line.split()[0]
        for line in p.stdout.splitlines()[1:]
        if line.strip() and line.split()[-1] == "device"
    ]
    if len(devices) != 1:
        log.error(
            "Esperado exatamente 1 device pronto; encontrado: %s", devices or "nenhum"
        )
        sys.exit(3)
    return devices[0]


# --- resolução de pacote e activity ---


def find_aapt() -> Path:
    sdk = Path(os.environ.get("ANDROID_HOME", ""))
    candidates = sorted(sdk.glob("build-tools/*/aapt"))
    if not candidates:
        log.error("aapt não encontrado em $ANDROID_HOME/build-tools/*/aapt")
        sys.exit(2)
    return candidates[-1]


def badging(aapt: Path, apk: Path) -> tuple[str, str]:
    """Retorna (package, launchable_activity). A activity vem vazia quando o
    MAIN/LAUNCHER está só em `<activity-alias>` — é o caso dos 19 do corpus."""
    p = subprocess.run(
        [str(aapt), "dump", "badging", str(apk)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    pkg = act = ""
    for line in p.stdout.splitlines():
        if line.startswith("package: name=") and not pkg:
            pkg = line.split("'")[1]
        elif line.startswith("launchable-activity: name=") and not act:
            act = line.split("'")[1]
    return pkg, act


def resolve_via_device(device: str, pkg: str) -> str:
    """Pergunta ao PackageManager do device qual activity responde ao LAUNCHER.
    Enxerga `<activity-alias>`, que é o que o `aapt` não mostra.

    Quando o app declara mais de uma activity LAUNCHER o PackageManager devolve
    `android/com.android.internal.app.ResolverActivity` — o seletor do sistema.
    Lançar isso abre o chooser, não o app, e o logcat sai sem cobertura por
    motivo nenhum do APK. Por isso só se aceita componente do pacote alvo."""
    rc, out, _ = adb(
        device,
        "shell",
        "cmd",
        "package",
        "resolve-activity",
        "--brief",
        "-c",
        "android.intent.category.LAUNCHER",
        pkg,
        timeout=60,
    )
    if rc != 0:
        return ""
    for line in out.splitlines():
        line = line.strip()
        if "/" in line and " " not in line and not line.startswith("priority"):
            return line if line.startswith(pkg + "/") else ""
    return ""


def manifest_package(meta: Path) -> str:
    """Pacote do manifesto, como a análise estática o registrou."""
    if not meta.exists():
        return ""
    try:
        return json.loads(meta.read_text()).get("package", "")
    except Exception:
        return ""


def app_classes(meta: Path) -> set[str]:
    """O universo do app, lido do artefato — sem chave e sem refiltro.

    `reachability` é o que o GATOR escreveu depois de aplicar sua própria chave,
    e é o denominador inteiro da cobertura (INV-ANA-59). Carrega-se como está.

    Devolve os nomes como o artefato os escreveu, para que `len()` seja o
    tamanho real do denominador; a diferença de grafia de classe interna é
    reconciliada no teste de pertinência, não inflando o conjunto."""
    if not meta.exists():
        return set()
    try:
        entries = json.loads(meta.read_text()).get("reachability") or []
    except Exception:
        return set()
    names = {e.get("className") or e.get("name") for e in entries}
    names.discard(None)
    return names


def belongs(cls: str, universe: set[str]) -> bool:
    """Aceita as duas grafias porque este script lê artefatos de duas eras.

    A premissa antiga — "o artefato traz `Outer.Inner` onde o logcat traz
    `Outer$Inner`" — está invertida: GATOR escreve `SootClass.getName()`, então um
    ponto entre dois segmentos capitalizados é fronteira de pacote, e quem
    inseria o cifrão era o parser. Um artefato produzido antes da gh111 pode
    carregar a grafia reescrita; a leniência aqui é para ele, não para o logcat."""
    return cls in universe or cls.replace("$", ".") in universe


# --- logcat ---


def analyze_logcat(text: str, universe: set[str]) -> dict:
    cov_total = cov_app = 0
    classes: set[str] = set()
    counts = {k: 0 for k in ERROR_PATTERNS}
    for line in text.splitlines():
        if COV_TAG in line:
            cov_total += 1
            m = COV_CLASS.search(line)
            if m:
                cls = m.group(1)
                classes.add(cls)
                if belongs(cls, universe):
                    cov_app += 1
        for name, pat in ERROR_PATTERNS.items():
            if pat.search(line):
                counts[name] += 1
    return {
        "cov_total": cov_total,
        "cov_app": cov_app,
        "cov_classes": len(classes),
        **counts,
    }


# --- um APK ---


def validate_one(
    apk: Path, device: str, aapt: Path, settle: int, logcat_dir: Path, meta: Path
) -> Result:
    r = Result(apk=apk.name)
    t_start = time.time()

    pkg, act = badging(aapt, apk)
    r.package = pkg or manifest_package(meta)
    universe = app_classes(meta)
    r.sa_classes = len(universe)
    if not r.package:
        r.status = "install_failed"
        r.detail = "não foi possível resolver o nome do pacote"
        r.total_s = round(time.time() - t_start, 1)
        return r

    # 1. instalar
    t0 = time.time()
    rc, out, err = adb(device, "install", "-r", "-g", str(apk), timeout=900)
    r.install_s = round(time.time() - t0, 1)
    if rc != 0 or "Success" not in out:
        r.status = "install_failed"
        combined = (out + " " + err).strip()
        for line in combined.splitlines():
            if "INSTALL_" in line or "Failure" in line or "error" in line.lower():
                combined = line
                break
        r.detail = combined[:400]
        r.total_s = round(time.time() - t_start, 1)
        return r

    try:
        # 2. resolver a activity: badging, depois o PackageManager do device
        if act:
            r.activity, r.launch_method = f"{pkg}/{act}", "badging"
        else:
            comp = resolve_via_device(device, pkg)
            if comp:
                r.activity, r.launch_method = comp, "resolve-activity"
            else:
                r.launch_method = "monkey"

        # 3. limpar o logcat imediatamente antes de lançar
        adb(device, "logcat", "-c", timeout=60)

        # 4. lançar
        t0 = time.time()
        if r.launch_method == "monkey":
            rc, out, err = adb(
                device,
                "shell",
                "monkey",
                "-p",
                pkg,
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
                timeout=120,
            )
            launch_bad = rc != 0 or "No activities found" in (out + err)
        else:
            rc, out, err = adb(
                device,
                "shell",
                "am",
                "start",
                "-W",
                "-S",
                "-n",
                r.activity,
                timeout=180,
            )
            launch_bad = rc != 0 or "Error" in (out + err)
            if launch_bad:
                # Última tentativa: o monkey usa o resolvedor do launcher e não
                # depende do nome de componente que acabou de falhar.
                rc2, out2, err2 = adb(
                    device,
                    "shell",
                    "monkey",
                    "-p",
                    pkg,
                    "-c",
                    "android.intent.category.LAUNCHER",
                    "1",
                    timeout=120,
                )
                if rc2 == 0 and "No activities found" not in (out2 + err2):
                    r.launch_method, launch_bad = "monkey-fallback", False
                    r.detail = f"am start falhou: {(out + ' ' + err).strip()[:200]}"
        r.launch_s = round(time.time() - t0, 1)

        # 5. deixar o app assentar e capturar
        time.sleep(settle)
        rc, out, err = adb(device, "logcat", "-d", timeout=180)
        logcat = out
        with gzip.open(logcat_dir / f"{apk.name}.logcat.gz", "wt") as fh:
            fh.write(logcat)

        stats = analyze_logcat(logcat, universe)
        for k, v in stats.items():
            setattr(r, k, v)

        # 6. classificar — a precedência importa: uma falha de lançamento
        # produz zero cobertura por si só, e reportá-la como falta de
        # instrumentação seria o erro de leitura da campanha de julho.
        if launch_bad or (r.error_type_3 and r.cov_app < COV_MIN):
            r.status = "launch_failed"
            if not r.detail:
                r.detail = (out + " " + err).strip()[:300]
        elif r.fatal_exception or r.verify_error or r.anr:
            r.status = "crash"
        elif r.cov_app < COV_MIN:
            r.status = "nocov"
        else:
            r.status = "pass"
    finally:
        adb(device, "shell", "am", "force-stop", r.package, timeout=60)
        adb(device, "uninstall", r.package, timeout=180)

    r.total_s = round(time.time() - t_start, 1)
    return r


# --- estado / resume ---


def load_done(state_csv: Path) -> set[str]:
    if not state_csv.exists():
        return set()
    with open(state_csv, newline="") as fh:
        return {row["apk"] for row in csv.DictReader(fh) if row.get("status")}


def append_row(state_csv: Path, r: Result) -> None:
    new = not state_csv.exists()
    with open(state_csv, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        if new:
            w.writeheader()
        w.writerow(asdict(r))


def reclassify(corpus: Path, out: Path) -> int:
    """Recalcula cobertura e status a partir dos logcats já gravados, sem tocar
    no device. Existe porque o critério é uma leitura do logcat, não uma
    propriedade da corrida: mudá-lo não pode custar 162 reinstalações."""
    state_csv = out / "validation.csv"
    logcat_dir = out / "logcats"
    if not state_csv.exists():
        log.error("Sem %s para reclassificar", state_csv)
        return 1

    # O CSV é append-only, então uma revalidação com `--force` deixa duas linhas
    # para o mesmo APK. A última é a boa.
    with open(state_csv, newline="") as fh:
        by_apk = {row["apk"]: row for row in csv.DictReader(fh)}
    rows = list(by_apk.values())

    rewritten = []
    for row in rows:
        r = Result(apk=row["apk"], package=row.get("package", ""))
        for f in ("activity", "launch_method", "detail"):
            setattr(r, f, row.get(f, ""))
        for f in ("install_s", "launch_s", "total_s"):
            setattr(r, f, float(row.get(f) or 0))
        meta = corpus / f"{row['apk']}.json"
        universe = app_classes(meta)
        r.sa_classes = len(universe)

        lg = logcat_dir / f"{row['apk']}.logcat.gz"
        if not lg.exists():
            # Sem logcat só existe um caso: a instalação nem chegou a acontecer.
            r.status = row.get("status", "install_failed")
            rewritten.append(r)
            continue

        with gzip.open(lg, "rt") as fh:
            stats = analyze_logcat(fh.read(), universe)
        for k, v in stats.items():
            setattr(r, k, v)

        if row.get("status") == "launch_failed" or (
            r.error_type_3 and r.cov_app < COV_MIN
        ):
            r.status = "launch_failed"
        elif r.fatal_exception or r.verify_error or r.anr:
            r.status = "crash"
        elif r.cov_app < COV_MIN:
            r.status = "nocov"
        else:
            r.status = "pass"
        rewritten.append(r)

    tmp = state_csv.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(asdict(r) for r in rewritten)
    tmp.replace(state_csv)

    tally: dict[str, int] = {}
    for r in rewritten:
        tally[r.status] = tally.get(r.status, 0) + 1
    log.info("Reclassificados %d registros — %s", len(rewritten), tally)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument(
        "--settle",
        type=int,
        default=15,
        help="segundos entre o lançamento e a captura do logcat",
    )
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument(
        "--only",
        action="append",
        default=[],
        help="valida apenas o(s) APK(s) nomeado(s); repetível",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="revalida mesmo o que já está no CSV de estado",
    )
    ap.add_argument(
        "--reclassify",
        action="store_true",
        help="recalcula status a partir dos logcats gravados, sem device",
    )
    args = ap.parse_args()

    if args.reclassify:
        return reclassify(args.corpus, args.out)

    apks = sorted(args.corpus.glob("*.apk"))
    if not apks:
        log.error("Nenhum APK em %s", args.corpus)
        return 1
    if args.only:
        wanted = set(args.only)
        apks = [a for a in apks if a.name in wanted]
        missing = wanted - {a.name for a in apks}
        if missing:
            log.error("APK não encontrado no corpus: %s", ", ".join(sorted(missing)))
            return 1

    args.out.mkdir(parents=True, exist_ok=True)
    logcat_dir = args.out / "logcats"
    logcat_dir.mkdir(exist_ok=True)
    state_csv = args.out / "validation.csv"

    done = set() if args.force else load_done(state_csv)
    pending = [a for a in apks if a.name not in done]
    if args.limit:
        pending = pending[: args.limit]

    log.info(
        "Corpus: %d APKs | já validados: %d | a validar agora: %d",
        len(apks),
        len(done),
        len(pending),
    )
    if not pending:
        log.info("Nada a fazer.")
        return 0

    device = single_device()
    aapt = find_aapt()
    rc, sdk_out, _ = adb(device, "shell", "getprop", "ro.build.version.sdk")
    rc, abi_out, _ = adb(device, "shell", "getprop", "ro.product.cpu.abi")
    log.info(
        "Device %s | API %s | ABI %s | aapt %s",
        device,
        sdk_out,
        abi_out,
        aapt.parent.name,
    )

    tally: dict[str, int] = {}
    t_batch = time.time()
    for i, apk in enumerate(pending, 1):
        meta = apk.parent / f"{apk.name}.json"
        log.info("[%d/%d] %s", i, len(pending), apk.name)
        r = validate_one(apk, device, aapt, args.settle, logcat_dir, meta)
        append_row(state_csv, r)
        tally[r.status] = tally.get(r.status, 0) + 1
        log.info(
            "  → %s | cov %d (app %d) | %s | %.0fs",
            r.status.upper(),
            r.cov_total,
            r.cov_app,
            r.launch_method or "-",
            r.total_s,
        )
        if r.detail:
            log.info("     %s", r.detail[:200])

    elapsed = time.time() - t_batch
    log.info("=" * 60)
    log.info(
        "Validados agora: %d em %.1f min (%.0f s/APK)",
        len(pending),
        elapsed / 60,
        elapsed / max(1, len(pending)),
    )
    for status in ("pass", "nocov", "crash", "launch_failed", "install_failed"):
        if status in tally:
            log.info("  %-15s %d", status, tally[status])
    log.info("Estado: %s", state_csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())

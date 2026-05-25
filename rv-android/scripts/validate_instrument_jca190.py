#!/usr/bin/env python3
"""Validação dos 190 APKs instrumentados pelo compose docker-compose.instrument-jca190.yml.

Para cada APK em data/results/instrument_jca190_NN/instrument_jca190_NN/instrumented_apks/:
  1. Resolve package + main launchable activity (androguard, cacheado)
  2. `adb logcat -c` (limpa buffer)
  3. `adb install -r -t -g <apk>` (60s timeout)
  4. `adb shell am start -W -n <pkg>/<activity>` (10s timeout)
  5. sleep 6s (deixa app carregar + dispara <clinit> JCA)
  6. `adb shell am force-stop <pkg>` + `adb uninstall <pkg>`
  7. `adb logcat -d` → grep RVSEC-COV / RVMOP / FATAL EXCEPTION / VerifyError
  8. Registra resultado em CSV + dump do logcat (em caso de falha)

Requer: UM emulador conectado (script aborta se 0 ou >1 dispositivos).
O usuário sobe o emulador antes (`emulator -avd <name>` ou pelo Docker).

Uso:
    # Inventário (não instala nada):
    uv run python scripts/validate_instrument_jca190.py --dry-run

    # Validação completa:
    uv run python scripts/validate_instrument_jca190.py

    # Smoke 5 APKs:
    uv run python scripts/validate_instrument_jca190.py --limit 5

    # Re-rodar do zero (ignora cache de resultados):
    uv run python scripts/validate_instrument_jca190.py --force

Saída:
    out/validate_instrument_jca190/install_report.csv  (1 linha por APK)
    out/validate_instrument_jca190/logs/<apk>.logcat   (logcat completo das falhas)
    out/validate_instrument_jca190/package_cache.json  (cache pkg+activity)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(
    "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
)
# Espelho do template instrument-jca226: results/instrument_jca190_NN/instrument_jca190_NN/instrumented_apks/*.apk
RESULTS_GLOB = "data/results/instrument_jca190_*/instrument_jca190_*/instrumented_apks/*.apk"

OUT_DIR = PROJECT_ROOT / "out/validate_instrument_jca190"
REPORT_CSV = OUT_DIR / "install_report.csv"
LOGS_DIR = OUT_DIR / "logs"
CACHE_FILE = OUT_DIR / "package_cache.json"

CSV_COLS = [
    "apk",
    "pkg",
    "main_activity",
    "install_ok",
    "install_err",
    "launch_ok",
    "launch_err",
    "has_rvsec_cov",
    "has_rvmop",
    "has_fatal",
    "has_verifyerror",
    "status",  # PASS | FAIL_INSTALL | FAIL_LAUNCH | FAIL_VERIFY | FAIL_FATAL | FAIL_NO_RVSEC
    "notes",
]

# Pós-launch: tempo que o app fica vivo gerando atividade JCA via <clinit>/onCreate.
LAUNCH_DWELL_SECONDS = 6


# --- adb helpers --------------------------------------------------------------

def adb(*args: str, timeout: int = 60) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["adb", *args], capture_output=True, text=True, timeout=timeout
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def get_connected_device() -> str:
    rc, out, err = adb("devices")
    if rc != 0:
        log.error("adb devices failed: %s", err)
        sys.exit(2)
    devices = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] in ("device", "emulator"):
            devices.append(parts[0])
    if not devices:
        log.error("Nenhum dispositivo conectado. Suba o emulador antes.")
        sys.exit(3)
    if len(devices) > 1:
        log.error("Múltiplos dispositivos: %s. Mantenha apenas um.", devices)
        sys.exit(4)
    return devices[0]


# --- pkg + activity resolution ------------------------------------------------

def load_cache() -> dict[str, dict]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            log.warning("Cache corrompido, recomeçando")
    return {}


def save_cache(cache: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, sort_keys=True))


def resolve_apk_info(apk: Path, cache: dict[str, dict]) -> tuple[Optional[str], Optional[str]]:
    """Retorna (pkg, main_activity_full). Cacheado por nome de arquivo."""
    key = apk.name
    if key in cache:
        c = cache[key]
        return c.get("pkg"), c.get("activity")
    pkg, activity = None, None
    try:
        # androguard 4.x path; cai pra 3.x se falhar.
        try:
            from androguard.core.apk import APK  # 4.x
        except ImportError:
            from androguard.core.bytecodes.apk import APK  # 3.x
        a = APK(str(apk))
        pkg = a.get_package()
        activity = a.get_main_activity()
        if activity and not activity.startswith(pkg + "."):
            # Se a activity vier sem qualificação, prepende package.
            if "." not in activity:
                activity = f"{pkg}.{activity}"
    except Exception as e:
        log.warning("androguard falhou em %s: %s", apk.name, e)
    cache[key] = {"pkg": pkg, "activity": activity}
    return pkg, activity


# --- install/launch/inspect ---------------------------------------------------

def install_apk(apk: Path, device: str) -> tuple[bool, str]:
    rc, out, err = adb("-s", device, "install", "-r", "-t", "-g", str(apk), timeout=120)
    combined = (out + " | " + err).strip(" |")
    if rc == 0 and "Success" in out:
        return True, ""
    msg = combined
    for line in (out + "\n" + err).splitlines():
        if "INSTALL_" in line or "Failure" in line:
            msg = line.strip()
            break
    return False, msg[:400]


def launch_main(pkg: str, activity: str, device: str) -> tuple[bool, str]:
    rc, out, err = adb(
        "-s", device, "shell", "am", "start", "-W", "-n", f"{pkg}/{activity}",
        timeout=30,
    )
    combined = (out + " | " + err).strip(" |")
    # `am start -W` retorna "Status: ok" no sucesso.
    if rc == 0 and ("Status: ok" in out or "LaunchState" in out):
        return True, ""
    return False, combined[:400]


def collect_logcat(device: str) -> str:
    rc, out, err = adb("-s", device, "logcat", "-d", "-v", "threadtime", timeout=30)
    if rc != 0:
        return f"(logcat fail: {err})\n{out}"
    return out


RX_RVSEC_COV = re.compile(r"\bRVSEC-COV\b")
RX_RVMOP = re.compile(r"\bRVSEC-MOP\b|\bRV-MOP\b|\bRVMonitorMessage\b")
RX_FATAL = re.compile(r"AndroidRuntime: FATAL EXCEPTION")
RX_VERIFYERROR = re.compile(r"VerifyError|java\.lang\.VerifyError|rejecting class")


def analyze_logcat(logtext: str, pkg: str) -> dict:
    # Heurística: o crash precisa pertencer ao app (ou ao sistema reportando o app).
    # Procuramos as linhas FATAL próximas a uma menção ao pkg para reduzir falso-positivo
    # de crashes residuais de outros apps. Para RVSEC, basta presença global.
    has_rvsec = bool(RX_RVSEC_COV.search(logtext))
    has_rvmop = bool(RX_RVMOP.search(logtext))
    has_fatal = bool(RX_FATAL.search(logtext) and (pkg in logtext))
    has_verify = bool(RX_VERIFYERROR.search(logtext) and (pkg in logtext))
    return {
        "has_rvsec_cov": has_rvsec,
        "has_rvmop": has_rvmop,
        "has_fatal": has_fatal,
        "has_verifyerror": has_verify,
    }


def cleanup(pkg: str, device: str) -> None:
    try:
        adb("-s", device, "shell", "am", "force-stop", pkg, timeout=15)
    except Exception:
        pass
    try:
        adb("-s", device, "uninstall", pkg, timeout=30)
    except Exception:
        pass


# --- main ---------------------------------------------------------------------

def load_existing_report() -> dict[str, dict]:
    if not REPORT_CSV.exists():
        return {}
    with open(REPORT_CSV, newline="") as f:
        return {row["apk"]: row for row in csv.DictReader(f)}


def write_report(rows: dict[str, dict]) -> None:
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT_CSV.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        for apk in sorted(rows):
            w.writerow({k: rows[apk].get(k, "") for k in CSV_COLS})
    tmp.replace(REPORT_CSV)


def process_apk(apk: Path, device: str, cache: dict) -> dict:
    row = {c: "" for c in CSV_COLS}
    row["apk"] = apk.name

    pkg, activity = resolve_apk_info(apk, cache)
    row["pkg"] = pkg or ""
    row["main_activity"] = activity or ""

    if not pkg:
        row["status"] = "FAIL_INSTALL"
        row["notes"] = "androguard nao resolveu package"
        return row
    if not activity:
        row["status"] = "FAIL_LAUNCH"
        row["notes"] = "androguard nao resolveu main activity"
        return row

    # Limpa logcat antes pra isolar este APK.
    adb("-s", device, "logcat", "-c", timeout=15)

    ok, msg = install_apk(apk, device)
    row["install_ok"] = "true" if ok else "false"
    row["install_err"] = msg
    if not ok:
        row["status"] = "FAIL_INSTALL"
        return row

    ok, msg = launch_main(pkg, activity, device)
    row["launch_ok"] = "true" if ok else "false"
    row["launch_err"] = msg

    time.sleep(LAUNCH_DWELL_SECONDS)

    logtext = collect_logcat(device)
    findings = analyze_logcat(logtext, pkg)
    row.update({k: ("true" if v else "false") for k, v in findings.items()})

    if findings["has_verifyerror"]:
        status = "FAIL_VERIFY"
    elif findings["has_fatal"]:
        status = "FAIL_FATAL"
    elif not ok:
        status = "FAIL_LAUNCH"
    elif not findings["has_rvsec_cov"]:
        status = "FAIL_NO_RVSEC"
    else:
        status = "PASS"
    row["status"] = status

    # Dump logcat das falhas pra debug posterior.
    if status != "PASS":
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        (LOGS_DIR / f"{apk.name}.logcat").write_text(logtext)

    cleanup(pkg, device)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="Lista APKs encontrados e sai (sem instalar)")
    ap.add_argument("--force", action="store_true",
                    help="Revalida mesmo APKs já presentes no CSV")
    ap.add_argument("--limit", type=int, default=None,
                    help="Processa só os primeiros N APKs")
    args = ap.parse_args()

    apks = sorted(set(PROJECT_ROOT.glob(RESULTS_GLOB)))
    # Dedup por nome (mesmo APK não deveria aparecer em 2 batches, mas defensivo).
    seen = {}
    for p in apks:
        seen.setdefault(p.name, p)
    apks = [seen[k] for k in sorted(seen)]

    log.info("Encontrados %d APKs instrumentados", len(apks))
    if args.limit:
        apks = apks[: args.limit]
        log.info("Limitado a %d APKs", len(apks))

    if args.dry_run:
        for p in apks:
            print(p.relative_to(PROJECT_ROOT))
        return 0

    if not apks:
        log.error("Nenhum APK encontrado em %s — rodou o compose?", RESULTS_GLOB)
        return 5

    device = get_connected_device()
    log.info("Dispositivo: %s", device)

    cache = load_cache()
    existing = load_existing_report()
    rows = dict(existing)

    processed = 0
    pass_count = 0
    fail_count = 0
    skip_count = 0
    t0 = time.time()

    try:
        for i, apk in enumerate(apks, 1):
            if not args.force and apk.name in existing and existing[apk.name].get("status"):
                skip_count += 1
                log.info("[%d/%d] SKIP %s (já no CSV: %s)",
                         i, len(apks), apk.name, existing[apk.name]["status"])
                continue
            try:
                row = process_apk(apk, device, cache)
            except subprocess.TimeoutExpired as e:
                row = {c: "" for c in CSV_COLS}
                row["apk"] = apk.name
                row["status"] = "FAIL_INSTALL"
                row["notes"] = f"timeout: {e}"
            except Exception as e:
                row = {c: "" for c in CSV_COLS}
                row["apk"] = apk.name
                row["status"] = "FAIL_INSTALL"
                row["notes"] = f"exception: {e}"
            rows[apk.name] = row
            processed += 1
            if row["status"] == "PASS":
                pass_count += 1
            else:
                fail_count += 1
            log.info("[%d/%d] %s -> %s", i, len(apks), apk.name, row["status"])
            # Checkpoint a cada 5 APKs.
            if processed % 5 == 0:
                write_report(rows)
                save_cache(cache)
    finally:
        write_report(rows)
        save_cache(cache)

    dt = time.time() - t0
    log.info("=" * 60)
    log.info("Total: %d APKs | %d PASS | %d FAIL | %d skip | %.1fs",
             processed + skip_count, pass_count, fail_count, skip_count, dt)
    log.info("Relatório: %s", REPORT_CSV)
    log.info("Logs falhas: %s/", LOGS_DIR)
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

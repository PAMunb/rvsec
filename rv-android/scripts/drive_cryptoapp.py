"""Deterministic UIAutomator driver for cryptoapp's 8 canonical violations.

Reproduces every event in
``rvsec/rvsec-android/rvsec-instrumentation-dexlib2/validator/oracles/cryptoapp-oracle.yaml``
by walking the UI through the three activities (MessageDigest, Cipher,
Cryptography) and triggering each unsafe path. Acts as the Layer-3
oracle reproducer for INV-INS-22 — APE-RV's stochastic exploration is
too input-shy to reach the unsafe branches in a 300s budget, so this
script is the canonical reference run.

Usage:
    uv run python scripts/drive_cryptoapp.py \\
        --serial emulator-5554 \\
        --apk /path/to/woven_cryptoapp.apk \\
        --output-dir /tmp/cryptoapp_drive

Pre-requisites:
    - Emulator booted and running.
    - Woven cryptoapp APK installed (the script will (re)install if
      ``--apk`` is given, otherwise it uses whatever is already on
      device).
    - ``uiautomator2`` available in the env (already in
      ``rv-android/.venv``).

What it does:
    1. Resets app state (force-stop + clear).
    2. Clears logcat with ``adb logcat -c``.
    3. Runs the 4 scenarios in order:
        - MessageDigest: MD5 + SHA-1 (events 1, 2)
        - Cipher: 30 encrypt clicks (events 3, 4, 5, 8 — DES path is 70%
          and AES is 30% per the random.nextInt(10) > 6 check, so 30
          clicks gives ≥99.99% chance of hitting both).
        - Cryptography: Key Pair tab → DSA → Generate (events 6, 7).
    4. Dumps logcat to ``output-dir/driver.logcat``.
    5. Greps for ``RVSEC:`` (violations) and prints a per-event match
       table against the oracle. Exits non-zero if any expected event
       is missing.

Notes:
    - The oracle's ``location.method`` is the RV-monitor invocation
      site, not necessarily where the unsafe API was called — e.g.
      event 6 (DSA InvalidKeySize) is attributed to
      ``CryptographyActivity.generateKeyPair`` because that's where
      ``KeyPairGenerator.initialize(1024)`` lives.
    - We pause briefly between actions to let UIAutomator resync; on
      slow emulators bump ``--step-delay`` (default 0.6s).
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import uiautomator2 as u2

PACKAGE = "br.unb.cic.cryptoapp"
MAIN_ACTIVITY = f"{PACKAGE}/.MainActivity"

# Oracle entries we expect to see. Keyed by id 1..8 to mirror
# cryptoapp-oracle.yaml. ``substr`` is a sufficient (not necessary)
# fragment from the violation's RVSEC log line; ``None`` means presence
# of the (spec, error_type) tuple is enough.
@dataclass(frozen=True)
class OracleEvent:
    id: int
    spec: str
    error_type: str
    substr: str | None


ORACLE: tuple[OracleEvent, ...] = (
    OracleEvent(1, "MessageDigestSpec", "UnsafeAlgorithm", "MD5"),
    OracleEvent(2, "MessageDigestSpec", "UnsafeAlgorithm", "SHA-1"),
    OracleEvent(3, "CipherSpec", "InvalidSequenceOfMethodCalls", None),
    OracleEvent(4, "CipherSpec", "UnsafeAlgorithm", "DES"),
    OracleEvent(5, "KeyGeneratorSpec", "UnsafeAlgorithm", "DES"),
    OracleEvent(6, "KeyPairGeneratorSpec", "InvalidKeySize", "DSA"),
    OracleEvent(7, "KeyPairSpec", "InvalidSequenceOfMethodCalls", None),
    OracleEvent(8, "SecretKeySpecSpec", "UnsatisfiedConstraint", "not randomized"),
)

# RVSEC log lines look like
#   "RVSEC: [SpecName] ErrorType: detail message"
# (some specs also emit just "[SpecName] ErrorType: ..." without the
# leading "RVSEC:" — we match either).
RVSEC_LINE = re.compile(
    r"(?:RVSEC:\s*)?\[(?P<spec>\w+)\]\s+(?P<etype>\w+)\s*[:\-]\s*(?P<msg>.*)$"
)

log = logging.getLogger("drive_cryptoapp")


def _adb(*args: str, serial: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    log.debug("adb: %s", " ".join(cmd))
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def _reset_app(serial: str | None) -> None:
    """Kill the process and clear app data so each run starts fresh.

    We do not uninstall — caller is expected to ensure the woven APK is
    already on the device.
    """
    _adb("shell", "am", "force-stop", PACKAGE, serial=serial, check=False)
    # ``pm clear`` removes app data but keeps the APK installed.
    _adb("shell", "pm", "clear", PACKAGE, serial=serial, check=False)


def _scenario_message_digest(d: u2.Device, step_delay: float) -> None:
    """Drive MessageDigestActivity for MD5 (event 1) and SHA-1 (event 2)."""
    log.info("Scenario: MessageDigest (MD5, SHA-1)")

    # Land on MainActivity
    d.app_start(PACKAGE, activity=".MainActivity", wait=True)
    time.sleep(step_delay)

    # Open MessageDigestActivity
    d(resourceId=f"{PACKAGE}:id/buttonMessageDigest").click()
    d(resourceId=f"{PACKAGE}:id/spinnerMessageDigest").wait(timeout=5)
    time.sleep(step_delay)

    for algorithm in ("MD5", "SHA-1"):
        # Open the spinner; entry list is a popup window.
        d(resourceId=f"{PACKAGE}:id/spinnerMessageDigest").click()
        d(text=algorithm).wait(timeout=5)
        d(text=algorithm).click()
        time.sleep(step_delay)

        # Type the input text. set_text replaces existing.
        d(resourceId=f"{PACKAGE}:id/editTextMessageDigest").set_text("driver_input")
        time.sleep(step_delay)

        d(resourceId=f"{PACKAGE}:id/buttonGenerateHash").click()
        time.sleep(step_delay)

    # Back to MainActivity
    d.press("back")
    time.sleep(step_delay)


def _scenario_cipher(d: u2.Device, step_delay: float, encrypt_clicks: int) -> None:
    """Drive CipherActivity until both DES (events 3,4,5) and AES (event 8) fire.

    ``CipherUtil.encrypt`` flips a coin (``random.nextInt(10) > 6``) on
    every click — DES wins ~70%, AES ~30%. ``encrypt_clicks=30`` gives
    P(both at least once) > 0.9999.
    """
    log.info("Scenario: Cipher (DES + AES, %d clicks)", encrypt_clicks)

    d.app_start(PACKAGE, activity=".MainActivity", wait=True)
    time.sleep(step_delay)

    d(resourceId=f"{PACKAGE}:id/buttonCipher").click()
    d(resourceId=f"{PACKAGE}:id/editTextCipherEncrypt").wait(timeout=5)
    time.sleep(step_delay)

    d(resourceId=f"{PACKAGE}:id/editTextCipherEncrypt").set_text("driver_input")
    time.sleep(step_delay)

    for i in range(encrypt_clicks):
        d(resourceId=f"{PACKAGE}:id/btn_cipher_encrypt").click()
        # Tight delay here: the encrypt path is a sub-second op and we
        # want enough RNG samples to converge on both branches.
        time.sleep(max(0.15, step_delay / 4))
        if (i + 1) % 10 == 0:
            log.info("  cipher click %d/%d", i + 1, encrypt_clicks)

    d.press("back")
    time.sleep(step_delay)


def _scenario_cryptography(d: u2.Device, step_delay: float) -> None:
    """Drive CryptographyActivity to generate a DSA KeyPair (events 6, 7).

    The activity defaults to the "Secret Key" tab; we switch to "Key
    Pair", select DSA from the algorithm spinner, ensure the Generate
    radio is checked, and hit Execute.
    """
    log.info("Scenario: Cryptography (DSA KeyPair generate)")

    d.app_start(PACKAGE, activity=".MainActivity", wait=True)
    time.sleep(step_delay)

    d(resourceId=f"{PACKAGE}:id/buttonGenerated").click()
    d(resourceId=f"{PACKAGE}:id/cryptoTabLayout").wait(timeout=5)
    time.sleep(step_delay)

    # Switch to "Key Pair" tab. TabLayout exposes tabs by text; clicking
    # the text view inside the tab is the most stable selector.
    d(text="Key Pair").click()
    time.sleep(step_delay)

    # Open algorithm spinner and pick DSA.
    d(resourceId=f"{PACKAGE}:id/algorithmSpinner").click()
    d(text="DSA").wait(timeout=5)
    d(text="DSA").click()
    time.sleep(step_delay)

    # Pick the Generate radio. Its label changes per tab; on Key Pair
    # it reads "Generate Key Pair".
    d(resourceId=f"{PACKAGE}:id/generateRadioButton").click()
    time.sleep(step_delay)

    d(resourceId=f"{PACKAGE}:id/executeButton").click()
    # Generation is synchronous and short for DSA-1024.
    time.sleep(step_delay * 2)


def _drive(serial: str | None, step_delay: float, encrypt_clicks: int) -> None:
    if serial:
        d = u2.connect(serial)
    else:
        d = u2.connect()
    log.info("Connected to %s (%s)", d.serial, d.info.get("displaySizeDpX", "?"))

    _scenario_message_digest(d, step_delay)
    _scenario_cipher(d, step_delay, encrypt_clicks)
    _scenario_cryptography(d, step_delay)


def _dump_logcat(serial: str | None, output: Path) -> None:
    """Snapshot the device logcat to ``output``.

    Uses ``-d`` (dump and exit) since by this point the driver has
    already triggered every event and we only need what's already in
    the ring buffer.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += ["logcat", "-d", "-v", "threadtime"]
    log.info("Dumping logcat → %s", output)
    with output.open("w") as f:
        subprocess.run(cmd, check=True, stdout=f)


def _match_oracle(logcat_path: Path) -> tuple[list[OracleEvent], list[OracleEvent], list[str]]:
    """Return (matched, missing, raw_rvsec_lines)."""
    raw: list[str] = []
    seen: set[int] = set()
    text = logcat_path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        # Only RVSEC tag lines; cheap pre-filter to avoid running the
        # regex on every coverage event.
        if "RVSEC" not in line or "RVSEC-COV" in line:
            continue
        m = RVSEC_LINE.search(line)
        if not m:
            continue
        raw.append(line)
        spec, etype, msg = m.group("spec"), m.group("etype"), m.group("msg")
        for ev in ORACLE:
            if ev.id in seen:
                continue
            if ev.spec != spec or ev.error_type != etype:
                continue
            if ev.substr and ev.substr not in msg:
                continue
            seen.add(ev.id)
            break

    matched = [ev for ev in ORACLE if ev.id in seen]
    missing = [ev for ev in ORACLE if ev.id not in seen]
    return matched, missing, raw


def _print_report(matched: Iterable[OracleEvent], missing: Iterable[OracleEvent], raw: Iterable[str]) -> None:
    matched = list(matched)
    missing = list(missing)
    print()
    print(f"Oracle: 8 expected events. Matched: {len(matched)}. Missing: {len(missing)}.")
    print()
    print("  ID  spec                      error_type                    matched")
    print("  --  ------------------------  ----------------------------  -------")
    by_id: dict[int, OracleEvent] = {ev.id: ev for ev in ORACLE}
    matched_ids = {ev.id for ev in matched}
    for ev in ORACLE:
        flag = "yes" if ev.id in matched_ids else "MISS"
        print(f"  {ev.id:>2}  {ev.spec:<24s}  {ev.error_type:<28s}  {flag}")

    if missing:
        print()
        print("Missing events:")
        for ev in missing:
            print(f"  - id={ev.id} {ev.spec}/{ev.error_type} substr={ev.substr!r}")
        print()
        print(f"Total RVSEC violation lines observed: {len(list(raw))}")
        print("Sample (first 20):")
        for line in list(raw)[:20]:
            print(f"  {line}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serial", default=None, help="ADB serial (default: single-attached device).")
    parser.add_argument("--apk", default=None, type=Path, help="Optional APK to (re)install before driving.")
    parser.add_argument(
        "--output-dir",
        default=Path("/tmp/cryptoapp_drive"),
        type=Path,
        help="Where to write driver.logcat and (later) match report.",
    )
    parser.add_argument("--step-delay", default=0.6, type=float, help="Seconds between UI actions (default 0.6).")
    parser.add_argument(
        "--encrypt-clicks",
        default=30,
        type=int,
        help="How many times to click Cipher.Encrypt (≥30 ensures both DES and AES branches fire).",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Skip ``pm clear`` reset (use when previous data is wanted).",
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose >= 2 else (logging.INFO if args.verbose == 1 else logging.WARNING),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.apk is not None:
        if not args.apk.is_file():
            log.error("APK not found: %s", args.apk)
            return 2
        log.info("Installing %s", args.apk)
        _adb("install", "-r", "-g", str(args.apk), serial=args.serial)

    if not args.no_clear:
        _reset_app(args.serial)

    _adb("logcat", "-c", serial=args.serial, check=False)

    try:
        _drive(args.serial, args.step_delay, args.encrypt_clicks)
    except Exception as e:
        log.error("UI driver failed: %s", e)
        # Still dump logcat for debugging.
        _dump_logcat(args.serial, args.output_dir / "driver.logcat")
        raise

    # Brief grace period for the runtime monitor to flush events to log.
    time.sleep(2.0)
    logcat = args.output_dir / "driver.logcat"
    _dump_logcat(args.serial, logcat)

    matched, missing, raw = _match_oracle(logcat)
    _print_report(matched, missing, raw)

    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""set_cons_hist.py — consolidated historical analysis of errors.csv (protocol §12).

DISCIPLINE (pre_registro §2, protocol §12): errors.csv is PRE-repair history — a
hypothesis generator ONLY. Four statistical units are reported SEPARATELY and never
mixed: lines, unique_msg, APKs, sites. A "site" here is (class, method) — the file
carries no __LOC column, so finer site identity is not available in this dataset.
NO causal claim is made anywhere in this output: every mechanism column is a
HYPOTHESIS-LINK to an audited, judge-executed current-artifact mechanism, and each
link names the discriminating replay test (G10 battery) that would decide it.

In-script integrity gate: the sha256 of errors.csv must equal the frozen manifest
value; the script aborts otherwise. Malformed-row census printed (protocol §12
"valide registros malformados/nulos").
"""
import csv, hashlib, os, sys, collections

ERRORS = ("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/"
          "ase-journal/dataset/results/errors.csv")
SHA_EXPECTED = "78023defec078353bbd1f64331edb7992a2c34e29570e6ceb064fb57f37dea69"
SETD = os.path.dirname(os.path.abspath(__file__))

# Hypothesis links: spec -> (audited mechanism [closure evidence], discriminating replay test)
# Every mechanism is a CLOSED current-artifact finding (judge-executed); the link to the
# historical stratum is a hypothesis pending the named replay. No line is attributed.
HYPOTHESIS_LINKS = [
    ("SecureRandomSpec", "H-SRD-1: next2 missing from `end` => FP on 2nd+ nextBytes "
     "(FEN-SRD-NEXTBYTES-FP, judge D2 executed; site profile of the historical lines "
     "matches the FP shape — GAMA-SRD-02 INCONCLUSIVE)", "G10-SRD-1 (device replay, paired jca/jca_android)"),
    ("KeyPairSpec", "H-KPR-1: co? made mandatory => FP at first getter on the canonical "
     "generateKeyPair route (FEN-KPR-CO-OPCIONAL, judge J2d executed; 668 historical lines "
     "100% unknown-InvalidSeq — GAMA-KPR-06 INCONCLUSIVE)",
     "GAMA-KPR-06 battery: micro-APK ajc+dexlib2, paired replay, campaign-APK DEX inspection"),
    ("TrustManagerFactorySpec", "H4/TMF fingerprint: creation-at-consume carrier => "
     "UnsafeAlgorithm with EMPTY 'but found .' label + paired InvalidSeq at the same site "
     "(FEN-C-EMPTY-LABEL H4 closed live; FEN-C-CARRIER-SEQFAIL; batchC pF1 pre-repair "
     "reconstruction conferred)", "G10-TMF-1"),
    ("MessageDigestSpec", "H2 (immediate pairing): specific error + spurious InvalidSeq on "
     "the same consuming call (FEN-C-CARRIER-SEQFAIL, judge D6 executed: pair at each of 3 "
     "distinct sites). ORACLE-SHIFT WARNING (batchD §6.6): most historical UnsafeAlgorithm "
     "lines are MD5/SHA-1 — SAFE under api30; any future drop is oracle change, not repair",
     "G10 batch battery (paired replay)"),
    ("KeyGeneratorSpec", "H2 + carrier (batchC S1-S5 executed); historical zero-emission of "
     "KGN/KMF is GAMA-SET-21 (INCONCLUSIVE) — and the batchC non-compiling artifact "
     "(FEN-KGN-NAOCOMPILA) is a candidate mechanism for per-spec builds",
     "G10-KGN-1 (per-spec production build) + GAMA-SET-21 battery"),
    ("KeyPairGeneratorSpec", "H2 immediate AND delayed pairing (FEN-KPG-INITERROR-PLACEMENT, "
     "judge D7a/D7b executed both directions); KPG NPE route would CRASH the app "
     "(FEN-KPG-NPE, D1) — a crash annihilates subsequent records from the process",
     "G10-KPG-1 (NPE), G10-KPG-2 (genKeyPair dexlib2 weave)"),
    ("SignatureSpec", "sign branch dead on both weave halves (FEN-SIG-SIGN-VOID) => "
     "conformant signing never accepts; empty-label live (sig_a)", "G10-SIG-1"),
    ("MacSpec", "key-gate suppression displaces accusations (FEN-MAC-KEYGATE-EXTRA, D4); "
     "f3 ajc-dead vs dexlib2-broadcast (FEN-MAC-F3-UNBOUND, D9)", "G10-MAC-1"),
    ("CipherInputStreamSpec / CipherOutputStreamSpec / SecretKeySpec / PBEKeySpecSpec",
     "historical zero-emission (GAMA-SET-16 INCONCLUSIVE); consistent with "
     "FEN-SKY-ZERO-CAPTURA (SKY inert on production dexlib2, measured) and the CIS/COS "
     "first-disjunct suspicion (batchD §6.7) — hypotheses only",
     "GAMA-SET-16 replay battery + host dexlib2 re-measure of CIS/COS"),
    ("SSLContextSpec", "engine events dead both halves (FEN-SSL-ENGINE-VOID); carrier "
     "pairing (S1-S5); getDefault FORBIDDEN omitted (silence, not lines)", "G10-SSL-2"),
    ("KeyStoreSpec", "global monitor + erasure chain (FEN-KST-MONITOR-GLOBAL/-ERASURE, "
     "S6/S7 executed)", "G10-KST-1"),
]

def main():
    h = hashlib.sha256()
    with open(ERRORS, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    digest = h.hexdigest()
    assert digest == SHA_EXPECTED, f"errors.csv hash mismatch: {digest}"
    out = []
    P = out.append
    P(f"errors.csv sha256 VERIFIED = {digest}")
    P("UNITS REPORTED SEPARATELY: lines | unique_msg | APKs | sites=(class,method). "
      "PRE-repair history: hypothesis generator only; no causal attribution.")

    rows = []
    malformed = 0
    with open(ERRORS, newline="", encoding="utf-8", errors="replace") as fh:
        rd = csv.DictReader(fh)
        for r in rd:
            if not r.get("spec") or not r.get("unique_msg"):
                malformed += 1
                continue
            rows.append(r)
    P(f"data lines parsed: {len(rows)}; malformed/null-field lines: {malformed}")

    def cat_of(r):
        parts = r["unique_msg"].split(":::")
        return parts[3] if len(parts) >= 4 else "MALFORMED_UNIQUE"

    per = collections.defaultdict(lambda: {"lines": 0, "uniq": set(), "apks": set(),
                                           "sites": set(), "cats": collections.Counter(),
                                           "unknown": 0, "empty_label": 0})
    for r in rows:
        d = per[r["spec"]]
        d["lines"] += 1
        d["uniq"].add(r["unique_msg"])
        d["apks"].add(r["apk"])
        site = (r["class"], r["method"])
        d["sites"].add(site)
        d["cats"][cat_of(r)] += 1
        if r["message"].strip() == "unknown":
            d["unknown"] += 1
        if r["message"].rstrip().endswith("but found ."):
            d["empty_label"] += 1

    P("\n== all-spec strata (four units separately) ==")
    P(f"{'spec':28s} {'lines':>7s} {'uniq_msg':>8s} {'apks':>5s} {'sites':>6s} "
      f"{'unknown':>8s} {'empty_lbl':>9s}  categories")
    for spec in sorted(per, key=lambda s: -per[s]["lines"]):
        d = per[spec]
        cats = " ".join(f"{k}={v}" for k, v in d["cats"].most_common())
        P(f"{spec:28s} {d['lines']:7d} {len(d['uniq']):8d} {len(d['apks']):5d} "
          f"{len(d['sites']):6d} {d['unknown']:8d} {d['empty_label']:9d}  {cats}")
    tot_lines = sum(d["lines"] for d in per.values())
    P(f"{'TOTAL':28s} {tot_lines:7d} {len(set().union(*[d['uniq'] for d in per.values()])):8d} "
      f"{len(set().union(*[d['apks'] for d in per.values()])):5d} "
      f"{len(set().union(*[d['sites'] for d in per.values()])):6d}")

    # pairing-shape census (H2 hypothesis shape): per (apk, class, method, spec) cell,
    # co-occurrence of InvalidSequenceOfMethodCalls with a specific (non-InvalidSeq)
    # category. This is a SHAPE census over pre-repair history, not an attribution.
    P("\n== pairing-shape census (H2 hypothesis shape; cells = (apk,class,method) per spec) ==")
    cells = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in rows:
        cells[r["spec"]][(r["apk"], r["class"], r["method"])].add(cat_of(r))
    P(f"{'spec':28s} {'cells':>7s} {'cells_invseq':>12s} {'cells_specific':>14s} {'cells_BOTH':>10s} {'both/invseq':>11s}")
    for spec in sorted(cells, key=lambda s: -len(cells[s])):
        cc = cells[spec]
        inv = sum(1 for cats in cc.values() if "InvalidSequenceOfMethodCalls" in cats)
        spec_only = sum(1 for cats in cc.values() if cats - {"InvalidSequenceOfMethodCalls"})
        both = sum(1 for cats in cc.values()
                   if "InvalidSequenceOfMethodCalls" in cats and cats - {"InvalidSequenceOfMethodCalls"})
        frac = f"{both/inv:.3f}" if inv else "-"
        P(f"{spec:28s} {len(cc):7d} {inv:12d} {spec_only:14d} {both:10d} {frac:>11s}")

    # MDG oracle-shift stratum (batchD §6.6 check)
    mdg = [r for r in rows if r["spec"] == "MessageDigestSpec" and cat_of(r) == "UnsafeAlgorithm"]
    md5sha1 = [r for r in mdg if ("MD5" in r["message"] or "SHA-1" in r["message"] or "SHA1" in r["message"])]
    P(f"\nMDG oracle-shift stratum: UnsafeAlgorithm lines={len(mdg)}, of which naming "
      f"MD5/SHA-1={len(md5sha1)} — SAFE under the api30 oracle (batchD §6.6: any future "
      f"drop here is oracle change, not repair). Judge-quoted figures were 6 048 / 5 891; "
      f"deltas vs this computation reflect message-matching definition and are printed, not asserted.")

    # zero-emission census (GAMA-SET-16 / GAMA-SET-21 inputs)
    all_specs = ["CipherSpec", "GCMParameterSpecSpec", "DHGenParameterSpecSpec",
                 "HMACParameterSpecSpec", "PBEParameterSpecSpec", "IvParameterSpecSpec",
                 "SecretKeySpecSpec", "CipherInputStreamSpec", "CipherOutputStreamSpec",
                 "KeyPairSpec", "SecretKeySpec", "PBEKeySpecSpec", "KeyGeneratorSpec",
                 "KeyManagerFactorySpec", "TrustManagerFactorySpec", "SSLContextSpec",
                 "KeyStoreSpec", "MacSpec", "MessageDigestSpec", "KeyPairGeneratorSpec",
                 "SecureRandomSpec", "SignatureSpec", "RandomStringPasswordSpec"]
    zero = [s for s in all_specs if s not in per]
    P(f"\nzero-emission specs in the historical file ({len(zero)}): {', '.join(zero)}")
    P("(GAMA-SET-16: CIS/COS/SKY/PBK; GAMA-SET-21: KGN/KMF — all INCONCLUSIVE, replay "
     "batteries named; absence of firing is never acceptance, modelo_semantico §5)")

    P("\n== hypothesis-link table (historical volume x audited mechanism x discriminating test) ==")
    for spec, mech, test in HYPOTHESIS_LINKS:
        key = spec.split(" /")[0]
        vol = per.get(key)
        vols = (f"lines={vol['lines']}, uniq={len(vol['uniq'])}, apks={len(vol['apks'])}, "
                f"sites={len(vol['sites'])}" if vol else "ZERO emission (see census)")
        P(f"- {spec}: [{vols}]")
        P(f"    mechanism (closed, judge-executed): {mech}")
        P(f"    discriminating replay: {test}")
    text = "\n".join(out)
    print(text)
    with open(os.path.join(SETD, "set_cons_hist_output.txt"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())

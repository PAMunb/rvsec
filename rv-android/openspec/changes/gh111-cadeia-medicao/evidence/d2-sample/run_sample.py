"""Task 3.15 — the D2 measurement, plus the two runs decision 3 added.

Two legs per APK against two distinct output directories, because the cache
treats mere existence as a hit and the filename carries no key. Six workers:
the binding constraint is the 12 GB JVM heap per leg against 123 GB of RAM,
not disk (peak scratch is the apktool extraction, 0-117 MB per run).
"""

import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
BIN = f"{ROOT}/.venv/bin/rv-static-analysis"
MOP = os.environ["RVSEC_HOME"] + "/rvsec/rvsec-mop/src/main/resources/jca"
DS = "/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET"
C162 = f"{DS}/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162"
C181 = f"{DS}/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706_selected181"
OUT = os.path.dirname(os.path.abspath(__file__))

# (apk, corpus, predicted N from calibration compiled_net, suffix family)
SAMPLE = [
    ("ch.rmy.android.http_shortcuts_1104060001", C162, 7016, ".debug"),
    ("app.pachli_50",                            C162, 6336, ".current"),
    ("com.nononsenseapps.feeder.play_4025",      C162, 3578, ".debug"),
    ("eu.opencloud.android_9",                   C162, 2600, ".qa.debug"),
    ("com.github.livingwithhippos.unchained_60", C162, 1952, ".debug"),
    ("br.com.colman.petals_3040000",             C162,  762, ".debug"),
    ("com.github.cvzi.screenshottile_148",       C162,  535, ".debug"),
    ("com.kwasow.musekit_1721768604",            C162,  525, ".beta"),
    ("com.vrem.wifianalyzer_71",                 C162,  343, ".BETA"),
    ("com.antony.muzei.pixiv_327",               C162,  169, ".dev"),
    ("me.testcase.ognarviewer_25",               C162,  134, ".debug"),
    ("org.musicbrainz.picard.barcodescanner_38", C162,   51, ".debug"),
]
CONTROL = ("de.grobox.liberario_131", C181, 0, "(none — unresolvable)")


def job(name, apk, corpus, leg, extra, timeout):
    d = f"{OUT}/{leg}/{apk}"
    os.makedirs(d, exist_ok=True)
    log = f"{OUT}/logs/{apk}.{leg}.log"
    cmd = [BIN, "analyze", "--apk", f"{corpus}/{apk}.apk", "--output", d,
           "--mop-dir", MOP, "--analysis-timeout", str(timeout), "--skip-wtg"] + extra
    t0 = time.time()
    with open(log, "w") as fh:
        fh.write("$ " + " ".join(cmd) + "\n\n")
        fh.flush()
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT).returncode
    el = time.time() - t0
    art = f"{d}/{apk}.apk.json"
    refused = art + ".refused"
    path = art if os.path.isfile(art) else (refused if os.path.isfile(refused) else None)
    n, key, src, cdu = None, None, None, None
    if path:
        try:
            raw = json.load(open(path))
            n = len(raw.get("reachability", []))
            key = raw.get("codePackage")
            src = raw.get("codePackageSource")
            cdu = raw.get("class_defs_under_key")
        except Exception as e:                       # truncated artefact
            txt = open(path).read()
            n = f"unparsed({e.__class__.__name__})"
    text = open(log).read()
    rec = dict(name=name, apk=apk, leg=leg, seconds=round(el, 2), rc=rc,
               artifact=os.path.basename(path) if path else None, reachability=n,
               codePackage=key, codePackageSource=src, class_defs_under_key=cdu,
               executed="Executing analysis" in text,
               cache_hit="Analysis result already exists" in text,
               timed_out="Analysis timed out" in text)
    print(json.dumps(rec), flush=True)
    with open(f"{OUT}/results.jsonl", "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


QUEUE = []
# treatments first, most expensive first — they set the makespan
for apk, corpus, n, fam in SAMPLE:
    QUEUE.append((f"{apk}:treatment", apk, corpus, "treat", ["--strip-build-type-suffix"], 5400))
# the symmetric control for task 1.9: untracker post-jar WITH --skip-wtg,
# matching the pre leg's --package-detector exactly
QUEUE.insert(4, ("me.zhanghai.android.untracker_9:control-1.9", "me.zhanghai.android.untracker_9",
                 C162, "ctrl", ["--package-detector"], 5400))
QUEUE.append((f"{CONTROL[0]}:treatment", CONTROL[0], CONTROL[1], "treat",
              ["--strip-build-type-suffix"], 3600))
# baselines: default policy, suffixed key, nothing survives the guard
for apk, corpus, n, fam in SAMPLE + [CONTROL]:
    QUEUE.append((f"{apk}:baseline", apk, corpus, "base", [], 1800))

print(f"# {len(QUEUE)} legs, 6 workers", flush=True)
t0 = time.time()
with ThreadPoolExecutor(max_workers=6) as ex:
    list(ex.map(lambda a: job(*a), QUEUE))
print(f"# total wall clock {round(time.time() - t0)} s", flush=True)

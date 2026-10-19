"""experimento-stampcb, hypothesis H3: the 5 direct JCA targets that ran in no rep of either arm.

Chains (CHAINS below). Each is the unique method per distance level in the full GATOR JSON's
`targetDistances` for the target index (rep pack data/raw/e6-static-analysis/final/<apk>.json; no
edges are available), and every link was read in the baksmali of the corpus APK (apktool -r):
- bitbanana i=4 certToPEM: CertInputView$1.onTabSelected (d2) -> CertificateUtil.DER_To_PEM (d1)
  -> certToPEM. onTabSelected maps the tab text through a sparse switch; only "PEM" (case 3,
  :pswitch_0) calls DER_To_PEM, whose first call is certToPEM, unconditional.
- aegis i=9 KeyStoreHandle.<init>: SecurityPreferencesFragment$$ExternalSyntheticLambda3
  .onPreferenceChange (d3) -> $r8$lambda$q1q2... (d2) -> lambda$onCreatePreferences$5 (d1) ->
  KeyStoreHandle.<init>. lambda$5 reaches it on both branches: no BiometricSlot and
  BiometricsHelper.isAvailable -> BiometricSlotInitializer.authenticate -> new KeyStoreHandle; or a
  BiometricSlot exists -> remove it -> new KeyStoreHandle. The switch itself is visible only when
  the vault is encrypted and enabled only when isAvailable (updateEncryptionPreferences).
- aegis i=7 KeyStoreHandle.generateKey: the same callback at d4 (via BiometricSlotInitializer
  .authenticate, d1), beyond the artifact's d <= 3, so no table record weights it.
- aegis i=28 VaultEntryIcon.generateHash: AssignIconsActivity.onOptionsItemSelected (d3; the
  save item) -> saveAndFinish (d2; per entry with getNewIcon() != null) -> VaultEntryIcon.<init>
  (d1) -> generateHash.
- vault i=15 deleteBiometricSecretKey: SettingsFragment$$ExternalSyntheticLambda6
  .onPreferenceChange (d3) -> $r8$lambda$Jf4c... (d2) -> lambda$onCreatePreferences$8 (d1):
  newValue true -> enableBiometrics(); false -> deleteBiometricSecretKey(). enableBiometrics
  returns false (switch stays off) when BiometricManager.canAuthenticate(0xf) != 0, before
  Encryption.getBiometricCipher.

Per (target, arm, rep), from the logcats and traces:
- `cov_<method>`: processes whose RVSEC-COV logged the chain method (RVSEC-COV logs a method once
  per process, so the count is processes, not calls), plus the extra probes of PROBES;
- `trigger`: for the first COV of the callback method, the step whose interval [t_s, t_{s+1})
  holds it (logcat clock mapped by the ApeRvHb heartbeats, as h2_preferences): s, dec.src,
  dec.ch, dec.mopd, dec.mops and the action's text;
- `host_steps`: steps on the host activity (ACT.name);
- `bind_callback`: `RVSEC-BIND view kind=callback ... callback=<callback class>` lines;
- `hnd_steps`: steps with dec.hnd = the callback class, split by dec.src / dec.ch and with dec.mopd;
- `ret_steps`: steps whose dec.ret lists the target index;
- `pair_<arm>`: the callback class's handlers record pairs for the target, in that arm's derive.

Writes analysis/h3_never_run.csv. Usage: python -I scripts/h3_never_run.py
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze  # noqa: E402
from h2_preferences import bisect_step, read_trace, naive_ms, TS, HB  # noqa: E402

X, OUT, CORPUS = analyze.X, analyze.OUT, analyze.CORPUS

CHAINS = [
    dict(apk="app.michaelwuensch.bitbanana_79.apk", i=4, name="certToPEM",
         cls="app.michaelwuensch.bitbanana.setup.CertInputView$1", host=None,
         chain=["<app.michaelwuensch.bitbanana.setup.CertInputView$1: void onTabSelected(com.google.android.material.tabs.TabLayout$Tab)>",
                "<app.michaelwuensch.bitbanana.util.CertificateUtil: java.lang.String DER_To_PEM(byte[])>",
                "<app.michaelwuensch.bitbanana.util.CertificateUtil: java.lang.String certToPEM(byte[])>"],
         probes=["<app.michaelwuensch.bitbanana.setup.CertInputView: void <init>(android.content.Context,android.util.AttributeSet)>",
                 "<app.michaelwuensch.bitbanana.setup.CertInputView: java.lang.String convertCurrentDataToBase64()>"]),
    dict(apk="com.beemdevelopment.aegis_81.apk", i=9, name="KeyStoreHandle.<init>",
         cls="com.beemdevelopment.aegis.ui.fragments.preferences.SecurityPreferencesFragment$$ExternalSyntheticLambda3",
         host="com.beemdevelopment.aegis.ui.PreferencesActivity",
         chain=["<com.beemdevelopment.aegis.ui.fragments.preferences.SecurityPreferencesFragment$$ExternalSyntheticLambda3: boolean onPreferenceChange(androidx.preference.Preference,java.lang.Object)>",
                "<com.beemdevelopment.aegis.ui.fragments.preferences.SecurityPreferencesFragment: boolean lambda$onCreatePreferences$5(androidx.preference.Preference,java.lang.Object)>",
                "<com.beemdevelopment.aegis.crypto.KeyStoreHandle: void <init>()>"],
         probes=["<com.beemdevelopment.aegis.ui.fragments.preferences.SecurityPreferencesFragment: void updateEncryptionPreferences()>",
                 "<com.beemdevelopment.aegis.helpers.BiometricsHelper: boolean isAvailable(android.content.Context)>",
                 "<com.beemdevelopment.aegis.vault.slots.PasswordSlot: void <init>()>"]),
    dict(apk="com.beemdevelopment.aegis_81.apk", i=7, name="KeyStoreHandle.generateKey",
         cls="com.beemdevelopment.aegis.ui.fragments.preferences.SecurityPreferencesFragment$$ExternalSyntheticLambda3",
         host="com.beemdevelopment.aegis.ui.PreferencesActivity",
         chain=["<com.beemdevelopment.aegis.ui.fragments.preferences.SecurityPreferencesFragment$$ExternalSyntheticLambda3: boolean onPreferenceChange(androidx.preference.Preference,java.lang.Object)>",
                "<com.beemdevelopment.aegis.helpers.BiometricSlotInitializer: void authenticate(androidx.biometric.BiometricPrompt$PromptInfo)>",
                "<com.beemdevelopment.aegis.crypto.KeyStoreHandle: javax.crypto.SecretKey generateKey(java.lang.String)>"],
         probes=["<com.beemdevelopment.aegis.ui.slides.SecuritySetupSlide: void showBiometricPrompt()>"]),
    dict(apk="com.beemdevelopment.aegis_81.apk", i=28, name="VaultEntryIcon.generateHash",
         cls="com.beemdevelopment.aegis.ui.AssignIconsActivity", host="com.beemdevelopment.aegis.ui.AssignIconsActivity",
         chain=["<com.beemdevelopment.aegis.ui.AssignIconsActivity: boolean onOptionsItemSelected(android.view.MenuItem)>",
                "<com.beemdevelopment.aegis.ui.AssignIconsActivity: void saveAndFinish()>",
                "<com.beemdevelopment.aegis.vault.VaultEntryIcon: void <init>(byte[],com.beemdevelopment.aegis.icons.IconType)>",
                "<com.beemdevelopment.aegis.vault.VaultEntryIcon: byte[] generateHash(byte[],com.beemdevelopment.aegis.icons.IconType)>"],
         probes=["<com.beemdevelopment.aegis.ui.AssignIconsActivity: void onCreate(android.os.Bundle)>",
                 "<com.beemdevelopment.aegis.ui.EditEntryActivity: boolean onSave()>",
                 "<com.beemdevelopment.aegis.helpers.BitmapHelper: com.beemdevelopment.aegis.vault.VaultEntryIcon toVaultEntryIcon(android.graphics.Bitmap,com.beemdevelopment.aegis.icons.IconType)>",
                 "<com.beemdevelopment.aegis.ui.fragments.preferences.IconPacksManagerFragment: void importIconPack(android.net.Uri)>"]),
    dict(apk="se.arctosoft.vault_41.apk", i=15, name="deleteBiometricSecretKey",
         cls="se.arctosoft.vault.SettingsFragment$$ExternalSyntheticLambda6", host="se.arctosoft.vault.MainActivity",
         chain=["<se.arctosoft.vault.SettingsFragment$$ExternalSyntheticLambda6: boolean onPreferenceChange(androidx.preference.Preference,java.lang.Object)>",
                "<se.arctosoft.vault.SettingsFragment: boolean lambda$onCreatePreferences$8(androidx.fragment.app.FragmentActivity,se.arctosoft.vault.utils.Settings,androidx.preference.Preference,java.lang.Object)>",
                "<se.arctosoft.vault.encryption.Encryption: void deleteBiometricSecretKey()>"],
         probes=["<se.arctosoft.vault.SettingsFragment: boolean enableBiometrics()>",
                 "<se.arctosoft.vault.encryption.Encryption: javax.crypto.Cipher getBiometricCipher()>"]),
]


def short(sig):
    cls, rest = sig[1:-1].split(": ", 1)
    return cls.rsplit(".", 1)[-1] + "." + rest.split(" ", 1)[1].split("(")[0]


def logcat_cov(path):
    """[(rel ms, sig)] of the RVSEC-COV lines, with the heartbeat offset."""
    raw, offs = [], []
    for line in path.read_text(errors="replace").splitlines():
        m = TS.match(line)
        if not m:
            continue
        if "RVSEC-COV" in line:
            c = analyze.COV.search(line)
            if c:
                raw.append((naive_ms(m.group(1)), c.group(1)))
        elif "ApeRvHb" in line:
            h = HB.search(line)
            if h:
                offs.append(int(h.group(2)) - naive_ms(m.group(1)))
    offs.sort()
    off = offs[len(offs) // 2]
    return [(t + off, s) for t, s in raw], path.read_text(errors="replace")


def text_of(action):
    a = action.split("@", 1)[-1]
    return a.rsplit("][", 1)[-1].rstrip("]")[:40] if "][" in a else a[:40]


def main():
    derives = {a: analyze.load_derive(X / "mount" / a / "derive_mop_artifact.py") for a in ("control", "treatment")}
    pairs = {}
    for apk in {c["apk"] for c in CHAINS}:
        doc = json.loads((CORPUS / f"{apk}.json").read_text())
        for a, mod in derives.items():
            h = mod.derive(doc)["handlers"]
            for c in CHAINS:
                if c["apk"] == apk:
                    rec = h.get(c["cls"], {})
                    pairs[a, c["name"]] = sorted({(ev, d) for ev, ps in rec.get("dist", {}).items()
                                                  for i, d in ps if i == c["i"]}) or ("no record" if not rec else "no pair")
        del doc

    rows = []
    for arm in ("control", "treatment"):
        for apk, rep, logcat, trace in analyze.runs(arm):
            chains = [c for c in CHAINS if c["apk"] == apk]
            if not chains:
                continue
            acts, steps = read_trace(trace)
            acts.pop("MOP_DATA", None)
            cov, text = logcat_cov(logcat)
            times = [s["t"] for s in steps]
            for c in chains:
                row = dict(target=c["name"], apk=apk, arm=arm, rep=rep, pair=str(pairs[arm, c["name"]]))
                for sig in c["chain"] + c["probes"]:
                    row["cov_" + short(sig)] = sum(1 for _, s in cov if s == sig)
                first = next((t for t, s in cov if s == c["chain"][0]), None)
                if first is not None:
                    k = bisect_step(times, first)
                    s = steps[k] if k >= 0 else None
                    row["trigger"] = (f"s={s['s']} src={s['dec'].get('src')} ch={s['dec'].get('ch')} "
                                      f"mopd={s['dec'].get('mopd', '-')} mops={s['dec'].get('mops', '-')} "
                                      f"act={acts.get(s['act'], '').rsplit('.', 1)[-1]} text={text_of(s['dec']['a'])}"
                                      if s else "before step 1")
                else:
                    row["trigger"] = ""
                row["host_steps"] = sum(acts.get(s["act"]) == c["host"] for s in steps) if c["host"] else ""
                row["bind_callback"] = text.count(f"callback={c['cls']} ")
                hs = [s["dec"] for s in steps if s["dec"].get("hnd") == c["cls"]]
                row["hnd_steps"] = len(hs)
                row["hnd_src_ch"] = ";".join(f"{k}:{v}" for k, v in sorted(Counter(
                    f"{d.get('src')}/{d.get('ch')}" for d in hs).items()))
                row["hnd_mopd"] = ";".join(f"{k}:{v}" for k, v in sorted(Counter(
                    str(d.get("mopd", "-")) for d in hs).items()))
                row["ret_steps"] = ";".join(str(s["s"]) for s in steps if c["i"] in s["dec"].get("ret", []))
                rows.append(row)

    for name in [c["name"] for c in CHAINS]:
        sub = [r for r in rows if r["target"] == name]
        keys = list(dict.fromkeys(k for r in sub for k in r))
        print(f"\n== {name}")
        for r in sub:
            print("  ", " ".join(f"{k}={r.get(k, '')}" for k in keys if k not in ("target", "apk")))
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT / "h3_never_run.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, restval="")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()

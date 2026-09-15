# Smoke APKs for task 15.2 (chosen from `sweep_before.csv`)

The design fixes four criteria for the end-to-end smoke (Open Questions): an APK that reaches
`SSLContext.init` through a TLS client, one with embedded BouncyCastle, one with a hooked
`Cipher.init` that is a branch target, and one with a `KeyStore.getEntry` call. The choice is made
from the before-sweep over the 163 APKs instrumented with `jca_android` + dexlib2
(`/home/pedro/desenvolvimento/RV_ANDROID_DATASET_FINAL/APKS_INSTRUMENTED_jca_android_dexlib2`).
The TLS-client and BouncyCastle facts come from the G5 scratch driver that ran in the same disk
pass; they are not columns of the sweep, which names no library.

| APK | TLS client → `SSLContext.init` | BouncyCastle | hooked `Cipher.init` branch target | `KeyStore.getEntry`/`setEntry` | arity call sites (a) |
|---|---|---|---|---|---|
| `eu.faircode.email_2322.apk` | yes | yes | yes (9) | yes | 19 |
| `me.diamondforge.tokn_19.apk` | yes | yes | yes | yes | 5 |
| `app.pachli_50.apk` | yes | — | — | yes (3) | 10 |
| `de.markusfisch.android.binaryeye_174.apk` | — | yes | yes (6) | — | 4 |

The first two satisfy all four criteria on their own; the other two repeat single criteria from a
different code base, so a failure of one APK does not leave a criterion untested. Original
(non-instrumented) APKs are instrumented through the production path in WAVE 3 (task 15.2, second
half), after the reactor build of task 15.1.

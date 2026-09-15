# After sweep and the woven after-finally handler (task 15.3)

The four smoke APKs of `smoke_apks.md`, instrumented through the production path with
`jca_android` and the DEX-native weaver of this change (`scripts/gh114_weave_sweep.py`, the same
script that produced `sweep_before.csv` over the 163 APKs of the previous instrumentation).
`sweep_after.csv` carries the four rows and the `TOTAL` trailer; `sweep_after_sites.csv` names, for
every counted item, the DEX, the caller and the target.

## The four counts

| measure | before (same four APKs) | after |
|---|---|---|
| (a) arity pairs fired — call sites / inline hooks | 38 call sites (10 + 4 + 19 + 5) | **0 / 0**, and no pair at all (`arity_pairs = 0`) |
| (b) framework-subtype invokes left unwoven | 332 (26 + 112 + 130 + 64) | **0** |
| (c) hooked calls that are branch targets | 89 (4 + 28 + 37 + 20) of 1,248 before-hooks | **0** of 1,253 |
| (d) `KeyStore.getEntry`/`setEntry` calls woven | 0 of 5 | **5 of 5** |

The before column is read from `sweep_before.csv`, whose rows for these four APKs come from the
instrumentation that produced `APKS_INSTRUMENTED_jca_android_dexlib2`. `wrappers` goes from 135 to
141: the six new wrappers are the inherited framework targets A2 resolves.

Every `getEntry` site is woven inline (`woven-inline` in `sweep_after_sites.csv`), and the three in
`app.pachli_50.apk` and one each in `eu.faircode.email_2322.apk` and `me.diamondforge.tokn_19.apk`
carry the nested parameter type `Ljava/security/KeyStore$ProtectionParameter;` that A4 resolves;
`de.markusfisch.android.binaryeye_174.apk` has no such call and reports `0 of 0`.

## The after-finally handler in the woven bytecode (INV-INS-163)

`classes24.dex` of `eu.faircode.email_2322.apk` is the DEX that defines `mop/MonitorWrappers`.
Disassembled with `dexdump -d`, the wrapper of `KeyAgreement.doPhase` reads:

```
mop.MonitorWrappers.javax_crypto_KeyAgreement_doPhase:(Ljavax/crypto/KeyAgreement;Ljava/security/Key;Z)Ljava/security/Key;
 0000: invoke-virtual {v1, v2, v3}, Ljavax/crypto/KeyAgreement;.doPhase:(Ljava/security/Key;Z)Ljava/security/Key;
 0003: move-result-object v0
 0005: invoke-static {v2, v3, v1}, Lmop/MultiSpec_1RuntimeMonitor;.KeyAgreementSpec_dophaseEvent:(Ljava/security/Key;ZLjavax/crypto/KeyAgreement;)V
 0008: return-object v0
 0009: move-exception v0
 000a: invoke-static {v2, v3, v1}, Lmop/MultiSpec_1RuntimeMonitor;.KeyAgreementSpec_dophaseEvent:(Ljava/security/Key;ZLjavax/crypto/KeyAgreement;)V
 000d: throw v0
catches : 1
  0x0000 - 0x0004
    <any> -> 0x0009
```

The try range covers the `invoke-virtual` of `doPhase`; the catch-all handler invokes the same
monitor event with the same registers (`v2`, `v3`, `v1` — the key, the flag and the target) and ends
in `throw` of the caught exception, so the original throwable propagates unchanged. The normal path
invokes the event once and returns the call's result.

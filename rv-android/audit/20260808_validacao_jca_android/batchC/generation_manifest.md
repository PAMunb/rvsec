# Batch C — generation manifest (common round input)

Date: 2026-08-09. Produced by the audit orchestrator, per judge adjustment 1
(`pilot/juiz_sintese.md` §6) and deviations D-piloto-3 / D-batchA-1
(`fase0/desvios.md`). Generation ran in a scratch directory, never over the spec
tree. Same pipeline and toolchain as batches A/B (`batchA/generation_manifest.md`
§Commands); `.rvm` kept for auditors.

## Batch C specs (5 of the 10 remaining; pairing per `fase0/inventario_pareamento.md`)

| Spec `.mop` (jca_android) | sha256 (= frozen manifest) | Paired CrySL rule (api30) | sha256 | ID abbrev |
|---|---|---|---|---|
| KeyGeneratorSpec.mop | `3788c3d8d0993b838d3469dd703b8df735cb16a1f98b7531e7e14a071cb77877` | KeyGenerator.cryptsl | `30779a3a516e6d0dd6b269a5528ef90ccf06564a5e08d3222f7edd6126de9ed3` | KGN |
| KeyManagerFactorySpec.mop | `a7fb68fb7bd119133b416b4e61a9d3898cfe5a03fca9a3bc7eecabff97eece8a` | KeyManagerFactory.cryptsl | `ebd1639ecc20d65934057e82e5dcdb8e256b206da00b123c86a4978f8f0afb4a` | KMF |
| TrustManagerFactorySpec.mop | `a4691fd43de403e5788e05a4ce8c3060cc4158072a282dccddab27a71a337a70` | TrustManagerFactory.cryptsl | `ae2a9d8f3fae3b782e81124846fc8b7943f9aa561764f9f366a685addbf160e6` | TMF |
| SSLContextSpec.mop | `42760be50837ab884a8bcf57b0a5253cbe63de1545c3e5f0d62e8aaaf63a15ce` | SSLContext.cryptsl | `610bbcdb4a71ffcac8a41a9ca0ff44ac4385f8b3cf63c56a5affdca9521df940` | SSL |
| KeyStoreSpec.mop | `3392a11d77305997a7e4f20559e24468386c9592355a5a0de198c85b825f8b00` | KeyStore.cryptsl | `083b171f5aea1e203d8136091ebf2a01172f9dca06d8ecd9e6bd39cbf432cd69` | KST |

All five `.mop` hashes byte-identical to `fase0/manifest_hashes.md` (jca_android
table) — freeze check PASS. All five diverge from the frozen `jca` twins, as expected
for the repair-carrying set.

## Results

All 10 executions (javamop + rv-monitor per spec): exit 0, empty non-time stderr, no
error/warning strings in stdout. Caveat in force: exit 0 does not guarantee success —
inspect artifacts (pilot GCM fail-open; batch A stray-paren; batch B undefined-symbol
all-fail row and `epsilon`-typo acceptance change).

| Spec | javamop wall/RSS | rv-monitor wall/RSS |
|---|---|---|
| KeyGeneratorSpec | 0.44 s / 87.7 MB | 1.05 s / 108.7 MB |
| KeyManagerFactorySpec | 0.42 s / 87.8 MB | 0.90 s / 89.7 MB |
| TrustManagerFactorySpec | 0.41 s / 86.7 MB | 0.93 s / 89.2 MB |
| SSLContextSpec | 0.41 s / 87.2 MB | 0.88 s / 88.2 MB |
| KeyStoreSpec | 0.42 s / 87.3 MB | 0.97 s / 93.3 MB |

## Artifact hashes (sha256)

```
85beaafe100fc2a9cb0be51734260f646d798d0c11f8df3bf64d3b771a7525bd  gen_KeyGeneratorSpec/out/KeyGeneratorSpecMonitorAspect.aj
494e285ef036f652619b4ad0afa008fd694d5f52987906deffadfdf21983165f  gen_KeyGeneratorSpec/out/KeyGeneratorSpecMonitorAspect.json
de9e52053a47a661be3c5c687cd7fb6524969090b4b32a99990010db3fd58ecd  gen_KeyGeneratorSpec/out/KeyGeneratorSpecRuntimeMonitor.java
31913e5bcd765cbff77ac4276924f2d1db99b324e9e9d42f0f7c1db6b625e2ab  gen_KeyGeneratorSpec/out/KeyGeneratorSpec.rvm
951533724b83894b0664f34f0312b0133dfdbdedcffcd1318549281269a38d14  gen_KeyManagerFactorySpec/out/KeyManagerFactorySpecMonitorAspect.aj
66042555845a53b1efbb68bb300279c401bfb4092bcf33559fc3dda3ab70256f  gen_KeyManagerFactorySpec/out/KeyManagerFactorySpecMonitorAspect.json
dca6fb3767c267fede1a71104a7a6a8169e05dd965234f0435d8d553ca82dd37  gen_KeyManagerFactorySpec/out/KeyManagerFactorySpecRuntimeMonitor.java
3ca38df18a731c928e470979aea38b0f5e34822775dc2d4a4f64b407db230005  gen_KeyManagerFactorySpec/out/KeyManagerFactorySpec.rvm
2e39523fcc03366c190e54fb0d2645ec74919be32052a7a8986425c38d544edb  gen_TrustManagerFactorySpec/out/TrustManagerFactorySpecMonitorAspect.aj
2efa3e302876f21f36fe29c26a3fc439b83481c275456f78683d0d202a56eb04  gen_TrustManagerFactorySpec/out/TrustManagerFactorySpecMonitorAspect.json
a99d7d54f423f30cc3465c2e635bdcf079ee459f0f2821d17a9113ad3e769f53  gen_TrustManagerFactorySpec/out/TrustManagerFactorySpecRuntimeMonitor.java
89e3e6b4bcf98324ec966d5939db7af252b6e7973f19ead6d09480bea2ade6c9  gen_TrustManagerFactorySpec/out/TrustManagerFactorySpec.rvm
41345efbddb7ff8203a6bbfb9039d7bb79910fc568332ffba773f627289d8f42  gen_SSLContextSpec/out/SSLContextSpecMonitorAspect.aj
211b9bde4803beae0e71dd34a23004af18932c70d1f273e81cd6d53f2c898e31  gen_SSLContextSpec/out/SSLContextSpecMonitorAspect.json
ea212b12220b1d62152b00cab92dcd36b89fd97b321e4b3bd8b2131d2df56569  gen_SSLContextSpec/out/SSLContextSpecRuntimeMonitor.java
23e06621957a5b6661741a721eff53dc6758639759aad9ad37f344d913480aab  gen_SSLContextSpec/out/SSLContextSpec.rvm
52a3bf836562275812b3e01dec08e9a686a6a31ed9bcc992d6fad7919ecd2f84  gen_KeyStoreSpec/out/KeyStoreSpecMonitorAspect.aj
706c0c466c67c66ffeed164fc6d3a93b9a241b741cdcb636bae51fce5f670526  gen_KeyStoreSpec/out/KeyStoreSpecMonitorAspect.json
45befd0b9ddd39cd96a4ec70ea83013454e2ef61ab2311675aeba1d94fe7ee45  gen_KeyStoreSpec/out/KeyStoreSpecRuntimeMonitor.java
aa37b08085d65bba527698cbeb98ce25f6b19eab2d578b7aae9e1bbb989c140d  gen_KeyStoreSpec/out/KeyStoreSpec.rvm
```

Scratch location this session:
`/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/d2ed0fb6-e4be-4945-abb4-21d8af2acd28/scratchpad/batchC/gen_<Spec>/`.
Commands + input hashes are the durable reproduction path (generator determinism, not
independent replication — REF-11).

## Round rules carried forward (binding for batch C)

All rules of `batchB/generation_manifest.md` §Round-rules remain in force
(D-piloto-1..4, D-batchA-1, indexing-tree standard check, dimension-5 multi-route,
decisive evidence preserved under `audit/.../batchC/`, fail-open probes, javap trap),
plus batch B additions:

- **Parameterless-spec check is standard** (FEN batch B: CIS/COS process-global
  monitors): verify each spec declares a parameter AND every event binds it (the
  unbound-`c1` KeyPair shape counts as a failure of the second half).
- **New fail-open shapes measured in batch B**: undefined ERE symbol leaves an
  orphaned event with an all-fail row (permanent FP source); a typo'd `epsilon`
  silently changes acceptance; rv-monitor with missing input prints `[Error]` but
  exits 0.
- **dexlib2 capture caveats (production path)**: `AndroidClassIndex.methods()` is
  declared-only (inherited members invisible); `WrapperEmitter.findFirstCall`
  keeps only the first `call()` disjunct (`WrapperEmitter.java:507-524`);
  `literalFallback` drops instance targets. Batch C specs are `getInstance`/`init`
  factories — static methods + instance methods mix: measure both halves.
- **`ErrorSummary` drops `expecting`** — distinct clause accusations collapse in the
  CSV (batch B, SET).
- Batch C is the READER-heavy side of several predicate edges audited in batches A/B
  (e.g., TMF/KMF/SSL context chain; KeyStore ↔ KMF; KeyGenerator writes GENERATED_KEY
  read elsewhere): audit both directions, citing the established FEN registers
  (FEN-SET-GENERATEDKEY-2A-CASA and the batch B gate/starvation phenomena).
- Judge observations for batch C in `batchB/juiz_sintese_batchB.md` §6 (and the §8
  final-decision additions once published) are BINDING reading for reviewers.

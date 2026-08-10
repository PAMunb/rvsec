# Batch B — generation manifest (common round input)

Date: 2026-08-09. Produced by the audit orchestrator, per judge adjustment 1
(`pilot/juiz_sintese.md` §6) and deviations D-piloto-3 / D-batchA-1
(`fase0/desvios.md`). Generation ran in a scratch directory, never over the spec
tree. Same pipeline and toolchain as batch A (`batchA/generation_manifest.md`);
`.rvm` kept for auditors.

## Batch B specs (5 of the 15 remaining; pairing per `fase0/inventario_pareamento.md`)

| Spec `.mop` (jca_android) | sha256 (= frozen manifest) | Paired CrySL rule (api30) | sha256 | ID abbrev |
|---|---|---|---|---|
| CipherInputStreamSpec.mop | `d71a86d8b396633bd3609fac1746b6e346e354d4760ab7d14444ecca87f84bb0` | CipherInputStream.cryptsl | `f291a28979d71b012b1c550f4af0c90bd2282ef4f49b7d574e37319bc6d52122` | CIS |
| CipherOutputStreamSpec.mop | `c105492951623e0b795f7a31341d340109583253f8820f14f290e66d981d9a70` | CipherOutputStream.cryptsl | `9a57e52bf6bb870a1812ffd0ca04c7696212813e1d85a481fcc985f1fddb45b2` | COS |
| KeyPairSpec.mop | `8bc496323dde905cd4dc0df0d543f2c77eb98b41951118a6379b9a575b6ffdf9` | KeyPair.cryptsl | `e204371fd1f4ed8f2036c87730b74f83e5f872bd7ea65982e82caeb0e29b70dd` | KPR |
| SecretKeySpec.mop (declared spec `SecretKeySpec`, target class `javax.crypto.SecretKey` — interface; pairing by CONTENT, the file name misleads) | `03768f3bb39fc5f2e1a230c30d6c9659d727ee72d633eb37f735d66c067b494b` | SecretKey.cryptsl | `ed4677b1e365920b0a1ec5fc03b03fbc4f208321b5904e95f8cad4d3fcee6b88` | SKY |
| PBEKeySpecSpec.mop | `8fdcabe6300321aa1d35214c72107a5bc32be4d95995f65d9e4469d86df578c7` | PBEKeySpec.cryptsl | `05f05202b9c5c198c2144a9bdadeafa3e3b66878a8b21ed959b975fbc2735da1` | PBK |

All five `.mop` hashes byte-identical to `fase0/manifest_hashes.md` (jca_android
table) — freeze check PASS. All five diverge from the frozen `jca` twins, as expected
for the repair-carrying set.

## Commands

Identical to batch A (see `batchA/generation_manifest.md` §Commands), applied per spec
under `$SCRATCH/batchB/gen_<Spec>/`.

## Results

All 10 executions: exit 0, empty non-time stderr, no error/warning strings in stdout.
Caveat in force: exit 0 does not guarantee success (pilot GCM fail-open; batch A
stray-paren absorption) — inspect artifacts.

| Spec | javamop wall/RSS | rv-monitor wall/RSS |
|---|---|---|
| CipherInputStreamSpec | 0.43 s / 86.2 MB | 0.93 s / 85.6 MB |
| CipherOutputStreamSpec | 0.43 s / 85.6 MB | 0.92 s / 85.6 MB |
| KeyPairSpec | 0.43 s / 85.1 MB | 0.95 s / 87.1 MB |
| SecretKeySpec | 0.42 s / 84.6 MB | 0.94 s / 86.7 MB |
| PBEKeySpecSpec | 0.44 s / 87.2 MB | 1.02 s / 90.7 MB |

## Artifact hashes (sha256)

```
6ccf00da15796823213350ed87e5941f242d1054f623a7981d45b2ed963c8318  gen_CipherInputStreamSpec/out/CipherInputStreamSpecMonitorAspect.aj
277026d4e7eea6661c527d197da1fd832f289890f3df339f92552a34fd93dffc  gen_CipherInputStreamSpec/out/CipherInputStreamSpecMonitorAspect.json
aa6e492e9c256db4e17ed96ae8ec6c3d870254d513b27b807c3b5ebf6be926c6  gen_CipherInputStreamSpec/out/CipherInputStreamSpecRuntimeMonitor.java
8a23b29b49fe0b634083b69e502b2e31bd39dad02f1336387b978b6aa5756077  gen_CipherInputStreamSpec/out/CipherInputStreamSpec.rvm
2542e5356a65f7d408520a0f1b5e48823ae33228e90bbedaf91c1716f45ad112  gen_CipherOutputStreamSpec/out/CipherOutputStreamSpecMonitorAspect.aj
e4c44a79be7f927a03d72d1c38ef3c97e34f3b92edaf88c3ad47a5e9ec832c71  gen_CipherOutputStreamSpec/out/CipherOutputStreamSpecMonitorAspect.json
65df35f2ea13f989fc1775483eb36134e213c70871b008000533c858f618a7dd  gen_CipherOutputStreamSpec/out/CipherOutputStreamSpecRuntimeMonitor.java
7c5752549e6654b137cb98d37209d33d54f251b6103fd66b2ec253ab3a9f7a92  gen_CipherOutputStreamSpec/out/CipherOutputStreamSpec.rvm
4e9d6323060e0864ce29aacb7f195dde6ab9e78e371969ce507262f627a65c22  gen_KeyPairSpec/out/KeyPairSpecMonitorAspect.aj
95ec85115aaa0c588eda74c47f8b7cb13725d9f394623e19cff87f544a11b34c  gen_KeyPairSpec/out/KeyPairSpecMonitorAspect.json
aa4c0f907f8eb972815916ef5b72b97d6c92a26748bb64fa0bdf00136d328362  gen_KeyPairSpec/out/KeyPairSpecRuntimeMonitor.java
4bdd1a1226e5e4501e78976614eeb96e05134e27140d4e7c563735004e7f7517  gen_KeyPairSpec/out/KeyPairSpec.rvm
6f4d09bb421dce6b1c701cb5ea6ab56ea14181bfaf27e9eec56be7d60c4bb23a  gen_SecretKeySpec/out/SecretKeySpecMonitorAspect.aj
cfc4f9cad6f4939fb544458289a09d564ef3c440586194573fe68f9ac97daed3  gen_SecretKeySpec/out/SecretKeySpecMonitorAspect.json
69791c1aa9174698f9e4ef2f3472e3b68733a7be1835a4863b76b4bc7ea75b4a  gen_SecretKeySpec/out/SecretKeySpecRuntimeMonitor.java
346aee6b804c5c588c2b7b8af908c106589bf94013448b721df80cf2c65ac77b  gen_SecretKeySpec/out/SecretKeySpec.rvm
f93a16feb46b82a41a91abee3ad6a5cbc02e98632beee1ca8ea3a9a214d04345  gen_PBEKeySpecSpec/out/PBEKeySpecSpecMonitorAspect.aj
f44554a1e6cfeef74d6547ab0b49e110d0586bd7a3d78d6992add540b6399bcd  gen_PBEKeySpecSpec/out/PBEKeySpecSpecMonitorAspect.json
30795a79621cdff1a2b0923418bf031e52bed119b318e5e07126dc8f79c9c9b8  gen_PBEKeySpecSpec/out/PBEKeySpecSpecRuntimeMonitor.java
801e47dcbf046046f11dddf68d2c47b45e10aa3e375432241ad75156238e8c61  gen_PBEKeySpecSpec/out/PBEKeySpecSpec.rvm
```

Scratch location this session:
`/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/d2ed0fb6-e4be-4945-abb4-21d8af2acd28/scratchpad/batchB/gen_<Spec>/`.
Commands + input hashes are the durable reproduction path (generator determinism, not
independent replication — REF-11).

## Round rules carried forward (batch A lessons, binding for batch B)

- D-piloto-1 (ORDER reading A), D-piloto-2 (standard tests), D-piloto-3 (effective
  automaton), D-piloto-4 (claim→dimension at creation; SET separate; FEN-* IDs; six
  states), D-batchA-1 (raw weighted sum is the score of record when dimensions are
  empty) — all in `fase0/desvios.md`.
- **Indexing-tree check is standard** (FEN-HMC-MONITOR-GLOBAL, batch A): verify the
  spec parameter is bound by every event and the generated indexing tree is
  per-object, not a global static tuple.
- **Dimension-5 must be multi-route** (REF-B-09): Beta and Gama also produce
  parametric/lifecycle claims with executable two-object/interleaving tests where
  possible, not Alfa alone.
- **Decisive executed evidence is preserved under `audit/.../batchB/`** with the
  producing agent's prefix, hashed (REF-B-01): scratch is not a replication package.
- **Fail-open probes standard** (batch A measured: stray `)` silently absorbed;
  undefined ORDER symbol silently dropped; stray `(` prints MOPException but exits 0
  with no artifacts).
- Known cross-spec phenomenon to test the counterpart of: FEN-SET-GENERATEDKEY-2A-CASA
  (the `[obj, alg]` second slot dropped on the write side — pilot ALFA-CIP-07, batch A
  SKS). Batch B contains the READER side of several predicates (KeyPair, SecretKey,
  Cipher streams) — audit both directions of each edge.
- SKY targets an INTERFACE (`javax.crypto.SecretKey`); `javax.crypto.spec.SecretKeySpec`
  (audited in batch A) IMPLEMENTS it — cross-spec double-fire on the same runtime
  object is an explicit check this round.
- `javap -classpath` silently falls back to the JDK for `javax.*` — build member
  tables from extracted class bytes (batch A trap, documented in beta_report.md).

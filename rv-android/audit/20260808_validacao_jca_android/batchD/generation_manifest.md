# Batch D — generation manifest (common round input)

Date: 2026-08-09. Produced by the audit orchestrator, per judge adjustment 1
(`pilot/juiz_sintese.md` §6) and deviations D-piloto-3 / D-batchA-1 / D-batchB-1
(`fase0/desvios.md`). Generation ran in a scratch directory, never over the spec
tree. Same pipeline and toolchain as batches A/B/C (`batchA/generation_manifest.md`
§Commands); `.rvm` kept for auditors. This is the LAST batch: with it, all 20
non-pilot specs of the round are covered (RandomStringPassword excluded by
researcher decision, `fase0/manifesto.md`).

## Batch D specs (final 5; pairing per `fase0/inventario_pareamento.md`)

| Spec `.mop` (jca_android) | sha256 (= frozen manifest) | Paired CrySL rule (api30) | sha256 | ID abbrev |
|---|---|---|---|---|
| MacSpec.mop | `db8b0d12be1f3b0a3ea40531d9b3a358a29105d4cfed6444f2bb70c61651c922` | Mac.cryptsl | `17245e0c95a67ab3ceb475a22cc7ecd64040969e6384520e4b487813cb3c03a1` | MAC |
| MessageDigestSpec.mop | `03ff03db45f0cfe56041c628c0ad771c1e7e134eb9a812769a178bce7bb7187c` | MessageDigest.cryptsl | `6bc3d2be90a449cb7ace2559bdbea38d6911638d2ffcace7c01d2537ee98d587` | MDG |
| KeyPairGeneratorSpec.mop | `9a2628406a78dd7f3983c5ed352379eb0b9ac0dc6c7379adc05c53000f5ac994` | KeyPairGenerator.cryptsl | `c820d2d0394bedc7265436edeec0be7612b784baab30dc53836510978f5e66d0` | KPG |
| SecureRandomSpec.mop | `9e58c92c395bdb2f3c4da88925076112cbf1aa3c5519d37e27ed79737479b7d3` | SecureRandom.cryptsl | `69c55557c0a430dc37d35c64c7bacfd68a383dba4d3c1fc00033fe60c6886c02` | SRD |
| SignatureSpec.mop | `68dd32a67ecae1c4ed23391021acd398a2fe167bc7018dbf63907cdf58272637` | Signature.cryptsl | `ce3b0317f52a657b5c90c304112da75edf1eaf1276017758c56c0ae2fc814230` | SIG |

All five `.mop` hashes byte-identical to `fase0/manifest_hashes.md` (jca_android
table) — freeze check PASS. All five diverge from the frozen `jca` twins.

## Results

All 10 executions: exit 0, empty non-time stderr, no error/warning strings in stdout.
Caveat in force: exit 0 does not guarantee success — inspect artifacts.

| Spec | javamop wall/RSS | rv-monitor wall/RSS | Note |
|---|---|---|---|
| MacSpec | 0.46 s / 89.3 MB | 1.65 s / 200.4 MB | 11 events |
| MessageDigestSpec | 0.44 s / 87.7 MB | 1.05 s / 98.4 MB | 8 events |
| KeyPairGeneratorSpec | 0.44 s / 87.2 MB | 1.12 s / 109.7 MB | 9 events |
| SecureRandomSpec | 0.44 s / 89.8 MB | **12.32 s / 1.59 GB** | 15 events — largest alphabet of the set; nearest to the 17-event ceiling; G2 must measure coenable saturation carefully |
| SignatureSpec | 0.45 s / 89.7 MB | 2.20 s / 308.7 MB | 12 events |

## Artifact hashes (sha256)

```
bf26c8e7f6c826b266eb9970ffa33b9f2feecd27e2cd7e2f62082ca773341f2c  gen_MacSpec/out/MacSpecMonitorAspect.aj
b4b7ef071d0c8a366cddf91ec39f5da4081879e06e8c69912b04c6b1b634c7f4  gen_MacSpec/out/MacSpecMonitorAspect.json
de080e29df10f0d690079b10603f1bd17f8b4125ef0fa689ccb09c280829c5e4  gen_MacSpec/out/MacSpecRuntimeMonitor.java
90f602eead52eac09a9e2f8aec958f2b81e5a200b214fec45d9753bb85e95a6b  gen_MacSpec/out/MacSpec.rvm
70b2942890eae691a103940eb1fdb8c3e2966b52b879869744f2122ea85d2222  gen_MessageDigestSpec/out/MessageDigestSpecMonitorAspect.aj
e5990740330b66ca6489d3bd1e22e9607d41b8ead7e3ad01dea1737edf2fedb4  gen_MessageDigestSpec/out/MessageDigestSpecMonitorAspect.json
6239fd2c1d55e680a3ca8376284c56754d153f4ee4001a78deeaa9b04b30f9ca  gen_MessageDigestSpec/out/MessageDigestSpecRuntimeMonitor.java
cab9e6952528f8c787a764a6a6906e244db02c35568670482d8eadabf9f23e9f  gen_MessageDigestSpec/out/MessageDigestSpec.rvm
e187009c989a5bbaf64967bc7c0e51daf2a676eceb97f93bd81f7a0ddf634c5a  gen_KeyPairGeneratorSpec/out/KeyPairGeneratorSpecMonitorAspect.aj
0ee58e37d516943aa376742f0215aa331388abc8cac4759c2d486d0a2c63d47d  gen_KeyPairGeneratorSpec/out/KeyPairGeneratorSpecMonitorAspect.json
9bc45d18a63ae019937b4b1f7f5cbbaea32f6ae6169207064d4fa8d510c85bdf  gen_KeyPairGeneratorSpec/out/KeyPairGeneratorSpecRuntimeMonitor.java
bee7f370d2d0b4ddcc737c69777efd8626c85f311c7b21e2d07ad45902376d9f  gen_KeyPairGeneratorSpec/out/KeyPairGeneratorSpec.rvm
8f9457b923e0e1b832d7713fc19db76f37c52125cc14c100a7aa4c2e9ff13612  gen_SecureRandomSpec/out/SecureRandomSpecMonitorAspect.aj
11bfefe279347d0ebcb1594c438ba344fbd2dc52694ff6914297b9b3095acafb  gen_SecureRandomSpec/out/SecureRandomSpecMonitorAspect.json
cfed51687cf0138a6c78ead44470b85a31d16ca103a7a6329b726f28ff7bb799  gen_SecureRandomSpec/out/SecureRandomSpecRuntimeMonitor.java
97ac595afa0dfae6fe0f03d9e69f03d69f6b92afb1c4603eb9856b9b4cc662e3  gen_SecureRandomSpec/out/SecureRandomSpec.rvm
5f7924523b80fcd08a694d2478d2485be23655918e0f108044d83c429b863aa8  gen_SignatureSpec/out/SignatureSpecMonitorAspect.aj
ad19a20a0e20be6e13cfde0e46e0650be931d54ae3b55ca449997923241e104d  gen_SignatureSpec/out/SignatureSpecMonitorAspect.json
21be928258d11ccf6ac79582908c5570fa699f88754e0a87428f5d707b0856b1  gen_SignatureSpec/out/SignatureSpecRuntimeMonitor.java
fc5e6368609e2ba298dba7a9088a387ebea26188932bf940ffb5ae17c47662ac  gen_SignatureSpec/out/SignatureSpec.rvm
```

Scratch location this session:
`/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/d2ed0fb6-e4be-4945-abb4-21d8af2acd28/scratchpad/batchD/gen_<Spec>/`.

## Round rules carried forward (binding for batch D)

All rules of `batchC/generation_manifest.md` §Round-rules remain in force
(D-piloto-1..4, D-batchA-1, D-batchB-1, indexing-tree and parameterless-spec checks,
dimension-5 multi-route, decisive evidence preserved under `audit/.../batchD/`,
fail-open probes, dexlib2 caveats, `ErrorSummary` drops `expecting`, javap trap,
provenance column jca-inherited vs gh101-introduced), plus batch-D-specific notes:

- Adversarial review of gh101 decisions concentrated here (protocol §8): removal of
  `MessageDigest.reset` (D-S12 family), `!macced[_, plainText]` transcription (Mac),
  D-S13 `ByteBuffer` FN and `Byte` cache over-reporting. The pilot's spurious-@fail
  hypothesis H2 names TMF and KPG; KPG is in this batch — and batch C's Gama found
  the same-call pairing shape in 5/5 specs (FEN-C-PAIRING-IMEDIATO): test it here.
- KPG is the WRITER of `generatedKeyPair` read by batch B's KeyPairSpec (which was
  REPROVADA with an unbound creation event) — audit the edge end to end.
- SRD (SecureRandom) is the producer of `RANDOMIZED` consumed across the whole set
  (pilot + batches A/B): its writer semantics decide several downstream verdicts'
  residual uncertainty; audit the writer side of every RANDOMIZED edge.
- Historical volume: MessageDigest/Signature/Mac carry the pilot's H4 residue (empty
  labels) — Gama must revisit H4 with the batch C update ("but found ." live shape).

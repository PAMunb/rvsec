# Batch A — generation manifest (common round input)

Date: 2026-08-09. Produced by the audit orchestrator, per judge adjustment 1
(`pilot/juiz_sintese.md` §6) and deviation D-piloto-3 (`fase0/desvios.md`): the
effective automaton extracted from the generated artifact is the common input of the
round; the `.mop` syntax is only the initial hypothesis. Generation ran in a scratch
directory, never over the spec tree (protocol §4; `fase0/pre_registro.md` §5).

## Batch A specs (5 of the 20 remaining; pairing per `fase0/inventario_pareamento.md`)

| Spec `.mop` (jca_android) | sha256 (= frozen manifest) | Paired CrySL rule (api30) | sha256 |
|---|---|---|---|
| DHGenParameterSpecSpec.mop | `f2f6aed6d049adc24b0a8be5c7901c5d2c163360866ae4e06c3425508f1072eb` | DHGenParameterSpec.cryptsl | `b5177f436864a60288a57fcab92baa58fe56544fcf1933c18ee0f32cc7335e98` |
| HMACParameterSpecSpec.mop | `254040e78e3215708ab3855e08661413f20a34fe27b953d03121b300f608f282` | HMACParameterSpec.cryptsl | `61d064317962f3a5fd801b989f311e4b550366518777534da21d8e05b714f14e` |
| PBEParameterSpecSpec.mop | `f088e3b7cd4fa111c0f7da4286bd4c216f1a76672a43e7c18a7b0465df7635fd` | PBEParameterSpec.cryptsl | `a6b7d2b18804502d9f70f54693ba6d6a245549457c1c0404726f38db48c8c827` |
| IvParameterSpec.mop (spec `IvParameterSpecSpec`) | `633237ac49e0bcc9b6bfd83284a4d4821130a204178839a08a8b538d8704fede` | IvParameterSpec.cryptsl | `833c3e231f334396789727c41c43e81a593df81b2fa51fba760e7031ee81a1b6` |
| SecretKeySpecSpec.mop | `d1cc088aee24205bffd3cb241427469f03d388e7aacdeed753399a088eacb8ef` | SecretKeySpec.cryptsl | `ee7edaf9024c280ee1d6a037a8453540db8ab185630a956b830bfc4c8ead2538` |

All five `.mop` hashes are byte-identical to `fase0/manifest_hashes.md` (jca_android
table) — freeze check PASS. DHGen and HMAC are byte-identical to the frozen `jca` set
(known anomaly 2 of `fase0/manifesto.md`); the other three diverge from `jca`, as
expected for the repair-carrying set.

## Commands (reproducible)

For each spec `S` (working dir `$SCRATCH/batchA/gen_S/`, spec copied to `specs/`):

```bash
RH=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
/usr/bin/time -v $RH/javamop/bin/javamop -d out -merge --emit-descriptor specs/S.mop
mv specs/*.rvm out/          # JavaMOP -d leaves .rvm beside the source
/usr/bin/time -v $RH/rv-monitor/bin/rv-monitor -d out -merge out/*.rvm
```

Same pipeline as production (`runtime_verification_generator.py:211,267`), except
`.rvm` files are **kept** (production deletes them) so reviewers can audit the
intermediate. Toolchain: the frozen JavaMOP/RV-Monitor of `fase0/toolchain_ambiente.md`
(JavaMOP rebuilt 2026-08-08 with gh100/gh101 patches and `--emit-descriptor`).

## Results

All 10 executions: exit 0, empty stderr (beyond `/usr/bin/time -v` output), no
error/warning strings in stdout. Caveat kept in force: exit 0 does not guarantee
success — reviewers must still inspect artifacts (the pilot's GCM fail-open was
silent).

| Spec | javamop wall/RSS | rv-monitor wall/RSS |
|---|---|---|
| DHGenParameterSpecSpec | 0.40 s / 86.7 MB | 0.90 s / 82.5 MB |
| HMACParameterSpecSpec | 0.43 s / 85.7 MB | 0.86 s / 84.0 MB |
| PBEParameterSpecSpec | 0.42 s / 85.1 MB | 0.92 s / 85.1 MB |
| IvParameterSpec | 0.39 s / 86.7 MB | 0.92 s / 86.7 MB |
| SecretKeySpecSpec | 0.43 s / 85.2 MB | 0.94 s / 87.2 MB |

## Artifact hashes (sha256)

```
a92d1df8524594ac02b55c50164c423778d20f12d0dad8b64e23e80c919c7c5c  gen_DHGenParameterSpecSpec/out/DHGenParameterSpecSpecMonitorAspect.aj
146da773f5b3c532ef87f6193c8ac46f674026b96e99109aaa7eb085676c7ab6  gen_DHGenParameterSpecSpec/out/DHGenParameterSpecSpecMonitorAspect.json
90aaf45bbc1f8675120d23f764c60ac91f8d8130168d5861b312169c82f61051  gen_DHGenParameterSpecSpec/out/DHGenParameterSpecSpecRuntimeMonitor.java
dd21179dd3cc0ff0fc25367632a0ca96b92c433c28ad2232048657c6d7baad5e  gen_DHGenParameterSpecSpec/out/DHGenParameterSpecSpec.rvm
98350cde8a946148381ba1fa434fc8341e801bb4a4d9edde608fc35016fc21fa  gen_HMACParameterSpecSpec/out/HMACParameterSpecSpecMonitorAspect.aj
021e991ac26948ddba239f66afa999268cca37bcf25e66150600178fd4f1fcad  gen_HMACParameterSpecSpec/out/HMACParameterSpecSpecMonitorAspect.json
adebef513ac4a68b99365afc00c73a56b6d6dde679f93c3013ccc4f5d151b99f  gen_HMACParameterSpecSpec/out/HMACParameterSpecSpecRuntimeMonitor.java
5b32098c3b29fde9659cd455bd108b2a5c621067c03bf22a279bceff6fd554dd  gen_HMACParameterSpecSpec/out/HMACParameterSpecSpec.rvm
bf68bc7a02180cac7867f1a20ad075ef0149179513d6e5149758c8fa690e2e58  gen_IvParameterSpec/out/IvParameterSpecMonitorAspect.aj
5816b1d91ac0746279384c2f918cc37fe9cb1364b325fb3f23938a1b865212db  gen_IvParameterSpec/out/IvParameterSpecMonitorAspect.json
0fb95150c82ae1022e0210de4943feb72749b59d9de6f88680b51fad4e123fec  gen_IvParameterSpec/out/IvParameterSpecRuntimeMonitor.java
b25aec0fb3d356572556130cb349b125cf6ae7bfcb84b50c99f03d579995b348  gen_IvParameterSpec/out/IvParameterSpec.rvm
2f0928813a26218ba21b9278fa18bf3baf3aed67df579ae5b2f692bb0745a3aa  gen_PBEParameterSpecSpec/out/PBEParameterSpecSpecMonitorAspect.aj
0e3fb11d212d852dcb04435ce56aed5d568419c081453feaee33eaf9524a8a18  gen_PBEParameterSpecSpec/out/PBEParameterSpecSpecMonitorAspect.json
42bf007bdb4b87ba0533842449fee8549919357dfeaeb342e3a9f4f7764df66d  gen_PBEParameterSpecSpec/out/PBEParameterSpecSpecRuntimeMonitor.java
90685cbfc0e8a6f0efdbedf70709824193603322ad44da46709b6e402ebdd7eb  gen_PBEParameterSpecSpec/out/PBEParameterSpecSpec.rvm
633040e8fa55f370754aac3e0a2ceefcac2c46319fffca45582d40b3960e6fe1  gen_SecretKeySpecSpec/out/SecretKeySpecSpecMonitorAspect.aj
71d52f0dbb1d2177a7f8513c1502155289f9ed9b971279ba6737e26c2e74efbe  gen_SecretKeySpecSpec/out/SecretKeySpecSpecMonitorAspect.json
2216bf9a90e3eb3eab35833358a23515c750b8891df378141d207a124818f6d7  gen_SecretKeySpecSpec/out/SecretKeySpecSpecRuntimeMonitor.java
b3e92e099900cc53db985ad9c1ccfea4678e19d176881a5989053b106c3f4aca  gen_SecretKeySpecSpec/out/SecretKeySpecSpec.rvm
```

Scratch location this session:
`/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/d2ed0fb6-e4be-4945-abb4-21d8af2acd28/scratchpad/batchA/gen_<Spec>/`.
Scratch is ephemeral; the commands + input hashes above are the durable reproduction
path (generation is deterministic — pilot §0.1 verified identical artifacts across
independent runs; per REF-11 this is generator determinism, not independent
replication).

## Scope notes fixed for the round (from fase0/desvios.md and the judge's decision)

- ORDER precedence: normative reading A — comma is the outermost (lowest-precedence)
  operator, `|` binds tighter (D-piloto-1, verified against upstream Xtext
  `fase0/upstream_CrySL_e92f5607.xtext:103-121`). MetaCrySL's grammar is recorded as
  divergent; do not re-litigate per spec.
- `RandomStringPassword.mop` is EXCLUDED from the round by researcher decision
  (2026-08-09) — no CrySL rule, hence no normative oracle (recorded in
  `fase0/manifesto.md`). The round audits 22 specs: 2 pilot + 20 in batches.
- Language verdicts are issued over the effective automaton from these artifacts
  (D-piloto-3); claim→dimension assignment happens at claim creation (D-piloto-4).

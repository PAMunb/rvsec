# Group 6 — E1: legible messages in `jca_v2`

Tracked checkboxes: `tasks.md` §6. Starts after Group 2's seed commit. Edits only `rvsec/rvsec-mop/src/main/resources/jca_v2/*.mop` and `jca_v2/codes.csv` (+ `data/jca_v2/divergence_record.csv` entries, `evidence/harness/e1-*.md`). Two subagents on disjoint halves: **6.a** = `CipherInputStreamSpec, CipherOutputStreamSpec, CipherSpec, DHGenParameterSpecSpec, GCMParameterSpecSpec, HMACParameterSpecSpec, IvParameterSpec, KeyGeneratorSpec, KeyManagerFactorySpec, KeyPairGeneratorSpec, KeyPairSpec, KeyStoreSpec`; **6.b** = `MacSpec, MessageDigestSpec, PBEKeySpecSpec, PBEParameterSpecSpec, RandomStringPassword, SecretKeySpec, SecretKeySpecSpec, SecureRandomSpec, SignatureSpec, SSLContextSpec, TrustManagerFactorySpec`. Each half appends its own rows to `codes.csv` and to the divergence record (distinct files touched → no merge conflict).

## Subagent brief

Read `design.md` D-2, D-3, D-4 and the `instrumentation` delta requirements `Violation Report Message Envelope`, `Event-Name Bookkeeping in Specification Bodies` (INV-INS-119/120/121). Do not touch automata, pointcuts, `fsm`/`ere`, bindings or predicate reads — that is Group 7. Do not touch `jca/` or `jca_android/`. Every hunk gets a divergence-record entry (kind `message`, task `6.x`). Regenerate the monitor of your half's set in scratch at the end (`RVSEC_HOME`, `TMPDIR` off tmpfs) and run the harness seed-vs-now per file: the classification must be `unchanged` for accusation (only the envelope differs). Java inside `.mop` bodies is inlined verbatim into the monitor: keep it minimal (a field write, a string concatenation, one `addError`).

## Idiom (per file)

```
declarations: String lastEventName = "";  // beside the existing fields
event g3 ... { lastEventName = "g3"; ...existing body... }
@fail {
    ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "<Spec>", "" + __LOC,
        "v=1 code=<SPEC>-ORDER-00 ev=" + lastEventName + " obj=<SimpleClass> val='' exp='' msg='<sentence>'"));
    ...existing removes...; __RESET;
}
value site: addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "<Spec>", "" + __LOC,
        "v=1 code=<SPEC>-ALG-01 ev=" + lastEventName + " obj=<SimpleClass> val='" + q(alg) + "' exp='" + q(String.join(",", safeAlgorithms)) + "' msg='expecting one of " + String.join(",", safeAlgorithms) + " but found " + alg + "'"));
```
`q(s)`: null → `""`, `'` → `\'`, cap 512 chars — a private helper in `declarations` (private methods in `declarations` are emitted verbatim; verified on `KeyPairGeneratorSpec`). No `static` declarations. `msg` must not start with `expecting` (`ErrorDescription.toString :143` prefixes it).

## Per-file inventory (frozen `jca` = seed of `jca_v2`; line numbers of the seed)

| file | lines | events | 3-arg sites (→ 4th arg) | 4-arg value sites (→ envelope) | `@fail` `__RESET` | `but found` field→arg | census fixes (6.1) |
|---|---|---|---|---|---|---|---|
| CipherInputStreamSpec | 28 | 4 | `@fail :26` | – | yes | – | – |
| CipherOutputStreamSpec | 28 | 5 | `@fail :26` | – | yes | – | – |
| CipherSpec | 218 | 17 | `@fail :212` | i1 `:60-61` UA, i2 `:75-76` UA | yes | `:61,:76` field `currentTransformation` → arg `transformation` | drop literal `...`; `exp` = "see CipherTransformationUtil" or the utility's list |
| DHGenParameterSpecSpec | 39 | 1 | `@fail :31` | – | yes | – | – |
| GCMParameterSpecSpec | 59 | 2 | `@fail :51` | – | yes | – | (dup `c1` — Group 7; allowlist G-6′ meanwhile) |
| HMACParameterSpecSpec | 37 | 1 | `@fail :29` | – | yes | – | – |
| IvParameterSpec | 69 | 4 | c3 `:48` UC, c4 `:55` UC, `@fail :61` | – | yes | – | – |
| KeyGeneratorSpec | 82 | 5 | `@fail :73` | gk1 `:63-64` UA | yes | `:64` field `currentAlgorithmInstance` → arg | `:64` missing space |
| KeyManagerFactorySpec | 98 | 5 | `@fail :89` | init `:54-55` UA | yes | `:55` field → arg | `:55` leading space |
| KeyPairGeneratorSpec | 118 | 9 | `@fail :111` | init1 `:71-72` UA, initError `:97-98` IKS | **no → add `__RESET`** | `:72` field `algorithm` → arg | `:72` leading space; `:71-72` unreachable (record; Group 7) |
| KeyPairSpec | 52 | 3 | `@fail :44` | – | yes | – | – |
| KeyStoreSpec | 87 | 7 | `@fail :77` | gk1 `:67-68` IKST | yes | `:68` field `currentKSType` → arg | `:68` missing space |
| MacSpec | 94 | 8 | `@fail :86` | i1 `:49-50` UA, i2 `:61-62` UA | yes | `:50,:62` field → arg | `:50` leading space; `:62` missing verb |
| MessageDigestSpec | 119 | 9 | `@fail :111` | update `:69-70` UA, d2 `:91-92` UA (+ commented g4 `:57-58` — un-comment, argument form) | yes | `:70,:92` field → arg | list `{SHA-256,SHA-384,SHA-512}` → allow-list `:16` (six entries) |
| PBEKeySpecSpec | 86 | 7 | f1 `:24` ISMC, f2 `:30` ISMC, `@fail :78-79` | err1 `:49-50` UC, err2 `:57-58` UC, err3 `:65-66` UC | yes | – | `:50` `1000`→`10000`; f1/f2 `ErrorType` → UC (forbidden constructor) |
| PBEParameterSpecSpec | 63 | 3 | `@fail :56` | c3 `:49-50` UA | yes | – | `:50` `1000`→`10000`; `:49` UA → UC |
| RandomStringPassword | 29 | 2 | – (no `@fail`) | – | n/a | – | – |
| SecretKeySpec | 34 | 1 | – (no `@fail`; null detector — Group 7) | – | n/a | – | – |
| SecretKeySpecSpec | 70 | 4 | `@fail :62` | c3 `:48-49` UC, c4 `:55-56` UC | yes | – | `:49` "length is not randomized" → array; leading spaces `:49,:56`; split algorithm half as UA (`:48,:55`) |
| SecureRandomSpec | 174 | 15 | `@fail :167` | g4 `:81-82` UA (already argument `alg`), setSeed3 `:100-101` UC | yes | – | `:82` joins with `" or "` — normalise to `","` |
| SignatureSpec | 138 | 12 | `@fail :130` | i1 `:57-58`, i2 `:67-68`, i3 `:77-78`, i4 `:87-88` UA | yes | `:58,:68,:78,:88` field → arg | – |
| SSLContextSpec | 93 | 5 | `@fail :84` | init `:57-58` UP | yes | `:58` field `currentProtocol` → arg | – |
| TrustManagerFactorySpec | 97 | 5 | `@fail :85` | init `:56-57` UA | yes | `:57` field → arg | – |

Totals: 25 three-argument sites (21 `@fail` + 4), 26 four-argument sites (1 commented), 134 event bodies, 17 active `but found` sites (16 field + 1 argument). `ErrorType` values (`rvsec-core/.../eh/ErrorType.java`): `UnsafeAlgorithm`, `InvalidSequenceOfMethodCalls`, `UnsatisfiedConstraint`, `InvalidKeySize`, `InvalidKeyStoreType`, `UnsafeProtocol`. KIND per code (design D-3): `ORDER`, `ALG`, `CONSTR`, `KEYSIZE`, `KSTYPE`, `PROTO` (`REQ`/`FORB` come with Group 8).

## Commands

```bash
python3 scripts/gh104_mop_lint.py ../rvsec/rvsec/rvsec-mop/src/main/resources/jca_v2       # 0 three-arg, 0 missing bookkeeping (dup c1 + parens remain until Group 7 → allowlisted)
python3 scripts/gh104_message_gate.py ../rvsec/rvsec/rvsec-mop/src/main/resources/jca_v2   # literals match; codes.csv bijective
python3 scripts/gh104_divergence_record.py --check
python3 scripts/gh104_diff_harness.py --a <seed snapshot (git show <seed-commit>:… into scratch)> --b ../rvsec/rvsec/rvsec-mop/src/main/resources/jca_v2 --traces traces --out evidence/harness/e1
```

## Acceptance

- Zero three-argument sites; zero field-interpolating `but found` sites; every body's first statement is its own name; `codes.csv` bijective with the 51 sites (+ any envelope-only sites); every hunk recorded.
- Harness seed-vs-E1: every trace `unchanged` in accusation; envelope now carries `ev=`.
- Monitor of `jca_v2` compiles (`MultiSpec_1RuntimeMonitor.java`) — record generation time.
- Two commits (one per half): `feat(jca_v2): mensagens legíveis com envelope v1 e escrituração do evento (arquivos A–K|M–T) (refs #104)`.

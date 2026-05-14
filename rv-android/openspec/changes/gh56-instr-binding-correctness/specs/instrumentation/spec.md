## ADDED Requirements

### Requirement: Named-Binding Contract for dexlib2 Advice Emission

The dexlib2 advice-emission pipeline (`PointcutMatcher.buildCallMatch` → `MonitorInvokeBuilder.resolveBindings` → `MonitorInvokeBuilder.registersFor`) SHALL resolve every pointcut binding to a real DEX register whose runtime type matches the corresponding parameter type of the monitor signature. The contract spans the five emitters (`Before`, `After`, `AfterReturning`, `AfterThrowing`, `StaticInitialization`) and the four binding kinds defined by JavaMOP pointcut expressions: `target(name)`, `args(n1, n2, …)`, `returning(name)`, and `throwing(name)`. An additional synthetic key `$return` is reserved for the destination register of the trailing `move-result*` instruction following a non-constructor invoke.

Bindings MUST be resolved by **name**, not by ordinal — the same parameter name appearing in `parameters[]`, `returning[]`, and `monitorCalls[i].args[]` MUST resolve to the same register at every site. Literal-zero fallbacks for unresolved bindings are forbidden, because `v0` is a meaningful local in arbitrary callers and conflating "unresolved" with `v0` produces type-mismatched `invoke-static` instructions that ART rejects with `java.lang.VerifyError`. When a binding cannot be resolved (e.g. an `args(name)` references a parameter the matcher could not locate), the emitter MUST skip the advice and record a `plansSkippedUnresolvedBinding` counter in `WeaveReport` rather than emit a malformed invoke.

The contract is enforced at unit-test level: every `(emitter, invoke-kind, binding-kind)` triple in the cross-product MUST have at least one parametrized test case in `MonitorInvokeBindingTest`, and the test MUST validate the **type of each register** against the monitor signature emitted, not only the instruction shape (opcode, register count, format selector).

The "type-per-register" assertion MUST source the expected type from a hand-written fixture table (`Map<Integer, String>` declared as a constant per scenario), NOT from any helper that re-parses the monitor signature with the same logic the builder uses. Without an independent type source, the assertion validates internal self-consistency — the original gh52 smoke missed the bug for exactly this reason.

#### Scenario: Constructor invoke with returning binding resolves to the freshly-constructed instance
- **WHEN** an advice with expression `call(public SecretKeySpec.new(byte[], String)) && args(keyMaterial, keyAlgorithm) && returning(secretKeySpec)` matches a site `invoke-direct {v4, v3, v0}, Ljavax/crypto/spec/SecretKeySpec;-><init>([BLjava/lang/String;)V`
- **THEN** the emitted invoke MUST be `invoke-static {v3, v0, v4}, ...->SecretKeySpecSpec_c1Event([BLjava/lang/String;Ljavax/crypto/spec/SecretKeySpec;)V`
- **AND** `Match.targetRegister` MUST equal `v4` (the `<this>` register populated by `new-instance`)
- **AND** `Match.argBindings.get("arg00")` MUST equal `v3` and `Match.argBindings.get("arg01")` MUST equal `v0`
- **AND** `resolveBindings` MUST resolve the binding name `secretKeySpec` to `v4`

#### Scenario: Non-constructor invoke with returning binding resolves to the move-result destination
- **WHEN** an advice with expression `call(public KeyGenerator.generateKey()) && target(generator) && returning(secretKey)` matches a site `invoke-virtual {v2}, ...KeyGenerator;->generateKey()Ljavax/crypto/SecretKey;` immediately followed by `move-result-object v5`
- **THEN** the resulting `Match.argBindings.get("$return")` MUST equal `5`
- **AND** `resolveBindings` MUST resolve the binding name `secretKey` to `v5`
- **AND** the emitted invoke MUST place `v5` at the position corresponding to `secretKey` in the monitor signature

#### Scenario: Static invoke without receiver leaves targetRegister unset
- **WHEN** an advice with expression `call(public static MessageDigest.getInstance(String)) && args(algorithm) && returning(digest)` matches a site `invoke-static {v3}, ...MessageDigest;->getInstance(Ljava/lang/String;)Ljava/security/MessageDigest;` followed by `move-result-object v6`
- **THEN** `Match.targetRegister` MUST equal `-1` (no receiver)
- **AND** `Match.argBindings.get("arg00")` MUST equal `v3`
- **AND** `Match.argBindings.get("$return")` MUST equal `6`
- **AND** the emitted invoke MUST place `v3` and `v6` at the positions matching the monitor signature

#### Scenario: Unresolved returning binding skips the advice and records a counter
- **WHEN** an advice with expression `call(public Cipher.init(int, Key)) && args(opmode, key) && returning(unused)` matches the bytecode site `invoke-virtual {v2, v3, v4}, ...Cipher;->init(ILjava/security/Key;)V` immediately followed by `return-void` (no `move-result*` because `Cipher.init` returns `void` — and even for return-bearing methods, the original code may discard the result)
- **THEN** the emitter MUST NOT emit a malformed `invoke-static` with `v0` substituted for `unused`
- **AND** `WeaveReport.plansSkippedUnresolvedBinding` MUST be incremented by 1
- **AND** the site MUST be logged at `WARN` level with the literal message format `"skipping advice {adviceName} at {className}.{methodName}@{insnIndex}: unresolved binding '{bindingName}' (kind=returning)"` so operators can grep by binding kind

#### Scenario: Unresolved args binding skips the advice and records a counter
- **WHEN** an advice with expression `call(public SSLContext.init(KeyManager[], TrustManager[], SecureRandom)) && args(km, tm, prng)` matches a site whose matched `regs[]` length is shorter than the advice's parameter list (e.g. obfuscator-rewritten descriptor), so `Match.argBindings` lacks an entry for `prng`
- **THEN** `MonitorInvokeBuilder.registersFor` MUST return `null` and the emitter MUST NOT emit a malformed `invoke-static` with `v0` substituted for `prng`
- **AND** `WeaveReport.plansSkippedUnresolvedBinding` MUST be incremented by 1
- **AND** the site MUST be logged at `WARN` level with the literal message format `"skipping advice {adviceName} at {className}.{methodName}@{insnIndex}: unresolved binding '{bindingName}' (kind=args)"`

#### Scenario: move-result-wide captures the low register of the wide pair
- **WHEN** an advice with expression `call(public static System.currentTimeMillis()) && returning(now)` matches a site `invoke-static {}, ...System;->currentTimeMillis()J` immediately followed by `move-result-wide v6` (which occupies the register pair `v6+v7` per the DEX wide-value convention)
- **THEN** `Match.argBindings.get("$return")` MUST equal `6` (the low register of the wide pair; the high register `v7` is implicit per DEX register-pair semantics)
- **AND** the emitted invoke MUST place `v6` at the position in the monitor signature corresponding to the primitive type `J` (long)
- **AND** the existing `RegisterShifter` (`INV-INS-26`) MUST preserve the `v6+v7` pair contiguity if any shift occurs downstream

#### Scenario: super.<init> chaining does not capture receiver under constructor semantics
- **WHEN** `buildCallMatch` is called for a `invoke-direct {v0, v1}, Ljava/lang/Object;-><init>()V` instruction inside a user-class constructor body, with a `CallPC` whose descriptor targets the user-class's own `<init>` (NOT `Object.<init>`, so `cp.isConstructor() == false` for this site)
- **THEN** `Match.isConstructor` MUST be `false`
- **AND** `Match.targetRegister` MUST equal `regs[0]` (`v0`, the `<this>` of the user constructor) via the virtual-instance fallback path, NOT via the constructor capture path
- **AND** the predicate disagreement (opcode is `invoke-direct` but descriptor predicate `cp.isConstructor()` is `false`) MUST NOT trigger the receiver-capture branch reserved for matched constructor advices

### Requirement: Constructor Invoke Offset in PointcutMatcher

`PointcutMatcher.buildCallMatch` SHALL distinguish constructor invokes (`invoke-direct <init>`) from truly static invokes when computing `baseOffset` and `targetRegister`. Constructor invokes place the freshly-allocated (uninitialised) instance in `regs[0]` and user-visible parameters start at `regs[1]` — the same shape as a virtual instance invoke. Truly static invokes lack a receiver and start user parameters at `regs[0]`. Conflating the two categories under a shared `treatAsZeroOffset` flag shifts every argument binding by one register and loses the receiver reference, which is the structural cause of bug #1 in `docs/20260514_erro.md`.

The semantic identification of "constructor" MUST come from `CallPC.isConstructor()` (the pointcut descriptor's classification) rather than from the opcode alone — the descriptor encodes user intent ("this advice targets `SecretKeySpec.new(...)`") while the opcode `invoke-direct` is also used for private and superclass-`<init>` calls that are not advice targets. For correctness, both predicates must agree before the receiver is captured.

- **INV-INS-70**: For every match where `match.isConstructor == true`, `Match.targetRegister` MUST equal `regs[0]` (the receiver / `<this>`), `baseOffset` MUST equal `1`, and `Match.argBindings.get("arg00")` MUST equal `regs[1]` (the first user-visible parameter). The boolean is set by `PointcutMatcher.buildCallMatch` only when both predicates agree: `CallPC.isConstructor() == true` AND the resolved `MethodReference.name` equals `"<init>"`.

#### Scenario: Constructor offset captures receiver
- **WHEN** `buildCallMatch` is called with `cp.isConstructor() == true` (the descriptor predicate; sets `match.isConstructor` to `true`), `isStaticInvoke == false`, `regs = [4, 3, 0]`, and a parameter list of length 2
- **THEN** `Match.targetRegister` MUST equal `4`
- **AND** `Match.argBindings.get("arg00")` MUST equal `3`
- **AND** `Match.argBindings.get("arg01")` MUST equal `0`

#### Scenario: Static offset omits receiver
- **WHEN** `buildCallMatch` is called with `cp.isConstructor() == false`, `isStaticInvoke == true`, `regs = [3, 0]`, and a parameter list of length 2
- **THEN** `Match.targetRegister` MUST equal `-1`
- **AND** `Match.argBindings.get("arg00")` MUST equal `3`
- **AND** `Match.argBindings.get("arg01")` MUST equal `0`

#### Scenario: Virtual instance offset behaves like constructor for arguments
- **WHEN** `buildCallMatch` is called with `cp.isConstructor() == false`, `isStaticInvoke == false`, `regs = [2, 5, 6]`, and a parameter list of length 2
- **THEN** `Match.targetRegister` MUST equal `2`
- **AND** `Match.argBindings.get("arg00")` MUST equal `5`
- **AND** `Match.argBindings.get("arg01")` MUST equal `6`

### Requirement: Returning-Register Resolution in MonitorInvokeBuilder

`MonitorInvokeBuilder.resolveBindings` SHALL resolve every `returning(name)` binding to a real DEX register through `resolveReturningRegister(match)`, which selects between (a) `match.targetRegister` when `match.isConstructor == true`, because the freshly-constructed instance is the semantic return value of `<init>`, and (b) `match.argBindings.get("$return")` for any other invoke kind, which carries the destination of the trailing `move-result*`. The new `Match.isConstructor` boolean (added by this change to the `Match` class) is the load-bearing predicate consumed here; it is set only when both the descriptor predicate (`CallPC.isConstructor() == true`) and the method-name predicate (`MethodReference.name.equals("<init>")`) agree at match time (D3 defence-in-depth).

The literal-zero fallback (`map.putIfAbsent(p.getName(), 0)`) MUST be removed entirely. If neither resolution path produces a register, the binding is unresolved and the emitter MUST follow the `plansSkippedUnresolvedBinding` policy defined in the Named-Binding Contract above.

- **INV-INS-71**: For every advice with a non-empty `returning[]` descriptor list, the binding name MUST map to a register `r` such that the runtime type of `r` at the emission point is assignment-compatible with the monitor parameter type. No literal-zero default is allowed.
- **INV-INS-72**: For every non-constructor invoke matched by `PointcutMatcher.buildCallMatch`, the instruction at position `i+1` MUST be inspected; if it is `MOVE_RESULT`, `MOVE_RESULT_OBJECT`, or `MOVE_RESULT_WIDE`, its destination register MUST be recorded in `Match.argBindings` under the synthetic key `$return`. The peek MUST be skipped for constructors (which have no `move-result*`).

#### Scenario: Constructor returning resolves to targetRegister
- **WHEN** `resolveBindings` is called with `match.isConstructor == true`, `match.targetRegister == 4`, and an advice whose `returning` descriptor declares parameter `secretKeySpec`
- **THEN** the returned map MUST contain `("secretKeySpec", 4)`

#### Scenario: Non-constructor returning resolves to $return synthetic key
- **WHEN** `resolveBindings` is called with `match.isConstructor == false`, `match.argBindings.get("$return") == 5`, and an advice whose `returning` descriptor declares parameter `digest`
- **THEN** the returned map MUST contain `("digest", 5)`

#### Scenario: Returning without resolvable register skips advice
- **WHEN** `resolveBindings` is called with `match.isConstructor == false`, `match.argBindings.get("$return") == null`, and an advice whose `returning` descriptor declares parameter `result`
- **THEN** the returned map MUST NOT contain a `("result", 0)` entry
- **AND** the calling emitter MUST observe a null/absent resolution and skip the advice
- **AND** `WeaveReport.plansSkippedUnresolvedBinding` MUST be incremented by 1

### Requirement: Cryptoapp Oracle Layer 3 Mandatory Gate

The validator harness `scripts/run_phase5_validators.sh` SHALL treat the `cryptoapp-oracle.yaml` Layer 3 oracle as a **mandatory** gate **only when the validated run includes `cryptoapp.apk` in the dex result set** (detected by `find "$DEX_DIR/instrumented_apks" -name 'cryptoapp*.apk'`). For runs that exclude cryptoapp, Layer 3 remains diagnostic and the orchestrator exits zero on deviation. For runs that include cryptoapp, the orchestrator MUST append `--mandatory` to its `layer3` invocation, producing a non-zero exit when the captured trace deviates from the eight expected events.

The `layer3` subcommand of `ValidationCli` (picocli, see `validator/src/main/java/.../ValidationCli.java` `@Command(name = "layer3", …)`) SHALL accept a new boolean option `--mandatory` (default `false`). When `--mandatory` is set and the subcommand detects any deviation from the loaded oracle for any APK validated by this invocation, the subcommand MUST construct `Report(passed=false)`, which the existing `Report.exitCode()` (`validator/Report.java:44-46`) maps to exit status `1`. When the option is absent, behaviour is unchanged (Layer 3 remains diagnostic, `Report(passed=true)`, exit `0` even on deviation). The flag is honoured in both `analyze` and `--batch` modes. No new exit code is introduced — `Report.exitCode()` retains its `0`/`1` contract.

The eight expected events in `cryptoapp-oracle.yaml` are keyed by `(spec, error_type, class, method)` tuples: two `MessageDigestSpec/UnsafeAlgorithm` events in `MessageDigestUtil.hash`, one `CipherSpec/InvalidSequenceOfMethodCalls` and one `CipherSpec/UnsafeAlgorithm` in `CipherUtil.des`, one `KeyGeneratorSpec/UnsafeAlgorithm` in `CipherUtil.des`, one `KeyPairGeneratorSpec/InvalidKeySize` and one `KeyPairSpec/InvalidSequenceOfMethodCalls` in `CryptographyActivity.generateKeyPair`, and one `SecretKeySpecSpec` event in `CipherUtil.aes`. The oracle YAML is invariant under this change; only the gating policy changes.

**Pivotal events** (exercise the constructor-advice path and are the events lost to `VerifyError` before this change):

- Event #7: `KeyPairSpec/InvalidSequenceOfMethodCalls` in `CryptographyActivity.generateKeyPair` (involves `KeyPair.<init>` indirectly via `KeyPairGenerator.generateKeyPair → move-result-object`).
- Event #8: `SecretKeySpecSpec` in `CipherUtil.aes` (involves `SecretKeySpec.<init>` directly — the canonical bug shape `invoke-direct {v4, v3, v0}` → `invoke-static {v3, v0, v4}`).

The remaining six events (#1, #2 = MessageDigest; #3, #4 = Cipher; #5 = KeyGenerator; #6 = KeyPairGenerator) are captured today via the `WrapperEmitter` path and do NOT exercise the bug. Treating the gate as a flat 8/8 mask, therefore, would let a wrapper regression (orthogonal to gh56) trigger a false binding-regression signal. Implementations of this gate SHOULD log the pass/fail status of the two pivotal events separately, so operators can distinguish a binding regression (pivotal events fail) from a wrapper regression (non-pivotal events fail).

`IvParameterSpec.<init>` is documented as affected by the original bug (`docs/20260514_erro.md:§2.4`) but is NOT one of the eight events emitted by `cryptoapp` under the JCA spec set. Coverage for `IvParameterSpec.<init>` is provided at the unit level by an explicit case in `DexWeaverConstructorAdviceTest` (see `tasks.md:3.4`) rather than at the oracle level.

- **INV-INS-73**: Whenever `cryptoapp.apk` appears in the dex result set of a validation run, the orchestrator MUST pass `--mandatory` to the `layer3` subcommand. Any event count deviation MUST produce `Report(passed=false)` and consequently exit status `1` from `ValidationCli`, propagated by `run_phase5_validators.sh` via its existing `run_layer` aggregator. When `cryptoapp.apk` is absent from the result set, `--mandatory` MUST NOT be passed.

#### Scenario: Cryptoapp oracle deviation fails the gate
- **WHEN** `run_phase5_validators.sh` runs against a dex result directory containing `cryptoapp.apk` whose trace contains only 3 of the 8 expected oracle events
- **THEN** the orchestrator MUST append `--mandatory` to the `layer3 --batch` invocation
- **AND** `ValidationCli` MUST construct `Report(passed=false)` and exit with status `1`
- **AND** the orchestrator MUST classify `layer3_batch` as `GATES_FAILED` and exit non-zero
- **AND** the report MUST list each missing event by spec name and a one-line diagnostic
- **AND** the report SHOULD distinguish whether pivotal events #7 / #8 are among the missing ones (signalling a binding-regression rather than a wrapper-regression)

#### Scenario: Cryptoapp oracle full match passes the gate
- **WHEN** `run_phase5_validators.sh` runs against a dex result directory whose `cryptoapp.apk` trace contains all 8 expected oracle events at the correct call sites (including the 2 pivotal events #7 `KeyPair.<init>` and #8 `SecretKeySpec.<init>`)
- **THEN** the orchestrator MUST append `--mandatory` to the `layer3 --batch` invocation (cryptoapp is in scope per INV-INS-73)
- **AND** `ValidationCli` MUST construct `Report(passed=true)` and exit with status `0`
- **AND** the orchestrator MUST classify `layer3_batch` as `GATES_PASSED` and exit with status `0`

#### Scenario: Non-cryptoapp APK with no oracle stays diagnostic
- **WHEN** `run_phase5_validators.sh` runs against a result directory containing only APKs without an authoritative oracle YAML
- **THEN** Layer 3 MUST run in diagnostic mode (warning-only)
- **AND** the orchestrator MUST exit with status `0` even when no oracle match is found

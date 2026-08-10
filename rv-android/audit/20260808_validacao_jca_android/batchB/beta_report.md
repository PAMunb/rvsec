# Agent Beta report — Batch B (CIS, COS, KPR, SKY, PBK)

Agent Beta (toolchain red team), 2026-08-09. Scope: CipherInputStreamSpec (CIS),
CipherOutputStreamSpec (COS), KeyPairSpec (KPR), SecretKeySpec targeting the interface
`javax.crypto.SecretKey` (SKY), PBEKeySpecSpec (PBK), per `batchB/generation_manifest.md`.
Rules fixed for the round respected: D-piloto-1 (ORDER reading A), D-piloto-3 (effective
automaton is the evidence source — `beta_effective_automata.md`), D-piloto-4 (dimension at
creation; SET claims separate; FEN-* ids; six states), D-batchA-1 (known), REF-B-01
(decisive evidence copied here and hashed), REF-B-09 (executable two-object/interleaving
drives delivered for all five). Sequential Thinking MCP not used (not required; §8 is the
published decomposition). Labels: PROVADO / MEDIDO / OBSERVADO_EM_ARTEFATO / INFERIDO /
NAO_VERIFICADO. Every material claim has an executable leg.

## 0. Inputs, freeze checks — MEDIDO

- 5 `.mop` + 5 `.cryptsl` sha256 match `fase0/manifest_hashes.md` and the batch B
  generation manifest exactly (this session).
- 20/20 round-input artifacts match the generation manifest hash-for-hash.
- Toolchain frozen: javamop jar `ab4e3765…`, rv-monitor jar `fab40319…`, android-30 jar
  `96ccfdc8…` (= `batchA/beta_hashes.txt:16`), instr-cli.jar `356e8b70…`, rvsec-core
  `7b4d72aa…`, rv-monitor-rt `0fa65fbc…`, rvsec-logger-csv `6787f411…`. Java Temurin 25.0.3.
- javap trap neutralized as in batch A: all member tables from class files **extracted**
  from the frozen android-30 jar (`beta_hashes.txt`).

## 1. Generability / budget (G2) — MEDIDO

Independent regeneration in my scratch (`batchB/beta/gen/g_<Spec>/`), frozen toolchain,
`/usr/bin/time -v`. **All 20 artifacts byte-identical to the round input** (generator
determinism; REF-11 wording: not independent replication). Reproduction note (MEDIDO,
live): `javamop -d out` writes the `.aj`/`.json` into `out/` but the `.rvm` BESIDE the
`.mop`; feeding rv-monitor the assumed `out/<spec>.rvm` path yields `[Error] Target
file ... doesn't exist!` on stderr **with exit 0 and no artifacts** (probe p5) — a
silent-no-op fail-open shape a pipeline gated on exit codes will not catch.

| Spec | events | javamop wall/RSS | rv-monitor wall/RSS | CoenableProbe (ERE, production plugins) |
|---|---|---|---|---|
| CIS | 4 | 0.40 s / 85.7 MB | 0.91 s / 86.1 MB | coenable[fail]=60 = 4×(2⁴−1) saturated; chars=704 |
| COS | 5 | 0.42 s / 86.7 MB | 0.94 s / 86.1 MB | 155 = 5×(2⁵−1) saturated; chars=1954 |
| KPR | 3 | 0.42 s / 85.1 MB | 0.94 s / 85.7 MB | fail 21 = 3×(2³−1) saturated; match 9; chars=361 |
| SKY | 2 | 0.42 s / 86.7 MB | 0.93 s / 85.1 MB | no fail category; match=3 (< 6 sat.); chars=51 |
| PBK | 7 | 0.43 s / 87.2 MB | 0.97 s / 91.2 MB | fail 889 = 7×(2⁷−1) saturated; match=0; chars=17145 |

All ≤ 17-event ceiling (max 7). Full 23-spec production `-merge` (scratch): javamop
0.70 s / 179.9 MB; rv-monitor 28.97 s / 1.71 GB — consistent with batch A. The five
`.rvm` from the merge are byte-identical to the per-spec ones; the five monitors inside
`MultiSpec_1RuntimeMonitor.java` carry identical tables and indexing shapes
(`:9446/:9448` global CIS/COS; `:9482` KPR tuple+set; `:9498/:9512` per-object PBK/SKY).

## 2. Artifact chain (G6 static half) — MEDIDO/OBSERVADO_EM_ARTEFATO

- **Descriptor ↔ aspect**: programmatic 1:1 comparison for all five — 18 advices, 21
  monitorCalls, matching in name, expression, position, call order and argument lists
  (PBK's 4-arg ctor advice carries the 4 monitorCalls c1,err1,err2,err3 in that order).
- **Advice kinds**: every advice is `after`; none `around`/`throwing`. Events declared
  with `returning` in the `.mop` (KPR c1/gpu/gpr, SKY e1, PBK f1/f2/c1/err*) become
  `after returning`; the rest (ALL CIS/COS events, SKY d, PBK c2) are **plain `after`
  (after-finally)** — see §5 for the ajc/dexlib2 semantic split this opens.
- **condition(...) prologue**: `return false` before `handleEvent` (SKY `:129-131`,
  PBK `:280-283`) — suppression without transition, pilot pattern.
- **Event body before transition**: ENSURES-style writes execute regardless of the
  automaton state — PROVEN live (SKY-d2: RANDOMIZED written in the dead state; KPR-a2:
  GENERATED_PUBLIC_KEY granted while the monitor fails). FEN-SET-escritas-sem-estado.
- **`__LOC`**: present in every handler/violating body as
  `ViolationRecorder.getLineOfCode()` (e.g. CIS `:172`, `:214`). Measured runtime trap:
  frames whose class starts with `mop.` are FILTERED (`ViolationRecorder.java:87-104`),
  so calls made from classes in package `mop` report a JDK frame and all same-spec errors
  dedupe to one row (bit my own first drive; production app classes are unaffected).
- **Stale category flags** (batch A FEN-SET-flags-obsoletas): the merged-advice pattern
  recurs in PBK (4 monitorCalls), but is BENIGN here by construction: no category state
  is reachable between sibling monitorCalls (post-c1 state 1 sets neither flag; @match
  sits on the separate c2 advice). Verified by table + drive (PBK-a: no double handler).
- **Naming / collision (explicit round check)**: spec `SecretKeySpec` (file
  SecretKeySpec.mop, target interface `javax.crypto.SecretKey`) vs batch A spec
  `SecretKeySpecSpec` — in the full 23-spec merge the generated families
  (`SecretKeySpecMonitor*` / `SecretKeySpecSpecMonitor*`, wrappers `SecretKeySpec_*` /
  `SecretKeySpecSpec_*`) coexist with the import `javax.crypto.spec.SecretKeySpec`
  (`MultiSpec_1RuntimeMonitor.java:38,2478,2525,7892,8027`), and
  `MultiSpec_1RuntimeMonitor.java` **compiles clean** against the production runtime
  (javac exit 0, 57 classes) — no artifact/class-name collision (PROVADO). errors.csv
  attribution uses the distinct literals `"SecretKeySpec"` / `"SecretKeySpecSpec"`.

## 3. Capture vs real android-30 + production dexlib2 pipeline (G5) — MEDIDO

Batch B is the first batch with instance-method events, and for those the production
dexlib2 path does NOT use the PointcutMatcher at emission time: every `after` advice is
realized by **wrapper substitution** (`WrapperEmitter.shouldWrap` = position=="after",
`WrapperEmitter.java:161-163`; `DexWeaver` rewrites matching call sites to
`mop.MonitorWrappers.*`, keyed by the exact (owner, name, params, return) of overloads
enumerated from android.jar, `DexWeaver.java:137-179`), while non-constructor inline
AFTER plans are **defensively skipped** (INV-INS-66, `DexWeaver.java:481-515`).
Constructor events remain inline (narrow allowed case, gh52 §5.13(a)).

New harness `beta_BetaWeaveProbeB.java` drives the FULL production pipeline exactly as
`BatchRunner.java:158-266` wires it (DescriptorReader → TypeResolver(descriptor imports)
→ AndroidClassIndex(frozen android-30) → WrapperEmitter.generate → DexWeaver(+wrappers)
→ expandWrapperReplacementsForApk → weave) over a synthetic DEX with 36 call-site
scenarios (owner variants, overloads, neighbors, an app-internal `SecretKey`
implementor). Outputs: `beta_weave_all.out` (per-spec), `beta_weave_multi.out` (merged
23-spec descriptor — identical behavior, no cross-spec interference at any site).

| Spec | Captured (production dexlib2) | NOT captured | Neighbors (0 hits) |
|---|---|---|---|
| CIS | ctor2 INLINE c1; read() WRAPPED; read([BII) WRAPPED; close WRAPPED | **read(byte[]) UNTOUCHED** (silently skipped: plansSkippedAliasing=1); upcast owners InputStream/FilterInputStream; protected ctor1 | skip, available, markSupported |
| COS | ctor2 INLINE c1; write(int), write([BII), flush, close WRAPPED | **write(byte[]) UNTOUCHED**; upcast OutputStream | — |
| KPR | ctor INLINE c1; getPublic, getPrivate WRAPPED — exact | — | — |
| SKY | **NOTHING — 0 wrappers, 0 matches applied, plansSkippedAliasing=2** | all 7 owner variants incl. `SecretKey` itself | — |
| PBK | 3 ctors INLINE (4-arg advice = 4 events); clearPassword WRAPPED — exact | — | getPassword, getSalt |

Three toolchain findings, all with the executable leg above plus the source mechanism:

1. **FEN-SET-firstcall-disjunct** — `WrapperEmitter.findFirstCall` walks the pointcut AST
   and keeps only the FIRST `call(...)` of a disjunction (`WrapperEmitter.java:507-524`,
   comment admits "the corpus uses one call(...) per advice in practice"). CIS r1 =
   `read() || read(byte[])` and COS w1 = `write(int) || write(byte[])` are two-disjunct
   events: the second disjunct gets no wrapper, its sites are matched by the
   PointcutMatcher pass and then **silently discarded** (only a counter increments).
   `read(buf)` / `write(buf)` — the dominant stream idioms — never fire on the
   production Android path. Silent FN, critical.
2. **FEN-SKY-zero-captura** — android-30 `javax.crypto.SecretKey` declares NO methods
   (getEncoded inherited from `java.security.Key`, destroy a `Destroyable` default —
   javap over extracted bytes); `AndroidClassIndex.methods()` is declared-only, so
   overload expansion is empty; `literalFallback` keeps only static targets
   (`WrapperEmitter.java:481-497`); inline-AFTER is skipped for non-ctors. Net effect,
   measured: **the whole SecretKeySpec is inert under the production dexlib2 pipeline**
   — both events unrealizable at every owner (interface, implementor, super-interface,
   app subtype). Zero-fire of an entire spec, critical.
3. **FEN-SET-tipo-estatico** — capture keys on the STATIC receiver type at the call site
   (exact owner for wrappers before subtype expansion; expansion covers only APK-internal
   subtypes, `DexWeaver.java:207-231`). Upcast sites (`InputStream.read()`,
   `OutputStream.write(...)`, `Key.getEncoded()`, `Destroyable.destroy()`) are invisible
   — measured 0 rewrites — while CrySL's lifecycle is over the dynamic object. This is
   AspectJ `call()` semantics faithfully mirrored, but nowhere registered as a
   monitoring-scope reduction; realizable FN (streams are routinely passed as
   InputStream/OutputStream).

The ajc half was not executable on this host (no ajc — `toolchain_ambiente.md` §7,
pendency held); its static reading (AspectJ call semantics over the same pointcuts):
r1's second disjunct IS matched, SKY events match `SecretKey`-typed receivers — i.e. the
two production halves disagree on capture for CIS/COS/SKY (OBSERVADO_EM_ARTEFATO +
INFERIDO from AspectJ semantics; named pendency G6/G10).

## 4. Executable drive of the generated monitors — PROVADO/MEDIDO

`beta_BetaDriveB.java` compiles the five batch-B monitors **unmodified** plus batch A's
`SecretKeySpecSpecRuntimeMonitor` (hash `2216bf9a…`) against the production runtime and
drives the static wrappers in exact advice order, feeding real JDK objects
(Cipher/CipherInputStream/KeyPairGenerator EC/KeyGenerator AES/SecretKeySpec/PBEKeySpec).
49 assertions, ALL PASS, **3 repetitions byte-identical** (`beta_betadriveB_run1.out`).
The drive class sits OUTSIDE package `mop` so error locations behave as in a real app
(§2 `__LOC` trap). Highlights (ids = output lines):

1. **CIS/COS global-monitor FP cascade (dimension 5, two-object)** — the 2nd CrySL-legal
   stream produces 3 spurious `InvalidSequenceOfMethodCalls` (ctor, first read/write,
   close: CIS-b/b2/b3, COS-b/b2/b3); every subsequent stream repeats the pattern
   (CIS-b4, COS-b4). Per-object CrySL lifecycle vs per-process artifact — the batch A
   HMC phenomenon (FEN-HMC-monitor-global) recurring on two specs, now on a class used
   many times per app. Legit accusations still work from a clean state (close-without-
   read/write: CIS-d, COS-d).
2. **KPR generator-route FP** — `KeyPairGenerator.generateKeyPair(); kp.getPublic()` (the
   canonical JCA route; CrySL `co?` makes the ctor optional) fires a spurious fail
   (KPR-a) while still granting GENERATED_PUBLIC_KEY (KPR-a2). Critical, realizable in
   effectively every keypair-using app.
3. **KPR set-wide c1 (dimension 5, two-object)** — c1 binds NO spec parameter, so a 2nd
   KeyPair construction fails EVERY live monitor: kp1's monitor was dragged from state 1
   (match) to 0 by kp2's c1 (KPR-c2), then kp2's own getPublic fails too (KPR-d). The
   simultaneous fails and the two distinct REQUIRES accusations (public/private) each
   collapse into ONE errors.csv row — `ErrorSummary` excludes `expecting` and identical
   (spec,error,location) dedupe (KPR-c3, KPR-e) — multiplicity and clause identity are
   lost (FEN-SET-dedupe-resumo).
4. **KPR @match marks null** — the generator materializes the unbound spec parameter as
   a local that shadows the same-named monitor variable (`:179` vs `:138`), so
   `setObjectAsInAcceptingState(null)` runs instead of marking the KeyPair (KPR-b2).
   Accepted silently by both generator phases. No reader of acceptingState exists in the
   23 specs (grep — searched all `.mop` for `isInAcceptingState`: none) — effect dead in
   the set, mechanism defect real (FEN-KPR-var-sombreada).
5. **SKY extra-oracle gate** — the rule has NO REQUIRES and ENSURES
   `preparedKeyMaterial[keyMaterial]` after ANY ge; the artifact conditions e1 on
   `validate(GENERATED_KEY, key)`: an oracle-legal key without the mark gets NO event,
   NO error and NO RANDOMIZED surrogate (SKY-b) → downstream readers of RANDOMIZED
   (SecretKeySpecSpec c1, PBK err2/err3) will accuse — realizable FP chain.
6. **SKY ORDER violations invisible** — ge-after-destroy and double-destroy reach the
   dead state with zero errors (no fail category exists; SKY-d/e); the event body still
   writes RANDOMIZED in the dead state (SKY-d2). NEGATES edge itself works and is
   per-object (SKY-c/f).
7. **Cross-spec same-object flow (explicit round check)** — one `SecretKeySpec` object
   through batch A SKS (ctor grants GENERATED_KEY) then batch B SKY (e1 validates it,
   d withdraws it): cooperative, zero spurious errors, no double-fire (SKY-g1..g3);
   at weave level the merged descriptor gives each site only its own spec's events
   (`beta_weave_multi.out`: sks_ctor2 → SecretKeySpecSpec_c1/c3 only).
8. **PBK extra-oracle password gate** — CrySL REQUIRES only `randomized[salt]` (its
   password constraint is `neverTypeOf(password, String)`); the artifact demands
   RANDOMIZED(password) (c1 cond + err2): a user-typed password with a proper random
   salt and iter=10000 — the canonical PBE use case — is accused
   (`UnsatisfiedConstraint`) and denied SPECCED_KEY (PBK-b). Realizable FP, critical.
   Not covered by any gh101 anchor (conformance_record.csv:16 records only the
   iteration/keylength reading; predicate_edges.csv:54 records only the salt edge).
9. **PBK sequencing conflation** — because conditions gate transitions, a 4-arg ctor
   with violated constraints leaves the monitor in state 0 and the later clearPassword
   @fails (PBK-c2), stacking a sequence error on top of the specific accusation; same
   for FORBIDDEN-ctor objects (PBK-d2), where the CrySL `FORBIDDEN ... => c1`
   substitution reading would accept `f1, cP` as ordered. Legit double-clear accusation
   works (PBK-e). err1's message says ">= 1000" for a >=10000 condition (`.mop:55`) —
   the batch A factor-10 message defect recurring.
10. **CIS/COS `len > off` CONSTRAINT omitted** — r2/w2 bind (arr,offset,len) and check
    nothing; `read(b,5,3)`/`write(b,5,3)` return normally on the JDK and violate the
    rule silently (CIS-e, COS-e).

## 5. Advice-kind split ajc × dexlib2 on exceptional returns — OBSERVADO/MEDIDO, pendency

CIS/COS events, SKY d and PBK c2 are plain `after` (after-finally) in the `.aj`; the
dexlib2 wrapper body is `result = recv.m(...); <monitor calls>; return result;` with no
try/finally (`WrapperEmitter.java:650-699`; emitted `beta_MonitorWrappers_multispec.java`)
— events fire only on NORMAL return. The divergence is realizable: `Destroyable.destroy()`
default implementation THROWS `DestroyFailedException` (MEDIDO, DestroyDemo — so an ajc
weave would remove GENERATED_KEY on a FAILED destroy, while dexlib2 would not fire d at
all); AEAD `CipherInputStream.read` throwing on tag failure is the same family for r1/r2.
ART execution remains a named pendency (G6/G10) — nothing here converted to PASS.

## 6. Fail-open probes — MEDIDO (`beta_probes_summary.txt`)

p1 stray `)` absorbed, `.rvm` byte-identical (CIS shape); p2 stray `(` → MOPException on
stderr, exit 0, NO artifacts (KPR shape); p3 undefined ERE symbol flows into the `.rvm`,
is dropped silently, AND the orphaned real event (COS w2) gets an **all-fail row**
`{4,4,4,4,4}` — a one-symbol typo converts a legal overload into a permanent FP source
(sharper consequence than batch A's "dropped symbol"); p5 rv-monitor on a missing input:
`[Error]` + exit 0 + nothing generated; p6 typo'd `epsilon` (SKY shape): tables unchanged
but the match category silently loses state 0 — acceptance changes (`ge*, d?` → `ge* d`)
with zero diagnostics; conversely it proves the frozen SKY artifact realizes `epsilon`
correctly.

## 7. gh101 record consistency — OBSERVADO_EM_ARTEFATO

`data/gh101/predicate_edges.csv` rows 2, 4, 35, 36, 37, 39 and 65 mark as
`missing`/`wrong-constant` edges that the FROZEN specs and artifacts realize and that
this report executed: CIS/COS validate GENERATED_CIPHER (drive CIS-f), KPR reads
GENERATED_PUBLIC/PRIVATE_KEY and writes GENERATED_KEY_PAIR (KPR-b/a2), KPR gpr writes
GENERATED_PRIVATE_KEY (artifact `:218`), SKY d removes GENERATED_KEY (SKY-c). Batch A's
BETA-SET-07 phenomenon (stale records) reproduced on batch B rows — the records are
claims, not evidence (pre-registration §1), and at least 7 rows are stale. Registered
omissions that ARE consistent: cipheredInputStream/cipheredOutputStream have no Property
constant and no reader (predicate_omissions.csv:19-20 — deliberate, D-S14);
GENERATED_KEY_PAIR and SPECCED_KEY write-no-read registered (rows 3 and 10).

## 8. Scientific log (decomposition, protocol §2)

Per spec, one loop: (Q) does the chain realize the spec on the real platform, and what
breaks it? (H) hypotheses from reading (global monitor, partial binding, first-disjunct
wrappers, interface member absence, epsilon handling, extra-oracle conditions);
(T) discriminating tests with an executable leg (hash-compare regeneration; full
production weave over synthetic call sites; monitor drive with real objects incl.
two-object interleavings; mutation probes; javap over extracted bytes); (E) evidence
filed with file:line and outputs; (R) claims in `beta_claims.csv`; (U) uncertainties:
ajc weave + ART execution (G6/G10), `__LOC` under DEX, container android-36 (REF-12),
Android libcore behavioral equality for the JDK-verified constructions (INFERIDO,
OpenJDK-derived). No unknown was converted to PASS.

## 9. Files

- `beta_effective_automata.md` — effective tables/scopes for the 5 specs (D-piloto-3).
- `beta_claims.csv` — 52 claims (24 PASS, 27 FAIL, 1 INCONCLUSIVE; 11 critical, 11 major,
  10 minor).
- `beta_hashes.txt` — sha256 of every input and decisive output.
- Harnesses/outputs: `beta_BetaWeaveProbeB.java`, `beta_weave_scenarios.tsv`,
  `beta_weave_all.out`, `beta_weave_multi.out`, `beta_BetaDriveB.java`,
  `beta_betadriveB_run1.out`, `beta_MonitorWrappers_multispec.java`,
  `beta_probes_summary.txt`.
- Scratch (ephemeral, not the replication package): `<scratchpad>/batchB/beta/` —
  regenerations, probes, merge, drive classes, weave runs.

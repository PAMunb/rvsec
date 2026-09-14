# G10 · M2 order

**Depends on:** G01, G02, G03 and G04. **Blocks:** G12.
**Parallel with:** G06–G09, G11.
**Size:** ~6 files in `rvsec-crysl-core`. **On the critical path** — start it the moment G03 closes.
**Watch the sizing rule**: if the normalization catalogue grows past 15 files, split into
`G10a comparison` and `G10b normalizations`.

## Reference
- `specs/conformance/spec.md` — "M2 Order Comparison over the Inverse Morphism", INV-CONF-10, -13
- `design.md` D-02, D-05
- `data/jca_android/order_alphabet_map.csv` (207 lines at `5fbe8173`), column `disposition`

> **Carimbo do corpus (24/08/2026).** Os alvos e as asserções deste arquivo estão fixados em
> `5fbe8173`, que é **ancestral** do HEAD, não o HEAD. O commit `5bc5c893` reescreveu as listas
> de valor (`Arrays.asList(...)`) de 13 das 24 specs do `jca_android`; as fórmulas `ere`/`fsm`
> ficaram byte a byte idênticas. A nota completa, com as regras de contagem, está em
> `G12-corpus-calibration.md` §"O corpus moveu durante a implementação" — **leia-a antes de
> carimbar qualquer número deste grupo.**

## D-20 · h⁻¹(L) is applied at the lift, not in M2 (researcher decision, 2026-08-24)

The artifacts contradicted each other and two groups implemented opposite readings without knowing:
**INV-CONF-03** and the design's API comment say `SpecModel.order` is *"over Signature, not Label"*,
while the design's **Data Flow §5** says *"M2 builds `h` … computes `h⁻¹(L_mop)`"*. G03 built
`LabelAutomaton` + `InverseMorphism.preimage` in `-core` for the typed route; G01, not knowing, built
a placeholder encoding in `-mop` (`Signature("<mop-label>", label, [], "<mop-label>")`).

**Decided: the preimage happens at lift time.** The MOP lift reads the `ere`/`fsm` into a
`LabelAutomaton`, builds `InverseMorphism.of(events, site)`, and stores
`SpecModel.order = morphism.preimage(labelAutomaton)` — a real signature automaton. *Chosen because*
`SpecModel` is the **canonical** model: if `order` means labels on one side and signatures on the
other, it is not canonical, and M2 would compare two automata with disjoint alphabets. M2 then
compares two real-signature automata directly. **The placeholder alphabet is deleted.**

*Consequences, both of which must be handled rather than discovered:*
- the morphism's refusals (`Unknown{OverlappingDispatch}`) now arise **at lift**, so the lift result
  carries them instead of M2 producing them;
- `mop.lower` (G11) cannot reconstruct the `ere` from the preimage, so the `LabelAutomaton` and the
  morphism are **retained on the `-mop` lift result** (not on `SpecModel`) for the lowerer and for
  reporting.

**D-02's own witness did not exist in code until this reconciliation, and that is worth recording.**
`InverseMorphism.of` grouped events by exact `Signature` equality, under which `use` — written
`call(public void Cipher.init(int, Key, AlgorithmParameterSpec, ..))` at `IvChainJunction.mop:131` —
and `useRandomSpec` — `call(public void Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom))`
at `:256` — **never claim the same call**. So the corpus witness the whole non-disjointness argument
rests on was unverifiable, and the claim already standing in `InverseMorphism`'s Javadoc was
unsubstantiated. The fix gives a matching rule to the trailing AspectJ `..`.

That rule is safe because the shapes it does **not** handle do not occur. Verified twice by different
routes: the implementing agent counted over the **952 expanded signatures** (97 carry `..`, all
trailing, none carries a `*` parameter); the orchestrator counted over the **raw `call(...)` text of
all 215 files** (`grep`, duplicates included) and got **100** occurrences of `..`, **0** of them
non-trailing, and **0** patterns with a bare `*` as a parameter type. The two totals differ because
the counting rules differ — expanded signatures versus raw textual occurrences — and they agree on
the load-bearing property: **every `..` is trailing and no `*` appears as a parameter type**, so
giving a rule only to the trailing ellipsis leaves no untested shape.

Measured effect on the whole corpus: multi-label letters 55 → 61, refusals 52 → **56**, files with
refusals 41 → **42** of 215.

**Consumer caveat G10 must honour:** a refused signature is not a letter of `SpecModel.order`, so a
consumer reading `order` **without** `MopLift.morphism().refusals()` is reading a language narrower
than the file. That narrowing belongs to the refusal, not to the specification.

**Artifact debt:** `design.md` Data Flow §5 still describes the M2 reading. It must be amended via
`/opsx:update` — it is a schema artifact and may not be hand-edited (G14 14.7-bis).

## Tasks

- [x] 10.1 `metric/M2Order.java` — compare `h⁻¹(L_mop)` against `L(A_crysl)` by product search in both directions, emitting equivalent / MOP more permissive / MOP more restrictive / incomparable.
- [x] 10.2-bis **Close G03 3.10, which is deferred here by construction.** `-core` may not depend on
  either parser, so the census of how many of the 47 upstream rule automata are already deterministic
  cannot run inside G03. G03 built the capability and left the checkbox open rather than assert an
  unmeasured value: call `Determinizer.census(Collection<Automaton>)` over the automata the CrySL
  lifter produces, put `alreadyDeterministic/total` into `M2Result.ruleAutomatonWasDeterministic` and
  into the report with `Determinizer.COUNTING_RULE` printed beside it, then tick 3.10 in
  `G03-core-automata.md`. **It is a new measurement**: do not carry over the historical `30 of 30`,
  which was taken over the abandoned `api30` corpus and is method history, not a target.

- [x] 10.2 Determinize the rule automaton before comparing. A no-op wherever the rule is already deterministic (G03 3.10 measures how many of the 47 upstream automata are) and it **still runs** — a future `ORDER con, a?, a` is genuinely non-deterministic and would otherwise be compared wrongly and silently.
- [x] 10.3 `compare/AlphabetMap.java` — read `order_alphabet_map.csv` and expose the `disposition` column. **M2 takes every ε-erasure decision from it** (INV-CONF-10). Delete any code path that infers erasure from automaton shape; the shape criterion is provably insufficient (it does not license erasing `KeyGeneratorSpec.g3`, which loops only at the initial state — what licenses that is N1, valid there by the decidable `MapOfMonitor` criterion).
- [x] 10.4 An unmapped event with no `disposition` row emits `Unknown` rather than a choice. An erasure the comparator invents is a decision nobody reviewed; an erasure the map declares has an owner, a written reason and provenance, and M2's job is to check it.
- [x] 10.5 Quote the declared reason verbatim in the emitted verdict, so the erasure travels with its justification instead of pointing at a CSV the reader has to open.
- [x] 10.6 Label **every** verdict `M2-decl` and attach the statement that a declared-automaton verdict says nothing about what the generated monitor accuses (INV-CONF-13). No unqualified "equivalent" is emitted anywhere.
- [x] 10.7 Print the set of normalizations applied beside each verdict. A specification that only passes under N3 + N4 is saying something, and hiding which normalizations were used makes two incomparable verdicts look alike.
- [x] 10.8 Implement the normalization catalogue as named, individually reportable rules: 1:N over aggregates; 1:1 with cross-renumbering; ε-erasure of the negated twin (now *declared*, per 10.3); **N1** parametric slicing (at most one creator event per monitor); **N2** projection of a non-observable symbol (`next(int)` is `protected`); **N3** acceptance ≠ every `alias match*`; **N4** overlapping pointcuts (now a construction step, per D-02, not a post-hoc normalization).
- [x] 10.9 N1 is **not** a general rule — it is a property of the generated indexing tree, valid per specification by the `MapOfMonitor` criterion. Where it does not hold, M2 must not apply it. Feed this from M0.1 rather than re-deriving it.
- [x] 10.10 **Recompute the `KeyGeneratorSpec` verdict** (`design.md`, Open Question 1). Its `ere` changed from `(g3* g1+ | g3* g2+) ((init gk1) | gk1)` to `(g3* g1+ | g3* g2+) (((init | initRandom | initRandomSize | initRandomSpec) gk1) | gk1)`, and the published verdict was computed over the first. The alphabet map already maps the four `init*` to the rule's `i1`…`i5`. Report the new verdict and state plainly whether it differs from the published one.
- [x] 10.11 Re-emit the three verdicts whose automata are byte-identical to the earlier measurement (`MessageDigestSpec`, `SignatureSpec`, `SecureRandomSpec`) with the `M2-decl` label, the normalizations and the witness status. They are **results** rather than re-derivations, and saying so is worth a line.
- [x] 10.12 Every witness carries `ABSTRACT` or `CONCRETE` and cannot be published with a false-positive claim beside it if `ABSTRACT` (INV-CONF-08). None of the current witnesses was executed; all are `ABSTRACT`.
- [x] 10.12-bis **Publish through `MarkdownEmitter.VerdictEntry`, which enforces INV-CONF-08 for
  you.** G04 made the emitter *refuse to render* a `Claim.FALSE_POSITIVE`/`FALSE_NEGATIVE` paired
  with an `ABSTRACT` witness, or with no witness at all. Since every current M2 witness is
  `ABSTRACT` (none was executed), every M2 claim must be `Claim.NONE`. Do not work around the
  refusal — it is the invariant, not an obstacle.

- [x] 10.13 `M2OrderTest` — the `SecureRandomSpec` verdict reads `M2-decl: MOP more permissive, under N1 + N2` with an `ABSTRACT` witness; the `CipherSpec` verdict is `INCOMPARÁVEIS` sustained **only** by the `regra \ MOP` direction (`g1 i2 i2 f2`), the other direction having died when gh105 task 6.6 made `f1`/`f2` disjoint.
- [x] 10.14 Test 10.4: an unmapped event with no disposition row yields `Unknown`, not an erasure.
- [x] 10.15 Test the overlap path end to end on `jca_android/IvChainJunction.mop`: `h` maps `Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom)` to `use useRandomSpec` in declaration order, and a non-statically-decidable guard yields `Unknown{OverlappingDispatch, labels: [...]}`.
- [x] 10.16 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-core test` green.

## Measured (2026-08-24)

Stamps: `rvsec` at **`6192b57a`** (the `.mop` corpus and this component), `rvsec-cognicrypt` at
**`f2f4d3b`** (the oracle, 47 of 49 rules load), `android.jar` at **API 30**. The alphabet map is the
committed `data/jca_android/order_alphabet_map.csv`, read verbatim and never written (INV-CONF-12).

**Population.** 24 files → 22 pairs by declared type → **21 M2 verdicts**: M0 refuses `SecretKeySpec`
(non-empty `@match`, no `@fail`, no `addError`), and INV-CONF-09 says a refused specification
receives none.

**Determinization census (10.2-bis).** **47 of 47** upstream rule automata are already deterministic,
under `Determinizer.COUNTING_RULE` (R-DET); **22 of 22** over the paired subset. A new measurement,
not the historical `30 of 30` of the abandoned `api30` corpus. G03 3.10 ticked.

**Verdicts (21).** EQUIVALENT 12 · MOP more permissive 2 (`CipherOutputStreamSpec`, `SSLContextSpec`)
· MOP more restrictive 5 (`KeyGeneratorSpec`, `KeyPairGeneratorSpec`, `KeyStoreSpec`,
`MessageDigestSpec`, `SecureRandomSpec`) · INCOMPARABLE 2 (`CipherSpec`, `MacSpec`). Every witness is
`ABSTRACT`, every claim is `Claim.NONE`, every verdict is labelled `M2-decl`.

**The dominant effect is the refusal, and it is disclosed.** **7 of the 21** verdicts are
*refusal-borne*: their distinguishing word contains a call the lift refused as
`Unknown{OverlappingDispatch}` because an accepted event and its negated twin claim it under
complementary `condition`s. Nine of the 24 files use that idiom and it produces 11 refusals over the
set. Removing those letters from the rule as well (`M2Order.withoutRefusedLetters`), **3 of the 7
become EQUIVALENT** — `KeyGeneratorSpec`, `KeyPairGeneratorSpec`, `MessageDigestSpec`. A consequence
worth recording: for those nine files the *declared* ε-erasure of the negated twin is unreachable,
because the shared letter left the language at lift before M2 could erase it.

**10.10 · `KeyGeneratorSpec`.** `M2-decl: MOP more restrictive, under N-REN + N1`, refusal-borne;
`EQUIVALENT` once the refused `getInstance(String)` is taken out of the rule too. **It differs from
the published `EQUIVALENTES, sob N1`** — and the `ere` is not what moved it. The four `init*` the
formula gained all map to the rule's `i1`…`i5` and are absorbed by the letter identification; no
witness of either direction contains an `init`. What moved it is the pair (oracle switch, D-20).

**10.11 · the three byte-identical automata.** Results, not re-derivations. `SignatureSpec`
**EQUIVALENT** under N-AGG + N-REN + N1 — reproduces the published verdict, and it is the one of the
three with no negated twin over a shared call. `MessageDigestSpec` **MOP more restrictive**,
refusal-borne, EQUIVALENT projected — published EQUIVALENT. `SecureRandomSpec` **MOP more
restrictive** — published *MOP more permissive under N1 + N2*.

**10.13.** `SecureRandomSpec` does not reproduce, for a measured reason: **N2 is vacuous against the
upstream oracle** (no rule of the 22 orders a symbol a program cannot emit; the `protected next(int)`
N2 was written for is an `api30` artifact — `Observability` reads the access flags of `android.jar`
and confirms `next(int)` non-public and `nextInt()` public), and the map's `order-unmapped` rows for
`next1`/`next3`, written because `api30` named no `nextInt`, now erase calls the upstream rule *does*
order (`nI: nextInt()`). The residual witness after projection is exactly
`SecureRandom(); nextInt()`. `CipherSpec` is **INCOMPARABLE with both directions alive**, not only
`rule \ MOP`: the `f1`/`f2` direction did die in gh105, and another mop-only word took its place —
`getInstance · init · doFinal · wrap`, the D-10 case (`wrap` after `ENCRYPT_MODE` throws before any
monitor sees it), which is why it stays `ABSTRACT` and carries no claim. The published `g1 i2 i2 f2`
**does** reproduce, letter for letter, as the `rule \ MOP` witness once the refused
`getInstance(String)` leaves the rule as well.

**10.15 · the overlap path.** Satisfiable from the lift, as D-20 says: `h` maps
`Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom)` to `use useRandomSpec` in declaration
order, with **no** refusal (neither event carries a `condition`). It is the **only** call in
`jca_android` that emits two letters. The guarded half of the scenario is the negated twin —
`KeyGeneratorSpec` refuses `getInstance` with `labels: [g1, g3]` (INV-CONF-07).

**N4 is not applied to `CipherSpec`,** which corrects the published reading: at HEAD its
`doFinal(..)`/`doFinal()` overlap is separated by complementary conditions, so the lift refuses it
rather than concatenating.

**N1 changes the verdict of two specifications, not one** (`KeyGeneratorSpec` and `SecureRandomSpec`,
both INCOMPARABLE → MOP more restrictive). **N3 changes no verdict**: `CipherSpec` is INCOMPARABLE
with and without it.

**Letter identification (a design decision, stated).** `R-M2-alphabet` widens at the rule's unbound
argument where `R-M1` refuses to, and only there. M1 asks how much of the rule the specification
covers and must not let the oracle widen to fit the artifact; M2 asks whether two languages accept
the same words, and the rule's `_` really does accept whatever the call carried. Measured: without
the widening, `SSLContextSpec`, `SignatureSpec` and `MessageDigestSpec` each came out INCOMPARABLE
over a `getInstance` overload the rule leaves open. The caveat is printed in every M2 report
(`CanonicalAlphabet.HOLE_CAVEAT`).

**Refusal taxonomy note.** An event with no `disposition` row is emitted as
`Unknown{UnresolvedSignature}` with `mode` starting `ORDER-SEM-DISPOSICAO`, because INV-CONF-06 closes
the taxonomy at six tags and none was written for this case. The mismatch is stated in
`M2Order.UNDECLARED_EVENT_MODE`'s Javadoc rather than hidden. Over the 21 paired specifications the
count is **0** — the map is complete, which is what task 10.14's corpus test checks.

**Suite.** `mvn -o -f rvsec/rvsec-crysl/pom.xml test` → BUILD SUCCESS. `-core` **154**, `-mop`
**58**, `-crysl` **92**, 0 failures. G10 adds 8 (`M2OrderTest`) + 6 (`AlphabetMapTest`) in `-core`
and 10 (`M2OrderCorpusTest`, `@Tag("oracle-dependent")`) in `-crysl`.

## Closing
G10 closes when 10.1–10.16 are `[x]`, **including 10.2-bis and 10.12-bis** — the two tasks other
groups handed here. Conferir o intervalo ao fechar (aprendizado nº 18: o G05 dizia "5.1–5.9" com 11
tarefas e deixou as de CI fora do fecho).

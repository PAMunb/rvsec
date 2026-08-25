# G06 · M0 vitality

**Depends on:** G01 only — it does **not** wait for G02. M0 reads the `.mop` and the `android.jar`
index; it needs no rule.
**Blocks:** G12. **Parallel with:** G07–G11.
**Size:** ~4 files in `rvsec-crysl-core`.

M0 is the metric this change added, and it exists because Phase 0 measured that the other four would
otherwise emit confident verdicts about artifacts that cannot accuse anything.

## Reference
- `specs/conformance/spec.md` — "M0 Monitor Vitality, and Typed Refusal", INV-CONF-09
- `design.md` D-03 (M0 first and refusing), D-04 (three causes of silence)
- The behavioural evidence: `docs/20260824_medicoes_pre_change_conformidade.md` §2

> **Carimbo do corpus (24/08/2026).** Os alvos e as asserções deste arquivo estão fixados em
> `5fbe8173`, que é **ancestral** do HEAD, não o HEAD. O commit `5bc5c893` reescreveu as listas
> de valor (`Arrays.asList(...)`) de 13 das 24 specs do `jca_android`; as fórmulas `ere`/`fsm`
> ficaram byte a byte idênticas. A nota completa, com as regras de contagem, está em
> `G12-corpus-calibration.md` §"O corpus moveu durante a implementação" — **leia-a antes de
> carimbar qualquer número deste grupo.**

## Tasks

- [x] 6.1 `metric/M0Vitality.java` — the three questions. **M0.1 does it index?** The AST proxy: a specification with `0/N` parameter binding, or declared with no parameter, compiles to one monitor for the whole program. **M0.2 is the accusation site reachable?** Is there a `@fail`? Is there an `addError` reachable in an event body? Is the event in the `ere`? **M0.3 does the pointcut resolve?** Each signature against `ApiIndex`.
- [x] 6.2 State in the emitted M0.1 result that the AST answer is a **proxy** and the generated monitor is the real oracle. It gives the same five specifications today, and it is not the same measurement. Publishing it as if it were would be the exact error the capability exists to prevent.
- [x] 6.3 The non-normalized AST checker: identifiers unique; formula alphabet ⊆ declared identifiers; every declared event reachable in the formula; every `@match` paired with a `@fail`. This class of defect passes parser, monitor generator and Java compiler with zero errors, so nothing downstream can be relied on.
- [x] 6.4 `compare/Pipeline.java` short-circuits: a specification M0 refuses does not receive an M1, M2, M3 or M4 verdict (INV-CONF-09), and the typed `Unknown` becomes its whole result.
- [x] 6.5 **Separate the three causes of silence** (D-04) — this is the part the behavioural run bought, and collapsing them would report a limit of the formalism as a defect of a file:
      (a) **live monitor, blind to end of trace** — the `ere` accepts the observed word as a live prefix and JavaMOP has no end-of-trace event. Not a refusal: a `divergence_record` row, because it is a property of the formalism;
      (b) **live monitor, absent target** — the pointcut names a class the platform does not have. `Unknown{UnresolvedSignature}`;
      (c) **no accusation site** — empty `@match`, no `@fail`. **This one is the refusal.**
- [x] 6.6 `M0VitalityTest` over `jca_android` at `5fbe8173`: exactly five specifications do not index — `CipherInputStreamSpec`, `CipherOutputStreamSpec`, `HMACParameterSpecSpec`, `KeyStoreSpec`, `RandomStringPassword` — with the counting rule asserted as data.
- [x] 6.7 Test cause (c): `jca_android/RandomStringPassword.mop` (`ere : vo gb`, empty `@match`, no `@fail`) is refused, and M1–M4 emit nothing for it. Quote the file's own header in the emitted reason — it explains that an empty handler is the only way JavaMOP's grammar lets you state an automaton with nothing to report.
- [x] 6.8 Test cause (b): `jca_android/HMACParameterSpecSpec.mop` emits `Unknown{UnresolvedSignature, class: "javax.xml.crypto.dsig.spec.HMACParameterSpec", mode: CLASSE-AUSENTE}`, and the report says the monitor is **live** and the target absent — not that the monitor is dead.
- [x] 6.9 Test cause (a): `CipherInputStreamSpec` and `CipherOutputStreamSpec` are **not** refused. Their `ere` is `c1 (r1|r2)+ cl1`; the word `c1 r1` is a live prefix; the silence on the `-unclosed` traces is the `IncompleteOperationError` blind spot, and it belongs in `divergence_record.csv`, not in a refusal.
- [x] 6.10 Test the AST checker against `jca/GCMParameterSpecSpec.mop` (two events with identifier `c1`, `ere` referencing a non-existent `c2`) and against `jca/SecretKeySpecSpec.mop` (unbalanced parentheses that nonetheless parse). Both are caught; the emitted note records that both files parse, generate a monitor and compile with zero errors.
- [x] 6.11 M0 measures the "absorbs misuse" property as an AST fact (an `addError` in an event body, before the `ere`/`fsm` line), replacing the ad-hoc regex census. Assert the declared rule reproduces `18 of 24` for `jca_android` and `15 of 23` for `jca` at `5fbe8173`, and emit the rule beside the number.
- [x] 6.12 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-core test` green.

- [x] 6.13 **Refuse `SecretKeySpec.mop` too — researcher decision, 2026-08-24.** M0.2's criterion is
  its own title, *"is the accusation site reachable?"*, not the single instance spec.md gives it
  (*"an empty `@match` and no `@fail`"*). Measured in **both** corpora: `SecretKeySpec.mop` has a
  **non-empty** `@match`, **no** `@fail` and **no** `addError` anywhere — it cannot accuse under any
  trace. The five-that-do-not-index census never saw it because it **does** index. G11 task 11.5 was
  already written on the broad reading (*"`SecretKeySpec.mop` and `RandomStringPassword.mop` are
  exactly that today"*), so this makes the artifacts agree with each other.
  **Consequence to carry, not to hide:** `SecretKeySpec.mop` is one of the 22 pairs, so M1–M4 report
  on **21**. Re-measure every affected aggregate and record the 22→21 shift explicitly; the pairing
  target itself stays 22 (pairing and vitality are different questions).

  **The 22→21 shift, measured at this working tree** (not estimated; the M4 row was produced by
  running M4's own corpus loop twice, once with `SecretKeySpec.mop` excluded):

  | aggregate | before | after | why |
  |---|---|---|---|
  | pairing (INV-CONF-11) | 22 | **22, unchanged** | pairing asks whether a rule is the oracle of a specification; vitality asks whether the specification can accuse. Conflating them would corrupt calibration target 6. |
  | M1 verdicts over `jca_android` | 22 | **21** | the dropped verdict is `SecretKeySpec` vs `SecretKey.crysl`: `declared=2`, `covered=1`, `ruleOnly=1`, `mopOnly=0`. |
  | M3 clause aggregates (denominator 80/119, implemented 31, absent 36, refused 13, byIdiom 12/7/4/8, ceilings 34/3, the 86 and 99 variants) | — | **all unchanged** | `SecretKey.crysl` has no `CONSTRAINTS` section at all, so it contributes 0 clauses under R1. Verified by the text route: `CountingRule.countClauses(SecretKey.crysl) = 0`. |
  | M3 verdicts | 22 | **21** | the count of results moves even though no clause total does. |
  | M4 pairs over `jca_android` | 23 | **22** | M4's own simple-name approximation, which reaches 23 where the rule of record reaches 22 (`IvChainJunction` meets `Cipher.crysl` by simple name). |
  | M4 `present` | 50 | **49** | `SecretKeySpec` contributes one present edge. |
  | M4 `absent` | 53 | **52** | |
  | M4 `inverted` | 0 | **0** | |
  | M4 `rows` | 123 | **120** | its two predicate sites (`REQUIRES generatedKey`, `ENSURES preparedKeyMaterial`) plus one absence row. |
  | M4 `derivedRows` | 103 | **101** | |
  | M4 derived fraction | 0.837 | **0.842** | it rises, and it rises for a reason worth naming: the removed specification was carrying rows the metric could not derive, so the fraction improves by refusing rather than by comparing better. Anyone quoting it must quote the denominator beside it. |
  | predicate-site censuses (`0/70/21`, the 85/70 frozen-vs-current shapes, the 5 negated) | — | **all unchanged** | these are censuses of the corpus, not verdicts about it. M0's gate removes a specification from what M1–M4 *report on*; it does not remove a file from the corpus. |

  The M1/M3/M4 corpus tests continue to pin the **ungated** numbers, deliberately: they measure those
  metrics over the pairing, and the gate belongs to `compare/Pipeline`. The two readings are kept
  apart rather than merged, and the table above is the bridge between them. The same table is
  written into `M0VitalityTest.test_secret_key_spec_also_has_no_accusation_site`, so it lives beside
  the assertion and not only in this file.

- [x] 6.14 **Emit the refusal as a sixth `Unknown` tag — researcher decision, 2026-08-24.**
  INV-CONF-09 requires M0's refusal to be a typed `Unknown`, but none of the five tags names an
  unreachable accusation site (`UnresolvedSignature` asserts something else: a signature the platform
  lacks). Added `UnreachableAccusationSite{specification, evidence, site}` to the sealed hierarchy in
  `-core/model/`. `Silence` stays as the classification of the three causes and is still what
  `M0Result.refused()` consults; when a cause's disposition is `REFUSAL`, `M0Vitality` *also* puts an
  `Unknown{UnreachableAccusationSite}` into `M0Result.refusals()` — one countable refusal vocabulary,
  per D-11. The two registers are not redundant: the `Silence` decides whether M1–M4 run, the
  `Unknown` is what the report counts.

  `evidence` is mandatory and non-blank, carrying the same line the `Silence` carries (what `@fail`
  is, which `@match` keys are declared, and that no event body holds an `addError` the formula
  admits), so the refusal can be checked against the file rather than believed.

  `UnknownTaxonomyTest` now pins **six** and still pins it **exactly**, over
  `getPermittedSubclasses()` and over the exact set of simple names, plus the record-and-final check
  for all six — a seventh tag breaks the build exactly as the sixth did.

  **Not done here, and not mine to do:** `specs/conformance/spec.md` INV-CONF-06 still says "exactly
  five". It must be amended via `/opsx:update`; that amendment is **G14 14.7-bis**.

- [x] 6.15 **Fix `PointcutExpander`'s missing implicit `java.lang` import** (G06 finding 2).
  `PointcutExpander.resolve` now falls back to `java.lang` for a bare name that neither an `import`
  nor a declared parameter type covers, asked of the running JDK
  (`Class.forName("java.lang." + name, false, ClassLoader.getPlatformClassLoader())`, memoised)
  rather than of a hand-written list that would go stale silently. Primitives and wildcards fall out
  of that test on their own — there is no `java.lang.int` — so nothing needs a special case, and
  nothing beyond `java.lang` is invented (P1).

  **What changed in the published counts.** `RandomStringPassword.mop` writes
  `call(public static String String.valueOf(Object))` and imports no `java.lang`, so it lifted to
  `declaringType = "String"`, missed the `android.jar` index, and was published as
  `Unknown{UnresolvedSignature}`: a defect of this component wearing the costume of an absent Android
  class — the worst shape of error, because it inflates a published "unresolved" count with the
  instrument's own failure.

  | published count | before | after |
  |---|---|---|
  | `jca_android` unresolved declaring classes, **fully-qualified** bucket | 1 (`javax.xml.crypto.dsig.spec.HMACParameterSpec`) | **1, unchanged** — still the only genuine platform absence |
  | `jca_android` unresolved declaring classes, **bare-name** bucket | 1 (`String`, from `RandomStringPassword`) | **0** |
  | `jca_android` unresolved declaring classes, total | 2 | **1** |

  The bare-name bucket is kept in the test **and kept empty**, because it is what makes the defect
  visible if it ever returns. Two pins moved with the repair, both as visible reds first:
  `LiftApiShapeTest` (`Mac.getInstance(String)` → `getInstance(java.lang.String)`) and
  `M1EventsCorpusTest`'s MessageDigest `mopOnly` list. Neither M1 number moved with them —
  `declared` stayed 9 and `covered` stayed 8 — and that is the reassuring part: the CrySL side
  already spelled `java.lang.String`, so the repair made the two sides comparable without moving a
  coverage figure.

- [x] 6.16 **Carry `eventsBindingParameters` on `MopLift`.** `MopLift` gained the record component
  and its counting rule (`EVENT_BINDING_COUNTING_RULE`), computed by `MopLifter` from
  `EventDefinition.getMOPParametersOnSpec()` during the parse it already pays for, with a constructor
  check that it lies in `0..declaredEventCount`. `MopLift.monitorFacts(MisuseAbsorption)` is the
  production route that hands M0 its `MonitorFacts`; the caller supplies only the absorption, because
  that scan is textual by design (the `ere`/`fsm` line is a lexical boundary, not an AST node) and
  the model module owns it.

  `MopFacts` — the `-crysl` test-tree adapter that re-parsed each file to reach the binding count —
  is **deleted**, not deprecated (P3). Its corpus-path and version helpers, the only other thing it
  held, are inlined into `M0VitalityTest`, its single caller, matching what `M1EventsCorpusTest`
  already did. Backed up at `backup/20260824-gh106-g06-mopfacts/MopFacts.java` before deletion,
  because the `rvsec-crysl` tree is not yet tracked in git and a delete there is not recoverable.

## Closing
G06 closes when 6.1–6.16 are `[x]` — 6.13/6.14 are the researcher decisions of 24/08 and
6.15/6.16 are this group's own findings. Conferir o intervalo ao fechar (aprendizado nº 18).

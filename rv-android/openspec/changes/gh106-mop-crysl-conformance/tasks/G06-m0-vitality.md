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

## Tasks

- [ ] 6.1 `metric/M0Vitality.java` — the three questions. **M0.1 does it index?** The AST proxy: a specification with `0/N` parameter binding, or declared with no parameter, compiles to one monitor for the whole program. **M0.2 is the accusation site reachable?** Is there a `@fail`? Is there an `addError` reachable in an event body? Is the event in the `ere`? **M0.3 does the pointcut resolve?** Each signature against `ApiIndex`.
- [ ] 6.2 State in the emitted M0.1 result that the AST answer is a **proxy** and the generated monitor is the real oracle. It gives the same five specifications today, and it is not the same measurement. Publishing it as if it were would be the exact error the capability exists to prevent.
- [ ] 6.3 The non-normalized AST checker: identifiers unique; formula alphabet ⊆ declared identifiers; every declared event reachable in the formula; every `@match` paired with a `@fail`. This class of defect passes parser, monitor generator and Java compiler with zero errors, so nothing downstream can be relied on.
- [ ] 6.4 `compare/Pipeline.java` short-circuits: a specification M0 refuses does not receive an M1, M2, M3 or M4 verdict (INV-CONF-09), and the typed `Unknown` becomes its whole result.
- [ ] 6.5 **Separate the three causes of silence** (D-04) — this is the part the behavioural run bought, and collapsing them would report a limit of the formalism as a defect of a file:
      (a) **live monitor, blind to end of trace** — the `ere` accepts the observed word as a live prefix and JavaMOP has no end-of-trace event. Not a refusal: a `divergence_record` row, because it is a property of the formalism;
      (b) **live monitor, absent target** — the pointcut names a class the platform does not have. `Unknown{UnresolvedSignature}`;
      (c) **no accusation site** — empty `@match`, no `@fail`. **This one is the refusal.**
- [ ] 6.6 `M0VitalityTest` over `jca_android` at `5fbe8173`: exactly five specifications do not index — `CipherInputStreamSpec`, `CipherOutputStreamSpec`, `HMACParameterSpecSpec`, `KeyStoreSpec`, `RandomStringPassword` — with the counting rule asserted as data.
- [ ] 6.7 Test cause (c): `jca_android/RandomStringPassword.mop` (`ere : vo gb`, empty `@match`, no `@fail`) is refused, and M1–M4 emit nothing for it. Quote the file's own header in the emitted reason — it explains that an empty handler is the only way JavaMOP's grammar lets you state an automaton with nothing to report.
- [ ] 6.8 Test cause (b): `jca_android/HMACParameterSpecSpec.mop` emits `Unknown{UnresolvedSignature, class: "javax.xml.crypto.dsig.spec.HMACParameterSpec", mode: CLASSE-AUSENTE}`, and the report says the monitor is **live** and the target absent — not that the monitor is dead.
- [ ] 6.9 Test cause (a): `CipherInputStreamSpec` and `CipherOutputStreamSpec` are **not** refused. Their `ere` is `c1 (r1|r2)+ cl1`; the word `c1 r1` is a live prefix; the silence on the `-unclosed` traces is the `IncompleteOperationError` blind spot, and it belongs in `divergence_record.csv`, not in a refusal.
- [ ] 6.10 Test the AST checker against `jca/GCMParameterSpecSpec.mop` (two events with identifier `c1`, `ere` referencing a non-existent `c2`) and against `jca/SecretKeySpecSpec.mop` (unbalanced parentheses that nonetheless parse). Both are caught; the emitted note records that both files parse, generate a monitor and compile with zero errors.
- [ ] 6.11 M0 measures the "absorbs misuse" property as an AST fact (an `addError` in an event body, before the `ere`/`fsm` line), replacing the ad-hoc regex census. Assert the declared rule reproduces `18 of 24` for `jca_android` and `15 of 23` for `jca` at `5fbe8173`, and emit the rule beside the number.
- [ ] 6.12 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-core test` green.

## Closing
G06 closes when 6.1–6.12 are `[x]`.

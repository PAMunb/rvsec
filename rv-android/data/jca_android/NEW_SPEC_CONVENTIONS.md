# Writing a new `jca_android` specification

The change `gh109-crysl-coverage` adds 24 `.mop` files to a set that had 22 paired rules, and it
adds them in parallel: several tasks write several files at once, against one oracle, into one
`codes.csv`, under one set of gates. This page is what makes those files come out the same shape.
It is not a style guide. Every rule here exists because a gate, a record or a measured defect of the
existing set demands it, and each one says which.

Roots used below: `SET` = `rvsec/rvsec-mop/src/main/resources/jca_android`,
`ORACLE` = `RVSec-replication-package/tools/rules` (the sole oracle, D-16, pinned by
`data/jca_android/oracle/expert_rules.sha256`).

## 1. Naming, and the one exception

A rule `<Rule>.crysl` is specified by `SET/<Rule>Spec.mop`, whose specification header is
`<Rule>Spec(<SpecClass> <binding>)` where `<SpecClass>` is the class the rule's `SPEC` line names.
`gh105_expert_ledger.py:438-448` pairs by exactly that convention — it tries `<Rule>Spec.mop` and
then `<Rule>.mop` — so a file named correctly is paired automatically and needs no table entry.

Two things a writer trips over:

- **`IvParameterSpec.mop`, not `IvParameterSpecSpec.mop`.** The set carries both spellings because
  `paired_rules` accepts both. Do not add a third. New files use `<Rule>Spec.mop`.
- **Rule `Key` becomes `KeySpec.mop`** (task 2.14). Read on its own the name suggests
  `java.security.spec.KeySpec`, which is a different type; the file is the specification of the
  interface `java.security.Key`, and its javadoc says so in the first line. The name is kept because
  changing it would mean teaching `paired_rules` an exception, and an exception in the pairing code
  is worse than a name that needs one sentence of explanation.

`NON_PAIRING_FILES` (`gh105_expert_ledger.py:164-168`) holds `SecretKeySpec.mop`,
`RandomStringPassword.mop` and `IvChainJunction.mop`. Never add a new file to it: a new file that
needs an exemption from pairing is a new file whose name is wrong.

## 2. Structure

The file has the shape of `GCMParameterSpecSpec.mop` (multi-clause producer) or
`IvParameterSpec.mop` (single-clause, overload-fused producer). Read one of the two before writing.

```
package mop;

import <the SPEC class>;

import br.unb.cic.mop.eh.*;
import br.unb.cic.mop.PredicateStore;
import br.unb.cic.mop.PredicateVerdict;
import br.unb.cic.mop.Property;

/**
 * <Rule>
 *
 * A JavaMOP specification of the correct usage of the <fully.qualified.SpecClass>.
 *
 * @see https://github.com/CROSSINGTUD/Crypto-API-Rules/blob/master/JavaCryptographicArchitecture/src/<Rule>.crysl
 */
<Rule>Spec(<SpecClass> s) {

    <SpecClass> spec;          // bound ONLY on the conforming branch; see §4

    event c1 after(<args>) returning(<SpecClass> s):
      call(public <SpecClass>.new(<types>)) && args(<args>) {
        ...                    // §3: every CONSTRAINTS and REQUIRES clause, accusing
    }

    ere : c1                   // §5: the rule's ORDER, verbatim

    @fail { ...; __RESET; }    // §5

    @match { PredicateStore.instance().ensure(Property.<P>, spec); }   // §4
}
```

- **Events realize the rule's `EVENTS`**, with constructor overloads fused only where the rule's own
  label fuses them (`Con := c1 | c2` fuses; two labels do not). A fused event keeps every conjunct
  of both overloads — `IvParameterSpec.mop:80-101` records why assuming complementarity lost calls.
- **Ceiling: 17 events per specification** (INV-INS-154). Every specification this change adds is
  ≤ 5; state the count in the task fiche anyway, because the check is the point.
- **Comment density matches the set.** Each event carries a paragraph saying which clause of the
  rule its body implements and why the check sits where it sits. That is not decoration: it is the
  only place a later reader learns whether a missing check is an omission or a decision.

## 3. Clauses go in the body, never in `condition(...)`

This is the substrate rule gh105 exists to establish (INV-INS-133), and it is the one mistake that
silently costs the whole specification.

`condition(...)` compiles to `if (!(guard)) return false;` **ahead of both the event body and the
transition**. A construction that breaks the guard therefore takes no transition, reaches no
accepting state, and is accused of nothing — measured on `GCMParameterSpecSpec`, where both events
were guarded and every program the file could see produced zero reports
(`GCMParameterSpecSpec.mop:26-44`). A failed `REQUIRES` is not a typestate failure.

So:

- **Every `CONSTRAINTS` clause lands in the event body**, with an accusing branch on the violated
  side (INV-INS-152). A value clause with no accuser is total silence, which is exactly the R1
  defect this change repairs in `DHGenParameterSpecSpec`.
- **Every `REQUIRES` clause is a `PredicateStore` read in the body**, three-valued, with
  `VIOLATED` and `NOT_OBSERVED` reported under **different code families** (INV-INS-143): `CONSTR`
  for the first, `NOBS` for the second. `VIOLATED` is positive evidence that the object carries the
  predicate with other values or had it withdrawn; `NOT_OBSERVED` says only that no producer was
  ever seen, which on Android is as often a reach limit of the instrumentation as a misuse. Folding
  them into one family counts a reach limit as a misuse.
- **Accumulate, do not short-circuit.** Use the `boolean conforms = true;` form of
  `GCMParameterSpecSpec.mop:65-84`: each failing clause reports and clears the flag, and the write
  happens under `if (conforms)`. An `else if` chain reports only the first failure of a construction
  that broke two clauses.
- **A guard that cannot be false stays a guard.** Where the constructor itself throws before the
  `after ... returning` advice can run (negative offsets, lengths past the end of an array), the
  conjunct is kept in the write guard and *not* given a code: a code with no reachable emission is
  an accusation against a program the platform forbids. `GCMParameterSpecSpec.mop:87-103` and
  `IvParameterSpec.mop:89-101` are the two worked examples.

Predicate reads use the enum-typed API of `PredicateStore` (`ensure`, `validate`, `validateAny`,
`validateAbsent`, `negate`; `PredicateStore.java:291-438`). There is no string path — the constant
must exist in `Property.java`, which is why task 0.7 adds all of them in one commit ahead of G2–G4.

## 4. Where the predicate write goes

`ENSURES p[this]` with no `after L` qualification means the acceptance point is the accepting state,
which in an `ere` is `@match` (INV-INS-134). `ENSURES p[x] after L` means the write goes in the
handler for `L`.

The object reaches `@match` through a **monitor field bound only on the conforming branch**. A
handler sees no event arguments, and `ensure` treats a `null` binding as a no-op
(`PredicateStore.java:291-293`), so a construction that broke a clause reaches the handler with
nothing bound and writes nothing. That is the literal reading of CrySL: a predicate is ensured for a
use that satisfied the rule.

**Algorithm-valued writes pass through `ConscryptAliasTable.canonical`** before they are stored
(D-20.3, INV-INS-153). Readers query canonical names and `PredicateStore` only lowercases, so a raw
user spelling (`HMAC/SHA256`, an OID, `RC4`) breaks propagation silently and shows up downstream as
`NOT_OBSERVED` — the R8 defect this change repairs at `KeyGeneratorSpec.mop:215`.

## 5. ORDER and `@fail`

The `ere` is the rule's `ORDER`, transcribed. Nothing else may govern a transition: a value clause
and a predicate read are accused in the body (§3), not by suppressing the event.

Two shapes to know:

- A single-event `ORDER = Con` makes `@fail` **unreachable** — the transition row is `{1, 2, 2}` and
  the monitor is keyed on the constructed object, so no monitor sees a second event. Write the
  handler anyway (the generator and `codes.csv` bijection both expect it) and say in a comment that
  it cannot fire, as `GCMParameterSpecSpec.mop:134-146` does.
- A `+` over an alternation does not mean what it looks like when one alternative erases to ε
  against the rule's alphabet. That is the R4 defect (`CipherOutputStreamSpec.mop:62`, where
  `c1 fl cl` is accepted and the rule rejects it). Check the erasure before writing a `+`.

**Every `@fail` block ends in `__RESET;`** — 21 of 21 in the live set do, since gh105 task 9.2.
Without it the monitor stays in the failure category and every later event of the same binding
re-raises the ordering code.

## 6. Codes

Append rows to `SET/codes.csv` **in the task that writes the `.mop`**, in file order. The columns
are `spec,code,error_type,site_kind,event,file_line`.

- The code is `<RULE-UPPER>-<KIND>-<NN>`, where `<RULE-UPPER>` is the **rule** name uppercased with
  no separators (`GCMParameterSpec` → `GCMPARAMETERSPEC`), not the specification name.
- `<KIND>` is one of the `site_kind` values already in use: `ORDER`, `CONSTR`, `NOBS`, `ALG`,
  `FORB`, `KEYSIZE`, `KSTYPE`, `PROTO`. `error_type` is the matching `ErrorType` constant —
  `UnsatisfiedConstraint` for `CONSTR` and `NOBS`, `InvalidSequenceOfMethodCalls` for `ORDER`,
  `UnsafeAlgorithm` for `ALG`, `ForbiddenMethod` for `FORB`. A `FORBIDDEN` clause reported as
  `InvalidSequenceOfMethodCalls` sends the reader hunting for a missing call
  (`ErrorType.java:12-18`).
- `<NN>` numbers sites **within the file**, in emission order, per kind.
- A code names a **site, not a clause**: one clause read at two constructors gets two codes, because
  the report has to say which constructor it is about (`IvParameterSpec.mop:103-106`).
- `file_line` is the line the `addError` call starts on. `gh104_message_gate.py` checks the anchor,
  the bijection (every site has one row, every row has one site) and that no standalone integer
  appears in the message that the guard does not use. Re-anchor after any edit that moves lines.

The message envelope is fixed (D-3):

```
"v=1 code=<CODE> ev=" + __EVENTNAME + " obj=<SpecClass> val='<observed>' exp='<what the rule admits>' msg='<one sentence, lower case>'"
```

`val` must be the operand the guard actually read. A guard on a monitor field whose message prints
the observed object's algorithm produces an envelope that can carry `val` inside the `exp` list it
is accused of missing — an accusation that refutes itself, which the gate flags as
`self-contradicting envelope`.

## 7. The viability fiche

Every G2–G4 task states, before it writes a line:

1. **Class and members confirmed in the api30 jar by `unzip -l`** (INV-INS-154). Never `javap -cp`:
   that resolves against the host JDK and will confirm a class Android does not ship.
2. **Event count**, against the ceiling of 17.
3. **Which predicates the file writes and which it reads**, by `Property` constant, with the
   `ORACLE/<Rule>.crysl` line of each clause.
4. **The `codes.csv` rows the task will append**, by code.

## 8. Records: what a spec task touches and what it must not

Ownership under D-22, because G2–G4 run in parallel:

| File | Owner |
|---|---|
| the new `.mop` | the spec's own task |
| `SET/codes.csv` (its own rows, appended) | the spec's own task |
| `divergence_record.csv` | the group's closing `X.R` task only |
| `predicate_graph.csv`, `predicate_ledger.csv`, `order_alphabet_map*.csv` | the group's closing `X.R` task only |
| `Property.java` | task 0.7 only, once, ahead of the groups |
| CI enumeration constants (`Corpora`, `MopLiftCorpusTest`, `CalibrationTargets`, G-PARAM count, G-ORDER skip set) | task 6.1 only |

**A new file is one `new-file` divergence row**, not a hunk-by-hunk baseline (precedent:
`IvChainJunction`). The `task` column of a gh109 row is written `gh109:<task>` — the task numbers of
this change collide with gh104's and gh105's, and the record is read by people.

An oracle defect is recorded as a narrative `oracle-wart` row against the **rule** path
(`tools/rules/<Rule>.crysl`), never as an upstream edit, and never as a terminal state: the rule is
transcribed by evident intent and ends `covered`, with the row as its warrant (D-21). The five rows
of task 0.1 are the worked examples.

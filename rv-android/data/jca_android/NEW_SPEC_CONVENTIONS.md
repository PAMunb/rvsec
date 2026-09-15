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
  of both overloads — the comment above `IvParameterSpec.c2` records why assuming complementarity lost calls.
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
(the comment above `GCMParameterSpecSpec.c1`). A failed `REQUIRES` is not a typestate failure.

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
  `GCMParameterSpecSpec.c1`: each failing clause reports and clears the flag, and the write
  happens under `if (conforms)`. An `else if` chain reports only the first failure of a construction
  that broke two clauses.
- **A guard that cannot be false stays a guard.** Where the constructor itself throws before the
  `after ... returning` advice can run (negative offsets, lengths past the end of an array), the
  conjunct is kept in the write guard and *not* given a code: a code with no reachable emission is
  an accusation against a program the platform forbids. The comments above `GCMParameterSpecSpec.c2`
  and `IvParameterSpec.c2` are the two worked examples.

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
`NOT_OBSERVED`. The `@match` handler of `KeyGeneratorSpec.mop` writes the canonical name for this
reason.

### The upstream-refusal mark

A producer that reports on the object it produces tells every later consumer so, through the
property `REPORTED_UPSTREAM`. Without it a consumer of a refused object answers `NOT_OBSERVED` —
the store has no producing predicate for the object, because the producer withheld the write — and
the report reads like a reach limit of the instrumentation when the object was in fact seen and
refused one link earlier. The mark changes only which `-NOBS-` code the consumer emits; it never
turns a `SATISFIED` read into a report, because the ordinary read runs first.

The producer idiom (`KeyFactorySpec.mop:90-114` is the worked example):

```
boolean conforms = true;
boolean reported = false;
... each value or origin report on the product ...
    conforms = false;
    ErrorCollector.instance().addError(...);
    reported = true;
...
if (conforms) { PredicateStore.instance().ensure(Property.<P>, product); }
if (reported) { PredicateStore.instance().ensure(Property.REPORTED_UPSTREAM, product); }
```

- **Only value and origin reports mark**: a code of the families `ALG`, `KEYSIZE`, `KSTYPE`,
  `PROTO`, `FORB`, `CONSTR` or `NOBS`, labels included. An `-ORDER-` report never marks, because a
  sequence failure says nothing about the value of the object, and mixing the order channel into
  the origin channel would relabel reports that have nothing to do with the product's value.
- **A consumer that produces marks in turn.** A chain therefore reports its first failure with its
  own code and every later link with `upstream-refused`.
- **Bridges carry the mark across a copy.** `KeySpec.ge1` and `SecretKeySpec.e1` mark the array
  `getEncoded()` returns when the key carries the mark, so the re-wrap
  `new SecretKeySpec(derived.getEncoded(), "AES")` does not break the chain in the middle.
- **The producers and consumers are the ones the set names, and the lists are not closed.** The
  producers are `SecretKeySpecSpec` (`c1`, `c2`), `GCMParameterSpecSpec` and `IvParameterSpec`
  (`c1`, `c2`), `PBEKeySpecSpec.c1`, `X509EncodedKeySpecSpec.c1`, `KeyFactorySpec`
  (`genPublic`, `genPrivate`), `SecretKeyFactorySpec.gen`, `KeyAgreementSpec` (`gs1`, `gs2`) and
  the two bridges. The consumers are `CipherSpec.i2`, `MacSpec.i1`, `IvChainJunction.use`,
  `SecretKeyFactorySpec.gen`, `KeyFactorySpec.genPublic`/`genPrivate`, `KeyAgreementSpec.dophase`,
  `SignatureSpec.i4`, `SecretKeySpecSpec.c1`/`c2` and `X509EncodedKeySpecSpec.c1`. Other producers
  that report on their product do not mark, and other `-NOBS-` sites keep `not-observed`. A new
  specification joins either list only by a recorded decision.
- **`SecureRandomSpec` and `KeyGeneratorSpec` do not mark.** A `SecureRandom` of a refused
  algorithm, and the arrays `SecureRandomSpec` discards in `@fail`, would be marked by a sequence
  failure or by the discard itself, which is the channel mixing the first bullet excludes. The
  `RANDOMIZED` readers therefore keep `not-observed`.

The consumer side is a `-NOBS-` label and is written as §6 describes: the read is
`validateAny(Property.REPORTED_UPSTREAM, bound) == PredicateVerdict.SATISFIED`, in the same
`else if` as the `NOT_OBSERVED` test.

## 5. ORDER and `@fail`

The `ere` is the rule's `ORDER`, transcribed. Nothing else may govern a transition: a value clause
and a predicate read are accused in the body (§3), not by suppressing the event.

Two shapes to know:

- A single-event `ORDER = Con` makes `@fail` **unreachable** — the transition row is `{1, 2, 2}` and
  the monitor is keyed on the constructed object, so no monitor sees a second event. Write the
  handler anyway (the generator and `codes.csv` bijection both expect it) and say in a comment that
  it cannot fire, as the comment above the `@fail` of `GCMParameterSpecSpec.mop` does.
- A `+` over an alternation does not mean what it looks like when one alternative erases to ε
  against the rule's alphabet: under `(w1 | w2 | fl)+` the word `c1 fl cl` is accepted and the rule
  rejects it, which is why `CipherOutputStreamSpec.mop` writes `fl*` around its writes (the comment
  above its `ere`). Check the erasure before writing a `+`.

**Every `@fail` block ends in `__RESET;`** — 21 of 21 in the live set do, since gh105 task 9.2.
Without it the monitor stays in the failure category and every later event of the same binding
re-raises the ordering code.

### Labels in `@fail`: the monitor-field idiom

An ordering failure is not always a program calling things in the wrong order. When the first
event a monitor sees is not a creation of the object, the object was created where the monitor
cannot see — inside the framework, by a route the rule does not list, by a subclass — and the
automaton fails on a correct program. And the API lets a used `Cipher` or `Mac` be initialised
again, which the rule's `ORDER` does not accept. The handler says which of the three it saw, by
code, and it can only do so from facts the specification recorded while events arrived. Those
facts are monitor fields, because the generated `reset()` clears only the state and the category
flags and never a user field, so a fact written before a failure is still there after it.

- **`boolean creationObserved = false;`** in every specification whose automaton begins with a
  creation event, set to `true` in the body of **every creation event**. A creation event is a
  constructor or static-factory event that binds the monitored parameter through
  `returning(...)`, whatever its condition or transition — refused and forbidden twins included
  (`CipherSpec.g3`, `SSLContextSpec.getDefault`, `PBEKeySpecSpec.f1`/`f2`). An event that binds the
  monitored parameter through `target(...)` is never a creation event
  (`DigestInputStreamSpec.on`, `KeyAgreementSpec.gs3`). A creation route guarded by
  `condition(...)` that rejects the call runs no body (§3), so every creation event guarded by an
  allow-list has a **refused twin** with the negated guard for every overload its pointcut admits;
  otherwise a refused creation in woven code would read `creation-unobserved`. A twin added for
  that purpose records the creation facts and nothing else, and sits in the automaton beside the
  admitted creation so that the first use fails where it would fail with no event (a Kleene prefix
  of the `ere`, an `fsm` state with no outgoing transition). When the event ceiling leaves no room
  (`CipherSpec`), the one-argument twin is widened to `getInstance(String, ..)` with
  `args(x, ..)` instead.
- **`boolean creationRefused = false;`** in every specification with a refused creation, set to
  `true` in the body of every refused twin and of every forbidden creation that reports `FORB`
  (`PBEKeySpecSpec.f1`/`f2`, `SSLContextSpec.getDefault`). The automaton admits no use of such an
  object, so its ordering failure is the consequence of the refusal, and the handler says so.
- **`boolean operationFinished = false;`** in `CipherSpec` and `MacSpec` only, set in the body of
  every event whose transition completes an operation (`CipherSpec.mop:112-116` lists them). It is
  set in the body, before the transition is decided, because the fact is about the object and not
  about the automaton.
- **`boolean reuseObserved = false;`**, beside it, set by `@fail` itself when `operationFinished`
  holds and the failing event is an initialisation event, tested with `__EVENTNAME`, which the
  generator expands in handlers too.

The handler then chooses one code, in this precedence (`CipherSpec.mop:555-586`):

```
@fail {
    if (operationFinished && ("i1".equals(__EVENTNAME) || "i2".equals(__EVENTNAME))) {
        reuseObserved = true;
    }
    if (!creationObserved)     { ... <RULE>-ORDER-NN  label creation-unobserved ... }
    else if (creationRefused)  { ... <RULE>-ORDER-NN  label creation-refused ... }
    else if (reuseObserved)    { ... <RULE>-ORDER-NN  label reuse-after-final ... }
    else                    { ... <RULE>-ORDER-00  label sequence ... }
    ...
    __RESET;
}
```

`creation-unobserved` comes first because it qualifies everything after it: with no creation seen,
the monitor's record of the object is partial, and so is any reuse it believes it saw. A refused
creation sets `creationObserved` too, so `creation-refused` is tested only once a creation was seen,
and it comes before reuse because a refused object admits no use at all. The three labels persist on the monitor: once one is reported,
every later failure of the same monitor carries it, because after a reset no creation event can
arrive for the object and the automaton cannot return to a state its real history satisfies. A
specification with no creation event (`SSLEngineSpec`) declares no field and has no
`creation-unobserved` code. A specification whose automaton is a single creation event has an
unreachable `@fail` (above) and still carries both branches, so every row of `codes.csv` keeps its
one site. The JavaMOP `creation` modifier is not a substitute for the field: it changes when
monitors are created, and therefore what is reported.

## 6. Codes

Append rows to `SET/codes.csv` **in the task that writes the `.mop`**, in file order. The columns
are `spec,code,error_type,site_kind,event,file_line,label`.

- The code is `<RULE-UPPER>-<KIND>-<NN>`, where `<RULE-UPPER>` is the **rule** name uppercased with
  no separators (`GCMParameterSpec` → `GCMPARAMETERSPEC`), not the specification name.
- `<KIND>` is one of the `site_kind` values already in use: `ORDER`, `CONSTR`, `NOBS`, `ALG`,
  `FORB`, `KEYSIZE`, `KSTYPE`, `PROTO`. `error_type` is the matching `ErrorType` constant —
  `UnsatisfiedConstraint` for `CONSTR` and `NOBS`, `InvalidSequenceOfMethodCalls` for `ORDER`,
  `UnsafeAlgorithm` for `ALG`, `ForbiddenMethod` for `FORB`. A `FORBIDDEN` clause reported as
  `InvalidSequenceOfMethodCalls` sends the reader hunting for a missing call
  (`ErrorType.java:12-18`).
- `<NN>` numbers sites **within the file**, per kind. A new file numbers them in emission order. A
  code added to a file that already has codes takes the **next free number of its family in that
  file** — the highest `<RULE-UPPER>-<KIND>-NN` in `codes.csv` plus one — wherever the site sits,
  and no existing code is renumbered. Numbers are therefore not in line order in an edited file
  (`SSLCONTEXT-NOBS-03` is emitted above `SSLCONTEXT-NOBS-00`), and that is the price of two
  workers editing two files never colliding on a number, and of a code meaning the same thing in
  every campaign that emitted it.
- A code names a **site, not a clause**: one clause read at two constructors gets two codes, because
  the report has to say which constructor it is about (the comment above `IvParameterSpec.c2`). One site
  with two labels is two sites and two codes (§6.2).
- `file_line` is the line the `addError` call starts on. `gh104_message_gate.py` checks the anchor,
  the bijection (every site has one row, every row has one site) and that no standalone integer
  appears in the message that the guard does not use. Re-anchor after any edit that moves lines.
- `label` names what the code means, from a closed vocabulary (§6.1).

### 6.1 The `label` column

A report of the `-NOBS-` family says the predicate store has no entry for the object a rule
constrains, and several structurally different situations produce that answer; an ordering report
likewise covers more than a wrong order (§5). Each of those situations has its own code **inside
the existing family**, and the `label` column says which situation a code stands for. The family is
kept on purpose: every consumer that separates not-observed from accusation reads the family
(`scripts/gh109_nobs_channel.py` counts every family other than `NOBS` as an accusation;
`gh104_message_gate.py` requires `NOBS` under a `NOT_OBSERVED` branch), and a new family would
silently become an accusation in all of them. An analysis joins `errors.csv.code` with
`codes.csv.label`.

| `label` | Family | Emitted when |
|---|---|---|
| `violation` | every family other than `ORDER` and `NOBS` | the value, constraint or forbidden-call site reports |
| `sequence` | `ORDER` | `@fail`, when none of the labels below applies |
| `creation-unobserved` | `ORDER` | `@fail`, when no creation event was observed on the monitor (§5) |
| `creation-refused` | `ORDER` | `@fail`, when the creation observed was a refused twin or a forbidden creation (§5) |
| `reuse-after-final` | `ORDER` | `@fail` of `CipherSpec` and `MacSpec`, when an initialisation event fails after an operation finished (§5) |
| `not-observed` | `NOBS` | a `NOT_OBSERVED` read none of the labels below explains |
| `platform-default` | `NOBS` | the bound argument is a `null` the API documents as "use the platform default" (`TrustManagerFactory.init`, `KeyManagerFactory.init`, each of the three arguments of `SSLContext.init`) |
| `upstream-refused` | `NOBS` | the bound object carries `REPORTED_UPSTREAM` (§4) |
| `application-manager` | `NOBS` | `SSLContext.init`, a non-null trust-manager array not credited per element that holds an element of a class defined by a class loader other than the one that defined `TrustManager` (`Evidence.isApplicationDefined`) |
| `random-key-material` | `NOBS` | `SecretKeySpecSpec.c1`/`c2`, key material that is not `PREPARED_KEY_MATERIAL` but is `RANDOMIZED` |

A label must agree with its family, and the message gate's `label-vocabulary` check fails a row
whose label is outside the vocabulary or filed under a family that does not admit it. The class
loader, not a package name, decides `application-manager`, so the rule holds for any APK; a
delegating manager written by the application lands there too, and the monitor cannot tell it from
a trust-all one.

### 6.2 Labels at a `-NOBS-` site

A label code is emitted **at the site and under the branch where the unlabelled code of its family
would otherwise be emitted**: a label adds a report site to `codes.csv` without adding or removing a
reported `(class, method, spec, event, location)` at run time (§6.3 is the one exception). So a
`NOT_OBSERVED` read with labels becomes an `else if` chain in which each label's condition is
conjoined **on the same line** with the verdict test:

```
if (verdict == PredicateVerdict.VIOLATED) {
    ... <RULE>-CONSTR-NN ...
}
else if (verdict == PredicateVerdict.NOT_OBSERVED && arg == null) {
    ... <RULE>-NOBS-NN  platform-default ...
}
else if (verdict == PredicateVerdict.NOT_OBSERVED && PredicateStore.instance().validateAny(Property.REPORTED_UPSTREAM, arg) == PredicateVerdict.SATISFIED) {
    ... <RULE>-NOBS-NN  upstream-refused ...
}
else if (verdict == PredicateVerdict.NOT_OBSERVED) {
    ... <RULE>-NOBS-00  not-observed ...
}
```

The same-line form is not taste. The message gate classifies a site by the nearest enclosing `if`
line and requires a `NOBS` code under a `NOT_OBSERVED` test; a label test nested as its own `if`
inside the `NOT_OBSERVED` branch hides the verdict from the gate, which then files a `NOBS` code
under a branch with no verdict and fails. `TrustManagerFactorySpec.mop:180-194`,
`SecretKeySpecSpec.mop:136-150` and `SSLContextSpec.mop:282-297` are the worked examples.

When more than one label applies, the chain is ordered by this precedence: `platform-default`, then
`upstream-refused`, then `application-manager` or `random-key-material`, then `not-observed`. A
`null` is decided first because nothing else can be said about it; a mark comes before a class or a
randomness fact because it points at a report already made, which is where the reader should go.

### 6.3 The per-element trust-manager credit

`TrustManagerFactorySpec.gtm1` marks every non-null element of the array it returns with
`GENERATED_TRUST_MANAGERS`, beside the array itself, and `SSLContextSpec.init` answers `SATISFIED`
for the trust-manager array when the array is marked, or when it is non-empty and **every** element
is marked (`SSLContextSpec.mop:270-281`). An application that copies a factory-issued manager into
a new array passes an array the store never saw, and the manager — the object the rule constrains —
is exactly the one the factory issued. One unmarked element withholds the credit, which closes the
case of an array that mixes a factory manager with one the application wrote. This is the one label
rule that changes which sites report. Key-manager arrays are not credited per element.

### 6.4 The envelope and its evidence keys

The message envelope is fixed (D-3):

```
"v=1 code=<CODE> ev=" + __EVENTNAME + " obj=<SpecClass> val='<observed>' exp='<what the rule admits>' msg='<one sentence, lower case>'"
```

which puts on the wire

```
v=1 code=<CODE> ev=<event> obj=<SpecClass> val='<observed>' exp='<admitted>' msg='<sentence>'[ vfp='<fingerprint>'][ vcls='<classes>']
```

The two trailing keys are **evidence**, and they appear only in a `-NOBS-` envelope. Every `-NOBS-`
site, of any label, ends its `ErrorDescription` argument with `+ Evidence.keysFor(<bound>)` right
after the closing `'` of `msg`, where `<bound>` is the object whose read answered `NOT_OBSERVED`:

```
"... msg='no generator of the key given to Cipher.init was observed'" + Evidence.keysFor(key)));
```

`br.unb.cic.mop.eh.Evidence.keysFor` returns ` vfp='sha256:<16 hex>'` (the first eight bytes of the
SHA-256 of the bytes) for a `byte[]`, ` vcls='<classes>'` (the runtime classes of the elements,
comma-joined in array order) for a `TrustManager[]`, and the empty string for anything else, `null`
included; values follow the `q()` rule (at most 512 characters, `'` escaped). The helper is not
called `suffix` because `suffix` is a reserved token of the JavaMOP grammar, and a `.mop` that
writes `Evidence.suffix(` does not parse. The keys exist so an analysis can triage non-observation
reports without reading source — a fingerprint identical across installations points to a value
embedded in the application, an application-defined class to a manager worth reading — and nothing
in the specification may depend on them: the gate's `evidence-only-on-nobs` check fails a helper
call outside a report argument, or inside the envelope of any other family. They sit after `msg`
so every reader that locates `code`, `ev`, `val` and `exp` by position or leading key is
unaffected, and `RvErrorLog.unique_msg` removes them from the record's identity, so a fingerprint
that differs per run does not multiply unique counts.

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

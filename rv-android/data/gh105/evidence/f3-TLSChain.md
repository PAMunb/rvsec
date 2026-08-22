# F3 — the TLS chain (tasks 5.9 and 6.2): ledger clauses #14, #36, #28 and #29

The batch that closes three of the four G-PRED2 findings and makes the closure gate move for the
first time since Group 5 began. Four `REQUIRES` clauses of api30 wire producer to consumer along
one chain — a key store into two factories, and the factories' manager arrays into an
`SSLContext` — and the pointcut repair that a producer needed before any of it could be measured
travels in the same commit, because the tasks declare the coupling in both directions.

| ledger | consuming rule | clause | read site |
|---|---|---|---|
| #14 | `KeyManagerFactory` | `generatedKeyStore[keyStore]` (`KeyManagerFactory.cryptsl:46`) | `KeyManagerFactorySpec.init` |
| #36 | `TrustManagerFactory` | `generatedKeyStore[keyStore]` (`TrustManagerFactory.cryptsl:42`) | `TrustManagerFactorySpec.init` |
| #28 | `SSLContext` | `generatedKeyManager[kms]` (`SSLContext.cryptsl:48`) | `SSLContextSpec.init` |
| #29 | `SSLContext` | `generatedTrustManager[tms]` (`SSLContext.cryptsl:50`) | `SSLContextSpec.init` |

The producers were already there and had been write-only since task 4.14:
`KeyStoreSpec.@match` writes `generatedKeyStore[this] after Loads`,
`KeyManagerFactorySpec.gkm1` writes `generatedKeyManager[kms]`, and
`TrustManagerFactorySpec.gtm1` writes `generatedTrustManager[tms]`. `KeyStoreSpec.mop` is not
edited by this batch at all: its finding closes because a reader appeared elsewhere, which is
what the closure gate measures.

The rule's third `SSLContext` clause, `randomized[sr]` (ledger #30), is **not** wired and is not
a gap: `Init: init(kms, tms, _)` binds `sr` in no event, so the clause has no site to be read
at. It stays recorded `vacuous`.

## The measurements that decided the batch

All on Temurin 21, all before the reads were written. Having a `.mop` at both ends is necessary
and not sufficient (finding 73), and the platform sometimes already refuses the program a clause
would accuse (finding 87), so both questions were asked of every link.

| probe | result |
|---|---|
| loaded PKCS12 → `kmf.init(ks, pw)` → `getKeyManagers()` → `ctx.init(kms, tms, null)` | **runs to completion** — the chain composes end to end |
| `kmf.init(store, pw)` on a store never loaded | `KeyStoreException: initialization failed` |
| `tmf.init(store)` on a store never loaded | **runs** — the platform does *not* refuse it |
| `tmf.init((KeyStore) null)` | **runs** — the documented default-truststore route |
| `ctx.init(null, null, null)` | **runs** |
| `ctx.init(null, {trust-all X509TrustManager}, sr)` | **runs** — the classic TLS misuse is reachable |
| `ctx.init(new KeyManager[0], new TrustManager[0], null)` | runs |
| `kmf.getKeyManagers()` / `tmf.getTrustManagers()` before an `init` | `IllegalStateException` |
| `getKeyManagers()` twice / `getTrustManagers()` twice | **a fresh array each time** (`kms1 == kms2` is false) |
| declared return types | `getKeyManagers()` → `KeyManager[]`; `getTrustManagers()` → `TrustManager[]` |

Three of those decided something.

**The platform does not refuse what these clauses accuse.** `ctx.init(null, null, null)` and the
trust-all manager both run, so finding 87 does not dissolve #28 and #29 the way it dissolved the
second position of clause #5. These reads have programs to be about, and the one they are most
about is the one the rule exists to catch.

**`tmf.init(unloadedStore)` runs where `kmf.init(unloadedStore, pw)` throws.** The asymmetry is
what makes #36 discriminate something the platform does not: a trust manager factory really can
be built over a key store nothing ever initialised, and only this read says so. It is witnessed
by a trace written for it.

**Both factories allocate a fresh array on every call.** The predicate travels with the array
*this* call returned and with no copy of it, so a program that rebuilds or copies the array
reaches the read with nothing written. That is a reach limit, it is named in both files, and it
is what the `NOBS` codes say.

## The three researcher decisions (2026-08-22)

### 65. A null argument is read, not exempted

Every existing corpus trace of these four specifications passes null — `kmf.init(null, chars)`,
`tmf.init(null)`, `ctx.init(null, null, null)` — and `PredicateStore.validate` answers
`NOT_OBSERVED` for a null bound object. The decision is to let the read report it.

It is faithful: api30 requires a key store this instrumentation saw loaded, and no argument is
not one. It is consistent: `IvChainJunctionSpec.useRandomKey` guards no null either, and task
5.7 already accepted three `SignatureSpec` traces with `initSign(null)` gaining a report as *the
reach limit saying its own name*. And a guard on null would fold "the program handed over no key
store" into silence, which is the same shape of suppression this change exists to remove — the
difference being only that the old one lived in `condition(...)` and this one would live in the
body.

**Cost stated in full and measured, not estimated**: six previously silent corpus traces gain a
report, and in a real application the default-truststore route (`tmf.init(null)`) is common and
conforming in practice. What the report says is exactly that no loading was observed, and not
that the program is broken; the distinction between a reach limit and a violation is what the
two codes per site carry. The set the 2026-08-08 audit reproved took the other option, which is
not why it was rejected but is worth recording.

### 66. The reads live in the existing `init` events, binding position zero as `Object`

`KeyManagerFactory.init` and `TrustManagerFactory.init` are each one event standing for the
rule's `i1` and `i2` at once, and neither bound an argument. Three ways to fix that were triaged
with `javamop`, and all three generate a clean aspect; the difference is the collateral.

* **Chosen**: add `args(arg, ..)` (KeyManagerFactory, whose overloads have arities 2 and 1) and
  `args(arg)` (TrustManagerFactory, both arity 1), with the formal declared `Object` and the
  body discriminating by `instanceof`. This is the fusion idiom the change already states, used
  under the condition it states — the bound position is the zeroth, which every fused signature
  has, so no overload drops out of the automaton. **Collateral: none.** No symbol enters an
  alphabet, no `fsm` changes, `order_alphabet_map.csv` needs no row, and no published `ev=`
  moves.
* Splitting into the rule's own `i1`/`i2` grows the alphabet of two mirror automata, forces the
  sibling's ordering map to be rewritten, changes the `ev=` of a published `ORDER` code, and
  duplicates the algorithm accusation across two sites.
* A separate predicate-only consumer specification adds a file to the enumerated universe, four
  `gate_allowlist.csv` rows, a code prefix and its own traces — and the one file of this set that
  is such a specification says in its own header that it exists only because `CipherSpec` had no
  event left to spend. `KeyManagerFactorySpec` declares five events and `TrustManagerFactorySpec`
  four.

`SSLContext.init` is one overload with its signature written out, so `args(kms, tms, *)` binds
both positions with the wildcard last, after every discriminating type — the only place a
wildcard is safe for the trace harness's resolver (finding 79), and it is in `args` rather than
in the `call(...)` signature the resolver actually walks.

The imprecision the fusion buys is recorded rather than hidden: a null carries no runtime type,
so `init((ManagerFactoryParameters) null)` is read as if it were `i1`. Discriminating them would
need the join point's static signature, which an event body does not see.

### 67. Task 6.2 repairs `gtm1` now, and the batch accepts what a live advice brings

`TrustManagerFactorySpec.gtm1` had **no execution path at all**, for three reasons at once: the
pointcut declared `getTrustManagers()` returning `KeyManager[]` where the API returns
`TrustManager[]` and both weavers match a return type exactly; the event parameter was declared
`TrustManager[][]`; and the target was bound to a name the specification does not declare. That
is gh104 8.7, recorded and deferred since then.

It had to be repaired in this commit rather than the next, because ledger #29 is wired in this
commit: measured against a producer that never runs, every read would have answered
`NOT_OBSERVED` for a reason that has nothing to do with the wiring, and the measurement would
have decided nothing.

**What the repair makes live, stated in full.** The write happens, so an `SSLContext.init` that
receives this array reads `SATISFIED`. And a second `getTrustManagers()` on one factory now
draws `TRUSTMANAGERFACTORY-ORDER-00`, because the transition row sends `gtm1` from the accepting
state to `start`, where the event is not declared. That accusation is faithful — api30 orders
`Gets, Init, gtm?` and the `?` refuses the repetition too — and it is symmetric:
`KeyManagerFactorySpec.gkm1` declares the right return type, has always been live, and has
always behaved this way. The repair restores two mirror specifications to being mirrors.

The `g1 i1 gtm` ordering divergence itself is untouched and stays with task 7.1, along with the
placement of both body writes. This batch does not edit an `fsm`.

## What the harness measured

126 traces against `backup/gh105-preimage/jca_android`, cumulative: **66 unchanged · 26 moved ·
24 introduced · 10 removed** (from 69 · 26 · 17 · 10 over 122).

`git diff --stat -- data/gh105/evidence/harness/` shows **three of the twenty-four reports
changed**, and they are the three specifications this batch edits. `KeyStoreSpec`, whose G-PRED2
finding this batch closes, does not appear — the closure is a reader appearing elsewhere, not a
change to the producer, and the harness says so.

### The four traces this batch adds

| trace | what it pins | class |
|---|---|---|
| `SSLContextSpec-tls-chain.txt` | the whole chain conforming: loaded PKCS12 → both factories → `ctx.init` | unchanged, silent on all four clauses |
| `KeyManagerFactorySpec-loaded-keystore.txt` | #14 satisfied | unchanged, silent |
| `TrustManagerFactorySpec-loaded-keystore.txt` | #36 satisfied | unchanged, silent |
| `TrustManagerFactorySpec-unloaded-keystore.txt` | #36 accusing — the case the platform does *not* refuse | **introduced**, `TRUSTMANAGERFACTORY-NOBS-00` |

The probe is auditable in both directions, which is what learning 27 asks: three controls that
must be silent are silent, one that must accuse accuses, and the six pre-existing traces that
gain a report gain it for a stated reason.

### The six pre-existing traces that change, one by one

| trace | before | after | why |
|---|---|---|---|
| `KeyManagerFactorySpec.txt` | silent | `KEYMANAGERFACTORY-NOBS-00` | `kmf.init(null, chars)` — decision 65 |
| `TrustManagerFactorySpec.txt` | silent | `TRUSTMANAGERFACTORY-NOBS-00` | `tmf.init(null)` — decision 65 |
| `TrustManagerFactorySpec-pkix-init.txt` | silent | `TRUSTMANAGERFACTORY-NOBS-00` | idem |
| `TrustManagerFactorySpec-x509.txt` | silent | `TRUSTMANAGERFACTORY-NOBS-00` | idem |
| `SSLContextSpec.txt` | silent | `SSLCONTEXT-NOBS-00` + `-NOBS-01` | `ctx.init(null, null, null)` — decision 65 |
| `SSLContextSpec-tls.txt` | silent | `SSLCONTEXT-NOBS-00` + `-NOBS-01` | idem |

Two more traces change what they report without changing class, because the harness classifies
by the set of accusing *events* and both the old and the new report come from `init`
(finding 14): `KeyManagerFactorySpec-guard-on-field.txt` and
`SSLContextSpec-guard-on-field.txt`. Their envelope lines in the reports show the substitution.

### The published `SSLCONTEXT-PROTO-00` control is intact, and it was counted to prove it

The harness shows `SSLContextSpec-sslv3.txt` carrying `SSLCONTEXT-NOBS-01` where it used to
carry `SSLCONTEXT-PROTO-00`, which reads like a lost accusation and is not one.
`TraceRunner.envelope` returns the **first** error whose specification matches, one per dispatch,
not one per report (finding 89). Measured directly against the generated monitor, dispatching
`g1("SSLv3")` then `init(null, null, ctx)`:

```
relatórios antes do despacho de init: 0
relatórios depois: 3
   SSLCONTEXT-NOBS-01   the TrustManager[] ... was not observed coming from a TrustManagerFactory
   SSLCONTEXT-NOBS-00   the KeyManager[] ... was not observed coming from a KeyManagerFactory
   SSLCONTEXT-PROTO-00  expecting one of Default,TLSv1.2,... but found SSLv3
```

All three fire; the harness column shows one. **The envelope column is not a count**, and a
batch that adds a second report to an already-accusing site has to measure the site rather than
read the column.

### The fourth `unresolved`, and why it is not a new one

The batch's `SSLContextSpec-tls-chain.txt` appears in the unresolved list with
`tmf.getTrustManagers() -> tms`, so the number of *trace files* carrying an unresolved line goes
from three to four. The number of unresolved *lines* stays at six, and the reason is the repair:
`TrustManagerFactorySpec.txt` used to carry the same line twice, once per snapshot, and now
carries it once — the pre-image still has the broken pointcut and this tree does not. **The
harness proves the 6.2 repair from the trace side**, in the same column that recorded the defect.

| trace | lines before | lines after |
|---|---|---|
| `MessageDigestSpec-reset.txt` | 2 | 2 |
| `SSLContextSpec.txt` | 2 | 2 |
| `TrustManagerFactorySpec.txt` | 2 | **1** |
| `SSLContextSpec-tls-chain.txt` | — | 1 (pre-image side only) |

## What the numbers did

| measure | before B4 | after |
|---|---|---|
| structural gate findings (all G-PRED2) | 4 | **1** |
| G-PRED2 lines in `gate_baseline.json` | 4 | **1** — three `repaired` |
| `predicate_graph.csv` rows | 65 | **69** |
| `read:body` / `read-absent:body` | 28 / 5 | **32** / 5 |
| `write:acceptance` / `write:body` | 26 / 5 | 26 / 5 — *unchanged* |
| reader census, `read`+`read-absent` | 33 | **37** |
| reader census, `write` | 31 | 31 — *unchanged* |
| codes in `codes.csv` | 102 | **110** |
| corpus traces | 122 | **126**, all committed |
| `divergence_record.csv` hunks | 284 | **278**, all recorded (25 stale retired, 19 new, reasons absorbed) |
| `gate_allowlist.csv` rows | 14 | 14 — *unchanged*, no new event |
| enumerated universe (`.mop`, 5 sets) | 215 | 215 — *unchanged*, no new file |
| events: `KeyManagerFactory` / `TrustManagerFactory` / `SSLContext` / `KeyStore` / `Cipher` | 5 / 4 / 4 / 7 / 17 | identical |
| assertions in the four suites | 94 | 94 (6 + 2 + 16 + 70) |

`gh104_gates.py` on the generated monitor: `G-2 0 · G-2a 11 hits/3 failures · G-2b' 18 ·
G-2c 2 · G-2d 3 · G-6' 0 · G-ERE 0 · G-CONF 0 · G-PRED 23` — **every counter identical to the
pre-batch measurement**, which is the same claim the event counts make from the other side: this
batch changed no structure.

G-ORDER: `6 passed, 4 failed, 14 skipped of 24` — the four open divergences are the four that
were open, and the row for `TrustManagerFactorySpec.gtm1` in `order_alphabet_map.csv` keeps its
symbol, its reason rewritten to say the repair changed what the event binds and whether it runs,
never which rule event it is.

## Found and not repaired

The `disposition=omission` records on `KeyManagerFactorySpec.match1/GENERATED_KEY_MANAGERS` and
`TrustManagerFactorySpec.match1/GENERATED_TRUST_MANAGER` are now operationally inert: G-PRED2
accumulates written and read predicates **by name over the whole set**, so a read of
`GENERATED_KEY_MANAGERS` anywhere stops the gate asking about every write of that name,
including the factory-bound half nobody reads. The records are kept and their reasons extended
rather than retired, because what they state is still true and still not the gate's business:
`SSLContext` asks for the predicate over the *array*, never over the factory, so that half has
no reader of its own and none is fabricated for it (INV-INS-137). The record is what keeps the
reason legible once the gate stops asking.

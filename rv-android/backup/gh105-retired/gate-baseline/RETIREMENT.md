# The expected-baseline mechanism of gh105 (task 7.6)

**Retired**: 2026-08-23, task 7.6 of `gh105-predicate-wiring`.
**What is here**: `scripts/gh105_gate_baseline.py` (279 lines), `data/jca_android/gate_baseline.json`
(91 lines) and `data/jca_android/evidence/gate_baseline_report.md` (76 lines), as they stood at
`f010cb92`.

## What it was

Design D-13 wrote the new gates before the edits that would make them green — G-ACC could not pass
until the orphans were absorbed, the placement gate not until the reads moved. Wiring them into
`tests/parity/` on arrival would have left the suite red across most of the change, and a suite
expected to be red stops being read. So each gate was registered against the baseline report its
first run committed: the pytest wrapper asserted *no regression against the recorded baseline*,
not *zero findings*, and a specification's row left the baseline as its group landed.

It was scaffolding with a demolition date written into itself — `DEMOLITION_TASK = "7.6"` — and
this is that date.

## Why it goes now, and where its two halves went

At retirement the file held **one** gate, G-ORDER, with nine rows, and five `retired` entries.
The other eight gates had already reached zero: their `_no_regression` calls were comparing
against the empty set, which the wrappers' own docstrings said in as many words. The mechanism
was already dead for eight of nine.

The nine G-ORDER rows were three anonymous fields each — `["jca_android", "CipherSpec.mop",
"order"]` — with no reason, no task and no direction, elected by whatever a `--write` happened to
measure. Task 7.6 calls that "an allow-list nobody voted for", and the accusation is about
provenance, not about the existence of exceptions. The nine therefore moved to
`data/jca_android/gate_allowlist.csv`, which is the opposite instrument: every row carries the
witness, the measurement, the reason and the owning task, and `gh105_order_gate.py` now reads it
and ignores any row whose reason is empty. G-ORDER asserts zero findings on its own.

## The five retirement records, preserved

These were decisions, not measurements, and they died with the JSON. They are kept verbatim
because each one says what a future finding from that gate would mean.

### G-ACC — task 3.7, was 17

the 17 orphan accusers of jca_android, closed by Group 3: 12 negated twins fused into their
siblings on 11 arrows, PBEKeySpecSpec.err1 fused on the same arrow as err2/err3, and 4 absorbed
into their automata (SecureRandomSpec.g4 and PBEKeySpecSpec.f1/f2 with self-loops and an
ORDER-unmapped row; KeyPairGeneratorSpec.initError as an Inits alternative mapped to i3). The gate
is now expected to be silent over jca_android in both directions, so a finding it reports is a
regression and not an expectation. The generic set's one orphan is informative and was never in
this record.

### INV-INS-133 — task 4.15, was 27

the 27 predicate reads jca_android evaluated inside condition(...), driven to zero by task 4.12,
which moved the last of them -- SecretKeySpec.e1 -- into its event body. Group 3 took 16 of the 27
away by fusing the guarded twins; the Group-4 file passes relocated the rest, and tasks 4.9 and
4.11 deleted four whose reads governed nothing any api30 rule asks for. Every read this change
still adds belongs in a body by INV-INS-133, so a guard reported here from now on is a new one and
not a leftover.

### INV-INS-134 — task 4.15, was 42

the 42 predicate writes placed away from their rule's acceptance point with no recorded reason,
driven to zero by task 4.14, which cleared the last eight over six files: six moved to the
acceptance point, and two -- KeyManagerFactorySpec.gkm1 and TrustManagerFactorySpec.gtm1, whose
transitions leave the accepting state for start, so an acceptance-point write would never run --
stayed in the event body and gained the reason the gate reads. The gate was never a ban on writing
in the body: seven sites still do, each with its reason in the predicate_graph.csv row beside it.
Retiring it says the accounting is complete, not that the sites are gone -- a write Group 5 or 6
adds off the acceptance point with no reason is a regression.

(Task 7.1 later repaired those two transitions: the edge now lands on a second accepting state,
so the body write runs at the acceptance point without moving. The reason rows stayed, because
what keeps the write out of the handler is the array, not the placement.)

### INV-INS-130 — task 4.15, was 23

the 23 specifications of jca_android that named ExecutionContext, driven to zero by task 4.14: the
seven files of its batch plus the two dangling imports left in CipherInputStreamSpec and
CipherOutputStreamSpec, which had no use at all. The check is a whole-word grep over the set and
counts mentions in comments and strings too, so the migration is complete in prose as well as in
code. No specification of the set may name the old substrate again.

### G-PRED2 — task 5.11, was 36

the 36 unclosed predicate edges jca_android opened this change with -- reads with no producer in
the set and writes with no reader, neither carrying a disposition that named the reason -- driven
to zero by Group 5. The wiring closed most of them by giving an existing write its reader; the
ones no reader could close were recorded, each with the category the ledger assigns it. Task 5.11
closed the last row, PBEKeySpecSpec c1/SPECCED_KEY, and it needed the write-side vocabulary: the
clause is an unmonitored-consumer (SecretKeyFactory, the one rule of api30 that requires
speccedKey, has no .mop in the set), but that is a *read* disposition, and a write with no reader
closes with omission or propagation and with nothing else. The ledger categorises the clause; this
column categorises the site. Retirement travels in the same commit as the closure and not a commit
later, because the baseline builds gates from findings alone: a gate at zero has no key here, and a
gate with no key is one whose next finding is compared against nothing. So the record is what
carries it forward -- a predicate read or written without an accounted counterpart is a regression
from here on, and the 21 wired clauses, the 14 recorded ones and preparedEC's unclosable are the
whole of the ledger's 36.

## The counts the JSON carried at retirement

`universe 215 · read 213 · skipped 2 · structural_findings 0 · informative 21 · allow_listed 0 ·
order_passed 13 · order_failed 9 · order_skipped 193`.

Every one of them is still derived by enumeration on each run — none of the gates ever held a
count literal. The nine `order_failed` are now nine allow-listed rows, and `order_failed` is zero.

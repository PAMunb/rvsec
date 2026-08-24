# 10.6 — code review, and what was adjudicated

What this records: the `/rv-code-reviewer` pass of 2026-08-24 over the whole change (Java + Python),
its verdict, and — for each critical finding — whether I could reproduce it against the source and
whose decision the repair is. The review is the task's deliverable; the adjudication is here because
a finding accepted without checking is how this tree inverted two diagnoses before.

## What the review found clean

Worth recording first, because it is the highest-stakes half. The **value oracle is correct**: every
list is an allow-list consumed with negated polarity, and no `addError` sits under a positive guard in
any of the 24 files. `AES/ECB` is accused (`ECB` is absent from `modes`, so `isValid` returns false);
MD5 and SHA-1 are accused in all three of MessageDigest, Signature and Mac, and `ConscryptAliasTable`
*widens* the accusation to alternate spellings rather than excusing them. `codes.csv` is an exact
bijection, verified independently: 114 rows, 114 distinct codes, 114 `code=` sites, zero orphans, zero
undeclared, zero duplicates. The `jca_android` alphabet sweep is 24/24. All suites green.

## Verdict: REQUEST CHANGES — on the instruments, not the specifications

## Findings I reproduced against the source

| # | finding | reproduced? | whose repair |
|---|---|---|---|
| 1 | `gh104_gates.py:1836` sets `ok` from failures alone and never consults `report["skipped"]`; `main()` returns `0 if report["ok"]` | **yes** | this change's — same defect class it already repaired twice |
| 2 | `backing_record():1444` — the `api30-omits`/`platform-value`/`oracle-wart`/`spelling-variant` branch tests `and obj`, where `obj` comes from the *row*, never from the record entry | **yes** | this change's |
| 3a | `TraceRunner.java:311-341` — the `catch { … continue; }` skips the before/after diff, so an accusation added before a throw is lost, and the next event's `before` set masks it forever | **yes** | this change's |
| 3b | `TraceRunner.java:1140` — `values.put(returning, produced != null ? produced : target)` binds the *receiver* as the return value for any trace line without `-> name` | **yes** | this change's |
| 5 | `CipherTransformationUtil.isValid` compares `alg` and `mode` case-**sensitively**; only padding is folded, so `Cipher.getInstance("aes/cbc/PKCS5Padding")` falls through to `return false` | **yes, but see below** | researcher's |
| 7 | `rvsec-logger-csv` `ErrorCollector:41` calls `escape(err.getExpecting()).trim()` with no null guard, while its logcat twin got `SENTINEL_ENVELOPE`; and `errors.add(err)` is evaluated before the throw, so the identity is in the dedup set and later occurrences are dropped | **yes** | researcher's — it changes what is recorded |

### Why finding 5 is a record, not an edit

The review frames it as something D-15 lost. Measured against the immediately-previous `jca_android`,
which called `Api30CipherTransformationUtil`, that is true. Measured against the thing that matters,
it is not: **the frozen `jca` set calls the same `CipherTransformationUtil.isValid`**
(`jca/CipherSpec.mop:15`, `import static br.unb.cic.mop.jca.util.CipherTransformationUtil.*`). The
case-sensitivity is therefore the behaviour every published measurement answered to, and D-15
re-pointed the successor at it deliberately.

So this is an **`oracle-wart`** in D-15's own vocabulary, and the discipline for a wart is to
transcribe and record it, never to correct it privately — correcting an expert-validated oracle on
one's own initiative is the exact failure the re-anchoring undoes. It is also forbidden mechanically:
task 11.3 and the freeze (INV-INS-109/118, task 10.1) prohibit editing that class, and 10.1's
byte-identity check is currently green.

The repair, if the researcher wants one, is a `divergence_record.csv` row plus a normalisation layer at
the **call site** in `jca_android/CipherSpec.mop` — never in the frozen class. It changes what is
accused, so it is his call and not this group's.

## Findings recorded and not adjudicated here

4 (envelope injection through unquoted `msg=`), 6 (comma injection through the positional CSV
contract), 8 (`logcat_parser.py:521` keeps a stale continuation key), 9 (neither the Java tests nor
`tests/parity/` run in CI), and roughly 45 warnings. Item 9 restates something already open in the
handoff: `TraceRunnerTest` sits in no battery, and putting it in one is the researcher's decision.

Findings 4, 6 and 7 all change what is accused or what is recorded. Under the standing rule of this
tree — a probable repair and a behavioural change are separated, and the second waits — they are
carried here and not applied in this group.

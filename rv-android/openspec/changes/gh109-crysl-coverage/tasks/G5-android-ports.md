# G5 — Android ports (independent; anytime after G0)

Small, mostly-record group. Each task is independent.

## 5.1 `HMACParameterSpecSpec` platform-dead disposition (INV-INS-155)

`javax.xml.crypto.dsig.spec.HMACParameterSpec` has zero archive entries at every scanned Android API
level — the spec's monitor can never fire an event. Researcher decision (design Open Question):
keep the file as documentation of untranslatability (default) or retire to `backup/` (P3 form).
Either way:
- `coverage_matrix.csv` row: `HMACParameterSpec → na-platform`, evidence = the archive scan.
- Reconcile the ledger's contradictory rows (#38 `unreachable-composition` — correct — vs #80
  `producible` for the same `preparedHMAC`): re-emit + `--check` green.
- If retired: G6 enumeration constants move again (same commit), divergence row records the removal.

## 5.2 The KeyStore alias gap, measured and closed as a record (revised)

**This task asked for alias rows and the measurement withdrew them.** It read: *the set admits
`BKS`/`BouncyCastle` store types but `alias_table.csv` has zero rows for the BC KeyStore service;
add the three verified missing ones and mirror them in `ConscryptAliasTable.java`.* Three
measurements taken together refuse that:

1. **There is no row to add from the table's source.** `alias_table.csv` holds exactly the
   `Alg.Alias` registrations of the pinned Conscrypt `OpenSSLProvider.java`, each citing its line
   (INV-INS-127). That file has 175 such registrations, the table has 175 rows, and the string
   `KeyStore` does not occur in it once. A BC row would be the first row of the table with no
   provider line to cite, and it would falsify the completeness claim the count exists to make
   checkable — the same reason `RSA/ECB/OAEPWithSHA1AndMGF1Padding` gets no row and is recorded
   as a `behavioural` divergence entry instead.
2. **The names are already admitted, by a different and correct mechanism.**
   `{AndroidKeyStore, AndroidCAStore, BKS, BouncyCastle}` are entries of the **closed**
   `platform-value` set, each with its citation in `divergence_record.csv`, and
   `ConscryptAliasTable.matches` resolves them by case-folded membership without consulting a
   row. Adding alias rows would record one departure twice, under two kinds.
3. **The corpus measures no other spelling.** The only KeyStore type the event census carries is
   `AndroidKeyStore` (2,005 events, 11 apps), which the list admits. No observed value is
   accused for want of a row.

So the task lands as a record and touches neither the table nor `ConscryptAliasTable.java`:
- The README's **declared limit 1** gains the measurement that closes it: the absence is a
  property of the source (zero `KeyStore` registrations in a 175/175 complete extraction), not a
  backlog, and the BC family reaches the allow-list through `platform-value`.
- A `divergence_record.csv` narrative row says the same, so the next reader of the allow-list
  finds the reason where the departure is recorded.

No reactor build and no `rvsec-core` test run are owed: no Java file moves.

## 5.3 TLS-default note + `getSocketFactory` non-addition (D-20.5)

Record (divergence narrative row + a paragraph in `data/jca_android/README.md`'s platform section):
on api30 the platform negotiates TLSv1.3 by default and TLSv1/1.1 are disabled platform-side, so the
protocol accusations measure *narrowing* by the program; and `SSLContext.getSocketFactory` is NOT
added as an event because it is outside the oracle's alphabet — this change adds no accusation
surface the oracle does not name. No spec edit in this task.

## 5.4 Seed the AndroidKeyStore future issue

Create the GitHub issue (feature template, Full SDD default) for authorial AndroidKeyStore
specifications — the largest Android-specific gap, deliberately out of gh109's scope because it has
no expert rule. Body carries the three verified candidate accusations with their measured incidence:
`setBlockModes` containing `"ECB"` (10/32 APKs use `KeyGenParameterSpec$Builder`),
`setRandomizedEncryptionRequired(false)` (2/32), `setDigests` with MD5/SHA-1 correlated to
`PURPOSE_SIGN`; plus the constants evidence (`KeyProperties` exposes `BLOCK_MODE_ECB`, `DIGEST_MD5`,
`DIGEST_SHA1` on api30). Link it from gh109's proposal Out-of-scope line. Do not start it.

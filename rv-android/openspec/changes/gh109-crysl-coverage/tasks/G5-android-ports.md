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

## 5.2 BouncyCastle alias rows for the KeyStore service family

The set admits `BKS`/`BouncyCastle` store types but `alias_table.csv` has zero rows for the BC
KeyStore service. Add the BC family rows (the 3 verified missing ones) to
`data/jca_android/alias_table.csv` AND mirror them in `ConscryptAliasTable.java` —
`ConscryptAliasTableTest.java:30` enforces line-for-line equality, so the two move in one commit,
followed by the reactor build (JDK 21 prefix) + rvsec-core tests.

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

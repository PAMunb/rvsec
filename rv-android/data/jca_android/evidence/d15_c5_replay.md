# D-15 acceptance: the published corpus replayed through the re-anchored lists

**Task 11.10** · measured 2026-08-24 · oracle `RVSec-replication-package/tools/rules/`
(sha256 `d7bcc019…`, freeze item of `README.md`)

## What was measured, and how

Every distinct `... but found <value>` accusation of the published campaign
(`ase-journal/dataset/results/errors.csv`, 97,018 rows, of which 26,251 carry a `but found`
label) was extracted with its event count, and each value was replayed through the *live*
allow-list of its specification — read out of the `.mop` file itself, not restated here —
using `ConscryptAliasTable.matches(service, value, list)`, the same call the generated
monitors make. `CipherSpec` has no `.mop` list and was replayed through
`CipherTransformationUtil.isValid`, the class `CipherSpec.mop` now names.

This is a replay of values against lists, not a re-run of the campaign: it answers "would
this accusation still be made", which is exactly what the two-sided criterion of D-15 asks,
and it answers it without an emulator.

## Result

| spec | accused value | events | verdict now |
|---|---|---:|---|
| SSLContextSpec | `TLS` | 8,648 | **silent** |
| TrustManagerFactorySpec | *(empty)* | 8,371 | accused |
| MessageDigestSpec | `MD5` | 3,552 | **accused** |
| KeyStoreSpec | `AndroidKeyStore` | 2,005 | **silent** |
| MessageDigestSpec | `SHA-1` | 1,915 | **accused** |
| TrustManagerFactorySpec | `X509` | 643 | **silent** |
| MessageDigestSpec | `SHA1` | 424 | **accused** |
| SignatureSpec | *(empty)* | 234 | accused |
| MessageDigestSpec | *(empty)* | 156 | accused |
| CipherSpec | `RSA/ECB/OAEPWithSHA1AndMGF1Padding` | 109 | accused |
| SSLContextSpec | `SSL` | 103 | **accused** |
| SSLContextSpec | *(empty)* | 51 | accused |
| MacSpec | *(empty)* | 31 | accused |
| SignatureSpec | `SHA256WITHRSA` | 4 | **silent** |
| SignatureSpec | `NONEWITHRSA` | 4 | **accused** |
| MessageDigestSpec | `SHA` | 1 | **accused** |

## The criterion, both sides

**The detections return.** 5,892 `MessageDigestSpec` rows (3,552 `MD5` + 1,915 `SHA-1` +
424 `SHA1` + 1 `SHA`) are accused again; so are the 103 `SSL` and the 4 `NONEwithRSA`. Under
the api30 anchor every one of these was silent, because the api30 lists are provider
registries. `SHA1` and `SHA` are accused *through* the alias table, which resolves them to
`SHA-1`: an alias row whose canonical name the expert list rejects widens the accusation
rather than excusing it, which is the direction the flag recomputation of task 11.6 records.

**The platform artefacts stay silent.** `TLS` (8,648) through the one `platform-value` row
for `SSLContextSpec`; `AndroidKeyStore` (2,005) through the `KeyStoreSpec` platform values;
`X509` (643) through the alias row to `PKIX`, which is an expert entry; `SHA256WITHRSA` (4)
through case folding alone. Four rows, four different mechanisms, none of them a preference.

**Neither side, recorded as unchanged.** The 109 `RSA/ECB/OAEPWithSHA1AndMGF1Padding` stay
accused, as they were under the api30 anchor — that rule spells the padding
`OAEPwithSHA-1andMGF1Padding`, with the hyphen — and as they must under the expert anchor,
which carries no SHA-1 OAEP variant at all. D-10 counted these among the rows a re-anchoring
must keep silent; that was an error of its own bookkeeping, corrected in D-15 and in the
`behavioural` row of `divergence_record.csv`.

**Not in scope of this measurement.** The five *(empty)* rows (8,843 events) are the
`but found .` defect gh104 fixes by reading the bound object's getter instead of a monitor
field; they are unaffected by which oracle the list answers to.

## The case with no published number

`AES/ECB/PKCS5Padding` does not appear above, because the corpus's 109 `CipherSpec`
accusations all carry the OAEP spelling. It is nonetheless the sharpest loss the api30
anchor caused: `Api30CipherTransformationUtil` admits it, `CipherTransformationUtil` accuses
it, and ECB is the misuse the crypto-API literature reports first. Costing no published
number is precisely why it needed a trace of its own rather than a replay
(`data/gh104/traces/CipherSpec-d15-aes-ecb-pkcs5.txt`, task 11.9): a false negative that
moves no number is one that travels into the next campaign unwitnessed.

## Reproducing

```bash
export RVSEC_HOME=.../rvsec
# the value census of the published campaign
python3 - <<'PY'
import csv, re, collections
p="ase-journal/dataset/results/errors.csv"
c=collections.Counter()
for r in csv.DictReader(open(p)):
    m=re.search(r'but found (.*?)\.?$', r['message'].strip())
    if m: c[(r['spec'], m.group(1).strip())] += 1
for (s,v),n in c.most_common(): print(n, s, repr(v))
PY
# then replay each value through its live list with ConscryptAliasTable.matches
# (CipherSpec through CipherTransformationUtil.isValid)
```

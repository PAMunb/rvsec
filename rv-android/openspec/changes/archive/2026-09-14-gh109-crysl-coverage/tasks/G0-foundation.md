# G0 — Foundation

Sequential, one session. Everything else dispatches after this lands. Roots: `RV` = the rv-android
tree; `RE` = the sibling reactor (`/home/pedro/.../rvsec/rvsec` for JVM work); `SET` =
`RE/rvsec-mop/src/main/resources/jca_android`; `ORACLE` = `RVSec-replication-package/tools/rules`.
Java command lines always carry the JDK 21 prefix (`export JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem; export PATH=$JAVA_HOME/bin:$PATH`).

## 0.1 Oracle-defect divergence rows (design D-21)

Add narrative rows (empty hunk, per the recorder's narrative-row convention) to
`RV/data/jca_android/divergence_record.csv` via `scripts/gh104_divergence_record.py --refresh` + fill:

| Rule anchor | Defect (verified this session) | Evident intent the spec will transcribe |
|---|---|---|
| `Cipher.crysl:140-141` | `preparedOAEP` guarded by `mode(transformation) in {OAEPWith...}` — those literals are paddings by the rule's own `:107-110`; RSA modes are `{"", "ECB"}` (`:101`); antecedent unsatisfiable | `pad(transformation) in {...} => preparedOAEP[paramSpec]` (form of the correct neighbours `:138-139`) |
| `SSLEngine.crysl:12` | `EnableProtocol := cp1;` — label `cp1` undeclared (event on `:11` is `ep1`); parse-breaking | `EnableProtocol := ep1` |
| `KeyAgreement.crysl:31` | `GenSecretBuffer := gs1 \| g2;` — `g2` is a `getInstance` overload; `gs2` is meant (the same rule also carries the dead alias `GenSecret := gs3 \| GenSecretBuffer` at `:34`, used by no ORDER or CONSTRAINT — anomaly note, same row) | `gs1 \| gs2` |
| `DSAParameterSpec.crysl` / `DHParameterSpec.crysl` | `p >= 1^2048` is literally 1 | bit-length ≥ 2048 (`p.bitLength() >= 2048`), D-20.4 |
| `OAEPParameterSpec.crysl:8` | orphan object `java.lang.String alg` — anomaly note only, no transcription consequence | — |

Write every one of these rows with `kind = oracle-wart` — the vocabulary already exists (4 rows
today) — and with the **rule** in the record's `file` column (`tools/rules/Cipher.crysl`,
`tools/rules/SSLEngine.crysl`, …). The column already carries non-`.mop` paths, and this is what makes
`coverage_matrix.csv`'s `oracle_defect_row` a join derivable by enumeration instead of a judgement
typed by hand (D-21). None of these rows is a terminal state: the rule they belong to is transcribed
by evident intent and ends `covered`, carrying the row as its warrant.

The pinned oracle files stay byte-identical (`gh105_sole_oracle_gate.py` and the sha256 manifest
must not move). Done when `--check` exits 0 with the rows present.

## 0.2 Producer-spec template + conventions note

Write `RV/data/jca_android/NEW_SPEC_CONVENTIONS.md` (one page) fixing, for every G2–G4 task:

- **Naming**: `<Rule>Spec.mop`, spec parameter = the rule's SPEC class (ledger pairing is automatic,
  `gh105_expert_ledger.py:441-448`). Exception style (`KeySpec.mop` for rule `Key`) noted explicitly.
- **Structure**: events realize the rule's EVENTS with ctor/overload fusion per the existing fusion
  rules; automaton = the rule's ORDER; every value CONSTRAINT lands in the event body with an
  accuser on the violated branch (INV-INS-152 — the `IvParameterSpec` fusion form is the template)
  and the predicate write only on the conforming branch, at the ORDER acceptance point.
- **Codes**: `<RULE-UPPER>-CONSTR-NN` / `-ORDER-00` rows appended to `SET/codes.csv` by the spec's
  own task; `file_line` anchored at the emission line (the message gate checks bijection + anchor).
- **Predicates**: writes/reads through `PredicateStore` exactly as the gh105 substrate rules state;
  algorithm-valued writes pass `ConscryptAliasTable.canonical` (D-20.3, INV-INS-153).
- **Viability fiche**: each task re-confirms its classes/members in the API 30 `android.jar` by `unzip -l`
  (INV-INS-154) and states the event count (ceiling 17; every new spec is ≤5).
- **Records**: individual tasks touch ONLY their `.mop` + their `codes.csv` rows. The group's `X.R`
  task owns divergence rows (`new-file` kind), graph re-emit, ledger/alphabet re-emit.

## 0.3 `.rvm`-preserving generation fixture

Follow the documented procedure (`RV/tests/parity/test_gh105_predicate_gates.py:1836-1861`): copy the
set to scratch, run `javamop -d <out> -merge` so the `.rvm` files survive, refresh
`results/gh51_e2e_test/monitors`. This is what lets G-PARAM actually verify the new specs instead of
skipping. Done when G-PARAM runs with 0 skips over the current 24 (count re-pin happens in 6.1).

## 0.4 Coverage-matrix derivation (INV-INS-150)

New `RV/scripts/gh109_coverage_matrix.py` + `RV/tests/parity/test_gh109_coverage_matrix.py`:
enumerate `ORACLE/*.crysl` × `SET/*.mop` (pairing convention of 0.2; `NON_PAIRING_FILES` respected),
emit `RV/data/jca_android/coverage_matrix.csv` with columns
`rule, terminal_state, evidence, oracle_defect_row`. `terminal_state` has **three** values
(`covered` | `na-platform` | `na-value`); `oracle_defect_row` is derived by joining
`divergence_record.csv` on `kind = oracle-wart` with the rule path in its `file` column (0.1), and is
empty for a rule with no recorded defect. Fail when any rule has no state or two states.

Carry the definition in the script's docstring and in the CSV header comment, because it is the thing
a reader will get wrong: **`covered` is a verdict of pairing and adjudication, not of clause
completeness.** Measured, 15 of the 22 rules paired today have at least one clause with no verdict
surface. The depth of a transcription is measured by M0–M4 of the `rvsec-crysl` conformance component
and clause by clause by `constraint_table.csv` / `predicate_ledger.csv`, and this script MUST NOT
re-derive it — a second derivation would be a second translation of the oracle (D-19). Two adjudicated mappings are built in: `SecretKey → SecretKeySpec.mop` is `covered` (the file
realizes the rule's ENSURES; the `Destroy` tail is recorded platform-dead per INV-INS-137, so no
reachable trace yields a further verdict — `NON_PAIRING_FILES` governs specification pairing, not
coverage), and `HMACParameterSpec` is `na-platform` despite its `.mop` (INV-INS-155).
Terminal states for `Cookie`, `DSAGenParameterSpec`, `PasswordAuthentication`, `HMACParameterSpec`
land with their adjudication tasks (4.4, 5.1) — until then the test asserts only the landed tiers
(derive, never hardcode totals). Keep it small (P1): one script, one test, one CSV.

## 0.5 D-20 value-decision rows

Five narrative divergence rows citing design D-20 items 1–5 (PBE families admitted; AES_128/AES_256 ≡
AES; canonical predicate values; bit-length semantics; no accusation surface beyond the oracle —
`getSocketFactory` and AndroidKeyStore excluded). These are the rows the campaign's comparability
caveat will point at. Done when `--check` exits 0.

## 0.6 Documentation pass

Run `/rv-doc-code scripts/gh109_coverage_matrix.py` once 0.4 lands (WORKFLOW §9: new Python module).
Done when the script and its parity test carry their documented docstrings.

## 0.7 Predicate constants the new specifications need (`rvsec-core`)

Add, in one commit, the enum constants the G2–G4 specifications write to
`RE/rvsec-core/src/main/java/br/unb/cic/mop/Property.java`. From the ENSURES column of the G2/G3/G4
fiches, the set is: `PREPARED_RSA`, `PREPARED_DSA`, `PREPARED_EC`, `PREPARED_MGF1`, `PREPARED_OAEP`,
`PREPARED_ALG`, `GENERATED_MANAGER_FACTORY_PARAMETERS`, `GENERATED_CERT_PATH_PARAMETERS`,
`GENERATED_TRUST_ANCHOR`, `GENERATED_CERT`, `GENERATED_KEY_FACTORY`, `DIGESTED_INPUT_STREAM`,
`DIGESTED_OUTPUT_STREAM`, `GENERATED_SSL_PARAMETERS` — re-confirm the list against the fiches before
writing, and against what already exists (`PREPARED_DH`, `SPECCED_KEY`, `PREPARED_KEY_MATERIAL`,
`GENERATED_KEY_STORE`, `GENERATED_PUBLIC_KEY`, `RANDOMIZED`, `GENERATE_SSL_ENGINE` are already there;
note the existing spelling `GENERATE_SSL_ENGINE`, without the `D`).

Why this is one task in G0 and not one line in each spec task: the whole `PredicateStore` API is
enum-typed (`ensure`, `validate`, `validateAny`, `validateAbsent`, `negate` at
`PredicateStore.java:291-438`) and there is no string path, so every G2–G4 task would otherwise edit
this file — 24 parallel tasks co-editing a file that compiles, against the ownership rule of D-22.
Doing it once up front is what keeps "each spec is one new file, disjoint by construction" true.

The gh106 conformance component is unaffected: `PredicateIdioms.java:154` strips the `Property.`
qualifier by regex and holds no closed list of names. Each constant carries a javadoc in the house
style of the file (what the CrySL clause is, which rule ensures it, which reads it).

Done when the reactor builds (`mvn clean install -DskipMopAgent -DskipTests`, JDK 21 prefix) and the
`rvsec-core` tests are green.

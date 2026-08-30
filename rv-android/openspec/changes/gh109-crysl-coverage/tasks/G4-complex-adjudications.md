# G4 — Complex specs + adjudications (after G3)

The three remaining rules have oracle defects (recorded in 0.1) or multi-path ORDERs. Each task
transcribes the *evident intent*, citing its divergence row as warrant. Records in 4.R.

## 4.1 `SSLEngineSpec.mop`

- Rule: `SSLEngine.crysl`. Defect row from 0.1: `EnableProtocol := cp1` → transcribe as `ep1`
  (`setEnabledProtocols`).
- ORDER: `(EnableCipher, EnableProtocol) | (EnableProtocol, EnableCipher)` — both orders admitted;
  2 events.
- Constraints: protocols ∈ {TLSv1.2, TLSv1.3} + the two suite implications (23 suites for 1.2, 2 for
  1.3) — transcribe the sets literally; array-valued arguments follow the set's existing
  array-argument idiom (the store binds arrays whole).
- ENSURES `generatedSSLEngine[this]` — note `SSLContextSpec` also produces it; the ledger already
  models multi-producer predicates.
- Platform note (recorded, not a departure): on API 30 the platform enables TLSv1.2/1.3 by default;
  the accusation surface is programs that *narrow* to insecure values, which is exactly what the
  rule's constraints accuse. No platform-value row needed unless a default spelling collides.

## 4.2 `SSLParametersSpec.mop`

- ORDER: `(Con1, ((CipherSuite, SetProtocol) | (SetProtocol, CipherSuite))) | (Con2, SetProtocol) |
  Con3` — 5 events (3 constructor profiles + 2 setters), the set's first multi-constructor-profile
  automaton; keep one event per binding profile per the fusion rules.
- Constraints: same protocol/suite sets as 4.1.
- ENSURES `generatedSSLParameters[this]` (unread among the 49 — write it, ledger classifies).

## 4.3 `KeyAgreementSpec.mop`

- Defect row from 0.1: `GenSecretBuffer := gs1 | g2` → `gs1 | gs2`.
- ORDER: `Get, Init, DoPhase, GenSecretBuffer`; `gs3` exists only for `noCallTo[gs3]` — realize it
  as a FORBIDDEN event (the `getDefault` precedent), not as an automaton state.
- Constraints: algorithm ∈ {DH, DiffieHellman, ECDH}; the `noCallTo`.
- REQUIRES `randomized[random]`, `generatedPrivkey[privKey]`, `generatedPubkey[pubKey]` (producers:
  `SecureRandomSpec`, 3.4, `KeyPairSpec`) + 2 conditional implications (`preparedDH`/`preparedEC` —
  guarded reads); ENSURES `preparedKeyMaterial[sharedSecretBuffer]`.
- **9 events** (the FORBIDDEN `gs3` included), not the 5 this fiche projected. The rule's label
  `Init := i1 | i2 | i3 | i4` fuses four overloads that bind DIFFERENT arguments —
  `randomized[random]` is about two of them, the guarded `preparedDH`/`preparedEC` clauses about
  the other two — and `GenSecretBuffer` fuses a call that RETURNS the buffer with one that takes
  it as an ARGUMENT, which one event cannot bind. Fusing to the projected count would leave
  three clauses of the rule with no site at all; the precedent and the measurement are
  `AlgorithmParameterGeneratorSpec.mop:62-74`. Recorded in `divergence_record.csv`: the fiche is
  the plan, the rule is the oracle, and where they disagree the rule wins.
- Still the largest new automaton: write its trace pair individually (satisfy: full DH
  agreement; violate: `GenSecret` without `DoPhase`).

## 4.4 Adjudications (N/A terminal states — coverage matrix rows, no `.mop`)

| Rule | Terminal state | Evidence to record |
|---|---|---|
| `Cookie` | N/A-by-platform | `javax/servlet` = 0 entries in the API 30 `android.jar` (`unzip -l`) |
| `DSAGenParameterSpec` | N/A-by-platform | class absent from the API 30 `android.jar` (`unzip -l` = 0; present from API 35) |
| `PasswordAuthentication` | N/A-by-value (ratified, INV-INS-156) | class exists in the API 30 `android.jar`. Two legs, both verified: (a) both constraints (`neverTypeOf[password, String]`, `notHardCoded`) are static-analysis predicates the instrument cannot evaluate at run time; (b) `generatedPasswordAuthentication` has no consumer among the 49, so a producer-only spec would monitor without a verdict surface. The third leg once claimed — "the ORDER is unviolatable" — is **withdrawn**: `Con, (GetPassword \| GetUserName)*` refuses a `getPassword()` on an object whose construction went unobserved, exactly as every `ere : c1 …` of the set does. Record the adjudication row with both surviving legs AND with what the ORDER would still accuse, so the departure is measured rather than assumed away |

## 4.R — Group records pass

Same shape as 2.R/3.R + the three adjudication rows land in `coverage_matrix.csv` with their
evidence strings. After this pass every rule except `HMACParameterSpec` MUST have its terminal state
(48/49; 49/49 once 5.1 lands — G5 is unordered relative to G4). **[GEN]** monitor + `tests/parity`.

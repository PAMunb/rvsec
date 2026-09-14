# G1b — Consumer reads unblocked by the producers (after G2)

Design D-24. This group exists because closing a producer gap moves a ledger disposition and, by
itself, moves no verdict. Measured: of the eight predicates INV-INS-151 counts, `preparedKeyMaterial`
already has a live read (`SecretKeySpecSpec` `c1`/`c2`) and four more gain one from the new
specifications themselves (`preparedEC`, `preparedDH` from 4.3 and 3.1; `preparedAlg`, `preparedOAEP`
from 3.1). The remaining three — `preparedRSA`, `preparedDSA`, `generatedManagerFactoryParameters` —
would end this change written by a brand-new specification and read by nobody, which is the ground on
which D-19 adjudicates `PasswordAuthentication` N/A-by-value.

This is not new scope. Both consuming specifications recorded, in their own text, that the read was
closed *because the producer did not exist*, and named what would open it. G2 writes those producers.

**Ordering**: after G2 (`2.1`, `2.4`, `2.5`, `2.8`, `2.9` must have landed) and, for `1b.1`, after
`1.2` — R2 edits the same file. Records land once, in `1b.R`.

**Form of every read** (gh105 substrate, unchanged): read in the event body, never in a `condition()`;
three-valued verdict; an accuser on VIOLATED and a **separate `-NOBS-` code** on NOT_OBSERVED, so a
program whose parameter object was built outside the monitored set stays distinguishable from one that
violated the clause. Each task appends its own `codes.csv` rows; no task touches the records.

## 1b.1 `KeyPairGeneratorSpec.mop` — the four guarded reads

- Clauses: `KeyPairGenerator.crysl:35-38` — `algorithm in {"RSA"} => preparedRSA[params]`,
  `{"DSA"} => preparedDSA[params]`, `{"DiffieHellman","DH"} => preparedDH[params]`,
  `{"EC"} => preparedEC[params]`. Ledger rows #32, #33, #34, #35.
- Sites: `init3` (`:145-148`) and `init4` (`:150-153`), whose bodies are empty today and whose only
  purpose, per the file's own comment at `:107-110`, is to bind `params`.
- Guarded-clause form: read the algorithm off the receiver, then take the branch the algorithm
  selects; a `params` under an algorithm the four clauses do not name reaches no read. Four codes
  plus four NOBS codes, or one pair parameterised by the branch — decide at execution and record the
  choice, the message gate checks bijection either way.
- Producers, all landing in G2: `preparedRSA` ← 2.1, `preparedDSA` ← 2.4, `preparedDH` ← 2.5,
  `preparedEC` ← 2.2/2.3.
- The comment at `:107-144` is the warrant and must be rewritten, not deleted: it currently concludes
  `unmonitored-producer` for all four and says "*what would close it is a `.mop` for
  `DHParameterSpec`*". Replace the conclusion, keep the measurement (the Temurin 21 note on
  `DHGenParameterSpec` vs `DHParameterSpec` at the JCA call stays true and stays relevant).

## 1b.2 `KeyManagerFactorySpec.mop` — `generatedManagerFactoryParameters`

- Clause: `KeyManagerFactory.crysl:32` `generatedManagerFactoryParameters[params]`. Ledger row #29.
- Site: the fused `event init` at `:114-117`, which already binds `arg` as `Object` over both
  overloads and already discriminates by runtime type at `:122` (`arg == null || arg instanceof
  KeyStore`) for its `generatedKeyStore` read. The new read is the sibling branch,
  `arg instanceof ManagerFactoryParameters` — the file measures it at "three lines".
- Producers, both in G2: 2.8 (`KeyStoreBuilderParameters`) and 2.9
  (`CertPathTrustManagerParameters`).
- Codes: `KEYMANAGERFACTORY-CONSTR-NN` + `KEYMANAGERFACTORY-NOBS-NN`, in the form the neighbouring
  `generatedKeyStore` branch already uses.

## 1b.3 `TrustManagerFactorySpec.mop` — the twin

- Clause: `TrustManagerFactory.crysl` `generatedManagerFactoryParameters[params]`. Ledger row #56.
- Site: the `init` event whose `generatedKeyStore` branch sits at `:142-151`; same shape as 1b.2.
- The comment at `:130-141` carries the derivation that concluded `unmonitored-producer` and the
  sentence "*What it would buy is an accuser that can answer NOT_OBSERVED and nothing else*". Rewrite
  it to the post-G2 state: the producers exist, so the read can answer SATISFIED, and what remains
  NOT_OBSERVED is a measurable population rather than every program in the world.

## 1b.4 Record the read that cannot open

`Cipher.crysl:136` requires `preparedAlg[params, alg(transformation)]`. It stays closed, and the
reason is structural:

- The rule binds `params` (`java.security.AlgorithmParameters`) only in `i5`/`i7`
  (`init(encmode, key, params[, random])`, `Cipher.crysl:48,50`).
- `CipherSpec.mop`'s `i2` (`:172-175`) fuses every `init(int, Key, ..)` overload under
  `args(mode, key, ..)` and binds no third argument.
- Giving it one, or adding an event, collides with the ceiling: `CipherSpec` declares 17 events of the
  17 the generator admits (INV-INS-154), and the design forbids new Cipher events.

Record it as a deferral in the F7 form (`divergence_record.csv`, `kind` from the existing vocabulary),
naming the ceiling and the missing binding, so the ledger's disposition for that clause is a measured
impossibility and not an unexplained silence. `preparedAlg` still gains a real reader — 3.1
(`AlgorithmParameters.crysl:34`) — so the predicate itself is not left unread.

## 1b.R — Group records pass

1. `gh104_divergence_record.py --refresh` → hunk rows for the three edited files + the 1b.4 deferral
   row; `--check` exit 0.
2. `codes.csv` bijection + anchors for every new site (message gate).
3. `gh105_predicate_graph.py --emit` — three new read sites enter the graph; placement census re-pin.
4. Trace pairs, three per site: satisfy (parameter object built under observation), violate (built
   under a value the rule refuses), not-observed (built outside the monitored set). The third is the
   one the NOBS census of 7.3 reads.
5. Ledger re-emit + `--check`: `preparedRSA`, `preparedDSA` and `generatedManagerFactoryParameters`
   must show a consuming site; the `Cipher` `preparedAlg` clause must show its recorded impossibility.
6. **[GEN]** regenerate the monitor (inspect the artifact, INV-INS-145) + `tests/parity`.

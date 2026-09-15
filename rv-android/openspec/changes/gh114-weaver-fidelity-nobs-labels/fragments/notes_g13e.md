# G13e hand-over notes (task 13.7)

Files: `TrustManagerFactorySpec.mop`, `SignatureSpec.mop`, `SecureRandomSpec.mop`,
`KeyPairGeneratorSpec.mop`, `PBEKeySpecSpec.mop`, `SSLContextSpec.mop` (all under
`rvsec/rvsec-mop/src/main/resources/jca_android/`). Codes fragment: `codes_g13e.csv` (6 new rows
plus 60 moved rows: every existing row of the six specs moved).

## New codes

| Spec | Code | Anchor | Label |
|---|---|---|---|
| TrustManagerFactorySpec | TRUSTMANAGERFACTORY-ORDER-02 | TrustManagerFactorySpec.mop:297 | creation-refused |
| SignatureSpec | SIGNATURE-ORDER-02 | SignatureSpec.mop:326 | creation-refused |
| SecureRandomSpec | SECURERANDOM-ORDER-02 | SecureRandomSpec.mop:397 | creation-refused |
| KeyPairGeneratorSpec | KEYPAIRGENERATOR-ORDER-02 | KeyPairGeneratorSpec.mop:390 | creation-refused |
| PBEKeySpecSpec | PBEKEYSPEC-ORDER-02 | PBEKeySpecSpec.mop:235 | creation-refused |
| SSLContextSpec | SSLCONTEXT-ORDER-02 | SSLContextSpec.mop:386 | creation-refused |

`-ORDER-02` was the next free number in all six (each had only `-00` and `-01`). Every new branch
sits between the `creation-unobserved` branch and the `sequence` branch, with
`ErrorType.InvalidSequenceOfMethodCalls` and
`msg='the observed call sequence is not one <Spec> accepts, after a creation the specification refused'`.

## Hunks and divergence-record kind

All hunks are kind `message` (twin events, creation fields, handler branches, and comments that
describe them). None touches the predicate store, so `predicate_graph.csv` and the census pins do
not move.

- **TrustManagerFactorySpec** (`@@` new-file lines): `44` field comment names `g3`; `49-56`
  `creationRefused` field; `108-123` new event `g3`; `252-253` state-index comment of `gtm1`
  (row `{5, 5, 3, 5, 5, 5}`, state 3); `271-273` `g3 -> refused` and state `refused [ ]`;
  `289-290` `@fail` comment; `296-299` `creation-refused` branch; `311` state-index comment of
  `init` (row `{5, 2, 5, 5, 5, 5}`, `nextstate == 2`).
- **SignatureSpec**: `60-61` field comment names `g3`; `64-71` `creationRefused` field; `118-134`
  new event `g3`; `249-250` state-index comment (`s1`/`s2` land in state 3, match category
  `nextstate == 3 || nextstate == 4`); `318` `ere`; `325-328` `creation-refused` branch.
- **SecureRandomSpec**: `40-46` field; `168` and `187` `creationRefused = true;` in `g4`/`g5`;
  `396-399` branch.
- **KeyPairGeneratorSpec**: `54-61` field; `159` and `196` in `g3`/`g4`; `389-392` branch.
- **PBEKeySpecSpec**: `25-31` field; `64` and `73` in `f1`/`f2`; `222-225` residue comment now
  names PBEKEYSPEC-ORDER-02 (`creation-refused`) instead of PBEKEYSPEC-ORDER-00; `234-237` branch.
- **SSLContextSpec**: `68-73` field; `124` cross-reference `PBEKeySpecSpec.mop:209-216` ->
  `:218-226` (the residue paragraph moved); `130-132` residue comment names SSLCONTEXT-ORDER-02
  (`creation-refused`) instead of SSLCONTEXT-ORDER-00; `141-143` `getDefault` comment (sets both
  fields, reported under `creation-refused`); `147` `creationRefused = true;`; `378-379` `@fail`
  comment; `385-388` branch.

## New events

- `TrustManagerFactorySpec.g3`: `after(String alg) returning(TrustManagerFactory mf):
  call(public static TrustManagerFactory TrustManagerFactory.getInstance(String, ..)) &&
  args(alg, *) && condition(!ConscryptAliasTable.matches("TrustManagerFactory", alg, algorithms))`,
  body `creationObserved = true; creationRefused = true;`.
- `SignatureSpec.g3`: `after(String alg, Object provider) returning(Signature s):
  call(public static Signature Signature.getInstance(String, Object+)) && args(alg, provider) &&
  condition(!ConscryptAliasTable.matches("Signature", alg, algorithms))`, same body.

`g3` was the next free `g<n>` as an event in both files.

## Event counts (ceiling 17)

TrustManagerFactorySpec 5 (was 4), SignatureSpec 12 (was 11), SecureRandomSpec 14,
KeyPairGeneratorSpec 11, PBEKeySpecSpec 4, SSLContextSpec 5.

## Automata

- TrustManagerFactorySpec, before: `start [ g1 -> waitingInit  g2 -> waitingInit ]`.
  After: `start [ g1 -> waitingInit  g2 -> waitingInit  g3 -> refused ]  refused [ ]`. Aliases
  unchanged (`match1 = final`, `match2 = taken`). Generated rows: `g3 = {4, 5, 5, 5, 5, 5}`, and
  every event is `5` (fail) at state 4, so the first use after `g3` fails.
- SignatureSpec, before: `ere: (g1 | g2) ( ((i1 | i2)+ (update+ (s1 | s2)+)+)+ | ((i3 | i4)+ (update* (v1 | v2)+)+)+ )`.
  After: `ere: g3* (g1 | g2) ( … unchanged … )`. Generated row `g3 = {0, 8, …}`: minimisation
  folds the prefix into the start state, which is a self-loop on `g3` where every use is `8`
  (fail).
- The other four automata are unchanged.

## Verification

- Monitor generation from a copy of the whole set (G13d's files at their working-tree state
  included): all 47 specifications generated, `MultiSpec_1RuntimeMonitor.java` generated, pipeline
  completed. `--summary` then crashes with `Unexpected Error: 'int' object is not subscriptable`
  and exit 1, after the generation succeeded; a second run over the six final files without
  `--summary` exits 0. Nothing generated landed in the real `jca_android/` directory.
- `scripts/gh104_message_gate.py` over a scratch copy of the set with `codes.csv` merged with this
  fragment: no finding for the six specs (code-anchor, bijection, label vocabulary). The remaining
  findings are G13d's files, whose fragment was not merged.

## Traces (not edited)

Comments that state the label `sequence` for a refused or forbidden creation of these files:

- `data/gh104/traces/SSLContextSpec-getdefault-engine.txt:6-7` — SSLCONTEXT-ORDER-00, label
  `sequence`; now SSLCONTEXT-ORDER-02, `creation-refused`. Its comment also cites
  `PBEKeySpecSpec.mop:183-189`, which is the residue paragraph at `:218-226`.
- `data/gh104/traces/PBEKeySpecSpec-forbidden-then-clear.txt:5-6` — PBEKEYSPEC-ORDER-00, label
  `sequence`; now PBEKEYSPEC-ORDER-02, `creation-refused`.

Traces whose ordering code changes although the comment names no label:

- `KeyPairGeneratorSpec-rejected-algorithm.txt` and
  `KeyPairGeneratorSpec-rejected-algorithm-provider.txt`: `g3`/`g4` then `initialize(256)` (via
  `initError`) fails and, after the reset, `generateKeyPair()` fails again; both failures are
  now KEYPAIRGENERATOR-ORDER-02 instead of -00. The comments say "the `ere` still fails".

No existing trace requests a refused algorithm through the two-argument `getInstance` of
`TrustManagerFactorySpec` or `SignatureSpec`, and no `SecureRandomSpec` trace uses a refused
algorithm followed by a use.

## Open points

1. **Name collision in historical comments.** `TrustManagerFactorySpec.mop:62-94` and
   `SignatureSpec.mop:72-95` describe a removed "negated twin `g3`" over the one-argument
   `getInstance` (it "named no state", "`g3`'s body accused nothing"). The new `g3` is a different
   event with a state. The paragraphs were not rewritten (outside this task); a reader can confuse
   the two.
2. **State-index comments.** The `TrustManagerFactorySpec` comments quoting generated rows were
   already wrong at HEAD (they said `gtm1 = {4, 2, 4, 4, 4}` and `init = {4, 4, 4, 1, 4}`; HEAD
   generates `{4, 3, 4, 4, 4}` and `{4, 4, 1, 4, 4}`). They now quote the rows the edited file
   generates. `SignatureSpec`'s `s1`/`s2` moved from state 1 to state 3 with the prefix; its
   comment was updated. The `v1`/`v2` "state 4" comment still holds.
3. **One-argument route of TrustManagerFactorySpec and SignatureSpec.** `g1` accepts every
   algorithm and does not set `creationRefused`: an object whose refused algorithm came through
   the one-argument `getInstance` follows the automaton (its algorithm is accused in the `init`
   bodies) and any later ordering failure reads `sequence`, while the same algorithm through the
   two-argument overload fails at its first use and reads `creation-refused`; apart from the code,
   that route reports what it reported without the twin. This follows D7 as written; it was not
   settled whether that asymmetry is intended.
4. **`SSLContext.getDefault()` returns the platform default context, which a program can replace
   with `SSLContext.setDefault(ctx)`.** For a context created by `g1`/`g2` and then installed as
   default, a later `getDefault()` sets `creationRefused` on a monitor that saw an admitted
   creation, and every later failure of that monitor reads `creation-refused`. Not measured.
5. **`order_alphabet_map.csv` and `order_alphabet_map_expert.csv`** have no row for
   `TrustManagerFactorySpec.g3` or `SignatureSpec.g3`. They need `order-unmapped` rows like
   `KeyPairGeneratorSpec.g4` (erasing `g3` leaves the rule's `Gets`; in the `fsm`, `refused` is a
   dead non-accepting state).
6. **Line anchors outside `codes.csv`.** `data/jca_android/*.csv` hold 30 `<File>.mop:<line>`
   anchors into these six files (KeyPairGeneratorSpec 8, PBEKeySpecSpec 7, TrustManagerFactorySpec
   5, SignatureSpec 4, SSLContextSpec 4, SecureRandomSpec 2), and
   `X509EncodedKeySpecSpec.mop:106` cites `PBEKeySpecSpec.mop:173` for the `SPECCED_KEY` write,
   which is now at `:182`. None of these was edited here.
7. `KeyPairGeneratorSpec.mop:146-153` (the residue paragraph over `g3`) says the `ere` still fails
   after a rejected algorithm, and names no code; it was left unchanged.

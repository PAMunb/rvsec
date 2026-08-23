"""The predicate-wiring gates of gh105, and the reader they are all built on.

The `jca_android` set is being wired: the CrySL predicates its rules ensure and
require stop being decoration and become links a gate can check. Everything here
answers to one reader (`scripts/gh105_predicate_graph.py`), so the reader is
tested first and on its own -- a defect there does not produce a wrong gate
verdict, it produces a wrong verdict on every gate at once.

Two properties of that reader carry the weight, and both are tested against the
cases that motivated them rather than against a happy path:

* **Neutralisation.** Every accusing event in these files carries an English
  message that names its own predicate and code. A reader that scans raw text
  finds sites inside those messages, and the sites it invents are exactly the
  ones nobody would think to look for.
* **The `Property.` discriminator.** `KeyPairGeneratorSpec` declares
  `private boolean validate(int keySize)` and calls it from three conditions;
  several specifications call `remove` on a collection. Neither is a predicate
  site, and only the literal `Property.` first argument tells them apart.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import gh105_order_gate  # noqa: E402
import gh105_param_gate  # noqa: E402
from gh105_predicate_graph import (  # noqa: E402
    COLUMNS,
    SPECIFICATION_SETS,
    SetReport,
    analyze_set,
    build_rows,
    carry_judgments,
    gate_acc,
    gate_junction_rules,
    gate_placement,
    gate_pred2,
    neutralize,
    read_graph,
    read_mop,
    run_gates,
)


def _rvsec_home() -> Path:
    home = os.environ.get("RVSEC_HOME")
    if not home or not (Path(home) / "rvsec/rvsec-mop/src/main/resources/jca").is_dir():
        pytest.skip("RVSEC_HOME not set or the sibling Java reactor is absent")
    return Path(home)


def _write(tmp_path: Path, body: str, name: str = "FixtureSpec.mop") -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


# --------------------------------------------------------------- neutralisation


def test_neutralisation_preserves_every_offset():
    """Offsets survive so a site can be reported at its real line.

    Reporting is the whole point of the reader, and a reader that finds the right
    site at the wrong line sends its reader to the wrong file.
    """
    source = 'a // comment\nb /* two\nlines */ c\nd "text" e\n'
    neutral = neutralize(source)
    assert len(neutral) == len(source)
    assert neutral.count("\n") == source.count("\n")
    assert neutral.splitlines()[0].startswith("a ")


@pytest.mark.parametrize(
    "case,source",
    [
        (
            "line comment",
            "// ExecutionContext.instance().validate(Property.RANDOMIZED, x)\n",
        ),
        (
            "block comment",
            "/* ExecutionContext.instance().validate(Property.RANDOMIZED, x) */\n",
        ),
        (
            "accusation message",
            '"obj=Cipher msg=ExecutionContext.instance().validate(Property.RANDOMIZED, iv)"\n',
        ),
        ("char literal", "char quote = '\"';\n"),
        ("escaped quote inside a string", '"he said \\"Property.RANDOMIZED\\" once"\n'),
    ],
)
def test_neutralisation_blanks_every_form_that_can_hide_a_false_site(case, source):
    assert "Property." not in neutralize(source), case


def test_a_site_inside_an_accusation_message_is_not_read_as_a_site(tmp_path):
    """The live shape of the problem, not a synthetic one.

    Every accusing event of the set writes a message that quotes the predicate it
    is accusing about. Counting those as sites would inflate the graph by roughly
    one row per accuser, and each invented row would look entirely plausible.
    """
    path = _write(
        tmp_path,
        """
FixtureSpec(Cipher c) {
    event c1 after(byte[] iv): call(public Cipher.new(byte[])) && args(iv) {
        ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsatisfiedConstraint,
            "FixtureSpec", "" + __LOC,
            "msg='ExecutionContext.instance().validate(Property.RANDOMIZED, iv) failed'"));
    }
    ere : c1
}
""",
    )
    assert read_mop(path).sites == []


# ------------------------------------------------------------- the discriminator


def test_a_helper_named_validate_is_not_a_predicate_read(tmp_path):
    """`KeyPairGeneratorSpec` is the live case: a private `validate(int)`.

    It is called from three conditions. Without the `Property.` anchor those
    three calls become three predicate reads of an unnamed predicate, and the
    closure gate then demands a producer for something that was never a
    predicate.
    """
    path = _write(
        tmp_path,
        """
FixtureSpec(KeyPairGenerator kpg) {
    private boolean validate(int keySize) { return keySize >= 2048; }

    event init before(int keySize): call(public void KeyPairGenerator.initialize(int))
      && args(keySize) && condition(validate(keySize)) { }
    ere : init
}
""",
    )
    assert read_mop(path).sites == []


def test_a_collection_remove_is_not_a_predicate_removal(tmp_path):
    path = _write(
        tmp_path,
        """
FixtureSpec(Cipher c) {
    List<String> seen = new ArrayList<>();
    event c1 after(String alg): call(public Cipher.new(String)) && args(alg) {
        seen.remove(alg);
    }
    ere : c1
}
""",
    )
    assert read_mop(path).sites == []


# ---------------------------------------------------------------- attribution


def test_a_read_in_a_condition_and_a_write_in_a_body_are_told_apart(tmp_path):
    """Placement is the invariant, so placement is what the reader must resolve.

    `condition(...)` compiles to a boolean guard: a false read there suppresses
    the transition and turns an unobserved predicate into a wrong ordering
    accusation. The same call in the body accuses about what it actually saw.
    Nothing but position distinguishes them in the source.
    """
    path = _write(
        tmp_path,
        """
FixtureSpec(Cipher c) {
    event c1 after(byte[] iv) returning(Cipher c):
      call(public Cipher.new(byte[])) && args(iv) &&
      condition(ExecutionContext.instance().validate(Property.RANDOMIZED, iv)) {
        ExecutionContext.instance().setProperty(Property.PREPARED_IV, c);
    }
    ere : c1
    @match {
        ExecutionContext.instance().setObjectAsInAcceptingState(c);
    }
}
""",
    )
    kinds = {
        (site.operation, site.site_kind, site.owner) for site in read_mop(path).sites
    }
    assert kinds == {
        ("read", "condition", "c1"),
        ("write", "body", "c1"),
        ("accepting-state", "@match", "match"),
    }


def test_an_alias_is_resolved_to_the_state_it_names(tmp_path):
    """`alias match1 = init` renames a handler, and five specifications use it.

    A handler reached through an alias is still a handler; a reader that did not
    resolve the alias would attribute its sites to nothing at all.
    """
    path = _write(
        tmp_path,
        """
FixtureSpec(SecureRandom sr) {
    event c1 after() returning(SecureRandom r): call(public SecureRandom.new()) { }
    fsm : start [ c1 -> init ] init [ ]
    alias match1 = init
    @match1 {
        ExecutionContext.instance().setProperty(Property.RANDOMIZED, sr);
    }
}
""",
    )
    source = read_mop(path)
    assert source.aliases == {"match1": "init"}
    assert [(site.owner, site.site_kind) for site in source.sites] == [
        ("match1", "@match1")
    ]


def test_the_declared_type_of_a_bound_symbol_is_recovered(tmp_path):
    """The tracked-type rule needs the declared type, not the runtime one.

    Only positions declared `String`, `int` or `Integer` are compared by value;
    everything else is compared by identity. The distinction is decided here, in
    the source, and an event parameter shadows a field of the same name exactly
    as it would for the compiler.
    """
    path = _write(
        tmp_path,
        """
FixtureSpec(Cipher c) {
    String transformation;
    event c1 after(byte[] transformation, int len): call(public Cipher.new(byte[], int))
      && args(transformation, len) {
        ExecutionContext.instance().setProperty(Property.RANDOMIZED, transformation);
    }
    ere : c1
}
""",
    )
    source = read_mop(path)
    assert source.fields["transformation"] == "String"
    assert source.declared_type("c1", "transformation") == "byte[]"
    assert source.declared_type("c1", "len") == "int"
    assert source.declared_type("<spec-body>", "transformation") == "String"


def test_arguments_are_split_on_top_level_commas_only(tmp_path):
    """A splitter argument is one argument, however many commas it contains.

    The oracle's `part(0,"/",transformation)` becomes a `split` call in Java, and
    a naive comma split would read one argument as three -- reporting arity 4 for
    a binary clause.
    """
    path = _write(
        tmp_path,
        """
FixtureSpec(Cipher c) {
    event i2 before(Key key, String transformation):
      call(public void Cipher.init(int, Key)) && args(key) {
        PredicateStore.instance().validate(Property.GENERATED_KEY, key,
            transformation.split("/")[0]);
    }
    ere : i2
}
""",
    )
    site = read_mop(path).sites[0]
    assert site.operation == "read"
    assert site.substrate == "PredicateStore"
    assert site.arity == 2
    assert site.arguments[0] == "key"
    assert site.arguments[1].startswith("transformation.split(")


def test_a_negated_read_in_a_condition_is_recorded_as_negated_in_the_source(tmp_path):
    """The accusing twin of a guard is written `!validate(...)`.

    That `!` is not the clause's polarity -- it is the branch that accuses -- and
    the twin fusions of this change are found by pairing a guard with the negated
    read that shares its pointcut. Losing the sign loses the pairing.
    """
    path = _write(
        tmp_path,
        """
FixtureSpec(IvParameterSpec s) {
    event c3 after(byte[] iv) returning(IvParameterSpec s):
      call(public IvParameterSpec.new(byte[])) && args(iv) &&
      condition(!ExecutionContext.instance().validate(Property.RANDOMIZED, iv)) { }
    ere : c3
}
""",
    )
    assert read_mop(path).sites[0].source_negated is True


# ----------------------------------------------------------- skip, never crash


def test_an_unbalanced_file_is_reported_and_not_half_read(tmp_path):
    """The frozen `jca/SecretKeySpecSpec.mop` carries a stray `)` after `c1`.

    It is frozen, so it is not repaired. What matters is that a reader meeting it
    says so instead of walking off the end of a region and attributing the rest of
    the file to nothing -- the gates' skip-and-count contract has no way to
    express a file that was read wrong, only one that was not read.
    """
    path = _write(
        tmp_path,
        """
FixtureSpec(SecretKeySpec s) {
    event c1 after(byte[] km) returning(SecretKeySpec s):
      call(public SecretKeySpec.new(byte[])) && args(km) &&
      condition(ExecutionContext.instance().validate(Property.RANDOMIZED, km))
    ) { }
    ere : c1
}
""",
    )
    source = read_mop(path)
    assert "unbalanced parenthesis" in source.parse_error
    assert source.has_specification is False
    assert source.sites == []


def test_a_file_with_no_specification_block_reads_as_empty_rather_than_failing(
    tmp_path,
):
    """17 files of `generic_new` declare events and nothing else.

    They are not broken and they are not predicate-free by accident; they are a
    different kind of file. Reading one must produce an empty source, so a gate
    can skip it declaredly instead of crashing on it.
    """
    path = _write(tmp_path, "package mop;\n\nimport java.util.List;\n")
    source = read_mop(path)
    assert source.parse_error == ""
    assert source.has_specification is False
    assert source.sites == []


# ------------------------------------------------------------------ the alphabet


def test_an_fsm_alphabet_is_a_multiset_over_its_transitions(tmp_path):
    """An event named once per state is not the same as an event named once.

    The absorptions of this change add a benign self-loop at every state where a
    call is legal, and the occurrence count is the only thing that distinguishes
    that from a loop added at one state and forgotten at the rest.
    """
    path = _write(
        tmp_path,
        """
FixtureSpec(Cipher c) {
    event g1 after(): call(public Cipher.new()) { }
    event i1 after(): call(public void Cipher.init()) { }
    event f1 after(): call(public void Cipher.doFinal()) { }
    fsm :
      start [ g1 -> s1 ]
      s1 [ i1 -> s2  f1 -> s2 ]
      s2 [ f1 -> s2 ]
}
""",
    )
    alphabet = read_mop(path).alphabet
    assert alphabet.kind == "fsm"
    assert alphabet.states == ("start", "s1", "s2")
    assert alphabet.occurrences("f1") == 2
    assert alphabet.occurrences("i1") == 1
    assert alphabet.orphans == ()
    assert alphabet.undeclared == ()


def test_an_ere_alphabet_ignores_the_empty_word(tmp_path):
    """`epsilon` is the one reserved identifier an `ere` uses.

    `generic/ListIterator_Set.mop` names it inside an alternation. Reading it as
    an event would report an undeclared symbol in a file that has none.
    """
    path = _write(
        tmp_path,
        """
FixtureSpec(List l) {
    event add after(): call(public boolean List.add(Object)) { }
    event next after(): call(public Object Iterator.next()) { }
    ere : add* ((next)+ (add | epsilon))*
}
""",
    )
    alphabet = read_mop(path).alphabet
    assert alphabet.kind == "ere"
    assert alphabet.undeclared == ()
    assert set(alphabet.referenced) == {"add", "next"}


def test_the_derived_set_carries_exactly_the_seventeen_orphan_accusers():
    """The census this change's first group is scoped against, re-derived.

    An orphan accuser is an event that is woven and fires but that the automaton
    never names: it reports a violation for a call the specification's own
    ordering does not model. Seventeen of them sustain at most 56.1 % of the
    published `InvalidSequenceOfMethodCalls` category -- a ceiling, not an
    attribution -- which is why they are the first thing this change absorbs.

    The list is asserted by name because the group has one task per file, and a
    census that only counted would not say which file moved. It moves as Group 3
    lands, one file per commit:

    * task 3.1 removed `SecureRandomSpec` whole -- `c3` and `setSeed3` fused into
      their siblings, `g4` absorbed into the automaton -- taking the count to 14.
    * task 3.2 fused `TrustManagerFactorySpec.g3` into `g1`, taking it to 13. The
      census had listed `g3` as an absorption until that task read its body: it
      only rebinds `currentAlgorithmInstance`, which makes it a negated twin and
      not a report of its own (design.md census, corrected 2026-08-20).
    * task 3.3 fused both `IvParameterSpec` twins -- `c3` into `c1` and `c4` into
      `c2` -- taking it to 11 and removing the file from this list entirely.
    * task 3.4 did the same for `SecretKeySpecSpec`, taking it to 9.
    * task 3.5 took `PBEKeySpecSpec` whole, taking it to 4: `err1`, `err2` and
      `err3` fused into `c1` on one arrow, and `f1` and `f2` absorbed into the
      Kleene groups of the `ere` because each accuses a FORBIDDEN constructor.
    * task 3.6 took the last four, and the census is empty. `PBEParameterSpecSpec
      .c3`, `SSLContextSpec.unsafe_protocol` and `SignatureSpec.g3` were fused
      into their siblings; `KeyPairGeneratorSpec.initError` was absorbed into the
      `Inits` group of the `ere`, where the api30 rule already puts the call it
      matches -- `i3: initialize(keySize)` is an `Inits` event whatever size it is
      handed, and the bound is a CONSTRAINTS clause.
    """
    home = _rvsec_home()
    root = home / "rvsec/rvsec-mop/src/main/resources/jca_android"

    found: dict[str, tuple[str, ...]] = {}
    for path in sorted(root.glob("*.mop")):
        source = read_mop(path)
        assert source.parse_error == "", f"{path.name}: {source.parse_error}"
        if source.alphabet.orphans:
            found[path.stem] = source.alphabet.orphans
        assert (
            source.alphabet.undeclared == ()
        ), f"{path.name} names an undeclared event"

    assert found == {}
    assert sum(len(events) for events in found.values()) == 0


def test_the_frozen_gcm_specification_is_read_in_both_broken_directions():
    """`GCMParameterSpecSpec` declares `c1` twice and its `ere` names `c2`.

    Both defects are real, both are in a frozen set, and neither is repaired: they
    are the standing negative fixture for the two directions of the orphan check.
    A gate that could only see events declared-and-unused would report this file
    as clean, which is the failure this fixture exists to make impossible.
    """
    home = _rvsec_home()
    root = home / "rvsec/rvsec-mop/src/main/resources"

    for frozen_set in ("jca", "jca_android_bug_predicate"):
        source = read_mop(root / frozen_set / "GCMParameterSpecSpec.mop")
        assert source.alphabet.duplicates == ("c1",), frozen_set
        assert source.alphabet.undeclared == ("c2",), frozen_set


def test_the_seventeen_event_only_files_declare_no_automaton_at_all():
    """`generic_new` holds 17 files with events and no `fsm`/`ere`.

    They are not broken. A gate that judged their events as orphans would report
    27 findings in a set that has none, and a gate that silently passed them would
    be green by vacuity. Both are wrong; the contract is to skip them and say so.
    """
    home = _rvsec_home()
    root = home / "rvsec/rvsec-mop/src/main/resources/generic_new"

    without = [
        path.name
        for path in sorted(root.glob("*.mop"))
        if not read_mop(path).alphabet.has_automaton
    ]
    assert len(without) == 17, without


def test_a_creation_modifier_is_read_off_the_declaration(tmp_path):
    """`creation event x` is a different declaration, and the difference is gated.

    A junction specification whose *consumer* event is declared `creation` starts
    a monitor at the consuming call, with the producer's mark never observed, and
    accuses the conforming trace. The pilot measured exactly that, which is why
    the modifier is read rather than skipped over.
    """
    path = _write(
        tmp_path,
        """
FixtureSpec(Collection c) {
    creation event enter before(Collection t): call(public boolean Collection.addAll(Collection))
      && target(t) { }
    event leave after(Collection t): call(public boolean Collection.addAll(Collection))
      && target(t) { }
    ere : (enter leave)*
}
""",
    )
    source = read_mop(path)
    assert source.creation_events == {"enter"}
    assert source.alphabet.undeclared == ()


# ------------------------------------------------- the reader against the tree


def test_the_reader_reproduces_the_measured_census_of_the_derived_set():
    """The counts this whole change is scoped against, re-derived from source.

    The change was scoped against 27 reads, every one of them inside a
    `condition`; 49 writes; 25 accepting-state calls; 9 removals. They are
    asserted here rather than trusted because every later gate subtracts from
    them, and a census that drifts silently turns each of those subtractions into
    a different number than the one that was planned.

    The numbers move as the migration lands. When they do, this test is what says
    which group moved them:

    * task 3.1 fused the two `SecureRandom` twin pairs. Four condition reads on
      `RANDOMIZED` leave with the guards, one comes back in the fused
      `setSeed2` body, and the total reads go 27 -> 24 with 23 still guards.
    * task 3.3 fused the two `IvParameterSpec` twin pairs. The two twins' guards
      leave with them and the two survivors read in their bodies, so the reads go
      24 -> 22, of which 19 are still guards and 3 are body reads.
    * task 3.4 fused the two `SecretKeySpecSpec` pairs. Only the two-argument twin
      carried a read, so the reads go 22 -> 21, of which 17 are still guards --
      `c1`'s moved into its body with the accusation -- and 4 are body reads.
    * task 3.5 fused the three `PBEKeySpecSpec` twins into one arrow. Two of the
      file's four reads were the twins' guards and leave with them; `c1`'s two move
      into its body, so the reads go 21 -> 19, of which 13 are still guards and 6
      are body reads.
    * task 3.6 fused `PBEParameterSpecSpec.c3` into `c1`. The twin's guard leaves
      with it and `c1`'s moves into its body, so the reads go 19 -> 18, of which
      11 are still guards and 7 are body reads. The other three files of the task
      carry no predicate read: their guards read an algorithm allow-list, and a
      key size is not a predicate.
    * task 4.1 migrated `CipherSpec`, the first file of the Group-4 pass. Its three
      key-origin probes leave `condition(...)` for the body, so the reads stay at 18
      and the guards go 11 -> 8 with 10 body reads. The writes go 49 -> 39: eleven
      `ENCRYPTED` body writes become the two acceptance-point writes of `@match1`
      and `@match2` -- one write site per acceptance point, which is the shape the
      rule's three clauses have -- and the twelfth, `WRAPPED_KEY`, is deleted
      because api30 names `wrap` in no ENSURES clause and no set reads the mark.
      The accepting-state calls go 25 -> 24 (INV-INS-147).
    * task 4.4 migrated `IvParameterSpec`. It moves no read and no write: task 3.3
      had already brought both reads into their bodies when it fused the twins, and
      `preparedIV[this]` is unqualified, so the rule's acceptance point is the
      accepting state and the write was already in `@match`. What the file pass does
      is change the substrate under all three sites and split the boolean read into
      three verdicts, which the counts here cannot see. The one number it moves is
      the accepting-state calls, 24 -> 23 (INV-INS-147).
    * task 4.5 migrated `SecureRandomSpec`. The reads stay at 18 -- `setSeed2`'s was
      already a body read after task 3.1 fused the twins -- and the writes go
      39 -> 38: five body writes become two, because `genSeed` and `next2` stage
      their arrays for the new `@match2` handler at `end` (the acceptance point of
      the rule's two unqualified `randomized` clauses), while the `ints` write is
      deleted for the reason `WRAPPED_KEY` was at 4.1 -- api30 declares no stream
      event, so the site translated no clause. `next1` and `next3` keep their body
      writes with a recorded reason, which is what INV-INS-134 asks of a write left
      off the acceptance point; task 5.5 owns them. The accepting-state calls go
      23 -> 22 (INV-INS-147).
    * task 4.6 migrated `PBEKeySpecSpec`. The reads stay at 18 and the guards at 8 --
      task 3.5 had already brought both of `c1`'s reads into its body when it fused the
      three twins -- and the writes stay at 38, because the one write does not move:
      api30 qualifies the clause `speccedKey[this, keylength] after c1`, the file states
      its automaton as an `ere` whose only alias is `match` over the accepting states,
      and here that is the state after `c2`, where the rule negates the predicate. The
      write keeps its body placement with the reason recorded, and rises to the rule's
      arity. Two numbers do move: the accepting-state calls go 22 -> 21, because the
      `@match` handler held nothing else and goes with them (INV-INS-147), and the nine
      removals stay nine while one of them changes species -- the `clearPassword`
      withdrawal is the set's one real `NEGATES` translation and reaches the new store
      here rather than at task 6.5, so that the predicate is not ensured on one
      substrate and withdrawn from the other in between.
    * task 4.7 migrated `PBEParameterSpecSpec`. The guards go 8 -> 7: `c2`'s read is the
      first to leave `condition(...)` because the migration asked it to since task 4.1,
      and it left with the CONSTRAINTS check that shared the guard with it, measured in
      the generated monitor to suppress the transition ahead of `handleEvent`. The reads
      stay at 18 and the writes at 38 -- the `ENSURES` write does not move, because
      api30 states `preparedPBE[this]` with no `after L` and the acceptance point of an
      `ere` is what `@match` names. The accepting-state calls go 21 -> 20, and the
      predicate becomes the first of the nine `ENSURES`-only dead ends to carry its
      deliberate-omission record (INV-INS-137), which is what closes its G-PRED2 row.
    * task 4.8 migrated `GCMParameterSpecSpec`. The guards go 7 -> 5: both of its reads
      leave `condition(...)` at once, which is what makes this file the pass that ends
      a mute specification rather than a mute event -- measured before the edit, both
      events opened with `if (!(guard)) return false;` ahead of `handleEvent` and the
      `fail` handler is unreachable (transition row {1, 2, 2}, monitor keyed on the
      constructed object), so the file produced zero reports on eight constructions and
      on all six of its corpus traces. The reads stay at 18 and the writes at 38 -- the
      `ENSURES` write does not move, for the same reason as task 4.7's. The
      accepting-state calls go 20 -> 19. No omission record here: `preparedGCM` is
      required at Cipher.cryptsl:184, ledger clause #10, wired at task 5.8.
    * task 4.9 migrated `MacSpec`, and it is the only pass so far that moves every one
      of these five numbers downward at once, because it leaves the file naming no
      predicate at all. The reads go 18 -> 16 and the guards 5 -> 3: `i1` and `i2` read
      `generatedKey`, which the api30 Mac rule does not require, and they feed no write
      either, so they are deleted rather than moved -- a read that translates no clause
      and propagates nothing has no body to move to. The writes go 38 -> 36: the two
      `Finals` writes held a one-place property that three sets write and none reads,
      and the rule's `macced` is two-place, so the real producer is ledger #8 at task
      5.7. The accepting-state calls go 19 -> 18 and the removals 9 -> 8, both with the
      `@match` handler and the `@fail` withdrawal that went with those writes.
    * task 4.10 migrated `SecretKeySpecSpec`, and only one of these five numbers moves: the
      accepting-state calls go 18 -> 17. Nothing else does, and that is the point of the pass.
      The read stays a read and the write stays a write; what changes is the store under them,
      which this census cannot see and INV-INS-130 can. The read is the last consumer whose
      producer had already moved -- `randomized`, from `SecureRandom` at task 4.5 -- so moving it
      closes the last open F2 window: measured over the whole `ErrorCollector`, key material an
      observed `SecureRandom` had just filled went from one report to none. The write closes a
      second window at `CipherSpec.i2` and deliberately stays below the rule's arity to do it
      (researcher, 2026-08-21; INV-INS-134's recorded-reason clause, the reason in
      `predicate_graph.csv`).
    * task 4.11 deleted all four sites of `RandomStringPassword`, so three numbers move at
      once: the reads go 16 -> 14, the guard reads 3 -> 1, and the writes 36 -> 34. Nothing
      is relocated. The file is the set's only dataflow bridge and it translates no rule, so
      the reads' whole justification was that they govern the writes and the writes' whole
      justification was that they feed `PBEKeySpecSpec.c1`. Measured, the bridge does not
      carry the predicate it stamps: `String.valueOf(Object)` calls `Object.toString()`, so a
      `byte[]` arrives as its identity string and the `SecureRandom` as a constant, while the
      one faithful conversion -- an `Integer` -- does not survive a store keyed by identity
      outside the `Integer` cache. The accepting-state calls stay at 17 and the removals at 8:
      the empty `@match` stays, because the JavaMOP grammar requires a handler after the `ere`.
    * task 4.12 moved `SecretKeySpec.e1`, and the only number it moves is the one this census
      exists for: the guard reads go 1 -> 0, and the set has none left. The reads stay 14, the
      writes 34, the accepting-state calls 17 and the removals 8 -- the read stays a read and
      the write stays a write, both of them relocated rather than added or deleted. What the
      relocation buys is measured over the whole `ErrorCollector`: a key built from randomised
      material hands its encoding on as randomised for the first time, one report to none,
      because `getEncoded()` returns a fresh clone and this event is the only thing in the set
      that carries the predicate across that copy. What it costs is a window against the two
      producers of `generatedKey` that task 4.14 still owns, and that window is measured too --
      it changes no report, because the write it suppresses went to a store no reader of
      `randomized` has used since task 4.4.
    * task 4.13 migrated the four write-only files -- `SignatureSpec`,
      `MessageDigestSpec`, `SSLContextSpec` and `KeyPairSpec` -- and two of these five
      numbers move. The writes go 34 -> 30, which is eleven sites becoming seven: four
      `SignatureSpec` bodies collapse into two acceptance writes and three
      `MessageDigestSpec` bodies into one, because a handler writes once for the clause
      however many events stage it. The accepting-state calls go 17 -> 11, the largest
      single drop of the group, and the six are all of that bookkeeping these four files
      had. The reads stay at 14 and the guards at 0: not one of the four declares a read,
      which is what made the pass a question about readers rather than about accusers.
      Nine of the eleven sites are dead ends -- no rule of api30 requires `signed`,
      `verified`, `digested`, `generatedSSLContext` or `generatedSSLEngine` -- and each
      carries a deliberate-omission record; the other two, `KeyPairSpec`'s, have a live
      reader at `CipherSpec.i2` and close a chain, measured one report to none.
    * task 4.14 migrated the seven remaining files -- `KeyStoreSpec`,
      `KeyGeneratorSpec`, `KeyManagerFactorySpec`, `TrustManagerFactorySpec`,
      `KeyPairGeneratorSpec`, `DHGenParameterSpecSpec` and `HMACParameterSpecSpec` --
      and it is the pass that takes two of these five numbers to zero. The
      accepting-state calls go 11 -> 0: these seven files held the last of the 25 the
      change was scoped against, so INV-INS-147 is met and this counter never moves
      again. The removals go 8 -> 1, and the one left is the `PBEKeySpecSpec`
      `clearPassword` withdrawal task 4.6 translated to `negate`, which is the set's
      only real `NEGATES` clause; the seven `@fail` removals task 6.4 owned travel here
      instead, because each undoes a write this same task migrates -- the criterion of
      tasks 4.6 and 4.9 -- and because `PredicateStore` offers no removal, so leaving
      them would make them no-ops on a store nothing writes and would keep INV-INS-130
      off zero (researcher decision, 2026-08-22).
      The reads stay at 14 and the guards at 0: not one of the seven declares a read,
      which makes this the second pass in a row whose question is who reads the write.
      The writes stay at 30, because all ten sites are relocated and none is deleted or
      merged -- eight to the acceptance point and two kept in the event body with a
      recorded reason, `KeyManagerFactorySpec.gkm1` and `TrustManagerFactorySpec.gtm1`,
      whose events leave the accepting state for `start` so that an acceptance-point
      write would never run at all.
    * task 4.15 moved none of these five numbers, and that is what it was for: it edits
      no `.mop` at all. It read each of them back off the tree -- the reads at 14, the
      guards and the accepting-state calls at 0, the writes at 30, the single withdrawal
      -- and retired the three placement gates in `gate_baseline.json`, so that a
      regeneration could no longer re-record what tasks 4.12 and 4.14 removed. Task 7.6
      then deleted that mechanism outright; the three retirement records it carried are
      preserved at `backup/gh105-retired/gate-baseline/RETIREMENT.md`.
    * task 5.1 moves the reads, 14 -> 15, and moves nothing else. It is the first task of
      the change that adds a specification instead of editing one: `IvChainJunction.mop`
      carries the consumer read of api30 Cipher's guarded `preparedIV[params]` clause,
      which had a producer in the set since task 4.4 and no reader. The writes stay at
      30 because the file writes nothing -- the rule states no ENSURES clause it could
      translate -- and the guards stay at 0 because the clause's antecedent is evaluated
      in the event body ahead of the read, not in a `condition(...)`.
    * tasks 5.2 and 5.3 move the reads once between them, 15 -> 16, and the one that moves
      it is 5.3. The read is `MacSpec.f2`, and it is the set's first `validateAbsent`:
      api30 Mac `!encrypted[output1, _]` (Mac.cryptsl:82, ledger #22), which absence
      satisfies, so it lands in the `read-absent` half of this sum rather than the `read`
      half. The other three clauses of the two tasks add no site at all and are recorded
      instead: #21 because the platform cannot compose its ends -- the api30 android.jar
      has no `javax/xml/crypto` for the producing class and no `Mac` accepts the type --
      and #23 with the returned half of #22 because `MacSpec.f1` binds an array the JCA
      allocates fresh, where `validateAbsent` could answer only SATISFIED. The writes stay
      at 30 and the withdrawal at 1: neither task writes or withdraws a predicate.

      Batch B2 -- tasks 5.4, 5.5 and 5.8 -- moves the reads from 16 to 24 and the writes
      from 30 to 28, and every one of the moves is a clause of the ledger. Nine reads
      arrive, over four clauses: clause #10 (`{GCM} => preparedGCM[params]`) as a second
      read in `IvChainJunction`'s `use` body, which shares its pointcut exactly; clause #6
      (`randomized[ranGen]`) in four new events of that file, over the SecureRandom
      `CipherSpec` cannot bind; clause #13 in three new events of `KeyGeneratorSpec`, split
      out of the merged `init` that bound none of the five overloads' arguments; and the
      constructor's half of clause #33 in `SecureRandomSpec.c2`, the site task 3.1 named
      as 5.5's when it wired `setSeed2`.

      Seven sites for two clauses is the measurement's count and not the clause's, and the
      three shorter statements that were tried first are recorded in the two files at
      length. A disjunction of the signatures makes javamop write `null` to stderr and emit
      no aspect at all, though every `.rvm` generates first. The one-event
      `args(.., ranGen)` form generates and matches every `init` whatever the last
      argument's type, binding no SecureRandom and answering NOT_OBSERVED for all of them.
      A wildcard in a middle position generates a correct aspect -- AspectJ resolves the
      signature statically -- but defeats the trace harness's resolver, which accepts any
      call from the first wildcard onward, so the conforming traces of task 5.1 drew a
      report they must not draw. A wildcard is safe only after every discriminating type,
      which is why the read at `use` may keep its trailing `..`.

      One read leaves, and it is the only read this change has deleted. `PBEKeySpecSpec.c1`
      read `randomized` over the `password`: api30 requires the predicate over the salt and
      states nothing about the password. Measured against the oracle, `randomized` is
      ENSURED over four objects only -- `this` at SecureRandom, `genSeed`, `next`, `numB` --
      and none is a `char[]`, nor does any of the set's writes bind one, so the read could
      answer only NOT_OBSERVED and fired at every construction of a PBEKeySpec, the
      conforming ones included. It also cleared the flag gating the `speccedKey` write, so
      that write had never run for any program.

      Two writes leave, `SecureRandomSpec.next1` and `next3`. They stood in for
      `randomized[numB]` over `next(int)`, an event neither `nextInt` overload is, and
      order_alphabet_map.csv:79,81 already recorded that pairing either with `ne` would be
      an inference INV-INS-138 forbids. A write that translates no clause is deleted rather
      than recorded, and an autoboxed `int` could carry a predicate to a later
      identity-keyed read only inside the Integer cache in any case. The two events stay in
      the automaton, marking nothing, as `ints` and `CipherSpec.wkb1` already do.

      Clause #17 adds no site and is recorded instead, for a reason clause #21 established
      and this batch confirms is not rare: the two ends have a `.mop` each and the platform
      refuses the composition. `DHGenParameterSpec` is the only producer of `preparedDH` in
      the oracle, and measured on Temurin 21,
      `KeyPairGenerator.getInstance("DH").initialize(new DHGenParameterSpec(2048, 0))`
      raises InvalidAlgorithmParameterException: Inappropriate parameter type. Clause #20
      (`preparedEC`) has no producing rule anywhere and is recorded `unclosable`.

      Batch B3 (tasks 5.6 and 5.7) moves three of these five numbers, and each of them by
      a count this docstring names so the next batch cannot move one silently.

      `read` goes from 24 to 28. Five reads arrive: ledger clauses #15 and #16 in
      `KeyPairSpec.c1`, the constructor's own `generatedPrivkey[consPriv]` and
      `generatedPubkey[consPub]`, which the file carried no site for; and clauses #34 and
      #35 in `SignatureSpec`, over three sites, because the rule binds `priv` in both `i1`
      and `i2` and `pub` in `i4`. `i3` gains none: it binds a Certificate, which api30
      states no clause over.

      `read-absent` goes from 1 to 5. Ledger clause #8, `!macced[_, plainText]`, is read at
      the four sites of the set that bind the rule's `plainText`: `CipherSpec.f5` and `f6`,
      and `IvChainJunction.finalInput` and `finalRange`, which take the two overloads
      `CipherSpec.f2` merges without binding an argument and that it cannot be split into
      at 17 of 17 events (INV-INS-145). `CipherSpec.f7` binds a ByteBuffer and gains no
      read: no site of the set can mark one under this predicate, so it could answer only
      SATISFIED.

      `write` goes from 28 to 31. `MacSpec` gains two -- the acceptance point of
      `macced[output1, pre_input]` and `macced[output2, input]`, where the set had zero
      sites of the predicate -- and `KeyStoreSpec` one, `generatedPrivkey[key]`
      (KeyStore.cryptsl:99), guarded by `instanceof PrivateKey`. Three clauses gain no site
      and are recorded instead: `macced[output1, inp]` binds a primitive byte, which boxes
      and which no Cipher takes as a plaintext; `generatedPubkey[key]` at KeyStore has no
      execution path, `getKey` never returning a PublicKey; and `generatedKeypair[this, _]`
      is still task 5.10's.

      The other two numbers do not move and that is also a claim: `condition` stays 0, and
      `negate` stays 1 -- the batch withdraws no predicate. The arity of five sites rises
      to what api30 states, which this census does not count and
      `test_the_graph_reproduces_the_measured_placement_census` does not either; the
      `predicate_graph.csv` rows carry it.

      Batch B4 (tasks 5.9 and 6.2, the TLS chain) moves `read` from 32 to 36, so the sum
      asserted below goes from 33 to 37. Four sites, all in event bodies of events that
      already existed: `generatedKeyStore[keyStore]` at `KeyManagerFactorySpec.init` and at
      `TrustManagerFactorySpec.init` (ledger #14 and #36), and `generatedKeyManager[kms]`
      and `generatedTrustManager[tms]` at `SSLContextSpec.init` (#28 and #29). Every one of
      the four is bound by adding an `args(...)` clause to a pointcut that was already
      there, so `write` stays 31, `accepting-state` stays 0, `negate` stays 1, and no
      specification of the set gains or loses an event -- which is the batch's strongest
      structural claim and the reason its three sibling file counts do not move either.

      Task 6.2 travels in the same batch and touches none of these numbers: it repairs the
      three defects that kept `TrustManagerFactorySpec.gtm1` from ever firing, which changes
      what a write binds and whether it runs, not how many sites there are.

      Batch B5 (tasks 5.10, 6.1 and 6.5) moves `read` from 36 to 37, so the sum asserted
      below goes from 37 to 38, and moves nothing else. The one new site is
      `preparedKeyMaterial[keyMaterial]` at `SecretKeySpecSpec.c2`, the four-argument
      constructor: api30 binds `keyMaterial` in both events of `Cons := c1 | c2` and states
      one REQUIRES over it, so the obligation is the constructor's and not one overload's,
      and task 4.10 had deferred the site here rather than adding a second conflated one.
      Like B4's four, it is bound by an event that already existed, so no alphabet grows.

      The un-conflation this batch performs moves no count at all, and that is the claim
      worth writing down: `SecretKeySpec.@match` and `SecretKeySpecSpec.c1` change which
      predicate they name -- `randomized` to `preparedKeyMaterial`, ledger clause #32 -- and
      a census of operations cannot see a rename. What it changes is measured in the harness
      and in `predicate_graph.csv`, not here. `write` stays 31, `condition` stays 0,
      `accepting-state` stays 0, and `negate` stays 1: task 6.5 verifies the one real
      NEGATES translation rather than performing it, and verifying it is exactly the
      assertion that this number did not move.

      Batch B6 (tasks 5.11 and 6.4) edits no `.mop` at all, and this census is where that
      is stated rather than assumed. The closure sweep reads `predicate_graph.csv` and
      writes a `disposition`, which is a judgment about a site and not a site; the
      verification at task 6.4 performs nothing by construction. So `write` stays 31,
      `read`+`read-absent` stays 38, `condition` stays 0 and `negate` stays 1 -- and the
      last of those is the fourth pass to leave it alone, which is what makes it a number
      and not a coincidence. What the sweep enumerated is one level up: the 31 writes name
      **22** distinct `Property` values, one more than the 21 the change opened with,
      because task 5.10 renamed a write rather than adding one.

      Batch B8 (tasks 7.1, 7.2 and 7.3) moves none of them either. It edits two `.mop`, but
      what it edits there is the `fsm` and the handlers around two existing writes, and a
      census of predicate operations cannot see a transition table: `write` stays 31,
      `read`+`read-absent` stays 38, `condition` stays 0, `negate` stays 1, and the 22 distinct
      `Property` values stay 22. The `@match2` handler each of the two files gains writes
      nothing, which is what makes it invisible here and is stated in the file itself.

      Batch B9 (tasks 7.4 and 7.6) edits no `.mop` at all, and the harness footprint is the
      proof: regenerated from `HEAD` and compared, all 24 reports are byte-identical. So
      `write` stays 31, `read`+`read-absent` stays 38, `condition` stays 0, `negate` stays 1
      and the `Property` values stay 22. What it moved is one level out of this census
      entirely -- the expected-baseline mechanism is gone and G-ORDER asserts zero on its
      own -- and a census of predicate operations cannot see a gate's verdict either.

      Batch B7 (tasks 6.3, 6.6 and 6.7) moves none of the five either, and for a reason
      worth telling apart from B6's: this batch *does* edit a `.mop`, and what it edits is
      not a predicate operation. Task 6.6 narrows the `CipherSpec.f2` pointcut from
      `doFinal(..)` to `doFinal(byte[], ..)` so that it stops matching the argument-less
      call `f1` already matched -- a pointcut signature, not a read, a write or a
      withdrawal. Task 6.3 performs nothing at all, because both halves of its statement
      were already repaired before it was reached: the `sign()` return types by the gh104
      structural pass and the `verified` argument by task 4.13, the file pass that migrated
      this specification. So `write` stays 31, `read`+`read-absent` stays 38, `condition`
      stays 0, `negate` stays 1, and the 22 distinct `Property` values stay 22 -- finding
      105 asks for that last one to be recounted after every rename, and this batch renames
      nothing. What the batch does move is the trace corpus, from 128 files to 129, which
      no assertion of this suite counts and the harness evidence carries instead.
    """
    home = _rvsec_home()
    specs = sorted(
        (home / "rvsec/rvsec-mop/src/main/resources/jca_android").glob("*.mop")
    )
    assert len(specs) >= 23

    counts: dict[str, int] = {}
    read_placement: dict[str, int] = {}
    for path in specs:
        source = read_mop(path)
        assert source.parse_error == "", f"{path.name}: {source.parse_error}"
        for site in source.sites:
            counts[site.operation] = counts.get(site.operation, 0) + 1
            if site.operation.startswith("read"):
                read_placement[site.site_kind] = (
                    read_placement.get(site.site_kind, 0) + 1
                )

    assert counts.get("read", 0) + counts.get("read-absent", 0) == 38
    assert read_placement.get("condition", 0) == 0
    assert counts.get("write", 0) == 31
    assert (
        counts.get("accepting-state", 0) + counts.get("accepting-state-unset", 0) == 0
    )
    assert counts.get("remove", 0) + counts.get("negate", 0) == 1


def test_the_predicate_free_sets_read_as_predicate_free():
    """`generic` and `generic_new` are the genericity test bed, and they are empty.

    145 files that call no predicate substrate at all. A reader that found a site
    in one of them would be finding it in a file where the answer is known, which
    is the cheapest possible way to catch a pattern that has started matching too
    much.

    Batch B3 (tasks 5.6 and 5.7) does not move this number, and that is worth
    stating rather than leaving to be inferred from the diff: the batch adds seven
    write sites, thirteen read sites and six events, and every one of them lands in
    `jca_android`. It creates no `.mop` -- the two `Cipher.doFinal` overloads that
    needed binding went into the junction specification that already exists -- so
    the enumerated universe stays at 215 and the file counts of the three sibling
    suites stay where they are.

    Batch B4 (tasks 5.9 and 6.2) does not move it either, and for a stronger reason:
    it adds no event and no file. Its four reads bind their arguments by adding an
    `args(...)` clause to pointcuts that already existed, so the enumerated universe
    stays at 215, `test_gparam_is_green_over_the_set_as_it_stands` stays at 23 files,
    and `test_conformance_record_covers_all_twenty_three` stays at 23 rows. A separate
    consumer specification was one of the three ways the batch could have bound those
    arguments, and it was the one that would have moved these numbers; it was measured
    against the other two and rejected (researcher decision, 2026-08-22).

    Batch B5 (tasks 5.10, 6.1 and 6.5) does not move it either, and for the same reason
    as B4: no file and no event. Its whole substance is a rename of one predicate on two
    sites that already existed and one read added to an event that already existed, so
    the enumerated universe stays at 215 and the sibling file counts stay at 23. What
    the batch does move is the trace corpus, from 126 files to 128, which no assertion
    of this suite counts and the harness evidence carries instead.
    """
    home = _rvsec_home()
    root = home / "rvsec/rvsec-mop/src/main/resources"
    files = sorted(root.glob("generic/*.mop")) + sorted(root.glob("generic_new/*.mop"))
    assert len(files) == 145

    for path in files:
        source = read_mop(path)
        assert source.parse_error == "", f"{path.name}: {source.parse_error}"
        assert source.sites == [], f"{path.name} names a predicate substrate"


# ------------------------------------------------------------------- the graph


GRAPH = REPO / "data/jca_android/predicate_graph.csv"


def _specs_root() -> Path:
    return _rvsec_home() / "rvsec/rvsec-mop/src/main/resources"


def test_the_graph_carries_exactly_the_fifteen_contracted_columns():
    """The column set is a contract, so it is asserted as a whole.

    Adding a column silently is how a record stops being comparable with the one
    committed beside it; removing one is how a gate starts reading an empty
    string as a decision.
    """
    rows = read_graph(GRAPH)
    assert rows, f"the predicate graph is missing or empty: {GRAPH}"
    assert tuple(rows[0]) == COLUMNS


def test_the_graph_round_trips_over_an_unedited_tree():
    """Regenerating over an unchanged tree reproduces the committed file exactly.

    Everything downstream diffs this file. A generator whose output depended on
    dictionary order, file-system order or a timestamp would produce a diff on
    every run, and a record that always differs from itself records nothing.
    """
    report = analyze_set(_specs_root() / "jca_android")
    regenerated = carry_judgments(list(report.rows), read_graph(GRAPH))
    committed = read_graph(GRAPH)

    assert len(regenerated) == len(committed)
    for fresh, stored in zip(regenerated, committed):
        assert fresh == stored


def test_the_graph_reproduces_the_measured_placement_census():
    """The placement distribution this change is scoped against.

    The change opened with 27 reads, every one of them a guard inside
    `condition(...)`; 42 of 49 writes in event bodies rather than at the
    acceptance point; 8 of the 9 removals in a `@fail` handler, implementing an
    undo that no CrySL generation has. These are the four numbers the migration
    drives to 0, 0, 8 and 1, and they are asserted here so that each group's
    progress is a diff on this test rather than a claim.

    * task 3.1: 23 guards left, and the first body read in the set -- the fused
      `setSeed2`, which reads the predicate where it can accuse about it.
    * task 3.3: 19 guards left, and three body reads -- the two fused
      `IvParameterSpec` constructors joined `setSeed2`.
    * task 3.4: 17 guards left, and four body reads, the fused `SecretKeySpecSpec`
      two-argument constructor being the fourth.
    * task 3.5: 13 guards left, and six body reads -- the fused `PBEKeySpecSpec.c1`
      carries two of them, one per predicate its decomposed body tests.
    * task 3.6: 11 guards left, and seven body reads -- the fused
      `PBEParameterSpecSpec.c1` is the seventh, reading the salt where it can
      accuse about it.
    * task 4.1: 8 guards left and ten body reads, `CipherSpec.i2`'s three key-origin
      probes being the three that moved. It is also the first task to move a write:
      `write:body` goes 42 -> 30 and `write:acceptance` 7 -> 9, because the eleven
      `ENCRYPTED` writes collapse into one site per acceptance point -- `@match1`
      for the two clauses the accepting state ensures, `@match2` for the
      `after updates` clause -- and the unclaused `WRAPPED_KEY` write is deleted.
      The bookkeeping calls go 25 -> 24 with `CipherSpec`'s.
    * task 4.4: no placement moves. `IvParameterSpec`'s two reads were already body
      reads and its write already sat at the acceptance point, so the four numbers
      this test drives stay where 4.1 left them; the bookkeeping calls go 24 -> 23.
      A file pass that moves nothing is still a file pass: what it changes is the
      substrate and the arity of the verdict, and the graph records that in the
      `mechanism` column rather than in these counts.
    * task 4.5: the guards and body reads stay at 8 and 10, and the write columns
      move for the second time: `write:body` goes 30 -> 27 and `write:acceptance`
      9 -> 11. `SecureRandomSpec` is the first file with two acceptance points whose
      handlers each carry their own clause -- `@match1` at `init` for
      `randomized[this] after Ins`, `@match2` at `end` for `randomized[genSeed]` and
      `randomized[next]`, one row per clause -- and the `ints` write is deleted. The
      two rows that stay `write:body` are `next1` and `next3`, and they stay because
      their `reason` column is filled, not because the gate missed them. The
      bookkeeping calls go 23 -> 22.
    * task 4.6: no placement moves again, for a reason of its own. `PBEKeySpecSpec`'s
      two reads were already body reads after task 3.5, and its write stays in the body
      with a recorded reason: api30 qualifies the clause `after c1`, and an `ere` has no
      way to name the state that follows an event -- its only alias is `match` over the
      accepting states, which here is the state after `c2`, where the rule negates the
      predicate. So `write:body` stays 27, `write:acceptance` stays 11, and the guards
      and body reads stay at 8 and 10. What moves is the bookkeeping, 22 -> 21, and the
      species of one removal: `remove:body` becomes `negate:body`, the set's one real
      `NEGATES` translation, brought forward from task 6.5 so that no window exists in
      which the write is on one substrate and the withdrawal on the other.
    * task 4.7: the first placement move since task 4.1. `PBEParameterSpecSpec.c2`'s
      read leaves `condition(...)` for its body, so the guards go 8 -> 7 and the body
      reads 10 -> 11. The write does not move: api30 states `preparedPBE[this]` with no
      `after L`, so its acceptance point is the accepting state, which in an `ere` is
      what `@match` names -- `write:acceptance` stays 11 and `write:body` stays 27. The
      bookkeeping goes 21 -> 20, and one row gains a `disposition` for the first time
      in the graph's life: `omission`, for the predicate no rule of the oracle requires.
    * task 4.8: both of `GCMParameterSpecSpec`'s reads leave `condition(...)` for their
      bodies, so the guards go 7 -> 5 and the body reads 11 -> 13. The write does not
      move -- api30 states `preparedGCM[this]` with no `after L` -- so `write:acceptance`
      stays 11 and `write:body` stays 27. The bookkeeping goes 20 -> 19. No row gains a
      `disposition`: `preparedGCM` has a consumer in the oracle (Cipher.cryptsl:184,
      ledger #10), so its G-PRED2 row closes by a read at task 5.8, not by a record.
    * task 4.9: `MacSpec` leaves the graph entirely. It is the first file of the
      migration to lose all of its rows rather than to have them re-classified -- the
      set goes 84 rows to 78 -- because after the pass the file names no predicate:
      the guards go 5 -> 3 with `i1`'s and `i2`'s reads deleted (not moved: they
      translate no clause of the rule and feed no write, so `read:body` stays 13),
      `write:body` goes 27 -> 25 with the two `Finals` writes, `remove:fail` goes
      8 -> 7 -- the withdrawal travels with the writes it undid, by the criterion of
      task 4.6 -- and the bookkeeping goes 19 -> 18 with the `@match` handler. A reader
      who looks only at this census will see the smallest kind of change; what it
      actually records is a whole file leaving.
    * task 4.10: `SecretKeySpecSpec` moves store without moving placement, so the only count that
      changes is the bookkeeping, 18 -> 17. `read:body` stays 13 and `write:acceptance` stays 11
      -- the read was already in its body (task 3.4 put it there when it fused the twins) and the
      write was already at the acceptance point, because api30 states `generatedKey[this, alg]`
      with no `after L`. Two rows gain judgments instead of changing verdicts: the read's `clause`
      records that it tests `randomized` where the rule requires `preparedKeyMaterial` (ledger
      #32, un-conflated at 5.10+6.1), and the write's `reason` records that it stays at arity 1
      until task 5.6 moves its consumer.
    * task 4.11: the second file to leave the graph whole rather than be re-classified, and for
      a reason the `MacSpec` precedent did not cover. The set goes 77 rows to 73: the guards go
      3 -> 1 and `write:body` 25 -> 23, all four rows deleted together. `MacSpec`'s reads went
      because they fed no write; these feed one, and go because the write does not carry the
      predicate across -- `String.valueOf(Object)` hands `Object.toString()` a `byte[]` and gets
      its identity string back. Recording them as `propagation` would have entered a claim the
      conversion does not support into the graph. Nothing else moves: `read:body` stays 13,
      `write:acceptance` 11, `remove:fail` 7, `negate:body` 1 and the bookkeeping 17.
    * task 4.12 relocated both sites of `SecretKeySpec`, so two pairs move together:
      `read:condition-guard` goes 1 -> 0 -- the set's last one -- and `read:body` 13 -> 14,
      while `write:body` goes 23 -> 22 and `write:acceptance` 11 -> 12. The read gains a
      `disposition` of `propagation`, the second row of the graph to carry one: api30
      SecretKey states an ENSURES and no REQUIRES, so it translates no clause and accuses
      nothing, and it is recorded rather than deleted because it feeds a write that does carry
      the predicate across -- both conditions of the delta's rule, which `MacSpec` failed on the
      first and `RandomStringPassword` on the second. The write goes to `@match` because the
      clause's `after ge` and the `ere`'s accepting state are the same state here, read off the
      generated monitor's transition row. The bookkeeping stays 17, the removals 7 and the
      `negate` 1: this file had none of them and gains none.
    * task 4.13 relocated eleven writes across four files, and the graph shows the move as
      a shrink: `write:body` goes 22 -> 13 and `write:acceptance` 12 -> 17, which is nine
      sites leaving the body against five arriving at an acceptance point, because a
      handler carries one row per predicate however many events stage it. The bookkeeping
      goes 17 -> 11 with the six accepting-state calls these files had, and the set goes
      73 rows to 63. Five rows gain `omission` -- `signed`, `verified`, `digested`,
      `generatedSSLContext`, `generatedSSLEngine`, none of them required by any rule of
      the oracle -- which takes the graph from one deliberate-omission record to six.
      Two rows do not move placement at all: `KeyPairSpec`'s two writes stay `write:body`
      with a recorded reason, because the `ere` demands the constructor api30 marks
      optional and the accepting state is therefore unreachable on the route by which a
      program obtains a KeyPair. `read:body` stays 14, the removals 7 and the `negate` 1:
      none of the four files carries a read or a withdrawal.
    * task 4.14 relocated ten writes across seven files, and the graph shrinks again:
      `write:body` goes 13 -> 7 and `write:acceptance` 17 -> 23, which is six sites
      leaving the body against six arriving at an acceptance point -- one for one here,
      because no two of the six share a handler. The bookkeeping goes 11 -> 0 and
      `remove:fail` 7 -> 0, so the set goes 63 rows to 45 and two whole verdict families
      disappear from the graph. Three rows gain `omission`, taking the graph from six
      deliberate-omission records to nine: `generatedKeypair`, which no rule of the
      oracle requires and which is the last of the seven dead-end predicates design.md
      counts over eleven sites, and the two `[this] after Init` halves of
      `generatedKeyManager` and `generatedTrustManager`, which the oracle ensures over
      the factory and which no rule asks for there -- their `[kms]`/`[tms]` siblings, the
      ones `SSLContext` reads at task 5.9, are separate sites and carry no record.
      The two rows that stay `write:body` do so with a recorded reason, and the reason is
      the automaton in both: `gkm1` and `gtm1` have transition rows that leave the
      accepting state for `start`, so an acceptance-point write would never run --
      measured, `validate` answers NOT_OBSERVED under that placement and SATISFIED under
      this one. `read:body` stays 14 and the `negate` 1: none of the seven files carries
      a read, and the one withdrawal is elsewhere.
    * task 4.15 moved no row of the graph. It has no `.mop` edit and no `--emit`: what it
      did was read these counts back off the file and retire the gates that measure them,
      so the graph and this census still meet at 45 rows.
    * task 5.1 adds the graph's 46th row and moves one number: `read:body` 14 -> 15. The
      row is `IvChainJunction.mop/use`, the consumer read of api30 Cipher.cryptsl:182,
      and it is the first row of the graph to carry a `guard` -- the clause is an
      implication, and its antecedent is evaluated in the event body ahead of the read
      rather than in a `condition(...)`, which is what INV-INS-133 asks of the eight
      guarded clauses. Nothing else moves: the file writes no predicate, withdraws none,
      and calls no bookkeeping.
    * task 5.3 adds the graph's 47th row and moves no number of this census, which is why
      the `read-absent:body` assertion below was added rather than an existing count
      changed. The row is `MacSpec.f2/ENCRYPTED`, the set's first `polarity=negated` row
      and its first `validateAbsent`: api30 Mac `!encrypted[output1, _]`
      (Mac.cryptsl:82). Task 5.2 adds no row at all -- ledger #21 is recorded as a
      deliberate omission on the producer's own row, `HMACParameterSpecSpec.mop/match`,
      which is how its G-PRED2 line closes without a reader.
    * batch B2 -- tasks 5.4, 5.5 and 5.8 -- takes the graph to 53 rows and moves two
      numbers: `read:body` 15 -> 23 and `write:body` 7 -> 5. Nine rows arrive and three
      leave, and each is a clause of the ledger resolved.
      Arriving: `IvChainJunction.mop/use/PREPARED_GCM` (clause #10), the second row of the
      graph to carry a `guard` and the first to share an event with another read -- it has
      the same pointcut as clause #9's row, which is why it is a read in that body and not
      a file of its own; four `IvChainJunction.mop/useRandom*/RANDOMIZED` rows (#6), one
      per `init` overload api30 binds `ranGen` in, two of which `use` does not match at all;
      three `KeyGeneratorSpec.mop/initRandom*/RANDOMIZED` rows (#13), split out of the
      merged `init` and not added to it; and `SecureRandomSpec.mop/c2/RANDOMIZED` (#33),
      the constructor's half of the self-chain, which task 3.1 named as 5.5's when it wired
      `setSeed2`'s half. One site per overload is what the generator and the trace harness
      between them will carry: a disjunction of signatures emits no aspect, an
      `args(.., ranGen)` catch-all accuses every `init` that passes through it, and a
      middle wildcard defeats the harness's resolver -- all three measured, and recorded in
      the `reason` column of each row.
      Leaving: `PBEKeySpecSpec.mop/c1/RANDOMIZED` over the `char[]`, the graph's row whose
      `clause` column was empty because there was no clause -- the read fired at every
      construction of a PBEKeySpec and cleared the flag that gated the `speccedKey` write,
      so that write had never run for any program; and `SecureRandomSpec.mop/next1` and
      `next3`, the two other rows with an empty `clause`, stand-ins for `randomized[numB]`
      over an event neither `nextInt` overload is. After this batch one row of the graph
      still has an empty `clause` column, and it is not this batch's: `SecretKeySpec.mop/e1`,
      the propagation read task 4.12 recorded, whose rule states an ENSURES and no REQUIRES
      section at all.
      One row gains `omission`, taking the deliberate-omission records from nine to ten:
      `DHGenParameterSpecSpec.mop/match/PREPARED_DH`, ledger #17, which has a `.mop` at
      both ends and no program that can compose them -- measured,
      `KeyPairGenerator.getInstance("DH").initialize(new DHGenParameterSpec(2048, 0))`
      raises InvalidAlgorithmParameterException, and this rule is the oracle's only
      producer of the predicate. Its G-PRED2 line closes by that record, the way #21's did;
      `GCMParameterSpecSpec`'s closes by a read. The gate goes from six findings to four.
      Nothing else moves: `write:acceptance` stays 23, the `negate` 1, the `read-absent` 1,
      and the bookkeeping and removals stay at zero.

      Batch B3 (tasks 5.6 and 5.7) moves three of them, and the two it does not move are
      the load-bearing ones.

      `read:body` goes from 23 to 28, for the five reads the reader census names: ledger
      clauses #15 and #16 at `KeyPairSpec.c1`, and #34 and #35 at `SignatureSpec.i1`, `i2`
      and `i4`.

      `read-absent:body` goes from 1 to 5, which is the assertion below doing the job it
      was written for. Clause #8 is the set's second negated clause to be wired and it
      arrives at four sites at once -- `CipherSpec.f5`, `f6`, and `IvChainJunction`'s
      `finalInput` and `finalRange`.

      `write:acceptance` goes from 23 to 26: two at `MacSpec.match`, the acceptance point
      of `macced` recreated with the handler task 4.9 deleted whole, and one at
      `KeyStoreSpec.match` for `generatedPrivkey[key]`.

      `write:body` stays 5 and `read:condition-guard` stays 0, and those two are the claim
      this batch most has to make: it adds seven write sites and thirteen read sites and
      puts none of them off the acceptance point or inside a guard. `negate:body` stays 1.

      The two `MacSpec.match/MACED` rows are indistinguishable in every column this reader
      computes, so they carry identical manual text on purpose: a swap between them on a
      re-emit is a no-op (finding 81).

      Batch B4 (tasks 5.9 and 6.2) moves `read:body` from 28 to 32 and moves nothing else.
      The four rows are the TLS chain's: `KeyManagerFactorySpec.init/GENERATED_KEY_STORE`,
      `TrustManagerFactorySpec.init/GENERATED_KEY_STORE`,
      `SSLContextSpec.init/GENERATED_KEY_MANAGERS` and
      `SSLContextSpec.init/GENERATED_TRUST_MANAGER`. `write:body` stays 5 and
      `write:acceptance` stays 26 because the batch adds no write at all -- it closes three
      G-PRED2 findings by giving three existing writes a reader, not by moving them. The two
      body writes that stay are still `gkm1` and `gtm1`, whose placement belongs to task 7.1
      and whose recorded reasons this batch updates rather than retires.

      `read:condition-guard` stays 0, which for this batch means something specific: two of
      the four reads sit behind an `instanceof` test in the body, because their event is a
      fusion of two overloads and the argument is bound as `Object`. That test discriminates
      which overload ran; it is not a `condition(...)` guard and it suppresses no transition,
      which is the distinction INV-INS-133 is about.

      Batch B5 (tasks 5.10, 6.1 and 6.5) moves `read:body` from 32 to 33 and moves nothing
      else. The row that arrives is `SecretKeySpecSpec.c2/PREPARED_KEY_MATERIAL`, the read
      the four-argument constructor gains; task 4.10 had deferred it here rather than adding
      a second site to a clause it knew was conflated.

      Two rows change their `predicate` column without changing any count, and that is the
      un-conflation of ledger clause #32: `SecretKeySpec.@match` writes
      `PREPARED_KEY_MATERIAL` where it wrote `RANDOMIZED`, and `SecretKeySpecSpec.c1` reads
      it where it read `RANDOMIZED`. A census keyed on `verdict` cannot see a rename, so the
      whole of what this batch is about is invisible here on purpose -- it is measured in
      the harness and carried in the `clause` and `reason` columns, where the two rows had
      recorded the conflation since tasks 4.10 and 4.12 and now record its repair.

      `write:acceptance` stays 26 and `negate:body` stays 1. The second of those is task
      6.5's verification rather than task 6.5's work: the one real NEGATES clause of the set
      was translated by task 4.6 with the write it withdraws, and the assertion that the
      number did not move is what verifying it amounts to.

      Batch B6 (tasks 5.11 and 6.4) moves no count here either, and it is the first batch
      of which that is the whole story: it edits no `.mop`, so the graph keeps its 70 rows
      and every `verdict` above keeps its number. What it changes is one cell of one row --
      the `disposition` of `PBEKeySpecSpec.mop c1/SPECCED_KEY`, from empty to `omission` --
      and no census in this file is keyed on that column, by design: a disposition is the
      reason an edge stays open, and counting reasons would make the record argue with
      itself. It is G-PRED2 that reads the column, and the closure drove it to zero.

      Batch B7 (tasks 6.3, 6.6 and 6.7) leaves all eight counts where B6 left them and the
      graph at its 70 rows. Neither `CipherSpec.f1` nor `f2` has a row in this file -- they
      stage the pair into a field and the write stands at `@match1` -- so narrowing `f2`'s
      pointcut has nothing here to move, and task 6.3 edits no site at all. The claim was
      checked the way finding 81 asks: the graph was copied, re-emitted from the edited set
      and diffed back, and the two files are identical.

      Batch B8 (tasks 7.1, 7.2 and 7.3) edits two `.mop` and still moves nothing here, which
      is the point of recording it. `gkm1` and `gtm1` keep their `write:body`, so `write:body`
      stays 5 and `write:acceptance` stays 26: what task 7.1 repaired is the automaton around
      those two writes, not their placement. The transition now lands on an accepting state --
      `@match2`, the second alias each file gains -- so the body write runs where the clause
      asks, and the two rows record that in their `reason` where they used to record the
      opposite. What keeps the write out of the handler is unchanged and is not a placement
      decision at all: a handler sees no parameter of the event it follows, and the predicate
      is over the array the event returns. The graph keeps its 70 rows, and the round trip was
      re-checked the way finding 81 asks.

      Batch B9 (tasks 7.4 and 7.6) edits no `.mop` and moves none of the eight. The graph
      keeps its 70 rows. What the batch changed is where the nine G-ORDER divergences are
      written down -- `gate_baseline.json`, which recorded them anonymously, is retired, and
      `gate_allowlist.csv` carries them with a witness, a reason and a task each -- and that
      is a fact about the gate's bookkeeping, not about any site this file counts.
    """
    rows = read_graph(GRAPH)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1

    assert counts.get("read:condition-guard", 0) == 0
    assert counts.get("read:body", 0) == 33
    # The negated clauses read through `validateAbsent`, which the graph records as its
    # own verdict, so a row of theirs is invisible to the `read:body` count above. Task
    # 5.3 put the set's first one there, and the assertion exists so that the next one
    # cannot arrive uncounted.
    assert counts.get("read-absent:body", 0) == 5
    assert counts.get("write:body", 0) == 5
    assert counts.get("write:acceptance", 0) == 26
    assert counts.get("remove:fail", 0) == 0
    assert counts.get("negate:body", 0) == 1
    assert counts.get("bookkeeping:match", 0) + counts.get("bookkeeping:fail", 0) == 0


def test_the_graph_marks_the_sites_carried_by_orphan_accusers():
    """A site on an orphan event is a predicate read the ordering never reaches.

    Eight of the seventeen orphans carried predicate sites, and those are the ones
    whose fusion changes what the set accuses rather than only where it accuses
    from. Marking membership in the graph is what lets the difference be counted.

    * task 3.1 took the two `SecureRandomSpec` rows out: `c3`'s read left with the
      guard it was, and `setSeed3`'s moved into the fused `setSeed2` body, where
      it is a member site and no longer an orphan one.
    * task 3.3 took the two `IvParameterSpec` rows out the same way: `c3` and `c4`
      were both guard-only reads, and what survives is the one body read each of
      `c1` and `c2` now carries.
    * task 3.4 took `SecretKeySpecSpec.c3` out; its four-argument twin `c4` never
      carried a site, because the clause it complements is a length comparison and
      not a predicate.
    * task 3.5 took `PBEKeySpecSpec.err2` and `err3` out, leaving one row in the
      set. Both reads survive in `c1`'s body, where they are member sites.
    * task 3.6 took the last one, `PBEParameterSpecSpec.c3`. Its read survives in
      the fused `c1` body; the three-argument `c2` keeps its accuser-less guard
      until that file's Group-4 pass, but `c2` is a member event and was never an
      orphan site.
    """
    rows = read_graph(GRAPH)
    orphan_sites = {
        (row["file"], row["event"])
        for row in rows
        if row["automaton_membership"] == "orphan"
    }
    assert orphan_sites == set()


def test_judgment_columns_survive_a_regeneration():
    """A decision written into the graph is not erased by re-reading the tree.

    Which clause a site translates, which mechanism wired it, why a write sits
    where it does -- none of that is recoverable from the source, and all of it is
    what the wiring groups produce. A regeneration that dropped it would quietly
    undo the work of the group that ran before it.
    """
    report = analyze_set(_specs_root() / "jca_android")
    rows = list(report.rows)
    assert rows

    annotated = [dict(row) for row in rows]
    annotated[0]["clause"] = "Cipher.cryptsl:180"
    annotated[0]["mechanism"] = "B"
    annotated[0]["disposition"] = "wired"
    annotated[0]["reason"] = "pilot chain"
    annotated[0]["guard"] = "alg in {AES}"

    carried = carry_judgments([dict(row) for row in rows], annotated)
    assert carried[0]["clause"] == "Cipher.cryptsl:180"
    assert carried[0]["mechanism"] == "B"
    assert carried[0]["disposition"] == "wired"
    assert carried[0]["reason"] == "pilot chain"
    assert carried[0]["guard"] == "alg in {AES}"
    assert carried[1]["clause"] == ""


def test_a_predicate_free_set_produces_zero_rows_and_that_is_green():
    """Genericity, stated as the case that is easiest to get wrong.

    `generic` and `generic_new` call no predicate substrate at all. The correct
    content of the graph over them is nothing -- not an error, not a skip, and not
    a pass that was never computed. A gate that cannot say "zero rows, read in
    full" about them is not generic; it is specialised to the set it was written
    against.
    """
    for name in ("generic", "generic_new"):
        report = analyze_set(_specs_root() / name)
        assert report.rows == [], name
        assert report.read == report.total, f"{name}: {report.skipped}"


def test_every_file_is_either_read_or_skipped_with_a_reason():
    """The skip-and-count contract: the three numbers always add up.

    Green by vacuity and red by absence are the two ways a gate over a
    heterogeneous universe lies. The defence is arithmetic -- read plus skipped
    equals the files that exist -- plus a reason for every skip, so a growing skip
    list is visible instead of comfortable.
    """
    root = _specs_root()
    universe = 0
    for name in (
        "jca",
        "jca_android",
        "jca_android_bug_predicate",
        "generic",
        "generic_new",
    ):
        report = analyze_set(root / name)
        existing = len(list((root / name).glob("*.mop")))
        assert report.total == existing, name
        universe += existing
        for skipped_file, reason in report.skipped:
            assert reason, f"{name}/{skipped_file} was skipped without a reason"

    # Enumerated, never asserted as a literal: this change adds junction
    # specifications, and the universe is meant to grow.
    assert universe == len(list(root.glob("*/*.mop")))


def test_the_frozen_unbalanced_specification_is_skipped_with_its_reason():
    """`jca/SecretKeySpecSpec.mop` cannot be walked, and says so.

    It carries a stray `)` after its `c1` condition. It is frozen, so it stays
    broken; what must not happen is a gate reading two thirds of it and reporting
    the result as a verdict over the set.
    """
    report = analyze_set(_specs_root() / "jca")
    skipped = dict(report.skipped)
    assert "SecretKeySpecSpec.mop" in skipped
    assert "unbalanced parenthesis" in skipped["SecretKeySpecSpec.mop"]


# ---------------------------------------------------------------- the gates


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gh105"
ALLOWLIST = REPO / "data/jca_android/gate_allowlist.csv"


def _fixture_report(name: str):
    source = read_mop(FIXTURES / name)
    assert source.parse_error == "", f"{name}: {source.parse_error}"
    report = SetReport(name="jca_android")
    report.read = 1
    report.rows = build_rows([source])
    return report, source


def test_gacc_reports_nothing_over_the_derived_set():
    """G-ACC over the set it governs, closed.

    A non-zero count was the expected state while Group 3 ran: the gates are
    written before the edits that make them green, which is what let each group's
    landing be measured as a drop rather than asserted. Seventeen at the start; 14
    after task 3.1 took `SecureRandomSpec` whole; 13 after task 3.2 fused
    `TrustManagerFactorySpec.g3` into `g1`; 11 after task 3.3 fused both
    `IvParameterSpec` twins; 9 after task 3.4 fused both `SecretKeySpecSpec`
    twins; 4 after task 3.5 took `PBEKeySpecSpec` whole; zero after task 3.6 took
    the last four. Task 3.7 retired the gate's baseline rows, so from here the
    assertion is the literal zero and not a subset.
    """
    root = _specs_root()
    report = analyze_set(root / "jca_android")
    sources = [read_mop(path) for path in sorted((root / "jca_android").glob("*.mop"))]

    findings = gate_acc(report, sources)
    assert all(finding.gate == "G-ACC" for finding in findings)
    assert len(findings) == 0


def test_gacc_reports_both_directions_and_the_duplicate_declaration():
    """The frozen GCM specification trips all three readings of the alphabet.

    Declared-and-unused, named-and-undeclared, declared-twice. It is allow-listed
    and never repaired -- it is frozen -- so it serves as the standing proof that
    a gate which only looks one way would call this file clean.
    """
    root = _specs_root()
    source = read_mop(root / "jca" / "GCMParameterSpecSpec.mop")
    report = SetReport(name="jca")
    report.read = 1

    subjects = {
        (finding.subject, finding.message.split(":")[0])
        for finding in gate_acc(report, [source])
    }
    assert ("c2", "the ere names `c2`, which no event declares") in subjects
    assert any(
        subject == "c1" and "declared more than once" in message
        for subject, message in subjects
    )


def test_the_placement_gate_reports_every_read_that_is_still_a_guard():
    """INV-INS-133 over the set, before the reads move.

    All 27 of them when the change opened; 23 after task 3.1's fusions took four
    guards out; 19 after task 3.3 fused the two `IvParameterSpec` pairs; 17 after
    task 3.4 fused the two `SecretKeySpecSpec` pairs; 13 after task 3.5 fused the
    three `PBEKeySpecSpec` twins; 11 after task 3.6 fused `PBEParameterSpecSpec`'s;
    8 after task 4.1 moved `CipherSpec.i2`'s three key-origin probes into the body,
    the first reads to move because the migration asked them to rather than because
    a fusion took their event away; 7 after task 4.7 moved `PBEParameterSpecSpec.c2`'s
    read of the salt, the last guard read of that file and the one whose guard was
    measured, in the generated monitor, to `return false` ahead of `handleEvent`; 5
    after task 4.8 moved both of `GCMParameterSpecSpec`'s, the pass in which the guard
    was measured to silence not one event but the whole specification -- both events
    guarded and the `fail` handler unreachable, so no program it could see drew a
    report. The gate exists to make the migration's progress a number that goes down,
    and to make it impossible for a new one to arrive quietly. 3 after task 4.9, whose
    two guards on `MacSpec.i1` and `i2` come out of the count by deletion rather than
    by relocation: they read `generatedKey`, which the Mac rule does not require, and
    they feed no write, so there is nothing for a body to carry. Measured, the guards
    were not inert -- one of them turned a program that breaks no clause into an
    `InvalidSequenceOfMethodCalls` and hid the algorithm accusation behind the same
    suppressed transition. Still 3 after task 4.10, which moved a read that was already in its
    body: this gate counts guards, and that pass moved a store, not a placement. 1 after task
    4.11, which took `RandomStringPassword`'s two guards out the way task 4.9 took `MacSpec`'s
    -- by deletion, not relocation -- but on a different ground: these two do govern writes,
    and the writes went with them because the conversion they span does not carry the predicate
    they stamp. 0 after task 4.12, which moved
    `SecretKeySpec.e1` into its body: the last guard read of the set, and the one with the
    least to lose by moving, since it accuses nothing either way. What its guard cost was not
    a report but a transition -- a key whose origin the monitor had not observed left the
    automaton instead of simply not propagating -- and what the read now decides is one thing
    only: whether there is anything to carry. This gate has nothing left to count, and the
    value of that is that a new guard arriving anywhere in the set can no longer hide inside a
    non-zero number. Still 0 after task 4.13, and that is worth writing down rather than
    passing over: the four files it migrated carry eleven writes and not one read, so this
    gate had nothing to count before the pass and nothing after it. A task that moves no
    guard says so. Still 0 after task 4.14, for the same reason and over seven files
    rather than four: none of the seven declares a predicate read at all, so the pass
    moved ten writes and no guard. What that pass did take to zero are the two counters
    the other censuses hold -- the accepting-state calls (INV-INS-147) and the `@fail`
    removals -- and the invariant this gate's neighbour checks, INV-INS-130, which the
    seven files plus two dangling imports in `CipherInputStreamSpec` and
    `CipherOutputStreamSpec` had been holding off zero. Still 0 after task 4.15, which
    moved no guard because it edits no specification: it confirmed the zero and retired
    the gate, so this count is not a baseline any more and the next finding is a
    regression.
    """
    report = analyze_set(_specs_root() / "jca_android")
    report.rows = carry_judgments(report.rows, read_graph(GRAPH))

    findings = gate_placement(report)
    guards = [finding for finding in findings if finding.gate == "INV-INS-133"]
    assert len(guards) == 0


def test_the_placement_gate_accepts_a_write_that_records_why_it_stays():
    """A write off the acceptance point is not forbidden -- it is accountable.

    Some writes legitimately belong elsewhere: `GENERATED_CIPHER` is marked at the
    init events rather than at acceptance, because a cipher handed to a
    `CipherInputStream` has been initialised and has not yet encrypted anything.
    What the gate demands is the reason, written where the next reader will find
    it.

    The direction is asserted by taking a reason away and putting it back, not by
    adding one to the live set. Since task 4.14 every `write:body` row of
    `jca_android` carries its reason and the gate reports nothing, so a test that
    only added a reason would compare zero against zero and pass whatever the gate
    did.
    """
    report = analyze_set(_specs_root() / "jca_android")
    report.rows = carry_judgments(report.rows, read_graph(GRAPH))

    kept = next(
        row for row in report.rows if row["verdict"] == "write:body" and row["reason"]
    )
    with_reason = len([f for f in gate_placement(report) if f.gate == "INV-INS-134"])

    reason, kept["reason"] = kept["reason"], ""
    without_reason = len([f for f in gate_placement(report) if f.gate == "INV-INS-134"])
    assert without_reason == with_reason + 1

    kept["reason"] = reason
    assert (
        len([f for f in gate_placement(report) if f.gate == "INV-INS-134"])
        == with_reason
    )


def test_gpred2_closes_a_read_whose_producer_is_recorded_as_absent():
    """A gap that is written down is closed; a gap that is silent is a finding.

    `preparedEC` has no producing rule anywhere in the oracle, so no edit can wire
    it. The gate's answer to that is a disposition naming the absence -- which is
    a decision a reader can disagree with -- rather than a green that hides it.
    """
    report = SetReport(name="jca_android")
    report.read = 1
    report.rows = [
        {column: "" for column in COLUMNS}
        | {
            "file": "CipherSpec.mop",
            "event": "i2",
            "predicate": "PREPARED_EC",
            "verdict": "read:body",
            "site_kind": "body",
        }
    ]
    assert len(gate_pred2(report)) == 1

    report.rows[0]["disposition"] = "unclosable"
    assert gate_pred2(report) == []


def test_gpred2_is_green_over_a_graph_with_no_rows():
    """Zero rows is the correct content over a predicate-free set, and it passes.

    The closure of an empty graph is the empty graph. A gate that could not say so
    would be reporting on 145 files it never looked at.
    """
    report = SetReport(name="generic")
    report.read = 118
    assert gate_pred2(report) == []


@pytest.mark.parametrize(
    "fixture,rule,subject",
    [
        ("CreationConsumerJunction.mop", "INV-INS-136(a)", "consume"),
        ("PartialLoopJunction.mop", "INV-INS-136(b)", "prepared/randomise"),
        ("HandlerParameterJunction.mop", "INV-INS-136(d)", "@match/spec"),
    ],
)
def test_each_junction_rule_catches_the_failure_the_pilot_measured(
    fixture, rule, subject
):
    """One fixture per rule, each carrying its defect and nothing else.

    (a) A consumer declared `creation` starts a monitor at the consuming call,
    which never saw the producer, and accuses the conforming trace. (b) A state
    without a transition for an event sends the cross-product instances that
    arrive there to `fail`. (d) A handler naming a specification parameter does
    not compile, and fails far from the edit that caused it.
    """
    report, source = _fixture_report(fixture)
    findings = gate_junction_rules(report, [source])
    assert [(finding.gate, finding.subject) for finding in findings] == [
        (rule, subject)
    ]


def test_the_conforming_junction_trips_nothing():
    """The chain written correctly. Without this, three red fixtures prove little.

    A gate that has only ever been shown broken input cannot demonstrate that it
    stays quiet on good input, and a rule that fires on everything is indistinguishable
    from a rule that means nothing.
    """
    report, source = _fixture_report("ConformingJunction.mop")
    assert gate_junction_rules(report, [source]) == []


def test_the_junction_rules_do_not_govern_typestate_specifications():
    """The four rules are mechanism B's, and only a junction is mechanism B.

    A typestate specification whose state has no transition for an event is doing
    its job -- that is how it accuses a wrong call sequence. Applying rule (b) to
    the 23 typestate specifications of the set -- all of it but the junction --
    would report the set's whole purpose as a defect, which is why the rules key on the junction naming convention.
    """
    root = _specs_root()
    report = analyze_set(root / "jca_android")
    sources = [read_mop(path) for path in sorted((root / "jca_android").glob("*.mop"))]
    assert gate_junction_rules(report, sources) == []


def test_the_suite_skips_the_frozen_sets_declaredly_rather_than_failing_them():
    """A frozen set cannot satisfy the placement contract, and is not asked to.

    `jca` produced published measurements; the archived set is a record. Running
    the migration's contract against either would report, correctly and uselessly,
    that a frozen file is still what it was frozen as -- and a suite that is
    expected to be red stops being read. The skips are counted and carry reasons,
    which is the difference between scoping a gate and quietly not running it.

    The finding assertion is a subset and not an equality, because task 5.11 drove
    the structural suite to zero over the whole universe: an equality would have
    required a finding to exist in order to say where findings may come from, and
    the claim here has never been that there is one. What it says is that nothing
    arrives from a set these gates do not govern, which is true of the empty set
    and stays true if a finding returns.
    """
    run = run_gates(_specs_root(), "all", GRAPH, ALLOWLIST)

    skipped_sets = {spec_set for _, spec_set, _ in run.gate_skips}
    assert skipped_sets == {
        "jca",
        "jca_android_bug_predicate",
        "generic",
        "generic_new",
    }
    assert all(reason for _, _, reason in run.gate_skips)
    assert {finding.spec_set for finding in run.findings} <= {"jca_android"}


def test_the_orphan_in_the_generic_set_is_reported_without_failing_the_run():
    """`generic/FSM246.mop` declares `event_2` and never names it.

    It is real, it is nobody's task, and this change does not edit that set. The
    gate reports it as informative: silence would mean the gate stops at the set
    it was written for, and a failure would make the only cure be to stop running
    there.
    """
    run = run_gates(_specs_root(), "all", GRAPH, ALLOWLIST)
    informative = {
        (finding.spec_set, finding.file, finding.subject) for finding in run.informative
    }
    assert ("generic", "FSM246.mop", "event_2") in informative


# ---------------------------------------------------------------------- G-PARAM


GPARAM = FIXTURES / "gparam"


def test_gparam_catches_every_primitive_array_the_generator_deletes():
    """The collapse, on the three array types the chains actually bind.

    JavaMOP deletes a primitive-array parameter from the generated header and
    returns 0. A specification that loses its `byte[]` position stops slicing by
    that object: every instance of the chain collapses into one monitor, so a
    randomised IV in one part of the program satisfies a constructor in another.
    The monitor compiles and runs and reports plausible nonsense, which is why
    nothing but an artifact comparison finds it.

    The pairs are checked in rather than generated, because the first real
    generation of a junction specification is exactly the run where a wrong gate
    costs the most.
    """
    result = gh105_param_gate.run(GPARAM, GPARAM / "monitors", "specs")

    collapsed = {finding.spec for finding in result.findings}
    assert collapsed == {"ByteArrayJunction", "IntArrayJunction", "CharArrayJunction"}
    assert all(
        "returned 0" in finding.message or "return code 0" in finding.message
        for finding in result.findings
    )


def test_gparam_passes_the_object_idiom():
    """`Object` survives the grammar branch, which is why the idiom exists.

    The overload is pinned in the `call(...)` signature instead, and `args(x)`
    with `Object` matches any single argument. Without this half of the fixture
    the gate would be indistinguishable from one that fails every junction.
    """
    result = gh105_param_gate.run(GPARAM, GPARAM / "monitors", "specs")
    assert "specs/ObjectIdiomJunction" in result.passed


def test_gparam_skips_a_specification_that_was_never_generated():
    """A missing monitor is a skip with a reason, never a pass.

    The generation this gate reads can fail while returning 0 and writing nothing
    at all -- a logic engine that ran out of memory does exactly that. Counting a
    missing artifact as a pass would make the gate green precisely when the
    generation failed hardest.
    """
    result = gh105_param_gate.run(GPARAM, GPARAM / "monitors" / "absent", "specs")
    assert result.passed == []
    assert len(result.skipped) == 4
    assert all("no generated monitor" in reason for _, reason in result.skipped)


def test_gparam_is_green_over_the_set_as_it_stands():
    """No specification of the set declares a primitive-array parameter today.

    The gate is written before the first one exists, so this assertion is what
    says the gate is quiet on the tree it will guard -- and the day it goes red is
    the day a junction specification was written the wrong way.

    The skip is asserted and not merely tolerated. `results/gh51_e2e_test/monitors`
    is a committed fixture generated before this change, so a specification the
    change adds has no `.rvm` there and the gate passes over it declaredly --
    which would quietly empty the promise above for exactly the files it was
    written for. Naming the skipped file keeps the census honest: 23 compared, one
    skipped for want of a generated artifact, and a second unmonitored file breaks
    this test instead of disappearing into the count. `IvChainJunction.mop`
    (task 5.1) declares one parameter, `Cipher c`, and no array; that it slices by
    it was read off the generated monitor's `IvChainJunctionSpec_c_Map` rather than
    inferred from this gate.
    """
    monitors = REPO / "results/gh51_e2e_test/monitors"
    if not monitors.is_dir():
        pytest.skip(f"no generated monitors to compare against: {monitors}")

    result = gh105_param_gate.run(_specs_root(), monitors, "jca_android")
    assert result.findings == []
    assert len(result.passed) == 23
    assert [name for name, _ in result.skipped] == ["jca_android/IvChainJunction"]


# ------------------------------------------------ the gates under the CI contract


# The gates of this change were written before the edits that make them green, so
# they spent most of the change registered against an expected baseline: each
# wrapper asserted that the gate reported nothing the baseline did not already
# carry, and a specification's row left the baseline as its group landed (design
# D-13). Task 7.6 deleted that mechanism. Every gate below now asserts zero
# findings on its own, and the exceptions that outlive their group live in
# `gate_allowlist.csv`, where each one carries the witness, the reason and the
# task that decided it. The retired mechanism, and the five retirement records it
# carried, are kept at `backup/gh105-retired/gate-baseline/RETIREMENT.md`.


@pytest.fixture(scope="module")
def suite():
    """One run of the whole structural suite, shared by every wrapper.

    The run walks 215 files over five sets; running it once per assertion would
    make the CI wiring cost more than everything it guards.
    """
    return run_gates(_specs_root(), "all", GRAPH, ALLOWLIST)


def _no_findings(suite, gates: tuple[str, ...]) -> None:
    """The structural suite reports nothing for these gates.

    Keyed on set/file/subject and never on line numbers or message text, so the
    failure names the specification and the subject a reader has to open -- a
    gate whose report is a diff of line numbers is a gate that gets muted.
    """
    measured = sorted(
        (finding.spec_set, finding.file, finding.subject)
        for finding in suite.findings
        if finding.gate in gates
    )
    assert not measured, f"{gates}: {measured}"


def test_inv_ins_130_import_discipline(suite):
    """No `.mop` of the migrated set may name `ExecutionContext` (INV-INS-130).

    The gate is the invariant's own check -- whole-word, so a fully-qualified use
    is caught like an import, and a mention in a comment or a string counts like
    one in code. It opened this change reporting all 23 files of the set and
    reports none: task 4.14 took the last seven plus the two dangling imports of
    `CipherInputStreamSpec` and `CipherOutputStreamSpec`, and task 4.15 retired
    the gate, so what is asserted here is zero findings outright.

    The literal `grep -rlw` beside it is not redundant with the gate: it is what
    says the gate and the invariant still name the same files, so a gate that
    stopped looking would fail here rather than read as green.
    """
    findings = [finding for finding in suite.findings if finding.gate == "INV-INS-130"]
    assert all(finding.spec_set == "jca_android" for finding in findings)

    literal = {
        path.name
        for path in sorted((_specs_root() / "jca_android").glob("*.mop"))
        if re.search(r"\bExecutionContext\b", path.read_text(encoding="utf-8"))
    }
    assert {
        finding.file for finding in findings
    } == literal, "the gate and the `grep -rlw` of INV-INS-130 must name the same files"
    _no_findings(suite, ("INV-INS-130",))


def test_inv_ins_133_no_condition_reads(suite):
    """A predicate read belongs in the event body, never in `condition(...)`.

    A false guard suppresses the transition, so an unobserved predicate is
    accused as a wrong call sequence -- the mechanism behind the set's largest
    published error category. The gate opened this change with 27 such reads and
    reports none: Group 3 fused 16 away with their guarded twins, the Group-4
    passes relocated seven and deleted four that governed nothing any api30 rule
    asks for, and task 4.12 moved the last one. Task 4.15 retired the gate, so
    zero findings is what is asserted, and a guard reported here now is a new one
    rather than a leftover.
    """
    findings = [finding for finding in suite.findings if finding.gate == "INV-INS-133"]
    assert all(finding.spec_set == "jca_android" for finding in findings)
    _no_findings(suite, ("INV-INS-133",))


def test_inv_ins_134_write_placement(suite):
    """A write sits at the rule's acceptance point, or records why it does not.

    Not forbidden elsewhere -- unjustified elsewhere. The reason lives in the
    graph, in the row's own `reason` column, where the next reader finds it
    beside the site instead of in a commit message. The gate opened this change
    with 42 unaccounted writes and reports none, which is not the same as having
    no writes in event bodies: seven sites still sit in one, each with its reason
    recorded. Task 4.14 cleared the last eight and task 4.15 retired the gate, so
    a write Group 5 or 6 places off the acceptance point without a reason is a
    regression and not an expectation.
    """
    findings = [finding for finding in suite.findings if finding.gate == "INV-INS-134"]
    assert all(finding.spec_set == "jca_android" for finding in findings)
    _no_findings(suite, ("INV-INS-134",))


def test_inv_ins_135_gacc(suite):
    """G-ACC: every declared event is in the automaton, and every named one declared.

    Both directions, because an accuser outside the ordering fires on a trace the
    automaton never judged, and a transition labelled by an undeclared event can
    never be taken. The 17 orphans of the derived set were Group 3's work and task
    3.7 retired the gate, so what is asserted here is zero findings outright.

    The `generic` orphan is nobody's, and is reported informatively rather than
    failing a run it does not belong to.
    """
    findings = [finding for finding in suite.findings if finding.gate == "G-ACC"]
    assert findings == []
    assert any(finding.gate == "G-ACC" for finding in suite.informative)
    _no_findings(suite, ("G-ACC",))


def test_inv_ins_136_junction_rules(suite):
    """The four junction rules, over the specifications they govern and no others.

    Rules (a), (b) and (d) are gated here: a consumer event declared `creation`
    accuses the conforming trace, a state without a benign self-loop fails a
    disconnected join, and a specification parameter named inside a handler does
    not compile. They key on the junction naming convention because a typestate
    specification that has no transition for an event is doing its job.
    """
    junction_gates = ("INV-INS-136(a)", "INV-INS-136(b)", "INV-INS-136(d)")
    findings = [finding for finding in suite.findings if finding.gate in junction_gates]
    assert findings == [], (
        "no junction specification exists yet; these are Group 5's, and a finding "
        f"here means a rule fired on a typestate specification: {findings}"
    )


def test_inv_ins_137_gpred2(suite):
    """G-PRED2: the graph closes, or names in writing the edge it cannot close.

    Every read has a producer in the set or a disposition saying why none exists;
    every write has a reader or a recorded omission. The gate is what stops the
    change from ending with a store that is written and never consulted, which is
    the state it started from.

    It opened this change reporting 36 edges and reports none: Group 5 wired the
    21 clauses a reader could close, recorded the 14 no reader could and the one
    `preparedEC` no rule produces, and task 5.11 closed the last row and retired
    the gate, so what is asserted here is zero findings outright.
    """
    findings = [finding for finding in suite.findings if finding.gate == "G-PRED2"]
    assert all(finding.spec_set == "jca_android" for finding in findings)
    _no_findings(suite, ("G-PRED2",))


def test_inv_ins_139_gparam(suite):
    """G-PARAM under CI: the header the specification declares is the header generated.

    Artifact against artifact, never exit codes -- JavaMOP deletes a
    primitive-array parameter and returns 0. Without generated monitors beside
    the sources there is nothing to compare, and that is a skip with a reason:
    counting a missing artifact as a pass would make the gate green exactly when
    the generation failed hardest.
    """
    monitors = REPO / "results/gh51_e2e_test/monitors"
    if not monitors.is_dir():
        pytest.skip(f"no generated monitors to compare against: {monitors}")

    result = gh105_param_gate.run(_specs_root(), monitors, "jca_android")
    assert result.findings == []
    assert result.passed, "a run that compared nothing is not a pass"


def test_inv_ins_140_genericity(suite):
    """Every gate degrades declaredly over a universe it enumerates.

    Three claims, and they are one claim: the files are counted from the
    directories rather than written down (this change adds junction
    specifications, so any literal count would fail on the day the first one
    lands); every file is either read or skipped with a reason, so the numbers
    add up to the files that exist; and a gate that does not govern a set says so
    with a reason instead of silently not running there.
    """
    enumerated = sum(
        len(list((_specs_root() / name).glob("*.mop")))
        for name in SPECIFICATION_SETS
        if (_specs_root() / name).is_dir()
    )
    assert suite.universe == enumerated
    assert suite.read + suite.skipped == enumerated

    for report in suite.reports:
        assert report.read + len(report.skipped) == report.total
        assert all(reason for _, reason in report.skipped)

    governed = {gate for gate, _, _ in suite.gate_skips}
    assert governed == {"INV-INS-130", "INV-INS-133", "INV-INS-134", "G-PRED2"}
    assert all(reason for _, _, reason in suite.gate_skips)


# ---------------------------------------------------------------------- G-ORDER


ORDER_MAP = REPO / "data/jca_android/order_alphabet_map.csv"


def _rules_root() -> Path:
    if not gh105_order_gate.DEFAULT_RULES.is_dir():
        pytest.skip(f"the api30 oracle is absent: {gh105_order_gate.DEFAULT_RULES}")
    return gh105_order_gate.DEFAULT_RULES


def _order_run():
    return gh105_order_gate.run(_specs_root(), "jca_android", _rules_root(), ORDER_MAP)


def test_the_order_grammar_is_read_with_sequence_weakest():
    """`a, b | c` is `a, (b | c)`, and the Cipher rule depends on it.

    `CrySL.xtext:103-120` makes `Sequence` the outermost production and
    `Alternative` the tighter one, which is the opposite of the regular-expression
    convention the `ere` follows. Cipher is the one rule of the api30 oracle that
    tells the two apart: its ORDER is
    `Gets, Inits+, w+ | (FINWOU | (updates+, DOFINALS))+`, and read as a regular
    expression the right-hand branch stands alone, so a program could finalise
    having never called `getInstance` -- while `g1 i2 f2`, the canonical use, would
    be rejected. The gate read it that way until task 7.1, and reported a
    divergence that was an artifact of its own parser.
    """
    parsed = gh105_order_gate.parse_expression("a, b | c")
    assert parsed == ("cat", (("sym", "a"), ("alt", (("sym", "b"), ("sym", "c")))))
    # The `ere` spells sequence by juxtaposition, where the precedence is the other
    # way round -- one parser, two notations, neither read under the other's rules.
    assert gh105_order_gate.parse_expression("a b | c") == (
        "alt",
        (("cat", (("sym", "a"), ("sym", "b"))), ("sym", "c")),
    )


def test_the_canonical_cipher_use_is_accepted_by_the_api30_order():
    """`g1 i2 f2` -- getInstance, init, doFinal -- is what the rule is for.

    It is the regression the precedence repair exists to catch: under the old
    parse the Cipher ORDER rejected it, because `Gets` and `Inits+` sat in a
    branch the finalising path did not have to pass through.
    """
    rule = gh105_order_gate.read_rule(_rules_root() / "Cipher.cryptsl")
    order = gh105_order_gate.expand_aggregates(
        gh105_order_gate.parse_expression(rule.order), rule.aggregates
    )
    alphabet = tuple(sorted(gh105_order_gate.symbols_of(order)))
    automaton = gh105_order_gate.determinize(
        gh105_order_gate.nfa_of_expression(order), alphabet
    )
    assert gh105_order_gate.accepts(automaton, ("g1", "i2", "f2"))
    assert not gh105_order_gate.accepts(automaton, ("f2",))


def test_an_aggregate_is_expanded_through_every_level_it_names():
    """`Ins := Gets | Cons` over `Gets := g1 | g2 | gI` is two levels deep.

    The SecureRandom rule orders `Ins`, and an `Ins` left unexpanded is a symbol
    the specification's alphabet can never contain -- the comparison would fail
    for a reason that has nothing to do with either language.
    """
    rule = gh105_order_gate.read_rule(_rules_root() / "SecureRandom.cryptsl")
    order = gh105_order_gate.expand_aggregates(
        gh105_order_gate.parse_expression(rule.order), rule.aggregates
    )
    assert gh105_order_gate.symbols_of(order) == {
        "c1",
        "c2",
        "g1",
        "g2",
        "gI",
        "gS",
        "s1",
        "s2",
        "ne",
        "nB",
    }


def test_the_securerandom_kleene_star_is_measured_and_not_argued():
    """The anchored case: `Ins, Seeds?, Ends*` against the automaton.

    The rule accepts `getInstance()` followed by any number of `nextBytes()`, and
    the specification now accepts them too. It did not before task 4.5, for two
    reasons the gate reads together: `end` had no `next2` transition of its own,
    and `end` was not an accepting state, because `alias match1 = init` was the
    file's only alias. Both moved for the same reason -- the rule ensures
    `randomized[genSeed]` and `randomized[next]` at the accepting state the Ends
    reach, so `end` needed the `@match2` handler INV-INS-134 asks for, and
    aliasing it is what tells this gate the state accepts. That is the shape of the
    measured false positive -- 12,400 events, 99.98 % of them inside libraries --
    and this test is what turns it from an argument into a decided question.

    A witness still exists, and it is a different defect: `c1 c1`, the `init`
    self-loop over the constructor, which the rule's `Ins` does not repeat. Task
    7.1 owns it, and this assertion is here so that a later repair of *this*
    automaton cannot pass unnoticed by closing the wrong hole.
    """
    built = gh105_order_gate.build_automata(
        _specs_root() / "jca_android" / "SecureRandomSpec.mop",
        _rules_root(),
        gh105_order_gate.read_map(ORDER_MAP),
    )
    assert not isinstance(built, str), built
    specified, ordered = built

    assert gh105_order_gate.accepts(ordered, ("c1", "nB", "nB"))
    assert gh105_order_gate.accepts(specified, ("c1", "nB", "nB"))
    assert gh105_order_gate.accepts(ordered, ("c1",)) and gh105_order_gate.accepts(
        specified, ("c1",)
    )

    assert gh105_order_gate.accepts(specified, ("c1", "c1"))
    assert not gh105_order_gate.accepts(ordered, ("c1", "c1"))

    witness = gh105_order_gate.difference_witness(specified, ordered)
    assert witness is not None


def test_an_absorbed_accuser_is_erased_from_both_languages():
    """`KeyPairGeneratorSpec` agrees with its rule *because* of the erasure.

    Its `ere` names `g3`, the invalid-algorithm accuser, and the rule's ORDER has
    no symbol for a call it turns down on a constraint. The mapping row records
    the exemption, the gate erases it, and what remains is `(g1|g2)(inits)gen`
    against `Gets, Inits, Generators`. Without the erasure Group 3 could not
    absorb an orphan without turning this gate red.

    Task 3.6 shows the exemption is not the only way to absorb one. `initError`
    was listed here too until that task read the rule: `i3: initialize(keySize)`
    is an `Inits` event whatever size it is handed, and the size bound is a
    CONSTRAINTS clause, so the honest row is the mapping to `i3` and not an
    exemption. Two events standing for one symbol is the non-bijection the map
    already models, and the erased languages are the same either way.
    """
    rows = gh105_order_gate.read_map(ORDER_MAP)["KeyPairGeneratorSpec"]
    exempt = {row.mop_event for row in rows if row.disposition == "order-unmapped"}
    assert exempt == {"g3"}
    assert {row.mop_event for row in rows if row.order_symbol == "i3"} == {
        "init1",
        "initError",
    }
    assert all(row.reason for row in rows if row.disposition == "order-unmapped")

    built = gh105_order_gate.build_automata(
        _specs_root() / "jca_android" / "KeyPairGeneratorSpec.mop",
        _rules_root(),
        gh105_order_gate.read_map(ORDER_MAP),
    )
    assert not isinstance(built, str), built
    assert gh105_order_gate.difference_witness(*built) is None


def test_a_specification_without_a_mapping_is_skipped_and_never_inferred(tmp_path):
    """A missing association is a skip with a reason, not a guess.

    Two ways to have none: a specification with no rows at all, and a specification
    whose rows stop short of an event its automaton names. The second is the
    dangerous one -- there is enough of a mapping to produce a verdict, and the
    verdict would be about an alphabet nobody finished writing down.

    Task 7.1 took the first kind from 13 specifications to 2, which is the whole of
    the census this test used to sample from: it mapped the twelve that translate an
    api30 rule, and what is left are the two that translate none -- RandomStringPassword,
    a bridge over two JDK string conversions, and IvChainJunction, a junction file whose
    `ere` states no ordering at all. Neither can ever gain a row, so the sample here is
    the set's permanent one rather than a backlog.
    """
    result = _order_run()
    skipped = dict(result.skipped)
    assert set(skipped) == {
        "jca_android/RandomStringPassword",
        "jca_android/IvChainJunction",
    }
    assert "no rows in the alphabet mapping" in skipped["jca_android/IvChainJunction"]

    partial = tmp_path / "order_alphabet_map.csv"
    partial.write_text(
        "\n".join(
            line
            for line in ORDER_MAP.read_text(encoding="utf-8").splitlines()
            if not line.startswith("SecureRandomSpec,next2,")
        ),
        encoding="utf-8",
    )
    outcome = gh105_order_gate.build_automata(
        _specs_root() / "jca_android" / "SecureRandomSpec.mop",
        _rules_root(),
        gh105_order_gate.read_map(partial),
    )
    assert isinstance(outcome, str) and "incomplete" in outcome


def test_the_gate_reports_a_word_a_reader_can_check_by_hand():
    """Every finding carries a witness, and the shortest one.

    A verdict of *not equivalent* over two automata is unactionable on its own.
    The product walk is breadth-first so the counterexample that comes back is a
    sequence short enough to read against the rule.
    """
    result = _order_run()
    # Since task 7.6 the set's divergences are allow-listed rather than failing,
    # and an allow-listed row is a finding in every respect except its verdict --
    # it is printed and it carries its witness. Both lists are walked, or the
    # check would go vacuous exactly when the gate went green.
    reported = result.findings + result.allowed
    assert (
        reported
    ), "the set diverges from its rules today; a green run here means the gate stopped looking"
    for finding in reported:
        assert finding.witness or "empty sequence" in finding.message
        assert finding.accepted_by in ("the api30 ORDER", "the specification")


def test_inv_ins_138_gorder(suite):
    """G-ORDER under CI: zero ordering divergences the set has not decided to keep.

    The nine divergences the gate reports over `jca_android` are all allow-listed,
    and the allow-list is the assertion: each row names the witness, the reason and
    task 7.6 that decided it, so the gate itself asserts zero. Two of the nine have
    no repair on the specification's side at all -- the rule orders a symbol no
    monitored program can produce -- and two more are inherited from the frozen
    `jca`, so a run that reported zero *findings and zero allowances* would mean the
    gate stopped looking rather than that the set converged. Both halves are checked
    here for that reason. It also asserts the shape of the run itself: every
    specification is decided or skipped with a reason, and the counts add up to the
    files that exist (INV-INS-140).
    """
    result = _order_run()
    assert result.total == len(list((_specs_root() / "jca_android").glob("*.mop")))
    assert all(reason for _, reason in result.skipped)

    assert result.findings == []
    assert result.allowed, (
        "the set keeps nine ordering divergences on purpose; a run with none means "
        "the gate stopped comparing"
    )


# --------------------------------------------------------------------- INV-INS-143


def _message_gate_report(directory: Path) -> dict:
    """The gh104 message gate over one specification-set directory."""
    import gh104_message_gate

    return gh104_message_gate.check(directory, _crysl_dir())


def _crysl_dir() -> Path:
    rules = Path(_rvsec_home()).parents[0] / "MetaCrySL/generated/api30"
    if not rules.is_dir():
        pytest.skip("the api30 oracle is not present beside the reactor")
    return rules


def test_inv_ins_143_the_not_observed_verdict_has_a_family_of_its_own(tmp_path):
    """A NOT_OBSERVED report is not a violation report, and the codes say so.

    The third verdict says the monitor never saw the producer -- on Android as
    often a reach limit of the instrumentation as a misuse. Filed under the
    violation family it would be counted as a misuse by everything downstream,
    which reads the code out of the envelope and not the branch that emitted it.
    So the gate holds the mapping in both directions: a site admitted by a
    NOT_OBSERVED test carries a code of the not-observed family, and a site
    admitted by a VIOLATED test carries one that is not.

    The set is asserted clean *and* non-vacuous: a gate that skipped the property
    would report the same empty findings as a gate that checked it, so the
    absence of the skip line is the half of this test that proves it ran.
    """
    import shutil

    specs = _specs_root() / "jca_android"
    report = _message_gate_report(specs)
    assert [f for f in report["findings"] if f["kind"] == "not-observed-family"] == []
    assert not [
        reason
        for reason in report["skipped"]
        if reason.startswith("not-observed-family")
    ]

    # the same set with the code re-filed under the violation family: one finding,
    # naming the site rather than the row, because the site is what a reader fixes
    mutated = tmp_path / "jca_android"
    shutil.copytree(specs, mutated)
    codes = mutated / "codes.csv"
    codes.write_text(
        codes.read_text(encoding="utf-8").replace(
            "CIPHER-NOBS-00,UnsatisfiedConstraint,NOBS,",
            "CIPHER-NOBS-00,UnsatisfiedConstraint,CONSTR,",
        ),
        encoding="utf-8",
    )
    findings = [
        f
        for f in _message_gate_report(mutated)["findings"]
        if f["kind"] == "not-observed-family"
    ]
    assert len(findings) == 1, findings
    assert findings[0]["file"] == "CipherSpec.mop"


def test_inv_ins_143_a_predicate_free_set_skips_the_family_check():
    """INV-INS-140 over the new property: no three-valued read, declared skip.

    `generic` calls no predicate substrate at all, so there is no branch to
    classify. The gate says so and counts it, rather than reporting green by
    vacuity -- which would be indistinguishable from a set whose codes are right.
    """
    report = _message_gate_report(_specs_root() / "generic")
    assert any(reason.startswith("not-observed-family") for reason in report["skipped"])

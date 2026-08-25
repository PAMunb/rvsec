package br.unb.cic.rvsec.crysl.core.metric;

import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.model.ObjectDecl;
import br.unb.cic.rvsec.crysl.core.model.Polarity;
import br.unb.cic.rvsec.crysl.core.model.PredicateRef;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Hand-built pairs for the M4 tests.
 *
 * <p>Hand-built rather than lifted, because the properties under test are about the comparison and
 * not about either parser: a test that had to read a corpus to state "arity 2 against arity 1 is a
 * projection" would fail for reasons that have nothing to do with the sentence it asserts.
 */
final class M4Fixtures {

    static final Version MOP = new Version("jca_android",
            new SourceStamp("rvsec", "5fbe8173", Instant.parse("2026-08-24T10:00:00Z")));

    static final Version ORACLE = new Version("CrySL-Rules",
            new SourceStamp("rvsec-cognicrypt", "a1b2c3d4", Instant.parse("2026-08-24T10:00:01Z")));

    private M4Fixtures() {
    }

    /** A rule carrying the three predicate sections and the {@code OBJECTS} the positions need. */
    static SpecModel rule(List<ObjectDecl> objects, List<PredicateRef> ensures,
                          List<PredicateRef> requires, List<PredicateRef> negates) {
        return new SpecModel(ORACLE, "javax.crypto.Cipher", Set.copyOf(objects), List.of(),
                emptyAutomaton(), List.of(), ensures, requires, negates, Set.of(), Map.of());
    }

    static Automaton emptyAutomaton() {
        return new Automaton(Set.of("q0"), "q0", Set.of("q0"), List.of());
    }

    static PredicateRef clause(String name, Polarity polarity, int line, String... arguments) {
        return new PredicateRef(name, List.of(arguments), polarity,
                new Provenance("Cipher.crysl", line));
    }

    static PredicateSiteFacts site(PredicateSiteFacts.Section section, PredicateSubstrate substrate,
                                   String event, PredicateSiteFacts.SiteKind kind, String name,
                                   Polarity polarity, int line, List<String> types,
                                   String... arguments) {
        return new PredicateSiteFacts("CipherSpec.mop", section, substrate, event, kind,
                Optional.empty(), types,
                new PredicateRef(name, List.of(arguments), polarity,
                        new Provenance("CipherSpec.mop", line)));
    }
}

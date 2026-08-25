package br.unb.cic.rvsec.crysl.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * INV-CONF-01: a model that carries no version cannot exist, so no emitter has to trust a caller.
 */
class SpecModelVersionTest {

    private static final Automaton EMPTY_ORDER =
            new Automaton(Set.of("q0"), "q0", Set.of("q0"), List.of());

    private static SpecModel modelWith(Version version) {
        return new SpecModel(version, "javax.crypto.Cipher", Set.of(), List.of(), EMPTY_ORDER,
                List.of(), List.of(), List.of(), List.of(), Set.of(), Map.of());
    }

    @Test
    @DisplayName("INV-CONF-01: a SpecModel cannot be constructed without a version")
    void test_inv_conf_01_version_required() {
        assertThrows(NullPointerException.class, () -> modelWith(null));
    }

    @Test
    @DisplayName("INV-CONF-01: the stamp names the repository the artifact came from")
    void test_inv_conf_01_stamp_names_its_own_repository() {
        Version mop = new Version("jca_android",
                new SourceStamp("rvsec", "5fbe8173", Instant.parse("2026-08-24T00:00:00Z")));
        Version oracle = new Version("CrySL-Rules",
                new SourceStamp("rvsec-cognicrypt", "0ab12cd3", Instant.parse("2026-08-24T00:00:00Z")));

        assertEquals("rvsec", modelWith(mop).version().source().repository());
        assertEquals("rvsec-cognicrypt", modelWith(oracle).version().source().repository());
        // The two models were lifted in the same run and carry different commits: one scalar commit
        // per run is exactly what this shape refuses to represent.
        assertEquals("5fbe8173", modelWith(mop).version().source().commit());
        assertEquals("0ab12cd3", modelWith(oracle).version().source().commit());
    }

    @Test
    @DisplayName("INV-CONF-01: a version without a commit cannot be constructed either")
    void test_inv_conf_01_commit_required() {
        assertThrows(NullPointerException.class,
                () -> new SourceStamp("rvsec", null, Instant.now()));
    }
}

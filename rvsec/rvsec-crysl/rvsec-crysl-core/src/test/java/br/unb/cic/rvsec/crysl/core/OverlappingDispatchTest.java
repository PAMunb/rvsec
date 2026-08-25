package br.unb.cic.rvsec.crysl.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import br.unb.cic.rvsec.crysl.core.model.OverlappingDispatch;
import br.unb.cic.rvsec.crysl.core.model.Provenance;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/** INV-CONF-07: a dispatch overlap must name the labels that overlap. */
class OverlappingDispatchTest {

    private static final Signature INIT = new Signature("javax.crypto.Cipher", "init",
            List.of("int", "java.security.Key", "java.security.spec.AlgorithmParameterSpec",
                    "java.security.SecureRandom"),
            "void");
    private static final Provenance SITE = new Provenance("jca_android/IvChainJunction.mop", 42);

    @Test
    @DisplayName("INV-CONF-07: an overlap with no labels is refused")
    void test_inv_conf_07_labels_required() {
        // A refusal that does not name the overlapping labels does not say how many letters the
        // call emits, which is the only thing the reader needs in order to judge the overlap.
        assertThrows(IllegalArgumentException.class,
                () -> new OverlappingDispatch(List.of(), INIT, SITE));
    }

    @Test
    @DisplayName("INV-CONF-07: the labels are kept in declaration order")
    void test_inv_conf_07_labels_keep_declaration_order() {
        OverlappingDispatch overlap =
                new OverlappingDispatch(List.of("use", "useRandomSpec"), INIT, SITE);

        assertEquals(List.of("use", "useRandomSpec"), overlap.labels());
        assertEquals(SITE, overlap.site());
    }
}

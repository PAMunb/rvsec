package br.unb.cic.rvsec.crysl.crysl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.ApiIndex;
import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SpecModel;
import java.io.IOException;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

/**
 * The API-30 index, and the three absences the conformance report depends on being able to tell
 * apart.
 *
 * <p><strong>Counting rule for {@code classCount}:</strong> one class per {@code .class} entry of
 * {@code android.jar}, nested classes counted separately, no filtering by visibility. API 30 gives
 * 4750 under that rule. A different number means either the SDK moved or the rule did, and the two
 * have to be distinguished before any absence measured through this index can be believed.
 */
@Tag(OracleCorpus.TAG)
class ApiIndexTest {

    private static final int EXPECTED_CLASSES = 4750;

    private static ApiIndex index;

    @BeforeAll
    static void buildIndex() throws IOException {
        index = ApiIndex.index(OracleCorpus.androidJar());
    }

    @Test
    @DisplayName("the API-30 index holds 4750 classes")
    void test_api_30_class_count() {
        assertEquals(EXPECTED_CLASSES, index.classCount(),
                "measured over " + index.source() + ". One class per .class entry, nested classes "
                        + "counted separately.");
    }

    @Test
    @DisplayName("the classes the corpus actually monitors are there")
    void test_the_index_finds_what_is_present() {
        assertTrue(index.hasClass("javax.crypto.Cipher"));
        assertTrue(index.hasClass("javax.crypto.KeyGenerator"));
        assertTrue(index.hasMethod("javax.crypto.KeyGenerator", "generateKey", List.of()));
        assertTrue(index.hasMethod("javax.crypto.Cipher", "getInstance",
                List.of("java.lang.String")));
        assertTrue(index.hasSignature(new Signature("javax.crypto.Cipher", "doFinal",
                List.of("byte[]"), "byte[]")),
                "the return type is not part of the lookup: Java does not overload on it");
    }

    @Test
    @DisplayName("a constructor is findable under the declaring type's simple name")
    void test_constructors_use_the_simple_name() {
        assertTrue(index.hasMethod("javax.crypto.spec.SecretKeySpec", "SecretKeySpec",
                List.of("byte[]", "java.lang.String")),
                "Signature spells a constructor as the type's simple name, and so does CrySL");
        assertTrue(index.hasMethod("javax.crypto.spec.SecretKeySpec", "<init>",
                List.of("byte[]", "java.lang.String")),
                "the bytecode spelling resolves too, so a caller need not know which produced it");
    }

    /**
     * {@code HMACParameterSpecSpec} monitors a class that exists in no verified Android API level.
     * That is a defect of the pointcut, and it is the reason M0 keeps "the class is absent" apart
     * from "the monitor is dead": the monitor is alive and can never fire.
     */
    @Test
    @DisplayName("javax.xml.crypto.dsig.spec.HMACParameterSpec is absent from API 30")
    void test_hmac_parameter_spec_is_absent() {
        assertFalse(index.hasClass("javax.xml.crypto.dsig.spec.HMACParameterSpec"),
                "Android carries no javax.xml.crypto; the class exists in no verified level");
    }

    /** Present in the JDK, added to Android only at API 35 — so absent from the level measured. */
    @Test
    @DisplayName("java.security.spec.DSAGenParameterSpec is absent from API 30")
    void test_dsa_gen_parameter_spec_is_absent() {
        assertFalse(index.hasClass("java.security.spec.DSAGenParameterSpec"));
    }

    /**
     * The declared limitation, asserted so that it stays declared.
     *
     * <p>{@code javax.crypto.SecretKey} is present and {@code destroy()} is callable on it — it is
     * inherited from {@code javax.security.auth.Destroyable}. The index records declared members
     * only and does not walk the hierarchy, so the lookup misses. Six upstream signature lines fall
     * into this bucket, and the report must present them as a limitation of the checker rather than
     * as an absence in the platform: those are opposite findings.
     */
    @Test
    @DisplayName("inherited members do not resolve, and that is a limitation of the checker")
    void test_inheritance_is_not_followed() {
        assertTrue(index.hasClass("javax.crypto.SecretKey"));
        assertTrue(index.hasClass("javax.security.auth.Destroyable"));
        assertTrue(index.hasMethod("javax.security.auth.Destroyable", "destroy", List.of()),
                "the platform does declare destroy(), on the interface SecretKey extends");
        assertFalse(index.hasMethod("javax.crypto.SecretKey", "destroy", List.of()),
                "SecretKey does not declare destroy(); it inherits it. The index does not follow "
                        + "inheritance, so this miss is the checker's limit and not the platform's.");
    }

    @Test
    @DisplayName("arity-only lookup is a separate, weaker answer")
    void test_arity_lookup_is_kept_apart_from_exact_lookup() {
        assertTrue(index.hasMethodWithArity("javax.crypto.Cipher", "init", 2));
        assertFalse(index.hasMethod("javax.crypto.Cipher", "init",
                List.of("int", "AnyType")),
                "a CrySL parameter written AnyType cannot match exactly by construction, which is "
                        + "why it must not be counted with the exact matches");
        assertTrue(index.hasSignatureWithArity(new Signature("javax.crypto.Cipher", "init",
                List.of("int", "AnyType"), "void")));
    }

    /**
     * The index's counting rule, checked against the whole oracle rather than against six chosen
     * names.
     *
     * <p>D-09 decomposes the 215 upstream signature lines as {@code 175 exact + 29 arity-only +
     * 5 absent-class + 6 inheritance limitations}, and that decomposition was produced by a route
     * this class did not write. Reproducing all four buckets is what says the lookup here means the
     * same thing the design means; a test that only checks three named absences would pass just as
     * well with a subtly different notion of "declared".
     *
     * <p><strong>Counting rule:</strong> every {@code Signature} of every event of the 47 rules that
     * lift, classified in this order — exact hit; else the declaring class is absent; else an
     * arity-only hit; else neither, which is the inheritance bucket. The order matters: an absent
     * class cannot produce an arity hit, and counting it as one would hide a platform absence
     * behind a checker limitation.
     */
    @Test
    @DisplayName("the 215 upstream signature lines decompose as 175 + 29 + 5 + 6")
    void test_signature_resolution_decomposes_as_the_design_measured_it() throws IOException {
        CryslLifter.CorpusLift lift =
                new CryslLifter().liftCorpus(OracleCorpus.cryslRules(), OracleCorpus.version());

        int exact = 0;
        int absentClass = 0;
        int arityOnly = 0;
        List<String> inherited = new java.util.ArrayList<>();
        for (SpecModel model : lift.models()) {
            for (Event event : model.events()) {
                for (Signature signature : event.signatures()) {
                    if (index.hasSignature(signature)) {
                        exact++;
                    } else if (!index.hasClass(signature.declaringType())) {
                        absentClass++;
                    } else if (index.hasSignatureWithArity(signature)) {
                        arityOnly++;
                    } else {
                        inherited.add(signature.declaringType() + "." + signature.name()
                                + signature.paramTypes());
                    }
                }
            }
        }

        assertEquals(215, exact + arityOnly + absentClass + inherited.size());
        assertEquals(175, exact);
        assertEquals(29, arityOnly);
        assertEquals(5, absentClass);
        assertEquals(List.of(
                        "java.security.DigestInputStream.close[]",
                        "java.security.DigestOutputStream.close[]",
                        "java.security.SecureRandom.nextInt[]",
                        "java.security.SecureRandom.nextInt[int]",
                        "javax.crypto.SecretKey.destroy[]",
                        "javax.crypto.SecretKey.getEncoded[]"),
                inherited.stream().sorted().toList(),
                "each of these is declared on a supertype and inherited by the class the rule names. "
                        + "They are limitations of this checker, not absences in the platform, and "
                        + "the report must not merge them with the five absent classes.");
    }

    @Test
    @DisplayName("an unknown class answers no rather than throwing")
    void test_unknown_class_is_a_plain_absence() {
        assertFalse(index.hasClass("no.such.Class"));
        assertFalse(index.hasMethod("no.such.Class", "anything", List.of()));
        assertFalse(index.hasMethodWithArity("no.such.Class", "anything", 0));
    }
}

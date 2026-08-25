package br.unb.cic.rvsec.crysl.mop;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.ApiIndex;
import br.unb.cic.rvsec.crysl.core.CiTags;
import br.unb.cic.rvsec.crysl.core.automata.Automaton;
import br.unb.cic.rvsec.crysl.core.metric.AstChecker;
import br.unb.cic.rvsec.crysl.core.metric.M2Result;
import br.unb.cic.rvsec.crysl.core.metric.MisuseAbsorption;
import br.unb.cic.rvsec.crysl.core.model.Normalization;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The two layers, and the demonstration that the split between them is not an assertion.
 *
 * <p>Layer 1 is the gate and Layer 2 is evidence, and the whole justification for that asymmetry is
 * that Layer 2 provably cannot see two defects. Two tests here show it happening on real corpus
 * files rather than restating design D-12: one where Layer 1 fails a generated specification whose
 * languages Layer 2 calls {@code EQUIVALENT}, and one where two specifications differing only in a
 * handler have byte-identical order automata while only one of them draws a violation.
 */
class RoundTripGateTest {

    /** The three specifications the round trip is asserted over, with the formalism of each. */
    private static final List<String[]> FORMALISMS = List.of(
            new String[] {"PBEKeySpecSpec.mop", "ere"},
            new String[] {"RandomStringPassword.mop", "ere"},
            new String[] {"CipherSpec.mop", "fsm"});

    private static MopLift lift(String corpus, String name) throws Exception {
        return new MopLifter().read(Corpora.file(corpus, name), Corpora.version(corpus));
    }

    /** The specification's own order automaton, standing in for a rule that denotes the same set. */
    private static RoundTripGate.LanguageOracle sameLanguageAs(MopLift lift, String rule) {
        return new RoundTripGate.LanguageOracle(rule, lift.model().order(), List.of());
    }

    @Test
    @DisplayName("11.9: the round trip is faithful over three real specifications, two ere one fsm")
    void test_round_trip_over_three_real_specifications(@TempDir Path out) throws Exception {
        for (String[] fixture : FORMALISMS) {
            String source = Files.readString(Corpora.file("jca", fixture[0]));
            assertTrue(source.contains(fixture[1] + " :") || source.contains(fixture[1] + ":"),
                    fixture[0] + " no longer declares a " + fixture[1] + "; the point of this test "
                            + "is that both formalisms survive, so the fixture has to keep being "
                            + "one of each");

            RoundTripGate.Report report = RoundTripGate.run(lift("jca", fixture[0]), out,
                    Optional.empty(), Optional.empty());

            assertTrue(report.faithful(), fixture[0] + " (" + fixture[1] + ") did not survive the "
                    + "round trip. Disagreements, per field: " + report.roundTrip());
        }
    }

    @Test
    @DisplayName("11.6: every jca specification round-trips, and a disagreement names its field")
    void test_the_whole_jca_corpus_round_trips(@TempDir Path out) throws Exception {
        for (Path file : Corpora.filesOf("jca")) {
            MopLift lift = new MopLifter().read(file, Corpora.version("jca"));
            RoundTripGate.Report report =
                    RoundTripGate.run(lift, out, Optional.empty(), Optional.empty());

            // The failure message is the point of the per-field list: a boolean would say a file
            // changed and say nothing about where to look.
            assertTrue(report.faithful(), file.getFileName() + " disagrees on "
                    + report.roundTrip().stream().map(RoundTripGate.Disagreement::field).toList()
                    + ": " + report.roundTrip());
        }
    }

    @Test
    @DisplayName("11.6: a disagreement carries the field and both sides, never a bare boolean")
    void test_a_disagreement_names_the_field_and_both_sides() {
        RoundTripGate.Disagreement disagreement =
                new RoundTripGate.Disagreement("events[3]", "g3", "g4");

        assertEquals("events[3]", disagreement.field(),
                "a list field must be reported indexed, so the reader knows which element moved");
        assertTrue(disagreement.toString().contains("g3") && disagreement.toString().contains("g4"),
                "both sides have to be in the line; one side alone is not actionable");
    }

    @Test
    @DisplayName("11.7: Layer 1 fails an event absent from the ere that Layer 2 calls equivalent")
    void test_layer1_catches_what_language_equivalence_cannot(@TempDir Path out) throws Exception {
        MopLift lift = lift("jca", "PBEKeySpecSpec.mop");

        RoundTripGate.Report report = RoundTripGate.run(lift, out, Optional.empty(),
                Optional.of(sameLanguageAs(lift, "PBEKeySpec.crysl")));

        assertEquals(M2Result.Verdict.EQUIVALENT, report.layer2().orElseThrow().verdict(),
                "Layer 2 is supposed to see nothing here; if it now sees a difference this test no "
                        + "longer demonstrates anything");
        assertFalse(report.passed(),
                "Layer 1 must fail the generation even though Layer 2 found the languages equal");
        for (String event : List.of("f1", "f2", "err1", "err2", "err3")) {
            assertTrue(report.layer1().stream().anyMatch(line -> line.contains("'" + event + "'")
                            && line.contains("absent from the formula")),
                    "PBEKeySpecSpec declares " + event + " and its ere is 'c1 c2', so the event is "
                            + "observed and the automaton never reads it. Layer 1 said: "
                            + report.layer1());
        }
    }

    @Test
    @DisplayName("11.5: an event absent from the formula contributes no letter, so it is invisible")
    void test_the_absent_event_is_outside_the_language_altogether(@TempDir Path out)
            throws Exception {
        MopLift lift = lift("jca", "PBEKeySpecSpec.mop");
        RoundTripGate.Report report = RoundTripGate.run(lift, out, Optional.empty(),
                Optional.of(sameLanguageAs(lift, "PBEKeySpec.crysl")));

        // f1 observes PBEKeySpec.new(char[]), which no other event names. Its signature is not a
        // letter of the order automaton at all, because the preimage builds an edge only where the
        // label automaton can follow the label - and 'f1' appears in no transition of the ere. That
        // is why the defect is local: nothing about the language changes when the event is added or
        // removed, so no comparison of languages can find it.
        Automaton order = lift.model().order();
        assertTrue(order.alphabet().stream().noneMatch(RoundTripGateTest::isSingleCharConstructor),
                "PBEKeySpec.new(char[]) is a letter of the order automaton, so f1 is visible to a "
                        + "language comparison after all and this witness has stopped being one");
        assertEquals(M2Result.Verdict.EQUIVALENT, report.layer2().orElseThrow().verdict());
        assertFalse(report.passed(), "only Layer 1 can see it, and it must");
    }

    private static boolean isSingleCharConstructor(Signature signature) {
        return signature.name().equals("PBEKeySpec") && signature.paramTypes().equals(List.of("char[]"));
    }

    @Test
    @DisplayName("11.5: two specifications differing only in the handler have identical languages")
    void test_match_without_fail_is_invisible_to_the_language(@TempDir Path out) throws Exception {
        // SecretKeySpec.mop and RandomStringPassword.mop both declare a @match and no @fail today,
        // which is a specification that compiles, runs and never accuses. It is the reason M0
        // refuses SecretKeySpec.mop, and this group agrees with M0 rather than re-deriving it.
        for (String witness : List.of("SecretKeySpec.mop", "RandomStringPassword.mop")) {
            MopLift lift = lift("jca", witness);
            assertTrue(lift.handlers().keySet().stream().anyMatch(k -> k.startsWith("match")),
                    witness + " no longer declares a @match");
            assertFalse(lift.handlers().containsKey("fail"),
                    witness + " now declares a @fail, so it has stopped being the witness");

            RoundTripGate.Report report =
                    RoundTripGate.run(lift, out, Optional.empty(), Optional.empty());
            assertTrue(report.layer1().stream().anyMatch(line -> line.contains("no @fail")),
                    "Layer 1 must say the specification reacts when the word is accepted and says "
                            + "nothing when it is rejected. It said: " + report.layer1());

            // The same generated file with one handler added. Everything else is byte-identical, so
            // the two files denote the same language by construction - which is exactly why an
            // equivalence gate cannot separate them, and why this failure mode belongs to Layer 1.
            Path withFail = out.resolve("withFail-" + witness);
            String generated = Files.readString(report.generated());
            Files.writeString(withFail, generated.substring(0, generated.lastIndexOf('}'))
                    + "@fail {\n  __RESET;\n}\n}\n");
            MopLift repaired = new MopLifter().read(withFail, Corpora.version("jca"));

            assertEquals(lift.model().order(), repaired.model().order(),
                    "adding a handler must not move the language; if it did, the two files differ "
                            + "in more than the handler and this is not the demonstration it claims");
            assertTrue(AstChecker.check(witness, repaired.model(), repaired.labelOrder(),
                            repaired.monitorFacts(
                                    MisuseAbsorption.scan(withFail)))
                            .stream().noneMatch(line -> line.contains("no @fail")),
                    "the repaired file must no longer draw the handler violation, which is what "
                            + "makes the pair a pair");
        }
    }

    @Test
    @DisplayName("11.4: Layer 2 is evidence - a clean generation passes with the languages apart")
    void test_layer2_never_decides(@TempDir Path out) throws Exception {
        MopLift lift = lift("jca", "HMACParameterSpecSpec.mop");
        Normalization erasure = new Normalization("N1",
                "the unmapped event was erased on the authority of the alphabet map");
        // A rule that accepts nothing: the empty language over one state, which shares no word with
        // the specification's. Layer 2 therefore has everything to say and still decides nothing.
        Automaton nothing = new Automaton(Set.of("q0"), "q0", Set.of(),
                List.of());

        RoundTripGate.Report report = RoundTripGate.run(lift, out, Optional.empty(),
                Optional.of(new RoundTripGate.LanguageOracle("HMACParameterSpec.crysl", nothing,
                        List.of(erasure))));

        assertTrue(report.passed(), "Layer 1 is clean on this file, so the gate passes whatever "
                + "Layer 2 saw. Layer 1 said: " + report.layer1());
        RoundTripGate.Evidence evidence = report.layer2().orElseThrow();
        assertEquals(M2Result.Verdict.MOP_MORE_PERMISSIVE, evidence.verdict());
        assertEquals(List.of(erasure), evidence.normalizations(),
                "the normalizations travel beside the verdict: 'more permissive under N1' and "
                        + "'more permissive' are different claims");
        assertTrue(evidence.witness().isPresent()
                        && evidence.witness().get().normalizations().equals(List.of(erasure)),
                "a witness that cannot say what it was compared modulo must not be published "
                        + "(INV-CONF-08)");
        assertTrue(RoundTripGate.LAYER_2_STANDING.contains("never decides"));
    }

    @Test
    @DisplayName("11.3: Layer 1 is M0's checker over the generated tree, not a second copy of it")
    void test_layer1_reuses_the_m0_checker() {
        assertTrue(RoundTripGate.LAYER_1_RULE.contains(AstChecker.RULE),
                "the four non-normalized checks are AstChecker's own rule, quoted whole. A Layer 1 "
                        + "that restated the rule in its own words would be a second checker, and "
                        + "the two would drift");
        assertTrue(RoundTripGate.LAYER_2_BLIND_SPOTS.contains("PBEKeySpecSpec.mop:26-32")
                        && RoundTripGate.LAYER_2_BLIND_SPOTS.contains("SecretKeySpec.mop")
                        && RoundTripGate.LAYER_2_BLIND_SPOTS.contains("RandomStringPassword.mop"),
                "the two failure modes are recorded with the corpus files that show them, so that "
                        + "the justification for the split is checkable and not a claim");
    }

    @Test
    @DisplayName("without an index the fifth check does not run, and the report says so")
    void test_the_missing_index_is_reported_as_not_checked(@TempDir Path out) throws Exception {
        RoundTripGate.Report report = RoundTripGate.run(lift("jca", "HMACParameterSpecSpec.mop"),
                out, Optional.empty(), Optional.empty());

        assertTrue(report.notes().contains(RoundTripGate.NO_INDEX_NOTE),
                "silence about a check that did not run reads as a check that passed");
        assertTrue(report.passed());
    }

    @Test
    @Tag(CiTags.ORACLE_DEPENDENT)
    @DisplayName("11.3: the fifth check resolves the generated pointcuts against android.jar")
    void test_the_fifth_check_resolves_pointcuts(@TempDir Path out) throws Exception {
        ApiIndex index = ApiIndex.index(androidJar());

        RoundTripGate.Report absent = RoundTripGate.run(lift("jca", "HMACParameterSpecSpec.mop"),
                out, Optional.of(index), Optional.empty());
        assertFalse(absent.passed(), "javax.xml.crypto.dsig.spec.HMACParameterSpec is absent from "
                + "every Android level (design D-09), so the generated pointcut names a call the "
                + "platform cannot make. Layer 1 said: " + absent.layer1());
        assertTrue(absent.layer1().stream()
                        .anyMatch(line -> line.contains(RoundTripGate.ABSENT_CLASS)),
                "the violation has to carry M0.3's own mode: " + absent.layer1());

        RoundTripGate.Report present = RoundTripGate.run(lift("jca", "SecureRandomSpec.mop"),
                out, Optional.of(index), Optional.empty());
        assertTrue(present.layer1().stream()
                        .noneMatch(line -> line.contains(RoundTripGate.ABSENT_CLASS)),
                "java.security.SecureRandom is on the platform, so no resolution violation is "
                        + "expected here. Layer 1 said: " + present.layer1());
    }

    /** {@code $ANDROID_HOME/platforms/android-30/android.jar}, or the test is skipped. */
    private static Path androidJar() {
        String override = System.getenv("RVSEC_ANDROID_JAR");
        Path jar = override != null && !override.isBlank() ? Paths.get(override)
                : Paths.get(String.valueOf(System.getenv("ANDROID_HOME")), "platforms",
                        "android-30", "android.jar");
        Assumptions.assumeTrue(Files.isReadable(jar), "android.jar for android-30 was not found. "
                + "It comes from the Android SDK, which is not part of this checkout. Set "
                + "ANDROID_HOME or RVSEC_ANDROID_JAR. Looked at " + jar.toAbsolutePath());
        return jar;
    }
}

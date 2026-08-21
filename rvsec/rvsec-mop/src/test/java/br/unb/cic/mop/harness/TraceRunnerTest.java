package br.unb.cic.mop.harness;

import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.PredicateStore;
import br.unb.cic.mop.PredicateVerdict;
import br.unb.cic.mop.Property;

import org.junit.Assume;
import org.junit.BeforeClass;
import org.junit.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * The self-test of the trace runner, against the frozen control snapshot.
 *
 * <p>
 * It asserts the two facts the whole differential harness rests on, and nothing about how many
 * accusations a specification happens to produce -- an assertion of that kind would freeze a
 * measurement into a test and fail every time a repair lands, which is the opposite of what a
 * harness is for.
 *
 * <ol>
 * <li>Every line of every committed trace resolves to at least one advice of the snapshot. A
 * trace line that resolves to nothing is reported as "not accused", and that reading is
 * indistinguishable from "not replayed" -- which is exactly the failure a differential harness
 * must never make silently.
 * <li>The two traces the self-test's classifier is calibrated on behave as the frozen set does:
 * {@code getInstance("X509"); init(ks)} is accused at {@code g3}, and the legitimate
 * {@code getInstance("PKIX"); init(ks)} is not accused at all.
 * <li>The finding the harness produced on its first run: adding {@code getTrustManagers()} to
 * that legitimate sequence makes the frozen set accuse it, through a binding defect rather than
 * an automaton one. See the test that pins it.
 * </ol>
 *
 * <p>
 * The snapshot is the 2026-08-08 frozen control, not {@code results/gh56-smoke/}: that one
 * predates the freeze by three months and two source fixes. The path is overridable with
 * {@code -Dgh104.monitorDir=}; when it is absent the test is skipped with its reason rather
 * than passing on nothing.
 */
public class TraceRunnerTest {

    private static final String DEFAULT_MONITOR_DIR =
            "../../rv-android/results/gh101_group8_jca_frozen_control/monitors";
    private static final String DEFAULT_TRACES_DIR = "../../rv-android/data/gh104/traces";

    private static Path monitorDir;
    private static Path tracesDir;
    private static Path workDir;

    @BeforeClass
    public static void locate() throws Exception {
        monitorDir = Paths.get(System.getProperty("gh104.monitorDir", DEFAULT_MONITOR_DIR))
                .toAbsolutePath().normalize();
        tracesDir = Paths.get(System.getProperty("gh104.tracesDir", DEFAULT_TRACES_DIR))
                .toAbsolutePath().normalize();
        workDir = Paths.get("target", "gh104-harness").toAbsolutePath();

        Assume.assumeTrue(
                "control monitor absent: " + monitorDir + "; regenerate per data/gh104/README.md",
                Files.isRegularFile(monitorDir.resolve("MultiSpec_1RuntimeMonitor.java")));
        Assume.assumeTrue("traces absent: " + tracesDir, Files.isDirectory(tracesDir));
        Files.createDirectories(workDir);
    }

    @Test
    public void everyTraceLineResolvesToAnAdvice() throws Exception {
        List<Path> traces = traces();
        StringBuilder unresolved = new StringBuilder();
        try (TraceRunner runner = TraceRunner.of(monitorDir, workDir.resolve("control"))) {
            for (Path trace : traces) {
                TraceRunner.Outcome outcome = runner.replay(trace);
                for (String line : outcome.unresolved) {
                    unresolved.append(trace.getFileName()).append(": ").append(line).append('\n');
                }
            }
        }
        assertEquals("trace lines that no pointcut of the frozen snapshot resolves:\n"
                + unresolved, 0, unresolved.length());
    }

    @Test
    public void theX509TraceIsAccusedAndTheLegitimatePkixTraceIsNot() throws Exception {
        try (TraceRunner runner = TraceRunner.of(monitorDir, workDir.resolve("control"))) {
            TraceRunner.Outcome x509 =
                    runner.replay(tracesDir.resolve("TrustManagerFactorySpec-x509.txt"));
            assertTrue("the frozen set must accuse getInstance(\"X509\"); its allow-list is "
                    + "{PKIX, SunX509} and X509 is what Conscrypt registers", x509.accused);
            assertTrue("the accusation must name g3 and init: " + x509.accusingEvents,
                    x509.accusingEvents.contains("TrustManagerFactorySpec.g3"));

            TraceRunner.Outcome pkix =
                    runner.replay(tracesDir.resolve("TrustManagerFactorySpec-pkix-init.txt"));
            assertFalse("a legitimate PKIX sequence must be accused by no snapshot; accused at "
                    + pkix.accusingEvents, pkix.accused);
        }
    }

    /**
     * A finding of the harness, pinned so that a repair cannot land unnoticed.
     *
     * <p>
     * {@code getInstance("PKIX"); init(ks); getTrustManagers()} is a legitimate sequence and the
     * frozen set accuses it, at {@code gtm1}, with {@code InvalidSequenceOfMethodCalls}. The
     * cause is a binding defect rather than the automaton: {@code gtm1} is declared
     * {@code target(k)} while the specification's parameter is {@code mf}
     * ({@code TrustManagerFactorySpec.mop:60}), so the generator puts it in the empty parameter
     * slice -- {@code TrustManagerFactorySpec__Map} -- where the monitor is still in the initial
     * state and {@code gtm1}'s row sends state 0 to {@code fail}. The two events before it
     * updated the {@code mf}-keyed monitor and this one never saw them.
     *
     * <p>
     * The design's scenario for this trace says both snapshots must report no accusation. On the
     * frozen set that is false today, and the successor set is where it becomes true. When it
     * does, this test fails and is deleted with the finding it records.
     */
    @Test
    public void theFrozenSetAccusesALegitimateGetTrustManagersThroughABindingDefect()
            throws Exception {
        try (TraceRunner runner = TraceRunner.of(monitorDir, workDir.resolve("control"))) {
            TraceRunner.Outcome outcome =
                    runner.replay(tracesDir.resolve("TrustManagerFactorySpec.txt"));
            assertTrue("gtm1 binds target(k), not the specification parameter mf, so it lands "
                    + "in the empty slice and accuses from state 0", outcome.accused);
            assertTrue("the accusation must be at gtm1: " + outcome.accusingEvents,
                    outcome.accusingEvents.contains("TrustManagerFactorySpec.gtm1"));
        }
    }

    @Test
    public void everySpecificationOfTheFrozenSetHasATrace() throws Exception {
        List<String> names = traces().stream()
                .map(path -> path.getFileName().toString().replace(".txt", ""))
                .map(name -> name.contains("-") ? name.substring(0, name.indexOf('-')) : name)
                .distinct().sorted().collect(Collectors.toList());
        assertEquals("one trace per specification of the frozen set, including the two the "
                + "successor set drops -- a comparison with no trace on one side classifies "
                + "nothing: " + names, 23, names.size());
    }

    /**
     * A replay starts from an empty predicate substrate, and the violating half of a pair is
     * still accused after the satisfying half ran before it.
     *
     * <p>
     * {@code replay()} rebuilds a class loader for the monitor classes, which is what makes each
     * trace see a fresh automaton. It does nothing for the predicate stores: both sit on
     * {@code java.class.path}, so parent-first delegation hands every trace of a directory replay
     * the same singleton. That is the same reason {@code ErrorCollector} needed an explicit reset,
     * and the consequence lands on the one thing the differential harness uses as evidence -- a
     * satisfying trace's mark silently satisfies the violating trace that follows it, and the pair
     * reports a pass it did not earn.
     *
     * <p>
     * The marks are planted from here rather than harvested from the satisfying trace because the
     * objects a trace binds are freshly allocated inside {@code replay()} and never escape it. A
     * planted mark is the same contamination the shared singleton produces, on an object this test
     * can name -- and it fails this assertion whenever the resets are removed, which harvesting
     * from a trace of byte arrays would not.
     */
    @Test
    public void aReplayStartsFromAnEmptySubstrateSoOneTraceCannotSatisfyTheNext() throws Exception {
        Object legacyMark = new Object();
        Object storeMark = new Object();

        try (TraceRunner runner = TraceRunner.of(monitorDir, workDir.resolve("control"))) {
            TraceRunner.Outcome satisfying =
                    runner.replay(tracesDir.resolve("IvParameterSpecSpec.txt"));
            assertFalse("an IV randomised before the constructor must be accused by nothing: "
                    + satisfying.accusingEvents, satisfying.accused);

            ExecutionContext.instance().setProperty(Property.RANDOMIZED, legacyMark);
            PredicateStore.instance().ensure(Property.RANDOMIZED, storeMark);

            TraceRunner.Outcome violating =
                    runner.replay(tracesDir.resolve("IvParameterSpecSpec-unrandomised.txt"));
            assertTrue("an IV nothing randomised must still be accused after a satisfying trace "
                    + "ran before it: " + violating.accusingEvents, violating.accused);

            assertFalse("replay() must clear the legacy substrate, not only the error sink",
                    ExecutionContext.instance().validate(Property.RANDOMIZED, legacyMark));
            assertEquals("replay() must clear the jca_android predicate store as well",
                    PredicateVerdict.NOT_OBSERVED,
                    PredicateStore.instance().validate(Property.RANDOMIZED, storeMark));
        }
    }

    /**
     * An {@code Integer} argument matches a declared type that accepts it, and only such a type.
     *
     * <p>
     * A trace has no way to say whether {@code 3072} was written as a primitive or as a box, so
     * {@link #literal} produces an {@code Integer} either way and {@code fitsPointcut} decides
     * which pointcut it fits. That decision used to be made by a blanket rule -- an
     * {@code Integer} fits no reference type at all -- which is right for
     * {@code initialize(AlgorithmParameterSpec)} and wrong for {@code String.valueOf(Object)},
     * and the second is a pointcut the set actually declares. A line it refuses resolves to
     * nothing, and an unreplayed line is reported as an unaccused one, which is the single
     * reading this harness exists to prevent.
     *
     * <p>
     * Both directions are pinned here because only one of them was ever wrong, and a repair that
     * fixed the second by breaking the first would leave the same suite green.
     */
    @Test
    public void anIntegerFitsAPointcutDeclaringObjectAndNotOneDeclaringAnUnrelatedType()
            throws Exception {
        try (TraceRunner runner = TraceRunner.of(monitorDir, workDir.resolve("control"))) {
            TraceRunner.Outcome bridge =
                    runner.replay(tracesDir.resolve("RandomStringPasswordSpec-int-route.txt"));
            assertEquals("String.valueOf(Object) must resolve for an Integer argument; an "
                    + "unresolved line here reads as 'not accused' and means 'not replayed': "
                    + bridge.unresolved, 0, bridge.unresolved.size());

            TraceRunner.Outcome keySize =
                    runner.replay(tracesDir.resolve("KeyPairGeneratorSpec-rsa3072.txt"));
            assertTrue("initialize(3072) must reach the int events and not "
                    + "initialize(AlgorithmParameterSpec): " + keySize.accusingEvents,
                    keySize.accusingEvents.stream()
                            .noneMatch(event -> event.endsWith(".init3")
                                    || event.endsWith(".init4")));
            assertEquals("and it must resolve: " + keySize.unresolved,
                    0, keySize.unresolved.size());
        }
    }

    private static List<Path> traces() throws Exception {
        try (Stream<Path> list = Files.list(tracesDir)) {
            return list.filter(path -> path.toString().endsWith(".txt")).sorted()
                    .collect(Collectors.toList());
        }
    }
}

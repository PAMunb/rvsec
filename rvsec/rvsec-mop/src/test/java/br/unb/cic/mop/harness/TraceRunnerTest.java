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
import java.util.Arrays;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static java.util.Collections.emptySet;

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

    /**
     * Specifications the traces directory serves that the frozen control does not carry.
     *
     * <p>
     * One directory of traces feeds both sides of every comparison, so it holds traces for
     * specifications only the successor set has. {@code IvChainJunction} is gh105's junction
     * specification; the frozen `jca` has no such file.
     */
    private static final List<String> SUCCESSOR_ONLY_SPECIFICATIONS =
            Arrays.asList("IvChainJunctionSpec");

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

    /**
     * Every trace line resolves to an advice, except at the sites the frozen set has dead.
     *
     * <p>
     * The assertion is the one the harness rests on: a line that resolves to nothing is reported
     * "not accused", and that reading is indistinguishable from "not replayed". It held
     * unconditionally until {@code bdc027a6} taught the runner to read return types, at which
     * point four sites of the frozen control stopped matching -- correctly, because they never
     * could have matched a real call, which is exactly what makes them the defects gh104
     * catalogues. Asserting zero after that is asserting the frozen set has no dead pointcuts,
     * which is false and is the whole reason the successor set exists.
     *
     * <p>
     * So the exceptions are enumerated with their reason, in the idiom the gate allow-lists use:
     * an entry without a reason allows nothing, and any unresolved line outside this list still
     * fails. Three of the four are dead pointcuts and the fourth is an advice that resolves and
     * throws; none may be added to without naming the specification line it comes from.
     */
    private static final List<String[]> DEAD_IN_THE_FROZEN_CONTROL = Arrays.asList(
            new String[] {".getTrustManagers()",
                "TrustManagerFactorySpec.mop:63 declares gtm1 returning(TrustManager[][]) while "
                + "TrustManagerFactory.getTrustManagers() returns TrustManager[], so no call can "
                + "match it (design D-1, measured and not repaired)"},
            new String[] {".createSSLEngine()",
                "SSLContextSpec.mop:64 is a dead pointcut (design D-1, measured and not "
                + "repaired)"},
            new String[] {".sign()",
                "SignatureSpec.mop:99,:106 declare sign() returning byte where javap on "
                + "android-30 gives byte[] and int; repaired in the successor set, dead here"},
            new String[] {".initialize(",
                "KeyPairGeneratorSpec.mop:26 leaves String algorithm uninitialised, so validate() "
                + "switches on null and the advice throws rather than failing to match; the "
                + "successor set conditions the initialize events on algorithm != null"});

    @Test
    public void everyTraceLineResolvesToAnAdviceExceptWhereTheFrozenSetIsDead() throws Exception {
        StringBuilder unresolved = new StringBuilder();
        try (TraceRunner runner = TraceRunner.of(monitorDir, workDir.resolve("control"))) {
            for (Path trace : traces()) {
                TraceRunner.Outcome outcome = runner.replay(trace);
                for (String line : outcome.unresolved) {
                    if (allowedDeadSite(line) == null) {
                        unresolved.append(trace.getFileName()).append(": ")
                                .append(line).append('\n');
                    }
                }
            }
        }
        assertEquals("trace lines that no pointcut of the frozen snapshot resolves, and that no "
                + "dead site of the frozen control accounts for:\n" + unresolved,
                0, unresolved.length());
    }

    /** The reason the frozen control cannot replay this line, or {@code null} if it has none. */
    private static String allowedDeadSite(String line) {
        for (String[] entry : DEAD_IN_THE_FROZEN_CONTROL) {
            if (line.contains(entry[0]) && !entry[1].isEmpty()) {
                return entry[1];
            }
        }
        return null;
    }

    /**
     * The allow-list above stays honest only while every entry still fires.
     *
     * <p>
     * An entry that stops matching means the site was revived -- by a repair, or by the control
     * being regenerated -- and a dead-site exception that no longer describes anything is how a
     * suppression outlives the defect it was written for.
     */
    @Test
    public void everyDeadSiteExceptionStillDescribesAnUnresolvedLine() throws Exception {
        Set<String> fired = new TreeSet<>();
        try (TraceRunner runner = TraceRunner.of(monitorDir, workDir.resolve("control"))) {
            for (Path trace : traces()) {
                for (String line : runner.replay(trace).unresolved) {
                    for (String[] entry : DEAD_IN_THE_FROZEN_CONTROL) {
                        if (line.contains(entry[0])) {
                            fired.add(entry[0]);
                        }
                    }
                }
            }
        }
        Set<String> stale = new TreeSet<>();
        for (String[] entry : DEAD_IN_THE_FROZEN_CONTROL) {
            stale.add(entry[0]);
        }
        stale.removeAll(fired);
        assertEquals("dead-site exceptions that no unresolved line needs any more -- the site "
                + "was revived and the exception outlived it", emptySet(), stale);
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
     * Two defects sit on {@code gtm1}, and the outer one hides the inner.
     *
     * <p>
     * This test was written to pin a harness finding: {@code getInstance("PKIX"); init(ks);
     * getTrustManagers()} is a legitimate sequence and the frozen set accused it at
     * {@code gtm1}, through a binding defect rather than the automaton -- {@code gtm1} is
     * declared {@code target(k)} while the specification's parameter is {@code mf}
     * ({@code TrustManagerFactorySpec.mop:60}), so the generator files it in the empty parameter
     * slice, {@code TrustManagerFactorySpec__Map}, where the monitor is still in its initial
     * state and {@code gtm1}'s row sends state 0 to {@code fail}.
     *
     * <p>
     * That accusation is no longer observable, and the reason is not a repair. {@code gtm1} is
     * also declared {@code returning(TrustManager[][])} ({@code TrustManagerFactorySpec.mop:63})
     * where {@code TrustManagerFactory.getTrustManagers()} returns {@code TrustManager[]}, so
     * once the runner learned to read return types ({@code bdc027a6}) no call could match it at
     * all. The binding defect is still in the frozen monitor; nothing can reach it from a real
     * call. The design says as much -- "any measurement of its revival exercises an
     * empty-binding broadcast, not the per-object row" -- and this is that statement executed.
     *
     * <p>
     * What is pinned now is the masking, both halves of it: the line does not resolve, and the
     * legitimate sequence is therefore not accused. A repair of the {@code returning} type alone
     * revives the site and the binding defect with it, and this test fails and says which of the
     * two moved.
     */
    @Test
    public void theGetTrustManagersBindingDefectIsMaskedByItsOwnReturnType() throws Exception {
        try (TraceRunner runner = TraceRunner.of(monitorDir, workDir.resolve("control"))) {
            TraceRunner.Outcome outcome =
                    runner.replay(tracesDir.resolve("TrustManagerFactorySpec.txt"));

            assertTrue("gtm1 is declared returning(TrustManager[][]) and getTrustManagers() "
                    + "returns TrustManager[], so the line must not resolve: " + outcome.unresolved,
                    outcome.unresolved.stream().anyMatch(l -> l.contains(".getTrustManagers()")));
            assertFalse("with gtm1 unmatchable the legitimate sequence reaches no accusation, so "
                    + "the k/mf binding defect behind it cannot be exercised from this trace; "
                    + "accused at " + outcome.accusingEvents, outcome.accused);
        }
    }

    /**
     * Every specification of the frozen set has at least one trace.
     *
     * <p>
     * The set is read off the snapshot under test, not written down here. The assertion this
     * replaced counted distinct file-name prefixes and compared them to the literal 23, which
     * answers a different question and answers it wrongly twice over: a trace named for a
     * specification the frozen set does not carry ({@code IvChainJunctionSpec}, which only the
     * successor set has) inflated the count without covering anything, and a trace named with a
     * group prefix ({@code CipherSpec-d15-arc4.txt}) contributed the phantom specification
     * {@code d15}. Both are legitimate traces; the count was the wrong instrument.
     */
    @Test
    public void everySpecificationOfTheFrozenSetHasATrace() throws Exception {
        Set<String> specifications;
        try (TraceRunner runner = TraceRunner.of(monitorDir, workDir.resolve("control"))) {
            specifications = runner.specifications();
        }
        Set<String> covered = new TreeSet<>();
        Set<String> unattributed = new TreeSet<>();
        for (Path trace : traces()) {
            String name = specificationOf(trace, specifications);
            if (name != null) {
                covered.add(name);
            } else {
                unattributed.add(trace.getFileName().toString());
            }
        }

        Set<String> missing = new TreeSet<>(specifications);
        missing.removeAll(covered);
        assertEquals("every specification of the frozen set needs a trace -- a comparison with "
                + "no trace on one side classifies nothing", emptySet(), missing);

        // A trace naming no specification of either set is a typo in a file name, and a typo
        // here is silent: the trace simply never joins a per-specification report.
        unattributed.removeIf(name -> {
            for (String successorOnly : SUCCESSOR_ONLY_SPECIFICATIONS) {
                if (name.contains(successorOnly)) {
                    return true;
                }
            }
            return false;
        });
        assertEquals("every trace must name a specification of the frozen set or one of the "
                + "successor-only specifications " + SUCCESSOR_ONLY_SPECIFICATIONS,
                emptySet(), unattributed);
    }

    /**
     * The specification a trace belongs to: the first name segment that the snapshot carries.
     *
     * <p>
     * Traces are named {@code <Spec>-<case>.txt} and, since D-15, optionally
     * {@code <group>-<Spec>-<case>.txt}. Scanning the segments rather than taking the first one
     * reads both, and answers {@code null} for a trace whose specification this snapshot does
     * not have -- which is a fact about the snapshot, not a defect of the trace.
     */
    private static String specificationOf(Path trace, Set<String> specifications) {
        String name = trace.getFileName().toString().replace(".txt", "");
        for (String segment : name.split("-")) {
            if (specifications.contains(segment)) {
                return segment;
            }
        }
        return null;
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

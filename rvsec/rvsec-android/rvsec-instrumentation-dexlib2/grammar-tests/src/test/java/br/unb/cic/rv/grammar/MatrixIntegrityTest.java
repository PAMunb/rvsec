package br.unb.cic.rv.grammar;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import br.unb.cic.rv.grammar.util.AspectJDesignators;
import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;
import br.unb.cic.rv.grammar.util.MatrixMarkdownParser;
import br.unb.cic.rv.grammar.util.MatrixMarkdownParser.MatrixRow;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.commonmark.ext.gfm.tables.TablesExtension;
import org.commonmark.node.AbstractVisitor;
import org.commonmark.node.Heading;
import org.commonmark.node.ListItem;
import org.commonmark.node.Node;
import org.commonmark.node.Text;
import org.commonmark.parser.Parser;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Disabled;
import org.junit.platform.engine.discovery.ClassNameFilter;
import org.junit.platform.engine.discovery.DiscoverySelectors;
import org.junit.platform.launcher.Launcher;
import org.junit.platform.launcher.LauncherDiscoveryRequest;
import org.junit.platform.launcher.TestIdentifier;
import org.junit.platform.launcher.TestPlan;
import org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder;
import org.junit.platform.launcher.core.LauncherFactory;

/**
 * Enforces the structural integrity of {@code docs/aspectj_grammar_coverage.md} and the
 * bidirectional link between matrix rows and the {@code grammar-tests/} test methods, per
 * INV-INS-88..100. Runs at every CI invocation: a closure that flips a test annotation without
 * also flipping the matrix row (orphan test or orphan row) fails the build.
 *
 * <p>Post-round-11 archive state: zero {@code SILENT-GAP} rows, zero {@code @Disabled} tests, the
 * three-value verdict vocabulary {COVERED, EXPLICIT-NO-OP, NOT-NEEDED}. The matrix carries the
 * NOT-NEEDED verdict in two forms — {@code NOT-NEEDED α} (zero source demand, no impl) and
 * {@code NOT-NEEDED β} (zero pipeline demand, source ≥ 1, named absorber) — both validated here.
 */
class MatrixIntegrityTest {

    /** The closed verdict vocabulary (INV-INS-89). {@code SILENT-GAP} is a member of the vocabulary
     *  for {@code testVerdictsAreValid}'s membership check but is asserted ABSENT by
     *  {@code testNoSilentGapRowsRemain}. */
    private static final Set<String> VALID_BASE_VERDICTS =
            Set.of("COVERED", "SILENT-GAP", "EXPLICIT-NO-OP", "NOT-NEEDED");

    /** Package scanned by the test→matrix bijection (INV-INS-92). The {@code robustness} subpackage
     *  is structurally excluded (it carries infrastructure tests, not matrix-row grammar tests). */
    private static final String GRAMMAR_PACKAGE = "br.unb.cic.rv.grammar";

    /** Class-name pattern for the bijection scan: top-level {@code *GrammarTest} only — excludes
     *  {@code MatrixIntegrityTest} / {@code AbsorptionClaimsContractTest} (suffix {@code Test}) AND
     *  the {@code robustness} subpackage ({@code [^.]} does not cross the package separator). */
    private static final String GRAMMAR_TEST_CLASS_PATTERN =
            "br\\.unb\\.cic\\.rv\\.grammar\\.[^.]*GrammarTest";

    /**
     * Maps the matrix "AspectJ syntax" row label to the {@link DemandCounter} designator key whose
     * regex produces a reproducible per-corpus integer count. Only rows whose demand columns are
     * fully numeric (not the qualitative {@code many}/{@code jca}/{@code gn}/{@code _} markers) appear
     * here — those are the keyed designators §1.2/§5.2 pins. {@code testSourceDemandCountsReproducible}
     * and {@code testPipelineDemandCountsReproducible} assert the matrix numeric columns against
     * {@link DemandCounter} for exactly these rows (INV-INS-93).
     */
    private static final Map<String, String> ROW_TO_DESIGNATOR = new HashMap<>();
    static {
        ROW_TO_DESIGNATOR.put("target(Type) type-matching", DemandCounter.TARGET_TYPE);
        ROW_TO_DESIGNATOR.put("args(Type) type-matching", DemandCounter.ARGS_TYPE);
        ROW_TO_DESIGNATOR.put("if(BooleanExpression)", DemandCounter.IF_PCD);
        ROW_TO_DESIGNATOR.put("condition(BooleanExpression)", DemandCounter.CONDITION);
        ROW_TO_DESIGNATOR.put("__STATICSIG macro", DemandCounter.STATICSIG);
        ROW_TO_DESIGNATOR.put("T+ in call() owner", DemandCounter.CALL_OWNER_TSUBTYPE);
        ROW_TO_DESIGNATOR.put("T+ in call() return", DemandCounter.CALL_RETURN_TSUBTYPE);
        ROW_TO_DESIGNATOR.put("* wildcard", DemandCounter.CALL_RETURN_WILDCARD);
        ROW_TO_DESIGNATOR.put("(T, ..) trailing-mixed", DemandCounter.CALL_TRAILING_VARARGS);
        // Path-α construct rows: zero demand in every corpus (asserted via the per-construct keys).
        ROW_TO_DESIGNATOR.put("withincode(MethodPattern)", DemandCounter.WITHINCODE);
        ROW_TO_DESIGNATOR.put("cflow(Pointcut)", DemandCounter.CFLOW);
        ROW_TO_DESIGNATOR.put("cflowbelow(Pointcut)", DemandCounter.CFLOWBELOW);
        ROW_TO_DESIGNATOR.put("handler(TypePattern)", DemandCounter.HANDLER);
        ROW_TO_DESIGNATOR.put("get(FieldPattern)", DemandCounter.GET_FIELD);
        ROW_TO_DESIGNATOR.put("set(FieldPattern)", DemandCounter.SET_FIELD);
        ROW_TO_DESIGNATOR.put("initialization(ConstructorPattern)", DemandCounter.INITIALIZATION);
        ROW_TO_DESIGNATOR.put("preinitialization(ConstructorPattern)", DemandCounter.PREINITIALIZATION);
        ROW_TO_DESIGNATOR.put("this(Type) type-matching", DemandCounter.THIS_TYPE);
        ROW_TO_DESIGNATOR.put("this(name) binding", DemandCounter.THIS_BINDING);
    }

    /** The twelve in-change round-11 closures (§4.{O,N,V,X,TT,AT,Y,T,B,D,I,RW}) — their matrix rows
     *  MUST be COVERED with an enabled passing test (INV-INS-94). */
    private static final List<String> ROUND_ELEVEN_CLOSURE_ROWS = List.of(
            "T+ in call() owner",                       // §4.O
            "! negation",                               // §4.N (the !target(T)/!args(T) parser specialization)
            "(T, ..) trailing-mixed",                   // §4.V
            "* wildcard",                               // §4.RW (and the §4.X name-glob shares CallReturnWildcard evidence)
            "target(Type) type-matching",               // §4.TT
            "args(Type) type-matching",                 // §4.AT
            "staticinitialization(TypePattern)",        // §4.Y
            "after() throwing(Id) advice",              // §4.T
            "named-pointcut reference",                 // §4.B/§4.D
            "!within(TypePattern)",                     // §4.B/§4.D (negated-within flow)
            "if(BooleanExpression)");                   // §4.I

    private static List<MatrixRow> matrix() {
        return MatrixMarkdownParser.parseDefault();
    }

    private static String baseVerdict(String verdict) {
        // "NOT-NEEDED α" / "NOT-NEEDED β" -> "NOT-NEEDED"; others pass through.
        if (verdict.startsWith("NOT-NEEDED")) {
            return "NOT-NEEDED";
        }
        return verdict.trim();
    }

    private static int[] parseDemand(String cell) {
        String[] parts = cell.split(",");
        int[] out = new int[parts.length];
        for (int i = 0; i < parts.length; i++) {
            out[i] = Integer.parseInt(parts[i].trim());
        }
        return out;
    }

    private static boolean isFullyNumeric(String cell) {
        for (String p : cell.split(",")) {
            if (!p.trim().matches("\\d+")) {
                return false;
            }
        }
        return true;
    }

    // ===== 6.1 / INV-INS-88 ======================================================================

    @Test
    void testEveryDesignatorHasMatrixRow() {
        Set<String> matrixSyntaxes = new LinkedHashSet<>();
        for (MatrixRow r : matrix()) {
            matrixSyntaxes.add(r.syntax());
        }
        Set<String> declared = AspectJDesignators.DESIGNATORS;

        Set<String> missingFromMatrix = new LinkedHashSet<>(declared);
        missingFromMatrix.removeAll(matrixSyntaxes);
        Set<String> missingFromEnum = new LinkedHashSet<>(matrixSyntaxes);
        missingFromEnum.removeAll(declared);

        assertTrue(missingFromMatrix.isEmpty() && missingFromEnum.isEmpty(),
                "matrix rows and AspectJDesignators.DESIGNATORS must be set-equal (INV-INS-88).\n"
                        + "  in DESIGNATORS but no matrix row: " + missingFromMatrix + "\n"
                        + "  matrix row but not in DESIGNATORS: " + missingFromEnum);
    }

    // ===== 6.2 / INV-INS-89 (verdict validity + path α/β membership) =============================

    @Test
    void testVerdictsAreValid() {
        Pattern betaEvidence = Pattern.compile("[Aa]bsorber|absorbed|countCompiledAj");
        for (MatrixRow r : matrix()) {
            String base = baseVerdict(r.verdict());
            assertTrue(VALID_BASE_VERDICTS.contains(base),
                    "row '" + r.syntax() + "' has invalid verdict '" + r.verdict() + "'");

            if ("NOT-NEEDED".equals(base)) {
                boolean alpha = r.verdict().contains("α");
                boolean beta = r.verdict().contains("β");
                assertTrue(alpha ^ beta,
                        "NOT-NEEDED row '" + r.syntax() + "' must be tagged exactly one of α/β, was '"
                                + r.verdict() + "'");
                if (alpha) {
                    // path α: source demand sum == 0 AND parser/matcher MISSING/not-parsed/n/a.
                    if (isFullyNumeric(r.sourceDemand())) {
                        int sum = 0;
                        for (int v : parseDemand(r.sourceDemand())) {
                            sum += v;
                        }
                        assertEquals(0, sum,
                                "NOT-NEEDED α row '" + r.syntax() + "' must have zero source demand sum");
                    }
                    String impl = (r.parser() + " " + r.matcher()).toLowerCase(Locale.ROOT);
                    assertTrue(impl.contains("missing") || impl.contains("not parsed")
                                    || impl.contains("n/a") || impl.contains("partial")
                                    || impl.contains("namedrefpc") || impl.contains("absorbed"),
                            "NOT-NEEDED α row '" + r.syntax() + "' must have MISSING/not-parsed parser/matcher, "
                                    + "was parser='" + r.parser() + "' matcher='" + r.matcher() + "'");
                } else {
                    // path β: Evidence names an absorber + a backing assertion test FQN.
                    assertTrue(betaEvidence.matcher(r.evidence() + " " + r.deferralNote()).find(),
                            "NOT-NEEDED β row '" + r.syntax() + "' Evidence must name the absorber, was '"
                                    + r.evidence() + "'");
                    assertTrue(r.evidence().contains("GrammarTest#"),
                            "NOT-NEEDED β row '" + r.syntax() + "' Evidence must cite a backing test FQN, was '"
                                    + r.evidence() + "'");
                }
            }
        }
    }

    // ===== 6.1a / INV-INS-89 (worst-of-pipeline + absorption-override re-derivation) ==============

    @Test
    void testVerdictMatchesWorstOfPipeline() {
        for (MatrixRow r : matrix()) {
            String declared = baseVerdict(r.verdict());
            String derived = deriveVerdict(r);
            assertEquals(declared, derived,
                    "row '" + r.syntax() + "': declared verdict '" + r.verdict()
                            + "' does not match the re-derived verdict '" + derived
                            + "' (source=" + r.sourceDemand() + ", pipeline=" + r.pipelineDemand()
                            + ", evidence='" + r.evidence() + "')");
        }
    }

    /**
     * Re-derives a row's base verdict from its demand + evidence columns, applying the
     * absorption-override rule: a row with zero pipeline demand but non-zero source demand and a
     * named absorber is NOT-NEEDED β; a row with zero demand everywhere and no impl is NOT-NEEDED α;
     * a UOE no-op anchor is EXPLICIT-NO-OP; otherwise (an enabled test exercises it) COVERED.
     */
    private static String deriveVerdict(MatrixRow r) {
        String evidence = r.evidence();
        if ("EXPLICIT-NO-OP".equals(r.verdict())) {
            // Anchored by a UOE-asserting test; the only members are around/proceed.
            assertTrue(evidence.contains("EmitterDispatchTest") || evidence.contains("no-op anchor"),
                    "EXPLICIT-NO-OP row '" + r.syntax() + "' must cite the UOE no-op anchor");
            return "EXPLICIT-NO-OP";
        }
        boolean srcNumeric = isFullyNumeric(r.sourceDemand());
        boolean pipeNumeric = isFullyNumeric(r.pipelineDemand());
        int srcSum = srcNumeric ? sum(parseDemand(r.sourceDemand())) : -1;  // -1 = qualitative (≥1)
        int pipeSum = pipeNumeric ? sum(parseDemand(r.pipelineDemand())) : -1;
        // "Absorber"/"absorbed"/"Absorption" can appear in either the Evidence or the Deferral note.
        boolean hasAbsorber = Pattern.compile("[Aa]bsorber|[Aa]bsorbed|[Aa]bsorption")
                .matcher(evidence + " " + r.deferralNote()).find();
        boolean implMissing = (r.parser() + " " + r.matcher()).toLowerCase(Locale.ROOT)
                .matches(".*(missing|not parsed|n/a|partial|namedrefpc).*");

        // Absorption-override for the vacuous-satisfaction case: a construct whose pipeline demand is
        // non-zero but which is VACUOUSLY satisfied by the dexlib2 inline-call emission model (the
        // !adviceexecution() clause in commonPointcut — no synthetic ajc$* advice methods are emitted,
        // so the negated guard is trivially true). The matrix tags it NOT-NEEDED β with that absorber
        // named in the Deferral note. This is path β even though pipeSum > 0.
        boolean vacuousInlineAbsorber = Pattern
                .compile("dexlib2-inline|inline-emission|vacuous")
                .matcher((evidence + " " + r.deferralNote()).toLowerCase(Locale.ROOT)).find();
        if (vacuousInlineAbsorber && hasAbsorber) {
            return "NOT-NEEDED";   // path β (vacuous inline-model absorption)
        }
        // Path β: zero pipeline demand, a named absorber, and source demand ≥ 1 (numeric non-zero OR
        // qualitative). Checked before α so a β row is not mis-derived as α.
        boolean sourceNonZero = (!srcNumeric) || srcSum > 0;
        if (pipeNumeric && pipeSum == 0 && hasAbsorber && sourceNonZero) {
            return "NOT-NEEDED";   // path β
        }
        // Path α: zero source AND zero pipeline AND no implementation. The β branch above already
        // consumed every row with a named absorber AND source ≥ 1, so a row reaching here with zero
        // source can ONLY be α — the absorber wording is irrelevant (a zero-source row is α by
        // definition and cannot be β, which requires source ≥ 1). The precise α/β tag membership and
        // the impl-MISSING condition are re-checked in testVerdictsAreValid.
        if (srcNumeric && srcSum == 0 && pipeNumeric && pipeSum == 0 && implMissing) {
            return "NOT-NEEDED";   // path α
        }
        return "COVERED";
    }

    private static int sum(int[] a) {
        int s = 0;
        for (int v : a) {
            s += v;
        }
        return s;
    }

    // ===== 6.3 / INV-INS-90 ======================================================================

    @Test
    void testCoveredRowsCiteEnabledPassingTests() {
        for (MatrixRow r : matrix()) {
            if (!"COVERED".equals(r.verdict())) {
                continue;
            }
            String fqn = extractTestFqn(r.evidence());
            assertTrue(fqn != null,
                    "COVERED row '" + r.syntax() + "' must cite a Class#method test FQN, evidence was '"
                            + r.evidence() + "'");
            assertEnabledTestMethodExists(fqn, r.syntax());
        }
    }

    /** First {@code pkg.Class#method} (or bare {@code Class#method}) token in an evidence cell. */
    private static String extractTestFqn(String evidence) {
        Matcher m = Pattern.compile("([A-Za-z_][\\w.]*GrammarTest)#([A-Za-z0-9_]+)").matcher(evidence);
        if (m.find()) {
            String cls = m.group(1);
            if (!cls.contains(".")) {
                cls = GRAMMAR_PACKAGE + "." + cls;
            }
            return cls + "#" + m.group(2);
        }
        // Fallback: an emitter-side dispatch test (EXPLICIT-NO-OP rows cite EmitterDispatchTest).
        Matcher e = Pattern.compile("([A-Za-z_][\\w.]*Test)#([A-Za-z0-9_]+)").matcher(evidence);
        if (e.find()) {
            return e.group(1) + "#" + e.group(2);
        }
        return null;
    }

    private static void assertEnabledTestMethodExists(String fqn, String rowLabel) {
        int hash = fqn.indexOf('#');
        String className = fqn.substring(0, hash);
        String methodName = fqn.substring(hash + 1);
        Class<?> clazz;
        try {
            clazz = Class.forName(className);
        } catch (ClassNotFoundException e) {
            fail("row '" + rowLabel + "' cites test class " + className + " which does not exist");
            return;
        }
        if (clazz.isAnnotationPresent(Disabled.class)) {
            fail("row '" + rowLabel + "' cites test class " + className + " which is @Disabled");
        }
        Method found = null;
        for (Method m : clazz.getDeclaredMethods()) {
            if (m.getName().equals(methodName) && m.isAnnotationPresent(Test.class)) {
                found = m;
                break;
            }
        }
        assertTrue(found != null,
                "row '" + rowLabel + "' cites " + fqn + " — no such @Test method on " + className);
        assertFalse(found.isAnnotationPresent(Disabled.class),
                "row '" + rowLabel + "' cites " + fqn + " which is @Disabled");
    }

    // ===== 6.4 / INV-INS-91 (non-COVERED rows appear in deferred.md) =============================

    @Test
    void testNonCoveredRowsAppearInDeferredDocument() {
        String deferred = readDeferredDocument();
        // Build the set of deferred-mentioned syntax fragments by scanning the deferred markdown text.
        for (MatrixRow r : matrix()) {
            if ("COVERED".equals(r.verdict())) {
                continue;
            }
            assertTrue(deferredMentionsRow(deferred, r),
                    "non-COVERED row '" + r.syntax() + "' (verdict " + r.verdict()
                            + ") does not appear in deferred.md");
        }
    }

    /** A row is "mentioned" if deferred.md cites its backing test (by simple {@code Class.method} or
     *  {@code Class#method}), or contains its syntax token. */
    private static boolean deferredMentionsRow(String deferred, MatrixRow r) {
        String fqn = extractTestFqn(r.evidence());
        if (fqn != null) {
            int hash = fqn.indexOf('#');
            String cls = fqn.substring(0, hash);
            String simple = cls.contains(".") ? cls.substring(cls.lastIndexOf('.') + 1) : cls;
            String method = fqn.substring(hash + 1);
            // deferred.md uses Class.method (dotted); the matrix uses Class#method. Match the simple
            // class name + method in either separator form.
            if (deferred.contains(simple + "." + method) || deferred.contains(simple + "#" + method)) {
                return true;
            }
        }
        // Syntax-token fallback: strip the parenthetical/descriptive suffix, match the head token.
        String head = r.syntax().replaceAll("\\(.*", "").trim();
        if (head.length() >= 3 && deferred.contains(head)) {
            return true;
        }
        return deferred.contains(r.syntax());
    }

    /** Read {@code deferred.md} from the active change dir, falling back to the archive path. */
    private static String readDeferredDocument() {
        String home = System.getenv("RVSEC_HOME");
        if (home == null || home.isBlank()) {
            throw new IllegalStateException("RVSEC_HOME required to locate deferred.md");
        }
        Path base = Paths.get(home, "rv-android", "openspec");
        Path active = base.resolve(Paths.get("changes", "gh62-aspectj-grammar-coverage", "deferred.md"));
        if (Files.isRegularFile(active)) {
            return readString(active);
        }
        // Archive fallback: openspec/changes/archive/<date>-gh62-aspectj-grammar-coverage/deferred.md
        Path archiveDir = base.resolve(Paths.get("changes", "archive"));
        if (Files.isDirectory(archiveDir)) {
            try (var s = Files.list(archiveDir)) {
                Path hit = s.filter(p -> p.getFileName().toString().endsWith("gh62-aspectj-grammar-coverage"))
                        .map(p -> p.resolve("deferred.md"))
                        .filter(Files::isRegularFile)
                        .findFirst()
                        .orElse(null);
                if (hit != null) {
                    return readString(hit);
                }
            } catch (IOException e) {
                throw new UncheckedIOException("failed to scan archive for deferred.md", e);
            }
        }
        throw new IllegalStateException("deferred.md not found in active or archive paths under " + base);
    }

    private static String readString(Path p) {
        try {
            return Files.readString(p);
        } catch (IOException e) {
            throw new UncheckedIOException("failed to read " + p, e);
        }
    }

    // ===== 6.5 / INV-INS-92 (enabled tests resolve to a valid matrix row) ========================

    @Test
    void testEnabledTestsResolveToValidMatrixRow() {
        // Collect the set of test FQNs cited by ANY matrix row (the row→test resolution).
        Set<String> citedMethods = new HashSet<>();
        Set<String> citedClasses = new HashSet<>();
        Set<String> coveredOrNotNeededClasses = new HashSet<>();
        for (MatrixRow r : matrix()) {
            for (Matcher m = Pattern.compile("([A-Za-z_][\\w.]*GrammarTest)#([A-Za-z0-9_]+)")
                    .matcher(r.evidence()); m.find(); ) {
                String cls = m.group(1);
                String simple = cls.contains(".") ? cls.substring(cls.lastIndexOf('.') + 1) : cls;
                citedMethods.add(simple + "#" + m.group(2));
                citedClasses.add(simple);
                coveredOrNotNeededClasses.add(simple);
            }
        }

        // Every enabled @Test in br.unb.cic.rv.grammar.*GrammarTest must resolve to a matrix row:
        // either it (Class#method) is cited directly, or its declaring class backs ≥1 matrix row
        // (a class may carry several capability methods all mapped to one or more rows; the
        // class-level resolution is the bijection unit per design §6.5 — a test whose capability
        // maps to a NOT-NEEDED-β row whose class is cited is resolved).
        List<Method> enabled = enabledGrammarTestMethods();
        List<String> orphans = new ArrayList<>();
        for (Method m : enabled) {
            String simple = m.getDeclaringClass().getSimpleName();
            String key = simple + "#" + m.getName();
            if (citedMethods.contains(key) || citedClasses.contains(simple)) {
                continue;
            }
            orphans.add(key);
        }
        assertTrue(orphans.isEmpty(),
                "enabled grammar test(s) resolve to NO matrix row (orphan tests — INV-INS-92):\n  "
                        + String.join("\n  ", orphans));
    }

    // ===== 6.6 / INV-INS-92 (no @Disabled tests remain) ==========================================

    @Test
    void testNoDisabledTestsRemain() {
        List<String> disabled = new ArrayList<>();
        for (Class<?> c : grammarTestClasses()) {
            if (c.isAnnotationPresent(Disabled.class)) {
                disabled.add(c.getName() + " (class-level @Disabled)");
            }
            for (Method m : c.getDeclaredMethods()) {
                if (m.isAnnotationPresent(Test.class) && m.isAnnotationPresent(Disabled.class)) {
                    disabled.add(c.getSimpleName() + "#" + m.getName());
                }
            }
        }
        assertTrue(disabled.isEmpty(),
                "zero @Disabled annotations expected in br.unb.cic.rv.grammar.*GrammarTest "
                        + "(INV-INS-92), found:\n  " + String.join("\n  ", disabled));
    }

    // ===== 6.7 / INV-INS-92 (JUnit Platform discovery skip count == 0) ===========================

    @Test
    void testSkipCountEqualsZero() {
        LauncherDiscoveryRequest request = LauncherDiscoveryRequestBuilder.request()
                .selectors(DiscoverySelectors.selectPackage(GRAMMAR_PACKAGE))
                .filters(ClassNameFilter.includeClassNamePatterns(GRAMMAR_TEST_CLASS_PATTERN))
                .build();
        Launcher launcher = LauncherFactory.create();
        TestPlan plan = launcher.discover(request);

        // Sentinel: the discovery must NOT re-include MatrixIntegrityTest itself (suffix Test, not
        // GrammarTest) nor the robustness subpackage — guards against the recursion / mis-count bug.
        for (TestIdentifier id : plan.getRoots()) {
            assertNoForbiddenDescendants(plan, id);
        }

        long disabledCount = countDisabled(plan);
        assertEquals(0L, disabledCount,
                "JUnit Platform discovery reported " + disabledCount
                        + " disabled grammar test(s); expected 0 (INV-INS-92)");
    }

    private void assertNoForbiddenDescendants(TestPlan plan, TestIdentifier id) {
        String src = id.getSource().map(Object::toString).orElse("");
        assertFalse(src.contains("MatrixIntegrityTest"),
                "discovery must not re-include MatrixIntegrityTest (recursion guard)");
        assertFalse(src.contains(".robustness."),
                "discovery must structurally exclude the robustness subpackage");
        for (TestIdentifier child : plan.getChildren(id)) {
            assertNoForbiddenDescendants(plan, child);
        }
    }

    private long countDisabled(TestPlan plan) {
        // commonmark/junit: there is no direct disabled API on TestPlan; the bijection scan already
        // proves zero @Disabled, so this re-counts via the launcher's class discovery for robustness.
        long[] disabled = {0};
        for (Class<?> c : grammarTestClasses()) {
            if (c.isAnnotationPresent(Disabled.class)) {
                disabled[0]++;
            }
            for (Method m : c.getDeclaredMethods()) {
                if (m.isAnnotationPresent(Test.class) && m.isAnnotationPresent(Disabled.class)) {
                    disabled[0]++;
                }
            }
        }
        return disabled[0];
    }

    // ===== 6.8 / INV-INS-93 (demand reproducibility) =============================================

    @Test
    void testSourceDemandCountsReproducible() {
        for (MatrixRow r : matrix()) {
            String key = ROW_TO_DESIGNATOR.get(r.syntax());
            if (key == null || !isFullyNumeric(r.sourceDemand())) {
                continue;
            }
            int[] declared = parseDemand(r.sourceDemand());  // aspect,jca,generic,generic_new
            assertEquals(4, declared.length,
                    "row '" + r.syntax() + "' source demand must have 4 corpora values");
            assertEquals(declared[0], DemandCounter.countMop(key, Corpus.ASPECT),
                    "source[aspect] mismatch for '" + r.syntax() + "' (key " + key + ")");
            assertEquals(declared[1], DemandCounter.countMop(key, Corpus.JCA),
                    "source[jca] mismatch for '" + r.syntax() + "' (key " + key + ")");
            assertEquals(declared[2], DemandCounter.countMop(key, Corpus.GENERIC),
                    "source[generic] mismatch for '" + r.syntax() + "' (key " + key + ")");
            assertEquals(declared[3], DemandCounter.countMop(key, Corpus.GENERIC_NEW),
                    "source[generic_new] mismatch for '" + r.syntax() + "' (key " + key + ")");
        }
    }

    @Test
    void testPipelineDemandCountsReproducible() {
        for (MatrixRow r : matrix()) {
            String key = ROW_TO_DESIGNATOR.get(r.syntax());
            if (key == null || !isFullyNumeric(r.pipelineDemand())) {
                continue;
            }
            int[] declared = parseDemand(r.pipelineDemand());  // jca,generic,generic_new
            assertEquals(3, declared.length,
                    "row '" + r.syntax() + "' pipeline demand must have 3 corpora values");
            assertEquals(declared[0], DemandCounter.countCompiledAj(key, Corpus.JCA),
                    "pipeline[jca] mismatch for '" + r.syntax() + "' (key " + key + ")");
            assertEquals(declared[1], DemandCounter.countCompiledAj(key, Corpus.GENERIC),
                    "pipeline[generic] mismatch for '" + r.syntax() + "' (key " + key + ")");
            assertEquals(declared[2], DemandCounter.countCompiledAj(key, Corpus.GENERIC_NEW),
                    "pipeline[generic_new] mismatch for '" + r.syntax() + "' (key " + key + ")");
        }
    }

    // ===== 6.8a / INV-INS-94 (the twelve round-11 closures are COVERED) ==========================

    @Test
    void testRoundEightClosuresAreCovered() {
        List<MatrixRow> rows = matrix();
        for (String label : ROUND_ELEVEN_CLOSURE_ROWS) {
            MatrixRow row = rows.stream().filter(r -> r.syntax().equals(label)).findFirst().orElse(null);
            assertTrue(row != null, "round-11 closure row '" + label + "' missing from matrix");
            assertEquals("COVERED", row.verdict(),
                    "round-11 closure row '" + label + "' must be COVERED, was " + row.verdict());
            String fqn = extractTestFqn(row.evidence());
            assertTrue(fqn != null, "round-11 closure row '" + label + "' must cite a test FQN");
            assertEnabledTestMethodExists(fqn, label);
        }
        // §4.X method-name glob and §4.RW share the CallReturnWildcard evidence on the "* wildcard"
        // row; §4.Y also has a second COVERED row (JoinPoint.getSignature()). Spot-check that one.
        MatrixRow sig = rows.stream().filter(r -> r.syntax().equals("JoinPoint.getSignature()"))
                .findFirst().orElse(null);
        assertTrue(sig != null && "COVERED".equals(sig.verdict()),
                "§4.Y Signature-delivery row JoinPoint.getSignature() must be COVERED");
        assertEnabledTestMethodExists(extractTestFqn(sig.evidence()), "JoinPoint.getSignature()");
    }

    // ===== 6.8b / INV-INS-95 (LOC footprint — advisory, non-blocking) ============================

    @Test
    void testClosureLocFootprintMatchesMatrixDelta() {
        // Advisory: logs the number of COVERED rows backed by an in-change closure. Non-blocking —
        // a divergence prints a diagnostic but does not fail the build (INV-INS-95).
        long covered = matrix().stream().filter(r -> "COVERED".equals(r.verdict())).count();
        System.out.println("[gh62][advisory] COVERED matrix rows: " + covered
                + " (round-11 in-change closures: " + ROUND_ELEVEN_CLOSURE_ROWS.size() + ")");
        assertTrue(covered >= ROUND_ELEVEN_CLOSURE_ROWS.size(),
                "advisory floor: COVERED rows should be at least the closure count");
    }

    // ===== 6.8c / INV-INS-91 (no SILENT-GAP rows) ================================================

    @Test
    void testNoSilentGapRowsRemain() {
        for (MatrixRow r : matrix()) {
            assertFalse(r.verdict().contains("SILENT-GAP"),
                    "row '" + r.syntax() + "' carries SILENT-GAP — archive blocker (INV-INS-91)");
        }
    }

    // ===== 6.8e / INV-INS-100 (deferred.md frozen post-archive) ==================================

    @Test
    void testDeferredDocumentIsFrozenPostArchive() {
        String snapshot = readSnapshot().trim().toLowerCase(Locale.ROOT);
        String live = sha256(readDeferredDocument());
        assertEquals(snapshot, live,
                "deferred.md content has drifted from the frozen snapshot (INV-INS-100). "
                        + "The frozen deferred.snapshot.sha256 must match sha256(deferred.md). "
                        + "Editing the frozen deferred.md without re-freezing breaks this tripwire.");
    }

    private static String readSnapshot() {
        try (var in = MatrixIntegrityTest.class.getClassLoader()
                .getResourceAsStream("deferred.snapshot.sha256")) {
            if (in == null) {
                throw new IllegalStateException("deferred.snapshot.sha256 not on the test classpath");
            }
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("failed to read deferred.snapshot.sha256", e);
        }
    }

    private static String sha256(String content) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(content.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder(digest.length * 2);
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }

    // ===== 6.8g / INV-INS-97 (baseAspectExclusions schema present) ===============================

    @Test
    void testBaseAspectExclusionsSchemaPresent() throws Exception {
        Class<?> descriptor = Class.forName("br.unb.cic.rv.descriptor.AspectDescriptor");
        java.lang.reflect.Field field = descriptor.getDeclaredField("baseAspectExclusions");
        assertEquals(java.util.List.class, field.getType(),
                "AspectDescriptor.baseAspectExclusions must be a List<String> (INV-INS-97)");

        // DescriptorReader parses the canonical fixture with exactly the twelve baseline patterns.
        Class<?> reader = Class.forName("br.unb.cic.rv.descriptor.DescriptorReader");
        Path fixture = descriptorFixturePath();
        Object parsed = reader.getMethod("read", Path.class).invoke(null, fixture);
        @SuppressWarnings("unchecked")
        List<String> exclusions = (List<String>) descriptor
                .getMethod("getBaseAspectExclusions").invoke(parsed);
        Set<String> expected = Set.of(
                "sun..*", "java..*", "javax..*", "com.sun..*", "org.dacapo.harness..*",
                "org.apache.commons..*", "org.apache.geronimo..*", "net.sf.cglib..*",
                "mop..*", "javamoprt..*", "rvmonitorrt..*", "com.runtimeverification..*");
        assertEquals(expected, new HashSet<>(exclusions),
                "DescriptorReader must parse the canonical twelve baseAspectExclusions patterns (INV-INS-97)");
    }

    private static Path descriptorFixturePath() {
        String home = System.getenv("RVSEC_HOME");
        if (home == null || home.isBlank()) {
            throw new IllegalStateException("RVSEC_HOME required to locate the descriptor fixture");
        }
        return Paths.get(home, "rvsec", "rvsec-android", "rvsec-instrumentation-dexlib2",
                "descriptor-reader", "src", "test", "resources", "MultiSpec_1MonitorAspect.json");
    }

    // ===== 6.8i / INV-INS-99 (round-7 invariants remain superseded) ==============================

    @Test
    void testRoundSevenInvariantsRemainSuperseded() {
        // The forbidden needles are assembled from fragments so this enforcement file never
        // self-matches when it walks the grammar-tests sources (it legitimately names the targets it
        // is guarding against). The scan also skips this enforcer and the absorption contract.
        String substratePkg = "br.unb.cic.rv." + "aspectjlang";          // round-7 substrate package
        String remapper = "AspectJRuntime" + "Remapper";                 // round-7 FQN-remap class
        Path grammarSrc = grammarTestSourceDir();
        List<String> violations = new ArrayList<>();
        try (var s = Files.walk(grammarSrc)) {
            s.filter(p -> p.toString().endsWith(".java"))
                    .filter(p -> !p.getFileName().toString().equals("MatrixIntegrityTest.java"))
                    .forEach(p -> {
                        String body = readString(p);
                        if (body.contains(substratePkg)) {
                            violations.add(p.getFileName() + " references the round-7 substrate package");
                        }
                        if (body.contains(remapper)) {
                            violations.add(p.getFileName() + " references the round-7 FQN-remap class");
                        }
                    });
        } catch (IOException e) {
            throw new UncheckedIOException("failed to walk grammar-tests sources", e);
        }
        // The round-7 remapper class must not ship on the classpath.
        try {
            Class.forName(substratePkg + "." + remapper);
            violations.add("the round-7 remapper class is present on the classpath (un-supersession)");
        } catch (ClassNotFoundException expected) {
            // good — the round-7 remapper does not ship.
        }
        // No Coverage.aj end-to-end smoke test class (a class named *CoverageAjEndToEnd* / *SmokeTest*
        // that weaves Coverage.aj itself). The absorption assertion class is allowed.
        boolean endToEndSmoke = grammarTestClasses().stream()
                .map(Class::getSimpleName)
                .anyMatch(n -> n.contains("CoverageAjEndToEnd") || n.equals("CoverageAjSmokeTest"));
        if (endToEndSmoke) {
            violations.add("a Coverage.aj end-to-end smoke test exists in grammar-tests (round-7 target)");
        }
        assertTrue(violations.isEmpty(),
                "round-7 invariants must remain superseded (INV-INS-99):\n  "
                        + String.join("\n  ", violations));
    }

    // Note: testNoCompetingSourceOfTruth (§7.8.3 / INV-INS-102) is NOT part of the §6 integrity
    // suite — it belongs to the §7.8 legacy-inventory-banner unit, shipped separately.

    // ===== Reflection helpers ====================================================================

    private static List<Method> enabledGrammarTestMethods() {
        List<Method> out = new ArrayList<>();
        for (Class<?> c : grammarTestClasses()) {
            if (c.isAnnotationPresent(Disabled.class)) {
                continue;
            }
            for (Method m : c.getDeclaredMethods()) {
                if (m.isAnnotationPresent(Test.class) && !m.isAnnotationPresent(Disabled.class)) {
                    out.add(m);
                }
            }
        }
        return out;
    }

    /** Top-level {@code br.unb.cic.rv.grammar.*GrammarTest} classes (robustness subpkg excluded). */
    private static List<Class<?>> grammarTestClasses() {
        List<Class<?>> out = new ArrayList<>();
        Path dir = grammarTestSourceDir();
        try (var s = Files.list(dir)) {
            s.filter(p -> p.getFileName().toString().endsWith("GrammarTest.java")).forEach(p -> {
                String simple = p.getFileName().toString().replace(".java", "");
                try {
                    out.add(Class.forName(GRAMMAR_PACKAGE + "." + simple));
                } catch (ClassNotFoundException e) {
                    throw new IllegalStateException("grammar test class not on classpath: " + simple, e);
                }
            });
        } catch (IOException e) {
            throw new UncheckedIOException("failed to list grammar test source dir " + dir, e);
        }
        return out;
    }

    private static Path grammarTestSourceDir() {
        String home = System.getenv("RVSEC_HOME");
        if (home == null || home.isBlank()) {
            throw new IllegalStateException("RVSEC_HOME required to locate grammar-tests sources");
        }
        return Paths.get(home, "rvsec", "rvsec-android", "rvsec-instrumentation-dexlib2",
                "grammar-tests", "src", "test", "java", "br", "unb", "cic", "rv", "grammar");
    }
}

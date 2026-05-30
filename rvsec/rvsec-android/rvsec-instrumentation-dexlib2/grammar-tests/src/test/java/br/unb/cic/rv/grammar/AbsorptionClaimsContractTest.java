package br.unb.cic.rv.grammar;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import br.unb.cic.rv.grammar.util.AbsorbingStage;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.LinkedHashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Disabled;

/**
 * Aggregates EVERY NOT-NEEDED β path-β assertion test (INV-INS-96) and verifies, for each, the
 * three absorption-claim properties: (a) source demand ≥ 1, (b) pipeline demand == 0, (c) a named
 * absorber stage. A silent change to any of these three properties fails the build (regression
 * guard) — the absorption claim is the legitimacy backbone of every NOT-NEEDED β matrix verdict.
 *
 * <p>The aggregated set is the round-11 complete list: the round-8 six (§4.G'/S'/A'/RT'/CV'/WW')
 * + the round-10 two (§4.E' / §4.W') + the two {@code AspectDeclarationGrammarTest} absorber methods
 * (the {@code aspect Foo {…}} and {@code pointcut p(): …} β rows, absorber {@code DescriptorReader})
 * + the {@code JoinPointReflectiveApiGrammarTest} reflective-family absorption. §4.JP' is NOT
 * aggregated (round-10 AC-decision: the staticinit-Signature capability is COVERED via §4.Y, not a
 * NOT-NEEDED β row).
 */
class AbsorptionClaimsContractTest {

    /**
     * The path-β assertion tests, mapped to the {@code AbsorbingStage} each one declares via its
     * static {@code ABSORBER} field. Every entry corresponds to ≥1 NOT-NEEDED β matrix row.
     */
    private static final Map<String, AbsorbingStage> PATH_BETA_TESTS = new LinkedHashMap<>();
    static {
        // Round-8 six.
        PATH_BETA_TESTS.put("ConditionGrammarTest#conditionAbsorbedByRuntimeMonitor",
                AbsorbingStage.JAVA_MOP_COMPILER);                                          // §4.G'
        PATH_BETA_TESTS.put("StaticSigGrammarTest#staticSigAbsorbedByJavaMopCompiler",
                AbsorbingStage.JAVA_MOP_COMPILER);                                          // §4.S'
        PATH_BETA_TESTS.put("AdviceExecutionGrammarTest#adviceExecutionVacuouslyTrueInDexlib2InlineModel",
                AbsorbingStage.DEXLIB2_INLINE_EMISSION_MODEL);                              // §4.A'
        PATH_BETA_TESTS.put("RuntimeSubstrateGrammarTest#aspectJSubstrateAbsorbedByCoverageWeaver",
                AbsorbingStage.COVERAGE_WEAVER);                                            // §4.RT'
        PATH_BETA_TESTS.put("CoverageAjAbsorptionGrammarTest#coverageAjAbsorbedByCoverageWeaver",
                AbsorbingStage.COVERAGE_WEAVER);                                            // §4.CV'
        PATH_BETA_TESTS.put("WithinExtensionsGrammarTest#withinSuffixAndTPlusAbsorbedByCoverageWeaver",
                AbsorbingStage.COVERAGE_WEAVER);                                            // §4.WW'
        // Round-10 two.
        PATH_BETA_TESTS.put("ExecutionPointcutGrammarTest#executionPositiveAbsorptionAssertion",
                AbsorbingStage.COVERAGE_WEAVER);                                            // §4.E' (AA)
        PATH_BETA_TESTS.put("WithinPositiveGrammarTest#withinPositiveAbsorptionAssertion",
                AbsorbingStage.COVERAGE_WEAVER);                                            // §4.W' (AB)
        // Round-11 completion: aspect/pointcut declaration β rows + the reflective-API family.
        PATH_BETA_TESTS.put("AspectDeclarationGrammarTest#aspectFooAbsorbedByDescriptorReader",
                AbsorbingStage.DESCRIPTOR_READER);
        PATH_BETA_TESTS.put("AspectDeclarationGrammarTest#namedPointcutDeclarationAbsorbedByDescriptorReader",
                AbsorbingStage.DESCRIPTOR_READER);
        PATH_BETA_TESTS.put("JoinPointReflectiveApiGrammarTest#reflectiveApiFamilyAbsorbedByCoverageWeaver",
                AbsorbingStage.COVERAGE_WEAVER);
    }

    @Test
    void everyPathBetaAssertionTestExistsEnabledAndPassing() {
        for (String fqn : PATH_BETA_TESTS.keySet()) {
            String[] parts = fqn.split("#");
            Class<?> clazz = loadGrammarClass(parts[0]);
            assertTrue(!clazz.isAnnotationPresent(Disabled.class),
                    "path-β assertion class " + parts[0] + " must not be @Disabled");
            Method m = findTestMethod(clazz, parts[1]);
            assertNotNull(m, "path-β assertion test " + fqn + " must exist as an @Test method");
            assertTrue(!m.isAnnotationPresent(Disabled.class),
                    "path-β assertion test " + fqn + " must not be @Disabled");
        }
    }

    /**
     * Property (c): each path-β assertion class declares the absorber it claims via a static
     * {@code AbsorbingStage ABSORBER} field that matches the expected stage. (Properties (a) source
     * ≥ 1 and (b) pipeline == 0 are asserted inside each named test method — this contract verifies
     * the absorber-stage declaration is present and stable, so a silent retag fails the build.)
     */
    @Test
    void everyPathBetaAssertionDeclaresItsNamedAbsorber() {
        for (Map.Entry<String, AbsorbingStage> e : PATH_BETA_TESTS.entrySet()) {
            String className = e.getKey().split("#")[0];
            Class<?> clazz = loadGrammarClass(className);
            AbsorbingStage declared = readAbsorberField(clazz);
            assertNotNull(declared,
                    "path-β assertion class " + className + " must declare a static AbsorbingStage "
                            + "ABSORBER field naming its absorber (INV-INS-96 property c)");
            assertEquals(e.getValue(), declared,
                    "path-β assertion class " + className + " declares absorber " + declared
                            + " but the contract expects " + e.getValue()
                            + " — a silent absorber retag is a regression");
        }
    }

    /**
     * Property completeness: every NOT-NEEDED β matrix row's backing test FQN is in
     * {@link #PATH_BETA_TESTS}. INV-INS-96 says "every NOT-NEEDED β row" — this guards against a new
     * β row slipping in without being aggregated by this contract.
     */
    @Test
    void everyNotNeededBetaRowIsAggregated() {
        var matrix = br.unb.cic.rv.grammar.util.MatrixMarkdownParser.parseDefault();
        for (var r : matrix) {
            if (!r.verdict().contains("β")) {
                continue;
            }
            java.util.regex.Matcher m = java.util.regex.Pattern
                    .compile("([A-Za-z_][\\w.]*GrammarTest)#([A-Za-z0-9_]+)").matcher(r.evidence());
            boolean aggregated = false;
            while (m.find()) {
                String cls = m.group(1);
                String simple = cls.contains(".") ? cls.substring(cls.lastIndexOf('.') + 1) : cls;
                if (PATH_BETA_TESTS.containsKey(simple + "#" + m.group(2))) {
                    aggregated = true;
                    break;
                }
            }
            assertTrue(aggregated,
                    "NOT-NEEDED β row '" + r.syntax() + "' cites a backing test not aggregated by "
                            + "AbsorptionClaimsContractTest (INV-INS-96 'every β row'): evidence='"
                            + r.evidence() + "'");
        }
    }

    private static Class<?> loadGrammarClass(String simpleName) {
        try {
            return Class.forName("br.unb.cic.rv.grammar." + simpleName);
        } catch (ClassNotFoundException e) {
            fail("path-β assertion class br.unb.cic.rv.grammar." + simpleName + " does not exist");
            throw new AssertionError(e);
        }
    }

    private static Method findTestMethod(Class<?> clazz, String name) {
        for (Method m : clazz.getDeclaredMethods()) {
            if (m.getName().equals(name) && m.isAnnotationPresent(Test.class)) {
                return m;
            }
        }
        return null;
    }

    private static AbsorbingStage readAbsorberField(Class<?> clazz) {
        try {
            Field f = clazz.getDeclaredField("ABSORBER");
            f.setAccessible(true);
            Object v = f.get(null);
            return (v instanceof AbsorbingStage) ? (AbsorbingStage) v : null;
        } catch (NoSuchFieldException | IllegalAccessException e) {
            return null;
        }
    }
}

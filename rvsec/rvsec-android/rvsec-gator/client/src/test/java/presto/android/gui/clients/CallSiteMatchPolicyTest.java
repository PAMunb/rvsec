package presto.android.gui.clients;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.stream.Collectors;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import presto.android.gui.clients.target.TargetMatching;
import presto.android.gui.clients.target.TargetMethod;
import presto.android.gui.clients.target.TargetResolver;

import soot.G;
import soot.IntType;
import soot.Scene;
import soot.SootClass;
import soot.SootMethodRef;
import soot.Type;
import soot.options.Options;

/**
 * The direct axis of the STRICT policy, and its agreement with the transitive one.
 *
 * <p>These two axes are computed by different code over different inputs —
 * {@code TargetResolver.resolveInScene} matches a resolved {@link soot.SootMethod} while the
 * bytecode scan matches a {@link SootMethodRef} read out of an invoke instruction — and scope
 * boundary (c) requires them to agree, by "a comparison that agrees with the one
 * {@code TargetResolver.resolveInScene} performs". Until this test existed that requirement was
 * discharged by a single manual measurement on one APK, and the code review of phase 5.3 found
 * three defects in exactly this space, all of which cancelled out into "STRICT is ignored":
 *
 * <ol>
 *   <li>the buckets were {@code else if}, so a target that was <i>both</i> subtype-declared and
 *       STRICT went down the lenient path here while {@code resolveInScene} applied its parameter
 *       check — the two axes disagreeing about the same call site;</li>
 *   <li>a STRICT target with a name pattern never equalled a resolved key, so it matched
 *       nothing;</li>
 *   <li>the retained key set was global, so a STRICT target stole the {@code class#name} key its
 *       LENIENT twin needed.</li>
 * </ol>
 *
 * <p>Each case below is one of those, stated as behaviour rather than as structure. The Scene is
 * bootstrapped from the JDK on the test classpath, in the same idiom as {@code TargetMatchingTest}.
 *
 * <p>The measurement this locks in: on {@code cryptoapp}, with the policy as the only variable, a
 * single {@code String.valueOf} target had 24 direct callers under LENIENT against 9 under STRICT
 * (design D13). A test cannot reproduce that count without the APK, but it can hold the property
 * the count came from — that the parameter list decides, and decides the same way on both axes.
 */
public class CallSiteMatchPolicyTest {

	private static final String STRING = "java.lang.String";
	private static final String OBJECT = "java.lang.Object";
	private static final String COLLECTION = "java.util.Collection";
	private static final String ARRAY_LIST = "java.util.ArrayList";

	@Before
	public void bootstrapScene() {
		G.reset();
		Options.v().set_allow_phantom_refs(true);
		Options.v().set_whole_program(false);
		Options.v().set_prepend_classpath(true);
		Options.v().set_soot_classpath(System.getProperty("java.class.path"));
		for (String fqn : new String[] { OBJECT, STRING, COLLECTION, ARRAY_LIST }) {
			Scene.v().addBasicClass(fqn, SootClass.SIGNATURES);
		}
		Scene.v().loadNecessaryClasses();
	}

	@After
	public void tearDown() {
		G.reset();
	}

	// ---------------------------------------------------------------- the parameter comparison

	@Test
	public void aStrictTargetAcceptsOnlyTheOverloadItDeclares() {
		TargetMethod valueOfObject = strict(STRING, "valueOf", OBJECT);

		assertTrue("String.valueOf(Object) is the declared overload",
				RvsecAnalysisClient.paramsMatchAtCallSite(ref(STRING, "valueOf", type(OBJECT)),
						valueOfObject));
		assertFalse("String.valueOf(int) is a different overload and STRICT excludes it",
				RvsecAnalysisClient.paramsMatchAtCallSite(ref(STRING, "valueOf", IntType.v()),
						valueOfObject));
		assertFalse("an arity mismatch is rejected before any type is compared",
				RvsecAnalysisClient.paramsMatchAtCallSite(
						ref(STRING, "valueOf", type(OBJECT), IntType.v()), valueOfObject));
	}

	@Test
	public void theDeclaredParametersAreComparedAsWritten() {
		// Why the extractor resolves pointcut parameter types to FQN (part (iii) of the scope
		// boundary (c) repair): Soot writes java.lang.Object at the call site, so a target that
		// kept the simple name the pointcut wrote could never match and STRICT would be
		// unexpressible rather than merely strict.
		assertFalse("the simple name the pointcut wrote never equals what Soot reports",
				RvsecAnalysisClient.paramsMatchAtCallSite(ref(STRING, "valueOf", type(OBJECT)),
						strict(STRING, "valueOf", "Object")));
	}

	// ------------------------------------------------------------- policy is the only variable

	@Test
	public void theSameCallSitePassesLenientAndFailsStrict() {
		TargetMatching matching = new TargetMatching();
		SootMethodRef valueOfInt = ref(STRING, "valueOf", IntType.v());

		TargetMethod lenient = lenient(STRING, "valueOf", OBJECT);
		TargetMethod strict = strict(STRING, "valueOf", OBJECT);
		matching.forceResolveTargets(setOf(lenient, strict));

		assertTrue("LENIENT ignores the signature, so every overload matches",
				RvsecAnalysisClient.matchesAtCallSite(valueOfInt, "valueOf", lenient, matching));
		assertFalse("STRICT is what makes the other overloads unmatchable",
				RvsecAnalysisClient.matchesAtCallSite(valueOfInt, "valueOf", strict, matching));
	}

	// ------------------------------- defect 1: subtype AND strict must honour BOTH constraints

	@Test
	public void aTargetThatIsBothSubtypeAndStrictHonoursBothAxes() {
		TargetMatching matching = new TargetMatching();
		TargetMethod target = new TargetMethod(COLLECTION, "addAll",
				Collections.singletonList(COLLECTION), null, TargetMethod.MatchPolicy.STRICT,
				true, false);
		matching.forceResolveTargets(setOf(target));

		assertTrue("ArrayList <: Collection and the declared overload matches",
				RvsecAnalysisClient.matchesAtCallSite(
						ref(ARRAY_LIST, "addAll", type(COLLECTION)), "addAll", target, matching));
		assertFalse("the subtype holds but the parameter list does not — STRICT still rejects it",
				RvsecAnalysisClient.matchesAtCallSite(
						ref(ARRAY_LIST, "addAll", IntType.v(), type(COLLECTION)), "addAll",
						target, matching));
		assertFalse("the parameter list holds but the type is unrelated",
				RvsecAnalysisClient.matchesAtCallSite(
						ref(STRING, "addAll", type(COLLECTION)), "addAll", target, matching));
	}

	// ------------------------------------ defect 2: a STRICT target may also carry a name pattern

	@Test
	public void aStrictTargetWithANamePatternStillMatchesByPrefix() {
		TargetMatching matching = new TargetMatching();
		TargetMethod target = new TargetMethod(STRING, "valueO*",
				Collections.singletonList(OBJECT), null, TargetMethod.MatchPolicy.STRICT,
				false, true);
		matching.forceResolveTargets(setOf(target));

		assertTrue("the prefix matches and so does the declared overload",
				RvsecAnalysisClient.matchesAtCallSite(ref(STRING, "valueOf", type(OBJECT)),
						"valueOf", target, matching));
		assertFalse("the prefix matches but the overload does not",
				RvsecAnalysisClient.matchesAtCallSite(ref(STRING, "valueOf", IntType.v()),
						"valueOf", target, matching));
		assertFalse("the prefix does not match",
				RvsecAnalysisClient.matchesAtCallSite(ref(STRING, "trim"), "trim", target,
						matching));
	}

	// ------------------------------------------------- the two axes must decide the same way

	@Test
	public void theTransitiveAxisResolvesExactlyWhatTheDirectAxisAccepts() {
		// resolveInScene sweeps Scene.getClasses() calling getMethods(), which opens with
		// checkLevel(SIGNATURES). In the real GATOR Scene every class is at that level or above
		// because Soot loaded the APK; in this bare Scene loadNecessaryClasses leaves the
		// transitive closure at HIERARCHY, so it is raised here rather than the sweep being
		// avoided — avoiding it would be testing something other than what production runs.
		raiseSceneToSignatures();

		TargetMatching matching = new TargetMatching();
		TargetMethod target = strict(STRING, "valueOf", OBJECT);

		Set<String> resolvedParams = TargetResolver.resolveInScene(setOf(target), matching).stream()
				.map(m -> m.getParameterTypes().stream().map(Type::toString)
						.collect(Collectors.joining(",")))
				.collect(Collectors.toSet());

		assertEquals("resolveInScene must seed the declared overload and no other",
				Collections.singleton(OBJECT), resolvedParams);

		// ...and the direct axis agrees, invoke by invoke, on the same two call sites.
		assertTrue(RvsecAnalysisClient.matchesAtCallSite(ref(STRING, "valueOf", type(OBJECT)),
				"valueOf", target, matching));
		assertFalse(RvsecAnalysisClient.matchesAtCallSite(ref(STRING, "valueOf", IntType.v()),
				"valueOf", target, matching));
	}

	// ------------------------------------------------------------------------------- helpers

	private static void raiseSceneToSignatures() {
		// forceResolve pulls further classes in at HIERARCHY, so one pass is not a fixpoint.
		for (int round = 0; round < 20; round++) {
			boolean raised = false;
			for (SootClass cls : new ArrayList<>(Scene.v().getClasses())) {
				if (cls.resolvingLevel() < SootClass.SIGNATURES) {
					Scene.v().forceResolve(cls.getName(), SootClass.SIGNATURES);
					raised = true;
				}
			}
			if (!raised) {
				return;
			}
		}
		throw new IllegalStateException("the Scene did not reach SIGNATURES in 20 rounds");
	}

	private static Type type(String fqn) {
		return Scene.v().getSootClass(fqn).getType();
	}

	/** A call-site reference carrying the descriptor the invoke instruction would carry. */
	private static SootMethodRef ref(String owner, String name, Type... params) {
		return Scene.v().makeMethodRef(Scene.v().getSootClass(owner), name,
				Arrays.asList(params), type(OBJECT), false);
	}

	private static TargetMethod strict(String owner, String name, String... params) {
		return new TargetMethod(owner, name, Arrays.asList(params), null,
				TargetMethod.MatchPolicy.STRICT, false, false);
	}

	private static TargetMethod lenient(String owner, String name, String... params) {
		return new TargetMethod(owner, name, Arrays.asList(params), null,
				TargetMethod.MatchPolicy.LENIENT, false, false);
	}

	private static Set<TargetMethod> setOf(TargetMethod... targets) {
		return new HashSet<>(Arrays.asList(targets));
	}
}

package presto.android.gui.clients.target;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import soot.G;
import soot.Scene;
import soot.SootClass;
import soot.Type;
import soot.options.Options;

/**
 * INV-ANA-42 and INV-ANA-43 on the matching predicate itself, over a minimal Soot Scene
 * bootstrapped from the JDK on the test classpath.
 *
 * <p>The load-bearing case is <b>interface→interface</b> ({@code java.util.List <: java.lang.Iterable}).
 * It is the one that distinguishes the adopted design from the rejected pre-expansion
 * alternative: {@code getActiveHierarchy().getImplementersOf(Iterable)} does not contain
 * {@code List}, so an interface-typed call site would be missed. {@code canStoreType} answers it.
 *
 * <p>The other load-bearing case is the <b>phantom owner</b>. Under
 * {@code allow_phantom_refs=true} an unresolvable type force-resolves to a phantom that passes
 * {@code containsClass}, and {@code canStoreType} then returns a definite, wrong {@code false}
 * instead of throwing — so a try/catch would never fire and the degrade path has to be driven by
 * inspecting the class. What it inspects is <b>hierarchy content</b>, not {@code isPhantom()}:
 * in the real GATOR Scene the JDK owners of both spec sets are read out of the platform
 * {@code android.jar} with a complete hierarchy and flagged phantom anyway, so keying on the flag
 * degraded every one of them. {@link TargetMatching#carriesHierarchy} is the predicate, and both
 * of its sides are asserted below: an invented phantom carries nothing and degrades; a phantom
 * that carries a hierarchy is used.
 */
public class TargetMatchingTest {

	private static final String LIST = "java.util.List";
	private static final String ARRAY_LIST = "java.util.ArrayList";
	private static final String COLLECTION = "java.util.Collection";
	private static final String ITERABLE = "java.lang.Iterable";
	private static final String ABSENT = "com.example.no.Such.Type";
	private static final String PHANTOM_WITH_HIERARCHY = "com.example.PhantomWithHierarchy";

	@Before
	public void bootstrapScene() {
		G.reset();
		Options.v().set_allow_phantom_refs(true);
		Options.v().set_whole_program(false);
		Options.v().set_prepend_classpath(true);
		Options.v().set_soot_classpath(System.getProperty("java.class.path"));
		for (String fqn : new String[] { ITERABLE, COLLECTION, LIST, ARRAY_LIST }) {
			Scene.v().addBasicClass(fqn, SootClass.HIERARCHY);
		}
		Scene.v().loadNecessaryClasses();
	}

	@After
	public void tearDown() {
		G.reset();
	}

	@Test
	public void subtypeMatchOnAConcreteLibraryType() {
		TargetMatching matching = new TargetMatching();
		Set<TargetMethod> targets = setOf(subtypeTarget(COLLECTION, "addAll"));
		matching.forceResolveTargets(targets);

		assertTrue("ArrayList <: Collection must match Collection+.addAll",
				matching.matches(type(ARRAY_LIST), "addAll", subtypeTarget(COLLECTION, "addAll"),
						Scene.v().getOrMakeFastHierarchy()));
	}

	@Test
	public void interfaceToInterfaceMatch() {
		// The A2-vs-A1 discriminator: List is a sub-INTERFACE of Iterable, which the rejected
		// getImplementersOf(Iterable) pre-expansion does not enumerate.
		TargetMatching matching = new TargetMatching();
		TargetMethod target = subtypeTarget(ITERABLE, "iterator");
		matching.forceResolveTargets(setOf(target));

		assertTrue("List <: Iterable must match Iterable+.iterator",
				matching.matches(type(LIST), "iterator", target, Scene.v().getOrMakeFastHierarchy()));
	}

	@Test
	public void exactOwnerPathIgnoresTheHierarchy() {
		// includeSubtypes=false is the JCA path: no hierarchy query at all, so a subtype of the
		// declared owner must NOT match.
		TargetMatching matching = new TargetMatching();
		TargetMethod exact = exactTarget(COLLECTION, "addAll");
		matching.forceResolveTargets(setOf(exact));

		assertTrue(matching.matches(type(COLLECTION), "addAll", exact,
				Scene.v().getOrMakeFastHierarchy()));
		assertFalse("an exact target must not pick up its subtypes",
				matching.matches(type(ARRAY_LIST), "addAll", exact,
						Scene.v().getOrMakeFastHierarchy()));
	}

	@Test
	public void nameIsCheckedBeforeTheHierarchy() {
		// The cost bound depends on this order, and the negative E2E depends on the name axis:
		// with an Object+ owner every type is a subtype, so a non-match can only come from the
		// name.
		TargetMatching matching = new TargetMatching();
		TargetMethod target = patternTarget(COLLECTION, "add*");
		matching.forceResolveTargets(setOf(target));

		assertFalse("remove does not match the pattern add*, subtype or not",
				matching.matches(type(ARRAY_LIST), "remove", target,
						Scene.v().getOrMakeFastHierarchy()));
		// Passing a null hierarchy proves canStoreType was never consulted: a name mismatch
		// returns before the owner axis is touched at all.
		assertFalse("a name mismatch must short-circuit before the hierarchy query",
				matching.matches(type(ARRAY_LIST), "remove", target, null));
	}

	@Test
	public void trailingStarMatchesByPrefix() {
		assertTrue(TargetMatching.nameMatches(patternTarget(COLLECTION, "add*"), "add"));
		assertTrue(TargetMatching.nameMatches(patternTarget(COLLECTION, "add*"), "addAll"));
		assertFalse(TargetMatching.nameMatches(patternTarget(COLLECTION, "add*"), "remove"));
		assertTrue(TargetMatching.nameMatches(patternTarget("java.io.Writer", "write*"), "write"));
		assertFalse(TargetMatching.nameMatches(patternTarget("java.io.Writer", "write*"), "flush"));
	}

	@Test
	public void bareStarMatchesEveryName() {
		// call(* Iterator.*(..)) — prefix "" matches all. This is the intended AspectJ reading
		// and must NOT be special-cased to false; two specs in the corpus depend on it.
		TargetMethod any = patternTarget("java.util.Iterator", "*");
		assertTrue(TargetMatching.nameMatches(any, "next"));
		assertTrue(TargetMatching.nameMatches(any, "hasNext"));
		assertTrue(TargetMatching.nameMatches(any, "anythingAtAll"));
	}

	@Test
	public void nonTrailingStarFallsThroughToEquals() {
		// No spec in the tree writes one, so a general glob is unnecessary; what matters is
		// that it degrades to a safe literal rather than crashing or over-matching.
		TargetMethod odd = patternTarget(COLLECTION, "*Listener");
		assertTrue(TargetMatching.nameMatches(odd, "*Listener"));
		assertFalse(TargetMatching.nameMatches(odd, "clickListener"));
	}

	@Test
	public void absentOwnerDegradesToExactMatchingAndIsReported() {
		TargetMatching matching = new TargetMatching();
		TargetMethod target = subtypeTarget(ABSENT, "m");
		matching.forceResolveTargets(setOf(target));

		assertTrue("an owner that cannot be resolved must be reported by name",
				matching.degradedOwners().contains(ABSENT));
		assertTrue("...and match exactly rather than silently matching nothing",
				matching.matches(phantomType(ABSENT), "m", target,
						Scene.v().getOrMakeFastHierarchy()));
		assertFalse("...and must not pick up unrelated types",
				matching.matches(type(ARRAY_LIST), "m", target,
						Scene.v().getOrMakeFastHierarchy()));
	}

	@Test
	public void phantomOwnerIsTreatedAsUnresolvedNotAsAContainedClass() {
		// containsClass alone is insufficient: force-resolving an unresolvable type under
		// allow_phantom_refs=true puts a phantom SootClass in the Scene that satisfies it.
		Scene.v().forceResolve(ABSENT, SootClass.SIGNATURES);
		assertTrue("precondition: the phantom is in the Scene and would satisfy containsClass",
				Scene.v().containsClass(ABSENT) && Scene.v().getSootClass(ABSENT).isPhantom());

		TargetMatching matching = new TargetMatching();
		TargetMethod target = subtypeTarget(ABSENT, "m");
		Set<soot.RefType> loaded = matching.forceResolveTargets(setOf(target));

		assertEquals("a phantom owner must not be counted as loaded", 0, loaded.size());
		assertTrue("...and must be reported as degraded",
				matching.degradedOwners().contains(ABSENT));
	}

	@Test
	public void anInventedPhantomCarriesNoHierarchyButARealClassDoes() {
		// The two sides of the guard, asserted on the predicate itself so the reason a phantom
		// is rejected is visible rather than inferred from a count.
		SootClass invented = Scene.v().forceResolve(ABSENT, SootClass.SIGNATURES);
		assertFalse("a class Soot invented carries no superclass, no interfaces and no methods",
				TargetMatching.carriesHierarchy(invented));
		assertTrue("a class Soot actually read does",
				TargetMatching.carriesHierarchy(Scene.v().getSootClass(COLLECTION)));
	}

	@Test
	public void aPhantomOwnerThatCarriesItsHierarchyIsUsedNotDegraded() {
		// The regression this guard exists for. Under -force-android-jar the JDK owners of both
		// spec sets arrive resolved-and-flagged-phantom; keying the degrade on isPhantom() alone
		// therefore switched the whole subtype axis off on every real APK.
		SootClass populated = new SootClass(PHANTOM_WITH_HIERARCHY);
		populated.setSuperclass(Scene.v().getSootClass("java.lang.Object"));
		Scene.v().addClass(populated);
		populated.setPhantomClass();
		assertTrue("precondition: the owner is flagged phantom",
				Scene.v().getSootClass(PHANTOM_WITH_HIERARCHY).isPhantom());

		TargetMatching matching = new TargetMatching();
		Set<soot.RefType> loaded =
				matching.forceResolveTargets(setOf(subtypeTarget(PHANTOM_WITH_HIERARCHY, "m")));

		assertEquals("a phantom that carries a hierarchy must be loaded, not degraded",
				1, loaded.size());
		assertTrue("...and must not be reported as degraded",
				matching.degradedOwners().isEmpty());
	}

	@Test
	public void resolvedOwnersAreReportedAsLoaded() {
		TargetMatching matching = new TargetMatching();
		Set<soot.RefType> loaded = matching.forceResolveTargets(
				setOf(subtypeTarget(COLLECTION, "addAll"), subtypeTarget(ITERABLE, "iterator")));
		assertEquals("both JDK owners must force-resolve", 2, loaded.size());
		assertTrue("no degrade may be reported for a JDK type",
				matching.degradedOwners().isEmpty());
	}

	private static Type type(String fqn) {
		return Scene.v().getSootClass(fqn).getType();
	}

	private static Type phantomType(String fqn) {
		return Scene.v().forceResolve(fqn, SootClass.SIGNATURES).getType();
	}

	private static Set<TargetMethod> setOf(TargetMethod... targets) {
		return new HashSet<>(Arrays.asList(targets));
	}

	private static TargetMethod subtypeTarget(String owner, String name) {
		return target(owner, name, true, false);
	}

	private static TargetMethod exactTarget(String owner, String name) {
		return target(owner, name, false, false);
	}

	private static TargetMethod patternTarget(String owner, String name) {
		return target(owner, name, true, true);
	}

	private static TargetMethod target(String owner, String name, boolean includeSubtypes,
			boolean nameIsPattern) {
		List<String> noParams = Collections.emptyList();
		return new TargetMethod(owner, name, noParams, null, TargetMethod.MatchPolicy.LENIENT,
				includeSubtypes, nameIsPattern);
	}
}

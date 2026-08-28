package br.unb.cic.mop.extractor.visitor;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.nio.file.Paths;
import java.util.HashSet;
import java.util.Set;
import java.util.TreeSet;

import org.junit.BeforeClass;
import org.junit.Test;

import br.unb.cic.mop.extractor.JavamopFacade;
import br.unb.cic.mop.extractor.model.MopMethod;

/**
 * INV-ANA-40 over the `generic_new` corpus — the verification fixture of this capability,
 * chosen because it is the only spec set that exercises all four pointcut constructions at
 * once: wildcard imports, the `+` subtype operator, wildcard method names, and the
 * constructor form `Owner.new(..)`.
 *
 * <p><b>The cardinality asserted here was fixed by enumerating the corpus before the visitor
 * was written</b>, not read back off the implementation. The key is
 * <b>{@code (className, includeSubtypes, methodName)}</b> — i.e. the `+` is part of the owner
 * identity, carried by the flag once the operator itself has been stripped. Under that key the
 * corpus holds {@value #EXPECTED_PAIRS} distinct `call()` pairs.
 *
 * <p>Under the alternative `+`-blind key {@code (className, methodName)} the corpus holds
 * {@value #EXPECTED_PAIRS_SUBTYPE_BLIND}: exactly one pair collapses, {@code Iterator.next}
 * (in `Map_UnsafeIterator`) against {@code Iterator+.next} (in `ListIterator_Set`). The change
 * artefacts quote 67 for that key; that figure is an arithmetic slip — the pre-constructor
 * count was 66 and the two constructor pairs are `(java.net.ServerSocket, &lt;init&gt;)` and
 * `(java.util.TreeMap, &lt;init&gt;)`, so 66 + 2 = 68. The ServerSocket constructor pair does
 * NOT merge with the `ServerSocket+` entries: those carry the method names `accept`, `bind`
 * and `setSoTimeout`, none of which is `&lt;init&gt;`. Both keys are asserted below so the
 * distinction stays measured rather than argued.
 */
public class UsedMethodsGenericTest {

	private static final String SPEC_SET = "generic_new";

	/** Distinct `call()` pairs keyed by (className, includeSubtypes, methodName). */
	private static final int EXPECTED_PAIRS = 69;
	/** Distinct `call()` pairs keyed by (className, methodName) — the `+`-blind key. */
	private static final int EXPECTED_PAIRS_SUBTYPE_BLIND = 68;
	/** Distinct owners carrying at least one target, after `+` stripping. */
	private static final int EXPECTED_OWNERS = 21;
	/**
	 * Specs contributing at least one static target. The three that contribute none declare
	 * only `staticinitialization(Owner+)`, which never reaches visit(MethodPointCut) — an
	 * accepted static false-negative (INV-ANA-40 scope boundary (a)).
	 */
	private static final int EXPECTED_SPECS_WITH_TARGETS = 24;

	private static Set<MopMethod> methods;
	private static Set<String> skippedOwners;

	@BeforeClass
	public static void extract() throws Exception {
		JavamopFacade facade = new JavamopFacade();
		methods = facade.listUsedMethods(SpecSets.dir(SPEC_SET), false);
		skippedOwners = new TreeSet<>(facade.getSkippedOwners());
	}

	@Test
	public void testCorpusIsTheOneTheGateWasEnumeratedOver() {
		assertEquals("generic_new must still hold 27 specs; a changed corpus invalidates every"
				+ " cardinality below", 27, SpecSets.specCount(SPEC_SET));
	}

	@Test
	public void testDistinctPairCardinality() {
		assertEquals("distinct (className, includeSubtypes, methodName) pairs", EXPECTED_PAIRS,
				pairsSubtypeAware().size());
		assertEquals("distinct (className, methodName) pairs — only Iterator#next collapses",
				EXPECTED_PAIRS_SUBTYPE_BLIND, pairsSubtypeBlind().size());
		assertEquals("exactly one pair differs only by the subtype flag", 1,
				pairsSubtypeAware().size() - pairsSubtypeBlind().size());
		assertTrue("the collapsing pair is Iterator#next",
				pairsSubtypeAware().contains("java.util.Iterator#next")
						&& pairsSubtypeAware().contains("java.util.Iterator+#next"));
	}

	@Test
	public void testEveryOwnerResolvesWithNoSkips() {
		assertEquals("owners carrying targets", EXPECTED_OWNERS, owners().size());
		// Zero, and the test must go red loudly if the CharSequence_NotInSet repair (adding
		// `import java.util.*;` so its `Set+` owner resolves) is ever reverted.
		assertEquals("generic_new must leave no owner unresolved; a non-empty set here means a"
				+ " spec declares an owner no import of its own registers", new TreeSet<String>(),
				skippedOwners);
		assertTrue("CharSequence_NotInSet's Set+ owner must resolve (its `import java.util.*;`"
				+ " is what makes it resolvable)", pairsSubtypeAware().contains("java.util.Set+#add"));
	}

	@Test
	public void testSubtypeOwnerIsStrippedAndFlagged() {
		MopMethod addAll = find("java.util.Collection", "addAll");
		assertTrue("Collection+ must set includeSubtypes", addAll.isIncludeSubtypes());
		assertTrue("addAll is a literal name, not a pattern", !addAll.isNameIsPattern());
	}

	@Test
	public void testWildcardMethodNamesArePreservedAsPatterns() {
		MopMethod add = find("java.util.Collection", "add*");
		assertTrue("add* must set nameIsPattern", add.isNameIsPattern());
		assertTrue("Collection+ still sets includeSubtypes", add.isIncludeSubtypes());

		// All eight patterns the corpus writes, the bare `*` included.
		for (String pattern : new String[] { "add*", "remove*", "retain*", "clear*", "put*",
				"offer*", "write*", "*" }) {
			assertTrue("pattern " + pattern + " must survive extraction",
					patternNames().contains(pattern));
		}
	}

	@Test
	public void testBareWildcardIsAMatchAllPattern() {
		// `call(* Iterator.*(..))` — exact owner, match-all name. The bare `*` is intended
		// AspectJ semantics, not a degenerate case to reject.
		MopMethod any = find("java.util.Iterator", "*");
		assertTrue("bare * must be a pattern", any.isNameIsPattern());
		assertTrue("Iterator carries no +, so no subtype match", !any.isIncludeSubtypes());
	}

	@Test
	public void testConstructorPointcutsAreMappedNotSkipped() {
		// D9: `new` is what the grammar emits and no Soot method carries it; `<init>` is what
		// every Soot constructor is named. Mapping, not suppression — so the skip count for
		// constructor pointcuts is zero.
		for (String owner : new String[] { "java.net.ServerSocket", "java.util.TreeMap" }) {
			MopMethod ctor = find(owner, "<init>");
			assertTrue(owner + " constructor target carries no subtype flag (no `+` on the"
					+ " pointcut)", !ctor.isIncludeSubtypes());
			assertTrue(owner + " constructor target is not a name pattern", !ctor.isNameIsPattern());
		}
		Set<String> leftovers = new TreeSet<>();
		for (MopMethod m : methods) {
			if ("new".equals(m.getName())) {
				leftovers.add(m.getClassName());
			}
		}
		assertEquals("no target may keep the grammar's literal `new` name", new TreeSet<String>(),
				leftovers);
	}

	@Test
	public void testJavaLangOwnerResolvesThroughItsOwnWildcardImport() {
		// Object_MonitorOwner carries `import java.lang.*;` explicitly. That registration is
		// what resolves the owner — the implicit java.lang package is deliberately not seeded
		// (seeding it would move the frozen jca set; see INV-ANA-40 scope boundary (c)).
		MopMethod wait = find("java.lang.Object", "wait");
		assertTrue("Object+ must set includeSubtypes", wait.isIncludeSubtypes());
	}

	@Test
	public void testSpecCoverage() {
		int withTargets = 0;
		for (File spec : new File(SpecSets.dir(SPEC_SET)).listFiles((d, n) -> n.endsWith(".mop"))) {
			if (!new JavamopFacade().listUsedMethods(spec).isEmpty()) {
				withTargets++;
			}
		}
		assertEquals("specs contributing at least one static target", EXPECTED_SPECS_WITH_TARGETS,
				withTargets);
	}

	@Test
	public void testUnimportedOwnerIsLoggedAndSkippedNeverSilentlyDropped() throws Exception {
		// Synthetic fixture, deliberately outside the real corpus: `Charset+` in a spec that
		// imports only java.io. Resolvability is import-driven, not a property of being a JDK
		// class — this is the regression guard for the class of defect that
		// CharSequence_NotInSet had. The fixture's owner was `Object+` until phase 5.6 made
		// `java.lang` the third resolution step; `Charset` is unresolvable through all three.
		JavamopFacade facade = new JavamopFacade();
		String dir = Paths.get("src", "test", "resources", "unresolvable_owner").toAbsolutePath()
				.normalize().toString();
		Set<MopMethod> extracted = facade.listUsedMethods(dir, false);

		assertTrue("an unresolvable owner contributes no target", extracted.isEmpty());
		assertEquals("...and is reported by name rather than dropped in silence",
				new TreeSet<>(java.util.Collections.singleton("Charset")),
				new TreeSet<>(facade.getSkippedOwners()));
	}

	@Test
	public void testImplicitPackageIsTheThirdResolutionStepAndIsRecordedAsSuch() throws Exception {
		// The other half of the same rule, and the reason the fixture above had to change: an
		// owner in java.lang that no import registers now RESOLVES, through the third step, and
		// the route is recorded so the gator can bound it with MatchPolicy.STRICT. Asserting
		// both halves in the same class keeps them from drifting apart — a seed that resolved
		// everything, or one that recorded nothing, fails one of the two.
		JavamopFacade facade = new JavamopFacade();
		String dir = Paths.get("src", "test", "resources", "implicit_owner").toAbsolutePath()
				.normalize().toString();
		Set<MopMethod> extracted = facade.listUsedMethods(dir, false);

		assertEquals("the java.lang owner resolves through the implicit package", 1,
				extracted.size());
		MopMethod m = extracted.iterator().next();
		assertEquals("java.lang.StringBuilder", m.getClassName());
		assertTrue("and the route is recorded, which is what makes it STRICT downstream",
				m.isOwnerFromImplicitSeed());
		assertEquals("nothing is skipped", new TreeSet<String>(),
				new TreeSet<>(facade.getSkippedOwners()));
	}

	private static MopMethod find(String className, String methodName) {
		for (MopMethod m : methods) {
			if (m.getClassName().equals(className) && m.getName().equals(methodName)) {
				return m;
			}
		}
		throw new AssertionError("no target " + className + "#" + methodName + " was extracted");
	}

	private static Set<String> pairsSubtypeAware() {
		Set<String> pairs = new TreeSet<>();
		for (MopMethod m : methods) {
			pairs.add(m.getClassName() + (m.isIncludeSubtypes() ? "+" : "") + "#" + m.getName());
		}
		return pairs;
	}

	private static Set<String> pairsSubtypeBlind() {
		Set<String> pairs = new TreeSet<>();
		for (MopMethod m : methods) {
			pairs.add(m.getClassName() + "#" + m.getName());
		}
		return pairs;
	}

	private static Set<String> owners() {
		Set<String> owners = new TreeSet<>();
		for (MopMethod m : methods) {
			owners.add(m.getClassName());
		}
		return owners;
	}

	private static Set<String> patternNames() {
		Set<String> names = new HashSet<>();
		for (MopMethod m : methods) {
			if (m.isNameIsPattern()) {
				names.add(m.getName());
			}
		}
		return names;
	}
}

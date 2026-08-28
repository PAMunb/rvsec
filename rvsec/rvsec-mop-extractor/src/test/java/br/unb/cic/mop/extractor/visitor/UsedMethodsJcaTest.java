package br.unb.cic.mop.extractor.visitor;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.junit.Test;

import br.unb.cic.mop.extractor.JavamopFacade;
import br.unb.cic.mop.extractor.model.MopMethod;

/**
 * The JCA-family gate: no drift on the frozen ruler, and the `+` path proven on the set that
 * is actually in production.
 *
 * <p>This is <b>the</b> load-bearing JCA regression gate. `MopSpecsParityTest` on the gator
 * side compares {@code MopSpecsTargetSource.load()} against {@code JavamopFacade.listUsedMethods()}
 * on the same directory — both sides run through the very visitor this change modifies, so it
 * cannot detect an extractor-side JCA regression. The literal count below can.
 *
 * <p>The two sets are asserted differently on purpose:
 * <ul>
 *   <li><b>`jca` is frozen</b> (gh101), so it is pinned by literal: <b>122</b> signatures /
 *       <b>70</b> pairs / <b>23</b> owners. The freeze forbids an <em>unenumerated</em> move, not
 *       every move: phase 5.6 seeds the implicit {@code java.lang} package and thereby resolves
 *       the two {@code RandomStringPassword.mop} pointcuts that had never loaded, taking the
 *       triple from 120/68/22. Those two rows, and nothing else, are the whole difference —
 *       {@link #testSeededStringTargetsAreTheWholeJcaDelta} asserts them by name so the literal
 *       above cannot be raised again without the same enumeration.</li>
 *   <li><b>`jca_android` is the live successor</b> and is being edited right now (gh109 took it
 *       from 23 to 48 specs during this change's own lifetime), so every count here is
 *       <b>derived by enumeration</b> and never pinned. Only the set-independent properties are
 *       asserted.</li>
 * </ul>
 */
public class UsedMethodsJcaTest {

	/** Frozen: signatures emitted from the 23 `jca` specs. Was 120 before the phase-5.6 seed. */
	private static final int JCA_SIGNATURES = 122;
	/** Frozen: distinct (className, methodName) pairs. Was 68. */
	private static final int JCA_PAIRS = 70;
	/** Frozen: distinct owners. Was 22; `java.lang.String` is the one that joins. */
	private static final int JCA_OWNERS = 23;

	/**
	 * The 11 `jca` owners whose targets come from a constructor pointcut. Under D9 these emit
	 * `&lt;init&gt;`; before it they emitted the literal `new`, which no Soot method carries —
	 * so the published ruler had never counted a constructor call site, `new SecretKeySpec(...)`
	 * included.
	 */
	private static final String[] JCA_CONSTRUCTOR_OWNERS = {
			"java.security.KeyPair",
			"java.security.SecureRandom",
			"javax.crypto.CipherInputStream",
			"javax.crypto.CipherOutputStream",
			"javax.crypto.spec.DHGenParameterSpec",
			"javax.crypto.spec.GCMParameterSpec",
			"javax.crypto.spec.IvParameterSpec",
			"javax.crypto.spec.PBEKeySpec",
			"javax.crypto.spec.PBEParameterSpec",
			"javax.crypto.spec.SecretKeySpec",
			"javax.xml.crypto.dsig.spec.HMACParameterSpec" };

	@Test
	public void testFrozenJcaSetDoesNotDrift() throws Exception {
		JavamopFacade facade = new JavamopFacade();
		Set<MopMethod> methods = facade.listUsedMethods(SpecSets.dir("jca"), false);

		assertEquals("the frozen jca corpus must still hold 23 specs", 23, SpecSets.specCount("jca"));
		assertEquals("jca signatures", JCA_SIGNATURES, methods.size());
		assertEquals("jca (class, method) pairs", JCA_PAIRS, pairs(methods).size());
		assertEquals("jca owners", JCA_OWNERS, owners(methods).size());

		for (MopMethod m : methods) {
			assertTrue("no jca pointcut declares a `+` owner: " + m, !m.isIncludeSubtypes());
			assertTrue("no jca pointcut declares a wildcard method name: " + m, !m.isNameIsPattern());
		}
	}

	@Test
	public void testJcaConstructorTargetsAreNamedInit() {
		// D9 does not move the jca triple — the 18 constructor rows already existed and only
		// the emitted name changes. What changes is that they can now resolve at all.
		Set<MopMethod> methods = extract("jca");
		Set<String> initOwners = new TreeSet<>();
		Set<String> literalNew = new TreeSet<>();
		for (MopMethod m : methods) {
			if ("<init>".equals(m.getName())) {
				initOwners.add(m.getClassName());
			}
			if ("new".equals(m.getName())) {
				literalNew.add(m.getClassName());
			}
		}
		assertEquals("constructor owners in jca", new TreeSet<>(java.util.Arrays.asList(
				JCA_CONSTRUCTOR_OWNERS)), initOwners);
		assertEquals("no target may keep the grammar's literal `new` name", new TreeSet<String>(),
				literalNew);
	}

	@Test
	public void testNoOwnerIsLeftUnresolvedInEitherJcaSet() throws Exception {
		// Scope boundary (c) / RISK-013, in its repaired form. This assertion INVERTED in phase
		// 5.6. It used to require that `String` stay unresolved and be *logged* — unresolved and
		// silent being the state that made the risk grave — while the measurement repair waited
		// for a later change. The repair landed here instead, so the same boundary is now
		// asserted from the other side: no owner is skipped at all, which is the only shape in
		// which the boundary is fully closed. A seed that resolved the owner while leaving some
		// other owner silently dropped would fail here, as would a regression that stopped
		// seeding.
		for (String specSet : new String[] { "jca", "jca_android" }) {
			JavamopFacade facade = new JavamopFacade();
			facade.listUsedMethods(SpecSets.dir(specSet), false);
			assertEquals(specSet + ": no owner may be left unresolved after the java.lang seed",
					new TreeSet<String>(), new TreeSet<>(facade.getSkippedOwners()));
		}
	}

	@Test
	public void testSeededStringTargetsAreTheWholeJcaDelta() {
		// The enumeration the gh101 freeze doctrine requires, asserted rather than written in a
		// commit message. Exactly two rows join the frozen set, both from RandomStringPassword,
		// and both carry FQN parameters — without which the STRICT policy the gator attaches to
		// them (owner resolved through the implicit package) could never match, since
		// TargetResolver compares against the Soot signature, which reads java.lang.Object.
		Set<MopMethod> seeded = new TreeSet<>(java.util.Comparator.comparing(MopMethod::toString));
		for (MopMethod m : extract("jca")) {
			if (m.isOwnerFromImplicitSeed()) {
				seeded.add(m);
			}
		}
		assertEquals("exactly two jca targets resolve through the implicit java.lang package",
				2, seeded.size());
		Set<String> described = new TreeSet<>();
		for (MopMethod m : seeded) {
			described.add(m.getClassName() + "#" + m.getName() + m.getParametersAsString());
			assertTrue("a seeded owner is never a subtype owner: " + m, !m.isIncludeSubtypes());
		}
		assertEquals(new TreeSet<>(java.util.Arrays.asList(
				"java.lang.String#toCharArray()",
				"java.lang.String#valueOf(java.lang.Object)")), described);
	}

	@Test
	public void testOwnersResolvedByAnImportAreNotMarkedSeeded() {
		// The criterion is the ROUTE, not the package. If it were the package, every java.lang
		// owner would become STRICT — including generic_new's Object+/Comparable+/CharSequence+,
		// which declare `(..)` parameters and would then match nothing. This asserts the
		// distinction on the set where it would do damage.
		for (MopMethod m : extract("generic_new")) {
			assertTrue("generic_new resolves every owner through its own imports, so none may be"
					+ " marked as seeded: " + m, !m.isOwnerFromImplicitSeed());
		}
	}

	@Test
	public void testProductionSetResolvesItsSubtypeOwners() {
		// The only assertion in this change that proves the `+` repair against the set actually
		// in production. `jca_android` declares exactly two subtype owners — Key+.getEncoded
		// (KeySpec.mop) and SecretKey+.getEncoded (SecretKeySpec.mop) — and both loaded zero
		// targets before this change. Asserted by property, never by count: gh109 is still
		// adding specs to this directory.
		Set<MopMethod> methods = extract("jca_android");
		Set<String> subtypeTargets = new TreeSet<>();
		for (MopMethod m : methods) {
			if (m.isIncludeSubtypes()) {
				subtypeTargets.add(m.getClassName() + "#" + m.getName());
			}
			assertTrue("jca_android declares no wildcard method name: " + m, !m.isNameIsPattern());
		}
		assertEquals("the subtype owners jca_android declares",
				new TreeSet<>(java.util.Arrays.asList(
						"java.security.Key#getEncoded", "javax.crypto.SecretKey#getEncoded")),
				subtypeTargets);
	}

	@Test
	public void testProductionSetConstructorCountIsDerivedNotPinned() throws IOException {
		// Enumerate `call(Owner.new(` in the directory and require the extractor to emit an
		// `<init>` target for every owner it finds. A literal count would go red on gh109 doing
		// the right thing.
		Set<String> declared = constructorOwnersDeclaredIn("jca_android");
		Set<String> emitted = new TreeSet<>();
		for (MopMethod m : extract("jca_android")) {
			if ("<init>".equals(m.getName())) {
				emitted.add(simpleName(m.getClassName()));
			}
		}
		assertTrue("jca_android must declare at least one constructor pointcut for this gate to"
				+ " mean anything", !declared.isEmpty());
		assertEquals("every declared constructor owner must emit an <init> target", declared,
				emitted);
	}

	private static Set<String> constructorOwnersDeclaredIn(String specSet) throws IOException {
		// `call (public IvParameterSpec.new(byte[]))` — the modifier and the space after
		// `call` are both admitted by the grammar and both occur in the corpus.
		Pattern ctor = Pattern.compile("call\\s*\\(\\s*(?:\\w+\\s+)*?(\\w+)\\.new\\s*\\(");
		Set<String> owners = new TreeSet<>();
		for (File spec : new File(SpecSets.dir(specSet)).listFiles((d, n) -> n.endsWith(".mop"))) {
			Matcher m = ctor.matcher(new String(Files.readAllBytes(spec.toPath()), StandardCharsets.UTF_8));
			while (m.find()) {
				owners.add(m.group(1));
			}
		}
		return owners;
	}

	private static String simpleName(String fqn) {
		return fqn.substring(fqn.lastIndexOf('.') + 1);
	}

	private static Set<MopMethod> extract(String specSet) {
		try {
			return new JavamopFacade().listUsedMethods(SpecSets.dir(specSet), false);
		} catch (Exception e) {
			throw new AssertionError("extraction failed for " + specSet, e);
		}
	}

	private static Set<String> pairs(Set<MopMethod> methods) {
		Set<String> pairs = new TreeSet<>();
		for (MopMethod m : methods) {
			pairs.add(m.getClassName() + "#" + m.getName());
		}
		return pairs;
	}

	private static Set<String> owners(Set<MopMethod> methods) {
		Set<String> owners = new TreeSet<>();
		for (MopMethod m : methods) {
			owners.add(m.getClassName());
		}
		return owners;
	}
}

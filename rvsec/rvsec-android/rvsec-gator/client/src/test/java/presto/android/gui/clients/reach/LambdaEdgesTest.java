package presto.android.gui.clients.reach;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import soot.G;
import soot.Modifier;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Type;
import soot.VoidType;
import soot.jimple.InvokeStmt;
import soot.jimple.Jimple;
import soot.jimple.JimpleBody;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;
import soot.options.Options;

/**
 * {@link LambdaEdges} on classes built in a Soot Scene bootstrapped from the JDK on the test
 * classpath (the idiom of {@code CallSiteMatchPolicyTest}). The app holds:
 * <ul>
 *   <li>{@code p.Main}: static {@code lambda$0} (calls {@code save}), {@code lambda$1},
 *       {@code save}, {@code other};</li>
 *   <li>{@code p.Main$$ExternalSyntheticLambda0.onClick} → {@code lambda$0} and
 *       {@code p.Main$$ExternalSyntheticLambda1.onClick} → {@code lambda$1};</li>
 *   <li>{@code p.Main$1 implements p.Listener}: {@code onClick} → {@code save} (one invoke) and
 *       {@code helper} → {@code save} (not the abstract method);</li>
 *   <li>{@code p.Main$2 implements p.Listener}: {@code onClick} → {@code save}, {@code other}
 *       (two invokes).</li>
 * </ul>
 */
public class LambdaEdgesTest {

	private final Map<SootClass, List<SootMethod>> appClasses = new LinkedHashMap<>();
	private SootClass listener;
	private SootMethod lambda0;
	private SootMethod lambda1;
	private SootMethod save;
	private SootMethod other;
	private SootMethod wrapper0;
	private SootMethod wrapper1;
	private SootMethod samOnClick;
	private SootMethod samHelper;
	private SootMethod twoInvokes;

	@Before
	public void buildScene() {
		G.reset();
		Options.v().set_allow_phantom_refs(true);
		Options.v().set_whole_program(false);
		Options.v().set_prepend_classpath(true);
		Options.v().set_soot_classpath(System.getProperty("java.class.path"));
		Scene.v().addBasicClass("java.lang.Object", SootClass.SIGNATURES);
		Scene.v().loadNecessaryClasses();

		listener = newClass("p.Listener", Modifier.PUBLIC | Modifier.INTERFACE | Modifier.ABSTRACT);
		listener.addMethod(new SootMethod("onClick", Collections.<Type>emptyList(), VoidType.v(),
				Modifier.PUBLIC | Modifier.ABSTRACT));

		SootClass main = newClass("p.Main", Modifier.PUBLIC);
		save = staticMethod(main, "save");
		other = staticMethod(main, "other");
		lambda0 = staticMethod(main, "lambda$0", save);
		lambda1 = staticMethod(main, "lambda$1");
		app(main);

		SootClass w0 = newClass("p.Main$$ExternalSyntheticLambda0", Modifier.FINAL);
		w0.addInterface(listener);
		wrapper0 = instanceMethod(w0, "onClick", lambda0);
		app(w0);

		SootClass w1 = newClass("p.Main$$ExternalSyntheticLambda1", Modifier.FINAL);
		w1.addInterface(listener);
		wrapper1 = instanceMethod(w1, "onClick", lambda1);
		app(w1);

		SootClass sam = newClass("p.Main$1", 0);
		sam.addInterface(listener);
		samOnClick = instanceMethod(sam, "onClick", save);
		samHelper = instanceMethod(sam, "helper", save);
		app(sam);

		SootClass two = newClass("p.Main$2", 0);
		two.addInterface(listener);
		twoInvokes = instanceMethod(two, "onClick", save, other);
		app(two);
	}

	@After
	public void tearDown() {
		G.reset();
	}

	private SootClass newClass(String name, int modifiers) {
		SootClass c = new SootClass(name, modifiers);
		c.setSuperclass(Scene.v().getSootClass("java.lang.Object"));
		c.setResolvingLevel(SootClass.BODIES);
		Scene.v().addClass(c);
		return c;
	}

	private void app(SootClass c) {
		appClasses.put(c, new ArrayList<>(c.getMethods()));
	}

	private static SootMethod staticMethod(SootClass owner, String name, SootMethod... callees) {
		return method(owner, name, Modifier.PUBLIC | Modifier.STATIC, callees);
	}

	private static SootMethod instanceMethod(SootClass owner, String name, SootMethod... callees) {
		return method(owner, name, Modifier.PUBLIC, callees);
	}

	/** A {@code void name()} whose body calls each callee once, statically, then returns. */
	private static SootMethod method(SootClass owner, String name, int modifiers,
			SootMethod... callees) {
		SootMethod m = new SootMethod(name, Collections.<Type>emptyList(), VoidType.v(), modifiers);
		owner.addMethod(m);
		JimpleBody body = Jimple.v().newBody(m);
		for (SootMethod callee : callees) {
			body.getUnits().add(Jimple.v().newInvokeStmt(
					Jimple.v().newStaticInvokeExpr(callee.makeRef())));
		}
		body.getUnits().add(Jimple.v().newReturnVoidStmt());
		m.setActiveBody(body);
		return m;
	}

	private static Set<String> edges(CallGraph cg) {
		Set<String> out = new HashSet<>();
		for (Edge e : cg) {
			out.add(e.src().getDeclaringClass().getName() + "." + e.src().getName() + " -> "
					+ e.tgt().getDeclaringClass().getName() + "." + e.tgt().getName());
		}
		return out;
	}

	@Test
	public void aWrapperIsLinkedToItsOwnBodyOnly() {
		CallGraph cg = new CallGraph();
		LambdaEdges.addTo(cg, appClasses);

		Set<String> edges = edges(cg);
		assertTrue(edges.contains("p.Main$$ExternalSyntheticLambda0.onClick -> p.Main.lambda$0"));
		assertTrue(edges.contains("p.Main$$ExternalSyntheticLambda1.onClick -> p.Main.lambda$1"));
		assertFalse("a sibling wrapper does not reach the other body",
				edges.contains("p.Main$$ExternalSyntheticLambda1.onClick -> p.Main.lambda$0"));
	}

	@Test
	public void aSingleInvokeSamImplementationIsLinkedToItsCallee() {
		CallGraph cg = new CallGraph();
		LambdaEdges.addTo(cg, appClasses);

		Set<String> edges = edges(cg);
		assertTrue(edges.contains("p.Main$1.onClick -> p.Main.save"));
		assertFalse("only the single abstract method is linked",
				edges.contains("p.Main$1.helper -> p.Main.save"));
		assertFalse("a SAM body with two invokes is not linked",
				edges.contains("p.Main$2.onClick -> p.Main.save"));
		assertFalse("ordinary app methods are not linked", edges.contains("p.Main.lambda$0 -> p.Main.save"));
		assertEquals(3, cg.size());
	}

	@Test
	public void anEdgeAlreadyInTheCallGraphIsNotAddedAgain() {
		CallGraph cg = new CallGraph();
		InvokeStmt site = (InvokeStmt) wrapper0.getActiveBody().getUnits().getFirst();
		cg.addEdge(new Edge(wrapper0, site, lambda0));

		int added = LambdaEdges.addTo(cg, appClasses);

		assertEquals(2, added);
		assertEquals(3, cg.size());
	}

	@Test
	public void theWrapperGetsItsOwnDistance() {
		// The wrapper -> lambda$0 -> save chain, with save the direct caller: the wrapper is two
		// calls away, its sibling none.
		CallGraph cg = new CallGraph();
		InvokeStmt site = (InvokeStmt) lambda0.getActiveBody().getUnits().getFirst();
		cg.addEdge(new Edge(lambda0, site, save));
		LambdaEdges.addTo(cg, appClasses);

		ReachabilityIndex index = new ReachabilityIndex(Collections.emptySet(),
				Collections.emptySet(), new HashSet<>(Arrays.asList(save)));
		TargetDistances<SootMethod> d = TargetDistances.compute(cg, index, appClasses,
				Collections.emptySet());

		assertEquals(Collections.singletonList(save), d.targets());
		assertArrayEquals(new int[][] { { 0, 2 } }, d.pairs(wrapper0));
		assertArrayEquals(new int[][] { { 0, 1 } }, d.pairs(lambda0));
		assertArrayEquals(new int[][] { { 0, 1 } }, d.pairs(samOnClick));
		assertEquals(0, d.pairs(wrapper1).length);
		assertEquals(0, d.pairs(twoInvokes).length);
		assertEquals(0, d.pairs(samHelper).length);
	}

	@Test
	public void lambdaClassNames() {
		assertTrue(LambdaEdges.isLambdaClass("a.B$$ExternalSyntheticLambda3"));
		assertTrue(LambdaEdges.isLambdaClass("a.B$$Lambda$1"));
		assertFalse(LambdaEdges.isLambdaClass("a.B$1"));
	}
}

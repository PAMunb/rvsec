package presto.android.gui.clients.reach;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import soot.G;
import soot.Kind;
import soot.Local;
import soot.Modifier;
import soot.Scene;
import soot.SootClass;
import soot.SootField;
import soot.SootMethod;
import soot.Type;
import soot.Unit;
import soot.VoidType;
import soot.jimple.InvokeExpr;
import soot.jimple.InvokeStmt;
import soot.jimple.Jimple;
import soot.jimple.JimpleBody;
import soot.jimple.Stmt;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;
import soot.options.Options;

/**
 * {@link EmptySiteEdges} on classes built in a Soot Scene bootstrapped from the JDK on the test
 * classpath (the idiom of {@link LambdaEdgesTest}). Every call site starts with no edge, as SPARK
 * leaves it when the receiver has no allocation it follows. The app holds:
 * <ul>
 *   <li>{@code p.Act}: {@code onNewIntent} calls {@code this.addToken()} (virtual),
 *       {@code onCreate} calls the private {@code this.init()} (special), {@code callStatic}
 *       calls the static {@code helper()}, and {@code broken} is concrete with no body;</li>
 *   <li>{@code p.UseCase.encryptNote} calls {@code this.helper.encrypt()} on the field type
 *       {@code p.Helper};</li>
 *   <li>{@code p.Loader.loadAll} calls {@code this.repo.load()} on the interface {@code p.Repo},
 *       implemented by the app classes {@code p.DbRepo} and {@code p.NetRepo} and by the library
 *       class {@code androidx.room.RoomRepo}, which the app class {@code p.CachedRepo} extends
 *       without overriding {@code load};</li>
 *   <li>{@code p.A.run} calls {@code this.b.work()} on {@code p.B}, overridden by the app
 *       subclass {@code p.C};</li>
 *   <li>{@code p.Canvas.paint} calls {@code this.shape.draw()} on the abstract {@code p.Shape},
 *       whose only subclass {@code p.RoundShape} is abstract too.</li>
 * </ul>
 */
public class EmptySiteEdgesTest {

	private final Map<SootClass, List<SootMethod>> appClasses = new LinkedHashMap<>();
	private SootMethod onNewIntent;
	private SootMethod onCreate;
	private SootMethod callStatic;
	private SootMethod encryptNote;
	private SootMethod loadAll;
	private SootMethod run;
	private SootMethod bWork;
	private SootMethod paint;

	@Before
	public void buildScene() {
		G.reset();
		Options.v().set_allow_phantom_refs(true);
		Options.v().set_whole_program(false);
		Options.v().set_prepend_classpath(true);
		Options.v().set_soot_classpath(System.getProperty("java.class.path"));
		Scene.v().addBasicClass("java.lang.Object", SootClass.SIGNATURES);
		Scene.v().loadNecessaryClasses();

		SootClass act = newClass("p.Act", Modifier.PUBLIC, null);
		SootMethod addToken = leaf(act, "addToken", Modifier.PUBLIC);
		SootMethod init = leaf(act, "init", Modifier.PRIVATE);
		SootMethod helper = leaf(act, "helper", Modifier.PUBLIC | Modifier.STATIC);
		onNewIntent = caller(act, "onNewIntent", null, Kind.VIRTUAL, addToken);
		onCreate = caller(act, "onCreate", null, Kind.SPECIAL, init);
		callStatic = caller(act, "callStatic", null, Kind.STATIC, helper);
		act.addMethod(new SootMethod("broken", Collections.<Type>emptyList(), VoidType.v(),
				Modifier.PUBLIC));
		app(act);

		SootClass helperCls = newClass("p.Helper", Modifier.PUBLIC, null);
		SootMethod encrypt = leaf(helperCls, "encrypt", Modifier.PUBLIC);
		app(helperCls);
		SootClass useCase = newClass("p.UseCase", Modifier.PUBLIC, null);
		encryptNote = caller(useCase, "encryptNote", field(useCase, "helper", helperCls), Kind.VIRTUAL,
				encrypt);
		app(useCase);

		SootClass repo = newClass("p.Repo", Modifier.PUBLIC | Modifier.INTERFACE | Modifier.ABSTRACT,
				null);
		SootMethod load = abstractMethod(repo, "load");
		app(repo);
		for (String name : new String[] { "p.DbRepo", "p.NetRepo" }) {
			SootClass impl = newClass(name, Modifier.PUBLIC, null);
			impl.addInterface(repo);
			leaf(impl, "load", Modifier.PUBLIC);
			app(impl);
		}
		SootClass roomRepo = newClass("androidx.room.RoomRepo", Modifier.PUBLIC, null);
		roomRepo.addInterface(repo);
		leaf(roomRepo, "load", Modifier.PUBLIC);
		app(newClass("p.CachedRepo", Modifier.PUBLIC, roomRepo));
		SootClass loader = newClass("p.Loader", Modifier.PUBLIC, null);
		loadAll = caller(loader, "loadAll", field(loader, "repo", repo), Kind.INTERFACE, load);
		app(loader);

		SootClass b = newClass("p.B", Modifier.PUBLIC, null);
		bWork = leaf(b, "work", Modifier.PUBLIC);
		app(b);
		SootClass c = newClass("p.C", Modifier.PUBLIC, b);
		leaf(c, "work", Modifier.PUBLIC);
		app(c);
		SootClass a = newClass("p.A", Modifier.PUBLIC, null);
		run = caller(a, "run", field(a, "b", b), Kind.VIRTUAL, bWork);
		app(a);

		SootClass shape = newClass("p.Shape", Modifier.PUBLIC | Modifier.ABSTRACT, null);
		SootMethod draw = abstractMethod(shape, "draw");
		app(shape);
		app(newClass("p.RoundShape", Modifier.PUBLIC | Modifier.ABSTRACT, shape));
		SootClass canvas = newClass("p.Canvas", Modifier.PUBLIC, null);
		paint = caller(canvas, "paint", field(canvas, "shape", shape), Kind.VIRTUAL, draw);
		app(canvas);
	}

	@After
	public void tearDown() {
		G.reset();
	}

	private SootClass newClass(String name, int modifiers, SootClass superclass) {
		SootClass c = new SootClass(name, modifiers);
		c.setSuperclass(superclass != null ? superclass : Scene.v().getSootClass("java.lang.Object"));
		c.setResolvingLevel(SootClass.BODIES);
		Scene.v().addClass(c);
		return c;
	}

	private void app(SootClass c) {
		appClasses.put(c, new ArrayList<>(c.getMethods()));
	}

	private static SootField field(SootClass owner, String name, SootClass type) {
		SootField f = new SootField(name, type.getType(), Modifier.PRIVATE);
		owner.addField(f);
		return f;
	}

	private static SootMethod abstractMethod(SootClass owner, String name) {
		SootMethod m = new SootMethod(name, Collections.<Type>emptyList(), VoidType.v(),
				Modifier.PUBLIC | Modifier.ABSTRACT);
		owner.addMethod(m);
		return m;
	}

	/** A {@code void name()} whose body only returns. */
	private static SootMethod leaf(SootClass owner, String name, int modifiers) {
		SootMethod m = new SootMethod(name, Collections.<Type>emptyList(), VoidType.v(), modifiers);
		owner.addMethod(m);
		JimpleBody body = Jimple.v().newBody(m);
		body.getUnits().add(Jimple.v().newReturnVoidStmt());
		m.setActiveBody(body);
		return m;
	}

	/**
	 * A public {@code void name()} that invokes {@code callee} once with the given kind, on
	 * {@code this} or, when {@code via} is set, on the value loaded from that field of
	 * {@code this}; a static kind invokes the callee with no receiver.
	 */
	private static SootMethod caller(SootClass owner, String name, SootField via, Kind kind,
			SootMethod callee) {
		SootMethod m = new SootMethod(name, Collections.<Type>emptyList(), VoidType.v(),
				Modifier.PUBLIC);
		owner.addMethod(m);
		JimpleBody body = Jimple.v().newBody(m);
		Local self = Jimple.v().newLocal("r0", owner.getType());
		body.getLocals().add(self);
		body.getUnits().add(Jimple.v().newIdentityStmt(self, Jimple.v().newThisRef(owner.getType())));
		Local receiver = self;
		if (via != null) {
			receiver = Jimple.v().newLocal("r1", via.getType());
			body.getLocals().add(receiver);
			body.getUnits().add(Jimple.v().newAssignStmt(receiver,
					Jimple.v().newInstanceFieldRef(self, via.makeRef())));
		}
		InvokeExpr ie;
		if (kind == Kind.VIRTUAL) {
			ie = Jimple.v().newVirtualInvokeExpr(receiver, callee.makeRef());
		} else if (kind == Kind.INTERFACE) {
			ie = Jimple.v().newInterfaceInvokeExpr(receiver, callee.makeRef());
		} else if (kind == Kind.SPECIAL) {
			ie = Jimple.v().newSpecialInvokeExpr(receiver, callee.makeRef());
		} else {
			ie = Jimple.v().newStaticInvokeExpr(callee.makeRef());
		}
		body.getUnits().add(Jimple.v().newInvokeStmt(ie));
		body.getUnits().add(Jimple.v().newReturnVoidStmt());
		m.setActiveBody(body);
		return m;
	}

	/** The single invoke statement of a {@link #caller} body. */
	private static Stmt site(SootMethod m) {
		for (Unit u : m.getActiveBody().getUnits()) {
			if (u instanceof InvokeStmt) {
				return (Stmt) u;
			}
		}
		throw new AssertionError("no invoke in " + m.getSignature());
	}

	/** {@code "class.method kind"} for each edge out of the site of {@code m}. */
	private static Set<String> edgesAt(CallGraph cg, SootMethod m) {
		Set<String> out = new HashSet<>();
		Iterator<Edge> it = cg.edgesOutOf(site(m));
		while (it.hasNext()) {
			Edge e = it.next();
			out.add(e.tgt().getDeclaringClass().getName() + "." + e.tgt().getName() + " "
					+ e.kind());
		}
		return out;
	}

	private static Set<String> setOf(String... values) {
		return new HashSet<>(Arrays.asList(values));
	}

	@Test
	public void aCallOnThisGetsItsEdge() {
		CallGraph cg = new CallGraph();
		EmptySiteEdges.addTo(cg, appClasses, new ArrayList<>());

		assertEquals(setOf("p.Act.addToken " + Kind.VIRTUAL), edgesAt(cg, onNewIntent));
	}

	@Test
	public void aCallThroughAFieldGetsItsEdge() {
		CallGraph cg = new CallGraph();
		EmptySiteEdges.addTo(cg, appClasses, new ArrayList<>());

		assertEquals(setOf("p.Helper.encrypt " + Kind.VIRTUAL), edgesAt(cg, encryptNote));
	}

	@Test
	public void aSpecialInvokeGoesToItsResolvedMethod() {
		CallGraph cg = new CallGraph();
		EmptySiteEdges.addTo(cg, appClasses, new ArrayList<>());

		assertEquals(setOf("p.Act.init " + Kind.SPECIAL), edgesAt(cg, onCreate));
	}

	@Test
	public void anInterfaceCallFansOutToTheAppImplementersOnly() {
		CallGraph cg = new CallGraph();
		EmptySiteEdges.addTo(cg, appClasses, new ArrayList<>());

		Set<String> edges = edgesAt(cg, loadAll);
		assertEquals(setOf("p.DbRepo.load " + Kind.INTERFACE, "p.NetRepo.load " + Kind.INTERFACE),
				edges);
		assertFalse("the library implementation, inherited by p.CachedRepo, is not a callee",
				edges.contains("androidx.room.RoomRepo.load " + Kind.INTERFACE));
	}

	@Test
	public void aResolvedSiteIsNotTouched() {
		CallGraph cg = new CallGraph();
		cg.addEdge(new Edge(run, site(run), bWork));
		EmptySiteEdges.addTo(cg, appClasses, new ArrayList<>());

		assertEquals("the app override p.C.work is not added next to the SPARK edge",
				setOf("p.B.work " + Kind.VIRTUAL), edgesAt(cg, run));
	}

	@Test
	public void aStaticInvokeIsNotTouched() {
		CallGraph cg = new CallGraph();
		EmptySiteEdges.addTo(cg, appClasses, new ArrayList<>());

		assertTrue(edgesAt(cg, callStatic).isEmpty());
	}

	@Test
	public void anAbstractOnlyHierarchyGivesNoEdge() {
		CallGraph cg = new CallGraph();
		EmptySiteEdges.addTo(cg, appClasses, new ArrayList<>());

		assertTrue(edgesAt(cg, paint).isEmpty());
	}

	@Test
	public void aBodyThatCannotBeRetrievedIsSkippedAndCounted() {
		// p.Act.broken is concrete with no body and no method source, so retrieving it throws.
		// The counters are visible only in the log line, which the test reads from stdout.
		CallGraph cg = new CallGraph();
		ByteArrayOutputStream log = new ByteArrayOutputStream();
		PrintStream stdout = System.out;
		List<Edge> added = new ArrayList<>();
		try {
			System.setOut(new PrintStream(log, true));
			EmptySiteEdges.addTo(cg, appClasses, added);
		} finally {
			System.setOut(stdout);
		}

		// this (1) + field (1) + special (1) + interface (2) + p.A.run, empty here (2): 7 edges.
		assertEquals(7, added.size());
		assertEquals(7, cg.size());
		assertTrue(log.toString(), log.toString().contains("[EmptySiteEdges] added 7 edges "
				+ "(instance-invoke sites: 6, empty sites: 6, bodies skipped: 1, largest fan-out: 2)"));
	}
}

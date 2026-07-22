/*
 * JimpleDefUtilsTest — synthetic Jimple bodies that exercise each branch
 * of the three primitives. We build minimal SootMethod/JimpleBody pairs
 * by hand instead of loading a real APK so the tests run in milliseconds
 * and have no environmental dependencies.
 *
 * Each scenario constructs a fresh Soot global state via {@code G.reset()}
 * because Soot keeps the Scene as singleton state; without the reset
 * neighbouring tests could leak SootClass/Body instances and confuse
 * SimpleLocalDefs.
 */
package presto.android.util;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import java.util.Collections;

import org.junit.Before;
import org.junit.Test;

import soot.G;
import soot.IntType;
import soot.Local;
import soot.RefType;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.Value;
import soot.VoidType;
import soot.jimple.GotoStmt;
import soot.jimple.IfStmt;
import soot.jimple.IntConstant;
import soot.jimple.Jimple;
import soot.jimple.JimpleBody;
import soot.jimple.Stmt;
import soot.jimple.StringConstant;
import soot.toolkits.graph.BriefUnitGraph;
import soot.toolkits.scalar.SimpleLocalDefs;

public class JimpleDefUtilsTest {

	private SootMethod method;
	private JimpleBody body;
	private Local xLocal;       // shared across buildIfElseTwoDefs scenarios
	private GotoStmt pendingGoto; // patched once the merge point is appended

	@Before
	public void setUp() {
		G.reset();
		SootClass sc = new SootClass("presto.android.util.JimpleDefUtilsTest$Fake");
		Scene.v().addClass(sc);
		method = new SootMethod("test", Collections.emptyList(), VoidType.v());
		sc.addMethod(method);
		body = Jimple.v().newBody(method);
		method.setActiveBody(body);
	}

	private SimpleLocalDefs defs() {
		return new SimpleLocalDefs(new BriefUnitGraph(body));
	}

	private Local addLocal(String name, soot.Type type) {
		Local l = Jimple.v().newLocal(name, type);
		body.getLocals().add(l);
		return l;
	}

	private Stmt addAssign(Local lhs, Value rhs) {
		Stmt s = Jimple.v().newAssignStmt(lhs, rhs);
		body.getUnits().add(s);
		return s;
	}

	private Stmt addReturn() {
		Stmt s = Jimple.v().newReturnVoidStmt();
		body.getUnits().add(s);
		return s;
	}

	/**
	 * Build an if/else producing two reaching defs of {@code xLocal} at the
	 * next unit appended after this call. Caller must subsequently call
	 * {@link #patchGotoToReturn(Stmt)} with the merge unit so the goto in
	 * the "then" branch lands correctly.
	 */
	private void buildIfElseTwoDefs(soot.Value rhsA, soot.Value rhsB) {
		xLocal = addLocal("x", IntType.v());
		Local c = addLocal("c", IntType.v());
		// c = 0
		addAssign(c, IntConstant.v(0));
		// assignB (target of the conditional) and assignA (fallthrough)
		Stmt assignB = Jimple.v().newAssignStmt(xLocal, rhsB);
		Stmt assignA = Jimple.v().newAssignStmt(xLocal, rhsA);
		// if (c == 0) goto assignB
		IfStmt ifStmt = Jimple.v().newIfStmt(
				Jimple.v().newEqExpr(c, IntConstant.v(0)), assignB);
		body.getUnits().add(ifStmt);
		body.getUnits().add(assignA);
		// goto <merge> — target patched in patchGotoToReturn()
		pendingGoto = Jimple.v().newGotoStmt(assignB); // placeholder target
		body.getUnits().add(pendingGoto);
		body.getUnits().add(assignB);
	}

	private void patchGotoToReturn(Stmt mergePoint) {
		pendingGoto.setTarget(mergePoint);
	}

	// ── definitionRhs ────────────────────────────────────────────────────

	@Test
	public void definitionRhs_singleAssign_returnsRhs() {
		Local x = addLocal("x", IntType.v());
		IntConstant rhs = IntConstant.v(42);
		addAssign(x, rhs);
		Stmt useSite = addReturn();

		assertSame(rhs, JimpleDefUtils.definitionRhs(x, useSite, defs()));
	}

	@Test
	public void definitionRhs_multipleDefs_returnsNull() {
		// Two reaching defs at useSite — primitives must err on the side of
		// "unresolved" so the consumer drops the entry rather than picking
		// an arbitrary def. We need real branching control flow (straight-
		// line "x=1; x=2" leaves only the latter alive after kill).
		buildIfElseTwoDefs(IntConstant.v(1), IntConstant.v(2));
		Stmt useSite = addReturn();
		patchGotoToReturn(useSite);

		assertNull(JimpleDefUtils.definitionRhs(xLocal, useSite, defs()));
	}

	@Test
	public void definitionRhs_noDef_returnsNull() {
		// Local is declared but never assigned before useSite.
		Local x = addLocal("x", IntType.v());
		Stmt useSite = addReturn();

		assertNull(JimpleDefUtils.definitionRhs(x, useSite, defs()));
	}

	// ── resolveInt ───────────────────────────────────────────────────────

	@Test
	public void resolveInt_directConstant() {
		Stmt useSite = addReturn();
		assertEquals(Integer.valueOf(7), JimpleDefUtils.resolveInt(IntConstant.v(7), useSite, defs()));
	}

	@Test
	public void resolveInt_localPointingToInt() {
		Local x = addLocal("x", IntType.v());
		addAssign(x, IntConstant.v(99));
		Stmt useSite = addReturn();

		assertEquals(Integer.valueOf(99), JimpleDefUtils.resolveInt(x, useSite, defs()));
	}

	@Test
	public void resolveInt_directNonInt_returnsNull() {
		Stmt useSite = addReturn();
		assertNull(JimpleDefUtils.resolveInt(StringConstant.v("not-an-int"), useSite, defs()));
	}

	@Test
	public void resolveInt_localPointingToNonInt_returnsNull() {
		// def-use walk reaches a StringConstant — resolveInt rejects it.
		Local x = addLocal("x", RefType.v("java.lang.String"));
		addAssign(x, StringConstant.v("hello"));
		Stmt useSite = addReturn();

		assertNull(JimpleDefUtils.resolveInt(x, useSite, defs()));
	}

	@Test
	public void resolveInt_localMultipleDefs_returnsNull() {
		// Underlying definitionRhs returns null → resolveInt propagates it.
		buildIfElseTwoDefs(IntConstant.v(1), IntConstant.v(2));
		Stmt useSite = addReturn();
		patchGotoToReturn(useSite);

		assertNull(JimpleDefUtils.resolveInt(xLocal, useSite, defs()));
	}

	// ── resolveStr ───────────────────────────────────────────────────────

	@Test
	public void resolveStr_directConstant() {
		Stmt useSite = addReturn();
		assertEquals("hi", JimpleDefUtils.resolveStr(StringConstant.v("hi"), useSite, defs()));
	}

	@Test
	public void resolveStr_localPointingToStr() {
		Local s = addLocal("s", RefType.v("java.lang.String"));
		addAssign(s, StringConstant.v("hello"));
		Stmt useSite = addReturn();

		assertEquals("hello", JimpleDefUtils.resolveStr(s, useSite, defs()));
	}

	@Test
	public void resolveStr_directNonStr_returnsNull() {
		Stmt useSite = addReturn();
		assertNull(JimpleDefUtils.resolveStr(IntConstant.v(123), useSite, defs()));
	}

	@Test
	public void resolveStr_localPointingToInt_returnsNull() {
		Local x = addLocal("x", IntType.v());
		addAssign(x, IntConstant.v(42));
		Stmt useSite = addReturn();

		assertNull(JimpleDefUtils.resolveStr(x, useSite, defs()));
	}

	@Test
	public void resolveStr_emptyString_isReturnedAsIs() {
		// Empty-string literal is a legitimate result; resolveStr must not
		// confuse it with "unresolved" (the consumer disambiguates via null).
		Stmt useSite = addReturn();
		assertEquals("", JimpleDefUtils.resolveStr(StringConstant.v(""), useSite, defs()));
	}

	// ── smoke: utility class shape ───────────────────────────────────────

	@Test
	public void utilityClass_hasOnlyPrivateCtor() {
		// Sanity check that nobody accidentally instantiates the utility.
		java.lang.reflect.Constructor<?>[] ctors = JimpleDefUtils.class.getDeclaredConstructors();
		assertEquals(1, ctors.length);
		assertTrue(java.lang.reflect.Modifier.isPrivate(ctors[0].getModifiers()));
	}
}

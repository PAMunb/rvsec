package presto.android.gui.clients;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import soot.ArrayType;
import soot.G;
import soot.IntType;
import soot.Local;
import soot.Modifier;
import soot.RefType;
import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.SootMethodRef;
import soot.Type;
import soot.Unit;
import soot.VoidType;
import soot.jimple.IntConstant;
import soot.jimple.Jimple;
import soot.jimple.JimpleBody;
import soot.jimple.NullConstant;
import soot.options.Options;

/**
 * {@link SpinnerItemExtractor} on activity bodies built in a Soot Scene bootstrapped from the JDK
 * on the test classpath (the idiom of {@code LambdaEdgesTest}). The Android classes the bodies
 * call are empty classes added to the Scene. Array ids: {@code 100} → TimeIntervals,
 * {@code 101} → Modes; {@code 999} is not an app array. The resource id map knows
 * ("array", "TimeIntervals") = 100 and ("id", "spin") = {@code SPINNER_ID}, for apps whose
 * {@code R} fields are not final and are read as static fields.
 */
public class SpinnerItemExtractorTest {

	private static final int SPINNER_ID = 200;

	private final Map<Integer, List<String>> arrays = new HashMap<>();
	private final Map<String, Integer> resourceIds = new HashMap<>();
	private SootClass arrayAdapter;
	private SootClass spinner;
	private SootClass resources;
	private SootClass activity;

	@Before
	public void buildScene() {
		G.reset();
		Options.v().set_allow_phantom_refs(true);
		Options.v().set_whole_program(false);
		Options.v().set_prepend_classpath(true);
		Options.v().set_soot_classpath(System.getProperty("java.class.path"));
		Scene.v().addBasicClass("java.lang.Object", SootClass.SIGNATURES);
		Scene.v().loadNecessaryClasses();

		newClass("android.content.Context");
		newClass("android.view.View");
		arrayAdapter = newClass("android.widget.ArrayAdapter");
		spinner = newClass("android.widget.Spinner");
		resources = newClass("android.content.res.Resources");
		activity = newClass("p.Act");

		arrays.put(100, Arrays.asList("30 Seconds", "60 Seconds"));
		arrays.put(101, Arrays.asList("Fast", "Slow"));
		resourceIds.put("array/TimeIntervals", 100);
		resourceIds.put("id/spin", SPINNER_ID);
	}

	@After
	public void tearDown() {
		G.reset();
	}

	@Test
	public void createFromResourceBindsTheArrayItems() {
		JimpleBody body = activityMethod("withCreateFromResource");
		Local adapter = local(body, "$a", RefType.v(arrayAdapter));
		body.getUnits().add(Jimple.v().newAssignStmt(adapter, Jimple.v().newStaticInvokeExpr(
				ref(arrayAdapter, "createFromResource", RefType.v(arrayAdapter), true,
						RefType.v("android.content.Context"), IntType.v(), IntType.v()),
				NullConstant.v(), IntConstant.v(100), IntConstant.v(7))));
		bindToSpinner(body, adapter);

		Map<Integer, List<String>> items = extract();

		assertEquals(Arrays.asList("30 Seconds", "60 Seconds"), items.get(SPINNER_ID));
	}

	@Test
	public void getStringArrayIntoTheConstructor() {
		JimpleBody body = activityMethod("withGetStringArray");
		Local res = local(body, "$res", RefType.v(resources));
		Local arr = local(body, "$arr", ArrayType.v(RefType.v("java.lang.String"), 1));
		Local adapter = local(body, "$a", RefType.v(arrayAdapter));
		body.getUnits().add(Jimple.v().newAssignStmt(res, NullConstant.v()));
		body.getUnits().add(Jimple.v().newAssignStmt(arr, Jimple.v().newVirtualInvokeExpr(res,
				ref(resources, "getStringArray", ArrayType.v(RefType.v("java.lang.String"), 1),
						false, IntType.v()),
				IntConstant.v(101))));
		body.getUnits().add(Jimple.v().newAssignStmt(adapter,
				Jimple.v().newNewExpr(RefType.v(arrayAdapter))));
		body.getUnits().add(Jimple.v().newInvokeStmt(Jimple.v().newSpecialInvokeExpr(adapter,
				ref(arrayAdapter, "<init>", VoidType.v(), false,
						RefType.v("android.content.Context"), IntType.v(),
						ArrayType.v(RefType.v("java.lang.Object"), 1)),
				NullConstant.v(), IntConstant.v(7), arr)));
		bindToSpinner(body, adapter);

		Map<Integer, List<String>> items = extract();

		assertEquals(Arrays.asList("Fast", "Slow"), items.get(SPINNER_ID));
	}

	@Test
	public void anIdThatIsNotAnAppArrayGivesNoItems() {
		JimpleBody body = activityMethod("withUnknownArray");
		Local adapter = local(body, "$a", RefType.v(arrayAdapter));
		body.getUnits().add(Jimple.v().newAssignStmt(adapter, Jimple.v().newStaticInvokeExpr(
				ref(arrayAdapter, "createFromResource", RefType.v(arrayAdapter), true,
						RefType.v("android.content.Context"), IntType.v(), IntType.v()),
				NullConstant.v(), IntConstant.v(999), IntConstant.v(7))));
		bindToSpinner(body, adapter);

		assertFalse(extract().containsKey(SPINNER_ID));
	}

	@Test
	public void resourceIdsReadFromNonFinalRFields() {
		SootClass rArray = newClass("p.R$array");
		SootClass rId = newClass("p.R$id");
		JimpleBody body = activityMethod("withRFields");
		Local arrayId = local(body, "$i0", IntType.v());
		Local viewId = local(body, "$i1", IntType.v());
		Local adapter = local(body, "$a", RefType.v(arrayAdapter));
		Local self = local(body, "$this", RefType.v(activity));
		Local view = local(body, "$v", RefType.v("android.view.View"));
		Local spin = local(body, "$s", RefType.v(spinner));
		body.getUnits().add(Jimple.v().newAssignStmt(arrayId, Jimple.v().newStaticFieldRef(
				Scene.v().makeFieldRef(rArray, "TimeIntervals", IntType.v(), true))));
		body.getUnits().add(Jimple.v().newAssignStmt(adapter, Jimple.v().newStaticInvokeExpr(
				ref(arrayAdapter, "createFromResource", RefType.v(arrayAdapter), true,
						RefType.v("android.content.Context"), IntType.v(), IntType.v()),
				NullConstant.v(), arrayId, IntConstant.v(7))));
		body.getUnits().add(Jimple.v().newAssignStmt(viewId, Jimple.v().newStaticFieldRef(
				Scene.v().makeFieldRef(rId, "spin", IntType.v(), true))));
		body.getUnits().add(Jimple.v().newAssignStmt(self, NullConstant.v()));
		body.getUnits().add(Jimple.v().newAssignStmt(view, Jimple.v().newVirtualInvokeExpr(self,
				ref(activity, "findViewById", RefType.v("android.view.View"), false, IntType.v()),
				viewId)));
		body.getUnits().add(Jimple.v().newAssignStmt(spin,
				Jimple.v().newCastExpr(view, RefType.v(spinner))));
		body.getUnits().add(Jimple.v().newInvokeStmt(Jimple.v().newVirtualInvokeExpr(spin,
				ref(spinner, "setAdapter", VoidType.v(), false,
						RefType.v("android.widget.SpinnerAdapter")),
				adapter)));
		body.getUnits().add(Jimple.v().newReturnVoidStmt());

		assertEquals(Arrays.asList("30 Seconds", "60 Seconds"), extract().get(SPINNER_ID));
	}

	/**
	 * The shape of {@code org.cry.otp.Home}: one register holds the spinner id for
	 * {@code findViewById} and is then overwritten by the array id for
	 * {@code createFromResource}, before {@code setAdapter}.
	 */
	@Test
	public void idRegisterReusedBeforeSetAdapter() {
		SootClass rArray = newClass("p.R$array");
		SootClass rId = newClass("p.R$id");
		JimpleBody body = activityMethod("withReusedRegister");
		Local i0 = local(body, "$i0", IntType.v());
		Local adapter = local(body, "$a", RefType.v(arrayAdapter));
		Local self = local(body, "$this", RefType.v(activity));
		Local view = local(body, "$v", RefType.v("android.view.View"));
		Local spin = local(body, "$s", RefType.v(spinner));
		body.getUnits().add(Jimple.v().newAssignStmt(self, NullConstant.v()));
		body.getUnits().add(Jimple.v().newAssignStmt(i0, Jimple.v().newStaticFieldRef(
				Scene.v().makeFieldRef(rId, "spin", IntType.v(), true))));
		body.getUnits().add(Jimple.v().newAssignStmt(view, Jimple.v().newVirtualInvokeExpr(self,
				ref(activity, "findViewById", RefType.v("android.view.View"), false, IntType.v()),
				i0)));
		body.getUnits().add(Jimple.v().newAssignStmt(spin,
				Jimple.v().newCastExpr(view, RefType.v(spinner))));
		body.getUnits().add(Jimple.v().newAssignStmt(i0, Jimple.v().newStaticFieldRef(
				Scene.v().makeFieldRef(rArray, "TimeIntervals", IntType.v(), true))));
		body.getUnits().add(Jimple.v().newAssignStmt(adapter, Jimple.v().newStaticInvokeExpr(
				ref(arrayAdapter, "createFromResource", RefType.v(arrayAdapter), true,
						RefType.v("android.content.Context"), IntType.v(), IntType.v()),
				NullConstant.v(), i0, IntConstant.v(7))));
		body.getUnits().add(Jimple.v().newInvokeStmt(Jimple.v().newVirtualInvokeExpr(spin,
				ref(spinner, "setAdapter", VoidType.v(), false,
						RefType.v("android.widget.SpinnerAdapter")),
				adapter)));
		body.getUnits().add(Jimple.v().newReturnVoidStmt());

		Map<Integer, List<String>> items = extract();

		assertEquals(Arrays.asList("30 Seconds", "60 Seconds"), items.get(SPINNER_ID));
		assertFalse(items.containsKey(100));
	}

	/**
	 * One adapter local reused for two adapters bound to two spinners: each spinner takes
	 * only the items of the adapter it was given.
	 */
	@Test
	public void adapterLocalReusedForTwoSpinners() {
		JimpleBody body = activityMethod("withTwoAdapters");
		Local adapter = local(body, "$a", RefType.v(arrayAdapter));
		Local self = local(body, "$this", RefType.v(activity));
		body.getUnits().add(Jimple.v().newAssignStmt(self, NullConstant.v()));
		int[][] pairs = {{100, SPINNER_ID}, {101, SPINNER_ID + 1}};
		for (int[] pair : pairs) {
			Local view = local(body, "$v" + pair[1], RefType.v("android.view.View"));
			Local spin = local(body, "$s" + pair[1], RefType.v(spinner));
			body.getUnits().add(Jimple.v().newAssignStmt(adapter, Jimple.v().newStaticInvokeExpr(
					ref(arrayAdapter, "createFromResource", RefType.v(arrayAdapter), true,
							RefType.v("android.content.Context"), IntType.v(), IntType.v()),
					NullConstant.v(), IntConstant.v(pair[0]), IntConstant.v(7))));
			body.getUnits().add(Jimple.v().newAssignStmt(view, Jimple.v().newVirtualInvokeExpr(self,
					ref(activity, "findViewById", RefType.v("android.view.View"), false,
							IntType.v()),
					IntConstant.v(pair[1]))));
			body.getUnits().add(Jimple.v().newAssignStmt(spin,
					Jimple.v().newCastExpr(view, RefType.v(spinner))));
			body.getUnits().add(Jimple.v().newInvokeStmt(Jimple.v().newVirtualInvokeExpr(spin,
					ref(spinner, "setAdapter", VoidType.v(), false,
							RefType.v("android.widget.SpinnerAdapter")),
					adapter)));
		}
		body.getUnits().add(Jimple.v().newReturnVoidStmt());

		Map<Integer, List<String>> items = extract();

		assertEquals(Arrays.asList("30 Seconds", "60 Seconds"), items.get(SPINNER_ID));
		assertEquals(Arrays.asList("Fast", "Slow"), items.get(SPINNER_ID + 1));
	}

	/**
	 * An adapter created in both branches of an if/else and bound once after the join:
	 * the spinner takes the items of both creations.
	 */
	@Test
	public void adapterCreatedInBothBranches() {
		JimpleBody body = activityMethod("withBranches");
		Local flag = local(body, "$c", IntType.v());
		Local adapter = local(body, "$a", RefType.v(arrayAdapter));
		Unit elseCreate = createFromResource(adapter, 101);
		Unit join = Jimple.v().newNopStmt();
		body.getUnits().add(Jimple.v().newAssignStmt(flag, IntConstant.v(0)));
		body.getUnits().add(Jimple.v().newIfStmt(
				Jimple.v().newEqExpr(flag, IntConstant.v(0)), elseCreate));
		body.getUnits().add(createFromResource(adapter, 100));
		body.getUnits().add(Jimple.v().newGotoStmt(join));
		body.getUnits().add(elseCreate);
		body.getUnits().add(join);
		bindToSpinner(body, adapter);

		Map<Integer, List<String>> items = extract();

		assertEquals(new HashSet<>(Arrays.asList("30 Seconds", "60 Seconds", "Fast", "Slow")),
				new HashSet<>(items.get(SPINNER_ID)));
		assertEquals(4, items.get(SPINNER_ID).size());
	}

	/** {@code adapter = ArrayAdapter.createFromResource(null, arrayId, 7)}. */
	private Unit createFromResource(Local adapter, int arrayId) {
		return Jimple.v().newAssignStmt(adapter, Jimple.v().newStaticInvokeExpr(
				ref(arrayAdapter, "createFromResource", RefType.v(arrayAdapter), true,
						RefType.v("android.content.Context"), IntType.v(), IntType.v()),
				NullConstant.v(), IntConstant.v(arrayId), IntConstant.v(7)));
	}

	private Map<Integer, List<String>> extract() {
		return new SpinnerItemExtractor(arrays::get,
				(type, name) -> resourceIds.get(type + "/" + name)).extractItems(activity);
	}

	/** {@code $v = findViewById(SPINNER_ID); $s = (Spinner) $v; $s.setAdapter(adapter); return}. */
	private void bindToSpinner(JimpleBody body, Local adapter) {
		Local self = local(body, "$this", RefType.v(activity));
		Local view = local(body, "$v", RefType.v("android.view.View"));
		Local spin = local(body, "$s", RefType.v(spinner));
		body.getUnits().add(Jimple.v().newAssignStmt(self, NullConstant.v()));
		body.getUnits().add(Jimple.v().newAssignStmt(view, Jimple.v().newVirtualInvokeExpr(self,
				ref(activity, "findViewById", RefType.v("android.view.View"), false, IntType.v()),
				IntConstant.v(SPINNER_ID))));
		body.getUnits().add(Jimple.v().newAssignStmt(spin,
				Jimple.v().newCastExpr(view, RefType.v(spinner))));
		body.getUnits().add(Jimple.v().newInvokeStmt(Jimple.v().newVirtualInvokeExpr(spin,
				ref(spinner, "setAdapter", VoidType.v(), false,
						RefType.v("android.widget.SpinnerAdapter")),
				adapter)));
		body.getUnits().add(Jimple.v().newReturnVoidStmt());
	}

	private JimpleBody activityMethod(String name) {
		SootMethod m = new SootMethod(name, Collections.<Type>emptyList(), VoidType.v(),
				Modifier.PUBLIC);
		activity.addMethod(m);
		JimpleBody body = Jimple.v().newBody(m);
		m.setActiveBody(body);
		return body;
	}

	private static Local local(JimpleBody body, String name, Type type) {
		Local l = Jimple.v().newLocal(name, type);
		body.getLocals().add(l);
		return l;
	}

	private static SootMethodRef ref(SootClass owner, String name, Type ret, boolean isStatic,
			Type... params) {
		return Scene.v().makeMethodRef(owner, name, Arrays.asList(params), ret, isStatic);
	}

	private static SootClass newClass(String name) {
		SootClass c = new SootClass(name, Modifier.PUBLIC);
		c.setSuperclass(Scene.v().getSootClass("java.lang.Object"));
		c.setResolvingLevel(SootClass.BODIES);
		Scene.v().addClass(c);
		return c;
	}
}

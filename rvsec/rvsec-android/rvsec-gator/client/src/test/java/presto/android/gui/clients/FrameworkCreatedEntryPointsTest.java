package presto.android.gui.clients;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
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
import soot.VoidType;

/**
 * Entry points of the components the framework or a library creates (INV-ANA-95):
 * the manifest's Application subclass, and the Fragment, ListenableWorker and RecyclerView
 * Adapter/ViewHolder subclasses among the app classes. A ViewModel subclass is not one.
 *
 * <p>The Scene is reset per test, as in {@code CallSiteMatchPolicyTest}, but holds synthetic
 * classes rather than JDK ones: the Android and androidx base classes are not on the test
 * classpath, and the rule matches them by name over the superclass chain, so a class with the
 * base's name is all a test needs. {@code getEntryPoints} itself also reads the activities of a
 * {@code GUIAnalysisOutput} and the manifest through the {@code XMLParser} singleton, so the
 * tests call the two helpers it adds to its result.
 */
public class FrameworkCreatedEntryPointsTest {

	private final Map<SootClass, List<SootMethod>> appClasses = new LinkedHashMap<>();

	@Before
	public void resetScene() {
		G.reset();
	}

	@After
	public void tearDown() {
		G.reset();
	}

	// ------------------------------------------------------------------------- Application

	@Test
	public void theManifestApplicationGivesItsLifecycleAndPublicProtectedMethods() {
		SootClass app = appClass("com.example.App", sceneClass("android.app.Application"));
		SootMethod onCreate = method(app, "onCreate", Modifier.PUBLIC);
		SootMethod attachBaseContext = method(app, "attachBaseContext", Modifier.PROTECTED);
		SootMethod onTrimMemory = method(app, "onTrimMemory", Modifier.PRIVATE);
		SootMethod getDatabase = method(app, "getDatabase", Modifier.PUBLIC);
		method(app, "initDatabaseEncryption", Modifier.PRIVATE);

		assertEquals(setOf(onCreate, attachBaseContext, onTrimMemory, getDatabase),
				RvsecAnalysisClient.applicationEntryPoints("com.example.App"));
	}

	@Test
	public void noApplicationNameGivesNoEntryPoint() {
		assertTrue(RvsecAnalysisClient.applicationEntryPoints(null).isEmpty());
	}

	@Test
	public void anApplicationAbsentFromTheSceneGivesNoEntryPoint() {
		assertTrue(RvsecAnalysisClient.applicationEntryPoints("com.example.Missing").isEmpty());
	}

	// ---------------------------------------------------------------------------- Fragment

	@Test
	public void aFragmentSubclassGivesItsPublicAndProtectedMethods() {
		SootClass base = appClass("com.example.BaseFragment", sceneClass("androidx.fragment.app.Fragment"));
		SootClass fragment = appClass("com.example.HomeFragment", base);
		SootMethod onCreateView = method(fragment, "onCreateView", Modifier.PUBLIC);
		SootMethod onResume = method(fragment, "onResume", Modifier.PROTECTED);
		method(fragment, "render", Modifier.PRIVATE);
		SootMethod baseOnViewCreated = method(base, "onViewCreated", Modifier.PUBLIC);

		assertEquals(setOf(onCreateView, onResume, baseOnViewCreated),
				RvsecAnalysisClient.frameworkCreatedEntryPoints(appClasses));
	}

	@Test
	public void everyFragmentBaseIsMatched() {
		Set<SootMethod> expected = new HashSet<>();
		int i = 0;
		for (String base : new String[] { "android.app.Fragment",
				"android.support.v4.app.Fragment", "androidx.fragment.app.Fragment" }) {
			SootClass fragment = appClass("com.example.F" + i++, sceneClass(base));
			expected.add(method(fragment, "onStart", Modifier.PUBLIC));
		}

		assertEquals(expected, RvsecAnalysisClient.frameworkCreatedEntryPoints(appClasses));
	}

	// ------------------------------------------------------------------------------ Worker

	@Test
	public void aWorkerGivesOnlyDoWorkAndStartWork() {
		SootClass coroutineWorker = sceneClass("androidx.work.CoroutineWorker",
				sceneClass("androidx.work.ListenableWorker"));
		SootClass worker = appClass("com.example.SyncWorker", coroutineWorker);
		SootMethod doWork = method(worker, "doWork", Modifier.PUBLIC);
		SootMethod startWork = method(worker, "startWork", Modifier.PUBLIC);
		method(worker, "buildRequest", Modifier.PUBLIC);
		method(worker, "onStopped", Modifier.PROTECTED);

		assertEquals(setOf(doWork, startWork),
				RvsecAnalysisClient.frameworkCreatedEntryPoints(appClasses));
	}

	// ----------------------------------------------------------------- Adapter, ViewHolder

	@Test
	public void anAdapterAndAViewHolderGiveTheirPublicMethods() {
		SootClass adapter = appClass("com.example.EntryAdapter",
				sceneClass("androidx.recyclerview.widget.RecyclerView$Adapter"));
		SootMethod onBindViewHolder = method(adapter, "onBindViewHolder", Modifier.PUBLIC);
		method(adapter, "notifyChanged", Modifier.PROTECTED);
		SootClass holder = appClass("com.example.EntryHolder",
				sceneClass("android.support.v7.widget.RecyclerView$ViewHolder"));
		SootMethod getOtp = method(holder, "getOtp", Modifier.PUBLIC);
		method(holder, "format", Modifier.PRIVATE);

		assertEquals(setOf(onBindViewHolder, getOtp),
				RvsecAnalysisClient.frameworkCreatedEntryPoints(appClasses));
	}

	@Test
	public void everyRecyclerViewBaseIsMatched() {
		Set<SootMethod> expected = new HashSet<>();
		int i = 0;
		for (String base : new String[] {
				"androidx.recyclerview.widget.RecyclerView$Adapter",
				"androidx.recyclerview.widget.RecyclerView$ViewHolder",
				"android.support.v7.widget.RecyclerView$Adapter",
				"android.support.v7.widget.RecyclerView$ViewHolder" }) {
			SootClass cls = appClass("com.example.R" + i++, sceneClass(base));
			expected.add(method(cls, "bind", Modifier.PUBLIC));
		}

		assertEquals(expected, RvsecAnalysisClient.frameworkCreatedEntryPoints(appClasses));
	}

	// ---------------------------------------------------------------------- not taken

	@Test
	public void aViewModelIsNotAnEntryPoint() {
		SootClass viewModel = appClass("com.example.HomeViewModel",
				sceneClass("androidx.lifecycle.ViewModel"));
		method(viewModel, "load", Modifier.PUBLIC);
		method(viewModel, "onCleared", Modifier.PROTECTED);

		assertTrue(RvsecAnalysisClient.frameworkCreatedEntryPoints(appClasses).isEmpty());
	}

	@Test
	public void aFrameworkSubclassOutsideTheAppClassesIsNotTaken() {
		SootClass libFragment = sceneClass("org.lib.LibFragment",
				sceneClass("androidx.fragment.app.Fragment"));
		method(libFragment, "onStart", Modifier.PUBLIC);

		assertTrue(RvsecAnalysisClient.frameworkCreatedEntryPoints(appClasses).isEmpty());
	}

	// ----------------------------------------------------------------------------- helpers

	private static SootClass sceneClass(String name) {
		SootClass cls = new SootClass(name, Modifier.PUBLIC);
		Scene.v().addClass(cls);
		return cls;
	}

	private static SootClass sceneClass(String name, SootClass superclass) {
		SootClass cls = sceneClass(name);
		cls.setSuperclass(superclass);
		return cls;
	}

	/** A Scene class that is also in the client's app-class map. */
	private SootClass appClass(String name, SootClass superclass) {
		SootClass cls = sceneClass(name, superclass);
		appClasses.put(cls, new ArrayList<>());
		return cls;
	}

	private SootMethod method(SootClass cls, String name, int modifiers) {
		SootMethod m = new SootMethod(name, Collections.emptyList(), VoidType.v(), modifiers);
		cls.addMethod(m);
		List<SootMethod> listed = appClasses.get(cls);
		if (listed != null) {
			listed.add(m);
		}
		return m;
	}

	private static Set<SootMethod> setOf(SootMethod... methods) {
		Set<SootMethod> result = new HashSet<>();
		Collections.addAll(result, methods);
		return result;
	}
}

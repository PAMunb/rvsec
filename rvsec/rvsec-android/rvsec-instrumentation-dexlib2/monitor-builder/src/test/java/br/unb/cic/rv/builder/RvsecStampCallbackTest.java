package br.unb.cic.rv.builder;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIf;
import org.junit.jupiter.api.io.TempDir;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * App-callback resolution of the stamp helper ({@code mop.RvsecStamp.callback}) on the paths
 * that call no {@code View} method: a preference row's dispatcher ({@code Preference$1}), a
 * dialog button's ({@code AlertController$1}), a menu item's own click listener, the menu
 * providers of a {@code MenuHostHelper}, an app-bound and an unresolved listener, and a failed
 * read, and the activity's options menu from the activity on. A view or an activity there is
 * only a placeholder, allocated without running the {@code android.jar}
 * stub constructor, which throws on the JVM. The parent walk (navigation, toolbar), the way
 * from a view to its activity ({@code View.getContext()}) and the stamp delegate
 * (its node and its log line) call stub methods and are checked on the device.
 *
 * <p>Compiled as {@link RvsecStampComposeTest} does: the helper source with the fixtures of
 * {@code stamp-fixtures/} against {@code android.jar}.
 */
@EnabledIf("canCompile")
class RvsecStampCallbackTest {

    @TempDir
    static Path dir;

    private static URLClassLoader loader;
    private static Method callback;
    private static Method firstAppProvider;
    private static Method readTyped;
    private static Method optionsMenu;

    private static Path androidJar() {
        String home = System.getenv("ANDROID_HOME");
        if (home == null || home.isEmpty()) return null;
        Path jar = Path.of(home, "platforms", "android-30", "android.jar");
        return Files.isRegularFile(jar) ? jar : null;
    }

    static boolean canCompile() {
        return androidJar() != null
                && Files.isExecutable(Path.of(System.getProperty("java.home"), "bin", "javac"));
    }

    @BeforeAll
    static void compileHelperWithFixtures() throws Exception {
        Path helper = StampSourceEmitter.emit(dir.resolve("src"));
        URL fixturesUrl = RvsecStampCallbackTest.class.getResource("/stamp-fixtures");
        assertNotNull(fixturesUrl, "stamp-fixtures resource directory");
        List<String> sources;
        try (Stream<Path> walk = Files.walk(Path.of(fixturesUrl.toURI()))) {
            sources = walk.filter(p -> p.toString().endsWith(".java"))
                    .map(Path::toString).sorted().collect(Collectors.toList());
        }
        Path out = Files.createDirectories(dir.resolve("out"));
        List<String> cmd = new ArrayList<>(List.of(
                Path.of(System.getProperty("java.home"), "bin", "javac").toString(),
                "-source", "1.8", "-target", "1.8", "-Xlint:-options",
                "-d", out.toString(), "-classpath", androidJar().toString(), helper.toString()));
        cmd.addAll(sources);
        Process p = new ProcessBuilder(cmd).redirectErrorStream(true).start();
        String output = new String(p.getInputStream().readAllBytes());
        assertEquals(0, p.waitFor(), output);
        Files.delete(out.resolve("com/example/app/AbsentAtRunTime.class"));

        loader = new URLClassLoader(
                new URL[] {out.toUri().toURL(), androidJar().toUri().toURL()},
                ClassLoader.getPlatformClassLoader());
        Class<?> stamp = loader.loadClass("mop.RvsecStamp");
        Class<?> view = loader.loadClass("android.view.View");
        callback = stamp.getDeclaredMethod("callback", view, Object.class);
        firstAppProvider = stamp.getDeclaredMethod("firstAppProvider", Object.class);
        readTyped = stamp.getDeclaredMethod("readTyped", Object.class, String.class);
        callback.setAccessible(true);
        firstAppProvider.setAccessible(true);
        readTyped.setAccessible(true);
        optionsMenu = stamp.getDeclaredMethod("optionsMenu", Object.class);
        optionsMenu.setAccessible(true);
    }

    private static Object make(String className) throws Exception {
        return loader.loadClass(className).getDeclaredConstructor().newInstance();
    }

    /** An instance of {@code className} allocated without running a constructor. */
    private static Object allocate(String className) throws Exception {
        Class<?> unsafeClass = Class.forName("sun.misc.Unsafe");
        Field theUnsafe = unsafeClass.getDeclaredField("theUnsafe");
        theUnsafe.setAccessible(true);
        return unsafeClass.getMethod("allocateInstance", Class.class)
                .invoke(theUnsafe.get(null), loader.loadClass(className));
    }

    private static Object set(Object target, String field, Object value) throws Exception {
        for (Class<?> c = target.getClass(); c != null; c = c.getSuperclass()) {
            for (Field f : c.getDeclaredFields()) {
                if (f.getName().equals(field)) {
                    f.setAccessible(true);
                    f.set(target, value);
                    return target;
                }
            }
        }
        throw new NoSuchFieldException(target.getClass().getName() + "." + field);
    }

    private static Object get(Object target, String field) throws Exception {
        Field f = target.getClass().getDeclaredField(field);
        f.setAccessible(true);
        return f.get(target);
    }

    private static Object invoke(Method m, Object... args) throws Exception {
        try {
            return m.invoke(null, args);
        } catch (InvocationTargetException ex) {
            Throwable cause = ex.getCause();
            if (cause instanceof Error) throw (Error) cause;
            throw (Exception) cause;
        }
    }

    /** The callback behind a preference row whose dispatcher holds {@code preference}. */
    private static String row(Object preference) throws Exception {
        Object dispatcher = set(make("androidx.preference.Preference$1"), "this$0", preference);
        return (String) invoke(callback, null, dispatcher);
    }

    @Test
    void preferenceClickListenerWins() throws Exception {
        Object pref = make("androidx.preference.Preference");
        set(pref, "mOnClickListener", make("com.example.app.PrefClickListener"));
        set(pref, "mOnChangeListener", make("com.example.app.PrefChangeListener"));
        assertEquals("com.example.app.PrefClickListener", row(pref));
    }

    @Test
    void preferenceChangeListenerWithoutClickListener() throws Exception {
        Object pref = make("androidx.preference.Preference");
        set(pref, "mOnChangeListener", make("com.example.app.PrefChangeListener"));
        assertEquals("com.example.app.PrefChangeListener", row(pref));
    }

    @Test
    void preferenceFallsBackToTreeClickFragment() throws Exception {
        Object manager = set(make("androidx.preference.PreferenceManager"),
                "mOnPreferenceTreeClickListener", make("com.example.app.SettingsFragment"));
        Object pref = set(make("androidx.preference.Preference"), "mPreferenceManager", manager);
        assertEquals("com.example.app.SettingsFragment", row(pref));
    }

    @Test
    void preferenceLibraryCandidateDoesNotCount() throws Exception {
        Object pref = make("androidx.preference.Preference");
        set(pref, "mOnClickListener", make("androidx.core.view.LibraryMenuProvider"));
        set(pref, "mOnChangeListener", make("com.example.app.PrefChangeListener"));
        assertEquals("com.example.app.PrefChangeListener", row(pref));
    }

    @Test
    void preferenceReadFailureReachesTheCaller() throws Exception {
        // The stamp delegate catches it and keeps the dispatcher's class; nothing partial
        // is returned from here.
        assertThrows(NoClassDefFoundError.class,
                () -> row(make("com.example.app.UnreadablePreference")));
    }

    @Test
    void dialogButtonNamesItsMessageListener() throws Exception {
        Object positive = allocate("android.widget.Button");
        Object negative = allocate("android.widget.Button");
        Object message = allocate("android.os.Message");
        set(message, "obj", make("com.example.app.DialogListener"));
        Object controller = make("androidx.appcompat.app.AlertController");
        set(controller, "mButtonPositive", positive);
        set(controller, "mButtonPositiveMessage", message);
        set(controller, "mButtonNegative", negative);
        Object dispatcher = set(make("androidx.appcompat.app.AlertController$1"),
                "this$0", controller);
        assertEquals("com.example.app.DialogListener", invoke(callback, positive, dispatcher));
        assertNull(invoke(callback, negative, dispatcher));
        assertNull(invoke(callback, allocate("android.widget.Button"), dispatcher));
    }

    @Test
    void menuItemOwnClickListenerWins() throws Exception {
        Object item = set(make("androidx.appcompat.view.menu.MenuItemImpl"),
                "mClickListener", make("com.example.app.MenuClickListener"));
        Object view = set(allocate("androidx.appcompat.view.menu.ActionMenuItemView"),
                "mItemData", item);
        assertEquals("com.example.app.MenuClickListener", invoke(callback, view, view));
    }

    @Test
    void unresolvedLibraryListenerResolvesNothing() throws Exception {
        Object listener = set(make("androidx.appcompat.widget.SearchView$5"),
                "this$0", make("androidx.appcompat.widget.SearchView"));
        assertNull(invoke(callback, allocate("android.view.View"), listener));
    }

    @Test
    void treeClickNamesTheDeclaringClass() throws Exception {
        Object manager = set(make("androidx.preference.PreferenceManager"),
                "mOnPreferenceTreeClickListener", make("com.example.app.SettingsSubFragment"));
        Object pref = set(make("androidx.preference.Preference"), "mPreferenceManager", manager);
        assertEquals("com.example.app.SettingsFragment", row(pref));
    }

    @Test
    void treeClickWithoutTheCallbackResolvesNothing() throws Exception {
        Object manager = set(make("androidx.preference.PreferenceManager"),
                "mOnPreferenceTreeClickListener", make("com.example.app.PlainSettingsFragment"));
        Object pref = set(make("androidx.preference.Preference"), "mPreferenceManager", manager);
        assertNull(row(pref));
    }

    @Test
    void optionsMenuNamesTheBaseClassThatDeclaresIt() throws Exception {
        assertEquals("com.example.app.BaseMenuActivity",
                invoke(optionsMenu, allocate("com.example.app.ContactsActivity")));
        assertEquals("com.example.app.BaseMenuActivity",
                invoke(optionsMenu, allocate("com.example.app.BaseMenuActivity")));
    }

    @Test
    void optionsMenuIgnoresOtherParameterLists() throws Exception {
        Object activity = allocate("com.example.app.IntMenuActivity");
        assertNull(invoke(optionsMenu, activity));
        Object helper = make("androidx.core.view.MenuHostHelper");
        set(activity, "menuHostHelper", helper);
        @SuppressWarnings("unchecked")
        List<Object> providers = (List<Object>) get(helper, "mMenuProviders");
        providers.add(make("com.example.app.BookmarksMenuProvider"));
        assertEquals("com.example.app.BookmarksMenuProvider", invoke(optionsMenu, activity));
    }

    @Test
    void preferenceWithNothingResolvesNothing() throws Exception {
        assertNull(row(make("androidx.preference.Preference")));
    }

    @Test
    void appListenerIsNotLookedBehind() throws Exception {
        assertNull(invoke(callback, null, make("com.example.app.PrefClickListener")));
    }

    @Test
    void firstProviderOfAppCodeSkipsLibraryProviders() throws Exception {
        Object host = make("com.example.app.MenuHostActivity");
        Object helper = invoke(readTyped, host, "androidx.core.view.MenuHostHelper");
        assertNotNull(helper);
        @SuppressWarnings("unchecked")
        List<Object> providers = (List<Object>) get(helper, "mMenuProviders");
        providers.add(make("androidx.core.view.LibraryMenuProvider"));
        providers.add(make("com.example.app.BookmarksMenuProvider"));
        assertEquals("com.example.app.BookmarksMenuProvider", invoke(firstAppProvider, helper));
    }

    @Test
    void noProviderResolvesNothing() throws Exception {
        assertNull(invoke(firstAppProvider, make("androidx.core.view.MenuHostHelper")));
        assertNull(invoke(firstAppProvider, (Object) null));
    }
}

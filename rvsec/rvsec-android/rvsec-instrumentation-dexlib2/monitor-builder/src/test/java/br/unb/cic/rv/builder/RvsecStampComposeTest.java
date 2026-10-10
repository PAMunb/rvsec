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

/**
 * Compose handler resolution of the stamp helper ({@code mop.RvsecStamp.composeHandler}):
 * the node step ({@code this$0}, or {@code f$0} when it is a foundation clickable node) and
 * the Material step (one structural unwrap of an {@code androidx.compose.material*} wrapper).
 *
 * <p>The helper source, as {@link StampSourceEmitter#emit} writes it, is compiled with the
 * fixture classes of {@code stamp-fixtures/} against {@code android.jar} in one {@code javac}
 * call. The fixtures carry the class and field names of the Compose libraries, so the helper
 * meets on the JVM the shapes it reads by name on a device. {@code composeHandler} touches no
 * Android API, and loading {@code mop.RvsecStamp} runs only collection initialisers, so the
 * {@code android.jar} stubs are never invoked.
 */
@EnabledIf("canCompile")
class RvsecStampComposeTest {

    private static final String ON_CLICK = "onClick";
    private static final String ON_LONG_CLICK = "onLongClick";

    @TempDir
    static Path dir;

    private static URLClassLoader loader;
    private static Method composeHandler;

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
        URL fixturesUrl = RvsecStampComposeTest.class.getResource("/stamp-fixtures");
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

        loader = new URLClassLoader(
                new URL[] {out.toUri().toURL(), androidJar().toUri().toURL()},
                ClassLoader.getPlatformClassLoader());
        composeHandler = loader.loadClass("mop.RvsecStamp")
                .getDeclaredMethod("composeHandler", Object.class, Object.class, String.class);
        composeHandler.setAccessible(true);
    }

    // ---- fixture plumbing ----

    private static Object make(String className) throws Exception {
        return loader.loadClass(className).getDeclaredConstructor().newInstance();
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

    private static Object key(String name) throws Exception {
        return loader.loadClass("androidx.compose.ui.semantics.SemanticsPropertyKey")
                .getConstructor(String.class).newInstance(name);
    }

    /** A configuration holding, under {@code key}, an action whose lambda is {@code fn}. */
    private static Object config(Object key, Object fn) throws Exception {
        Object config = make("androidx.compose.ui.semantics.SemanticsConfiguration");
        Object action = loader.loadClass("androidx.compose.ui.semantics.AccessibilityAction")
                .getConstructor(Object.class).newInstance(fn);
        config.getClass().getMethod("set", key.getClass(), Object.class).invoke(config, key, action);
        return config;
    }

    private static String resolve(Object config, Object key, String field) throws Exception {
        try {
            return (String) composeHandler.invoke(null, config, key, field);
        } catch (InvocationTargetException ex) {
            Throwable cause = ex.getCause();
            if (cause instanceof Error) throw (Error) cause;
            throw (Exception) cause;
        }
    }

    /** The handler resolved for an {@code OnClick} action whose lambda is {@code fn}. */
    private static String click(Object fn) throws Exception {
        Object key = key("OnClick");
        return resolve(config(key, fn), key, ON_CLICK);
    }

    /** foundation 1.9 shape: a D8 action lambda capturing {@code node} in {@code f$0}. */
    private static Object d8Action(Object node) throws Exception {
        return set(make("androidx.compose.foundation.AbstractClickableNode$$ExternalSyntheticLambda1"),
                "f$0", node);
    }

    /** foundation ≤ 1.8 shape: a kotlinc action lambda whose outer instance is a semantics node with {@code onClick}. */
    private static Object kotlincAction(Object onClick) throws Exception {
        Object node = set(make("androidx.compose.foundation.ClickableSemanticsNode"), ON_CLICK, onClick);
        return set(make("androidx.compose.foundation.ClickableSemanticsNode$applySemantics$1"),
                "this$0", node);
    }

    // ---- node step ----

    @Test
    void thisZeroOwnerIsReadAsBefore() throws Exception {
        // ClickableSemanticsNode is not an AbstractClickableNode: this$0 is followed unchecked.
        assertEquals("com.example.app.MainKt$Screen$1",
                click(kotlincAction(make("com.example.app.MainKt$Screen$1"))));
    }

    @Test
    void fZeroClickableNodeIsUnwrapped() throws Exception {
        Object node = set(make("androidx.compose.foundation.ClickableNode"), ON_CLICK,
                make("com.luk.saucenao.MainScreenKt$$ExternalSyntheticLambda43"));
        assertEquals("com.luk.saucenao.MainScreenKt$$ExternalSyntheticLambda43", click(d8Action(node)));
    }

    @Test
    void fZeroToggleableReadsOnValueChange() throws Exception {
        Object node = make("androidx.compose.foundation.selection.ToggleableNode");
        set(node, ON_CLICK, set(make("androidx.compose.foundation.selection.ToggleableNode$$ExternalSyntheticLambda0"),
                "f$0", node));
        set(node, "onValueChange", make("com.example.app.SettingsKt$$ExternalSyntheticLambda9"));
        assertEquals("com.example.app.SettingsKt$$ExternalSyntheticLambda9", click(d8Action(node)));
    }

    @Test
    void fZeroToggleableWithNullOnValueChangeReadsOnClick() throws Exception {
        Object node = set(make("androidx.compose.foundation.selection.ToggleableNode"), ON_CLICK,
                make("com.example.app.ListKt$$ExternalSyntheticLambda2"));
        assertEquals("com.example.app.ListKt$$ExternalSyntheticLambda2", click(d8Action(node)));
    }

    @Test
    void fZeroNodeWithNullOnClickFallsBackToActionLambda() throws Exception {
        Object node = make("androidx.compose.foundation.ClickableNode");
        assertEquals("androidx.compose.foundation.AbstractClickableNode$$ExternalSyntheticLambda1",
                click(d8Action(node)));
    }

    @Test
    void fZeroCombinedLongClick() throws Exception {
        Object node = make("androidx.compose.foundation.CombinedClickableNode");
        set(node, ON_CLICK, make("com.example.app.ListKt$$ExternalSyntheticLambda2"));
        set(node, ON_LONG_CLICK, make("com.example.app.ListKt$$ExternalSyntheticLambda3"));
        Object fn = d8Action(node);
        Object onClick = key("OnClick");
        Object onLongClick = key("OnLongClick");
        assertEquals("com.example.app.ListKt$$ExternalSyntheticLambda3",
                resolve(config(onLongClick, fn), onLongClick, ON_LONG_CLICK));
        assertEquals("com.example.app.ListKt$$ExternalSyntheticLambda2",
                resolve(config(onClick, fn), onClick, ON_CLICK));
    }

    @Test
    void fZeroOtherObjectIsNotRead() throws Exception {
        Object state = set(make("com.example.RowState"), ON_CLICK,
                make("com.example.ScreenKt$$ExternalSyntheticLambda1"));
        Object fn = set(make("com.example.ScreenKt$$ExternalSyntheticLambda0"), "f$0", state);
        assertEquals("com.example.ScreenKt$$ExternalSyntheticLambda0", click(fn));
    }

    @Test
    void absentActionResolvesToNull() throws Exception {
        Object onClick = key("OnClick");
        Object onLongClick = key("OnLongClick");
        Object config = config(onClick, make("com.example.app.MainKt$Screen$1"));
        assertNull(resolve(config, onLongClick, ON_LONG_CLICK));
        assertNull(resolve(config, null, ON_LONG_CLICK));
        assertNull(resolve(config(onClick, null), onClick, ON_CLICK));
    }

    // ---- Material step ----

    @Test
    void checkboxD8FormIsUnwrapped() throws Exception {
        Object wrapper = make("androidx.compose.material3.CheckboxKt$$ExternalSyntheticLambda6");
        set(wrapper, "f$0", make("com.example.SettingsKt$$ExternalSyntheticLambda7"));
        set(wrapper, "f$1", true);
        Object node = set(make("androidx.compose.foundation.ClickableNode"), ON_CLICK, wrapper);
        assertEquals("com.example.SettingsKt$$ExternalSyntheticLambda7", click(d8Action(node)));
    }

    @Test
    void checkboxKotlincFormIsUnwrapped() throws Exception {
        Object wrapper = make("androidx.compose.material3.CheckboxKt$Checkbox$1$1");
        set(wrapper, "$checked", false);
        set(wrapper, "$onCheckedChange", make("com.example.SettingsKt$Row$1$1"));
        assertEquals("com.example.SettingsKt$Row$1$1", click(kotlincAction(wrapper)));
    }

    @Test
    void wrapperOfLibraryFunctionIsKept() throws Exception {
        Object wrapper = set(make("androidx.compose.material3.DatePickerKt$$ExternalSyntheticLambda12"),
                "f$0", make("androidx.compose.material3.DatePickerKt$$ExternalSyntheticLambda3"));
        assertEquals("androidx.compose.material3.DatePickerKt$$ExternalSyntheticLambda12",
                click(kotlincAction(wrapper)));
    }

    @Test
    void wrapperWithTwoFunctionsIsKept() throws Exception {
        Object wrapper = make("androidx.compose.material3.SomeKt$$ExternalSyntheticLambda2");
        set(wrapper, "f$0", make("com.example.app.ListKt$$ExternalSyntheticLambda2"));
        set(wrapper, "f$1", make("com.example.app.ListKt$$ExternalSyntheticLambda3"));
        assertEquals("androidx.compose.material3.SomeKt$$ExternalSyntheticLambda2",
                click(kotlincAction(wrapper)));
    }

    @Test
    void nonMaterialHandlerIsNotUnwrapped() throws Exception {
        // One function capture holding an app lambda: only the package keeps it from being followed.
        Object fn = set(make(
                "androidx.compose.foundation.text.input.internal.CoreTextFieldSemanticsModifierNode$$ExternalSyntheticLambda12"),
                "f$0", make("com.example.app.MainKt$Screen$1"));
        assertEquals(
                "androidx.compose.foundation.text.input.internal.CoreTextFieldSemanticsModifierNode$$ExternalSyntheticLambda12",
                click(fn));
    }

    @Test
    void nullFunctionIsKept() throws Exception {
        Object wrapper = make("androidx.compose.material3.CheckboxKt$$ExternalSyntheticLambda6");
        assertEquals("androidx.compose.material3.CheckboxKt$$ExternalSyntheticLambda6",
                click(kotlincAction(wrapper)));
    }

    @Test
    void materialActionLambdaFallbackIsUnwrapped() throws Exception {
        // No this$0 and no clickable node in f$0: the handler is the action lambda itself,
        // and the Material step applies to it.
        Object fn = set(make("androidx.compose.material3.ModalBottomSheetKt$$ExternalSyntheticLambda4"),
                "f$0", make("com.example.app.SheetKt$$ExternalSyntheticLambda1"));
        assertEquals("com.example.app.SheetKt$$ExternalSyntheticLambda1", click(fn));
    }
}

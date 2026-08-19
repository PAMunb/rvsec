package com.runtimeverification.rvmonitor.java.rvj.output.monitor;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.PrintWriter;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.Arrays;
import java.util.List;

import javax.tools.JavaCompiler;
import javax.tools.ToolProvider;

import org.junit.Test;

import com.runtimeverification.rvmonitor.java.rt.tablebase.AbstractSynchronizedMonitor;
import com.runtimeverification.rvmonitor.java.rvj.Main;
import com.runtimeverification.rvmonitor.util.RVMException;
import com.runtimeverification.rvmonitor.util.Tool;

/**
 * INV-INS-120 — the generator, not the specification, names the offending event.
 *
 * <p>
 * A specification writes the macro {@code __EVENTNAME} where its report needs
 * {@code ev=}. The generator expands it in two shapes, and the two are not
 * interchangeable:
 *
 * <ul>
 * <li>inside an <b>event body</b> the name is known at generation time, so the
 * macro becomes a string literal and costs nothing at runtime;</li>
 * <li>inside a <b>handler body</b> ({@code @fail}) the offending event is only
 * known at runtime, so the macro becomes a call to the per-class helper
 * {@code RVM_eventName()}, never a direct table lookup.</li>
 * </ul>
 *
 * <p>
 * The reason the handler form goes through a helper rather than indexing the
 * table itself is that <b>the two monitor shapes do not store the same
 * number</b>. The atomic shape packs {@code lastEvent + 1} into {@code pairValue}
 * ({@code calculatePairValue}) and its {@code getLastEvent()} shifts the value
 * back out without subtracting, so the raw call yields {@code idnum + 1}, and
 * {@code 0} before any event. The non-atomic shape keeps the index itself in
 * {@code RVM_lastevent}, which {@link AbstractSynchronizedMonitor} initialises
 * to {@code -1}. One lookup written for both would name the <i>next</i> event in
 * every atomic class and the <i>first</i> event instead of {@code none} — a
 * misindexed name, which is worse than no name because it reads as a fact.
 *
 * <p>
 * The last test therefore does not settle for inspecting text: it compiles the
 * table and the helper the generator emits, drives them with the raw values each
 * shape really produces, and asserts the decoded name.
 */
public class EventNameMacroTest {

    /** The atomic-shape fixture: {@code SecretKeySpecSpec}'s event alphabet. */
    private static final List<String> ATOMIC_EVENTS = Arrays.asList("c1", "c2", "c3", "c4");

    /** The non-atomic fixture: {@code TrustManagerFactorySpec}'s alphabet. */
    private static final List<String> NON_ATOMIC_EVENTS = Arrays.asList("g1", "g2", "g3",
            "init", "gtm1");

    // ---------------------------------------------------------------- case 1

    @Test
    public void eventBodyMacroBecomesAStringLiteral() {
        String body = "ErrorCollector.instance().addError(new ErrorDescription("
                + "ErrorType.UnsafeAlgorithm, \"S\", \"ev=\" + __EVENTNAME));";

        String expanded = BaseMonitor.expandEventNameToLiteral(body, "g3");

        assertFalse("the macro must not survive", expanded.contains("__EVENTNAME"));
        assertTrue("the event name must appear as a literal, so it costs nothing at "
                + "runtime and needs no field: " + expanded, expanded.contains("\"g3\""));
        assertFalse("an event body must not consult the table at runtime",
                expanded.contains("RVM_eventNames["));
        assertFalse("an event body must not call the helper either",
                expanded.contains("RVM_eventName()"));
    }

    // ---------------------------------------------------------------- case 2

    @Test
    public void handlerMacroBecomesTheHelperCall() {
        String body = "ErrorCollector.instance().addError(new ErrorDescription("
                + "ErrorType.InvalidSequenceOfMethodCalls, \"S\", \"ev=\" + __EVENTNAME));";

        String expanded = BaseMonitor.expandEventNameToHelperCall(body);

        assertFalse("the macro must not survive", expanded.contains("__EVENTNAME"));
        assertTrue("a handler must call the per-class helper: " + expanded,
                expanded.contains("RVM_eventName()"));
        assertFalse("a handler must never index the table itself — HandlerMethod runs "
                + "before the monitor's shape is known, so it cannot decode the index",
                expanded.contains("RVM_eventNames["));
    }

    // ---------------------------------------------------------------- case 3

    @Test
    public void generationFailsClosedOnASurvivingMacro() {
        String content = "package mop;\nclass M {\n  String m() {\n"
                + "    return \"ev=\" + __EVENTNAME;\n  }\n}\n";
        try {
            Main.checkNoUnexpandedEventNameMacro(content, "MultiSpec_1RuntimeMonitor.java");
            fail("generation must abort when the literal __EVENTNAME reaches the output: "
                    + "javac would read it as an undefined identifier, or, inside a string, "
                    + "it would be reported as text and read as a fact");
        } catch (RVMException e) {
            String msg = String.valueOf(e.getMessage());
            assertTrue("the abort must name the file: " + msg,
                    msg.contains("MultiSpec_1RuntimeMonitor.java"));
            assertTrue("the abort must name the line: " + msg, msg.contains("4"));
        }
    }

    @Test
    public void generationProceedsWhenNoMacroSurvives() throws RVMException {
        Main.checkNoUnexpandedEventNameMacro("class M { String m() { return \"g1\"; } }",
                "MultiSpec_1RuntimeMonitor.java");
    }

    // ------------------------------------------------------- table emission

    @Test
    public void theTableIsIndexedByTheEventIndexAndBuiltFromOneIteration() {
        String table = BaseMonitor.eventNameTableCode(ATOMIC_EVENTS);

        assertTrue(table, table.contains("static final String[] RVM_eventNames"));
        assertTrue("names in event-index order, which is their position in the "
                + "specification's event list: " + table,
                table.contains("{\"c1\", \"c2\", \"c3\", \"c4\"}"));
    }

    /**
     * The generated file is formatted after the fact by
     * {@code Tool.changeIndentation}, which reads the brace structure of each
     * line. A line ending in <code>};</code> counts as the close of a block
     * there, so an array initialiser written that way unbalances the offset and,
     * at class level, underflows it — at which point the formatter catches the
     * exception and returns the whole file unindented. The table therefore ends
     * in <code>};;</code>, as the {@code Prop_N_transition_*} arrays beside it
     * already do. This test is what keeps that from being silently undone.
     */
    @Test
    public void theTableDoesNotUnbalanceTheFormatter() {
        String body = "class M {\n" + "int x = 1;\n"
                + BaseMonitor.eventNameTableCode(ATOMIC_EVENTS)
                + BaseMonitor.eventNameHelperCode(true, true) + "int y = 2;\n" + "}\n";

        String formatted = Tool.changeIndentation(body, "", "\t");

        assertTrue("the members of the class must be indented one level; the "
                + "formatter bailing out is what leaves them at column 0:\n" + formatted,
                formatted.contains("\tint x = 1;"));
        assertTrue(formatted, formatted.contains("\tint y = 2;"));
        assertTrue("the helper's body must be indented inside the helper:\n" + formatted,
                formatted.contains("\t\tint idx = this.getLastEvent();"));
    }

    // ------------------------------------------------- the helper, executed

    /**
     * The no-event value of the non-atomic shape is not a choice this change
     * makes; it is what the runtime the generated monitor extends already does.
     * Pinning it here means the helper's {@code -1} sentinel cannot drift away
     * from the field it decodes.
     */
    @Test
    public void theNonAtomicRuntimeStartsWithNoEvent() {
        AbstractSynchronizedMonitor monitor = new AbstractSynchronizedMonitor() {
            @Override
            protected void terminateInternal(int treeid) {
            }

            @Override
            public int getState() {
                return 0;
            }
        };
        assertEquals("AbstractSynchronizedMonitor.RVM_lastevent starts at -1", -1,
                monitor.getLastEvent());
    }

    @Test
    public void theAtomicHelperNamesTheEventThatFiredAndNotTheNextOne() throws Exception {
        EmittedHelper helper = compileHelper("AtomicShape", ATOMIC_EVENTS, true, true);

        // calculatePairValue(-1, 0) is the initial pairValue, so the raw call is 0.
        assertEquals("a handler that runs before any event must render none", "none",
                helper.nameFor(0));
        // The first dispatched event has idnum 0 and is stored as 0 + 1.
        assertEquals("the handler of the first dispatched event sees that event's own "
                + "name, not the next one in the table", "c1", helper.nameFor(1));
        assertEquals("c2", helper.nameFor(2));
        assertEquals("c4", helper.nameFor(4));
        assertEquals("out of range is none, never an out-of-range access", "none",
                helper.nameFor(99));
    }

    @Test
    public void theNonAtomicHelperNamesTheEventThatFired() throws Exception {
        EmittedHelper helper = compileHelper("NonAtomicShape", NON_ATOMIC_EVENTS, true, false);

        assertEquals("RVM_lastevent starts at -1, so a handler run before any event "
                + "renders none", "none", helper.nameFor(-1));
        assertEquals("the index is stored as is in this shape", "g1", helper.nameFor(0));
        assertEquals("init", helper.nameFor(3));
        assertEquals("gtm1", helper.nameFor(4));
        assertEquals("none", helper.nameFor(99));
    }

    @Test
    public void aNonOutermostMonitorHasNoLastEventAndSaysSo() throws Exception {
        EmittedHelper helper = compileHelper("SuffixShape", ATOMIC_EVENTS, false, false);

        assertEquals("a non-outermost monitor records no last event at all", "none",
                helper.nameFor(0));
        assertEquals("none", helper.nameFor(3));
    }

    // ------------------------------------------------------------- plumbing

    /** A compiled copy of one monitor class's table and helper, driven by hand. */
    private static final class EmittedHelper {
        private final Object instance;
        private final Method probe;
        private final java.lang.reflect.Field raw;

        EmittedHelper(Object instance, Method probe, java.lang.reflect.Field raw) {
            this.instance = instance;
            this.probe = probe;
            this.raw = raw;
        }

        String nameFor(int rawLastEvent) throws Exception {
            raw.setInt(instance, rawLastEvent);
            return (String) probe.invoke(instance);
        }
    }

    /**
     * Wrap the generator's own table and helper in the smallest class that can
     * run them, compile it, and hand back a driver.
     *
     * <p>
     * The stub supplies the one thing the helper reads — {@code getLastEvent()} —
     * from a settable field, which is how the test can put the raw value each
     * shape really produces (index + 1 with 0 for "none" in the atomic shape;
     * the index itself with -1 for "none" in the other) without building a whole
     * monitor and a trace to drive it.
     */
    private static EmittedHelper compileHelper(String className, List<String> events,
            boolean isOutermost, boolean atomic) throws Exception {
        String source = "public class " + className + " {\n"
                + "  public int rawLastEvent;\n"
                + "  public int getLastEvent() { return this.rawLastEvent; }\n"
                + BaseMonitor.eventNameTableCode(events)
                + BaseMonitor.eventNameHelperCode(isOutermost, atomic)
                + "  public String probe() { return RVM_eventName(); }\n"
                + "}\n";

        File dir = new File(System.getProperty("java.io.tmpdir"),
                "gh104-eventname-" + className + "-" + System.nanoTime());
        if (!dir.mkdirs()) {
            throw new IllegalStateException("could not create " + dir);
        }
        File file = new File(dir, className + ".java");
        PrintWriter writer = new PrintWriter(file, "UTF-8");
        writer.print(source);
        writer.close();

        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException("no javac on this JVM; run the tests on a JDK");
        }
        int rc = compiler.run(null, null, null, "-d", dir.getAbsolutePath(),
                file.getAbsolutePath());
        assertEquals("the emitted table and helper must compile:\n" + source, 0, rc);

        URLClassLoader loader = new URLClassLoader(new URL[] { dir.toURI().toURL() },
                EventNameMacroTest.class.getClassLoader());
        try {
            Class<?> cls = loader.loadClass(className);
            Object instance = cls.getDeclaredConstructor().newInstance();
            Method probe = cls.getMethod("probe");
            java.lang.reflect.Field raw = cls.getField("rawLastEvent");
            return new EmittedHelper(instance, probe, raw);
        } finally {
            // The class stays loaded through the instance; closing the loader
            // here would break the reflective calls, so it is left to the JVM.
        }
    }
}

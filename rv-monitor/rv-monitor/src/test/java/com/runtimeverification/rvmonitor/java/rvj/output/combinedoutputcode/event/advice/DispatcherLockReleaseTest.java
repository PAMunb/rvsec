package com.runtimeverification.rvmonitor.java.rvj.output.combinedoutputcode.event.advice;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.PrintWriter;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import javax.tools.JavaCompiler;
import javax.tools.ToolProvider;

import org.junit.Test;

import com.runtimeverification.rvmonitor.java.rvj.output.RVMVariable;
import com.runtimeverification.rvmonitor.java.rvj.output.combinedoutputcode.GlobalLock;

/**
 * INV-INS-129 — the generated dispatcher releases its lock on every exit.
 *
 * <p>
 * Every dispatcher the generator emits serialises its work behind one
 * {@code ReentrantLock} shared by the whole generated file: it opens with
 * {@code while (!L.tryLock()) { Thread.yield(); }} and closes with
 * {@code L.unlock()}. A {@code condition()}, an event body or a {@code @fail}
 * handler that throws unwinds straight past that {@code unlock()}. Because the
 * waiting form is a spin and not a block, the consequence is not a lost report:
 * the next monitored call of <b>any</b> specification, on any other thread,
 * enters an unbounded {@code Thread.yield()} loop. The application stops
 * progressing, the instrumentation stops emitting, and the run is
 * indistinguishable from a timeout.
 *
 * <p>
 * The test therefore needs a <b>second thread</b>. The lock is reentrant, so the
 * throwing thread re-enters it whatever the generator emits, and two calls on
 * one thread would pass with the lock still leaked.
 *
 * <p>
 * The dispatcher under test is assembled from the generator's own fragments —
 * {@link Advice#enterGuardedRegion} and {@link Advice#leaveGuardedRegion}, the
 * two sites {@code Advice.adviceBody()} uses — around a body that throws, and
 * then compiled and run. Assembling it from anything else would test a copy.
 */
public class DispatcherLockReleaseTest {

    private static final long BOUND_SECONDS = 2;

    @Test
    public void aSecondThreadStillDispatchesAfterAHandlerThrows() throws Exception {
        Method dispatch = compileDispatcher();

        // Thread A: the throw. The exception must reach the application, as it
        // does today — the repair changes the lock's release, not the
        // propagation.
        try {
            dispatch.invoke(null, Boolean.TRUE);
            fail("the exception must still propagate to the woven application");
        } catch (InvocationTargetException e) {
            assertEquals(RuntimeException.class, e.getCause().getClass());
        }

        // Thread B: a monitored call from another thread, bounded. Daemon, so a
        // thread left spinning in the yield loop cannot hold the JVM open.
        ExecutorService other = Executors.newSingleThreadExecutor(new ThreadFactory() {
            @Override
            public Thread newThread(Runnable r) {
                Thread t = new Thread(r, "gh104-other-thread");
                t.setDaemon(true);
                return t;
            }
        });
        try {
            Future<String> call = other.submit(new Callable<String>() {
                @Override
                public String call() throws Exception {
                    dispatch.invoke(null, Boolean.FALSE);
                    return "completed";
                }
            });
            try {
                assertEquals("completed", call.get(BOUND_SECONDS, TimeUnit.SECONDS));
            } catch (TimeoutException timeout) {
                fail("a second thread's dispatcher did not complete within "
                        + BOUND_SECONDS + "s: the global lock was never released by "
                        + "the throwing call, so every other thread now spins in "
                        + "the tryLock/Thread.yield loop for ever (INV-INS-129)");
            }
        } finally {
            other.shutdownNow();
        }
    }

    /**
     * The framing belongs to the advice emitter, not to {@code GlobalLock}.
     *
     * <p>
     * {@code GlobalLock.getAcquireCode()} and {@code getReleaseCode()} are string
     * fragments that {@code BaseMonitor.execEvent}, {@code StartThread},
     * {@code EndThread} and {@code ThreadStatusMonitor} also use, and use
     * <i>unbalanced</i> by design — release, start a thread, re-acquire. Framing
     * them there would emit a stray {@code try} into every one of those callers.
     */
    @Test
    public void theFramingIsInTheAdviceEmitterAndNotInGlobalLock() {
        GlobalLock lock = new GlobalLock(new RVMVariable("Gh104_RVMLock"));

        assertFalse("GlobalLock's acquire fragment must stay a bare fragment",
                lock.getAcquireCode().contains("try {"));
        assertFalse("GlobalLock's release fragment must stay a bare fragment",
                lock.getReleaseCode().contains("finally"));

        assertTrue("the advice emitter opens the guarded region",
                Advice.enterGuardedRegion(lock).contains("try {"));
        assertTrue("the advice emitter closes it whatever path leaves it",
                Advice.leaveGuardedRegion(lock).contains("finally"));
        assertTrue("and the release itself is unchanged, only relocated",
                Advice.leaveGuardedRegion(lock).contains("Gh104_RVMLock.unlock();"));
    }

    // ------------------------------------------------------------- plumbing

    /**
     * Build one dispatcher out of the generator's fragments and compile it.
     *
     * @return the static {@code dispatch(boolean raise)} of the compiled class
     */
    private static Method compileDispatcher() throws Exception {
        GlobalLock lock = new GlobalLock(new RVMVariable("Gh104_RVMLock"));

        String source = "import java.util.concurrent.locks.Condition;\n"
                + "import java.util.concurrent.locks.ReentrantLock;\n"
                + "public class Gh104Dispatcher {\n"
                + lock.toString()
                + "public static void dispatch(boolean raise) {\n"
                + Advice.enterGuardedRegion(lock)
                + "if (raise) {\n"
                + "throw new RuntimeException(\"a condition() or a @fail handler threw\");\n"
                + "}\n"
                + Advice.leaveGuardedRegion(lock)
                + "}\n"
                + "}\n";

        File dir = new File(System.getProperty("java.io.tmpdir"),
                "gh104-dispatcher-" + System.nanoTime());
        if (!dir.mkdirs()) {
            throw new IllegalStateException("could not create " + dir);
        }
        File file = new File(dir, "Gh104Dispatcher.java");
        PrintWriter writer = new PrintWriter(file, "UTF-8");
        writer.print(source);
        writer.close();

        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException("no javac on this JVM; run the tests on a JDK");
        }
        int rc = compiler.run(null, null, null, "-d", dir.getAbsolutePath(),
                file.getAbsolutePath());
        assertEquals("the emitted dispatcher must compile:\n" + source, 0, rc);

        URLClassLoader loader = new URLClassLoader(new URL[] { dir.toURI().toURL() },
                DispatcherLockReleaseTest.class.getClassLoader());
        return loader.loadClass("Gh104Dispatcher").getMethod("dispatch", boolean.class);
    }
}

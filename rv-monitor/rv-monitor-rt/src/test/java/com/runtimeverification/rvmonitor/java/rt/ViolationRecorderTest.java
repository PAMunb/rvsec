package com.runtimeverification.rvmonitor.java.rt;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.List;

import org.junit.Test;

/**
 * Covers which stack frame a violation is attributed to.
 *
 * <p>
 * {@code makeRelevantList} decides the {@code location} of every record the monitors emit, and
 * {@code location} is part of the dedupe identity, so a frame kept by mistake is not a cosmetic
 * defect — it silently re-keys the record. Frames are built with the four-argument
 * {@code StackTraceElement} constructor so that a {@code null} file name, which only a runtime-
 * generated or debug-stripped class produces in the wild, can be exercised deterministically.
 */
public class ViolationRecorderTest {

	private static StackTraceElement frame(String className, String fileName) {
		return new StackTraceElement(className, "someMethod", fileName, 42);
	}

	@Test
	public void aRuntimeFrameWithoutAFileNameIsExcluded() {
		StackTraceElement[] stack = {
			frame("com.runtimeverification.rvmonitor.java.rt.RuntimeOption", null),
			frame("com.example.Crypto", "Crypto.java"),
		};

		List<StackTraceElement> relevant = ViolationRecorder.makeRelevantList(stack);

		assertEquals(1, relevant.size());
		assertEquals("com.example.Crypto", relevant.get(0).getClassName());
	}

	@Test
	public void theFirstApplicationFrameBelowIsTheReportedOne() {
		StackTraceElement[] stack = {
			frame("rvm.MessageDigestSpecMonitor", null),
			frame("mop.MonitorWrappers", null),
			frame("javamop.Agent", null),
			frame("com.example.Crypto", "Crypto.java"),
			frame("com.example.Main", "Main.java"),
		};

		List<StackTraceElement> relevant = ViolationRecorder.makeRelevantList(stack);

		assertEquals(2, relevant.size());
		assertEquals("com.example.Crypto", relevant.get(0).getClassName());
	}

	@Test
	public void aRuntimeFrameWithAFileNameIsStillExcluded() {
		StackTraceElement[] stack = {
			frame("com.runtimeverification.rvmonitor.java.rt.ViolationRecorder", "ViolationRecorder.java"),
			frame("com.example.Crypto", "Crypto.java"),
		};

		assertEquals(1, ViolationRecorder.makeRelevantList(stack).size());
	}

	@Test
	public void anAspectSourceFrameIsExcluded() {
		StackTraceElement[] stack = {
			frame("com.example.generated.Aspect", "MultiSpec_1.aj"),
			frame("com.example.Crypto", "Crypto.java"),
		};

		List<StackTraceElement> relevant = ViolationRecorder.makeRelevantList(stack);

		assertEquals(1, relevant.size());
		assertEquals("com.example.Crypto", relevant.get(0).getClassName());
	}

	@Test
	public void anApplicationFrameWithoutAFileNameIsKept() {
		StackTraceElement[] stack = {
			frame("com.example.Generated$$Lambda", null),
			frame("com.example.Crypto", "Crypto.java"),
		};

		List<StackTraceElement> relevant = ViolationRecorder.makeRelevantList(stack);

		assertEquals(2, relevant.size());
		assertEquals("com.example.Generated$$Lambda", relevant.get(0).getClassName());
	}

	@Test
	public void aStackOfNothingButRuntimeFramesIsEmpty() {
		StackTraceElement[] stack = {
			frame("com.runtimeverification.rvmonitor.java.rt.ViolationRecorder", null),
			frame("rvm.CipherSpecMonitor", null),
		};

		assertTrue(ViolationRecorder.makeRelevantList(stack).isEmpty());
	}
}

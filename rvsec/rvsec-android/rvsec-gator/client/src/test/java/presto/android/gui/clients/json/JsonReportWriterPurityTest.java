package presto.android.gui.clients.json;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.lang.reflect.Field;

import org.junit.Test;

import presto.android.gui.clients.reach.ReachabilityIndex;

/**
 * INV-ANA-30 — writer purity. {@link JsonReportWriter} MUST NOT hold
 * any reference to {@link ReachabilityIndex}; per-method reachability
 * is read exclusively through the injected
 * {@link presto.android.gui.clients.reach.ReachabilityEnricher}.
 *
 * <p>The structural check walks declared fields and asserts none are
 * typed {@code ReachabilityIndex}. A future change that adds a direct
 * index reference (e.g., a cache field) fails this test at the next
 * build.
 */
public class JsonReportWriterPurityTest {

	@Test
	public void writerHasNoReachabilityIndexField() {
		for (Field f : JsonReportWriter.class.getDeclaredFields()) {
			assertFalse(
					"JsonReportWriter field '" + f.getName() + "' must not be typed "
							+ "ReachabilityIndex (INV-ANA-30). Per-method reachability "
							+ "is consulted through ReachabilityEnricher; a direct "
							+ "index reference re-introduces the writer-impurity that "
							+ "the C1d visitor extraction closed.",
					ReachabilityIndex.class.isAssignableFrom(f.getType()));
		}
	}

	@Test
	public void writerHasNoReachabilityIndexReferenceInPublicSurface() {
		// Walking method signatures: no parameter or return type may
		// expose ReachabilityIndex either. The writer's published API
		// surface should mention only ReachabilityEnricher.
		for (var m : JsonReportWriter.class.getDeclaredMethods()) {
			for (Class<?> p : m.getParameterTypes()) {
				assertFalse(
						"JsonReportWriter method " + m.getName()
								+ " takes ReachabilityIndex (INV-ANA-30 violation)",
						ReachabilityIndex.class.isAssignableFrom(p));
			}
			assertFalse(
					"JsonReportWriter method " + m.getName()
							+ " returns ReachabilityIndex (INV-ANA-30 violation)",
					ReachabilityIndex.class.isAssignableFrom(m.getReturnType()));
		}
	}

	@Test
	public void writerConstructorTakesEnricherOnly() {
		boolean foundEnricherCtor = false;
		for (var ctor : JsonReportWriter.class.getDeclaredConstructors()) {
			Class<?>[] params = ctor.getParameterTypes();
			if (params.length == 1
					&& params[0].getSimpleName().equals("ReachabilityEnricher")) {
				foundEnricherCtor = true;
			}
			for (Class<?> p : params) {
				assertFalse(
						"JsonReportWriter constructor takes ReachabilityIndex "
								+ "(INV-ANA-30 violation)",
						ReachabilityIndex.class.isAssignableFrom(p));
			}
		}
		assertTrue("JsonReportWriter must expose a constructor accepting only the "
				+ "ReachabilityEnricher visitor", foundEnricherCtor);
	}
}

package presto.android.gui.clients.target;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.junit.Test;

import presto.android.gui.clients.target.TargetMethod.MatchPolicy;

/**
 * Unit tests for the {@link TargetMethod} POJO: equality, hashCode,
 * and immutability of the {@code params} list.
 */
public class TargetMethodTest {

	@Test
	public void equalInstancesAreEqualAndShareHash() {
		TargetMethod a = new TargetMethod("javax.crypto.Cipher", "init",
				Arrays.asList("int", "java.security.Key"),
				"<javax.crypto.Cipher: void init(int,java.security.Key)>",
				MatchPolicy.STRICT);
		TargetMethod b = new TargetMethod("javax.crypto.Cipher", "init",
				Arrays.asList("int", "java.security.Key"),
				"<javax.crypto.Cipher: void init(int,java.security.Key)>",
				MatchPolicy.STRICT);
		assertEquals(a, b);
		assertEquals(a.hashCode(), b.hashCode());
	}

	@Test
	public void differentPolicyMakesUnequal() {
		TargetMethod lenient = new TargetMethod("X", "m",
				Arrays.asList(), null, MatchPolicy.LENIENT);
		TargetMethod strict = new TargetMethod("X", "m",
				Arrays.asList(), null, MatchPolicy.STRICT);
		assertNotEquals(lenient, strict);
	}

	@Test
	public void differentMethodNameMakesUnequal() {
		TargetMethod a = new TargetMethod("X", "m", Arrays.asList(), null, MatchPolicy.LENIENT);
		TargetMethod b = new TargetMethod("X", "n", Arrays.asList(), null, MatchPolicy.LENIENT);
		assertNotEquals(a, b);
	}

	@Test
	public void paramsListIsUnmodifiable() {
		List<String> original = new ArrayList<>(Arrays.asList("int"));
		TargetMethod t = new TargetMethod("X", "m", original, null, MatchPolicy.LENIENT);
		try {
			t.getParams().add("extra");
			fail("Expected UnsupportedOperationException on getParams().add(...)");
		} catch (UnsupportedOperationException expected) {
			// good
		}
		assertEquals(1, t.getParams().size());
	}

	@Test
	public void paramsListReflectsConstructionValue() {
		TargetMethod t = new TargetMethod("X", "m",
				Arrays.asList("int", "java.lang.String"),
				null, MatchPolicy.LENIENT);
		assertEquals(Arrays.asList("int", "java.lang.String"), t.getParams());
	}

	@Test(expected = NullPointerException.class)
	public void nullClassNameRejected() {
		new TargetMethod(null, "m", Arrays.asList(), null, MatchPolicy.LENIENT);
	}

	@Test(expected = NullPointerException.class)
	public void nullMethodNameRejected() {
		new TargetMethod("X", null, Arrays.asList(), null, MatchPolicy.LENIENT);
	}

	@Test(expected = NullPointerException.class)
	public void nullParamsRejected() {
		new TargetMethod("X", "m", null, null, MatchPolicy.LENIENT);
	}

	@Test(expected = NullPointerException.class)
	public void nullPolicyRejected() {
		new TargetMethod("X", "m", Arrays.asList(), null, null);
	}

	@Test
	public void nullSignatureAllowed() {
		TargetMethod t = new TargetMethod("X", "m", Arrays.asList(), null, MatchPolicy.LENIENT);
		assertEquals(null, t.getSignature());
		assertTrue(t.toString().contains("X.m"));
		assertFalse(t.toString().contains("null"));
	}
}

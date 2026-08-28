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
				MatchPolicy.STRICT, false, false);
		TargetMethod b = new TargetMethod("javax.crypto.Cipher", "init",
				Arrays.asList("int", "java.security.Key"),
				"<javax.crypto.Cipher: void init(int,java.security.Key)>",
				MatchPolicy.STRICT, false, false);
		assertEquals(a, b);
		assertEquals(a.hashCode(), b.hashCode());
	}

	@Test
	public void differentPolicyMakesUnequal() {
		TargetMethod lenient = new TargetMethod("X", "m",
				Arrays.asList(), null, MatchPolicy.LENIENT, false, false);
		TargetMethod strict = new TargetMethod("X", "m",
				Arrays.asList(), null, MatchPolicy.STRICT, false, false);
		assertNotEquals(lenient, strict);
	}

	@Test
	public void differentSubtypeFlagMakesUnequal() {
		// The corpus contains a real pair that differs only by the `+` operator
		// (Iterator.next vs Iterator+.next), and both must survive in a Set<TargetMethod>.
		TargetMethod exact = new TargetMethod("java.util.Iterator", "next",
				Arrays.asList(), null, MatchPolicy.LENIENT, false, false);
		TargetMethod subtype = new TargetMethod("java.util.Iterator", "next",
				Arrays.asList(), null, MatchPolicy.LENIENT, true, false);
		assertNotEquals(exact, subtype);
	}

	@Test
	public void differentNamePatternFlagMakesUnequal() {
		TargetMethod literal = new TargetMethod("X", "add",
				Arrays.asList(), null, MatchPolicy.LENIENT, false, false);
		TargetMethod pattern = new TargetMethod("X", "add",
				Arrays.asList(), null, MatchPolicy.LENIENT, false, true);
		assertNotEquals(literal, pattern);
	}

	@Test
	public void differentMethodNameMakesUnequal() {
		TargetMethod a = new TargetMethod("X", "m", Arrays.asList(), null, MatchPolicy.LENIENT, false, false);
		TargetMethod b = new TargetMethod("X", "n", Arrays.asList(), null, MatchPolicy.LENIENT, false, false);
		assertNotEquals(a, b);
	}

	@Test
	public void paramsListIsUnmodifiable() {
		List<String> original = new ArrayList<>(Arrays.asList("int"));
		TargetMethod t = new TargetMethod("X", "m", original, null, MatchPolicy.LENIENT, false, false);
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
				null, MatchPolicy.LENIENT, false, false);
		assertEquals(Arrays.asList("int", "java.lang.String"), t.getParams());
	}

	@Test(expected = NullPointerException.class)
	public void nullClassNameRejected() {
		new TargetMethod(null, "m", Arrays.asList(), null, MatchPolicy.LENIENT, false, false);
	}

	@Test(expected = NullPointerException.class)
	public void nullMethodNameRejected() {
		new TargetMethod("X", null, Arrays.asList(), null, MatchPolicy.LENIENT, false, false);
	}

	@Test(expected = NullPointerException.class)
	public void nullParamsRejected() {
		new TargetMethod("X", "m", null, null, MatchPolicy.LENIENT, false, false);
	}

	@Test(expected = NullPointerException.class)
	public void nullPolicyRejected() {
		new TargetMethod("X", "m", Arrays.asList(), null, null, false, false);
	}

	@Test
	public void nullSignatureAllowed() {
		TargetMethod t = new TargetMethod("X", "m", Arrays.asList(), null, MatchPolicy.LENIENT, false, false);
		assertEquals(null, t.getSignature());
		assertTrue(t.toString().contains("X.m"));
		assertFalse(t.toString().contains("null"));
	}
}

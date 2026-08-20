package br.unb.cic.mop.eh;

import static org.junit.Assert.assertEquals;

import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;

import org.junit.Test;

/**
 * The report vocabulary is closed, and this test is what closes it.
 *
 * <p>
 * An {@link ErrorType} is not free-form metadata: the message-property gate of gh104 maps each
 * CrySL clause family to the types admissible for it, so adding a value here without a site that
 * emits it leaves dead vocabulary that the next reader assumes is live, and removing one silently
 * breaks the mapping. Asserting the whole set — rather than the presence of one member — is what
 * makes either move visible in a diff.
 */
public class ErrorTypeTest {

	@Test
	public void vocabularyIsExactlyTheSevenClauseFamiliesTheSpecificationsEmit() {
		Set<String> expected = new LinkedHashSet<>(Arrays.asList(
				"UnsafeAlgorithm",
				"InvalidSequenceOfMethodCalls",
				"UnsatisfiedConstraint",
				"InvalidKeySize",
				"InvalidKeyStoreType",
				"UnsafeProtocol",
				"ForbiddenMethod"));

		Set<String> actual = new LinkedHashSet<>();
		for (ErrorType type : ErrorType.values()) {
			actual.add(type.name());
		}

		assertEquals(expected, actual);
	}

	/**
	 * A {@code FORBIDDEN} constructor is reported as itself.
	 *
	 * <p>
	 * {@code PBEKeySpecSpec}'s {@code f1}/{@code f2} encode the two constructors
	 * {@code generated/api30/PBEKeySpec.cryptsl} forbids. They used to report
	 * {@code InvalidSequenceOfMethodCalls}, which describes a call the developer failed to make;
	 * the finding is the call they did make.
	 */
	@Test
	public void forbiddenMethodTravelsThroughAReportUnchanged() {
		ErrorDescription report = new ErrorDescription(ErrorType.ForbiddenMethod, "PBEKeySpecSpec",
				"a.b.C.m(C.java:1)", "v=1 code=PBEKEYSPEC-FORB-00");

		assertEquals(ErrorType.ForbiddenMethod, report.getType());
		assertEquals("ForbiddenMethod", report.getErrorSummary().getError());
	}
}

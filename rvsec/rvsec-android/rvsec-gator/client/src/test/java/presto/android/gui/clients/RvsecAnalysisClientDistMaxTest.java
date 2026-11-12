package presto.android.gui.clients;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import org.junit.Test;

/**
 * {@link RvsecAnalysisClient#parseDistMax}, the check of {@code -clientParam distMax=N}
 * (INV-ANA-99, INV-ANA-100). {@code run} calls it before anything else, so a value it refuses
 * ends the run before the client computes or writes anything; a run without the parameter
 * gets {@code null}, the default horizon and no {@code distMax} member.
 */
public class RvsecAnalysisClientDistMaxTest {

	@Test
	public void anAbsentParameterGivesNull() {
		assertNull(RvsecAnalysisClient.parseDistMax(null));
	}

	@Test
	public void anIntegerOfAtLeastOneIsReturned() {
		assertEquals(Integer.valueOf(1), RvsecAnalysisClient.parseDistMax("1"));
		assertEquals(Integer.valueOf(15), RvsecAnalysisClient.parseDistMax("15"));
	}

	@Test
	public void aLeadingPlusSignIsAccepted() {
		// Integer.parseInt accepts it, and the check is Integer.parseInt's.
		assertEquals(Integer.valueOf(5), RvsecAnalysisClient.parseDistMax("+5"));
	}

	@Test
	public void aValueThatIsNotAnIntegerOfAtLeastOneIsRefusedNamingIt() {
		// Below 1, not a number, empty, not an integer, beyond the int range.
		for (String given : new String[] { "0", "-1", "ten", "", "1.5", "99999999999" }) {
			try {
				RvsecAnalysisClient.parseDistMax(given);
				fail("distMax '" + given + "' was accepted");
			} catch (IllegalStateException expected) {
				String message = expected.getMessage();
				assertTrue(message, message.contains("distMax"));
				assertTrue(message, message.contains("'" + given + "'"));
			}
		}
	}

	@Test
	public void theRefusalStatesTheRule() {
		try {
			RvsecAnalysisClient.parseDistMax("ten");
			fail("distMax 'ten' was accepted");
		} catch (IllegalStateException expected) {
			assertEquals("distMax must be an integer >= 1, got 'ten'", expected.getMessage());
		}
	}
}

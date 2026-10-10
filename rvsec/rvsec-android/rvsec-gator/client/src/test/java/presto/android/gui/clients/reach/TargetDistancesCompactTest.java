package presto.android.gui.clients.reach;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;

import org.junit.Test;

/**
 * {@link TargetDistances#compact} (INV-ANA-85): a method keeps its pairs at
 * {@code d <= COMPACT_WEIGHED_MAX} and its {@code COMPACT_K} nearest by {@code (d, i)},
 * sorted by {@code i}. Each input holds at most one pair per target index, as the
 * distance pass writes it.
 */
public class TargetDistancesCompactTest {

	private static int[][] pairs(int... flat) {
		int[][] out = new int[flat.length / 2][];
		for (int k = 0; k < out.length; k++) {
			out[k] = new int[] { flat[2 * k], flat[2 * k + 1] };
		}
		return out;
	}

	@Test
	public void constantsAreTheDerivesValues() {
		assertEquals(3, TargetDistances.COMPACT_WEIGHED_MAX);
		assertEquals(3, TargetDistances.COMPACT_K);
	}

	@Test
	public void aMethodFarFromMostTargetsKeepsItsThreeNearest() {
		int[][] in = pairs(0, 7, 1, 5, 2, 9, 3, 6, 4, 10);

		assertArrayEquals(pairs(0, 7, 1, 5, 3, 6), TargetDistances.compact(in));
	}

	@Test
	public void everyPairWithinThreeCallsIsKept() {
		int[][] in = pairs(0, 1, 1, 3, 2, 2, 3, 3, 4, 8);

		assertArrayEquals(pairs(0, 1, 1, 3, 2, 2, 3, 3), TargetDistances.compact(in));
	}

	@Test
	public void tiesInDistanceAreBrokenByIndex() {
		int[][] in = pairs(0, 5, 1, 5, 2, 5, 3, 5);

		assertArrayEquals(pairs(0, 5, 1, 5, 2, 5), TargetDistances.compact(in));
	}

	@Test
	public void tiesAreBrokenByIndexWhateverTheInputOrder() {
		int[][] in = pairs(3, 5, 0, 4, 2, 5, 1, 5);

		assertArrayEquals(pairs(0, 4, 1, 5, 2, 5), TargetDistances.compact(in));
	}

	@Test
	public void fewerThanThreePairsAreKeptWhole() {
		int[][] in = pairs(0, 9, 4, 10);

		assertArrayEquals(pairs(0, 9, 4, 10), TargetDistances.compact(in));
	}

	@Test
	public void aSinglePairAtTheCapIsKept() {
		int[][] in = pairs(2, TargetDistances.DIST_MAX);

		assertArrayEquals(pairs(2, TargetDistances.DIST_MAX), TargetDistances.compact(in));
	}

	@Test
	public void emptyInputGivesEmptyOutput() {
		int[][] out = TargetDistances.compact(new int[0][]);

		assertNotNull(out);
		assertEquals(0, out.length);
	}

	@Test
	public void theInputIsNotModified() {
		int[][] in = pairs(0, 7, 1, 5, 2, 9, 3, 6, 4, 10);
		int[][] before = pairs(0, 7, 1, 5, 2, 9, 3, 6, 4, 10);

		TargetDistances.compact(in);

		assertArrayEquals(before, in);
	}
}

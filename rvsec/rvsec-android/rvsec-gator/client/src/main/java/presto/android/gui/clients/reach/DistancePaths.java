package presto.android.gui.clients.reach;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * The distance paths of a run (INV-ANA-91, -92, -93), as the document writes them: the
 * {@code pathMethods} table and the {@code distancePaths} steps.
 *
 * <p>A step {@code [i, v, n]} says that on the way to distance target {@code i}, method
 * {@code v} calls method {@code n}, and {@code n} is one call closer to the target. {@code v}
 * and {@code n} are indices into {@link #methods()}. A reader rebuilds the chain of a pair
 * {@code [i, d]} on a method by following {@code n} from that method, {@code d} times.
 *
 * <p>{@link TargetDistances#paths} builds it. The holder is not modified after construction;
 * {@link #steps()} returns its own arrays, which callers read and do not modify.
 */
public final class DistancePaths {

	private final List<String> methods;
	private final int[][] steps;

	/**
	 * @param methods the signatures of the methods that occur in some step, sorted
	 * @param steps the steps {@code [i, v, n]}, sorted by {@code (i, v)}, at most one per
	 *     {@code (i, v)}
	 */
	public DistancePaths(List<String> methods, int[][] steps) {
		this.methods = Collections.unmodifiableList(new ArrayList<>(methods));
		this.steps = steps;
	}

	/** Signatures of the methods that occur in some step, sorted; the index space of the steps. */
	public List<String> methods() {
		return methods;
	}

	/** Steps {@code [i, v, n]}, sorted by {@code (i, v)}. */
	public int[][] steps() {
		return steps;
	}
}

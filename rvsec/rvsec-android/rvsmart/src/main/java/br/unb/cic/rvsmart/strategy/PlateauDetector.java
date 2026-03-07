package br.unb.cic.rvsmart.strategy;

import java.util.LinkedList;

/**
 * Detects exploration plateaus using a sliding window of iteration outcomes.
 *
 * Each iteration records whether it discovered a new state and whether it triggered
 * new MOP coverage. A plateau is detected when the last WINDOW_SIZE iterations all
 * had no new state AND no new MOP coverage -- meaning the agent is stuck repeating
 * already-visited states without gaining coverage.
 *
 * The plateau signal is used by the agent loop to trigger proactive backtracking
 * or other recovery strategies, rather than continuing to waste iterations on
 * exhausted areas of the app.
 */
public class PlateauDetector {

    /** Number of consecutive no-progress iterations required to declare a plateau. */
    public static final int WINDOW_SIZE = 10;

    /**
     * Sliding window storing the last WINDOW_SIZE iteration outcomes.
     * Each entry is true if progress was made (new state OR new MOP coverage),
     * false otherwise.
     */
    private final LinkedList<Boolean> window = new LinkedList<>();

    /** Running count of consecutive iterations with no progress. */
    private int consecutiveNoProgress = 0;

    /**
     * Records the outcome of one iteration.
     *
     * @param isNewState true if this iteration discovered a previously unseen screen state
     * @param hasNewMopCoverage true if this iteration triggered new MOP coverage
     */
    public void recordIteration(boolean isNewState, boolean hasNewMopCoverage) {
        boolean hasProgress = isNewState || hasNewMopCoverage;

        window.addLast(hasProgress);
        if (window.size() > WINDOW_SIZE) {
            window.removeFirst();
        }

        if (hasProgress) {
            consecutiveNoProgress = 0;
        } else {
            consecutiveNoProgress++;
        }
    }

    /**
     * Returns true if the agent is in a plateau: the last WINDOW_SIZE iterations
     * all had no progress (no new state, no new MOP coverage).
     *
     * Returns false if fewer than WINDOW_SIZE iterations have been recorded,
     * since the window is not yet full.
     */
    public boolean isPlateauDetected() {
        if (window.size() < WINDOW_SIZE) {
            return false;
        }
        for (boolean hasProgress : window) {
            if (hasProgress) {
                return false;
            }
        }
        return true;
    }

    /**
     * Returns the number of consecutive iterations with no progress.
     * Used for RVTRACK logging to show how deep into a plateau the agent is.
     */
    public int getConsecutiveNoProgress() {
        return consecutiveNoProgress;
    }
}

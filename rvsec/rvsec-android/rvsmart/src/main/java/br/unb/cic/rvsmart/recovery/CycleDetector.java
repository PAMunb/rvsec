package br.unb.cic.rvsmart.recovery;

import java.util.ArrayList;
import java.util.List;

/**
 * Detects ping-pong cycles in structural hash sequences.
 * Uses a ring buffer of the last 10 structHashes and checks for
 * period-2 to period-4 repeating patterns.
 *
 * A period-N cycle means the last 2*N entries form a repeating
 * pattern: entry[i] == entry[i+N] for all i in [0, N).
 */
public class CycleDetector {

    private static final int BUFFER_SIZE = 10;

    private final List<String> buffer = new ArrayList<>();

    /**
     * Record a structural hash from the current iteration.
     * Maintains a ring buffer of the last BUFFER_SIZE entries.
     */
    public void recordHash(String structHash) {
        buffer.add(structHash);
        if (buffer.size() > BUFFER_SIZE) {
            buffer.remove(0);
        }
    }

    /**
     * Check if a cycle has been detected.
     * Tests for period-2, period-3, and period-4 patterns
     * in the most recent entries.
     *
     * @return true if a repeating pattern is detected
     */
    public boolean isCycleDetected() {
        for (int period = 2; period <= 4; period++) {
            if (hasCycle(period)) return true;
        }
        return false;
    }

    /**
     * Check for a cycle of the given period in the most recent 2*period entries.
     * A cycle exists when entry[i] == entry[i+period] for all i in [0, period).
     */
    private boolean hasCycle(int period) {
        int needed = 2 * period;
        if (buffer.size() < needed) return false;

        int start = buffer.size() - needed;
        for (int i = 0; i < period; i++) {
            if (!buffer.get(start + i).equals(buffer.get(start + i + period))) {
                return false;
            }
        }
        return true;
    }

    /** Reset the buffer (e.g., after cycle recovery). */
    public void reset() {
        buffer.clear();
    }

    /** Get current buffer size. For testing. */
    public int getBufferSize() {
        return buffer.size();
    }
}

package br.unb.cic.rvsmart.device;

import android.util.Log;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Non-blocking logcat reader that captures RVSEC-COV coverage tags
 * from instrumented APKs.
 *
 * Runs as a daemon thread, continuously reading logcat output.
 * The main agent loop calls drainCoverageTags() each iteration to
 * collect newly covered method signatures.
 *
 * Coverage tag format: Log.v("RVSEC-COV", signature)
 * Logcat output format: "... V RVSEC-COV: javax.crypto.Cipher.getInstance"
 *
 * Graceful degradation (INV-RSM-05): if the APK is not instrumented,
 * no RVSEC-COV tags appear and drainCoverageTags() returns empty lists.
 */
public class LogcatReader {

    private static final String TAG = "RVSMART";
    private static final String COV_TAG = "RVSEC-COV";

    private final int maxBufferSize;
    private final ConcurrentLinkedQueue<String> buffer = new ConcurrentLinkedQueue<>();
    private final AtomicBoolean running = new AtomicBoolean(false);
    private Thread readerThread;

    public LogcatReader(int maxBufferSize) {
        this.maxBufferSize = maxBufferSize;
    }

    /**
     * Start the logcat reader daemon thread.
     * Clears existing logcat before starting to avoid stale entries.
     */
    public void start() {
        if (running.getAndSet(true)) {
            return; // Already running
        }

        // Clear logcat buffer to avoid stale coverage entries from previous runs
        try {
            new ProcessBuilder("logcat", "-c").start().waitFor();
        } catch (Exception e) {
            Log.w(TAG, "Failed to clear logcat: " + e.getMessage());
        }

        readerThread = new Thread(this::readLoop, "rvsmart-logcat");
        readerThread.setDaemon(true);
        readerThread.start();
        Log.d(TAG, "LogcatReader started");
    }

    /**
     * Stop the reader thread.
     */
    public void stop() {
        running.set(false);
        if (readerThread != null) {
            readerThread.interrupt();
        }
    }

    /**
     * Drain all accumulated coverage tags and clear the buffer.
     * Called from the main agent loop each iteration.
     *
     * @return List of covered method signatures since last drain
     */
    public List<String> drainCoverageTags() {
        List<String> tags = new ArrayList<>();
        String tag;
        while ((tag = buffer.poll()) != null) {
            tags.add(tag);
        }
        return tags;
    }

    /**
     * Number of buffered tags not yet drained.
     */
    public int bufferedCount() {
        return buffer.size();
    }

    private void readLoop() {
        try {
            // Read logcat filtered to RVSEC-COV tag only
            ProcessBuilder pb = new ProcessBuilder(
                    "logcat", "-v", "brief", "-s", COV_TAG + ":V");
            pb.redirectErrorStream(true);
            Process proc = pb.start();

            BufferedReader reader = new BufferedReader(
                    new InputStreamReader(proc.getInputStream()));

            String line;
            while (running.get() && (line = reader.readLine()) != null) {
                String signature = extractSignature(line);
                if (signature != null) {
                    if (buffer.size() < maxBufferSize) {
                        buffer.add(signature);
                    }
                    // Drop if buffer full — oldest entries already drained
                }
            }

            proc.destroy();
        } catch (Exception e) {
            if (running.get()) {
                Log.w(TAG, "LogcatReader error: " + e.getMessage());
            }
        }
    }

    /**
     * Extract method signature from a logcat line.
     * Input format: "V/RVSEC-COV( 1234): javax.crypto.Cipher.getInstance"
     * Output: "javax.crypto.Cipher.getInstance"
     */
    static String extractSignature(String line) {
        if (line == null || !line.contains(COV_TAG)) {
            return null;
        }
        // Find the ": " separator after the tag
        int colonIdx = line.indexOf(": ");
        if (colonIdx < 0) return null;
        String sig = line.substring(colonIdx + 2).trim();
        return sig.isEmpty() ? null : sig;
    }
}

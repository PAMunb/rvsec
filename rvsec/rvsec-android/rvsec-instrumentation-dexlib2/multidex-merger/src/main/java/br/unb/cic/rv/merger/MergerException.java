package br.unb.cic.rv.merger;

/**
 * Raised when APK repack / zipalign / apksigner pipeline fails. Carries the
 * failing tool name + exit code + stderr so the Python wrapper can populate
 * {@code _error_phase} on the resulting {@code InstrumentationResults}
 * error.
 */
public final class MergerException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public final String tool;
    public final int exitCode;
    public final String stderr;

    public MergerException(String tool, int exitCode, String stderr, String message) {
        super(message);
        this.tool = tool;
        this.exitCode = exitCode;
        this.stderr = stderr == null ? "" : stderr;
    }

    public MergerException(String tool, String message, Throwable cause) {
        super(message, cause);
        this.tool = tool;
        this.exitCode = -1;
        this.stderr = "";
    }
}

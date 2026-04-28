package br.unb.cic.rv.builder;

/**
 * Raised when an external subprocess (javac / d8) returns a non-zero exit
 * code or fails to start. Carries the tool name, exit code, and captured
 * stderr so the Python wrapper can surface the root cause and populate
 * {@code _error_phase} on the {@code InstrumentationResults} error entry.
 */
public final class CommandException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public final String tool;
    public final int exitCode;
    public final String stderr;

    public CommandException(String tool, int exitCode, String stderr, String message) {
        super(message);
        this.tool = tool;
        this.exitCode = exitCode;
        this.stderr = stderr == null ? "" : stderr;
    }

    public CommandException(String tool, String message, Throwable cause) {
        super(message, cause);
        this.tool = tool;
        this.exitCode = -1;
        this.stderr = "";
    }
}

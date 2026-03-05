package br.unb.cic.rvsmart.llm;

/**
 * Thrown when the LLM client encounters an HTTP error, timeout, or response parsing failure.
 */
public class LlmException extends RuntimeException {

    public LlmException(String message) {
        super(message);
    }

    public LlmException(String message, Throwable cause) {
        super(message, cause);
    }
}

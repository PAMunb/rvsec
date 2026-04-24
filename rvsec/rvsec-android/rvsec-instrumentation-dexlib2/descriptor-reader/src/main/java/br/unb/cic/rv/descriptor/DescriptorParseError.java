package br.unb.cic.rv.descriptor;

/**
 * Raised when the JSON descriptor cannot be deserialized into {@link AspectDescriptor}.
 *
 * <p>The message cites the JSON pointer of the failing field when Jackson provides
 * one (via {@code JsonMappingException.getPathReference()}).
 */
public final class DescriptorParseError extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public DescriptorParseError(String message) {
        super(message);
    }

    public DescriptorParseError(String message, Throwable cause) {
        super(message, cause);
    }
}

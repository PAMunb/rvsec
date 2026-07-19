package br.unb.cic.rv.descriptor;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;

/**
 * Loads an {@link AspectDescriptor} from the JSON produced by patched JavaMOP
 * ({@code --emit-descriptor}).
 *
 * <p>Fail-on-unknown-properties is enabled: any field in the JSON not mapped by a
 * POJO getter triggers {@link DescriptorParseError} with the JSON pointer of the
 * offending field. This catches descriptor schema drift early instead of silently
 * dropping data during weaving.
 */
public final class DescriptorReader {

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true);

    private DescriptorReader() {}

    public static AspectDescriptor read(File file) {
        try {
            return MAPPER.readValue(file, AspectDescriptor.class);
        } catch (JsonMappingException e) {
            throw new DescriptorParseError(formatMappingError(e, file.getPath()), e);
        } catch (IOException e) {
            throw new DescriptorParseError("Failed to read descriptor file: " + file, e);
        }
    }

    /** Convenience overload for callers holding an NIO {@link Path} instead of a {@link File}. */
    public static AspectDescriptor read(Path path) {
        return read(path.toFile());
    }

    /** Reads the descriptor from an already-open stream (e.g. a classpath resource). */
    public static AspectDescriptor read(InputStream in) {
        try {
            return MAPPER.readValue(in, AspectDescriptor.class);
        } catch (JsonMappingException e) {
            throw new DescriptorParseError(formatMappingError(e, "<input stream>"), e);
        } catch (IOException e) {
            throw new DescriptorParseError("Failed to read descriptor from input stream", e);
        }
    }

    /** Reads the descriptor from an in-memory JSON string (mainly used by tests). */
    public static AspectDescriptor read(String json) {
        try {
            return MAPPER.readValue(json, AspectDescriptor.class);
        } catch (JsonMappingException e) {
            throw new DescriptorParseError(formatMappingError(e, "<inline>"), e);
        } catch (IOException e) {
            throw new DescriptorParseError("Failed to read descriptor from string", e);
        }
    }

    private static String formatMappingError(JsonMappingException e, String source) {
        String pointer = e.getPathReference();
        return "Failed to parse descriptor from " + source
                + (pointer == null || pointer.isEmpty() ? "" : " at path " + pointer)
                + ": " + e.getOriginalMessage();
    }
}

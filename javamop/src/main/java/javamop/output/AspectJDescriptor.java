// Copyright (c) 2026 RVSec. Released under the same license as JavaMOP.
package javamop.output;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import javamop.output.combinedaspect.CombinedAspect;
import javamop.output.descriptor.DescriptorWriter;
import javamop.parser.ast.MOPSpecFile;
import javamop.parser.ast.mopspec.JavaMOPSpec;
import javamop.parser.ast.mopspec.PropertyAndHandlers;
import javamop.util.MOPException;

import java.util.Map;

/**
 * Sibling of {@link AspectJCode} that, instead of emitting the textual {@code .aj} file, produces a
 * structured JSON descriptor describing all pointcuts, advices, parameters and monitor calls.
 *
 * <p>Consumed by {@code prototipo-dexlib2} ({@code descriptor-reader} module) to drive DEX-native
 * bytecode weaving without needing to parse AspectJ source.
 */
public class AspectJDescriptor {

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .enable(SerializationFeature.INDENT_OUTPUT);

    private final String name;
    private final CombinedAspect aspect;
    private final MOPSpecFile mopSpecFile;

    /**
     * Build the descriptor from the same inputs as {@link AspectJCode}.
     *
     * @param name        The aspect short name (e.g. {@code "MultiSpec_1"}).
     * @param mopSpecFile The specification tree.
     */
    public AspectJDescriptor(String name, MOPSpecFile mopSpecFile) throws MOPException {
        this.name = name;
        this.mopSpecFile = mopSpecFile;
        boolean versionedStack = false;
        for (JavaMOPSpec mopSpec : mopSpecFile.getSpecs()) {
            for (PropertyAndHandlers prop : mopSpec.getPropertiesAndHandlers()) {
                versionedStack |= prop.getVersionedStack();
            }
        }
        this.aspect = new CombinedAspect(name, mopSpecFile, versionedStack);
    }

    /**
     * Produce the descriptor tree (unserialized).
     */
    public Map<String, Object> toTree() {
        return DescriptorWriter.buildAspect(name, aspect, mopSpecFile);
    }

    /**
     * Produce pretty-printed JSON.
     */
    public String toJson() throws MOPException {
        try {
            return MAPPER.writeValueAsString(toTree());
        } catch (Exception e) {
            throw new MOPException("Failed to serialize aspect descriptor: " + e.getMessage());
        }
    }
}

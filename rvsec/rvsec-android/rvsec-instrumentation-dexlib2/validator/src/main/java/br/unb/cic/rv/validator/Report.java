package br.unb.cic.rv.validator;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Common JSON report shape used by every validator CLI subcommand.
 *
 * <p>The Python wrapper / CI reads this JSON as-is; the shape is stable
 * across layers so automation (e.g. comparing gate deltas between runs)
 * can count on identical top-level fields.
 */
public final class Report {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    public final String layer;
    public final boolean passed;
    public final String message;
    public final Map<String, Object> metrics;

    public Report(String layer, boolean passed, String message, Map<String, Object> metrics) {
        this.layer = layer;
        this.passed = passed;
        this.message = message;
        this.metrics = metrics == null ? new LinkedHashMap<>() : new LinkedHashMap<>(metrics);
    }

    public void write(Path out) throws IOException {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("layer", layer);
        body.put("passed", passed);
        body.put("message", message);
        body.put("metrics", metrics);
        Files.createDirectories(out.getParent());
        MAPPER.writerWithDefaultPrettyPrinter().writeValue(out.toFile(), body);
    }

    public int exitCode() {
        return passed ? 0 : 1;
    }
}

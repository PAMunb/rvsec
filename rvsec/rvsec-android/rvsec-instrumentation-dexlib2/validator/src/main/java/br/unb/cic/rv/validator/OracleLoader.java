package br.unb.cic.rv.validator;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

/**
 * Loads every {@code *-oracle.yaml} under a directory and enforces the
 * minimum-count gate declared by INV-INS-22.
 *
 * <p>The YAML schema is intentionally simple (no external dep): each file
 * is read as raw text; the {@code name:} top-level key identifies the
 * oracle. Structural validation lives in {@code TraceComparator} which
 * actually evaluates each oracle against captured traces.
 *
 * <p>Gate: at least 3 oracles must be present, covering disjoint profiles
 * (Java pre-R8, Kotlin/R8, multidex real-world). The loader does not
 * enforce profile diversity at this level; that's documented in
 * {@code LIMITATIONS.md} and validated by visual review during Phase-5
 * preparation.
 */
public final class OracleLoader {

    /** Minimum oracle count for the Layer-3 / Layer-4 gate (INV-INS-22). */
    public static final int MINIMUM_ORACLES = 3;

    private OracleLoader() {}

    public static LoadResult load(Path oracleDir) throws IOException {
        List<Path> files = new ArrayList<>();
        if (Files.isDirectory(oracleDir)) {
            try (Stream<Path> ls = Files.list(oracleDir)) {
                ls.filter(Files::isRegularFile)
                  .filter(p -> p.getFileName().toString().endsWith("-oracle.yaml"))
                  .sorted()
                  .forEach(files::add);
            }
        }
        return new LoadResult(oracleDir, files);
    }

    public static Report report(LoadResult loaded) {
        boolean passed = loaded.files.size() >= MINIMUM_ORACLES;
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("oracleDir", loaded.dir.toString());
        metrics.put("oracleCount", loaded.files.size());
        metrics.put("oracleNames", loaded.files.stream()
                .map(p -> p.getFileName().toString())
                .toList());
        String msg = passed
                ? "≥" + MINIMUM_ORACLES + " oracles present (INV-INS-22 satisfied)"
                : "only " + loaded.files.size() + " oracle(s) present; "
                        + "INV-INS-22 requires ≥" + MINIMUM_ORACLES
                        + " — see validator/oracles/";
        return new Report("oracle-loader", passed, msg, metrics);
    }

    public record LoadResult(Path dir, List<Path> files) {}
}

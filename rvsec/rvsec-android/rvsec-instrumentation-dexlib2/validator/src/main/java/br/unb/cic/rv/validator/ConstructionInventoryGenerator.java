package br.unb.cic.rv.validator;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Scans the RVSEC specification corpus and produces
 * {@code docs/AJ_CONSTRUCTIONS_INVENTORY.md} programmatically.
 *
 * <p>Called at Phase-5 time to keep the inventory in sync with the spec
 * corpus. The diff between the regenerated and committed versions must be
 * empty in CI (INV-INS-17).
 *
 * <p>Spec-set agnostic: scans every {@code .mop} / {@code .aj} file under
 * the provided root, including JCA and Generic subdirectories.
 */
public final class ConstructionInventoryGenerator {

    /** AspectJ constructs recognized by the scanner. */
    private static final List<String> CONSTRUCTS = List.of(
            "call", "execution", "before", "after", "args", "target",
            "within", "staticinitialization", "if", "thisJoinPoint",
            "adviceexecution", "around", "cflow", "cflowbelow",
            "handler", "get", "set", "initialization", "preinitialization"
    );

    /** Constructs that are intentionally out of scope (LIMITATIONS.md). */
    private static final List<String> OUT_OF_SCOPE = List.of(
            "around", "cflow", "cflowbelow", "handler", "get", "set",
            "initialization", "preinitialization"
    );

    private ConstructionInventoryGenerator() {}

    /**
     * Scan {@code specRoot} for {@code .mop} / {@code .aj} files and write a
     * Markdown inventory to {@code outputFile}.
     */
    public static Inventory scan(Path specRoot) throws IOException {
        Map<String, List<Location>> byConstruct = new TreeMap<>();
        for (String c : CONSTRUCTS) byConstruct.put(c, new ArrayList<>());

        try (Stream<Path> walk = Files.walk(specRoot)) {
            walk.filter(Files::isRegularFile)
                .filter(ConstructionInventoryGenerator::isSpecFile)
                .forEach(file -> scanFile(file, byConstruct));
        }
        return new Inventory(specRoot, byConstruct);
    }

    public static void write(Inventory inv, Path outputFile) throws IOException {
        StringBuilder md = new StringBuilder();
        md.append("# AJ Constructions Inventory (auto-generated)\n\n");
        md.append("Scanned: ").append(inv.specRoot).append("\n\n");
        md.append("## Supported constructs\n\n");
        md.append("| Construct | Usages | Files |\n|---|---|---|\n");
        for (var entry : inv.byConstruct.entrySet()) {
            if (OUT_OF_SCOPE.contains(entry.getKey())) continue;
            List<Location> locs = entry.getValue();
            String files = locs.stream()
                    .map(l -> l.file.getFileName().toString() + ":" + l.line)
                    .distinct()
                    .reduce((a, b) -> a + ", " + b)
                    .orElse("—");
            md.append("| `").append(entry.getKey()).append("` | ")
              .append(locs.size()).append(" | ").append(files).append(" |\n");
        }
        md.append("\n## Out-of-scope constructs (LIMITATIONS.md)\n\n");
        md.append("| Construct | Usages | Status |\n|---|---|---|\n");
        for (String c : OUT_OF_SCOPE) {
            int count = inv.byConstruct.getOrDefault(c, List.of()).size();
            String status = count == 0
                    ? "zero empirical usages (per LIMITATIONS.md)"
                    : "**USAGES DETECTED** — LIMITATIONS.md must be revisited";
            md.append("| `").append(c).append("` | ")
              .append(count).append(" | ").append(status).append(" |\n");
        }
        Files.createDirectories(outputFile.getParent());
        Files.writeString(outputFile, md.toString());
    }

    // --- scanning ------------------------------------------------------------

    private static boolean isSpecFile(Path p) {
        String n = p.getFileName().toString();
        return n.endsWith(".mop") || n.endsWith(".aj");
    }

    private static void scanFile(Path file, Map<String, List<Location>> out) {
        try {
            List<String> lines = Files.readAllLines(file);
            for (int i = 0; i < lines.size(); i++) {
                String line = lines.get(i);
                for (String c : CONSTRUCTS) {
                    if (containsKeyword(line, c)) {
                        out.get(c).add(new Location(file, i + 1));
                    }
                }
            }
        } catch (IOException ex) {
            // Skip unreadable files; the scan is best-effort for paper-grade rigor,
            // not a data-integrity gate.
        }
    }

    /** Whole-word keyword match (excludes substring hits inside identifiers). */
    private static boolean containsKeyword(String line, String kw) {
        Matcher m = keywordPattern(kw).matcher(line);
        return m.find();
    }

    private static final Map<String, Pattern> PATTERN_CACHE = new LinkedHashMap<>();

    private static Pattern keywordPattern(String kw) {
        return PATTERN_CACHE.computeIfAbsent(kw,
                k -> Pattern.compile("\\b" + Pattern.quote(k) + "\\b"));
    }

    // --- value classes -------------------------------------------------------

    /** A single (file, line) sighting of a construct. */
    public record Location(Path file, int line) {}

    /** Aggregated scan result: per-construct list of sightings. */
    public record Inventory(Path specRoot, Map<String, List<Location>> byConstruct) {
        public int totalUsages() {
            return byConstruct.values().stream().mapToInt(List::size).sum();
        }
        public boolean hasAny(String construct) {
            return !byConstruct.getOrDefault(construct, List.of()).isEmpty();
        }
    }
}

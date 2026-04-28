package br.unb.cic.rv.validator;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Enforces INV-INS-17: every AspectJ construct in
 * {@code docs/AJ_CONSTRUCTIONS_INVENTORY.md} MUST appear either in
 * {@code docs/AJ_TO_DEXLIB2_MAPPING.md} (with a test reference) or in
 * {@code docs/LIMITATIONS.md} (with rationale). A construct present in the
 * inventory but absent from both MUST fail the check.
 *
 * <p>The check is lightweight: it grep-scans the three markdown files for
 * construct names (backtick-wrapped) and computes set membership. The CLI
 * wrapper emits a {@link Report} and returns exit code 0 when the mapping
 * is closed.
 */
public final class FeatureMappingChecker {

    private FeatureMappingChecker() {}

    public static Report check(Path inventoryMd, Path mappingMd, Path limitationsMd)
            throws IOException {
        Set<String> inInventory = extractConstructs(inventoryMd);
        Set<String> inMapping = extractConstructs(mappingMd);
        Set<String> inLimitations = extractConstructs(limitationsMd);

        Set<String> unmapped = new LinkedHashSet<>(inInventory);
        unmapped.removeAll(inMapping);
        unmapped.removeAll(inLimitations);

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("inventoryCount", inInventory.size());
        metrics.put("mappingCount", inMapping.size());
        metrics.put("limitationsCount", inLimitations.size());
        metrics.put("unmapped", unmapped);

        boolean passed = unmapped.isEmpty();
        String msg = passed
                ? "every inventory construct has mapping or limitation entry"
                : "unmapped constructs (INV-INS-17 violation): " + unmapped;
        return new Report("feature-mapping", passed, msg, metrics);
    }

    /** Extract construct names (backtick-wrapped, whole words) from a markdown file. */
    private static Set<String> extractConstructs(Path md) throws IOException {
        Set<String> out = new LinkedHashSet<>();
        if (!Files.isRegularFile(md)) return out;
        String body = Files.readString(md);
        // The docs write constructs as `call`, `execution`, etc.
        for (String c : KNOWN) {
            if (body.contains("`" + c + "`") || body.contains("`" + c + "(")
                    || body.contains("`" + c + "+`")) {
                out.add(c);
            }
        }
        return out;
    }

    /** Every construct name the docs may reference. */
    private static final List<String> KNOWN = List.of(
            "call", "execution", "before", "after", "args", "target",
            "within", "!within", "staticinitialization", "if", "thisJoinPoint",
            "adviceexecution", "around", "cflow", "cflowbelow",
            "handler", "get", "set", "initialization", "preinitialization",
            "after() returning", "after() throwing"
    );
}

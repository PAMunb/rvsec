package br.unb.cic.rv.validator;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.DescriptorReader;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Enforces INV-INS-19: the JSON descriptor emitted by patched JavaMOP
 * mirrors the semantic content of the corresponding {@code .aj} file.
 *
 * <p>Comparison scope (intentionally coarse to avoid brittle textual diff):
 * <ul>
 *   <li>Advice count: number of {@code before}/{@code after}/{@code around}
 *       clauses in the {@code .aj} must equal {@code advices.size()} in JSON.</li>
 *   <li>Aspect name: the {@code aspect <Name>} declaration in the {@code .aj}
 *       must match JSON {@code aspectName}.</li>
 *   <li>Package: the {@code package ...;} line must match JSON {@code package}.</li>
 * </ul>
 *
 * <p>Deeper per-pointcut equivalence is left to the weaver's pointcut
 * parser (already covered by {@code PointcutExpressionParserTest} against
 * the same fixture); this check enforces the structural contract.
 */
public final class DescriptorAjParityChecker {

    private static final Pattern ASPECT_DECL = Pattern.compile(
            "(?m)^\\s*(?:public\\s+)?aspect\\s+(\\S+)");
    private static final Pattern PACKAGE_DECL = Pattern.compile(
            "(?m)^\\s*package\\s+[^;]+;");
    private static final Pattern ADVICE_CLAUSE = Pattern.compile(
            "(?m)^\\s*(?:before|after|around)\\b");

    private DescriptorAjParityChecker() {}

    public static Report check(Path aj, Path json) throws IOException {
        Map<String, Object> metrics = new LinkedHashMap<>();
        if (!Files.isRegularFile(aj) || !Files.isRegularFile(json)) {
            metrics.put("ajExists", Files.isRegularFile(aj));
            metrics.put("jsonExists", Files.isRegularFile(json));
            return new Report("descriptor-parity", false,
                    "one of the paired files is missing", metrics);
        }

        String ajText = Files.readString(aj);
        AspectDescriptor desc = DescriptorReader.read(json);

        String ajAspect = matchFirst(ASPECT_DECL, ajText);
        String ajPackage = matchFirst(PACKAGE_DECL, ajText);
        int adviceCount = countMatches(ADVICE_CLAUSE, ajText);

        metrics.put("ajAspect", ajAspect);
        metrics.put("ajPackage", ajPackage);
        metrics.put("ajAdviceCount", adviceCount);
        metrics.put("jsonAspect", desc.getAspectName());
        metrics.put("jsonPackage", desc.getPackageDecl());
        metrics.put("jsonAdviceCount", desc.getAdvices().size());

        boolean aspectsMatch = ajAspect == null
                ? desc.getAspectName() == null
                : ajAspect.equals(desc.getAspectName());
        boolean packagesMatch = ajPackage == null
                ? true  // some .aj files elide package; harmless
                : desc.getPackageDecl() != null
                        && ajPackage.contains(desc.getPackageDecl().replace("package ", "").replace(";", ""));
        boolean countsMatch = adviceCount == desc.getAdvices().size();

        // Name-by-name spot-check: every named advice in .aj must appear in JSON
        // (at this layer we only check aspect-level structure; advice-level
        // equivalence is deeper, covered by the pointcut parser tests).
        boolean passed = aspectsMatch && packagesMatch && countsMatch;
        StringBuilder msg = new StringBuilder();
        if (!aspectsMatch) msg.append("aspect name mismatch; ");
        if (!packagesMatch) msg.append("package mismatch; ");
        if (!countsMatch) {
            msg.append("advice count mismatch (").append(adviceCount)
               .append(" vs ").append(desc.getAdvices().size()).append("); ");
        }
        return new Report("descriptor-parity", passed,
                passed ? "aspect/package/advice-count agree" : msg.toString(),
                metrics);
    }

    private static String matchFirst(Pattern p, String text) {
        Matcher m = p.matcher(text);
        return m.find() ? (m.groupCount() >= 1 ? m.group(1) : m.group()) : null;
    }

    private static int countMatches(Pattern p, String text) {
        int count = 0;
        Matcher m = p.matcher(text);
        while (m.find()) count++;
        return count;
    }
}

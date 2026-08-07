package br.unb.cic.rv.validator;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Contract test for INV-INS-106: no component of the validator may attribute a
 * woven artefact to a specification by reading only the first element of
 * {@code monitorCalls}.
 *
 * <p>The invariant exists because an instrument that shares the premise of a
 * defect cannot certify its repair. A JavaMOP advice fused from N events
 * carries N monitor calls; {@code BaksmaliDiffer} used to bind a wrapper to
 * {@code monitorCalls.get(0)}'s spec, which is the same "an advice has one
 * monitor call" assumption the inline emission path makes. With it in place
 * the static oracle would report the same hook recall whether or not the
 * weaver truncates.
 *
 * <p>This is a source scan rather than a list of line numbers on purpose: the
 * five known sites were found by inspection, and inspection is exactly what
 * missed them for fifteen months.
 *
 * <p>The emitter sources carry the same premise today and are repaired in the
 * emission group; the scan over {@code advice-emitter} lands with V0 as
 * red evidence, since INV-INS-108 requires it to be seen failing against the
 * unrepaired weaver first.
 */
class MonitorCallsPremiseContractTest {

    /** Direct form: {@code advice.getMonitorCalls().get(0)}. */
    private static final Pattern DIRECT =
            Pattern.compile("getMonitorCalls\\(\\)\\s*\\.\\s*get\\(\\s*0\\s*\\)");

    /** A local assigned from {@code getMonitorCalls()}, later read with {@code .get(0)}. */
    private static final Pattern ASSIGNED =
            Pattern.compile("(\\w+)\\s*=\\s*[\\w.]*\\bgetMonitorCalls\\(\\)");

    @Test
    void noValidatorSourceReadsOnlyTheFirstMonitorCall() throws IOException {
        List<String> offenders = scan(moduleDir().resolve("src/main/java"));
        assertTrue(offenders.isEmpty(),
                "INV-INS-106: the validator must attribute using every monitor call, "
                        + "not the first. Offending sites:\n  " + String.join("\n  ", offenders));
    }

    /**
     * Every {@code .java} under {@code root} that reduces {@code monitorCalls}
     * to its first element, as {@code <file>:<line>: <text>}.
     */
    static List<String> scan(Path root) throws IOException {
        List<String> offenders = new ArrayList<>();
        if (!Files.isDirectory(root)) {
            throw new IllegalStateException("source root not found: " + root.toAbsolutePath()
                    + " — the scan silently passing on a wrong path would be worse than failing");
        }
        try (Stream<Path> files = Files.walk(root)) {
            for (Path java : files.filter(p -> p.toString().endsWith(".java")).toList()) {
                String text = Files.readString(java);
                List<String> locals = new ArrayList<>();
                Matcher assigned = ASSIGNED.matcher(text);
                while (assigned.find()) locals.add(assigned.group(1));

                Pattern indirect = locals.isEmpty() ? null : Pattern.compile(
                        "\\b(" + String.join("|", locals) + ")\\s*\\.\\s*get\\(\\s*0\\s*\\)");

                String[] lines = text.split("\n", -1);
                for (int i = 0; i < lines.length; i++) {
                    boolean hit = DIRECT.matcher(lines[i]).find()
                            || (indirect != null && indirect.matcher(lines[i]).find());
                    if (hit) {
                        offenders.add(java.getFileName() + ":" + (i + 1) + ": " + lines[i].trim());
                    }
                }
            }
        }
        return offenders;
    }

    /**
     * The module directory. Surefire runs with the module as working directory,
     * but resolving explicitly keeps the scan honest if that ever changes.
     */
    static Path moduleDir() {
        Path cwd = Path.of("").toAbsolutePath();
        return cwd.getFileName().toString().equals("validator") ? cwd : cwd.resolve("validator");
    }
}

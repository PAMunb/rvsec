package br.unb.cic.rvsec.crysl.crysl.cli;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * {@code lower} over one real specification, end to end through {@link ConformanceCli#run}.
 *
 * <p>It runs in CI. The corpus it reads is the sibling {@code rvsec-mop} module's working tree,
 * which is part of this checkout — unlike the CrySL oracle, which is a separate repository — so
 * nothing here needs the {@code oracle-dependent} tag.
 *
 * <p>The specification is <em>copied</em> into a temporary directory before the command sees it, and
 * the command writes only under {@code --out}. That is INV-CONF-12 exercised rather than asserted:
 * if {@code lower} ever wrote next to what it read, this test's corpus directory would end up with
 * a file in it, and the last assertion says it does not.
 */
class LowerSmokeTest {

    /** The specification corpus, in the sibling module's working tree. */
    private static final Path CORPUS = Paths.get("..", "..", "rvsec-mop", "src", "main",
            "resources", "jca_android").normalize();

    /** One specification, chosen because M0 does not refuse it and its lift is exercised widely. */
    private static final String SPECIFICATION = "MessageDigestSpec.mop";

    private final ByteArrayOutputStream out = new ByteArrayOutputStream();
    private final ByteArrayOutputStream err = new ByteArrayOutputStream();

    @Test
    @DisplayName("lower writes a .mop and a gate verdict, and exits 0 having measured something")
    void test_lower_runs_the_gate_and_says_what_it_found(@TempDir Path root) throws IOException {
        Path mopDir = Files.createDirectories(root.resolve("corpus"));
        Files.copy(CORPUS.resolve(SPECIFICATION), mopDir.resolve(SPECIFICATION),
                StandardCopyOption.REPLACE_EXISTING);
        Path outputDir = root.resolve("out");

        ExitCode code = ConformanceCli.run(new String[] {
            "lower",
            "--mop-dir", mopDir.toString(),
            "--corpus", "jca_android",
            "--commit", "6192b57a",
            "--out", outputDir.toString(),
        }, new PrintStream(out, true, StandardCharsets.UTF_8),
                new PrintStream(err, true, StandardCharsets.UTF_8));

        String stdout = out.toString(StandardCharsets.UTF_8);
        assertEquals(ExitCode.OK, code, "stderr was: " + err.toString(StandardCharsets.UTF_8));

        assertTrue(stdout.contains("MessageDigestSpec"),
                "the verdict names the specification it is about; got: " + stdout);
        assertTrue(stdout.contains("Layer 1"),
                "and says what decided it, which is Layer 1 and not the round trip; got: " + stdout);
        assertTrue(stdout.contains("Layer 2 did not run"),
                "no --rules-dir was given, so the product-search evidence is absent and the run "
                        + "says so rather than leaving the reader to assume it passed; got: "
                        + stdout);

        assertEquals(List.of(SPECIFICATION), lowered(outputDir),
                "the lowered specification is written under --out, which is the whole output of "
                        + "this command");
        assertEquals(List.of(SPECIFICATION), lowered(mopDir),
                "and nothing was written beside what was read (INV-CONF-12): the corpus directory "
                        + "still holds exactly the one file that was copied into it");
    }

    private static List<String> lowered(Path directory) throws IOException {
        try (Stream<Path> entries = Files.list(directory)) {
            return entries.map(path -> path.getFileName().toString()).sorted().toList();
        }
    }
}

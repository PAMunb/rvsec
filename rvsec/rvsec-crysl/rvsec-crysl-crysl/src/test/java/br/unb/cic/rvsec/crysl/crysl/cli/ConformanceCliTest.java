package br.unb.cic.rvsec.crysl.crysl.cli;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The command line's contract: what it accepts, what it refuses, and which exit code each refusal
 * produces.
 *
 * <p>These read no corpus and touch no oracle — every path they use is a temporary directory — so
 * they run in CI. That is deliberate: the exit-code mapping is the part of the component a caller
 * automates against, and a mapping that is only exercised on one machine is a contract in name
 * only.
 *
 * <p>All three subcommands are wired, and what they are checked for here is one rule: a corpus with
 * nothing in it is refused rather than measured, because a report of zero rows that exits {@code 0}
 * is the green this component was built to stop producing. That they measure something when there
 * <em>is</em> something to measure is checked by {@code LowerSmokeTest}, by {@code CompareSmokeIT}
 * and, for the gate, by {@code CalibrationGateTest} — all three against the real corpora, which is
 * why they are not here.
 */
class ConformanceCliTest {

    private final ByteArrayOutputStream out = new ByteArrayOutputStream();
    private final ByteArrayOutputStream err = new ByteArrayOutputStream();

    private ExitCode run(String... args) {
        return ConformanceCli.run(args,
                new PrintStream(out, true, StandardCharsets.UTF_8),
                new PrintStream(err, true, StandardCharsets.UTF_8));
    }

    private String stderr() {
        return err.toString(StandardCharsets.UTF_8);
    }

    /** A directory with the four inputs {@code compare} requires, all readable. */
    private static String[] completeCompare(Path root) throws IOException {
        Path mopDir = Files.createDirectories(root.resolve("jca_android"));
        Path rulesDir = Files.createDirectories(root.resolve("CrySL-Rules"));
        Path alphabet = Files.writeString(root.resolve("order_alphabet_map.csv"), "spec,event\n");
        Path androidJar = Files.writeString(root.resolve("android.jar"), "not a real jar\n");
        return new String[] {
            "compare",
            "--mop-dir", mopDir.toString(),
            "--corpus", "jca_android",
            "--commit", "0123456789abcdef",
            "--rules-dir", rulesDir.toString(),
            "--oracle-commit", "f2f4d3b",
            "--alphabet", alphabet.toString(),
            "--android-jar", androidJar.toString(),
            "--out", root.resolve("out").toString(),
        };
    }

    @Test
    @DisplayName("no subcommand is a usage error, not a silent no-op")
    void test_no_subcommand() {
        assertEquals(ExitCode.USAGE, run());
    }

    @Test
    @DisplayName("an unknown subcommand is a usage error")
    void test_unknown_subcommand() {
        assertEquals(ExitCode.USAGE, run("measure"));
    }

    @Test
    @DisplayName("compare without --commit is refused; there is no default and no detection from git")
    void test_compare_requires_an_explicit_commit(@TempDir Path root) throws IOException {
        String[] complete = completeCompare(root);
        String[] withoutCommit = Arrays.stream(complete)
                .filter(argument -> !argument.equals("--commit") && !argument.equals("0123456789abcdef"))
                .toArray(String[]::new);

        assertEquals(ExitCode.USAGE, run(withoutCommit),
                "the caller states which corpus state is being measured. Inferring it from the "
                        + "working tree would make a wrong stamp look exactly like a right one");
        assertTrue(stderr().contains("--commit"), "the refusal must name the missing option; got: "
                + stderr());
    }

    @Test
    @DisplayName("compare without --oracle-commit is refused: two repositories, two stamps")
    void test_compare_requires_the_oracle_commit(@TempDir Path root) throws IOException {
        String[] complete = completeCompare(root);
        String[] withoutOracleCommit = Arrays.stream(complete)
                .filter(argument -> !argument.equals("--oracle-commit") && !argument.equals("f2f4d3b"))
                .toArray(String[]::new);

        assertEquals(ExitCode.USAGE, run(withoutOracleCommit),
                "the .mop corpus and the rules are two git repositories; one commit field cannot "
                        + "stamp the run (INV-CONF-01)");
    }

    @Test
    @DisplayName("there is no second-oracle option to pass")
    void test_no_two_oracle_mode(@TempDir Path root) throws IOException {
        String[] complete = completeCompare(root);
        String[] withSecondOracle = Arrays.copyOf(complete, complete.length + 2);
        withSecondOracle[complete.length] = "--oracle";
        withSecondOracle[complete.length + 1] = "api30";

        assertEquals(ExitCode.USAGE, run(withSecondOracle),
                "the generated api30 corpus is not an oracle and there is no mode that offers it; "
                        + "an --oracle selector is what would make that mistake available again");
    }

    @Test
    @DisplayName("a missing input directory is a CorpusReadError, not a corpus that refused everything")
    void test_missing_mop_dir_is_a_corpus_read_error(@TempDir Path root) throws IOException {
        String[] complete = completeCompare(root);
        complete[2] = root.resolve("does-not-exist").toString();

        assertEquals(ExitCode.CORPUS_READ_ERROR, run(complete));
        assertTrue(stderr().contains("does-not-exist"),
                "the message must name the path that was tried; got: " + stderr());
    }

    @Test
    @DisplayName("a missing oracle directory is a CorpusReadError")
    void test_missing_rules_dir_is_a_corpus_read_error(@TempDir Path root) throws IOException {
        String[] complete = completeCompare(root);
        complete[8] = root.resolve("no-rules-here").toString();

        assertEquals(ExitCode.CORPUS_READ_ERROR, run(complete));
    }

    @Test
    @DisplayName("compare over a directory with no .mop file is refused, not measured as empty")
    void test_compare_refuses_a_corpus_with_no_specification(@TempDir Path root)
            throws IOException {
        ExitCode code = run(completeCompare(root));

        assertEquals(ExitCode.CORPUS_READ_ERROR, code);
        assertNotEquals(ExitCode.OK, code,
                "every path is readable and the directory holds no *.mop file, so the run would "
                        + "publish a report of zero rows and exit 0 - the one outcome this "
                        + "component exists to stop producing");
        assertTrue(stderr().contains("*.mop"),
                "the refusal must say what the directory is missing rather than only that it is "
                        + "unusable; got: " + stderr());
    }

    @Test
    @DisplayName("lower over a directory with no .mop file is refused for the same reason")
    void test_lower_refuses_a_corpus_with_no_specification(@TempDir Path root) throws IOException {
        Path mopDir = Files.createDirectories(root.resolve("jca"));

        assertEquals(ExitCode.CORPUS_READ_ERROR, run("lower",
                "--mop-dir", mopDir.toString(),
                "--corpus", "jca",
                "--commit", "deadbeef",
                "--out", root.resolve("out").toString()),
                "a gate that ran over no file would report a clean pass");
        assertTrue(stderr().contains("*.mop"), "got: " + stderr());
    }

    @Test
    @DisplayName("calibrate refuses an unreadable corpus before it measures anything")
    void test_calibrate_refuses_an_unreadable_corpus(@TempDir Path root) throws IOException {
        Path mopRoot = Files.createDirectory(root.resolve("corpora"));

        // The five corpus directories do not exist under it, so the first one the gate reaches is
        // unreadable. A gate that answered "0 of 0, reproduced" here would be the exact failure the
        // component exists to remove: a green with nothing behind it.
        assertEquals(ExitCode.CORPUS_READ_ERROR, run("calibrate",
                "--mop-root", mopRoot.toString(),
                "--rules-dir", root.toString(),
                "--commit", "deadbeef",
                "--oracle-commit", "cafebabe"));
        assertTrue(stderr().contains("corpus"), "got: " + stderr());
    }

    @Test
    @DisplayName("exit codes: 0 means measured and published, and no two failures share a code")
    void test_exit_codes_are_distinct_and_ok_is_zero() {
        assertEquals(0, ExitCode.OK.code());
        Set<Integer> codes = new HashSet<>();
        for (ExitCode code : ExitCode.values()) {
            assertTrue(codes.add(code.code()),
                    code + " reuses an exit code already taken; a caller could not tell the two "
                            + "apart");
        }
    }
}

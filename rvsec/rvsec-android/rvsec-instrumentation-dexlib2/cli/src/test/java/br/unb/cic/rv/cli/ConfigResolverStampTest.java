package br.unb.cic.rv.cli;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import picocli.CommandLine;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Resolution of {@code --stamp-handlers} into {@link EffectiveConfig#stampHandlers}
 * (INV-INS-174): either form of the option wins, and with neither form the
 * value comes from {@code RVSEC_STAMP_HANDLERS}.
 *
 * <p>The case with the variable set is not covered here: a JUnit test cannot
 * set the environment of its own JVM, so the absent-option case is checked
 * against whatever the test JVM carries, and the variable itself is exercised
 * by real {@code instr-cli} runs.
 *
 * <p>{@code --android-jar} is given only because {@link ConfigResolver#resolve}
 * requires it; the path is never opened.
 */
class ConfigResolverStampTest {

    /** Parses {@code args} as the command line would and resolves the root command. */
    private static InstrumentationCli parse(String... args) {
        InstrumentationCli cli = new InstrumentationCli();
        new CommandLine(cli).parseArgs(args);
        return cli;
    }

    private static boolean resolveStamp(String... args) {
        return ConfigResolver.resolve(parse(args)).stampHandlers();
    }

    @Test
    void stampHandlersTurnsTheStampOn() {
        assertTrue(resolveStamp("instrument", "app.apk",
                "--android-jar", "android.jar", "--stamp-handlers"));
    }

    @Test
    void noStampHandlersTurnsTheStampOff() {
        assertFalse(resolveStamp("instrument", "app.apk",
                "--android-jar", "android.jar", "--no-stamp-handlers"));
    }

    /**
     * The option has no default, so an absent option reaches
     * {@link ConfigResolver} as {@code null}; that is what lets the resolver
     * tell "not given" from {@code --no-stamp-handlers}.
     */
    @Test
    void absentOptionParsesToNullAndFallsBackToTheEnvironment() {
        InstrumentationCli cli = parse("instrument", "app.apk", "--android-jar", "android.jar");

        assertNull(cli.stampHandlers);
        assertEquals(Boolean.parseBoolean(System.getenv("RVSEC_STAMP_HANDLERS")),
                ConfigResolver.resolve(cli).stampHandlers());
    }

    /**
     * The Python wrapper builds the arguments of both subcommands through one
     * method and places the option after the subcommand name, so both
     * subcommands must accept it in that position.
     */
    @ParameterizedTest
    @ValueSource(strings = {"instrument", "batch"})
    void bothSubcommandsAcceptTheOptionInBothForms(String subcommand) {
        assertTrue(resolveStamp(subcommand, "input",
                "--android-jar", "android.jar", "--stamp-handlers"));
        assertFalse(resolveStamp(subcommand, "input",
                "--android-jar", "android.jar", "--no-stamp-handlers"));
    }
}

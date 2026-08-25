package br.unb.cic.rvsec.crysl.mop;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import javamop.parser.ast.MOPSpecFile;
import javamop.parser.ast.visitor.DumpVisitor;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * What {@link MopLowerer} promises about the text it writes.
 *
 * <p>Every test here reads a corpus file and writes only into a {@code @TempDir}, which is
 * INV-CONF-12 held by construction rather than by discipline: there is no path in these tests from
 * a corpus directory to a write.
 */
class MopLowererTest {

    private static MopLift lift(String corpus, String name) throws Exception {
        return new MopLifter().read(Corpora.file(corpus, name), Corpora.version(corpus));
    }

    @Test
    @DisplayName("11.1: the text is what DumpVisitor printed from a MOPSpecFile, never a builder")
    void test_the_text_comes_from_the_technology_s_own_writer() throws Exception {
        MopLift lift = lift("jca", "PBEKeySpecSpec.mop");
        MOPSpecFile tree = new MopLowerer().specFileOf(lift);

        assertEquals(1, tree.getSpecs().size(),
                "the lowerer builds one specification per model, as SpecModel describes one");
        DumpVisitor visitor = new DumpVisitor();
        tree.accept(visitor, null);
        assertEquals(visitor.getSource(), new MopLowerer().lower(lift),
                "lower() must be exactly what DumpVisitor renders from the tree the lowerer built. "
                        + "If these ever differ, something is assembling text beside the AST, and a "
                        + "string builder can emit .mop text no MOPSpecFile could represent");
    }

    @Test
    @DisplayName("11.8: comments are discarded, and the loss is declared rather than discovered")
    void test_comments_are_discarded() throws Exception {
        Path source = Corpora.file("jca", "PBEKeySpecSpec.mop");
        String original = Files.readString(source);
        assertTrue(original.contains("A JavaMOP specification of the correct usage"),
                "this test needs a file with prose in it; the fixture has stopped being one");

        String lowered = new MopLowerer().lower(lift("jca", "PBEKeySpecSpec.mop"));
        assertFalse(lowered.contains("A JavaMOP specification of the correct usage"),
                "the file's prose survived the lowering");
        assertFalse(lowered.contains("Crypto-API-Rules"),
                "the file's @see link survived the lowering");
        assertTrue(MopLowerer.COMMENTS_ARE_DISCARDED.contains("comments are discarded on lower"),
                "the loss has to be stated on the class, so a reader meets it before the diff does");
    }

    @Test
    @DisplayName("the formula comes out as fsm whatever it went in as, and says why")
    void test_the_formula_is_written_as_an_automaton() throws Exception {
        String source = Files.readString(Corpora.file("jca", "PBEKeySpecSpec.mop"));
        assertTrue(source.contains("ere : c1 c2"), "the fixture has stopped being an ere file");

        String lowered = new MopLowerer().lower(lift("jca", "PBEKeySpecSpec.mop"));
        assertTrue(lowered.contains("fsm:"),
                "an ere is lowered as fsm, because what the lift retains is an automaton");
        assertFalse(lowered.contains("ere:"), "no ere is reconstructed; h⁻¹(L) cannot be run "
                + "backwards, which is what D-20 made true and what FORMULA_SYNTAX_RULE records");
        assertTrue(MopLowerer.FORMULA_SYNTAX_RULE.contains("D-20"));
    }

    @Test
    @DisplayName("INV-CONF-12: the lowerer writes into the directory it was given and nowhere else")
    void test_the_corpus_is_never_written(@TempDir Path out) throws Exception {
        Path source = Corpora.file("jca", "SecretKeySpec.mop");
        byte[] before = Files.readAllBytes(source);

        Path written = new MopLowerer().lowerTo(lift("jca", "SecretKeySpec.mop"), out);

        assertTrue(written.startsWith(out), "the lowered file landed outside the given directory: "
                + written.toAbsolutePath());
        assertEquals("SecretKeySpec.mop", written.getFileName().toString(),
                "the name must end in .mop: SpecExtractor consults Tool.isSpecFile and hands the "
                        + "parser an empty string for anything else");
        org.junit.jupiter.api.Assertions.assertArrayEquals(before, Files.readAllBytes(source),
                "the corpus file was modified");
    }

    @Test
    @DisplayName("a specification with no handler lowers with no property, and its language holds")
    void test_a_property_less_specification_keeps_its_language() throws Exception {
        MopLift before = lift("generic_new", "Collection_HashCode.mop");
        assertTrue(before.handlers().isEmpty(),
                "the fixture has stopped being one of the seventeen property-less files");

        String lowered = new MopLowerer().lower(before);
        assertFalse(lowered.contains("fsm:"), "a property with no handler cannot be written: the "
                + "grammar reads the formula until it meets an '@', so it would run to end of file");
    }

    @Test
    @DisplayName("11.2: the package documentation records why there is no crysl.lower")
    void test_the_absence_of_crysl_lower_is_recorded() throws Exception {
        Path documentation = Paths.get("src", "main", "java", "br", "unb", "cic", "rvsec", "crysl",
                "mop", "package-info.java");
        assertTrue(Files.exists(documentation), "the package documentation is missing: "
                + documentation.toAbsolutePath());
        String text = Files.readString(documentation);

        for (String required : List.of("crysl.lower", "no consumer", "ships no formatter",
                "MetaCrySL")) {
            assertTrue(text.contains(required), "the package documentation must record why "
                    + "crysl.lower does not exist, so a later reader does not treat its absence as "
                    + "an oversight and add four hundred lines of pretty-printer. Missing: "
                    + required);
        }
    }
}

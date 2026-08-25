package br.unb.cic.rvsec.crysl.core.emit;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * {@link StampedTable} is the choke point, checked over the compiled classes rather than by review.
 *
 * <p>The invariant it defends - INV-CONF-02, no table without its counting rule - is only worth
 * anything if there is no way round it. "Every emitter goes through StampedTable" as a convention
 * survives exactly until the first emitter that finds it convenient to open a {@code FileWriter}.
 * So the rule is structural: nothing in this package but {@code StampedTable} may reach the
 * filesystem or an output stream, which leaves handing text to {@code StampedTable.write} as the
 * only route from an aggregate to a file, and building a {@code StampedTable} - which demands a
 * counting rule - as the only route to that text.
 */
class EmitterChokePointTest {

    private static JavaClasses emitClasses;

    @BeforeAll
    static void importClasses() {
        // Production classes only: the tests of this package read the committed schemas and
        // assert over emitted files, which is reading, not a second way of publishing one.
        emitClasses = new ClassFileImporter()
                .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("br.unb.cic.rvsec.crysl.core.emit");
    }

    @Test
    @DisplayName("nothing but StampedTable writes: the choke point cannot be bypassed")
    void test_only_the_stamped_table_reaches_the_filesystem() {
        noClasses().that().resideInAPackage("..core.emit..")
                .and().doNotHaveSimpleName("StampedTable")
                .should().dependOnClassesThat()
                .haveFullyQualifiedName("java.nio.file.Files")
                .orShould().dependOnClassesThat().haveFullyQualifiedName("java.io.Writer")
                .orShould().dependOnClassesThat().haveFullyQualifiedName("java.io.FileWriter")
                .orShould().dependOnClassesThat().haveFullyQualifiedName("java.io.OutputStream")
                .orShould().dependOnClassesThat().haveFullyQualifiedName("java.io.PrintWriter")
                .orShould().dependOnClassesThat().haveFullyQualifiedName("java.io.PrintStream")
                .because("INV-CONF-02: StampedTable is the only route from an aggregate to a file, "
                        + "and it refuses a table that names no counting rule; an emitter able to "
                        + "open its own file could publish an unstamped table")
                .check(emitClasses);
    }
}

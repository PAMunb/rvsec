package br.unb.cic.rvsec.crysl.crysl;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noFields;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaCodeUnit;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.lang.ArchRule;
import crysl.parsing.CrySLModelReader;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * INV-CONF-04, made impossible rather than discouraged.
 *
 * <p>A {@code CrySLModelReader} accumulates {@code OBJECTS} scope across the rules it reads, so a
 * reader that outlives one rule turns the set of rules that load into a function of read order.
 * {@link CryslLiftOracleTest#test_inv_conf_04_order_invariance()} catches the symptom; these rules
 * catch the cause, and they catch it at the only two places a reader can escape a single rule's
 * scope.
 *
 * <p><strong>A field</strong> is how a reader survives between calls, so no field of this module may
 * hold one. <strong>A parameter</strong> is how a reader is handed in from outside, so no method or
 * constructor may accept one — that is the "no overload accepts a shared reader" half, and it is
 * also, in practice, the shape a sharing flag would take: whoever wants to reuse a reader has to
 * pass it somewhere. There is no configuration switch to check for, because there is no place to
 * put one.
 *
 * <p>This test reads no corpus, so it runs in CI.
 */
class NoSharedReaderArchTest {

    private static JavaClasses moduleClasses;

    @BeforeAll
    static void importModule() {
        moduleClasses = new ClassFileImporter()
                .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("br.unb.cic.rvsec.crysl.crysl");
    }

    @Test
    @DisplayName("INV-CONF-04: no field of the module holds a CrySLModelReader")
    void test_inv_conf_04_no_reader_is_held_in_a_field() {
        ArchRule rule = noFields().should().haveRawType(CrySLModelReader.class)
                .because("a reader that outlives one rule leaks OBJECTS scope between rules, and "
                        + "the set of rules that load becomes a function of read order "
                        + "(INV-CONF-04). A fresh reader is constructed inside CryslLifter.lift "
                        + "and discarded with the call.");
        rule.check(moduleClasses);
    }

    @Test
    @DisplayName("INV-CONF-04: no method or constructor accepts a CrySLModelReader")
    void test_inv_conf_04_no_reader_can_be_handed_in() {
        List<String> offenders = new ArrayList<>();
        for (JavaClass type : moduleClasses) {
            for (JavaCodeUnit codeUnit : type.getCodeUnits()) {
                boolean accepts = codeUnit.getRawParameterTypes().stream()
                        .anyMatch(parameter -> parameter.isAssignableTo(CrySLModelReader.class));
                if (accepts) {
                    offenders.add(codeUnit.getFullName());
                }
            }
        }
        assertTrue(offenders.isEmpty(),
                "these accept a CrySLModelReader from outside, which is how reader sharing gets "
                        + "reintroduced - a flag that turns non-determinism back on is a flag that "
                        + "will eventually be set: " + offenders);
    }

    @Test
    @DisplayName("INV-CONF-04: no method of the module returns a CrySLModelReader either")
    void test_inv_conf_04_no_reader_can_be_handed_out() {
        List<String> offenders = new ArrayList<>();
        for (JavaClass type : moduleClasses) {
            for (JavaCodeUnit codeUnit : type.getCodeUnits()) {
                if (codeUnit.getRawReturnType().isAssignableTo(CrySLModelReader.class)) {
                    offenders.add(codeUnit.getFullName());
                }
            }
        }
        assertTrue(offenders.isEmpty(),
                "a factory that hands a reader out is a reader with a lifetime longer than one "
                        + "rule, whoever holds it: " + offenders);
    }
}

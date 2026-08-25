package br.unb.cic.rvsec.crysl.core;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noFields;

import br.unb.cic.rvsec.crysl.core.model.Label;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaField;
import com.tngtech.archunit.core.domain.JavaParameterizedType;
import com.tngtech.archunit.core.domain.JavaType;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.lang.ArchCondition;
import com.tngtech.archunit.lang.ConditionEvents;
import com.tngtech.archunit.lang.SimpleConditionEvent;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * The two structural invariants of the model, checked over the compiled classes rather than by
 * review.
 *
 * <p>INV-CONF-03 forbids representing a specification as a map keyed by label. The rule is
 * expressible only because {@link Label} is a distinct type: over {@code Map<String, ?>} it would
 * be unenforceable, since {@code String} keys are pervasive and legitimate. Record components
 * compile to private final fields, so a record component of that shape is caught too.
 *
 * <p>The layering rule states what the three-module split exists for: the model module knows
 * neither parser. If {@code -core} ever depends on {@code javamop..} or {@code crysl..}, the split
 * has stopped buying anything.
 *
 * <p>The import covers the classes of this module. The two lifter modules are not on this module's
 * test classpath by construction - that is the layering the second rule asserts - so each of them
 * carries its own dependency discipline test instead.
 */
class ModelShapeArchTest {

    private static JavaClasses componentClasses;

    @BeforeAll
    static void importClasses() {
        componentClasses = new ClassFileImporter().importPackages("br.unb.cic.rvsec.crysl");
    }

    @Test
    @DisplayName("INV-CONF-03: no field is a Map keyed by Label")
    void test_inv_conf_03_no_map_keyed_by_label() {
        noFields().should(beAMapKeyedByLabel())
                .because("INV-CONF-03: events are an ordered List and order is an automaton over "
                        + "Signature; a Map<Label, ?> is the representation that loses declaration "
                        + "order and puts labels into the comparison alphabet")
                .check(componentClasses);
    }

    @Test
    @DisplayName("the model module depends on neither parser")
    void test_core_does_not_depend_on_either_parser() {
        noClasses().should().dependOnClassesThat()
                .resideInAnyPackage("javamop..", "crysl..", "de.darmstadt.tu.crossing..")
                .because("the model module is the one both lifters share; importing either parser "
                        + "here is the coupling the three-module split exists to prevent")
                .check(componentClasses);
    }

    private static ArchCondition<JavaField> beAMapKeyedByLabel() {
        return new ArchCondition<>("be a Map keyed by Label") {
            @Override
            public void check(JavaField field, ConditionEvents events) {
                boolean violated = false;
                if (field.getType() instanceof JavaParameterizedType parameterized
                        && parameterized.toErasure().isAssignableTo(Map.class)) {
                    List<JavaType> arguments = parameterized.getActualTypeArguments();
                    violated = !arguments.isEmpty()
                            && arguments.get(0).toErasure().getName().equals(Label.class.getName());
                }
                events.add(new SimpleConditionEvent(field, violated,
                        field.getFullName() + " is a Map keyed by Label"));
            }
        };
    }
}

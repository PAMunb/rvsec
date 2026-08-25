package br.unb.cic.rvsec.crysl.core.model;

import java.util.Objects;

/**
 * The name an event is declared under in a {@code .mop} specification, e.g. {@code g1} or
 * {@code initRandomSpec}.
 *
 * <p>A distinct type rather than a bare {@code String}, and that is the whole reason it exists.
 * INV-CONF-03 forbids representing a specification as a map from label to signatures; a rule stated
 * over {@code Map<String, ?>} would be unenforceable because {@code String} keys are pervasive and
 * legitimate, while a rule stated over {@code Map<Label, ?>} is machine-checkable.
 */
public record Label(String name) {

    public Label {
        Objects.requireNonNull(name, "Label.name is mandatory");
    }
}

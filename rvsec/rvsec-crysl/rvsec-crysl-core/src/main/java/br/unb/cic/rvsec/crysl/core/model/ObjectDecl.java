package br.unb.cic.rvsec.crysl.core.model;

import java.util.Objects;

/**
 * One entry of the {@code OBJECTS} section of a CrySL rule, or one declared parameter of a
 * {@code .mop} specification: a typed name the events and constraints refer to.
 *
 * @param type fully-qualified declared type
 * @param name the identifier the rule or specification binds it to
 */
public record ObjectDecl(String type, String name) {

    public ObjectDecl {
        Objects.requireNonNull(type, "ObjectDecl.type is mandatory");
        Objects.requireNonNull(name, "ObjectDecl.name is mandatory");
    }
}

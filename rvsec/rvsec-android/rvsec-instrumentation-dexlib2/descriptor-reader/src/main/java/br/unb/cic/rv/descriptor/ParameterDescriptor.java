package br.unb.cic.rv.descriptor;

/**
 * Jackson POJO for a single advice parameter's {@code type} and {@code name}, as
 * emitted in the JSON descriptor by patched JavaMOP.
 *
 * <p>Deserialized as part of {@link AdviceDescriptor}; consumed when building the
 * argument list for the monitor-invoke call the weaver injects at each advice site.
 */
public final class ParameterDescriptor {

    private String type;
    private String name;

    public ParameterDescriptor() {}

    public ParameterDescriptor(String type, String name) {
        this.type = type;
        this.name = name;
    }

    public String getType() { return type; }
    public void setType(String type) { this.type = type; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    @Override
    public String toString() {
        return type + " " + name;
    }
}

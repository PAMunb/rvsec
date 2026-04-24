package br.unb.cic.rv.descriptor;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Collections;
import java.util.List;

/**
 * A pointcut + advice pair (one declaration of
 * {@code pointcut X(...); before/after(...) {...}} in the generated .aj).
 */
public final class AdviceDescriptor {

    private String name;
    private String specName;
    private List<ParameterDescriptor> parameters = Collections.emptyList();

    /** {@code "before"}, {@code "after"}, or {@code "around"}. */
    private String position;
    /**
     * Kept as a first-class JSON field because JavaMOP's DescriptorWriter emits it
     * verbatim ({@code "isAround": false}); Jackson's default naming would map the
     * {@code boolean isAround} field to JSON property {@code "around"}, so we pin
     * the mapping explicitly to avoid a silent mismatch with the descriptor.
     */
    @JsonProperty("isAround")
    private boolean isAround;
    private String returnType;
    /** Non-null when advice is {@code after() returning(...)}; an empty list becomes null. */
    private List<ParameterDescriptor> returning;
    /** Non-null when advice is {@code after() throwing(...)}. */
    private List<ParameterDescriptor> throwing;
    /**
     * Raw pointcut expression as AspectJ source
     * (e.g. {@code call(public static Cipher Cipher.getInstance(String)) && args(transformation)}).
     */
    private String expression;
    private List<MonitorCallDescriptor> monitorCalls = Collections.emptyList();

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getSpecName() { return specName; }
    public void setSpecName(String specName) { this.specName = specName; }

    public List<ParameterDescriptor> getParameters() { return parameters; }
    public void setParameters(List<ParameterDescriptor> parameters) { this.parameters = parameters; }

    public String getPosition() { return position; }
    public void setPosition(String position) { this.position = position; }

    public boolean isAround() { return isAround; }
    public void setAround(boolean around) { isAround = around; }

    public String getReturnType() { return returnType; }
    public void setReturnType(String returnType) { this.returnType = returnType; }

    public List<ParameterDescriptor> getReturning() { return returning; }
    public void setReturning(List<ParameterDescriptor> returning) { this.returning = returning; }

    public List<ParameterDescriptor> getThrowing() { return throwing; }
    public void setThrowing(List<ParameterDescriptor> throwing) { this.throwing = throwing; }

    public String getExpression() { return expression; }
    public void setExpression(String expression) { this.expression = expression; }

    public List<MonitorCallDescriptor> getMonitorCalls() { return monitorCalls; }
    public void setMonitorCalls(List<MonitorCallDescriptor> calls) { this.monitorCalls = calls; }
}

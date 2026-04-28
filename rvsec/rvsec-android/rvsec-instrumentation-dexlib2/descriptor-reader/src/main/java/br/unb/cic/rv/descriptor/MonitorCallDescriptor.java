package br.unb.cic.rv.descriptor;

import java.util.Collections;
import java.util.List;

/**
 * A single call to the generated RuntimeMonitor for a matched join point
 * (e.g. {@code MultiSpec_1RuntimeMonitor.CipherSpec_g1Event(transformation, c)}).
 */
public final class MonitorCallDescriptor {

    /**
     * Fully-qualified target method reference as AspectJ source
     * (e.g. {@code "MultiSpec_1RuntimeMonitor.CipherSpec_g1Event"}).
     */
    private String method;
    private String specName;
    private String eventId;
    private String uniqueId;
    /** Ordered list of argument expressions (parameter names from the advice declaration). */
    private List<String> args = Collections.emptyList();
    /** Optional {@code @count(...)} condition; null when absent. */
    private String countCond;

    public String getMethod() { return method; }
    public void setMethod(String method) { this.method = method; }

    public String getSpecName() { return specName; }
    public void setSpecName(String specName) { this.specName = specName; }

    public String getEventId() { return eventId; }
    public void setEventId(String eventId) { this.eventId = eventId; }

    public String getUniqueId() { return uniqueId; }
    public void setUniqueId(String uniqueId) { this.uniqueId = uniqueId; }

    public List<String> getArgs() { return args; }
    public void setArgs(List<String> args) { this.args = args; }

    public String getCountCond() { return countCond; }
    public void setCountCond(String countCond) { this.countCond = countCond; }
}

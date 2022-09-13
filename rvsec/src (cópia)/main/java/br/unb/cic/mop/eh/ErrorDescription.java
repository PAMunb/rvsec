package br.unb.cic.mop.eh;

import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ErrorDescription {
    static Pattern pattern = Pattern.compile("([\\w+\\.\\$]+)[.](\\<?\\w+\\>?)\\((.+)\\)");

    private ErrorType type;
    private String spec;
    private String location;
    private String expecting;
    private ErrorSummary summary;

    public ErrorDescription(ErrorType type, String spec, String location) {
        this(type, spec, location, "unknown");
    }

    public ErrorDescription(ErrorType type, String spec, String location, String expecting) {
        this.type = type;
        this.spec = spec;
        this.location = location;
        this.expecting = expecting;
        summary = createErrorSummary();
    }

    public ErrorType getType() {
        return type;
    }

    public String getSpec() {
        return spec;
    }

    public String getLocation() {
        return location;
    }

    public String getExpecting() {
        return expecting;
    }

    public ErrorSummary getErrorSummary() {
        return summary;
    }

    private ErrorSummary createErrorSummary() {
        String clazz = location;
        String method = location;
        String loc = location;

        Matcher matcher = pattern.matcher(location);
        if (matcher.matches()) {
            clazz = matcher.group(1);
            method = matcher.group(2);
            loc = matcher.group(3);
        }

        return new ErrorSummary(spec, type, clazz, method, loc);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o)
            return true;
        if (o == null || getClass() != o.getClass())
            return false;
        ErrorDescription that = (ErrorDescription) o;
        return getErrorSummary().equals(that.getErrorSummary());
    }

    @Override
    public int hashCode() {
        return Objects.hash(getErrorSummary().hashCode());
    }

    @Override
    public String toString() {
        return String.format("[%s] %s at %s expecting %s", spec, type, location, expecting);
    }

}

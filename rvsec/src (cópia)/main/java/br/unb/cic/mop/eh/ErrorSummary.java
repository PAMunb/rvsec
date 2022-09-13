package br.unb.cic.mop.eh;

import java.util.Objects;

public class ErrorSummary {
    private String spec;
    private String error;
    private String classQualifiedName;
    private String methodName;
    private String location;

    public ErrorSummary(String spec, ErrorType error, String classQualifiedName, String methodName, String location) {
        this(spec, error.toString(), classQualifiedName, methodName, location);
    }

    public ErrorSummary(String spec, String error, String classQualifiedName, String methodName, String location) {
        this.spec = spec;
        this.error = error;
        this.classQualifiedName = classQualifiedName;
        this.methodName = methodName;
        this.location = location;
    }

    public String getSpec() {
        return spec;
    }

    public String getError() {
        return error;
    }

    public String getClassQualifiedName() {
        return classQualifiedName;
    }

    public String getMethodName() {
        return methodName;
    }

    public String getLocation() {
        return location;
    }

    private String className() {
        String res = classQualifiedName;
//        if(classQualifiedName.contains("$")) {
//            int idx = classQualifiedName.indexOf("$");
//            res =  res.substring(0, idx);
//        }
        return res.substring(res.lastIndexOf(".") + 1);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o)
            return true;
        if (o == null || getClass() != o.getClass())
            return false;
        ErrorSummary that = (ErrorSummary) o;
        return Objects.equals(spec, that.spec) && Objects.equals(error, that.error)
                && Objects.equals(classQualifiedName, that.classQualifiedName)
                && Objects.equals(methodName, that.methodName)
                && Objects.equals(location, that.location);
    }

    @Override
    public int hashCode() {
        return Objects.hash(spec, error, classQualifiedName, methodName, location);
    }

    @Override
    public String toString() {
        return String.format("%s,%s,%s,%s,%s,%s", spec, classQualifiedName, className(), methodName, location, error);
    }

}

package br.unb.cic.mop.eh;

import java.io.Serializable;

public class ErrorSummary implements Serializable {
	private static final long serialVersionUID = 1L;

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
	public int hashCode() {
		final int prime = 31;
		int result = 1;
		result = prime * result + ((classQualifiedName == null) ? 0 : classQualifiedName.hashCode());
		result = prime * result + ((error == null) ? 0 : error.hashCode());
		result = prime * result + ((location == null) ? 0 : location.hashCode());
		result = prime * result + ((methodName == null) ? 0 : methodName.hashCode());
		result = prime * result + ((spec == null) ? 0 : spec.hashCode());
		return result;
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if (obj == null)
			return false;
		if (getClass() != obj.getClass())
			return false;
		ErrorSummary other = (ErrorSummary) obj;
		if (classQualifiedName == null) {
			if (other.classQualifiedName != null)
				return false;
		} else if (!classQualifiedName.equals(other.classQualifiedName))
			return false;
		if (error == null) {
			if (other.error != null)
				return false;
		} else if (!error.equals(other.error))
			return false;
		if (location == null) {
			if (other.location != null)
				return false;
		} else if (!location.equals(other.location))
			return false;
		if (methodName == null) {
			if (other.methodName != null)
				return false;
		} else if (!methodName.equals(other.methodName))
			return false;
		if (spec == null) {
			if (other.spec != null)
				return false;
		} else if (!spec.equals(other.spec))
			return false;
		return true;
	}

	@Override
	public String toString() {
		return String.format("%s,%s,%s,%s,%s,%s", spec, classQualifiedName, className(), methodName, location, error);
	}

}

package br.unb.cic.rvsec.taint.model;

import soot.SootMethod;

public class SourceSinkItem {
	private SootMethod method;
	private SourceSinkCategory category;

	public SourceSinkItem(SootMethod method, SourceSinkCategory category) {
		this.method = method;
		this.category = category;
	}

	public SootMethod getMethod() {
		return method;
	}

	public SourceSinkCategory getCategory() {
		return category;
	}

	@Override
	public String toString() {
		return String.format("<%s: %s %s> -> %s"
				, method.getDeclaringClass().getName()
				, method.getReturnType().toString()
				, method.getSignature()
				, category.getValue());
	}

}

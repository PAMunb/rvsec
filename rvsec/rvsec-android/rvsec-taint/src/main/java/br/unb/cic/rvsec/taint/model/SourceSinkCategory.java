package br.unb.cic.rvsec.taint.model;

public enum SourceSinkCategory {
	SOURCE("_SOURCE_"), SINK("_SINK_");

	private String value;

	SourceSinkCategory(String value) {
		this.value = value;
	}

	public String getValue() {
		return value;
	}
}

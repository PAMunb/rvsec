package com.fdu.se.sootanalyze.model;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class WindowNode {
	private long id;
	private String name;
	private String type;
	private Set<TransitionEdge> outEdges = new HashSet<>();
	private List<Widget> widgets = new ArrayList<>();

	public WindowNode() {
	}

	public long getId() {
		return id;
	}

	public void setId(long id) {
		this.id = id;
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public String getType() {
		return type;
	}

	public void setType(String type) {
		this.type = type;
	}

	public Set<TransitionEdge> getOutEdges() {
		return outEdges;
	}

	public void setOutEdges(Set<TransitionEdge> outEdges) {
		this.outEdges = outEdges;
	}

	public List<Widget> getWidgets() {
		return widgets;
	}

	public void setWidgets(List<Widget> widgets) {
		this.widgets = widgets;
	}

	@Override
	public String toString() {
		return String.format("WindowNode [id=%s, name=%s, type=%s, widgets=%s]", id, name, type, widgets);
	}

}

package com.fdu.se.sootanalyze.model.out;

import java.util.HashSet;
import java.util.Set;
import java.util.stream.Collectors;

import com.fdu.se.sootanalyze.model.ActivityWindowNode;
import com.fdu.se.sootanalyze.model.WindowNode;

public class WindowInfoOut {
	private long id;
	private String name;
	private boolean isMain = false;
	private String layoutFileName;
	private String type;

	private Set<WidgetInfoOut> widgets = new HashSet<>();
	private WindowInfoOut optionsMenu;

	// TODO remover ... temporario
//	private WindowNode node;

	public WindowInfoOut(WindowNode node) {
//		this.node = node;
		if (node != null) {
			this.id = node.getId();
			this.name = node.getName();
			this.type = node.getType();
			process(node);
		}
	}

	private Set<WidgetInfoOut> getWidgets(WindowNode node) {
		return node.getWidgets().stream()
				.map(WidgetInfoOut::new)
				.collect(Collectors.toSet());
	}

	private void process(WindowNode windowNode) {
		this.widgets = getWidgets(windowNode);
		if (windowNode instanceof ActivityWindowNode) {
			ActivityWindowNode node = (ActivityWindowNode) windowNode;
			this.isMain = node.isMain();
			this.layoutFileName = node.getLayoutFileName();
			WindowNode menu = node.getOptionsMenuNode();
			if (menu != null) {
				this.optionsMenu = new WindowInfoOut(menu);
			}
		}
	}

	public long getId() {
		return id;
	}

	public String getName() {
		return name;
	}

	public boolean isMain() {
		return isMain;
	}

	public String getLayoutFileName() {
		return layoutFileName;
	}

	public String getType() {
		return type;
	}

	public Set<WidgetInfoOut> getWidgets() {
		return widgets;
	}

	public WindowInfoOut getOptionsMenu() {
		return optionsMenu;
	}

	@Override
	public String toString() {
		return String.format("WindowInfoOut [id=%s, name=%s, isMain=%s, layoutFileName=%s, type=%s, widgets=%s, optionsMenu=%s]", id, name, isMain, layoutFileName, type, widgets, optionsMenu);
	}

}

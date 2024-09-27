package br.unb.cic.rvsec.reach.gesda;

import java.util.HashSet;
import java.util.Set;

public class WindowInfoOut {
	private long id;
	private String name;
	private boolean isMain = false;
	private String layoutFileName;
	private String type;

	private Set<WidgetInfoOut> widgets = new HashSet<>();
	private WindowInfoOut optionsMenu;

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

	public boolean isMain() {
		return isMain;
	}

	public void setMain(boolean isMain) {
		this.isMain = isMain;
	}

	public String getLayoutFileName() {
		return layoutFileName;
	}

	public void setLayoutFileName(String layoutFileName) {
		this.layoutFileName = layoutFileName;
	}

	public String getType() {
		return type;
	}

	public void setType(String type) {
		this.type = type;
	}

	public Set<WidgetInfoOut> getWidgets() {
		return widgets;
	}

	public void setWidgets(Set<WidgetInfoOut> widgets) {
		this.widgets = widgets;
	}

	public WindowInfoOut getOptionsMenu() {
		return optionsMenu;
	}

	public void setOptionsMenu(WindowInfoOut optionsMenu) {
		this.optionsMenu = optionsMenu;
	}

	@Override
	public String toString() {
		return String.format("WindowInfoOut [id=%s, name=%s, isMain=%s, layoutFileName=%s, type=%s, widgets=%s, optionsMenu=%s]", id, name, isMain, layoutFileName, type, widgets, optionsMenu);
	}

}

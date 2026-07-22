package com.fdu.se.sootanalyze.model;

import br.unb.cic.rvsec.apk.model.ActivityInfo;

public class ActivityWindowNode extends WindowNode {
    private WindowNode optionsMenuNode;
	private final ActivityInfo actInfo;

    public ActivityWindowNode(ActivityInfo actInfo) {
		this.actInfo = actInfo;
    }
   

    @Override
	public String getName() {
        return actInfo.getName();
    }
    
    @Override
    public String getType() {
        return WindowType.ACT;
    }

    @Override
	public void setType(String type) {       
    }

	public boolean isMain() {
		return actInfo.isMain();
	}

	public String getLayoutFileName() {
		return actInfo.getLayoutFileName();
	}
	
	public WindowNode getOptionsMenuNode() {
        return optionsMenuNode;
    }

    public void setOptionsMenuNode(WindowNode optionsMenuNode) {
        this.optionsMenuNode = optionsMenuNode;
    }

	@Override
	public String toString() {
		return String.format("ActivityWindowNode [id=%s, name=%s, type=%s, isMain=%s, layoutFileName=%s, optionsMenuNode=%s, widgets=%s]", 
				getId(), getName(), getType(), isMain(), getLayoutFileName(), optionsMenuNode, getWidgets());
	}
    
}

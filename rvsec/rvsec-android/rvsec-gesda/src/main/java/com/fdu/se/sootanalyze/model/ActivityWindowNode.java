package com.fdu.se.sootanalyze.model;

import java.util.List;

import com.fdu.se.sootanalyze.model.xml.ActivityInfo;

public class ActivityWindowNode extends WindowNode {
    private WindowNode optionsMenuNode;
	private ActivityInfo actInfo;

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
	
	

//	public void setLayoutFileName(String layoutFileName) {
//		this.layoutFileName = layoutFileName;
//	}

//	public void setName(String name) {
//        this.name = name;
//    }
//
//    public String getLabel() {
//        return label;
//    }
//
//    public void setLabel(String label) {
//        this.label = label;
//    }


	public WindowNode getOptionsMenuNode() {
        return optionsMenuNode;
    }

    public void setOptionsMenuNode(WindowNode optionsMenuNode) {
        this.optionsMenuNode = optionsMenuNode;
    }

	public void printOptMenuWidgets(){
        if(optionsMenuNode != null){
            System.out.println(optionsMenuNode.getName());
            List<Widget> menuWidgets = optionsMenuNode.getWidgets();
            for(Widget w:menuWidgets){
                System.out.println("id: "+w.getId());
                if(w instanceof MenuItem){
                    MenuItem item = (MenuItem)w;
                    System.out.println("menu_item: "+item.getItemId()+"\t"+item.getText());
                }
                if(w instanceof SubMenu){
                    SubMenu sub = (SubMenu)w;
                    System.out.println("sub_menu: "+sub.getSubMenuId()+"\t"+sub.getText());
                    for(MenuItem subItem:sub.getItems()){
                        System.out.println("sub_item id: "+subItem.getId());
                        System.out.println("sub_menu_item: "+subItem.getItemId()+"\t"+subItem.getText());
                    }
                }
            }
        }
    }


	@Override
	public String toString() {
		return String.format("ActivityWindowNode [optionsMenuNode=%s, getName()=%s, isMain()=%s, getLayoutFileName()=%s, getId()=%s, getType()=%s, optionsMenuNode=%s, widgets=%s]", optionsMenuNode!=null, getName(), isMain(), getLayoutFileName(), getId(), getType(), optionsMenuNode, getWidgets());
	}
    
}

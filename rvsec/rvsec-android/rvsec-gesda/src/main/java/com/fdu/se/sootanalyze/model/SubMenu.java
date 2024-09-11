package com.fdu.se.sootanalyze.model;

import java.util.ArrayList;
import java.util.List;

@Deprecated
public class SubMenu extends Widget {
    private String text;
    private int subMenuId;
    private List<TextViewWidget> items = new ArrayList<>();

    public SubMenu() {
    	super(WidgetBuilder.newSubMenu());//TODO
//        this.setEvent("click");
//        this.setWidgetType("android.view.SubMenu");
    }



    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }

    public int getSubMenuId() {
        return subMenuId;
    }

    public void setSubMenuId(int subMenuId) {
        this.subMenuId = subMenuId;
    }

    public List<TextViewWidget> getItems() {
        return items;
    }

    public void setItems(List<TextViewWidget> items) {
        this.items = items;
    }




}

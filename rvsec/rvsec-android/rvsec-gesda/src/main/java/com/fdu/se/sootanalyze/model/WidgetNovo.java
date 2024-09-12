package com.fdu.se.sootanalyze.model;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import soot.SootField;

public class WidgetNovo {

	private long id;
	private String widgetId;
	private WidgetType type; 
	private String name;
	private Set<Listener> listeners = new HashSet<>();
	private SootField field;
	
	private List<Widget> dWidgets = new ArrayList<>();// the dependency of this widget
	
	//view
	private String contentDescription;
	private String tooltipText;
	
	//textView
	private String text;
	private String hint;
	private String inputMethod;
	private String inputType;
	
	//toggle e switch
	private String textOn;
	private String textOff;
	
	//spinner
	private List<String> entries;
	private String prompt;
	private int spinnerMode;
}

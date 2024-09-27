package com.fdu.se.sootanalyze;

import java.util.ArrayList;
import java.util.List;

public class Constants {
	public static List<String> startActivitySignatures;
	public static List<String> addMenuItemSignatures;
	public static List<String> addSubMenuSignatures;
	public static List<String> addSubMenuItemSignatures;
	public static List<String> systemCallbacks;
	
	static {
		init();
	}

	private static void init() {
		initStartActSignatures();
		initAddMenuItemSignatures();
		initAddSubMenuSignatures();
		initAddSubMenuItemSignatures();
		initSystemCallbacks();
	}
	
	private static void initStartActSignatures() {
		startActivitySignatures = new ArrayList<>();
		startActivitySignatures.add("<android.app.Activity: void startActivity(android.content.Intent)>");
		startActivitySignatures.add("<android.app.Activity: void startActivity(android.content.Intent,android.os.Bundle)");
		startActivitySignatures.add("<android.app.Activity: void startActivityForResult(android.content.Intent,int)>");
		startActivitySignatures.add("<android.app.Activity: void startActivityForResult(android.content.Intent,int,android.os.Bundle)>");
		startActivitySignatures.add("<android.app.Activity: void startActivityIfNeeded(android.content.Intent,int,android.os.Bundle)>");
		startActivitySignatures.add("<android.app.Activity: void startActivityIfNeeded(android.content.Intent,int)>");
	}

	private static void initAddMenuItemSignatures() {
		addMenuItemSignatures = new ArrayList<>();
		addMenuItemSignatures.add("<android.view.Menu: android.view.MenuItem add(int,int,int,int)>");
		addMenuItemSignatures.add("<android.view.Menu: android.view.MenuItem add(int,int,int,java.lang.CharSequence)>");
	}

	private static void initAddSubMenuSignatures() {
		addSubMenuSignatures = new ArrayList<>();
		addSubMenuSignatures.add("<android.view.Menu: android.view.SubMenu addSubMenu(int,int,int,int)>");
		addSubMenuSignatures.add("<android.view.Menu: android.view.SubMenu addSubMenu(int,int,int,java.lang.CharSequence)>");
	}

	private static void initAddSubMenuItemSignatures() {
		addSubMenuItemSignatures = new ArrayList<>();
		addSubMenuItemSignatures.add("<android.view.SubMenu: android.view.MenuItem add(int,int,int,int)>");
		addSubMenuItemSignatures.add("<android.view.SubMenu: android.view.MenuItem add(int,int,int,java.lang.CharSequence)>");
	}
	
	private static void initSystemCallbacks() {
		systemCallbacks = new ArrayList<>();
		systemCallbacks.add("onSaveInstanceState");
		systemCallbacks.add("onRestoreInstanceState");
		systemCallbacks.add("onTouchEvent");
	}
}

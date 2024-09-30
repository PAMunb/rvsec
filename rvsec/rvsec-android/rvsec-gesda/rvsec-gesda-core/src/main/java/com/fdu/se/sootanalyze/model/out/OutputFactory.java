package com.fdu.se.sootanalyze.model.out;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import com.fdu.se.sootanalyze.model.ActivityWindowNode;
import com.fdu.se.sootanalyze.model.Listener;
import com.fdu.se.sootanalyze.model.Widget;
import com.fdu.se.sootanalyze.model.WindowNode;

import br.unb.cic.rvsec.apk.model.AppInfo;
import soot.SootMethod;

public final class OutputFactory {

	public static ApkInfoOut createApkInfoOut(AppInfo appInfo, List<WindowNode> windows) {
		String fileName = appInfo.getFileName();
		String appName = appInfo.getAppName();
		String packageName = appInfo.getPackage();
		
		List<WindowInfoOut> windowsInfo = windows.stream()
			.map(OutputFactory::createWindowInfoOut)
			.collect(Collectors.toList());
		
		return new ApkInfoOut(fileName, appName, packageName, windowsInfo);	
	}
	
	private static WindowInfoOut createWindowInfoOut(WindowNode windowNode) {
		WindowInfoOut info = new WindowInfoOut();
		
		info.setId(windowNode.getId());
		info.setName(windowNode.getName());
		info.setType(windowNode.getType());
		
		Set<WidgetInfoOut> widgets = windowNode.getWidgets().stream()
				.map(OutputFactory::createWidgetInfoOut)
				.collect(Collectors.toSet());
		info.setWidgets(widgets);
		
		if (windowNode instanceof ActivityWindowNode) {
			ActivityWindowNode node = (ActivityWindowNode) windowNode;
			info.setMain(node.isMain());
			info.setLayoutFileName(node.getLayoutFileName());
			WindowNode menu = node.getOptionsMenuNode();
			if (menu != null) {
				info.setOptionsMenu(createWindowInfoOut(menu));
			}
		}
			
		return info;
	}
	
	
	private static WidgetInfoOut createWidgetInfoOut(Widget widget) {
		WidgetInfoOut info = new WidgetInfoOut();
		
		info.setWidgetId(widget.getWidgetId());
		info.setType(widget.getType());
		info.setName(widget.getName());
		info.setContentDescription(widget.getContentDescription());
		info.setTooltipText(widget.getTooltipText());
		info.setText(widget.getText());
		info.setHint(widget.getHint());
		info.setInputType(widget.getInputType());
		info.setEntries(widget.getEntries());
		info.setPrompt(widget.getPrompt());
		info.setSpinnerMode(widget.getSpinnerMode());
		
		String field = null;
		if (widget.getField() != null) {
			field = widget.getField().getSignature();
		}
		info.setField(field);
		
		List<ListenerInfoOut> listeners = widget.getListeners().stream()
			.map(OutputFactory::createListenerInfoOut)
			.collect(Collectors.toList());
		info.setListeners(listeners);
		
		List<WidgetInfoOut> items = widget.getItems().stream()
				.map(OutputFactory::createWidgetInfoOut)
				.collect(Collectors.toList());
		info.setItems(items);
		
		return info;
	}
	
	private static ListenerInfoOut createListenerInfoOut(Listener listener) {
		ListenerInfoOut info = new ListenerInfoOut();
		info.setType(listener.getType());
		info.setListernerClass(listener.getListernerClass());		
		info.setRegisteredInFile(listener.isEventRegisteredInLayoutFile());
		info.setCallbackMethod(createMethodInfoOut(listener.getCallbackMethod()));
		return info;
	}
	
	private static MethodInfoOut createMethodInfoOut(SootMethod method) {
		if(method == null) {
			return null;
		}
		return new MethodInfoOut(method.getName(), 
				method.getDeclaringClass().getName(), 
				method.getSignature(), 
				method.getModifiers());
	}
	
}

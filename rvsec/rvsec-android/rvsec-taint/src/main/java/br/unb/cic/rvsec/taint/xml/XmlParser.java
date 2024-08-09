package br.unb.cic.rvsec.taint.xml;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import br.unb.cic.rvsec.taint.model.ViewInfo;
import soot.jimple.infoflow.android.axml.AXmlAttribute;
import soot.jimple.infoflow.android.axml.AXmlHandler;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.axml.ApkHandler;

public class XmlParser {
	
	private String apkPath;
	private Map<String, String> idMap;

	public XmlParser(String apkPath, Map<String, String> idMap) {
		this.apkPath = apkPath;
		this.idMap = idMap;
	}
	
	public List<ViewInfo> parseActivityLayout(String filename) {		
		List<ViewInfo> views = new ArrayList<>();
		String layoutPath = "res/layout/" + filename + ".xml";
		System.out.println("Parsing layout file: "+layoutPath);
		try (ApkHandler apkHandler = new ApkHandler(apkPath)) {
			InputStream layoutStream = apkHandler.getInputStream(layoutPath);
			if (layoutStream != null) {
				AXmlHandler aXmlHandler = new AXmlHandler(layoutStream);

				List<ViewInfo> buttons = parseButtons(aXmlHandler);
				views.addAll(buttons);

				List<ViewInfo> editTexts = parseEditTexts(aXmlHandler);
				views.addAll(editTexts);

				List<ViewInfo> spinnerTexts = parseSpinners(aXmlHandler);
				views.addAll(spinnerTexts);

			}
		} catch (IOException e) {
			// TODO
			e.printStackTrace();
		}
		return views;
	}
	
	private List<ViewInfo> parseButtons(AXmlHandler aXmlHandler) {
		System.out.println("Parsing Buttons ...");
		List<ViewInfo> views = new ArrayList<>();
		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("Button");
		for (AXmlNode node : buttonNodes) {
			System.out.println("node ...");
			Integer id = getAttributeValue("id", node);
			System.out.println("\tid= "+id);
			String callback = getAttributeValue("onClick", node);
			System.out.println("\tcallback=" + callback);
			String name = idMap.get(id.toString());
			System.out.println("\tbuttonName=" + name);

			ViewInfo info = new ViewInfo();
			info.setId(id.toString());
			info.setName(name);
			info.setTipo("Button");
			info.setCallback(callback);

			views.add(info);
		}
		return views;
	}
	
	private List<ViewInfo> parseEditTexts(AXmlHandler aXmlHandler) {
		List<ViewInfo> views = new ArrayList<>();
		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("EditText");
		for (AXmlNode node : buttonNodes) {
			Integer id = getAttributeValue("id", node);
			String name = idMap.get(id.toString());
			System.out.println("\teditTextName=" + name);

			ViewInfo info = new ViewInfo();
			info.setId(id.toString());
			info.setName(name);
			info.setTipo("EditText");
//			info.setCallback(callback);

			views.add(info);
		}
		return views;
	}

	private List<ViewInfo> parseSpinners(AXmlHandler aXmlHandler) {
		List<ViewInfo> views = new ArrayList<>();
		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("Spinner");
		for (AXmlNode node : buttonNodes) {
			Integer id = getAttributeValue("id", node);
			String name = idMap.get(id.toString());
			System.out.println("\tspinnerName=" + name);

			ViewInfo info = new ViewInfo();
			info.setId(id.toString());
			info.setName(name);
			info.setTipo("Spinner");
//			info.setCallback(callback);

			views.add(info);
		}
		return views;
	}

	
	private <T> T getAttributeValue(String name, AXmlNode bNode) {
		AXmlAttribute<T> attribute = (AXmlAttribute<T>) bNode.getAttribute(name);
		if (attribute != null) {
			return attribute.getValue();
		}
		return null;
	}
}

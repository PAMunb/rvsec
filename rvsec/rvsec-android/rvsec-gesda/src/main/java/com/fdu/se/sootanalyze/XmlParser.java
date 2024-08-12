package com.fdu.se.sootanalyze;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import com.fdu.se.sootanalyze.model.Widget;
import com.fdu.se.sootanalyze.model.xml.AppInfo;

import soot.jimple.infoflow.android.axml.AXmlAttribute;
import soot.jimple.infoflow.android.axml.AXmlHandler;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.axml.ApkHandler;

public class XmlParser {

	private String apkPath;
	private Map<String, String> idMap;
	private File decompiledApkDir;

	public XmlParser(String apkPath, Map<String, String> idMap) {
		this.apkPath = apkPath;
		this.idMap = idMap;
	}
	
	public List<Widget> parseActivityLayout(String filename) {		
		List<Widget> views = new ArrayList<>();
		System.out.println("*** PATH="+Path.of("res", "layout", filename+".xml"));
		System.out.println("*** PATH="+Path.of("res", "layout", filename+".xml").toAbsolutePath());
//		String layoutPath = "res/layout/" + filename + ".xml";
		String layoutPath = Path.of("res", "layout", filename+".xml").toString();
		System.out.println("Parsing layout file: "+layoutPath);
		try (ApkHandler apkHandler = new ApkHandler(apkPath)) {
			InputStream layoutStream = apkHandler.getInputStream(layoutPath);
			if (layoutStream != null) {
				AXmlHandler aXmlHandler = new AXmlHandler(layoutStream);
				//TODO mudar a logica pra ficar na ordem (na lista) q eh declarado

				List<Widget> buttons = parseButtons(aXmlHandler);
				views.addAll(buttons);

				List<Widget> editTexts = parseEditTexts(aXmlHandler);
				views.addAll(editTexts);

				List<Widget> spinnerTexts = parseSpinners(aXmlHandler);
				views.addAll(spinnerTexts);
			}
		} catch (IOException e) {
			// TODO
			e.printStackTrace();
		}
		return views;
	}
	
	public Map<String, String> parseAppStrings(AppInfo appInfo) {
		Map<String, String> mapa = new HashMap<>();
		
//		if(decompiledApkDir == null) {
//			decompiledApkDir = AppReader.decompileApp(appInfo);
//		}
		
//		String stringPath = "apks\\" + appInfo.getLabel() + "\\res\\values\\strings.xml";
//		String stringPath = Path.of(decompiledApkDir.getAbsolutePath(), "res","values","strings.xml").toString();
//		System.out.println("%%%%%% parseAppStrings :: " + stringPath);
//		File stringsFile = new File(stringPath);
//		System.out.println("stringsFile :: " + stringsFile);
//		if (!stringsFile.exists()) {
//			decompiledApkDir = AppReader.decompileApp(appInfo);
//		}
		try {
			decompiledApkDir = AppReader.decompileApp(appInfo);
			String stringPath = Path.of(decompiledApkDir.getAbsolutePath(), "res","values","strings.xml").toString();
			System.out.println("%%%%%% parseAppStrings :: " + stringPath);
			File stringsFile = new File(stringPath);
			System.out.println("stringsFile :: " + stringsFile);
			
			DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
			DocumentBuilder docBuilder = dbf.newDocumentBuilder();
			Document strings = docBuilder.parse(stringsFile);
			NodeList strElements = strings.getElementsByTagName("string");
			for (int i = 0; i < strElements.getLength(); i++) {
				Node strElement = strElements.item(i);
				Element e = (Element) strElement;
				String nameValue = e.getAttribute("name");
//				if (name.equals(nameValue)) {
					System.out.println("MAPA_STRING: "+nameValue+" --> "+strElement.getFirstChild().getNodeValue());
					mapa.put(nameValue, strElement.getFirstChild().getNodeValue());
//				}
			}
		} catch (Exception e) {
			e.printStackTrace();
		}
		return mapa;
	}
	
	private List<Widget> parseButtons(AXmlHandler aXmlHandler) {
		System.out.println("Parsing Buttons ...");
		List<Widget> views = new ArrayList<>();
		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("Button");
		for (AXmlNode node : buttonNodes) {
			System.out.println("node ...");
			Integer id = getAttributeValue("id", node);
			System.out.println("\tid= "+id);
			String callback = getAttributeValue("onClick", node);
			System.out.println("\tcallback=" + callback);
			String name = idMap.get(id.toString());
			System.out.println("\tbuttonName=" + name);
			
			String textId = null;
			AXmlAttribute<?> textAttribute = node.getAttribute("text");
			if(textAttribute != null) {
				textId = textAttribute.getValue().toString();	
			}
			System.out.println("\ttext=" + name);

			Widget button = new Widget();
			button.setWidgetType("android.widget.Button");
            button.setEvent("click");
            button.setEventMethod(callback);
            button.setLayoutRegister(callback != null);
            button.setWidgetId(id.toString());
            button.setName(name);
            //TODO
//            Integer text = getAttributeValue("text", node);
//            if(text != null) {
			button.setTextId(textId);
//            }

			views.add(button);
		}
		return views;
	}
	
	private List<Widget> parseEditTexts(AXmlHandler aXmlHandler) {
		List<Widget> views = new ArrayList<>();
		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("EditText");
		for (AXmlNode node : buttonNodes) {
			Integer id = getAttributeValue("id", node);
			String name = idMap.get(id.toString());
			System.out.println("\teditTextName=" + name);

			Widget editText = new Widget();
			editText.setWidgetType("android.widget.EditText");
            editText.setEvent("edit");
            editText.setWidgetId(id.toString());
            editText.setName(name);
            editText.setText(getAttributeValue("text", node));
			
			//TODO text e tip

			views.add(editText);
		}
		return views;
	}

	private List<Widget> parseSpinners(AXmlHandler aXmlHandler) {
		List<Widget> views = new ArrayList<>();
		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("Spinner");
		for (AXmlNode node : buttonNodes) {
			Integer id = getAttributeValue("id", node);
			String name = idMap.get(id.toString());
			System.out.println("\tspinnerName=" + name);

			Widget spinner = new Widget();
			spinner.setWidgetType("android.widget.Spinner");
            spinner.setEvent("select");
            spinner.setWidgetId(id.toString());
            spinner.setName(name);
            spinner.setText(getAttributeValue("text", node));
            
			//TODO values e text

			views.add(spinner);
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

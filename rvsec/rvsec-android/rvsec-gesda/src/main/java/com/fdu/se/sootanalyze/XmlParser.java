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
import javax.xml.parsers.ParserConfigurationException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.SAXException;

import com.fdu.se.sootanalyze.model.MenuItem;
import com.fdu.se.sootanalyze.model.SubMenu;
import com.fdu.se.sootanalyze.model.Widget;
import com.fdu.se.sootanalyze.model.xml.AppInfo;
import com.fdu.se.sootanalyze.utils.NumberIncrementer;
import com.fdu.se.sootanalyze.utils.StringUtil;

import soot.jimple.infoflow.android.axml.AXmlAttribute;
import soot.jimple.infoflow.android.axml.AXmlHandler;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.axml.ApkHandler;

public class XmlParser {
	private static final String TEXT = "text";

	private static Logger log = LoggerFactory.getLogger(XmlParser.class);

	private AppInfo appInfo;
	private String apkPath;
	private Map<String, String> idMap;
	private Map<String, String> mapAppStrings;
	private File decompiledApkDir;
	

	public XmlParser(AppInfo appInfo, Map<String, String> idMap) {
		this.appInfo = appInfo;
		this.apkPath = appInfo.getPath();
		this.idMap = idMap;
	}

	public List<Widget> parseActivityLayout(String filename) {
		List<Widget> views = new ArrayList<>();
		String layoutPath = Path.of("res", "layout", filename + ".xml").toString();
		log.debug("Parsing activity layout file: "+layoutPath);
		try (ApkHandler apkHandler = new ApkHandler(apkPath)) {
			InputStream layoutStream = apkHandler.getInputStream(layoutPath);
			if (layoutStream != null) {
				AXmlHandler aXmlHandler = new AXmlHandler(layoutStream);
				
				// TODO mudar a logica pra ficar na ordem (na lista) q eh declarado ??

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

	public String getStringValueByName(String name) {
		if (mapAppStrings == null) {
			initializeStringsMap();
		}
		log.trace("getStringValueByName("+name+")="+mapAppStrings.get(name));
		return mapAppStrings.get(name);
	}

	private void initializeStringsMap() {
		mapAppStrings = new HashMap<>();
		try {
			decompiledApkDir = AppReader.decompileApp(appInfo);
			
			String stringPath = Path.of(decompiledApkDir.getAbsolutePath(), "res", "values", "strings.xml").toString();
			parseStringFile(stringPath);			
//			
			String publicPath = Path.of(decompiledApkDir.getAbsolutePath(), "res", "values", "public.xml").toString();
			parsePublicStringFile(publicPath);
		} catch (Exception e) {
			log.error("Error parsing resources file: "+e.getMessage(), e);
		}
	}
	
	private void parseStringFile(String filePath) throws ParserConfigurationException, SAXException, IOException {
		log.debug("Parsing strings file: "+filePath);
		File stringsFile = new File(filePath);
		DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
		DocumentBuilder docBuilder = dbf.newDocumentBuilder();
		Document strings = docBuilder.parse(stringsFile);
		NodeList strElements = strings.getElementsByTagName("string");
		for (int i = 0; i < strElements.getLength(); i++) {
			Node strElement = strElements.item(i);
			Element e = (Element) strElement;
			String nameValue = e.getAttribute("name");
			mapAppStrings.put(nameValue, strElement.getFirstChild().getNodeValue());
		}
	}
	
	private void parsePublicStringFile(String filePath) throws ParserConfigurationException, SAXException, IOException {
		log.debug("Parsing public strings file: "+filePath);
		final List<String> validTypes = List.of("id", "menu", "string");
		DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
		DocumentBuilder docBuilder = dbf.newDocumentBuilder();
		Document resources = docBuilder.parse(new File(filePath));
		NodeList elements = resources.getElementsByTagName("public");
		for (int i = 0; i < elements.getLength(); i++) {
			Node element = elements.item(i);
			Element e = (Element) element;
			String typeValue = e.getAttribute("type");
			if(validTypes.contains(typeValue)) {
				String nameValue = e.getAttribute("name");
				String idValue = e.getAttribute("id");
				if(StringUtil.isHexadecimal(idValue)) {
					int id = Integer.parseInt(idValue.substring(2), 16);
					idMap.put(id+"", nameValue);				
				}
			}
		}
	}

	private List<Widget> parseButtons(AXmlHandler aXmlHandler) {
		log.debug("Parsing Buttons ...");
		List<Widget> views = new ArrayList<>();
		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("Button");
		for (AXmlNode node : buttonNodes) {
			log.trace("Button node ..."+node);
			Integer id = getAttributeValue("id", node);
			log.trace("\tid= " + id);
			String callback = getAttributeValue("onClick", node);
			log.trace("\tcallback=" + callback);
			String name = getNameById(id.toString());
			log.trace("\tbuttonName=" + name);

			//TODO
			String textId = null;
			AXmlAttribute<?> textAttribute = node.getAttribute(TEXT);
			if (textAttribute != null) {
				textId = textAttribute.getValue().toString();
			}
			log.trace("\ttextId="+textId);			

			Widget button = new Widget();
			button.setWidgetType("android.widget.Button");
			button.setEvent("click");
			button.setEventMethod(callback);
			button.setEventRegisteredInLayoutFile(callback != null);
			button.setWidgetId(id.toString());
			button.setName(name);
			button.setTextId(textId);
			button.setText(getNameById(textId));

			log.debug("Adding button: "+button);
			views.add(button);
		}
		return views;
	}

	
	
	private List<Widget> parseEditTexts(AXmlHandler aXmlHandler) {
		log.debug("Parsing EditTexts ...");
		
//		List<Widget> widgets = parseWidgetsByTag(aXmlHandler, "EditText", "android.widget.EditText", "edit");
//		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("EditText");
//		for (AXmlNode node : buttonNodes) {
//			Integer id = getAttributeValue("id", node);
//			Widget widget = findWidgetById(id, widgets);
			
			//TODO
//			String hint = getAttributeValue("hint", node);
//			log.trace("parseEditTexts ::: hint="+hint);
//			widget.setHint(hint);
//			
//			//https://developer.android.com/reference/android/widget/TextView.html#attr_android%3ainputType
//			String inputType = getAttributeValue("inputType", node);
//			widget.setInputType(inputType);
//		}
		
		
		return parseWidgetsByTag(aXmlHandler, "EditText", "android.widget.EditText", "edit");
	}
	
//	private Widget findWidgetById(Integer id, List<Widget> widgets) {
//		String idStr = id.toString();
//		for (Widget widget : widgets) {
//			if(widget.getWidgetId().equals(idStr)) {
//				return widget;
//			}
//		}
//		return null;
//	}

	private List<Widget> parseSpinners(AXmlHandler aXmlHandler) {
		log.debug("Parsing Spinners ...");
		
		
//		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("Spinner");
//		for (AXmlNode node : buttonNodes) {
//			log.trace("Spinner node ... : "+node);
//			Integer id = getAttributeValue("id", node);
//			log.trace("\tid= " + id);
//			String name = getNameById(id.toString());
//			log.trace("\tspinnerName=" + name);
//
//			Widget spinner = new Widget();
//			spinner.setWidgetType("android.widget.Spinner");
//			spinner.setEvent("select");
//			spinner.setWidgetId(id.toString());
//			spinner.setName(name);
//			spinner.setText(getAttributeValue(TEXT, node));
//
//			// TODO values e text
//
//			log.debug("Adding spinner: "+spinner);
//			views.add(spinner);
//		}
		return parseWidgetsByTag(aXmlHandler, "Spinner", "android.widget.Spinner", "select");
	}
	
	private List<Widget> parseWidgetsByTag(AXmlHandler aXmlHandler, String tag, String type, String event) {
		List<Widget> views = new ArrayList<>();
		List<AXmlNode> nodes = aXmlHandler.getNodesWithTag(tag);
		for (AXmlNode node : nodes) {
			log.trace("Widget node ... : "+node);
			Integer id = getAttributeValue("id", node);
			log.trace("\tid= " + id);
			String name = getNameById(id.toString());
			log.trace("\tname=" + name);

			Widget widget = new Widget();
			widget.setWidgetType(type);
			widget.setEvent(event);
			widget.setWidgetId(id.toString());
			widget.setName(name);
			//TODO
			log.trace("parseWidgetsByTag ::: 01="+getAttributeValue(TEXT, node));
			log.trace("parseWidgetsByTag ::: 02="+getNameById(getAttributeValue(TEXT, node)));
			widget.setText(getAttributeValue(TEXT, node));
			
			String hint = getAttributeValue("hint", node);
			log.trace("parseWidgetsByTag ::: hint="+hint);
//			widget.setHint(hint);
			
			//https://developer.android.com/reference/android/widget/TextView.html#attr_android%3ainputType
			Integer inputType = getAttributeValue("inputType", node);
			log.trace("parseWidgetsByTag ::: inputType="+inputType);
			log.trace("parseWidgetsByTag ::: inputMode="+getAttributeValue("inputMode", node));
			log.trace("parseWidgetsByTag ::: tooltipText="+getAttributeValue("tooltipText", node));
			log.trace("parseWidgetsByTag ::: autofillHints="+getAttributeValue("autofillHints", node));
//			widget.setInputType(inputType);

			log.debug("Adding widget: "+widget);
			views.add(widget);
		}
		return views;
	}
	
	public List<Widget> parseAppMenu(String menuName, NumberIncrementer curWidgetId) {
		log.trace("* parseAppMenu: " + menuName);
		List<Widget> menuWidgets = new ArrayList<>();
		String menuPath = "res/menu/" + menuName + ".xml";
		try (ApkHandler apkHandler = new ApkHandler(appInfo.getPath())) {
			InputStream menuStream = apkHandler.getInputStream(menuPath);
			if (menuStream != null) {
				AXmlHandler aXmlHandler = new AXmlHandler(menuStream);
				AXmlNode root = aXmlHandler.getDocument().getRootNode();
				List<AXmlNode> itemNodes = root.getChildrenWithTag("item");
				for (AXmlNode itemNode : itemNodes) {
					List<AXmlNode> sub = itemNode.getChildrenWithTag("menu");
					if (sub.isEmpty()) {// itemNode is MenuItem
						menuWidgets.add(newMenuTitem(itemNode, curWidgetId));
					} else {// itemNode is SubMenu
						SubMenu subMenu = new SubMenu();
						subMenu.setId(curWidgetId.inc());
						AXmlAttribute<Integer> idAttr = (AXmlAttribute<Integer>) itemNode.getAttribute("id");
						if (idAttr != null) {
							int subId = idAttr.getValue();
							subMenu.setSubMenuId(subId);
						}
						String subText = getTitleFromMenuRes(itemNode);
						subMenu.setText(subText);
						List<AXmlNode> subItemNodes = sub.get(0).getChildrenWithTag("item");
						List<MenuItem> subItems = new ArrayList<>();
						for (AXmlNode subItemNode : subItemNodes) {
							subItems.add(newMenuTitem(subItemNode, curWidgetId));
						}
						subMenu.setItems(subItems);
						menuWidgets.add(subMenu);
					}
				}
			}
		} catch (IOException e) {
			e.printStackTrace();
		}
		return menuWidgets;
	}

	private MenuItem newMenuTitem(AXmlNode node, NumberIncrementer curWidgetId) {
		log.trace("newMenuTitem ::: node="+node);
		MenuItem item = new MenuItem();
		item.setId(curWidgetId.inc());
		AXmlAttribute<Integer> subIdAttr = (AXmlAttribute<Integer>) node.getAttribute("id");
		if (subIdAttr != null) {
			int subId = subIdAttr.getValue();
			log.trace("newMenuTitem ::: subId="+subId);
			item.setItemId(subId);
		}
		String itemText = getTitleFromMenuRes(node);
		log.trace("newMenuTitem ::: itemText="+itemText);
		item.setText(itemText);
		return item;
	}
	
	private String getTitleFromMenuRes(AXmlNode node) {
		log.trace("getTitleFromMenuRes: "+node);
		AXmlAttribute<?> attr = node.getAttribute("title");
		log.trace("getTitleFromMenuRes ::: attr="+attr);
		if (attr != null) {
			Object titleValue = attr.getValue();			
			if (titleValue instanceof Integer) {// Attribute is Integer
				Integer intValue = (Integer) titleValue;
				log.trace("getTitleFromMenuRes ::: intValue="+intValue);
				//TODO esta no public?
				String name = getNameById(intValue.toString());
				log.trace("getTitleFromMenuRes ::: name="+name);
				if (name != null) {
					return getStringValueByName(name);
				}
			} else if (titleValue instanceof String) {// Attribute is String
				log.trace("getTitleFromMenuRes ::: string="+titleValue);
				return (String) titleValue;
			}
		}
		return null;
	}

	private String getNameById(String id) {
		log.trace("getNameById: "+id);
		if(idMap == null) {
			//TODO
//			log.trace("getNameById ::: idMap == null");
			return null;
		}
//		log.trace("getNameById ::: "+idMap.get(id));
//		log.trace("getNameById ::: mapAppStrings ... "+getStringValueByName(id));
//		idMap.keySet().forEach(k -> log.trace("getNameById ::: idMap ::: "+k+"="+idMap.get(k)));
		return idMap.get(id);
	}
	
	private <T> T getAttributeValue(String name, AXmlNode bNode) {
		AXmlAttribute<T> attribute = (AXmlAttribute<T>) bNode.getAttribute(name);
		if (attribute == null) {
			return null;
		}
		return attribute.getValue();
	}

}

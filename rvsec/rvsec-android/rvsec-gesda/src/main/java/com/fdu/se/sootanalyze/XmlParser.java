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

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import com.fdu.se.sootanalyze.model.MenuItem;
import com.fdu.se.sootanalyze.model.SubMenu;
import com.fdu.se.sootanalyze.model.Widget;
import com.fdu.se.sootanalyze.model.xml.AppInfo;
import com.fdu.se.sootanalyze.utils.NumberIncrementer;

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
		log.info("Parsing activity layout file: "+layoutPath);
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
			mapAppStrings = new HashMap<>();
			try {
				decompiledApkDir = AppReader.decompileApp(appInfo);
				String stringPath = Path.of(decompiledApkDir.getAbsolutePath(), "res", "values", "strings.xml").toString();
				log.info("Parsing strings file: "+stringPath);
				File stringsFile = new File(stringPath);

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
			} catch (Exception e) {
				log.error("Error parsing strings file: "+e.getMessage(), e);
			}
		}
		
		log.trace("getStringValueByName("+name+")="+mapAppStrings.get(name));
		return mapAppStrings.get(name);
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
			button.setLayoutRegister(callback != null);
			button.setWidgetId(id.toString());
			button.setName(name);
			button.setTextId(textId);
			//TODO pegar o texto
			log.warn(">>>> "+getNameById(textId));

			log.debug("Adding button: "+button);
			views.add(button);
		}
		return views;
	}

	
	
	private List<Widget> parseEditTexts(AXmlHandler aXmlHandler) {
		log.debug("Parsing EditTexts ...");
		List<Widget> views = new ArrayList<>();
		List<AXmlNode> buttonNodes = aXmlHandler.getNodesWithTag("EditText");
		for (AXmlNode node : buttonNodes) {
			log.trace("EditText node ...");
			Integer id = getAttributeValue("id", node);
			log.trace("\tid= " + id);
			String name = getNameById(id.toString());
			log.trace("\teditTextName=" + name);

			Widget editText = new Widget();
			editText.setWidgetType("android.widget.EditText");
			editText.setEvent("edit");
			editText.setWidgetId(id.toString());
			editText.setName(name);
			editText.setText(getAttributeValue(TEXT, node));

			// TODO textId, text e tip
			
			log.debug("Adding EditText: "+editText);
			views.add(editText);
		}
		return views;
	}

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
			widget.setWidgetType("android.widget.Spinner");
			widget.setEvent("select");
			widget.setWidgetId(id.toString());
			widget.setName(name);
			widget.setText(getAttributeValue(TEXT, node));

			// TODO values e text

			log.debug("Adding widget: "+widget);
			views.add(widget);
		}
		return views;
	}
	
	
	public List<Widget> parseAppMenu(String menuName, NumberIncrementer curWidgetId) {
		System.out.println("* parseAppMenu: " + menuName);
		List<Widget> menuWidgets = new ArrayList<>();
		String menuPath = "res/menu/" + menuName + ".xml";
		try {
			ApkHandler apkHandler = new ApkHandler(appInfo.getPath());
			InputStream menuStream = apkHandler.getInputStream(menuPath);
			if (menuStream != null) {
				AXmlHandler aXmlHandler = new AXmlHandler(menuStream);
				AXmlNode root = aXmlHandler.getDocument().getRootNode();
				List<AXmlNode> itemNodes = root.getChildrenWithTag("item");
//				if (!itemNodes.isEmpty()) {
				for (AXmlNode itemNode : itemNodes) {
					List<AXmlNode> sub = itemNode.getChildrenWithTag("menu");
					if (sub.isEmpty()) {// itemNode is MenuItem
//						System.out.println("******** menuItem .......");
//						MenuItem menuItem = new MenuItem();
//						menuItem.setId(++curWidgetId);
//						AXmlAttribute<Integer> idAttr = (AXmlAttribute<Integer>) itemNode.getAttribute("id");
//						if (idAttr != null) {
//							int itemId = idAttr.getValue();
//							menuItem.setItemId(itemId);
//							System.out.println("itemId="+itemId);
//						}
////                            AXmlAttribute<String> textAttr = (AXmlAttribute<String>)itemNode.getAttribute("title");
////                            if(textAttr != null){
////                                String itemText = textAttr.getValue();
////                                menuItem.setText(itemText);
////                            }
//						String itemText = getTitleFromMenuRes(itemNode);
//						System.out.println("itemText="+itemText);
//						menuItem.setText(itemText);
						menuWidgets.add(newMenuTitem(itemNode, curWidgetId));
					} else {// itemNode is SubMenu
						SubMenu subMenu = new SubMenu();
						subMenu.setId(curWidgetId.inc());
						AXmlAttribute<Integer> idAttr = (AXmlAttribute<Integer>) itemNode.getAttribute("id");
						if (idAttr != null) {
							int subId = idAttr.getValue();
							subMenu.setSubMenuId(subId);
						}
//                            AXmlAttribute<String> textAttr = (AXmlAttribute<String>)itemNode.getAttribute("title");
//                            if(textAttr != null){
//                                String subText = textAttr.getValue();
//                                subMenu.setText(subText);
//                            }
						String subText = getTitleFromMenuRes(itemNode);
						subMenu.setText(subText);
						List<AXmlNode> subItemNodes = sub.get(0).getChildrenWithTag("item");
						List<MenuItem> subItems = new ArrayList<>();
						for (AXmlNode subItemNode : subItemNodes) {
//							MenuItem subItem = new MenuItem();
//							subItem.setId(++curWidgetId);
//							AXmlAttribute<Integer> subIdAttr = (AXmlAttribute<Integer>) subItemNode.getAttribute("id");
//							if (subIdAttr != null) {
//								int subId = subIdAttr.getValue();
//								subItem.setItemId(subId);
//							}
////                                AXmlAttribute<String> subTextAttr = (AXmlAttribute<String>)subItemNode.getAttribute("title");
////                                if(subTextAttr != null){
////                                    String subText = subTextAttr.getValue();
////                                    subItem.setText(subText);
////                                }
//							String subItemText = getTitleFromMenuRes(subItemNode);
//							subItem.setText(subItemText);
							subItems.add(newMenuTitem(subItemNode, curWidgetId));
						}
						subMenu.setItems(subItems);
						menuWidgets.add(subMenu);
					}
				}
//				}
			}
		} catch (IOException e) {
			e.printStackTrace();
		}
		return menuWidgets;
	}

	private MenuItem newMenuTitem(AXmlNode node, NumberIncrementer curWidgetId) {
		MenuItem item = new MenuItem();
		item.setId(curWidgetId.inc());
		AXmlAttribute<Integer> subIdAttr = (AXmlAttribute<Integer>) node.getAttribute("id");
		if (subIdAttr != null) {
			int subId = subIdAttr.getValue();
			item.setItemId(subId);
		}
		String itemText = getTitleFromMenuRes(node);
		System.out.println("itemText="+itemText);
		item.setText(itemText);
		return item;
	}
	
	private String getTitleFromMenuRes(AXmlNode node) {
		System.out.println("* getTitleFromMenuRes: "+node.getAttribute("title"));
		AXmlAttribute<?> attr = node.getAttribute("title");
		if (attr != null) {
			Object titleValue = attr.getValue();
			if (titleValue instanceof Integer) {// Attribute is Integer
				Integer intValue = (Integer) titleValue;
				System.out.println("intValue="+intValue);
				//TODO esta no 
				String name = getNameById(intValue.toString());
				System.out.println("name="+name);
				if (name != null) {
					return getStringValueByName(name);
				}
			} else if (titleValue instanceof String) {// Attribute is String
				return (String) titleValue;
			}
		}
		return null;
	}

	private String getNameById(String id) {
		if(idMap == null) {
			return null;
		}
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

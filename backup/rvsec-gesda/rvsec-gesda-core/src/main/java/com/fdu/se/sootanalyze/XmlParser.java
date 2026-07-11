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

import com.fdu.se.sootanalyze.model.Listener;
import com.fdu.se.sootanalyze.model.ListenerType;
import com.fdu.se.sootanalyze.model.Widget;
import com.fdu.se.sootanalyze.model.Widget.WidgetBuilder;
import com.fdu.se.sootanalyze.model.WidgetBuilderFactory;
import com.fdu.se.sootanalyze.model.WidgetType;
import com.fdu.se.sootanalyze.utils.NumberIncrementer;
import com.fdu.se.sootanalyze.utils.StringUtil;

import br.unb.cic.rvsec.apk.model.AppInfo;
import br.unb.cic.rvsec.apk.reader.AppReader;
import pxb.android.axml.AxmlVisitor;
import soot.jimple.infoflow.android.axml.AXmlAttribute;
import soot.jimple.infoflow.android.axml.AXmlHandler;
import soot.jimple.infoflow.android.axml.AXmlNode;
import soot.jimple.infoflow.android.axml.ApkHandler;

public class XmlParser {
	private static final String TEXT = "text";
	private static final Map<Integer, String> inputTypeValues = new HashMap<>();

	private static final Logger log = LoggerFactory.getLogger(XmlParser.class);

	private final AppInfo appInfo;
	private final String apkPath;
	private final Map<String, String> idMap;
	private Map<String, String> mapAppStrings;
	private File decompiledApkDir;

	public XmlParser(AppInfo appInfo, Map<String, String> idMap) {
		this.appInfo = appInfo;
		this.apkPath = appInfo.getPath();
		this.idMap = idMap;
		initializeStringsMap();
	}

	public List<Widget> parseActivityLayout(String filename) {
		List<Widget> views = new ArrayList<>();
		String layoutPath = Path.of("res", "layout", filename + ".xml").toString();
		log.debug("Parsing activity layout file: " + layoutPath);
		try (ApkHandler apkHandler = new ApkHandler(apkPath)) {
			InputStream layoutStream = apkHandler.getInputStream(layoutPath);
			if (layoutStream != null) {
				AXmlHandler aXmlHandler = new AXmlHandler(layoutStream);

				List<Widget> textViewWidgets = parseTextViewWidgets(aXmlHandler);
				views.addAll(textViewWidgets);

				List<Widget> spinnerTexts = parseSpinners(aXmlHandler);
				views.addAll(spinnerTexts);
			}
		} catch (Exception e) {
			// TODO
			e.printStackTrace();
		}
		return views;
	}

	public String getStringValueByName(String name) {
		return mapAppStrings.get(name);
	}

	private void initializeStringsMap() {
		mapAppStrings = new HashMap<>();
		try {
			decompiledApkDir = AppReader.decompileApp(appInfo);

			String stringPath = Path.of(decompiledApkDir.getAbsolutePath(), "res", "values", "strings.xml").toString();
			parseStringFile(stringPath);

			String publicPath = Path.of(decompiledApkDir.getAbsolutePath(), "res", "values", "public.xml").toString();
			parsePublicStringFile(publicPath);
		} catch (Exception e) {
			log.error("Error parsing resources file: " + e.getMessage(), e);
		}
	}

	private void parseStringFile(String filePath) throws ParserConfigurationException, SAXException, IOException {
		log.debug("Parsing strings file: " + filePath);
		File stringsFile = new File(filePath);
		if (stringsFile.exists()) {
			DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
			DocumentBuilder docBuilder = dbf.newDocumentBuilder();
			Document strings = docBuilder.parse(stringsFile);
			NodeList strElements = strings.getElementsByTagName("string");
			for (int i = 0; i < strElements.getLength(); i++) {
				Node strElement = strElements.item(i);
				Element e = (Element) strElement;
				String nameValue = e.getAttribute("name");
				Node firstChild = strElement.getFirstChild();
				if (firstChild != null) {
					mapAppStrings.put(nameValue, strElement.getFirstChild().getNodeValue());
				}
			}
		}
	}

	private void parsePublicStringFile(String filePath) throws ParserConfigurationException, SAXException, IOException {
		log.debug("Parsing public strings file: " + filePath);
		File publicStringsFile = new File(filePath);
		if (publicStringsFile.exists()) {
			final List<String> validTypes = List.of("id", "menu", "string");
			DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
			DocumentBuilder docBuilder = dbf.newDocumentBuilder();
			Document resources = docBuilder.parse(publicStringsFile);
			NodeList elements = resources.getElementsByTagName("public");
			for (int i = 0; i < elements.getLength(); i++) {
				Node element = elements.item(i);
				Element e = (Element) element;
				String typeValue = e.getAttribute("type");
				if (validTypes.contains(typeValue)) {
					String nameValue = e.getAttribute("name");
					String idValue = e.getAttribute("id");
					if (StringUtil.isHexadecimal(idValue)) {
						int id = Integer.parseInt(idValue.substring(2), 16);
						idMap.put(id + "", nameValue);
						mapAppStrings.put(id + "", nameValue);
					}
				}
			}
		}
	}

	private Listener getListener(AXmlNode node) {
		ListenerType type = ListenerType.OnClickListener;
		String callback = getAttributeValue(type.getEventCallback(), node);
		if (callback != null) {
			return new Listener(type, callback, true);
		}
		return null;
	}

	private List<Widget> parseTextViewWidgets(AXmlHandler aXmlHandler) {
		List<Widget> views = new ArrayList<>();

		List<WidgetType> widgetTypes = List.of(WidgetType.BUTTON, WidgetType.EDIT_TEXT, WidgetType.TEXT_VIEW, WidgetType.CHECKED_TEXT_VIEW, WidgetType.CHECKBOX, WidgetType.TOGGLE_BUTTON, WidgetType.RADIO_BUTTON, WidgetType.IMAGE_BUTTON);

		for (WidgetType type : widgetTypes) {
			List<AXmlNode> nodes = aXmlHandler.getNodesWithTag(type.getXmlTag());
			for (AXmlNode node : nodes) {
				WidgetBuilder builder = parseView(node, type);

				// https://developer.android.com/reference/android/widget/TextView.html#attr_android%3ainputType
				Integer inputTypeInt = getAttributeValue("inputType", node);
				String inputType = (inputTypeInt == null) ? null : inputTypeValues.get(inputTypeInt);

				Widget widget = builder
						.text(getAttributeValueAsString(TEXT, node))
						.hint(getAttributeValueAsString("hint", node))
						.inputType(inputType)
						.addListener(getListener(node))
						.build();

				String logText = String.format("Adding widget: [id=%s, widgetId=%s, type=%s, name=%s]", widget.getId(), widget.getWidgetId(), widget.getType(), widget.getName());
				log.debug(logText);
				views.add(widget);
			}
		}

		return views;
	}

	private String getAttributeValueAsString(String attributeName, AXmlNode node) {
		String text = null;
		AXmlAttribute<?> attribute = node.getAttribute(attributeName);
		if (attribute != null) {
			if (AxmlVisitor.TYPE_INT_HEX == attribute.getAttributeType()) {
				Integer textId = (Integer) attribute.getValue();
				text = getNameById(textId.toString());
			} else if (AxmlVisitor.TYPE_STRING == attribute.getAttributeType()) {
				text = attribute.getValue().toString();
			}

		}
		return text;
	}

	private WidgetBuilder parseView(AXmlNode node, WidgetType type) {
		Integer id = getAttributeValue("id", node);
		if(id == null) {
			id = -1;
		}
		String name = getNameById(id.toString());
		String contentDescription = getAttributeValueAsString("contentDescription", node);
		String tooltipText = getAttributeValue("tooltipText", node);
		return Widget.builder(type).widgetId(id.toString()).name(name).contentDescription(contentDescription).tooltipText(tooltipText);
	}

	// https://developer.android.com/reference/android/widget/Spinner#xml-attributes
	private List<Widget> parseSpinners(AXmlHandler aXmlHandler) throws SAXException, IOException, ParserConfigurationException {
		List<Widget> views = new ArrayList<>();
		WidgetType type = WidgetType.SPINNER;
		List<AXmlNode> nodes = aXmlHandler.getNodesWithTag(type.getXmlTag());
		for (AXmlNode node : nodes) {
			WidgetBuilder builder = parseView(node, type);
			parseSpinnerEntries(node, builder);
			Widget widget = builder.build();
			log.debug("Adding spinner: " + widget);
			views.add(widget);
		}
		return views;
	}

	private void parseSpinnerEntries(AXmlNode node, WidgetBuilder builder) throws SAXException, IOException, ParserConfigurationException {
		Integer id = getAttributeValue("entries", node);
		if (id != null) {
			String name = getNameById(id.toString());
			if (name != null) {
				String arraysFilePath = Path.of(decompiledApkDir.getAbsolutePath(), "res", "values", "arrays.xml").toString();
				DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
				DocumentBuilder docBuilder = dbf.newDocumentBuilder();
				Document resources = docBuilder.parse(new File(arraysFilePath));
				NodeList elements = resources.getElementsByTagName("string-array");
				for (int i = 0; i < elements.getLength(); i++) {
					Node element = elements.item(i);
					Element e = (Element) element;
					String nameValue = e.getAttribute("name");
					if (nameValue.equals(name)) {
						NodeList items = e.getElementsByTagName("item");
						for (int j = 0; j < items.getLength(); j++) {
							Node item = items.item(j);
							Element it = (Element) item;
							String value = it.getTextContent();
							builder.addEntry(value);
						}
					}
				}
			}
		}
	}

	public List<Widget> parseAppMenu(String menuName, NumberIncrementer curWidgetId) {
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
						Widget menuItem = newMenuItem(itemNode, curWidgetId);
						String logText = String.format("Adding menu item: [id=%s, widgetId=%s, name=%s]", menuItem.getId(), menuItem.getWidgetId(), menuItem.getName());
						log.debug(logText);
						menuWidgets.add(menuItem);
					} else {// itemNode is SubMenu
						WidgetBuilder builder = WidgetBuilderFactory.newSubMenu();
						AXmlAttribute<Integer> idAttr = (AXmlAttribute<Integer>) itemNode.getAttribute("id");
						if (idAttr != null) {
							int subId = idAttr.getValue();
							builder.widgetId(subId + "");
						}
						String subText = getTitleFromMenuRes(itemNode);
						builder.text(subText);
						List<AXmlNode> subItemNodes = sub.get(0).getChildrenWithTag("item");
						for (AXmlNode subItemNode : subItemNodes) {
							builder.addMenuItem(newMenuItem(subItemNode, curWidgetId));
						}
						Widget subMenu = builder.build();
						log.debug("Adding sub menu: " + subMenu);
						menuWidgets.add(subMenu);
					}
				}
			}
		} catch (IOException e) {
			log.error("Error parsing menu: " + e.getMessage(), e);
		}
		return menuWidgets;
	}

	private Widget newMenuItem(AXmlNode node, NumberIncrementer curWidgetId) {
		WidgetBuilder builder = WidgetBuilderFactory.newMenuItem();

		AXmlAttribute<Integer> idAttribute = (AXmlAttribute<Integer>) node.getAttribute("id");
		if (idAttribute != null) {
			String widgetId = idAttribute.getValue().toString();
			builder.widgetId(widgetId);
			builder.name(getNameById(widgetId));
		}

		return builder.addListener(getListener(node)).text(getTitleFromMenuRes(node)).build();
	}

	private String getTitleFromMenuRes(AXmlNode node) {
		AXmlAttribute<?> attr = node.getAttribute("title");
		if (attr != null) {
			Object titleValue = attr.getValue();
			if (titleValue instanceof Integer) {// Attribute is Integer
				Integer intValue = (Integer) titleValue;
				String name = getNameById(intValue.toString());
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
		if (idMap == null) {
			// TODO
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

	static {
		// map inspired on res/values/attrs.xml from android.jar

		/* There is no content type. The text is not editable. */
		inputTypeValues.put(Integer.parseInt("00000000", 16), "none");
		/*
		 * Just plain old text. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_NORMAL}.
		 */
		inputTypeValues.put(Integer.parseInt("00000001", 16), "text");
		/*
		 * Can be combined with <var>text</var> and its variations to request
		 * capitalization of all characters. Corresponds to {@link
		 * android.text.InputType#TYPE_TEXT_FLAG_CAP_CHARACTERS}.
		 */
		inputTypeValues.put(Integer.parseInt("00001001", 16), "textCapCharacters");
		/*
		 * Can be combined with <var>text</var> and its variations to request
		 * capitalization of the first character of every word. Corresponds to {@link
		 * android.text.InputType#TYPE_TEXT_FLAG_CAP_WORDS}.
		 */
		inputTypeValues.put(Integer.parseInt("00002001", 16), "textCapWords");
		/*
		 * Can be combined with <var>text</var> and its variations to request
		 * capitalization of the first character of every sentence. Corresponds to
		 * {@link android.text.InputType#TYPE_TEXT_FLAG_CAP_SENTENCES}.
		 */
		inputTypeValues.put(Integer.parseInt("00004001", 16), "textCapSentences");
		/*
		 * Can be combined with <var>text</var> and its variations to request
		 * auto-correction of text being input. Corresponds to {@link
		 * android.text.InputType#TYPE_TEXT_FLAG_AUTO_CORRECT}.
		 */
		inputTypeValues.put(Integer.parseInt("00008001", 16), "textAutoCorrect");
		/*
		 * Can be combined with <var>text</var> and its variations to specify that this
		 * field will be doing its own auto-completion and talking with the input method
		 * appropriately. Corresponds to {@link
		 * android.text.InputType#TYPE_TEXT_FLAG_AUTO_COMPLETE}.
		 */
		inputTypeValues.put(Integer.parseInt("00010001", 16), "textAutoComplete");
		/*
		 * Can be combined with <var>text</var> and its variations to allow multiple
		 * lines of text in the field. If this flag is not set, the text field will be
		 * constrained to a single line. Corresponds to {@link
		 * android.text.InputType#TYPE_TEXT_FLAG_MULTI_LINE}.
		 * 
		 * Note: If this flag is not set and the text field doesn't have max length
		 * limit, the framework automatically set maximum length of the characters to
		 * 5000 for the performance reasons.
		 */
		inputTypeValues.put(Integer.parseInt("00020001", 16), "textMultiLine");
		/*
		 * Can be combined with <var>text</var> and its variations to indicate that
		 * though the regular text view should not be multiple lines, the IME should
		 * provide multiple lines if it can. Corresponds to {@link
		 * android.text.InputType#TYPE_TEXT_FLAG_IME_MULTI_LINE}.
		 */
		inputTypeValues.put(Integer.parseInt("00040001", 16), "textImeMultiLine");
		/*
		 * Can be combined with <var>text</var> and its variations to indicate that the
		 * IME should not show any dictionary-based word suggestions. Corresponds to
		 * {@link android.text.InputType#TYPE_TEXT_FLAG_NO_SUGGESTIONS}.
		 */
		inputTypeValues.put(Integer.parseInt("00080001", 16), "textNoSuggestions");
		/*
		 * Can be combined with <var>text</var> and its variations to indicate that if
		 * there is extra information, the IME should provide {@link
		 * android.view.inputmethod.TextAttribute}. Corresponds to {@link
		 * android.text.InputType#TYPE_TEXT_FLAG_ENABLE_TEXT_CONVERSION_SUGGESTIONS}.
		 */
		inputTypeValues.put(Integer.parseInt("00100001", 16), "textEnableTextConversionSuggestions");
		/*
		 * Text that will be used as a URI. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_URI}.
		 */
		inputTypeValues.put(Integer.parseInt("00000011", 16), "textUri");
		/*
		 * Text that will be used as an e-mail address. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_EMAIL_ADDRESS}.
		 */
		inputTypeValues.put(Integer.parseInt("00000021", 16), "textEmailAddress");
		/*
		 * Text that is being supplied as the subject of an e-mail. Corresponds to
		 * {@link android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_EMAIL_SUBJECT}.
		 */
		inputTypeValues.put(Integer.parseInt("00000031", 16), "textEmailSubject");
		/*
		 * Text that is the content of a short message. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_SHORT_MESSAGE}.
		 */
		inputTypeValues.put(Integer.parseInt("00000041", 16), "textShortMessage");
		/*
		 * Text that is the content of a long message. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_LONG_MESSAGE}.
		 */
		inputTypeValues.put(Integer.parseInt("00000051", 16), "textLongMessage");
		/*
		 * Text that is the name of a person. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_PERSON_NAME}.
		 */
		inputTypeValues.put(Integer.parseInt("00000061", 16), "textPersonName");
		/*
		 * Text that is being supplied as a postal mailing address. Corresponds to
		 * {@link android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_POSTAL_ADDRESS}.
		 */
		inputTypeValues.put(Integer.parseInt("00000071", 16), "textPostalAddress");
		/*
		 * Text that is a password. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_PASSWORD}.
		 */
		inputTypeValues.put(Integer.parseInt("00000081", 16), "textPassword");
		/*
		 * Text that is a password that should be visible. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_VISIBLE_PASSWORD}.
		 */
		inputTypeValues.put(Integer.parseInt("00000091", 16), "textVisiblePassword");
		/*
		 * Text that is being supplied as text in a web form. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_WEB_EDIT_TEXT}.
		 */
		inputTypeValues.put(Integer.parseInt("000000a1", 16), "textWebEditText");
		/*
		 * Text that is filtering some other data. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_FILTER}.
		 */
		inputTypeValues.put(Integer.parseInt("000000b1", 16), "textFilter");
		/*
		 * Text that is for phonetic pronunciation, such as a phonetic name field in a
		 * contact entry. Corresponds to {@link android.text.InputType#TYPE_CLASS_TEXT}
		 * | {@link android.text.InputType#TYPE_TEXT_VARIATION_PHONETIC}.
		 */
		inputTypeValues.put(Integer.parseInt("000000c1", 16), "textPhonetic");
		/*
		 * Text that will be used as an e-mail address on a web form. Corresponds to
		 * {@link android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS}.
		 */
		inputTypeValues.put(Integer.parseInt("000000d1", 16), "textWebEmailAddress");
		/*
		 * Text that will be used as a password on a web form. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_TEXT} | {@link
		 * android.text.InputType#TYPE_TEXT_VARIATION_WEB_PASSWORD}.
		 */
		inputTypeValues.put(Integer.parseInt("000000e1", 16), "textWebPassword");
		/*
		 * A numeric only field. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_NUMBER} | {@link
		 * android.text.InputType#TYPE_NUMBER_VARIATION_NORMAL}.
		 */
		inputTypeValues.put(Integer.parseInt("00000002", 16), "number");
		/*
		 * Can be combined with <var>number</var> and its other options to allow a
		 * signed number. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_NUMBER} | {@link
		 * android.text.InputType#TYPE_NUMBER_FLAG_SIGNED}.
		 */
		inputTypeValues.put(Integer.parseInt("00001002", 16), "numberSigned");
		/*
		 * Can be combined with <var>number</var> and its other options to allow a
		 * decimal (fractional) number. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_NUMBER} | {@link
		 * android.text.InputType#TYPE_NUMBER_FLAG_DECIMAL}.
		 */
		inputTypeValues.put(Integer.parseInt("00002002", 16), "numberDecimal");
		/*
		 * A numeric password field. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_NUMBER} | {@link
		 * android.text.InputType#TYPE_NUMBER_VARIATION_PASSWORD}.
		 */
		inputTypeValues.put(Integer.parseInt("00000012", 16), "numberPassword");
		/*
		 * For entering a phone number. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_PHONE}.
		 */
		inputTypeValues.put(Integer.parseInt("00000003", 16), "phone");
		/*
		 * For entering a date and time. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_DATETIME} | {@link
		 * android.text.InputType#TYPE_DATETIME_VARIATION_NORMAL}.
		 */
		inputTypeValues.put(Integer.parseInt("00000004", 16), "datetime");
		/*
		 * For entering a date. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_DATETIME} | {@link
		 * android.text.InputType#TYPE_DATETIME_VARIATION_DATE}.
		 */
		inputTypeValues.put(Integer.parseInt("00000014", 16), "date");
		/*
		 * For entering a time. Corresponds to {@link
		 * android.text.InputType#TYPE_CLASS_DATETIME} | {@link
		 * android.text.InputType#TYPE_DATETIME_VARIATION_TIME}.
		 */
		inputTypeValues.put(Integer.parseInt("00000024", 16), "time");
//		inputTypeValues.put(0,"TYPE_DATETIME_VARIATION_NORMAL");
//		inputTypeValues.put(1,"TYPE_CLASS_TEXT");
//		inputTypeValues.put(2,"TYPE_CLASS_NUMBER");
//		inputTypeValues.put(3,"TYPE_CLASS_PHONE");
//		inputTypeValues.put(4,"TYPE_CLASS_DATETIME");
//		inputTypeValues.put(15,"TYPE_MASK_CLASS");
//		inputTypeValues.put(16,"TYPE_DATETIME_VARIATION_DATE");
//		inputTypeValues.put(32,"TYPE_DATETIME_VARIATION_TIME");
//		inputTypeValues.put(33,"TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS");
//		inputTypeValues.put(48,"TYPE_TEXT_VARIATION_EMAIL_SUBJECT");
//		inputTypeValues.put(64,"TYPE_TEXT_VARIATION_SHORT_MESSAGE");
//		inputTypeValues.put(80,"TYPE_TEXT_VARIATION_LONG_MESSAGE");
//		inputTypeValues.put(96,"TYPE_TEXT_VARIATION_PERSON_NAME");
//		inputTypeValues.put(97,"TYPE_TEXT_VARIATION_PERSON_NAME");
//		inputTypeValues.put(112,"TYPE_TEXT_VARIATION_POSTAL_ADDRESS");
//		inputTypeValues.put(128,"TYPE_TEXT_VARIATION_PASSWORD");
//		inputTypeValues.put(144,"TYPE_TEXT_VARIATION_VISIBLE_PASSWORD");
//		inputTypeValues.put(160,"TYPE_TEXT_VARIATION_WEB_EDIT_TEXT");
//		inputTypeValues.put(176,"TYPE_TEXT_VARIATION_FILTER");
//		inputTypeValues.put(192,"TYPE_TEXT_VARIATION_PHONETIC");
//		inputTypeValues.put(208,"TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS");
//		inputTypeValues.put(224,"TYPE_TEXT_VARIATION_WEB_PASSWORD");
//		inputTypeValues.put(4080,"TYPE_MASK_VARIATION");
//		inputTypeValues.put(4096,"TYPE_NUMBER_FLAG_SIGNED");
//		inputTypeValues.put(8192,"TYPE_NUMBER_FLAG_DECIMAL");
//		inputTypeValues.put(16384,"TYPE_TEXT_FLAG_CAP_SENTENCES");
//		inputTypeValues.put(32768,"TYPE_TEXT_FLAG_AUTO_CORRECT");
//		inputTypeValues.put(65536,"TYPE_TEXT_FLAG_AUTO_COMPLETE");
//		inputTypeValues.put(131072,"TYPE_TEXT_FLAG_MULTI_LINE");
//		inputTypeValues.put(262144,"TYPE_TEXT_FLAG_IME_MULTI_LINE");
//		inputTypeValues.put(524288,"TYPE_TEXT_FLAG_NO_SUGGESTIONS");
//		inputTypeValues.put(16773120,"TYPE_MASK_FLAGS");
	}

}

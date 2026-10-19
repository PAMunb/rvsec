package presto.android.xml;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;

import javax.xml.parsers.DocumentBuilderFactory;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.w3c.dom.Document;
import org.w3c.dom.Node;

import presto.android.Configs;
import soot.G;
import soot.Scene;
import soot.SootClass;

/**
 * {@code <application android:name>} as {@link DefaultXMLParser#readApplicationClassName}
 * resolves it for {@link XMLParser#getApplicationClassName()}: a relative name against the
 * manifest package, an absolute name as written, and {@code null} without the attribute or
 * with an empty one.
 *
 * <p>The parser singleton reads the manifest, the R file and the resources together, so the
 * test drives the static reader on an {@code <application>} element parsed here, namespace
 * aware as {@code readManifest} parses it. {@link XMLParser.Helper#getClassName} rejects a
 * phantom class, so each named class is added to a fresh Scene.
 */
public class ApplicationClassNameTest {

	private String savedBenchmarkName;

	@Before
	public void setUp() {
		G.reset();
		Scene.v().addClass(new SootClass("com.example.App"));
		Scene.v().addClass(new SootClass("org.lib.BaseApplication"));
		savedBenchmarkName = Configs.benchmarkName;
		Configs.benchmarkName = "";
	}

	@After
	public void tearDown() {
		Configs.benchmarkName = savedBenchmarkName;
		G.reset();
	}

	@Test
	public void aRelativeNameIsResolvedAgainstThePackage() throws Exception {
		assertEquals("com.example.App", read("android:name=\".App\""));
	}

	@Test
	public void anAbsoluteNameIsKeptAsWritten() throws Exception {
		assertEquals("org.lib.BaseApplication", read("android:name=\"org.lib.BaseApplication\""));
	}

	@Test
	public void noNameAttributeGivesNull() throws Exception {
		assertNull(read("android:label=\"App\""));
	}

	@Test
	public void anEmptyNameGivesNull() throws Exception {
		assertNull(read("android:name=\"\""));
	}

	private static String read(String applicationAttributes) throws Exception {
		String manifest = "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\""
				+ " package=\"com.example\">"
				+ "<application " + applicationAttributes + "/>"
				+ "</manifest>";
		DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
		factory.setNamespaceAware(true);
		Document doc = factory.newDocumentBuilder()
				.parse(new ByteArrayInputStream(manifest.getBytes(StandardCharsets.UTF_8)));
		Node appNode = doc.getElementsByTagName("application").item(0);
		return DefaultXMLParser.readApplicationClassName(appNode, "com.example");
	}
}

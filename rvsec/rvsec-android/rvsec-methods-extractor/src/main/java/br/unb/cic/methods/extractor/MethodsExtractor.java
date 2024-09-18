package br.unb.cic.methods.extractor;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import soot.Scene;
import soot.SootMethod;
import soot.Type;
import soot.options.Options;

public class MethodsExtractor {

	private boolean debug;

	public void execute(String app, String appPackage, String androidPlatformsDir, String outputFile,
			boolean excludeConstructors, boolean excludeStaticInitializers, boolean debug) {

		this.debug = debug;

		initializeSoot(app, androidPlatformsDir);

		Map<String, Set<String>> methodsMap = getMethods(appPackage, excludeConstructors, excludeStaticInitializers);

		writeMethods(outputFile, methodsMap);

		if (debug) {
			System.out.println("File generated: " + outputFile);
		}
	}

	private Map<String, Set<String>> getMethods(String appPackage, boolean excludeConstructors,
			boolean excludeStaticInitializers) {
		if (debug) {
			System.out.println("Extracting methods");
		}
		Map<String, Set<String>> methodsMap = new HashMap<>();
		Scene.v().getApplicationClasses().stream().filter(c -> c.getName().startsWith(appPackage))
				.filter(c -> !("R".equals(c.getShortName()))).filter(c -> !(c.getShortName().startsWith("R$")))
				.forEach(c -> {
					String clazz = c.getName();

					methodsMap.putIfAbsent(clazz, new HashSet<>());

					Stream<SootMethod> stream = c.getMethods().stream();
					if (excludeConstructors) {
						stream = stream.filter(m -> !m.isConstructor());
					}
					if (excludeStaticInitializers) {
						stream = stream.filter(m -> !m.isStaticInitializer());
					}

					stream.forEach(m -> {
						List<String> types = m.getParameterTypes().stream().map(Type::toString)
								.collect(Collectors.toList());
						String sig = String.format("%s(%s)", m.getName(), String.join(",", types));
						methodsMap.get(clazz).add(sig);
					});
				});
		return methodsMap;
	}

	private void writeMethods(String outputFile, Map<String, Set<String>> methodsMap) {
		if (debug) {
			System.out.println("Writing to file");
		}
		try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputFile))) {
			writer.write("class;method\n");
			for (String clazz : methodsMap.keySet()) {
				for (String method : methodsMap.get(clazz)) {
					writer.write(String.format("%s;%s%n", clazz, method));
				}
			}
		} catch (IOException e) {
			e.printStackTrace();
			System.exit(1);
		}
	}

	private void initializeSoot(String apk, String androidJAR) {
		if (debug) {
			System.out.println("Initializing Soot");
		}
		Options.v().set_full_resolver(true);
		Options.v().set_allow_phantom_refs(true);
		Options.v().set_prepend_classpath(true);
		Options.v().set_validate(true);
		Options.v().set_output_format(Options.output_format_none);
		Options.v().set_process_dir(Collections.singletonList(apk));
		Options.v().set_android_jars(androidJAR);
		Options.v().set_src_prec(Options.src_prec_apk);
		Options.v().set_process_multiple_dex(true);
		Options.v().set_soot_classpath(androidJAR);
		Scene.v().loadNecessaryClasses();
	}

}
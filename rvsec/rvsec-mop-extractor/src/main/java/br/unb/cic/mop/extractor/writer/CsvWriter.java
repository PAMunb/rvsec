package br.unb.cic.mop.extractor.writer;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import br.unb.cic.mop.extractor.model.JcaMethod;

public class CsvWriter implements Writer {

	static final String HEADER_CLASSES = "class";
	static final String HEADER_METHODS = "class,method";
	static final String HEADER_METHODS_WITH_PARAMS = "class,method,parameters,signature";

	@Override
	public void writeClasses(Set<String> classes, File out) {
		try (PrintWriter pw = new PrintWriter(new FileWriter(out, true), true)) {
			pw.println(HEADER_CLASSES);
			classes.forEach(c -> pw.println(c));
		} catch (IOException e) {
			throw new RuntimeException(e);
		}
	}

	@Override
	public void writeMethods(Set<JcaMethod> methods, File out) {
		writeMethods(methods, out, false);
	}

	@Override
	public void writeMethods(Set<JcaMethod> methods, File out, boolean withParameters) {
		try (PrintWriter pw = new PrintWriter(new FileWriter(out, true), true)) {
			List<JcaMethod> methodsList = List.copyOf(methods)
					.stream()
					.sorted(Comparator.comparing(JcaMethod::getClassName).thenComparing(Comparator.comparing(JcaMethod::getName)))
					.collect(Collectors.toList());
			if (withParameters) {
				// TODO arrumar o csv
				pw.println(HEADER_METHODS_WITH_PARAMS);
				methodsList.forEach(m -> pw.println(String.format("%s,%s,\"%s\",\"%s\"", m.getClassName(), m.getName(), m.getParametersAsString(), m.getSignature())));
			} else {
				pw.println(HEADER_METHODS);
				Set<String> methodsStr = new HashSet<>();
				methodsList.forEach(m -> methodsStr.add(String.format("%s,%s", m.getClassName(), m.getName())));
				methodsStr.stream().sorted().forEach(m -> pw.println(m));
			}
		} catch (IOException e) {
			throw new RuntimeException(e);
		}
	}

}

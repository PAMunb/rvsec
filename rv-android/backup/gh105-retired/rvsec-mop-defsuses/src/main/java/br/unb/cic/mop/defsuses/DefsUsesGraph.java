package br.unb.cic.mop.defsuses;

import java.io.File;
import java.util.Collection;
import java.util.Comparator;

import javamop.parser.SpecExtractor;
import javamop.parser.ast.MOPSpecFile;
import javamop.util.MOPException;

public class DefsUsesGraph {
	private static final String EXTENSION_MOP = ".mop";

	public void execute(File mopSpecsDir) throws MOPException {
		System.out.println("INICIANDO ...");
		Collection<MOPSpecDefsUses> defsUses = getDefsUses(mopSpecsDir);
		System.out.println(toPlantUml(defsUses));
		System.out.println("FIM DE FESTA");
	}
	
	public Collection<MOPSpecDefsUses> getDefsUses(File mopSpecsDir) throws MOPException {
		UseDefVisitor useDefVisitor = new UseDefVisitor();
		for (File file : mopSpecsDir.listFiles()) {
			if (file.getName().toLowerCase().endsWith(EXTENSION_MOP)) {
				readSpec(file, useDefVisitor);
			}
		}
		return useDefVisitor.getSpecs();
	}

	private void readSpec(File mopFile, UseDefVisitor useDefVisitor) throws MOPException {
		System.out.println("Parsing file: " + mopFile.getName());
		MOPSpecFile specFile = SpecExtractor.parse(mopFile);
		specFile.accept(useDefVisitor, null);
	}

	private String toPlantUml(Collection<MOPSpecDefsUses> specs) {
		String plantUml = "@startuml %n"
				+ "%s %n"
				+ "@enduml";
		return String.format(plantUml, specsToPlantUml(specs));
	}

	private String specsToPlantUml(Collection<MOPSpecDefsUses> specs) {
		StringBuilder sb = new StringBuilder();
		String specTemplate = "class %s << (M,LightSkyBlue) MOP Spec>> { %n"
				+ "  .. DEFINES ..%n"
				+ "%s %n"
				+ "  .. USES ..%n"
				+ "%s %n"
				+ "} %n";
		String fieldTemplate = "{field} %s %n";

		specs.stream().sorted(Comparator.comparing(MOPSpecDefsUses::getName)).forEach(spec -> {
			StringBuilder defs = new StringBuilder();
			StringBuilder uses = new StringBuilder();
			spec.getDefs().forEach(prop -> defs.append(String.format(fieldTemplate, prop)));
			spec.getUses().forEach(prop -> uses.append(String.format(fieldTemplate, prop)));
			sb.append(String.format(specTemplate, spec.getName(), defs.toString(), uses.toString()));
		});

		return sb.toString();
	}

	public static void main(String[] args) {
		File mopDir = new File("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources");

		try {
			new DefsUsesGraph().execute(mopDir);
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

}

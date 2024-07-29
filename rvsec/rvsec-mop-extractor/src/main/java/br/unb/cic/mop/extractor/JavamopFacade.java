package br.unb.cic.mop.extractor;

import java.io.File;
import java.util.HashSet;
import java.util.Set;

import br.unb.cic.mop.extractor.model.MopMethod;
import br.unb.cic.mop.extractor.visitor.UsedJcaClassesVisitor;
import br.unb.cic.mop.extractor.visitor.UsedJcaMethodsVisitor;
import javamop.parser.SpecExtractor;
import javamop.parser.ast.MOPSpecFile;
import javamop.util.MOPException;

public class JavamopFacade {

	private static final String MOP_SUFFIX = ".mop";
	private boolean debug;

	public Set<String> listUsedClasses(String mopSpecsDirPath, boolean debug) throws MOPException {
		this.debug = debug;
		Set<String> classes = new HashSet<>();

		getMopFiles(mopSpecsDirPath).forEach(f -> classes.addAll(listUsedClasses(f)));

		return classes;
	}

	public Set<MopMethod> listUsedMethods(String mopSpecsDirPath, boolean debug) throws MOPException {
		this.debug = debug;
		Set<MopMethod> methods = new HashSet<>();

		getMopFiles(mopSpecsDirPath).forEach(f -> methods.addAll(listUsedMethods(f)));

		return methods;
	}

	private Set<String> listUsedClasses(File mopFile) {
		if(debug) {
			System.out.println("Parsing file: " + mopFile.getName());
		}
		MOPSpecFile specFile = getMopFile(mopFile);

		UsedJcaClassesVisitor usedClassesVisitor = new UsedJcaClassesVisitor();
		specFile.accept(usedClassesVisitor, null);

		return usedClassesVisitor.getClasses();
	}

	private Set<MopMethod> listUsedMethods(File mopFile) {
		if(debug) {
			System.out.println("Parsing file: " + mopFile.getName());
		}
		MOPSpecFile specFile = getMopFile(mopFile);

		UsedJcaMethodsVisitor visitor = new UsedJcaMethodsVisitor();
		specFile.accept(visitor, null);

		return visitor.getMethods();
	}

	private Set<File> getMopFiles(String mopSpecsDirPath) {
		Set<File> mopFiles = new HashSet<>();
		File mopSpecsDir = new File(mopSpecsDirPath);
		if (mopSpecsDir.exists() && mopSpecsDir.isDirectory()) {
			for (File file : mopSpecsDir.listFiles()) {
				if (file.getName().toLowerCase().endsWith(MOP_SUFFIX)) {
					mopFiles.add(file);
				}
			}
		}
		return mopFiles;
	}

	private MOPSpecFile getMopFile(File mopFile) {
		MOPSpecFile specFile;
		try {
			specFile = SpecExtractor.parse(mopFile);
		} catch (MOPException e) {
			throw new RuntimeException(e);
		}
		return specFile;
	}

}

package br.unb.cic.mop.extractor;

import java.io.File;
import java.util.HashSet;
import java.util.LinkedHashSet;
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
	// Accumulated across every spec of the last listUsedMethods() call: an owner no import of
	// its own spec could resolve. Kept as observable state because "the owner was dropped" is
	// exactly the condition that used to be invisible (INV-ANA-40 log-and-skip rule).
	private final Set<String> skippedOwners = new LinkedHashSet<>();

	public Set<String> listUsedClasses(String mopSpecsDirPath, boolean debug) throws MOPException {
		this.debug = debug;
		Set<String> classes = new HashSet<>();

		getMopFiles(mopSpecsDirPath).forEach(f -> classes.addAll(listUsedClasses(f)));

		return classes;
	}

	public Set<MopMethod> listUsedMethods(String mopSpecsDirPath, boolean debug) throws MOPException {
		this.debug = debug;
		skippedOwners.clear();
		Set<MopMethod> methods = new HashSet<>();

		getMopFiles(mopSpecsDirPath).forEach(f -> methods.addAll(listUsedMethods(f)));

		return methods;
	}

	private Set<String> listUsedClasses(File mopFile) {
		MOPSpecFile specFile = getSpecFile(mopFile);

		UsedJcaClassesVisitor usedClassesVisitor = new UsedJcaClassesVisitor();
		specFile.accept(usedClassesVisitor, null);

		return usedClassesVisitor.getClasses();
	}

	/**
	 * Extract the targets of a single spec file. Public because per-spec coverage (how many
	 * specs contribute at least one static target) is a stated gate of this capability, and a
	 * directory-level call cannot answer it.
	 */
	public Set<MopMethod> listUsedMethods(File mopFile) {
		MOPSpecFile specFile = getSpecFile(mopFile);

		UsedJcaMethodsVisitor visitor = new UsedJcaMethodsVisitor();
		specFile.accept(visitor, null);
		skippedOwners.addAll(visitor.getSkippedOwners());

		return visitor.getMethods();
	}

	/** Owners skipped during the last {@link #listUsedMethods} call, across every spec parsed. */
	public Set<String> getSkippedOwners() {
		return skippedOwners;
	}

	private MOPSpecFile getSpecFile(File mopFile) {
		if(debug) {
			System.out.println("Parsing file: " + mopFile.getName());
		}
		MOPSpecFile specFile = getMopFile(mopFile);
		return specFile;
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

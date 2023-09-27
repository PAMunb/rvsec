package br.unb.cic.mop.extractor.cli;


import com.beust.jcommander.Parameter;

import br.unb.cic.mop.extractor.writer.CsvWriter;
import br.unb.cic.mop.extractor.writer.Writer;

public class CommandLineArgs {

	public enum TYPE {
		CLASSES,
		METHODS,
		METHODS_PARAMS
	}

	public enum WRITER {
		CSV(new CsvWriter());

		public final Writer writer;

	    WRITER(Writer writer) {
	        this.writer = writer;
	    }

	    public Writer getWriter() {
	    	return writer;
	    }
	}

	@Parameter(names = { "--specs-dir", "-d" }, description = "JavaMOP specifications directory (*.mop)", required = true)
	private String mopSpecsDir;

	@Parameter(names = { "--output", "-o" }, description = "Output file containing the results", required = true)
	private String outputFile;

	@Parameter(names = { "--type", "-t" }, description = "Type of output")
	private TYPE type = TYPE.METHODS;

	@Parameter(names = { "--writer", "-w" }, description = "Type of output writer")
	private WRITER writer = WRITER.CSV;

//	@Parameter(names = "--help", help = true)
//	boolean help;

	public String getMopSpecsDir() {
		return mopSpecsDir;
	}

	public String getOutputFile() {
		return outputFile;
	}

	public TYPE getType() {
		return type;
	}

	public WRITER getWriter() {
		return writer;
	}

}

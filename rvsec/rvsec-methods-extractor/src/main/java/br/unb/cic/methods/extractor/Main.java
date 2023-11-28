package br.unb.cic.methods.extractor;

import com.beust.jcommander.JCommander;

import br.unb.cic.methods.extractor.cli.CommandLineArgs;

public class Main {
	
	public static void main(String[] args) {
		CommandLineArgs jArgs = new CommandLineArgs();
		
		JCommander jc = JCommander.newBuilder().addObject(jArgs).build();
		jc.parse(args);
				
		if(jArgs.isHelp()) {
			jc.usage();
			System.exit(0);
		}		

		MethodsExtractor extractor = new MethodsExtractor();
		extractor.execute(jArgs.getApk(), jArgs.getAppPackage(), jArgs.getAndroidPlatformsDir(), 
				jArgs.getOutputFile(), !jArgs.isIncludeConstructors(), !jArgs.isIncludeStaticInitializers());
	
		System.out.println("Done!");
	}

}

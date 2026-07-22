package br.unb.cic.mop;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugins.annotations.LifecyclePhase;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;

@Mojo(name = "mop-gen", defaultPhase = LifecyclePhase.GENERATE_SOURCES)
public class MOPGen extends AbstractMojo {

	private static final String SRC_MAIN_JAVA_MOP = "." + File.separator + "src" + File.separator + "main" + File.separator + "java" + File.separator + "mop";

	@Parameter(property = "pathToJavaMop", required = true)
    private String pathToJavaMop;

    @Parameter(property = "pathToMonitor", required = true)
    private String pathToMonitor;

    @Parameter(property = "pathToMopFiles", required = true)
    private String pathToMopFiles;

    @Parameter(property = "destinationFolder")
    private String destinationFolder = SRC_MAIN_JAVA_MOP;

    @Parameter(property = "skipMopAgent")
    private boolean skipMopAgent = false;
    
    @Parameter(property = "generateMopStatistics")
    private boolean generateMopStatistics = true;


    @Override
    public void execute() throws MojoExecutionException {
    	if(skipMopAgent) {
    		getLog().info("MopGen skipped.");
    		return;
    	}
        try {
            getLog().info("--------------------------------------------------------");
            getLog().info("Excluding previously generated files");
            getLog().info("--------------------------------------------------------");
            removeGeneratedJavaFiles();
            removeGeneratedMonitorFiles();
            executeJavaMop();
            executeRVMonitor();
        } catch(IOException e) {
            throw new MojoExecutionException(e.getMessage());
        }
    }

    private void executeJavaMop() throws MojoExecutionException, IOException  {
        getLog().info("--------------------------------------------------------");
        getLog().info("Executing javamop -merge " + pathToMopFiles + File.separator + "*.mop");
        getLog().info("--------------------------------------------------------");

        List<String> args = new ArrayList<>();
        args.add(pathToJavaMop + File.separator + "javamop");
        if(generateMopStatistics) {
            args.add("-s");
        }
        args.add("-merge");
        args.add(pathToMopFiles + File.separator + "*.mop");
        
        ProcessUtil.executeExternalProgram(getLog(), args.toArray(new String[0]));
    }

    private void executeRVMonitor() throws MojoExecutionException, IOException {
        getLog().info("--------------------------------------------------------");
        getLog().info("Executing rv-monitor -merge " + pathToMopFiles + File.separator + "*.rvm");
        getLog().info("--------------------------------------------------------");

        List<String> args = new ArrayList<>();
        args.add(pathToMonitor + File.separator + "rv-monitor");
        if(generateMopStatistics) {
            args.add("-s");
        }
        args.add("-merge");
        args.add("-d");
        args.add(destinationFolder);
        args.add(pathToMopFiles + File.separator + "*.rvm");
        
        ProcessUtil.executeExternalProgram(getLog(), args.toArray(new String[0]));
    }

    private void removeGeneratedMonitorFiles() {
        File dest = new File(pathToMopFiles);
        if(dest.exists() && dest.isDirectory()) {
        	File[] files = dest.listFiles((d,f) ->
        			f.toLowerCase().startsWith("MultiSpec")
        			|| f.toLowerCase().endsWith(".rvm"));
            deleteFiles(files);
        }
    }

    private void removeGeneratedJavaFiles() {
        File dest = new File(destinationFolder);
        if(dest.exists() && dest.isDirectory()) {
        	File[] files = dest.listFiles((d,f)-> f.toLowerCase().endsWith(".java"));
            deleteFiles(files);
        }
    }

	private void deleteFiles(File[] files) {
		for(File f: files) {
		    f.delete();
		}
	}

}
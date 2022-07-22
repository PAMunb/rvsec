package br.unb.cic.mop;

import java.io.File;
import java.util.List;
import java.util.stream.Collectors;

import org.apache.maven.model.Dependency;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugins.annotations.LifecyclePhase;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.project.MavenProject;

@Mojo(name = "agent-gen", defaultPhase = LifecyclePhase.PROCESS_CLASSES)
public class AgentGen extends AbstractMojo {

    private static final String TARGET_CLASSES = File.separator + "target" + File.separator + "classes";

    @Parameter(defaultValue = "${project}", required = true, readonly = true)
    private MavenProject project;

    @Parameter(property = "path-to-java-mop")
    private String pathToJavaMop;

    @Parameter(property = "path-to-mop-files")
    private String pathToMopFiles;

    @Parameter(property = "skipMopAgent")
    private boolean skipMopAgent = false;

    @Override
    public void execute() throws MojoExecutionException {
        if (skipMopAgent) {
            getLog().info("AgentGen skipped.");
            return;
        }
        try {
            List<Dependency> cp = project.getDependencies();
            StringBuilder sb = new StringBuilder();

            String classpath = cp.stream()
                    .map(this::artifact)
                    .collect(Collectors.joining(":"));

            sb.append(classpath);
            sb.append(project.getBasedir() + TARGET_CLASSES);

            getLog().info("--------------------------------------------------------");
            getLog().info("Executing javamopagent " + pathToMopFiles + File.separator + "*.aj");
            getLog().info("--------------------------------------------------------");

            ProcessUtil.addVariable("CLASSPATH", sb.toString());

            ProcessUtil.executeExternalProgram(getLog(), pathToJavaMop + File.separator+ "javamopagent",
                    pathToMopFiles + File.separator + "*.aj",
                    project.getBasedir() + TARGET_CLASSES, //"-v",
                    "-n",
                    "JavaMOPAgent");

        } catch (Exception e) {
            getLog().error(e);
            throw new MojoExecutionException(e.getMessage());
        }
    }

    private String artifact(Dependency d) {
        String path =  String.format("~/.m2/repository/%s/%s/%s/%s-%s.jar",
                d.getGroupId().replace(".", File.separator),
                d.getArtifactId(),
                d.getVersion(),
                d.getArtifactId(),
                d.getVersion());
        return path.replace("/", File.separator);
    }
}

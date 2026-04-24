package br.unb.cic.rv.descriptor;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Collections;
import java.util.List;

/**
 * Root of the JSON descriptor emitted by patched JavaMOP ({@code --emit-descriptor}).
 *
 * <p>Mirrors the Map produced by
 * {@code javamop.output.descriptor.DescriptorWriter#buildAspect}.
 */
public final class AspectDescriptor {

    private String aspectName;
    private String fileName;
    private String shortName;
    @JsonProperty("package")
    private String packageDecl;
    private List<String> imports = Collections.emptyList();
    private String commonPointcut;
    private List<String> baseAspectExclusions = Collections.emptyList();
    private List<AdviceDescriptor> advices = Collections.emptyList();

    public String getAspectName() { return aspectName; }
    public void setAspectName(String aspectName) { this.aspectName = aspectName; }

    public String getFileName() { return fileName; }
    public void setFileName(String fileName) { this.fileName = fileName; }

    public String getShortName() { return shortName; }
    public void setShortName(String shortName) { this.shortName = shortName; }

    public String getPackageDecl() { return packageDecl; }
    public void setPackageDecl(String packageDecl) { this.packageDecl = packageDecl; }

    public List<String> getImports() { return imports; }
    public void setImports(List<String> imports) { this.imports = imports; }

    public String getCommonPointcut() { return commonPointcut; }
    public void setCommonPointcut(String commonPointcut) { this.commonPointcut = commonPointcut; }

    public List<String> getBaseAspectExclusions() { return baseAspectExclusions; }
    public void setBaseAspectExclusions(List<String> v) { this.baseAspectExclusions = v; }

    public List<AdviceDescriptor> getAdvices() { return advices; }
    public void setAdvices(List<AdviceDescriptor> advices) { this.advices = advices; }
}

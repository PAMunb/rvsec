package br.unb.cic.rv.cli;

import br.unb.cic.rv.builder.BuilderConfig;
import br.unb.cic.rv.merger.MergerConfig;

import java.nio.file.Path;
import java.util.List;

/**
 * Effective configuration after {@link ConfigResolver} merges CLI flags,
 * environment variables, config file, and defaults.
 */
public record EffectiveConfig(
        Path descriptorPath,
        Path androidJar,
        Path workDir,
        Path outputDir,
        List<Path> apkDexes,         // extracted from the input APK before weaving
        BuilderConfig builderConfig,
        MergerConfig mergerConfig,
        Path monitorSrcDir,          // rv-monitor-generated .java sources (null → skip build+sign)
        boolean enableCoverage,
        Path keystorePath,
        String logLevel
) {
}

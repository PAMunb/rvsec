"""Quantificar o impacto da quarantine (gh50 §16) nas violações detectadas.

A quarantine move classes conhecidas por crashar ajc/d8 (okio, media3, tika,
licensing, bouncycastle, web3j, tink) para fora do processo de weaving. Logo:
- Call-sites no APP code são instrumentados normalmente (violações detectáveis)
- Chamadas MOP INTERNAS dessas libs não recebem aspectos (violações perdidas)

Este script cruza as violações registradas pelo paper contra os padrões de
quarantine para quantificar quantas violações SÃO ESPERADAMENTE perdidas pelo
novo pipeline.

Input:
- Paper errors: exp01_jca_errors.csv (coluna `class` identifica onde disparou)
- Quarantine YAML: modules/rv-instrumentation-ajc/assets/weaving_excludes.yaml

Output:
- data/results/jca557_quarantine_impact.csv (violação por violação, flag quarantined)
- data/results/jca557_quarantine_impact.md (resumo agregado)

Usage:
    uv run python scripts/jca557_quarantine_impact.py

See: docs/20260422_executar_dataset_antigo.md §6.3
"""

import fnmatch
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "data" / "results"
PAPER_DIR = Path(
    "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/"
    "workspace-rv/ase-journal-jss-jca/dataset/results"
)
QUARANTINE_YAML = ROOT / "modules" / "rv-instrumentation-ajc" / "assets" / "weaving_excludes.yaml"

OUTPUT_CSV = RESULTS_DIR / "jca557_quarantine_impact.csv"
OUTPUT_MD = RESULTS_DIR / "jca557_quarantine_impact.md"


def load_quarantine_patterns():
    """Load quarantine YAML or fallback to embedded defaults."""
    if yaml and QUARANTINE_YAML.exists():
        with open(QUARANTINE_YAML) as f:
            data = yaml.safe_load(f) or {}
        patterns = data.get("patterns", [])
    else:
        # Fallback: padrões conhecidos (gh50 §16)
        patterns = [
            "okio/**/*.class",
            "androidx/media3/datasource/**/*.class",
            "androidx/media3/exoplayer/drm/**/*.class",
            "org/apache/tika/**/*.class",
            "com/google/android/vending/licensing/AESObfuscator*.class",
            "com/google/crypto/tink/subtle/AesGcmJce*.class",
            "org/bouncycastle/**/*.class",
        ]
    # Convert slash-style paths to dot-style class names for matching
    converted = []
    for p in patterns:
        # okio/**/*.class → okio.**
        # com/google/crypto/tink/subtle/AesGcmJce*.class → com.google.crypto.tink.subtle.AesGcmJce*
        dot_pattern = p.replace("/", ".").removesuffix(".class")
        converted.append(dot_pattern)
    return patterns, converted


def is_quarantined(class_fqn: str, patterns_dot: list[str]) -> str | None:
    """Return the matching quarantine pattern, or None if not quarantined."""
    for pat in patterns_dot:
        # fnmatch handles * and **
        if fnmatch.fnmatch(class_fqn, pat) or fnmatch.fnmatch(class_fqn, f"{pat}*"):
            return pat
    return None


def classify_code_origin(class_fqn: str, app_package: str | None) -> str:
    """Label as app-code / lib-code / framework-code."""
    if class_fqn.startswith("android.") or class_fqn.startswith("androidx."):
        # Framework (but watch: some androidx is lib — e.g., androidx.media3 is partly lib)
        if class_fqn.startswith("androidx.media3") or class_fqn.startswith("androidx.compose"):
            return "lib"
        return "framework"
    if class_fqn.startswith("java.") or class_fqn.startswith("javax.") or class_fqn.startswith("kotlin."):
        return "framework"
    if app_package and class_fqn.startswith(app_package):
        return "app"
    return "lib"


def main():
    patterns_slash, patterns_dot = load_quarantine_patterns()
    print(f"Loaded {len(patterns_dot)} quarantine patterns")

    errors_path = PAPER_DIR / "errors" / "exp01_jca_errors.csv"
    apks_path = PAPER_DIR / "apks" / "apks_complete.csv"
    if not errors_path.exists():
        print(f"ERROR: {errors_path} not found")
        sys.exit(1)

    errors = pd.read_csv(errors_path)
    apks_meta = pd.read_csv(apks_path) if apks_path.exists() else pd.DataFrame()

    # Build apk → manifest_package lookup
    apk_pkg = {}
    if not apks_meta.empty and "manifest_package" in apks_meta.columns:
        apk_pkg = dict(zip(apks_meta["apk"], apks_meta["manifest_package"]))

    print(f"Paper errors: {len(errors)} rows, {errors['apk'].nunique()} unique APKs")

    # Enrich each error row with origin + quarantine flag
    origins, quarantine_pats = [], []
    for _, r in errors.iterrows():
        cls = str(r.get("class", ""))
        pkg = apk_pkg.get(r["apk"])
        origins.append(classify_code_origin(cls, pkg))
        quarantine_pats.append(is_quarantined(cls, patterns_dot) or "")
    errors = errors.copy()
    errors["origin"] = origins
    errors["quarantine_pattern"] = quarantine_pats
    errors["is_quarantined"] = errors["quarantine_pattern"] != ""

    # Save enriched CSV
    errors.to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote enriched CSV: {OUTPUT_CSV}")

    # Aggregates
    total = len(errors)
    by_origin = Counter(errors["origin"])
    quarantined_count = int(errors["is_quarantined"].sum())
    quarantined_by_pattern = Counter(p for p in errors["quarantine_pattern"] if p)
    quarantined_by_spec = Counter(
        errors[errors["is_quarantined"]]["spec"]
    )

    # Distinct APKs with ≥1 quarantined violation
    apks_with_quarantined = set(errors[errors["is_quarantined"]]["apk"].unique())

    # Report markdown
    lines = []
    lines.append("# Impacto da quarantine (gh50 §16) nas violações do paper ASE/JSS")
    lines.append("")
    lines.append(f"- Total violações do paper: **{total}** (em {errors['apk'].nunique()} APKs)")
    lines.append(f"- Violações em classes **quarantined**: **{quarantined_count}** "
                 f"({100*quarantined_count/total:.1f}%)")
    lines.append(f"- APKs com ≥1 violação quarantined: **{len(apks_with_quarantined)}** "
                 f"({100*len(apks_with_quarantined)/errors['apk'].nunique():.1f}% dos 188)")
    lines.append("")
    lines.append("## Distribuição por origem do código")
    lines.append("")
    lines.append("| Origem | Count | % |")
    lines.append("|---|---:|---:|")
    for origin in ["app", "lib", "framework"]:
        c = by_origin.get(origin, 0)
        lines.append(f"| {origin} | {c} | {100*c/total:.1f}% |")
    lines.append("")
    lines.append("## Quarantine breakdown por pattern")
    lines.append("")
    if quarantined_by_pattern:
        lines.append("| Pattern | Count | % de total |")
        lines.append("|---|---:|---:|")
        for pat, c in quarantined_by_pattern.most_common():
            lines.append(f"| `{pat}` | {c} | {100*c/total:.2f}% |")
    else:
        lines.append("_Nenhuma violação em classes quarantined no paper._")
    lines.append("")
    lines.append("## Quarantine breakdown por spec")
    lines.append("")
    if quarantined_by_spec:
        lines.append("| Spec | Violações quarantined |")
        lines.append("|---|---:|")
        for spec, c in quarantined_by_spec.most_common():
            lines.append(f"| {spec} | {c} |")
    else:
        lines.append("_Sem dados._")
    lines.append("")
    lines.append("## Interpretação")
    lines.append("")
    lines.append("Violações em classes quarantined são **esperadamente perdidas** pelo novo ")
    lines.append("pipeline (gh50 §16), pois essas classes não recebem aspect weaving. ")
    lines.append("Porém, chamadas `call()` do JavaMOP no **app code que invoca essas libs** ")
    lines.append("continuam instrumentadas — portanto a violação ainda pode ser detectada ")
    lines.append("no caller-site, não no callee-site interno da lib.")
    lines.append("")

    OUTPUT_MD.write_text("\n".join(lines))
    print(f"Wrote report: {OUTPUT_MD}")

    print("\nSummary:")
    print(f"  total violações paper:    {total}")
    print(f"  em classes quarantined:   {quarantined_count} ({100*quarantined_count/total:.1f}%)")
    print(f"  por origem: {dict(by_origin)}")
    print(f"  top patterns: {dict(quarantined_by_pattern.most_common(5))}")


if __name__ == "__main__":
    main()

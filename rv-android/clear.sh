#!/bin/sh

# RV-Android Cleanup Script
# WARNING: This script removes directories with experiment artifacts and temporary files

# New directory structure
OUT_DIR="out"                    # Default output directory (temporary artifacts)
LIB_TMP="lib_tmp"                # Maven dependencies
TMP_DIR="tmp"                    # Temporary files
RVM_TMP_DIR="rvm_tmp"            # RVM temporary files
RESULTS_DIR="results"            # Experiment results (persistent)
SOOT_OUTPUT="sootOutput"         # Soot compiler output

# Legacy directories (for compatibility)
OUTPUT_DIR="output"              # Legacy output directory
MOP_OUT="mop_out"                # Legacy generated monitors directory

# Parse command line arguments
CLEAN_RESULTS=false
for arg in "$@"; do
    case $arg in
        --clean-results)
            CLEAN_RESULTS=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--clean-results] [--help]"
            echo ""
            echo "Clean RV-Android experiment artifacts and temporary files"
            echo ""
            echo "Options:"
            echo "  --clean-results    Also remove experiment results directory"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Directories cleaned:"
            echo "  - $OUT_DIR/ (default output directory with monitors/, instrumented_apks/, static_analysis/)"
            echo "  - */monitors/, */instrumented_apks/, */static_analysis/ (experiment artifacts in any output directory)"
            echo "  - $OUTPUT_DIR, $MOP_OUT (legacy directories for compatibility)"
            echo "  - $TMP_DIR, $RVM_TMP_DIR (temporary files)"
            echo "  - $LIB_TMP (maven dependencies)"
            echo "  - __pycache__, $SOOT_OUTPUT (build artifacts)"
            echo "  - *.dex, ajcore*.txt (compilation artifacts)"
            if [ "$CLEAN_RESULTS" = true ]; then
                echo "  - $RESULTS_DIR (experiment results) [--clean-results flag]"
            fi
            echo ""
            echo "Note: Use 'modules/clean.sh' to clean module build artifacts"
            exit 0
            ;;
    esac
done

echo "[+] Cleaning RV-Android artifacts..."

# Standard cleanup (always performed)
echo "    Removing temporary and build directories..."
rm -rvf __pycache__ $TMP_DIR $RVM_TMP_DIR $LIB_TMP $SOOT_OUTPUT

# Remove default output directory and its subdirectories
echo "    Removing default output directory and experiment artifacts..."
rm -rvf $OUT_DIR

# Remove legacy directories for compatibility
echo "    Removing legacy directories..."
rm -rvf $OUTPUT_DIR $MOP_OUT

# Remove experiment artifacts from any custom output directories
echo "    Removing experiment artifacts from custom directories..."
find . -maxdepth 2 -type d \( -name "monitors" -o -name "instrumented_apks" -o -name "static_analysis" \) -exec rm -rvf {} + 2>/dev/null || true

echo "    Removing compilation artifacts..."
rm -f *.dex ajcore*.txt 2>/dev/null

# Optional results cleanup
if [ "$CLEAN_RESULTS" = true ]; then
    echo "    Removing experiment results..."
    rm -rf $RESULTS_DIR
fi

echo "[+] Cleanup completed successfully"
echo "    Cleaned: default output directory ($OUT_DIR/), legacy directories, and experiment artifacts"
echo "    Use './clear.sh --clean-results' to also remove persistent experiment results ($RESULTS_DIR/)"
echo "    Use 'modules/clean.sh' to clean module build artifacts"
echo "    Note: Custom output directories are also cleaned of experiment artifacts"

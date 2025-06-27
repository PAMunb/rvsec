#!/bin/sh

# RV-Android Cleanup Script
# WARNING: This script removes directories with experiment artifacts and temporary files

OUT_DIR="out"                    # Instrumented APKs directory  
OUTPUT_DIR="output"              # Output directory for monitors and instrumented APKs
LIB_TMP="lib_tmp"                # Maven dependencies
MOP_OUT="mop_out"                # Generated monitors (legacy)
TMP_DIR="tmp"                    # Temporary files
RVM_TMP_DIR="rvm_tmp"            # RVM temporary files
RESULTS_DIR="results"            # Experiment results
SOOT_OUTPUT="sootOutput"         # Soot compiler output

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
            echo "  - $OUT_DIR (instrumented APKs)"
            echo "  - $OUTPUT_DIR (output directory for monitors and instrumented APKs)"
            echo "  - $MOP_OUT (generated monitors - legacy)"
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
rm -rf __pycache__ $TMP_DIR $RVM_TMP_DIR $LIB_TMP $OUT_DIR $OUTPUT_DIR $MOP_OUT $SOOT_OUTPUT

echo "    Removing compilation artifacts..."
rm -f *.dex ajcore*.txt 2>/dev/null

# Optional results cleanup
if [ "$CLEAN_RESULTS" = true ]; then
    echo "    Removing experiment results..."
    rm -rf $RESULTS_DIR
fi

echo "[+] Cleanup completed successfully"
echo "    Use './clear.sh --clean-results' to also remove experiment results"
echo "    Use 'modules/clean.sh' to clean module build artifacts"

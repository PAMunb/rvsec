#!/bin/bash

# Module Installer for RV-Android
# Uses Poetry workspace (root pyproject.toml with develop=true dependencies)
# All modules are installed in editable mode via single `poetry install` at root

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Colors for output
declare -r RED='\033[0;31m'
declare -r GREEN='\033[0;32m'
declare -r YELLOW='\033[0;33m'
declare -r BLUE='\033[0;34m'
declare -r CYAN='\033[0;36m'
declare -r NC='\033[0m'

# Root directory (parent of modules)
declare -r ROOT_DIR=".."

# Global configuration
declare -g VERBOSE=false
declare -g SYNC_MODE=false

# ============================================================================
# LOGGING
# ============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step() { echo -e "${CYAN}[STEP]${NC} $*"; }

print_header() {
    echo
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${CYAN} RV-Android Module Installer (Poetry Workspace)${NC}"
    echo -e "${CYAN}============================================================================${NC}"
    echo
}

error_exit() {
    log_error "$1"
    exit "${2:-1}"
}

# ============================================================================
# VALIDATION
# ============================================================================

validate_environment() {
    log_step "Validating environment"

    # Check if we're in the modules directory
    if [[ ! -f "install.sh" ]] || [[ ! -d "rv-android-core" ]]; then
        error_exit "Must run from the modules directory"
    fi

    # Check root pyproject.toml exists
    if [[ ! -f "$ROOT_DIR/pyproject.toml" ]]; then
        error_exit "Root pyproject.toml not found at $ROOT_DIR/pyproject.toml"
    fi

    # Check Poetry availability
    if ! command -v poetry &> /dev/null; then
        error_exit "Poetry is required but not found"
    fi

    log_success "Environment validated"
}

# ============================================================================
# INSTALLATION
# ============================================================================

install_workspace() {
    log_step "Installing all modules via Poetry workspace"

    cd "$ROOT_DIR"

    local poetry_cmd="poetry install"
    if [[ "$SYNC_MODE" == "true" ]]; then
        poetry_cmd="poetry install --sync"
    fi

    log_info "Running: $poetry_cmd"

    if [[ "$VERBOSE" == "true" ]]; then
        if $poetry_cmd; then
            log_success "All modules installed in editable mode"
        else
            error_exit "Poetry install failed"
        fi
    else
        if $poetry_cmd 2>&1 | grep -E "(Installing|Updating|Removing|Already installed)" || true; then
            log_success "All modules installed in editable mode"
        else
            error_exit "Poetry install failed. Run with --verbose for details."
        fi
    fi

    cd - > /dev/null
}

verify_installation() {
    log_step "Verifying installation"

    cd "$ROOT_DIR"

    # Check that key modules are importable
    local modules=("rv_android_core" "rv_agent" "rv_experiment" "rv_platform")
    local failed=0

    for module in "${modules[@]}"; do
        if poetry run python -c "import $module" 2>/dev/null; then
            log_info "  ✓ $module"
        else
            log_warning "  ✗ $module (import failed)"
            ((failed++))
        fi
    done

    cd - > /dev/null

    if [[ $failed -gt 0 ]]; then
        log_warning "$failed modules failed to import"
        return 1
    fi

    log_success "All key modules verified"
    return 0
}

# ============================================================================
# ARGUMENT PARSING
# ============================================================================

print_usage() {
    cat << 'EOF'
Usage: ./install.sh [OPTIONS] [MODULES...]

Poetry workspace installer for RV-Android.
Installs all modules in editable mode via root pyproject.toml.

OPTIONS:
    --verbose       Show detailed output
    --sync          Use poetry install --sync (remove unused packages)
    --verify        Only verify installation, don't install
    --help, -h      Show this help message

MODULES:
    Module arguments are accepted for backwards compatibility but ignored.
    All modules are always installed together via the workspace.

EXAMPLES:
    ./install.sh                    # Install all modules
    ./install.sh --verbose          # Install with detailed output
    ./install.sh --sync             # Install and remove unused packages
    ./install.sh --verify           # Only verify current installation

NOTE:
    This script uses Poetry workspaces. All modules are defined in the root
    pyproject.toml with 'develop = true', ensuring editable installation.
    Changes to source files are immediately reflected without reinstalling.

EOF
}

parse_arguments() {
    local verify_only=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose)
                VERBOSE=true
                shift
                ;;
            --sync)
                SYNC_MODE=true
                shift
                ;;
            --verify)
                verify_only=true
                shift
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            -*)
                error_exit "Unknown option: $1"
                ;;
            *)
                # Accept module names for backwards compatibility but ignore
                log_info "Module '$1' specified (ignored - workspace installs all modules)"
                shift
                ;;
        esac
    done

    if [[ "$verify_only" == "true" ]]; then
        validate_environment
        verify_installation
        exit $?
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    print_header

    parse_arguments "$@"

    log_info "Mode: Poetry workspace (editable install)"
    log_info "Verbose: $VERBOSE"
    log_info "Sync: $SYNC_MODE"
    echo

    validate_environment
    install_workspace
    verify_installation

    echo
    log_success "Installation complete!"
    log_info "All modules are installed in editable mode."
    log_info "Source changes are reflected immediately - no reinstall needed."
}

main "$@"

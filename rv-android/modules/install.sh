#!/bin/bash

# Module Installer for RV-Android
# Manages installation and validation of monitored operations modules
# Complete rewrite with modern bash practices and comprehensive error handling

set -euo pipefail  # Strict error handling

# ============================================================================
# CONFIGURATION
# ============================================================================

# Static module list in dependency order - no dynamic discovery
declare -ra MODULES=(
    "rv-android-core"           # Foundation - core utilities and domain models
    "rv-monitor-generator"      # Monitor generation from MOP specifications  
    "rv-instrumentation"        # APK instrumentation with monitors
    "rv-static-analysis"        # Static analysis tools (GATOR, GESDA, REACH)
    "rv-coverage"               # Coverage analysis tools
    "rv-screen-parser"          # Screen parsing utilities
    "rv-llm"                    # Language Model integration infrastructure
    "rv-tools"                  # Tool registry and plugin system
    "rvandroid-tool"            # RVAndroid tool implementation with LLM integration
    "rv-experiment"             # Experiment orchestration and coordination
#    "rvandroid"                 # Main framework module
)

# Colors for output (with fallbacks for non-color terminals)
declare -r RED='\033[0;31m'
declare -r GREEN='\033[0;32m'
declare -r YELLOW='\033[0;33m'
declare -r BLUE='\033[0;34m'
declare -r PURPLE='\033[0;35m'
declare -r CYAN='\033[0;36m'
declare -r NC='\033[0m' # No Color

# Global configuration
declare -g DRY_RUN=false
declare -g VERBOSE=false
declare -g SELECTED_MODULES=()

# ============================================================================
# LOGGING AND OUTPUT
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $*"
    fi
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $*"
}

print_header() {
    echo
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${CYAN} RV-Android Module Installer${NC}"
    echo -e "${CYAN} Modern installation of monitored operations modules${NC}"
    echo -e "${CYAN}============================================================================${NC}"
    echo
}

print_separator() {
    echo -e "${CYAN}----------------------------------------------------------------------------${NC}"
}

# ============================================================================
# ERROR HANDLING
# ============================================================================

error_exit() {
    local exit_code=${2:-1}
    log_error "$1"
    log_error "Installation failed. Check the error above for details."
    exit "$exit_code"
}

validate_environment() {
    log_step "Validating installation environment"
    
    # Check if we're in the modules directory
    if [[ ! -f "install.sh" ]] || [[ ! -d "rv-android-core" ]]; then
        error_exit "Must run from the modules directory containing install.sh"
    fi
    
    # Check Poetry availability
    if ! command -v poetry &> /dev/null; then
        error_exit "Poetry is required but not found. Please install Poetry first."
    fi
    
    # Check Poetry version (basic check)
    local poetry_version
    poetry_version=$(poetry --version 2>/dev/null | cut -d' ' -f3 || echo "unknown")
    log_debug "Found Poetry version: $poetry_version"
    
    log_success "Environment validation passed"
}

validate_module() {
    local module="$1"
    log_debug "Validating module: $module"
    
    # Check if module directory exists
    if [[ ! -d "$module" ]]; then
        log_error "Module directory not found: $module"
        return 1
    fi
    
    # Check if pyproject.toml exists
    if [[ ! -f "$module/pyproject.toml" ]]; then
        log_error "pyproject.toml not found in: $module"
        return 1
    fi
    
    log_debug "Module validation passed: $module"
    return 0
}

# ============================================================================
# INSTALLATION LOGIC
# ============================================================================

install_module() {
    local module="$1"
    
    log_step "Installing module: $module"
    
    # Validate module before installation
    if ! validate_module "$module"; then
        return 1
    fi
    
    # Change to module directory
    if ! cd "$module"; then
        log_error "Failed to enter directory: $module"
        return 1
    fi
    
    # Dry run mode
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would install: $module"
        cd ..
        return 0
    fi
    
    # Execute poetry install with error handling
    log_debug "Executing: poetry install"
    
    if [[ "$VERBOSE" == "true" ]]; then
        if poetry install; then
            log_success "Successfully installed: $module"
        else
            log_error "Failed to install: $module"
            cd ..
            return 1
        fi
    else
        if poetry install >/dev/null 2>&1; then
            log_success "Successfully installed: $module"
        else
            log_error "Failed to install: $module"
            log_error "Run with --verbose for detailed error output"
            cd ..
            return 1
        fi
    fi
    
    # Return to parent directory
    cd ..
    return 0
}

verify_installation() {
    local module="$1"
    
    log_debug "Verifying installation: $module"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    # Change to module directory
    if ! cd "$module"; then
        log_error "Failed to enter directory for verification: $module"
        return 1
    fi
    
    # Check if poetry environment exists and is valid
    if poetry env info --path >/dev/null 2>&1; then
        log_debug "Poetry environment verified: $module"
        cd ..
        return 0
    else
        log_warning "Poetry environment verification failed: $module"
        cd ..
        return 1
    fi
}

install_all_modules() {
    local modules_to_install=("$@")
    local failed_modules=()
    local installed_count=0
    
    log_info "Installing ${#modules_to_install[@]} modules in dependency order"
    print_separator
    
    for module in "${modules_to_install[@]}"; do
        echo
        if install_module "$module"; then
            if verify_installation "$module"; then
                ((installed_count++))
            else
                failed_modules+=("$module (verification failed)")
            fi
        else
            failed_modules+=("$module (installation failed)")
        fi
    done
    
    # Report results
    print_separator
    log_info "Installation Summary:"
    log_success "Successfully installed: $installed_count modules"
    
    if [[ ${#failed_modules[@]} -gt 0 ]]; then
        log_error "Failed modules: ${#failed_modules[@]}"
        for failed in "${failed_modules[@]}"; do
            log_error "  - $failed"
        done
        return 1
    fi
    
    return 0
}

# ============================================================================
# ARGUMENT PARSING
# ============================================================================

print_usage() {
    cat << 'EOF'
Usage: ./install.sh [OPTIONS] [MODULES...]

Modern installer for RV-Android monitored operations modules.
Supports experiments with JCA cryptography specifications and generic runtime specifications.

OPTIONS:
    --dry-run           Validate without installing
    --verbose           Enable detailed logging output
    --help, -h          Show this help message

MODULES:
    If no modules specified, installs all modules in dependency order.
    Available modules:
        rv-android-core           Core utilities and domain models
        rv-monitor-generator      Monitor generation from MOP specifications
        rv-instrumentation        APK instrumentation with monitors
        rv-static-analysis        Static analysis tools (GATOR, GESDA, REACH)
        rv-coverage              Coverage analysis tools
        rv-screen-parser         Screen parsing utilities
        rv-llm                   Language Model integration infrastructure
        rv-tools                 Tool registry and plugin system
        rvandroid-tool           RVAndroid tool implementation with LLM integration
        rv-experiment            Experiment orchestration and coordination
        rvandroid               Main framework module

EXAMPLES:
    ./install.sh                                    # Install all modules
    ./install.sh rv-android-core rv-static-analysis # Install specific modules
    ./install.sh --dry-run                          # Validate without installing
    ./install.sh --verbose rv-instrumentation       # Verbose installation

EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
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
                # Check if it's a valid module
                local valid_module=false
                for module in "${MODULES[@]}"; do
                    if [[ "$1" == "$module" ]]; then
                        valid_module=true
                        break
                    fi
                done
                
                if [[ "$valid_module" == "true" ]]; then
                    SELECTED_MODULES+=("$1")
                else
                    error_exit "Invalid module: $1"
                fi
                shift
                ;;
        esac
    done
    
    # If no modules selected, use all modules
    if [[ ${#SELECTED_MODULES[@]} -eq 0 ]]; then
        SELECTED_MODULES=("${MODULES[@]}")
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    print_header
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Show configuration
    log_info "Configuration:"
    log_info "  Dry run: $DRY_RUN"
    log_info "  Verbose: $VERBOSE"
    log_info "  Modules: ${SELECTED_MODULES[*]}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN MODE - No actual installation will be performed"
    fi
    
    echo
    
    # Validate environment
    validate_environment
    
    # Install modules
    if install_all_modules "${SELECTED_MODULES[@]}"; then
        echo
        log_success "All modules installed successfully!"
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "Re-run without --dry-run to perform actual installation"
        fi
        exit 0
    else
        echo
        error_exit "Some modules failed to install"
    fi
}

# Execute main function with all arguments
main "$@"
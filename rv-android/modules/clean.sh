#!/bin/bash

# Clean Manager for RV-Android
# Manages cleanup of virtual environments, caches, and build artifacts
# Restores modules to "original code" state (git-like state with modifications)

set -euo pipefail  # Strict error handling

# ============================================================================
# CONFIGURATION
# ============================================================================

# Static module list in dependency order - same as install.sh
declare -ra MODULES=(
    "rv-android-core"           # Foundation - core utilities and domain models
    "rv-monitor-generator"      # Monitor generation from MOP specifications
    "rv-instrumentation-core"   # Pure abstractions: Instrumenter ABC + shared types
    "rv-instrumentation"        # Parent canonical: factory + shared keystore
    "rv-instrumentation-ajc"    # AspectJ-based instrumentation variant
    "rv-instrumentation-dexlib2" # DEX-native instrumentation variant (gh52)
    "rv-static-analysis"        # Static analysis tools (GATOR, GESDA, REACH)
    "rv-coverage"               # Coverage analysis tools
    "rv-screen-parser"          # Screen parsing utilities
    "rv-tools"                  # Tool registry and plugin system
    "rv-uiautomator"           # Shared UIAutomator components for device interaction
    "rv-platform"               # Central execution platform for Android experiments
    "rv-agent"                  # LLM-driven agentic testing with LangGraph
    "rvagent-tool"              # RVAgent tool plugin for rv-tools registry
    "aperv-tool"                # APE-RV tool plugin for rv-tools registry
    "rv-experiment"             # Experiment orchestration and coordination
    "aperv-llm-validation"      # APE-RV LLM validation (temporary)
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
declare -g DEEP_CLEAN=false

# Files and directories to clean (per module)
declare -ra CLEAN_TARGETS=(
    ".venv"                     # Virtual environments
    "__pycache__"               # Python bytecode cache
    "*.pyc"                     # Compiled Python files
    "*.pyo"                     # Optimized Python files
    "*.pyd"                     # Python extension modules
    ".pytest_cache"             # Pytest cache
    ".coverage"                 # Coverage data files
    "htmlcov"                   # Coverage HTML reports
    ".mypy_cache"               # MyPy cache
    ".ruff_cache"               # Ruff linter cache
    "dist"                      # Build distributions
    "build"                     # Build artifacts
    "*.egg-info"                # Package metadata
    ".tox"                      # Tox environments
    "node_modules"              # Node.js modules (if any)
    ".DS_Store"                 # macOS metadata files
    "Thumbs.db"                 # Windows thumbnail cache
)

# Additional clean targets for deep clean
declare -ra DEEP_CLEAN_TARGETS=(
    "*.log"                     # Log files
    "*.tmp"                     # Temporary files
    "temp"                      # Temporary directories
    ".temp"                     # Hidden temporary directories
)

# Experiment-specific directories to clean
declare -ra EXPERIMENT_TARGETS=(
    "out"                       # Experiment output directories
    "results"                   # Experiment results
    "mop_out"                   # Monitor output
)

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
    echo -e "${CYAN} RV-Android Clean Manager${NC}"
    echo -e "${CYAN} Cleanup virtual environments, caches, and build artifacts${NC}"
    echo -e "${CYAN}============================================================================${NC}"
    echo
}

print_separator() {
    echo -e "${CYAN}----------------------------------------------------------------------------${NC}"
}

print_clean_result() {
    local module="$1"
    local status="$2"
    local cleaned_items="$3"
    
    case "$status" in
        "CLEANED")
            echo -e "${GREEN}✓${NC} $module ${CYAN}($cleaned_items items)${NC}"
            ;;
        "ALREADY_CLEAN")
            echo -e "${YELLOW}○${NC} $module ${CYAN}(already clean)${NC}"
            ;;
        "FAILED")
            echo -e "${RED}✗${NC} $module ${CYAN}(failed)${NC}"
            ;;
    esac
}

# ============================================================================
# ERROR HANDLING
# ============================================================================

error_exit() {
    local exit_code=${2:-1}
    log_error "$1"
    log_error "Clean operation failed. Check the error above for details."
    exit "$exit_code"
}

validate_environment() {
    log_step "Validating clean environment"
    
    # Check if we're in the modules directory
    if [[ ! -f "clean.sh" ]] || [[ ! -d "rv-android-core" ]]; then
        error_exit "Must run from the modules directory containing clean.sh"
    fi
    
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
    
    log_debug "Module validation passed: $module"
    return 0
}

# ============================================================================
# CLEANING LOGIC
# ============================================================================

clean_file_pattern() {
    local pattern="$1"
    local base_dir="$2"
    local found_items=0
    
    log_debug "Cleaning pattern: $pattern in $base_dir"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        # Count items that would be cleaned
        while IFS= read -r -d '' item; do
            ((found_items++))
            log_debug "[DRY RUN] Would remove: $item"
        done < <(find "$base_dir" -name "$pattern" -print0 2>/dev/null || true)
    else
        # Actually clean items
        while IFS= read -r -d '' item; do
            if [[ -e "$item" ]]; then
                log_debug "Removing: $item"
                rm -rf "$item"
                ((found_items++))
            fi
        done < <(find "$base_dir" -name "$pattern" -print0 2>/dev/null || true)
    fi
    
    return $found_items
}

clean_module() {
    local module="$1"
    local total_cleaned=0
    
    log_step "Cleaning module: $module"
    
    # Validate module before cleaning
    if ! validate_module "$module"; then
        return 1
    fi
    
    # Change to module directory
    if ! cd "$module"; then
        log_error "Failed to enter directory: $module"
        return 1
    fi

    rm -rf .venv
    
    # Clean standard targets
    for target in "${CLEAN_TARGETS[@]}"; do
        clean_file_pattern "$target" "."
        local cleaned=$?
        ((total_cleaned += cleaned))
        if [[ $cleaned -gt 0 ]]; then
            log_debug "Cleaned $cleaned items matching: $target"
        fi
    done
    
    # Clean deep targets if requested
    if [[ "$DEEP_CLEAN" == "true" ]]; then
        for target in "${DEEP_CLEAN_TARGETS[@]}"; do
            clean_file_pattern "$target" "."
            local cleaned=$?
            ((total_cleaned += cleaned))
            if [[ $cleaned -gt 0 ]]; then
                log_debug "Deep cleaned $cleaned items matching: $target"
            fi
        done
    fi
    
    # Clean experiment directories if this is rv-experiment module
    if [[ "$module" == "rv-experiment" ]]; then
        for target in "${EXPERIMENT_TARGETS[@]}"; do
            if [[ -d "$target" ]]; then
                if [[ "$DRY_RUN" == "true" ]]; then
                    log_debug "[DRY RUN] Would remove experiment directory: $target"
                    ((total_cleaned++))
                else
                    log_debug "Removing experiment directory: $target"
                    rm -rf "$target"
                    ((total_cleaned++))
                fi
            fi
        done
    fi
    
    # Return to parent directory
    cd ..
    
    # Report results
    if [[ $total_cleaned -gt 0 ]]; then
        print_clean_result "$module" "CLEANED" "$total_cleaned"
    else
        print_clean_result "$module" "ALREADY_CLEAN" "0"
    fi
    
    return 0
}

clean_all_modules() {
    local modules_to_clean=("$@")
    local failed_modules=()
    local cleaned_count=0
    local total_items_cleaned=0
    
    log_info "Cleaning ${#modules_to_clean[@]} modules"
    if [[ "$DEEP_CLEAN" == "true" ]]; then
        log_info "Deep clean mode enabled"
    fi
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN MODE - No files will actually be removed"
    fi
    print_separator
    
    for module in "${modules_to_clean[@]}"; do
        echo
        if clean_module "$module"; then
            ((cleaned_count++))
        else
            failed_modules+=("$module")
        fi
    done
    
    # Report results
    print_separator
    log_info "Clean Summary:"
    log_success "Successfully processed: $cleaned_count modules"
    
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
Usage: ./clean.sh [OPTIONS] [MODULES...]

Clean manager for RV-Android monitored operations modules.
Removes virtual environments, caches, and build artifacts to restore modules
to "original code" state (similar to git clean but preserving modifications).

OPTIONS:
    --deep              Deep clean including logs and temporary files
    --dry-run           Show what would be cleaned without removing
    --verbose           Enable detailed logging output
    --help, -h          Show this help message

MODULES:
    If no modules specified, cleans all modules.
    Available modules:
        rv-android-core           Core utilities and domain models
        rv-monitor-generator      Monitor generation from MOP specifications
        rv-instrumentation-core   Pure abstractions (Instrumenter ABC + types)
        rv-instrumentation        Parent canonical (factory + shared keystore)
        rv-instrumentation-ajc    AspectJ-based instrumentation variant
        rv-instrumentation-dexlib2 DEX-native instrumentation variant (gh52)
        rv-static-analysis        Static analysis tools (GATOR, GESDA, REACH)
        rv-coverage              Coverage analysis tools
        rv-screen-parser         Screen parsing utilities
        rv-tools                 Tool registry and plugin system
        rv-uiautomator           Shared UIAutomator components for device interaction
        rv-platform              Central execution platform for Android experiments
        rv-agent                 LLM-driven agentic testing with LangGraph
        rvagent-tool             RVAgent tool plugin for rv-tools registry
        aperv-tool               APE-RV tool plugin for rv-tools registry
        rv-experiment            Experiment orchestration and coordination
        aperv-llm-validation     APE-RV LLM validation (temporary)

WHAT GETS CLEANED:
    Standard Clean:
        - .venv (virtual environments)
        - __pycache__ (Python bytecode cache)
        - .pytest_cache (Pytest cache)
        - .coverage (Coverage data)
        - .mypy_cache (MyPy cache)
        - .ruff_cache (Ruff linter cache)
        - dist, build (Build artifacts)
        - *.egg-info (Package metadata)
        - .DS_Store, Thumbs.db (OS metadata)
        
    Deep Clean (--deep):
        - All standard targets plus:
        - *.log (Log files)
        - *.tmp (Temporary files)
        - temp directories
        
    Experiment Clean (rv-experiment only):
        - out/ (Experiment output)
        - results/ (Experiment results)
        - mop_out/ (Monitor output)

EXAMPLES:
    ./clean.sh                                    # Clean all modules
    ./clean.sh rv-android-core rv-static-analysis # Clean specific modules
    ./clean.sh --deep                             # Deep clean all modules
    ./clean.sh --dry-run                          # Preview what would be cleaned
    ./clean.sh --verbose rv-experiment            # Verbose clean of rv-experiment

EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --deep)
                DEEP_CLEAN=true
                shift
                ;;
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
    log_info "  Deep clean: $DEEP_CLEAN"
    log_info "  Dry run: $DRY_RUN"
    log_info "  Verbose: $VERBOSE"
    log_info "  Modules: ${SELECTED_MODULES[*]}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN MODE - No files will actually be removed"
    fi
    
    if [[ "$DEEP_CLEAN" == "true" ]]; then
        log_warning "DEEP CLEAN MODE - Additional temporary files and logs will be removed"
    fi
    
    echo
    
    # Validate environment
    validate_environment
    
    # Clean modules
    if clean_all_modules "${SELECTED_MODULES[@]}"; then
        echo
        log_success "All modules cleaned successfully!"
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "Re-run without --dry-run to perform actual cleanup"
        else
            log_info "Modules restored to 'original code' state"
            log_info "Run './install.sh' to reinstall virtual environments"
        fi
        exit 0
    else
        echo
        error_exit "Some modules failed to clean"
    fi
}

# Execute main function with all arguments
main "$@"
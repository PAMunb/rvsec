#!/bin/bash

# Lock Manager for RV-Android
# Manages uv lock file for all workspace modules
# Ensures consistent dependency resolution across all modules

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
declare -g UPDATE_MODE=false
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
    echo -e "${CYAN} RV-Android Lock Manager${NC}"
    echo -e "${CYAN} uv lock file management for monitored operations modules${NC}"
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
    log_error "Lock operation failed. Check the error above for details."
    exit "$exit_code"
}

validate_environment() {
    log_step "Validating lock environment"
    
    # Check if we're in the modules directory
    if [[ ! -f "lock.sh" ]] || [[ ! -d "rv-android-core" ]]; then
        error_exit "Must run from the modules directory containing lock.sh"
    fi
    
    # Check uv availability
    if ! command -v uv &> /dev/null; then
        error_exit "uv is required but not found. Please install uv first."
    fi

    # Check uv version (basic check)
    local uv_version
    uv_version=$(uv --version 2>/dev/null || echo "unknown")
    log_debug "Found uv version: $uv_version"
    
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
# LOCK LOGIC
# ============================================================================

lock_workspace() {
    log_step "Locking workspace (single uv.lock at root)"

    cd ..

    # Dry run mode
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run: uv lock"
        cd - > /dev/null
        return 0
    fi

    local lock_cmd="uv lock"

    log_debug "Executing: $lock_cmd"

    if [[ "$VERBOSE" == "true" ]]; then
        if eval "$lock_cmd"; then
            log_success "Successfully locked workspace"
        else
            log_error "Failed to lock workspace"
            cd - > /dev/null
            return 1
        fi
    else
        if eval "$lock_cmd" >/dev/null 2>&1; then
            log_success "Successfully locked workspace"
        else
            log_error "Failed to lock workspace"
            log_error "Run with --verbose for detailed error output"
            cd - > /dev/null
            return 1
        fi
    fi

    cd - > /dev/null
    return 0
}

verify_lock() {
    log_debug "Verifying lock file"

    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi

    # Check if uv.lock exists at root
    if [[ -f "../uv.lock" ]]; then
        log_debug "Lock file verified: ../uv.lock"
        return 0
    else
        log_warning "Lock file not found: ../uv.lock"
        return 1
    fi
}

lock_all_modules() {
    log_info "Locking workspace (uv uses single lock file)"
    print_separator

    echo
    if lock_workspace; then
        if verify_lock; then
            log_success "Workspace locked and verified"
        else
            log_error "Lock verification failed"
            return 1
        fi
    else
        log_error "Lock failed"
        return 1
    fi

    # Report results
    print_separator
    log_info "Lock Summary:"
    log_success "Workspace locked successfully"

    return 0
}

update_all_locks() {
    log_info "Updating workspace lock file"
    log_warning "This will update dependencies to latest compatible versions"
    print_separator

    cd ..

    # Dry run mode
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run: uv lock --upgrade"
        cd - > /dev/null
        return 0
    fi

    log_debug "Executing: uv lock --upgrade"

    if [[ "$VERBOSE" == "true" ]]; then
        if uv lock --upgrade; then
            log_success "Successfully updated workspace lock"
        else
            log_error "Failed to update workspace lock"
            cd - > /dev/null
            return 1
        fi
    else
        if uv lock --upgrade >/dev/null 2>&1; then
            log_success "Successfully updated workspace lock"
        else
            log_error "Failed to update workspace lock"
            log_error "Run with --verbose for detailed error output"
            cd - > /dev/null
            return 1
        fi
    fi

    cd - > /dev/null

    # Report results
    print_separator
    log_info "Update Summary:"
    log_success "Workspace lock updated successfully"

    return 0
}

# ============================================================================
# ARGUMENT PARSING
# ============================================================================

print_usage() {
    cat << 'EOF'
Usage: ./lock.sh [OPTIONS] [COMMAND] [MODULES...]

uv lock file manager for RV-Android monitored operations modules.
Manages dependency resolution and lock file consistency across all modules.
uv uses a single lock file at the workspace root, so module arguments are ignored.

COMMANDS:
    lock                Lock specified modules (default command)
    update              Update dependencies and regenerate lock files
    verify              Verify existing lock files are valid

OPTIONS:
    --dry-run           Show what would be done without executing
    --verbose           Enable detailed logging output
    --help, -h          Show this help message

MODULES:
    If no modules specified, operates on all modules in dependency order.
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

EXAMPLES:
    ./lock.sh                                       # Lock all modules
    ./lock.sh lock rv-android-core rv-static-analysis # Lock specific modules
    ./lock.sh update                                # Update all module locks
    ./lock.sh --dry-run update rv-agent             # Preview update for rv-agent
    ./lock.sh --verbose lock                        # Lock with verbose output
    ./lock.sh verify                                # Verify all lock files

EOF
}

parse_arguments() {
    local command=""
    
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
            lock|update|verify)
                if [[ -z "$command" ]]; then
                    command="$1"
                else
                    error_exit "Multiple commands specified: $command and $1"
                fi
                shift
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
    
    # Default command is lock
    if [[ -z "$command" ]]; then
        command="lock"
    fi
    
    # If no modules selected, use all modules
    if [[ ${#SELECTED_MODULES[@]} -eq 0 ]]; then
        SELECTED_MODULES=("${MODULES[@]}")
    fi
    
    # Set command mode
    case "$command" in
        "update")
            UPDATE_MODE=true
            ;;
        "verify")
            VERIFY_MODE=true
            ;;
        "lock")
            # Default mode
            ;;
    esac
    
    # Export command for main function
    export LOCK_COMMAND="$command"
}

verify_all_locks() {
    log_info "Verifying workspace lock file"
    print_separator

    echo
    log_step "Verifying workspace lock file"

    if verify_lock; then
        print_separator
        log_info "Verification Summary:"
        log_success "Workspace lock file verified"
        return 0
    else
        print_separator
        log_error "Workspace lock file verification failed"
        return 1
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
    log_info "  Command: $LOCK_COMMAND"
    log_info "  Dry run: $DRY_RUN"
    log_info "  Verbose: $VERBOSE"
    log_info "  Modules: ${SELECTED_MODULES[*]}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN MODE - No actual changes will be made"
    fi
    
    echo
    
    # Validate environment
    validate_environment
    
    # Execute command (uv uses single workspace lock, module selection is ignored)
    case "$LOCK_COMMAND" in
        "lock")
            if lock_all_modules; then
                echo
                log_success "All modules locked successfully!"
                if [[ "$DRY_RUN" == "true" ]]; then
                    log_info "Re-run without --dry-run to perform actual locking"
                fi
                exit 0
            else
                echo
                error_exit "Some modules failed to lock"
            fi
            ;;
        "update")
            if update_all_locks; then
                echo
                log_success "All module locks updated successfully!"
                if [[ "$DRY_RUN" == "true" ]]; then
                    log_info "Re-run without --dry-run to perform actual updates"
                fi
                exit 0
            else
                echo
                error_exit "Some modules failed to update"
            fi
            ;;
        "verify")
            if verify_all_locks; then
                echo
                log_success "All lock files verified successfully!"
                exit 0
            else
                echo
                error_exit "Some lock files failed verification"
            fi
            ;;
        *)
            error_exit "Unknown command: $LOCK_COMMAND"
            ;;
    esac
}

# Execute main function with all arguments
main "$@"
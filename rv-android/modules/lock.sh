#!/bin/bash

# Lock Manager for RV-Android
# Manages Poetry lock files for monitored operations modules
# Ensures consistent dependency resolution across all modules

set -euo pipefail  # Strict error handling

# ============================================================================
# CONFIGURATION
# ============================================================================

# Static module list in dependency order - same as install.sh
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
    echo -e "${CYAN} Poetry lock file management for monitored operations modules${NC}"
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
# LOCK LOGIC
# ============================================================================

lock_module() {
    local module="$1"
    
    log_step "Locking module: $module"
    
    # Validate module before locking
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
        log_info "[DRY RUN] Would lock: $module"
        cd ..
        return 0
    fi
    
    # Execute poetry lock with appropriate flags
    local lock_cmd="poetry lock"
    if [[ "$UPDATE_MODE" == "true" ]]; then
        lock_cmd="$lock_cmd --no-update"
    fi
    
    log_debug "Executing: $lock_cmd"
    
    if [[ "$VERBOSE" == "true" ]]; then
        if eval "$lock_cmd"; then
            log_success "Successfully locked: $module"
        else
            log_error "Failed to lock: $module"
            cd ..
            return 1
        fi
    else
        if eval "$lock_cmd" >/dev/null 2>&1; then
            log_success "Successfully locked: $module"
        else
            log_error "Failed to lock: $module"
            log_error "Run with --verbose for detailed error output"
            cd ..
            return 1
        fi
    fi
    
    # Return to parent directory
    cd ..
    return 0
}

verify_lock() {
    local module="$1"
    
    log_debug "Verifying lock: $module"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    # Change to module directory
    if ! cd "$module"; then
        log_error "Failed to enter directory for verification: $module"
        return 1
    fi
    
    # Check if poetry.lock exists and is valid
    if [[ -f "poetry.lock" ]] && poetry check --lock >/dev/null 2>&1; then
        log_debug "Lock file verified: $module"
        cd ..
        return 0
    else
        log_warning "Lock file verification failed: $module"
        cd ..
        return 1
    fi
}

lock_all_modules() {
    local modules_to_lock=("$@")
    local failed_modules=()
    local locked_count=0
    
    log_info "Locking ${#modules_to_lock[@]} modules in dependency order"
    if [[ "$UPDATE_MODE" == "true" ]]; then
        log_info "Update mode: Re-locking without updating dependencies"
    fi
    print_separator
    
    for module in "${modules_to_lock[@]}"; do
        echo
        if lock_module "$module"; then
            if verify_lock "$module"; then
                ((locked_count++))
            else
                failed_modules+=("$module (verification failed)")
            fi
        else
            failed_modules+=("$module (lock failed)")
        fi
    done
    
    # Report results
    print_separator
    log_info "Lock Summary:"
    log_success "Successfully locked: $locked_count modules"
    
    if [[ ${#failed_modules[@]} -gt 0 ]]; then
        log_error "Failed modules: ${#failed_modules[@]}"
        for failed in "${failed_modules[@]}"; do
            log_error "  - $failed"
        done
        return 1
    fi
    
    return 0
}

update_all_locks() {
    local modules_to_update=("$@")
    local failed_modules=()
    local updated_count=0
    
    log_info "Updating lock files for ${#modules_to_update[@]} modules"
    log_warning "This will update dependencies to latest compatible versions"
    print_separator
    
    for module in "${modules_to_update[@]}"; do
        echo
        log_step "Updating lock for module: $module"
        
        # Validate module before updating
        if ! validate_module "$module"; then
            failed_modules+=("$module (validation failed)")
            continue
        fi
        
        # Change to module directory
        if ! cd "$module"; then
            log_error "Failed to enter directory: $module"
            failed_modules+=("$module (directory access failed)")
            continue
        fi
        
        # Dry run mode
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY RUN] Would update lock: $module"
            cd ..
            ((updated_count++))
            continue
        fi
        
        # Execute poetry update and lock
        log_debug "Executing: poetry update && poetry lock"
        
        if [[ "$VERBOSE" == "true" ]]; then
            if poetry update && poetry lock; then
                log_success "Successfully updated lock: $module"
                ((updated_count++))
            else
                log_error "Failed to update lock: $module"
                failed_modules+=("$module (update failed)")
            fi
        else
            if poetry update >/dev/null 2>&1 && poetry lock >/dev/null 2>&1; then
                log_success "Successfully updated lock: $module"
                ((updated_count++))
            else
                log_error "Failed to update lock: $module"
                log_error "Run with --verbose for detailed error output"
                failed_modules+=("$module (update failed)")
            fi
        fi
        
        # Return to parent directory
        cd ..
    done
    
    # Report results
    print_separator
    log_info "Update Summary:"
    log_success "Successfully updated: $updated_count modules"
    
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
Usage: ./lock.sh [OPTIONS] [COMMAND] [MODULES...]

Poetry lock file manager for RV-Android monitored operations modules.
Manages dependency resolution and lock file consistency across all modules.

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
    ./lock.sh                                       # Lock all modules
    ./lock.sh lock rv-android-core rv-static-analysis # Lock specific modules
    ./lock.sh update                                # Update all module locks
    ./lock.sh --dry-run update rv-llm               # Preview update for rv-llm
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
    local modules_to_verify=("$@")
    local failed_modules=()
    local verified_count=0
    
    log_info "Verifying lock files for ${#modules_to_verify[@]} modules"
    print_separator
    
    for module in "${modules_to_verify[@]}"; do
        echo
        log_step "Verifying lock for module: $module"
        
        if verify_lock "$module"; then
            ((verified_count++))
        else
            failed_modules+=("$module")
        fi
    done
    
    # Report results
    print_separator
    log_info "Verification Summary:"
    log_success "Successfully verified: $verified_count modules"
    
    if [[ ${#failed_modules[@]} -gt 0 ]]; then
        log_error "Failed verification: ${#failed_modules[@]} modules"
        for failed in "${failed_modules[@]}"; do
            log_error "  - $failed"
        done
        return 1
    fi
    
    return 0
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
    
    # Execute command
    case "$LOCK_COMMAND" in
        "lock")
            if lock_all_modules "${SELECTED_MODULES[@]}"; then
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
            if update_all_locks "${SELECTED_MODULES[@]}"; then
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
            if verify_all_locks "${SELECTED_MODULES[@]}"; then
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
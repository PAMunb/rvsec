#!/bin/bash

# Test Runner for RV-Android
# Manages isolated testing of monitored operations modules
# Solves conftest.py conflicts through directory-based test isolation

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
    "rv-platform"               # Central execution platform for Android experiments
    "rvandroid-tool"            # RVAndroid tool implementation with LLM integration
    "rv-experiment"             # Experiment orchestration and coordination
#    "rvandroid"                # Main framework module
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
declare -g COVERAGE=false
declare -g CONTINUE_ON_ERROR=false
declare -g PARALLEL=false
declare -g VERBOSE=false
declare -g SELECTED_MODULES=()

# Test results tracking
declare -ga PASSED_MODULES=()
declare -ga FAILED_MODULES=()
declare -ga SKIPPED_MODULES=()

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
    echo -e "${CYAN} RV-Android Test Runner${NC}"
    echo -e "${CYAN} Isolated testing of monitored operations modules${NC}"
    echo -e "${CYAN}============================================================================${NC}"
    echo
}

print_separator() {
    echo -e "${CYAN}----------------------------------------------------------------------------${NC}"
}

print_test_result() {
    local module="$1"
    local status="$2"
    local duration="$3"
    
    case "$status" in
        "PASSED")
            echo -e "${GREEN}✓${NC} $module ${CYAN}($duration)${NC}"
            ;;
        "FAILED")
            echo -e "${RED}✗${NC} $module ${CYAN}($duration)${NC}"
            ;;
        "SKIPPED")
            echo -e "${YELLOW}○${NC} $module ${CYAN}(skipped)${NC}"
            ;;
    esac
}

# ============================================================================
# ERROR HANDLING
# ============================================================================

error_exit() {
    local exit_code=${2:-1}
    log_error "$1"
    log_error "Testing failed. Check the error above for details."
    exit "$exit_code"
}

validate_environment() {
    log_step "Validating test environment"
    
    # Check if we're in the modules directory
    if [[ ! -f "test.sh" ]] || [[ ! -d "rv-android-core" ]]; then
        error_exit "Must run from the modules directory containing test.sh"
    fi
    
    # Check Poetry availability
    if ! command -v poetry &> /dev/null; then
        error_exit "Poetry is required but not found. Please install Poetry first."
    fi
    
    # Check pytest availability (will be checked per module)
    log_debug "Poetry found, pytest availability will be checked per module"
    
    log_success "Environment validation passed"
}

validate_module_for_testing() {
    local module="$1"
    log_debug "Validating module for testing: $module"
    
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
    
    # Check if tests directory exists
    if [[ ! -d "$module/tests" ]]; then
        log_warning "No tests directory found in: $module"
        return 2  # Special return code for "no tests"
    fi
    
    log_debug "Module validation passed: $module"
    return 0
}

# ============================================================================
# TESTING LOGIC
# ============================================================================

test_module() {
    local module="$1"
    local start_time
    local end_time
    local duration
    
    start_time=$(date +%s)
    
    log_step "Testing module: $module"
    
    # Validate module before testing
    local validation_result
    validate_module_for_testing "$module"
    validation_result=$?
    
    if [[ $validation_result -eq 1 ]]; then
        FAILED_MODULES+=("$module")
        return 1
    elif [[ $validation_result -eq 2 ]]; then
        SKIPPED_MODULES+=("$module")
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        print_test_result "$module" "SKIPPED" "${duration}s"
        return 0
    fi
    
    # Change to module directory for isolated testing
    if ! cd "$module"; then
        log_error "Failed to enter directory: $module"
        FAILED_MODULES+=("$module")
        return 1
    fi
    
    # Check if poetry environment exists
    if ! poetry env info --path >/dev/null 2>&1; then
        log_error "Poetry environment not found for: $module"
        log_error "Run './install.sh $module' first"
        cd ..
        FAILED_MODULES+=("$module")
        return 1
    fi
    
    # Build pytest command
    local pytest_cmd="poetry run pytest"
    
    if [[ "$COVERAGE" == "true" ]]; then
        pytest_cmd="$pytest_cmd --cov=src --cov-report=term-missing"
    fi
    
    if [[ "$VERBOSE" == "false" ]]; then
        pytest_cmd="$pytest_cmd -q"
    else
        pytest_cmd="$pytest_cmd -v"
    fi
    
    # Execute tests
    log_debug "Executing: $pytest_cmd"
    
    local test_result=0
    if [[ "$VERBOSE" == "true" ]]; then
        eval "$pytest_cmd" || test_result=$?
    else
        eval "$pytest_cmd" >/dev/null 2>&1 || test_result=$?
    fi
    
    # Calculate duration
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    # Record results
    if [[ $test_result -eq 0 ]]; then
        PASSED_MODULES+=("$module")
        print_test_result "$module" "PASSED" "${duration}s"
    else
        FAILED_MODULES+=("$module")
        print_test_result "$module" "FAILED" "${duration}s"
        if [[ "$CONTINUE_ON_ERROR" == "false" ]]; then
            cd ..
            return 1
        fi
    fi
    
    # Return to parent directory
    cd ..
    return $test_result
}

test_module_parallel() {
    local module="$1"
    
    # Create a temporary file for this module's output
    local temp_file="/tmp/rvandroid_test_${module}_$$"
    
    # Run test in background and capture result
    (
        if test_module "$module"; then
            echo "PASSED" > "$temp_file"
        else
            echo "FAILED" > "$temp_file"
        fi
    ) &
    
    # Return the PID for tracking
    echo $!
}

test_all_modules() {
    local modules_to_test=("$@")
    
    log_info "Testing ${#modules_to_test[@]} modules"
    if [[ "$PARALLEL" == "true" ]]; then
        log_info "Running tests in parallel"
    fi
    if [[ "$COVERAGE" == "true" ]]; then
        log_info "Coverage reporting enabled"
    fi
    if [[ "$CONTINUE_ON_ERROR" == "true" ]]; then
        log_info "Continuing on errors"
    fi
    
    print_separator
    
    if [[ "$PARALLEL" == "true" ]]; then
        # Parallel testing
        local pids=()
        local temp_files=()
        
        for module in "${modules_to_test[@]}"; do
            local pid
            pid=$(test_module_parallel "$module")
            pids+=("$pid")
            temp_files+=("/tmp/rvandroid_test_${module}_$$")
        done
        
        # Wait for all tests to complete
        for pid in "${pids[@]}"; do
            wait "$pid"
        done
        
        # Clean up temporary files
        for temp_file in "${temp_files[@]}"; do
            if [[ -f "$temp_file" ]]; then
                rm "$temp_file"
            fi
        done
    else
        # Sequential testing
        for module in "${modules_to_test[@]}"; do
            echo
            if ! test_module "$module"; then
                if [[ "$CONTINUE_ON_ERROR" == "false" ]]; then
                    return 1
                fi
            fi
        done
    fi
    
    return 0
}

generate_test_report() {
    local total_modules=${#SELECTED_MODULES[@]}
    local passed_count=${#PASSED_MODULES[@]}
    local failed_count=${#FAILED_MODULES[@]}
    local skipped_count=${#SKIPPED_MODULES[@]}
    
    print_separator
    log_info "Test Results Summary:"
    echo
    
    log_success "Passed:  $passed_count/$total_modules modules"
    if [[ $passed_count -gt 0 ]]; then
        for module in "${PASSED_MODULES[@]}"; do
            echo -e "  ${GREEN}✓${NC} $module"
        done
    fi
    
    if [[ $failed_count -gt 0 ]]; then
        echo
        log_error "Failed:  $failed_count/$total_modules modules"
        for module in "${FAILED_MODULES[@]}"; do
            echo -e "  ${RED}✗${NC} $module"
        done
    fi
    
    if [[ $skipped_count -gt 0 ]]; then
        echo
        log_warning "Skipped: $skipped_count/$total_modules modules"
        for module in "${SKIPPED_MODULES[@]}"; do
            echo -e "  ${YELLOW}○${NC} $module (no tests)"
        done
    fi
    
    echo
    if [[ $failed_count -eq 0 ]]; then
        log_success "All tests completed successfully!"
        return 0
    else
        log_error "Some tests failed"
        return 1
    fi
}

# ============================================================================
# ARGUMENT PARSING
# ============================================================================

print_usage() {
    cat << 'EOF'
Usage: ./test.sh [OPTIONS] [MODULES...]

Test runner for RV-Android monitored operations modules.
Supports experiments with JCA cryptography specifications and generic runtime specifications.
Runs tests in isolation to avoid conftest.py conflicts.

OPTIONS:
    --coverage              Run tests with coverage reporting
    --continue-on-error     Continue testing even if modules fail
    --parallel              Run tests in parallel (for independent modules)
    --verbose               Enable detailed test output
    --help, -h              Show this help message

MODULES:
    If no modules specified, tests all modules in dependency order.
    Available modules:
        rv-android-core           Core utilities and domain models
        rv-monitor-generator      Monitor generation from MOP specifications
        rv-instrumentation        APK instrumentation with monitors
        rv-static-analysis        Static analysis tools (GATOR, GESDA, REACH)
        rv-coverage              Coverage analysis tools
        rv-screen-parser         Screen parsing utilities
        rv-llm                   Language Model integration infrastructure
        rv-tools                 Tool registry and plugin system
        rv-platform              Central execution platform for Android experiments
        rvandroid-tool           RVAndroid tool implementation with LLM integration
        rv-experiment            Experiment orchestration and coordination
        rvandroid               Main framework module

EXAMPLES:
    ./test.sh                                       # Test all modules
    ./test.sh rv-android-core rv-static-analysis    # Test specific modules
    ./test.sh --coverage                            # Test with coverage
    ./test.sh --continue-on-error                   # Continue on failures
    ./test.sh --parallel --verbose                  # Parallel with verbose output

EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --coverage)
                COVERAGE=true
                shift
                ;;
            --continue-on-error)
                CONTINUE_ON_ERROR=true
                shift
                ;;
            --parallel)
                PARALLEL=true
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
    log_info "  Coverage: $COVERAGE"
    log_info "  Continue on error: $CONTINUE_ON_ERROR"
    log_info "  Parallel: $PARALLEL"
    log_info "  Verbose: $VERBOSE"
    log_info "  Modules: ${SELECTED_MODULES[*]}"
    echo
    
    # Validate environment
    validate_environment
    
    # Run tests
    if test_all_modules "${SELECTED_MODULES[@]}"; then
        generate_test_report
        exit $?
    else
        generate_test_report
        exit 1
    fi
}

# Execute main function with all arguments
main "$@"
#!/bin/bash

# Define project root relative to tests directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Source the script containing the functions
source "${PROJECT_ROOT}/dist/sync/sync-workflows.sh"

# Variable to track overall test status
EXIT_CODE=0

echo "Running tests for sync_shared_config function in sync-workflows.sh"
echo "------------------------------------------------------------------"

# Helper function to assert test results
assert_equal() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"

    if [[ "$expected" == "$actual" ]]; then
        echo "✅ PASS: $test_name"
    else
        echo "❌ FAIL: $test_name"
        echo "   Expected: '$expected'"
        echo "   Actual:   '$actual'"
        EXIT_CODE=1
    fi
}

assert_json_valid() {
    local test_name="$1"
    local json_file="$2"

    if jq . "$json_file" >/dev/null 2>&1; then
        echo "✅ PASS (Valid JSON): $test_name"
    else
        echo "❌ FAIL (Invalid JSON): $test_name"
        cat "$json_file"
        EXIT_CODE=1
    fi
}

# Mock git function for testing check-ignore
git() {
    if [[ "$1" == "check-ignore" && "$2" == "--stdin" ]]; then
        # Read paths from stdin
        while read -r path; do
            # Mock behavior: Any file with 'ignored' in the name is considered ignored
            if [[ "$path" == *"ignored"* ]]; then
                echo "$path"
            fi
        done
        return 0
    fi
    # Fallback to actual git for other commands (if any)
    command git "$@"
}

test_sync_shared_config() {
    echo "▶️  Testing sync_shared_config..."

    # Setup test environment
    export AGENT_WORKFLOWS="${PROJECT_ROOT}/.test_agents/workflows"
    export KILO_COMMANDS="${PROJECT_ROOT}/.test_kilo/commands"
    export SHARED_CONFIG="${PROJECT_ROOT}/.test_omnistate/shared-workflow.json"

    mkdir -p "$AGENT_WORKFLOWS"
    mkdir -p "$KILO_COMMANDS"
    mkdir -p "$(dirname "$SHARED_CONFIG")"

    # Create dummy workflow files
    touch "$AGENT_WORKFLOWS/test1.sh"
    touch "$AGENT_WORKFLOWS/test_ignored.sh"
    touch "$KILO_COMMANDS/test2.sh"
    touch "$KILO_COMMANDS/test3_ignored.sh"

    # Run the function under test
    local output
    output=$(sync_shared_config)

    # Assertions

    # 1. Check if the JSON is valid
    assert_json_valid "SHARED_CONFIG is valid JSON" "$SHARED_CONFIG"

    # 2. Check if non-ignored files are in the JSON
    local file_count=$(jq '.workflow_files | length' "$SHARED_CONFIG")
    assert_equal "JSON contains only non-ignored files" "2" "$file_count"

    # 3. Check for specific files
    local has_test1=$(jq '.workflow_files | contains(["test1.sh"])' "$SHARED_CONFIG")
    assert_equal "JSON includes test1.sh" "true" "$has_test1"

    local has_test2=$(jq '.workflow_files | contains(["test2.sh"])' "$SHARED_CONFIG")
    assert_equal "JSON includes test2.sh" "true" "$has_test2"

    # 4. Check that ignored files are NOT in the JSON
    local has_ignored1=$(jq '.workflow_files | contains(["test_ignored.sh"])' "$SHARED_CONFIG")
    assert_equal "JSON excludes test_ignored.sh" "false" "$has_ignored1"

    local has_ignored2=$(jq '.workflow_files | contains(["test3_ignored.sh"])' "$SHARED_CONFIG")
    assert_equal "JSON excludes test3_ignored.sh" "false" "$has_ignored2"

    # Teardown
    rm -rf "${PROJECT_ROOT}/.test_agents"
    rm -rf "${PROJECT_ROOT}/.test_kilo"
    rm -rf "${PROJECT_ROOT}/.test_omnistate"
}

test_sync_shared_config_empty() {
    echo "▶️  Testing sync_shared_config with empty directories..."

    # Setup test environment
    export AGENT_WORKFLOWS="${PROJECT_ROOT}/.test_agents_empty/workflows"
    export KILO_COMMANDS="${PROJECT_ROOT}/.test_kilo_empty/commands"
    export SHARED_CONFIG="${PROJECT_ROOT}/.test_omnistate_empty/shared-workflow.json"

    mkdir -p "$AGENT_WORKFLOWS"
    mkdir -p "$KILO_COMMANDS"
    mkdir -p "$(dirname "$SHARED_CONFIG")"

    # Run the function under test
    local output
    output=$(sync_shared_config)

    # Assertions

    # 1. Check if the JSON is valid
    assert_json_valid "Empty SHARED_CONFIG is valid JSON" "$SHARED_CONFIG"

    # 2. Check if array is empty
    local file_count=$(jq '.workflow_files | length' "$SHARED_CONFIG")
    assert_equal "JSON array is empty" "0" "$file_count"

    # Teardown
    rm -rf "${PROJECT_ROOT}/.test_agents_empty"
    rm -rf "${PROJECT_ROOT}/.test_kilo_empty"
    rm -rf "${PROJECT_ROOT}/.test_omnistate_empty"
}

test_sync_shared_config_injection() {
    echo "▶️  Testing sync_shared_config with JSON injection characters..."

    # Setup test environment with paths containing injection characters
    export AGENT_WORKFLOWS="${PROJECT_ROOT}/.test_agents_inj\"quote\\slash/workflows"
    export KILO_COMMANDS="${PROJECT_ROOT}/.test_kilo_inj\\slash\"quote/commands"
    export SHARED_CONFIG="${PROJECT_ROOT}/.test_omnistate_inj/shared-workflow.json"

    mkdir -p "$AGENT_WORKFLOWS"
    mkdir -p "$KILO_COMMANDS"
    mkdir -p "$(dirname "$SHARED_CONFIG")"

    # Create dummy workflow files with injection characters
    touch "$AGENT_WORKFLOWS/test\"quote\".sh"
    touch "$AGENT_WORKFLOWS/test\\slash.sh"

    # Run the function under test
    local output
    output=$(sync_shared_config)

    # Assertions
    assert_json_valid "Injected SHARED_CONFIG is valid JSON" "$SHARED_CONFIG"

    # Teardown
    rm -rf "${PROJECT_ROOT}/.test_agents_inj"
    rm -rf "${PROJECT_ROOT}/.test_kilo_inj"
    rm -rf "${PROJECT_ROOT}/.test_omnistate_inj"
}

# Run tests
test_sync_shared_config
test_sync_shared_config_empty
test_sync_shared_config_injection

# Exit with appropriate code
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "------------------------------------------------------------------"
    echo "🎉 All tests passed!"
    exit 0
else
    echo "------------------------------------------------------------------"
    echo "💥 Some tests failed."
    exit 1
fi

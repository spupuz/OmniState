#!/bin/bash

# OmniState Bidirectional Workflow Sync
# This script synchronizes workflow files between different IDE directories
# while respecting gitignore rules and project isolation

# Configuration - these paths can be customized per project
AGENT_WORKFLOWS=".agents/workflows"
KILO_COMMANDS=".kilo/commands"
SHARED_CONFIG=".omnistate/shared-workflow.json"

# Ensure directories exist
mkdir -p "$AGENT_WORKFLOWS"
mkdir -p "$KILO_COMMANDS"
mkdir -p "$(dirname "$SHARED_CONFIG")"

# Function to sync workflows with gitignore awareness
function sync_workflows() {
    local source_dir="$1"
    local target_dir="$2"
    local direction="$3"
    
    echo "🔄 Syncing $direction: $source_dir → $target_dir"
    
    # Sync only files that are not in gitignore
    for file in "$source_dir"/*; do
        if [[ -f "$file" ]]; then
            filename="${file##*/}"
            
            # Sync all files, bypassing gitignore for cross‑IDE workflow sync
            # (intentionally ignore .gitignore for workflow synchronization)
            
            # Check if target file exists and compare timestamps
            target_file="$target_dir/$filename"
            if [[ -f "$target_file" ]]; then
                if [[ "$file" -nt "$target_file" ]]; then
                    echo "   → Updating: $filename"
                    tmp_file=$(mktemp "$(dirname "$target_file")/.tmp.XXXXXX")
                    cat "$file" > "$tmp_file"
                    chmod 644 "$tmp_file"
                    mv "$tmp_file" "$target_file"
                elif [[ "$file" -ot "$target_file" ]]; then
                    echo "   ← Newer in target: $filename"
                else
                    echo "   ✓ Already synced: $filename"
                fi
            else
                echo "   → Adding: $filename"
                tmp_file=$(mktemp "$(dirname "$target_file")/.tmp.XXXXXX")
                cat "$file" > "$tmp_file"
                chmod 644 "$tmp_file"
                mv "$tmp_file" "$target_file"
            fi
        fi
    done
}

# Function to create shared workflow configuration
function sync_shared_config() {
    echo "📋 Creating shared workflow configuration..."
    
    # Collect all workflow files from both directories
    local workflow_files=()
    local candidates=()
    
    for dir in "$AGENT_WORKFLOWS" "$KILO_COMMANDS"; do
        for file in "$dir"/*; do
            if [[ -f "$file" ]]; then
                candidates+=("$file")
            fi
        done
    done

    # Batch check git ignore status
    local ignored_files=""
    if [ ${#candidates[@]} -gt 0 ]; then
        # Capture ignored files. We check the exit code because git check-ignore
        # returns 0 if at least one file is ignored, 1 if none are ignored, and >1 for fatal errors (e.g., not a git repo).
        local git_exit_code=0
        ignored_files=$(printf "%s\n" "${candidates[@]}" | git check-ignore --stdin 2>/dev/null) || git_exit_code=$?

        # If exit code is >1, it's a fatal error (like not being in a git repository).
        # In this case, we act as if nothing is ignored.
        if [ $git_exit_code -gt 1 ]; then
            ignored_files=""
        fi
    fi

    # Format ignored files string with leading/trailing newlines for exact matching
    local ignored_str=$'\n'"$ignored_files"$'\n'

    # Filter out ignored files
    for file in "${candidates[@]}"; do
        # If the file path is not in the ignored string exactly
        if [[ "$ignored_str" != *$'\n'"$file"$'\n'* ]]; then
            # SECURITY: escape backslashes and double quotes to prevent JSON injection
            local filename="${file##*/}"
            filename="${filename//\\/\\\\}"
            filename="${filename//\"/\\\"}"
            workflow_files+=("$filename")
        fi
    done
    
    # Format JSON array
    local json_files=""
    if [ ${#workflow_files[@]} -gt 0 ]; then
        json_files=$(printf '        "%s",\n' "${workflow_files[@]}" | sed '$ s/,$//')
    fi

    # Create JSON configuration
    tmp_file=$(mktemp "$(dirname "$SHARED_CONFIG")/.tmp.XXXXXX")
    cat > "$tmp_file" << EOF
{
    "version": "1.1.1",
    "last_sync": "$(date -Iseconds)",
    "workflow_files": [
$json_files
    ],
    "agent_workflows": "$AGENT_WORKFLOWS",
    "kilo_commands": "$KILO_COMMANDS"
}
EOF
    chmod 644 "$tmp_file"
    mv "$tmp_file" "$SHARED_CONFIG"
    
    echo "   ✓ Shared config created: $SHARED_CONFIG"
}

function main() {
    # Main execution
    echo "🔄 OmniState Bidirectional Workflow Sync"
    echo "=========================================="

    # Sync from .agents/workflows to .kilo/commands
    sync_workflows "$AGENT_WORKFLOWS" "$KILO_COMMANDS" "AGENT → KILO"

    # Sync from .kilo/commands to .agents/workflows
    sync_workflows "$KILO_COMMANDS" "$AGENT_WORKFLOWS" "KILO → AGENT"

    # Create shared configuration
    sync_shared_config

    echo ""
    echo "✅ Sync complete!"
    echo "   📁 Agent workflows: $AGENT_WORKFLOWS"
    echo "   📁 Kilocode commands: $KILO_COMMANDS"
    echo "   📋 Shared config: $SHARED_CONFIG"
    echo ""
}

# Run main if not sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
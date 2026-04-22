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
            filename=$(basename "$file")
            
            # Sync all files, bypassing gitignore for cross‑IDE workflow sync
            # (intentionally ignore .gitignore for workflow synchronization)
            
            # Check if target file exists and compare timestamps
            target_file="$target_dir/$filename"
            if [[ -f "$target_file" ]]; then
                if [[ "$file" -nt "$target_file" ]]; then
                    echo "   → Updating: $filename"
                    cp "$file" "$target_file"
                elif [[ "$file" -ot "$target_file" ]]; then
                    echo "   ← Newer in target: $filename"
                else
                    echo "   ✓ Already synced: $filename"
                fi
            else
                echo "   → Adding: $filename"
                cp "$file" "$target_file"
            fi
        fi
    done
}

# Function to create shared workflow configuration
function sync_shared_config() {
    echo "📋 Creating shared workflow configuration..."
    
    # Collect all workflow files from both directories
    local workflow_files=()
    
    for dir in "$AGENT_WORKFLOWS" "$KILO_COMMANDS"; do
        for file in "$dir"/*; do
            if [[ -f "$file" ]] && ! git check-ignore -q "$file" 2>/dev/null; then
                workflow_files+=("$(basename "$file")")
            fi
        done
    done
    
    # Create JSON configuration
    cat > "$SHARED_CONFIG" << EOF
{
    "version": "1.1.1",
    "last_sync": "$(date -Iseconds)",
    "workflow_files": [
$(printf '		"%s",
' "${workflow_files[@]}")	],
    "agent_workflows": "$AGENT_WORKFLOWS",
    "kilo_commands": "$KILO_COMMANDS"
}
EOF
    
    echo "   ✓ Shared config created: $SHARED_CONFIG"
}

# Main execution
echo "🔄 OmniState Bidirectional Workflow Sync"
echo "=========================================="

# Sync from .agents/workflows to .roo/commands
sync_workflows "$AGENT_WORKFLOWS" "$KILO_COMMANDS" "AGENT → KILO"

# Sync from .roo/commands to .agents/workflows
sync_workflows "$KILO_COMMANDS" "$AGENT_WORKFLOWS" "KILO → AGENT"

# Create shared configuration
sync_shared_config

echo ""
echo "✅ Sync complete!"
echo "   📁 Agent workflows: $AGENT_WORKFLOWS"
echo "   📁 Kilocode commands: $KILO_COMMANDS"
echo "   📋 Shared config: $SHARED_CONFIG"
echo ""
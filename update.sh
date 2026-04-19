#!/bin/bash

# OmniState Update & Sync Script (v1.1.0)
# This script manages global installation and local project synchronization.

# 1. Configuration & Paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION_FILE="$SCRIPT_DIR/VERSION.txt"
VERSION=$(cat "$VERSION_FILE" 2>/dev/null || echo "1.1.0")
PLUGIN_NAME="omnistate"

# Detect global directories
GLOBAL_BASE_DIR="$HOME/.gemini/antigravity"
if [ "$EUID" -eq 0 ] && [ "$HOME" == "/root" ]; then
    GLOBAL_BASE_DIR="/root/.gemini/antigravity"
fi

GLOBAL_PLUGINS_DIR="$GLOBAL_BASE_DIR/plugins"
GLOBAL_WORKFLOWS_DIR="$GLOBAL_BASE_DIR/workflows"
GLOBAL_KNOWLEDGE_DIR="$GLOBAL_BASE_DIR/knowledge"
TARGET_PLUGIN_PATH="$GLOBAL_PLUGINS_DIR/$PLUGIN_NAME"

# 2. Argument Parsing
ACTION="install"
PROJECT_ROOT=""
SILENT=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --sync-only) ACTION="sync"; PROJECT_ROOT="$2"; shift ;;
        --auto) ACTION="auto"; PROJECT_ROOT="$2"; shift ;;
        --check) ACTION="check" ;;
        --silent) SILENT=true ;;
        *) PROJECT_ROOT="$1" ;;
    esac
    shift
done

log() {
    if [ "$SILENT" = false ]; then
        echo -e "$1"
    fi
}

# 3. Helpers
sync_workflows() {
    local target_project="$1"
    local source_wf="$TARGET_PLUGIN_PATH/.agent/workflows"
    
    if [ ! -d "$source_wf" ]; then
        source_wf="$SCRIPT_DIR/.agent/workflows"
    fi

    if [ -d "$target_project" ] && [ -d "$source_wf" ]; then
        log "\033[0;36mSynchronizing OmniState workflows to $target_project...\033[0m"
        for wfDir in ".agent" ".agents"; do
            mkdir -p "$target_project/$wfDir/workflows"
            cp -a "$source_wf/"* "$target_project/$wfDir/workflows/"
            
            # Git Protection
            if [ -f "$target_project/.gitignore" ]; then
                if ! grep -q "^$wfDir/" "$target_project/.gitignore"; then
                    echo -e "\n# OmniState Workflows\n$wfDir/" >> "$target_project/.gitignore"
                fi
            fi
        done
        log "\033[0;32mWorkflows synchronized successfully.\033[0m"
    fi
}

check_github_update() {
    if [ -d "$TARGET_PLUGIN_PATH/.git" ]; then
        cd "$TARGET_PLUGIN_PATH" || return
        
        # Fast check using ls-remote (no fetch of objects)
        REMOTE_HASH=$(git ls-remote origin -h refs/heads/main | awk '{print $1}')
        LOCAL_HASH=$(git rev-parse HEAD)
        
        if [ "$REMOTE_HASH" != "$LOCAL_HASH" ]; then
            return 1 # Update available
        fi
    fi
    return 0 # Up to date
}

# 4. Actions Logic
if [ "$ACTION" == "check" ]; then
    check_github_update
    exit $?
fi

if [ "$ACTION" == "auto" ]; then
    # 24h Throttle for GitHub check
    LAST_CHECK_FILE="$TARGET_PLUGIN_PATH/.last_update_check"
    NOW=$(date +%s)
    LAST_CHECK=0
    if [ -f "$LAST_CHECK_FILE" ]; then LAST_CHECK=$(cat "$LAST_CHECK_FILE"); fi
    
    if (( NOW - LAST_CHECK > 86400 )); then
        log "\033[0;33mChecking for OmniState global updates...\033[0m"
        if ! check_github_update; then
            log "\033[0;32mNew version detected! Updating global OmniState...\033[0m"
            cd "$TARGET_PLUGIN_PATH" && git pull origin main --quiet
            echo "$NOW" > "$LAST_CHECK_FILE"
            # Re-run install to update global workflows/metadata
            bash "$TARGET_PLUGIN_PATH/update.sh" --silent
        else
            echo "$NOW" > "$LAST_CHECK_FILE"
        fi
    fi
    # Always sync local project if provided
    if [ -n "$PROJECT_ROOT" ]; then
        sync_workflows "$PROJECT_ROOT"
    fi
    exit 0
fi

if [ "$ACTION" == "sync" ]; then
    sync_workflows "$PROJECT_ROOT"
    exit 0
fi

# 5. Default Install Logic (original behavior with improvements)
log "\033[0;36mInstalling/Updating OmniState Globale (v$VERSION)...\033[0m"

# Self-Healing
if [ -d "$SCRIPT_DIR/workflows" ] && [ ! -d "$SCRIPT_DIR/.agent/workflows" ]; then
    mkdir -p "$SCRIPT_DIR/.agent/workflows"
    mv "$SCRIPT_DIR/workflows/"* "$SCRIPT_DIR/.agent/workflows/" 2>/dev/null
    rm -rf "$SCRIPT_DIR/workflows"
fi

# Update from Git if in the source repo
if [ -d "$SCRIPT_DIR/.git" ] && command -v git &> /dev/null; then
    log "\033[0;32mFetching latest changes...\033[0m"
    git pull origin main --quiet
fi

# Ensure global layout
mkdir -p "$GLOBAL_PLUGINS_DIR" "$GLOBAL_WORKFLOWS_DIR" "$GLOBAL_KNOWLEDGE_DIR"

# Install Plugin
rm -rf "$TARGET_PLUGIN_PATH"
mkdir -p "$TARGET_PLUGIN_PATH"
cp -a "$SCRIPT_DIR/." "$TARGET_PLUGIN_PATH/"
rm -rf "$TARGET_PLUGIN_PATH/.git" # Remove git from the installed copy to keep it a flat plugin unless user specifically wants dev mode

# Register Knowledge Item
mkdir -p "$GLOBAL_KNOWLEDGE_DIR/$PLUGIN_NAME/artifacts"
cat <<EOF > "$GLOBAL_KNOWLEDGE_DIR/$PLUGIN_NAME/metadata.json"
{
  "summary": "OmniState Global Plugin (v$VERSION): Persistent Memory, Cost Savings, and Model Optimization. Keywords: cost-setup, start-session, snapshot-session, project-summary, tokens.",
  "updatedAt": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "references": ["$TARGET_PLUGIN_PATH"]
}
EOF

# Global Workflows
if [ -d "$SCRIPT_DIR/.agent/workflows" ]; then
    cp -a "$SCRIPT_DIR/.agent/workflows/"* "$GLOBAL_WORKFLOWS_DIR/"
fi

log "\033[0;32mOmniState v$VERSION successfully installed globally!\033[0m"

if [ -n "$PROJECT_ROOT" ]; then
    sync_workflows "$PROJECT_ROOT"
fi

echo -e "\n\033[0;36mAll set! Type 'OmniState activation' if slash commands are missing.\033[0m"
if [ -z "$NON_INTERACTIVE" ] && [ -z "$PROJECT_ROOT" ] && [[ $- == *i* ]]; then
    read -p "Press enter to exit..."
fi

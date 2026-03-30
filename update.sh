#!/bin/bash

# Optional: Target Project Path
PROJECT_ROOT="$1"

# Update and Install OmniState from GitHub
echo -e "\033[0;36mUpdating and Synchronizing OmniState...\033[0m"

# Change directory to the script's folder
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit

# 0. Self-Healing: Fix local folder inconsistencies
if [ -d "workflows" ] && [ ! -d ".agent/workflows" ]; then
    echo -e "\033[0;33mSelf-Healing: Moving legacy workflows to required hidden folder...\033[0m"
    mkdir -p .agent/workflows
    mv workflows/* .agent/workflows/ 2>/dev/null
    rm -rf workflows
fi

# 1. Update from GitHub (if applicable)
if command -v git &> /dev/null; then
    if [ -d ".git" ]; then
        echo -e "\033[0;32mFetching latest changes from GitHub...\033[0m"
        git pull origin main --quiet
    fi
fi

# 2. Automated Installation to Antigravity (Universal Discovery)
pluginName="omnistate"

# Detect possible global directories (standard or root)
globalBaseDir="$HOME/.gemini/antigravity"
if [ "$EUID" -eq 0 ] && [ "$HOME" == "/root" ]; then
    # Standard for root
    globalBaseDir="/root/.gemini/antigravity"
fi

globalPluginsDir="$globalBaseDir/plugins"
globalWorkflowsDir="$globalBaseDir/workflows"
globalKnowledgeDir="$globalBaseDir/knowledge"
targetPluginPath="$globalPluginsDir/$pluginName"
targetKnowledgePath="$globalKnowledgeDir/$pluginName"

echo -e "\033[0;36mTargeting Global Installation in $globalBaseDir...\033[0m"

# Ensure layout exists
mkdir -p "$globalPluginsDir"
mkdir -p "$globalWorkflowsDir"
mkdir -p "$globalKnowledgeDir"

# Clean up and Install Plugin
if [ -e "$targetPluginPath" ]; then
    rm -rf "$targetPluginPath"
fi
mkdir -p "$targetPluginPath"

echo -e "\033[0;32mInstalling OmniState plugin components...\033[0m"
cp -a "$SCRIPT_DIR/." "$targetPluginPath/"
rm -rf "$targetPluginPath/.git"
rm -rf "$targetPluginPath/.agent"

# Install Slash Commands globally
echo -e "\033[0;32mInstalling Slash Commands globally...\033[0m"
if [ -d "$SCRIPT_DIR/.agent/workflows" ]; then
    cp -a "$SCRIPT_DIR/.agent/workflows/"* "$globalWorkflowsDir/"
    chmod +x "$globalWorkflowsDir"/*.md 2>/dev/null
fi

# C. Universal Discovery: Create Knowledge Item (KI)
echo -e "\033[0;36mRegistering OmniState for Universal Discovery (Knowledge Item)...\033[0m"
mkdir -p "$targetKnowledgePath/artifacts"

cat <<EOF > "$targetKnowledgePath/metadata.json"
{
  "summary": "OmniState Global Plugin (v1.0.1): Persistent Memory, Cost Savings, and Model Optimization. Found at $targetPluginPath. Essential for any project. Keywords: cost-setup, start-session, snapshot-session, project-summary, tokens.",
  "updatedAt": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "references": ["$targetPluginPath"]
}
EOF

cat <<EOF > "$targetKnowledgePath/artifacts/omnistate-info.md"
# OmniState Global Plugin Guide

OmniState is correctly installed as a global plugin on this machine.
If slash commands (like /cost-setup) are not visible in the UI, it's because the project isn't initialized yet.

### CRITICAL ACTIVATION:
To activate OmniState in THIS workspace, the agent MUST:
1. Locate the **cost-setup** skill in: $targetPluginPath
2. **Action:** Execute the skill 'cost-setup' using the `run_skill` or `view_file` on its SKILL.md.
3. The skill will automatically install the project-specific workflows to activate the slash commands.

*Always mention 'OmniState' or 'cost-setup' to trigger this knowledge.*
EOF

echo -e "\033[0;32mOmniState successfully installed and registered globally!\033[0m"

# 3. Optional: Inject into project root if provided
if [ -n "$PROJECT_ROOT" ]; then
    if [ -d "$PROJECT_ROOT" ]; then
        echo -e "\033[0;32mInjecting workflows into project: $PROJECT_ROOT\033[0m"
        # Support both singular and plural for maximum compatibility
        for wfDir in ".agent" ".agents"; do
            targetProjectWf="$PROJECT_ROOT/$wfDir/workflows"
            mkdir -p "$targetProjectWf"
            cp -a "$SCRIPT_DIR/.agent/workflows/"* "$targetProjectWf/"
            
            # Ensure folder is hidden from GitHub (Git Protection)
            if [ -f "$PROJECT_ROOT/.gitignore" ]; then
                if ! grep -q "^$wfDir/" "$PROJECT_ROOT/.gitignore"; then
                    echo -e "\n# Antigravity Workflows\n$wfDir/" >> "$PROJECT_ROOT/.gitignore"
                fi
            fi
        done
        echo -e "\033[0;32mWorkflows successfully injected and hidden from Git!\033[0m"
    fi
fi

echo -e "\n\033[0;36mUpdate and Installation complete! Type 'OmniState activation' if slash commands are missing.\033[0m"
if [ -z "$NON_INTERACTIVE" ] && [ -z "$PROJECT_ROOT" ] && [[ $- == *i* ]]; then
    read -p "Press enter to exit..."
fi

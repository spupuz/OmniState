#!/bin/bash

# Optional: Target Project Path
PROJECT_ROOT="$1"

# Update and Install AntiGOptimize from GitHub
echo -e "\033[0;36mUpdating and Synchronizing AntiGOptimize...\033[0m"

# Change directory to the script's folder
cd "$(dirname "$0")" || exit

# 0. Self-Healing: Fix local folder inconsistencies
if [ -d "workflows" ]; then
    echo -e "\033[0;33mSelf-Healing: Moving legacy workflows to required hidden folder...\033[0m"
    mkdir -p .agent/workflows
    mv workflows/* .agent/workflows/ 2>/dev/null
    rm -rf workflows
fi

# 1. Update from GitHub (if applicable)
if command -v git &> /dev/null; then
    if [ -d ".git" ]; then
        echo -e "\033[0;32mFetching latest changes from GitHub...\033[0m"
        git pull origin main
    fi
fi

# 2. Automated Installation to Antigravity
pluginName="omnistate"
globalBaseDir="$HOME/.gemini/antigravity"
globalPluginsDir="$globalBaseDir/plugins"
globalWorkflowsDir="$globalBaseDir/workflows"
globalKnowledgeDir="$globalBaseDir/knowledge"
targetPluginPath="$globalPluginsDir/$pluginName"
targetKnowledgePath="$globalKnowledgeDir/$pluginName"

echo -e "\033[0;36mVerifying Global Installation in $globalBaseDir...\033[0m"

# A. Handle Global Plugins
if [ ! -d "$globalPluginsDir" ]; then
    echo -e "\033[0;33mCreating Antigravity plugins directory...\033[0m"
    mkdir -p "$globalPluginsDir"
fi

# Clean up old installation
if [ -e "$targetPluginPath" ]; then
    echo -e "\033[0;33mCleaning up old global plugin...\033[0m"
    rm -rf "$targetPluginPath"
fi
mkdir -p "$targetPluginPath"

# Copy everything EXCEPT .git and .agent to the plugin folder
echo -e "\033[0;32mInstalling OmniState plugin components...\033[0m"
cp -a . "$targetPluginPath/"
rm -rf "$targetPluginPath/.git"
rm -rf "$targetPluginPath/.agent"

# B. Handle Global Workflows (Critical for Slash Commands)
if [ ! -d "$globalWorkflowsDir" ]; then
    echo -e "\033[0;33mCreating Antigravity global workflows directory...\033[0m"
    mkdir -p "$globalWorkflowsDir"
fi

echo -e "\033[0;32mInstalling Slash Commands globally...\033[0m"
if [ -d ".agent/workflows" ]; then
    cp -a .agent/workflows/* "$globalWorkflowsDir/"
fi

# C. Universal Discovery: Create Knowledge Item (KI)
echo -e "\033[0;36mRegistering OmniState for Universal Discovery (Knowledge Item)...\033[0m"
mkdir -p "$targetKnowledgePath/artifacts"

cat <<EOF > "$targetKnowledgePath/metadata.json"
{
  "summary": "OmniState Global Plugin: Persistent Memory, Cost Savings, and Model Optimization. Essential for any project to manage tasks, snapshots, and start reduced sessions. Keywords: cost-setup, start-session, snapshot-session, project-summary, tokens.",
  "updatedAt": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "references": []
}
EOF

cat <<EOF > "$targetKnowledgePath/artifacts/omnistate-info.md"
# OmniState Global Plugin Guide

OmniState is correctly installed as a global plugin on this machine.
If you are in a brand-new project and you do NOT see the slash commands (like /cost-setup, /start-session), it means they need to be initialized for THIS workspace.

### How to use:
1. **Command:** Execute the **cost-setup** skill from the global plugins directory.
2. **Path:** $targetPluginPath
3. **Action:** The skill will automatically install the project-specific workflows to activate the slash commands.

*Always mention 'OmniState' or 'cost-setup' to trigger this knowledge.*
EOF

echo -e "\033[0;32mOmniState successfully installed and registered globally!\033[0m"

# 3. Optional: Inject into project root if provided
if [ -n "$PROJECT_ROOT" ]; then
    if [ -d "$PROJECT_ROOT" ]; then
        echo -e "\033[0;32mInjecting workflows into project: $PROJECT_ROOT\033[0m"
        targetProjectWf="$PROJECT_ROOT/.agent/workflows"
        mkdir -p "$targetProjectWf"
        cp -a .agent/workflows/* "$targetProjectWf/"
        echo -e "\033[0;32mWorkflows successfully injected!\033[0m"
    else
        echo -e "\033[0;31mWarning: Target Project Path not found: $PROJECT_ROOT\033[0m"
    fi
fi

echo -e "\n\033[0;36mUpdate and Installation complete! Project is now up to date and active.\033[0m"
if [ -z "$NON_INTERACTIVE" ] && [ -z "$PROJECT_ROOT" ]; then
    read -p "Press enter to exit..."
fi

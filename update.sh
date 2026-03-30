#!/bin/bash

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
globalPluginsDir="$HOME/.gemini/antigravity/plugins"
targetPath="$globalPluginsDir/$pluginName"

echo -e "\033[0;36mVerifying Global Installation in $globalPluginsDir...\033[0m"

# Create plugins directory if it doesn't exist
if [ ! -d "$globalPluginsDir" ]; then
    echo -e "\033[0;33mCreating Antigravity plugins directory...\033[0m"
    mkdir -p "$globalPluginsDir"
fi

# Remove existing target to ensure fresh installation
if [ -L "$targetPath" ] || [ -e "$targetPath" ]; then
    echo -e "\033[0;33mCleaning up old installation...\033[0m"
    rm -rf "$targetPath"
fi

# Copy everything including hidden folders (.agent), preserving all attributes
echo -e "\033[0;32mInstalling OmniState to global plugins folder...\033[0m"
# Create path then copy
mkdir -p "$targetPath"
cp -a . "$targetPath/"
rm -rf "$targetPath/.git"

echo -e "\033[0;32mOmniState successfully installed globally!\033[0m"

echo -e "\n\033[0;36mUpdate and Installation complete! Project is now up to date and active.\033[0m"
if [ -z "$NON_INTERACTIVE" ]; then
    read -p "Press enter to exit..."
fi

#!/bin/bash

# Update AntiGOptimize from GitHub
echo "Updating AntiGOptimize from GitHub..."

# Change directory to the script's folder to ensure we're in the right place
cd "$(dirname "$0")"
echo "Working directory: $(pwd)"

# Check if git is installed
if ! command -v git &> /dev/null
then
    echo "Git is not installed or not in the PATH."
    exit 1
fi

repoUrl="https://github.com/spupuz/AntiGOptimize.git"

# Check if this is a git repository
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
    git remote add origin $repoUrl
fi

# Ensure the remote is set correctly
git remote set-url origin $repoUrl

# Fetch latest changes
echo "Fetching latest changes..."
git fetch origin main

# Check if we should reset or pull
if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
    echo "Synchronizing project files..."
    git reset --hard origin/main
else
    git pull origin main
fi

if [ $? -eq 0 ]; then
    echo "Update complete! Project is now up to date."
else
    echo "Update failed. Please check for merge conflicts or connection issues."
fi

# Optional: keep terminal open
read -p "Press enter to exit..."

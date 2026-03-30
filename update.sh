#!/bin/bash

# Update AntiGOptimize from GitHub
echo "Updating AntiGOptimize from GitHub..."

# Check if git is installed
if ! command -v git &> /dev/null
then
    echo "Git is not installed or not in the PATH."
    exit 1
fi

# Pull changes from main branch
git pull origin main

if [ $? -eq 0 ]; then
    echo "Update complete! Project is now up to date."
else
    echo "Update failed. Please check for merge conflicts or connection issues."
fi

# Optional: keep terminal open
read -p "Press enter to exit..."

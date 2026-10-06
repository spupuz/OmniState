#!/bin/sh
# Minimal install helper for OmniState v2
# Requires: git, docker, docker-compose, and basic shell

set -e

# Clone repo if not present
if [ ! -d "OmniState" ]; then
  echo "Cloning OmniState repository..."
  git clone https://github.com/spupuz/Omnistate.git OmniState || exit 1
fi
cd OmniState

# Copy .env.example if not present
if [ ! -f .env ]; then
  echo "Creating .env from .env.example"
  cp .env.example .env
fi

# Prompt for PROJECTS_ROOT
read -p "Enter absolute path to your projects root (e.g., /home/you/projects): " proj
if [ -z "$proj" ]; then
  echo "PROJECTS_ROOT required. Exiting."
  exit 1
fi
sed -i "s|^PROJECTS_ROOT=.*|PROJECTS_ROOT=$proj|" .env

# Optional GitHub PAT
read -p "Enter a GitHub PAT (or leave empty to skip): " token
if [ -n "$token" ]; then
  sed -i "s|^GITHUB_TOKEN=.*|GITHUB_TOKEN=$token|" .env || echo "GITHUB_TOKEN=$token" >> .env
fi

echo ""
echo "Setup complete!"
echo "Run:  docker compose up -d --build"
echo "Dashboard: http://localhost:8347"

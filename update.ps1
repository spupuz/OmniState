# Update and Install AntiGOptimize from GitHub
Write-Host "Updating and Synchronizing AntiGOptimize..." -ForegroundColor Cyan

# 0. Self-Healing: Fix local folder inconsistencies
$legacyWorkflows = Join-Path $PSScriptRoot "workflows"
$newWorkflows = Join-Path $PSScriptRoot ".agent\workflows"

if (Test-Path $legacyWorkflows) {
    Write-Host "Self-Healing: Moving legacy workflows to required hidden folder..." -ForegroundColor Yellow
    if (!(Test-Path $newWorkflows)) {
        New-Item -ItemType Directory -Path $newWorkflows -Force | Out-Null
    }
    Move-Item -Path "$legacyWorkflows\*" -Destination $newWorkflows -Force
    Remove-Item -Path $legacyWorkflows -Recurse -Force
}

# 1. Update from GitHub (if applicable)
if (Get-Command git -ErrorAction SilentlyContinue) {
    if (Test-Path ".git") {
        Write-Host "Fetching latest changes from GitHub..." -ForegroundColor Green
        git pull origin main
    }
}

# 2. Automated Installation to Antigravity
$pluginName = "omnistate"
$globalPluginsDir = "$HOME\.gemini\antigravity\plugins"
$targetPath = Join-Path $globalPluginsDir $pluginName

Write-Host "Verifying Global Installation in $globalPluginsDir..." -ForegroundColor Cyan

# Create plugins directory if it doesn't exist
if (!(Test-Path $globalPluginsDir)) {
    Write-Host "Creating Antigravity plugins directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $globalPluginsDir -Force | Out-Null
}

# Remove existing target completely to ensure fresh installation
if (Test-Path $targetPath) {
    Write-Host "Cleaning up old installation..." -ForegroundColor Yellow
    # Use -Force and -Recurse to remove even hidden/locked items in the target
    Remove-Item -Path $targetPath -Recurse -Force
}

# Create a fresh plugin directory
New-Item -ItemType Directory -Path $targetPath -Force | Out-Null

# Copy everything including hidden folders (.agent), excluding .git, one by one
Write-Host "Installing OmniState to global plugins folder..." -ForegroundColor Green
Get-ChildItem -Path $PSScriptRoot -Force -Exclude ".git" | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $targetPath -Recurse -Force
}
Write-Host "OmniState successfully installed globally!" -ForegroundColor Green

Write-Host "`nUpdate and Installation complete! Project is now up to date and active." -ForegroundColor Cyan
if ($args.Count -eq 0) { pause }

# Update and Install AntiGOptimize from GitHub

param(
    [string]$ProjectRoot = ""
)

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
$globalBaseDir = "$HOME\.gemini\antigravity"
$globalPluginsDir = Join-Path $globalBaseDir "plugins"
$globalWorkflowsDir = Join-Path $globalBaseDir "workflows"
$globalKnowledgeDir = Join-Path $globalBaseDir "knowledge"
$targetPluginPath = Join-Path $globalPluginsDir $pluginName
$targetKnowledgePath = Join-Path $globalKnowledgeDir $pluginName

Write-Host "Verifying Global Installation in $globalBaseDir..." -ForegroundColor Cyan

# A. Handle Global Plugins
if (!(Test-Path $globalPluginsDir)) {
    Write-Host "Creating Antigravity plugins directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $globalPluginsDir -Force | Out-Null
}

# Clean up old installation
if (Test-Path $targetPluginPath) {
    Write-Host "Cleaning up old global plugin..." -ForegroundColor Yellow
    Remove-Item -Path $targetPluginPath -Recurse -Force
}
New-Item -ItemType Directory -Path $targetPluginPath -Force | Out-Null

# Copy everything EXCEPT .git and .agent to the plugin folder
Write-Host "Installing OmniState plugin components..." -ForegroundColor Green
Get-ChildItem -Path $PSScriptRoot -Force -Exclude ".git", ".agent" | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $targetPluginPath -Recurse -Force
}

# B. Handle Global Workflows (Critical for Slash Commands)
if (!(Test-Path $globalWorkflowsDir)) {
    Write-Host "Creating Antigravity global workflows directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $globalWorkflowsDir -Force | Out-Null
}

Write-Host "Installing Slash Commands globally..." -ForegroundColor Green
$wfSource = Join-Path $PSScriptRoot ".agent\workflows"
if (Test-Path $wfSource) {
    Copy-Item -Path "$wfSource\*" -Destination $globalWorkflowsDir -Force
}

# C. Universal Discovery: Create Knowledge Item (KI)
Write-Host "Registering OmniState for Universal Discovery (Knowledge Item)..." -ForegroundColor Cyan
if (!(Test-Path $targetKnowledgePath)) {
    New-Item -ItemType Directory -Path $targetKnowledgePath -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $targetKnowledgePath "artifacts") -Force | Out-Null
}

$kiMetadata = @{
    summary = "OmniState Global Plugin: Persistent Memory, Cost Savings, and Model Optimization. Essential for any project to manage tasks, snapshots, and start reduced sessions. Keywords: cost-setup, start-session, snapshot-session, project-summary, tokens."
    updatedAt = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    references = @()
} | ConvertTo-Json

$kiInfo = @"
# OmniState Global Plugin Guide

OmniState is correctly installed as a global plugin on this machine.
If you are in a brand-new project and you do NOT see the slash commands (like /cost-setup, /start-session), it means they need to be initialized for THIS workspace.

### How to use:
1. **Command:** Execute the **cost-setup** skill from the global plugins directory.
2. **Path:** $targetPluginPath
3. **Action:** The skill will automatically install the project-specific workflows to activate the slash commands.

*Always mention 'OmniState' or 'cost-setup' to trigger this knowledge.*
"@

$kiMetadata | Out-File -FilePath (Join-Path $targetKnowledgePath "metadata.json") -Encoding UTF-8
$kiInfo | Out-File -FilePath (Join-Path $targetKnowledgePath "artifacts/omnistate-info.md") -Encoding UTF-8

Write-Host "OmniState successfully installed and registered globally!" -ForegroundColor Green

# 3. Optional: Inject into project root if provided
if ($ProjectRoot -ne "") {
    if (Test-Path $ProjectRoot) {
        Write-Host "Injecting workflows into project: $ProjectRoot" -ForegroundColor Green
        $targetProjectWf = Join-Path $ProjectRoot ".agent\workflows"
        if (!(Test-Path $targetProjectWf)) {
            New-Item -ItemType Directory -Path $targetProjectWf -Force | Out-Null
        }
        Copy-Item -Path "$wfSource\*" -Destination $targetProjectWf -Force
        Write-Host "Workflows successfully injected!" -ForegroundColor Green
    } else {
        Write-Warning "Target ProjectRoot not found: $ProjectRoot"
    }
}

Write-Host "`nUpdate and Installation complete! Project is now up to date and active." -ForegroundColor Cyan
if ($args.Count -eq 0 -and $ProjectRoot -eq "") { pause }

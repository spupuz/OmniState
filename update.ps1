# Update and Install OmniState from GitHub

param(
    [string]$ProjectRoot = ""
)

Write-Host "Updating and Synchronizing OmniState..." -ForegroundColor Cyan

# Change directory to the script's folder
Set-Location $PSScriptRoot

# 0. Self-Healing: Fix local folder inconsistencies
$legacyWf = Join-Path $PSScriptRoot "workflows"
$newWf = Join-Path $PSScriptRoot ".agent\workflows"

if ((Test-Path $legacyWf) -and !(Test-Path $newWf)) {
    Write-Host "Self-Healing: Moving legacy workflows..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $newWf -Force | Out-Null
    Copy-Item -Path "$legacyWf\*" -Destination $newWf -Force -Recurse
    Remove-Item -Path $legacyWf -Recurse -Force
}

# 1. Update from GitHub (if applicable)
if (Get-Command git -ErrorAction SilentlyContinue) {
    if (Test-Path ".git") {
        Write-Host "Fetching latest changes from GitHub..." -ForegroundColor Green
        git pull origin main --quiet
    }
}

# 2. Automated Installation to Antigravity (Universal Discovery)
$pluginName = "omnistate"
$globalBaseDir = "$HOME\.gemini\antigravity"
$globalPluginsDir = Join-Path $globalBaseDir "plugins"
$globalWorkflowsDir = Join-Path $globalBaseDir "workflows"
$globalKnowledgeDir = Join-Path $globalBaseDir "knowledge"
$targetPluginPath = Join-Path $globalPluginsDir $pluginName
$targetKnowledgePath = Join-Path $globalKnowledgeDir $pluginName

Write-Host "Targeting Global Installation in $globalBaseDir..." -ForegroundColor Cyan

# Ensure layout exists
if (!(Test-Path $globalPluginsDir)) { New-Item -ItemType Directory -Path $globalPluginsDir -Force | Out-Null }
if (!(Test-Path $globalWorkflowsDir)) { New-Item -ItemType Directory -Path $globalWorkflowsDir -Force | Out-Null }
if (!(Test-Path $globalKnowledgeDir)) { New-Item -ItemType Directory -Path $globalKnowledgeDir -Force | Out-Null }

# Clean up and Install Plugin
if (Test-Path $targetPluginPath) { Remove-Item -Path $targetPluginPath -Recurse -Force }
New-Item -ItemType Directory -Path $targetPluginPath -Force | Out-Null

# Copy everything EXCEPT .git and .agent to the plugin folder
Write-Host "Installing OmniState plugin components..." -ForegroundColor Green
Get-ChildItem -Path $PSScriptRoot -Force -Exclude ".git", ".agent" | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $targetPluginPath -Recurse -Force
}

# Install Slash Commands globally
Write-Host "Installing Slash Commands globally..." -ForegroundColor Green
$wfSource = Join-Path $PSScriptRoot ".agent\workflows"
if (Test-Path $wfSource) { Copy-Item -Path "$wfSource\*" -Destination $globalWorkflowsDir -Force }

# C. Universal Discovery: Create Knowledge Item (KI)
Write-Host "Registering OmniState for Universal Discovery..." -ForegroundColor Cyan
if (!(Test-Path $targetKnowledgePath)) {
    New-Item -ItemType Directory -Path $targetKnowledgePath -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $targetKnowledgePath "artifacts") -Force | Out-Null
}

$kiMetadata = @{
    summary = "OmniState Global Plugin (v1.0.1): Persistent Memory, Cost Savings, and Model Optimization. Found at $targetPluginPath. Essential for any project. Keywords: cost-setup, start-session, snapshot-session, project-summary, tokens."
    updatedAt = (Get-Date -uformat "%Y-%m-%dT%H:%M:%SZ")
    references = @($targetPluginPath)
} | ConvertTo-Json

$kiInfo = @"
# OmniState Global Plugin Guide

OmniState is correctly installed as a global plugin on this machine.
If slash commands (like /cost-setup) are not visible in the UI, it's because the project isn't initialized yet.

### CRITICAL ACTIVATION:
To activate OmniState in THIS workspace, the agent MUST:
1. Locate the **cost-setup** skill in: $targetPluginPath
2. **Action:** Execute the skill 'cost-setup' using the `run_skill` or `view_file` on its SKILL.md.
3. The skill will automatically install the project-specific workflows to activate the slash commands.

*Always mention 'OmniState' or 'cost-setup' to trigger this knowledge.*
"@

$kiMetadata | Out-File -FilePath (Join-Path $targetKnowledgePath "metadata.json") -Encoding UTF8 -Force
$kiInfo | Out-File -FilePath (Join-Path $targetKnowledgePath "artifacts/omnistate-info.md") -Encoding UTF8 -Force

Write-Host "OmniState successfully installed and registered globally!" -ForegroundColor Green

# 3. Optional: Inject into project root if provided
if (($ProjectRoot -ne "") -and (Test-Path $ProjectRoot)) {
    Write-Host "Injecting workflows into project: $ProjectRoot" -ForegroundColor Green
    $wfSource = Join-Path $PSScriptRoot ".agent\workflows"
    $wfDirs = @(".agent", ".agents")
    foreach ($wfDir in $wfDirs) {
        $targetProjectWf = Join-Path $ProjectRoot "$wfDir\workflows"
        if (!(Test-Path $targetProjectWf)) { New-Item -ItemType Directory -Path $targetProjectWf -Force | Out-Null }
        Copy-Item -Path "$wfSource\*" -Destination $targetProjectWf -Force
        
        # Git Protection: Ensure folder is hidden
        $gitignoreFile = Join-Path $ProjectRoot ".gitignore"
        if (Test-Path $gitignoreFile) {
            $content = Get-Content $gitignoreFile -Raw
            if ($content -notmatch "\n$wfDir/") {
                Add-Content -Path $gitignoreFile -Value "`n# Antigravity Workflows`n$wfDir/" -Encoding UTF8
            }
        }
    }
    Write-Host "Workflows successfully injected and hidden from Git!" -ForegroundColor Green
}

Write-Host "`nUpdate and Installation complete! Type 'OmniState activation' if slash commands are missing." -ForegroundColor Cyan
if ($args.Count -eq 0 -and $ProjectRoot -eq "" -and $Host.Name -eq "ConsoleHost") { pause }
# End of OmniState update script

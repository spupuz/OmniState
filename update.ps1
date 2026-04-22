# OmniState Update & Sync Script (v1.1.1)
# PowerShell version for Windows and cross-platform compatibility

param(
    [string]$ProjectRoot = "",
    [switch]$SyncOnly,
    [switch]$Auto,
    [switch]$Check,
    [switch]$Silent
)

# 1. Configuration & Paths
$scriptDir = $PSScriptRoot
$versionFile = Join-Path $scriptDir "VERSION.txt"
$version = if (Test-Path $versionFile) { (Get-Content $versionFile -Raw).Trim() } else { "1.1.1" }
$pluginName = "omnistate"

# Detect global directories
$globalBaseDir = Join-Path $HOME ".gemini\antigravity"
$globalPluginsDir = Join-Path $globalBaseDir "plugins"
$globalWorkflowsDir = Join-Path $globalBaseDir "workflows"
$globalKnowledgeDir = Join-Path $globalBaseDir "knowledge"
$targetPluginPath = Join-Path $globalPluginsDir $pluginName

function Write-Log($message, $color = "White") {
    if (!$Silent) {
        Write-Host $message -ForegroundColor $color
    }
}

# 2. Helpers
function Sync-Workflows($targetProject) {
    $sourceWf = Join-Path $targetPluginPath "dist\workflows"
    if (!(Test-Path $sourceWf)) { $sourceWf = Join-Path $scriptDir "dist\workflows" }
    
    $sourceTemplates = Join-Path $targetPluginPath "dist\templates"
    if (!(Test-Path $sourceTemplates)) { $sourceTemplates = Join-Path $scriptDir "dist\templates" }

    if ((Test-Path $targetProject) -and (Test-Path $sourceWf)) {
        Write-Log "Synchronizing OmniState components to $targetProject..." "Cyan"
        $wfDirs = @(".agent", ".agents")
        foreach ($wfDir in $wfDirs) {
            # Sync Workflows
            $destWf = Join-Path $targetProject "$wfDir\workflows"
            if (!(Test-Path $destWf)) { New-Item -ItemType Directory -Path $destWf -Force | Out-Null }
            Copy-Item -Path "$sourceWf\*" -Destination $destWf -Force
            
            # Sync Templates
            if (Test-Path $sourceTemplates) {
                $destTemplates = Join-Path $targetProject "$wfDir\templates"
                if (!(Test-Path $destTemplates)) { New-Item -ItemType Directory -Path $destTemplates -Force | Out-Null }
                Copy-Item -Path "$sourceTemplates\*" -Destination $destTemplates -Force
            }

            # Git Protection
            $gitignore = Join-Path $targetProject ".gitignore"
            if (Test-Path $gitignore) {
                $content = Get-Content $gitignore -Raw
                foreach ($pattern in @("$wfDir/", "/omnistate-dashboard.html", "project-summary.md", "tasks-history.json", "tasks-archive.json", "antigravity.config.json", "chunks/")) {
                    if ($content -notmatch [regex]::Escape($pattern)) {
                        Add-Content -Path $gitignore -Value "$pattern" -Encoding UTF8
                    }
                }
            }
        }
        Write-Log "Components synchronized and Git Protection enforced." "Green"
    }
}

function Check-GitHubUpdate {
    $gitPath = Join-Path $targetPluginPath ".git"
    if (Test-Path $gitPath) {
        Set-Location $targetPluginPath
        if (Get-Command git -ErrorAction SilentlyContinue) {
            $remoteHash = (git ls-remote origin -h refs/heads/main).Split("`t")[0]
            $localHash = (git rev-parse HEAD)
            if ($remoteHash -ne $localHash) { return $false } # Update available
        }
    }
    return $true # Up to date
}

# 3. Actions Logic
if ($Check) {
    if (Check-GitHubUpdate) { exit 0 } else { exit 1 }
}

if ($Auto) {
    $lastCheckFile = Join-Path $targetPluginPath ".last_update_check"
    $now = [DateTimeOffset]::Now.ToUnixTimeSeconds()
    $lastCheck = if (Test-Path $lastCheckFile) { (Get-Content $lastCheckFile).Trim() } else { 0 }
    
    if ($now - $lastCheck -gt 86400) {
        Write-Log "Checking for OmniState global updates..." "Yellow"
        if (!(Check-GitHubUpdate)) {
            Write-Log "New version detected! Updating global OmniState..." "Green"
            Set-Location $targetPluginPath
            git pull origin main --quiet
            Set-Content -Path $lastCheckFile -Value $now
            # Re-run install
            powershell -File (Join-Path $targetPluginPath "update.ps1") -Silent
        } else {
            Set-Content -Path $lastCheckFile -Value $now
        }
    }
    if ($ProjectRoot -ne "") {
        Sync-Workflows $ProjectRoot
    }
    exit 0
}

if ($SyncOnly) {
    Sync-Workflows $ProjectRoot
    exit 0
}

# 4. Default Install Logic
Write-Log "Installing/Updating OmniState Globale (v$version)..." "Cyan"

# Self-Healing
$legacyWf = Join-Path $scriptDir "workflows"
$newWf = Join-Path $scriptDir ".agent\workflows"
if ((Test-Path $legacyWf) -and !(Test-Path $newWf)) {
    New-Item -ItemType Directory -Path $newWf -Force | Out-Null
    Copy-Item -Path "$legacyWf\*" -Destination $newWf -Force -Recurse
    Remove-Item -Path $legacyWf -Recurse -Force
}

# Update from Git if in the source repo
if ((Test-Path (Join-Path $scriptDir ".git")) -and (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Log "Fetching latest changes..." "Green"
    git pull origin main --quiet
}

# Ensure global layout
if (!(Test-Path $globalPluginsDir)) { New-Item -ItemType Directory -Path $globalPluginsDir -Force | Out-Null }
if (!(Test-Path $globalWorkflowsDir)) { New-Item -ItemType Directory -Path $globalWorkflowsDir -Force | Out-Null }
if (!(Test-Path $globalKnowledgeDir)) { New-Item -ItemType Directory -Path $globalKnowledgeDir -Force | Out-Null }

# Install Plugin
if (Test-Path $targetPluginPath) { Remove-Item -Path $targetPluginPath -Recurse -Force }
New-Item -ItemType Directory -Path $targetPluginPath -Force | Out-Null
Copy-Item -Path "$scriptDir\*" -Destination $targetPluginPath -Recurse -Exclude ".git"

# Register Knowledge Item
$targetKnowledgePath = Join-Path $globalKnowledgeDir $pluginName
if (!(Test-Path $targetKnowledgePath)) { New-Item -ItemType Directory -Path $targetKnowledgePath -Force | Out-Null }
$kiMetadata = @{
    summary = "OmniState Global Plugin (v$version): Persistent Memory, Cost Savings, and Model Optimization. Keywords: cost-setup, start-session, snapshot-session, project-summary, tokens."
    updatedAt = (Get-Date -uformat "%Y-%m-%dT%H:%M:%SZ")
    references = @($targetPluginPath)
} | ConvertTo-Json
$kiMetadata | Out-File -FilePath (Join-Path $targetKnowledgePath "metadata.json") -Encoding UTF8 -Force

# Global Workflows
$wfSource = Join-Path $scriptDir ".agent\workflows"
if (Test-Path $wfSource) { Copy-Item -Path "$wfSource\*" -Destination $globalWorkflowsDir -Force }

Write-Log "OmniState v$version successfully installed globally!" "Green"

if ($ProjectRoot -ne "") {
    Sync-Workflows $ProjectRoot
}

Write-Log "`nAll set! Type 'OmniState activation' if slash commands are missing." "Cyan"
if ($args.Count -eq 0 -and $ProjectRoot -eq "" -and $Host.Name -eq "ConsoleHost") { pause }

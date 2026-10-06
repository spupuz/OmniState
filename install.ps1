# Minimal install helper for OmniState v2 (Windows PowerShell)
# Requires: git, docker, docker-compose

# Clone repo if not present
if (-not (Test-Path "OmniState")) {
    Write-Host "Cloning OmniState repository..."
    git clone https://github.com/spupuz/Omnistate.git OmniState
}
Set-Location OmniState

# Copy .env.example if not present
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
}

# Prompt for PROJECTS_ROOT
$proj = Read-Host "Enter absolute path to your projects root (e.g., C:\Users\you\projects)"
if (-not $proj) {
    Write-Host "PROJECTS_ROOT required. Exiting."
    exit 1
}
$envContent = Get-Content .env
$envContent = $envContent -replace "^PROJECTS_ROOT=.*", "PROJECTS_ROOT=$proj"
$envContent | Set-Content .env

# Optional GitHub PAT
$token = Read-Host "Enter a GitHub PAT (or leave empty to skip)"
if ($token) {
    if ($envContent -match "^GITHUB_TOKEN=") {
        $envContent = $envContent -replace "^GITHUB_TOKEN=.*", "GITHUB_TOKEN=$token"
    } else {
        Add-Content .env "GITHUB_TOKEN=$token"
    }
    $envContent | Set-Content .env
}

Write-Host ""
Write-Host "Setup complete!"
Write-Host "Run:  docker compose up -d --build"
Write-Host "Dashboard: http://localhost:8347"

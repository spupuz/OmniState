# Update AntiGOptimize from GitHub
Write-Host "Updating AntiGOptimize from GitHub..." -ForegroundColor Cyan

# Check if git is installed
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git is not installed or not in the PATH."
    exit 1
}

$repoUrl = "https://github.com/spupuz/AntiGOptimize.git"

# Check if this is a git repository
if (!(Test-Path ".git")) {
    Write-Host "Initializing git repository..." -ForegroundColor Yellow
    git init
    git remote add origin $repoUrl
}

# Ensure the remote is set correctly
git remote set-url origin $repoUrl

# Fetch and pull
Write-Host "Fetching latest changes..." -ForegroundColor Green
git fetch origin main

# Check if we should reset or pull
# If there are no commits yet (brand new init), we need a reset
$commitCount = git rev-list --count HEAD 2>$null
if ($LASTEXITCODE -ne 0 -or $commitCount -eq 0) {
    Write-Host "Synchronizing project files..." -ForegroundColor Yellow
    git reset --hard origin/main
} else {
    git pull origin main
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "Update complete! Project is now up to date." -ForegroundColor Green
} else {
    Write-Error "Update failed. Please check for merge conflicts or connection issues."
}
pause

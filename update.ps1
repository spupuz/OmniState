# Update AntiGOptimize from GitHub
Write-Host "Updating AntiGOptimize from GitHub..." -ForegroundColor Cyan

# Check if git is installed
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git is not installed or not in the PATH."
    exit 1
}

# Pull changes from main branch
git pull origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "Update complete! Project is now up to date." -ForegroundColor Green
} else {
    Write-Error "Update failed. Please check for merge conflicts or connection issues."
}
pause

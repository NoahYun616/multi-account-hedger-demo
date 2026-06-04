Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = "python"
$Venv = Join-Path $Root ".venv-build"
$BuildOut = Join-Path $Root "release"
$ReleaseName = "MultiAccountHedger-Windows"
$ReleaseDir = Join-Path $BuildOut $ReleaseName
$ZipPath = Join-Path $BuildOut "$ReleaseName.zip"

Write-Host "== Multi Account Hedger Windows Build =="
Write-Host "Project: $Root"

if (-not (Test-Path $Venv)) {
  Write-Host "Creating build virtual environment..."
  & $Python -m venv $Venv
}

$VenvPython = Join-Path $Venv "Scripts\python.exe"

Write-Host "Installing build dependencies..."
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements-windows-build.txt

Write-Host "Running syntax and unit checks..."
& $VenvPython -m compileall -q app.py launcher.py dashboard.py clients core notify tests windows_dashboard.py windows_engine.py
& $VenvPython -m unittest discover -s tests

Write-Host "Building dashboard exe..."
& $VenvPython -m PyInstaller --noconfirm --clean packaging\windows\MultiAccountHedgerDashboard.spec

Write-Host "Building engine exe..."
& $VenvPython -m PyInstaller --noconfirm --clean packaging\windows\MultiAccountHedgerEngine.spec

if (Test-Path $ReleaseDir) {
  Remove-Item -Recurse -Force $ReleaseDir
}
New-Item -ItemType Directory -Force $ReleaseDir | Out-Null

Write-Host "Assembling release directory..."
Copy-Item -Recurse -Force "dist\MultiAccountHedgerDashboard" (Join-Path $ReleaseDir "Dashboard")
Copy-Item -Recurse -Force "dist\MultiAccountHedgerEngine" (Join-Path $ReleaseDir "Engine")
Copy-Item -Force "README_WINDOWS.md" (Join-Path $ReleaseDir "README_WINDOWS.md")
Copy-Item -Force "requirements-windows-build.txt" (Join-Path $ReleaseDir "requirements-windows-build.txt")

New-Item -ItemType Directory -Force (Join-Path $ReleaseDir "config") | Out-Null
Copy-Item -Force "config\global_config.json" (Join-Path $ReleaseDir "config\global_config.json")
Copy-Item -Force "config\strategy_config.json" (Join-Path $ReleaseDir "config\strategy_config.json")
Copy-Item -Force "config\accounts.json.example" (Join-Path $ReleaseDir "config\accounts.json.example")

New-Item -ItemType Directory -Force (Join-Path $ReleaseDir "logs") | Out-Null

@"
@echo off
cd /d "%~dp0Dashboard"
MultiAccountHedgerDashboard.exe
"@ | Set-Content -Encoding ASCII (Join-Path $ReleaseDir "启动前端控制台.bat")

@"
@echo off
cd /d "%~dp0Engine"
MultiAccountHedgerEngine.exe
pause
"@ | Set-Content -Encoding ASCII (Join-Path $ReleaseDir "启动同步引擎.bat")

if (Test-Path $ZipPath) {
  Remove-Item -Force $ZipPath
}

Write-Host "Creating zip..."
Compress-Archive -Path (Join-Path $ReleaseDir "*") -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "Build complete:"
Write-Host $ZipPath
Write-Host ""
Write-Host "You can run:"
Write-Host (Join-Path $ReleaseDir "启动前端控制台.bat")
Write-Host (Join-Path $ReleaseDir "启动同步引擎.bat")

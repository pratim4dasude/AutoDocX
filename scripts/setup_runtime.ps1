$ErrorActionPreference = "Stop"

$PythonVersion = "3.11.9"

# This script is inside AutoDocX\scripts.
# The parent folder of scripts is the AutoDocX project root.
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "============================================"
Write-Host "     Preparing AutoDocX Private Runtime"
Write-Host "============================================"
Write-Host ""
Write-Host "Project root: $ProjectRoot"
Write-Host "Python version: $PythonVersion"
Write-Host ""

$RuntimeDirectory = Join-Path $ProjectRoot "runtime"
$PythonDirectory = Join-Path $RuntimeDirectory "python"
$DownloadDirectory = Join-Path $RuntimeDirectory "downloads"

$ArchiveName = "python-$PythonVersion-embed-amd64.zip"
$ArchivePath = Join-Path $DownloadDirectory $ArchiveName

$DownloadUrl = (
    "https://www.python.org/ftp/python/" +
    "$PythonVersion/$ArchiveName"
)

$PythonExecutable = Join-Path $PythonDirectory "python.exe"
$GetPipPath = Join-Path $DownloadDirectory "get-pip.py"
$RequirementsPath = Join-Path $ProjectRoot "requirements.txt"

Write-Host "[1/7] Creating runtime directories..."

New-Item `
    -ItemType Directory `
    -Force `
    -Path $RuntimeDirectory | Out-Null

New-Item `
    -ItemType Directory `
    -Force `
    -Path $DownloadDirectory | Out-Null

if (Test-Path $PythonDirectory) {
    Write-Host "Removing previous private runtime..."

    Remove-Item `
        -Path $PythonDirectory `
        -Recurse `
        -Force
}

New-Item `
    -ItemType Directory `
    -Force `
    -Path $PythonDirectory | Out-Null

Write-Host "[2/7] Downloading Python $PythonVersion..."
Write-Host "Source: $DownloadUrl"

Invoke-WebRequest `
    -Uri $DownloadUrl `
    -OutFile $ArchivePath `
    -UseBasicParsing

if (-not (Test-Path $ArchivePath)) {
    throw "Python embedded package was not downloaded."
}

Write-Host "[3/7] Extracting private Python..."

Expand-Archive `
    -Path $ArchivePath `
    -DestinationPath $PythonDirectory `
    -Force

if (-not (Test-Path $PythonExecutable)) {
    throw "python.exe was not found after extraction."
}

$VersionParts = $PythonVersion.Split(".")

if ($VersionParts.Count -lt 2) {
    throw "Invalid Python version: $PythonVersion"
}

$MajorMinor = "$($VersionParts[0])$($VersionParts[1])"
$PthFile = Join-Path $PythonDirectory "python$MajorMinor._pth"

if (-not (Test-Path $PthFile)) {
    throw "Embedded Python configuration file was not found: $PthFile"
}

Write-Host "[4/7] Configuring isolated package paths..."

$PthContent = @"
python$MajorMinor.zip
.
Lib
Lib\site-packages

import site
"@

Set-Content `
    -Path $PthFile `
    -Value $PthContent `
    -Encoding ASCII

New-Item `
    -ItemType Directory `
    -Force `
    -Path (Join-Path $PythonDirectory "Lib") | Out-Null

New-Item `
    -ItemType Directory `
    -Force `
    -Path (Join-Path $PythonDirectory "Lib\site-packages") | Out-Null

Write-Host "[5/7] Downloading pip installer..."

Invoke-WebRequest `
    -Uri "https://bootstrap.pypa.io/get-pip.py" `
    -OutFile $GetPipPath `
    -UseBasicParsing

if (-not (Test-Path $GetPipPath)) {
    throw "get-pip.py was not downloaded."
}

Write-Host "[6/7] Installing pip into private Python..."

& $PythonExecutable `
    $GetPipPath `
    --no-warn-script-location

if ($LASTEXITCODE -ne 0) {
    throw "pip installation failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path $RequirementsPath)) {
    throw "requirements.txt was not found: $RequirementsPath"
}

Write-Host "[7/7] Installing AutoDocX dependencies..."

& $PythonExecutable `
    -m pip install `
    --disable-pip-version-check `
    --no-warn-script-location `
    -r $RequirementsPath

if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "Verifying AutoDocX runtime..."

& $PythonExecutable `
    -c "import fastapi, uvicorn; print('Runtime verification successful.')"

if ($LASTEXITCODE -ne 0) {
    throw "Runtime verification failed."
}

Write-Host ""
Write-Host "============================================"
Write-Host "     Private Runtime Created Successfully"
Write-Host "============================================"
Write-Host ""
Write-Host "Runtime location:"
Write-Host $PythonDirectory
Write-Host ""
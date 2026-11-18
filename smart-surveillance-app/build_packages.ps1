$ErrorActionPreference = "Stop"

$currentDir = Get-Location
$distPath = Join-Path -Path $currentDir -ChildPath "dist"

Write-Host "Creating dist directory if it does not exist..."
if (!(Test-Path -Path $distPath)) {
    New-Item -ItemType Directory -Path $distPath | Out-Null
}

Write-Host "Building Smart Surveillance App..."
Set-Location -Path $currentDir
# Build SmartSurveillance
pyinstaller SmartSurveillance.spec --distpath $distPath -y
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to build SmartSurveillance"
    exit 1
}

Write-Host "Building Face Recognition App..."
$faceRecogDir = Join-Path -Path (Split-Path -Path $currentDir -Parent) -ChildPath "smart-Face-Recognization"
Set-Location -Path $faceRecogDir
pyinstaller Smart-Face-Recognization.spec --distpath $distPath -y
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to build Face Recognition"
    exit 1
}

Write-Host "Building Unattended Object App..."
$unattendedObjDir = Join-Path -Path (Split-Path -Path $currentDir -Parent) -ChildPath "smart-unattended-object"
Set-Location -Path $unattendedObjDir
pyinstaller UnattendedObject.spec --distpath $distPath -y
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to build Unattended Object"
    exit 1
}

Set-Location -Path $currentDir
Write-Host "All applications successfully built and placed into $distPath"

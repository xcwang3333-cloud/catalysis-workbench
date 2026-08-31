param(
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [Parameter(Mandatory = $true)][string]$ReleaseSource,
    [Parameter(Mandatory = $true)][string]$InfraSource,
    [Parameter(Mandatory = $true)][string]$ConstraintsFile,
    [Parameter(Mandatory = $true)][string]$IsccPath,
    [Parameter(Mandatory = $true)][string]$ExpectedTag,
    [Parameter(Mandatory = $true)][string]$ExpectedReleaseSha,
    [Parameter(Mandatory = $true)][string]$ExpectedVersion,
    [Parameter(Mandatory = $true)][string]$OutputRoot
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-LastExitCode([string]$Label) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

$ReleaseSource = (Resolve-Path $ReleaseSource).Path
$InfraSource = (Resolve-Path $InfraSource).Path
$ConstraintsFile = (Resolve-Path $ConstraintsFile).Path
$IsccPath = (Resolve-Path $IsccPath).Path
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$OutputRoot = (Resolve-Path $OutputRoot).Path

$releaseHead = (& git -C $ReleaseSource rev-parse HEAD).Trim()
Assert-LastExitCode "git rev-parse release source"
if ($releaseHead -ne $ExpectedReleaseSha) {
    throw "Release source drift: expected $ExpectedReleaseSha, got $releaseHead"
}

$releaseTagCommit = (& git -C $ReleaseSource rev-list -n 1 $ExpectedTag).Trim()
Assert-LastExitCode "git resolve release tag"
if ($releaseTagCommit -ne $ExpectedReleaseSha) {
    throw "Release tag drift: $ExpectedTag resolves to $releaseTagCommit"
}

$runtimeVersion = (& $PythonExe -c "import catalysis_workbench; print(catalysis_workbench.__version__)").Trim()
Assert-LastExitCode "runtime version check"
if ($runtimeVersion -ne $ExpectedVersion) {
    throw "Installed runtime version drift: expected $ExpectedVersion, got $runtimeVersion"
}

$pyinstallerVersion = (& $PythonExe -m PyInstaller --version).Trim()
Assert-LastExitCode "PyInstaller version check"
if ($pyinstallerVersion -ne "6.22.2") {
    throw "Unexpected PyInstaller version: $pyinstallerVersion"
}

$buildRoot = Join-Path $OutputRoot "build"
$frozenRoot = Join-Path $buildRoot "frozen"
$workRoot = Join-Path $buildRoot "pyinstaller"
$artifactRoot = Join-Path $OutputRoot "artifact"
New-Item -ItemType Directory -Force -Path $frozenRoot, $workRoot, $artifactRoot | Out-Null

$spec = Join-Path $InfraSource "packaging\windows\CatalysisWorkbench.spec"
& $PythonExe -m PyInstaller `
    --clean `
    --noconfirm `
    --distpath $frozenRoot `
    --workpath $workRoot `
    $spec
Assert-LastExitCode "PyInstaller build"

$appDir = Join-Path $frozenRoot "CatalysisWorkbench"
$appExe = Join-Path $appDir "CatalysisWorkbench.exe"
if (-not (Test-Path $appExe -PathType Leaf)) {
    throw "Frozen executable not found: $appExe"
}

$env:QT_QPA_PLATFORM = "offscreen"
$env:CATALYSIS_WORKBENCH_EXPECTED_VERSION = $ExpectedVersion
$frozenSmoke = Start-Process -FilePath $appExe -ArgumentList @("--installer-smoke") -Wait -PassThru
if ($frozenSmoke.ExitCode -ne 0) {
    throw "frozen desktop smoke failed with exit code $($frozenSmoke.ExitCode)"
}

$resolvedRequirements = Join-Path $artifactRoot "resolved-requirements.txt"
(& $PythonExe -m pip list --format=freeze --exclude catalysis-workbench) |
    Sort-Object |
    Set-Content -Path $resolvedRequirements -Encoding utf8

$notices = Join-Path $artifactRoot "THIRD_PARTY_NOTICES.txt"
& $PythonExe (Join-Path $InfraSource "packaging\windows\collect_notices.py") --output $notices
Assert-LastExitCode "third-party notice generation"

$requirementsHash = (Get-FileHash -Algorithm SHA256 $resolvedRequirements).Hash.ToLowerInvariant()
$constraintsHash = (Get-FileHash -Algorithm SHA256 $ConstraintsFile).Hash.ToLowerInvariant()
$infraSha = (& git -C $InfraSource rev-parse HEAD).Trim()
Assert-LastExitCode "git resolve packaging infrastructure head"

$buildProvenance = [ordered]@{
    schema_version = 1
    product = "CatalysisWorkbench"
    product_version = $ExpectedVersion
    release_tag = $ExpectedTag
    release_commit = $ExpectedReleaseSha
    packaging_infrastructure_commit = $infraSha
    platform = "windows-x64"
    python_version = (& $PythonExe -c "import platform; print(platform.python_version())").Trim()
    pyinstaller_version = $pyinstallerVersion
    inno_setup_compiler = (Get-Item $IsccPath).VersionInfo.ProductVersion
    dependency_constraints_sha256 = $constraintsHash
    resolved_requirements_sha256 = $requirementsHash
    code_signing = "unsigned-readiness-build"
}
$buildProvenancePath = Join-Path $artifactRoot "BUILD_PROVENANCE.json"
$buildProvenance | ConvertTo-Json -Depth 4 | Set-Content -Path $buildProvenancePath -Encoding utf8
Copy-Item $ConstraintsFile (Join-Path $artifactRoot "constraints-v1.1.0-windows-x64.txt")

$licenseFile = Join-Path $ReleaseSource "LICENSE"
if (-not (Test-Path $licenseFile -PathType Leaf)) {
    throw "Release LICENSE file is missing"
}

$iss = Join-Path $InfraSource "packaging\windows\CatalysisWorkbench.iss"
& $IsccPath `
    "/DAppVersion=$ExpectedVersion" `
    "/DAppSource=$appDir" `
    "/DOutputDir=$artifactRoot" `
    "/DLicenseFile=$licenseFile" `
    "/DNoticesFile=$notices" `
    "/DBuildProvenance=$buildProvenancePath" `
    $iss
Assert-LastExitCode "Inno Setup compile"

$installer = Join-Path $artifactRoot "CatalysisWorkbench-$ExpectedVersion-windows-x64-setup.exe"
if (-not (Test-Path $installer -PathType Leaf)) {
    throw "Installer was not produced: $installer"
}

$installerHash = (Get-FileHash -Algorithm SHA256 $installer).Hash.ToLowerInvariant()
"$installerHash  $(Split-Path $installer -Leaf)" |
    Set-Content -Path (Join-Path $artifactRoot "SHA256SUMS.txt") -Encoding ascii

Write-Host "Installer readiness artifact: $installer"

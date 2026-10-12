param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$skillDirectory = Split-Path -Parent $PSScriptRoot
$vendorDirectory = Join-Path $skillDirectory 'vendor/jev-ultrafast'
$revision = '1231850a0bf1a0c0341fe408ef1668dbbfdfac46'
& $Python -c 'import sys; assert sys.version_info >= (3,12), "Python 3.12+ required"'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12+ required' }
if (!(Test-Path -LiteralPath $vendorDirectory)) {
    git clone https://github.com/browser-use/jev-ultrafast.git $vendorDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Jev clone failed' }
    git -C $vendorDirectory checkout --detach $revision
    if ($LASTEXITCODE -ne 0) { throw 'Pinned revision checkout failed' }
} else {
    $actualRevision = git -C $vendorDirectory rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $actualRevision.Trim() -ne $revision) {
        throw 'Existing vendor revision differs. Preserve your changes and inspect before replacing it.'
    }
}
$venvDirectory = Join-Path $skillDirectory '.venv'
if (!(Test-Path -LiteralPath $venvDirectory)) {
    & $Python -m venv $venvDirectory
    if ($LASTEXITCODE -ne 0) { throw 'venv creation failed' }
}
$venvPython = Join-Path $venvDirectory 'Scripts/python.exe'
& $venvPython -m pip install -r (Join-Path $skillDirectory 'requirements.txt') -e $vendorDirectory
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $venvPython -X utf8 -B (Join-Path $PSScriptRoot 'test_scaffold.py')
if ($LASTEXITCODE -ne 0) { throw 'Offline checks failed' }
Write-Output 'Installed. Configure profile allowlist and model credentials before running server.py.'

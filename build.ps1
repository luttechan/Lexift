param([switch]$RebuildEngine, [switch]$Installer)
$ErrorActionPreference = 'Stop'
$savedPath = $env:PATH
$savedPythonPath = $env:PYTHONPATH
$savedUtf8 = $env:PYTHONUTF8
$workspace = Split-Path $PSScriptRoot -Parent
$runtime = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies'
Push-Location $PSScriptRoot
try {
    $bundledNode = Join-Path $runtime 'node\bin\node.exe'
    if (Test-Path -LiteralPath $bundledNode) {
        $env:PATH = (Split-Path $bundledNode -Parent) + ';' + (Join-Path $runtime 'bin\fallback') + ';' + $env:PATH
    }
    node -e "if(Number(process.versions.node.split('.')[0])<22)process.exit(1)"
    if ($LASTEXITCODE -ne 0) { throw 'Node.js 22.12 이상이 필요합니다.' }
    $python = Join-Path $workspace '.security-python\cpython-3.12.16-windows-x86_64-none\python.exe'
    if (!(Test-Path -LiteralPath $python)) { $python = 'python' }
    $env:PYTHONUTF8 = '1'
    if ($RebuildEngine) {
        $paths = @((Join-Path $PSScriptRoot 'engine\module'))
        foreach ($folder in @('.security-builddeps','.builddeps')) {
            $candidate = Join-Path $workspace $folder
            if (Test-Path -LiteralPath $candidate) { $paths += $candidate }
        }
        $env:PYTHONPATH = $paths -join ';'
        $zig = $env:KANASHIFT_ZIG
        if (!$zig) { $zig = (Get-Command zig -ErrorAction SilentlyContinue).Source }
        if (!(Test-Path 'engine\lab\ime_candidate_host.exe')) {
            if (!$zig) { throw 'Set KANASHIFT_ZIG to zig.exe (0.14.1).' }
            & .\engine\lab\build.ps1 -Zig $zig
        }
        foreach ($builder in @('build_native_hooks.py', 'build_keyboard_worker.py')) {
            & $python (Join-Path 'engine\module' $builder)
            if ($LASTEXITCODE -ne 0) { throw 'Native engine build failed' }
        }
        & $python scripts\prepare-engine.py
        if ($LASTEXITCODE -ne 0) { throw 'Engine specification failed' }
        & $python -m PyInstaller --noconfirm --distpath . --workpath engine-build engine\LexiftEngine.spec
        if ($LASTEXITCODE -ne 0) { throw 'Engine build failed' }
    }
    if (!(Test-Path -LiteralPath 'engine-dist\LexiftEngine.exe')) { throw '엔진 빌드가 필요합니다. -RebuildEngine 옵션을 사용하세요.' }
    & $python scripts\build_locales.py
    if ($LASTEXITCODE -ne 0) { throw 'Translation validation failed' }
    pnpm build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    & $python scripts\cargo.py build --release
    if ($LASTEXITCODE -ne 0) { throw 'Tauri build failed' }
    & $python scripts\package.py
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
    if ($Installer) {
        pnpm exec tauri bundle --bundles nsis
        if ($LASTEXITCODE -ne 0) { throw 'Windows installer build failed' }
    }
} finally {
    $env:PATH = $savedPath
    $env:PYTHONPATH = $savedPythonPath
    $env:PYTHONUTF8 = $savedUtf8
    Pop-Location
}

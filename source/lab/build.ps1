param([string]$Zig)
$ErrorActionPreference = 'Stop'
$labFolder = $PSScriptRoot
$experimentFolder = Split-Path -Parent $labFolder
$workspaceFolder = Split-Path -Parent $experimentFolder
if (-not $Zig) { $Zig = Join-Path $workspaceFolder 'zig-x86_64-windows-0.14.1\zig.exe' }
$env:ZIG_GLOBAL_CACHE_DIR = Join-Path $workspaceFolder 'zig-cache'
$env:ZIG_LOCAL_CACHE_DIR = Join-Path $labFolder 'build-cache'
& $Zig c++ (Join-Path $labFolder 'ime_candidate_host.cpp') -target x86_64-windows-gnu -mcpu=baseline -std=c++17 -O2 -municode '-Wl,--subsystem,windows' -lole32 -loleaut32 -loleacc -luuid -limm32 -luser32 -lgdi32 -lshell32 -o (Join-Path $labFolder 'ime_candidate_host.exe')
if ($LASTEXITCODE -ne 0) { throw 'IME host build failed' }
$lexiftNativeManifest=@{ target='x86_64-windows-gnu'; cpu='baseline'; binary_sha256=(Get-FileHash -LiteralPath (Join-Path $labFolder 'ime_candidate_host.exe') -Algorithm SHA256).Hash.ToLowerInvariant() }
$lexiftNativeManifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $labFolder 'ime_candidate_host_build.json') -Encoding utf8

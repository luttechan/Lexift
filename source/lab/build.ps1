param([string]$Zig)
$ErrorActionPreference = 'Stop'
$labFolder = $PSScriptRoot
$experimentFolder = Split-Path -Parent $labFolder
$workspaceFolder = Split-Path -Parent $experimentFolder
if (-not $Zig) { $Zig = Join-Path $workspaceFolder 'zig-x86_64-windows-0.14.1\zig.exe' }
$env:ZIG_GLOBAL_CACHE_DIR = Join-Path $workspaceFolder 'zig-cache'
$env:ZIG_LOCAL_CACHE_DIR = Join-Path $labFolder 'build-cache'
& $Zig c++ (Join-Path $labFolder 'ime_candidate_host.cpp') -std=c++17 -O2 -municode '-Wl,--subsystem,windows' -lole32 -loleaut32 -loleacc -luuid -limm32 -luser32 -lgdi32 -lshell32 -o (Join-Path $labFolder 'ime_candidate_host.exe')
if ($LASTEXITCODE -ne 0) { throw 'IME host build failed' }

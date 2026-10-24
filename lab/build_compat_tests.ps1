param([string]$Zig)
$ErrorActionPreference='Stop'
$labFolder=$PSScriptRoot
$workspaceFolder=Split-Path -Parent (Split-Path -Parent $labFolder)
if(-not $Zig) {$Zig=Join-Path $workspaceFolder 'zig-x86_64-windows-0.14.1\zig.exe'}
$env:ZIG_GLOBAL_CACHE_DIR=Join-Path $workspaceFolder 'zig-cache'
$env:ZIG_LOCAL_CACHE_DIR=Join-Path $labFolder 'build-cache'
foreach($name in @('native_edit_test','scintilla_test')) {
    & $Zig c++ (Join-Path $labFolder "$name.cpp") -std=c++17 -O2 -municode '-Wl,--subsystem,windows' -luser32 -lshell32 -o (Join-Path $labFolder "$name.exe")
    if($LASTEXITCODE -ne 0) {throw "Failed to build $name"}
}
& $Zig c++ (Join-Path $labFolder 'scintilla_test.cpp') -target x86-windows-gnu -std=c++17 -O2 -municode '-Wl,--subsystem,windows' -luser32 -lshell32 -o (Join-Path $labFolder 'scintilla_fixture32.exe')
if($LASTEXITCODE -ne 0) {throw 'Failed to build 32-bit Scintilla fixture'}

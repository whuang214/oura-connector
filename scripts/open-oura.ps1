param([string]$Config)
$ErrorActionPreference = 'Stop'
try {
    $repoRoot = Split-Path $PSScriptRoot -Parent
    $uvPath = (Get-Command uv.exe -ErrorAction Stop).Source
    $arguments = @('run', '--locked', '--directory', $repoRoot, 'oura-connector')
    if ($Config) { $arguments += @('--config', $Config) }
    $arguments += 'ui'
    & $uvPath @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Oura Connect exited with an error.' }
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show('Oura Connect could not start. Make sure uv is installed, then run uv sync --locked in the repository and try again. See docs/guides/troubleshooting.md for terminal diagnostics.', 'Oura Connect') | Out-Null
    exit 1
}

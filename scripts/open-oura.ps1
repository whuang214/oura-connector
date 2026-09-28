param([string]$Config)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$uvPath = (Get-Command uv.exe -ErrorAction Stop).Source
$arguments = @('run', '--locked', '--directory', $repoRoot, 'oura-connector')
if ($Config) { $arguments += @('--config', $Config) }
$arguments += 'ui'
& $uvPath @arguments
if ($LASTEXITCODE -ne 0) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show('Oura Connect could not start. Run uv sync --locked in the repository, then try again.', 'Oura Connect') | Out-Null
}

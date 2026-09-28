param([string]$Destination = [Environment]::GetFolderPath('DesktopDirectory'))
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$shellPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$scriptPath = Join-Path $PSScriptRoot 'open-oura.ps1'
$shortcutPath = Join-Path $Destination 'Oura Connect.lnk'
if (Test-Path -LiteralPath $shortcutPath) { throw 'Oura Connect shortcut already exists; choose another destination.' }
$shell = New-Object -ComObject WScript.Shell
try {
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $shellPath
    $shortcut.Arguments = '-NoProfile -WindowStyle Hidden -File "' + $scriptPath + '"'
    $shortcut.WorkingDirectory = $repoRoot
    $shortcut.Description = 'Connect Oura and save your sign-in locally'
    $shortcut.IconLocation = (Join-Path $env:SystemRoot 'System32\shell32.dll') + ',47'
    $shortcut.Save()
    Write-Output 'Created Oura Connect on your desktop.'
} finally { [Runtime.InteropServices.Marshal]::ReleaseComObject($shell) | Out-Null }

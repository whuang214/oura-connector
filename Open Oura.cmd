@echo off
rem Open the saved Oura connection from any working directory.
start "" "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -WindowStyle Hidden -File "%~dp0scripts\open-oura.ps1" %*

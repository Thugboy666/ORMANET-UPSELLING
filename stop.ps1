$ErrorActionPreference = "Stop"
$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = Join-Path $baseDir "runtime"
$pidFile = Join-Path $runtimeDir "app.pid"
$logDir = Join-Path $baseDir "logs"
$logFile = Join-Path $logDir "app.log"

function Write-StopLog($message) {
  $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $logFile -Value "$timestamp | INFO | $message"
}

if (Test-Path $pidFile) {
  $pid = Get-Content $pidFile | Select-Object -First 1
  if ($pid) {
    try {
      Stop-Process -Id $pid -Force
      Write-StopLog "Stop process PID $pid"
      Remove-Item $pidFile -Force
      exit 0
    } catch {
      Write-StopLog "Errore stop PID $pid: $($_.Exception.Message)"
    }
  }
}

$process = Get-Process | Where-Object { $_.Path -like "*app_gui.py" }
if ($process) {
  $process | Stop-Process -Force
  Write-StopLog "Stop process by name app_gui.py"
  exit 0
}

Write-StopLog "Nessun processo trovato"

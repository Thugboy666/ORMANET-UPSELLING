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
  $appPid = Get-Content $pidFile | Select-Object -First 1
  if ($appPid) {
    try {
      Stop-Process -Id $appPid -Force
      Write-StopLog "Stop process PID $appPid"
      Remove-Item $pidFile -Force
      exit 0
    } catch {
      Write-StopLog "Errore stop PID ${appPid}: $($_.Exception.Message)"
    }
  }
}

$process = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*-m app.server*" }
if ($process) {
  $process | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  Write-StopLog "Stop process by module app.server"
  exit 0
}

Write-StopLog "Nessun processo trovato"

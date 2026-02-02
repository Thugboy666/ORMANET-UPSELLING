$ErrorActionPreference = "Stop"
$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = Join-Path $baseDir "runtime"
$pythonExe = Join-Path $runtimeDir "python310\python.exe"
$logDir = Join-Path $baseDir "logs"
if (!(Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}
$stdoutLog = Join-Path $logDir "stdout.log"
$stderrLog = Join-Path $logDir "stderr.log"
$pidFile = Join-Path $runtimeDir "app.pid"
$scriptPath = Join-Path $baseDir "app\app_gui.py"

if (!(Test-Path $pythonExe)) {
  Write-Host "Python embedded non trovato in runtime/python310."
  exit 1
}

$process = Start-Process -FilePath $pythonExe -ArgumentList $scriptPath -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
$process.Id | Out-File -FilePath $pidFile -Encoding ascii
Write-Host "Avviato. PID: $($process.Id)"

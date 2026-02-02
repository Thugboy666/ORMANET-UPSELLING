$ErrorActionPreference = "Stop"
$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = Join-Path $baseDir "runtime"
$pythonExe = Join-Path $runtimeDir "python310\python.exe"
$logDir = Join-Path $baseDir "logs"
$outputDir = Join-Path $baseDir "output"
if (!(Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}
if (!(Test-Path $outputDir)) {
  New-Item -ItemType Directory -Path $outputDir | Out-Null
}
if (!(Test-Path $runtimeDir)) {
  New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}
$stdoutLog = Join-Path $logDir "stdout.log"
$stderrLog = Join-Path $logDir "stderr.log"
$pidFile = Join-Path $runtimeDir "app.pid"
$modulePath = "app.server"

if (!(Test-Path $pythonExe)) {
  Write-Host "Python embedded non trovato in runtime/python310."
  exit 1
}

$process = Start-Process -FilePath $pythonExe -ArgumentList "-m $modulePath" -WorkingDirectory $baseDir -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
$process.Id | Out-File -FilePath $pidFile -Encoding ascii
Write-Host "Avviato. PID: $($process.Id)"
Start-Sleep -Seconds 1
Start-Process "http://127.0.0.1:8765"

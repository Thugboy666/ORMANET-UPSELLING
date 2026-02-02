$ErrorActionPreference = "Stop"
$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $baseDir "logs"
$importDir = Join-Path $baseDir "import"
$outputDir = Join-Path $baseDir "output"
$reportPath = Join-Path $logDir "diagnose_report.json"
$bundlePath = Join-Path $logDir "diagnose_bundle.zip"
$errorSummaryPath = Join-Path $logDir "ERRORS_FOR_CHATGPT.txt"

if (!(Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

function Get-LastLines($path, $count) {
  if (!(Test-Path $path)) { return @() }
  return Get-Content $path -Tail $count
}

function Get-Tree($path, $depth) {
  if (!(Test-Path $path)) { return @() }
  return Get-ChildItem -Path $path -Recurse -Depth $depth | Select-Object FullName, Length
}

$report = [ordered]@{}
$report.timestamp = (Get-Date).ToString("o")
$report.system = [ordered]@{
  powershell = $PSVersionTable
  windows = (Get-CimInstance -ClassName Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber)
}
$report.python = [ordered]@{
  embeddedPath = Join-Path $baseDir "runtime\python310\python.exe"
}
$report.tree = Get-Tree -path $baseDir -depth 3
$report.logs = [ordered]@{
  appLogTail = Get-LastLines (Join-Path $logDir "app.log") 200
  stderrTail = Get-LastLines (Join-Path $logDir "stderr.log") 200
}
$report.counts = [ordered]@{
  importFiles = (Get-ChildItem -Path $importDir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
  outputFiles = (Get-ChildItem -Path $outputDir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
}

$report | ConvertTo-Json -Depth 5 | Out-File -FilePath $reportPath -Encoding utf8

$summary = @()
$summary += "Diagnose report generated: $reportPath"
$summary += "Import files: $($report.counts.importFiles)"
$summary += "Output files: $($report.counts.outputFiles)"
$summary += "--- app.log tail ---"
$summary += $report.logs.appLogTail
$summary += "--- stderr.log tail ---"
$summary += $report.logs.stderrTail
$summary | Out-File -FilePath $errorSummaryPath -Encoding utf8

$filesToZip = @(
  $reportPath,
  $errorSummaryPath,
  (Join-Path $logDir "app.log"),
  (Join-Path $logDir "stderr.log"),
  (Join-Path $logDir "stdout.log")
) | Where-Object { Test-Path $_ }

if (Test-Path $bundlePath) {
  Remove-Item $bundlePath -Force
}
Compress-Archive -Path $filesToZip -DestinationPath $bundlePath
Write-Host "Diagnose bundle created: $bundlePath"

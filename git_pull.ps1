$ErrorActionPreference = "Stop"
$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = Join-Path $baseDir "runtime"
$logDir = Join-Path $baseDir "logs"
if (!(Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}
$logOut = Join-Path $logDir "git_pull.log"
$logErr = Join-Path $logDir "git_pull.err.log"

$envPath = Join-Path $runtimeDir ".env"
if (Test-Path $envPath) {
  Get-Content $envPath | ForEach-Object {
    if ($_ -match "^") {
      $parts = $_.Split("=", 2)
      if ($parts.Length -eq 2) {
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($name) {
          [System.Environment]::SetEnvironmentVariable($name, $value)
        }
      }
    }
  }
}

$gitUser = $env:GIT_USER
$gitToken = $env:GIT_TOKEN
$repoUrl = $env:GIT_REPO
if (-not $repoUrl) {
  $repoUrl = "https://github.com/Thugboy666/ORMANET-UPSELLING"
}

if (-not (Test-Path (Join-Path $baseDir ".git"))) {
  git init *>> $logOut 2>> $logErr
  git remote add origin $repoUrl *>> $logOut 2>> $logErr
}

if ($gitUser -and $gitToken) {
  $authUrl = $repoUrl -replace "https://", "https://${gitUser}:${gitToken}@"
  git remote set-url origin $authUrl *>> $logOut 2>> $logErr
}

git pull origin main *>> $logOut 2>> $logErr

if ($gitUser -and $gitToken) {
  git remote set-url origin $repoUrl *>> $logOut 2>> $logErr
}

Write-Host "Git pull completed. Logs in $logOut"

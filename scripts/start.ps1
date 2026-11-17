$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Docker {
    param([string[]]$DockerArgs)
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed: docker $($DockerArgs -join ' ')" }
}

function Test-DockerReady {
    $ErrorActionPreference = 'Continue'
    & docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Install Docker Desktop with the Linux engine first.'
}
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}

if (-not (Test-DockerReady)) {
    $desktopPath = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path -LiteralPath $desktopPath)) { throw 'Docker Desktop was not found.' }
    Start-Process -FilePath $desktopPath -WindowStyle Hidden
    Write-Host 'Waiting for Docker Desktop Linux engine...'
    $deadline = (Get-Date).AddMinutes(3)
    do {
        Start-Sleep -Seconds 3
        $ready = Test-DockerReady
    } until ($ready -or (Get-Date) -ge $deadline)
    if (-not $ready) { throw 'Docker engine did not start. Check Docker Desktop startup errors.' }
}

Invoke-Docker -DockerArgs @('compose', 'up', '--build', '-d', '--wait', '--wait-timeout', '180')
Invoke-Docker -DockerArgs @('compose', 'exec', '-T', 'web', 'python', 'manage.py', 'seed_demo')
Invoke-Docker -DockerArgs @('compose', 'exec', '-T', 'web', 'python', 'manage.py', 'check')
Invoke-Docker -DockerArgs @('compose', 'ps', '-a')
foreach ($path in @('/health/live/', '/health/ready/', '/')) {
    $response = Invoke-WebRequest -Uri "http://localhost:8000$path" -UseBasicParsing -TimeoutSec 15
    if ($response.StatusCode -ne 200) { throw "HTTP check failed: $path" }
    Write-Host "OK: $path"
}
Write-Host 'TicketFlow ready: http://localhost:8000/'
Write-Host 'For an admin account: docker compose exec web python manage.py createsuperuser'

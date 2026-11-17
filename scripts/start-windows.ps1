$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$logDir = Join-Path $projectRoot '.tmp\windows-run'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

function Invoke-Python {
    param([string[]]$PythonArgs)
    & $python @PythonArgs
    if ($LASTEXITCODE -ne 0) { throw "Python command failed: $($PythonArgs -join ' ')" }
}

# Explicitly use the documented local SQLite/demo configuration.
Remove-Item Env:DB_HOST -ErrorAction SilentlyContinue
$env:DEBUG = '1'
$env:PAYMENT_URL = 'http://127.0.0.1:8001'
$env:PAYMENT_SECRET = 'local-simulator-only'
$env:ALLOWED_HOSTS = 'localhost,127.0.0.1'

foreach ($port in @(8000, 8001)) {
    $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $port)
    try { $listener.Start() }
    catch { throw "Port $port is occupied. Stop its service before starting TicketFlow." }
    finally { $listener.Stop() }
}
if (-not (Test-Path -LiteralPath $python)) {
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required to create .venv.' }
}
Invoke-Python -PythonArgs @('-m', 'ensurepip', '--upgrade')
Invoke-Python -PythonArgs @('-m', 'pip', 'install', '-r', 'requirements.txt')
Invoke-Python -PythonArgs @('manage.py', 'check')
Invoke-Python -PythonArgs @('manage.py', 'migrate', '--noinput')
Invoke-Python -PythonArgs @('manage.py', 'seed_demo')

$services = @(
    @{ Name = 'payment'; Args = @('manage.py', 'runserver', '127.0.0.1:8001', '--noreload', '--settings=payment_service.settings') },
    @{ Name = 'web'; Args = @('manage.py', 'runserver', '127.0.0.1:8000', '--noreload') },
    @{ Name = 'worker'; Args = @('manage.py', 'expire_bookings', '--loop') }
)
$started = @()
try {
    foreach ($service in $services) {
        $process = Start-Process -FilePath $python -ArgumentList $service.Args -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir "$($service.Name).out.log") -RedirectStandardError (Join-Path $logDir "$($service.Name).err.log")
        $started += $process
    }
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        foreach ($process in $started) {
            if ($process.HasExited) { throw "Service exited. See logs in $logDir" }
        }
        try {
            foreach ($url in @('http://127.0.0.1:8001/health/live/', 'http://127.0.0.1:8000/health/ready/', 'http://127.0.0.1:8000/')) {
                $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
                if ($response.StatusCode -ne 200) { throw "HTTP check failed: $url" }
            }
            $ready = $true
            break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ready) { throw "Services did not become healthy. See logs in $logDir" }
    Write-Host 'TicketFlow ready: http://localhost:8000/'
    Write-Host "Service PIDs: $($started.Id -join ', ')"
    Write-Host "Logs: $logDir"
    Write-Host 'Admin account: .\.venv\Scripts\python.exe manage.py createsuperuser'
    Write-Host "Stop these services: Stop-Process -Id $($started.Id -join ',')"
} catch {
    foreach ($process in $started) {
        if (-not $process.HasExited) { $process.Kill() }
    }
    throw
}

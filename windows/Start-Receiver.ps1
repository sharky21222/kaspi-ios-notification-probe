param([string]$Python = 'python', [switch]$Advertise)
$ErrorActionPreference = 'Stop'
$config = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1
if (-not $config) { throw 'No connected network with an IPv4 gateway. Specify the host manually with receiver.py.' }
$hostAddress = $config.IPv4Address.IPAddress | Select-Object -First 1
$arguments = @((Join-Path $PSScriptRoot 'receiver.py'), '--host', $hostAddress)
if ($Advertise) { $arguments += '--advertise' }
& $Python @arguments

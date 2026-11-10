$ErrorActionPreference='Stop'
$bin=Join-Path $PSScriptRoot 'bin'
$active=@(Get-Process paraview,paraview-core -ErrorAction SilentlyContinue | Where-Object {$_.Path -and $_.Path.StartsWith($bin+'\',[StringComparison]::OrdinalIgnoreCase)})
if($active.Count){throw 'Please close ParaView before restoring.'}
$core=Join-Path $bin 'paraview-core.exe'
if((Get-FileHash -LiteralPath $core -Algorithm SHA256).Hash -ne 'FD4ED46AF3089DAFE178FAE33843A758EED07E274863B15834AB4D0E6C4643D1'){throw 'Original executable checksum mismatch.'}
Copy-Item -LiteralPath $core -Destination (Join-Path $bin 'paraview.exe') -Force
Write-Output 'Original English entry point restored.'

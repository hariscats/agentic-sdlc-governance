$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "../..")
$payload = [Console]::In.ReadToEnd()
$payload | python -m governance.hooks $args[0]
exit $LASTEXITCODE

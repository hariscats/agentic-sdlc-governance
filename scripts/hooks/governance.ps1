$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $root
$payload = [Console]::In.ReadToEnd()
# Same isolation as governance.sh: -I -S, repository appended after the stdlib.
# TODO(verify): not yet exercised on Windows.
$payload | python -I -S -c "import sys; sys.path.append(sys.argv.pop(1)); from governance.hooks import main; main()" $root $args[0]
exit $LASTEXITCODE

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
& (Join-Path $root 'launch-lbe.ps1') @Arguments
exit $LASTEXITCODE

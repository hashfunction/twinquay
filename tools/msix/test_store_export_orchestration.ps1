# Copyright 2026 Trieflow LLC. MIT.
# Execute the actual package/install/export loop with only child process calls replaced.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'qualify-msix.ps1'),[ref]$tokens,[ref]$errors)
if ($errors.Count) {throw 'Production orchestration must parse.'}
$loop=@($ast.EndBlock.Statements | Where-Object {$_.Extent.Text.StartsWith('foreach ($identityMode')})
$export=@($ast.EndBlock.Statements | Where-Object {$_.Extent.Text.StartsWith('if ($ExportStore)')})
if ($loop.Count -ne 1 -or $export.Count -ne 1 -or $loop[0].Extent.EndOffset -ge $export[0].Extent.StartOffset) {throw 'Expected export after the exact dual lifecycle loop.'}
$body=[scriptblock]::Create($loop[0].Extent.Text+"`n"+$export[0].Extent.Text)
$previousLocation=Get-Location
$previousTemporary=$env:RUNNER_TEMP
$fixtureRoot=Join-Path ([IO.Path]::GetTempPath()) ('duplisift-export-order-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixtureRoot | Out-Null
try {
    foreach ($scenario in @('default','success','qualification-failure','store-failure','export-failure')) {
        $scenarioRoot=Join-Path $fixtureRoot $scenario
        New-Item -ItemType Directory -Path (Join-Path $scenarioRoot 'build-evidence') -Force | Out-Null
        Set-Location $scenarioRoot
        $env:RUNNER_TEMP=$scenarioRoot
        $ExportStore=$scenario -ne 'default'
        $qualifiedPackages=@{};$script:calls=[Collections.Generic.List[string]]::new()
        $python='python-fixture';$powerShell='powershell-fixture';$sourceCommit='a'*40;$sdkDirectory=$scenarioRoot;$sdkVersion='10.0.26100.0'
        function Invoke-Checked([string]$Program,[string[]]$Arguments) {
            if ($Arguments[0] -eq 'tools/msix/msix_qualification.py') {
                $mode=$Arguments[[Array]::IndexOf($Arguments,'--identity-mode')+1]
                $script:calls.Add('pack:'+ $mode)
                $output=$Arguments[[Array]::IndexOf($Arguments,'--output')+1]
                New-Item -ItemType Directory -Path $output | Out-Null
                [IO.File]::WriteAllText((Join-Path $output 'package-record.json'),$mode)
                $packageName=if($mode -eq 'store') {'DupliSift_1.0.1.0_x64.msix'}else{'DupliSift.Qualification_1.0.1.0_x64.msix'}
                [IO.File]::WriteAllText((Join-Path $output $packageName),$mode+' unsigned')
            } elseif ($Arguments -contains 'tools/msix/qualify-msix-install.ps1') {
                $mode=$Arguments[[Array]::IndexOf($Arguments,'-IdentityMode')+1]
                $script:calls.Add('install:'+ $mode)
                if ($scenario -eq ($mode+'-failure')) {throw 'fixture installed failure'}
            } elseif ($Arguments[0] -eq 'tools/msix/store_export.py') {
                $script:calls.Add('export')
                foreach ($mode in @('qualification','store')) {
                    $package=$Arguments[[Array]::IndexOf($Arguments,('--'+$mode+'-package'))+1]
                    if ($package -cne $qualifiedPackages[$mode] -or [IO.File]::ReadAllText($package) -cne ($mode+' unsigned')) {throw 'Export did not receive the exact qualified unsigned file.'}
                }
                if ($Arguments[[Array]::IndexOf($Arguments,'--output')+1] -cne 'build-evidence/store-upload') {throw 'Export output changed.'}
                if ($scenario -eq 'export-failure') {throw 'fixture export failure'}
            } else {throw 'Unexpected child process in release loop.'}
        }
        $failure=$null
        try {& $body} catch {$failure=$_.Exception.Message}
        $expected=switch($scenario) {
            'default' {'pack:qualification,install:qualification,pack:store,install:store'}
            'qualification-failure' {'pack:qualification,install:qualification'}
            'store-failure' {'pack:qualification,install:qualification,pack:store,install:store'}
            default {'pack:qualification,install:qualification,pack:store,install:store,export'}
        }
        if (($script:calls -join ',') -cne $expected) {throw "Incorrect exact production sequence: $scenario / $script:calls"}
        if (($scenario.EndsWith('-failure')) -ne [bool]$failure) {throw "Failure swallowed or success failed: $scenario / $failure"}
    }
} finally {
    Set-Location $previousLocation
    $env:RUNNER_TEMP=$previousTemporary
    Remove-Item -LiteralPath $fixtureRoot -Recurse -Force
}
Write-Output 'PASS: five actual dual-identity/export sequences; exact unsigned paths, default no export, and every failure terminates.'

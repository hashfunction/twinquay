# Copyright 2026 Trieflow LLC. MIT. Actual loader/closure host regression; no process guard stub.
param([switch]$Probe,[string]$QualifiedSource,[string]$ProbeOutput,[ValidateSet('owned-refusal','missing-command')][string]$Expected='owned-refusal')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function Check($Value,[string]$Message) {if(-not $Value){throw $Message}}
if ($Probe) {
    # Same production loader and order as the real capture entrypoint.
    . (Join-Path $PSScriptRoot 'capture_library.ps1') -QualifiedSource $QualifiedSource
    $guard=Get-Command Assert-TwinQuayWorkflowProcess -CommandType Function
    Check (([IO.Path]::GetFullPath($guard.ScriptBlock.File)) -ceq ([IO.Path]::GetFullPath((Join-Path $QualifiedSource 'tools/msix/qualify-workflow.ps1')))) 'Process guard did not come from actual qualified source.'
    # Assembly availability is the only platform substitution. The original
    # guard, workflow operations, core, diagnostics and closure remain intact.
    if (-not $IsWindows) {function Add-Type {param($AssemblyName)}}
    $absent=Join-Path ([IO.Path]::GetTempPath()) ('duplisift-loader-uncreated-'+[guid]::NewGuid().ToString('N'))
    Check (-not (Test-Path -LiteralPath $absent)) 'Probe path must not exist.'
    $state=@{processOwned=$false;processHandle=$null;process=[pscustomobject]@{Id=42};record=@{sourceCommit='loader-fixture'};
        ownedPackageFullName='unowned-fixture';executableSha256='fixture';workflow=$null;qualified=$QualifiedSource;
        output=$absent;temporary='retained-signing-directory';demo=@{root=$absent}}
    $failure=$null
    try {Invoke-DupliCaptureWorkflow $state 'never-called-python'}catch{$failure=$_.Exception.Message}
    Check ([bool]$failure -and $null -ne $state.workflow) 'Original workflow did not retain its refusal.'
    $result=$state.workflow.result
    Check (-not $result.passed -and $result.completed_stages.Count -eq 0 -and $result.failed_stage -ceq 'Prepare' -and $result.cleanup_errors.Count -eq 0) 'Unowned probe unexpectedly progressed.'
    Check (-not (Test-Path -LiteralPath $absent) -and $state.temporary -ceq 'retained-signing-directory' -and $null -eq $script:DupliCapturePython) 'Refusal mutated fixtures or lost signing-directory restoration.'
    if ($Expected -eq 'owned-refusal') {
        Check ($result.primary_error -ceq 'The original owned installed process is no longer live.' -and
            $result.primary_error_record.script_stack_trace -match 'at Assert-TwinQuayWorkflowProcess,') 'Fresh host failed to execute the unchanged process guard.'
        # The other unchanged workflow dependencies must be visible from a real
        # closure too, not merely present in the enclosing script scope.
        $dependencies=@('Assert-TwinQuayWorkflowProcess','New-TwinQuayCollision','Wait-TwinQuayWorkflowWindow',
            'Send-TwinQuayWorkflowKeys','Press-TwinQuayWorkflowButton','Wait-TwinQuayWorkflowCompletion',
            'Invoke-TwinQuayWorkflowRestore','Get-CanonicalPath','Assert-FileMatchesRecord',
            'Save-TwinQuayWorkflowSurface','Invoke-TwinQuayFileOracle','Set-DupliCaptureWindow','Save-DupliCaptureFrame')
        $resolved=& {foreach($name in $dependencies){(Get-Command $name -CommandType Function -ErrorAction Stop).Name}}.GetNewClosure()
        Check (($resolved -join ',') -ceq ($dependencies -join ',')) 'A required original/capture function is absent from the actual closure scope.'
    } else {
        Check ($result.primary_error_record.fully_qualified_error_id -ceq 'CommandNotFoundException' -and
            $result.primary_error -match "Assert-TwinQuayWorkflowProcess.*not recognized") 'Nested host did not reproduce the actual native scope failure.'
    }
    Write-NewUtf8Json $ProbeOutput @{expected=$Expected;result=$result;original_guard_source=$guard.ScriptBlock.File;fixture_created=$false}
    return
}
$qualified=if($QualifiedSource){(Resolve-Path -LiteralPath $QualifiedSource).Path}else{(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path}
$pwsh=(Get-Process -Id $PID).Path
$probeRoot=Join-Path ([IO.Path]::GetTempPath()) ('duplisift-loader-test-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $probeRoot | Out-Null
try {
    # Actions runs a generated top-level script. Its previous './capture.ps1'
    # invocation adds exactly this nested scope; fresh '-File' does not.
    $wrapper=Join-Path $probeRoot 'nested-action.ps1'
    [IO.File]::WriteAllText($wrapper,'& $args[0] -Probe -QualifiedSource $args[1] -ProbeOutput $args[2] -Expected missing-command')
    & $pwsh -NoProfile -File $wrapper $PSCommandPath $qualified (Join-Path $probeRoot 'nested.json')
    Check ($LASTEXITCODE -eq 0) 'Actual nested loader regression failed.'
    & $pwsh -NoProfile -File $PSCommandPath -Probe -QualifiedSource $qualified -ProbeOutput (Join-Path $probeRoot 'fresh.json')
    Check ($LASTEXITCODE -eq 0) 'Actual fresh loader regression failed.'
    $workflow=Get-Content -LiteralPath (Join-Path $PSScriptRoot '../../.github/workflows/marketing-screenshots.yml') -Raw
    Check ($workflow.Contains('& $pwsh -NoProfile -File ./tools/marketing/capture.ps1') -and
        $workflow.Contains("if (`$LASTEXITCODE -ne 0) { throw 'Native capture host failed.' }")) 'Production workflow must use the checked fresh process host demonstrated above.'
} finally {Remove-Item -LiteralPath $probeRoot -Recurse -Force}
Write-Output 'PASS: exact production loader, original guard/core/Prepare, nested-host native failure reproduction, fresh-host refusal and closure dependency availability, no fixture mutation.'

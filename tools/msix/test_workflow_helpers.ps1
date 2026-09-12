# Copyright 2026 Trieflow LLC. MIT. Local helper tests are not installed UI acceptance.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
. (Join-Path $PSScriptRoot 'qualify-workflow.ps1')
function Assert($Value,[string]$Message) { if (-not $Value) { throw $Message } }
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class TwinQuayTransientUiaFixture {
    public static void FindAll(int hresult) {
        throw new COMException("Unrecognized error.", hresult);
    }
}
'@
$literal='C:\fixture +{x}(y)[z]^%~\keep.bin'
Assert ((ConvertTo-TwinQuaySendKeysLiteral $literal) -ceq 'C:\fixture {+}{{}x{}}{(}y{)}{[}z{]}{^}{%}{~}\keep.bin') 'Literal path keyboard escaping changed.'
$one=[pscustomobject]@{name='Scan';control_type='ControlType.Button';enabled=$true;offscreen=$false;process_id=42}
Assert ((Select-TwinQuayWorkflowControl @($one) 42 'Scan' @('ControlType.Button')).name -ceq 'Scan') 'Exact source control selection failed.'
foreach ($bad in @(@($one,$one),@($one | Select-Object * -ExcludeProperty process_id | Select-Object *,@{n='process_id';e={43}}),@())) {
    $failure=$null
    try { Select-TwinQuayWorkflowControl $bad 42 'Scan' @('ControlType.Button') | Out-Null } catch { $failure=$_.Exception.Message }
    Assert ([bool]$failure) 'Ambiguous/missing/foreign control passed.'
}
# Real window polling with observed-enumeration adapters: a scan progress
# window temporarily shares the main title on Windows (run34642776050).
$originalWindows=${function:Get-TwinQuayWorkflowWindows}
$script:polls=0;$script:windowMode='transient'
$script:mainWindow=[pscustomobject]@{Current=[pscustomobject]@{Name='DupliSift'}}
$script:progressWindow=[pscustomobject]@{Current=[pscustomobject]@{Name='DupliSift'}}
function Get-TwinQuayWorkflowWindows($State) {
    $script:polls++
    if($script:windowMode -eq 'transient-uia' -and $script:polls -eq 1){[TwinQuayTransientUiaFixture]::FindAll(-2147220991)}
    if($script:windowMode -eq 'other-uia'){[TwinQuayTransientUiaFixture]::FindAll(-2147220988)}
    if($script:windowMode -eq 'error'){return [pscustomobject]@{Current=[pscustomobject]@{Name='Error loading input'}}}
    if($script:windowMode -eq 'absent'){return @()}
    if($script:windowMode -eq 'persistent' -or $script:polls -eq 1){return @($script:mainWindow,$script:progressWindow)}
    return @($script:mainWindow)
}
try {
    $found=Wait-TwinQuayWorkflowWindow @{} 'DupliSift' 2
    Assert ($script:polls -eq 2 -and [object]::ReferenceEquals($found,$script:mainWindow)) 'Transient scan window was selected or rejected instead of awaited.'
    $script:windowMode='transient-uia';$script:polls=0
    $found=Wait-TwinQuayWorkflowWindow @{} 'DupliSift' 2
    Assert ($script:polls -eq 2 -and [object]::ReferenceEquals($found,$script:mainWindow)) 'UIA_E_ELEMENTNOTAVAILABLE was not retried within the owned bounded wait.'
    $script:windowMode='other-uia';$script:polls=0;$failure=$null
    try{Wait-TwinQuayWorkflowWindow @{} 'DupliSift' 2|Out-Null}catch{$failure=$_.Exception.Message}
    Assert ($failure -match 'Unrecognized error' -and $script:polls -eq 1) 'A different UI Automation HRESULT was retried or concealed.'
    foreach($script:windowMode in @('persistent','absent','error')){
        $script:polls=0;$failure=$null
        try{Wait-TwinQuayWorkflowWindow @{} 'DupliSift' 0|Out-Null}catch{$failure=$_.Exception.Message}
        $expected=@{persistent='Ambiguous';absent='Timed out';error='Owned application error'}[$script:windowMode]
        Assert ($failure -match $expected -and $script:polls -eq 1) "Window polling accepted or misreported $script:windowMode"
    }
} finally {Set-Item Function:Get-TwinQuayWorkflowWindows $originalWindows}
Write-Output 'PASS: bounded wait tolerates transient same-title scan progress and UIA_E_ELEMENTNOTAVAILABLE only, never chooses an ambiguous window and preserves other failures.'
$originalWait=${function:Wait-TwinQuayWorkflowWindow}
$originalElements=${function:Get-TwinQuayWorkflowElements}
$script:scanPolls=0
$script:scanWindow=[pscustomobject]@{Current=[pscustomobject]@{Name='DupliSift'}}
$script:scanElement=[pscustomobject]@{identity='exact rendered row'}
function Wait-TwinQuayWorkflowWindow($State,[string]$Title,[int]$Seconds=30) { return $script:scanWindow }
function Get-TwinQuayWorkflowElements($Root) {
    $script:scanPolls++
    if($script:scanPolls -eq 1){[TwinQuayTransientUiaFixture]::FindAll(-2147220991)}
    return [pscustomobject]@{name='Cedar House Brief.txt';process_id=42;offscreen=$false;element=$script:scanElement}
}
try {
    $scan=Wait-TwinQuayWorkflowScanResult @{process=[pscustomobject]@{Id=42}} 2
    Assert ($script:scanPolls -eq 2 -and [object]::ReferenceEquals($scan.window,$script:scanWindow) -and
        [object]::ReferenceEquals($scan.reference,$script:scanElement)) 'Transient scan-result tree was not reacquired exactly.'
} finally {
    Set-Item Function:Wait-TwinQuayWorkflowWindow $originalWait
    Set-Item Function:Get-TwinQuayWorkflowElements $originalElements
}
Write-Output 'PASS: actual scan-result polling reacquires the owned window after UIA_E_ELEMENTNOTAVAILABLE.'
foreach ($failureStage in @('', 'Scan', 'Review', 'Quarantine', 'Conflict', 'Restore')) {
    $calls=[Collections.Generic.List[string]]::new()
    $operations=[ordered]@{}
    foreach ($name in @('Prepare','Scan','Review','Quarantine','Conflict','Restore','Finish','ReleaseCollision')) {
        $stage=$name
        $operations[$name]={ $calls.Add($stage); if ($failureStage -ceq $stage) { throw "primary $stage" } }.GetNewClosure()
    }
    $result=Invoke-TwinQuayWorkflowCore $operations
    Assert ($calls[$calls.Count-1] -ceq 'ReleaseCollision') 'Owned collision handle was not released.'
    Assert ($result.passed -eq (-not $failureStage)) 'Incomplete workflow passed or complete flow failed.'
    if ($failureStage) {
        Assert ($result.primary_error -ceq "primary $failureStage") 'Primary operation error lost.'
        Assert ($result.failed_stage -ceq $failureStage) 'The exact failing workflow stage was not retained.'
        Assert ($result.primary_error_record.script_stack_trace -match [regex]::Escape('test_workflow_helpers.ps1')) 'Primary script stack was not retained.'
        Assert ($result.primary_error_record.invocation.script_name -match [regex]::Escape('test_workflow_helpers.ps1')) 'Primary invocation source was not retained.'
        Assert ($result.primary_error_record.invocation.script_line_number -gt 0 -and $result.primary_error_record.invocation.offset_in_line -gt 0) 'Primary invocation position was not retained.'
    } else {
        Assert ($null -eq $result.failed_stage -and $null -eq $result.primary_error_record) 'Successful workflow manufactured failure diagnostics.'
    }
}
$operations.Restore={throw 'primary restore'}
$operations.ReleaseCollision={throw 'separate cleanup'}
$result=Invoke-TwinQuayWorkflowCore $operations
Assert (-not $result.passed -and $result.primary_error -ceq 'primary restore' -and $result.cleanup_errors[0] -ceq 'separate cleanup') 'Primary/cleanup failures were not retained separately.'
$diagnosticOperations=[ordered]@{}
foreach ($name in @('Prepare','Scan','Review','Quarantine','Conflict','Restore','Finish','ReleaseCollision')) {
    $operationName=$name
    $diagnosticOperations[$name]={
        if($operationName -ceq 'Scan'){[TwinQuayTransientUiaFixture]::FindAll(-2147220991)}
    }.GetNewClosure()
}
$diagnostic=Invoke-TwinQuayWorkflowCore $diagnosticOperations
Assert ($diagnostic.primary_error -ceq 'Exception calling "FindAll" with "1" argument(s): "Unrecognized error."') 'Primary failure text changed while recording diagnostics.'
Assert ($diagnostic.primary_exception_chain.Count -eq 2) 'Wrapped primary exception chain was not retained exactly.'
Assert ($diagnostic.primary_exception_chain[0].type -ceq 'System.Management.Automation.MethodInvocationException' -and
    $diagnostic.primary_exception_chain[1].type -ceq 'System.Runtime.InteropServices.COMException') 'Primary exception types were not retained in order.'
Assert ($diagnostic.primary_exception_chain[1].hresult -eq -2147220991 -and
    $diagnostic.primary_exception_chain[1].hresult_hex -ceq '0x80040201') 'Primary inner HRESULT was not retained exactly.'
Assert ($diagnostic.failed_stage -ceq 'Scan' -and $diagnostic.primary_error_record.fully_qualified_error_id) 'Primary stage/error-record identity was not retained.'
Assert ($diagnostic.primary_error_record.script_stack_trace.Length -le 8192 -and
    $diagnostic.primary_error_record.invocation.line.Length -le 4096 -and
    $diagnostic.primary_error_record.invocation.position_message.Length -le 4096) 'Primary source diagnostics exceeded their evidence bounds.'
$diagnosticJson=$diagnostic | ConvertTo-Json -Depth 10 | ConvertFrom-Json
Assert ($diagnosticJson.primary_exception_chain.Count -eq 2 -and
    $diagnosticJson.primary_exception_chain[1].hresult_hex -ceq '0x80040201' -and
    $diagnosticJson.failed_stage -ceq 'Scan' -and $diagnosticJson.primary_error_record.script_stack_trace) 'Serialized workflow metadata lost the exception source evidence.'
$geometry=Get-TwinQuayWorkflowSurfaceGeometry `
    ([pscustomobject]@{Left=-1920;Top=40;Right=-800;Bottom=630;Width=1120;Height=590}) `
    ([pscustomobject]@{Left=-1920;Top=0;Right=1920;Bottom=1080;Width=3840;Height=1080})
Assert ($geometry.fully_visible -and
    $geometry.uia_bounds.left -eq -1920 -and $geometry.uia_bounds.top -eq 40 -and
    $geometry.uia_bounds.right -eq -800 -and $geometry.uia_bounds.bottom -eq 630 -and
    $geometry.uia_bounds.width -eq 1120 -and $geometry.uia_bounds.height -eq 590 -and
    $geometry.virtual_screen.left -eq -1920 -and $geometry.virtual_screen.top -eq 0 -and
    $geometry.virtual_screen.right -eq 1920 -and $geometry.virtual_screen.bottom -eq 1080 -and
    $geometry.virtual_screen.width -eq 3840 -and $geometry.virtual_screen.height -eq 1080) 'Exact valid surface/virtual-screen geometry was not retained.'
$clipped=Get-TwinQuayWorkflowSurfaceGeometry `
    ([pscustomobject]@{Left=900;Top=40;Right=2020;Bottom=630;Width=1120;Height=590}) `
    ([pscustomobject]@{Left=0;Top=0;Right=1920;Bottom=1080;Width=1920;Height=1080})
Assert (-not $clipped.fully_visible -and $clipped.uia_bounds.right -eq 2020 -and $clipped.virtual_screen.right -eq 1920) 'Partially offscreen surface passed or lost the decisive bounds.'
$undersized=Get-TwinQuayWorkflowSurfaceGeometry `
    ([pscustomobject]@{Left=10;Top=10;Right=159;Bottom=89;Width=149;Height=79}) `
    ([pscustomobject]@{Left=0;Top=0;Right=1920;Bottom=1080;Width=1920;Height=1080})
Assert (-not $undersized.fully_visible) 'Existing minimum usable-surface gate was weakened.'
$handleFailure=$null
try { ConvertTo-TwinQuayWorkflowHandle $null 'input-root' | Out-Null } catch { $handleFailure=$_.Exception.Message }
Assert ($handleFailure -ceq 'Native window handle is null at input-root (value type: null).') 'Null native-handle evidence did not identify its exact consumer site.'
Assert ((ConvertTo-TwinQuayWorkflowHandle 42 'surface-root').ToInt64() -eq 42) 'Valid native handle did not retain its exact value.'
$syntheticError=[Management.Automation.ErrorRecord]::new([InvalidOperationException]::new('synthetic'),
    'SyntheticDiagnostic',[Management.Automation.ErrorCategory]::InvalidOperation,$null)
$syntheticEvidence=Get-TwinQuayErrorRecordEvidence $syntheticError
Assert ($syntheticEvidence.fully_qualified_error_id -ceq 'SyntheticDiagnostic' -and
    $null -eq $syntheticEvidence.invocation.script_name -and $syntheticEvidence.invocation.script_line_number -eq 0) 'Missing invocation metadata displaced the retained primary error evidence.'
$temp=Join-Path ([IO.Path]::GetTempPath()) ('twin-workflow-handle-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    $path=Join-Path $temp 'collision.bin'
    $stream=New-TwinQuayCollision $path ([byte[]](1,2,3))
    Assert (Test-Path -LiteralPath $path) 'Actual collision file was not created.'
    $failed=$false
    try { New-TwinQuayCollision $path ([byte[]](4)) | Out-Null } catch { $failed=$true }
    Assert $failed 'Collision creation replaced an existing file.'
    if ($IsWindows) {
        $failed=$false
        try { [IO.File]::Delete($path) } catch { $failed=$true }
        Assert $failed 'Retained Windows handle allowed deletion by another actor.'
    }
    $python=if ($IsWindows) { Join-Path $PSScriptRoot '../../.venv/Scripts/python.exe' } else { Join-Path $PSScriptRoot '../../env-qt6/bin/python' }
    & $python -c 'import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from workflow_files import read; assert read(Path(sys.argv[2]).resolve())[0] == bytes((1,2,3))' $PSScriptRoot $path
    Assert ($LASTEXITCODE -eq 0) 'Independent actual reader could not read the held collision with the required sharing.'
    $stream.Dispose()
    Assert (-not (Test-Path -LiteralPath $path)) 'DeleteOnClose did not remove the exact owned file.'
    [IO.File]::WriteAllText($path,'preexisting')
    $failed=$false
    try { New-TwinQuayCollision $path ([byte[]](4)) | Out-Null } catch { $failed=$true }
    Assert ($failed -and [IO.File]::ReadAllText($path) -ceq 'preexisting') 'Failed ownership acquisition changed preexisting bytes.'
    $record=Join-Path $temp 'workflow.json'
    [IO.File]::WriteAllText($record,'preserve')
    $failed=$null
    try { Write-TwinQuayWorkflowResult $record $result } catch { $failed=$_.Exception.Message }
    Assert ($failed -match 'primary restore' -and $failed -match 'separate cleanup' -and $failed -match 'reporting' -and [IO.File]::ReadAllText($record) -ceq 'preserve') 'Exclusive reporting lost errors or replaced bytes.'
} finally { if ($stream) { $stream.Dispose() }; Remove-Item -LiteralPath $temp -Recurse -Force }
Write-Output 'PASS: exact selectors, literal input, seven orchestration cases, actual collision handle and exclusive reporting.'

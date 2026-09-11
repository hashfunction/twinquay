# Copyright 2026 Trieflow LLC. MIT. Local helper tests are not installed UI acceptance.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
. (Join-Path $PSScriptRoot 'qualify-workflow.ps1')
function Assert($Value,[string]$Message) { if (-not $Value) { throw $Message } }
$literal='C:\fixture +{x}(y)[z]^%~\keep.bin'
Assert ((ConvertTo-TwinQuaySendKeysLiteral $literal) -ceq 'C:\fixture {+}{{}x{}}{(}y{)}{[}z{]}{^}{%}{~}\keep.bin') 'Literal path keyboard escaping changed.'
$one=[pscustomobject]@{name='Scan';control_type='ControlType.Button';enabled=$true;offscreen=$false;process_id=42}
Assert ((Select-TwinQuayWorkflowControl @($one) 42 'Scan' @('ControlType.Button')).name -ceq 'Scan') 'Exact source control selection failed.'
foreach ($bad in @(@($one,$one),@($one | Select-Object * -ExcludeProperty process_id | Select-Object *,@{n='process_id';e={43}}),@())) {
    $failure=$null
    try { Select-TwinQuayWorkflowControl $bad 42 'Scan' @('ControlType.Button') | Out-Null } catch { $failure=$_.Exception.Message }
    Assert ([bool]$failure) 'Ambiguous/missing/foreign control passed.'
}
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
    if ($failureStage) { Assert ($result.primary_error -ceq "primary $failureStage") 'Primary operation error lost.' }
}
$operations.Restore={throw 'primary restore'}
$operations.ReleaseCollision={throw 'separate cleanup'}
$result=Invoke-TwinQuayWorkflowCore $operations
Assert (-not $result.passed -and $result.primary_error -ceq 'primary restore' -and $result.cleanup_errors[0] -ceq 'separate cleanup') 'Primary/cleanup failures were not retained separately.'
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

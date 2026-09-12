# Copyright 2026 Trieflow LLC. MIT. Production adapter replay; not Windows UI acceptance.
param([Parameter(Mandatory)][string]$Python)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '../msix/qualify-msix-install.ps1') -LibraryOnly
. (Join-Path $PSScriptRoot 'capture_helpers.ps1')
function Check($Value,[string]$Message) {if(-not $Value){throw $Message}}
$script:events=[Collections.Generic.List[string]]::new();$script:surfaceFailure=$false
function Save-TwinQuayWorkflowSurface($State,$Context,[string]$Name,$Root) {
    $script:events.Add('original:'+ $Name);if($script:surfaceFailure){throw 'original owned capture failed'}
}
. (Join-Path $PSScriptRoot 'capture_adapter.ps1')
function Set-DupliCaptureWindow($State,$Handle,$Title) {$script:events.Add('resize:'+ $Title)}
function Save-DupliCaptureFrame($State,$Root,$Name) {$script:events.Add('frame:'+ $Name)}
$root=[pscustomobject]@{Current=[pscustomobject]@{NativeWindowHandle=123;Name='Review Cleanup Plan — DupliSift'}}
Save-TwinQuayWorkflowSurface @{} @{} '03-reviewed-plan' $root
Check (($script:events -join '|') -ceq 'resize:Review Cleanup Plan — DupliSift|original:03-reviewed-plan|frame:02-review-quarantine-plan') 'Original surface must pass before additional marketing image.'
$script:events.Clear();$script:surfaceFailure=$true;$failed=$false
try {Save-TwinQuayWorkflowSurface @{} @{} '03-reviewed-plan' $root}catch{$failed=$true}
Check ($failed -and $script:events.Count -eq 2) 'Original refusal was swallowed or reached additional screenshot.'
$script:events.Clear();$script:surfaceFailure=$false
Save-TwinQuayWorkflowSurface @{} @{} '06-conflict-disclosed' $root
Check (($script:events -join '|') -ceq 'original:06-conflict-disclosed') 'Nonmarketing conflict proof was changed.'
# Real Windows observation: Qt's inactive restored checkbox is an enabled UIA
# DataItem. Test the recorded provider value, not the model flag assumption.
$observed=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'fixtures/34685566093-restored-observation.json') -Raw|ConvertFrom-Json
$cells=@($observed.controls|Where-Object control_type -CEQ 'ControlType.DataItem')
Check ($cells.Count -eq 5) 'Native restored row fixture differs.'
$nativeSnapshot=@{process_id=$observed.process_id;rows=1;columns=5;path_pid=$cells[1].process_id;status_pid=$cells[3].process_id;
    checkbox_pid=$cells[0].process_id;original_path=$cells[1].name;status=$cells[3].name;checkbox_enabled=$cells[0].enabled;
    path_offscreen=$cells[1].offscreen;status_offscreen=$cells[3].offscreen;table_type='ControlType.Table';
    path_type=$cells[1].control_type;status_type=$cells[3].control_type;checkbox_type=$cells[0].control_type;observation_error=$null}
Assert-DupliRestoredTable $nativeSnapshot $observed.process_id $cells[1].name
$base=@{process_id=42;rows=1;columns=5;path_pid=42;status_pid=42;checkbox_pid=42;original_path='C:\Demo\Cedar House Review\Project Documents\Cedar House Brief - emailed.txt';status='restored';checkbox_enabled=$true;path_offscreen=$false;status_offscreen=$false;table_type='ControlType.Table';path_type='ControlType.DataItem';status_type='ControlType.DataItem';checkbox_type='ControlType.DataItem';observation_error=$null}
Assert-DupliRestoredTable $base 42 $base.original_path
foreach ($key in @('process_id','rows','columns','path_pid','status_pid','checkbox_pid','original_path','status','checkbox_enabled','path_offscreen','status_offscreen','table_type','path_type','status_type','checkbox_type','observation_error')) {
    $copy=@{};foreach($name in $base.Keys){$copy[$name]=$base[$name]}
    $copy[$key]=if($key -eq 'checkbox_enabled'){$false}elseif($key -in @('path_offscreen','status_offscreen')){$true}elseif($key -in @('original_path','status','table_type','path_type','status_type','checkbox_type','observation_error')){'foreign'}else{99}
    $failed=$false;try{Assert-DupliRestoredTable $copy 42 $base.original_path}catch{$failed=$true};Check $failed "Changed restored row accepted: $key"
}
# Call the actual original workflow entrypoint and Prepare closure. Suppress only
# its platform assembly loads and UI operations; the unchanged real oracle writes
# and hashes the actual Cedar House fixture. Inject a deliberate native-stage
# failure and prove signed-temp restoration and retained original error.
$probe=Join-Path ([IO.Path]::GetTempPath()) ('duplisift-adapter-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $probe | Out-Null
try {
    $demo=New-DupliCaptureDirectory (Join-Path $probe 'Demo')
    $state=@{temporary='owned-signing-temp';demo=$demo;output=(Join-Path $probe 'output');qualified=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path;
        process=[pscustomobject]@{Id=42};record=[pscustomobject]@{sourceCommit='fixture'};ownedPackageFullName='owned-package';executableSha256='fixture';workflow=$null}
    New-Item -ItemType Directory -Path $state.output | Out-Null
    function Add-Type {param($AssemblyName)}
    function Assert-TwinQuayWorkflowProcess($State) {Check ($State.process.Id -eq 42) 'Foreign process in actual Prepare closure.'}
    function Get-TwinQuayWorkflowWindows($State) {return @()}
    function Invoke-TwinQuayWorkflowCore($Operations) {
        Check (($Operations.Keys -join ',') -ceq 'Prepare,Scan,Review,Quarantine,Conflict,Restore,Finish,ReleaseCollision') 'Existing workflow operations differ.'
        & $Operations.Prepare | Out-Null
        return [pscustomobject]@{passed=$false;completed_stages=@('Prepare');failed_stage='Scan';primary_error='native fixture refusal';cleanup_errors=@()}
    }
    $failed=$false;try{Invoke-DupliCaptureWorkflow $state $Python}catch{$failed=$_.Exception.Message -match 'native fixture refusal'}
    Check ($failed -and $state.temporary -ceq 'owned-signing-temp' -and $null -eq $script:DupliCapturePython) 'Original workflow failure or signing directory restoration lost.'
    Check ($state.workflow.files.prepare.root -ceq (Join-Path $demo.root 'Cedar House Review')) 'Short original demo fixture parent differs.'
    Check ($state.workflow.files.prepare.files.Count -eq 3 -and $state.workflow.files.prepare.collision.bytes -eq 66) 'Actual byte oracle was not executed.'
    $ownerPath=$demo.root
    $failed=$false;try{$null=New-DupliCaptureDirectory $ownerPath}catch{$failed=$true};Check $failed 'Preexisting demo accepted.'
    $marker=Join-Path $ownerPath '.duplisift-marketing-owner'
    [IO.File]::WriteAllText($marker,'foreign');$failed=$false
    try{$null=Remove-DupliCaptureDirectory $demo}catch{$failed=$true}
    Check ($failed -and (Test-Path -LiteralPath $ownerPath)) 'Foreign marker was removed.'
    [IO.File]::WriteAllText($marker,$demo.marker)
    Check (Remove-DupliCaptureDirectory $demo) 'Owned actual demo cleanup failed.'
} finally {Remove-Item -LiteralPath $probe -Recurse -Force}
Write-Output 'PASS: original surface-before-frame, capture refusal, untouched conflict proof, restored row refusals, actual original Prepare/oracle closure and failure restoration, exclusive marker provenance.'

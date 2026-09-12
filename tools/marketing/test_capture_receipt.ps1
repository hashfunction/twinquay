# Copyright 2026 Trieflow LLC. MIT. Production observation/dismissal replay, not Windows UI acceptance.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'capture_library.ps1') -QualifiedSource (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
function Check($Value,[string]$Message) {if(-not $Value){throw $Message}}
$record=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'fixtures/34685566093-restored-observation.json') -Raw|ConvertFrom-Json
$cells=@($record.controls|Where-Object control_type -CEQ 'ControlType.DataItem')
$table=@($record.controls|Where-Object control_type -CEQ 'ControlType.Table')[0]
$nativeCells=@(foreach($cell in $cells){[pscustomobject]@{Current=[pscustomobject]@{
    ProcessId=$cell.process_id;Name=$cell.name;IsEnabled=$cell.enabled;IsOffscreen=$cell.offscreen;
    ControlType=[pscustomobject]@{ProgrammaticName=$cell.control_type}}}})
$grid=[pscustomobject]@{Current=[pscustomobject]@{RowCount=1;ColumnCount=5};Items=$nativeCells}
$grid|Add-Member ScriptMethod GetItem {param($Row,$Column) if($Row -ne 0){throw 'Unexpected row'};return $this.Items[$Column]}
$snapshot=Get-DupliRestoredTableSnapshot $grid $table
Assert-DupliRestoredTable $snapshot $record.process_id $cells[1].name
Check ($snapshot.checkbox_enabled -eq $true -and $snapshot.checkbox_type -ceq 'ControlType.DataItem') 'Actual Windows provider value was not retained.'
# These are the two observed Close buttons. Neither is selected heuristically.
Check (@($record.controls|Where-Object {$_.control_type -ceq 'ControlType.Button' -and $_.name -ceq 'Close' -and $_.enabled -and -not $_.offscreen}).Count -eq 2) 'Native duplicate Close evidence differs.'
$probe=Join-Path ([IO.Path]::GetTempPath()) ('duplisift-receipt-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $probe | Out-Null
try {
    $state=@{process=[pscustomobject]@{Id=$record.process_id};output=$probe}
    # Real exclusive JSON publication happens before the rejected row assertion.
    $snapshot.status='restore_collision';$failed=$false
    try {Confirm-DupliRestoredTable $state $snapshot $cells[1].name}catch{$failed=$_.Exception.Message -ceq 'Real restored receipt row differs from the verified original file.'}
    $path=Join-Path $probe 'restored-table.json'
    $saved=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
    Check ($failed -and $saved.observed.status -ceq 'restore_collision' -and $saved.observed.checkbox_enabled -eq $true -and
        $saved.expected_process_id -eq $record.process_id -and $saved.expected_original_path -ceq $cells[1].name) 'Rejected actual row was not retained before failure.'
    $hash=(Get-FileHash -LiteralPath $path).Hash;$failed=$false
    try {Confirm-DupliRestoredTable $state (Get-DupliRestoredTableSnapshot $grid $table) $cells[1].name}catch{$failed=$true}
    Check ($failed -and (Get-FileHash -LiteralPath $path).Hash -ceq $hash) 'Existing observation was overwritten.'
    $broken=[pscustomobject]@{Current=[pscustomobject]@{RowCount=1;ColumnCount=5}}
    $broken|Add-Member ScriptMethod GetItem {throw ('provider unavailable '+('x'*5000))}
    $partial=Get-DupliRestoredTableSnapshot $broken $table
    Check ($partial.rows -eq 1 -and $partial.columns -eq 5 -and $partial.observation_error.Length -eq 2048 -and $null -eq $partial.original_path) 'Partial provider observation was lost or unbounded.'
    $state.output=Join-Path $probe 'partial';New-Item -ItemType Directory -Path $state.output|Out-Null
    $failed=$false;try {Confirm-DupliRestoredTable $state $partial $cells[1].name}catch{$failed=$true}
    $saved=Get-Content -LiteralPath (Join-Path $state.output 'restored-table.json') -Raw|ConvertFrom-Json
    Check ($failed -and $saved.observed.observation_error.Length -eq 2048) 'Provider exception did not retain its bounded snapshot before refusal.'
    $grid.Items[1].Current.Name='x'*5000
    $bounded=Get-DupliRestoredTableSnapshot $grid $table
    Check ($bounded.original_path.Length -eq 4096 -and [bool]$bounded.observation_error) 'Oversized provider text was accepted or unbounded.'
} finally {Remove-Item -LiteralPath $probe -Recurse -Force}

function Window([string]$Title,[int]$Owner,[long]$Handle) {return [pscustomobject]@{Current=[pscustomobject]@{Name=$Title;ProcessId=$Owner;NativeWindowHandle=$Handle}}}
$dialog=Window $record.title $record.process_id $record.native_window.handle
$main=Window 'DupliSift' $record.process_id 101
$state=@{process=[pscustomobject]@{Id=$record.process_id}}
$script:events=[Collections.Generic.List[string]]::new();$script:mode='';$script:polls=0;$script:returnMain=$main
# Only platform ownership/input observations are substituted here. The real
# capture dismissal function must keep its original guarded SendKeys calls.
function Send-TwinQuayWorkflowKeys($State,$Root,[string]$Keys) {
    $script:events.Add('input:'+ $Root.Current.NativeWindowHandle +':'+$Keys)
    if($script:mode -ceq 'input-refusal' -or ($script:mode -ceq 'main-focus-refusal' -and -not $Keys)){throw 'original ownership/foreground refusal'}
}
function Get-TwinQuayWorkflowWindows($State) {
    $script:events.Add('observe');$script:polls++
    switch($script:mode) {
        'persistent' {return @($dialog,$main)}
        'replacement' {return @(Window $record.title $record.process_id ($record.native_window.handle+1))}
        'renamed' {return @(Window 'Unexpected dialog' $record.process_id $record.native_window.handle)}
        'foreign' {return @(Window $record.title ($record.process_id+1) $record.native_window.handle)}
        'duplicate' {return @($dialog,(Window $record.title $record.process_id ($record.native_window.handle+1)))}
        'observation-refusal' {throw 'original process observation refusal'}
        'delayed' {if($script:polls -eq 1){return @($dialog,$main)}}
    }
    return @($main)
}
function Wait-TwinQuayWorkflowWindow($State,[string]$Title) {
    Check ($Title -ceq 'DupliSift') 'Dismissal requested another window.'
    $script:events.Add('main-return')
    if($script:mode -ceq 'main-absent'){throw 'original main window wait refusal'}
    return $script:returnMain
}
function Start-Sleep {param($Milliseconds) $script:events.Add('wait');Check ($script:events.Count -lt 20) 'Unbounded dismissal replay.'}
function Reset([string]$Mode) {$script:mode=$Mode;$script:events.Clear();$script:polls=0;$script:returnMain=$main}
Reset 'delayed'
Close-DupliRestoredReceipt $state $dialog $main
Check (($script:events -join '|') -ceq "input:$($record.native_window.handle):{ESC}|observe|wait|observe|main-return|input:101:") 'Escape, exact disappearance and guarded original main return were not sequenced.'
foreach($mode in @('input-refusal','persistent','replacement','renamed','foreign','duplicate','observation-refusal','main-absent','main-focus-refusal')) {
    Reset $mode;$failed=$false
    try {Close-DupliRestoredReceipt $state $dialog $main -Seconds 0}catch{$failed=$true}
    Check ($failed -and @($script:events|Where-Object {$_ -like 'input:*:{ESC}'}).Count -eq 1) "Dismissal refusal swallowed or repeated input: $mode"
    if($mode -ceq 'input-refusal'){Check ($script:events.Count -eq 1) 'Input refusal reached later observations.'}
    if($mode -cnotin @('main-absent','main-focus-refusal')){Check (-not $script:events.Contains('main-return')) "Unexpected receipt reached main return: $mode"}
}
foreach($initial in @((Window 'Unknown receipt' $record.process_id $record.native_window.handle),(Window $record.title ($record.process_id+1) $record.native_window.handle))) {
    Reset 'closed';$failed=$false
    try {Close-DupliRestoredReceipt $state $initial $main}catch{$failed=$true}
    Check ($failed -and $script:events.Count -eq 0) 'Foreign initial receipt reached input.'
}
foreach($changed in @((Window 'Unknown' $record.process_id 101),(Window 'DupliSift' ($record.process_id+1) 101),(Window 'DupliSift' $record.process_id 102))) {
    Reset 'closed';$script:returnMain=$changed;$failed=$false
    try {Close-DupliRestoredReceipt $state $dialog $main}catch{$failed=$true}
    Check ($failed -and @($script:events|Where-Object {$_ -like 'input:*'}).Count -eq 1) 'Changed main window reached post-dismissal input.'
}
Write-Output 'PASS: native provider replay, pre-assert exclusive/partial/bounded snapshots, observed duplicate Close labels, one owned Escape and exact main return, 14 dismissal refusals.'

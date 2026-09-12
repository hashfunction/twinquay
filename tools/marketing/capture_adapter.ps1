# Copyright 2026 Trieflow LLC. MIT. Capture-only adaptation of unchanged qualification functions.
$script:DupliOriginalSurface=${function:Save-TwinQuayWorkflowSurface}
$script:DupliOriginalOracle=${function:Invoke-TwinQuayFileOracle}
$script:DupliCapturePython=$null
function Invoke-TwinQuayFileOracle($Context,[string]$Command) {
    if (-not $script:DupliCapturePython) {throw 'Capture Python runtime was not bound.'}
    # Same qualified independent byte oracle; only its host interpreter changes.
    $Context.python=$script:DupliCapturePython
    & $script:DupliOriginalOracle $Context $Command
}
function Save-TwinQuayWorkflowSurface($State,$Context,[string]$Name,$Root) {
    if ($Name -in @('01-scan-folder','03-reviewed-plan','05-conflict-receipt','07-restore-receipt')) {
        $handle=ConvertTo-TwinQuayWorkflowHandle $Root.Current.NativeWindowHandle 'surface-root'
        $null=Set-DupliCaptureWindow $State $handle $Root.Current.Name
    }
    # The original owned screenshot/control record always runs and can fail.
    & $script:DupliOriginalSurface $State $Context $Name $Root
    if ($Name -ceq '02-duplicate-results') {Save-DupliCaptureFrame $State $Root '01-scan-results'}
    if ($Name -ceq '03-reviewed-plan') {Save-DupliCaptureFrame $State $Root '02-review-quarantine-plan'}
}
function Assert-DupliRestoredTable($Snapshot,[int]$ProcessId,[string]$OriginalPath) {
    if ($Snapshot.process_id -ne $ProcessId -or $Snapshot.rows -ne 1 -or $Snapshot.columns -ne 5 -or
        $Snapshot.path_pid -ne $ProcessId -or $Snapshot.status_pid -ne $ProcessId -or $Snapshot.checkbox_pid -ne $ProcessId -or
        $Snapshot.original_path -cne $OriginalPath -or $Snapshot.status -cne 'restored' -or $Snapshot.checkbox_enabled -ne $false -or $Snapshot.path_offscreen -ne $false -or $Snapshot.status_offscreen -ne $false) {
        throw 'Real restored receipt row differs from the verified original file.'
    }
}
function Show-DupliRestoredReceipt($State) {
    $main=Wait-TwinQuayWorkflowWindow $State 'DupliSift'
    Send-TwinQuayWorkflowKeys $State $main '^+q'
    $dialog=Wait-TwinQuayWorkflowWindow $State 'Quarantine Receipts — DupliSift'
    $handle=ConvertTo-TwinQuayWorkflowHandle $dialog.Current.NativeWindowHandle 'surface-root'
    $null=Set-DupliCaptureWindow $State $handle $dialog.Current.Name
    # Preserve the actual full tree as well as its native pixels.
    $context=@{output=$State.output;surfaces=[Collections.Generic.List[object]]::new()}
    & $script:DupliOriginalSurface $State $context 'restored-receipt-observation' $dialog
    $tables=@(Get-TwinQuayWorkflowElements $dialog | Where-Object {
        $_.process_id -eq $State.process.Id -and $_.control_type -cin @('ControlType.Table','ControlType.DataGrid') -and -not $_.offscreen
    })
    if ($tables.Count -ne 1) {throw 'Expected one real restored receipt table.'}
    $grid=$tables[0].element.GetCurrentPattern([Windows.Automation.GridPattern]::Pattern)
    $path=$grid.GetItem(0,1);$status=$grid.GetItem(0,3);$checkbox=$grid.GetItem(0,0)
    $snapshot=@{process_id=$tables[0].process_id;rows=$grid.Current.RowCount;columns=$grid.Current.ColumnCount;
        path_pid=$path.Current.ProcessId;status_pid=$status.Current.ProcessId;checkbox_pid=$checkbox.Current.ProcessId;
        original_path=$path.Current.Name;status=$status.Current.Name;checkbox_enabled=$checkbox.Current.IsEnabled;
        path_offscreen=$path.Current.IsOffscreen;status_offscreen=$status.Current.IsOffscreen}
    $expected=$State.workflow.files.restored.receipt.items[0].original_path
    Assert-DupliRestoredTable $snapshot $State.process.Id $expected
    Save-DupliCaptureFrame $State $dialog '03-restore-complete'
    Write-NewUtf8Json (Join-Path $State.output 'restored-table.json') $snapshot
    Press-TwinQuayWorkflowButton $State $dialog 'Close'
    $null=Wait-TwinQuayWorkflowWindow $State 'DupliSift'
}
function Invoke-DupliCaptureWorkflow($State,[string]$Python) {
    $script:DupliCapturePython=$Python
    $signingTemporary=$State.temporary
    try {
        # Exclusive marker-owned C:\Demo; original Prepare appends Cedar House Review.
        $State.temporary=$State.demo.root
        Invoke-TwinQuayInstalledWorkflow $State
        Show-DupliRestoredReceipt $State
        # Viewing a receipt must leave the original successful restore bytes intact.
        $proof=& $Python (Join-Path $State.qualified 'tools/msix/workflow_files.py') 'restored' $State.workflow.files.prepare.root
        if ($LASTEXITCODE -ne 0) {throw 'Post-capture restored file verification failed.'}
        Write-NewUtf8Json (Join-Path $State.output 'restored-after-capture.json') (($proof -join "`n")|ConvertFrom-Json)
    } finally {$State.temporary=$signingTemporary;$script:DupliCapturePython=$null}
}

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
function Get-DupliRestoredTableSnapshot($Grid,$Table) {
    $snapshot=[ordered]@{process_id=$Table.process_id;table_type=$Table.control_type;rows=$null;columns=$null;
        path_pid=$null;status_pid=$null;checkbox_pid=$null;original_path=$null;status=$null;checkbox_enabled=$null;
        path_type=$null;status_type=$null;checkbox_type=$null;path_offscreen=$null;status_offscreen=$null;observation_error=$null}
    try {
        $snapshot.rows=$Grid.Current.RowCount;$snapshot.columns=$Grid.Current.ColumnCount
        $path=$Grid.GetItem(0,1);$status=$Grid.GetItem(0,3);$checkbox=$Grid.GetItem(0,0)
        $snapshot.path_pid=$path.Current.ProcessId;$snapshot.status_pid=$status.Current.ProcessId;$snapshot.checkbox_pid=$checkbox.Current.ProcessId
        $snapshot.original_path=[string]$path.Current.Name;$snapshot.status=[string]$status.Current.Name
        $snapshot.checkbox_enabled=$checkbox.Current.IsEnabled
        $snapshot.path_type=$path.Current.ControlType.ProgrammaticName;$snapshot.status_type=$status.Current.ControlType.ProgrammaticName
        $snapshot.checkbox_type=$checkbox.Current.ControlType.ProgrammaticName
        $snapshot.path_offscreen=$path.Current.IsOffscreen;$snapshot.status_offscreen=$status.Current.IsOffscreen
        foreach($name in @('original_path','status')) {if($snapshot[$name].Length -gt 4096){throw 'Restored cell text exceeds bounded capture observation.'}}
    } catch {$snapshot.observation_error=ConvertTo-TwinQuayBoundedDiagnosticText $_.Exception.Message 2048}
    foreach($name in @('original_path','status')) {if($null -ne $snapshot[$name]){$snapshot[$name]=ConvertTo-TwinQuayBoundedDiagnosticText $snapshot[$name] 4096}}
    return $snapshot
}
function Assert-DupliRestoredTable($Snapshot,[int]$ProcessId,[string]$OriginalPath) {
    # Qt 6.11.2 table-cell state never derives `disabled` from ItemIsEnabled.
    # UIA therefore reports this inactive model item as enabled. Preserve that
    # observed provider value; it is not the item's restore eligibility.
    if ($Snapshot.observation_error -or $Snapshot.process_id -ne $ProcessId -or $Snapshot.rows -ne 1 -or $Snapshot.columns -ne 5 -or
        $Snapshot.table_type -cnotin @('ControlType.Table','ControlType.DataGrid') -or
        $Snapshot.path_type -cne 'ControlType.DataItem' -or $Snapshot.status_type -cne 'ControlType.DataItem' -or $Snapshot.checkbox_type -cne 'ControlType.DataItem' -or
        $Snapshot.path_pid -ne $ProcessId -or $Snapshot.status_pid -ne $ProcessId -or $Snapshot.checkbox_pid -ne $ProcessId -or
        $Snapshot.original_path -cne $OriginalPath -or $Snapshot.status -cne 'restored' -or $Snapshot.checkbox_enabled -ne $true -or $Snapshot.path_offscreen -ne $false -or $Snapshot.status_offscreen -ne $false) {
        throw 'Real restored receipt row differs from the verified original file.'
    }
}
function Confirm-DupliRestoredTable($State,$Snapshot,[string]$OriginalPath) {
    Write-NewUtf8Json (Join-Path $State.output 'restored-table.json') @{observed=$Snapshot;expected_process_id=$State.process.Id;expected_original_path=$OriginalPath}
    Assert-DupliRestoredTable $Snapshot $State.process.Id $OriginalPath
}
function Close-DupliRestoredReceipt($State,$Dialog,$Main,[int]$Seconds=5) {
    $title='Quarantine Receipts — DupliSift'
    if ($Dialog.Current.Name -cne $title -or $Dialog.Current.ProcessId -ne $State.process.Id) {throw 'Only the exact owned receipt dialog can be dismissed.'}
    $handle=ConvertTo-TwinQuayWorkflowHandle $Dialog.Current.NativeWindowHandle 'surface-root'
    if ($Main.Current.Name -cne 'DupliSift' -or $Main.Current.ProcessId -ne $State.process.Id) {throw 'Original main window identity differs before receipt dismissal.'}
    $mainHandle=ConvertTo-TwinQuayWorkflowHandle $Main.Current.NativeWindowHandle 'surface-root'
    Send-TwinQuayWorkflowKeys $State $Dialog '{ESC}'
    $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        $remaining=@(Get-TwinQuayWorkflowWindows $State|Where-Object {
            $_.Current.Name -ceq $title -or (ConvertTo-TwinQuayWorkflowHandle $_.Current.NativeWindowHandle 'surface-root') -eq $handle
        })
        if ($remaining.Count -eq 0) {
            $main=Wait-TwinQuayWorkflowWindow $State 'DupliSift'
            if ($main.Current.Name -cne 'DupliSift' -or $main.Current.ProcessId -ne $State.process.Id -or
                (ConvertTo-TwinQuayWorkflowHandle $main.Current.NativeWindowHandle 'surface-root') -ne $mainHandle) {throw 'Original main window did not return after receipt dismissal.'}
            Send-TwinQuayWorkflowKeys $State $main ''
            return
        }
        if ($remaining.Count -ne 1 -or $remaining[0].Current.Name -cne $title -or $remaining[0].Current.ProcessId -ne $State.process.Id -or
            (ConvertTo-TwinQuayWorkflowHandle $remaining[0].Current.NativeWindowHandle 'surface-root') -ne $handle) {throw 'Receipt dialog identity changed during dismissal.'}
        if ([DateTime]::UtcNow -ge $deadline) {break}
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $deadline)
    throw 'Exact receipt dialog did not disappear after ordinary Escape.'
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
    $snapshot=Get-DupliRestoredTableSnapshot $grid $tables[0]
    $expected=$State.workflow.files.restored.receipt.items[0].original_path
    Confirm-DupliRestoredTable $State $snapshot $expected
    Save-DupliCaptureFrame $State $dialog '03-restore-complete'
    Close-DupliRestoredReceipt $State $dialog $main
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

# Copyright 2026 Trieflow LLC. MIT. Real installed consumer UI qualification.
# Dot-sourced by qualify-msix-install.ps1, retaining that helper's process handle.
Set-StrictMode -Version Latest

function ConvertTo-TwinQuaySendKeysLiteral([string]$Value) {
    $escaped=[Text.StringBuilder]::new()
    foreach ($character in $Value.ToCharArray()) {
        if ('+^%~()[]{}'.Contains([string]$character)) { [void]$escaped.Append('{').Append($character).Append('}') }
        else { [void]$escaped.Append($character) }
    }
    return $escaped.ToString()
}

function Select-TwinQuayWorkflowControl([object[]]$Items,[int]$ProcessId,[string]$Name,[string[]]$Types) {
    $matches=@($Items | Where-Object {
        $_.process_id -eq $ProcessId -and $_.name -ceq $Name -and
        $_.control_type -cin $Types -and $_.enabled -and -not $_.offscreen
    })
    if ($matches.Count -ne 1) { throw "Expected one owned visible enabled control '$Name' ($($Types -join ',')); found $($matches.Count)." }
    return $matches[0]
}

function Get-TwinQuayExceptionChain($Exception) {
    $chain=[Collections.Generic.List[object]]::new()
    $depth=0
    while ($Exception -and $depth -lt 16) {
        $chain.Add([ordered]@{
            depth=$depth
            type=$Exception.GetType().FullName
            message=$Exception.Message
            hresult=$Exception.HResult
            hresult_hex=('0x{0:X8}' -f ([long]$Exception.HResult -band 0xffffffffL))
            has_inner=[bool]$Exception.InnerException
        })
        $Exception=$Exception.InnerException
        $depth++
    }
    return @($chain)
}

function ConvertTo-TwinQuayBoundedDiagnosticText($Value,[int]$Limit) {
    if ($null -eq $Value) { return $null }
    $text=[string]$Value
    if ($text.Length -le $Limit) { return $text }
    return $text.Substring(0,$Limit)
}

function Get-TwinQuayErrorRecordEvidence($ErrorRecord) {
    $invocation=$ErrorRecord.InvocationInfo
    $scriptName=$null;$scriptLineNumber=0;$offsetInLine=0;$invocationName=$null;$line=$null;$positionMessage=$null
    if ($invocation) {
        $scriptName=$invocation.ScriptName
        $scriptLineNumber=$invocation.ScriptLineNumber
        $offsetInLine=$invocation.OffsetInLine
        $invocationName=$invocation.InvocationName
        $line=$invocation.Line
        $positionMessage=$invocation.PositionMessage
    }
    return [ordered]@{
        fully_qualified_error_id=ConvertTo-TwinQuayBoundedDiagnosticText $ErrorRecord.FullyQualifiedErrorId 1024
        category_info=ConvertTo-TwinQuayBoundedDiagnosticText $ErrorRecord.CategoryInfo 2048
        script_stack_trace=ConvertTo-TwinQuayBoundedDiagnosticText $ErrorRecord.ScriptStackTrace 8192
        invocation=[ordered]@{
            script_name=ConvertTo-TwinQuayBoundedDiagnosticText $scriptName 4096
            script_line_number=$scriptLineNumber
            offset_in_line=$offsetInLine
            invocation_name=ConvertTo-TwinQuayBoundedDiagnosticText $invocationName 1024
            line=ConvertTo-TwinQuayBoundedDiagnosticText $line 4096
            position_message=ConvertTo-TwinQuayBoundedDiagnosticText $positionMessage 4096
        }
    }
}

function ConvertTo-TwinQuayWorkflowHandle($Value,
    [ValidateSet('window-enumeration','input-root','native-dialog','native-dialog-button','surface-root')][string]$Site) {
    if ($null -eq $Value) { throw "Native window handle is null at $Site (value type: null)." }
    $valueType=$Value.GetType().FullName
    try { return [IntPtr]$Value }
    catch { throw "Native window handle conversion failed at $Site (value type: $valueType): $($_.Exception.Message)" }
}

function Invoke-TwinQuayWorkflowCore([Collections.IDictionary]$Operations) {
    $completed=[Collections.Generic.List[string]]::new()
    $errors=[Collections.Generic.List[string]]::new()
    $primary=$null
    $primaryExceptionChain=@()
    $primaryErrorRecord=$null
    $failedStage=$null
    foreach ($name in @('Prepare','Scan','Review','Quarantine','Conflict','Restore','Finish','ReleaseCollision')) {
        if (-not $Operations.Contains($name) -or $Operations[$name] -isnot [scriptblock]) { throw "Missing workflow operation: $name" }
    }
    try {
        foreach ($name in @('Prepare','Scan','Review','Quarantine','Conflict','Restore','Finish')) {
            $failedStage=$name
            & $Operations[$name] | Out-Host
            $completed.Add($name)
            $failedStage=$null
        }
    } catch {
        $primary=$_.Exception.Message
        $primaryExceptionChain=@(Get-TwinQuayExceptionChain $_.Exception)
        $primaryErrorRecord=Get-TwinQuayErrorRecordEvidence $_
    }
    finally {
        try { & $Operations.ReleaseCollision | Out-Host } catch { $errors.Add($_.Exception.Message) }
    }
    return [ordered]@{ passed=(-not $primary -and $errors.Count -eq 0); completed_stages=@($completed);
        failed_stage=$failedStage; primary_error=$primary; primary_exception_chain=@($primaryExceptionChain);
        primary_error_record=$primaryErrorRecord; cleanup_errors=@($errors) }
}

function New-TwinQuayCollision([string]$Path,[byte[]]$Bytes) {
    $stream=$null
    try {
        $stream=[IO.FileStream]::new($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,
            [IO.FileShare]::Read,4096,[IO.FileOptions]::DeleteOnClose)
        $stream.Write($Bytes,0,$Bytes.Length)
        $stream.Flush($true)
        return $stream
    } catch {
        # Close only the successfully created file handle; no cleanup by pathname.
        $primary=$_.Exception.Message
        if ($stream) {
            try { $stream.Dispose() } catch { throw "Collision creation failed: $primary; exact-handle cleanup failed: $($_.Exception.Message)" }
        }
        throw
    }
}

function Write-TwinQuayWorkflowResult([string]$Path,$Result) {
    try { Write-NewUtf8Json $Path $Result }
    catch { throw ('Workflow reporting failed: ' + $_.Exception.Message + '; retained workflow result: ' + ($Result | ConvertTo-Json -Depth 20 -Compress)) }
}

function Assert-TwinQuayWorkflowProcess($State) {
    if (-not $State.processOwned -or -not $State.processHandle -or $State.processHandle.IsClosed -or
        $State.processHandle.IsInvalid -or $State.process.HasExited) { throw 'The original owned installed process is no longer live.' }
    $State.process.Refresh()
    if ((Get-CanonicalPath $State.process.MainModule.FileName) -ine (Get-CanonicalPath (Join-Path $State.installed.InstallLocation 'TwinQuay.exe')) -or
        [TwinQuayQualification.NativePackageProbe]::GetFullName($State.process.Handle) -cne $State.ownedPackageFullName) {
        throw 'Installed workflow process path/package identity changed.'
    }
    Assert-FileMatchesRecord $State.process.MainModule.FileName (Get-RecordPayloadEntry $State.record 'TwinQuay.exe') 'Workflow executable' | Out-Null
}

function Get-TwinQuayWorkflowWindows($State) {
    Assert-TwinQuayWorkflowProcess $State
    $condition=[Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::ProcessIdProperty,$State.process.Id)
    $all=[Windows.Automation.AutomationElement]::RootElement.FindAll([Windows.Automation.TreeScope]::Children,$condition)
    $result=[Collections.Generic.List[object]]::new()
    $handles=[Collections.Generic.HashSet[long]]::new()
    foreach ($root in $all) {
        # A native owned IFileDialog is a descendant of its Qt owner in UIA,
        # even though its HWND is a separate top-level window (GA_ROOT).
        foreach ($item in @(Get-TwinQuayWorkflowElements $root)) {
            $element=$item.element
            if ($item.control_type -cne 'ControlType.Window') { continue }
            $nativeHandle=$element.Current.NativeWindowHandle
            # Qt can expose a transient UIA Window with no native HWND while the
            # scan table replaces its progress subtree. It cannot satisfy native
            # ownership, so treat it exactly like the existing zero-HWND case.
            if ($null -eq $nativeHandle) { continue }
            $handle=ConvertTo-TwinQuayWorkflowHandle $nativeHandle 'window-enumeration'
            if ($item.process_id -ne $State.process.Id -or $item.offscreen -or $handle -eq [IntPtr]::Zero) { continue }
            $native=Get-TwinQuayWorkflowNativeWindow $handle
            if ($native.process_id -ne $State.process.Id -or $native.root -ne $handle -or -not $native.visible) { continue }
            if ($handles.Add($handle.ToInt64())) { $result.Add($element) }
        }
    }
    return @($result)
}

function Get-TwinQuayWorkflowNativeWindow([IntPtr]$Handle) {
    $ownerId=[uint32]0
    [void][TwinQuayQualification.NativePackageProbe]::GetWindowThreadProcessId($Handle,[ref]$ownerId)
    $class=[Text.StringBuilder]::new(256);$title=[Text.StringBuilder]::new(4096)
    [void][TwinQuayQualification.NativePackageProbe]::GetClassName($Handle,$class,$class.Capacity)
    [void][TwinQuayQualification.NativePackageProbe]::GetWindowText($Handle,$title,$title.Capacity)
    return [pscustomobject]@{handle=$Handle;process_id=$ownerId;
        root=[TwinQuayQualification.NativePackageProbe]::GetAncestor($Handle,2);
        visible=[TwinQuayQualification.NativePackageProbe]::IsWindowVisible($Handle);
        enabled=[TwinQuayQualification.NativePackageProbe]::IsWindowEnabled($Handle);
        class_name=$class.ToString();title=$title.ToString();
        control_id=[TwinQuayQualification.NativePackageProbe]::GetDlgCtrlID($Handle)}
}

function Get-TwinQuayWorkflowElements($Root) {
    $items=[Collections.Generic.List[object]]::new()
    $elements=$Root.FindAll([Windows.Automation.TreeScope]::Subtree,[Windows.Automation.Condition]::TrueCondition)
    if ($elements.Count -gt 1500) { throw 'Owned workflow UI tree exceeds its evidence bound.' }
    foreach ($element in $elements) {
        $current=$element.Current
        $items.Add([pscustomobject]@{name=$current.Name;control_type=$current.ControlType.ProgrammaticName;
            process_id=$current.ProcessId;enabled=$current.IsEnabled;offscreen=$current.IsOffscreen;element=$element})
    }
    return @($items)
}

function Test-TwinQuayTransientUiaError($Exception) {
    while ($Exception) {
        # UIA_E_ELEMENTNOTAVAILABLE: the provider element was virtualized or
        # destroyed between enumeration and access. PowerShell wraps this COM
        # error in MethodInvocationException for AutomationElement.FindAll.
        if ($Exception.HResult -eq -2147220991) { return $true }
        $Exception=$Exception.InnerException
    }
    return $false
}

function Wait-TwinQuayWorkflowWindow($State,[string]$Title,[int]$Seconds=30) {
    $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
    $matches=@()
    $lastTransient=$null
    do {
        try {
            $windows=@(Get-TwinQuayWorkflowWindows $State)
            $errors=@($windows | Where-Object { $_.Current.Name -cmatch '^(Error|Traceback|Cannot read receipt|Plan was not saved|Application Error)' })
            if ($errors.Count) { throw ('Owned application error window: ' + $errors[0].Current.Name) }
            $matches=@($windows | Where-Object { $_.Current.Name -ceq $Title })
            # Scan progress can temporarily share the main window's title. Never
            # pick either ambiguous HWND; await a unique observed match instead.
            if ($matches.Count -eq 1) { return $matches[0] }
        } catch {
            if (-not (Test-TwinQuayTransientUiaError $_.Exception)) { throw }
            $lastTransient=$_.Exception.Message
            $matches=@()
        }
        Start-Sleep -Milliseconds 150
    } while ([DateTime]::UtcNow -lt $deadline)
    if ($matches.Count -gt 1) { throw "Ambiguous owned workflow window at deadline: $Title" }
    if ($lastTransient) { throw "Timed out awaiting exact owned workflow window after UIA_E_ELEMENTNOTAVAILABLE: $Title; $lastTransient" }
    throw "Timed out awaiting exact owned workflow window: $Title"
}

function Wait-TwinQuayWorkflowScanResult($State,[int]$Seconds=45) {
    $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
    $lastTransient=$null
    do {
        try {
            # Reacquire the owned top-level element on every poll. Qt replaces
            # its scan-progress UIA subtree when the result table is rendered.
            $main=Wait-TwinQuayWorkflowWindow $State 'TwinQuay'
            $items=@(Get-TwinQuayWorkflowElements $main)
            $matches=@($items | Where-Object {
                $_.name -ceq 'keep-original.bin' -and $_.process_id -eq $State.process.Id -and -not $_.offscreen
            })
            if ($matches.Count -gt 1) { throw 'Ambiguous original row in scan results.' }
            if ($matches.Count -eq 1) {
                return [pscustomobject]@{window=$main;reference=$matches[0].element}
            }
        } catch {
            if (-not (Test-TwinQuayTransientUiaError $_.Exception)) { throw }
            $lastTransient=$_.Exception.Message
        }
        Start-Sleep -Milliseconds 200
    } while ([DateTime]::UtcNow -lt $deadline)
    if ($lastTransient) { throw "Actual scan result remained unavailable after UIA_E_ELEMENTNOTAVAILABLE: $lastTransient" }
    throw 'Actual generated original/duplicate scan result was not rendered.'
}

function Find-TwinQuayWorkflowControl($State,$Root,[string]$Name,[string[]]$Types=@('ControlType.Button')) {
    Assert-TwinQuayWorkflowProcess $State
    return (Select-TwinQuayWorkflowControl @(Get-TwinQuayWorkflowElements $Root) $State.process.Id $Name $Types).element
}

function Send-TwinQuayWorkflowKeys($State,$Root,[string]$Keys,$Control=$null,[IntPtr]$ExpectedFocusHandle=[IntPtr]::Zero) {
    Assert-TwinQuayWorkflowProcess $State
    $handle=ConvertTo-TwinQuayWorkflowHandle $Root.Current.NativeWindowHandle 'input-root'
    if ($Root.Current.ProcessId -ne $State.process.Id -or $handle -eq [IntPtr]::Zero) { throw 'Cannot focus an unowned workflow window.' }
    $native=Get-TwinQuayWorkflowNativeWindow $handle
    if ($native.process_id -ne $State.process.Id -or $native.root -ne $handle -or -not $native.visible) { throw 'Workflow HWND is not the exact owned visible top-level window.' }
    [void][TwinQuayQualification.NativePackageProbe]::ShowWindow($handle,5)
    [void][TwinQuayQualification.NativePackageProbe]::SetForegroundWindow($handle)
    if ($Control) {
        if ($Control.Current.ProcessId -ne $State.process.Id) { throw 'Refusing input to an unowned control.' }
        $Control.SetFocus()
    }
    Start-Sleep -Milliseconds 100
    $foreground=[TwinQuayQualification.NativePackageProbe]::GetForegroundWindow()
    $foregroundPid=[uint32]0
    [void][TwinQuayQualification.NativePackageProbe]::GetWindowThreadProcessId($foreground,[ref]$foregroundPid)
    if ($foreground -ne $handle -or $foregroundPid -ne $State.process.Id) { throw 'Refusing keyboard input: exact owned dialog is not foreground.' }
    if ($ExpectedFocusHandle -ne [IntPtr]::Zero -and [TwinQuayQualification.NativePackageProbe]::GetFocusedWindow($handle) -ne $ExpectedFocusHandle) {
        throw 'Refusing keyboard input: exact native control no longer has focus.'
    }
    if ($Keys.Length) { [Windows.Forms.SendKeys]::SendWait($Keys) }
}

function Press-TwinQuayWorkflowButton($State,$Root,[string]$Name) {
    $button=Find-TwinQuayWorkflowControl $State $Root $Name
    Send-TwinQuayWorkflowKeys $State $Root ' ' $button
}

function Assert-TwinQuayNativeDialogButton($Dialog,$Button,[int]$ProcessId,[string]$Title,[string]$Name) {
    $expectedName=if($Title -ceq 'Save selected cleanup plan'){'Save'}else{'Select Folder'}
    if ($Title -cnotin @('Select a folder to add to the scanning list','Choose quarantine folder','Save selected cleanup plan') -or
        $Name -cne $expectedName -or $Dialog.title -cne $Title -or $Dialog.class_name -cne '#32770' -or
        $Dialog.process_id -ne $ProcessId -or $Dialog.handle -eq [IntPtr]::Zero -or $Dialog.root -ne $Dialog.handle -or
        -not $Dialog.visible -or -not $Dialog.enabled -or $Button.process_id -ne $ProcessId -or
        $Button.handle -eq [IntPtr]::Zero -or $Button.root -ne $Dialog.handle -or $Button.class_name -cne 'Button' -or
        $Button.control_id -ne 1 -or $Button.title.Replace('&','') -cne $Name -or -not $Button.visible -or -not $Button.enabled) {
        throw 'Native chooser action lacks the exact owned dialog and enabled IDOK Button identity.'
    }
}

function Press-TwinQuayNativeDialogButton($State,$Root,[string]$Name) {
    # This Windows common-dialog button is exposed as a UIA Pane on the native
    # runner. Require its real Button class, IDOK, caption and HWND ancestry.
    $button=Find-TwinQuayWorkflowControl $State $Root $Name @('ControlType.Button','ControlType.Pane')
    $dialogHandle=ConvertTo-TwinQuayWorkflowHandle $Root.Current.NativeWindowHandle 'native-dialog'
    $buttonHandle=ConvertTo-TwinQuayWorkflowHandle $button.Current.NativeWindowHandle 'native-dialog-button'
    $dialog=Get-TwinQuayWorkflowNativeWindow $dialogHandle
    $nativeButton=Get-TwinQuayWorkflowNativeWindow $buttonHandle
    Assert-TwinQuayNativeDialogButton $dialog $nativeButton $State.process.Id $Root.Current.Name $Name
    if (-not [TwinQuayQualification.NativePackageProbe]::IsChild($dialogHandle,$buttonHandle)) { throw 'Native chooser button is outside the exact dialog.' }
    Send-TwinQuayWorkflowKeys $State $Root ''
    # Use normal dialog focus management, then real keyboard input; no BM_CLICK,
    # direct IFileDialog result injection or application action API.
    if (-not [TwinQuayQualification.NativePackageProbe]::PostMessage($dialogHandle,0x28,$buttonHandle,[IntPtr]1)) { throw 'Native dialog focus request failed.' }
    $deadline=[DateTime]::UtcNow.AddSeconds(2)
    do {
        if ([TwinQuayQualification.NativePackageProbe]::GetFocusedWindow($dialogHandle) -eq $buttonHandle) { break }
        Start-Sleep -Milliseconds 50
    } while ([DateTime]::UtcNow -lt $deadline)
    if ([TwinQuayQualification.NativePackageProbe]::GetFocusedWindow($dialogHandle) -ne $buttonHandle) { throw 'Exact native chooser button did not receive keyboard focus.' }
    Assert-TwinQuayNativeDialogButton (Get-TwinQuayWorkflowNativeWindow $dialogHandle) (Get-TwinQuayWorkflowNativeWindow $buttonHandle) $State.process.Id $Root.Current.Name $Name
    Send-TwinQuayWorkflowKeys $State $Root ' ' $null $buttonHandle
}

function Save-TwinQuayWorkflowSurface($State,$Context,[string]$Name,$Root) {
    Assert-TwinQuayWorkflowProcess $State
    $items=@(Get-TwinQuayWorkflowElements $Root | Select-Object name,control_type,process_id,enabled,offscreen)
    $native=Get-TwinQuayWorkflowNativeWindow (ConvertTo-TwinQuayWorkflowHandle $Root.Current.NativeWindowHandle 'surface-root')
    $entry=[ordered]@{name=$Name;title=$Root.Current.Name;process_id=$Root.Current.ProcessId;controls=$items;
        native_window=[ordered]@{handle=$native.handle.ToInt64();root=$native.root.ToInt64();process_id=$native.process_id;title=$native.title;class_name=$native.class_name};
        screenshot_sha256=$null;screenshot_error=$null}
    try {
        Send-TwinQuayWorkflowKeys $State $Root ''
        $bounds=$Root.Current.BoundingRectangle
        $screen=[Windows.Forms.SystemInformation]::VirtualScreen
        if ($bounds.Width -lt 150 -or $bounds.Height -lt 80 -or $bounds.Width -gt 4096 -or $bounds.Height -gt 2160 -or
            $bounds.Left -lt $screen.Left -or $bounds.Top -lt $screen.Top -or $bounds.Right -gt $screen.Right -or $bounds.Bottom -gt $screen.Bottom) {
            throw 'Workflow screenshot bounds are not a fully visible owned window.'
        }
        $imagePath=Join-Path $Context.output ($Name+'.png')
        $bitmap=[Drawing.Bitmap]::new([int]$bounds.Width,[int]$bounds.Height)
        $graphics=$null; $stream=$null
        try {
            $graphics=[Drawing.Graphics]::FromImage($bitmap)
            $graphics.CopyFromScreen([int]$bounds.Left,[int]$bounds.Top,0,0,$bitmap.Size)
            $stream=[IO.FileStream]::new($imagePath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            $bitmap.Save($stream,[Drawing.Imaging.ImageFormat]::Png)
            $stream.Flush($true)
        } finally { if ($stream) {$stream.Dispose()}; if ($graphics) {$graphics.Dispose()}; $bitmap.Dispose() }
        $entry.screenshot_sha256=(Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash.ToLowerInvariant()
    } catch { $entry.screenshot_error=$_.Exception.Message }
    Write-NewUtf8Json (Join-Path $Context.output ($Name+'.json')) $entry
    $Context.surfaces.Add($entry)
    if ($entry.screenshot_error) { throw $entry.screenshot_error }
}

function Invoke-TwinQuayFileOracle($Context,[string]$Command) {
    $result=& $Context.python (Join-Path $PSScriptRoot 'workflow_files.py') $Command $Context.root
    if ($LASTEXITCODE -ne 0) { throw "Independent workflow $Command byte/receipt verification failed (exit $LASTEXITCODE)." }
    $parsed=($result -join "`n") | ConvertFrom-Json
    Write-NewUtf8Json (Join-Path $Context.output ($Command+'-files.json')) $parsed
    $Context.facts[$Command]=$parsed
    return $parsed
}

function Set-TwinQuayWorkflowFolder($State,[string]$Title,[string]$Folder) {
    $dialog=Wait-TwinQuayWorkflowWindow $State $Title
    # Native Windows IFileDialog address bar accepts a literal existing directory.
    Send-TwinQuayWorkflowKeys $State $dialog '%d'
    Send-TwinQuayWorkflowKeys $State $dialog ((ConvertTo-TwinQuaySendKeysLiteral $Folder)+'{ENTER}')
    Start-Sleep -Milliseconds 300
    Press-TwinQuayNativeDialogButton $State $dialog 'Select Folder'
}

function Wait-TwinQuayWorkflowCompletion($State,$Context,[string]$Status,[string]$Capture) {
    $expected="1 $Status`nReceipt: $($Context.facts.plan.receipt_path)`nUse Quarantine Receipts to inspect or restore. Rescan after restore."
    $deadline=[DateTime]::UtcNow.AddSeconds(30)
    do {
        foreach ($window in @(Get-TwinQuayWorkflowWindows $State)) {
            $items=@(Get-TwinQuayWorkflowElements $window)
            $message=@($items | Where-Object { $_.process_id -eq $State.process.Id -and $_.name.Replace("`r`n","`n") -ceq $expected -and -not $_.offscreen })
            if ($message.Count -eq 1) {
                Save-TwinQuayWorkflowSurface $State $Context $Capture $window
                Press-TwinQuayWorkflowButton $State $window 'OK'
                return
            }
        }
        Start-Sleep -Milliseconds 150
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Expected actual completion disclosure not observed: $Status"
}

function Invoke-TwinQuayWorkflowRestore($State,$Context,[string]$Capture) {
    $main=Wait-TwinQuayWorkflowWindow $State 'TwinQuay'
    Send-TwinQuayWorkflowKeys $State $main '^+q'
    $dialog=Wait-TwinQuayWorkflowWindow $State 'Quarantine Receipts — TwinQuay'
    $tables=@(Get-TwinQuayWorkflowElements $dialog | Where-Object {
        $_.process_id -eq $State.process.Id -and $_.control_type -cin @('ControlType.Table','ControlType.DataGrid') -and -not $_.offscreen
    })
    if ($tables.Count -ne 1) { throw 'Expected one actual receipt table.' }
    $grid=$tables[0].element.GetCurrentPattern([Windows.Automation.GridPattern]::Pattern)
    if ($grid.Current.RowCount -ne 1 -or $grid.Current.ColumnCount -ne 5) { throw 'Receipt table does not have exactly one item and the five source columns.' }
    $checkbox=$grid.GetItem(0,0)
    if ($checkbox.Current.ProcessId -ne $State.process.Id) { throw 'Receipt checkbox is not owned.' }
    $toggle=$checkbox.GetCurrentPattern([Windows.Automation.TogglePattern]::Pattern)
    if ($toggle.Current.ToggleState -ne [Windows.Automation.ToggleState]::Off) { throw 'Receipt restore selection was unexpectedly preselected.' }
    # Qt 6.11.2 QAccessibleTableCell's toggle action selects the cell; it does
    # not edit CheckStateRole. Use real QTableWidget keyboard behavior and then
    # read the actual checkbox state through UIA (also covered with QTest).
    Send-TwinQuayWorkflowKeys $State $dialog '^{HOME} ' $tables[0].element
    if ($toggle.Current.ToggleState -ne [Windows.Automation.ToggleState]::On) { throw 'Actual receipt restore checkbox did not become checked.' }
    Save-TwinQuayWorkflowSurface $State $Context $Capture $dialog
    Press-TwinQuayWorkflowButton $State $dialog 'Restore selected'
}

function Invoke-TwinQuayInstalledWorkflow($State) {
    Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes,System.Windows.Forms,System.Drawing
    $context=[ordered]@{root=$null;output=$null;python=(Join-Path $PSScriptRoot '../../.venv/Scripts/python.exe');
        collision=$null;facts=[ordered]@{};surfaces=[Collections.Generic.List[object]]::new()}
    $operations=[ordered]@{}
    $operations.Prepare={
        Assert-TwinQuayWorkflowProcess $State
        $candidate=Join-Path $State.temporary 'workflow-fixture'
        New-Item -ItemType Directory -Path $candidate -ErrorAction Stop | Out-Null
        $context.root=$candidate
        $candidate=Join-Path $State.output 'workflow'
        New-Item -ItemType Directory -Path $candidate -ErrorAction Stop | Out-Null
        $context.output=$candidate
        Invoke-TwinQuayFileOracle $context 'prepare' | Out-Null
    }.GetNewClosure()
    $operations.Scan={
        $main=Wait-TwinQuayWorkflowWindow $State 'TwinQuay'
        $standard=Find-TwinQuayWorkflowControl $State $main 'Standard' @('ControlType.RadioButton')
        Send-TwinQuayWorkflowKeys $State $main ' ' $standard
        $combo=Find-TwinQuayWorkflowControl $State $main '' @('ControlType.ComboBox')
        # Actual source order: Filename, Contents, Folders. Saved-plan exact_content
        # validation additionally rejects any scan/configuration mismatch.
        Send-TwinQuayWorkflowKeys $State $main '{HOME}{DOWN}' $combo
        # QAccessibleComboBox has Value, not Selection, in Qt 6.11.2's UIA provider.
        if ($combo.GetCurrentPattern([Windows.Automation.ValuePattern]::Pattern).Current.Value -cne 'Contents') { throw 'Actual Contents scan mode was not selected.' }
        Press-TwinQuayWorkflowButton $State $main ''
        Set-TwinQuayWorkflowFolder $State 'Select a folder to add to the scanning list' $context.facts.prepare.input
        $main=Wait-TwinQuayWorkflowWindow $State 'TwinQuay'
        Save-TwinQuayWorkflowSurface $State $context '01-scan-folder' $main
        Press-TwinQuayWorkflowButton $State $main 'Scan'
        $scan=Wait-TwinQuayWorkflowScanResult $State
        $main=$scan.window
        $reference=$scan.reference
        $reference.GetCurrentPattern([Windows.Automation.SelectionItemPattern]::Pattern).Select()
        # Windows Forms SendKeys represents Space as a literal, not {SPACE}.
        Send-TwinQuayWorkflowKeys $State $main '^ '
        Send-TwinQuayWorkflowKeys $State $main '^a'
        Save-TwinQuayWorkflowSurface $State $context '02-duplicate-results' $main
    }.GetNewClosure()
    $operations.Review={
        $main=Wait-TwinQuayWorkflowWindow $State 'TwinQuay'
        Send-TwinQuayWorkflowKeys $State $main '^d'
        $dialog=Wait-TwinQuayWorkflowWindow $State 'Review Cleanup Plan — TwinQuay'
        Press-TwinQuayWorkflowButton $State $dialog 'Save plan…'
        $save=Wait-TwinQuayWorkflowWindow $State 'Save selected cleanup plan'
        Send-TwinQuayWorkflowKeys $State $save '%n^a'
        Send-TwinQuayWorkflowKeys $State $save ((ConvertTo-TwinQuaySendKeysLiteral $context.facts.prepare.plan_path))
        Press-TwinQuayNativeDialogButton $State $save 'Save'
        $dialog=Wait-TwinQuayWorkflowWindow $State 'Review Cleanup Plan — TwinQuay'
        Invoke-TwinQuayFileOracle $context 'plan' | Out-Null
        Press-TwinQuayWorkflowButton $State $dialog 'Choose folder…'
        Set-TwinQuayWorkflowFolder $State 'Choose quarantine folder' $context.facts.prepare.quarantine
        $dialog=Wait-TwinQuayWorkflowWindow $State 'Review Cleanup Plan — TwinQuay'
        $folder=Find-TwinQuayWorkflowControl $State $dialog 'User-selected quarantine folder' @('ControlType.Edit')
        if ((Get-CanonicalPath $folder.GetCurrentPattern([Windows.Automation.ValuePattern]::Pattern).Current.Value) -ine (Get-CanonicalPath $context.facts.prepare.quarantine)) { throw 'Actual quarantine folder selection differs from the owned fixture.' }
        Save-TwinQuayWorkflowSurface $State $context '03-reviewed-plan' $dialog
    }.GetNewClosure()
    $operations.Quarantine={
        $dialog=Wait-TwinQuayWorkflowWindow $State 'Review Cleanup Plan — TwinQuay'
        Press-TwinQuayWorkflowButton $State $dialog 'Verify and quarantine selected'
        Wait-TwinQuayWorkflowCompletion $State $context 'quarantined' '04-quarantine-complete'
        Invoke-TwinQuayFileOracle $context 'quarantined' | Out-Null
    }.GetNewClosure()
    $operations.Conflict={
        # Fixed generated content stays outside uploaded metadata. Bind its exact
        # bytes to the independent Python oracle before creating the held file.
        $bytes=[Text.Encoding]::UTF8.GetBytes("TwinQuay owned restore collision: preserve while handle is held.`n")
        $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
        if ($bytes.Length -ne $context.facts.prepare.collision.bytes -or $hash -cne $context.facts.prepare.collision.sha256) { throw 'Collision fixture differs from the independent source oracle.' }
        $context.collision=New-TwinQuayCollision (Join-Path $context.root 'input/duplicate-copy.bin') $bytes
        Invoke-TwinQuayWorkflowRestore $State $context '05-conflict-receipt'
        Wait-TwinQuayWorkflowCompletion $State $context 'restore_collision' '06-conflict-disclosed'
        Invoke-TwinQuayFileOracle $context 'restore_collision' | Out-Null
        $context.collision.Dispose()
        $context.collision=$null
        if (Test-Path -LiteralPath (Join-Path $context.root 'input/duplicate-copy.bin')) { throw 'Exact owned collision file did not disappear after handle close.' }
    }.GetNewClosure()
    $operations.Restore={
        Invoke-TwinQuayWorkflowRestore $State $context '07-restore-receipt'
        Wait-TwinQuayWorkflowCompletion $State $context 'restored' '08-restore-complete'
        Invoke-TwinQuayFileOracle $context 'restored' | Out-Null
    }.GetNewClosure()
    $operations.Finish={
        $main=Wait-TwinQuayWorkflowWindow $State 'TwinQuay'
        Save-TwinQuayWorkflowSurface $State $context '09-restored-main' $main
        Assert-TwinQuayWorkflowProcess $State
    }.GetNewClosure()
    $operations.ReleaseCollision={ if ($context.collision) { $context.collision.Dispose(); $context.collision=$null } }.GetNewClosure()
    $result=Invoke-TwinQuayWorkflowCore $operations
    $State.workflow=[ordered]@{schema_version=1;source_commit=$State.record.sourceCommit;process_id=$State.process.Id;
        package_full_name=$State.ownedPackageFullName;executable_sha256=$State.executableSha256;
        result=$result;files=$context.facts;surfaces=@($context.surfaces);diagnostic_errors=@();source_inputs=[ordered]@{}}
    try {
        foreach ($relative in @('qualify-workflow.ps1','workflow_files.py')) {
            $State.workflow.source_inputs[$relative]=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $relative) -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    } catch {
        $State.workflow.diagnostic_errors+= 'Source evidence failed: '+$_.Exception.Message
        $result.passed=$false
    }
    if (-not $result.passed -and $context.output) {
        try {
            $index=0
            foreach ($window in @(Get-TwinQuayWorkflowWindows $State)) {
                try { Save-TwinQuayWorkflowSurface $State $context ('failure-window-'+$index) $window }
                catch { $State.workflow.diagnostic_errors+= $_.Exception.Message }
                $index++
                if ($index -ge 8) { break }
            }
        } catch { $State.workflow.diagnostic_errors+= $_.Exception.Message }
        $State.workflow.surfaces=@($context.surfaces)
    }
    if ($context.output) { Write-TwinQuayWorkflowResult (Join-Path $context.output 'workflow.json') $State.workflow }
    if (-not $result.passed) { throw ('Installed consumer workflow failed: '+($State.workflow | ConvertTo-Json -Depth 20 -Compress)) }
}

function Close-TwinQuayWorkflowWindow($State) {
    Assert-TwinQuayWorkflowProcess $State
    if (-not $State.process.CloseMainWindow()) { throw 'Activated TwinQuay refused a normal main-window close request.' }
    # Real scan results make the document dirty. Answer only the source-defined
    # exact normal-close question; other dialogs remain failures, never dismissed.
    $deadline=[DateTime]::UtcNow.AddSeconds(10)
    do {
        if ($State.process.HasExited) { return }
        foreach ($window in @(Get-TwinQuayWorkflowWindows $State)) {
            if ($window.Current.Name -ceq 'Unsaved results') {
                $message=Find-TwinQuayWorkflowControl $State $window 'You have unsaved results, do you really want to quit?' @('ControlType.Text')
                if ($message) { Press-TwinQuayWorkflowButton $State $window 'Yes'; return }
            }
        }
        Start-Sleep -Milliseconds 150
    } while ([DateTime]::UtcNow -lt $deadline)
}

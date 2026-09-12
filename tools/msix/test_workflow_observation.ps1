# Copyright 2026 Trieflow LLC. MIT. Local helper tests are not installed UI acceptance.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-workflow.ps1')
function Assert($Value,[string]$Message) { if (-not $Value) { throw $Message } }
if ($IsWindows) {
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
} else {
    # Only the unavailable platform boundary is modeled. The production tree
    # reader, error classifier, and bounded completion wait execute below.
    Add-Type @'
namespace Windows.Automation {
    public enum TreeScope { Subtree }
    public class Condition { public static readonly Condition TrueCondition = new Condition(); }
    public class AutomationElement { public static readonly object NotSupported = new object(); }
}
'@
}
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class TwinQuayUnavailableObservationFixture {
    public static void Read(int hresult) { throw new COMException("Provider observation failed.", hresult); }
}
'@
$script:state=@{process=[pscustomobject]@{Id=42}}
$script:context=@{facts=@{plan=@{receipt_path='C:\owned-fixture\receipt.json'}}}
$script:expected="1 quarantined`nReceipt: C:\owned-fixture\receipt.json`nUse Quarantine Receipts to inspect or restore. Rescan after restore."
function New-Element($ControlType=[pscustomobject]@{ProgrammaticName='ControlType.Text'},[string]$Name=$script:expected,[int]$Owner=42,[bool]$Offscreen=$false) {
    return [pscustomobject]@{Current=[pscustomobject]@{Name=$Name;ControlType=$ControlType;ProcessId=$Owner;IsEnabled=$true;IsOffscreen=$Offscreen}}
}
$script:root=[pscustomobject]@{Current=[pscustomobject]@{Name='Completion';ProcessId=42}}
$script:root | Add-Member ScriptMethod FindAll {
    param($Scope,$Condition)
    Assert ($Scope -eq [Windows.Automation.TreeScope]::Subtree -and
        [object]::ReferenceEquals($Condition,[Windows.Automation.Condition]::TrueCondition)) 'Production tree query changed.'
    $script:reads++
    $index=[Math]::Min($script:reads-1,$script:snapshots.Count-1)
    foreach ($item in $script:snapshots[$index]) {
        if ($item -is [Runtime.InteropServices.COMException]) { [TwinQuayUnavailableObservationFixture]::Read($item.HResult) }
    }
    return ,$script:snapshots[$index]
}
function Get-TwinQuayWorkflowWindows($State) {
    Assert ([object]::ReferenceEquals($State,$script:state)) 'Completion changed its ownership state.'
    return $script:root
}
function Save-TwinQuayWorkflowSurface($State,$Context,[string]$Capture,$Root) {
    Assert ([object]::ReferenceEquals($State,$script:state) -and [object]::ReferenceEquals($Context,$script:context) -and
        [object]::ReferenceEquals($Root,$script:root) -and $Capture -ceq 'quarantine') 'Completion changed its evidence target.'
    $script:saved++
    if ($script:actionFailure -ceq 'capture') { throw [Runtime.InteropServices.COMException]::new('Capture failed.',-2147220991) }
}
function Press-TwinQuayWorkflowButton($State,$Root,[string]$Name) {
    Assert ([object]::ReferenceEquals($State,$script:state) -and [object]::ReferenceEquals($Root,$script:root) -and
        $Name -ceq 'OK' -and $script:saved -eq 1) 'Completion changed its input target or skipped evidence.'
    $script:pressed++
    if ($script:actionFailure -ceq 'input') { throw [Runtime.InteropServices.COMException]::new('Input failed.',-2147220991) }
}
function Reset-Observation($Snapshots,[string]$ActionFailure='') {
    $script:snapshots=$Snapshots;$script:reads=0;$script:saved=0;$script:pressed=0;$script:actionFailure=$ActionFailure
}

$valid=New-Element
foreach ($kind in @('null','not-supported','element-unavailable')) {
    $unavailable=switch ($kind) {
        'null' { New-Element -ControlType $null -Name 'transition child' }
        'not-supported' { New-Element -ControlType ([Windows.Automation.AutomationElement]::NotSupported) -Name 'transition child' }
        'element-unavailable' { [Runtime.InteropServices.COMException]::new('Provider observation failed.',-2147220991) }
    }
    # The exact success text comes first: rejecting only the bad child would
    # incorrectly permit input using an incomplete snapshot.
    Reset-Observation @(@($valid,$unavailable),@($valid))
    Wait-TwinQuayWorkflowCompletion $script:state $script:context 'quarantined' 'quarantine' -Seconds 2
    Assert ($script:reads -eq 2 -and $script:saved -eq 1 -and $script:pressed -eq 1) "Incomplete $kind snapshot was accepted or was not retried."
    Reset-Observation (, @($valid,$unavailable))
    $failure=$null
    try { Wait-TwinQuayWorkflowCompletion $script:state $script:context 'quarantined' 'quarantine' -Seconds 0 } catch { $failure=$_.Exception.Message }
    Assert ($failure -match 'Expected actual completion disclosure not observed' -and
        $script:reads -eq 1 -and $script:saved -eq 0 -and $script:pressed -eq 0) "Persistent $kind observation escaped the deadline or produced input."
}
Write-Output 'PASS: real tree reader discards complete snapshots on null/NotSupported/unavailable control observations; completion reacquires within its deadline.'

foreach ($bad in @((New-Element -ControlType ([pscustomobject]@{})),([Runtime.InteropServices.COMException]::new('Provider observation failed.',-2147220988)))) {
    Reset-Observation @(@($valid,$bad),@($valid))
    $failure=$null
    try { Wait-TwinQuayWorkflowCompletion $script:state $script:context 'quarantined' 'quarantine' -Seconds 2 } catch { $failure=$_ }
    Assert ($null -ne $failure -and -not (Test-TwinQuayTransientUiaError $failure.Exception) -and
        $script:reads -eq 1 -and $script:saved -eq 0 -and $script:pressed -eq 0) 'Unexpected property/provider failure was retried or concealed.'
}
Assert (-not (Test-TwinQuayTransientUiaError ([InvalidOperationException]::new('unmarked')))) 'Unmarked operation failure became transient.'
Write-Output 'PASS: unexpected control objects, other UIA HRESULTs, and unmarked errors remain fatal.'

$rejected=[ordered]@{
    foreign=@((New-Element -Owner 43))
    mismatched=@((New-Element -Name ($script:expected.Replace('receipt.json','other.json'))))
    offscreen=@((New-Element -Offscreen $true))
    absent=@()
    ambiguous=@($valid,$valid)
}
foreach ($case in $rejected.Keys) {
    Reset-Observation (, $rejected[$case])
    $failure=$null
    try { Wait-TwinQuayWorkflowCompletion $script:state $script:context 'quarantined' 'quarantine' -Seconds 0 } catch { $failure=$_.Exception.Message }
    Assert ($failure -match 'Expected actual completion disclosure not observed' -and
        $script:reads -eq 1 -and $script:saved -eq 0 -and $script:pressed -eq 0) "The $case completion passed or lost its bounded failure."
}
foreach ($action in @('capture','input')) {
    Reset-Observation (, @($valid)) $action
    $failure=$null
    try { Wait-TwinQuayWorkflowCompletion $script:state $script:context 'quarantined' 'quarantine' -Seconds 2 } catch { $failure=$_.Exception.Message }
    $expectedPresses=if ($action -ceq 'input') { 1 } else { 0 }
    Assert ($failure -match "$action failed" -and $script:reads -eq 1 -and
        $script:saved -eq 1 -and $script:pressed -eq $expectedPresses) 'Capture/input failure was retried as an observation failure.'
}
Write-Output 'PASS: exact completion ownership/disclosure/visibility/uniqueness gates remain required; capture and input failures are never retried.'

# Replay run 34673149420's owned recent-folder popup through the production
# classifier/tree reader/navigation. Only UIA/native/input endpoints are adapters.
$script:state=@{process=[pscustomobject]@{Id=9224}}
function Reset-RecentMenu([int]$Focus=-1) {
    $script:menuMode='valid';$script:menuEntered=$false;$script:menuKeys=[Collections.Generic.List[string]]::new()
    $script:root.Current=[pscustomobject]@{Name='DupliSift';ProcessId=9224;IsEnabled=$true;IsOffscreen=$false;
        NativeWindowHandle=852364;ControlType=[pscustomobject]@{ProgrammaticName='ControlType.Window'}}
    $script:menuItems=@($script:root)
    foreach($pair in @(
        @('Add Folder...','MenuItem'),@('','Separator'),
        @('D:/a/_temp/.duplisift-install-950c7331ddbe49fc9c6a986318e3a34c/Cedar House Review/Project Documents','MenuItem'),
        @('','Separator'),@('Clear List','MenuItem'))) {
        $item=New-Element -Name $pair[0] -Owner 9224 -ControlType ([pscustomobject]@{ProgrammaticName=('ControlType.'+$pair[1])})
        $item.Current.IsEnabled=$pair[1] -ceq 'MenuItem'
        $item.Current|Add-Member NoteProperty HasKeyboardFocus $false
        $script:menuItems+= $item
    }
    $script:menuActions=@($script:menuItems | Where-Object {$_.Current.ControlType.ProgrammaticName -ceq 'ControlType.MenuItem'})
    if($Focus -ge 0){$script:menuActions[$Focus].Current.HasKeyboardFocus=$true}
    Reset-Observation (, $script:menuItems)
}
function Get-TwinQuayWorkflowWindows($State) {
    Assert ([object]::ReferenceEquals($State,$script:state)) 'Menu changed its ownership state.'
    if($script:menuEntered) {
        return [pscustomobject]@{Current=[pscustomobject]@{Name='Select a folder to add to the scanning list';ProcessId=9224;
            IsEnabled=$true;IsOffscreen=$false;NativeWindowHandle=200}}
    }
    if($script:menuMode -ceq 'absent'){return @()}
    if($script:menuMode -ceq 'duplicate-window'){return @($script:root,$script:root)}
    return $script:root
}
function Get-TwinQuayWorkflowNativeWindow([IntPtr]$Handle) {
    $native=[pscustomobject]@{handle=$Handle;root=$Handle;process_id=9224;visible=$true;enabled=$true;
        title='DupliSift';class_name='Qt6112QWindowPopupDropShadowSaveBits'}
    if($Handle -eq [IntPtr]200){$native.title='Select a folder to add to the scanning list';$native.class_name='#32770'}
    switch($script:menuMode) {
        'foreign-native' {$native.process_id=9999}
        'child-window' {$native.root=[IntPtr]123}
        'hidden-native' {$native.visible=$false}
        'disabled-native' {$native.enabled=$false}
        'wrong-class' {$native.class_name='Qt6112QWindowPopup'}
        'wrong-title' {$native.title='Other'}
    }
    return $native
}
function Send-TwinQuayWorkflowKeys($State,$Root,[string]$Keys,$ExpectedFocusedMenuItem=$null) {
    Assert ([object]::ReferenceEquals($State,$script:state) -and [object]::ReferenceEquals($Root,$script:root)) 'Menu input changed owned target.'
    $script:menuKeys.Add($Keys)
    if($script:menuMode -ceq 'input-failure'){throw [Runtime.InteropServices.COMException]::new('Menu input failed.',-2147220991)}
    $focused=@($script:menuActions|Where-Object {$_.Current.HasKeyboardFocus})
    if($Keys -ceq '{ENTER}') {
        Assert ($focused.Count -eq 1 -and $focused[0].Current.Name -ceq 'Add Folder...') 'Enter reached another menu action.'
        Assert ([object]::ReferenceEquals($ExpectedFocusedMenuItem,$focused[0])) 'Input boundary did not receive exact menu item for its final focus check.'
        $script:menuEntered=$true;return
    }
    if($script:menuMode -ceq 'stuck-focus'){return}
    $index=0
    if($Keys -ceq '{UP}') {
        Assert ($focused.Count -eq 1) 'Up sent without observed focus.'
        $index=[Math]::Max(0,[array]::IndexOf($script:menuActions,$focused[0])-1)
    } else {Assert ($Keys -ceq '{DOWN}' -and $focused.Count -eq 0) 'Unexpected menu navigation input.'}
    foreach($item in $script:menuActions){$item.Current.HasKeyboardFocus=$false}
    $script:menuActions[$index].Current.HasKeyboardFocus=$true
    if($script:menuMode -ceq 'changed-menu'){$script:menuActions[1].Current.Name='changed recent folder'}
}
foreach($focus in @(-1,0,1,2)) {
    Reset-RecentMenu $focus
    $chooser=Wait-TwinQuayWorkflowAddFolderChooser $script:state -Seconds 3
    Assert ($chooser.Current.NativeWindowHandle -eq 200 -and $script:menuKeys[-1] -ceq '{ENTER}' -and
        $script:menuKeys.Count -le 3) "Menu route failed from focus position $focus."
}
Reset-RecentMenu;$script:menuEntered=$true
$chooser=Wait-TwinQuayWorkflowAddFolderChooser $script:state -Seconds 0
Assert ($chooser.Current.NativeWindowHandle -eq 200 -and $script:menuKeys.Count -eq 0) 'Fresh-profile chooser caused menu input.'
foreach($case in @('foreign-native','child-window','hidden-native','disabled-native','wrong-class','wrong-title',
    'duplicate-window','foreign-control','disabled-add','offscreen-add','duplicate-add','wrong-order','missing-clear','ambiguous-focus','absent')) {
    Reset-RecentMenu 0;$script:menuMode=$case
    switch($case) {
        'foreign-control' {$script:menuActions[1].Current.ProcessId=9999}
        'disabled-add' {$script:menuActions[0].Current.IsEnabled=$false}
        'offscreen-add' {$script:menuActions[0].Current.IsOffscreen=$true}
        'duplicate-add' {$script:menuActions[1].Current.Name='Add Folder...'}
        'wrong-order' {$script:menuActions[0].Current.Name='recent';$script:menuActions[1].Current.Name='Add Folder...'}
        'missing-clear' {$script:menuActions[-1].Current.Name='Other'}
        'ambiguous-focus' {$script:menuActions[1].Current.HasKeyboardFocus=$true}
    }
    $failure=$null;try{Wait-TwinQuayWorkflowAddFolderChooser $script:state -Seconds 0|Out-Null}catch{$failure=$_.Exception.Message}
    Assert ($failure -and $script:menuKeys.Count -eq 0) "Unsafe $case menu accepted or received input."
}
foreach($case in @('changed-menu','stuck-focus','input-failure')) {
    Reset-RecentMenu 2;$script:menuMode=$case
    $failure=$null;try{Wait-TwinQuayWorkflowAddFolderChooser $script:state -Seconds 3|Out-Null}catch{$failure=$_.Exception.Message}
    $expected=switch($case){'changed-menu'{'popup changed'}'stuck-focus'{'bounded menu navigation'}'input-failure'{'Menu input failed'}}
    $maxKeys=if($case -ceq 'stuck-focus'){3}else{1}
    Assert ($failure -match $expected -and $script:menuKeys.Count -eq $maxKeys -and -not $script:menuEntered) "Unsafe $case navigation was retried or activated."
}
'PASS: observed owned recent-folder popup, all initial focus positions and fresh chooser; 18 negative/action variants, bounded navigation and no history selection.'

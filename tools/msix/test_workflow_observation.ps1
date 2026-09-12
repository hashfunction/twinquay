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

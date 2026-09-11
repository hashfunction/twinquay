# Copyright 2026 Trieflow LLC. MIT. Parser regression; no keyboard input is sent.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if (-not ('System.Windows.Forms.SendKeys' -as [type])) {
    Add-Type -AssemblyName System.Windows.Forms
}
function Assert($Value,[string]$Message) { if (-not $Value) { throw $Message } }

# Parse the actual workflow arguments with the same Windows Forms implementation
# used by SendWait. Inspect queued key events without sending them to any window.
$type='System.Windows.Forms.SendKeys' -as [type]
$flags=[Reflection.BindingFlags]'NonPublic,Static'
$parse=$type.GetMethod('ParseKeys',$flags)
$queueField=$type.GetField('s_events',$flags)
Assert ($parse -and $queueField) 'Windows Forms parser contract is unavailable.'
$queue=$queueField.GetValue($null)
$emptyWindow=[Activator]::CreateInstance($parse.GetParameters()[1].ParameterType)
function Get-KeyDowns([string]$Keys) {
    Assert ($queue.Count -eq 0) 'Parser fixture inherited pending keyboard input.'
    try {
        [void]$parse.Invoke($null,@($Keys,$emptyWindow))
        $control=$false;$shift=$false;$alt=$false
        foreach($event in $queue) {
            $message=[int]$event.WM;$key=[int]$event.ParamL
            Assert ($message -in @(0x100,0x101,0x104,0x105)) 'Shortcut emitted character data instead of keyboard events.'
            $down=$message -in @(0x100,0x104)
            switch($key) {
                16 {$shift=$down}
                17 {$control=$down}
                18 {$alt=$down}
                default {if($down){'{0}:{1}:{2}:{3}' -f $key,$control,$shift,$alt}}
            }
        }
        Assert (-not $control -and -not $shift -and -not $alt) 'Shortcut left a modifier pressed.'
    } finally { $queue.Clear() }
}
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'qualify-workflow.ps1'),[ref]$tokens,[ref]$errors)
Assert (-not $errors) 'Workflow PowerShell failed to parse.'
$scan=@($ast.FindAll({param($node)
    $node -is [Management.Automation.Language.AssignmentStatementAst] -and $node.Left.Extent.Text -ceq '$operations.Scan'
},$true))
$restore=@($ast.FindAll({param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Invoke-TwinQuayWorkflowRestore'
},$true))
Assert ($scan.Count -eq 1 -and $restore.Count -eq 1) 'Exact workflow operations were not found.'
function Get-LiteralInputs($Node) {
    foreach($command in $Node.FindAll({param($child)
        $child -is [Management.Automation.Language.CommandAst] -and $child.GetCommandName() -ceq 'Send-TwinQuayWorkflowKeys'
    },$true)) {
        Assert ($command.CommandElements[3] -is [Management.Automation.Language.StringConstantExpressionAst]) 'Expected a literal workflow shortcut.'
        $command.CommandElements[3].Value
    }
}
$scanInputs=@(Get-LiteralInputs $scan[0].Right)
$restoreInputs=@(Get-LiteralInputs $restore[0].Body)
Assert ($scanInputs.Count -eq 4 -and $restoreInputs.Count -eq 2) 'Workflow shortcut sequence changed; review its event contract.'
Assert ((@(Get-KeyDowns $scanInputs[2]) -join ',') -ceq '32:True:False:False') 'Reference action must receive Ctrl+Space.'
Assert ((@(Get-KeyDowns $restoreInputs[1]) -join ',') -ceq '36:True:False:False,32:False:False:False') 'Receipt selection must receive Ctrl+Home, then Space without Ctrl.'
Write-Output 'PASS: actual workflow inputs parse as Ctrl+Space and Ctrl+Home then unmodified Space, with all modifiers released; no input sent.'

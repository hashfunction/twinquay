# Copyright 2026 Trieflow LLC. MIT. Windows native fixture; macOS UIA topology replay.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
. (Join-Path $PSScriptRoot 'qualify-workflow.ps1')
function Assert($Value,[string]$Message) { if (-not $Value) { throw $Message } }

if (-not $IsWindows) {
    # Replay the actual run34640354182 owner/modal hierarchy through the real
    # production traversal. Only unavailable Windows UIA/native APIs are adapters.
    Add-Type @'
using System;
using System.Collections.Generic;
namespace Windows.Automation {
    public enum TreeScope { Children, Subtree }
    public class PropertyCondition { public int Id; public PropertyCondition(object key,int value) { Id=value; } }
    public class Condition { public static object TrueCondition=new object(); }
    public class Kind { public string ProgrammaticName="ControlType.Window"; }
    public class Info {
        public string Name; public int ProcessId; public bool IsOffscreen=false;
        public bool IsEnabled=true; public object NativeWindowHandle; public Kind ControlType=new Kind();
    }
    public class AutomationElement {
        public static AutomationElement RootElement; public static object ProcessIdProperty=new object();
        public Info Current=new Info(); public List<AutomationElement> Children=new List<AutomationElement>();
        public AutomationElement(string name,int pid,int hwnd) { Current.Name=name;Current.ProcessId=pid;Current.NativeWindowHandle=hwnd; }
        public List<AutomationElement> FindAll(TreeScope scope,object condition) {
            var list=new List<AutomationElement>();
            if(scope==TreeScope.Subtree) list.Add(this);
            foreach(var child in Children) {
                if(scope==TreeScope.Subtree) list.AddRange(child.FindAll(scope,condition));
                else if(!(condition is PropertyCondition) || child.Current.ProcessId==((PropertyCondition)condition).Id) list.Add(child);
            }
            return list;
        }
    }
}
'@
    function Assert-TwinQuayWorkflowProcess($State) { Assert ($State.process.Id -eq 8368) 'Foreign process adapter input.' }
    $script:nativeMode='valid'
    function Get-TwinQuayWorkflowNativeWindow([IntPtr]$Handle) {
        $row=[pscustomobject]@{handle=$Handle;process_id=8368;root=$Handle;visible=$true;enabled=$true;class_name='#32770';title='';control_id=1}
        if($Handle -eq [IntPtr]200){
            switch($script:nativeMode){
                'foreign-native-pid' {$row.process_id=9999}
                'child-hwnd' {$row.root=[IntPtr]100}
                'hidden-native-window' {$row.visible=$false}
            }
        }
        return $row
    }
    $desktop=[Windows.Automation.AutomationElement]::new('desktop',0,1)
    $owner=[Windows.Automation.AutomationElement]::new('TwinQuay',8368,100)
    $modal=[Windows.Automation.AutomationElement]::new('Select a folder to add to the scanning list',8368,200)
    $owner.Children.Add($modal)
    $owner.Children.Add([Windows.Automation.AutomationElement]::new('',8368,0))
    $virtualRow=[Windows.Automation.AutomationElement]::new('virtual result',8368,0)
    $virtualRow.Current.ControlType.ProgrammaticName='ControlType.DataItem'
    $virtualRow.Current.NativeWindowHandle=$null
    $owner.Children.Add($virtualRow)
    $owner.Children.Add([Windows.Automation.AutomationElement]::new('Foreign error',9999,300))
    $desktop.Children.Add($owner)
    [Windows.Automation.AutomationElement]::RootElement=$desktop
    $state=@{process=[pscustomobject]@{Id=8368}}
    $found=Wait-TwinQuayWorkflowWindow $state 'Select a folder to add to the scanning list' 0
    Assert ([object]::ReferenceEquals($found,$modal)) 'Actual modal descendant was not selected.'
    $windows=@(Get-TwinQuayWorkflowWindows $state)
    Assert ($windows.Count -eq 2) 'Foreign, handleless, or virtual result row became an owned native window.'
    $nullWindow=[Windows.Automation.AutomationElement]::new('Unknown window',8368,0)
    $nullWindow.Current.NativeWindowHandle=$null
    $owner.Children.Add($nullWindow)
    $failure=$null;try{Wait-TwinQuayWorkflowWindow $state $modal.Current.Name 0|Out-Null}catch{$failure=$_.Exception.Message}
    Assert ($failure -ceq 'Native window handle is null at window-enumeration (value type: null).') 'A null handle on an actual Window was not an immediate site-identified unknown observation failure.'
    $owner.Children.Remove($nullWindow)|Out-Null
    foreach($script:nativeMode in @('foreign-native-pid','child-hwnd','hidden-native-window')){
        $failure=$null;try{Wait-TwinQuayWorkflowWindow $state $modal.Current.Name 0|Out-Null}catch{$failure=$_.Exception.Message}
        Assert ($failure -match 'Timed out') "Native window boundary accepted $script:nativeMode"
    }
    $script:nativeMode='valid'
    $owner.Children.Add($modal)
    Assert (@(Get-TwinQuayWorkflowWindows $state).Count -eq 2) 'Same HWND from two UIA paths was not deduplicated.'
    $duplicate=[Windows.Automation.AutomationElement]::new($modal.Current.Name,8368,201)
    $owner.Children.Add($duplicate)
    $failure=$null;try{Wait-TwinQuayWorkflowWindow $state $modal.Current.Name 0|Out-Null}catch{$failure=$_.Exception.Message}
    Assert ($failure -match 'Ambiguous') 'Different same-title HWNDs were accepted.'
    $owner.Children.Remove($duplicate)|Out-Null
    $failure=$null;try{Wait-TwinQuayWorkflowWindow $state 'Select a folder' 0|Out-Null}catch{$failure=$_.Exception.Message}
    Assert ($failure -match 'Timed out') 'Title prefix was accepted.'
    $dialog=[pscustomobject]@{handle=[IntPtr]200;root=[IntPtr]200;process_id=8368;visible=$true;enabled=$true;title=$modal.Current.Name;class_name='#32770'}
    $button=[pscustomobject]@{handle=[IntPtr]201;root=[IntPtr]200;process_id=8368;visible=$true;enabled=$true;title='&Select Folder';class_name='Button';control_id=1}
    Assert-TwinQuayNativeDialogButton $dialog $button 8368 $modal.Current.Name 'Select Folder'
    foreach($case in @('foreign-pid','wrong-root','wrong-class','wrong-id','wrong-caption','disabled','hidden','zero-handle','wrong-dialog-title')) {
        $bad=$button|Select-Object *;$badDialog=$dialog|Select-Object *
        switch($case) {
            'foreign-pid' {$bad.process_id=9999}
            'wrong-root' {$bad.root=[IntPtr]300}
            'wrong-class' {$bad.class_name='Pane'}
            'wrong-id' {$bad.control_id=2}
            'wrong-caption' {$bad.title='Cancel'}
            'disabled' {$bad.enabled=$false}
            'hidden' {$bad.visible=$false}
            'zero-handle' {$bad.handle=[IntPtr]::Zero}
            'wrong-dialog-title' {$badDialog.title='Select a folder'}
        }
        $failure=$null;try{Assert-TwinQuayNativeDialogButton $badDialog $bad 8368 $modal.Current.Name 'Select Folder'}catch{$failure=$_.Exception.Message}
        Assert ($failure -match 'IDOK Button identity') "Native action accepted $case"
    }
    Add-TwinQuayActivationTypes # Compile the actual interop; do not call user32 on macOS.
    'PASS: production owner/modal traversal, exact titles, native HWND requirement, foreign PID and duplicate/ambiguous HWND handling.'
    'PASS: exact native dialog/button identity and nine negative variants; production C# interop compiled.'
    'LIMIT: macOS replays the actual native failure topology; Windows executes the real Qt/IFileDialog fixture.'
    exit 0
}

Add-TwinQuayActivationTypes
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes,System.Windows.Forms,System.Drawing
$venvPython=(Resolve-Path (Join-Path $PSScriptRoot '../../.venv/Scripts/python.exe')).Path
# The Windows venv executable may be a redirector that creates a second process.
# Query the executing interpreter image and launch that exact image with only
# this venv's package directory added, retaining the process that owns the UI.
$pythonPaths=@(& $venvPython -c 'import ctypes; b=ctypes.create_unicode_buffer(32768); n=ctypes.windll.kernel32.GetModuleFileNameW(None,b,len(b)); assert n and n<len(b); print(b.value)')
if($LASTEXITCODE -ne 0 -or $pythonPaths.Count -ne 1 -or -not [IO.Path]::IsPathFullyQualified($pythonPaths[0])){throw 'Cannot identify the native fixture interpreter image.'}
$python=(Resolve-Path $pythonPaths[0]).Path
$sitePackages=(Resolve-Path (Join-Path $PSScriptRoot '../../.venv/Lib/site-packages')).Path
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('twinquay-native-chooser-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary -ErrorAction Stop|Out-Null
$process=$null;$handle=$null;$stdout=$null;$stderr=$null;$primary=$null;$exitCode=$null;$processId=$null;$naturalExit=$false
$cleanup=[Collections.Generic.List[string]]::new();$observed=[Collections.Generic.List[object]]::new()
try {
    New-Item -ItemType Directory -Path (Join-Path $temporary 'selected + [folder]')|Out-Null
    $start=[Diagnostics.ProcessStartInfo]::new($python)
    $start.UseShellExecute=$false;$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
    $start.Environment['QT_QPA_PLATFORM']='windows'
    foreach($argument in @('-c','import runpy,sys; sys.path.insert(0,sys.argv[1]); sys.argv=sys.argv[2:]; runpy.run_path(sys.argv[0],run_name="__main__")',$sitePackages,(Join-Path $PSScriptRoot 'native_chooser_fixture.py'),$temporary)){$start.ArgumentList.Add($argument)}
    $candidate=[Diagnostics.Process]::new();$candidate.StartInfo=$start
    try { if(-not $candidate.Start()){throw 'Native fixture failed to start.'};$handle=$candidate.SafeHandle }
    catch { $candidate.Dispose();throw }
    $process=$candidate
    $processId=$process.Id
    $stdout=$process.StandardOutput.ReadToEndAsync();$stderr=$process.StandardError.ReadToEndAsync()
    $state=@{process=$process;processHandle=$handle}
    # This source-method fixture is not packaged. Replace only the installed
    # package check; continue checking the original live handle/executable.
    function Assert-TwinQuayWorkflowProcess($State) {
        Assert ([object]::ReferenceEquals($State.process,$process) -and [object]::ReferenceEquals($State.processHandle,$handle) -and
            -not $handle.IsClosed -and -not $handle.IsInvalid -and -not $process.HasExited) 'Native fixture lost its original live process handle.'
        $process.Refresh()
        Assert ((Get-CanonicalPath $process.MainModule.FileName) -ieq (Get-CanonicalPath $python)) 'Native fixture executable changed.'
    }
    $title='Select a folder to add to the scanning list'
    $dialog=Wait-TwinQuayWorkflowWindow $state $title 15
    $observed.Add((Get-TwinQuayWorkflowNativeWindow ([IntPtr]$dialog.Current.NativeWindowHandle)))
    Set-TwinQuayWorkflowFolder $state $title (Join-Path $temporary 'selected + [folder]')
    $save=Wait-TwinQuayWorkflowWindow $state 'Save selected cleanup plan' 15
    $observed.Add((Get-TwinQuayWorkflowNativeWindow ([IntPtr]$save.Current.NativeWindowHandle)))
    Send-TwinQuayWorkflowKeys $state $save '%n^a'
    Send-TwinQuayWorkflowKeys $state $save (ConvertTo-TwinQuaySendKeysLiteral (Join-Path $temporary 'selected + [plan].json'))
    Press-TwinQuayNativeDialogButton $state $save 'Save'
    Assert ($process.WaitForExit(10000)) 'Source chooser fixture did not exit.'
    $naturalExit=$true;$exitCode=$process.ExitCode
    Assert ($process.ExitCode -eq 0) 'Source chooser fixture exited unsuccessfully.'
    $result=$stdout.GetAwaiter().GetResult()|ConvertFrom-Json
    Assert ($result.source_methods_completed -eq 2) 'Real source chooser methods did not complete.'
    Assert ((Get-CanonicalPath $result.selected[0]) -ieq (Get-CanonicalPath (Join-Path $temporary 'selected + [folder]'))) 'Wrong selected folder.'
    Assert ((Get-CanonicalPath $result.saved) -ieq (Get-CanonicalPath (Join-Path $temporary 'selected + [plan].json'))) 'Wrong saved plan.'
} catch { $primary=$_.Exception.ToString() }
finally {
    if($process) {
        try { if(-not $process.HasExited){$process.Kill();Assert ($process.WaitForExit(10000)) 'Owned fixture cleanup did not finish.'} }
        catch {$cleanup.Add($_.Exception.ToString())}
    }
    $out=$null;$err=$null
    try { if($stdout -and $stdout.Wait(2000)){$out=$stdout.GetAwaiter().GetResult()};if($stderr -and $stderr.Wait(2000)){$err=$stderr.GetAwaiter().GetResult()} }
    catch {$cleanup.Add($_.Exception.ToString())}
    if($process){try{$process.Dispose()}catch{$cleanup.Add($_.Exception.ToString())}}
    try{Remove-Item -LiteralPath $temporary -Recurse -Force}catch{$cleanup.Add($_.Exception.ToString())}
}
$report=[ordered]@{passed=(-not $primary -and $cleanup.Count -eq 0);primary_error=$primary;cleanup_errors=@($cleanup);
    scope='Actual source Qt/IFileDialog methods and real Windows HWND/input APIs; external fixture has no package identity';
    process_id=$processId;executable=$python;exit_code=$exitCode;natural_exit=$naturalExit;
    windows=@($observed);stdout=$out;stderr=$err}
$evidence=Join-Path $PSScriptRoot '../../build-evidence'
[IO.Directory]::CreateDirectory($evidence)|Out-Null
try {Write-NewUtf8Json (Join-Path $evidence 'native-chooser-test.json') $report}
catch {throw ('Native fixture reporting failed: '+$_.Exception.Message+'; retained result: '+($report|ConvertTo-Json -Depth 10 -Compress))}
if(-not $report.passed){throw ($report|ConvertTo-Json -Depth 10 -Compress)}
'PASS: actual Windows source folder/save methods, exact modal HWND/PID, native IDOK focus/keyboard and normal exit.'

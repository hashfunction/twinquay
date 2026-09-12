# Copyright 2026 Trieflow LLC. MIT. Capture the unchanged, already-qualified Store package.
param([Parameter(Mandatory)][string]$Inputs,[Parameter(Mandatory)][string]$QualifiedSource,[Parameter(Mandatory)][string]$CaptureOutput)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $QualifiedSource 'tools/msix/qualify-msix-install.ps1') -LibraryOnly
. (Join-Path $PSScriptRoot 'capture_helpers.ps1')
. (Join-Path $PSScriptRoot 'capture_adapter.ps1')
. (Join-Path $PSScriptRoot 'display_modes.ps1')
if (-not $IsWindows -or $env:CI -cne 'true' -or $env:GITHUB_REPOSITORY -cne 'hashfunction/twinquay') {throw 'Requires isolated DupliSift Windows CI.'}
Import-Module Appx -UseWindowsPowerShell -ErrorAction Stop
$inputRoot=(Resolve-Path -LiteralPath $Inputs).Path;$qualified=(Resolve-Path -LiteralPath $QualifiedSource).Path
$python=@(Get-Command python -CommandType Application)[0].Source
Invoke-CheckedNative $python @((Join-Path $PSScriptRoot 'capture_checks.py'),'--inputs',$inputRoot,'--qualified-source',$qualified)
$output=[IO.Path]::GetFullPath($CaptureOutput)
if (Test-Path -LiteralPath $output) {throw 'Capture output exists; replacement refused.'}
New-Item -ItemType Directory -Path $output | Out-Null;Assert-NoReparsePath $output
[IO.File]::Copy((Join-Path $inputRoot 'capture-inputs.json'),(Join-Path $output 'capture-inputs.json'),$false)
$recordPath=Join-Path $inputRoot 'metadata/msix-store-package-record.json'
$record=Get-Content -LiteralPath $recordPath -Raw|ConvertFrom-Json
Assert-TwinQuayIdentityRecord $record 'store'
$state=[ordered]@{record=$record;package=(Join-Path $inputRoot 'store/DupliSift_1.0.1.0_x64.msix');temporary=$null;certificate=$null;trustAttempted=$false;
    workflowProfile=$null;profileRemoved=$false;installed=$null;installedByUs=$false;installAttempted=$false;addCompleted=$false;ownedPackageFullName=$null;
    process=$null;processOwned=$false;brokerProcessId=0;processShutdownVerified=$false;driver=$null;processExit=$null;cleanupProcessExit=$null;
    qualified=$qualified;output=$output;workflow=$null;executableSha256=$null;processHandle=$null;demo=$null;demoRemoved=$false;expectedTitle='DupliSift';normalClose=$false;uninstallVerified=$false;residualPackageFullNames=@();cleanupErrors=[Collections.Generic.List[string]]::new();
    displayOriginalMode=$null;displayDevice=$null;displayRestoreRequired=$false;displayEvidence=$null}
$expectedHash='bf0ec697fd0eab1517c1ca42c530cb46fc057454ab74acbff1c05feb64d44ae7'
$fullName='1659hashfunction.TwinQuay_1.0.1.0_x64__r3hxytd7jt6c4'
$primary=$null;$unsignedUnchanged=$false
try {
    foreach ($profile in @((Join-Path $env:LOCALAPPDATA 'TwinQuay'),'C:\Demo')) {
        if (Test-Path -LiteralPath $profile) {throw 'Existing current or legacy profile must be preserved.'}
    }
    if (@(Get-AppxPackage -Name '1659hashfunction.TwinQuay' -ErrorAction Stop).Count) {throw 'Existing DupliSift registration preserved.'}
    Start-MarketingDisplay $state
    $temporary=Join-Path $env:RUNNER_TEMP ('.duplisift-capture-'+[guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $temporary | Out-Null;$state.temporary=$temporary
    $state.workflowProfile=New-DupliCaptureDirectory (Join-Path $env:LOCALAPPDATA 'TwinQuay')
    $state.demo=New-DupliCaptureDirectory 'C:\Demo'
    $signTool=Join-Path ${env:ProgramFiles(x86)} 'Windows Kits/10/bin/10.0.26100.0/x64/signtool.exe'
    $toolHash=(Get-FileHash -LiteralPath $signTool -Algorithm SHA256).Hash
    $signed=Join-Path $temporary 'DupliSift.capture.signed.msix'
    [IO.File]::Copy($state.package,$signed,$false)
    $state.certificate=New-SelfSignedCertificate -Type Custom -KeyUsage DigitalSignature -KeyExportPolicy NonExportable -KeySpec Signature `
        -CertStoreLocation 'Cert:\CurrentUser\My' -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3','2.5.29.19={text}') `
        -Subject 'CN=B6A2631A-FD32-45CC-AE12-82466975F528' -FriendlyName 'DupliSift ephemeral marketing capture' -NotAfter (Get-Date).AddHours(2)
    $public=Join-Path $temporary 'capture-public.cer'
    Export-Certificate -Cert $state.certificate -FilePath $public | Out-Null
    $state.trustAttempted=$true;Import-Certificate -FilePath $public -CertStoreLocation 'Cert:\LocalMachine\TrustedPeople' | Out-Null
    Invoke-CheckedNative $signTool @('sign','/fd','SHA256','/sha1',$state.certificate.Thumbprint,'/s','My',$signed)
    Invoke-CheckedNative $signTool @('verify','/pa','/all','/v',$signed)
    $signature=Get-AuthenticodeSignature -LiteralPath $signed
    if ($signature.Status -ne [Management.Automation.SignatureStatus]::Valid -or $signature.SignerCertificate.Thumbprint -cne $state.certificate.Thumbprint -or
        (Get-FileHash -LiteralPath $signTool -Algorithm SHA256).Hash -cne $toolHash -or
        (Get-FileHash -LiteralPath $state.package -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expectedHash) {throw 'Capture signing source/tool/certificate integrity differs.'}
    $state.installAttempted=$true
    Add-AppxPackage -Path $signed -ErrorAction Stop;$state.addCompleted=$true
    $matches=@(Get-AppxPackage -Name '1659hashfunction.TwinQuay' -ErrorAction Stop)
    if ($matches.Count -ne 1 -or $matches[0].PackageFullName -cne $fullName -or
        $matches[0].Publisher -cne 'CN=B6A2631A-FD32-45CC-AE12-82466975F528' -or
        $matches[0].PackageFamilyName -cne '1659hashfunction.TwinQuay_r3hxytd7jt6c4') {throw 'Installed capture registration differs; ownership unproven.'}
    $state.installed=$matches[0];$state.installedByUs=$true;$state.ownedPackageFullName=$fullName
    foreach ($row in $record.payload.PSObject.Properties) {$null=Assert-FileMatchesRecord (Join-Path $state.installed.InstallLocation $row.Name) $row.Value $row.Name}
    Add-TwinQuayActivationTypes
    $state.brokerProcessId=[int][TwinQuayQualification.ActivationBroker]::Activate('1659hashfunction.TwinQuay_r3hxytd7jt6c4!TwinQuay')
    $state.process=[Diagnostics.Process]::GetProcessById($state.brokerProcessId);$state.processHandle=$state.process.SafeHandle
    Assert-DupliCaptureProcess $state.process $state.installed.InstallLocation $record;$state.processOwned=$true
    $state.executableSha256=(Get-RecordPayloadEntry $record 'DupliSift.exe').sha256
    $deadline=[DateTime]::UtcNow.AddSeconds(30)
    do {$state.process.Refresh();if($state.process.HasExited){throw 'Capture consumer exited during startup.'};Start-Sleep -Milliseconds 200}
    until (($state.process.MainWindowHandle -ne 0 -and $state.process.MainWindowTitle -ceq $state.expectedTitle) -or [DateTime]::UtcNow -ge $deadline)
    if ($state.process.MainWindowHandle -eq 0 -or $state.process.MainWindowTitle -cne $state.expectedTitle) {throw ('Actual window title differs: '+$state.process.MainWindowTitle)}
    Write-NewUtf8Json (Join-Path $output 'loaded-modules.json') (Get-DupliCaptureModules $state)
    Write-NewUtf8Json (Join-Path $output 'native-window.json') (Set-DupliCaptureWindow $state)
    Invoke-DupliCaptureWorkflow $state $python
    foreach ($name in @('01-scan-results','02-review-quarantine-plan','03-restore-complete')) {
        $frame=Get-Content -LiteralPath (Join-Path $output ($name+'.json')) -Raw|ConvertFrom-Json
        if ($frame.process_id -ne $state.process.Id -or $frame.qualified_source_commit -cne $record.sourceCommit -or
            $frame.package_full_name -cne $state.ownedPackageFullName -or $frame.pixel_manipulation -ne $false) {throw 'Native screenshot receipt identity differs.'}
        $null=Assert-FileMatchesRecord (Join-Path $output ($name+'.png')) $frame.png 'Unaltered native screenshot'
    }
    Write-NewUtf8Json (Join-Path $output 'loaded-modules-after-capture.json') (Get-DupliCaptureModules $state)
    Assert-DupliCaptureProcess $state.process $state.installed.InstallLocation $record
    Close-TwinQuayWorkflowWindow $state
    $state.processExit=Get-TwinQuayProcessExitEvidence $state.process 15000
    if (-not $state.processExit.normal_exit) {throw 'Captured DupliSift did not close normally with zero exit.'}
    $state.normalClose=$true;$state.processShutdownVerified=$true
    Remove-AppxPackage -Package $state.ownedPackageFullName -ErrorAction Stop
    if (@(Get-AppxPackage -Name '1659hashfunction.TwinQuay' -ErrorAction Stop).Count) {throw 'Registration remains after normal uninstall.'}
    $state.uninstallVerified=$true
} catch {$primary=$_.Exception.Message}
finally {
    Complete-DupliCaptureCleanup $state
    try {Restore-MarketingDisplay $state}catch {$state.cleanupErrors.Add('display: '+$_.Exception.Message)}
    if ($state.displayEvidence) {Write-NewUtf8Json (Join-Path $output 'native-display.json') $state.displayEvidence}
    try {$unsignedUnchanged=(Get-FileHash -LiteralPath $state.package -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $expectedHash}catch {$state.cleanupErrors.Add('Original unsigned package cannot be rechecked.')}
    $captured=(-not $primary -and $state.cleanupErrors.Count -eq 0 -and $state.normalClose -and $state.uninstallVerified -and $state.profileRemoved -and $state.demoRemoved -and $unsignedUnchanged)
    Write-NewUtf8Json (Join-Path $output 'capture-result.json') @{schema_version=1;purpose='real native marketing screenshots only';captured=$captured;
        consumer_acceptance=$false;installation_qualification_claimed=$false;product_binary_changed=$false;submission_changed=$false;
        capture_source_commit=$env:GITHUB_SHA;capture_run_id=$env:GITHUB_RUN_ID;capture_run_attempt=$env:GITHUB_RUN_ATTEMPT;
        qualified_source_commit='73f3842a2cc81aa3c69a5873a262517eae35b6f4';qualified_run_id='34683417158';original_unsigned_sha256=$expectedHash;
        original_unsigned_unchanged=$unsignedUnchanged;certificate_private_key_exported=$false;package_full_name=$state.ownedPackageFullName;
        normal_close_verified=$state.normalClose;process_exit=$state.processExit;cleanup_process_exit=$state.cleanupProcessExit;uninstall_verified=$state.uninstallVerified;
        workflow_profile_removed=$state.profileRemoved;demo_removed=$state.demoRemoved;residual_package_full_names=$state.residualPackageFullNames;primary_error=$primary;cleanup_errors=@($state.cleanupErrors);
        captured_at_utc=[DateTime]::UtcNow.ToString('o')}
    foreach ($process in @($state.driver,$state.process)) {if($process){$process.Dispose()}}
}
if (-not $captured) {throw "Native marketing capture incomplete: $primary; cleanup: $($state.cleanupErrors -join '; ')"}
Write-Output 'Captured three real DupliSift screens and completed normal close/uninstall/owned profile and demo cleanup. Capture only.'

# Copyright 2026 Trieflow LLC. MIT. Real files/collector; platform metadata boundaries modeled.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
function Check($Value,[string]$Message) { if (-not $Value) { throw $Message } }
function Reject($Action,[string]$Pattern) {
    $failure=$null
    try { & $Action | Out-Null } catch { $failure=$_.Exception.Message }
    Check ($failure -match $Pattern) "Expected $Pattern, observed $failure"
}
$temporaryBase=if ($IsMacOS) { '/private/tmp' } else { [IO.Path]::GetTempPath() }
$fixture=Join-Path $temporaryBase ('duplisift-text-input-'+[guid]::NewGuid().ToString('N'))
$common=Join-Path $fixture 'Common Files'
$script:expected=Join-Path $common 'microsoft shared/ink/tiptsf.dll'
$script:status='Valid';$script:subject='CN=Microsoft Windows Publisher, O=Microsoft Corporation, C=US'
$script:version=[pscustomobject]@{OriginalFilename='tiptsf.dll';CompanyName='Microsoft Corporation';ProductName='Windows fixture';FileDescription='Text input fixture';FileVersion='10.0.26100.1'}
$script:mutation=''
function Get-TwinQuayWindowsTextInputPath { return $script:expected }
function Read-TwinQuayModuleVersionInfo([string]$Path) {
    Check ($Path -ceq $script:expected) 'Metadata read outside the exact module.'
    return $script:version
}
function Get-AuthenticodeSignature([string]$LiteralPath) {
    if ($script:mutation -ceq 'bytes') { [IO.File]::WriteAllText($LiteralPath,('x'*(Get-Item $LiteralPath).Length)) }
    if ($script:mutation -ceq 'link') {
        Move-Item (Split-Path $LiteralPath) $script:signatureTarget
        $kind=if ($IsWindows) { 'Junction' } else { 'SymbolicLink' }
        New-Item -ItemType $kind -Path (Split-Path $LiteralPath) -Target $script:signatureTarget | Out-Null
    }
    return [pscustomobject]@{Status=$script:status;SignerCertificate=[pscustomobject]@{
        Subject=$script:subject;SubjectName=[Security.Cryptography.X509Certificates.X500DistinguishedName]::new($script:subject);
        Issuer='Fixture authority';Thumbprint=('A'*40)}}
}
$previousSystemRoot=$env:SystemRoot
New-Item -ItemType Directory -Path (Split-Path $script:expected) -Force | Out-Null
[IO.File]::WriteAllText($script:expected,'fixture DLL bytes; not a signed Windows file')
try {
    $record=Get-VerifiedWindowsTextInputModuleEvidence $script:expected
    Check ($record.sha256 -ceq (Get-FileHash $script:expected).Hash.ToLowerInvariant() -and
        $record.original_filename -ceq 'tiptsf.dll' -and $record.company_name -ceq 'Microsoft Corporation' -and
        $record.file_version -ceq '10.0.26100.1') 'Exact file/metadata evidence lost.'
    foreach ($name in @('Microsoft Corporation','Microsoft Windows')) {
        $script:subject='CN='+$name+', O=Microsoft Corporation, C=US'
        Check ((Get-VerifiedWindowsTextInputModuleEvidence $script:expected).signer_common_name -ceq $name) 'Valid parsed Microsoft signer rejected.'
    }
    $script:subject='CN=Microsoft Windows Publisher, O=Microsoft Corporation, C=US'
    foreach ($script:status in @('NotSigned','HashMismatch','NotTrusted','UnknownError')) {
        Reject { Get-VerifiedWindowsTextInputModuleEvidence $script:expected } 'valid Microsoft'
    }
    $script:status='Valid'
    foreach ($script:subject in @('CN=Unrelated, O=Microsoft Corporation, C=US','CN=Microsoft Windows Publisher, O=Other, C=US',
        'CN=Other, O=Other, OU="CN=Microsoft Windows Publisher, O=Microsoft Corporation", C=US',
        'CN=Microsoft Windows Publisher+OU=Other, O=Microsoft Corporation, C=US',
        'CN=Microsoft Windows Publisher, CN=Other, O=Microsoft Corporation, C=US',
        'CN=Microsoft Windows Publisher, O=Microsoft Corporation, O=Other, C=US')) {
        Reject { Get-VerifiedWindowsTextInputModuleEvidence $script:expected } 'Microsoft signer'
    }
    $script:subject='CN=Microsoft Windows Publisher, O=Microsoft Corporation, C=US'
    $script:version.OriginalFilename='TIPTSF.DLL'
    Check ((Get-VerifiedWindowsTextInputModuleEvidence $script:expected).original_filename -ceq 'TIPTSF.DLL') 'Windows filename case rejected.'
    $script:version.OriginalFilename='TipTsf.dll.mui'
    Check ((Get-VerifiedWindowsTextInputModuleEvidence $script:expected).original_filename -ceq 'TipTsf.dll.mui') 'Observed Windows localized version identity rejected.'
    foreach ($name in @('kernel32.dll','kernel32.dll.mui','tiptsf.dll.fake','tiptsf.dll.mui.fake','')) {
        $script:version.OriginalFilename=$name
        Reject { Get-VerifiedWindowsTextInputModuleEvidence $script:expected } 'version identity'
    }
    $script:version.OriginalFilename='tiptsf.dll';$script:version.CompanyName='Microsoft Corporation Fake'
    Reject { Get-VerifiedWindowsTextInputModuleEvidence $script:expected } 'version identity'
    $script:version.CompanyName='Microsoft Corporation';$script:version.FileDescription='x'*1025
    Reject { Get-VerifiedWindowsTextInputModuleEvidence $script:expected } 'metadata bound'
    $script:version.FileDescription='Text input fixture'
    foreach ($relative in @('microsoft shared/ink/other.dll','microsoft shared/ink/nested/tiptsf.dll','microsoft shared/ink2/tiptsf.dll','../Common Files Fake/microsoft shared/ink/tiptsf.dll')) {
        $path=Join-Path $common $relative
        New-Item -ItemType Directory -Path (Split-Path $path) -Force | Out-Null
        [IO.File]::WriteAllText($path,'other DLL')
        Reject { Get-VerifiedWindowsTextInputModuleEvidence $path } 'exact Windows text input path'
    }
    # Windows component-store files can have multiple hard-link names while
    # remaining regular files. The exact allowed path and byte checks still apply.
    $hardLink=Join-Path $fixture 'component-store-alias.dll'
    New-Item -ItemType HardLink -Path $hardLink -Target $script:expected | Out-Null
    Check ((Get-Item -LiteralPath $script:expected).LinkType -ceq 'HardLink') 'Fixture did not create a real hard link.'
    $linked=Get-VerifiedWindowsTextInputModuleEvidence $script:expected
    Check ($linked.filesystem_link_type -ceq 'HardLink' -and
        $linked.sha256 -ceq (Get-FileHash $hardLink).Hash.ToLowerInvariant()) 'Regular hard-linked platform bytes lost provenance.'
    Reject { Get-VerifiedWindowsTextInputModuleEvidence $hardLink } 'exact Windows text input path'
    Remove-Item -LiteralPath $hardLink
    $script:mutation='bytes'
    Reject { Get-VerifiedWindowsTextInputModuleEvidence $script:expected } 'changed during'
    $script:mutation=''
    $script:signatureTarget=Join-Path $fixture 'signature-target'
    $script:mutation='link'
    Reject { Get-VerifiedWindowsTextInputModuleEvidence $script:expected } 'Reparse point'
    $script:mutation=''
    Remove-Item -LiteralPath (Split-Path $script:expected)
    Move-Item $script:signatureTarget (Split-Path $script:expected)
    $savedFile=Join-Path $fixture 'saved-module'
    Move-Item $script:expected $savedFile
    New-Item -ItemType Directory $script:expected | Out-Null
    Reject { Get-VerifiedWindowsTextInputModuleEvidence $script:expected } 'regular non-reparse file'
    Remove-Item -LiteralPath $script:expected
    Move-Item $savedFile $script:expected
    $real=Join-Path $fixture 'real'
    Move-Item (Split-Path $script:expected) $real
    $linkType=if ($IsWindows) { 'Junction' } else { 'SymbolicLink' }
    New-Item -ItemType $linkType -Path (Split-Path $script:expected) -Target $real | Out-Null
    Reject { Get-VerifiedWindowsTextInputModuleEvidence $script:expected } 'Reparse point'
    Remove-Item -LiteralPath (Split-Path $script:expected)
    Move-Item $real (Split-Path $script:expected)
    Write-Output 'PASS: exact path, three Microsoft signers, filename/company identity, bounded metadata, mutation and reparse rejection.'

    # Exercise the real module collector. Only the Defender call is adapted to
    # identify routing; its full actual helper regression remains separate.
    $script:defenderCalls=[Collections.Generic.List[string]]::new()
    function Get-VerifiedDefenderModuleEvidence([string]$Path,[string]$PlatformRoot) {
        $script:defenderCalls.Add($Path)
        if ([IO.Path]::GetFileName($Path) -cne 'MpOav.dll') { throw 'existing Defender policy rejected foreign DLL' }
        return @{sha256=(Get-FileHash $Path).Hash.ToLowerInvariant();signature_status='Valid'}
    }
    $package=Join-Path $fixture 'package';$env:SystemRoot=Join-Path $fixture 'Windows'
    New-Item -ItemType Directory -Path $package,$env:SystemRoot | Out-Null
    $exe=Join-Path $package 'DupliSift.exe';[IO.File]::WriteAllText($exe,'owned exe')
    $os=Join-Path $env:SystemRoot 'kernel32.dll';[IO.File]::WriteAllText($os,'Windows fixture')
    $defender=Join-Path $fixture 'MpOav.dll';[IO.File]::WriteAllText($defender,'Defender fixture')
    $state=@{installed=@{InstallLocation=$package};record=[pscustomobject]@{
        runtime=[pscustomobject]@{exe='DupliSift.exe'};payload=[pscustomobject]@{'DupliSift.exe'=@{bytes=(Get-Item $exe).Length;sha256=(Get-FileHash $exe).Hash.ToLowerInvariant()}}};
        process=[pscustomobject]@{Modules=@($exe,$os,$defender,$script:expected | ForEach-Object { [pscustomobject]@{FileName=$_;ModuleName=[IO.Path]::GetFileName($_)} })}}
    $modules=@(Get-TwinQuayInstalledModuleEvidence $state)
    Check ($modules.Count -eq 4 -and $modules[3].origin -ceq 'microsoft_windows_text_input_signed_platform' -and
        $modules[2].origin -ceq 'microsoft_defender_signed_platform' -and $script:defenderCalls.Count -eq 1 -and
        $modules[3].platform_signature.original_filename -ceq 'tiptsf.dll') 'Module evidence origin or Defender routing changed.'
    $script:status='NotTrusted'
    Reject { Get-TwinQuayInstalledModuleEvidence $state } 'failed the external-platform policy.*valid Microsoft'
    $script:status='Valid'
    $foreign=Join-Path $common 'microsoft shared/ink/other.dll'
    $state.process.Modules[3]=[pscustomobject]@{FileName=$foreign;ModuleName='other.dll'}
    Reject { Get-TwinQuayInstalledModuleEvidence $state } 'existing Defender policy rejected foreign DLL'
    Check ($script:defenderCalls.Contains((Get-CanonicalPath $foreign))) 'Other Common Files DLL bypassed unchanged external handling.'
    $foreign=Get-CanonicalPath (Join-Path $common '../Common Files Fake/microsoft shared/ink/tiptsf.dll')
    $state.process.Modules[3]=[pscustomobject]@{FileName=$foreign;ModuleName='tiptsf.dll'}
    Reject { Get-TwinQuayInstalledModuleEvidence $state } 'existing Defender policy rejected foreign DLL'
    Check ($script:defenderCalls.Contains($foreign)) 'Same basename outside exact native path bypassed unchanged external handling.'
    $state.process.Modules=@($state.process.Modules[1])
    Reject { Get-TwinQuayInstalledModuleEvidence $state } 'did not load required packaged'
    Write-Output 'PASS: real collector assigns distinct text-input origin, retains Defender routing and rejects other foreign DLLs/missing runtime.'
} finally {
    $env:SystemRoot=$previousSystemRoot
    Remove-Item -LiteralPath $fixture -Recurse -Force
}

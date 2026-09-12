# Copyright 2026 Trieflow LLC. MIT. Read-only original/staged native file evidence.
param([string]$InputPath,[string]$OutputPath,[switch]$LibraryOnly)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function ConvertTo-TwinQuayCertificateEvidence($Certificate) {
    if($null -eq $Certificate){return $null}
    return [ordered]@{subject=$Certificate.Subject;issuer=$Certificate.Issuer;serial_number=$Certificate.SerialNumber;
        thumbprint=$Certificate.Thumbprint;not_before_utc=$Certificate.NotBefore.ToUniversalTime().ToString('o');
        not_after_utc=$Certificate.NotAfter.ToUniversalTime().ToString('o')}
}
function ConvertTo-TwinQuaySignatureEvidence($Signature) {
    return [ordered]@{status=$Signature.Status.ToString();status_message=$Signature.StatusMessage;
        signature_type=$Signature.SignatureType.ToString();is_os_binary=$Signature.IsOSBinary;
        signer_certificate=(ConvertTo-TwinQuayCertificateEvidence $Signature.SignerCertificate);
        timestamp_certificate=(ConvertTo-TwinQuayCertificateEvidence $Signature.TimeStamperCertificate)}
}
function Get-TwinQuayNativeMetadata($Request) {
    if($Request.schema_version -ne 1 -or $Request.files.Count -lt 1 -or $Request.files.Count -gt 1024){throw 'Invalid native metadata request schema/count.'}
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($inputFile in $Request.files) {
        if(-not [IO.Path]::IsPathFullyQualified($inputFile.path) -or $inputFile.sha256 -cnotmatch '^[a-f0-9]{64}$' -or
            -not $seen.Add([IO.Path]::GetFullPath($inputFile.path))){throw 'Invalid or duplicate native metadata path/hash.'}
        $item=Get-Item -LiteralPath $inputFile.path -Force -ErrorAction Stop
        if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Native metadata input is not a regular file.'}
        if((Get-FileHash -LiteralPath $inputFile.path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant() -cne $inputFile.sha256){throw 'Native metadata input bytes changed before observation.'}
    }
    $records=[Collections.Generic.List[object]]::new()
    foreach($inputFile in $Request.files) {
        $path=$inputFile.path
        $version=[Diagnostics.FileVersionInfo]::GetVersionInfo($path)
        $signature=Get-AuthenticodeSignature -LiteralPath $path -ErrorAction Stop
        $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
        if($hash -cne $inputFile.sha256){throw 'Native metadata input bytes changed during observation.'}
        $records.Add([ordered]@{path=$path;sha256=$hash;
            version=[ordered]@{file_version=$version.FileVersion;product_version=$version.ProductVersion;
                original_filename=$version.OriginalFilename;internal_name=$version.InternalName;
                company_name=$version.CompanyName;product_name=$version.ProductName;file_description=$version.FileDescription;
                legal_copyright=$version.LegalCopyright;legal_trademarks=$version.LegalTrademarks;language=$version.Language};
            authenticode=(ConvertTo-TwinQuaySignatureEvidence $signature)})
    }
    return [ordered]@{schema_version=1;platform='Windows';powershell_version=$PSVersionTable.PSVersion.ToString();
        os_version=[Environment]::OSVersion.VersionString;files=@($records)}
}
if($LibraryOnly){return}
if(-not $IsWindows -or $PSVersionTable.PSVersion.Major -lt 7){throw 'Native Authenticode metadata requires Windows and PowerShell 7.'}
if(-not $InputPath -or -not $OutputPath -or (Test-Path -LiteralPath $OutputPath)){throw 'Expected request path and a new metadata output path.'}
if((Get-Item -LiteralPath $InputPath -ErrorAction Stop).Length -gt 1048576){throw 'Metadata request exceeds bound.'}
$request=[IO.File]::ReadAllText($InputPath)|ConvertFrom-Json
$record=Get-TwinQuayNativeMetadata $request
# No output is created until every requested native observation succeeds.
$stream=[IO.File]::Open($OutputPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try {
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($record|ConvertTo-Json -Depth 10)+"`n")
    $stream.Write($bytes,0,$bytes.Length)
} finally {$stream.Dispose()}

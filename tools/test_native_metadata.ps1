# Copyright 2026 Trieflow LLC. MIT. Exercises the production collector at OS APIs.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'collect-native-metadata.ps1') -LibraryOnly
function Assert($Value,[string]$Message){if(-not $Value){throw $Message}}
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('duplisift-metadata-test-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temporary)|Out-Null
$path=Join-Path $temporary 'native + [input].dll'
try {
    [IO.File]::WriteAllBytes($path,[byte[]]@(77,90,0,0))
    $script:mode='valid';$script:observations=0
    function Get-AuthenticodeSignature {
        param([string]$LiteralPath,[string]$ErrorAction)
        Assert ($LiteralPath -ceq $path -and $ErrorAction -ceq 'Stop') 'Signature API lost literal path or terminating errors.'
        $script:observations++
        if($script:mode -ceq 'error'){throw 'Signature provider failed.'}
        if($script:mode -ceq 'changed'){[IO.File]::AppendAllText($path,'changed')}
        [pscustomobject]@{Status='NotSigned';StatusMessage='No signature';SignatureType='None';IsOSBinary=$false;
            SignerCertificate=$null;TimeStamperCertificate=$null}
    }
    $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    $request=[pscustomobject]@{schema_version=1;files=@([pscustomobject]@{path=$path;sha256=$hash})}
    $record=Get-TwinQuayNativeMetadata $request
    Assert ($record.files.Count -eq 1 -and $record.files[0].sha256 -ceq $hash -and
        $record.files[0].authenticode.status -ceq 'NotSigned' -and $script:observations -eq 1) 'Unsigned input was lost or treated as clearance.'
    foreach($case in @('duplicate','wrong-hash','relative-path','empty','wrong-schema')) {
        $bad=$request|ConvertTo-Json -Depth 5|ConvertFrom-Json
        switch($case){
            'duplicate' {$bad.files=@($bad.files[0],$bad.files[0])}
            'wrong-hash' {$bad.files[0].sha256='f'*64}
            'relative-path' {$bad.files[0].path='native.dll'}
            'empty' {$bad.files=@()}
            'wrong-schema' {$bad.schema_version=2}
        }
        $failure=$null;try{Get-TwinQuayNativeMetadata $bad|Out-Null}catch{$failure=$_.Exception.Message}
        Assert ($failure) "Invalid $case metadata request passed."
    }
    foreach($script:mode in @('error','changed')) {
        $failure=$null;try{Get-TwinQuayNativeMetadata $request|Out-Null}catch{$failure=$_.Exception.Message}
        Assert ($failure -match '(Signature provider failed|changed)') "Provider $script:mode was swallowed."
    }
    $inputPath=Join-Path $temporary 'request.json';$outputPath=Join-Path $temporary 'output.json'
    [IO.File]::WriteAllText($inputPath,($request|ConvertTo-Json -Depth 5))
    $failureText=(& (Get-Process -Id $PID).Path -NoLogo -NoProfile -File (Join-Path $PSScriptRoot 'collect-native-metadata.ps1') -InputPath $inputPath -OutputPath $outputPath 2>&1|Out-String)
    Assert ($LASTEXITCODE -ne 0 -and -not (Test-Path -LiteralPath $outputPath)) 'Production CLI wrote metadata after initialization/input failure.'
    $expected=if($IsWindows){'bytes changed'}else{'requires Windows'}
    Assert ($failureText -match $expected) 'Production CLI failed for an unexpected reason.'
    # Real version extraction and hashing ran above. Catalog/certificate fields
    # are tested through actual production serialization with a public cert.
    $key=[Security.Cryptography.RSA]::Create(2048)
    $certificateRequest=[Security.Cryptography.X509Certificates.CertificateRequest]::new(
        'CN=DupliSift metadata serialization fixture',$key,[Security.Cryptography.HashAlgorithmName]::SHA256,
        [Security.Cryptography.RSASignaturePadding]::Pkcs1)
    $certificate=$certificateRequest.CreateSelfSigned([DateTimeOffset]::UtcNow.AddDays(-1),[DateTimeOffset]::UtcNow.AddDays(1))
    try {
        $signed=ConvertTo-TwinQuaySignatureEvidence ([pscustomobject]@{Status='Valid';StatusMessage='Valid';SignatureType='Catalog';
            IsOSBinary=$true;SignerCertificate=$certificate;TimeStamperCertificate=$certificate})
        Assert ($signed.signature_type -ceq 'Catalog' -and $signed.is_os_binary -and
            $signed.signer_certificate.thumbprint -ceq $certificate.Thumbprint -and
            $signed.timestamp_certificate.subject -ceq $certificate.Subject) 'Catalog/public certificate evidence omitted.'
    } finally {$certificate.Dispose();$key.Dispose()}
} finally {Remove-Item -LiteralPath $temporary -Recurse -Force}
'PASS: production literal-path hashing/version read, signature serialization, five invalid requests, provider failure and input-byte changes.'
'LIMIT: Authenticode API is replayed; actual Windows catalog/version observations require the build collector.'

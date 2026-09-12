# Copyright 2026 Trieflow LLC. MIT. Fixed identity boundaries before installation.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
foreach ($mode in @('qualification','store')) {
    $identity=Get-TwinQuayExpectedIdentity $mode
    $expectedName=if ($mode -eq 'store') {'1659hashfunction.TwinQuay'} else {'Trieflow.TwinQuay.Qualification'}
    if ($identity.packageName -cne $expectedName) {throw 'Wrong exact package name'}
    if ($mode -eq 'store' -and $identity.publisher -cne 'CN=B6A2631A-FD32-45CC-AE12-82466975F528') {throw 'Wrong Store publisher'}
    if ($identity.applicationId -cne 'TwinQuay' -or $identity.executable -cne 'DupliSift.exe' -or $identity.version -cne '1.0.1.0') {throw 'Renamed package lost its fixed activation ID, executable or version'}
    $record=[pscustomobject]@{schemaVersion=1;identityMode=$mode;qualificationIdentityOnly=($mode -eq 'qualification');storeIdentityUsed=($mode -eq 'store');identity=[pscustomobject]$identity;signed=$false;publicRelease=$false;licenseClearanceClaimed=$false;installationQualificationPassed=$false}
    Assert-TwinQuayIdentityRecord $record $mode
    foreach ($field in @('identityMode','qualificationIdentityOnly','storeIdentityUsed','signed','publicRelease','licenseClearanceClaimed','installationQualificationPassed','packageName','publisher','capability','applicationId','executable','version')) {
        $changed= $record | ConvertTo-Json -Depth 10 | ConvertFrom-Json
        if ($field -in @('packageName','publisher','capability','applicationId','executable','version')) {$changed.identity.$field='foreign'}
        elseif ($field -eq 'identityMode') {$changed.$field=if ($mode -eq 'store') {'qualification'} else {'store'}}
        else {$changed.$field=-not $changed.$field}
        $rejected=$false
        try {Assert-TwinQuayIdentityRecord $changed $mode} catch {$rejected=$true}
        if (-not $rejected) {throw "Accepted changed $mode identity record: $field"}
    }
    $opposite=if ($mode -eq 'store') {'qualification'} else {'store'}
    $rejected=$false;try {Assert-TwinQuayIdentityRecord $record $opposite} catch {$rejected=$true}
    if (-not $rejected) {throw 'Accepted opposite caller identity mode'}
}
$rejected=$false;try {Get-TwinQuayExpectedIdentity 'foreign'} catch {$rejected=$true}
if (-not $rejected) {throw 'Accepted arbitrary identity mode'}
Write-Output 'PASS: both fixed identities, 26 changed metadata cases, two cross-mode records and arbitrary-mode refusal.'

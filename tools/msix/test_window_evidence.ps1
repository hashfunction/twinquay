# Copyright 2026 Trieflow LLC. MIT. Observation-policy fixtures, not GUI execution.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'qualify-msix-install.ps1') -LibraryOnly
$good=[ordered]@{ title='TwinQuay'; process_id=123; visible=$true; width=800; height=600;
    screenshot_captured=$true; screenshot_sha256=('a'*64); sampled_colors=50;
    controls=@([ordered]@{name='More Options';control_type='ControlType.Button';enabled=$true;offscreen=$false;process_id=123}) }
Assert-TwinQuayWindowEvidence $good
foreach ($case in @('title','splash','foreign-control','disabled','hidden','no-screenshot','blank-screenshot','small-window')) {
    $probe=$good | ConvertTo-Json -Depth 8 | ConvertFrom-Json -AsHashtable
    switch ($case) {
        title {$probe.title='TwinQuay fatal error'}
        splash {$probe.controls=@()}
        foreign-control {$probe.controls[0].process_id=456}
        disabled {$probe.controls[0].enabled=$false}
        hidden {$probe.controls[0].offscreen=$true}
        no-screenshot {$probe.screenshot_captured=$false}
        blank-screenshot {$probe.sampled_colors=1}
        small-window {$probe.width=50}
    }
    $rejected=$false
    try { Assert-TwinQuayWindowEvidence $probe } catch { $rejected=$true }
    if (-not $rejected) { throw "Invalid observation accepted: $case" }
}
Write-Output 'PASS real window-observation policy: complete fixture and eight negative variants'

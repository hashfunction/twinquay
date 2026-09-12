# Copyright 2026 Trieflow LLC. MIT. Dot-source in a fresh -File capture host.
param([Parameter(Mandatory)][string]$QualifiedSource)
. (Join-Path $QualifiedSource 'tools/msix/qualify-msix-install.ps1') -LibraryOnly
. (Join-Path $PSScriptRoot 'capture_helpers.ps1')
. (Join-Path $PSScriptRoot 'capture_adapter.ps1')
. (Join-Path $PSScriptRoot 'display_modes.ps1')

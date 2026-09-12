# Prepare the corresponding-source publication

`source-release-assets.json` selects **71 verified source archives, 766,583,964 bytes** from the historical acquisition manifest. The cached files were all rehashed successfully on 2026-09-11. The plan deliberately excludes the eight native binary comparison archives. The later official Qt PDF binary comparison archive is also not a source asset. Original notices, build metadata, license references and preparation scripts are contained in the final application source archive instead.

This is the prepared upload inventory. `publication_verified: false` and `final_application_source_added: false` remain accurate until the final modified application archive and every source download have been published and checked. A product rename can change that final application archive, but cannot change an upstream source archive's recorded bytes.

1. Choose the release tag and canonical source page with the final product naming. Use a fixed release, not a moving branch URL. Keep this source release available for as long as required by the binary distribution's chosen GPL/LGPL source-offer route. Supply equivalent source access alongside the binary offer under GPLv3 section 6(d); do not substitute a discretionary email-only request process for that route.
2. Export the final committed application tree, including `LICENSE`, `THIRD-PARTY-NOTICES.txt`, application/extension source, icons and generation inputs, complete locked build scripts, both notice trees, this directory and the tracked freezer spec. Record the exact release commit, archive filename, length and SHA-256. A plain `git archive` of that final commit preserves tracked contents and excludes local environments, private caches and signing material. If public source is produced by the repository's snapshot exporter, retain its mapping back to the audited local commit and validate its complete file inventory. Do not export a stale pre-rename tree.
3. Re-run `materials.py verify` over the existing cache. Upload the exact 71 selected source files directly; no second large TAR or local copy is required. Add the final application archive and a publication manifest containing the final commit and fixed HTTPS download URLs for every asset. The complete QtWebEngine archive supplies the original patched PDFium/Chromium source; the official binary comparison and generated PDF documentation do not substitute for it.
4. Read each public download anonymously over HTTPS, stream its bytes through SHA-256, and compare both length and digest to the local record. Retain URL, final redirected HTTPS URL, measurement and verification time. A release API's asset metadata or a successful HEAD request is insufficient to establish the downloadable bytes. Keep the artifact list restricted to source and notices: no MSIX, executable, original binary wheel, PFX, certificate or key belongs in the source assets.
5. Verify that the final application archive reproduces both prepared notice maps and includes the rebuild/install instructions. The exact original-build records in `original-build-evidence.json` bind PDF and Microsoft analysis to ten library hashes. If any of those files changes in the final package, review the replacement input and update the evidence instead of reusing the previous conclusion.
6. Bind the final current-source native package inventory, both installed qualification receipts, successful owned cleanup and public-source verification to a separate final release receipt. Existing qualification-only flags remain historically accurate. The source publication record alone does not authorize retaining an unsigned Store upload package before the normal installed acceptance gates pass.

Local source verification:

```sh
python distribution/corresponding-source/materials.py verify --cache /path/to/downloads
python distribution/corresponding-source/test_materials.py -v
python distribution/corresponding-source/test_release_notices.py -v
python tools/test_native_notices.py -v
```

For upload automation, read `assets[*].filename` from the plan and invoke the release API/CLI with each corresponding regular cache file after rechecking its recorded length/hash. Do not construct shell code from archive metadata. Record public download verification separately from this acquisition plan. Root coordinates the final commit, source page, release upload and unsigned Store export.

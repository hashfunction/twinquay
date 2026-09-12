# Copyright 2026 Trieflow LLC. MIT.
"""Retain only the unsigned, source-bound Store package after both real lifecycles."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import sys
from datetime import datetime, timezone

import msix_qualification as msix
import source_publication as publication
from source_publication import require
import workflow_files as oracle

STAGES = ['Prepare', 'Scan', 'Review', 'Quarantine', 'Conflict', 'Restore', 'Finish']
SURFACES = ['01-scan-folder', '02-duplicate-results', '03-reviewed-plan', '04-quarantine-complete',
            '05-conflict-receipt', '06-conflict-disclosed', '07-restore-receipt', '08-restore-complete', '09-restored-main']
PACKAGE_NAME = 'DupliSift_1.0.1.0_x64.msix'
CLOSURE = 'distribution/corresponding-source/'


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate release evidence JSON key')
            result[key] = value
        return result
    with msix._regular_stream(path) as stream:
        data = stream.read(16 * 1024 * 1024 + 1)
    require(len(data) <= 16 * 1024 * 1024, 'Oversized release evidence')
    return json.loads(data.decode('utf-8-sig'), object_pairs_hook=unique)


def check_context(value, context):
    require(all(value.get(key) == expected for key, expected in context.items()),
            'Release evidence differs from current source/run/attempt')


def digest(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def validate_workflow_files(files):
    require(set(files) == {'prepare', 'plan', 'quarantined', 'restore_collision', 'restored'}, 'Incomplete file workflow evidence')
    prepared = files['prepare']
    base = PureWindowsPath(prepared['root'])
    require(base.is_absolute() and prepared['input'] == str(base / 'Project Documents')
            and prepared['quarantine'] == str(base / 'Review Copies'), 'Workflow fixture paths changed')
    original = str(base / 'Project Documents/Cedar House Brief.txt')
    duplicate = str(base / 'Project Documents/Cedar House Brief - emailed.txt')
    control = str(base / 'Project Documents/Cedar House Site Notes.txt')
    expected = {original: digest(oracle.PAIR_BYTES), duplicate: digest(oracle.PAIR_BYTES), control: digest(oracle.CONTROL_BYTES)}
    require(prepared['collision'] == digest(oracle.COLLISION_BYTES), 'Collision fixture bytes changed')

    def check_rows(rows, wanted):
        require(isinstance(rows, list) and len(rows) == len(wanted), 'Unexpected workflow file set')
        actual = {row['path']: {key: row[key] for key in ('bytes', 'sha256')} for row in rows}
        require(len(actual) == len(rows) and actual == wanted, 'Workflow exact file bytes changed')

    check_rows(prepared['files'], expected)
    plan = files['plan']['plan']
    require(files['plan']['candidate_count'] == 1 and len(plan['candidates']) == 1, 'Expected one reviewed duplicate')
    candidate = plan['candidates'][0]
    require(candidate['path'] == duplicate and candidate['reference_path'] == original
            and candidate['evidence'] == 'exact_content', 'Reviewed exact-content reference changed')
    check_rows(files['plan']['files'], expected)
    for status in ('quarantined', 'restore_collision', 'restored'):
        result = files[status]
        require(result['status'] == status and result['receipt']['plan'] == plan
                and result['receipt_path'] == files['plan']['receipt_path'], 'Workflow receipt/plan/status changed')
        items = result['receipt']['items']
        require(len(items) == 1, 'Expected exactly one receipt item')
        item = items[0]
        require(item['status'] == status and item['original_path'] == duplicate
                and item['name'] == PureWindowsPath(duplicate).name
                and item['size'] == len(oracle.PAIR_BYTES) and item['sha256'] == digest(oracle.PAIR_BYTES)['sha256'],
                'Receipt does not bind the original duplicate bytes')
        payload = str(base / 'Review Copies' / plan['plan_id'] / 'payload' / item['item_id'] / item['name'])
        wanted = {original: expected[original], control: expected[control]}
        if status == 'restored': wanted[duplicate] = expected[duplicate]
        else: wanted[payload] = expected[duplicate]
        if status == 'restore_collision':
            wanted[duplicate] = digest(oracle.COLLISION_BYTES)
            require(item['detail'] == 'Original path is occupied; existing file was kept.', 'Collision was not disclosed')
        check_rows(result['files'], wanted)


def validate_installation(folder, record, source, context, mode):
    install = load(folder / 'installation-qualification.json')
    check_context(install, context)
    require(install.get('identity') == msix.identity_for_mode(mode) == record['identity']
            and install.get('identity_mode') == mode
            and install.get('qualification_identity_only') is (mode == 'qualification')
            and install.get('store_identity_used') is (mode == 'store'), 'Installation identity mode changed')
    for key in ('add_appx_completed', 'registration_ownership_established', 'unsigned_package_unchanged',
                'process_identity_ownership_established', 'clean_close_verified', 'uninstall_verified',
                'installation_qualification_passed', 'workflow_acceptance', 'cleanup_restore_workflow_tested',
                'duplicate_scanning_tested'):
        require(install.get(key) is True, 'Installed release gate failed: ' + key)
    require(install.get('primary_error') is None and install.get('certificate_private_key_exported') is False,
            'Installation failed or exported a private key')
    for key in ('preflight_package_full_names', 'residual_package_full_names', 'cleanup_errors', 'evidence_errors'):
        require(install.get(key) == [], 'Installation has missing/unclean ownership evidence: ' + key)
    package_full_name = install['package_full_name']
    identity = record['identity']
    require(re.fullmatch(re.escape(identity['packageName']+'_'+identity['version']+'_x64__')+'[a-z0-9]{13}', package_full_name or ''),
            'Installed package full name differs from assigned identity')
    require(all(install.get(key) == package_full_name for key in ('owned_package_full_name', 'activated_process_package_full_name')),
            'Installed/activated package ownership differs')
    require(install['unsigned_package_sha256'] == record['containerVerification']['package']['sha256'], 'Installed unsigned package hash changed')
    executable = record['releaseInput']['DupliSift.exe']['sha256']
    require(install['executable_sha256'] == executable, 'Installed executable differs from staged package')
    workflow = load(folder / 'workflow/workflow.json')
    require(install['workflow'] == workflow, 'Standalone and installed workflow receipts differ')
    check_context(workflow, context)
    require(workflow['package_full_name'] == package_full_name and workflow['executable_sha256'] == executable
            and workflow['process_id'] == install['window']['process_id'] and workflow['process_id'] > 0,
            'Workflow process is not the exact activated package')
    for field in ('process_exit', 'cleanup_process_exit'):
        result = install[field]
        require(result.get('process_id') == workflow['process_id'] and result.get('wait_completed') is True
                and result.get('normal_exit') is True and type(result.get('exit_code')) is int and result['exit_code'] == 0
                and result.get('observation_error') is None, 'Installed process did not close normally')
    result = workflow['result']
    require(result.get('passed') is True and result.get('completed_stages') == STAGES
            and result.get('failed_stage') is None and result.get('primary_error') is None
            and result.get('cleanup_errors') == [] and workflow.get('diagnostic_errors') == [], 'Incomplete real consumer workflow')
    require(workflow.get('source_inputs') == {
        name: msix.file_record(source / 'tools/msix' / name)['sha256']
        for name in ('qualify-workflow.ps1', 'workflow_files.py')}, 'Workflow helper source changed')
    validate_workflow_files(workflow['files'])
    for stage, facts in workflow['files'].items():
        require(load(folder / 'workflow' / (stage+'-files.json')) == facts, 'Standalone file facts differ: ' + stage)
    require([surface['name'] for surface in workflow['surfaces']] == SURFACES, 'Missing real workflow surfaces')
    for surface in workflow['surfaces']:
        require(surface['process_id'] == workflow['process_id'] and surface['native_window']['process_id'] == workflow['process_id']
                and surface['screenshot_error'] is None and surface['surface_geometry']['fully_visible'] is True,
                'Workflow surface is not captured from the owned visible process')
        stem = folder / 'workflow' / surface['name']
        require(load(stem.with_suffix('.json')) == surface, 'Workflow surface facts differ')
        require(msix.file_record(stem.with_suffix('.png'))['sha256'] == surface['screenshot_sha256'], 'Workflow screenshot changed')
    for filename, count_key in (('loaded-modules.json', 'loaded_module_count'), ('loaded-modules-after-workflow.json', 'post_workflow_loaded_module_count')):
        modules = load(folder / filename)
        require(isinstance(modules, list) and len(modules) == install[count_key] and len(modules) > 0, 'Missing installed module evidence')
        package_modules = {}
        executable_rows = [row for row in modules if row.get('origin') == 'package' and str(row.get('relative_path', '')).casefold() == 'duplisift.exe']
        require(len(executable_rows) == 1, 'Expected exactly one owned installed executable module')
        install_root = PureWindowsPath(executable_rows[0]['path']).parent
        require(install_root.is_absolute() and install_root.name == package_full_name and install_root.parent.name.casefold() == 'windowsapps',
                'Installed executable is outside the owned package root')
        payload = {name.casefold(): value for name, value in record['payload'].items()}
        for module in modules:
            if module['origin'] == 'package':
                relative = module['relative_path']
                require(relative.casefold() in payload and module['sha256'] == payload[relative.casefold()]['sha256']
                        and PureWindowsPath(module['path']) == install_root / relative,
                        'Installed module source/path differs from exact package')
                package_modules[relative] = module['sha256']
            else:
                require(module['origin'] in ('windows', 'microsoft_windows_text_input_signed_platform', 'microsoft_defender_signed_platform'),
                        'Unqualified external module origin')
        require(package_modules.get('DupliSift.exe') == executable, 'Modules omit exact installed executable')
    return install


def clean_source(source, commit):
    require(publication.git(source, 'rev-parse', 'HEAD').decode().strip() == commit, 'Export source commit changed')
    require(not publication.git(source, 'status', '--porcelain=v1', '--untracked-files=all').strip(), 'Export source is not clean')


def validate_native_origin(source, evidence, record, context):
    provenance = load(evidence / 'native-build-provenance.json')
    require(provenance.get('source_commit') == context['source_commit'], 'Native collector source commit changed')
    measured = {row['staged_path']: dict(bytes=row['bytes'], sha256=row['original_sha256']) for row in provenance['native_files']}
    expected = {name: value for name,value in record['releaseInput'].items() if name.lower().endswith(('.dll', '.exe', '.pyd'))}
    require(len(measured) == len(provenance['native_files']) and measured == expected, 'Native collector origins differ from final payload')
    original = load(source / CLOSURE / 'original-build-evidence.json')
    for item in original['pdf']['binary_matches'] + original['microsoft']['files']:
        require(record['releaseInput'].get(item['staged_path']) == {key:item[key] for key in ('bytes', 'sha256')},
                'Final DLL differs from reviewed PDF configuration or Microsoft runtime evidence')


def export_store(source, evidence, qualification_package, store_package, output, context):
    """All input paths come from this run's orchestration; no acceptance override."""
    source, evidence, output = Path(source).resolve(), Path(evidence).resolve(), Path(output).absolute()
    require(re.fullmatch('[0-9a-f]{40}', context.get('source_commit', ''))
            and all(re.fullmatch('[1-9][0-9]*', context.get(key, '')) for key in ('workflow_run_id', 'workflow_run_attempt')),
            'Export needs exact current source and CI run/attempt')
    require(output == evidence / 'store-upload', 'Store output must be the exclusive evidence/store-upload directory')
    require(not os.path.lexists(output), 'Store export output already exists; will not overwrite')
    commit = context['source_commit']
    clean_source(source, commit)
    paths = {mode: Path(path).absolute() for mode,path in [('qualification', qualification_package), ('store', store_package)]}
    records = {mode: evidence / ('msix-store-package-record.json' if mode == 'store' else 'msix-package-record.json') for mode in paths}
    publication_path = source / CLOSURE / 'native-source-publication.json'
    plan_path = source / CLOSURE / 'source-release-assets.json'
    # Retain hashes of every evidence byte (including screenshots) and source publication inputs.
    before = msix.inventory_tree(evidence)
    source_records = {name: msix.file_record(source / CLOSURE / name) for name in
                      ('native-source-publication.json', 'source-release-assets.json', 'original-build-evidence.json')}
    startup = load(evidence / 'windows-startup.json')
    check_context(startup, context)
    installs = {}
    for mode, package in paths.items():
        msix.verify_record_inputs(package, records[mode], source / 'dist/DupliSift', source / 'images/duplisift/logo-256.png',
                                  commit, evidence / 'package-inventory.json', evidence / 'windows-startup.json', source, mode)
        record = load(records[mode])
        require(record.get('signed') is False and record.get('unresolvedNotices') == [], 'Unsigned package/notices gate failed')
        folder = evidence / ('msix-store-install' if mode == 'store' else 'msix-install')
        installs[mode] = validate_installation(folder, record, source, context, mode)
    store_record = load(records['store'])
    validate_native_origin(source, evidence, store_record, context)
    public_sources = publication.verify_public_sources(load(publication_path), plan_path, source, commit)
    require(msix.inventory_tree(evidence) == before, 'Qualification evidence changed during source verification')
    require(all(msix.file_record(source / CLOSURE / name) == value for name,value in source_records.items()), 'Source publication input changed')
    clean_source(source, commit)
    # Repeat source/stage/container binding after the remote read, before retaining any package.
    msix.verify_record_inputs(paths['store'], records['store'], source / 'dist/DupliSift', source / 'images/duplisift/logo-256.png',
                              commit, evidence / 'package-inventory.json', evidence / 'windows-startup.json', source, 'store')
    output.parent.mkdir(parents=True, exist_ok=True)
    for ancestor in (output.parent, *output.parent.parents):
        msix._reject_link(ancestor)
    output.mkdir()
    try:
        package = output / PACKAGE_NAME
        with msix._regular_stream(paths['store']) as original, package.open('xb') as destination:
            shutil.copyfileobj(original, destination, 1024 * 1024)
        require(msix.verify_msix(package, store_record['payload'], 'store') == store_record['containerVerification'], 'Retained unsigned package changed')
        clean_source(source, commit)
        after = {name: value for name, value in msix.inventory_tree(evidence).items() if not name.startswith('store-upload/')}
        require(after == before, 'Qualification evidence changed during package retention')
        require(all(msix.file_record(source / CLOSURE / name) == value for name,value in source_records.items()), 'Publication inputs changed during retention')
        receipt = dict(schema_version=1, product='DupliSift', generated_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            **context, identity=msix.STORE_IDENTITY, package=dict(filename=PACKAGE_NAME, **msix.file_record(package)),
            signed=False, store_upload_ready=True, submitted=False, public_release=False,
            qualified_identity_modes=['qualification', 'store'], public_sources=public_sources,
            source_publication_inputs=source_records, qualification_evidence=before)
        with (output / 'release-ready.json').open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(receipt, stream, indent=2); stream.write('\n')
    except BaseException:
        # Only these two files in the directory created above are owned by this invocation.
        for name in (PACKAGE_NAME, 'release-ready.json'):
            (output / name).unlink(missing_ok=True)
        output.rmdir()
        raise
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--qualification-package', type=Path, required=True)
    parser.add_argument('--store-package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32' or os.environ.get('CI') != 'true' or os.environ.get('GITHUB_REPOSITORY') != 'hashfunction/twinquay':
        parser.error('Store export requires the current DupliSift Windows CI run')
    context = dict(source_commit=os.environ.get('GITHUB_SHA', ''), workflow_run_id=os.environ.get('GITHUB_RUN_ID', ''),
                   workflow_run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT', ''))
    export_store(args.source_root, args.evidence, args.qualification_package, args.store_package, args.output, context)
    print('PASS: retained exact unsigned Store package and source-bound release-ready.json after both installed lifecycles.')


if __name__ == '__main__': main()

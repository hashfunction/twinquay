"""Acquire exact audit inputs and recheck native provenance; never certify a release.

Only hashes/lengths in the reviewed manifest are accepted. No archive is unpacked,
no package is installed, and binary provenance inputs are never source assets.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.parse
import urllib.request
import zipfile


def validate_entry(entry):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', entry.get('filename', '')) or '..' in entry['filename']:
        raise ValueError('Expected a flat archive filename')
    url = urllib.parse.urlsplit(entry.get('url', ''))
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment:
        raise ValueError('Expected an HTTPS upstream URL')
    if not re.fullmatch(r'[0-9a-f]{64}', entry.get('sha256', '')):
        raise ValueError('Expected verified SHA-256')
    if type(entry.get('bytes')) is not int or entry['bytes'] <= 0:
        raise ValueError('Expected positive byte count')
    if entry.get('kind') not in ('source', 'binary-provenance'):
        raise ValueError('Expected explicit source/binary classification')


def validate_manifest(manifest):
    if manifest.get('schema_version') != 1 or manifest.get('source_closure_claimed') is not False:
        raise ValueError('This preparation record cannot assert release/source clearance')
    entries = manifest.get('archives')
    if not isinstance(entries, list) or not entries:
        raise ValueError('No exact source archives recorded')
    names = set()
    for entry in entries:
        validate_entry(entry)
        if entry['filename'].casefold() in names:
            raise ValueError('Duplicate archive filename')
        names.add(entry['filename'].casefold())


def digest_file(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Expected regular file: {path}')
    size = 0
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            size += len(block)
            digest.update(block)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def verify_file(path, expected):
    if digest_file(path) != {key: expected[key] for key in ('bytes', 'sha256')}:
        raise ValueError(f'Archive/inventory bytes changed: {path}')


def acquire(entry, cache, opener=urllib.request.urlopen):
    validate_entry(entry)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    if cache.is_symlink():
        raise ValueError('Cache must be an actual directory')
    target = cache / entry['filename']
    if target.exists() or target.is_symlink():
        verify_file(target, entry)
        return
    # A rejected download can never appear under its final, manifest-bound name.
    fd, temporary_name = tempfile.mkstemp(prefix='.source-download-', dir=cache)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, 'wb') as output, opener(entry['url'], timeout=60) as response:
            if hasattr(response, 'geturl') and urllib.parse.urlsplit(response.geturl()).scheme != 'https':
                raise ValueError('Upstream redirected to a non-HTTPS location')
            size = 0
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > entry['bytes']:
                    raise ValueError('Download exceeds verified archive length')
                output.write(block)
            output.flush()
            os.fsync(output.fileno())
        verify_file(temporary, entry)
        # Exclusive install also refuses a file created concurrently at target.
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def verify_native(inventory, native, cache):
    files = {name: value for name, value in inventory['files'].items()
             if name.lower().endswith(('.exe', '.dll', '.pyd'))}
    if len(native) != len(files) or {row['path'] for row in native} != set(files):
        raise ValueError('Native inventory set differs from the audited run')
    matched = unmatched = 0
    for row in native:
        expected = {key: row[key] for key in ('bytes', 'sha256')}
        if files[row['path']] != expected:
            raise ValueError(f'Native file changed: {row["path"]}')
        if not row['matches']:
            if not row.get('unmatched_reason'):
                raise ValueError('Unmatched native input lacks explicit unresolved provenance')
            unmatched += 1
            continue
        for match in row['matches']:
            name = match['archive']
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name) or '..' in name:
                raise ValueError('Unsafe provenance archive name')
            path = Path(cache) / name
            if path.is_symlink():
                raise ValueError('Provenance archive is a symlink')
            with zipfile.ZipFile(path) as archive:
                entries = [item for item in archive.infolist() if item.filename == match['member']]
                if len(entries) != 1 or entries[0].file_size != expected['bytes']:
                    raise ValueError('Native member missing, duplicated, or wrong size')
                with archive.open(entries[0]) as stream:
                    digest = hashlib.sha256()
                    while block := stream.read(1024 * 1024):
                        digest.update(block)
                if digest.hexdigest() != expected['sha256']:
                    raise ValueError('Native member differs from the actual installed build')
        matched += 1
    return {'native_files': len(files), 'matched': matched, 'unmatched': unmatched,
            'source_closure_claimed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('verify', 'fetch'))
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('source-manifest.json'))
    parser.add_argument('--include-binaries', action='store_true', help='Include private comparison inputs; never publish them as source')
    parser.add_argument('--inventory', type=Path, help='Original run package-inventory.json, for native comparison')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    validate_manifest(manifest)
    selected = [entry for entry in manifest['archives'] if entry['kind'] == 'source' or args.include_binaries]
    for entry in selected:
        if args.operation == 'fetch':
            acquire(entry, args.cache)
        else:
            verify_file(args.cache / entry['filename'], entry)
    result = {'verified_archives': len(selected), 'source_closure_claimed': False,
              'public_release': False, 'publication_verified': False}
    if args.inventory:
        if not args.include_binaries:
            parser.error('--inventory requires --include-binaries')
        verify_file(args.inventory, manifest['evidence']['package_inventory'])
        inventory = json.loads(args.inventory.read_text(encoding='utf-8'))
        if inventory['sourceCommit'] != manifest['evidence']['public_source_commit']:
            raise ValueError('Inventory source revision differs')
        native_path = args.manifest.with_name('native-provenance.json')
        verify_file(native_path, manifest['native_provenance'])
        native = json.loads(native_path.read_text(encoding='utf-8'))
        result['native'] = verify_native(inventory, native, args.cache)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

"""Materialize reviewed source-license references, without a binary clearance claim."""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import tarfile

spec = importlib.util.spec_from_file_location('materials', Path(__file__).with_name('materials.py'))
materials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(materials)


def collect(manifest, notice_map, cache, output):
    materials.validate_manifest(manifest)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Notice destination must not already exist')
    archives = {entry['filename']: entry for entry in manifest['archives'] if entry['kind'] == 'source'}
    grouped = defaultdict(dict)
    destinations = set()
    for row in notice_map['entries']:
        relative = PurePosixPath(row['output'])
        if relative.is_absolute() or '..' in relative.parts or '\\' in row['output'] or ':' in row['output']:
            raise ValueError('Unsafe notice output path')
        if str(relative) != row['output'] or not relative.parts:
            raise ValueError('Noncanonical notice output path')
        if row['output'].casefold() in destinations or row['archive'] not in archives:
            raise ValueError('Duplicate output or notice input is not source')
        if row['member'] in grouped[row['archive']]:
            raise ValueError('Duplicate notice input')
        destinations.add(row['output'].casefold())
        grouped[row['archive']][row['member']] = row
    content = []
    for filename, wanted in grouped.items():
        archive = Path(cache) / filename
        materials.verify_file(archive, archives[filename])
        found = set()
        with tarfile.open(archive, mode='r|*') as source:
            for member in source:
                if member.name not in wanted:
                    continue
                row = wanted[member.name]
                if member.name in found or not member.isfile() or member.size != row['bytes'] or member.size > 1000000:
                    raise ValueError('Notice member duplicated, nonregular, or wrong size')
                data = source.extractfile(member).read()
                if hashlib.sha256(data).hexdigest() != row['sha256']:
                    raise ValueError('Notice bytes changed')
                found.add(member.name)
                content.append((row['output'], data))
        if found != set(wanted):
            raise ValueError('Expected source notice member is absent')
    # Validate every input before creating any output. Files are read, never tar-extracted.
    output.mkdir(parents=True, exist_ok=False)
    for name, data in content:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
    record = {'schema_version': 1, 'source_closure_claimed': False,
              'scope': notice_map['scope'], 'files': len(content), 'entries': notice_map['entries']}
    with (output / 'NOTICE-INDEX.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    return {'notice_files': len(content), 'source_closure_claimed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).parent
    manifest = json.loads((here / 'source-manifest.json').read_text())
    notice_path = here / 'notice-inputs.json'
    materials.verify_file(notice_path, manifest['notice_inputs'])
    print(json.dumps(collect(manifest, json.loads(notice_path.read_text()), args.cache, args.output), indent=2))


if __name__ == '__main__':
    main()

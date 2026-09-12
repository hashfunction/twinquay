# Copyright 2026 Trieflow LLC. MIT.
"""Validate reviewed source-license bytes before adding them to package notices."""
import json
from pathlib import Path
import shutil
from msix.msix_qualification import file_record, inventory_tree


def stage_native_notices(source, output):
    return _stage_notices(source,output,'native-notices','native-notice-inputs.json',
        'source-notices','DupliSift native source notices',
        'Exact source notices collected; release review required')


def stage_release_notices(source, output):
    return _stage_notices(source,output,'release-notices','release-notice-inputs.json',
        'release-notices','DupliSift original build and runtime notices',
        'Configured PDF notices and scoped Microsoft terms collected; release review required')


def _stage_notices(source, output, directory, mapping_name, target_name, record_name, review):
    source, output = Path(source), Path(output)
    prepared = source/'distribution'/directory
    mapping = source/'distribution/corresponding-source'/mapping_name
    inputs = json.loads(mapping.read_text(encoding='utf-8'))
    index = json.loads((prepared/'NOTICE-INDEX.json').read_text(encoding='utf-8'))
    if (inputs.get('schema_version') != 1 or not inputs.get('entries') or
            index != dict(schema_version=1,source_closure_claimed=False,scope=inputs['scope'],
                          files=len(inputs['entries']),entries=inputs['entries'])):
        raise ValueError('Prepared native notice index differs from reviewed source references')
    actual = inventory_tree(prepared)
    expected = {'NOTICE-INDEX.json': file_record(prepared/'NOTICE-INDEX.json')}
    for row in inputs['entries']:
        if row['output'] in expected:
            raise ValueError('Duplicate prepared notice')
        expected[row['output']] = {key: row[key] for key in ('bytes','sha256')}
    if actual != expected:
        raise ValueError('Prepared native notices are missing, changed or contain unreviewed files')
    target = output/target_name
    if target.exists() or target.is_symlink():
        raise ValueError('Native notice stage must be new')
    # Complete input validation precedes every generated-output mutation.
    target.mkdir(parents=True)
    for name, record in sorted(expected.items()):
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True)
        with (prepared/name).open('rb') as original, dest.open('xb') as copied:
            shutil.copyfileobj(original,copied)
        if file_record(dest) != record:
            raise ValueError('Native notice source changed during staging')
    return dict(name=record_name,version=file_record(mapping)['sha256'],
                notices=[target_name+'/'+name for name in sorted(expected)],
                review=review,
                scope=inputs['scope'])


def source_notice_fallbacks(source, record):
    """Missing wheel notices may use only same-version verified source notices."""
    source=Path(source)
    manifest=json.loads((source/'distribution/corresponding-source/source-manifest.json').read_text(encoding='utf-8'))
    inputs=json.loads((source/'distribution/corresponding-source/native-notice-inputs.json').read_text(encoding='utf-8'))
    archives={row['filename']:row for row in manifest['archives'] if row['kind']=='source'}
    collected=set(record['notices']); result={}
    for row in inputs['entries']:
        archive=archives[row['archive']]
        if not archive.get('version'):
            continue
        path='source-notices/'+row['output']
        if path not in collected:
            raise ValueError('Source notice fallback was not actually collected')
        key=(archive['component'].lower().replace('_','-'),archive['version'])
        result.setdefault(key,[]).append(path)
    return result

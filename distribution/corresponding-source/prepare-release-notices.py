"""Recreate exact original PDF attribution and Microsoft notice bytes offline.

Reads only the explicitly selected documentation/license inputs. The official
Qt binary comparison archive can never become a packaged notice or source asset.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('materials',here/'materials.py')
materials=importlib.util.module_from_spec(spec);spec.loader.exec_module(materials)

def checked_name(name):
    path=PurePosixPath(name)
    if not name or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or str(path)!=name:
        raise ValueError('Unsafe notice reference')
    return path

def prepare(inputs,cache,source,output):
    cache,source,output=Path(cache),Path(source),Path(output)
    if output.exists() or output.is_symlink():raise ValueError('Notice destination must be new')
    if inputs.get('schema_version')!=1 or not inputs.get('entries'):raise ValueError('Missing reviewed inputs')
    artifacts={}
    for artifact in inputs['artifacts']:
        name=artifact['filename']
        if len(checked_name(name).parts)!=1 or name.casefold() in artifacts:raise ValueError('Duplicate or nonflat artifact')
        artifacts[name.casefold()]=artifact
    content={};destinations=set()
    for row in inputs['entries']:
        name=row['output'];checked_name(name)
        if name.casefold()=='notice-index.json' or name.casefold() in destinations:raise ValueError('Duplicate or reserved notice destination')
        destinations.add(name.casefold())
        if 'source' in row:
            checked_name(row['source'])
            path=source/row['source']
            if not path.resolve().is_relative_to(source.resolve()):raise ValueError('Source reference escaped checkout')
            materials.verify_file(path,row);data=path.read_bytes()
        else:
            artifact=artifacts[row['artifact'].casefold()]
            if artifact['kind'] not in ('generated-documentation','license-document','license-evidence'):
                raise ValueError('Private binary comparison input is not a notice')
            path=cache/artifact['filename'];materials.verify_file(path,artifact)
            if row['member'] is None:
                if row['bytes']>1_000_000:raise ValueError('Oversized original notice')
                data=path.read_bytes()
            else:
                checked_name(row['member'])
                with zipfile.ZipFile(path) as archive:
                    matches=[entry for entry in archive.infolist() if entry.filename==row['member']]
                    if len(matches)!=1 or matches[0].is_dir() or matches[0].file_size!=row['bytes'] or row['bytes']>1_000_000:
                        raise ValueError('Missing, duplicate or unbounded notice member')
                    if stat.S_ISLNK(matches[0].external_attr>>16):raise ValueError('Notice member is a link')
                    data=archive.read(matches[0])
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('Original notice bytes changed')
        content[name]=data
    # Every reference has passed before creating the new output directory.
    output.mkdir(parents=True)
    for name,data in content.items():
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write(data)
    index=dict(schema_version=1,source_closure_claimed=False,scope=inputs['scope'],files=len(content),entries=inputs['entries'])
    (output/'NOTICE-INDEX.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    return dict(notice_files=len(content),source_closure_claimed=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    inputs=json.loads((here/'release-notice-inputs.json').read_text(encoding='utf-8'))
    print(json.dumps(prepare(inputs,args.cache,here.parents[1],args.output),indent=2))

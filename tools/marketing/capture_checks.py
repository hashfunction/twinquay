"""Pinned existing DupliSift package/evidence for capture only; no new acceptance."""
# Copyright 2026 Trieflow LLC. MIT.
import hashlib
import json
from pathlib import Path,PurePosixPath
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'msix'))
import msix_qualification as msix
from store_export import validate_installation, load

SOURCE='73f3842a2cc81aa3c69a5873a262517eae35b6f4'
RUN='34683417158'
PACKAGE_NAME='DupliSift_1.0.1.0_x64.msix'
FULL_NAME='1659hashfunction.TwinQuay_1.0.1.0_x64__r3hxytd7jt6c4'
PACKAGE={'bytes':46032604,'sha256':'bf0ec697fd0eab1517c1ca42c530cb46fc057454ab74acbff1c05feb64d44ae7'}
READY={'bytes':17395,'sha256':'5d6c6485b3b9cf823af4b469878ee6ac88627fc17955b2e61e01d19179b788ec'}
LOCKED_IDENTITY={'packageName':'1659hashfunction.TwinQuay','publisher':'CN=B6A2631A-FD32-45CC-AE12-82466975F528',
    'version':'1.0.1.0','architecture':'x64','applicationId':'TwinQuay','executable':'DupliSift.exe','deviceFamily':'Windows.Desktop',
    'minVersion':'10.0.19041.0','maxVersionTested':'10.0.26100.0','capability':'runFullTrust'}
# Original workflow uploads metadata only. These six runtime profile bytes were
# hashed by export but are not part of its artifact; no capture claim relies on them.
UNRETAINED_PROFILE={f'runtime-profile/TwinQuay/{name}' for name in (
    'debug.log','exclude_list.xml','hash_cache.db','ignore_list.xml','last_directories.xml','settings.ini')}


def require(value,message):
    if not value:raise ValueError(message)


def digest(path):
    with msix._regular_stream(Path(path)) as stream:
        h=hashlib.sha256();size=0
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk);size+=len(chunk)
    return {'bytes':size,'sha256':h.hexdigest()}


def read_json(path):
    with msix._regular_stream(Path(path)) as stream:data=stream.read(16*1024*1024+1)
    require(len(data)<=16*1024*1024,'Oversized capture evidence')
    return json.loads(data.decode('utf-8-sig'))


def relative_path(name):
    require(isinstance(name,str) and name and '\\' not in name and ':' not in name and not name.startswith('/')
            and all(part not in ('','.','..') for part in name.split('/')) and str(PurePosixPath(name))==name,'Unsafe artifact/evidence path')
    return name


def assert_current_capture_binding():
    require(msix.STORE_IDENTITY==LOCKED_IDENTITY,'Current product identity differs from pinned existing package')


def validate_receipts(ready,run):
    require(run.get('id')==int(RUN) and run.get('head_sha')==SOURCE and type(run.get('run_attempt')) is int and run['run_attempt']==1
            and run.get('conclusion')=='success' and run.get('repository',{}).get('full_name')=='hashfunction/twinquay'
            and run.get('path')=='.github/workflows/windows.yml','Pinned successful qualification run differs')
    require(ready.get('store_upload_ready') is True and ready.get('signed') is False and ready.get('identity')==LOCKED_IDENTITY
            and ready.get('package')==dict(PACKAGE,filename=PACKAGE_NAME)
            and ready.get('qualified_identity_modes')==['qualification','store'],'Pinned Store readiness receipt differs')
    require(ready.get('source_commit')==SOURCE and ready.get('workflow_run_id')==RUN and ready.get('workflow_run_attempt')=='1',
            'Qualified source/run differs')
    require(isinstance(ready.get('qualification_evidence'),dict) and ready['qualification_evidence'],'Original evidence binding is absent')


def verify_evidence(ready,metadata,source):
    for name,expected in ready['qualification_evidence'].items():
        relative_path(name)
        if name in UNRETAINED_PROFILE:continue
        require(digest(Path(metadata)/name)==expected,'Original qualification evidence changed: '+name)
    for name,expected in ready['source_publication_inputs'].items():
        relative_path(name)
        require(digest(Path(source)/'distribution/corresponding-source'/name)==expected,'Published source record changed: '+name)


def assert_qualified_checkout(source):
    import subprocess
    require(subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==SOURCE,'Qualified source checkout differs')
    require(not subprocess.check_output(['git','-C',str(source),'status','--porcelain=v1','--untracked-files=all'],text=True).strip(),
            'Qualified source checkout contains modified inputs')


def verify_inputs(package,ready_path,metadata,source,run):
    assert_current_capture_binding()
    require(digest(package)==PACKAGE,'Exact qualified unsigned package bytes differ')
    require(digest(ready_path)==READY,'Exact original readiness receipt differs')
    ready=load(ready_path);validate_receipts(ready,run)
    verify_evidence(ready,metadata,source)
    context={'source_commit':SOURCE,'workflow_run_id':RUN,'workflow_run_attempt':'1'}
    for mode in ('qualification','store'):
        prefix='msix-store' if mode=='store' else 'msix'
        record=load(Path(metadata)/(prefix+'-package-record.json'))
        require(record['sourceCommit']==SOURCE and record['identityMode']==mode and record['identity']==msix.identity_for_mode(mode),
                'Original package record differs')
        validate_installation(Path(metadata)/(prefix+'-install'),record,Path(source),context,mode)
    require(msix.verify_msix(package,record['payload'],'store')==record['containerVerification'],
            'Original unsigned container differs from verified payload')
    return record


if __name__=='__main__':
    import argparse,subprocess
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--qualified-source',type=Path,required=True)
    args=parser.parse_args()
    assert_qualified_checkout(args.qualified_source)
    verify_inputs(args.inputs/'store'/PACKAGE_NAME,args.inputs/'store/release-ready.json',args.inputs/'metadata',args.qualified_source,read_json(args.inputs/'qualified-run.json'))
    print('Verified exact existing DupliSift Store package and original successful installed workflow; capture only.')

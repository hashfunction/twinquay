"""Unsigned export boundary fixtures; these do not claim a Windows installed run."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import shutil
import zipfile
from pathlib import PureWindowsPath
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import msix_qualification as msix
try:
    import store_export as export
    import source_publication as publication
except ImportError:
    export = publication = None

SOURCE = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name('fixtures') / 'store-export-success.json'


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(export, 'Production exporter must exist')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.evidence = self.root / 'evidence'
        self.source = self.root / 'source'
        self.source.mkdir()
        self.commit = 'a' * 40
        self.context = dict(source_commit=self.commit, workflow_run_id='123', workflow_run_attempt='2')
        self.data = json.loads(FIXTURE.read_text())
        for mode, entry in self.data.items():
            install = entry['installation']
            install.update(self.context)
            workflow = install['workflow']
            workflow.update(self.context)
            for relative in workflow['source_inputs']:
                target = self.source / 'tools/msix' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((SOURCE / 'tools/msix' / relative).read_bytes())
                workflow['source_inputs'][relative] = msix.file_record(target)['sha256']
            folder = self.evidence / ('msix-store-install' if mode == 'store' else 'msix-install')
            folder.mkdir(parents=True)
            wf = folder / 'workflow'
            wf.mkdir()
            for surface in workflow['surfaces']:
                picture = wf / (surface['name'] + '.png')
                picture.write_bytes(b'local screenshot byte fixture: ' + surface['name'].encode())
                surface['screenshot_sha256'] = msix.file_record(picture)['sha256']
                self.write(wf / (surface['name'] + '.json'), surface)
            for stage, facts in workflow['files'].items():
                self.write(wf / (stage + '-files.json'), facts)
            self.write(wf / 'workflow.json', workflow)
            self.write(folder / 'installation-qualification.json', install)
            for name, rows in entry['modules'].items():
                self.write(folder / name, rows)
        self.record = self.data['store']['record']

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def validate(self, mode='store'):
        entry = self.data[mode]
        folder = self.evidence / ('msix-store-install' if mode == 'store' else 'msix-install')
        return export.validate_installation(folder, entry['record'], self.source, self.context, mode)

    def test_actual_success_receipt_shape_for_both_identities(self):
        for mode in ('qualification', 'store'):
            with self.subTest(mode=mode):
                self.assertTrue(self.validate(mode)['installation_qualification_passed'])

    def test_each_failed_or_stale_installation_refuses(self):
        folder = self.evidence / 'msix-store-install'
        original = self.data['store']['installation']
        changes = {key: False for key in (
            'add_appx_completed', 'registration_ownership_established', 'unsigned_package_unchanged',
            'process_identity_ownership_established', 'clean_close_verified', 'uninstall_verified',
            'installation_qualification_passed', 'workflow_acceptance', 'cleanup_restore_workflow_tested',
            'duplicate_scanning_tested', 'store_identity_used')}
        changes.update(source_commit='b'*40, workflow_run_id='124', workflow_run_attempt='1',
                       identity_mode='qualification', qualification_identity_only=True,
                       unsigned_package_sha256='f'*64, owned_package_full_name='foreign',
                       activated_process_package_full_name='foreign', certificate_private_key_exported=True,
                       primary_error='failure', cleanup_errors=['residue'], evidence_errors=['missing'],
                       preflight_package_full_names=['existing'], residual_package_full_names=['residue'],
                       loaded_module_count=0, post_workflow_loaded_module_count=0)
        for key, value in changes.items():
            with self.subTest(key=key):
                damaged = copy.deepcopy(original); damaged[key] = value
                self.write(folder / 'installation-qualification.json', damaged)
                with self.assertRaises(ValueError): self.validate()
        self.write(folder / 'installation-qualification.json', original)

    def test_workflow_cannot_be_replaced_with_only_a_pass_flag(self):
        folder = self.evidence / 'msix-store-install'
        original = self.data['store']['installation']
        for key, value in [('workflow', {'result': {'passed': True}}),
                           ('process_exit', {'normal_exit': True, 'exit_code': 1})]:
            damaged = copy.deepcopy(original); damaged[key] = value
            self.write(folder / 'installation-qualification.json', damaged)
            with self.subTest(key=key), self.assertRaises(ValueError): self.validate()

    def test_missing_altered_workflow_files_images_modules_refuse(self):
        folder = self.evidence / 'msix-store-install'
        for relative in ['workflow/08-restore-complete.png', 'workflow/restored-files.json',
                         'workflow/03-reviewed-plan.json', 'loaded-modules-after-workflow.json']:
            path = folder / relative; original = path.read_bytes()
            path.write_bytes(b'{}')
            with self.subTest(relative=relative), self.assertRaises(ValueError): self.validate()
            path.write_bytes(original)

    def test_coherent_changed_restored_bytes_or_failed_stage_refuses(self):
        folder = self.evidence / 'msix-store-install'
        for change in ('bytes', 'stages', 'collision'):
            install = copy.deepcopy(self.data['store']['installation']); workflow = install['workflow']
            if change == 'bytes': workflow['files']['restored']['files'][0]['sha256'] = 'f'*64
            elif change == 'collision': workflow['files']['restore_collision']['receipt']['items'][0]['detail'] = ''
            else: workflow['result']['completed_stages'].remove('Restore')
            self.write(folder / 'installation-qualification.json', install)
            self.write(folder / 'workflow/workflow.json', workflow)
            for stage, facts in workflow['files'].items(): self.write(folder / 'workflow' / (stage+'-files.json'), facts)
            with self.subTest(change=change), self.assertRaises(ValueError): self.validate()


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(publication, 'Production publication verifier must exist')
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.plan = SOURCE / 'distribution/corresponding-source/source-release-assets.json'
        self.record = dict(schema_version=1, product='DupliSift', publication_verified=True,
            source_page=publication.SOURCE_PAGE, release_url=publication.RELEASE_URL,
            verified_at_utc='2026-09-12T08:00:00Z', assets=[])
        for item in json.loads(self.plan.read_text())['assets']:
            self.record['assets'].append(self.item(item['filename'], item['bytes'], item['sha256']))
        self.record['manifest'] = self.item(self.plan.name, **msix.file_record(self.plan))

    def item(self, filename, bytes, sha256):
        return dict(filename=filename, bytes=bytes, sha256=sha256,
                    url=publication.DOWNLOAD_ROOT+filename, final_url='https://release-assets.githubusercontent.com/asset',
                    verified_at_utc='2026-09-12T08:00:00Z')

    def test_exact_71_verified_assets_and_manifest(self):
        publication.validate_publication(self.record, self.plan)
        self.assertEqual(len(self.record['assets']), 71)

    def test_missing_stale_mutable_and_unverified_publications_refuse(self):
        cases = []
        for key,value in [('publication_verified',False),('release_url',publication.RELEASE_URL+'-other'),('assets',[])]:
            record=copy.deepcopy(self.record);record[key]=value;cases.append(record)
        for key,value in [('sha256','a'*64),('bytes',1),('url','https://example.com/latest.tar'),('final_url','http://example.com/source'),('verified_at_utc','yesterday')]:
            record=copy.deepcopy(self.record);record['assets'][0][key]=value;cases.append(record)
        record=copy.deepcopy(self.record);record['assets'].append(record['assets'][0]);cases.append(record)
        record=copy.deepcopy(self.record);record['manifest']['sha256']='f'*64;cases.append(record)
        for index,record in enumerate(cases):
            with self.subTest(index=index),self.assertRaises(ValueError): publication.validate_publication(record,self.plan)

    def make_git(self):
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        (self.root/'README.md').write_text('Original current source\n')
        (self.root/'run.sh').write_text('#!/bin/sh\ntrue\n');(self.root/'run.sh').chmod(0o755)
        subprocess.run(['git','-C',str(self.root),'add','.'],check=True)
        subprocess.run(['git','-C',str(self.root),'update-index','--chmod=+x','run.sh'],check=True)
        subprocess.run(['git','-C',str(self.root),'-c','user.name=Fixture','-c','user.email=fixture@example.com','commit','-qm','fixture'],check=True)
        return subprocess.check_output(['git','-C',str(self.root),'rev-parse','HEAD'],text=True).strip()

    def test_actual_git_archive_complete_tree_and_modes(self):
        commit=self.make_git();archive=self.root.parent/(self.root.name+'.tar.gz');self.addCleanup(archive.unlink)
        subprocess.run(['git','-C',str(self.root),'archive','--format=tar.gz','--prefix=fixture/','-o',str(archive),commit],check=True)
        result=publication.verify_application_archive(archive,self.root,commit)
        self.assertEqual(result['verified_tracked_files'],2)
        self.assertEqual(result['source_commit'],commit)

    def test_archive_tampering_missing_extra_duplicate_or_mode_refuses(self):
        commit=self.make_git()
        for kind in ('altered','missing','extra','duplicate','mode','traversal'):
            archive=self.root/'fixture.tar.gz'
            with tarfile.open(archive,'w:gz') as tf:
                for name,mode in [('README.md',0o644),('run.sh',0o755)]:
                    if kind=='missing' and name=='run.sh':continue
                    data=(self.root/name).read_bytes()
                    if kind=='altered':data+=b'changed'
                    member=tarfile.TarInfo('fixture/'+name);member.size=len(data)
                    member.mode=0o644 if kind=='mode' else mode
                    tf.addfile(member,io.BytesIO(data))
                    if kind=='duplicate':tf.addfile(member,io.BytesIO(data))
                if kind in ('extra','traversal'):
                    member=tarfile.TarInfo('fixture/'+('extra' if kind=='extra' else '../outside'));tf.addfile(member,io.BytesIO())
            with self.subTest(kind=kind),self.assertRaises(ValueError):publication.verify_application_archive(archive,self.root,commit)


class FullExportTests(unittest.TestCase):
    def setUp(self):
        from test_msix_qualification import QualificationTests
        self.base = QualificationTests(methodName='runTest'); self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.root, self.source = self.base.root, self.base.source
        self.release = self.source / 'dist/DupliSift'
        shutil.copytree(self.base.release, self.release)
        self.evidence = self.root / 'evidence'; self.evidence.mkdir()
        self.output = self.evidence / 'store-upload'
        # Actual SDK-format ZIP and input-tree fixtures, with synthetic native bytes.
        notices = json.loads((self.release/'_internal/notices/dependency-inventory.json').read_text())
        notices = [item for item in notices if item['name'] != 'unresolved-fixture']
        (self.release/'_internal/notices/dependency-inventory.json').write_text(json.dumps(notices))
        for name in ('qualify-workflow.ps1','workflow_files.py'):
            path=self.source/'tools/msix'/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((SOURCE/'tools/msix'/name).read_bytes())
        closure=self.source/export.CLOSURE;closure.mkdir(parents=True)
        for name in ('source-release-assets.json','native-source-publication.json'):
            shutil.copyfile(SOURCE/export.CLOSURE/name,closure/name)
        pdf=dict(staged_path='_internal/PyQt6/Qt6/bin/Qt6Core.dll', **msix.file_record(self.release/'_internal/PyQt6/Qt6/bin/Qt6Core.dll'))
        (closure/'original-build-evidence.json').write_text(json.dumps(dict(pdf=dict(binary_matches=[pdf]),microsoft=dict(files=[]))))
        (self.source/'.gitignore').write_text('dist/\n')
        subprocess.run(['git','init','-q',str(self.source)],check=True)
        subprocess.run(['git','-C',str(self.source),'add','.'],check=True)
        subprocess.run(['git','-C',str(self.source),'-c','user.name=Fixture','-c','user.email=fixture@example.com','commit','-qm','fixture'],check=True)
        self.commit=publication.git(self.source,'rev-parse','HEAD').decode().strip()
        self.context=dict(source_commit=self.commit,workflow_run_id='123',workflow_run_attempt='2')
        inventory=msix.create_input_inventory(self.release,self.source,self.commit)
        self.write(self.evidence/'package-inventory.json',inventory)
        exe=inventory['files']['DupliSift.exe']['sha256']
        self.write(self.evidence/'windows-startup.json',dict(**self.context,windows_native_startup=True,window_title='DupliSift',
            executable_sha256=exe,package_inventory_sha256=msix.file_record(self.evidence/'package-inventory.json')['sha256']))
        rows=[dict(staged_path=name,bytes=value['bytes'],original_sha256=value['sha256']) for name,value in inventory['files'].items()
              if name.lower().endswith(('.dll','.pyd','.exe'))]
        self.write(self.evidence/'native-build-provenance.json',dict(source_commit=self.commit,native_files=rows))
        self.packages={}
        for mode,entry in json.loads(FIXTURE.read_text()).items():
            stage=self.root/('stage-'+mode)
            record=msix.stage_release(self.release,self.source/'images/duplisift/logo-256.png',stage,self.commit,
                self.evidence/'package-inventory.json',self.evidence/'windows-startup.json',self.source,mode)
            package=self.root/(mode+'.msix')
            with zipfile.ZipFile(package,'w') as archive:
                for path in stage.rglob('*'):
                    if path.is_file():archive.write(path,path.relative_to(stage).as_posix())
                archive.writestr('AppxBlockMap.xml',b'<BlockMap/>')
                archive.writestr('[Content_Types].xml',b'<Types/>')
            record['containerVerification']=msix.verify_msix(package,record['payload'],mode)
            record['unpackedVerification']=msix.verify_unpacked(stage,record['payload'],mode)
            self.packages[mode]=package
            self.write(self.evidence/('msix-store-package-record.json' if mode=='store' else 'msix-package-record.json'),record)
            folder=self.evidence/('msix-store-install' if mode=='store' else 'msix-install');(folder/'workflow').mkdir(parents=True)
            install=entry['installation'];install.update(self.context);install['executable_sha256']=exe
            install['unsigned_package_sha256']=record['containerVerification']['package']['sha256']
            workflow=install['workflow'];workflow.update(self.context);workflow['executable_sha256']=exe
            workflow['source_inputs']={name:msix.file_record(self.source/'tools/msix'/name)['sha256'] for name in workflow['source_inputs']}
            for surface in workflow['surfaces']:
                picture=folder/'workflow'/(surface['name']+'.png');picture.write_bytes(b'screenshot byte fixture')
                surface['screenshot_sha256']=msix.file_record(picture)['sha256']
                self.write(picture.with_suffix('.json'),surface)
            for name,facts in workflow['files'].items():self.write(folder/'workflow'/(name+'-files.json'),facts)
            self.write(folder/'workflow/workflow.json',workflow)
            module=dict(name='DupliSift.exe',path=str(PureWindowsPath('C:/Program Files/WindowsApps')/install['package_full_name']/'DupliSift.exe'),
                        origin='package',relative_path='DupliSift.exe',sha256=exe,platform_signature=None)
            for name in entry['modules']:self.write(folder/name,[module])
            install['loaded_module_count']=install['post_workflow_loaded_module_count']=1
            self.write(folder/'installation-qualification.json',install)

    def write(self,path,value):path.write_text(json.dumps(value),encoding='utf-8')

    def download(self,url,target,limit):
        if url.endswith('/source-release-assets.json'):
            shutil.copyfile(self.source/export.CLOSURE/'source-release-assets.json',target)
        else:
            subprocess.run(['git','-C',str(self.source),'archive','--format=tar.gz','--prefix=fixture/','-o',str(target),self.commit],check=True)
        return dict(url=url,final_url=url,**msix.file_record(target),verified_at_utc='2026-09-12T08:00:00Z')

    def run_export(self):
        with patch.object(publication,'download',side_effect=self.download):
            return export.export_store(self.source,self.evidence,self.packages['qualification'],self.packages['store'],self.output,self.context)

    def test_complete_real_zip_rederivation_exports_only_unsigned_and_receipt(self):
        receipt=self.run_export()
        self.assertEqual({path.name for path in self.output.iterdir()},{export.PACKAGE_NAME,'release-ready.json'})
        self.assertEqual(msix.file_record(self.output/export.PACKAGE_NAME),msix.file_record(self.packages['store']))
        self.assertEqual(receipt['source_commit'],self.commit)
        self.assertTrue(receipt['store_upload_ready']);self.assertFalse(receipt['signed'])
        self.assertGreater(receipt['public_sources']['application_source']['verified_tracked_files'],10)
        for mode in ('qualification','store'):
            record=self.evidence/('msix-store-package-record.json' if mode=='store' else 'msix-package-record.json')
            self.assertFalse(json.loads(record.read_text())['installationQualificationPassed'])
        with self.assertRaises(ValueError):self.run_export()

    def test_actual_signed_or_changed_zip_never_retained(self):
        with zipfile.ZipFile(self.packages['store'],'a') as archive:archive.writestr('AppxSignature.p7x',b'test signature')
        with self.assertRaises(ValueError):self.run_export()
        self.assertFalse(self.output.exists())

    def test_coherent_zip_record_tamper_cannot_replace_current_release(self):
        package=self.packages['store'];recordpath=self.evidence/'msix-store-package-record.json'
        record=json.loads(recordpath.read_text());record['payload']['DupliSift.exe']=dict(bytes=4,sha256=hashlib.sha256(b'evil').hexdigest())
        stage=self.root/'stage-store';(stage/'DupliSift.exe').write_bytes(b'evil')
        with zipfile.ZipFile(package,'w') as archive:
            for path in stage.rglob('*'):
                if path.is_file():archive.write(path,path.relative_to(stage).as_posix())
            archive.writestr('AppxBlockMap.xml',b'<BlockMap/>');archive.writestr('[Content_Types].xml',b'<Types/>')
        record['containerVerification']=msix.verify_msix(package,record['payload'],'store');self.write(recordpath,record)
        with self.assertRaises(ValueError):self.run_export()
        self.assertFalse(self.output.exists())

    def test_remote_manifest_or_source_mismatch_and_input_race_refuse(self):
        original=self.download
        for kind in ('manifest','source','race'):
            def changed(url,target,limit):
                result=original(url,target,limit)
                if kind=='manifest' and url.endswith('.json'):target.write_bytes(b'{}')
                if kind=='source' and url.endswith('.tar.gz'):target.write_bytes(b'not source')
                if kind=='race':(self.evidence/'late.json').write_text('{}')
                return result
            with patch.object(publication,'download',side_effect=changed):
                with self.subTest(kind=kind),self.assertRaises((ValueError,tarfile.TarError)):
                    export.export_store(self.source,self.evidence,self.packages['qualification'],self.packages['store'],self.output,self.context)
            self.assertFalse(self.output.exists())

    def test_missing_publication_leaves_no_export(self):
        (self.source/export.CLOSURE/'native-source-publication.json').unlink()
        with self.assertRaises((ValueError,FileNotFoundError)):self.run_export()
        self.assertFalse(self.output.exists())

    def test_copy_failure_removes_only_owned_partial_export(self):
        original=shutil.copyfileobj
        def fail_final(source,target,*args,**kwargs):
            if str(getattr(target,'name','')).endswith(export.PACKAGE_NAME):
                target.write(b'incomplete');raise OSError('fixture output failure')
            return original(source,target,*args,**kwargs)
        with patch.object(shutil,'copyfileobj',side_effect=fail_final):
            with self.assertRaisesRegex(OSError,'fixture output failure'):self.run_export()
        self.assertFalse(self.output.exists())
        self.assertTrue(self.packages['qualification'].is_file())
        self.assertTrue(self.packages['store'].is_file())

    def test_incomplete_cleanup_cannot_export_even_with_valid_package(self):
        path=self.evidence/'msix-install/installation-qualification.json';receipt=json.loads(path.read_text())
        receipt['cleanup_errors']=['owned certificate remains'];self.write(path,receipt)
        with self.assertRaises(ValueError):self.run_export()
        self.assertFalse(self.output.exists())


if __name__ == '__main__': unittest.main()

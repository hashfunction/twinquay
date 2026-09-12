# Copyright 2026 Trieflow LLC. MIT.
import hashlib
import json
import os
import runpy
import shutil
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).parent))
from native_notices import stage_native_notices, source_notice_fallbacks

class NativeNoticeTests(unittest.TestCase):
    def test_real_git_checkout_preserves_source_notice_bytes_with_windows_line_endings(self):
        source=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='twin-notice-checkout-') as name:
            repo=Path(name)
            shutil.copytree(source/'distribution/native-notices',repo/'distribution/native-notices')
            attributes=source/'.gitattributes'
            if attributes.exists():shutil.copyfile(attributes,repo/'.gitattributes')
            subprocess.run(['git','init','-q',str(repo)],check=True)
            subprocess.run(['git','-c','core.autocrlf=false','add','.'],cwd=repo,check=True)
            checked=repo/'checkout'
            subprocess.run(['git','-c','core.autocrlf=true','-c','core.eol=crlf','checkout-index','--all','--prefix='+checked.as_posix()+'/'],cwd=repo,check=True)
            index=json.loads((source/'distribution/native-notices/NOTICE-INDEX.json').read_text())
            for row in index['entries']:
                actual=(checked/'distribution/native-notices'/row['output']).read_bytes()
                self.assertEqual((len(actual),hashlib.sha256(actual).hexdigest()),(row['bytes'],row['sha256']),row['output'])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve(); self.prepared=self.root/'distribution/native-notices'
        self.prepared.mkdir(parents=True); self.output=self.root/'build/notices'; self.output.mkdir(parents=True)
        data=b'Exact copyright, permission, conditions and disclaimer.'
        self.relative='package-1.0.tar.gz/LICENSE'; path=self.prepared/self.relative;path.parent.mkdir();path.write_bytes(data)
        row=dict(archive='package-1.0.tar.gz',member='package-1.0/LICENSE',output=self.relative,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        self.inputs=dict(schema_version=1,scope='Reference notices; no source clearance',entries=[row])
        self.mapping=self.root/'distribution/corresponding-source';self.mapping.mkdir()
        (self.mapping/'native-notice-inputs.json').write_text(json.dumps(self.inputs))
        (self.prepared/'NOTICE-INDEX.json').write_text(json.dumps(dict(schema_version=1,source_closure_claimed=False,scope=self.inputs['scope'],files=1,entries=[row])))
        (self.mapping/'source-manifest.json').write_text(json.dumps(dict(archives=[dict(component='package',version='1.0',filename='package-1.0.tar.gz',kind='source')])))

    def test_exact_notice_bytes_and_scope_are_staged(self):
        record=stage_native_notices(self.root,self.output)
        self.assertEqual((self.output/'source-notices'/self.relative).read_bytes(),(self.prepared/self.relative).read_bytes())
        self.assertEqual(record['notices'],['source-notices/NOTICE-INDEX.json','source-notices/'+self.relative])
        self.assertIn('review required',record['review'])

    def test_missing_changed_extra_and_forged_index_refused_before_output(self):
        for change in ('changed','extra','forged','missing'):
            with self.subTest(change=change):
                target=self.prepared/self.relative; original=target.read_bytes()
                index=self.prepared/'NOTICE-INDEX.json';original_index=index.read_bytes()
                if change=='changed':target.write_bytes(b'different')
                if change=='extra':(self.prepared/'extra.txt').write_text('unreviewed')
                if change=='forged':index.write_text('{}')
                if change=='missing':target.unlink()
                with self.assertRaises(ValueError):stage_native_notices(self.root,self.output)
                self.assertFalse((self.output/'source-notices').exists())
                target.write_bytes(original);index.write_bytes(original_index);(self.prepared/'extra.txt').unlink(missing_ok=True)

    def test_fallback_requires_exact_distribution_version_and_real_collected_files(self):
        record=stage_native_notices(self.root,self.output)
        fallback=source_notice_fallbacks(self.root,record)
        self.assertEqual(fallback[('package','1.0')],['source-notices/'+self.relative])
        self.assertNotIn(('package','1.1'),fallback)
        self.assertNotIn(('foreign','1.0'),fallback)

    def test_production_collection_uses_only_exact_source_fallback_and_preserves_open_review(self):
        source=Path(__file__).resolve().parents[1]
        (self.root/'hscommon').mkdir();(self.root/'hscommon/LICENSE').write_text('BSD original')
        (self.root/'THIRD-PARTY-NOTICES.txt').write_text('Original project notices')
        packages=[SimpleNamespace(metadata={'Name':'sphinxcontrib-applehelp'},version='2.0.0',files=[]),
                  SimpleNamespace(metadata={'Name':'sphinxcontrib-qthelp'},version='99.0.0',files=[])]
        previous=Path.cwd()
        try:
            os.chdir(self.root)
            with patch('importlib.metadata.distributions',return_value=packages):
                runpy.run_path(str(source/'tools/collect_notices.py'),run_name='__main__')
            records=json.loads((self.root/'build/notices/dependency-inventory.json').read_text())
            by_name={row['name']:row for row in records}
            self.assertEqual(len(by_name['sphinxcontrib-applehelp']['notices']),1)
            self.assertIn('sphinxcontrib_applehelp-2.0.0.tar.gz/LICENCE.rst',by_name['sphinxcontrib-applehelp']['notices'][0])
            self.assertEqual(by_name['sphinxcontrib-qthelp']['notices'],[])
            self.assertEqual(by_name['sphinxcontrib-qthelp']['review'],'required')
            self.assertIn('review required',by_name['TwinQuay native source notices']['review'])
        finally:
            os.chdir(previous)

if __name__=='__main__':unittest.main()

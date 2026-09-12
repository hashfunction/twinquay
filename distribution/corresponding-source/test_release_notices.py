"""Exercise the real original-document preparation boundary without downloads."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

spec=importlib.util.spec_from_file_location('release_notices',Path(__file__).with_name('prepare-release-notices.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def measured(data):return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())

class ReleaseNoticeTests(unittest.TestCase):
    def test_packaged_plaintext_preserves_original_runtime_license_paragraphs(self):
        here=Path(__file__).resolve().parent
        original=here/'original-build-records/Visual-C-Runtime-2015-2022-License-1.docx'
        with zipfile.ZipFile(original) as archive:
            document=ET.fromstring(archive.read('word/document.xml'))
        ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        expected=('\n'.join(''.join(t.text or '' for t in paragraph.iter(ns+'t')) for paragraph in document.iter(ns+'p'))+'\n').encode('utf-8')
        actual=(here.parent/'release-notices/Microsoft/Visual-C-Runtime-2015-2022-License-1.txt').read_bytes()
        self.assertEqual(actual,expected)

    def test_archive_and_direct_originals_are_verified_before_output(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);cache=root/'cache';cache.mkdir();source=root/'source';source.mkdir()
            html=b'Original attribution';license=b'Original runtime conditions'
            with zipfile.ZipFile(cache/'docs.zip','w') as z:z.writestr('docs/license.html',html)
            (cache/'license.docx').write_bytes(license)
            artifacts=[dict(filename=n,kind=k,**measured((cache/n).read_bytes())) for n,k in [('docs.zip','generated-documentation'),('license.docx','license-document')]]
            entries=[dict(artifact='docs.zip',member='docs/license.html',output='QtPdf/license.html',**measured(html)),dict(artifact='license.docx',member=None,output='Microsoft/license.docx',**measured(license))]
            inputs=dict(schema_version=1,scope='Fixture only',artifacts=artifacts,entries=entries)
            module.prepare(inputs,cache,source,root/'out')
            self.assertEqual((root/'out/QtPdf/license.html').read_bytes(),html)
            self.assertEqual((root/'out/Microsoft/license.docx').read_bytes(),license)
            with self.assertRaisesRegex(ValueError,'new'):module.prepare(inputs,cache,source,root/'out')
            (cache/'license.docx').write_bytes(b'Changed')
            with self.assertRaises(ValueError):module.prepare(inputs,cache,source,root/'refused')
            self.assertFalse((root/'refused').exists())

    def test_private_binary_and_unsafe_or_duplicate_members_refused(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);data=b'notice';(root/'input').write_bytes(data)
            row=dict(artifact='input',member=None,output='notice.txt',**measured(data))
            artifact=dict(filename='input',kind='license-document',**measured(data))
            for kind,output,duplicate in [('private-original-build-comparison','notice.txt',False),('license-document','../outside',False),('license-document','notice.txt',True)]:
                with self.subTest(kind=kind,output=output,duplicate=duplicate):
                    entry=dict(row,output=output)
                    inputs=dict(schema_version=1,scope='Fixture',artifacts=[dict(artifact,kind=kind)],entries=[entry,entry] if duplicate else [entry])
                    with self.assertRaises(ValueError):module.prepare(inputs,root,root,root/'out')
                    self.assertFalse((root/'out').exists())

if __name__=='__main__':unittest.main()

"""Exercise the acquisition and binary/source evidence boundary without network."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('materials', Path(__file__).with_name('materials.py'))
materials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(materials)


def record(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


class MaterialsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.payload = b'exact upstream source'
        self.entry = dict(filename='source-1.tar.gz', url='https://example.org/source-1.tar.gz',
                          kind='source', **record(self.payload))

    def test_download_checks_bytes_before_installing_cache_entry(self):
        materials.acquire(self.entry, self.root, opener=lambda *_a, **_k: io.BytesIO(self.payload))
        self.assertEqual((self.root / self.entry['filename']).read_bytes(), self.payload)

    def test_bad_or_oversized_download_never_becomes_source(self):
        for data in (b'wrong upstream bytes', self.payload + b'x'):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    materials.acquire(self.entry, self.root, opener=lambda *_a, **_k: io.BytesIO(data))
                self.assertEqual(list(self.root.iterdir()), [])

    def test_existing_corrupt_cache_fails_without_overwrite_or_network(self):
        target = self.root / self.entry['filename']
        target.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            materials.acquire(self.entry, self.root, opener=lambda *_a, **_k: self.fail('network'))
        self.assertEqual(target.read_bytes(), b'changed')

    def test_manifest_refuses_paths_duplicates_http_and_clearance_claim(self):
        for change in ({'filename': '../source.tar.gz'}, {'url': 'http://example.org/source.tar.gz'},
                       {'sha256': 'unverified'}, {'bytes': True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                materials.validate_entry(dict(self.entry, **change))
        manifest = {'schema_version': 1, 'source_closure_claimed': False, 'archives': [self.entry]}
        materials.validate_manifest(manifest)
        with self.assertRaises(ValueError):
            materials.validate_manifest(dict(manifest, source_closure_claimed=True))
        with self.assertRaises(ValueError):
            materials.validate_manifest(dict(manifest, archives=[self.entry, self.entry]))

    def test_real_zip_member_and_complete_native_set_are_checked(self):
        data = b'actual native library bytes'
        archive = self.root / 'exact.whl'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('package/Qt6Pdf.dll', data)
        inventory = {'files': {'_internal/Qt6Pdf.dll': record(data)}}
        native = [dict(path='_internal/Qt6Pdf.dll', matches=[{'archive': archive.name,
                  'member': 'package/Qt6Pdf.dll'}], **record(data))]
        materials.verify_native(inventory, native, self.root)
        with self.assertRaises(ValueError):
            materials.verify_native({'files': dict(inventory['files'], **{'unknown.pyd': record(data)})}, native, self.root)
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('package/Qt6Pdf.dll', b'same filename, different build')
        with self.assertRaises(ValueError):
            materials.verify_native(inventory, native, self.root)

    def test_uncategorized_native_file_is_not_treated_as_cleared(self):
        inventory = {'files': {'ucrtbase.dll': record(b'windows')}}
        row = dict(path='ucrtbase.dll', matches=[], **record(b'windows'))
        with self.assertRaises(ValueError):
            materials.verify_native(inventory, [row], self.root)
        row['unmatched_reason'] = 'Redistributable origin not retained'
        result = materials.verify_native(inventory, [row], self.root)
        self.assertEqual(result['unmatched'], 1)
        self.assertFalse(result['source_closure_claimed'])


if __name__ == '__main__':
    unittest.main()

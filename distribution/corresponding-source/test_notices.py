import copy
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('notices', Path(__file__).with_name('collect-notices.py'))
notices = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notices)


def digest(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


class NoticeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = Path(self.tmp.name)
        self.output = self.cache / 'collected'
        self.data = b'Exact library copyright, terms and disclaimer'
        archive = self.cache / 'source.tar.gz'
        with tarfile.open(archive, 'w:gz') as t:
            member = tarfile.TarInfo('source/LICENSE')
            member.size = len(self.data)
            t.addfile(member, io.BytesIO(self.data))
        self.manifest = dict(schema_version=1, source_closure_claimed=False, archives=[
            dict(filename=archive.name, url='https://example.org/source.tar.gz', kind='source', **digest(archive.read_bytes()))])
        self.inputs = dict(scope='Source reference; no compiled inclusion claim', entries=[
            dict(archive=archive.name, member='source/LICENSE', output='component/LICENSE', **digest(self.data))])

    def test_collects_actual_tar_bytes_and_preserves_explicit_limit(self):
        record = notices.collect(self.manifest, self.inputs, self.cache, self.output)
        self.assertEqual((self.output / 'component/LICENSE').read_bytes(), self.data)
        self.assertEqual(record, {'notice_files': 1, 'source_closure_claimed': False})

    def test_missing_changed_and_noncanonical_notice_fail_before_output(self):
        for change in ({'member': 'absent/LICENSE'}, {'sha256': '0' * 64}, {'output': '../outside'}, {'output': 'a//b'}):
            with self.subTest(change=change):
                inputs = copy.deepcopy(self.inputs)
                inputs['entries'][0].update(change)
                with self.assertRaises(ValueError):
                    notices.collect(self.manifest, inputs, self.cache, self.output)
                self.assertFalse(self.output.exists())

    def test_refuses_existing_destination_without_mutation(self):
        self.output.mkdir()
        sentinel = self.output / 'existing'
        sentinel.write_text('keep')
        with self.assertRaises(ValueError):
            notices.collect(self.manifest, self.inputs, self.cache, self.output)
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_binary_provenance_archive_cannot_supply_source_notices(self):
        self.manifest['archives'][0]['kind'] = 'binary-provenance'
        with self.assertRaises(ValueError):
            notices.collect(self.manifest, self.inputs, self.cache, self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()

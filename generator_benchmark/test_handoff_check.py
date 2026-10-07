"""Safety contracts for supplemental validation; no real final-set access."""
import json
from pathlib import Path
import tempfile
import unittest

from mvp_handoff_check import check, require


class HandoffTests(unittest.TestCase):
    def test_output_inside_release_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp).resolve()
            output = release/'new_evidence'
            with self.assertRaisesRegex(ValueError, 'outside the locked release'):
                check(release, output)
            self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError, 'outside the locked release'):
                check(release, release)

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            release = root/'release'; release.mkdir()
            output = root/'evidence'; output.mkdir()
            sentinel = output/'results.json'; sentinel.write_text('existing evidence')
            with self.assertRaises(FileExistsError):
                check(release, output)
            self.assertEqual(sentinel.read_text(), 'existing evidence')

    def test_bad_integrity_retains_failure_and_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            release = root/'release'; release.mkdir()
            artifact = release/'data.bin'; artifact.write_bytes(b'original')
            manifest = release/'integrity.json'
            manifest.write_text(json.dumps({'files': {'data.bin': 'incorrect hash'}}))
            original = manifest.read_bytes()
            output = root/'evidence'
            with self.assertRaisesRegex(ValueError, 'Integrity failure'):
                check(release, output)
            result = json.loads((output/'results.json').read_text())
            self.assertEqual(result['status'], 'FAIL')
            self.assertIn('Integrity failure', result['error'])
            self.assertEqual(manifest.read_bytes(), original)
            self.assertEqual(artifact.read_bytes(), b'original')
            self.assertEqual(len(list(release.iterdir())), 2)

    def test_require_fail_closed(self):
        require(True, 'success')
        with self.assertRaisesRegex(ValueError, 'failure'):
            require(False, 'failure')


if __name__ == '__main__':
    unittest.main(verbosity=2)
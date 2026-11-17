"""Release failure safety checks; Docker execution is intentionally mocked here."""
import json
from pathlib import Path
import subprocess
import uuid
import unittest
from unittest.mock import patch
from deploy import release

IMAGE_A = 'ghcr.io/example/ticketly@sha256:' + 'a' * 64
IMAGE_B = 'ghcr.io/example/ticketly@sha256:' + 'b' * 64


class ReleaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(__file__).resolve().parent.parent / '.tmp' / 'release-tests'
        self.root = self.parent / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.addCleanup(self.clean_fixture)
        self.env = self.root / '.env.production'
        self.env.write_text('TEST=1')
        self.state = self.root / 'release-state.json'
        self.state.write_text(json.dumps({'current': IMAGE_A, 'previous': None}))

    def clean_fixture(self):
        assert self.root.resolve().parent == self.parent.resolve()
        for name in ('.env.production', 'release-state.json', '.release.lock', 'release-state.tmp'):
            (self.root / name).unlink(missing_ok=True)
        self.root.rmdir()

    def invoke(self, *args):
        with patch.object(release, 'ROOT', self.root), patch('sys.argv', ['release.py', '--env-file', str(self.env), *args]):
            release.main()

    @patch.object(release, 'backup')
    @patch.object(release, 'run')
    def test_success_records_previous_only_after_health(self, run, backup):
        self.invoke('--image', IMAGE_B)
        state = json.loads(self.state.read_text())
        self.assertEqual((state['current'], state['previous']), (IMAGE_B, IMAGE_A))
        self.assertIn('--wait', run.call_args.args[0])
        backup.assert_called_once()
        self.assertFalse((self.root / '.release.lock').exists())

    @patch.object(release, 'backup')
    @patch.object(release, 'run')
    def test_migration_failure_preserves_last_release_and_does_not_start_web(self, run, backup):
        def execute(command, *args, **kwargs):
            if command[-3:] == ['run', '--rm', 'migrate']:
                raise subprocess.CalledProcessError(1, command)
        run.side_effect = execute
        before = self.state.read_text()
        with self.assertRaises(subprocess.CalledProcessError): self.invoke('--image', IMAGE_B)
        self.assertEqual(self.state.read_text(), before)
        self.assertFalse(any('proxy' in call.args[0] and 'up' in call.args[0] for call in run.call_args_list))
        self.assertFalse((self.root / '.release.lock').exists())

    @patch.object(release, 'backup')
    @patch.object(release, 'run')
    def test_rollback_does_not_reverse_or_run_migrations(self, run, backup):
        self.state.write_text(json.dumps({'current': IMAGE_B, 'previous': IMAGE_A}))
        self.invoke('--rollback')
        self.assertEqual(json.loads(self.state.read_text())['current'], IMAGE_A)
        self.assertFalse(any('migrate' in call.args[0] for call in run.call_args_list))

    @patch.object(release, 'run')
    def test_mutable_image_and_concurrent_release_are_rejected(self, run):
        with self.assertRaises(ValueError): self.invoke('--image', 'ghcr.io/example/ticketly:latest')
        (self.root / '.release.lock').touch()
        with self.assertRaises(FileExistsError): self.invoke('--image', IMAGE_B)
        run.assert_not_called()

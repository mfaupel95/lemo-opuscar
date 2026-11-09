"""Offline CLI regression tests; all data stays in a private test directory."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'core' / 'render' / 'srt.py'


class SrtTests(unittest.TestCase):
    def export(self, cues):
        # Explicit dir avoids the system temp folder and any production input.
        with tempfile.TemporaryDirectory(prefix='srt-test-', dir=ROOT / 'tests') as tmp:
            source = Path(tmp) / 'cues.json'
            target = Path(tmp) / 'out.srt'
            source.write_text(json.dumps(cues), encoding='utf-8')
            result = subprocess.run(
                [sys.executable, '-I', str(SCRIPT), str(source), str(target)],
                cwd=tmp, capture_output=True, text=True, check=True,
            )
            return target.read_text(encoding='utf-8'), result.stdout

    def test_equal_starts_drop_collapsed_cue_and_renumber(self):
        output, stdout = self.export([
            {'t0': 1, 't1': 3, 'text': 'collapsed'},
            {'t0': 1, 't1': 4, 'text': 'visible'},
        ])
        self.assertEqual(output, '1\n00:00:01,000 --> 00:00:04,000\nvisible\n')
        self.assertIn('1 cues', stdout)

    def test_submillisecond_cue_is_not_exported_as_zero_duration(self):
        output, _ = self.export([{'t0': 1.0001, 't1': 1.0002, 'text': 'invisible'}])
        self.assertEqual(output, '')

    def test_negative_clamped_interval_and_reversed_interval_are_omitted(self):
        output, _ = self.export([
            {'t0': -2, 't1': -1, 'text': 'before start'},
            {'t0': 3, 't1': 2, 'text': 'reversed'},
        ])
        self.assertEqual(output, '')

    def test_sort_trim_and_keep_unicode(self):
        output, _ = self.export([
            {'t0': 2, 't1': 4, 'text': 'Gr\u00fc\u00dfe'},
            {'t0': 1, 't1': 3, 'text': 'first'},
        ])
        self.assertEqual(output, '1\n00:00:01,000 --> 00:00:02,000\nfirst\n\n2\n00:00:02,000 --> 00:00:04,000\nGr\u00fc\u00dfe\n')

    def test_rounding_carries_to_next_second(self):
        output, _ = self.export([{'t0': 1.9996, 't1': 3, 'text': 'carry'}])
        self.assertIn('00:00:02,000 --> 00:00:03,000', output)

    def test_empty_input(self):
        output, stdout = self.export([])
        self.assertEqual(output, '')
        self.assertIn('0 cues', stdout)


if __name__ == '__main__':
    unittest.main()

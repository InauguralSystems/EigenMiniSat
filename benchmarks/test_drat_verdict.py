#!/usr/bin/env python3
"""Library and shell-facing CLI must classify the same captured fixtures."""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

import drat_verdict


class DratVerdictTests(unittest.TestCase):
    CASES = (
        (0, b"c checked\n\rs VERIFIED\n", True, "VERIFIED"),
        (0, b"s TIMEOUT\n", False, "TIMEOUT"),
        (0, b"c MEMOUT allocation failed\n", False, "MEMOUT"),
        (0, b"c stopped\n", False, "missing verdict line"),
        (1, b"s NOT VERIFIED\n", False, "NOT VERIFIED"),
        (1, b"s VERIFIED\n", False, "VERIFIED with nonzero exit status 1"),
        (0, b"s VERIFIED\ns VERIFIED\n", False, "ambiguous verdict lines"),
    )

    def test_library_and_cli_share_every_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "checker.out"
            for rc, output, expected, reason in self.CASES:
                with self.subTest(rc=rc, output=output):
                    self.assertEqual(drat_verdict.classify(rc, output)[0], expected)
                    self.assertIn(reason, drat_verdict.classify(rc, output)[1])
                    fixture.write_bytes(output)
                    result = subprocess.run([sys.executable, drat_verdict.__file__, str(rc), fixture],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode == 0, expected)
                    self.assertIn(reason, result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

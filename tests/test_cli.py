from __future__ import annotations

import unittest

from cleanzd.__main__ import main


class CliTest(unittest.TestCase):
    def test_no_args_exits_2(self):
        with self.assertRaises(SystemExit):
            main([])

    def test_status_runs(self):
        self.assertEqual(main(["status"]), 0)

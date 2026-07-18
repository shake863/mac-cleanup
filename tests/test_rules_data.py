from __future__ import annotations
import unittest
from cleanzd.rules import load_rules

class RulesDataTest(unittest.TestCase):
    def test_loads_and_ids_unique(self):
        prules, crules, aliases = load_rules()
        ids = [r.id for r in prules] + [c.id for c in crules]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(prules), 25)
        self.assertGreaterEqual(len(crules), 10)
        self.assertIsInstance(aliases, dict)

    def test_all_paths_in_home(self):
        prules, crules, _ = load_rules()
        for r in prules:
            for p in r.paths:
                self.assertTrue(p.startswith("~") or p.startswith("$"),
                                f"{r.id} 路径必须以 ~ 或 $ 开头: {p}")

    def test_risks_valid(self):
        prules, crules, _ = load_rules()
        for r in prules + crules:
            self.assertIn(r.risk, ("recommend", "caution"), r.id)

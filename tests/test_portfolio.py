import unittest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from src.portfolio import (
    load_portfolio,
    save_portfolio,
    add_position,
    remove_position,
    clear_portfolio
)

class TestPortfolio(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.patcher = patch("src.portfolio.PORTFOLIO_FILE", Path(self.temp_file.name))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_add_and_load_position(self):
        pos = add_position("NVDA", "BUY", 120.0, stop_loss=110.0, take_profit=145.0)
        self.assertIsNotNone(pos)
        self.assertEqual(pos["ticker"], "NVDA")
        self.assertEqual(pos["direction"], "BUY")
        self.assertEqual(pos["entry_price"], 120.0)

        positions = load_portfolio()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["ticker"], "NVDA")

    def test_remove_position(self):
        add_position("AAPL", "BUY", 180.0)
        add_position("TSLA", "SELL", 250.0)
        self.assertEqual(len(load_portfolio()), 2)

        removed = remove_position("AAPL")
        self.assertTrue(removed)
        positions = load_portfolio()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["ticker"], "TSLA")

    def test_clear_portfolio(self):
        add_position("AAPL", "BUY", 180.0)
        clear_portfolio()
        self.assertEqual(len(load_portfolio()), 0)

if __name__ == "__main__":
    unittest.main()

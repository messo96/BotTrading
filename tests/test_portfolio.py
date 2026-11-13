import unittest
from pathlib import Path
from unittest.mock import patch
from src.portfolio import (
    load_portfolio,
    add_position,
    update_entry_price,
    update_stop_loss,
    update_take_profit,
    remove_position,
    clear_portfolio,
    archive_position,
    load_archived_portfolio
)

class TestPortfolio(unittest.TestCase):

    def setUp(self):
        self.portfolio_file = Path(__file__).parent / ".portfolio-test.json"
        self.archive_file = Path(__file__).parent / ".portfolio-archive-test.json"
        self.portfolio_file.unlink(missing_ok=True)
        self.archive_file.unlink(missing_ok=True)
        self.portfolio_patcher = patch("src.portfolio.PORTFOLIO_FILE", self.portfolio_file)
        self.archive_patcher = patch("src.portfolio.ARCHIVED_PORTFOLIO_FILE", self.archive_file)
        self.portfolio_patcher.start()
        self.archive_patcher.start()

    def tearDown(self):
        self.portfolio_patcher.stop()
        self.archive_patcher.stop()
        self.portfolio_file.unlink(missing_ok=True)
        self.archive_file.unlink(missing_ok=True)

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

    def test_update_entry_price(self):
        add_position("AAPL", "BUY", 180.0)

        self.assertTrue(update_entry_price("AAPL", 182.5))
        self.assertEqual(load_portfolio()[0]["entry_price"], 182.5)
        self.assertFalse(update_entry_price("TSLA", 200.0))

    def test_update_stop_loss_and_take_profit(self):
        add_position("AAPL", "BUY", 180.0, stop_loss=170.0, take_profit=200.0)

        self.assertTrue(update_stop_loss("AAPL", 175.0))
        self.assertEqual(load_portfolio()[0]["stop_loss"], 175.0)

        self.assertTrue(update_take_profit("AAPL", 210.0))
        self.assertEqual(load_portfolio()[0]["take_profit"], 210.0)

        self.assertFalse(update_stop_loss("TSLA", 190.0))
        self.assertFalse(update_take_profit("TSLA", 250.0))

        with self.assertRaises(ValueError):
            update_stop_loss("AAPL", -5.0)

        with self.assertRaises(ValueError):
            update_take_profit("AAPL", 0.0)

    def test_archive_position_preserves_history(self):
        add_position("AAPL", "SELL", 180.0)

        self.assertTrue(archive_position("AAPL"))
        self.assertEqual(load_portfolio(), [])
        archived = load_archived_portfolio()
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0]["ticker"], "AAPL")
        self.assertEqual(archived[0]["direction"], "SELL")
        self.assertEqual(archived[0]["entry_price"], 180.0)
        self.assertIn("archived_at", archived[0])
        self.assertFalse(archive_position("AAPL"))

    def test_entry_price_must_be_positive(self):
        with self.assertRaises(ValueError):
            add_position("AAPL", "BUY", 0)

if __name__ == "__main__":
    unittest.main()

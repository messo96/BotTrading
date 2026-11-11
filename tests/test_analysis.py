import unittest
import numpy as np
import pandas as pd
from src.indicators import (
    compute_rsi,
    compute_ema,
    compute_sma,
    compute_bollinger_bands,
    compute_macd,
    compute_atr,
    compute_volume_metrics
)
from src.analyzer import analyze_dataframe
from src.screener import analyze_single_ticker, run_market_screener
from src.formatters import format_single_ticker, format_screening_report

class TestTradingBot(unittest.TestCase):

    def setUp(self):
        # Genera dati sintetici realistici (60 giorni)
        np.random.seed(42)
        dates = pd.date_range(start="2026-01-01", periods=100, freq="B")
        prices = 100 + np.cumsum(np.random.randn(100) * 1.5)
        highs = prices + np.random.uniform(0.5, 2.0, 100)
        lows = prices - np.random.uniform(0.5, 2.0, 100)
        opens = prices + np.random.uniform(-0.5, 0.5, 100)
        volumes = np.random.randint(100000, 500000, 100)
        
        self.df = pd.DataFrame({
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": prices,
            "Volume": volumes
        }, index=dates)

    def test_indicators(self):
        rsi = compute_rsi(self.df["Close"])
        self.assertEqual(len(rsi), len(self.df))
        self.assertTrue(0 <= rsi.iloc[-1] <= 100)

        ema20 = compute_ema(self.df["Close"], 20)
        self.assertEqual(len(ema20), len(self.df))

        sma50 = compute_sma(self.df["Close"], 50)
        self.assertFalse(pd.isna(sma50.iloc[-1]))

        bb = compute_bollinger_bands(self.df["Close"])
        self.assertIn("bb_upper", bb)
        self.assertIn("bb_lower", bb)

        macd = compute_macd(self.df["Close"])
        self.assertIn("macd", macd)
        self.assertIn("macd_hist", macd)

        atr = compute_atr(self.df)
        self.assertGreater(atr.iloc[-1], 0)

        vol = compute_volume_metrics(self.df)
        self.assertGreater(vol["volume_surge_ratio"], 0)

    def test_analyzer(self):
        analysis = analyze_dataframe("TEST", self.df, asset_type="usa")
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis["ticker"], "TEST")
        self.assertTrue(0 <= analysis["score"] <= 100)
        self.assertIn("stop_loss", analysis)
        self.assertIn("take_profit_1", analysis)
        self.assertIn("take_profit_2", analysis)
        self.assertLess(analysis["stop_loss"], analysis["current_price"])
        self.assertGreater(analysis["take_profit_1"], analysis["current_price"])
        self.assertGreater(analysis["take_profit_2"], analysis["take_profit_1"])

    def test_formatters(self):
        analysis = analyze_dataframe("AAPL", self.df, asset_type="usa")
        single_msg = format_single_ticker(analysis)
        self.assertIn("ANALISI & SWING SETUP", single_msg)
        self.assertIn("AAPL", single_msg)

        report_msg = format_screening_report("TEST REPORT", [analysis], category="usa")
        self.assertIn("TEST REPORT", report_msg)
        self.assertIn("AAPL", report_msg)

if __name__ == "__main__":
    unittest.main()


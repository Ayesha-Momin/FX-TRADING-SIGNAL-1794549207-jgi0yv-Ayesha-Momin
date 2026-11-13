"""
FX Signal Lab - Unit & Integration Test Suite
Validates mathematical accuracy and operational integrity of all core quantitative modules.
"""

import sys
import os
import unittest
import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from indicators import calculate_sma, calculate_ema, calculate_rsi, calculate_macd, calculate_bollinger_bands, calculate_atr
from composite_signal_engine import CompositeSignalEngine
from backtester import FXBacktester
from monte_carlo import FXMonteCarloEngine


class TestFXQuantitativeModules(unittest.TestCase):
    
    def setUp(self):
        np.random.seed(42)
        prices = 1.0500 + np.cumsum(np.random.normal(0, 0.002, 100))
        self.series = pd.Series(prices)
        self.high = self.series * 1.002
        self.low = self.series * 0.998
        self.close = self.series
        
        self.sample_df = pd.DataFrame({
            'Open': self.series,
            'High': self.high,
            'Low': self.low,
            'Close': self.close,
            'Volume': 1000
        })

    def test_sma(self):
        sma = calculate_sma(self.series, window=10)
        self.assertEqual(len(sma), 100)
        self.assertTrue(np.isnan(sma.iloc[0]))
        self.assertAlmostEqual(sma.iloc[9], self.series.iloc[:10].mean(), places=5)

    def test_rsi_bounds(self):
        rsi = calculate_rsi(self.series, window=14)
        self.assertTrue((rsi >= 0.0).all())
        self.assertTrue((rsi <= 100.0).all())

    def test_bollinger_bands(self):
        upper, middle, lower, pct_b, bw = calculate_bollinger_bands(self.series, window=20, num_std=2.0)
        valid = ~upper.isna()
        self.assertTrue((upper[valid] >= middle[valid]).all())
        self.assertTrue((middle[valid] >= lower[valid]).all())

    def test_composite_signal_engine(self):
        engine = CompositeSignalEngine()
        # Add required indicator columns to sample_df
        from indicators import build_indicator_features
        df_ind = build_indicator_features(self.sample_df)
        eval_df = engine.evaluate(df_ind)
        self.assertIn('Composite_Score', eval_df.columns)
        self.assertIn('Signal_Direction', eval_df.columns)
        self.assertTrue(set(eval_df['Signal_Direction'].unique()).issubset({-1, 0, 1}))

    def test_backtester(self):
        bt = FXBacktester(initial_capital=50000.0)
        df_test = self.sample_df.copy()
        df_test['Signal_Direction'] = np.random.choice([-1, 0, 1], len(df_test))
        res = bt.run_backtest(df_test, signal_col='Signal_Direction', pair_name='EUR/USD')
        self.assertIn('metrics', res)
        self.assertIn('Total_Trades', res['metrics'])
        self.assertIn('Win_Rate', res['metrics'])

    def test_monte_carlo_engine(self):
        pairs = ['EUR/USD', 'USD/JPY']
        corr = np.array([[1.0, -0.4], [-0.4, 1.0]])
        mc = FXMonteCarloEngine(pairs=pairs, corr_matrix=corr, n_sims=500, horizon=50)
        res = mc.simulate_portfolio_pnl(
            spot_prices=np.array([1.08, 145.0]),
            vols=np.array([0.08, 0.11]),
            drifts=np.array([0.01, -0.02]),
            positions_usd=np.array([100000.0, -50000.0])
        )
        self.assertIn('var_95', res['metrics'])
        self.assertGreater(res['metrics']['var_95'], 0)


if __name__ == '__main__':
    unittest.main()

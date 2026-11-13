"""
FX Signal Lab - Scenario Engine & Macro Stress Simulator
Simulates extreme market shocks, central bank policy divergence, and liquidity crises
to evaluate quantitative signal robustness and risk mitigation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any


class ScenarioEngine:
    """
    Stress-testing and regime detection framework for multi-currency FX strategies.
    """
    def __init__(self):
        self.scenarios = {
            'BOJ_SHOCK': {
                'name': 'The BOJ Shock (Carry Trade Unwind)',
                'description': 'Bank of Japan unexpectedly hikes rates by 100bps, triggering massive carry unwind.',
                'shocks': {'USD/JPY': -0.085, 'AUD/JPY': -0.092, 'EUR/USD': +0.012, 'GBP/USD': +0.008, 'USD/INR': -0.005},
                'spread_multiplier': 3.5,
                'regime': 'CRISIS'
            },
            'FLASH_CRASH': {
                'name': 'The Asian Session Flash Crash',
                'description': 'GBP/USD plummets 600 pips in 2 minutes during thin Asian liquidity with 50-pip spreads.',
                'shocks': {'GBP/USD': -0.062, 'EUR/USD': -0.015, 'USD/JPY': -0.020, 'AUD/USD': -0.025, 'USD/INR': +0.004},
                'spread_multiplier': 8.0,
                'regime': 'CRISIS'
            },
            'RBI_INTERVENTION': {
                'name': 'USD/INR RBI Range Intervention',
                'description': 'Reserve Bank of India pins USD/INR strictly between 82.50 and 83.50 via FX reserves.',
                'shocks': {'USD/INR': -0.002, 'USD/JPY': 0.000, 'EUR/USD': +0.001, 'GBP/USD': +0.001, 'AUD/USD': +0.002},
                'spread_multiplier': 1.1,
                'regime': 'LOW_VOL'
            },
            'FED_PIVOT': {
                'name': 'Dovish Fed Emergency Pivot',
                'description': 'Federal Reserve cuts benchmark rate by 75bps amid banking liquidity stress.',
                'shocks': {'EUR/USD': +0.035, 'GBP/USD': +0.040, 'AUD/USD': +0.045, 'USD/JPY': -0.038, 'USD/INR': -0.018},
                'spread_multiplier': 2.0,
                'regime': 'HIGH_VOL'
            },
            'CORRELATION_BREAKDOWN': {
                'name': 'Multi-Pair Correlation Breakdown',
                'description': 'EUR/USD and GBP/USD decoupling; historical correlation crashes from +0.85 to -0.20.',
                'shocks': {'EUR/USD': +0.022, 'GBP/USD': -0.031, 'AUD/USD': -0.015, 'USD/JPY': +0.010, 'USD/INR': +0.003},
                'spread_multiplier': 2.5,
                'regime': 'HIGH_VOL'
            }
        }

    def detect_volatility_regime(self, df: pd.DataFrame, vol_col: str = 'vol_20d') -> pd.Series:
        """
        Classifies historical periods into four distinct regimes:
            - LOW_VOL: Vol < 15th percentile
            - NORMAL: 15th <= Vol <= 80th percentile
            - HIGH_VOL: 80th < Vol <= 95th percentile
            - CRISIS: Vol > 95th percentile
        """
        vols = df[vol_col].dropna()
        q15 = vols.quantile(0.15)
        q80 = vols.quantile(0.80)
        q95 = vols.quantile(0.95)
        
        conditions = [
            df[vol_col] < q15,
            (df[vol_col] >= q15) & (df[vol_col] <= q80),
            (df[vol_col] > q80) & (df[vol_col] <= q95),
            df[vol_col] > q95
        ]
        regimes = ['LOW_VOL', 'NORMAL', 'HIGH_VOL', 'CRISIS']
        return pd.Series(np.select(conditions, regimes, default='NORMAL'), index=df.index)

    def apply_scenario_stress(
        self,
        scenario_key: str,
        base_positions: Dict[str, float],
        base_portfolio_val: float = 1000000.0
    ) -> Dict[str, Any]:
        """
        Applies a predefined macro scenario shock to an FX portfolio book.
        
        Args:
            scenario_key: e.g. 'BOJ_SHOCK', 'FLASH_CRASH'
            base_positions: Dict of currency pair to USD exposure, e.g. {'EUR/USD': 400000, 'USD/JPY': -300000}
            base_portfolio_val: Total portfolio notional
            
        Returns:
            Dictionary with shocked PnL, post-shock equity, VaR recalculation, and recommended action.
        """
        scen = self.scenarios.get(scenario_key, self.scenarios['BOJ_SHOCK'])
        shocks = scen['shocks']
        
        pair_impacts = {}
        total_pnl = 0.0
        
        for pair, exposure in base_positions.items():
            pct_move = shocks.get(pair, 0.0)
            pnl = exposure * pct_move
            pair_impacts[pair] = {
                'Exposure_USD': exposure,
                'Shock_Pct': round(pct_move * 100.0, 2),
                'PnL_Impact': round(pnl, 2)
            }
            total_pnl += pnl
            
        post_equity = base_portfolio_val + total_pnl
        drawdown_pct = (total_pnl / base_portfolio_val) * 100.0
        
        # Recommendations
        if scen['regime'] == 'CRISIS':
            action = "EMERGENCY PROTOCOL: Cut gross exposure by 60%, hedge JPY legs, widen stop-losses to 3x ATR."
        elif scen['regime'] == 'HIGH_VOL':
            action = "VOLATILITY REBALANCING: Halve position sizes, transition from trend-following to mean-reversion."
        else:
            action = "RANGE-BOUND CORRIDOR: Maximize carry harvesting and RSI boundary mean-reversion."
            
        return {
            'scenario_name': scen['name'],
            'regime': scen['regime'],
            'description': scen['description'],
            'spread_multiplier': scen['spread_multiplier'],
            'total_shock_pnl': round(total_pnl, 2),
            'drawdown_pct': round(drawdown_pct, 2),
            'post_shock_equity': round(post_equity, 2),
            'pair_impacts': pair_impacts,
            'recommended_action': action
        }

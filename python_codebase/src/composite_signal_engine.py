"""
FX Signal Lab - Composite Signal Engine
Multi-factor quantitative signal generation combining trend-following, momentum,
volatility breakouts, and mean-reversion with weighted voting and confidence scoring.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple


class CompositeSignalEngine:
    """
    Institutional composite FX signal generator with weighted multi-indicator consensus.
    """
    def __init__(self, weights: Dict[str, float] = None, threshold_buy: float = 0.25, threshold_sell: float = -0.25):
        # Default weights summing to 1.0
        self.weights = weights or {
            'MA_Cross': 0.20,
            'EMA_Trend': 0.15,
            'RSI': 0.15,
            'MACD': 0.20,
            'Bollinger': 0.15,
            'Ichimoku': 0.15
        }
        # Normalize weights
        total_w = sum(self.weights.values())
        self.weights = {k: v / total_w for k, v in self.weights.items()}
        
        self.threshold_buy = threshold_buy
        self.threshold_sell = threshold_sell

    def generate_component_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates individual sub-signals: -1 (Bearish), 0 (Neutral), +1 (Bullish)
        """
        sig_df = pd.DataFrame(index=df.index)
        
        # 1. Moving Average Crossover (SMA 10 vs SMA 50)
        sig_df['Sig_MA_Cross'] = np.where(df['SMA_10'] > df['SMA_50'], 1.0,
                                 np.where(df['SMA_10'] < df['SMA_50'], -1.0, 0.0))
        
        # 2. EMA Trend (Close vs EMA 50)
        sig_df['Sig_EMA_Trend'] = np.where(df['Close'] > df['EMA_50'], 1.0,
                                  np.where(df['Close'] < df['EMA_50'], -1.0, 0.0))
        
        # 3. RSI Momentum & Mean Reversion (Overbought > 70, Oversold < 30)
        sig_df['Sig_RSI'] = np.where(df['RSI_14'] < 30, 1.0,  # Oversold -> Bullish bounce
                            np.where(df['RSI_14'] > 70, -1.0, # Overbought -> Bearish reversal
                            np.where(df['RSI_14'] > 55, 0.5,
                            np.where(df['RSI_14'] < 45, -0.5, 0.0))))
        
        # 4. MACD Momentum (Line vs Signal + Histogram expansion)
        macd_cross = np.where(df['MACD_Line'] > df['MACD_Signal'], 1.0, -1.0)
        hist_mom = np.where(df['MACD_Hist'] > 0, 0.5, -0.5)
        sig_df['Sig_MACD'] = np.clip(macd_cross * 0.7 + hist_mom * 0.3, -1.0, 1.0)
        
        # 5. Bollinger Bands (%B oscillator)
        sig_df['Sig_Bollinger'] = np.where(df['BB_PctB'] < 0.05, 1.0,  # Band breach low -> long
                                  np.where(df['BB_PctB'] > 0.95, -1.0, # Band breach high -> short
                                  np.where(df['BB_PctB'] < 0.30, 0.5,
                                  np.where(df['BB_PctB'] > 0.70, -0.5, 0.0))))
        
        # 6. Ichimoku Cloud Breakout
        above_cloud = (df['Close'] > df['Ichimoku_SenkouA']) & (df['Close'] > df['Ichimoku_SenkouB'])
        below_cloud = (df['Close'] < df['Ichimoku_SenkouA']) & (df['Close'] < df['Ichimoku_SenkouB'])
        tk_cross = df['Ichimoku_Tenkan'] > df['Ichimoku_Kijun']
        
        sig_df['Sig_Ichimoku'] = np.where(above_cloud & tk_cross, 1.0,
                                 np.where(above_cloud, 0.5,
                                 np.where(below_cloud & (~tk_cross), -1.0,
                                 np.where(below_cloud, -0.5, 0.0))))
        
        return sig_df

    def evaluate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Evaluates full composite signals, confidence scores, SL, and TP levels.
        """
        res = df.copy()
        comp_signals = self.generate_component_signals(res)
        for col in comp_signals.columns:
            res[col] = comp_signals[col]
            
        # Weighted composite score (-1.0 to +1.0)
        res['Composite_Score_Raw'] = (
            comp_signals['Sig_MA_Cross'] * self.weights['MA_Cross'] +
            comp_signals['Sig_EMA_Trend'] * self.weights['EMA_Trend'] +
            comp_signals['Sig_RSI'] * self.weights['RSI'] +
            comp_signals['Sig_MACD'] * self.weights['MACD'] +
            comp_signals['Sig_Bollinger'] * self.weights['Bollinger'] +
            comp_signals['Sig_Ichimoku'] * self.weights['Ichimoku']
        )
        
        # Scale to -100 to +100
        res['Composite_Score'] = (res['Composite_Score_Raw'] * 100.0).round(2)
        
        # Discrete directional signal: +1 (BUY), -1 (SELL), 0 (HOLD)
        res['Signal_Direction'] = np.where(res['Composite_Score_Raw'] >= self.threshold_buy, 1,
                                  np.where(res['Composite_Score_Raw'] <= self.threshold_sell, -1, 0))
        
        # Indicator Consensus (% of indicators agreeing with direction)
        directional_cols = [c for c in comp_signals.columns if c.startswith('Sig_')]
        bullish_count = (comp_signals[directional_cols] > 0).sum(axis=1)
        bearish_count = (comp_signals[directional_cols] < 0).sum(axis=1)
        total_indicators = len(directional_cols)
        
        res['Indicator_Agreement'] = np.where(
            res['Signal_Direction'] == 1, bullish_count / total_indicators,
            np.where(res['Signal_Direction'] == -1, bearish_count / total_indicators, 0.0)
        ).round(3)
        
        # Confidence Score: combination of magnitude and agreement
        res['Signal_Confidence'] = (
            (res['Composite_Score_Raw'].abs() * 0.6 + res['Indicator_Agreement'] * 0.4)
        ).clip(0.0, 1.0).round(3)
        
        # Risk levels: ATR-based Dynamic Stop-Loss and Take-Profit
        atr = res['ATR_14'].fillna(res['Close'] * 0.005)
        res['Stop_Loss'] = np.where(
            res['Signal_Direction'] == 1, res['Close'] - (1.5 * atr),
            np.where(res['Signal_Direction'] == -1, res['Close'] + (1.5 * atr), np.nan)
        )
        res['Take_Profit'] = np.where(
            res['Signal_Direction'] == 1, res['Close'] + (3.0 * atr),
            np.where(res['Signal_Direction'] == -1, res['Close'] - (3.0 * atr), np.nan)
        )
        
        return res

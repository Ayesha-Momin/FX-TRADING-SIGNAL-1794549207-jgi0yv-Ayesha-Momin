"""
FX Signal Lab - Feature Engineering Pipeline
Constructs 35+ quantitative features and forward-looking classification targets for ML/RL models.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple


def generate_ml_features(df: pd.DataFrame, forward_horizon: int = 5, target_threshold: float = 0.003) -> Tuple[pd.DataFrame, List[str]]:
    """
    Transforms raw OHLCV and indicator data into 35+ clean predictive features and forward return targets.
    
    Args:
        df: DataFrame containing OHLCV, DateTime, and basic indicators.
        forward_horizon: Number of periods forward for target evaluation.
        target_threshold: Minimum return required to classify as BUY/SELL vs NEUTRAL.
        
    Returns:
        df_feat: DataFrame with features and Target column.
        feature_cols: List of generated feature column names.
    """
    feat = df.copy()
    close = feat['Close']
    high = feat['High']
    low = feat['Low']
    vol = feat['Volume'] if 'Volume' in feat.columns else pd.Series(1, index=feat.index)
    
    # 1. Multi-horizon Returns
    feat['return_1d'] = close.pct_change(1)
    feat['return_2d'] = close.pct_change(2)
    feat['return_3d'] = close.pct_change(3)
    feat['return_5d'] = close.pct_change(5)
    feat['return_10d'] = close.pct_change(10)
    feat['return_20d'] = close.pct_change(20)
    feat['return_60d'] = close.pct_change(60)
    
    # 2. Log Returns
    feat['log_return_1d'] = np.log(close / close.shift(1))
    feat['log_return_5d'] = np.log(close / close.shift(5))
    
    # 3. Rolling Volatility Measures (Annualized)
    feat['vol_5d'] = feat['return_1d'].rolling(5).std() * np.sqrt(252)
    feat['vol_10d'] = feat['return_1d'].rolling(10).std() * np.sqrt(252)
    feat['vol_20d'] = feat['return_1d'].rolling(20).std() * np.sqrt(252)
    feat['vol_60d'] = feat['return_1d'].rolling(60).std() * np.sqrt(252)
    
    # Parkinson Volatility (High-Low volatility estimator)
    feat['parkinson_vol_10d'] = np.sqrt(
        (np.log(high / low) ** 2).rolling(10).mean() / (4 * np.log(2))
    ) * np.sqrt(252)
    
    # 4. Moving Average Ratios & Spreads
    sma_10 = close.rolling(10).mean()
    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()
    
    feat['close_to_sma20'] = close / sma_20 - 1.0
    feat['close_to_sma50'] = close / sma_50 - 1.0
    feat['close_to_sma200'] = close / sma_200 - 1.0
    feat['sma20_to_sma50'] = sma_20 / sma_50 - 1.0
    
    # 5. Momentum & Oscillators
    feat['roc_5'] = (close - close.shift(5)) / close.shift(5) * 100.0
    feat['roc_10'] = (close - close.shift(10)) / close.shift(10) * 100.0
    feat['roc_20'] = (close - close.shift(20)) / close.shift(20) * 100.0
    
    # Normalized RSI & Bollinger features (recompute if missing)
    if 'RSI_14' in feat.columns:
        feat['norm_rsi'] = (feat['RSI_14'] - 50.0) / 50.0
    else:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        feat['norm_rsi'] = ((100 - (100 / (1 + rs))) - 50.0) / 50.0
        
    if 'BB_PctB' in feat.columns:
        feat['bb_pctb'] = feat['BB_PctB']
        feat['bb_width'] = feat['BB_Bandwidth']
    else:
        bb_mid = sma_20
        bb_std = close.rolling(20).std()
        feat['bb_pctb'] = (close - (bb_mid - 2*bb_std)) / (4*bb_std).replace(0, np.nan)
        feat['bb_width'] = (4*bb_std) / bb_mid.replace(0, np.nan)
        
    if 'ATR_14' in feat.columns:
        feat['atr_pct'] = feat['ATR_14'] / close
    else:
        tr = (high - low).rolling(14).mean()
        feat['atr_pct'] = tr / close
        
    # 6. Interaction & Non-linear Features
    feat['vol_momentum_interaction'] = feat['return_5d'] * feat['vol_10d']
    feat['rsi_bb_interaction'] = feat['norm_rsi'] * (feat['bb_pctb'] - 0.5)
    feat['skew_20d'] = feat['return_1d'].rolling(20).skew()
    feat['kurt_20d'] = feat['return_1d'].rolling(20).kurt()
    
    # 7. Time & Seasonality Features
    if 'DateTime' in feat.columns:
        dt = pd.to_datetime(feat['DateTime'])
        feat['day_of_week'] = dt.dt.dayofweek
        feat['hour_of_day'] = dt.dt.hour
        # Sine/Cosine cyclical encoding
        feat['day_sin'] = np.sin(2 * np.pi * feat['day_of_week'] / 5.0)
        feat['day_cos'] = np.cos(2 * np.pi * feat['day_of_week'] / 5.0)
        feat['hour_sin'] = np.sin(2 * np.pi * feat['hour_of_day'] / 24.0)
        feat['hour_cos'] = np.cos(2 * np.pi * feat['hour_of_day'] / 24.0)
        # Session flags (UTC hours)
        feat['is_asian_session'] = ((feat['hour_of_day'] >= 0) & (feat['hour_of_day'] < 9)).astype(int)
        feat['is_london_session'] = ((feat['hour_of_day'] >= 7) & (feat['hour_of_day'] < 16)).astype(int)
        feat['is_ny_session'] = ((feat['hour_of_day'] >= 13) & (feat['hour_of_day'] < 22)).astype(int)
        feat['is_overlap_session'] = ((feat['hour_of_day'] >= 13) & (feat['hour_of_day'] < 16)).astype(int)
    
    # 8. Target Formulation (Forward Return)
    feat['forward_return'] = (close.shift(-forward_horizon) - close) / close
    
    # 3-Class Target: 1 = BUY, 0 = NEUTRAL / FLAT, -1 = SELL
    conditions = [
        feat['forward_return'] > target_threshold,
        feat['forward_return'] < -target_threshold
    ]
    choices = [1, -1]
    feat['Target'] = np.select(conditions, choices, default=0)
    
    # List of all numeric feature columns
    excluded = ['DateTime', 'Date', 'PairID', 'PairName', 'Open', 'High', 'Low', 'Close', 
                'Volume', 'Spread', 'forward_return', 'Target', 'Stop_Loss', 'Take_Profit',
                'DateTimeKey', 'DateKey', 'VolatilityRegime', 'PrevClose']
    feature_cols = [c for c in feat.columns if c not in excluded and pd.api.types.is_numeric_dtype(feat[c])]
    
    return feat, feature_cols

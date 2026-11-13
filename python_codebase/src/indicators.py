"""
FX Signal Lab - Quantitative Technical Indicators Module
Implements institutional-grade technical analysis indicators with precision mathematical formulas.
"""

import numpy as np
import pandas as pd


def calculate_sma(series: pd.Series, window: int = 20) -> pd.Series:
    """Calculate Simple Moving Average."""
    return series.rolling(window=window, min_periods=window).mean()


def calculate_ema(series: pd.Series, window: int = 20, alpha: float = None) -> pd.Series:
    """
    Calculate Exponential Moving Average.
    If alpha is not specified, uses alpha = 2 / (window + 1).
    """
    if alpha is None:
        return series.ewm(span=window, adjust=False).mean()
    else:
        return series.ewm(alpha=alpha, adjust=False).mean()


def calculate_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI) using Wilder's smoothing technique.
    Formula:
        RS = Smoothed Avg Gain / Smoothed Avg Loss
        RSI = 100 - (100 / (1 + RS))
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Wilder's smoothing: alpha = 1 / window
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # Fill edge cases
    rsi = rsi.fillna(50.0)
    return rsi


def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    Calculate Moving Average Convergence Divergence (MACD).
    Returns:
        macd_line = EMA(fast) - EMA(slow)
        signal_line = EMA(macd_line, signal)
        histogram = macd_line - signal_line
    """
    ema_fast = calculate_ema(series, window=fast)
    ema_slow = calculate_ema(series, window=slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, window=signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0):
    """
    Calculate Bollinger Bands:
        Middle Band = SMA(window)
        Upper Band = Middle + num_std * StdDev(window)
        Lower Band = Middle - num_std * StdDev(window)
        %B = (Close - Lower) / (Upper - Lower)
        Bandwidth = (Upper - Lower) / Middle
    """
    middle = series.rolling(window=window, min_periods=window).mean()
    std = series.rolling(window=window, min_periods=window).std()
    upper = middle + (num_std * std)
    lower = middle - (num_std * std)
    
    bandwidth = (upper - lower) / middle.replace(0, np.nan)
    pct_b = (series - lower) / (upper - lower).replace(0, np.nan)
    
    return upper, middle, lower, pct_b, bandwidth


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR) using Wilder's smoothing.
    TR = max(High - Low, |High - Close_prev|, |Low - Close_prev|)
    ATR = Smoothed TR over window
    """
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.ewm(alpha=1.0 / window, adjust=False).mean()
    return atr


def calculate_ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
                       tenkan_period: int = 9, kijun_period: int = 26,
                       senkou_span_b_period: int = 52, displacement: int = 26):
    """
    Calculate Ichimoku Kinko Hyo:
        Tenkan-sen (Conversion Line) = (Highest High + Lowest Low) / 2 over 9 periods
        Kijun-sen (Base Line) = (Highest High + Lowest Low) / 2 over 26 periods
        Senkou Span A (Leading Span A) = (Tenkan + Kijun) / 2 shifted forward by 26 periods
        Senkou Span B (Leading Span B) = (Highest High + Lowest Low) / 2 over 52 periods shifted forward by 26
        Chikou Span (Lagging Span) = Close shifted backward by 26 periods
    """
    tenkan = (high.rolling(window=tenkan_period).max() + low.rolling(window=tenkan_period).min()) / 2.0
    kijun = (high.rolling(window=kijun_period).max() + low.rolling(window=kijun_period).min()) / 2.0
    
    senkou_a = ((tenkan + kijun) / 2.0).shift(displacement)
    senkou_b = ((high.rolling(window=senkou_span_b_period).max() +
                 low.rolling(window=senkou_span_b_period).min()) / 2.0).shift(displacement)
    chikou = close.shift(-displacement)
    
    return tenkan, kijun, senkou_a, senkou_b, chikou


def build_indicator_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute comprehensive technical indicator columns for an OHLCV dataframe.
    Required columns in df: 'Open', 'High', 'Low', 'Close', 'Volume'
    """
    res = df.copy()
    close = res['Close']
    high = res['High']
    low = res['Low']
    
    # Moving Averages
    res['SMA_10'] = calculate_sma(close, 10)
    res['SMA_20'] = calculate_sma(close, 20)
    res['SMA_50'] = calculate_sma(close, 50)
    res['SMA_200'] = calculate_sma(close, 200)
    res['EMA_12'] = calculate_ema(close, 12)
    res['EMA_26'] = calculate_ema(close, 26)
    res['EMA_50'] = calculate_ema(close, 50)
    
    # RSI
    res['RSI_14'] = calculate_rsi(close, 14)
    res['RSI_7'] = calculate_rsi(close, 7)
    
    # MACD
    res['MACD_Line'], res['MACD_Signal'], res['MACD_Hist'] = calculate_macd(close, 12, 26, 9)
    
    # Bollinger Bands
    res['BB_Upper'], res['BB_Middle'], res['BB_Lower'], res['BB_PctB'], res['BB_Bandwidth'] = calculate_bollinger_bands(close, 20, 2.0)
    
    # ATR
    res['ATR_14'] = calculate_atr(high, low, close, 14)
    res['ATR_Pct'] = res['ATR_14'] / close
    
    # Ichimoku
    res['Ichimoku_Tenkan'], res['Ichimoku_Kijun'], res['Ichimoku_SenkouA'], res['Ichimoku_SenkouB'], res['Ichimoku_Chikou'] = calculate_ichimoku(high, low, close)
    
    # Volatility & Momentum
    res['Daily_Return'] = close.pct_change()
    res['Rolling_Vol_20'] = res['Daily_Return'].rolling(20).std() * np.sqrt(252)
    res['ROC_10'] = (close - close.shift(10)) / close.shift(10) * 100.0
    
    return res

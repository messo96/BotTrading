import numpy as np
import pandas as pd

def compute_rsi(close_series: pd.Series, period: int = 14) -> pd.Series:
    """Calcola il Relative Strength Index (RSI) con smoothing esponenziale."""
    delta = close_series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Media mobile esponenziale per gain e loss (formula Wilder)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def compute_ema(series: pd.Series, period: int) -> pd.Series:
    """Calcola la Media Mobile Esponenziale (EMA)."""
    return series.ewm(span=period, adjust=False).mean()

def compute_sma(series: pd.Series, period: int) -> pd.Series:
    """Calcola la Media Mobile Semplice (SMA)."""
    return series.rolling(window=period).mean()

def compute_bollinger_bands(close_series: pd.Series, period: int = 20, num_std: float = 2.0) -> dict:
    """Calcola le Bande di Bollinger e la percentuale %B."""
    middle = close_series.rolling(window=period).mean()
    std = close_series.rolling(window=period).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    bandwidth = ((upper - lower) / middle) * 100
    
    # %B = (Prezzo - Lower) / (Upper - Lower)
    pct_b = (close_series - lower) / (upper - lower).replace(0, np.nan)
    
    return {
        "bb_upper": upper,
        "bb_middle": middle,
        "bb_lower": lower,
        "bb_width": bandwidth,
        "bb_pct_b": pct_b
    }

def compute_macd(close_series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Calcola il MACD, la Signal Line e l'Istogramma."""
    ema_fast = close_series.ewm(span=fast, adjust=False).mean()
    ema_slow = close_series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        "macd": macd_line,
        "macd_signal": signal_line,
        "macd_hist": histogram
    }

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calcola l'Average True Range (ATR) per la misurazione della volatilità."""
    high = df['High']
    low = df['Low']
    close_prev = df['Close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    return atr

def compute_volume_metrics(df: pd.DataFrame, period: int = 20) -> dict:
    """Analizza il volume recente rispetto alla media storica."""
    vol = df['Volume']
    vol_sma = vol.rolling(window=period).mean()
    
    current_vol = float(vol.iloc[-1]) if len(vol) > 0 else 0.0
    avg_vol = float(vol_sma.iloc[-1]) if len(vol_sma) > 0 and not pd.isna(vol_sma.iloc[-1]) else 1.0
    
    surge_ratio = (current_vol / avg_vol) if avg_vol > 0 else 1.0
    
    return {
        "current_volume": current_vol,
        "avg_volume": avg_vol,
        "volume_surge_ratio": surge_ratio
    }

def find_key_levels(df: pd.DataFrame, lookback: int = 30) -> dict:
    """Individua i livelli recenti di minimo (supporto) e massimo (resistenza)."""
    sub_df = df.iloc[-lookback:] if len(df) >= lookback else df
    recent_low = float(sub_df['Low'].min())
    recent_high = float(sub_df['High'].max())
    
    return {
        "recent_support": recent_low,
        "recent_resistance": recent_high
    }

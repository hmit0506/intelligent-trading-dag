import numpy as np
import pandas as pd
import math


def calculate_trend_signals(prices_df):
    """Advanced trend following strategy using multiple timeframes and indicators."""
    ema_8 = calculate_ema(prices_df, 8)
    ema_21 = calculate_ema(prices_df, 21)
    ema_55 = calculate_ema(prices_df, 55)
    adx = calculate_adx(prices_df, 14)
    short_trend = ema_8 > ema_21
    medium_trend = ema_21 > ema_55
    adx_value = adx["adx"].iloc[-1] if not adx.empty else float('nan')
    trend_strength = adx_value / 100.0 if not pd.isna(adx_value) else 0.5
    if pd.isna(short_trend.iloc[-1]) or pd.isna(medium_trend.iloc[-1]):
        signal = "neutral"
        confidence = 0.5
    elif short_trend.iloc[-1] and medium_trend.iloc[-1]:
        signal = "bullish"
        confidence = trend_strength if not pd.isna(trend_strength) else 0.5
    elif not short_trend.iloc[-1] and not medium_trend.iloc[-1]:
        signal = "bearish"
        confidence = trend_strength if not pd.isna(trend_strength) else 0.5
    else:
        signal = "neutral"
        confidence = 0.5
    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "adx": float(adx_value) if not pd.isna(adx_value) else 0.0,
            "trend_strength": float(trend_strength) if not pd.isna(trend_strength) else 0.5,
        },
    }


def calculate_mean_reversion_signals(prices_df):
    """Mean reversion strategy using statistical measures and Bollinger Bands."""
    if len(prices_df) < 50:
        return {
            "signal": "neutral",
            "confidence": 0.5,
            "metrics": {"z_score": 0.0, "price_vs_bb": 0.5, "rsi_14": 50.0, "rsi_28": 50.0},
        }
    ma_50 = prices_df["close"].rolling(window=50, min_periods=1).mean()
    std_50 = prices_df["close"].rolling(window=50, min_periods=1).std()
    z_score = (prices_df["close"] - ma_50) / std_50.replace(0, pd.NA)
    bb_upper, bb_lower = calculate_bollinger_bands(prices_df)
    rsi_14 = calculate_rsi(prices_df, 14)
    rsi_28 = calculate_rsi(prices_df, 28)
    z_score_val = z_score.iloc[-1] if not z_score.empty else float('nan')
    bb_upper_val = bb_upper.iloc[-1] if not bb_upper.empty else float('nan')
    bb_lower_val = bb_lower.iloc[-1] if not bb_lower.empty else float('nan')
    rsi_14_val = rsi_14.iloc[-1] if not rsi_14.empty else float('nan')
    rsi_28_val = rsi_28.iloc[-1] if not rsi_28.empty else float('nan')
    if pd.isna(bb_upper_val) or pd.isna(bb_lower_val) or (bb_upper_val - bb_lower_val) == 0:
        price_vs_bb = 0.5
    else:
        price_vs_bb = (prices_df["close"].iloc[-1] - bb_lower_val) / (bb_upper_val - bb_lower_val)
    if pd.isna(z_score_val) or pd.isna(price_vs_bb):
        signal, confidence = "neutral", 0.5
    elif z_score_val < -2 and price_vs_bb < 0.2:
        signal, confidence = "bullish", min(abs(z_score_val) / 4, 1.0)
    elif z_score_val > 2 and price_vs_bb > 0.8:
        signal, confidence = "bearish", min(abs(z_score_val) / 4, 1.0)
    else:
        signal, confidence = "neutral", 0.5
    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "z_score": float(z_score_val) if not pd.isna(z_score_val) else 0.0,
            "price_vs_bb": float(price_vs_bb),
            "rsi_14": float(rsi_14_val) if not pd.isna(rsi_14_val) else 50.0,
            "rsi_28": float(rsi_28_val) if not pd.isna(rsi_28_val) else 50.0,
        },
    }


def calculate_momentum_signals(prices_df):
    """Multi-factor momentum strategy."""
    if len(prices_df) < 21:
        return {
            "signal": "neutral",
            "confidence": 0.5,
            "metrics": {"momentum_1m": 0.0, "momentum_3m": 0.0, "momentum_6m": 0.0, "volume_momentum": 1.0},
        }
    returns = prices_df["close"].pct_change()
    mom_1m = returns.rolling(21, min_periods=1).sum()
    mom_3m = returns.rolling(63, min_periods=1).sum()
    mom_6m = returns.rolling(126, min_periods=1).sum()
    volume_ma = prices_df["volume"].rolling(21, min_periods=1).mean()
    volume_momentum = prices_df["volume"] / volume_ma.replace(0, pd.NA)
    momentum_score = (0.4 * mom_1m + 0.3 * mom_3m + 0.3 * mom_6m).iloc[-1]
    volume_momentum_val = volume_momentum.iloc[-1] if not volume_momentum.empty else float('nan')
    volume_confirmation = not pd.isna(volume_momentum_val) and volume_momentum_val > 1.0
    if pd.isna(momentum_score):
        signal, confidence = "neutral", 0.5
    elif momentum_score > 0.05 and volume_confirmation:
        signal, confidence = "bullish", min(abs(momentum_score) * 5, 1.0)
    elif momentum_score < -0.05 and volume_confirmation:
        signal, confidence = "bearish", min(abs(momentum_score) * 5, 1.0)
    else:
        signal, confidence = "neutral", 0.5
    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "momentum_1m": float(mom_1m.iloc[-1]) if not pd.isna(mom_1m.iloc[-1]) else 0.0,
            "momentum_3m": float(mom_3m.iloc[-1]) if not pd.isna(mom_3m.iloc[-1]) else 0.0,
            "momentum_6m": float(mom_6m.iloc[-1]) if not pd.isna(mom_6m.iloc[-1]) else 0.0,
            "volume_momentum": float(volume_momentum_val) if not pd.isna(volume_momentum_val) else 1.0,
        },
    }


def calculate_volatility_signals(prices_df):
    """Volatility-based trading strategy."""
    if len(prices_df) < 21:
        return {
            "signal": "neutral",
            "confidence": 0.5,
            "metrics": {"historical_volatility": 0.0, "volatility_regime": 1.0, "volatility_z_score": 0.0, "atr_ratio": 0.0},
        }
    returns = prices_df["close"].pct_change()
    hist_vol = returns.rolling(21, min_periods=1).std() * math.sqrt(365)
    vol_ma = hist_vol.rolling(63, min_periods=1).mean()
    vol_regime = hist_vol / vol_ma.replace(0, pd.NA)
    vol_std = hist_vol.rolling(63, min_periods=1).std()
    vol_z_score = (hist_vol - vol_ma) / vol_std.replace(0, pd.NA)
    atr = calculate_atr(prices_df)
    atr_ratio = atr / prices_df["close"]
    current_vol_regime = vol_regime.iloc[-1] if not vol_regime.empty else float('nan')
    vol_z = vol_z_score.iloc[-1] if not vol_z_score.empty else float('nan')
    if pd.isna(current_vol_regime) or pd.isna(vol_z):
        signal, confidence = "neutral", 0.5
    elif current_vol_regime < 0.8 and vol_z < -1:
        signal, confidence = "bullish", min(abs(vol_z) / 3, 1.0)
    elif current_vol_regime > 1.2 and vol_z > 1:
        signal, confidence = "bearish", min(abs(vol_z) / 3, 1.0)
    else:
        signal, confidence = "neutral", 0.5
    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "historical_volatility": float(hist_vol.iloc[-1]) if not pd.isna(hist_vol.iloc[-1]) else 0.0,
            "volatility_regime": float(current_vol_regime) if not pd.isna(current_vol_regime) else 1.0,
            "volatility_z_score": float(vol_z) if not pd.isna(vol_z) else 0.0,
            "atr_ratio": float(atr_ratio.iloc[-1]) if not pd.isna(atr_ratio.iloc[-1]) else 0.0,
        },
    }


def calculate_stat_arb_signals(prices_df):
    """Statistical arbitrage signals based on price action analysis."""
    if len(prices_df) < 63:
        return {"signal": "neutral", "confidence": 0.5, "metrics": {"hurst_exponent": 0.5, "skewness": 0.0, "kurtosis": 0.0}}
    returns = prices_df["close"].pct_change()
    skew = returns.rolling(63, min_periods=1).skew()
    kurt = returns.rolling(63, min_periods=1).kurt()
    hurst = calculate_hurst_exponent(prices_df["close"])
    skew_val = skew.iloc[-1] if not skew.empty else float('nan')
    kurt_val = kurt.iloc[-1] if not kurt.empty else float('nan')
    if pd.isna(hurst) or pd.isna(skew_val):
        signal, confidence = "neutral", 0.5
    elif hurst < 0.4 and skew_val > 1:
        signal, confidence = "bullish", min((0.5 - hurst) * 2, 1.0)
    elif hurst < 0.4 and skew_val < -1:
        signal, confidence = "bearish", min((0.5 - hurst) * 2, 1.0)
    else:
        signal, confidence = "neutral", 0.5
    return {
        "signal": signal,
        "confidence": confidence,
        "metrics": {
            "hurst_exponent": float(hurst) if not pd.isna(hurst) else 0.5,
            "skewness": float(skew_val) if not pd.isna(skew_val) else 0.0,
            "kurtosis": float(kurt_val) if not pd.isna(kurt_val) else 0.0,
        },
    }


def weighted_signal_combination(signals, weights):
    """Combines multiple trading signals using a weighted approach."""
    signal_values = {"bullish": 1, "neutral": 0, "bearish": -1}
    weighted_sum = 0
    total_confidence = 0
    for strategy, signal in signals.items():
        numeric_signal = signal_values[signal["signal"]]
        weight = weights[strategy]
        confidence = signal["confidence"]
        weighted_sum += numeric_signal * weight * confidence
        total_confidence += weight * confidence
    if total_confidence > 0:
        final_score = weighted_sum / total_confidence
    else:
        final_score = 0
    if final_score > 0.2:
        signal = "bullish"
    elif final_score < -0.2:
        signal = "bearish"
    else:
        signal = "neutral"
    return {"signal": signal, "confidence": abs(final_score)}


def normalize_pandas(obj):
    """Convert pandas Series/DataFrames to primitive Python types."""
    if isinstance(obj, pd.Series):
        return obj.tolist()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict("records")
    elif isinstance(obj, dict):
        return {k: normalize_pandas(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [normalize_pandas(item) for item in obj]
    return obj


def calculate_rsi(prices_df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = prices_df["close"].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(prices_df: pd.DataFrame, window: int = 20) -> tuple:
    sma = prices_df["close"].rolling(window).mean()
    std_dev = prices_df["close"].rolling(window).std()
    upper_band = sma + (std_dev * 2)
    lower_band = sma - (std_dev * 2)
    return upper_band, lower_band


def calculate_ema(df: pd.DataFrame, window: int) -> pd.Series:
    return df["close"].ewm(span=window, adjust=False).mean()


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df = df.copy()
    df["high_low"] = df["high"] - df["low"]
    df["high_close"] = abs(df["high"] - df["close"].shift())
    df["low_close"] = abs(df["low"] - df["close"].shift())
    df["tr"] = df[["high_low", "high_close", "low_close"]].max(axis=1)
    df["up_move"] = df["high"] - df["high"].shift()
    df["down_move"] = df["low"].shift() - df["low"]
    df["plus_dm"] = np.where((df["up_move"] > df["down_move"]) & (df["up_move"] > 0), df["up_move"], 0)
    df["minus_dm"] = np.where((df["down_move"] > df["up_move"]) & (df["down_move"] > 0), df["down_move"], 0)
    df["+di"] = 100 * (df["plus_dm"].ewm(span=period).mean() / df["tr"].ewm(span=period).mean())
    df["-di"] = 100 * (df["minus_dm"].ewm(span=period).mean() / df["tr"].ewm(span=period).mean())
    df["dx"] = 100 * abs(df["+di"] - df["-di"]) / (df["+di"] + df["-di"])
    df["adx"] = df["dx"].ewm(span=period).mean()
    return df[["adx", "+di", "-di"]]


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean()


def calculate_hurst_exponent(price_series: pd.Series, max_lag: int = 20) -> float:
    lags = range(2, max_lag)
    tau = [max(1e-8, np.sqrt(np.std(np.subtract(price_series[lag:], price_series[:-lag])))) for lag in lags]
    try:
        reg = np.polyfit(np.log(lags), np.log(tau), 1)
        return reg[0]
    except (ValueError, RuntimeWarning):
        return 0.5

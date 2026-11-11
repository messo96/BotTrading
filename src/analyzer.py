from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.indicators import (
    compute_rsi,
    compute_ema,
    compute_sma,
    compute_bollinger_bands,
    compute_macd,
    compute_atr,
    compute_volume_metrics,
    find_key_levels
)
from src.config import STRATEGY_SETTINGS

def analyze_dataframe(ticker: str, df: pd.DataFrame, asset_type: str = "stock") -> Optional[Dict[str, Any]]:
    """
    Esegue l'analisi quantitativa e tecnica su un DataFrame storico di prezzi (Open, High, Low, Close, Volume).
    Restituisce un dizionario con indicatori, punteggio di opportunità (0-100), e piano di risk management.
    """
    if df is None or len(df) < 30:
        return None

    # Ordina per data crescente ed elimina righe non valide
    df = df.copy().dropna(subset=['Close', 'Volume'])
    if len(df) < 30:
        return None

    close = df['Close']
    current_price = float(close.iloc[-1])
    prev_close = float(close.iloc[-2]) if len(close) > 1 else current_price
    price_change_pct = ((current_price - prev_close) / prev_close) * 100
    
    five_days_change = 0.0
    if len(close) >= 5:
        p_5d = float(close.iloc[-5])
        five_days_change = ((current_price - p_5d) / p_5d) * 100

    # Calcolo indicatori
    rsi_series = compute_rsi(close, period=STRATEGY_SETTINGS["rsi_period"])
    current_rsi = float(rsi_series.iloc[-1])
    prev_rsi = float(rsi_series.iloc[-2]) if len(rsi_series) > 1 else current_rsi

    ema20_series = compute_ema(close, STRATEGY_SETTINGS["ema_short"])
    sma50_series = compute_sma(close, STRATEGY_SETTINGS["sma_medium"])
    sma200_series = compute_sma(close, STRATEGY_SETTINGS["sma_long"]) if len(close) >= 150 else None

    current_ema20 = float(ema20_series.iloc[-1])
    current_sma50 = float(sma50_series.iloc[-1]) if sma50_series is not None and not pd.isna(sma50_series.iloc[-1]) else current_ema20
    current_sma200 = float(sma200_series.iloc[-1]) if sma200_series is not None and not pd.isna(sma200_series.iloc[-1]) else None

    bb = compute_bollinger_bands(close, STRATEGY_SETTINGS["bollinger_period"], STRATEGY_SETTINGS["bollinger_std"])
    current_bb_upper = float(bb["bb_upper"].iloc[-1])
    current_bb_lower = float(bb["bb_lower"].iloc[-1])
    current_bb_width = float(bb["bb_width"].iloc[-1])
    current_pct_b = float(bb["bb_pct_b"].iloc[-1])

    macd_data = compute_macd(close)
    current_macd = float(macd_data["macd"].iloc[-1])
    current_macd_signal = float(macd_data["macd_signal"].iloc[-1])
    current_macd_hist = float(macd_data["macd_hist"].iloc[-1])
    prev_macd_hist = float(macd_data["macd_hist"].iloc[-2]) if len(macd_data["macd_hist"]) > 1 else current_macd_hist

    atr_series = compute_atr(df, STRATEGY_SETTINGS["atr_period"])
    current_atr = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else (current_price * 0.02)

    vol_metrics = compute_volume_metrics(df)
    key_levels = find_key_levels(df, lookback=25)

    # -----------------------------
    # MOTORE DI SCORING & PATTERN
    # -----------------------------
    score = 0
    signals = []

    # 1. Analisi Oscillazioni RSI
    if current_rsi <= STRATEGY_SETTINGS["rsi_oversold"]:
        # Condizione di ipervenduto estremo
        if current_rsi > prev_rsi:
            score += 30
            signals.append(f"🟢 Rimbalzo da Ipervenduto: RSI a {current_rsi:.1f} in risalita")
        else:
            score += 18
            signals.append(f"⚠️ Ipervenduto marcato: RSI a {current_rsi:.1f} (possibile bottom)")
    elif STRATEGY_SETTINGS["rsi_momentum_low"] <= current_rsi <= STRATEGY_SETTINGS["rsi_momentum_high"]:
        if current_rsi > prev_rsi:
            score += 20
            signals.append(f"🚀 Momentum rialzista solido: RSI a {current_rsi:.1f}")
        else:
            score += 12
    elif current_rsi >= STRATEGY_SETTINGS["rsi_overbought"]:
        score -= 15
        signals.append(f"🔴 Ipercomprato critico: RSI a {current_rsi:.1f} (rischio ritracciamento)")

    # 2. Trend & Allineamento Medie
    if current_sma200 is not None:
        if current_price > current_sma200:
            score += 15
            signals.append("📈 Trend Primario Rialzista (Prezzo sopra la SMA 200)")
        else:
            score -= 10
            signals.append("📉 Sotto la SMA 200 (Macro trend debole)")

    if current_price > current_ema20 and current_price > current_sma50:
        score += 15
        signals.append("✨ Prezzo sopra EMA 20 e SMA 50 (Setup a breve rialzista)")
    elif current_price > current_ema20:
        score += 8

    # 3. Bande di Bollinger
    if current_pct_b <= 0.20:
        score += 15
        signals.append(f"🎯 Prezzo a ridosso della Banda Inferiore di Bollinger (Supporto dinamico)")
    elif current_pct_b >= 0.85:
        score -= 5
        signals.append(f"⚠️ Prezzo vicino alla Banda Superiore di Bollinger (Resistenza)")

    # 4. MACD
    if current_macd > current_macd_signal and current_macd_hist > prev_macd_hist:
        score += 10
        signals.append("⚡ MACD con incrocio rialzista ed espansione positiva")

    # 5. Volumi
    vol_ratio = vol_metrics["volume_surge_ratio"]
    if vol_ratio >= STRATEGY_SETTINGS["volume_surge_multiplier"]:
        score += 15
        signals.append(f"🔥 Spike di Volume anomalo ({vol_ratio:.1f}x la media a 20 giorni)")
    elif vol_ratio >= 1.05:
        score += 5

    # Normalizzazione punteggio finale tra 0 e 100
    final_score = max(0, min(100, score))

    # Definizione del verdetto
    if final_score >= 70:
        verdict = "FORTE BUY (Opportunità Top)"
        verdict_icon = "🟢"
    elif final_score >= 55:
        verdict = "BUY MODERATO (Buon setup)"
        verdict_icon = "🟡"
    elif final_score >= 40:
        verdict = "NEUTRALE / ATTESA (In osservazione)"
        verdict_icon = "⚪"
    else:
        verdict = "EVITA / PRESA DI BENEFICIO"
        verdict_icon = "🔴"

    # -----------------------------
    # PIANO DI RISK MANAGEMENT
    # -----------------------------
    # Stop loss basato su ATR o minimo recente
    sl_distance = current_atr * STRATEGY_SETTINGS["atr_sl_multiplier"]
    stop_loss = round(max(current_price - sl_distance, key_levels["recent_support"] * 0.995), 4)
    
    # Se per qualche motivo lo stop loss risultasse troppo vicino o lontano:
    if stop_loss >= current_price or ((current_price - stop_loss) / current_price) < 0.01:
        stop_loss = round(current_price * 0.96, 4)  # 4% di sicurezza

    risk_amount = current_price - stop_loss
    take_profit_1 = round(current_price + (risk_amount * 1.5), 4)
    take_profit_2 = round(current_price + (risk_amount * 2.5), 4)
    risk_reward_ratio = round((take_profit_2 - current_price) / risk_amount, 2) if risk_amount > 0 else 2.5

    return {
        "ticker": ticker,
        "asset_type": asset_type,
        "current_price": current_price,
        "price_change_pct": price_change_pct,
        "five_days_change": five_days_change,
        "score": final_score,
        "verdict": verdict,
        "verdict_icon": verdict_icon,
        "signals": signals,
        "rsi": round(current_rsi, 1),
        "ema20": round(current_ema20, 2),
        "sma50": round(current_sma50, 2),
        "sma200": round(current_sma200, 2) if current_sma200 is not None else "N/A",
        "volume_surge": round(vol_ratio, 2),
        "entry_range": (round(current_price * 0.995, 4), round(current_price * 1.005, 4)),
        "stop_loss": stop_loss,
        "stop_loss_pct": round(((stop_loss - current_price) / current_price) * 100, 2),
        "take_profit_1": take_profit_1,
        "take_profit_1_pct": round(((take_profit_1 - current_price) / current_price) * 100, 2),
        "take_profit_2": take_profit_2,
        "take_profit_2_pct": round(((take_profit_2 - current_price) / current_price) * 100, 2),
        "risk_reward_ratio": risk_reward_ratio
    }


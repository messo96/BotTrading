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
    Valuta sia opportunità RIALZISTE (BUY / Long) che RIBASSISTE (SELL / Short) e formula il piano operativo.
    """
    if df is None or len(df) < 30:
        return None

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
    vol_ratio = vol_metrics["volume_surge_ratio"]

    # =========================================================================
    # 1. VALUTAZIONE SEGNALI BUY (LONG)
    # =========================================================================
    buy_score = 0
    buy_signals = []

    # Oscillatore RSI (Rialzista)
    if current_rsi <= STRATEGY_SETTINGS["rsi_oversold"]:
        if current_rsi > prev_rsi:
            buy_score += 30
            buy_signals.append(f"🟢 Rimbalzo da Ipervenduto: RSI a {current_rsi:.1f} in ripartenza verso l'alto")
        else:
            buy_score += 15
            buy_signals.append(f"🟢 Ipervenduto marcato: RSI a {current_rsi:.1f} (in cerca di supporto)")
    elif 48 <= current_rsi <= STRATEGY_SETTINGS["rsi_momentum_high"]:
        if current_rsi > prev_rsi:
            buy_score += 25
            buy_signals.append(f"🚀 Momentum rialzista solido: RSI a {current_rsi:.1f}")
        else:
            buy_score += 15

    # Trend e Medie Mobili (Rialzista)
    if current_sma200 is not None and current_price > current_sma200:
        buy_score += 15
        buy_signals.append("📈 Trend Macro Rialzista (Prezzo sopra la SMA 200)")
    if current_price > current_ema20 and current_price > current_sma50:
        buy_score += 15
        buy_signals.append("✨ Prezzo sopra EMA 20 e SMA 50 (Allineamento rialzista)")
    elif current_price > current_ema20:
        buy_score += 10

    # Bande di Bollinger (Rialzista)
    if current_pct_b <= 0.22 and current_price > current_bb_lower:
        buy_score += 15
        buy_signals.append("🎯 Prezzo a contatto con la Banda Inferiore di Bollinger (Supporto dinamico)")

    # MACD (Rialzista)
    if current_macd > current_macd_signal and current_macd_hist > prev_macd_hist:
        buy_score += 10
        buy_signals.append("⚡ MACD con crossover rialzista e istogramma in espansione")

    # Volume Surge su giornata positiva
    if vol_ratio >= STRATEGY_SETTINGS["volume_surge_multiplier"] and price_change_pct >= -0.3:
        buy_score += 15
        buy_signals.append(f"🔥 Spike di Volume in acquisto ({vol_ratio:.1f}x la media a 20 periodi)")

    # =========================================================================
    # 2. VALUTAZIONE SEGNALI SELL (SHORT)
    # =========================================================================
    sell_score = 0
    sell_signals = []

    # Oscillatore RSI (Ribassista)
    if current_rsi >= 65 and current_rsi < prev_rsi:
        sell_score += 30
        sell_signals.append(f"🔴 Rifiuto da Ipercomprato: RSI a {current_rsi:.1f} in discesa (Top di breve)")
    elif current_rsi >= STRATEGY_SETTINGS["rsi_overbought"]:
        sell_score += 20
        sell_signals.append(f"🔴 Ipercomprato critico: RSI a {current_rsi:.1f} (forte estensione rialzista)")
    elif current_rsi <= 50 and current_rsi < prev_rsi:
        sell_score += 25
        sell_signals.append(f"🔻 Accelerazione ribassista: RSI a {current_rsi:.1f} in flessione")
    elif current_rsi < 50:
        sell_score += 15

    # Trend e Medie Mobili (Ribassista)
    if current_sma200 is not None and current_price < current_sma200:
        sell_score += 15
        sell_signals.append("📉 Trend Macro Ribassista (Prezzo sotto la SMA 200)")
    if current_price < current_ema20 and current_price < current_sma50:
        sell_score += 20
        sell_signals.append("⚠️ Prezzo sotto EMA 20 e SMA 50 (Allineamento ribassista)")
    elif current_price < current_ema20:
        sell_score += 10

    # Bande di Bollinger (Ribassista)
    if current_pct_b >= 0.80 and current_price < current_bb_upper:
        sell_score += 15
        sell_signals.append("🎯 Rifiuto dalla Banda Superiore di Bollinger (Resistenza dinamica)")
    elif current_pct_b <= 0.15 and current_rsi <= prev_rsi:
        sell_score += 15
        sell_signals.append("💥 Pressione ribassista con rottura della Banda Inferiore")

    # MACD (Ribassista)
    if current_macd < current_macd_signal or current_macd_hist < prev_macd_hist:
        sell_score += 10
        sell_signals.append("⚡ MACD con incrocio ribassista e divergenza negativa")

    # Volume Surge su giornata negativa (scarico/vendite)
    if vol_ratio >= STRATEGY_SETTINGS["volume_surge_multiplier"] and price_change_pct <= 0.3:
        sell_score += 15
        sell_signals.append(f"🔥 Forte pressione di vendita con volumi ({vol_ratio:.1f}x la media)")

    # =========================================================================
    # 3. DETERMINAZIONE DELLA DIREZIONE PREVALENTE (BUY vs SELL)
    # =========================================================================
    buy_score = max(0, min(100, buy_score))
    sell_score = max(0, min(100, sell_score))

    sl_distance = current_atr * STRATEGY_SETTINGS["atr_sl_multiplier"]

    if buy_score >= sell_score and buy_score >= 45:
        action = "BUY"
        final_score = buy_score
        signals = buy_signals
        if final_score >= 70:
            verdict = "FORTE BUY (LONG)"
            verdict_icon = "🟢"
        else:
            verdict = "BUY MODERATO (LONG)"
            verdict_icon = "🟡"

        # Piano di trade BUY (Long)
        stop_loss = round(max(current_price - sl_distance, key_levels["recent_support"] * 0.995), 4)
        if stop_loss >= current_price or ((current_price - stop_loss) / current_price) < 0.01:
            stop_loss = round(current_price * 0.96, 4)
        
        risk_amount = current_price - stop_loss
        take_profit_1 = round(current_price + (risk_amount * 1.5), 4)
        take_profit_2 = round(current_price + (risk_amount * 2.5), 4)
        risk_reward_ratio = round((take_profit_2 - current_price) / risk_amount, 2) if risk_amount > 0 else 2.5

    elif sell_score > buy_score and sell_score >= 45:
        action = "SELL"
        final_score = sell_score
        signals = sell_signals
        if final_score >= 70:
            verdict = "FORTE SELL (SHORT)"
            verdict_icon = "🔴"
        else:
            verdict = "SELL MODERATO (SHORT)"
            verdict_icon = "🟠"

        # Piano di trade SELL (Short): Stop loss SOPRA il prezzo corrente
        stop_loss = round(min(current_price + sl_distance, key_levels["recent_resistance"] * 1.005), 4)
        if stop_loss <= current_price or ((stop_loss - current_price) / current_price) < 0.01:
            stop_loss = round(current_price * 1.04, 4)
        
        risk_amount = stop_loss - current_price
        # Take profit SOTTO il prezzo corrente
        take_profit_1 = round(current_price - (risk_amount * 1.5), 4)
        take_profit_2 = round(current_price - (risk_amount * 2.5), 4)
        risk_reward_ratio = round((current_price - take_profit_2) / risk_amount, 2) if risk_amount > 0 else 2.5

    else:
        # Nessun setup direzionale forte (fase neutrale)
        action = "NEUTRAL"
        final_score = max(buy_score, sell_score)
        signals = buy_signals if buy_score >= sell_score else sell_signals
        verdict = "NEUTRALE / ATTESA (In osservazione)"
        verdict_icon = "⚪"

        stop_loss = round(current_price - sl_distance, 4)
        risk_amount = current_price - stop_loss
        take_profit_1 = round(current_price + (risk_amount * 1.5), 4)
        take_profit_2 = round(current_price + (risk_amount * 2.5), 4)
        risk_reward_ratio = 2.0

    stop_loss_pct = round(((stop_loss - current_price) / current_price) * 100, 2)
    take_profit_1_pct = round(((take_profit_1 - current_price) / current_price) * 100, 2)
    take_profit_2_pct = round(((take_profit_2 - current_price) / current_price) * 100, 2)

    return {
        "ticker": ticker,
        "asset_type": asset_type,
        "current_price": current_price,
        "price_change_pct": price_change_pct,
        "five_days_change": five_days_change,
        "action": action,
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
        "stop_loss_pct": stop_loss_pct,
        "take_profit_1": take_profit_1,
        "take_profit_1_pct": take_profit_1_pct,
        "take_profit_2": take_profit_2,
        "take_profit_2_pct": take_profit_2_pct,
        "risk_reward_ratio": risk_reward_ratio
    }

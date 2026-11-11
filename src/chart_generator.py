import io
from typing import Dict, Any, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from src.indicators import compute_ema, compute_sma, compute_bollinger_bands, compute_rsi

def generate_technical_chart(ticker: str, df: pd.DataFrame, analysis: Dict[str, Any]) -> Optional[io.BytesIO]:
    """
    Genera un grafico tecnico in stile TradingView (Dark Mode) con:
    - Prezzo, EMA 20, SMA 50, SMA 200, Bande di Bollinger
    - Livelli chiave: Entry, Stop Loss (Rosso), Take Profit 1 e 2 (Verde)
    - Oscillatore RSI con bande di ipervenduto e ipercomprato
    Restituisce un buffer BytesIO in memoria contenente l'immagine PNG.
    """
    if df is None or len(df) < 25:
        return None

    # Utilizziamo gli ultimi 60 giorni per chiarezza visiva
    plot_df = df.iloc[-60:].copy()
    close = plot_df["Close"]
    dates = plot_df.index

    # Calcolo indicatori sul subset
    ema20 = compute_ema(df["Close"], 20).iloc[-60:]
    sma50 = compute_sma(df["Close"], 50).iloc[-60:]
    bb = compute_bollinger_bands(df["Close"])
    bb_upper = bb["bb_upper"].iloc[-60:]
    bb_lower = bb["bb_lower"].iloc[-60:]
    rsi = compute_rsi(df["Close"]).iloc[-60:]

    has_sma200 = len(df) >= 150
    sma200 = compute_sma(df["Close"], 200).iloc[-60:] if has_sma200 else None

    # Palette colori TradingView Dark
    bg_color = "#131722"
    panel_color = "#1e222d"
    text_color = "#d1d4dc"
    grid_color = "#2a2e39"

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 6.5),
        dpi=130,
        gridspec_kw={"height_ratios": [3, 1]},
        facecolor=bg_color
    )

    # -----------------------------
    # PANNELLO 1: PREZZO & LIVELLI
    # -----------------------------
    ax1.set_facecolor(panel_color)
    ax1.plot(dates, close, label=f"Prezzo ({close.iloc[-1]:.2f})", color="#2962ff", linewidth=2.0)
    ax1.plot(dates, ema20, label="EMA 20", color="#ff9800", linewidth=1.2, alpha=0.9)
    ax1.plot(dates, sma50, label="SMA 50", color="#00bcd4", linewidth=1.2, alpha=0.9)
    
    if has_sma200 and sma200 is not None and not sma200.isna().all():
        ax1.plot(dates, sma200, label="SMA 200", color="#ab47bc", linewidth=1.4, linestyle="--", alpha=0.9)

    # Bande di Bollinger
    ax1.plot(dates, bb_upper, color="#787b86", linestyle=":", linewidth=0.8)
    ax1.plot(dates, bb_lower, color="#787b86", linestyle=":", linewidth=0.8)
    ax1.fill_between(dates, bb_lower, bb_upper, color="#787b86", alpha=0.08, label="Bollinger Bands")

    # Livelli Operativi
    curr_p = analysis["current_price"]
    sl = analysis["stop_loss"]
    tp1 = analysis["take_profit_1"]
    tp2 = analysis["take_profit_2"]

    ax1.axhline(sl, color="#ef5350", linestyle="--", linewidth=1.5, label=f"Stop Loss: {sl:.2f}")
    ax1.axhline(tp1, color="#26a69a", linestyle=":", linewidth=1.4, label=f"Take Profit 1: {tp1:.2f}")
    ax1.axhline(tp2, color="#00e676", linestyle="--", linewidth=1.5, label=f"Take Profit 2: {tp2:.2f}")

    # Annotazioni visive sui livelli a destra
    last_date = dates[-1]
    ax1.text(last_date, sl, f" SL ({analysis['stop_loss_pct']}%)", color="#ef5350", fontsize=8, va="center", weight="bold")
    ax1.text(last_date, tp1, f" TP1 ({analysis['take_profit_1_pct']}%)", color="#26a69a", fontsize=8, va="center")
    ax1.text(last_date, tp2, f" TP2 ({analysis['take_profit_2_pct']}%)", color="#00e676", fontsize=8, va="center", weight="bold")

    score = analysis["score"]
    verdict = analysis["verdict"]
    ax1.set_title(f"{ticker} — Swing Setup [Score: {score}/100 | {verdict}]", color=text_color, fontsize=12, pad=10, weight="bold")
    ax1.grid(True, color=grid_color, linestyle="--", linewidth=0.5, alpha=0.7)
    ax1.tick_params(colors=text_color, labelsize=8)
    ax1.legend(loc="upper left", facecolor=bg_color, edgecolor=grid_color, labelcolor=text_color, fontsize=7.5, ncol=2)

    # -----------------------------
    # PANNELLO 2: OSCILLATORE RSI
    # -----------------------------
    ax2.set_facecolor(panel_color)
    ax2.plot(dates, rsi, color="#b388ff", linewidth=1.5, label=f"RSI 14 ({rsi.iloc[-1]:.1f})")
    ax2.axhline(70, color="#ef5350", linestyle="--", linewidth=0.8)
    ax2.axhline(30, color="#26a69a", linestyle="--", linewidth=0.8)
    ax2.axhline(50, color=grid_color, linestyle=":", linewidth=0.7)
    ax2.fill_between(dates, 30, 70, color="#787b86", alpha=0.1)

    ax2.set_ylim(10, 90)
    ax2.set_yticks([30, 50, 70])
    ax2.grid(True, color=grid_color, linestyle="--", linewidth=0.5, alpha=0.7)
    ax2.tick_params(colors=text_color, labelsize=8)
    ax2.legend(loc="upper left", facecolor=bg_color, edgecolor=grid_color, labelcolor=text_color, fontsize=7.5)

    # Formattazione date asse X
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.setp(ax2.get_xticklabels(), rotation=0, ha="center")

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf


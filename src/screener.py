import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import yfinance as yf
from src.config import ALL_TICKERS, USA_TICKERS, EU_TICKERS, CRYPTO_TICKERS
from src.watchlist import load_watchlist
from src.analyzer import analyze_dataframe

logger = logging.getLogger(__name__)

def detect_asset_type(ticker: str) -> str:
    """Riconosce la tipologia di asset dal simbolo."""
    ticker_upper = ticker.upper()
    if ticker_upper.endswith("-USD") or ticker_upper.endswith("-EUR"):
        return "crypto"
    if any(ticker_upper.endswith(ext) for ext in [".MI", ".AS", ".DE", ".PA", ".MC", ".L"]):
        return "eu"
    return "usa"

def analyze_single_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """Scarica lo storico ed esegue l'analisi completa su un singolo ticker."""
    ticker = ticker.upper().strip()
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1y")
        if df.empty or len(df) < 30:
            return None
        asset_type = detect_asset_type(ticker)
        return analyze_dataframe(ticker, df, asset_type=asset_type)
    except Exception as e:
        logger.error(f"Errore durante l'analisi del ticker {ticker}: {e}")
        return None

def scan_tickers_list(tickers: List[str]) -> List[Dict[str, Any]]:
    """Esegue la scansione in batch di una lista di ticker e restituisce i risultati ordinati per score."""
    if not tickers:
        return []
    
    unique_tickers = list(dict.fromkeys([t.upper().strip() for t in tickers]))
    results = []

    try:
        data = yf.download(unique_tickers, period="1y", group_by="ticker", progress=False, threads=True)
        
        is_multi = len(unique_tickers) > 1 and isinstance(data.columns, pd.MultiIndex)
        
        for t in unique_tickers:
            try:
                if is_multi:
                    if t in data.columns.levels[0]:
                        df_ticker = data[t].dropna(how="all")
                    else:
                        continue
                else:
                    df_ticker = data.dropna(how="all")
                
                if df_ticker.empty or len(df_ticker) < 30:
                    continue
                
                asset_type = detect_asset_type(t)
                analysis = analyze_dataframe(t, df_ticker, asset_type=asset_type)
                if analysis:
                    results.append(analysis)
            except Exception as item_err:
                logger.warning(f"Errore elaborazione ticker {t}: {item_err}")
                continue

    except Exception as batch_err:
        logger.error(f"Errore nel download batch: {batch_err}")
        # Fallback a download sequenziale per i primi 10
        for t in unique_tickers[:10]:
            res = analyze_single_ticker(t)
            if res:
                results.append(res)

    # Ordina i risultati dal punteggio più alto a quello più basso
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

def run_market_screener(category: str = "all", top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Esegue lo screening del mercato selezionato ('all', 'usa', 'eu', 'crypto', 'watchlist').
    Ritorna la top N delle migliori opportunità con il punteggio più alto.
    """
    category = category.lower().strip()
    
    if category == "watchlist":
        tickers = load_watchlist()
    elif category == "usa":
        tickers = USA_TICKERS
    elif category == "eu":
        tickers = EU_TICKERS
    elif category == "crypto":
        tickers = CRYPTO_TICKERS
    elif category == "all":
        # Seleziona un mix bilanciato dei vari mercati
        tickers = USA_TICKERS + EU_TICKERS + CRYPTO_TICKERS
    else:
        tickers = USA_TICKERS

    all_results = scan_tickers_list(tickers)
    return all_results[:top_n]

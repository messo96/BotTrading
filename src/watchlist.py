import json
from pathlib import Path
from typing import List
from src.config import WATCHLIST_FILE

# Default iniziale della watchlist
DEFAULT_WATCHLIST = [
    "AAPL", "NVDA", "TSLA", "ENI.MI", "ISP.MI", "BTC-USD", "ETH-USD"
]

def load_watchlist() -> List[str]:
    """Carica la lista dei ticker preferiti dell'utente."""
    if not WATCHLIST_FILE.exists():
        save_watchlist(DEFAULT_WATCHLIST)
        return DEFAULT_WATCHLIST
    try:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return DEFAULT_WATCHLIST
    except Exception:
        return DEFAULT_WATCHLIST

def save_watchlist(tickers: List[str]) -> None:
    """Salva la lista dei ticker preferiti su file JSON."""
    WATCHLIST_FILE.parent.mkdir(exist_ok=True, parents=True)
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(set(tickers))), f, indent=2)

def add_to_watchlist(ticker: str) -> bool:
    """Aggiunge un ticker alla watchlist se non presente."""
    ticker = ticker.upper().strip()
    tickers = load_watchlist()
    if ticker in tickers:
        return False
    tickers.append(ticker)
    save_watchlist(tickers)
    return True

def remove_from_watchlist(ticker: str) -> bool:
    """Rimuove un ticker dalla watchlist."""
    ticker = ticker.upper().strip()
    tickers = load_watchlist()
    if ticker not in tickers:
        return False
    tickers.remove(ticker)
    save_watchlist(tickers)
    return True

import os
from pathlib import Path
from dotenv import load_dotenv

# Carica variabili da .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Timezone & Orari Briefing
TIMEZONE = os.getenv("TIMEZONE", "Europe/Rome").strip()
MORNING_BRIEFING_TIME = os.getenv("MORNING_BRIEFING_TIME", "08:30").strip()
AFTERNOON_BRIEFING_TIME = os.getenv("AFTERNOON_BRIEFING_TIME", "15:00").strip()

# Path Watchlist & Dati
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
WATCHLIST_FILE = DATA_DIR / "watchlist.json"

# Universi di Mercato di default
USA_TICKERS = [
    # Big Tech & AI
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "AVGO", "ARM", "PLTR",
    # Semiconductors & Hardware
    "QCOM", "INTC", "MU", "SMCI",
    # Consumer & Financials & Healthcare
    "JPM", "V", "LLY", "UNH", "COST", "WMT", "NFLX", "CRM", "DIS", "BA",
    # Crypto/Fintech proxies & ETF di riferimento
    "COIN", "SPY", "QQQ"
]

EU_TICKERS = [
    # FTSE MIB (Piazza Affari - Italia)
    "ENI.MI", "ISP.MI", "UCG.MI", "RACE.MI", "STMMI.MI", "ENEL.MI",
    "PRY.MI", "BAMI.MI", "G.MI", "TEN.MI", "MB.MI", "A2A.MI", "MONC.MI",
    # Leader Europei (Euro Stoxx)
    "ASML.AS", "SAP.DE", "MC.PA", "TTE.PA", "AIR.PA", "SIE.DE"
]

CRYPTO_TICKERS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "AVAX-USD", "DOGE-USD", "LINK-USD", "DOT-USD",
    "NEAR-USD", "SUI-USD"
]

# Dizionario raggruppato
ALL_TICKERS = {
    "usa": USA_TICKERS,
    "eu": EU_TICKERS,
    "crypto": CRYPTO_TICKERS
}

# Parametri Strategia Swing Trading
STRATEGY_SETTINGS = {
    "rsi_period": 14,
    "rsi_oversold": 35,
    "rsi_momentum_low": 50,
    "rsi_momentum_high": 68,
    "rsi_overbought": 72,
    "volume_surge_multiplier": 1.25,
    "ema_short": 20,
    "sma_medium": 50,
    "sma_long": 200,
    "bollinger_period": 20,
    "bollinger_std": 2.0,
    "atr_period": 14,
    "atr_sl_multiplier": 1.8,
    "min_risk_reward_ratio": 1.8
}


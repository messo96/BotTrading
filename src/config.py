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

# ==============================================================================
# ALIAS TICKER (Mappatura nomi comuni -> Simboli Yahoo Finance ufficiali)
# Permette all'utente di digitare /analizza XAUUSD, /analizza CRUDE, ecc.
# ==============================================================================
TICKER_ALIASES = {
    # Oro & Metalli preziosi
    "XAUUSD": "GC=F",
    "GOLD": "GC=F",
    "ORO": "GC=F",
    "SILVER": "SI=F",
    "ARGENTO": "SI=F",
    "COPPER": "HG=F",
    "RAME": "HG=F",

    # Energia & Petrolio
    "CRUDE": "CL=F",
    "OIL": "CL=F",
    "PETROLIO": "CL=F",
    "WTI": "CL=F",
    "BRENT": "BZ=F",
    "NATGAS": "NG=F",
    "GAS": "NG=F",

    # Indici & Futures Americani
    "TECH100": "NQ=F",
    "NAS100": "NQ=F",
    "NASDAQ": "NQ=F",
    "NASDAQ100": "NQ=F",
    "NDX": "NQ=F",
    "SP500": "ES=F",
    "US500": "ES=F",
    "S&P500": "ES=F",
    "US30": "YM=F",
    "DOW": "YM=F",
    "DOWJONES": "YM=F",
    "RUSSELL": "RTY=F",
    "US2000": "RTY=F",

    # Valute Forex principali
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",

    # Crypto (senza bisogno di digitare -USD)
    "BTC": "BTC-USD",
    "BITCOIN": "BTC-USD",
    "ETH": "ETH-USD",
    "ETHEREUM": "ETH-USD",
    "SOL": "SOL-USD",
    "SOLANA": "SOL-USD",
    "XRP": "XRP-USD",
    "RIPPLE": "XRP-USD",
    "DOGE": "DOGE-USD",

    # Macro & Volatilità
    "DXY": "DX-Y.NYB",
    "DOLLARO": "DX-Y.NYB",
    "VIX": "^VIX",
    "SOX": "SOXX",
    "SEMICONDUCTORS": "SOXX",
    "DAX": "^GDAXI"
}

# Nomi descrittivi per la visualizzazione nei report e nei grafici
TICKER_NAMES = {
    "GC=F": "XAU/USD (Oro / Gold)",
    "CL=F": "CRUDE OIL (Petrolio WTI)",
    "BZ=F": "BRENT (Petrolio Brent)",
    "SI=F": "SILVER (Argento)",
    "NG=F": "NATURAL GAS (Gas Naturale)",
    "HG=F": "COPPER (Rame)",
    "NQ=F": "TECH100 (Nasdaq 100 Futures)",
    "ES=F": "US500 (S&P 500 Futures)",
    "YM=F": "US30 (Dow Jones 30 Futures)",
    "RTY=F": "RUSSELL 2000 (US Small Cap)",
    "DX-Y.NYB": "DOLLAR INDEX (DXY)",
    "^VIX": "VIX (Indice di Volatilità)",
    "SOXX": "SOX (Semiconductor Index)",
    "^GDAXI": "DAX 40 (Germania)",
    "EURUSD=X": "EUR/USD (Euro/Dollaro)",
    "BTC-USD": "Bitcoin (BTC)",
    "ETH-USD": "Ethereum (ETH)",
    "SOL-USD": "Solana (SOL)",
    "XRP-USD": "Ripple (XRP)"
}

# ==============================================================================
# UNIVERSI DI MERCATO MONITORATI
# ==============================================================================

# Commodities / Materie Prime (Futures benchmark)
COMMODITIES_TICKERS = [
    "GC=F",  # Oro (XAUUSD)
    "CL=F",  # Petrolio Greggio WTI (Crude Oil)
    "BZ=F",  # Petrolio Brent
    "SI=F",  # Argento
    "NG=F",  # Gas Naturale
    "HG=F"   # Rame
]

# Indici & Futures Americani
INDICES_TICKERS = [
    "NQ=F",  # Tech 100 / Nasdaq 100 Futures
    "ES=F",  # US 500 / S&P 500 Futures
    "YM=F",  # US 30 / Dow Jones Futures
    "RTY=F"  # Russell 2000 Futures
]

# Azionario USA (Large Cap & High Momentum)
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

# Azionario Italiano ed Europeo (Piazza Affari & Euro Stoxx)
EU_TICKERS = [
    # FTSE MIB (Piazza Affari - Italia)
    "ENI.MI", "ISP.MI", "UCG.MI", "RACE.MI", "STMMI.MI", "ENEL.MI",
    "PRY.MI", "BAMI.MI", "G.MI", "TEN.MI", "MB.MI", "A2A.MI", "MONC.MI",
    # Leader Europei (Euro Stoxx)
    "ASML.AS", "SAP.DE", "MC.PA", "TTE.PA", "AIR.PA", "SIE.DE"
]

# Criptovalute Principali (24/7)
CRYPTO_TICKERS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "AVAX-USD", "DOGE-USD", "LINK-USD", "DOT-USD",
    "NEAR-USD", "SUI-USD"
]

# Dizionario raggruppato
ALL_TICKERS = {
    "commodities": COMMODITIES_TICKERS,
    "indici": INDICES_TICKERS,
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

# Configurazione Alert Intraday sulla Watchlist
ALERTS_CONFIG = {
    "enabled": True,
    "check_interval_seconds": 1800,  # Controllo automatico ogni 30 minuti
    "cooldown_seconds": 10800,       # Minimo 3 ore tra due alert consecutivi sullo stesso ticker
    "rsi_oversold_alert": 33,        # Alert se RSI <= 33 (Ipervenduto / Rimbalzo)
    "rsi_overbought_alert": 72,      # Alert se RSI >= 72 (Ipercomprato / Presa profitto)
    "volume_surge_alert": 1.8,       # Alert se volume >= 1.8x la media
    "score_threshold_alert": 70      # Alert se Score >= 70 (Forte opportunità)
}

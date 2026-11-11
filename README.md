# 🤖 Trading Broker Assistant Bot (Telegram)

Un assistente algoritmico consultivo per **Telegram** progettato per affiancarti nello **Swing Trading** sui mercati finanziari:
- 🥇 **Commodities & Metalli:** Oro (XAU/USD), Petrolio (Crude WTI & Brent), Argento, Gas Naturale, Rame.
- 📈 **Indici & Futures Americani:** Tech 100 (Nasdaq 100), US 500 (S&P 500), US 30 (Dow Jones), Russell 2000.
- 🇺🇸 **Azionario USA:** Big Tech (Nvidia, Apple, Microsoft, Tesla, AMD, Palantir, ecc.) e blue chip.
- 🇪🇺 **Piazza Affari & Europa:** FTSE MIB (Eni, Intesa Sanpaolo, Ferrari, Unicredit, STM) ed Euro Stoxx.
- 🪙 **Criptovalute:** Bitcoin, Ethereum, Solana e principali altcoin (24/7).

> ⚠️ **DISCLAIMER:** Questo bot ha scopo puramente **informativo, analitico e consultivo**. Non si collega al tuo conto broker e non effettua ordini automatici. La decisione finale di acquisto o vendita e la gestione del rischio rimangono al 100% sotto la tua responsabilità.

---

## 🎯 Cosa Fa il Bot

1. **Scansione Intelligente delle Oscillazioni:**
   - **RSI (14)**: Rileva rimbalzi da ipervenduto (<35) e momentum rialzista consolidato (50-68).
   - **Trend e Medie Mobili**: Valuta l'allineamento con EMA 20, SMA 50 e il macro trend sopra la SMA 200.
   - **Bande di Bollinger**: Intercetta compressioni di volatilità (squeeze) e rimbalzi sulla banda inferiore.
   - **Volume Surge**: Verifica se il volume odierno supera la media storica a 20 periodi (ingresso istituzionale).
2. **Punteggio Quantitativo (0-100)**: Assegna a ogni asset un punteggio oggettivo sulla solidità tecnica del setup.
3. **Grafici Tecnici Professionali in Dark Mode**: Inviati direttamente su Telegram come foto ad alta risoluzione con livelli operativi evidenziati e pannello oscillatore RSI.
4. **Piano di Risk Management Dettagliato**:
   - **Zona di Ingresso Consigliata (Entry Range)**
   - **Stop Loss Tecnico** (basato sull'ATR - Average True Range o minimi recenti)
   - **Take Profit 1 e 2** (con rapporto Rischio/Rendimento tipico 1:2 o 1:2.5)
5. **Briefing Automatici Schedulati:**
   - ☀️ **Mattina (08:30 CET)**: Apertura Europa / FTSE MIB, Commodities (Oro & Petrolio) e chiusura 24h Crypto.
   - 🔔 **Pomeriggio (15:00 CET)**: Pre-market Wall Street, Tech 100 (Nasdaq) e US 500 (S&P).
   - 🪙 **Weekend (Sab-Dom 09:30 CET)**: Digest settimanale per le Criptovalute.

---

## 🚀 Guida Rapida all'Avvio

### 1. Configurazione `.env`
Assicurati di avere il file `.env` compilato con il tuo token e Chat ID:
```env
TELEGRAM_BOT_TOKEN=il_tuo_token_qui
TELEGRAM_CHAT_ID=il_tuo_chat_id_qui
TIMEZONE=Europe/Rome
MORNING_BRIEFING_TIME=08:30
AFTERNOON_BRIEFING_TIME=15:00
```

### 2. Gestione del Bot con gli Script

- **Avvio in Background (Consigliato):**
  ```bash
  ./start.sh
  ```
- **Controllo dello Stato:**
  ```bash
  ./status.sh
  ```
- **Arresto del Bot:**
  ```bash
  ./stop.sh
  ```
- **Consultazione Log in Tempo Reale:**
  ```bash
  tail -f bot.log
  ```

---

## 📱 Comandi Telegram e Supporto Alias

Il bot riconosce automaticamente gli **alias comuni dei mercati finanziari**, senza dover ricordare i simboli specifici di Yahoo Finance!

| Comando / Alias | Strumento Analizzato |
|---|---|
| `/analizza XAUUSD` oppure `/analizza GOLD` | 🥇 **Oro Spot / Futures (Gold)** |
| `/analizza CRUDE` oppure `/analizza OIL` | 🛢 **Petrolio Greggio WTI** |
| `/analizza BRENT` | 🛢 **Petrolio Brent** |
| `/analizza TECH100` oppure `/analizza NASDAQ` | 📈 **Nasdaq 100 Futures (Tech 100)** |
| `/analizza SP500` oppure `/analizza US500` | 📈 **S&P 500 Futures (US 500)** |
| `/analizza US30` oppure `/analizza DOW` | 📈 **Dow Jones 30 Futures** |
| `/analizza SILVER` | 🥈 **Argento Futures** |
| `/analizza NATGAS` | 💨 **Gas Naturale** |
| `/analizza NVDA`, `AAPL`, `TSLA`, `ENI.MI` | 🇺🇸 / 🇪🇺 **Azioni Singole** |
| `/analizza BTC-USD`, `ETH-USD`, `SOL-USD` | 🪙 **Criptovalute** |

### Comandi di Scansione Mercati:
- `/scan` : Scansione globale e classifica dei migliori setup del momento.
- `/scan commodities` : Scansione mirata di Oro, Petrolio WTI, Brent, Argento, Gas Naturale.
- `/scan indici` : Scansione di Tech 100, US 500, US 30, Russell 2000.
- `/scan usa` : Scansione azionario USA (S&P 500 & Nasdaq 100).
- `/scan eu` : Scansione Piazza Affari (FTSE MIB) e campioni europei.
- `/scan crypto` : Scansione criptovalute ad alta liquidità.
- `/scan watchlist` : Scansione ristretta ai tuoi titoli preferiti.
- `/top` : I migliori 5 setup in assoluto.
- `/watch add XAUUSD` : Aggiunge un asset alla tua lista preferiti (supporta gli alias).
- `/watchlist` : Mostra la lista dei titoli monitorati.

---

## 📂 Struttura del Progetto

```
BotTrading/
├── .venv/                   # Ambiente virtuale Python
├── .env                     # Variabili d'ambiente private (NON tracciato su Git)
├── .env.example             # Modello di configurazione
├── requirements.txt         # Dipendenze Python (python-telegram-bot, yfinance, matplotlib, ecc.)
├── start.sh                 # Script di avvio in background
├── stop.sh                  # Script di arresto
├── status.sh                # Script di verifica stato e log
├── run.py                   # Entry point principale del bot
├── src/
│   ├── config.py            # Alias (XAUUSD, CRUDE, TECH100), universi e parametri di trading
│   ├── indicators.py        # Calcolo matematico oscillatori (RSI, Bollinger, MACD, ATR, Medie)
│   ├── analyzer.py          # Motore di scoring (0-100) e calcolo Stop Loss / Take Profit
│   ├── chart_generator.py   # Generatore di grafici tecnici Dark Mode con livelli operativi
│   ├── screener.py          # Scansione batch con risoluzione alias
│   ├── watchlist.py         # Gestione persistente preferiti (data/watchlist.json)
│   ├── formatters.py        # Formattazione HTML messaggi Telegram
│   └── bot.py               # Handlers Telegram, bottoni interattivi e scheduler
└── tests/
    └── test_analysis.py     # Suite di test unitari
```

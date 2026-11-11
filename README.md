# 🤖 Trading Broker Assistant Bot (Telegram)

Un assistente algoritmico consultivo per **Telegram** progettato per affiancarti nello **Swing Trading** sui mercati finanziari (**Azionario USA, Piazza Affari / Europa e Criptovalute**).

> ⚠️ **DISCLAIMER:** Questo bot ha scopo puramente **informativo, analitico e consultivo**. Non si collega al tuo conto broker e non effettua ordini automatici. La decisione finale di acquisto o vendita e la gestione del rischio rimangono al 100% sotto la tua responsabilità.

---

## 🎯 Cosa Fa il Bot

1. **Scansione Intelligente delle Oscillazioni:**
   - **RSI (14)**: Rileva rimbalzi da ipervenduto (<35) e momentum rialzista consolidato (50-65).
   - **Trend e Medie Mobili**: Valuta l'allineamento con EMA 20, SMA 50 e il macro trend sopra la SMA 200.
   - **Bande di Bollinger**: Intercetta compressioni di volatilità (squeeze) e rimbalzi sulla banda inferiore.
   - **Volume Surge**: Verifica se il volume odierno supera di almeno 1.3x la media storica a 20 periodi (ingresso di investitori istituzionali).
2. **Punteggio di Opportunità (0-100)**: Assegna a ogni titolo un punteggio quantitativo basato sulla confluenza dei segnali tecnici.
3. **Piano di Risk Management Dettagliato**:
   - **Zona di Ingresso Suggerita (Entry)**
   - **Stop Loss Tecnico** (basato sull'ATR - Average True Range o sui minimi recenti)
   - **Take Profit 1 e 2** (con rapporto Rischio/Rendimento tipico 1:2 o 1:2.5)
4. **Briefing Automatici Schedulati:**
   - ☀️ **Mattina (08:30 CET)**: Apertura Piazza Affari / Europa e chiusura candela 24h Crypto.
   - 🔔 **Pomeriggio (15:00 CET)**: Pre-market Wall Street prima dell'apertura di NYSE/NASDAQ (15:30 CET).
   - 🪙 **Weekend (Sab-Dom 09:30 CET)**: Digest settimanale per le Criptovalute.

---

## 🚀 Guida Rapida all'Installazione

### 1. Prerequisiti
- Python 3.10+ (già testato su macOS con Python 3.15)
- Connessione a Internet

### 2. Creare il Bot su Telegram (Richiede 1 minuto)
1. Apri Telegram e cerca l'utente ufficiale **`@BotFather`**.
2. Invia il comando `/newbot`.
3. Scegli un nome visualizzato per il bot (es. `Mio Broker Assistant`).
4. Scegli uno username univoco che termina in `bot` (es. `mio_broker_trading_bot`).
5. `@BotFather` ti restituirà un **token HTTP API** (es. `7123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

### 3. Configurare il file `.env`
Copia il file di esempio `.env.example` in `.env`:
```bash
cp .env.example .env
```
Apri il file `.env` con un editor di testo e inserisci il tuo token:
```env
TELEGRAM_BOT_TOKEN=il_tuo_token_copiato_da_botfather
TELEGRAM_CHAT_ID=
TIMEZONE=Europe/Rome
MORNING_BRIEFING_TIME=08:30
AFTERNOON_BRIEFING_TIME=15:00
```

### 4. Avviare il Bot
Attiva l'ambiente virtuale e avvia lo script principale:
```bash
source .venv/bin/activate
python run.py
```

### 5. Ottenere il tuo Chat ID (per i report automatici)
1. Apri la chat del tuo bot su Telegram e premi **Avvia** (`/start`).
2. Digita il comando `/chatid`.
3. Il bot ti risponderà con il tuo identificativo numerico (es. `123456789`).
4. Inseriscilo nel file `.env` alla voce `TELEGRAM_CHAT_ID=123456789` e riavvia il bot per abilitare l'invio dei briefing automatici.

---

## 📱 Comandi Disponibili in Chat

| Comando | Descrizione |
|---|---|
| `/start` | Avvia il bot e mostra il messaggio di benvenuto. |
| `/scan` | Scansione completa di tutti i mercati e classifica delle migliori opportunità. |
| `/scan usa` | Scansione mirata dell'azionario USA (S&P 500 & Nasdaq 100). |
| `/scan eu` | Scansione mirata di Piazza Affari (FTSE MIB) e leader europei. |
| `/scan crypto` | Scansione delle principali criptovalute liquide. |
| `/scan watchlist` | Scansione esclusiva dei titoli presenti nella tua lista preferiti. |
| `/analizza <TICKER>` | Analisi tecnica completa, oscillatori e piano di trade (es. `/analizza NVDA`, `/analizza ENI.MI`, `/analizza BTC-USD`). |
| `/top` | Mostra rapidamente le 3 migliori opportunità con score più alto. |
| `/watchlist` | Visualizza la tua lista di titoli monitorati. |
| `/watch add <TICKER>` | Aggiunge un titolo alla tua Watchlist personale (es. `/watch add TSLA`). |
| `/watch del <TICKER>` | Rimuove un titolo dalla tua Watchlist personale. |
| `/orari` | Visualizza gli orari dei briefing automatici e il fuso orario configurato. |
| `/chatid` | Mostra il tuo ID Telegram. |
| `/help` | Guida completa ai comandi. |

---

## 📂 Struttura del Progetto

```
BotTrading/
├── .venv/                   # Ambiente virtuale Python
├── .env                     # Variabili d'ambiente private (Token bot, Chat ID)
├── .env.example             # Modello di configurazione
├── requirements.txt         # Dipendenze Python
├── run.py                   # Entry point per avviare il bot
├── src/
│   ├── config.py            # Universi di titoli (USA, EU, Crypto) e parametri strategia
│   ├── indicators.py        # Calcolo matematico oscillatori (RSI, Bollinger, MACD, ATR, Medie)
│   ├── analyzer.py          # Motore di scoring (0-100) e calcolo Stop Loss / Take Profit
│   ├── screener.py          # Motore di scansione batch tramite Yahoo Finance
│   ├── watchlist.py         # Gestione persistente della watchlist personale (data/watchlist.json)
│   ├── formatters.py        # Generatore di messaggi formattati in HTML per Telegram
│   └── bot.py               # Gestione eventi Telegram e scheduler dei briefing
└── tests/
    └── test_analysis.py     # Test unitari e di validazione
```

---

## 🛠 Come tenerlo attivo 24/7 (Opzionale)

Se desideri che il bot rimanga attivo anche quando chiudi il terminale del tuo Mac:
- **Metodo rapido con `nohup`:**
  ```bash
  nohup .venv/bin/python run.py > bot.log 2>&1 &
  ```
- **Metodo con `tmux` o `screen`:**
  ```bash
  tmux new -s tradingbot
  source .venv/bin/activate
  python run.py
  # Premi Ctrl+B, poi D per staccarti dalla sessione lasciando il bot attivo.
  ```


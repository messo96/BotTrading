import logging
import datetime
from typing import Optional
import pytz
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    Application
)
from src.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TIMEZONE,
    MORNING_BRIEFING_TIME,
    AFTERNOON_BRIEFING_TIME
)
from src.screener import run_market_screener, analyze_single_ticker
from src.watchlist import load_watchlist, add_to_watchlist, remove_from_watchlist
from src.formatters import (
    format_single_ticker,
    format_screening_report,
    format_help_message
)

# Configurazione Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fuso orario configurato
local_tz = pytz.timezone(TIMEZONE)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Messaggio di benvenuto al comando /start."""
    chat_id = update.effective_chat.id
    welcome_text = f"""👋 <b>Benvenuto nel tuo Trading Broker Assistant Bot!</b>

Sono il tuo assistente quantitativo personale per lo <b>Swing Trading</b> su oscillazioni di prezzo e momentum.

🔎 <b>Cosa faccio per te:</b>
• Monitoro i mercati (Azionario USA, Piazza Affari / Europa, Crypto).
• Eseguo lo screening delle oscillazioni (RSI, Medie Mobili, Volumi e Bollinger).
• Ti segnalo i setup più promettenti con Entry, Stop Loss e Take Profit.
• Ti invio i briefing automatici al mattino (08:30 CET) e prima di Wall Street (15:00 CET).

⚠️ <b>Nessun trading automatico:</b> Io ti affianco e ti consiglio, ma la decisione e la responsabilità finale sono tue al 100%.

<b>Il tuo Chat ID è:</b> <code>{chat_id}</code>
<i>(Se vuoi ricevere i report automatici programmati, imposta questo Chat ID nel tuo file .env)</i>

Digita /help per visualizzare tutti i comandi disponibili o /scan per iniziare una scansione immediata.
"""
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra la guida ai comandi."""
    await update.message.reply_text(format_help_message(), parse_mode=ParseMode.HTML)

async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fornisce all'utente il suo chat ID."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🆔 Il tuo Telegram Chat ID è: <code>{chat_id}</code>\n\n"
        f"Inseriscilo nella variabile <code>TELEGRAM_CHAT_ID={chat_id}</code> nel file <code>.env</code> "
        f"per ricevere i briefing automatici del mattino e del pomeriggio.",
        parse_mode=ParseMode.HTML
    )

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Esegue la scansione di mercato su richiesta."""
    args = context.args
    category = "all"
    if args and len(args) > 0:
        arg_cat = args[0].lower()
        if arg_cat in ["usa", "eu", "crypto", "watchlist", "all"]:
            category = arg_cat

    status_msg = await update.message.reply_text(
        f"⏳ <i>Scansione in corso per il comparto '<b>{category.upper()}</b>'... Controllo oscillazioni, RSI, volumi e medie mobili...</i>",
        parse_mode=ParseMode.HTML
    )
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        results = run_market_screener(category=category, top_n=5)
        title = f"REPORT SCANSIONE MERCATO ({category.upper()})"
        report_text = format_screening_report(title, results, category=category)
        await status_msg.edit_text(report_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Errore durante lo scan: {e}")
        await status_msg.edit_text(
            f"❌ <i>Si è verificato un errore durante la scansione: {e}</i>",
            parse_mode=ParseMode.HTML
        )

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analisi tecnica e swing setup di un singolo ticker."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Specifica un simbolo da analizzare.</b>\n"
            "Esempi:\n"
            "• <code>/analizza NVDA</code> (Azioni USA)\n"
            "• <code>/analizza ENI.MI</code> (Piazza Affari)\n"
            "• <code>/analizza BTC-USD</code> (Criptovalute)\n"
            "• <code>/analizza ASML.AS</code> (Europa)",
            parse_mode=ParseMode.HTML
        )
        return

    ticker = context.args[0].upper().strip()
    status_msg = await update.message.reply_text(
        f"🔍 <i>Scarico i dati e calcolo gli oscillatori per <b>{ticker}</b>...</i>",
        parse_mode=ParseMode.HTML
    )
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        analysis = analyze_single_ticker(ticker)
        if not analysis:
            await status_msg.edit_text(
                f"❌ Impossibile recuperare dati sufficienti per il ticker <b>{ticker}</b>.\n"
                f"Verifica che il simbolo sia corretto su Yahoo Finance (es. per titoli italiani aggiungi '.MI').",
                parse_mode=ParseMode.HTML
            )
            return

        msg = format_single_ticker(analysis)
        await status_msg.edit_text(msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Errore durante l'analisi del ticker {ticker}: {e}")
        await status_msg.edit_text(
            f"❌ Errore durante l'analisi: {e}",
            parse_mode=ParseMode.HTML
        )

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra i Top 3 titoli con il miglior punteggio."""
    status_msg = await update.message.reply_text(
        "🏆 <i>Calcolo i migliori 3 setup del mercato al momento...</i>",
        parse_mode=ParseMode.HTML
    )
    try:
        results = run_market_screener(category="all", top_n=3)
        report_text = format_screening_report("TOP 3 OPPORTUNITÀ SWING DEL MOMENTO", results, category="all")
        await status_msg.edit_text(report_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Errore top command: {e}")
        await status_msg.edit_text(f"❌ Errore nel calcolo dei Top: {e}", parse_mode=ParseMode.HTML)

async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra la watchlist dei ticker preferiti."""
    tickers = load_watchlist()
    if not tickers:
        await update.message.reply_text(
            "📋 La tua Watchlist è vuota. Aggiungi titoli con <code>/watch add TICKER</code>.",
            parse_mode=ParseMode.HTML
        )
        return

    tickers_list = ", ".join([f"<code>{t}</code>" for t in tickers])
    msg = f"""📋 <b>I TUOI TITOLI PREFERITI (WATCHLIST):</b>

{tickers_list}

Per scansionare solo questi titoli digita: <code>/scan watchlist</code>
Per aggiungere: <code>/watch add TICKER</code>
Per rimuovere: <code>/watch del TICKER</code>
"""
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def watch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce l'aggiunta o rimozione di ticker dalla watchlist."""
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "ℹ️ <b>Uso del comando /watch:</b>\n"
            "• <code>/watch add NVDA</code> : aggiunge un titolo\n"
            "• <code>/watch del NVDA</code> : rimuove un titolo\n"
            "• <code>/watchlist</code> : visualizza tutti i titoli monitorati",
            parse_mode=ParseMode.HTML
        )
        return

    action = args[0].lower()
    ticker = args[1].upper().strip()

    if action == "add":
        added = add_to_watchlist(ticker)
        if added:
            await update.message.reply_text(f"✅ Titolo <b>{ticker}</b> aggiunto alla tua Watchlist!", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"ℹ️ Il titolo <b>{ticker}</b> è già presente nella tua Watchlist.", parse_mode=ParseMode.HTML)
    elif action in ["del", "remove", "rm"]:
        removed = remove_from_watchlist(ticker)
        if removed:
            await update.message.reply_text(f"🗑 Titolo <b>{ticker}</b> rimosso dalla tua Watchlist.", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"⚠️ Il titolo <b>{ticker}</b> non era presente nella tua Watchlist.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("⚠️ Azione non valida. Usa <code>add</code> oppure <code>del</code>.", parse_mode=ParseMode.HTML)

async def orari_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra gli orari programmati dei briefing."""
    msg = f"""⏰ <b>ORARI BRIEFING AUTOMATICI PROGRAMMATI</b>

• <b>Briefing Mattutino:</b> Ore <code>{MORNING_BRIEFING_TIME}</code> (Lun-Ven)
  <i>Focus: Piazza Affari (apertura 09:00), Europa e chiusura 24h Crypto.</i>

• <b>Briefing Pre-Market USA:</b> Ore <code>{AFTERNOON_BRIEFING_TIME}</code> (Lun-Ven)
  <i>Focus: Wall Street (NYSE/NASDAQ) prima dell'apertura delle 15:30.</i>

• <b>Briefing Weekend Crypto:</b> Sabato e Domenica ore <code>09:30</code>

Fuso Orario: <code>{TIMEZONE}</code>
Destinatario automatico: <code>{TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID else 'Non configurato (ricevibile via /chatid)'}</code>
"""
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# -----------------------------
# FUNZIONI SCHEDULATE (JOB QUEUE)
# -----------------------------
async def scheduled_morning_briefing(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Briefing mattutino programmato (Europa + Crypto)."""
    target_chat = TELEGRAM_CHAT_ID or context.job.chat_id
    if not target_chat:
        logger.warning("Nessun TELEGRAM_CHAT_ID configurato per il briefing mattutino.")
        return

    logger.info("Esecuzione del briefing mattutino automatico...")
    try:
        # Screening misto Europa + Crypto
        results = run_market_screener(category="eu", top_n=3)
        crypto_results = run_market_screener(category="crypto", top_n=2)
        combined = results + crypto_results
        
        report = format_screening_report("☀️ MORNING BRIEFING: APERTURA EUROPA & CRYPTO", combined, category="Europa & Crypto")
        await context.bot.send_message(chat_id=target_chat, text=report, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Errore nel morning briefing: {e}")

async def scheduled_afternoon_briefing(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Briefing pomeridiano programmato (Pre-Market USA)."""
    target_chat = TELEGRAM_CHAT_ID or context.job.chat_id
    if not target_chat:
        logger.warning("Nessun TELEGRAM_CHAT_ID configurato per il briefing pomeridiano.")
        return

    logger.info("Esecuzione del briefing pre-market USA...")
    try:
        results = run_market_screener(category="usa", top_n=5)
        report = format_screening_report("🔔 AFTERNOON BRIEFING: PRE-MARKET WALL STREET", results, category="USA")
        await context.bot.send_message(chat_id=target_chat, text=report, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Errore nel pre-market USA briefing: {e}")

async def scheduled_weekend_crypto_briefing(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Briefing crypto per il weekend."""
    target_chat = TELEGRAM_CHAT_ID or context.job.chat_id
    if not target_chat:
        return

    logger.info("Esecuzione del briefing weekend crypto...")
    try:
        results = run_market_screener(category="crypto", top_n=4)
        report = format_screening_report("🪙 WEEKEND CRYPTO DIGEST", results, category="Crypto")
        await context.bot.send_message(chat_id=target_chat, text=report, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Errore nel weekend crypto briefing: {e}")

def create_bot_application() -> Application:
    """Inizializza l'applicazione Telegram con tutti i comandi e la JobQueue."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN non è impostato nel file .env!")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Registrazione Comandi
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("chatid", chatid_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("analizza", analyze_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("watchlist", watchlist_command))
    app.add_handler(CommandHandler("watch", watch_command))
    app.add_handler(CommandHandler("orari", orari_command))

    # Configurazione JobQueue schedulata
    job_queue = app.job_queue
    if job_queue:
        try:
            m_h, m_m = map(int, MORNING_BRIEFING_TIME.split(":"))
            morning_time = datetime.time(hour=m_h, minute=m_m, tzinfo=local_tz)
            job_queue.run_daily(
                scheduled_morning_briefing,
                time=morning_time,
                days=(0, 1, 2, 3, 4), # Da Lunedì a Venerdì
                name="morning_briefing"
            )
            logger.info(f"Schedulato Morning Briefing alle {morning_time} (Lun-Ven)")
        except Exception as e:
            logger.error(f"Errore configurazione Morning Briefing: {e}")

        try:
            a_h, a_m = map(int, AFTERNOON_BRIEFING_TIME.split(":"))
            afternoon_time = datetime.time(hour=a_h, minute=a_m, tzinfo=local_tz)
            job_queue.run_daily(
                scheduled_afternoon_briefing,
                time=afternoon_time,
                days=(0, 1, 2, 3, 4), # Da Lunedì a Venerdì
                name="afternoon_briefing"
            )
            logger.info(f"Schedulato Afternoon Briefing alle {afternoon_time} (Lun-Ven)")
        except Exception as e:
            logger.error(f"Errore configurazione Afternoon Briefing: {e}")

        try:
            weekend_time = datetime.time(hour=9, minute=30, tzinfo=local_tz)
            job_queue.run_daily(
                scheduled_weekend_crypto_briefing,
                time=weekend_time,
                days=(5, 6), # Sabato e Domenica
                name="weekend_crypto_briefing"
            )
            logger.info(f"Schedulato Weekend Crypto Briefing alle {weekend_time} (Sab-Dom)")
        except Exception as e:
            logger.error(f"Errore configurazione Weekend Briefing: {e}")

    return app

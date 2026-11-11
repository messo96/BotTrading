import logging
import datetime
from typing import Optional, List
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    Application
)
from src.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TIMEZONE,
    MORNING_BRIEFING_TIME,
    AFTERNOON_BRIEFING_TIME,
    TICKER_NAMES
)
from src.screener import (
    run_market_screener,
    analyze_single_ticker,
    fetch_ticker_data_and_analysis,
    resolve_ticker
)
from src.watchlist import load_watchlist, add_to_watchlist, remove_from_watchlist
from src.formatters import (
    format_single_ticker,
    format_screening_report,
    format_help_message,
    get_ticker_display_name
)
from src.chart_generator import generate_technical_chart

# Configurazione Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Fuso orario configurato
local_tz = pytz.timezone(TIMEZONE)

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Tastiera interattiva per la dashboard principale."""
    keyboard = [
        [
            InlineKeyboardButton("🥇 Oro & Commodities", callback_data="scan_commodities"),
            InlineKeyboardButton("📈 Tech100 & Indici", callback_data="scan_indici")
        ],
        [
            InlineKeyboardButton("🇺🇸 Azioni USA", callback_data="scan_usa"),
            InlineKeyboardButton("🇪🇺 Europa / FTSE MIB", callback_data="scan_eu")
        ],
        [
            InlineKeyboardButton("🪙 Criptovalute", callback_data="scan_crypto"),
            InlineKeyboardButton("📋 Mia Watchlist", callback_data="scan_watchlist")
        ],
        [
            InlineKeyboardButton("🏆 Top 3 Setup", callback_data="scan_top"),
            InlineKeyboardButton("⏰ Orari Briefing", callback_data="info_orari")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_report_keyboard(results: list) -> Optional[InlineKeyboardMarkup]:
    """Genera pulsanti rapidi per visualizzare il grafico e l'analisi dei titoli trovati."""
    if not results:
        return None
    keyboard = []
    row = []
    for r in results[:4]:
        t = r["ticker"]
        short_name = TICKER_NAMES.get(t, t).split(" ")[0]
        row.append(InlineKeyboardButton(f"📊 {short_name}", callback_data=f"analizza_{t}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("🔄 Tutti i Mercati", callback_data="scan_all"),
        InlineKeyboardButton("🏠 Menu Principale", callback_data="menu_home")
    ])
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Messaggio di benvenuto al comando /start con tastiera interattiva."""
    chat_id = update.effective_chat.id
    welcome_text = f"""👋 <b>Benvenuto nel tuo Trading Broker Assistant Bot!</b>

Sono il tuo assistente quantitativo per lo <b>Swing Trading</b> basato su oscillazioni di prezzo, momentum e volumi.

🔎 <b>Cosa monitoro per te:</b>
• 🥇 <b>Commodities:</b> Oro (XAU/USD), Petrolio WTI (Crude), Brent, Argento, Gas.
• 📈 <b>Indici & Futures:</b> Tech 100 (Nasdaq), US 500 (S&P), US 30 (Dow Jones).
• 🇺🇸 <b>Azioni USA:</b> Nvidia, Apple, Tesla, Microsoft, AMD, ecc.
• 🇪🇺 <b>Piazza Affari & Europa:</b> Eni, Intesa, Ferrari, Unicredit, ASML.
• 🪙 <b>Crypto:</b> Bitcoin, Ethereum, Solana, ecc.

📊 <b>Cosa ti fornisco:</b>
• Indicatori avanzati (RSI, Medie Mobili, Bande di Bollinger, Volume Surge).
• Grafici tecnici completi con <b>Stop Loss</b> e <b>Take Profit</b>.
• Punteggio quantitativo (0-100) per ogni setup.
• Briefing automatici del mattino (08:30) e pomeriggio (15:00).

⚠️ <i>Broker-Assistant consultivo: nessun ordine viene piazzato in automatico. La decisione finale e la responsabilità sono tue al 100%.</i>

🆔 <b>Il tuo Chat ID:</b> <code>{chat_id}</code>

<b>Seleziona un comparto dal menu qui sotto:</b>
"""
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra la guida ai comandi."""
    await update.message.reply_text(
        format_help_message(),
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard()
    )

async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fornisce all'utente il suo chat ID."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🆔 Il tuo Telegram Chat ID è: <code>{chat_id}</code>\n\n"
        f"Inseriscilo nella variabile <code>TELEGRAM_CHAT_ID={chat_id}</code> nel file <code>.env</code> "
        f"per ricevere i briefing automatici del mattino e del pomeriggio.",
        parse_mode=ParseMode.HTML
    )

async def execute_and_send_analysis(chat_id: int, raw_ticker: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Funzione ausiliaria per eseguire e inviare l'analisi con grafico tecnico."""
    ticker = resolve_ticker(raw_ticker)
    display_name = get_ticker_display_name(ticker)

    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔍 <i>Scarico lo storico e genero il grafico tecnico per <b>{display_name}</b>...</i>",
        parse_mode=ParseMode.HTML
    )
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)

    try:
        df, analysis = fetch_ticker_data_and_analysis(ticker)
        if not analysis or df is None:
            await status_msg.edit_text(
                f"❌ Impossibile recuperare dati sufficienti per <b>{raw_ticker.upper()}</b> (simbolo: <code>{ticker}</code>).\n"
                f"Verifica che il simbolo sia corretto su Yahoo Finance.",
                parse_mode=ParseMode.HTML
            )
            return

        msg = format_single_ticker(analysis)
        chart_buf = generate_technical_chart(ticker, df, analysis)

        try:
            await status_msg.delete()
        except Exception:
            pass

        watch_btn_text = f"➕ Aggiungi {raw_ticker.upper()} a Watchlist"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(watch_btn_text, callback_data=f"watch_add_{ticker}")],
            [InlineKeyboardButton("🔄 Nuova Scansione", callback_data="scan_all"), InlineKeyboardButton("🏠 Menu", callback_data="menu_home")]
        ])

        if chart_buf:
            if len(msg) <= 1024:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=chart_buf,
                    caption=msg,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
            else:
                short_caption = f"📊 <b>ANALISI & GRAFICO: {display_name}</b>\nScore: <b>{analysis['score']}/100</b> ({analysis['verdict']})"
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=chart_buf,
                    caption=short_caption,
                    parse_mode=ParseMode.HTML
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

    except Exception as e:
        logger.error(f"Errore durante l'analisi del ticker {ticker}: {e}")
        try:
            await status_msg.edit_text(f"❌ Errore durante l'analisi: {e}", parse_mode=ParseMode.HTML)
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Errore durante l'analisi: {e}")

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /analizza o /grafico per analisi tecnica dettagliata con foto."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ <b>Specifica un simbolo o alias da analizzare.</b>\n\n"
            "Esempi:\n"
            "• <code>/analizza XAUUSD</code> (Oro / Gold)\n"
            "• <code>/analizza CRUDE</code> (Petrolio WTI)\n"
            "• <code>/analizza TECH100</code> (Nasdaq 100 Futures)\n"
            "• <code>/analizza SP500</code> (S&P 500 Futures)\n"
            "• <code>/analizza NVDA</code> (Azioni USA)\n"
            "• <code>/analizza ENI.MI</code> (Piazza Affari)\n"
            "• <code>/analizza BTC-USD</code> (Bitcoin)",
            parse_mode=ParseMode.HTML
        )
        return

    raw_ticker = context.args[0].upper().strip()
    await execute_and_send_analysis(update.effective_chat.id, raw_ticker, context)

async def execute_and_send_scan(chat_id: int, category: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Funzione ausiliaria per eseguire la scansione e inviare il report con pulsanti interattivi."""
    category_label = category.upper()
    if category in ["commodities", "commodity", "oro", "materieprime"]:
        category_label = "COMMODITIES (Oro, Petrolio, Metalli, Gas)"
    elif category in ["indici", "indices", "futures"]:
        category_label = "INDICI & FUTURES (Tech 100, US 500, US 30)"

    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏳ <i>Scansione in corso per <b>{category_label}</b>... Controllo oscillazioni, RSI, volumi e medie...</i>",
        parse_mode=ParseMode.HTML
    )
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        top_n = 5 if category != "top" else 3
        cat_query = "all" if category == "top" else category
        results = run_market_screener(category=cat_query, top_n=top_n)

        title = f"REPORT SCANSIONE: {category_label}" if category != "top" else "TOP 3 OPPORTUNITÀ SWING DEL MOMENTO"
        report_text = format_screening_report(title, results, category=cat_query)
        kb = get_report_keyboard(results)

        await status_msg.edit_text(report_text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        logger.error(f"Errore durante lo scan ({category}): {e}")
        await status_msg.edit_text(
            f"❌ <i>Si è verificato un errore durante la scansione: {e}</i>",
            parse_mode=ParseMode.HTML
        )

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Esegue la scansione di mercato su richiesta testuale."""
    args = context.args
    category = "all"
    if args and len(args) > 0:
        arg_cat = args[0].lower()
        if arg_cat in ["usa", "eu", "crypto", "commodities", "commodity", "oro", "indici", "indices", "futures", "watchlist", "all"]:
            category = arg_cat

    await execute_and_send_scan(update.effective_chat.id, category, context)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra i Top 3 titoli con il miglior punteggio."""
    await execute_and_send_scan(update.effective_chat.id, "top", context)

async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra la watchlist dei ticker preferiti."""
    tickers = load_watchlist()
    if not tickers:
        await update.message.reply_text(
            "📋 La tua Watchlist è vuota. Aggiungi titoli con <code>/watch add TICKER</code>.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
        return

    items_list = []
    for t in tickers:
        name = get_ticker_display_name(t)
        items_list.append(f"• <b>{name}</b> (<code>{t}</code>)")
    tickers_text = "\n".join(items_list)

    msg = f"""📋 <b>I TUOI TITOLI PREFERITI (WATCHLIST):</b>

{tickers_text}

Per scansionare solo questi titoli: <code>/scan watchlist</code>
Per aggiungere: <code>/watch add XAUUSD</code> (supporta anche alias!)
Per rimuovere: <code>/watch del TICKER</code>
"""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Scansiona Watchlist Adesso", callback_data="scan_watchlist")],
        [InlineKeyboardButton("🏠 Menu Principale", callback_data="menu_home")]
    ])
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=kb)

async def watch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce l'aggiunta o rimozione di ticker dalla watchlist."""
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "ℹ️ <b>Uso del comando /watch:</b>\n"
            "• <code>/watch add XAUUSD</code> : aggiunge l'Oro\n"
            "• <code>/watch add CRUDE</code> : aggiunge il Petrolio\n"
            "• <code>/watch add TECH100</code> : aggiunge il Nasdaq 100\n"
            "• <code>/watch del NVDA</code> : rimuove un titolo\n"
            "• <code>/watchlist</code> : visualizza la lista",
            parse_mode=ParseMode.HTML
        )
        return

    action = args[0].lower()
    raw_ticker = args[1].upper().strip()
    ticker = resolve_ticker(raw_ticker)
    display_name = get_ticker_display_name(ticker)

    if action == "add":
        added = add_to_watchlist(ticker)
        if added:
            await update.message.reply_text(f"✅ <b>{display_name}</b> aggiunto alla tua Watchlist!", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"ℹ️ <b>{display_name}</b> è già presente nella tua Watchlist.", parse_mode=ParseMode.HTML)
    elif action in ["del", "remove", "rm"]:
        removed = remove_from_watchlist(ticker)
        if removed:
            await update.message.reply_text(f"🗑 <b>{display_name}</b> rimosso dalla tua Watchlist.", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"⚠️ <b>{display_name}</b> non era presente nella tua Watchlist.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("⚠️ Azione non valida. Usa <code>add</code> oppure <code>del</code>.", parse_mode=ParseMode.HTML)

async def orari_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra gli orari programmati dei briefing."""
    msg = f"""⏰ <b>ORARI BRIEFING AUTOMATICI PROGRAMMATI</b>

• <b>Briefing Mattutino:</b> Ore <code>{MORNING_BRIEFING_TIME}</code> (Lun-Ven)
  <i>Focus: Piazza Affari (09:00), Europa, Commodities (Oro, Petrolio) e Crypto.</i>

• <b>Briefing Pre-Market USA:</b> Ore <code>{AFTERNOON_BRIEFING_TIME}</code> (Lun-Ven)
  <i>Focus: Wall Street (15:30), Tech 100 (Nasdaq) e US 500 (S&P).</i>

• <b>Briefing Weekend Crypto:</b> Sabato e Domenica ore <code>09:30</code>

Fuso Orario: <code>{TIMEZONE}</code>
Destinatario automatico: <code>{TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID else 'Non configurato'}</code>
"""
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu Principale", callback_data="menu_home")]])
    )

# -----------------------------
# GESTIONE PULSANTI INTERATTIVI
# -----------------------------
async def callback_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Intercetta e gestisce i click sui pulsanti della tastiera inline."""
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data == "menu_home":
        await query.message.reply_text(
            "🏠 <b>Dashboard Principale:</b> Scegli un'opzione:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
    elif data.startswith("scan_"):
        category = data.replace("scan_", "")
        await execute_and_send_scan(chat_id, category, context)
    elif data.startswith("analizza_"):
        ticker = data.replace("analizza_", "")
        await execute_and_send_analysis(chat_id, ticker, context)
    elif data.startswith("watch_add_"):
        ticker = data.replace("watch_add_", "")
        added = add_to_watchlist(ticker)
        name = get_ticker_display_name(ticker)
        resp = f"✅ <b>{name}</b> aggiunto alla Watchlist!" if added else f"ℹ️ <b>{name}</b> è già nella Watchlist."
        await query.message.reply_text(resp, parse_mode=ParseMode.HTML)
    elif data == "info_orari":
        await orari_command(update, context)

# -----------------------------
# FUNZIONI SCHEDULATE (JOB QUEUE)
# -----------------------------
async def scheduled_morning_briefing(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Briefing mattutino programmato (Europa + Commodities + Crypto)."""
    target_chat = TELEGRAM_CHAT_ID or context.job.chat_id
    if not target_chat:
        logger.warning("Nessun TELEGRAM_CHAT_ID configurato per il briefing mattutino.")
        return

    logger.info("Esecuzione del briefing mattutino automatico...")
    try:
        eu_results = run_market_screener(category="eu", top_n=2)
        comm_results = run_market_screener(category="commodities", top_n=2)
        crypto_results = run_market_screener(category="crypto", top_n=2)
        combined = comm_results + eu_results + crypto_results
        
        report = format_screening_report("☀️ MORNING BRIEFING: COMMODITIES, EUROPA & CRYPTO", combined, category="Misto Mattina")
        kb = get_report_keyboard(combined)
        await context.bot.send_message(chat_id=target_chat, text=report, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        logger.error(f"Errore nel morning briefing: {e}")

async def scheduled_afternoon_briefing(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Briefing pomeridiano programmato (Pre-Market USA & Indici Futures)."""
    target_chat = TELEGRAM_CHAT_ID or context.job.chat_id
    if not target_chat:
        logger.warning("Nessun TELEGRAM_CHAT_ID configurato per il briefing pomeridiano.")
        return

    logger.info("Esecuzione del briefing pre-market USA...")
    try:
        indices_results = run_market_screener(category="indici", top_n=2)
        usa_results = run_market_screener(category="usa", top_n=4)
        combined = indices_results + usa_results

        report = format_screening_report("🔔 AFTERNOON BRIEFING: WALL STREET & INDICI FUTURES", combined, category="USA & Indici")
        kb = get_report_keyboard(combined)
        await context.bot.send_message(chat_id=target_chat, text=report, parse_mode=ParseMode.HTML, reply_markup=kb)
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
        kb = get_report_keyboard(results)
        await context.bot.send_message(chat_id=target_chat, text=report, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        logger.error(f"Errore nel weekend crypto briefing: {e}")

def create_bot_application() -> Application:
    """Inizializza l'applicazione Telegram con tutti i comandi, tastiere e la JobQueue."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN non è impostato nel file .env!")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Registrazione Comandi
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("chatid", chatid_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("analizza", analyze_command))
    app.add_handler(CommandHandler("grafico", analyze_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CommandHandler("watchlist", watchlist_command))
    app.add_handler(CommandHandler("watch", watch_command))
    app.add_handler(CommandHandler("orari", orari_command))

    # Gestore Callback Query per bottoni inline
    app.add_handler(CallbackQueryHandler(callback_button_handler))

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

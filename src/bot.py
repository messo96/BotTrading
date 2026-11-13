import logging
import datetime
import math
import time
from typing import Optional, List
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.constants import ParseMode, ChatAction
from telegram.request import HTTPXRequest
from telegram.error import NetworkError, TimedOut
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    Application
)
from src.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_GROUP_ID,
    PORTFOLIO_UPDATE_INTERVAL_HOURS,
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
from src.portfolio import (
    load_portfolio,
    add_position,
    update_entry_price,
    remove_position,
    archive_position,
    load_archived_portfolio,
    clear_portfolio,
    evaluate_full_portfolio
)
from src.formatters import (
    format_single_ticker,
    format_screening_report,
    format_help_message,
    format_portfolio_update,
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
PORTFOLIO_INPUT_TTL_SECONDS = 10 * 60
PORTFOLIO_HISTORY_PAGE_SIZE = 10

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
            InlineKeyboardButton("💼 Il Mio Portafoglio", callback_data="menu_portfolio"),
            InlineKeyboardButton("🏆 Top 5 Setup", callback_data="scan_top")
        ],
        [
            InlineKeyboardButton("📢 Invia Report al Gruppo", callback_data="send_group_report"),
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
    for r in results[:5]:
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

def get_portfolio_management_keyboard(positions: list) -> InlineKeyboardMarkup:
    """Crea i controlli per modificare, rimuovere o archiviare ogni posizione."""
    keyboard = []
    for pos in positions:
        ticker = pos["ticker"]
        keyboard.append([
            InlineKeyboardButton("✏️ Ingresso", callback_data=f"port_edit_{ticker}"),
            InlineKeyboardButton("📦 Archivia", callback_data=f"port_archive_{ticker}"),
            InlineKeyboardButton("🗑 Elimina", callback_data=f"port_delete_{ticker}")
        ])
    keyboard.append([InlineKeyboardButton("📢 Pubblica nel Gruppo", callback_data="send_group_report")])
    keyboard.append([
        InlineKeyboardButton("🗂 Storico", callback_data="portfolio_history"),
        InlineKeyboardButton("🏠 Menu Principale", callback_data="menu_home")
    ])
    return InlineKeyboardMarkup(keyboard)

def _update_pending_portfolio(
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    ticker: str,
    chat_id: int,
    direction: Optional[str] = None
) -> None:
    pending = {
        "action": action,
        "ticker": ticker,
        "chat_id": chat_id,
        "created_at": time.time()
    }
    if direction:
        pending["direction"] = direction
    context.user_data["pending_portfolio"] = pending


async def _prompt_portfolio_price(
    message,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    include_cancel: bool = True
) -> None:
    pending = context.user_data.get("pending_portfolio")
    if not pending:
        return
    prompt = await message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=ForceReply(selective=True, input_field_placeholder="Prezzo di ingresso")
    )
    pending["prompt_message_id"] = prompt.message_id
    if include_cancel:
        await message.reply_text(
            "Per annullare l'inserimento, premi qui sotto.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✖️ Annulla", callback_data="port_cancel_pending")]
            ])
        )


def _portfolio_history_page(history: list, requested_page: int) -> tuple[str, InlineKeyboardMarkup]:
    page_count = max(1, math.ceil(len(history) / PORTFOLIO_HISTORY_PAGE_SIZE))
    page = min(max(requested_page, 0), page_count - 1)
    if not history:
        text = "🗂 <b>Storico portafoglio</b>\n\nNon ci sono ancora posizioni archiviate."
    else:
        start = max(0, len(history) - (page + 1) * PORTFOLIO_HISTORY_PAGE_SIZE)
        end = len(history) - page * PORTFOLIO_HISTORY_PAGE_SIZE
        rows = []
        for position in history[start:end][::-1]:
            direction = "BUY" if position.get("direction") == "BUY" else "SELL"
            rows.append(
                f"• <b>{position.get('ticker', 'N/A')}</b> · {direction} · "
                f"Ingresso {float(position.get('entry_price', 0)):,.2f} · "
                f"archiviato {position.get('archived_at', 'N/A')}"
            )
        text = f"🗂 <b>Storico portafoglio</b> · {page + 1}/{page_count}\n\n" + "\n".join(rows)

    keyboard = []
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton("⬅️ Più recenti", callback_data=f"portfolio_history_page_{page - 1}"))
    if page < page_count - 1:
        navigation.append(InlineKeyboardButton("Più vecchie ➡️", callback_data=f"portfolio_history_page_{page + 1}"))
    if navigation:
        keyboard.append(navigation)
    keyboard.append([InlineKeyboardButton("💼 Torna al portafoglio", callback_data="menu_portfolio")])
    return text, InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Messaggio di benvenuto al comando /start con tastiera interattiva."""
    chat_id = update.effective_chat.id
    welcome_text = f"""👋 <b>Benvenuto nel tuo Trading Broker Assistant Bot!</b>

Sono il tuo assistente per lo <b>Swing Trading</b> su oscillazioni di mercato (<b>BUY & SELL</b>) e gestione del tuo <b>Portafoglio Reale</b>.

🔎 <b>Cosa monitoro per te:</b>
• 🥇 <b>Commodities:</b> Oro (XAU/USD), Petrolio WTI (Crude), Brent, Argento, Gas.
• 📈 <b>Indici & Futures:</b> Tech 100 (Nasdaq), US 500 (S&P), US 30 (Dow Jones).
• 🇺🇸 <b>Azioni USA:</b> Nvidia, Apple, Tesla, AMD, Palantir, ecc.
• 🇪🇺 <b>Piazza Affari ed Europa:</b> Eni, Intesa, Ferrari, Unicredit, ASML.
• 🪙 <b>Crypto:</b> Bitcoin, Ethereum, Solana, ecc.

💼 <b>Gestione Portafoglio & Gruppo Telegram:</b>
• Monitoro i trade che hai aperto e ti consiglio se <b>Mantenere</b>, <b>Alzare lo Stop a Pareggio</b> o <b>Chiudere</b>.
• Invio aggiornamenti periodici automatici nel tuo gruppo Telegram (ID: <code>{TELEGRAM_GROUP_ID}</code>).

⚠️ <i>Broker-Assistant consultivo: nessun ordine viene piazzato in automatico. La decisione finale e la responsabilità sono tue al 100%.</i>

🆔 <b>Il tuo Chat ID:</b> <code>{chat_id}</code>

<b>Seleziona un'operazione dal menu qui sotto:</b>
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
    """Fornisce all'utente il suo chat ID o quello del gruppo in cui viene eseguito."""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    await update.message.reply_text(
        f"🆔 ID di questa chat ({chat_type}): <code>{chat_id}</code>\n\n"
        f"• Se è la tua chat privata: inseriscilo in <code>TELEGRAM_CHAT_ID={chat_id}</code>\n"
        f"• Se è un gruppo o supergruppo: inseriscilo in <code>TELEGRAM_GROUP_ID={chat_id}</code>",
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

        watch_btn_text = f"➕ Aggiungi a Watchlist"
        port_btn_text = f"💼 Registra in Portafoglio"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(watch_btn_text, callback_data=f"watch_add_{ticker}"), InlineKeyboardButton(port_btn_text, callback_data=f"port_add_prompt_{ticker}")],
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
            "• <code>/analizza XAUUSD</code> (Oro)\n"
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
        top_n = 5
        cat_query = "all" if category == "top" else category
        results = run_market_screener(category=cat_query, top_n=top_n)

        title = f"REPORT SCANSIONE: {category_label}" if category != "top" else "TOP 5 OPPORTUNITÀ SWING DEL MOMENTO"
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
    """Mostra i Top 5 titoli con il miglior punteggio."""
    await execute_and_send_scan(update.effective_chat.id, "top", context)

# -----------------------------
# GESTIONE PORTAFOGLIO
# -----------------------------
async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce la visualizzazione, aggiunta e rimozione di posizioni reali nel portafoglio."""
    args = context.args
    chat_id = update.effective_chat.id

    if not args:
        source_message = update.message or (update.callback_query.message if update.callback_query else None)
        status_msg = await source_message.reply_text("💼 <i>Analizzo le posizioni del tuo portafoglio in tempo reale...</i>", parse_mode=ParseMode.HTML)
        try:
            evaluations = evaluate_full_portfolio()
            report = format_portfolio_update(evaluations)
            kb = get_portfolio_management_keyboard(load_portfolio())
            await status_msg.edit_text(report, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception as e:
            logger.error(f"Errore portafoglio: {e}")
            await status_msg.edit_text(f"❌ Errore durante l'analisi del portafoglio: {e}", parse_mode=ParseMode.HTML)
        return

    sub = args[0].lower()
    if sub == "add":
        # Sintassi: /portfolio add <TICKER> <BUY|SELL> <PREZZO> [SL] [TP]
        if len(args) < 4:
            await update.message.reply_text(
                "ℹ️ <b>Come registrare un'operazione nel Portafoglio:</b>\n"
                "<code>/portfolio add TICKER BUY/SELL PREZZO [SL] [TP]</code>\n\n"
                "<b>Esempi:</b>\n"
                "• <code>/portfolio add NVDA SELL 170.50</code>\n"
                "• <code>/portfolio add XAUUSD BUY 4050 4010 4150</code>\n"
                "• <code>/portfolio add TECH100 SELL 28400</code>\n"
                "• <code>/portfolio add ENI.MI BUY 24.50</code>",
                parse_mode=ParseMode.HTML
            )
            return

        raw_ticker = args[1]
        direction = args[2].upper()
        try:
            entry_price = float(args[3].replace(",", "."))
            if not math.isfinite(entry_price) or entry_price <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Prezzo di ingresso non valido. Inserisci un numero maggiore di zero (es. <code>170.50</code>).", parse_mode=ParseMode.HTML)
            return

        sl = None
        tp = None
        if len(args) > 4:
            try:
                sl = float(args[4].replace(",", "."))
            except ValueError:
                pass
        if len(args) > 5:
            try:
                tp = float(args[5].replace(",", "."))
            except ValueError:
                pass

        pos = add_position(raw_ticker, direction, entry_price, stop_loss=sl, take_profit=tp)
        name = get_ticker_display_name(pos["ticker"])
        dir_badge = "🟢 BUY (Long)" if pos["direction"] == "BUY" else "🔴 SELL (Short)"
        sl_text = f"\n• <b>Stop Loss:</b> <code>{pos['stop_loss']}</code>" if pos.get("stop_loss") else ""
        tp_text = f"\n• <b>Take Profit:</b> <code>{pos['take_profit']}</code>" if pos.get("take_profit") else ""

        msg = f"""✅ <b>Posizione aggiunta con successo al Portafoglio!</b>

• <b>Asset:</b> {name} (<code>{pos['ticker']}</code>)
• <b>Operazione:</b> {dir_badge}
• <b>Prezzo Ingresso:</b> <b>{pos['entry_price']:,.2f}</b>{sl_text}{tp_text}

Il bot ora monitorerà costantemente questo trade e invierà gli aggiornamenti sul tuo gruppo ogni tot ore e ogni volta che digiti <code>/portfolio</code>.
"""
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    elif sub in ["del", "remove", "close"]:
        if len(args) < 2:
            await update.message.reply_text("ℹ️ Specifica quale posizione chiudere: <code>/portfolio del TICKER</code>", parse_mode=ParseMode.HTML)
            return
        raw_ticker = args[1]
        removed = remove_position(raw_ticker)
        if removed:
            await update.message.reply_text(f"🗑 Posizione <b>{raw_ticker.upper()}</b> chiusa e rimossa dal portafoglio.", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"⚠️ Posizione <b>{raw_ticker.upper()}</b> non trovata tra quelle aperte.", parse_mode=ParseMode.HTML)

    elif sub == "clear":
        clear_portfolio()
        await update.message.reply_text("🗑 Portafoglio azzerato completamente.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("⚠️ Azione non valida. Usa <code>/portfolio</code>, <code>/portfolio add</code> o <code>/portfolio del</code>.", parse_mode=ParseMode.HTML)

async def portfolio_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Completa l'aggiunta o la modifica dopo aver ricevuto il prezzo digitato."""
    pending = context.user_data.get("pending_portfolio")
    if not pending or not update.message or not update.effective_chat or not update.message.text:
        return

    if update.effective_chat.id != pending.get("chat_id"):
        return

    is_prompt_reply = (
        update.message.reply_to_message is not None
        and update.message.reply_to_message.message_id == pending.get("prompt_message_id")
    )
    if time.time() - pending.get("created_at", 0) > PORTFOLIO_INPUT_TTL_SECONDS:
        context.user_data.pop("pending_portfolio", None)
        if is_prompt_reply:
            await update.message.reply_text("⌛ Operazione scaduta. Avviane una nuova dal portafoglio.")
        return
    if not is_prompt_reply:
        return

    text = update.message.text.strip().replace(",", ".")
    try:
        entry_price = float(text)
        if not math.isfinite(entry_price) or entry_price <= 0:
            raise ValueError
    except ValueError:
        await _prompt_portfolio_price(
            update.message,
            context,
            "❌ Prezzo non valido. Rispondi a questo messaggio con un numero maggiore di zero "
            "(es. <code>170.50</code>).",
            include_cancel=False
        )
        return

    ticker = pending["ticker"]
    action = pending["action"]
    if action == "add":
        position = add_position(ticker, pending["direction"], entry_price)
        direction_label = "BUY" if position["direction"] == "BUY" else "SELL"
        await update.message.reply_text(
            f"✅ <b>{position['ticker']}</b> aggiunto al portafoglio: <b>{direction_label}</b> a <b>{entry_price:,.2f}</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_portfolio_management_keyboard(load_portfolio())
        )
    elif update_entry_price(ticker, entry_price):
        await update.message.reply_text(
            f"✅ Prezzo di ingresso di <b>{ticker}</b> aggiornato a <b>{entry_price:,.2f}</b>.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(f"⚠️ La posizione <b>{ticker}</b> non è più nel portafoglio.", parse_mode=ParseMode.HTML)
    context.user_data.pop("pending_portfolio", None)


async def clear_pending_portfolio_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Un nuovo comando interrompe un eventuale inserimento del prezzo rimasto in sospeso."""
    context.user_data.pop("pending_portfolio", None)

async def aggiornagruppo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pubblica immediatamente il report del portafoglio nel gruppo Telegram."""
    chat_id = update.effective_chat.id
    evaluations = evaluate_full_portfolio()
    if not evaluations:
        await update.message.reply_text(
            "ℹ️ Il portafoglio è vuoto. Aggiungi operazioni con <code>/portfolio add TICKER BUY/SELL PREZZO</code> prima di pubblicare l'aggiornamento.",
            parse_mode=ParseMode.HTML
        )
        return

    report = format_portfolio_update(evaluations)
    target_group = TELEGRAM_GROUP_ID

    try:
        await context.bot.send_message(chat_id=target_group, text=report, parse_mode=ParseMode.HTML)
        if str(chat_id) != str(target_group):
            await update.message.reply_text(
                f"✅ <b>Report Portafoglio pubblicato con successo nel gruppo!</b> (ID: <code>{target_group}</code>)",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Errore invio a gruppo {target_group}: {e}")
        await update.message.reply_text(
            f"❌ Impossibile inviare al gruppo (ID: <code>{target_group}</code>): {e}\n\n"
            f"<b>Cosa fare:</b> Assicurati di aver aggiunto il bot come membro o amministratore nel gruppo Telegram!",
            parse_mode=ParseMode.HTML
        )

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

• <b>Aggiornamenti Portafoglio nel Gruppo:</b> Ogni <code>{PORTFOLIO_UPDATE_INTERVAL_HOURS} ore</code>
  <i>Gruppo Destinazione: <code>{TELEGRAM_GROUP_ID}</code></i>

Fuso Orario: <code>{TIMEZONE}</code>
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
    if not query:
        return

    # Notifica a Telegram la ricezione del click (best-effort)
    try:
        await query.answer()
    except (NetworkError, TimedOut) as net_err:
        logger.warning(f"Timeout o disconnessione durante query.answer (proseguo): {net_err}")
    except Exception as e:
        logger.warning(f"Errore query.answer (ignorabile): {e}")

    data = query.data
    chat_id = query.message.chat_id if query.message else update.effective_chat.id
    pending = context.user_data.get("pending_portfolio")
    pending_flow_callback = (
        data == "port_cancel_pending"
        or data.startswith(("port_buy_", "port_sell_", "port_edit_"))
    )
    if pending and pending.get("chat_id") != chat_id:
        if pending_flow_callback:
            await query.message.reply_text(
                "Hai già un'operazione in corso in un'altra chat. Completala o annullala lì."
            )
            return
    elif pending and not pending_flow_callback:
        context.user_data.pop("pending_portfolio", None)

    if data == "menu_home":
        await query.message.reply_text(
            "🏠 <b>Dashboard Principale:</b> Scegli un'opzione:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
        )
    elif data == "menu_portfolio":
        await portfolio_command(update, context)
    elif data == "send_group_report":
        await aggiornagruppo_command(update, context)
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
    elif data.startswith("port_add_prompt_"):
        ticker = data.replace("port_add_prompt_", "")
        await query.message.reply_text(
            f"📥 <b>Registra {ticker} nel portafoglio</b>\nScegli il tipo di operazione:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🟢 BUY", callback_data=f"port_buy_{ticker}"),
                    InlineKeyboardButton("🔴 SELL", callback_data=f"port_sell_{ticker}")
                ],
                [InlineKeyboardButton("✖️ Annulla", callback_data="port_cancel_pending")]
            ])
        )
    elif data.startswith("port_buy_") or data.startswith("port_sell_"):
        direction, ticker = data.split("_", 2)[1].upper(), data.split("_", 2)[2]
        _update_pending_portfolio(context, "add", ticker, chat_id, direction)
        await _prompt_portfolio_price(
            query.message,
            context,
            f"💰 Inserisci il prezzo di ingresso per <b>{ticker}</b> ({direction}).\n"
            "Rispondi a questo messaggio con il prezzo. La posizione verrà aggiunta automaticamente."
        )
    elif data.startswith("port_edit_"):
        ticker = data.removeprefix("port_edit_")
        if not any(position.get("ticker") == ticker for position in load_portfolio()):
            await query.message.reply_text(f"⚠️ <b>{ticker}</b> non è più nel portafoglio.", parse_mode=ParseMode.HTML)
            return
        _update_pending_portfolio(context, "edit", ticker, chat_id)
        await _prompt_portfolio_price(
            query.message,
            context,
            f"✏️ Inserisci il nuovo prezzo di ingresso per <b>{ticker}</b>. Rispondi a questo messaggio."
        )
    elif data.startswith("port_delete_"):
        ticker = data.removeprefix("port_delete_")
        if remove_position(ticker):
            await query.message.reply_text(f"🗑 <b>{ticker}</b> eliminato dal portafoglio.", parse_mode=ParseMode.HTML)
            await portfolio_command(update, context)
        else:
            await query.message.reply_text(f"⚠️ <b>{ticker}</b> non è più nel portafoglio.", parse_mode=ParseMode.HTML)
    elif data.startswith("port_archive_"):
        ticker = data.removeprefix("port_archive_")
        if archive_position(ticker):
            await query.message.reply_text(f"📦 <b>{ticker}</b> archiviato. Lo trovi nello storico del portafoglio.", parse_mode=ParseMode.HTML)
            await portfolio_command(update, context)
        else:
            await query.message.reply_text(f"⚠️ <b>{ticker}</b> non è più nel portafoglio.", parse_mode=ParseMode.HTML)
    elif data == "portfolio_history" or data.startswith("portfolio_history_page_"):
        history = load_archived_portfolio()
        try:
            page = int(data.removeprefix("portfolio_history_page_")) if data != "portfolio_history" else 0
        except ValueError:
            page = 0
        text, keyboard = _portfolio_history_page(history, page)
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    elif data == "port_cancel_pending":
        context.user_data.pop("pending_portfolio", None)
        await query.message.reply_text("Operazione annullata.", parse_mode=ParseMode.HTML)
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

async def scheduled_portfolio_group_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Invia periodicamente il monitoraggio delle posizioni del portafoglio nel gruppo Telegram."""
    evaluations = evaluate_full_portfolio()
    if not evaluations:
        logger.info("Nessuna posizione aperta nel portafoglio. Nessun report da inviare al gruppo.")
        return

    target_group = TELEGRAM_GROUP_ID
    if not target_group:
        return

    logger.info(f"Invio aggiornamento portafoglio al gruppo {target_group}...")
    try:
        report = format_portfolio_update(evaluations)
        await context.bot.send_message(chat_id=target_group, text=report, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Impossibile inviare aggiornamento portafoglio al gruppo {target_group}: {e}")

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

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Intercetta e gestisce errori di rete o timeout globalmente per evitare crash."""
    if isinstance(context.error, (NetworkError, TimedOut)):
        logger.warning(f"⚠️ Errore di rete temporaneo con Telegram intercettato (auto-recovery): {context.error}")
        return
    logger.error(f"Errore non gestito durante l'elaborazione dell'update: {context.error}", exc_info=context.error)

def create_bot_application() -> Application:
    """Inizializza l'applicazione Telegram con tutti i comandi, tastiere, timeout estesi e la JobQueue."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN non è impostato nel file .env!")

    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=15.0,
        connection_pool_size=128
    )

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).request(request).build()

    # Gestore Errori Globale
    app.add_error_handler(global_error_handler)

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
    app.add_handler(CommandHandler("portfolio", portfolio_command))
    app.add_handler(CommandHandler("portafoglio", portfolio_command))
    app.add_handler(CommandHandler("aggiornagruppo", aggiornagruppo_command))
    app.add_handler(CommandHandler("orari", orari_command))

    # Riceve i prezzi digitati dopo aver scelto BUY/SELL o aver premuto Modifica.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, portfolio_input_handler))
    app.add_handler(MessageHandler(filters.COMMAND, clear_pending_portfolio_on_command), group=1)

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
                days=(0, 1, 2, 3, 4),
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
                days=(0, 1, 2, 3, 4),
                name="afternoon_briefing"
            )
            logger.info(f"Schedulato Afternoon Briefing alle {afternoon_time} (Lun-Ven)")
        except Exception as e:
            logger.error(f"Errore configurazione Afternoon Briefing: {e}")

        try:
            # Aggiornamento periodico del portafoglio nel gruppo ogni N ore
            interval_secs = max(1800, PORTFOLIO_UPDATE_INTERVAL_HOURS * 3600)
            job_queue.run_repeating(
                scheduled_portfolio_group_update,
                interval=interval_secs,
                first=180, # 3 minuti dopo l'avvio
                name="portfolio_group_updates"
            )
            logger.info(f"Schedulato aggiornamento periodico portafoglio ogni {PORTFOLIO_UPDATE_INTERVAL_HOURS} ore.")
        except Exception as e:
            logger.error(f"Errore configurazione aggiornamenti portafoglio: {e}")

        try:
            weekend_time = datetime.time(hour=9, minute=30, tzinfo=local_tz)
            job_queue.run_daily(
                scheduled_weekend_crypto_briefing,
                time=weekend_time,
                days=(5, 6),
                name="weekend_crypto_briefing"
            )
            logger.info(f"Schedulato Weekend Crypto Briefing alle {weekend_time} (Sab-Dom)")
        except Exception as e:
            logger.error(f"Errore configurazione Weekend Briefing: {e}")

    return app

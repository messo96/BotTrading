from datetime import datetime
from typing import Dict, Any, List
import pytz
from src.config import TIMEZONE, TICKER_NAMES

def get_progress_bar(score: int, length: int = 10) -> str:
    """Genera una barra grafica testuale per il punteggio."""
    filled = int(round((score / 100) * length))
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)

def get_asset_badge(asset_type: str) -> str:
    """Ritorna l'icona e l'etichetta del mercato."""
    if asset_type == "commodity":
        return "🥇 <b>Commodity / Materia Prima</b>"
    if asset_type == "index":
        return "📈 <b>Indice USA / Futures</b>"
    if asset_type == "crypto":
        return "🪙 <b>Criptovaluta</b>"
    if asset_type == "eu":
        return "🇪🇺 <b>Europa / Italia</b>"
    return "🇺🇸 <b>Azionario USA</b>"

def get_ticker_display_name(ticker: str) -> str:
    """Restituisce il nome descrittivo dell'asset se disponibile."""
    return TICKER_NAMES.get(ticker, ticker)

def format_single_ticker(d: Dict[str, Any]) -> str:
    """Formatta l'analisi dettagliata di un singolo titolo in HTML con indicazione chiara di BUY o SELL."""
    bar = get_progress_bar(d['score'])
    badge = get_asset_badge(d.get('asset_type', 'stock'))
    display_title = get_ticker_display_name(d['ticker'])
    
    change_color = "🟢" if d['price_change_pct'] >= 0 else "🔴"
    change_5d_color = "🟢" if d['five_days_change'] >= 0 else "🔴"
    
    signals_html = ""
    if d['signals']:
        signals_html = "\n".join([f"  • {s}" for s in d['signals']])
    else:
        signals_html = "  • Nessun pattern anomalo rilevato al momento."

    currency = "$" if d.get('asset_type') != "eu" else "€"

    action = d.get('action', 'BUY')
    if action == "BUY":
        action_label = "🟢 <b>BUY (LONG - Acquisto)</b>"
        action_type = "LONG"
        sl_label = "Sotto il prezzo"
        tp_label = "Sopra il prezzo"
    elif action == "SELL":
        action_label = "🔴 <b>SELL (SHORT - Vendita allo scoperto)</b>"
        action_type = "SHORT"
        sl_label = "Sopra il prezzo"
        tp_label = "Sotto il prezzo"
    else:
        action_label = "⚪ <b>NEUTRALE (In attesa di conferma)</b>"
        action_type = "ATTESA"
        sl_label = "Stop"
        tp_label = "Target"

    msg = f"""📊 <b>ANALISI & SWING SETUP: {display_title}</b>
{badge} | Prezzo: <b>{currency}{d['current_price']:,.2f}</b>

{change_color} Variazione 24h: <b>{d['price_change_pct']:+.2f}%</b>
{change_5d_color} Variazione 5gg: <b>{d['five_days_change']:+.2f}%</b>

<b>Direzione Consigliata:</b>
{action_label}
Valutazione: {d['verdict_icon']} <b>{d['verdict']}</b>
Score Opportunità: <b>{d['score']}/100</b> [{bar}]

<b>Indicatori & Oscillazioni:</b>
• RSI (14): <b>{d['rsi']}</b>
• Volume Surge: <b>{d['volume_surge']}x</b> rispetto alla media
• EMA 20: <b>{currency}{d['ema20']:,.2f}</b> | SMA 50: <b>{currency}{d['sma50']:,.2f}</b>
• SMA 200 (Macro): <b>{currency if d['sma200'] != 'N/A' else ''}{d['sma200']}</b>

<b>Segnali Tecnici Rilevati:</b>
{signals_html}

🎯 <b>PIANO OPERATIVO SUGGERITO ({action_type}):</b>
• <b>Operazione:</b> {action_label}
• <b>Zona Ingresso:</b> {currency}{d['entry_range'][0]:,.2f} - {currency}{d['entry_range'][1]:,.2f}
• <b>Stop Loss ({sl_label}):</b> <code>{currency}{d['stop_loss']:,.2f}</code> ({d['stop_loss_pct']:+.2f}%)
• <b>Take Profit 1:</b> <code>{currency}{d['take_profit_1']:,.2f}</code> ({d['take_profit_1_pct']:+.2f}%)
• <b>Take Profit 2 ({tp_label}):</b> <code>{currency}{d['take_profit_2']:,.2f}</code> ({d['take_profit_2_pct']:+.2f}%)
• <b>Rapporto Rischio/Rendimento:</b> 1:{d['risk_reward_ratio']}

⚠️ <i>Assistente consultivo: nessun ordine viene piazzato automaticamente. La decisione finale e la responsabilità sono tue al 100%.</i>
"""
    return msg

def format_screening_report(title: str, results: List[Dict[str, Any]], category: str = "all") -> str:
    """Formatta il report di mercato con la classifica dei migliori titoli sia BUY che SELL."""
    now_tz = datetime.now(pytz.timezone(TIMEZONE)).strftime("%d/%m/%Y alle %H:%M")
    
    if not results:
        return f"""🧭 <b>{title}</b>
📅 {now_tz}

<i>Nessun setup ad alta convinzione rilevato in questo momento per il comparto '{category}'. I titoli monitorati sono in fase neutrale o attendista.</i>
"""

    items_text = []
    for idx, r in enumerate(results, 1):
        bar = get_progress_bar(r['score'], length=6)
        currency = "$" if r.get('asset_type') != "eu" else "€"
        
        main_signal = r['signals'][0] if r['signals'] else "Fase neutrale"
        name = get_ticker_display_name(r['ticker'])
        action = r.get('action', 'BUY')
        action_tag = "🟢 <b>BUY</b>" if action == "BUY" else ("🔴 <b>SELL</b>" if action == "SELL" else "⚪ <b>NEUTRO</b>")
        
        item = f"""<b>#{idx} | {name}</b> ({action_tag} | Score: {r['score']}/100 [{bar}])
• Prezzo: <b>{currency}{r['current_price']:,.2f}</b> ({r['price_change_pct']:+.2f}%)
• Segnale: {main_signal}
• Setup ({action}): SL: <code>{currency}{r['stop_loss']:,.2f}</code> | TP: <code>{currency}{r['take_profit_2']:,.2f}</code> (R:R 1:{r['risk_reward_ratio']})
• Dettagli completi: digita /analizza {r['ticker']}"""
        items_text.append(item)

    body = "\n\n".join(items_text)

    msg = f"""🧭 <b>{title}</b>
📅 <i>{now_tz} (Fuso {TIMEZONE})</i>
🔍 Comparto: <b>{category.upper()}</b> | Setup migliori trovati: <b>{len(results)}</b>

{body}

💡 <i>Usa <code>/analizza TICKER</code> per la scheda tecnica e il grafico dettagliato.</i>
⚠️ <i>Promemoria: Questo bot agisce come broker-assistant consultivo. La responsabilità dell'investimento è al 100% tua.</i>
"""
    return msg

def format_portfolio_update(evaluations: List[Dict[str, Any]]) -> str:
    """Formatta l'aggiornamento dettagliato del portafoglio per il gruppo Telegram."""
    now_tz = datetime.now(pytz.timezone(TIMEZONE)).strftime("%d/%m/%Y alle %H:%M")
    
    if not evaluations:
        return f"""💼 <b>AGGIORNAMENTO PORTAFOGLIO TRADING</b>
📅 <i>{now_tz} (Fuso {TIMEZONE})</i>

<i>Nessuna posizione aperta registrata nel portafoglio.</i>

<b>Per aggiungere un asset:</b> usa <code>/scan</code>, apri l'analisi del titolo e premi <b>Registra in Portafoglio</b>.
Puoi anche continuare a usare <code>/portfolio add TICKER BUY/SELL PREZZO</code>.
"""

    items_text = []
    total_pnl = 0.0

    for idx, ev in enumerate(evaluations, 1):
        currency = "$" if ev.get("asset_type") != "eu" else "€"
        name = get_ticker_display_name(ev["ticker"])
        pnl = ev["pnl_pct"]
        total_pnl += pnl
        pnl_color = "🟢" if pnl >= 0 else "🔴"
        dir_badge = "🟢 <b>BUY (Long)</b>" if ev["direction"] == "BUY" else "🔴 <b>SELL (Short)</b>"
        
        item = f"""<b>#{idx} | {name}</b> ({dir_badge})
• Ingresso: <b>{currency}{ev['entry_price']:,.2f}</b> ➡️ Attuale: <b>{currency}{ev['current_price']:,.2f}</b>
• Performance: {pnl_color} <b>{pnl:+.2f}%</b>
• <b>Consiglio:</b> {ev['advice_icon']} <b>{ev['advice_title']}</b>
• <b>Analisi:</b> <i>{ev['advice_detail']}</i>
• Livelli attivi: SL: <code>{currency}{ev['stop_loss']:,.2f}</code> | TP: <code>{currency}{ev['take_profit']:,.2f}</code>"""
        items_text.append(item)

    avg_pnl = total_pnl / len(evaluations)
    avg_color = "🟢" if avg_pnl >= 0 else "🔴"
    cards = "\n\n".join(items_text)

    msg = f"""💼 <b>REPORT AGGIORNAMENTO PORTAFOGLIO</b>
📅 <i>{now_tz} (Fuso {TIMEZONE})</i>
📊 Posizioni monitorate: <b>{len(evaluations)}</b> | P&L medio: {avg_color} <b>{avg_pnl:+.2f}%</b>

{cards}

💡 <i>Usa i pulsanti sotto per modificare l'ingresso, archiviare o eliminare una posizione. Per aggiungerne una, apri un'analisi da /scan.</i>
⚠️ <i>Broker-Assistant consultivo: la responsabilità operativa finale è tua al 100%.</i>
"""
    return msg

def format_help_message() -> str:
    """Messaggio di aiuto con tutti i comandi disponibili."""
    return """🤖 <b>BROKER ASSISTANT BOT - GUIDA COMANDI</b>

Il bot monitora costantemente le oscillazioni di mercato (BUY e SELL) e aggiorna automaticamente il tuo **Portafoglio Posizioni Reali**.

<b>Gestione Portafoglio Reale:</b>
• <code>/portfolio</code> : Mostra le posizioni aperte; i pulsanti permettono di modificare il prezzo, archiviarle o eliminarle.
• Per aggiungere un asset: <code>/scan</code> → apri l'analisi → <b>Registra in Portafoglio</b> → BUY/SELL → prezzo di ingresso.
• In alternativa: <code>/portfolio add TICKER BUY/SELL PREZZO [SL] [TP]</code>.
• <code>/portfolio del TICKER</code> : Elimina una posizione dal portafoglio.
• <code>/aggiornagruppo</code> : Invia subito il report del portafoglio nel gruppo Telegram.

<b>Comandi di Scansione Mercati:</b>
• <code>/scan</code> : Scansione globale di tutti i mercati (Top opportunità BUY e SELL).
• <code>/scan commodities</code> : Scansione Oro (XAUUSD), Petrolio (Crude WTI/Brent), Argento, Gas.
• <code>/scan indici</code> : Scansione Tech 100 (Nasdaq), US 500 (S&P), US 30 (Dow Jones).
• <code>/scan usa</code> : Scansione Azionario USA.
• <code>/scan eu</code> : Scansione Piazza Affari (FTSE MIB) ed Europa.
• <code>/scan crypto</code> : Scansione principali criptovalute.
• <code>/top</code> : I 5 migliori setup in assoluto (BUY o SELL).

<b>Analisi Rapida con Grafico Dark Mode:</b>
• <code>/analizza XAUUSD</code> (Oro) | <code>/analizza CRUDE</code> (Petrolio) | <code>/analizza TECH100</code> (Nasdaq) | <code>/analizza NVDA</code>.

<b>Briefing Automatici:</b>
• <b>Mattina (08:30):</b> Apertura Europa + Commodities + Crypto.
• <b>Pomeriggio (15:00):</b> Pre-Market Wall Street + Tech100.
• <b>Aggiornamenti Portafoglio Gruppo:</b> Report periodico inviato automaticamente nel gruppo!

⚠️ <i>Ricorda: Il bot è consultivo, nessun ordine automatico. La decisione finale spetta sempre a te al 100%.</i>
"""

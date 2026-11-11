from datetime import datetime
from typing import Dict, Any, List
import pytz
from src.config import TIMEZONE

def get_progress_bar(score: int, length: int = 10) -> str:
    """Genera una barra grafica testuale per il punteggio."""
    filled = int(round((score / 100) * length))
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)

def get_asset_badge(asset_type: str) -> str:
    """Ritorna l'icona e l'etichetta del mercato."""
    if asset_type == "crypto":
        return "🪙 <b>Crypto</b>"
    if asset_type == "eu":
        return "🇪🇺 <b>Europa / Italia</b>"
    return "🇺🇸 <b>USA</b>"

def format_single_ticker(d: Dict[str, Any]) -> str:
    """Formatta l'analisi dettagliata di un singolo titolo in HTML."""
    bar = get_progress_bar(d['score'])
    badge = get_asset_badge(d.get('asset_type', 'stock'))
    
    change_color = "🟢" if d['price_change_pct'] >= 0 else "🔴"
    change_5d_color = "🟢" if d['five_days_change'] >= 0 else "🔴"
    
    signals_html = ""
    if d['signals']:
        signals_html = "\n".join([f"  • {s}" for s in d['signals']])
    else:
        signals_html = "  • Nessun pattern anomalo rilevato al momento."

    currency = "$" if d.get('asset_type') != "eu" else "€"

    msg = f"""📊 <b>ANALISI & SWING SETUP: {d['ticker']}</b>
{badge} | Prezzo: <b>{currency}{d['current_price']:,.2f}</b>

{change_color} Variazione 24h: <b>{d['price_change_pct']:+.2f}%</b>
{change_5d_color} Variazione 5gg: <b>{d['five_days_change']:+.2f}%</b>

<b>Valutazione Strategica:</b>
{d['verdict_icon']} <b>{d['verdict']}</b>
Score Opportunità: <b>{d['score']}/100</b> [{bar}]

<b>Indicatori & Oscillazioni:</b>
• RSI (14): <b>{d['rsi']}</b>
• Volume Surge: <b>{d['volume_surge']}x</b> rispetto alla media
• EMA 20: <b>{currency}{d['ema20']:,.2f}</b> | SMA 50: <b>{currency}{d['sma50']:,.2f}</b>
• SMA 200 (Macro): <b>{currency if d['sma200'] != 'N/A' else ''}{d['sma200']}</b>

<b>Segnali Rilevati:</b>
{signals_html}

🎯 <b>PIANO OPERATIVO SUGGERITO (SWING):</b>
• <b>Zona Ingresso:</b> {currency}{d['entry_range'][0]:,.2f} - {currency}{d['entry_range'][1]:,.2f}
• <b>Stop Loss:</b> <code>{currency}{d['stop_loss']:,.2f}</code> ({d['stop_loss_pct']:+.2f}%)
• <b>Take Profit 1:</b> <code>{currency}{d['take_profit_1']:,.2f}</code> ({d['take_profit_1_pct']:+.2f}%)
• <b>Take Profit 2:</b> <code>{currency}{d['take_profit_2']:,.2f}</code> ({d['take_profit_2_pct']:+.2f}%)
• <b>Rapporto Rischio/Rendimento:</b> 1:{d['risk_reward_ratio']}

⚠️ <i>Assistente consultivo: nessun ordine viene piazzato automaticamente. La decisione finale e la responsabilità sono tue al 100%.</i>
"""
    return msg

def format_screening_report(title: str, results: List[Dict[str, Any]], category: str = "all") -> str:
    """Formatta il report di mercato con la classifica dei migliori titoli."""
    now_tz = datetime.now(pytz.timezone(TIMEZONE)).strftime("%d/%m/%Y alle %H:%M")
    
    if not results:
        return f"""🧭 <b>{title}</b>
📅 {now_tz}

<i>Nessun setup rialzista ad alta convinzione rilevato in questo momento per il mercato '{category}'. Tutti i titoli monitorati sono in fase neutrale o attendista.</i>
"""

    items_text = []
    for idx, r in enumerate(results, 1):
        bar = get_progress_bar(r['score'], length=6)
        currency = "$" if r.get('asset_type') != "eu" else "€"
        
        main_signal = r['signals'][0] if r['signals'] else "Trend neutrale"
        
        item = f"""<b>#{idx} | {r['ticker']}</b> ({r['verdict_icon']} Score: {r['score']}/100 [{bar}])
• Prezzo: <b>{currency}{r['current_price']:,.2f}</b> ({r['price_change_pct']:+.2f}%)
• Motivo: {main_signal}
• Setup: SL: <code>{currency}{r['stop_loss']:,.2f}</code> | TP: <code>{currency}{r['take_profit_2']:,.2f}</code> (R:R 1:{r['risk_reward_ratio']})
• Dettagli completi: digita /analizza {r['ticker']}"""
        items_text.append(item)

    body = "\n\n".join(items_text)

    msg = f"""🧭 <b>{title}</b>
📅 <i>{now_tz} (Fuso {TIMEZONE})</i>
🔍 Mercato: <b>{category.upper()}</b> | Setup migliori trovati: <b>{len(results)}</b>

{body}

💡 <i>Usa <code>/analizza TICKER</code> per la scheda tecnica approfondita di ciascun asset.</i>
⚠️ <i>Promemoria: Questo bot agisce come broker-assistant consultivo. La responsabilità dell'investimento è al 100% tua.</i>
"""
    return msg

def format_help_message() -> str:
    """Messaggio di aiuto con tutti i comandi disponibili."""
    return """🤖 <b>BROKER ASSISTANT BOT - GUIDA COMANDI</b>

Il bot monitora costantemente le oscillazioni di mercato, individuando setup ad alto rendimento/basso rischio (Swing Trading) su Azioni USA, Europa/Italia e Crypto.

<b>Comandi Principali:</b>
• <code>/scan</code> : Scansione istantanea dei mercati e classifica delle migliori opportunità.
• <code>/scan usa</code> : Scansione esclusiva del mercato azionario USA (S&P 500 / Nasdaq).
• <code>/scan eu</code> : Scansione esclusiva di Piazza Affari (FTSE MIB) e campioni europei.
• <code>/scan crypto</code> : Scansione delle principali criptovalute.
• <code>/analizza TICKER</code> : Analisi tecnica dettagliata (es. <code>/analizza NVDA</code>, <code>/analizza ENI.MI</code>, <code>/analizza BTC-USD</code>).
• <code>/top</code> : Mostra i 3 migliori titoli con il punteggio più alto in assoluto.

<b>Gestione Watchlist Personale:</b>
• <code>/watchlist</code> : Mostra i titoli nella tua lista preferiti.
• <code>/watch add TICKER</code> : Aggiunge un titolo alla lista (es. <code>/watch add TSLA</code>).
• <code>/watch del TICKER</code> : Rimuove un titolo dalla lista.
• <code>/scan watchlist</code> : Esegue lo screening solo sui tuoi titoli preferiti.

<b>Briefing Automatici Programmati:</b>
• <b>Mattina (08:30 CET):</b> Apertura Europa / FTSE MIB e chiusura candela 24h Crypto.
• <b>Pomeriggio (15:00 CET):</b> Pre-Market Wall Street prima dell'apertura delle 15:30.

<b>Altro:</b>
• <code>/chatid</code> : Mostra il tuo Telegram Chat ID (necessario per configurare il file .env).
• <code>/help</code> : Mostra questo messaggio di aiuto.

⚠️ <i>Ricorda: Il bot non esegue ordini al tuo posto e non gestisce fondi. La decisione di trading spetta sempre a te al 100%.</i>
"""

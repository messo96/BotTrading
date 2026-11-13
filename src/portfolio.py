import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.config import ARCHIVED_PORTFOLIO_FILE, PORTFOLIO_FILE, STRATEGY_SETTINGS
from src.screener import resolve_ticker, fetch_ticker_data_and_analysis

logger = logging.getLogger(__name__)

def load_portfolio() -> List[Dict[str, Any]]:
    """Carica le posizioni aperte nel portafoglio dal file JSON."""
    if not PORTFOLIO_FILE.exists() or PORTFOLIO_FILE.stat().st_size == 0:
        return []
    try:
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        logger.error(f"Errore durante il caricamento del portafoglio: {e}")
        return []

def save_portfolio(positions: List[Dict[str, Any]]) -> None:
    """Salva le posizioni aperte nel portafoglio su file JSON."""
    PORTFOLIO_FILE.parent.mkdir(exist_ok=True, parents=True)
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2)

def load_archived_portfolio() -> List[Dict[str, Any]]:
    """Carica lo storico delle posizioni archiviate."""
    if not ARCHIVED_PORTFOLIO_FILE.exists() or ARCHIVED_PORTFOLIO_FILE.stat().st_size == 0:
        return []
    try:
        with open(ARCHIVED_PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Errore durante il caricamento dello storico portafoglio: {e}")
        return []

def save_archived_portfolio(positions: List[Dict[str, Any]]) -> None:
    """Salva lo storico delle posizioni archiviate su file JSON."""
    ARCHIVED_PORTFOLIO_FILE.parent.mkdir(exist_ok=True, parents=True)
    with open(ARCHIVED_PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2)

def add_position(
    raw_ticker: str,
    direction: str,
    entry_price: float,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None
) -> Dict[str, Any]:
    """Aggiunge una nuova posizione aperta (BUY o SELL) al portafoglio."""
    ticker = resolve_ticker(raw_ticker)
    direction = direction.upper().strip()
    if direction not in ["BUY", "SELL", "LONG", "SHORT"]:
        direction = "BUY"
    if direction in ["LONG"]:
        direction = "BUY"
    elif direction in ["SHORT"]:
        direction = "SELL"

    entry_price = float(entry_price)
    if not math.isfinite(entry_price) or entry_price <= 0:
        raise ValueError("Il prezzo di ingresso deve essere un numero maggiore di zero.")

    positions = load_portfolio()
    # Rimuove eventuale posizione preesistente sullo stesso ticker per aggiornarla
    positions = [p for p in positions if p.get("ticker") != ticker]

    new_pos = {
        "ticker": ticker,
        "raw_ticker": raw_ticker.upper().strip(),
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": float(stop_loss) if stop_loss else None,
        "take_profit": float(take_profit) if take_profit else None,
        "date_added": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    positions.append(new_pos)
    save_portfolio(positions)
    return new_pos

def update_entry_price(raw_ticker: str, entry_price: float) -> bool:
    """Aggiorna il prezzo di ingresso di una posizione aperta."""
    price = float(entry_price)
    if not math.isfinite(price) or price <= 0:
        raise ValueError("Il prezzo di ingresso deve essere maggiore di zero.")

    ticker = resolve_ticker(raw_ticker)
    positions = load_portfolio()
    for position in positions:
        if position.get("ticker") == ticker or position.get("raw_ticker") == raw_ticker.upper().strip():
            position["entry_price"] = price
            save_portfolio(positions)
            return True
    return False

def update_stop_loss(raw_ticker: str, stop_loss: float) -> bool:
    """Aggiorna il livello di Stop Loss di una posizione aperta."""
    sl = float(stop_loss)
    if not math.isfinite(sl) or sl <= 0:
        raise ValueError("Lo Stop Loss deve essere maggiore di zero.")

    ticker = resolve_ticker(raw_ticker)
    positions = load_portfolio()
    for position in positions:
        if position.get("ticker") == ticker or position.get("raw_ticker") == raw_ticker.upper().strip():
            position["stop_loss"] = sl
            save_portfolio(positions)
            return True
    return False

def update_take_profit(raw_ticker: str, take_profit: float) -> bool:
    """Aggiorna il livello di Take Profit di una posizione aperta."""
    tp = float(take_profit)
    if not math.isfinite(tp) or tp <= 0:
        raise ValueError("Il Take Profit deve essere maggiore di zero.")

    ticker = resolve_ticker(raw_ticker)
    positions = load_portfolio()
    for position in positions:
        if position.get("ticker") == ticker or position.get("raw_ticker") == raw_ticker.upper().strip():
            position["take_profit"] = tp
            save_portfolio(positions)
            return True
    return False

def remove_position(raw_ticker: str) -> bool:
    """Rimuove/chiude una posizione dal portafoglio."""
    ticker = resolve_ticker(raw_ticker)
    positions = load_portfolio()
    initial_len = len(positions)
    positions = [p for p in positions if p.get("ticker") != ticker and p.get("raw_ticker") != raw_ticker.upper().strip()]
    if len(positions) < initial_len:
        save_portfolio(positions)
        return True
    return False

def archive_position(raw_ticker: str) -> bool:
    """Sposta una posizione aperta nello storico, conservandone i dati."""
    ticker = resolve_ticker(raw_ticker)
    positions = load_portfolio()
    archived = next(
        (position for position in positions
         if position.get("ticker") == ticker or position.get("raw_ticker") == raw_ticker.upper().strip()),
        None
    )
    if archived is None:
        return False

    positions.remove(archived)
    archived["archived_at"] = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Prova a determinare il prezzo di uscita attuale e calcolare il P&L realizzato
    try:
        df, analysis = fetch_ticker_data_and_analysis(ticker)
        if analysis and "current_price" in analysis:
            exit_price = float(analysis["current_price"])
            entry_price = float(archived.get("entry_price", exit_price))
            direction = archived.get("direction", "BUY")
            if direction == "BUY":
                final_pnl = ((exit_price - entry_price) / entry_price) * 100
            else:
                final_pnl = ((entry_price - exit_price) / entry_price) * 100
            archived["exit_price"] = round(exit_price, 4)
            archived["final_pnl_pct"] = round(final_pnl, 2)
    except Exception as e:
        logger.warning(f"Impossibile calcolare exit_price per archiviazione {ticker}: {e}")

    history = load_archived_portfolio()
    history.append(archived)
    save_archived_portfolio(history)
    save_portfolio(positions)
    return True

def clear_portfolio() -> None:
    """Svuota tutte le posizioni del portafoglio."""
    save_portfolio([])

def evaluate_single_position(pos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Analizza lo stato di salute di una singola posizione nel portafoglio e fornisce un consiglio:
    - MANTIENI (HOLD)
    - ALZA/ABBASSA STOP A PAREGGIO (BREAK-EVEN)
    - TAKE PROFIT RAGGIUNTO (INCASSA O ALLEGGIRISCI)
    - CAMBIA STRATEGIA / CHIUDI (INVERSIONE TREND)
    - STOP LOSS CRITICO (PROTEGGI CAPITALE)
    """
    ticker = pos["ticker"]
    direction = pos["direction"]
    entry_price = float(pos["entry_price"])
    user_sl = pos.get("stop_loss")
    user_tp = pos.get("take_profit")

    df, analysis = fetch_ticker_data_and_analysis(ticker)
    if not analysis or df is None:
        return None

    current_price = analysis["current_price"]
    market_action = analysis["action"]
    market_score = analysis["score"]
    rsi = analysis["rsi"]

    # Calcolo Profit & Loss percentuale
    if direction == "BUY":
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
    else:  # SELL (Short)
        pnl_pct = ((entry_price - current_price) / entry_price) * 100

    # Livelli di Stop Loss e Take Profit coerenti con la direzione del trade
    if user_sl:
        sl = float(user_sl)
    else:
        if direction == "BUY":
            sl = analysis["stop_loss"] if analysis["action"] == "BUY" else round(entry_price * 0.95, 4)
        else:
            sl = analysis["stop_loss"] if analysis["action"] == "SELL" else round(entry_price * 1.05, 4)

    if user_tp:
        tp = float(user_tp)
    else:
        if direction == "BUY":
            tp = analysis["take_profit_2"] if analysis["action"] == "BUY" else round(entry_price * 1.10, 4)
        else:
            tp = analysis["take_profit_2"] if analysis["action"] == "SELL" else round(entry_price * 0.90, 4)

    # Regole di Valutazione e Consiglio
    advice_code = "HOLD"
    advice_title = "MANTIENI LA POSIZIONE"
    advice_icon = "✅"
    advice_detail = "Il setup rimane valido e coerente con la tua operazione."

    if direction == "BUY":
        # Posizione LONG
        if current_price <= sl:
            advice_code = "STOP_LOSS"
            advice_title = "STOP LOSS CRITICO / VALUTA USCITA"
            advice_icon = "🚨"
            advice_detail = f"Il prezzo ha toccato o rotto il livello di Stop Loss ({sl:,.2f}). Consigliata chiusura per proteggere il capitale."
        elif current_price >= tp:
            advice_code = "TAKE_PROFIT"
            advice_title = "TARGET TAKE PROFIT RAGGIUNTO"
            advice_icon = "🎯"
            advice_detail = f"Il target prefissato ({tp:,.2f}) è stato raggiunto. Ottimo momento per incassare o chiudere il 70% della posizione."
        elif pnl_pct >= 3.0:
            advice_code = "BREAK_EVEN"
            advice_title = "PROTEGGI IL PROFITTO (SPOSTA SL A PAREGGIO)"
            advice_icon = "🛡"
            advice_detail = f"Sei in utile del {pnl_pct:+.2f}%. Sposta lo Stop Loss al prezzo di ingresso ({entry_price:,.2f}) per azzerare il rischio."
        elif market_action == "SELL" and market_score >= 60:
            advice_code = "TREND_REVERSAL"
            advice_title = "ATTENZIONE: CAMBIO TREND A RIBASSO"
            advice_icon = "⚠️"
            advice_detail = f"Il motore analitico rileva forte pressione ribassista (Score SELL: {market_score}/100, RSI: {rsi}). Valuta di chiudere o alleggerire."
        elif pnl_pct > 0:
            advice_code = "HOLD_PROFIT"
            advice_title = "MANTIENI (IN UTILE)"
            advice_icon = "🟢"
            advice_detail = f"Operazione in guadagno ({pnl_pct:+.2f}%). Il trend rialzista supporta la continuazione verso i target."
        else:
            advice_code = "HOLD_DRAWDOWN"
            advice_title = "MANTIENI (LIEVE FLESSIONE SOTTO CONTROLLO)"
            advice_icon = "🟡"
            advice_detail = f"Lieve ritracciamento ({pnl_pct:+.2f}%), ma sopra il livello di Stop Loss. Mantieni con disciplina."

    else:
        # Posizione SHORT (SELL)
        if current_price >= sl:
            advice_code = "STOP_LOSS"
            advice_title = "STOP LOSS CRITICO / VALUTA USCITA"
            advice_icon = "🚨"
            advice_detail = f"Il prezzo è salito oltre lo Stop Loss ({sl:,.2f}). Consigliata chiusura dello short per limitare le perdite."
        elif current_price <= tp:
            advice_code = "TAKE_PROFIT"
            advice_title = "TARGET TAKE PROFIT RAGGIUNTO"
            advice_icon = "🎯"
            advice_detail = f"Il target ribassista ({tp:,.2f}) è stato centrato. Ottimo momento per incassare il profitto dello short."
        elif pnl_pct >= 3.0:
            advice_code = "BREAK_EVEN"
            advice_title = "PROTEGGI IL PROFITTO (SL A PAREGGIO)"
            advice_icon = "🛡"
            advice_detail = f"Lo short è in utile del {pnl_pct:+.2f}%. Sposta lo Stop Loss al livello di ingresso ({entry_price:,.2f}) per rendere il trade a rischio zero."
        elif market_action == "BUY" and market_score >= 60:
            advice_code = "TREND_REVERSAL"
            advice_title = "ATTENZIONE: RIMBALZO RIALZISTA IN CORSO"
            advice_icon = "⚠️"
            advice_detail = f"Il mercato mostra segnali di acquisto marcati (Score BUY: {market_score}/100, RSI: {rsi}). Valuta di chiudere lo short."
        elif pnl_pct > 0:
            advice_code = "HOLD_PROFIT"
            advice_title = "MANTIENI SHORT (IN UTILE)"
            advice_icon = "🟢"
            advice_detail = f"Short in guadagno ({pnl_pct:+.2f}%). La debolezza dei prezzi supporta il proseguimento verso i target."
        else:
            advice_code = "HOLD_DRAWDOWN"
            advice_title = "MANTIENI SHORT (SOTTO CONTROLLO)"
            advice_icon = "🟡"
            advice_detail = f"Prezzo in temporaneo rimbalzo ({pnl_pct:+.2f}%), ma lo Stop Loss ({sl:,.2f}) tiene. Mantieni la posizione."

    return {
        "ticker": ticker,
        "raw_ticker": pos.get("raw_ticker", ticker),
        "direction": direction,
        "entry_price": entry_price,
        "current_price": current_price,
        "pnl_pct": round(pnl_pct, 2),
        "stop_loss": sl,
        "take_profit": tp,
        "date_added": pos.get("date_added", "N/A"),
        "advice_code": advice_code,
        "advice_title": advice_title,
        "advice_icon": advice_icon,
        "advice_detail": advice_detail,
        "market_action": market_action,
        "market_score": market_score,
        "rsi": rsi,
        "asset_type": analysis.get("asset_type", "stock")
    }

def evaluate_full_portfolio() -> List[Dict[str, Any]]:
    """Esegue l'analisi completa di tutte le posizioni aperte nel portafoglio."""
    positions = load_portfolio()
    results = []
    for pos in positions:
        try:
            ev = evaluate_single_position(pos)
            if ev:
                results.append(ev)
        except Exception as e:
            logger.error(f"Errore durante la valutazione della posizione {pos.get('ticker')}: {e}")
    return results

#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

PID_FILE="$DIR/bot.pid"
LOG_FILE="$DIR/bot.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️ Il bot è già in esecuzione (PID: $PID)."
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

if [ ! -d ".venv" ]; then
    echo "❌ Ambiente virtuale non trovato! Esegui prima setup dipendenze."
    exit 1
fi

echo "🚀 Avvio di BotTrading in background..."
nohup .venv/bin/python run.py > "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"

sleep 1
if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ Bot avviato con successo! (PID: $PID)"
    echo "📄 I log sono consultabili in tempo reale con: tail -f bot.log"
else
    echo "❌ Errore durante l'avvio del bot. Consulta il file bot.log:"
    cat "$LOG_FILE"
fi


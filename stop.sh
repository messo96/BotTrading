#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

PID_FILE="$DIR/bot.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "ℹ️ Nessun file PID trovato. Cerco processi attivi di run.py..."
    PIDS=$(pgrep -f "python.*run.py")
    if [ -n "$PIDS" ]; then
        echo "Trovati processi: $PIDS. Arresto in corso..."
        kill $PIDS
        echo "✅ Bot arrestato."
    else
        echo "ℹ️ Nessun bot in esecuzione trovato."
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")
if ps -p "$PID" > /dev/null 2>&1; then
    echo "🛑 Arresto di BotTrading (PID: $PID)..."
    kill "$PID"
    sleep 1
    if ps -p "$PID" > /dev/null 2>&1; then
        kill -9 "$PID"
    fi
    rm -f "$PID_FILE"
    echo "✅ Bot arrestato con successo."
else
    echo "ℹ️ Il processo (PID: $PID) non era in esecuzione."
    rm -f "$PID_FILE"
fi

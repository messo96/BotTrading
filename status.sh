#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

PID_FILE="$DIR/bot.pid"
LOG_FILE="$DIR/bot.log"

echo "============================================================"
echo "          STATO TRADING BROKER ASSISTANT BOT                "
echo "============================================================"

RUNNING=false
PID=""

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        RUNNING=true
    fi
fi

if [ "$RUNNING" = false ]; then
    SYS_PID=$(pgrep -f "python.*run.py" | head -n 1)
    if [ -n "$SYS_PID" ]; then
        PID="$SYS_PID"
        RUNNING=true
    fi
fi

if [ "$RUNNING" = true ]; then
    echo "🟢 STATO: ATTIVO E IN ESECUZIONE"
    echo "• PID di sistema: $PID"
    echo "• Processo: $(ps -p $PID -o command= | cut -c 1-60)..."
else
    echo "🔴 STATO: NON IN ESECUZIONE"
    echo "• Per avviarlo: ./start.sh oppure python run.py"
fi

if [ -f "$LOG_FILE" ]; then
    echo "------------------------------------------------------------"
    echo "Ultime righe del file di log (bot.log):"
    tail -n 10 "$LOG_FILE"
fi
echo "============================================================"


#!/bin/bash
# 10-Hour Paper Trading Monitor Script
# Dieses Script läuft im Hintergrund für 10 Stunden

WORKSPACE="/data/.openclaw/workspace/projects/trading-bot"
LOG_FILE="$WORKSPACE/logs/10h_run.log"
REPORT_FILE="$WORKSPACE/final_report_10h.json"
REPORTS_DIR="$WORKSPACE/reports"
INITIAL_CAPITAL=10000

# Erstelle Verzeichnisse
mkdir -p "$WORKSPACE/logs"
mkdir -p "$REPORTS_DIR"

# Logging-Funktion
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local message="[$timestamp] $1"
    echo "$message"
    echo "$message" >> "$LOG_FILE"
}

# Header
log "======================================================================"
log "STARTING 10-HOUR PAPER TRADING SESSION"
log "======================================================================"
log "Symbol: AAPL"
log "Strategy: sma_crossover"
log "Initial Capital: \$${INITIAL_CAPITAL}"
log "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
log "End Time: $(date -d '+10 hours' '+%Y-%m-%d %H:%M:%S')"
log "----------------------------------------------------------------------"

# Starte das Monitoring
START_TIME=$(date +%s)
END_TIME=$((START_TIME + 36000))  # 10 Stunden = 36000 Sekunden
ITERATION=0

while [ $(date +%s) -lt $END_TIME ]; do
    ITERATION=$((ITERATION + 1))
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    RUNNING_HOURS=$(python3 -c "print(f'{$ELAPSED / 3600:.1f}')")
    
    # Starte einen Paper Trading Durchlauf
    cd "$WORKSPACE"
    python3 trading_bot.py --mode paper --symbol AAPL --strategy sma_crossover --save-report >> "$WORKSPACE/logs/bot_output.log" 2>&1
    RETURN_CODE=$?
    
    # Extrahiere Werte aus dem neuesten Report
    LATEST_REPORT=$(ls -t "$REPORTS_DIR"/paper_trading_AAPL_sma_crossover_*.json 2>/dev/null | head -1)
    
    if [ -f "$LATEST_REPORT" ]; then
        PORTFOLIO=$(python3 -c "import json; d=json.load(open('$LATEST_REPORT')); print(f'{d.get(\"total_value\", $INITIAL_CAPITAL):.2f}')")
        TRADES=$(python3 -c "import json; d=json.load(open('$LATEST_REPORT')); print(d.get(\"trade_count\", 0))")
        PNL=$(python3 -c "import json; d=json.load(open('$LATEST_REPORT')); print(f'{d.get(\"total_pnl\", 0):+.2f}')")
    else
        PORTFOLIO="$INITIAL_CAPITAL.00"
        TRADES="0"
        PNL="+0.00"
    fi
    
    # Logge den Status
    log "Portfolio: \$${PORTFOLIO} | Trades: ${TRADES} | P&L: \$${PNL} | Running: ${RUNNING_HOURS}h"
    
    # Speichere Zwischenstand
    STATE_FILE="$WORKSPACE/logs/state_$(printf "%04d" $ITERATION).json"
    python3 -c "
import json
from datetime import datetime
state = {
    'timestamp': datetime.now().isoformat(),
    'iteration': $ITERATION,
    'portfolio_value': $PORTFOLIO,
    'trades_count': $TRADES,
    'pnl': $PNL,
    'running_hours': $RUNNING_HOURS
}
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null
    
    # Warte bis zur nächsten 30-Minuten-Marke
    NEXT_CHECK=$((START_TIME + (ITERATION * 1800)))
    CURRENT_TIME=$(date +%s)
    WAIT_TIME=$((NEXT_CHECK - CURRENT_TIME))
    
    if [ $WAIT_TIME -gt 0 ]; then
        log "Waiting $((WAIT_TIME / 60)) minutes until next cycle..."
        sleep $WAIT_TIME
    fi
done

# Finaler Report
log "======================================================================"
log "SESSION COMPLETE - GENERATING FINAL REPORT"
log "======================================================================"

# Hole letzte Werte
LATEST_REPORT=$(ls -t "$REPORTS_DIR"/paper_trading_AAPL_sma_crossover_*.json 2>/dev/null | head -1)
if [ -f "$LATEST_REPORT" ]; then
    FINAL_PORTFOLIO=$(python3 -c "import json; d=json.load(open('$LATEST_REPORT')); print(d.get('total_value', $INITIAL_CAPITAL))")
    FINAL_TRADES=$(python3 -c "import json; d=json.load(open('$LATEST_REPORT')); print(d.get('trade_count', 0))")
    FINAL_PNL=$(python3 -c "import json; d=json.load(open('$LATEST_REPORT')); print(d.get('total_pnl', 0))")
else
    FINAL_PORTFOLIO=$INITIAL_CAPITAL
    FINAL_TRADES=0
    FINAL_PNL=0
fi

TOTAL_HOURS="10.0"

# Erstelle finalen Report
python3 -c "
import json
from datetime import datetime, timedelta

report = {
    'session_start': datetime.fromtimestamp($START_TIME).isoformat(),
    'session_end': datetime.now().isoformat(),
    'duration_hours': $TOTAL_HOURS,
    'symbol': 'AAPL',
    'strategy': 'sma_crossover',
    'initial_capital': $INITIAL_CAPITAL,
    'final_portfolio_value': $FINAL_PORTFOLIO,
    'total_return_pct': (($FINAL_PORTFOLIO - $INITIAL_CAPITAL) / $INITIAL_CAPITAL) * 100,
    'total_trades': $FINAL_TRADES,
    'total_pnl': $FINAL_PNL,
    'iterations': $ITERATION
}

with open('$REPORT_FILE', 'w') as f:
    json.dump(report, f, indent=2)

print(f'Duration: {TOTAL_HOURS} hours')
print(f'Initial Capital: \${INITIAL_CAPITAL:,.2f}')
print(f'Final Portfolio: \${FINAL_PORTFOLIO:,.2f}')
print(f'Total Return: {((FINAL_PORTFOLIO - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100:.2f}%')
print(f'Total Trades: {FINAL_TRADES}')
print(f'P&L: \${FINAL_PNL:+.2f}')
print(f'Report saved to: {REPORT_FILE}')
" 2>/dev/null

log "Duration: ${TOTAL_HOURS} hours"
log "Initial Capital: \$${INITIAL_CAPITAL}"
log "Final Portfolio: \$${FINAL_PORTFOLIO}"
log "Total Return: $(python3 -c "print(f'{((float($FINAL_PORTFOLIO) - $INITIAL_CAPITAL) / $INITIAL_CAPITAL) * 100:.2f}')")%"
log "Total Trades: ${FINAL_TRADES}"
log "P&L: \$${FINAL_PNL}"
log "Report saved to: ${REPORT_FILE}"
log "======================================================================"

#!/usr/bin/env python3
"""
PLTR 6-Hour Periodic Paper Trading Test
Simulates live paper trading by running the bot periodically over 6 hours
"""

import subprocess
import time
import json
import os
import sys
import signal
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

# Configuration
WORKSPACE = "/data/.openclaw/workspace/projects/trading-bot"
LOG_FILE = Path(f"{WORKSPACE}/logs/pltr_6h_test.log")
REPORT_FILE = Path(f"{WORKSPACE}/reports/pltr_6h_report.json")
DB_FILE = Path(f"{WORKSPACE}/data/paper_trades_PLTR_mean_reversion.db")
DURATION_HOURS = 6
RUN_INTERVAL_MINUTES = 30  # Run every 30 minutes

running = True
all_trades = []
start_capital = 10000.0


def log(message):
    """Write message to log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')


def run_bot_iteration():
    """Run one iteration of the bot"""
    cmd = [
        "python3", "trading_bot.py",
        "--mode", "paper",
        "--symbol", "PLTR",
        "--strategy", "mean_reversion",
        "--save-report"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=WORKSPACE,
            timeout=300  # 5 minute timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def get_portfolio_status():
    """Get current portfolio status from database"""
    if not DB_FILE.exists():
        return None
    
    try:
        conn = sqlite3.connect(str(DB_FILE))
        cursor = conn.cursor()
        
        # Get latest portfolio snapshot
        cursor.execute('''
            SELECT timestamp, cash, total_value, unrealized_pnl, positions 
            FROM portfolio_snapshots 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        snapshot = cursor.fetchone()
        
        # Get all trades
        cursor.execute('''
            SELECT timestamp, symbol, side, quantity, price, pnl, pnl_pct, notes
            FROM trades WHERE symbol = ? ORDER BY timestamp
        ''', ('PLTR',))
        
        trades = []
        for row in cursor.fetchall():
            trades.append({
                'timestamp': row[0],
                'symbol': row[1],
                'side': row[2],
                'quantity': row[3],
                'price': row[4],
                'pnl': row[5],
                'pnl_pct': row[6],
                'notes': row[7]
            })
        
        conn.close()
        
        return {
            'snapshot': snapshot,
            'trades': trades
        }
    except Exception as e:
        log(f"Error reading DB: {e}")
        return None


def calculate_performance():
    """Calculate final performance metrics"""
    status = get_portfolio_status()
    if not status:
        return None
    
    trades = status['trades']
    
    if not trades:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0,
            'win_rate': 0
        }
    
    total_pnl = sum(t.get('pnl', 0) or 0 for t in trades)
    total_trades = len(trades)
    winning_trades = len([t for t in trades if (t.get('pnl') or 0) > 0])
    losing_trades = len([t for t in trades if (t.get('pnl') or 0) < 0])
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'total_pnl': round(total_pnl, 2),
        'win_rate': round(winning_trades / total_trades * 100, 2) if total_trades > 0 else 0
    }


def generate_report(start_time, end_time):
    """Generate final JSON report"""
    status = get_portfolio_status()
    performance = calculate_performance()
    
    report = {
        "test_name": "PLTR 6H Paper Trading Test",
        "symbol": "PLTR",
        "strategy": "mean_reversion",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_hours": DURATION_HOURS,
        "run_interval_minutes": RUN_INTERVAL_MINUTES,
        "summary": performance if performance else {},
        "trades": status['trades'] if status else []
    }
    
    REPORT_FILE.parent.mkdir(exist_ok=True)
    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report


def signal_handler(signum, frame):
    """Handle termination signals"""
    global running
    log("\n⚠️  Signal received, shutting down...")
    running = False


def main():
    """Main entry point"""
    global running
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Clear previous log and DB
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, 'w') as f:
        f.write(f"""=== PLTR 6-Hour Periodic Paper Trading Test ===
Symbol: PLTR
Strategy: mean_reversion
Started: {datetime.now().isoformat()}
Duration: {DURATION_HOURS} hours
Run Interval: {RUN_INTERVAL_MINUTES} minutes

""")
    
    if DB_FILE.exists():
        DB_FILE.unlink()
    
    log("="*70)
    log("PLTR 6-HOUR PERIODIC PAPER TRADING TEST")
    log("="*70)
    log(f"Symbol: PLTR")
    log(f"Strategy: mean_reversion")
    log(f"Duration: {DURATION_HOURS} hours")
    log(f"Run interval: Every {RUN_INTERVAL_MINUTES} minutes")
    log(f"Log file: {LOG_FILE}")
    log(f"Report file: {REPORT_FILE}")
    log(f"Database: {DB_FILE}")
    log("="*70)
    
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=DURATION_HOURS)
    iteration = 0
    
    log(f"\nStart time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log("="*70)
    
    try:
        while running and datetime.now() < end_time:
            iteration += 1
            elapsed = (datetime.now() - start_time).total_seconds() / 3600
            remaining = (end_time - datetime.now()).total_seconds() / 3600
            
            log("\n" + "="*70)
            log(f"ITERATION #{iteration} - Hour {elapsed:.2f}/{DURATION_HOURS}")
            log("="*70)
            
            # Run the bot
            log("Running bot...")
            returncode, stdout, stderr = run_bot_iteration()
            
            if returncode == 0:
                log("✅ Bot completed successfully")
            else:
                log(f"⚠️  Bot exited with code {returncode}")
                if stderr:
                    log(f"Error: {stderr[:200]}")
            
            # Get status
            status = get_portfolio_status()
            if status and status['snapshot']:
                snap = status['snapshot']
                log(f"\n📊 Portfolio Status:")
                log(f"   Cash: ${snap[1]:.2f}")
                log(f"   Total Value: ${snap[2]:.2f}")
                log(f"   Unrealized P&L: ${snap[3]:.2f}")
                log(f"   Total Trades: {len(status['trades'])}")
            
            # Wait for next iteration
            if running and datetime.now() < end_time:
                next_run = datetime.now() + timedelta(minutes=RUN_INTERVAL_MINUTES)
                log(f"\n⏱️  Next run at: {next_run.strftime('%H:%M:%S')}")
                log(f"   Sleeping for {RUN_INTERVAL_MINUTES} minutes...")
                
                # Sleep in small chunks to allow for signal handling
                sleep_start = time.time()
                while running and time.time() - sleep_start < RUN_INTERVAL_MINUTES * 60:
                    time.sleep(1)
    
    except KeyboardInterrupt:
        log("\n⚠️  Interrupted by user")
    
    # Generate final report
    log("\n" + "="*70)
    log("GENERATING FINAL REPORT")
    log("="*70)
    
    report = generate_report(start_time, datetime.now())
    
    # Print final summary
    log("\n" + "="*70)
    log("FINAL SUMMARY")
    log("="*70)
    log(f"Total Iterations: {iteration}")
    log(f"Total Trades: {report['summary'].get('total_trades', 0)}")
    log(f"Winning Trades: {report['summary'].get('winning_trades', 0)}")
    log(f"Losing Trades: {report['summary'].get('losing_trades', 0)}")
    log(f"Total P&L: ${report['summary'].get('total_pnl', 0):+.2f}")
    log(f"Win Rate: {report['summary'].get('win_rate', 0):.1f}%")
    log("="*70)
    log(f"\n✅ Report saved: {REPORT_FILE}")
    log("✅ PLTR 6-hour test completed!")
    
    return report


if __name__ == "__main__":
    result = main()
    sys.exit(0)

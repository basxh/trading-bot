#!/usr/bin/env python3
"""
PLTR 6-Hour Paper Trading Test Runner
Single asset test with Mean Reversion strategy
"""

import subprocess
import time
import json
import os
import sys
import signal
from datetime import datetime, timedelta
from pathlib import Path
import threading

# Configuration
WORKSPACE = "/data/.openclaw/workspace/projects/trading-bot"
LOG_FILE = Path(f"{WORKSPACE}/logs/pltr_6h_test.log")
REPORT_FILE = Path(f"{WORKSPACE}/reports/pltr_6h_report.json")
DURATION_HOURS = 6
CHECK_INTERVAL_MINUTES = 15

running = True


def log(message, file_only=False):
    """Write message to log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    if not file_only:
        print(log_line)
    
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')


def status_check_paper_trader():
    """Check portfolio status from paper_trades.db"""
    db_path = Path(f"{WORKSPACE}/data/paper_trades.db")
    if not db_path.exists():
        return None
    
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get latest portfolio snapshot
        cursor.execute('''
            SELECT timestamp, cash, total_value, unrealized_pnl, positions 
            FROM portfolio_snapshots 
            ORDER BY timestamp DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        
        # Get trade count
        cursor.execute('SELECT COUNT(*) FROM trades WHERE symbol = ?', ('PLTR',))
        trade_count = cursor.fetchone()[0]
        
        conn.close()
        
        if row:
            return {
                'timestamp': row[0],
                'cash': row[1],
                'total_value': row[2],
                'unrealized_pnl': row[3],
                'positions': row[4],
                'trade_count': trade_count
            }
    except Exception as e:
        log(f"Error reading status: {e}", file_only=True)
    
    return None


def generate_final_report(start_time, end_time, trades):
    """Generate final JSON report"""
    
    # Calculate total P&L
    total_pnl = sum(t.get('pnl', 0) or 0 for t in trades)
    total_trades = len(trades)
    winning_trades = len([t for t in trades if (t.get('pnl') or 0) > 0])
    losing_trades = len([t for t in trades if (t.get('pnl') or 0) < 0])
    
    report = {
        "test_name": "PLTR 6H Paper Trading Test",
        "symbol": "PLTR",
        "strategy": "mean_reversion",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_hours": DURATION_HOURS,
        "summary": {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(winning_trades / total_trades * 100, 2) if total_trades > 0 else 0
        },
        "trades": trades
    }
    
    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
    
    log(f"\n✅ Final report saved: {REPORT_FILE}")
    return report


def get_trades_from_db():
    """Get all trades from database"""
    db_path = Path(f"{WORKSPACE}/data/paper_trades.db")
    if not db_path.exists():
        return []
    
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
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
        return trades
    except Exception as e:
        log(f"Error getting trades: {e}")
        return []


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
    
    # Clear previous log
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, 'w') as f:
        f.write(f"""=== PLTR 6-Hour Paper Trading Test ===
Symbol: PLTR
Strategy: mean_reversion
Started: {datetime.now().isoformat()}
Duration: {DURATION_HOURS} hours
Check interval: {CHECK_INTERVAL_MINUTES} minutes

""")
    
    log("="*70)
    log("PLTR 6-HOUR PAPER TRADING TEST")
    log("="*70)
    log(f"Symbol: PLTR")
    log(f"Strategy: mean_reversion")
    log(f"Duration: {DURATION_HOURS} hours")
    log(f"Status updates: Every {CHECK_INTERVAL_MINUTES} minutes")
    log(f"Log file: {LOG_FILE}")
    log(f"Report file: {REPORT_FILE}")
    log("="*70)
    
    # Build command
    cmd = [
        "python3", "trading_bot.py",
        "--mode", "paper",
        "--symbol", "PLTR",
        "--strategy", "mean_reversion",
        "--save-report"
    ]
    
    log(f"\nStarting with command: {' '.join(cmd)}")
    
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=DURATION_HOURS)
    last_check = start_time
    check_interval = CHECK_INTERVAL_MINUTES * 60
    
    # Start the process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=WORKSPACE,
        universal_newlines=True
    )
    
    log(f"Process started (PID: {process.pid})")
    log(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        while running and datetime.now() < end_time:
            current_time = datetime.now()
            
            # Check if it's time for status update
            if (current_time - last_check).total_seconds() >= check_interval:
                elapsed = (current_time - start_time).total_seconds() / 3600
                remaining = (end_time - current_time).total_seconds() / 3600
                
                log("\n" + "-"*70)
                log(f"STATUS UPDATE - Hour {elapsed:.1f}/{DURATION_HOURS} (Remaining: {remaining:.1f}h)")
                log("-"*70)
                
                # Get portfolio status
                status = status_check_paper_trader()
                if status:
                    log(f"Cash: ${status['cash']:.2f}")
                    log(f"Total Value: ${status['total_value']:.2f}")
                    log(f"Unrealized P&L: ${status['unrealized_pnl']:.2f}")
                    log(f"Total Trades: {status['trade_count']}")
                else:
                    log("Portfolio status: Not yet available")
                
                last_check = current_time
            
            # Check if process is still running
            if process.poll() is not None:
                log(f"\n⚠️  Process exited with code: {process.poll()}")
                break
            
            # Brief sleep to prevent CPU spinning
            time.sleep(5)
            
    except KeyboardInterrupt:
        log("\n⚠️  Interrupted by user")
    finally:
        # Terminate process if still running
        if process.poll() is None:
            log("\nTerminating trading process...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    
    # Generate final report
    log("\n" + "="*70)
    log("GENERATING FINAL REPORT")
    log("="*70)
    
    trades = get_trades_from_db()
    report = generate_final_report(start_time, datetime.now(), trades)
    
    # Print summary
    log("\n" + "="*70)
    log("FINAL SUMMARY")
    log("="*70)
    log(f"Total Trades: {report['summary']['total_trades']}")
    log(f"Winning Trades: {report['summary']['winning_trades']}")
    log(f"Losing Trades: {report['summary']['losing_trades']}")
    log(f"Total P&L: ${report['summary']['total_pnl']:+.2f}")
    log(f"Win Rate: {report['summary']['win_rate']:.1f}%")
    log("="*70)
    log("\n✅ PLTR 6-hour test completed!")
    
    return report


if __name__ == "__main__":
    result = main()
    sys.exit(0)

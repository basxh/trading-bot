#!/usr/bin/env python3
"""
10-Hour Paper Trading Monitor
Ein zuverlässiger Python-Monitor, der alle 30 Minuten Status loggt.
"""
import subprocess
import time
import json
import os
import glob
from datetime import datetime, timedelta

# Configuration
WORKSPACE = "/data/.openclaw/workspace/projects/trading-bot"
LOG_FILE = os.path.join(WORKSPACE, "logs/10h_run.log")
REPORT_FILE = os.path.join(WORKSPACE, "final_report_10h.json")
REPORTS_DIR = os.path.join(WORKSPACE, "reports")
INITIAL_CAPITAL = 10000.00
RUN_DURATION_HOURS = 10
CHECK_INTERVAL_MINUTES = 30


def log(message):
    """Write message to log file and print to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')


def run_paper_trading():
    """Run a single paper trading iteration"""
    cmd = [
        "python3", "trading_bot.py",
        "--mode", "paper",
        "--symbol", "AAPL",
        "--strategy", "sma_crossover",
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


def get_latest_report_data():
    """Extract data from the most recent report file"""
    report_files = glob.glob(os.path.join(REPORTS_DIR, "paper_trading_AAPL_sma_crossover_*.json"))
    if not report_files:
        return INITIAL_CAPITAL, 0, 0.0
    
    latest_report = max(report_files, key=os.path.getmtime)
    
    try:
        with open(latest_report, 'r') as f:
            data = json.load(f)
        return (
            float(data.get('total_value', INITIAL_CAPITAL)),
            int(data.get('trade_count', 0)),
            float(data.get('total_pnl', 0.0))
        )
    except:
        return INITIAL_CAPITAL, 0, 0.0


def main():
    """Main entry point - runs for 10 hours with periodic updates"""
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=RUN_DURATION_HOURS)
    
    # Create directories
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # Clear previous log
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    
    # Header
    log("=" * 70)
    log("STARTING 10-HOUR PAPER TRADING SESSION")
    log("=" * 70)
    log(f"Symbol: AAPL")
    log(f"Strategy: sma_crossover")
    log(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    log(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log("-" * 70)
    
    iteration = 0
    next_check = start_time + timedelta(minutes=CHECK_INTERVAL_MINUTES)
    
    try:
        while datetime.now() < end_time:
            iteration += 1
            elapsed = (datetime.now() - start_time).total_seconds()
            running_hours = elapsed / 3600
            
            # Run paper trading
            log(f"Running paper trading iteration {iteration}...")
            returncode, stdout, stderr = run_paper_trading()
            
            if returncode == 0:
                # Get data from report
                portfolio_value, trades_count, pnl = get_latest_report_data()
                
                # Log status
                log(f"Portfolio: ${portfolio_value:,.2f} | Trades: {trades_count} | P&L: ${pnl:+,.2f} | Running: {running_hours:.1f}h")
                
                # Save intermediate state
                state_file = os.path.join(WORKSPACE, f"logs/state_{iteration:04d}.json")
                state = {
                    "timestamp": datetime.now().isoformat(),
                    "iteration": iteration,
                    "portfolio_value": portfolio_value,
                    "trades_count": trades_count,
                    "pnl": pnl,
                    "running_hours": running_hours
                }
                with open(state_file, 'w') as f:
                    json.dump(state, f, indent=2)
            else:
                log(f"ERROR: Bot returned code {returncode}")
                if stderr:
                    log(f"Error: {stderr[:200]}")
            
            # Calculate time to next check
            now = datetime.now()
            if now < next_check:
                wait_seconds = (next_check - now).total_seconds()
                wait_minutes = int(wait_seconds / 60)
                log(f"Waiting {wait_minutes} minutes until next cycle...")
                time.sleep(wait_seconds)
            
            # Update next check time
            next_check = next_check + timedelta(minutes=CHECK_INTERVAL_MINUTES)
            
    except KeyboardInterrupt:
        log("Session interrupted by user")
    except Exception as e:
        log(f"ERROR: {str(e)}")
    
    # Final report
    log("=" * 70)
    log("SESSION COMPLETE - GENERATING FINAL REPORT")
    log("=" * 70)
    
    # Get final values
    final_portfolio, final_trades, final_pnl = get_latest_report_data()
    elapsed = (datetime.now() - start_time).total_seconds()
    total_hours = elapsed / 3600
    total_return_pct = ((final_portfolio - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    
    report = {
        "session_start": start_time.isoformat(),
        "session_end": datetime.now().isoformat(),
        "duration_hours": total_hours,
        "symbol": "AAPL",
        "strategy": "sma_crossover",
        "initial_capital": INITIAL_CAPITAL,
        "final_portfolio_value": final_portfolio,
        "total_return_pct": total_return_pct,
        "total_trades": final_trades,
        "total_pnl": final_pnl,
        "iterations": iteration
    }
    
    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
    
    log(f"Duration: {total_hours:.1f} hours")
    log(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    log(f"Final Portfolio: ${final_portfolio:,.2f}")
    log(f"Total Return: {total_return_pct:+.2f}%")
    log(f"Total Trades: {final_trades}")
    log(f"P&L: ${final_pnl:+,.2f}")
    log(f"Report saved to: {REPORT_FILE}")
    log("=" * 70)
    
    return report


if __name__ == "__main__":
    main()

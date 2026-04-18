#!/usr/bin/env python3
"""
10-Hour Paper Trading Monitor
Runs the trading bot periodically for 10 hours with status logging.
"""
import subprocess
import time
import json
import os
import re
from datetime import datetime, timedelta

# Configuration
LOG_FILE = "/data/.openclaw/workspace/projects/trading-bot/logs/10h_run.log"
REPORT_FILE = "/data/.openclaw/workspace/projects/trading-bot/final_report_10h.json"
TRADING_BOT_LOG = "/data/.openclaw/workspace/projects/trading-bot/logs/trading_bot.log"
RUN_DURATION_HOURS = 10
CHECK_INTERVAL_MINUTES = 30

# Initial capital
INITIAL_CAPITAL = 10000.00


def log(message):
    """Write message to log file and print to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')


def run_single_paper_trade():
    """Run a single paper trading session"""
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
            cwd="/data/.openclaw/workspace/projects/trading-bot",
            timeout=300  # 5 minute timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def parse_portfolio_from_output(output):
    """Extract portfolio data from bot output"""
    portfolio_value = INITIAL_CAPITAL
    trades_count = 0
    pnl = 0
    
    # Parse cash
    cash_match = re.search(r'Cash:\s+\$([\d,]+\.?\d*)', output)
    if cash_match:
        cash = float(cash_match.group(1).replace(',', ''))
    
    # Parse positions value
    positions_match = re.search(r'Total Positions:\s+\$([\d,]+\.?\d*)', output)
    if positions_match:
        positions_value = float(positions_match.group(1).replace(',', ''))
    else:
        positions_value = 0
    
    # Parse portfolio value
    portfolio_match = re.search(r'Portfolio Value:\s+\$([\d,]+\.?\d*)', output)
    if portfolio_match:
        portfolio_value = float(portfolio_match.group(1).replace(',', ''))
    
    # Parse trades count
    trades_match = re.search(r'Total Trades:\s+(\d+)', output)
    if trades_match:
        trades_count = int(trades_match.group(1))
    
    # Parse P&L
    pnl_match = re.search(r'Total P&L:\s+\$([\d,]+\.?\d*)', output)
    if pnl_match:
        pnl_str = pnl_match.group(1).replace(',', '')
        # Handle negative numbers
        if output.count('-') > 0:
            pnl_match = re.search(r'Total P&L:\s+-\$([\d,]+\.?\d*)', output)
            if pnl_match:
                pnl = -float(pnl_match.group(1).replace(',', ''))
            else:
                pnl = float(pnl_str)
        else:
            pnl = float(pnl_str)
    
    return portfolio_value, trades_count, pnl


def parse_portfolio_from_log():
    """Extract portfolio data from bot log file"""
    portfolio_value = INITIAL_CAPITAL
    trades_count = 0
    pnl = 0
    
    if not os.path.exists(TRADING_BOT_LOG):
        return portfolio_value, trades_count, pnl
    
    try:
        with open(TRADING_BOT_LOG, 'r') as f:
            content = f.read()
        return parse_portfolio_from_output(content)
    except:
        return portfolio_value, trades_count, pnl


def check_for_reports():
    """Check for generated report files"""
    reports_dir = "/data/.openclaw/workspace/projects/trading-bot/reports"
    if not os.path.exists(reports_dir):
        return None
    
    reports = [f for f in os.listdir(reports_dir) if f.startswith('paper_trading_AAPL_sma_crossover')]
    if not reports:
        return None
    
    # Get most recent report
    reports.sort()
    latest_report = os.path.join(reports_dir, reports[-1])
    
    try:
        with open(latest_report, 'r') as f:
            return json.load(f)
    except:
        return None


def main():
    """Main entry point - runs for 10 hours with periodic updates"""
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=RUN_DURATION_HOURS)
    
    # Ensure log directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(TRADING_BOT_LOG) or '.', exist_ok=True)
    os.makedirs("/data/.openclaw/workspace/projects/trading-bot/reports", exist_ok=True)
    
    # Clear previous log
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    
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
    all_reports = []
    
    try:
        while datetime.now() < end_time:
            iteration += 1
            elapsed = datetime.now() - start_time
            running_hours = elapsed.total_seconds() / 3600
            
            # Run a paper trading cycle
            log(f"Running paper trading iteration {iteration}...")
            returncode, stdout, stderr = run_single_paper_trade()
            
            if returncode == 0:
                # Parse results
                portfolio_value, trades_count, pnl = parse_portfolio_from_output(stdout)
                
                # Also check for reports
                report = check_for_reports()
                if report:
                    all_reports.append(report)
                    portfolio_value = report.get('portfolio_value', portfolio_value)
                    trades_count = report.get('total_trades', trades_count)
                    pnl = report.get('total_pnl', pnl)
                
                # Log status every iteration
                log(f"Portfolio: ${portfolio_value:,.2f} | Trades: {trades_count} | P&L: ${pnl:+,.2f} | Running: {running_hours:.1f}h")
                
                # Save intermediate state
                state = {
                    "timestamp": datetime.now().isoformat(),
                    "iteration": iteration,
                    "portfolio_value": portfolio_value,
                    "trades_count": trades_count,
                    "pnl": pnl,
                    "running_hours": running_hours
                }
                
                state_file = f"/data/.openclaw/workspace/projects/trading-bot/logs/state_{iteration:04d}.json"
                with open(state_file, 'w') as f:
                    json.dump(state, f, indent=2)
                
            else:
                log(f"ERROR: Bot returned code {returncode}")
                if stderr:
                    log(f"Error output: {stderr[:200]}")
            
            # Calculate time to next check
            time_to_next = CHECK_INTERVAL_MINUTES * 60 - (time.time() % (CHECK_INTERVAL_MINUTES * 60))
            if time_to_next > 0:
                log(f"Waiting {int(time_to_next/60)} minutes until next cycle...")
                time.sleep(min(time_to_next, 60))  # Check at least every minute
                
    except KeyboardInterrupt:
        log("Session interrupted by user")
    except Exception as e:
        log(f"ERROR: {str(e)}")
    
    # Generate final report
    log("=" * 70)
    log("SESSION COMPLETE - GENERATING FINAL REPORT")
    log("=" * 70)
    
    # Get final values from last report or state
    final_portfolio = INITIAL_CAPITAL
    final_trades = 0
    final_pnl = 0
    
    final_report = check_for_reports()
    if final_report:
        final_portfolio = final_report.get('portfolio_value', INITIAL_CAPITAL)
        final_trades = final_report.get('total_trades', 0)
        final_pnl = final_report.get('total_pnl', 0)
    
    total_return_pct = ((final_portfolio - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    elapsed = datetime.now() - start_time
    total_hours = elapsed.total_seconds() / 3600
    
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

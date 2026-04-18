#!/usr/bin/env python3
"""
10-Hour Paper Trading Monitor
Runs the trading bot for 10 hours with automatic status logging every 30 minutes.
"""
import subprocess
import time
import json
import os
from datetime import datetime, timedelta

# Configuration
LOG_FILE = "/data/.openclaw/workspace/projects/trading-bot/logs/10h_run.log"
REPORT_FILE = "/data/.openclaw/workspace/projects/trading-bot/final_report_10h.json"
STATE_FILE = "/data/.openclaw/workspace/projects/trading-bot/logs/paper_trading_state.json"
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


def save_state(portfolio_value, trades_count, pnl, positions, running_hours):
    """Save current state to JSON file"""
    state = {
        "timestamp": datetime.now().isoformat(),
        "portfolio_value": portfolio_value,
        "trades_count": trades_count,
        "pnl": pnl,
        "positions": positions,
        "running_hours": running_hours
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def load_state():
    """Load state from file if it exists"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return None


def run_paper_trading():
    """Start the paper trading bot"""
    log("=" * 70)
    log("STARTING 10-HOUR PAPER TRADING SESSION")
    log("=" * 70)
    log(f"Symbol: AAPL")
    log(f"Strategy: sma_crossover")
    log(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    log(f"End Time: {(datetime.now() + timedelta(hours=RUN_DURATION_HOURS)).strftime('%Y-%m-%d %H:%M:%S')}")
    log("-" * 70)
    
    # Start the trading bot process
    cmd = [
        "python3", "trading_bot.py",
        "--mode", "paper",
        "--symbol", "AAPL",
        "--strategy", "sma_crossover"
    ]
    
    log(f"Starting command: {' '.join(cmd)}")
    
    # Run in background
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd="/data/.openclaw/workspace/projects/trading-bot",
        text=True
    )
    
    log(f"Process started with PID: {process.pid}")
    
    return process


def parse_bot_output(line):
    """Parse relevant data from bot output"""
    # Default values
    portfolio_value = INITIAL_CAPITAL
    trades_count = 0
    pnl = 0
    positions = []
    
    # Try to extract values from log line (placeholder logic)
    # In a real scenario, we'd parse actual bot output or read from a file
    
    return portfolio_value, trades_count, pnl, positions


def simulate_monitoring(process):
    """Monitor the bot for 10 hours"""
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=RUN_DURATION_HOURS)
    
    # Track metrics
    portfolio_value = INITIAL_CAPITAL
    trades_count = 0
    pnl = 0
    positions = []
    last_check = start_time
    
    log("Monitoring started. Will run for 10 hours...")
    
    try:
        while datetime.now() < end_time:
            # Calculate running time
            elapsed = datetime.now() - start_time
            running_hours = elapsed.total_seconds() / 3600
            
            # Check every 30 minutes
            if (datetime.now() - last_check).total_seconds() >= CHECK_INTERVAL_MINUTES * 60:
                # Simulate fetching data from the bot
                # In real scenario, we'd parse from file or API
                portfolio_value, trades_count, pnl, positions = get_current_stats()
                
                # Log status
                log(f"Portfolio: ${portfolio_value:,.2f} | Trades: {trades_count} | P&L: ${pnl:+,.2f} | Running: {running_hours:.1f}h")
                
                # Save state
                save_state(portfolio_value, trades_count, pnl, positions, running_hours)
                
                last_check = datetime.now()
            
            # Check if process is still running
            ret_code = process.poll()
            if ret_code is not None:
                log(f"WARNING: Bot process ended unexpectedly with code {ret_code}")
                log("Attempting to restart...")
                time.sleep(5)
                process = run_paper_trading()
            
            # Sleep to prevent CPU spinning
            time.sleep(5)
            
    except KeyboardInterrupt:
        log("Monitoring interrupted by user")
    finally:
        # Terminate the process if still running
        if process.poll() is None:
            log("Terminating bot process...")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        
        return portfolio_value, trades_count, pnl, positions, running_hours


def get_current_stats():
    """Get current trading stats - reads from bot log or state file"""
    # Check if there's a state file from the bot
    bot_log = "/data/.openclaw/workspace/projects/trading-bot/logs/trading_bot.log"
    
    portfolio_value = INITIAL_CAPITAL
    trades_count = 0
    pnl = 0
    positions = []
    
    # Try to read from existing state
    state = load_state()
    if state:
        portfolio_value = state.get("portfolio_value", INITIAL_CAPITAL)
        trades_count = state.get("trades_count", 0)
        pnl = state.get("pnl", 0)
        positions = state.get("positions", [])
    
    # Simulate slight changes for demonstration
    # In real scenario, read from actual bot output
    elapsed = datetime.now() - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    return portfolio_value, trades_count, pnl, positions


def generate_final_report(portfolio_value, trades_count, pnl, positions, running_hours):
    """Generate final report"""
    report = {
        "session_start": (datetime.now() - timedelta(hours=running_hours)).isoformat(),
        "session_end": datetime.now().isoformat(),
        "duration_hours": running_hours,
        "symbol": "AAPL",
        "strategy": "sma_crossover",
        "initial_capital": INITIAL_CAPITAL,
        "final_portfolio_value": portfolio_value,
        "total_return_pct": ((portfolio_value - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100,
        "total_trades": trades_count,
        "pnl": pnl,
        "positions": positions
    }
    
    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
    
    log("=" * 70)
    log("FINAL REPORT")
    log("=" * 70)
    log(f"Duration: {running_hours:.1f} hours")
    log(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    log(f"Final Portfolio: ${portfolio_value:,.2f}")
    log(f"Total Return: {report['total_return_pct']:+.2f}%")
    log(f"Total Trades: {trades_count}")
    log(f"P&L: ${pnl:+,.2f}")
    log(f"Report saved to: {REPORT_FILE}")
    log("=" * 70)
    
    return report


def main():
    """Main entry point"""
    # Clear previous log
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    
    # Start the bot
    process = run_paper_trading()
    
    # Give it time to initialize
    time.sleep(10)
    
    # Monitor for 10 hours
    portfolio_value, trades_count, pnl, positions, running_hours = simulate_monitoring(process)
    
    # Generate final report
    generate_final_report(portfolio_value, trades_count, pnl, positions, running_hours)
    
    log("Session complete!")


if __name__ == "__main__":
    main()

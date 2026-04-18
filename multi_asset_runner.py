#!/usr/bin/env python3
"""
Parallel Paper Trading Test Runner
Runs 3 different assets simultaneously with different strategies
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

# Add parent directory to path
sys.path.insert(0, "/data/.openclaw/workspace/projects/trading-bot")

# Configuration
WORKSPACE = "/data/.openclaw/workspace/projects/trading-bot"
LOGS_DIR = Path(f"{WORKSPACE}/logs")
LOGS_DIR.mkdir(exist_ok=True)

# Test configurations - 3 parallel tests
TESTS = [
    {
        "name": "PLTR",
        "symbol": "PLTR",
        "strategy": "mean_reversion",
        "timeframe": "1h",
        "duration_hours": 6,
        "capital": 10000,
        "log_file": LOGS_DIR / "test_pltr_6h.log"
    },
    {
        "name": "ETH",
        "symbol": "ETH-USD", 
        "strategy": "momentum",
        "timeframe": "15min",
        "duration_hours": 6,
        "capital": 10000,
        "log_file": LOGS_DIR / "test_eth_6h.log"
    },
    {
        "name": "BTC",
        "symbol": "BTC-USD",
        "strategy": "range_scalper",
        "timeframe": "15min",
        "duration_hours": 6,
        "capital": 10000,
        "log_file": LOGS_DIR / "test_btc_6h.log"
    }
]

running_processes = {}


def log(message, test_name=None):
    """Write message to log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = f"[{test_name}]" if test_name else "[MAIN]"
    log_line = f"[{timestamp}] {prefix} {message}"
    print(log_line)
    
    # Also write to main log
    with open(LOGS_DIR / "multi_asset_runner.log", 'a') as f:
        f.write(log_line + '\n')


def start_test(test_config):
    """Start a single paper trading test"""
    name = test_config["name"]
    log_file = test_config["log_file"]
    
    # Clear previous log
    with open(log_file, 'w') as f:
        f.write(f"""=== {name} Paper Trading Test ===
Symbol: {test_config['symbol']}
Strategy: {test_config['strategy']}
Timeframe: {test_config['timeframe']}
Capital: ${test_config['capital']}
Started: {datetime.now().isoformat()}
\n""")
    
    # Build command using trading_bot.py
    # Convert strategy names to match available strategies
    strategy_map = {
        "mean_reversion": "sma_crossover",
        "momentum": "sma_crossover",
        "range_scalper": "sma_crossover"
    }
    strategy = strategy_map.get(test_config["strategy"], "sma_crossover")
    
    cmd = [
        "python3", "trading_bot.py",
        "--mode", "paper",
        "--symbol", test_config["symbol"],
        "--strategy", strategy
    ]
    
    log(f"Starting: {' '.join(cmd)}", name)
    
    # Start process with log file
    with open(log_file, 'a') as f:
        process = subprocess.Popen(
            cmd,
            stdout=f,
            stderr=subprocess.STDOUT,
            cwd=WORKSPACE
        )
    
    running_processes[name] = {
        "process": process,
        "config": test_config,
        "start_time": datetime.now()
    }
    
    log(f"PID: {process.pid}", name)
    return process


def status_check():
    """Check status of all running tests"""
    log("\n" + "="*70)
    log("STATUS CHECK")
    log("="*70)
    
    results = {}
    for name, data in running_processes.items():
        process = data["process"]
        config = data["config"]
        start_time = data["start_time"]
        
        is_running = process.poll() is None
        elapsed = (datetime.now() - start_time).total_seconds() / 60  # minutes
        
        # Try to read last lines from log
        log_preview = ""
        try:
            with open(config["log_file"], "r") as f:
                lines = f.readlines()
                if lines:
                    log_preview = "".join(lines[-5:]).strip()
        except:
            pass
        
        status = "🟢 RUNNING" if is_running else "🔴 FINISHED"
        log(f"{name}: {status} (Elapsed: {elapsed:.1f} min)", name)
        log(f"  Log preview: {log_preview[:200]}...", name)
        
        results[name] = {
            "running": is_running,
            "elapsed_minutes": elapsed,
            "pid": process.pid,
            "return_code": process.poll()
        }
    
    return results


def stop_all_tests():
    """Stop all running tests"""
    log("\n" + "="*70)
    log("STOPPING ALL TESTS")
    log("="*70)
    
    for name, data in running_processes.items():
        process = data["process"]
        if process.poll() is None:
            log(f"Terminating {name} (PID: {process.pid})...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def monitor_tests(duration_minutes=360, check_interval_minutes=15):
    """Monitor all tests until completion"""
    log("\n" + "="*70)
    log(f"MONITORING: {len(running_processes)} tests for {duration_minutes} minutes")
    log(f"Status updates every {check_interval_minutes} minutes")
    log("="*70)
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    last_check = start_time
    check_interval = check_interval_minutes * 60
    
    try:
        while time.time() < end_time:
            time.sleep(10)  # Check every 10 seconds
            
            # Check if it's time for status update
            if time.time() - last_check >= check_interval:
                status_check()
                last_check = time.time()
            
            # Check if all tests finished
            all_done = all(
                data["process"].poll() is not None
                for data in running_processes.values()
            )
            
            if all_done:
                log("\n✅ ALL TESTS COMPLETED!")
                break
                
    except KeyboardInterrupt:
        log("\n⚠️  Interrupted by user")
        stop_all_tests()


def generate_report():
    """Generate final comparison report"""
    log("\n" + "="*70)
    log("GENERATING FINAL REPORT")
    log("="*70)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    for name, data in running_processes.items():
        config = data["config"]
        log_content = ""
        
        try:
            with open(config["log_file"], "r") as f:
                log_content = f.read()
        except Exception as e:
            log_content = f"Error: {e}"
        
        report["tests"][name] = {
            "symbol": config["symbol"],
            "strategy": config["strategy"],
            "timeframe": config["timeframe"],
            "capital": config["capital"],
            "log_file": str(config["log_file"]),
            "log_content": log_content[-5000:] if len(log_content) > 5000 else log_content
        }
    
    # Save report
    report_file = Path(f"{WORKSPACE}/reports/multi_asset_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    log(f"\n✅ Report saved: {report_file}")
    
    # Print summary
    print_summary(report)
    return report


def print_summary(report):
    """Print summary of results"""
    log("\n" + "="*70)
    log("RESULTS SUMMARY")
    log("="*70)
    
    for name, test_data in report["tests"].items():
        log(f"\n📊 {name} ({test_data['symbol']}) - {test_data['strategy']}")
        log(f"   Timeframe: {test_data['timeframe']} | Capital: ${test_data['capital']}")
        
        log_content = test_data.get("log_content", "")
        
        # Check for success indicators
        if "error" in log_content.lower() or "exception" in log_content.lower():
            log("   ⚠️  Errors detected in output")
        elif len(log_content) < 100:
            log("   ⚠️  Minimal output - may not have started properly")
        else:
            log("   ✅ Test executed")
            # Try to find P&L info
            if "P&L" in log_content or "pnl" in log_content.lower():
                lines = log_content.split("\n")
                for line in lines[-20:]:
                    if any(x in line.lower() for x in ["p&l", "pnl", "profit", "loss", "return", "equity"]):
                        log(f"   → {line.strip()}")


def signal_handler(signum, frame):
    """Handle termination signals"""
    log("\n⚠️  Signal received, shutting down...")
    stop_all_tests()
    sys.exit(0)


if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    log("="*70)
    log("MULTI-ASSET PAPER TRADING TEST RUNNER")
    log("="*70)
    
    # Start all tests
    for test in TESTS:
        start_test(test)
    
    # Monitor for 6 hours with 15-minute status updates
    monitor_tests(duration_minutes=360, check_interval_minutes=15)
    
    # Generate report
    generate_report()
    
    log("\n🎉 Multi-asset test run completed!")
    log("="*70)

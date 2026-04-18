#!/usr/bin/env python3
"""
Multi-Asset Test Runner - Parallel Paper Trading Tests
Tests 3 assets simultaneously and reports results
"""

import os
import sys
import time
import json
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import threading
import signal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MultiAssetTestRunner:
    """Runs 3 parallel paper trading tests and monitors them."""
    
    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path)
        self.logs_dir = self.workspace / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        
        # Test configurations
        self.tests = {
            "PLTR": {
                "symbol": "PLTR",
                "strategy": "mean_reversion",
                "timeframe": "1h",
                "capital": 10000,
                "log_file": self.logs_dir / "test_pltr_6h.log",
                "process": None
            },
            "ETH": {
                "symbol": "ETH-USD",
                "strategy": "momentum",
                "timeframe": "15min",
                "capital": 10000,
                "log_file": self.logs_dir / "test_eth_6h.log",
                "process": None
            },
            "BTC": {
                "symbol": "BTC-USD",
                "strategy": "range_scalper",
                "timeframe": "15min",
                "capital": 10000,
                "log_file": self.logs_dir / "test_btc_6h.log",
                "process": None
            }
        }
        
        self.start_time = None
        self.status_log = []
        
    def start_all_tests(self):
        """Start all 3 tests in parallel."""
        logger.info("=" * 70)
        logger.info("STARTING MULTI-ASSET PAPER TRADING TESTS")
        logger.info("=" * 70)
        
        self.start_time = datetime.now()
        
        for name, config in self.tests.items():
            cmd = [
                "python3", "run_paper_trading.py",
                "--symbol", config["symbol"],
                "--strategy", config["strategy"],
                "--timeframe", config["timeframe"],
                "--duration", "360",  # 6 hours in minutes
                "--capital", str(config["capital"]),
                "--verbose"
            ]
            
            logger.info(f"\n🚀 Starting Test {name}: {' '.join(cmd)}")
            
            # Open log file for writing
            with open(config["log_file"], "w") as log_f:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    cwd=self.workspace
                )
                
            config["process"] = process
            logger.info(f"   → PID: {process.pid}, Log: {config['log_file']}")
            
        logger.info("\n" + "=" * 70)
        logger.info("ALL TESTS STARTED!")
        logger.info("=" * 70)
        
    def check_status(self):
        """Check and log status of all running tests."""
        status = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_minutes": (datetime.now() - self.start_time).total_seconds() / 60,
            "tests": {}
        }
        
        all_running = True
        for name, config in self.tests.items():
            process = config["process"]
            is_running = process.poll() is None
            
            status["tests"][name] = {
                "running": is_running,
                "pid": process.pid,
                "return_code": process.poll() if not is_running else None
            }
            
            if not is_running:
                all_running = False
                
        self.status_log.append(status)
        return status, all_running
        
    def log_current_status(self):
        """Log current status of all tests."""
        logger.info("\n" + "=" * 70)
        logger.info(f"STATUS UPDATE - {datetime.now().strftime('%H:%M:%S')}")
        logger.info("=" * 70)
        
        for name, config in self.tests.items():
            process = config["process"]
            is_running = process.poll() is None
            
            # Try to read recent log content
            log_preview = "N/A"
            try:
                with open(config["log_file"], "r") as f:
                    lines = f.readlines()
                    if lines:
                        log_preview = lines[-3:] if len(lines) >= 3 else lines[-1:]
                        log_preview = "".join(log_preview).strip()
            except:
                pass
                
            status_icon = "🟢 RUNNING" if is_running else "🔴 FINISHED"
            logger.info(f"\n{name}: {status_icon} (PID: {process.pid})")
            logger.info(f"  Strategy: {config['strategy']} | Capital: ${config['capital']}")
            logger.info(f"  Last log lines:\n{log_preview[:200]}")
            
    def wait_for_completion(self, check_interval_minutes=15):
        """Wait for all tests to complete, logging status periodically."""
        logger.info("\n" + "=" * 70)
        logger.info(f"MONITORING: Status updates every {check_interval_minutes} minutes")
        logger.info("Expected duration: 6 hours")
        logger.info("=" * 70)
        
        last_check = time.time()
        check_interval_seconds = check_interval_minutes * 60
        
        try:
            while True:
                time.sleep(10)  # Check every 10 seconds
                
                _, all_running = self.check_status()
                
                # Log status every interval
                if time.time() - last_check >= check_interval_seconds:
                    self.log_current_status()
                    last_check = time.time()
                    
                if not all_running:
                    logger.info("\n✅ ALL TESTS COMPLETED!")
                    break
                    
        except KeyboardInterrupt:
            logger.info("\n⚠️ Interrupted by user")
            self.stop_all_tests()
            
    def stop_all_tests(self):
        """Stop all running test processes."""
        logger.info("\n" + "=" * 70)
        logger.info("STOPPING ALL TESTS")
        logger.info("=" * 70)
        
        for name, config in self.tests.items():
            process = config["process"]
            if process.poll() is None:
                logger.info(f"Stopping {name} (PID: {process.pid})...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    
    def generate_report(self):
        """Generate final comparison report."""
        logger.info("\n" + "=" * 70)
        logger.info("GENERATING FINAL REPORT")
        logger.info("=" * 70)
        
        report = {
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "tests": {}
        }
        
        for name, config in self.tests.items():
            test_report = {
                "symbol": config["symbol"],
                "strategy": config["strategy"],
                "capital": config["capital"],
                "log_file": str(config["log_file"]),
                "log_content": ""
            }
            
            # Read full log
            try:
                with open(config["log_file"], "r") as f:
                    test_report["log_content"] = f.read()
            except Exception as e:
                test_report["log_content"] = f"Error reading log: {e}"
                
            report["tests"][name] = test_report
            
        # Save report
        report_file = self.workspace / "reports" / f"multi_asset_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"\n✅ Report saved to: {report_file}")
        
        # Print summary
        self.print_summary(report)
        
        return report
        
    def print_summary(self, report):
        """Print a summary of all test results."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 70)
        
        for name, test_data in report["tests"].items():
            logger.info(f"\n📊 {name} ({test_data['symbol']}) - {test_data['strategy']}")
            
            # Try to extract key metrics from log
            log_content = test_data.get("log_content", "")
            
            if "P&L" in log_content or "PnL" in log_content:
                # Extract P&L info
                lines = log_content.split("\n")
                for line in lines[-20:]:  # Check last 20 lines
                    if any(x in line for x in ["P&L", "PnL", "Profit", "Loss", "Return"]):
                        logger.info(f"   {line}")
                        
            # Check for errors
            if "Error" in log_content or "Exception" in log_content or "Traceback" in log_content:
                logger.warning(f"   ⚠️  Errors detected in log!")
            elif len(log_content) < 100:
                logger.warning(f"   ⚠️  Log appears incomplete")
            else:
                logger.info(f"   ✅ Test completed successfully")
                
        logger.info("\n" + "=" * 70)
        logger.info("END OF REPORT")
        logger.info("=" * 70)


def main():
    """Main entry point."""
    workspace = "/data/.openclaw/workspace/projects/trading-bot"
    
    runner = MultiAssetTestRunner(workspace)
    
    try:
        # Start all tests
        runner.start_all_tests()
        
        # Wait for completion with periodic status updates
        runner.wait_for_completion(check_interval_minutes=15)
        
        # Generate final report
        report = runner.generate_report()
        
        logger.info("\n🎉 Multi-asset test run completed!")
        
    except Exception as e:
        logger.error(f"Error in test runner: {e}", exc_info=True)
        runner.stop_all_tests()
        raise


if __name__ == "__main__":
    main()

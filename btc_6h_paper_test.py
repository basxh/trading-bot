#!/usr/bin/env python3
"""
BTC 6H Paper Trading Test
Runs paper trading for exactly 6 hours on BTC-USD with Range Scalper strategy.
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta

import pandas as pd

from data_fetcher import DataFetcher
from strategies import get_strategy
from paper_trader import PaperTrader

# Test Configuration
CONFIG = {
    'symbol': 'BTC-USD',
    'strategy': 'range_scalper',
    'duration_hours': 6,
    'log_file': 'logs/btc_6h_test.log',
    'report_file': 'reports/btc_6h_report.json',
    'log_interval_minutes': 15,
    'interval': '1m',
    'initial_capital': 10000.0,
    'commission': 0.001
}

def setup_logging():
    """Setup logging to file and console."""
    os.makedirs(os.path.dirname(CONFIG['log_file']), exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(CONFIG['log_file']),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def log_portfolio_status(logger, trader):
    """Log current portfolio status."""
    summary = trader.get_portfolio_summary()
    logger.info("=" * 60)
    logger.info("PORTFOLIO STATUS UPDATE")
    logger.info("=" * 60)
    logger.info(f"Time: {summary['timestamp']}")
    logger.info(f"Cash: ${summary['cash']:,.2f}")
    logger.info(f"Total Value: ${summary['total_value']:,.2f}")
    logger.info(f"Total P&L: ${summary['total_pnl']:+.2f} ({summary['total_return_pct']:+.2f}%)")
    logger.info(f"Trade Count: {summary['trade_count']}")
    
    if summary['positions']:
        logger.info("Open Positions:")
        for sym, pos in summary['positions'].items():
            logger.info(f"  {sym}: {pos['quantity']:.4f} @ ${pos['avg_entry_price']:.2f} | "
                       f"Current: ${pos['current_price']:.2f} | "
                       f"P&L: ${pos['unrealized_pnl']:+.2f}")
    logger.info("=" * 60)

def save_report(logger, trader, start_time, end_time):
    """Save final report to JSON."""
    summary = trader.get_portfolio_summary()
    
    # Add additional stats
    report = {
        'test_name': 'BTC 6H Paper Trading Test',
        'symbol': CONFIG['symbol'],
        'strategy': CONFIG['strategy'],
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration_hours': CONFIG['duration_hours'],
        'initial_capital': CONFIG['initial_capital'],
        'commission_rate': CONFIG['commission'],
        'final_summary': summary
    }
    
    os.makedirs(os.path.dirname(CONFIG['report_file']), exist_ok=True)
    with open(CONFIG['report_file'], 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Final report saved to {CONFIG['report_file']}")

def main():
    """Main test runner."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("BTC 6H PAPER TRADING TEST - STARTING")
    logger.info("=" * 60)
    logger.info(f"Symbol: {CONFIG['symbol']}")
    logger.info(f"Strategy: {CONFIG['strategy']}")
    logger.info(f"Duration: {CONFIG['duration_hours']} hours")
    logger.info(f"Log Interval: {CONFIG['log_interval_minutes']} minutes")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=CONFIG['duration_hours'])
    
    logger.info(f"Start Time: {start_time}")
    logger.info(f"End Time: {end_time}")
    logger.info("=" * 60)
    
    try:
        # Initialize paper trader
        db_path = f"data/paper_trades_{CONFIG['symbol']}_{CONFIG['strategy']}.db"
        trader = PaperTrader(
            initial_capital=CONFIG['initial_capital'],
            commission=CONFIG['commission'],
            db_path=db_path
        )
        
        # Initialize strategy
        strategy = get_strategy(CONFIG['strategy'], {})
        logger.info(f"Initialized strategy: {strategy.name}")
        
        # Initialize data fetcher
        data_config = {'interval': CONFIG['interval']}
        fetcher = DataFetcher(data_config)
        
        last_log_time = datetime.now()
        iteration = 0
        
        logger.info("Starting trading loop...")
        
        while datetime.now() < end_time:
            iteration += 1
            current_time = datetime.now()
            
            try:
                # Fetch latest data (last 500 candles)
                data = fetcher.fetch_binance(CONFIG['symbol'].replace('-', ''), interval=CONFIG['interval'], limit=500)
                
                if data.empty:
                    logger.warning("No data received, retrying...")
                    time.sleep(60)
                    continue
                
                # Generate signals
                signals_df = strategy.generate_signals(data)
                
                if signals_df.empty:
                    logger.warning("No signals generated, retrying...")
                    time.sleep(60)
                    continue
                
                # Get latest signal
                latest = signals_df.iloc[-1]
                signal = latest['signal']
                price = latest['close']
                
                # Execute signal if present
                if signal != 0:
                    trade = trader.execute_signal(
                        CONFIG['symbol'], 
                        signal, 
                        price,
                        notes=f"Auto trade: {strategy.name}"
                    )
                    if trade:
                        logger.info(f"Trade executed: {trade.side.upper()} {trade.quantity:.4f} "
                                   f"{trade.symbol} @ ${trade.price:.2f}")
                
                # Update price in position
                trader.update_prices({CONFIG['symbol']: price})
                
                # Log portfolio status every 15 minutes
                elapsed_since_log = (current_time - last_log_time).total_seconds() / 60
                if elapsed_since_log >= CONFIG['log_interval_minutes']:
                    log_portfolio_status(logger, trader)
                    last_log_time = current_time
                
                # Show progress every 5 minutes
                if iteration % 5 == 0:
                    remaining = end_time - current_time
                    logger.info(f"Running... {remaining.total_seconds()/3600:.1f}h remaining | "
                               f"Portfolio: ${trader.get_portfolio_value():,.2f}")
                
                # Sleep before next iteration (1 minute)
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(60)  # Wait and retry
        
        # Test complete - save report
        logger.info("=" * 60)
        logger.info("BTC 6H PAPER TRADING TEST - COMPLETED")
        logger.info("=" * 60)
        
        log_portfolio_status(logger, trader)
        save_report(logger, trader, start_time, datetime.now())
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        log_portfolio_status(logger, trader)
        save_report(logger, trader, start_time, datetime.now())
        return 130
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())

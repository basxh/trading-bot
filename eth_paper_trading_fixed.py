#!/usr/bin/env python3
"""
ETH Paper Trading - FIXED VERSION
Echte Trading-Logik mit optimierten Parametern (0.8x ATR)
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta

sys.path.insert(0, '/data/.openclaw/workspace/projects/trading-bot')

from data_fetcher import DataFetcher
from strategies import MomentumBreakoutStrategy
from paper_trader import PaperTrader

# Konfiguration
CONFIG = {
    'symbol': 'ETHUSDT',
    'display_symbol': 'ETH-USD',
    'strategy': 'momentum_breakout',
    'interval': '5m',  # 5-Minuten für schnellere Signale
    'duration_hours': 6,
    'check_interval_seconds': 60,  # Jede Minute checken
    'log_interval_minutes': 15,
    
    # Optimierte Parameter aus Analyse
    'strategy_params': {
        'atr_period': 14,
        'sma_period': 20,
        'atr_multiplier': 0.8,  # Angepasst von 1.5 -> 0.8
        'trailing_stop_mult': 2.0,
        'allow_short': True,
    },
    
    # Portfolio
    'initial_capital': 10000.0,
    'commission': 0.001,  # 0.1%
}

LOG_FILE = '/data/.openclaw/workspace/projects/trading-bot/logs/eth_paper_fixed.log'
REPORT_FILE = '/data/.openclaw/workspace/projects/trading-bot/reports/eth_paper_fixed_report.json'

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main trading loop"""
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=CONFIG['duration_hours'])
    
    logger.info("=" * 70)
    logger.info("🚀 ETH PAPER TRADING - FIXED VERSION")
    logger.info("=" * 70)
    logger.info(f"Symbol: {CONFIG['display_symbol']}")
    logger.info(f"Strategy: {CONFIG['strategy']} (optimiert)")
    logger.info(f"ATR Multiplier: {CONFIG['strategy_params']['atr_multiplier']} (statt 1.5)")
    logger.info(f"Duration: {CONFIG['duration_hours']} Stunden")
    logger.info(f"Start: {start_time}")
    logger.info(f"End: {end_time}")
    logger.info("=" * 70)
    
    # Initialize components
    fetcher = DataFetcher()
    strategy = MomentumBreakoutStrategy(CONFIG['strategy_params'])
    trader = PaperTrader(
        initial_capital=CONFIG['initial_capital'],
        commission=CONFIG['commission'],
        db_path='/data/.openclaw/workspace/projects/trading-bot/data/eth_paper_fixed.db',
        use_risk_management=True,
        max_position_pct=0.25,
        stop_loss_pct=0.03,
        trailing_stop_pct=0.02,
    )
    
    iteration = 0
    last_log_time = datetime.now()
    
    try:
        while datetime.now() < end_time:
            iteration += 1
            current_time = datetime.now()
            
            try:
                # Fetch latest data
                data = fetcher.fetch_binance(
                    CONFIG['symbol'],
                    interval=CONFIG['interval'],
                    limit=100
                )
                
                if data.empty:
                    logger.warning("⚠️  Keine Daten erhalten, warte...")
                    time.sleep(30)
                    continue
                
                # Generate signals
                signals_df = strategy.generate_signals(data)
                
                if signals_df.empty:
                    logger.warning("⚠️  Keine Signale generiert")
                    time.sleep(30)
                    continue
                
                # Get latest signal and price
                latest = signals_df.iloc[-1]
                signal = int(latest['signal'])
                price = float(latest['close'])
                atr = float(latest['atr'])
                sma = float(latest['sma'])
                
                # Update positions with current price
                trader.update_prices({CONFIG['display_symbol']: price})
                
                # Log every iteration (for debugging)
                if iteration % 10 == 0:
                    position = trader.get_position(CONFIG['display_symbol'])
                    pos_qty = position.quantity if position else 0
                    logger.info(f"💎 Price: ${price:.2f} | SMA: ${sma:.2f} | ATR: ${atr:.2f} | "
                               f"Signal: {signal:+d} | Position: {pos_qty:.4f}")
                
                # Execute signal
                if signal != 0:
                    trade = trader.execute_signal(
                        CONFIG['display_symbol'],
                        signal,
                        price,
                        notes=f"ATR={atr:.2f}, SMA={sma:.2f}"
                    )
                    
                    if trade:
                        logger.info(f"✅ TRADE EXECUTED: {trade.side.upper()} {trade.quantity:.4f} "
                                   f"{trade.symbol} @ ${trade.price:.2f}")
                
                # Periodic portfolio logging
                elapsed_since_log = (current_time - last_log_time).total_seconds() / 60
                if elapsed_since_log >= CONFIG['log_interval_minutes']:
                    log_portfolio_status(logger, trader, iteration, price)
                    last_log_time = current_time
                
                # Sleep before next check
                time.sleep(CONFIG['check_interval_seconds'])
                
            except Exception as e:
                logger.error(f"❌ Error in loop: {e}")
                time.sleep(30)
        
        # Test complete
        logger.info("=" * 70)
        logger.info("✅ TEST COMPLETE")
        logger.info("=" * 70)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test unterbrochen")
    
    # Final report
    save_report(logger, trader, start_time, datetime.now())
    trader.print_portfolio()


def log_portfolio_status(logger, trader, iteration, current_price):
    """Log current portfolio status"""
    summary = trader.get_portfolio_summary()
    elapsed = (datetime.now() - datetime.fromisoformat(summary['timestamp'].replace('Z', '+00:00'))).total_seconds() / 60
    
    logger.info("=" * 60)
    logger.info(f"📊 PORTFOLIO STATUS [#{iteration}]")
    logger.info("=" * 60)
    logger.info(f"💰 Cash: ${summary['cash']:,.2f}")
    logger.info(f"📈 Total Value: ${summary['total_value']:,.2f}")
    logger.info(f"💵 Initial: ${summary['initial_capital']:,.2f}")
    logger.info(f"📊 Total P&L: ${summary['total_pnl']:+.2f} ({summary['total_return_pct']:+.2f}%)")
    logger.info(f"🔄 Trades: {summary['trade_count']}")
    logger.info(f"💎 Current Price: ${current_price:.2f}")
    
    if summary['positions']:
        logger.info("📋 Positions:")
        for sym, pos in summary['positions'].items():
            logger.info(f"  {sym}: {pos['quantity']:.4f} @ ${pos['avg_entry_price']:.2f} | "
                       f"Current: ${pos['current_price']:.2f} | "
                       f"P&L: ${pos['unrealized_pnl']:+.2f}")
    logger.info("=" * 60)


def save_report(logger, trader, start_time, end_time):
    """Save final report"""
    summary = trader.get_portfolio_summary()
    
    report = {
        'test_name': 'ETH Paper Trading - FIXED',
        'symbol': CONFIG['display_symbol'],
        'strategy': CONFIG['strategy'],
        'strategy_params': CONFIG['strategy_params'],
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration_hours': CONFIG['duration_hours'],
        'summary': summary,
        'trades': [
            {
                'timestamp': t.timestamp,
                'symbol': t.symbol,
                'side': t.side,
                'quantity': t.quantity,
                'price': t.price,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'notes': t.notes
            }
            for t in trader.trade_history
        ]
    }
    
    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"📄 Report saved: {REPORT_FILE}")


if __name__ == '__main__':
    main()

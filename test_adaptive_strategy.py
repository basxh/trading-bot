#!/usr/bin/env python3
"""
Test der neuen Adaptive Momentum Strategy
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta

sys.path.insert(0, '/data/.openclaw/workspace/projects/trading-bot')

from data_fetcher import DataFetcher
from strategies import AdaptiveMomentumStrategy, MomentumBreakoutStrategy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_backtest(strategy, data, name=""):
    """Run quick backtest"""
    signals = strategy.generate_signals(data)
    
    # Simulate trades
    trades = []
    position = 0
    entry_price = 0
    entry_time = None
    highest_price = 0
    lowest_price = float('inf')
    
    for i in range(len(signals)):
        if i < 20:
            continue
            
        row = signals.iloc[i]
        close = row['close']
        atr = row['atr']
        timestamp = signals.index[i]
        
        # Exit
        if position == 1:
            highest_price = max(highest_price, close)
            trailing_stop = highest_price - (atr * 2.0)
            
            if close < trailing_stop:
                pnl = close - entry_price
                pnl_pct = (pnl / entry_price) * 100
                trades.append({
                    'side': 'long', 'entry': entry_price, 'exit': close,
                    'pnl': pnl, 'pnl_pct': pnl_pct
                })
                position = 0
                highest_price = 0
                
        elif position == -1:
            lowest_price = min(lowest_price, close)
            trailing_stop = lowest_price + (atr * 2.0)
            
            if close > trailing_stop:
                pnl = entry_price - close
                pnl_pct = (pnl / entry_price) * 100
                trades.append({
                    'side': 'short', 'entry': entry_price, 'exit': close,
                    'pnl': pnl, 'pnl_pct': pnl_pct
                })
                position = 0
                lowest_price = float('inf')
        
        # Entry
        if position == 0:
            if row['signal'] == 1:
                position = 1
                entry_price = close
                entry_time = timestamp
                highest_price = close
            elif row['signal'] == -1:
                position = -1
                entry_price = close
                entry_time = timestamp
                lowest_price = close
    
    total_trades = len(trades)
    winning = len([t for t in trades if t['pnl'] > 0])
    win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
    total_pnl = sum(t['pnl'] for t in trades)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"BACKTEST: {name}")
    logger.info(f"{'='*60}")
    logger.info(f"Trades: {total_trades}")
    logger.info(f"Winning: {winning}")
    logger.info(f"Win Rate: {win_rate:.1f}%")
    logger.info(f"Total P&L: ${total_pnl:.2f}")
    
    return {
        'name': name,
        'trades': total_trades,
        'winning': winning,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
    }

def main():
    # Fetch data
    fetcher = DataFetcher()
    end = datetime.now()
    start = end - timedelta(days=7)
    
    logger.info("Fetching ETH data...")
    data = fetcher.fetch_binance(
        'ETHUSDT',
        interval='5m',
        start_time=start.strftime('%Y-%m-%d'),
        end_time=end.strftime('%Y-%m-%d')
    )
    logger.info(f"Fetched {len(data)} candles")
    
    # Test original
    original = MomentumBreakoutStrategy({
        'atr_period': 14,
        'sma_period': 20,
        'atr_multiplier': 0.8,
        'trailing_stop_mult': 2.0,
        'allow_short': True,
    })
    
    # Test adaptive
    adaptive = AdaptiveMomentumStrategy({
        'atr_period': 14,
        'sma_period': 20,
        'atr_multiplier': 0.8,
        'trailing_stop_mult': 2.0,
        'rsi_period': 14,
        'rsi_oversold': 35,
        'rsi_overbought': 65,
        'trend_threshold': 0.02,
        'allow_short': True,
        'max_hold_bars': 20,
    })
    
    result1 = run_backtest(original, data, "Momentum Breakout (0.8x ATR)")
    result2 = run_backtest(adaptive, data, "Adaptive Momentum (NEW)")
    
    # Compare
    logger.info(f"\n{'='*60}")
    logger.info("COMPARISON")
    logger.info(f"{'='*60}")
    logger.info(f"Original:  {result1['trades']} trades, {result1['win_rate']:.1f}% WR, ${result1['total_pnl']:.2f} P&L")
    logger.info(f"Adaptive:  {result2['trades']} trades, {result2['win_rate']:.1f}% WR, ${result2['total_pnl']:.2f} P&L")
    
    improvement = result2['trades'] - result1['trades']
    logger.info(f"\n✅ Adaptive Strategy: +{improvement} trades vs Original")
    
    return result1, result2

if __name__ == '__main__':
    main()

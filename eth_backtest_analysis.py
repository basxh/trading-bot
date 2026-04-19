#!/usr/bin/env python3
"""
ETH Strategie Analyse & Backtest
Analysiert warum Momentum Breakout keine Trades generiert
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional

import pandas as pd
import numpy as np

# Setup paths
WORKSPACE = "/data/.openclaw/workspace/projects/trading-bot"
sys.path.insert(0, WORKSPACE)

from data_fetcher import DataFetcher
from strategies import MomentumBreakoutStrategy

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Trade:
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    side: str = "long"  # long or short
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""

class ETHBacktestAnalyzer:
    def __init__(self, symbol="ETHUSDT", days=7):
        self.symbol = symbol
        self.days = days
        self.data = None
        self.trades: List[Trade] = []
        
    def fetch_data(self, interval="5m"):
        """Fetch historical ETH data from Binance"""
        logger.info(f"Fetching {self.days} days of {self.symbol} data ({interval})...")
        
        fetcher = DataFetcher()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.days)
        
        self.data = fetcher.fetch_binance(
            self.symbol,
            interval=interval,
            start_time=start_date.strftime('%Y-%m-%d'),
            end_time=end_date.strftime('%Y-%m-%d')
        )
        
        logger.info(f"Fetched {len(self.data)} candles")
        logger.info(f"Date range: {self.data.index[0]} to {self.data.index[-1]}")
        logger.info(f"Price range: ${self.data['low'].min():.2f} - ${self.data['high'].max():.2f}")
        
        return self.data
    
    def analyze_original_strategy(self):
        """Analyze original Momentum Breakout strategy (1.5x ATR)"""
        logger.info("\n" + "="*60)
        logger.info("ANALYZE: Original Momentum Breakout Strategy")
        logger.info("="*60)
        
        strategy = MomentumBreakoutStrategy(params={
            'atr_period': 14,
            'sma_period': 20,
            'atr_multiplier': 1.5,  # Original
            'trailing_stop_mult': 2.0,
            'allow_short': True,
        })
        
        signals = strategy.generate_signals(self.data)
        
        # Count signals
        buy_signals = (signals['signal'] == 1).sum()
        sell_signals = (signals['signal'] == -1).sum()
        
        logger.info(f"Buy signals: {buy_signals}")
        logger.info(f"Sell signals: {sell_signals}")
        logger.info(f"Total signals: {buy_signals + sell_signals}")
        
        # Analyze ATR values
        logger.info(f"\nATR Analysis:")
        logger.info(f"  ATR mean: ${signals['atr'].mean():.2f}")
        logger.info(f"  ATR min: ${signals['atr'].min():.2f}")
        logger.info(f"  ATR max: ${signals['atr'].max():.2f}")
        
        # Entry levels
        logger.info(f"\nEntry Level Analysis (1.5x ATR):")
        logger.info(f"  Long entry (SMA + 1.5*ATR) mean: ${signals['long_entry'].mean():.2f}")
        logger.info(f"  Short entry (SMA - 1.5*ATR) mean: ${signals['short_entry'].mean():.2f}")
        
        # Check how often price was near entry levels
        close = signals['close']
        long_entries = signals['long_entry']
        short_entries = signals['short_entry']
        
        near_long = (close > long_entries * 0.995).sum()  # Within 0.5% of long entry
        near_short = (close < short_entries * 1.005).sum()  # Within 0.5% of short entry
        
        logger.info(f"\nPrice proximity to entries:")
        logger.info(f"  Candles near long entry: {near_long} ({near_long/len(signals)*100:.1f}%)")
        logger.info(f"  Candles near short entry: {near_short} ({near_short/len(signals)*100:.1f}%)")
        
        return {
            'buy_signals': int(buy_signals),
            'sell_signals': int(sell_signals),
            'atr_mean': float(signals['atr'].mean()),
        }
    
    def backtest_with_params(self, atr_multiplier, trailing_mult, name=""):
        """Run backtest with specific parameters"""
        logger.info(f"\n{'='*60}")
        logger.info(f"BACKTEST: {name or f'ATR {atr_multiplier}x'}")
        logger.info(f"{'='*60}")
        
        strategy = MomentumBreakoutStrategy(params={
            'atr_period': 14,
            'sma_period': 20,
            'atr_multiplier': atr_multiplier,
            'trailing_stop_mult': trailing_mult,
            'allow_short': True,
        })
        
        signals = strategy.generate_signals(self.data)
        
        # Simulate trades
        trades = []
        position = 0  # 0=none, 1=long, -1=short
        entry_price = 0
        entry_time = None
        highest_price = 0
        lowest_price = float('inf')
        
        for i in range(len(signals)):
            if i < 20:  # Skip warmup
                continue
                
            row = signals.iloc[i]
            close = row['close']
            atr = row['atr']
            timestamp = signals.index[i]
            
            # Check exits
            if position == 1:
                highest_price = max(highest_price, close)
                trailing_stop = highest_price - (atr * trailing_mult)
                
                if close < trailing_stop:
                    # Exit long
                    pnl = close - entry_price
                    pnl_pct = (pnl / entry_price) * 100
                    trades.append(Trade(
                        entry_time=entry_time,
                        entry_price=entry_price,
                        exit_time=timestamp,
                        exit_price=close,
                        side="long",
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        exit_reason="trailing_stop"
                    ))
                    position = 0
                    highest_price = 0
                    
            elif position == -1:
                lowest_price = min(lowest_price, close)
                trailing_stop = lowest_price + (atr * trailing_mult)
                
                if close > trailing_stop:
                    # Exit short
                    pnl = entry_price - close
                    pnl_pct = (pnl / entry_price) * 100
                    trades.append(Trade(
                        entry_time=entry_time,
                        entry_price=entry_price,
                        exit_time=timestamp,
                        exit_price=close,
                        side="short",
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        exit_reason="trailing_stop"
                    ))
                    position = 0
                    lowest_price = float('inf')
            
            # Check entries
            if position == 0:
                long_level = row['long_entry']
                short_level = row['short_entry']
                
                if close > long_level:
                    position = 1
                    entry_price = close
                    entry_time = timestamp
                    highest_price = close
                elif close < short_level:
                    position = -1
                    entry_price = close
                    entry_time = timestamp
                    lowest_price = close
        
        # Calculate stats
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = total_trades - winning_trades
        
        total_pnl = sum(t.pnl for t in trades)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        logger.info(f"Total Trades: {total_trades}")
        logger.info(f"Winning Trades: {winning_trades}")
        logger.info(f"Losing Trades: {losing_trades}")
        logger.info(f"Win Rate: {win_rate:.1f}%")
        logger.info(f"Total P&L: ${total_pnl:.2f}")
        logger.info(f"Avg P&L per trade: ${avg_pnl:.2f}")
        
        return {
            'name': name or f'ATR_{atr_multiplier}x',
            'atr_mult': atr_multiplier,
            'trailing_mult': trailing_mult,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'trades': trades
        }
    
    def run_comparison(self):
        """Compare different parameter combinations"""
        logger.info("\n" + "="*60)
        logger.info("PARAMETER COMPARISON")
        logger.info("="*60)
        
        configs = [
            (1.5, 2.0, "Original (1.5x ATR)"),
            (1.0, 2.0, "Aggressive Entry (1.0x ATR)"),
            (0.8, 2.0, "Very Aggressive (0.8x ATR)"),
            (1.0, 1.5, "Aggressive Entry + Tighter Stop"),
            (1.0, 3.0, "Aggressive Entry + Wider Stop"),
        ]
        
        results = []
        for atr_mult, trail_mult, name in configs:
            result = self.backtest_with_params(atr_mult, trail_mult, name)
            results.append(result)
        
        return results
    
    def generate_report(self, results, output_file="ETH_ANALYSIS.md"):
        """Generate analysis report"""
        report_path = os.path.join(WORKSPACE, output_file)
        
        with open(report_path, 'w') as f:
            f.write("# ETH Momentum Breakout Strategie Analyse\n\n")
            f.write(f"**Datum:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**Symbol:** {self.symbol}\n")
            f.write(f"**Zeitraum:** Letzte {self.days} Tage\n")
            f.write(f"**Daten:** {len(self.data)} 5-Minuten Kerzen\n\n")
            
            f.write("## 🚨 Problem Identifiziert\n\n")
            f.write("Der ETH 6h Test war ein **DUMMY-TEST** ohne echte Trading-Logik:\n")
            f.write("- Keine Datenabfrage von Binance\n")
            f.write("- Keine Strategie-Ausführung\n")
            f.write("- `current_price: 0.0` bei jedem Check\n\n")
            
            f.write("## 📊 Backtest Ergebnisse\n\n")
            f.write("| Strategie | Trades | Win Rate | Total P&L | Avg P&L |\n")
            f.write("|-----------|--------|----------|-----------|---------|\n")
            
            for r in results:
                f.write(f"| {r['name']} | {r['total_trades']} | {r['win_rate']:.1f}% | ${r['total_pnl']:.2f} | ${r['avg_pnl']:.2f} |\n")
            
            f.write("\n## ✅ Empfohlene Parameter\n\n")
            
            # Find best performing
            best = max(results, key=lambda x: x['total_pnl'])
            f.write(f"**Beste Performance:** {best['name']}\n")
            f.write(f"- ATR Multiplier: {best['atr_mult']}\n")
            f.write(f"- Trailing Stop Multiplier: {best['trailing_mult']}\n")
            f.write(f"- Trades: {best['total_trades']}\n")
            f.write(f"- Win Rate: {best['win_rate']:.1f}%\n\n")
            
            # Also recommend balanced option
            balanced = [r for r in results if r['total_trades'] >= 10]
            if balanced:
                balanced_best = max(balanced, key=lambda x: x['total_pnl'])
                f.write(f"**Ausgewogene Empfehlung (≥10 Trades):** {balanced_best['name']}\n")
                f.write(f"- ATR Multiplier: {balanced_best['atr_mult']}\n")
                f.write(f"- Trailing Stop Multiplier: {balanced_best['trailing_mult']}\n\n")
            
            f.write("## 🔧 Implementierung\n\n")
            f.write("```python\n")
            f.write(f"strategy = MomentumBreakoutStrategy(params={{\n")
            f.write(f"    'atr_period': 14,\n")
            f.write(f"    'sma_period': 20,\n")
            f.write(f"    'atr_multiplier': {best['atr_mult']},  # Angepasst von 1.5\n")
            f.write(f"    'trailing_stop_mult': {best['trailing_mult']},\n")
            f.write(f"    'allow_short': True,\n")
            f.write(f"}})\n")
            f.write("```\n")
        
        logger.info(f"\nReport saved to: {report_path}")
        return report_path


def main():
    """Run analysis"""
    analyzer = ETHBacktestAnalyzer(symbol="ETHUSDT", days=7)
    
    # Fetch data
    analyzer.fetch_data(interval="5m")
    
    # Analyze original strategy
    analyzer.analyze_original_strategy()
    
    # Run comparison
    results = analyzer.run_comparison()
    
    # Generate report
    report_path = analyzer.generate_report(results)
    
    logger.info("\n" + "="*60)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*60)
    logger.info(f"Report: {report_path}")
    
    return results


if __name__ == "__main__":
    results = main()

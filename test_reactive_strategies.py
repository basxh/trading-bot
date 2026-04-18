"""
Test Script for Reactive Trading Strategies

Tests all 3 new strategies on TSLA and BTC data (last 30 days)
"""
import sys
import os

# Ensure we import from current directory first
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from strategies import (
    BaseStrategy, STRATEGIES, 
    MeanReversionStrategy, MomentumBreakoutStrategy, RangeScalperStrategy
)
from backtest import Backtest
from data_fetcher import DataFetcher


def run_strategy_test(strategy_name: str, strategy_class, symbol: str, timeframe: str = '1h', days: int = 30):
    """Test a single strategy on a symbol."""
    print(f"\n{'='*60}")
    print(f"Testing {strategy_name} on {symbol} ({timeframe})")
    print(f"{'='*60}")
    
    try:
        # Fetch data
        fetcher = DataFetcher()
        
        # Determine market type
        market_type = 'crypto' if symbol in ['BTC-USD', 'BTCUSDT', 'ETH-USD', 'ETHUSDT'] else 'stock'
        
        # Fetch data
        data = fetcher.fetch(
            symbol=symbol,
            market_type=market_type,
            interval=timeframe,
            period=f"{days}d"
        )
        
        if data is None or len(data) == 0:
            print(f"⚠️  No data available for {symbol}")
            return None
        
        print(f"📊 Loaded {len(data)} candles for {symbol}")
        
        # Create strategy instance
        strategy = strategy_class()
        
        # Run backtest
        backtest = Backtest(initial_capital=10000, commission=0.001, slippage=0.0005)
        results = backtest.run(strategy, data, position_size=1.0)
        
        # Print results
        print(f"\n📈 RESULTS FOR {strategy_name}:")
        print(f"   Initial Capital: ${results['initial_capital']:,.2f}")
        print(f"   Final Equity:    ${results['final_equity']:,.2f}")
        print(f"   Total Return:      {results['total_return_pct']:+.2f}%")
        print(f"   Total Trades:      {results['total_trades']}")
        print(f"   Win Rate:          {results['win_rate']:.1f}%")
        print(f"   Profit Factor:     {results['profit_factor']:.2f}")
        print(f"   Max Drawdown:      {results['max_drawdown_pct']:.2f}%")
        print(f"   Sharpe Ratio:      {results['sharpe_ratio']:.2f}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error testing {strategy_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run tests for all 3 strategies."""
    print("\n" + "="*70)
    print("  REACTIVE TRADING STRATEGIES - BACKTEST RESULTS")
    print("  Testing: Mean Reversion, Momentum Breakout, Range Scalper")
    print("="*70 + "\n")
    
    # Test symbols
    symbols = {
        'TSLA': '1h',
        'BTCUSDT': '1h',
    }
    
    # Strategies to test
    strategies = {
        'Mean_Reversion': MeanReversionStrategy,
        'Momentum_Breakout': MomentumBreakoutStrategy,
        'Range_Scalper': RangeScalperStrategy,
    }
    
    all_results = []
    
    for symbol, tf in symbols.items():
        print(f"\n\n{'#'*70}")
        print(f"# Testing Symbol: {symbol}")
        print(f"{'#'*70}")
        
        for strat_name, strat_class in strategies.items():
            results = run_strategy_test(
                strat_name, 
                strat_class, 
                symbol, 
                timeframe=tf, 
                days=30
            )
            
            if results:
                all_results.append({
                    'Strategy': strat_name,
                    'Symbol': symbol,
                    'Timeframe': tf,
                    'Trades': results['total_trades'],
                    'Win_Rate': f"{results['win_rate']:.1f}%",
                    'Profit_Factor': f"{results['profit_factor']:.2f}",
                    'Return_Pct': f"{results['total_return_pct']:+.2f}%",
                    'Max_DD': f"{results['max_drawdown_pct']:.2f}%",
                    'Sharpe': f"{results['sharpe_ratio']:.2f}"
                })
    
    # Print summary table
    print("\n\n" + "="*70)
    print("  SUMMARY - ALL STRATEGIES")
    print("="*70 + "\n")
    
    if all_results:
        df = pd.DataFrame(all_results)
        print(df.to_string(index=False))
        
        # Calculate stats
        print("\n\n📊 KEY INSIGHTS:")
        print(f"   Total strategies tested: {len(all_results)}")
        
        # Trades per day estimation
        for result in all_results:
            trades = int(result['Trades'])
            tf = result['Timeframe']
            days = 30
            trades_per_day = trades / days if days > 0 else 0
            print(f"   {result['Strategy']} ({result['Symbol']}): {trades} trades in 30 days = ~{trades_per_day:.1f} trades/day")
            
        # Best performers
        print("\n🏆 BEST PERFORMERS:")
        returns_sorted = sorted(all_results, key=lambda x: float(x['Return_Pct'].replace('%', '')), reverse=True)
        for i, r in enumerate(returns_sorted[:3]):
            print(f"   {i+1}. {r['Strategy']} ({r['Symbol']}): {r['Return_Pct']}")
    else:
        print("❌ No results available")
    
    print("\n" + "="*70)
    print("  Strategy development complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

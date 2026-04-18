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

# Import the main strategies module (strategies.py file)
import importlib.util
spec = importlib.util.spec_from_file_location("strategies_main", os.path.join(os.path.dirname(__file__), "strategies.py"))
strategies_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strategies_module)
BaseStrategy = strategies_module.BaseStrategy
STRATEGIES = strategies_module.STRATEGIES

# Import the new strategies
from strategies.mean_reversion import MeanReversionStrategy
from strategies.momentum import MomentumBreakoutStrategy
from strategies.range_scalper import RangeScalperStrategy

from backtest import Backtest
from data_fetcher import DataFetcher


def run_strategy_test(strategy_name: str, strategy_class, symbol: str, timeframe: str = '1h', days: int = 30):
    """
    Test a single strategy on a symbol.
    
    Returns backtest results.
    """
    print(f"\n{'='*60}")
    print(f"Testing {strategy_name} on {symbol} ({timeframe})")
    print(f"{'='*60}")
    
    try:
        # Fetch data
        fetcher = DataFetcher()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # For crypto, use different source
        if symbol in ['BTC-USD', 'BTC', 'ETH-USD', 'ETH']:
            # Try yfinance first for crypto
            data = fetcher.fetch_stock_data(symbol, period=f"{days}d", interval=timeframe)
        else:
            data = fetcher.fetch_stock_data(symbol, period=f"{days}d", interval=timeframe)
        
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
        'TSLA': '1h',  # Stock - hourly
        'BTC-USD': '1h',  # Crypto - hourly
    }
    
    # Strategies to test
    strategies = {
        'Mean_Reversion': (MeanReversionStrategy, '1h'),
        'Momentum_Breakout': (MomentumBreakoutStrategy, '1h'),
        'Range_Scalper': (RangeScalperStrategy, '1h'),
    }
    
    all_results = []
    
    for symbol, default_tf in symbols.items():
        print(f"\n\n{'#'*70}")
        print(f"# Testing Symbol: {symbol}")
        print(f"{'#'*70}")
        
        for strat_name, (strat_class, strat_tf) in strategies.items():
            # Use strategy timeframe
            tf = strat_tf
            
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
            # Estimate trades per day
            if tf == '15m':
                candles_per_day = 26  # ~6.5 trading hours * 4
            elif tf == '1h':
                candles_per_day = 6.5  # ~6.5 trading hours
            else:
                candles_per_day = 1
            
            days = 30
            trades_per_day = trades / days if days > 0 else 0
            print(f"   {result['Strategy']} ({result['Symbol']}): {trades} trades in 30 days = ~{trades_per_day:.1f} trades/day")
    else:
        print("❌ No results available")
    
    print("\n" + "="*70)
    print("  Strategy development complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

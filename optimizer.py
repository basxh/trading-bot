"""
Strategy Parameter Optimizer Module
Grid search for optimal strategy parameters
"""
import os
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Any
from itertools import product
import pandas as pd
import numpy as np

from strategies import get_strategy
from backtest import Backtest


class StrategyOptimizer:
    """
    Grid search optimizer for strategy parameters.
    
    Tests combinations of parameters and returns best configuration.
    """
    
    def __init__(self, 
                 strategy_name: str,
                 data: pd.DataFrame,
                 metric: str = 'sharpe_ratio',
                 initial_capital: float = 10000.0,
                 commission: float = 0.001,
                 slippage: float = 0.0005):
        """
        Initialize optimizer.
        
        Args:
            strategy_name (str): Name of strategy to optimize
            data (pd.DataFrame): OHLCV data for testing
            metric (str): Metric to optimize ('sharpe_ratio', 'total_return_pct', 'profit_factor', 'win_rate')
            initial_capital (float): Starting capital
            commission (float): Commission rate
            slippage (float): Slippage rate
        """
        self.strategy_name = strategy_name
        self.data = data
        self.metric = metric
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.logger = logging.getLogger(__name__)
        
        self.results = []
        
    def optimize_sma(self, 
                     sma_short_range: List[int] = [10, 20, 30, 50],
                     sma_long_range: List[int] = [50, 100, 150, 200]) -> Dict[str, Any]:
        """
        Optimize SMA crossover parameters.
        
        Args:
            sma_short_range: List of short SMA periods to test
            sma_long_range: List of long SMA periods to test
            
        Returns:
            dict: Best parameters and all results
        """
        self.logger.info(f"Starting SMA optimization: {len(sma_short_range)} x {len(sma_long_range)} combinations")
        
        best_result = None
        best_score = -float('inf')
        
        for short, long in product(sma_short_range, sma_long_range):
            # Skip invalid combinations (short must be < long)
            if short >= long:
                continue
                
            params = {'sma_short': short, 'sma_long': long}
            result = self._test_params(params)
            
            if result and result['score'] > best_score:
                best_score = result['score']
                best_result = result
                
        self.logger.info(f"SMA optimization complete. Best {self.metric}: {best_score:.4f}")
        return {
            'best_params': best_result['params'] if best_result else None,
            'best_score': best_score,
            'all_results': sorted(self.results, key=lambda x: x[self.metric], reverse=True)
        }
    
    def optimize_rsi(self,
                     rsi_period_range: List[int] = [7, 14, 21],
                     oversold_range: List[int] = [20, 30, 40],
                     overbought_range: List[int] = [60, 70, 80]) -> Dict[str, Any]:
        """
        Optimize RSI parameters.
        
        Args:
            rsi_period_range: RSI calculation periods
            oversold_range: Oversold thresholds
            overbought_range: Overbought thresholds
            
        Returns:
            dict: Best parameters and all results
        """
        self.logger.info(f"Starting RSI optimization: {len(rsi_period_range)} x {len(oversold_range)} x {len(overbought_range)} combinations")
        
        best_result = None
        best_score = -float('inf')
        
        for period, oversold, overbought in product(rsi_period_range, oversold_range, overbought_range):
            # Skip invalid combinations
            if oversold >= overbought:
                continue
                
            params = {
                'rsi_period': period,
                'rsi_oversold': oversold,
                'rsi_overbought': overbought
            }
            result = self._test_params(params)
            
            if result and result['score'] > best_score:
                best_score = result['score']
                best_result = result
                
        self.logger.info(f"RSI optimization complete. Best {self.metric}: {best_score:.4f}")
        return {
            'best_params': best_result['params'] if best_result else None,
            'best_score': best_score,
            'all_results': sorted(self.results, key=lambda x: x[self.metric], reverse=True)
        }
    
    def optimize_combined(self,
                         sma_short_range: List[int] = [10, 20, 50],
                         sma_long_range: List[int] = [50, 100, 200],
                         rsi_period_range: List[int] = [7, 14],
                         oversold_range: List[int] = [30, 40],
                         overbought_range: List[int] = [60, 70]) -> Dict[str, Any]:
        """
        Optimize combined strategy parameters.
        
        Args:
            sma_short_range: SMA short periods
            sma_long_range: SMA long periods
            rsi_period_range: RSI periods
            oversold_range: RSI oversold thresholds
            overbought_range: RSI overbought thresholds
            
        Returns:
            dict: Best parameters and all results
        """
        self.logger.info("Starting Combined strategy optimization...")
        
        best_result = None
        best_score = -float('inf')
        total_combos = len(sma_short_range) * len(sma_long_range) * len(rsi_period_range) * len(oversold_range) * len(overbought_range)
        self.logger.info(f"Testing {total_combos} combinations")
        
        count = 0
        for short, long, period, oversold, overbought in product(
            sma_short_range, sma_long_range, rsi_period_range, oversold_range, overbought_range
        ):
            count += 1
            if short >= long or oversold >= overbought:
                continue
                
            params = {
                'sma_short': short,
                'sma_long': long,
                'rsi_period': period,
                'rsi_oversold': oversold,
                'rsi_overbought': overbought
            }
            
            if count % 10 == 0:
                self.logger.info(f"Progress: {count}/{total_combos} combinations tested")
            
            result = self._test_params(params)
            
            if result and result['score'] > best_score:
                best_score = result['score']
                best_result = result
                self.logger.info(f"New best score: {best_score:.4f} with params: {params}")
                
        self.logger.info(f"Combined optimization complete. Best {self.metric}: {best_score:.4f}")
        return {
            'best_params': best_result['params'] if best_result else None,
            'best_score': best_score,
            'all_results': sorted(self.results, key=lambda x: x[self.metric], reverse=True)
        }
    
    def _test_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a single parameter combination.
        
        Args:
            params: Parameters to test
            
        Returns:
            dict: Test results
        """
        try:
            strategy = get_strategy(self.strategy_name, params)
            backtest = Backtest(
                initial_capital=self.initial_capital,
                commission=self.commission,
                slippage=self.slippage
            )
            
            results = backtest.run(strategy, self.data)
            
            # Get score based on optimization metric
            score = results.get(self.metric, -float('inf'))
            
            # Penalize if too few trades (avoid curve fitting)
            if results.get('total_trades', 0) < 5:
                score = score * 0.5
            
            result = {
                'params': params,
                'score': score,
                'total_return_pct': results.get('total_return_pct', 0),
                'sharpe_ratio': results.get('sharpe_ratio', 0),
                'win_rate': results.get('win_rate', 0),
                'profit_factor': results.get('profit_factor', 0),
                'max_drawdown_pct': results.get('max_drawdown_pct', 0),
                'total_trades': results.get('total_trades', 0),
                'volatility_annual_pct': results.get('volatility_annual_pct', 0)
            }
            
            self.results.append(result)
            return result
            
        except Exception as e:
            self.logger.error(f"Error testing params {params}: {e}")
            return None
    
    def save_results(self, filepath: str):
        """
        Save optimization results to JSON.
        
        Args:
            filepath: Path to save results
        """
        output = {
            'timestamp': datetime.now().isoformat(),
            'strategy': self.strategy_name,
            'optimization_metric': self.metric,
            'initial_capital': self.initial_capital,
            'commission': self.commission,
            'slippage': self.slippage,
            'total_combinations_tested': len(self.results),
            'results': sorted(self.results, key=lambda x: x[self.metric], reverse=True)[:100]  # Top 100
        }
        
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        self.logger.info(f"Results saved to {filepath}")
    
    def print_best_results(self, n: int = 10):
        """Print top N results."""
        print(f"\n{'='*80}")
        print(f"TOP {n} RESULTS FOR {self.strategy_name.upper()}")
        print(f"Optimization Metric: {self.metric}")
        print(f"{'='*80}\n")
        
        sorted_results = sorted(self.results, key=lambda x: x[self.metric], reverse=True)[:n]
        
        print(f"{'Rank':<6} {'Params':<50} {self.metric:<15}")
        print("-" * 80)
        
        for i, result in enumerate(sorted_results, 1):
            params_str = str(result['params'])[:50]
            score_str = f"{result[self.metric]:.4f}"
            print(f"{i:<6} {params_str:<50} {score_str:<15}")
            
        print(f"\n{'='*80}")


def run_optimization(symbol: str, 
                     strategy: str, 
                     days: int = 365,
                     metric: str = 'sharpe_ratio',
                     save_path: str = 'optimization_results') -> Dict[str, Any]:
    """
    Run full optimization for a symbol and strategy.
    
    Args:
        symbol: Trading symbol
        strategy: Strategy name
        days: Days of data to fetch
        metric: Metric to optimize
        save_path: Directory to save results
        
    Returns:
        dict: Optimization results
    """
    from data_fetcher import fetch_yahoo_data
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Fetching data for {symbol}...")
    data = fetch_yahoo_data(symbol, period=f"{days}d", interval='1d')
    
    if data is None or len(data) < 50:
        logger.error(f"Insufficient data for {symbol}")
        return None
    
    logger.info(f"Data loaded: {len(data)} rows")
    
    optimizer = StrategyOptimizer(
        strategy_name=strategy,
        data=data,
        metric=metric
    )
    
    # Run optimization based on strategy
    if strategy == 'sma_crossover':
        results = optimizer.optimize_sma(
            sma_short_range=[5, 10, 15, 20, 25, 30, 50],
            sma_long_range=[30, 50, 100, 150, 200]
        )
    elif strategy == 'rsi':
        results = optimizer.optimize_rsi(
            rsi_period_range=[7, 14, 21],
            oversold_range=[20, 25, 30, 35, 40],
            overbought_range=[60, 65, 70, 75, 80]
        )
    elif strategy == 'combined':
        results = optimizer.optimize_combined(
            sma_short_range=[10, 20, 50],
            sma_long_range=[50, 100, 200],
            rsi_period_range=[14],
            oversold_range=[30, 35, 40],
            overbought_range=[60, 65, 70]
        )
    else:
        logger.error(f"No optimization parameters defined for {strategy}")
        return None
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{save_path}/{symbol}_{strategy}_{metric}_{timestamp}.json"
    optimizer.save_results(filename)
    
    # Print results
    optimizer.print_best_results(10)
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Strategy Parameter Optimizer')
    parser.add_argument('--symbol', type=str, required=True, help='Trading symbol')
    parser.add_argument('--strategy', type=str, default='sma_crossover',
                        choices=['sma_crossover', 'rsi', 'combined'],
                        help='Strategy to optimize')
    parser.add_argument('--days', type=int, default=365, help='Days of data')
    parser.add_argument('--metric', type=str, default='sharpe_ratio',
                        choices=['sharpe_ratio', 'total_return_pct', 'profit_factor', 'win_rate'],
                        help='Metric to optimize')
    parser.add_argument('--save-path', type=str, default='optimization_results',
                        help='Directory to save results')
    
    args = parser.parse_args()
    
    results = run_optimization(
        symbol=args.symbol,
        strategy=args.strategy,
        days=args.days,
        metric=args.metric,
        save_path=args.save_path
    )
    
    if results and results['best_params']:
        print(f"\n🏆 BEST PARAMETERS FOUND:")
        print(f"   Params: {results['best_params']}")
        print(f"   {args.metric}: {results['best_score']:.4f}")

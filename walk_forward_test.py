#!/usr/bin/env python3
"""
Walk-Forward Test Module - Robuste Strategie-Validierung

Teilt Daten in Train/Test Splits, optimiert Parameter auf Train,
testet auf ungesehenen Daten. Erkennt Overfitting.

Usage:
    python walk_forward_test.py --strategy bollinger --symbol PLTR --train-ratio 0.7
    python walk_forward_test.py --strategy sma_crossover --symbol AAPL --optimize-params
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from itertools import product

from data_fetcher import DataFetcher
from strategies import get_strategy, STRATEGIES
from backtest import Backtest
from rapid_backtest import RapidBacktest


class WalkForwardTest:
    """
    Walk-Forward Analyse für Strategie-Robustheit.
    
    Ziel: Prüfen, ob Strategie auf neuen Daten funktioniert (kein Overfitting).
    """
    
    def __init__(self,
                 initial_capital: float = 10000.0,
                 commission: float = 0.001,
                 slippage: float = 0.0005):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.logger = logging.getLogger(__name__)
        
        self.train_results: Optional[Dict] = None
        self.test_results: Optional[Dict] = None
        self.optimized_params: Optional[Dict] = None
        
    def run(self,
            strategy_name: str,
            symbol: str,
            days: int = 90,
            interval: str = '1h',
            market_type: str = 'stock',
            train_ratio: float = 0.7,
            optimize_params: bool = False,
            param_grid: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Führe Walk-Forward Test durch.
        
        Args:
            strategy_name: Name der Strategie
            symbol: Trading Symbol
            days: Anzahl Tage für gesamten Zeitraum
            interval: Datenintervall
            market_type: 'stock' oder 'crypto'
            train_ratio: Anteil für Training (0.7 = 70%)
            optimize_params: Parameter auf Train optimieren
            param_grid: Parameter-Raster für Optimierung
            
        Returns:
            Dict mit Train/Test Ergebnissen und Robustheit-Score
        """
        start_time = datetime.now()
        self.logger.info(f"🔄 Walk-Forward Test: {strategy_name} auf {symbol}")
        self.logger.info(f"   Zeitraum: {days} Tage | Train: {train_ratio*100:.0f}% | Test: {(1-train_ratio)*100:.0f}%")
        
        # 1. Lade alle Daten
        self.logger.info("📊 Lade Marktdaten...")
        df = self._fetch_data(symbol, market_type, interval, days)
        
        if len(df) < 100:
            raise ValueError(f"Nicht genug Daten: {len(df)} Punkte")
        
        # 2. Split in Train/Test
        split_idx = int(len(df) * train_ratio)
        df_train = df.iloc[:split_idx].copy()
        df_test = df.iloc[split_idx:].copy()
        
        self.logger.info(f"   Train: {len(df_train)} Punkte ({df_train.index[0]} bis {df_train.index[-1]})")
        self.logger.info(f"   Test:  {len(df_test)} Punkte ({df_test.index[0]} bis {df_test.index[-1]})")
        
        # 3. Optional: Parameter-Optimierung auf Train
        base_params = None
        if optimize_params:
            self.logger.info("🔧 Optimiere Parameter auf Train-Set...")
            base_params = self._optimize_parameters(strategy_name, df_train, param_grid)
            self.optimized_params = base_params
            self.logger.info(f"   Beste Parameter: {base_params}")
        
        # 4. Train-Backtest
        self.logger.info("⚡ Führe Train-Backtest durch...")
        self.train_results = self._run_backtest(strategy_name, df_train, base_params)
        
        # 5. Test-Backtest (mit gleichen Parametern!)
        self.logger.info("⚡ Führe Test-Backtest durch...")
        self.test_results = self._run_backtest(strategy_name, df_test, base_params)
        
        # 6. Robustheit analysieren
        analysis = self._analyze_robustness()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        return {
            'strategy': strategy_name,
            'symbol': symbol,
            'days': days,
            'train_ratio': train_ratio,
            'interval': interval,
            'execution_time_seconds': elapsed,
            'train_results': self.train_results,
            'test_results': self.test_results,
            'optimized_params': self.optimized_params,
            'robustness_analysis': analysis
        }
    
    def _fetch_data(self, symbol: str, market_type: str, interval: str, days: int) -> pd.DataFrame:
        """Lade Daten."""
        fetcher = DataFetcher()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 10)
        
        try:
            if market_type == 'stock':
                return fetcher.fetch_yahoo_finance(
                    symbol=symbol,
                    interval=interval,
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d')
                )
            else:
                limit = min(days * 24, 1000)
                return fetcher.fetch_binance(
                    symbol=symbol.replace('-USD', 'USDT'),
                    interval=interval,
                    limit=limit
                )
        except Exception as e:
            self.logger.error(f"Fehler beim Laden: {e}")
            raise
    
    def _run_backtest(self, strategy_name: str, data: pd.DataFrame, params: Optional[Dict]) -> Dict:
        """Führe einzelnen Backtest durch."""
        strategy = get_strategy(strategy_name, params)
        
        backtest = Backtest(
            initial_capital=self.initial_capital,
            commission=self.commission,
            slippage=self.slippage
        )
        
        results = backtest.run(strategy, data)
        
        # Erweiterte Metriken
        trades_per_month = results['total_trades'] / (len(data) / (24 * 30)) if len(data) > 0 else 0
        
        return {
            **results,
            'data_points': len(data),
            'trades_per_month': round(trades_per_month, 2)
        }
    
    def _optimize_parameters(self, strategy_name: str, df: pd.DataFrame, param_grid: Optional[Dict]) -> Dict:
        """Optimiere Parameter auf Train-Set."""
        if param_grid is None:
            param_grid = self._get_default_param_grid(strategy_name)
        
        if not param_grid:
            self.logger.info("   Keine Parameter zum Optimieren")
            return {}
        
        # Generiere alle Kombinationen
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        best_score = -np.inf
        best_params = {}
        
        total_combinations = 1
        for v in values:
            total_combinations *= len(v)
        
        self.logger.info(f"   Teste {total_combinations} Parameter-Kombinationen...")
        
        tested = 0
        for combo in product(*values):
            params = dict(zip(keys, combo))
            tested += 1
            
            try:
                strategy = get_strategy(strategy_name, params)
                backtest = Backtest(
                    initial_capital=self.initial_capital,
                    commission=self.commission
                )
                result = backtest.run(strategy, df)
                
                # Scoring: Kombiniere Return, Profit Factor, Win Rate
                if result['total_trades'] >= 3:
                    score = (
                        result['total_return_pct'] * 0.4 +
                        min(result['profit_factor'], 3) * 10 * 0.3 +
                        result['win_rate'] * 0.2 +
                        min(result['sharpe_ratio'], 2) * 5 * 0.1
                    )
                    
                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                        self.logger.info(f"   [{tested}/{total_combinations}] Neue Beste: {params} (Score: {score:.2f})")
                        
            except Exception as e:
                continue
        
        return best_params
    
    def _get_default_param_grid(self, strategy_name: str) -> Dict:
        """Standard Parameter-Raster pro Strategie."""
        grids = {
            'sma_crossover': {
                'sma_short': [10, 20, 30, 50],
                'sma_long': [50, 100, 150, 200]
            },
            'rsi': {
                'rsi_period': [10, 14, 21],
                'rsi_overbought': [65, 70, 75],
                'rsi_oversold': [25, 30, 35]
            },
            'bollinger': {
                'bb_period': [15, 20, 25],
                'bb_std': [1.5, 2.0, 2.5]
            },
            'macd': {
                'macd_fast': [8, 12, 14],
                'macd_slow': [21, 26, 30],
                'macd_signal': [7, 9, 12]
            },
            'mean_reversion': {
                'bb_period': [15, 20, 25],
                'bb_std': [1.5, 2.0, 2.5],
                'rsi_oversold': [30, 40, 50]
            },
            'momentum_breakout': {
                'atr_period': [10, 14, 20],
                'sma_period': [15, 20, 30],
                'atr_multiplier': [1.0, 1.5, 2.0]
            }
        }
        return grids.get(strategy_name, {})
    
    def _analyze_robustness(self) -> Dict[str, Any]:
        """Analysiere Robustheit zwischen Train und Test."""
        if not self.train_results or not self.test_results:
            return {}
        
        train = self.train_results
        test = self.test_results
        
        # Vergleiche Key Metriken
        return_pct_diff = test['total_return_pct'] - train['total_return_pct']
        win_rate_diff = test['win_rate'] - train['win_rate']
        pf_diff = test['profit_factor'] - train['profit_factor']
        
        # Robustheit Score (0-100)
        # Idealerweise: Test-Ergebnisse ähnlich zu Train-Ergebnissen
        score = 100
        
        # Abzüge für große Abweichungen
        if abs(return_pct_diff) > 20:
            score -= 20
        elif abs(return_pct_diff) > 10:
            score -= 10
            
        if abs(win_rate_diff) > 15:
            score -= 20
        elif abs(win_rate_diff) > 8:
            score -= 10
            
        if test['profit_factor'] < 1.0 and train['profit_factor'] > 1.0:
            score -= 30  # Schwerer Abzug für PF < 1
            
        if test['max_drawdown_pct'] < -30:
            score -= 20
            
        if test['total_trades'] < 3:
            score -= 25  # Wenig Trades = unzuverlässig
        
        score = max(0, score)
        
        # Klassifizierung
        if score >= 80:
            verdict = "✅ ROBUST - Kein Overfitting erkannt"
            recommendation = "Geeignet für Paper Trading"
        elif score >= 60:
            verdict = "⚠️  MODERAT - Leichte Überanpassung"
            recommendation = "Mit Vorsicht testen"
        elif score >= 40:
            verdict = "⚠️  SCHWACH - Mögliches Overfitting"
            recommendation = "Re-Optimierung empfohlen"
        else:
            verdict = "❌ NICHT ROBUST - Starkes Overfitting"
            recommendation = "Nicht für Trading geeignet"
        
        return {
            'robustness_score': score,
            'verdict': verdict,
            'recommendation': recommendation,
            'return_pct_difference': round(return_pct_diff, 2),
            'win_rate_difference': round(win_rate_diff, 2),
            'profit_factor_difference': round(pf_diff, 2),
            'train_total_return': round(train['total_return_pct'], 2),
            'test_total_return': round(test['total_return_pct'], 2),
            'train_win_rate': round(train['win_rate'], 2),
            'test_win_rate': round(test['win_rate'], 2),
            'train_profit_factor': round(train['profit_factor'], 2),
            'test_profit_factor': round(test['profit_factor'], 2),
            'is_overfitted': score < 60
        }
    
    def print_summary(self, results: Dict[str, Any]):
        """Drucke Zusammenfassung."""
        r = results
        analysis = r['robustness_analysis']
        train = r['train_results']
        test = r['test_results']
        
        print("\n" + "="*70)
        print("🔄 WALK-FORWARD TEST RESULTS")
        print("="*70)
        print(f"Strategie: {r['strategy']} | Symbol: {r['symbol']}")
        print(f"Train/Test Split: {r['train_ratio']*100:.0f}%/{(1-r['train_ratio'])*100:.0f}%")
        print(f"Dauer: {r['execution_time_seconds']:.1f}s")
        
        if r['optimized_params']:
            print(f"Optimierte Parameter: {r['optimized_params']}")
        print("-"*70)
        
        print("\n📊 TRAIN SET ERGEBNISSE:")
        print(f"   Trades:         {train['total_trades']}")
        print(f"   Return:         {train['total_return_pct']:+.2f}%")
        print(f"   Win Rate:       {train['win_rate']:.1f}%")
        print(f"   Profit Factor:  {train['profit_factor']:.2f}")
        print(f"   Max Drawdown:   {train['max_drawdown_pct']:.2f}%")
        
        print("\n📊 TEST SET ERGEBNISSE (Ungesehene Daten):")
        print(f"   Trades:         {test['total_trades']}")
        print(f"   Return:         {test['total_return_pct']:+.2f}%")
        print(f"   Win Rate:       {test['win_rate']:.1f}%")
        print(f"   Profit Factor:  {test['profit_factor']:.2f}")
        print(f"   Max Drawdown:   {test['max_drawdown_pct']:.2f}%")
        
        print("\n" + "-"*70)
        print("🔍 ROBUSTHEIT ANALYSE:")
        print(f"   Return Diff:    {analysis['return_pct_difference']:+.2f}%")
        print(f"   Win Rate Diff:  {analysis['win_rate_difference']:+.1f}%")
        print(f"   PF Diff:        {analysis['profit_factor_difference']:+.2f}")
        print("-"*70)
        print(f"   Robustness Score: {analysis['robustness_score']}/100")
        print(f"   Verdict:          {analysis['verdict']}")
        print(f"   Empfehlung:       {analysis['recommendation']}")
        print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Walk-Forward Test - Robuste Strategie-Validierung',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Standard Walk-Forward (70/30 Split)
  python walk_forward_test.py --strategy bollinger --symbol PLTR
  
  # Mit Parameter-Optimierung
  python walk_forward_test.py --strategy sma_crossover --symbol AAPL --optimize-params
  
  # Kürzerer Zeitraum, mehr Test-Daten
  python walk_forward_test.py --strategy rsi --symbol BTC-USD --days 60 --train-ratio 0.6
        """
    )
    
    parser.add_argument('--strategy', type=str, required=True,
                       choices=list(STRATEGIES.keys()),
                       help='Name der Strategie')
    parser.add_argument('--symbol', type=str, required=True,
                       help='Trading Symbol')
    parser.add_argument('--days', type=int, default=90,
                       help='Anzahl Tage gesamt (default: 90)')
    parser.add_argument('--interval', type=str, default='1h',
                       choices=['15m', '30m', '1h', '4h', '1d'],
                       help='Datenintervall (default: 1h)')
    parser.add_argument('--market-type', type=str, default='stock',
                       choices=['stock', 'crypto'],
                       help='Markttyp (default: stock)')
    parser.add_argument('--train-ratio', type=float, default=0.7,
                       help='Anteil Training (0.7 = 70%, default: 0.7)')
    parser.add_argument('--optimize-params', action='store_true',
                       help='Optimiere Parameter auf Train-Set')
    parser.add_argument('--capital', type=float, default=10000.0,
                       help='Startkapital (default: 10000)')
    parser.add_argument('--save', action='store_true',
                       help='Ergebnisse speichern')
    
    args = parser.parse_args()
    
    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Walk-Forward Test
        wft = WalkForwardTest(
            initial_capital=args.capital
        )
        
        results = wft.run(
            strategy_name=args.strategy,
            symbol=args.symbol,
            days=args.days,
            interval=args.interval,
            market_type=args.market_type,
            train_ratio=args.train_ratio,
            optimize_params=args.optimize_params
        )
        
        # Zeige Ergebnisse
        wft.print_summary(results)
        
        # Speichern
        if args.save:
            os.makedirs('walk_forward_results', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"walk_forward_results/{args.strategy}_{args.symbol}_{timestamp}.json"
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"💾 Gespeichert: {filepath}")
        
        # Exit code basierend auf Robustheit
        if results['robustness_analysis']['is_overfitted']:
            print("⚠️  WARNUNG: Strategie zeigt Overfitting!")
            return 1
        return 0
        
    except Exception as e:
        logging.error(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

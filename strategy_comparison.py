#!/usr/bin/env python3
"""
Strategy Comparison Module - Multi-Strategie Vergleich

Testet ALLE Strategien auf mehrere Assets und erstellt Ranking.
Ideal, um Top-3 Kombinationen in 15 Minuten zu identifizieren.

Usage:
    python strategy_comparison.py --assets PLTR,ETH-USD,BTC-USD,TSLA --strategies all
    python strategy_comparison.py --assets AAPL,MSFT --strategies sma_crossover,rsi,macd
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd
import concurrent.futures
from tabulate import tabulate

from rapid_backtest import RapidBacktest
from strategies import STRATEGIES


class StrategyComparator:
    """
    Vergleicht mehrere Strategien auf mehrere Assets.
    
    Ziel: Top 3 Kombinationen in 15 Minuten identifizieren.
    """
    
    def __init__(self, 
                 days: int = 90,
                 interval: str = '1h',
                 initial_capital: float = 10000.0,
                 commission: float = 0.001):
        self.days = days
        self.interval = interval
        self.initial_capital = initial_capital
        self.commission = commission
        self.logger = logging.getLogger(__name__)
        
        # Results storage
        self.results: List[Dict[str, Any]] = []
        
    def run_comparison(self,
                      assets: List[str],
                      strategies: List[str],
                      market_types: Dict[str, str] = None,
                      parallel: bool = True) -> pd.DataFrame:
        """
        Führe Vergleich durch.
        
        Args:
            assets: Liste der Symbole (z.B. ['PLTR', 'AAPL', 'BTC-USD'])
            strategies: Liste der Strategien-Namen
            market_types: Dict mit Symbol -> 'stock'/'crypto'
            parallel: Parallelisierung verwenden
            
        Returns:
            DataFrame mit allen Ergebnissen (sortiert nach Score)
        """
        start_time = datetime.now()
        self.logger.info(f"🚀 Starte Strategy Comparison")
        self.logger.info(f"   Assets: {', '.join(assets)}")
        self.logger.info(f"   Strategies: {', '.join(strategies)}")
        self.logger.info(f"   Zeitraum: {self.days} Tage")
        
        # Erstelle Job-Liste
        jobs = []
        for asset in assets:
            for strategy in strategies:
                market_type = market_types.get(asset, 'stock') if market_types else 'stock'
                jobs.append({
                    'asset': asset,
                    'strategy': strategy,
                    'market_type': market_type
                })
        
        self.logger.info(f"   Total Jobs: {len(jobs)}")
        
        # Führe Jobs aus
        if parallel and len(jobs) > 1:
            self.results = self._run_parallel(jobs)
        else:
            self.results = self._run_sequential(jobs)
        
        # Erstelle DataFrame
        df = self._create_results_dataframe()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"✅ Vergleich abgeschlossen in {elapsed:.1f}s")
        
        return df
    
    def _run_single_backtest(self, job: Dict) -> Dict[str, Any]:
        """Führe einzelnen Backtest aus."""
        try:
            rapid = RapidBacktest(
                initial_capital=self.initial_capital,
                commission=self.commission
            )
            
            result = rapid.run(
                strategy_name=job['strategy'],
                symbol=job['asset'],
                days=self.days,
                interval=self.interval,
                market_type=job['market_type']
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei {job['strategy']} auf {job['asset']}: {e}")
            return {
                'strategy': job['strategy'],
                'symbol': job['asset'],
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown_pct': -100,
                'sharpe_ratio': 0,
                'trades_per_month': 0,
                'score': 0,
                'rating': 'ERROR',
                'total_return_pct': -100,
                'error': str(e)
            }
    
    def _run_sequential(self, jobs: List[Dict]) -> List[Dict]:
        """Führe Jobs sequentiell aus."""
        results = []
        for i, job in enumerate(jobs, 1):
            self.logger.info(f"\n[{i}/{len(jobs)}] Teste {job['strategy']} auf {job['asset']}...")
            result = self._run_single_backtest(job)
            results.append(result)
        return results
    
    def _run_parallel(self, jobs: List[Dict], max_workers: int = 4) -> List[Dict]:
        """Führe Jobs parallel aus."""
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_job = {
                executor.submit(self._run_single_backtest, job): job 
                for job in jobs
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_job), 1):
                job = future_to_job[future]
                try:
                    result = future.result()
                    results.append(result)
                    self.logger.info(f"   [{i}/{len(jobs)}] {job['strategy']}/{job['asset']}: Score={result.get('score', 0):.1f}")
                except Exception as e:
                    self.logger.error(f"   [{i}/{len(jobs)}] {job['strategy']}/{job['asset']}: Fehler - {e}")
                    results.append({
                        'strategy': job['strategy'],
                        'symbol': job['asset'],
                        'score': 0,
                        'rating': 'ERROR',
                        'error': str(e)
                    })
        
        return results
    
    def _create_results_dataframe(self) -> pd.DataFrame:
        """Erstelle DataFrame aus Results."""
        if not self.results:
            return pd.DataFrame()
        
        # Extrahiere relevante Spalten
        records = []
        for r in self.results:
            records.append({
                'Strategy': r.get('strategy', 'N/A'),
                'Asset': r.get('symbol', 'N/A'),
                'Trades': r.get('total_trades', 0),
                'Win Rate %': round(r.get('win_rate', 0), 1),
                'Profit Factor': round(r.get('profit_factor', 0), 2),
                'Max DD %': round(r.get('max_drawdown_pct', 0), 2),
                'Sharpe': round(r.get('sharpe_ratio', 0), 2),
                'Trades/Month': round(r.get('trades_per_month', 0), 1),
                'Return %': round(r.get('total_return_pct', 0), 2),
                'Score': round(r.get('score', 0), 1),
                'Rating': r.get('rating', 'N/A')
            })
        
        df = pd.DataFrame(records)
        
        # Sortiere nach Score
        df = df.sort_values('Score', ascending=False).reset_index(drop=True)
        
        return df
    
    def print_ranking(self, df: pd.DataFrame, top_n: int = 10):
        """Drucke Ranking-Tabelle."""
        print("\n" + "="*100)
        print("🏆 STRATEGY COMPARISON RANKING")
        print("="*100)
        
        if df.empty:
            print("❌ Keine Ergebnisse verfügbar")
            return
        
        # Zeige Top N
        display_df = df.head(top_n).copy()
        display_df.index = display_df.index + 1  # 1-basiert
        
        print(f"\n📊 Top {min(top_n, len(df))} Strategie-Asset Kombinationen:")
        print(tabulate(
            display_df,
            headers='keys',
            tablefmt='grid',
            floatfmt='.2f',
            stralign='center',
            numalign='center'
        ))
        
        # Statistik
        print("\n📈 STATISTIK:")
        print(f"   Total Tests:      {len(df)}")
        print(f"   ⭐ Excellent:     {len(df[df['Rating'] == '⭐⭐⭐ EXCELLENT'])}")
        print(f"   ⭐⭐ Good:         {len(df[df['Rating'] == '⭐⭐ GOOD'])}")
        print(f"   ⭐ OK:             {len(df[df['Rating'] == '⭐ OK'])}")
        print(f"   ❌ Poor:           {len(df[df['Rating'] == '❌ POOR'])}")
        
        # Top 3 Empfehlungen
        top_3 = df.head(3)
        if not top_3.empty:
            print("\n🎯 TOP 3 EMPFEHLUNGEN:")
            for i, row in top_3.iterrows():
                print(f"   {i+1}. {row['Strategy']} auf {row['Asset']}")
                print(f"      Score: {row['Score']:.1f} | Win Rate: {row['Win Rate %']:.1f}% | PF: {row['Profit Factor']:.2f}")
        
        print("="*100 + "\n")
    
    def save_results(self, df: pd.DataFrame, output_dir: str = 'comparison_results') -> str:
        """Speichere Ergebnisse."""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(output_dir, f'comparison_{timestamp}.csv')
        
        df.to_csv(filepath, index=False)
        self.logger.info(f"💾 Ergebnisse gespeichert: {filepath}")
        
        # Auch als JSON
        json_path = os.path.join(output_dir, f'comparison_{timestamp}.json')
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        return filepath
    
    def get_top_combinations(self, df: pd.DataFrame, min_score: float = 60) -> List[Dict]:
        """Hole Top-Kombinationen für Paper Trading."""
        top = df[df['Score'] >= min_score].head(3)
        return top.to_dict('records')


def detect_market_type(symbol: str) -> str:
    """Erkenne Markttyp basierend auf Symbol."""
    symbol_upper = symbol.upper()
    if symbol_upper.endswith('-USD') or symbol_upper.endswith('USDT') or symbol_upper in ['BTC', 'ETH', 'SOL', 'ADA']:
        return 'crypto'
    return 'stock'


def main():
    parser = argparse.ArgumentParser(
        description='Strategy Comparison - Multi-Strategie Vergleich',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Vergleiche alle Strategien auf Standard-Assets
  python strategy_comparison.py --assets PLTR,ETH-USD,BTC-USD,TSLA --strategies all
  
  # Nur spezifische Strategien
  python strategy_comparison.py --assets AAPL,MSFT --strategies sma_crossover,rsi,macd
  
  # Mit spezifischem Zeitraum
  python strategy_comparison.py --assets BTC-USD,ETH-USD --strategies all --days 60 --interval 1h
        """
    )
    
    parser.add_argument('--assets', type=str, required=True,
                       help='Komma-getrennte Liste (z.B. "PLTR,AAPL,BTC-USD")')
    parser.add_argument('--strategies', type=str, required=True,
                       help='"all" oder komma-getrennte Liste (z.B. "sma_crossover,rsi")')
    parser.add_argument('--days', type=int, default=90,
                       help='Anzahl Tage (default: 90)')
    parser.add_argument('--interval', type=str, default='1h',
                       choices=['15m', '30m', '1h', '4h', '1d'],
                       help='Datenintervall (default: 1h)')
    parser.add_argument('--capital', type=float, default=10000.0,
                       help='Startkapital (default: 10000)')
    parser.add_argument('--save', action='store_true',
                       help='Ergebnisse speichern')
    parser.add_argument('--parallel', action='store_true', default=True,
                       help='Parallelisierung verwenden (default: True)')
    parser.add_argument('--no-parallel', dest='parallel', action='store_false',
                       help='Keine Parallelisierung')
    parser.add_argument('--top-n', type=int, default=10,
                       help='Zeige Top N Ergebnisse (default: 10)')
    
    args = parser.parse_args()
    
    # Logging setup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Parse Assets
        assets = [a.strip().upper() for a in args.assets.split(',')]
        
        # Parse Strategies
        if args.strategies.lower() == 'all':
            strategies = list(STRATEGIES.keys())
        else:
            strategies = [s.strip() for s in args.strategies.split(',')]
            # Validierung
            invalid = [s for s in strategies if s not in STRATEGIES]
            if invalid:
                print(f"❌ Ungültige Strategien: {', '.join(invalid)}")
                print(f"Verfügbar: {', '.join(STRATEGIES.keys())}")
                return 1
        
        # Markttypen erkennen
        market_types = {asset: detect_market_type(asset) for asset in assets}
        
        # Führe Vergleich durch
        comparator = StrategyComparator(
            days=args.days,
            interval=args.interval,
            initial_capital=args.capital
        )
        
        df = comparator.run_comparison(
            assets=assets,
            strategies=strategies,
            market_types=market_types,
            parallel=args.parallel
        )
        
        # Zeige Ergebnisse
        comparator.print_ranking(df, top_n=args.top_n)
        
        # Speichern
        if args.save:
            comparator.save_results(df)
        
        # Gib Top-3 zurück für weitere Verarbeitung
        top_3 = comparator.get_top_combinations(df)
        if top_3:
            print("\n💡 Für Walk-Forward Test:")
            print(f"   Beste Kombination: {top_3[0]['Strategy']} auf {top_3[0]['Asset']}")
        
        return 0
        
    except Exception as e:
        logging.error(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

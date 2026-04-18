#!/usr/bin/env python3
"""
Rapid Test Suite - Kombiniert alle Rapid Testing Tools

End-to-End Testing Pipeline:
1. Historischer Backtest (5 Min)
2. Multi-Strategie Vergleich (15 Min)
3. Walk-Forward Analyse (20 Min)
4. Paper Trading Empfehlung

Usage:
    python rapid_test_suite.py --symbol PLTR --full-test
    python rapid_test_suite.py --symbol BTC-USD --market-type crypto --quick-test
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from tabulate import tabulate

from rapid_backtest import RapidBacktest
from strategy_comparison import StrategyComparator, detect_market_type
from walk_forward_test import WalkForwardTest
from strategies import STRATEGIES


class RapidTestSuite:
    """
    Komplette Rapid Testing Pipeline.
    
    Von "10h warten" auf "20 Minuten Rapid Testing" kommen.
    """
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 commission: float = 0.001,
                 output_dir: str = 'rapid_test_results'):
        self.initial_capital = initial_capital
        self.commission = commission
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Results
        self.full_results: Dict[str, Any] = {}
        
    def run_quick_test(self,
                       symbol: str,
                       strategy: str,
                       market_type: str = 'stock',
                       days: int = 90) -> Dict:
        """
        Schneller Einzel-Test (5 Minuten).
        
        Args:
            symbol: Trading Symbol
            strategy: Strategie-Name
            market_type: 'stock' oder 'crypto'
            days: Anzahl Tage
            
        Returns:
            Backtest-Ergebnisse
        """
        self.logger.info(f"🚀 QUICK TEST: {strategy} auf {symbol}")
        
        rapid = RapidBacktest(
            initial_capital=self.initial_capital,
            commission=self.commission
        )
        
        result = rapid.run(
            strategy_name=strategy,
            symbol=symbol,
            days=days,
            interval='1h',
            market_type=market_type
        )
        
        rapid.print_summary()
        
        return result
    
    def run_full_pipeline(self,
                         symbol: str,
                         market_type: str = 'stock',
                         days: int = 90,
                         test_strategies: Optional[List[str]] = None) -> Dict:
        """
        Komplette Pipeline (20 Minuten).
        
        Args:
            symbol: Trading Symbol
            market_type: 'stock' oder 'crypto'
            days: Anzahl Tage für Backtest
            test_strategies: Liste zu testender Strategien (None = alle)
            
        Returns:
            Komplette Pipeline-Ergebnisse
        """
        start_time = datetime.now()
        self.logger.info("="*70)
        self.logger.info("🚀 RAPID TEST SUITE - Full Pipeline")
        self.logger.info("="*70)
        self.logger.info(f"Asset: {symbol} | Markt: {market_type} | Zeitraum: {days} Tage")
        
        strategies = test_strategies or list(STRATEGIES.keys())
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'market_type': market_type,
            'days': days,
            'tested_strategies': strategies,
            'phases': {}
        }
        
        # === PHASE 1: Multi-Strategie Vergleich ===
        self.logger.info("\n" + "="*70)
        self.logger.info("📊 PHASE 1: Multi-Strategie Vergleich")
        self.logger.info("="*70)
        
        comparator = StrategyComparator(
            days=days,
            interval='1h',
            initial_capital=self.initial_capital,
            commission=self.commission
        )
        
        market_types = {symbol: market_type}
        comparison_df = comparator.run_comparison(
            assets=[symbol],
            strategies=strategies,
            market_types=market_types,
            parallel=True
        )
        
        comparator.print_ranking(comparison_df, top_n=5)
        results['phases']['comparison'] = comparison_df.to_dict('records')
        
        # Hole Top-3
        top_3 = comparator.get_top_combinations(comparison_df, min_score=50)
        results['top_3'] = top_3
        
        if not top_3:
            self.logger.warning("⚠️  Keine Strategie mit Score >= 50 gefunden!")
            self.logger.warning("   Empfehlung: Andere Assets oder Parameter testen.")
            return results
        
        # === PHASE 2: Walk-Forward Test für Top Strategy ===
        best_strategy = top_3[0]['Strategy']
        
        self.logger.info("\n" + "="*70)
        self.logger.info("🔄 PHASE 2: Walk-Forward Analyse (Top Strategy)")
        self.logger.info(f"   Strategie: {best_strategy}")
        self.logger.info("="*70)
        
        wft = WalkForwardTest(
            initial_capital=self.initial_capital,
            commission=self.commission
        )
        
        wf_results = wft.run(
            strategy_name=best_strategy,
            symbol=symbol,
            days=days,
            interval='1h',
            market_type=market_type,
            train_ratio=0.7,
            optimize_params=True
        )
        
        wft.print_summary(wf_results)
        results['phases']['walk_forward'] = wf_results
        
        # === PHASE 3: Final Recommendation ===
        self.logger.info("\n" + "="*70)
        self.logger.info("🎯 PHASE 3: Final Recommendation")
        self.logger.info("="*70)
        
        recommendation = self._generate_recommendation(
            comparison_df, 
            wf_results
        )
        results['recommendation'] = recommendation
        
        self._print_recommendation(recommendation)
        
        # Speichere alles
        self._save_full_results(results)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        results['total_execution_time_seconds'] = elapsed
        
        self.logger.info("\n" + "="*70)
        self.logger.info(f"✅ Pipeline abgeschlossen in {elapsed/60:.1f} Minuten")
        self.logger.info("="*70)
        
        return results
    
    def _generate_recommendation(self, 
                                comparison_df: pd.DataFrame,
                                wf_results: Dict) -> Dict:
        """Generiere finale Empfehlung."""
        top = comparison_df.iloc[0] if not comparison_df.empty else None
        wf = wf_results.get('robustness_analysis', {})
        
        # Score-Berechnung
        overall_score = 0
        
        if top is not None:
            overall_score += top['Score'] * 0.4  # 40% Backtest Score
        
        if wf:
            overall_score += wf.get('robustness_score', 0) * 0.4  # 40% Robustheit
            
        # 20% für PF > 1.5 und Win Rate > 50%
        if top is not None:
            if top['Profit Factor'] >= 1.5:
                overall_score += 10
            if top['Win Rate %'] > 50:
                overall_score += 10
        
        # Decision
        if overall_score >= 75:
            decision = "✅ GO"
            confidence = "HIGH"
            action = "Start Paper Trading"
        elif overall_score >= 60:
            decision = "⚠️  CAUTION"
            confidence = "MEDIUM"
            action = "Short Paper Test (1h), dann entscheiden"
        else:
            decision = "❌ STOP"
            confidence = "LOW"
            action = "Strategie ablehnen, andere testen"
        
        return {
            'overall_score': round(overall_score, 1),
            'decision': decision,
            'confidence': confidence,
            'recommended_action': action,
            'best_strategy': top['Strategy'] if top is not None else None,
            'best_asset': top['Asset'] if top is not None else None,
            'backtest_score': top['Score'] if top is not None else 0,
            'robustness_score': wf.get('robustness_score', 0),
            'is_robust': not wf.get('is_overfitted', True),
            'risk_level': self._calculate_risk_level(top, wf)
        }
    
    def _calculate_risk_level(self, top: Optional[pd.Series], wf: Dict) -> str:
        """Berechne Risiko-Level."""
        if top is None:
            return "UNKNOWN"
        
        risk_score = 0
        
        if top['Max DD %'] < -20:
            risk_score += 2
        elif top['Max DD %'] < -10:
            risk_score += 1
            
        if top['Profit Factor'] < 1.2:
            risk_score += 2
        elif top['Profit Factor'] < 1.5:
            risk_score += 1
            
        if wf.get('is_overfitted', True):
            risk_score += 2
        
        if risk_score >= 4:
            return "HIGH"
        elif risk_score >= 2:
            return "MEDIUM"
        return "LOW"
    
    def _print_recommendation(self, rec: Dict):
        """Drucke Empfehlung."""
        print("\n" + "="*70)
        print("🎯 FINAL RECOMMENDATION")
        print("="*70)
        print(f"\n   Beste Strategie:   {rec['best_strategy']} auf {rec['best_asset']}")
        print(f"   Overall Score:     {rec['overall_score']:.1f}/100")
        print(f"   Backtest Score:    {rec['backtest_score']:.1f}/100")
        print(f"   Robustness Score:  {rec['robustness_score']:.0f}/100")
        print(f"   Is Robust:         {rec['is_robust']}")
        print(f"   Risk Level:        {rec['risk_level']}")
        print("-"*70)
        print(f"   DECISION:          {rec['decision']}")
        print(f"   Confidence:        {rec['confidence']}")
        print(f"   Action:            {rec['recommended_action']}")
        print("="*70 + "\n")
    
    def _save_full_results(self, results: Dict):
        """Speichere alle Ergebnisse."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        symbol = results['symbol']
        
        filepath = os.path.join(
            self.output_dir, 
            f"rapid_suite_{symbol}_{timestamp}.json"
        )
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"💾 Vollständige Ergebnisse: {filepath}")


def print_usage_examples():
    """Drucke Nutzungsbeispiele."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    RAPID TEST SUITE - USAGE GUIDE                              ║
╠══════════════════════════════════════════════════════════════════════════════╣

🚀 QUICK TEST (5 Minuten):
   python rapid_test_suite.py --symbol PLTR --quick-test --strategy bollinger
   
   → Einzelne Strategie schnell testen
   → Idealer Sprint für Entwicklungs-Iterationen

📊 FULL PIPELINE (20 Minuten):
   python rapid_test_suite.py --symbol PLTR --full-test
   
   → Testet alle Strategien
   → Walk-Forward für beste Strategie
   → Finale Empfehlung mit Score

🔥 MULTI-ASSET TEST:
   # Crypto
   python rapid_test_suite.py --symbol BTC-USD --market-type crypto --full-test
   
   # Aktien
   python rapid_test_suite.py --symbol AAPL --full-test

📈 CUSTOM STRATEGY SET:
   python rapid_test_suite.py --symbol PLTR --strategies sma_crossover,rsi,bollinger

🎯 DIRECT TOOLS:
   # Nur 5-Min Backtest
   python rapid_backtest.py --strategy bollinger --symbol PLTR --days 90
   
   # Nur Strategie-Vergleich
   python strategy_comparison.py --assets PLTR,AAPL --strategies all
   
   # Nur Walk-Forward
   python walk_forward_test.py --strategy bollinger --symbol PLTR --optimize-params

╚══════════════════════════════════════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(
        description='Rapid Test Suite - 20 Minuten statt 10 Stunden',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Quick Test (5 Min)
  python rapid_test_suite.py --symbol PLTR --quick-test --strategy bollinger
  
  # Full Pipeline (20 Min)
  python rapid_test_suite.py --symbol PLTR --full-test
  
  # Crypto
  python rapid_test_suite.py --symbol BTC-USD --market-type crypto --full-test
  
  # Custom Strategies
  python rapid_test_suite.py --symbol AAPL --strategies sma_crossover,rsi,bollinger
        """
    )
    
    parser.add_argument('--symbol', type=str, required=True,
                       help='Trading Symbol (z.B. PLTR, AAPL, BTC-USD)')
    parser.add_argument('--market-type', type=str, default='stock',
                       choices=['stock', 'crypto'],
                       help='Markttyp (default: stock)')
    parser.add_argument('--strategy', type=str, default='bollinger',
                       choices=list(STRATEGIES.keys()),
                       help='Strategie für Quick-Test (default: bollinger)')
    parser.add_argument('--strategies', type=str, default=None,
                       help='Komma-getrennte Liste für Full-Test (None = alle)')
    parser.add_argument('--days', type=int, default=90,
                       help='Anzahl Tage (default: 90)')
    parser.add_argument('--quick-test', action='store_true',
                       help='Schneller 5-Min Test')
    parser.add_argument('--full-test', action='store_true',
                       help='Komplette 20-Min Pipeline')
    parser.add_argument('--capital', type=float, default=10000.0,
                       help='Startkapital (default: 10000)')
    parser.add_argument('--examples', action='store_true',
                       help='Zeige Nutzungsbeispiele')
    
    args = parser.parse_args()
    
    # Zeige Beispiele
    if args.examples:
        print_usage_examples()
        return 0
    
    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        suite = RapidTestSuite(
            initial_capital=args.capital,
            output_dir='rapid_test_results'
        )
        
        if args.quick_test:
            # Schneller Test
            result = suite.run_quick_test(
                symbol=args.symbol,
                strategy=args.strategy,
                market_type=args.market_type,
                days=args.days
            )
            
            # Exit code basierend auf Score
            return 0 if result.get('score', 0) >= 50 else 1
            
        elif args.full_test:
            # Volle Pipeline
            strategies = None
            if args.strategies:
                strategies = [s.strip() for s in args.strategies.split(',')]
                # Validierung
                invalid = [s for s in strategies if s not in STRATEGIES]
                if invalid:
                    print(f"❌ Ungültige Strategien: {', '.join(invalid)}")
                    return 1
            
            results = suite.run_full_pipeline(
                symbol=args.symbol,
                market_type=args.market_type,
                days=args.days,
                test_strategies=strategies
            )
            
            # Exit code basierend auf Empfehlung
            rec = results.get('recommendation', {})
            if rec.get('decision', '').startswith('✅'):
                return 0
            elif rec.get('decision', '').startswith('⚠️'):
                return 2  # Caution
            return 1
            
        else:
            print("❌ Bitte --quick-test oder --full-test angeben")
            print("   Nutze --examples für Beispiele")
            return 1
            
    except Exception as e:
        logging.error(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

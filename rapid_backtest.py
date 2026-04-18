#!/usr/bin/env python3
"""
Rapid Backtest Module - 5-Minute Historical Test

Testet Strategien schnell auf den letzten 90 Tagen (1h-Daten).
Ideal für schnelle Strategie-Validierung vor Paper Trading.

Usage:
    python rapid_backtest.py --strategy bollinger_mean_reversion --symbol PLTR --days 90
    python rapid_backtest.py --strategy sma_crossover --symbol AAPL --days 60 --interval 1h
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import pandas as pd
import numpy as np

from data_fetcher import DataFetcher
from strategies import get_strategy, STRATEGIES
from backtest import Backtest


class RapidBacktest:
    """
    Schneller Backtest für Strategie-Validierung.
    
    Ziel: In 5 Minuten wissen, ob eine Strategie profitabel war.
    """
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 commission: float = 0.001,
                 slippage: float = 0.0005):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.logger = logging.getLogger(__name__)
        
        # Results storage
        self.results: Dict[str, Any] = {}
        self.equity_curve: Optional[pd.Series] = None
        self.trades: list = []
        
    def run(self,
            strategy_name: str,
            symbol: str,
            days: int = 90,
            interval: str = '1h',
            market_type: str = 'stock',
            strategy_params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Führe schnellen Backtest durch.
        
        Args:
            strategy_name: Name der Strategie (aus STRATEGIES)
            symbol: Trading Symbol (z.B. 'PLTR', 'BTC-USD')
            days: Anzahl Tage für Historie (default: 90)
            interval: Datenintervall ('1h', '15m', '1d')
            market_type: 'stock' oder 'crypto'
            strategy_params: Optionale Strategie-Parameter
            
        Returns:
            Dict mit Backtest-Results
        """
        start_time = datetime.now()
        self.logger.info(f"🚀 Rapid Backtest: {strategy_name} auf {symbol} ({days} Tage)")
        
        # 1. Daten laden (letzte N Tage)
        self.logger.info("📊 Lade Marktdaten...")
        df = self._fetch_data(symbol, market_type, interval, days)
        
        if df.empty or len(df) < 50:
            raise ValueError(f"Nicht genug Daten für {symbol}. Nur {len(df)} Datenpunkte.")
        
        self.logger.info(f"   ✓ {len(df)} Datenpunkte geladen ({df.index[0]} bis {df.index[-1]})")
        
        # 2. Strategie initialisieren
        self.logger.info(f"🧠 Initialisiere Strategie: {strategy_name}")
        strategy = get_strategy(strategy_name, strategy_params)
        
        # 3. Backtest durchführen
        self.logger.info("⚡ Führe Backtest durch...")
        backtest = Backtest(
            initial_capital=self.initial_capital,
            commission=self.commission,
            slippage=self.slippage
        )
        
        results = backtest.run(strategy, df)
        self.equity_curve = backtest.equity_curve
        self.trades = backtest.trades
        
        # 4. Zusätzliche Metriken berechnen
        self.results = self._calculate_extended_metrics(results, backtest, days)
        self.results['strategy'] = strategy_name
        self.results['symbol'] = symbol
        self.results['interval'] = interval
        self.results['days_backtested'] = days
        self.results['data_points'] = len(df)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        self.results['execution_time_seconds'] = elapsed
        
        self.logger.info(f"✅ Backtest abgeschlossen in {elapsed:.1f}s")
        
        return self.results
    
    def _fetch_data(self, symbol: str, market_type: str, interval: str, days: int) -> pd.DataFrame:
        """Lade Daten für den Backtest-Zeitraum."""
        fetcher = DataFetcher()
        
        # Berechne Start-Datum
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 10)  # +10 für Rolling-Indikatoren
        
        try:
            if market_type == 'stock':
                df = fetcher.fetch_yahoo_finance(
                    symbol=symbol,
                    interval=interval,
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d')
                )
            else:  # crypto
                # Für Crypto: berechne limit basierend auf Tagen
                # 1h = 24 candles pro Tag
                limit = min(days * 24, 1000)  # Max 1000 für Binance
                df = fetcher.fetch_binance(
                    symbol=symbol.replace('-USD', 'USDT').replace('-USDT', 'USDT'),
                    interval=interval,
                    limit=limit
                )
            
            return df
            
        except Exception as e:
            self.logger.error(f"Fehler beim Laden der Daten: {e}")
            raise
    
    def _calculate_extended_metrics(self, 
                                   results: Dict, 
                                   backtest: Backtest,
                                   days: int) -> Dict[str, Any]:
        """Berechne erweiterte Performance-Metriken."""
        
        # Trades pro Monat
        trades_per_month = results['total_trades'] / (days / 30) if days > 0 else 0
        
        # Gewinn pro Trade
        profit_per_trade = results['total_return'] / results['total_trades'] if results['total_trades'] > 0 else 0
        
        # Calmar Ratio (Return / Max Drawdown)
        calmar_ratio = abs(results['total_return_pct'] / results['max_drawdown_pct']) if results['max_drawdown_pct'] != 0 else 0
        
        # Expectancy (erwarteter Gewinn pro Trade)
        win_rate_decimal = results['win_rate'] / 100
        avg_win = results['avg_win']
        avg_loss = abs(results['avg_loss'])
        expectancy = (win_rate_decimal * avg_win) - ((1 - win_rate_decimal) * avg_loss) if results['total_trades'] > 0 else 0
        
        # Score: Kombinierte Metrik (0-100)
        # Gewichtung: Win Rate (30%), Profit Factor (25%), Trades/Monat (15%), Sharpe (20%), Drawdown (10%)
        score = 0
        if results['total_trades'] > 5:  # Mindestens 5 Trades
            win_score = min(results['win_rate'], 70) / 70 * 30
            pf_score = min(results['profit_factor'], 3) / 3 * 25
            trade_score = min(trades_per_month, 20) / 20 * 15
            sharpe_score = min(max(results['sharpe_ratio'], 0), 3) / 3 * 20
            dd_score = max(0, 1 - abs(results['max_drawdown_pct']) / 20) * 10
            score = win_score + pf_score + trade_score + sharpe_score + dd_score
        
        # Klassifizierung
        if score >= 80:
            rating = "⭐⭐⭐ EXCELLENT"
        elif score >= 60:
            rating = "⭐⭐ GOOD"
        elif score >= 40:
            rating = "⭐ OK"
        else:
            rating = "❌ POOR"
        
        extended = {
            **results,
            'trades_per_month': round(trades_per_month, 2),
            'profit_per_trade': round(profit_per_trade, 2),
            'calmar_ratio': round(calmar_ratio, 2),
            'expectancy': round(expectancy, 2),
            'score': round(score, 1),
            'rating': rating
        }
        
        return extended
    
    def save_results(self, output_dir: str = 'rapid_results') -> str:
        """Speichere Ergebnisse als JSON."""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.results['strategy']}_{self.results['symbol']}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'backtest_config': {
                'initial_capital': self.initial_capital,
                'commission': self.commission,
                'slippage': self.slippage
            },
            'results': self.results,
            'equity_curve': self.equity_curve.to_dict() if self.equity_curve is not None else {},
            'trades': [
                {**t, 'timestamp': str(t['timestamp'])}
                for t in self.trades
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"💾 Ergebnisse gespeichert: {filepath}")
        return filepath
    
    def print_summary(self):
        """Drucke zusammenfassende Ergebnisse."""
        if not self.results:
            print("❌ Keine Ergebnisse verfügbar")
            return
        
        r = self.results
        print("\n" + "="*60)
        print(f"🚀 RAPID BACKTEST RESULTS")
        print("="*60)
        print(f"Strategie:  {r['strategy']}")
        print(f"Symbol:     {r['symbol']}")
        print(f"Zeitraum:   {r['days_backtested']} Tage ({r['data_points']} Datenpunkte)")
        print(f"Dauer:      {r['execution_time_seconds']:.1f}s")
        print("-"*60)
        print(f"💰 Initial:        ${r['initial_capital']:,.2f}")
        print(f"💰 Final:          ${r['final_equity']:,.2f}")
        print(f"📈 Total Return:   {r['total_return_pct']:+.2f}%")
        print("-"*60)
        print(f"🔄 Total Trades:   {r['total_trades']}")
        print(f"✅ Win Rate:       {r['win_rate']:.1f}%")
        print(f"📊 Profit Factor:  {r['profit_factor']:.2f}")
        print(f"📉 Max Drawdown:   {r['max_drawdown_pct']:.2f}%")
        print(f"📊 Sharpe Ratio:   {r['sharpe_ratio']:.2f}")
        print(f"📊 Calmar Ratio:   {r['calmar_ratio']:.2f}")
        print("-"*60)
        print(f"🔄 Trades/Monat:   {r['trades_per_month']:.1f}")
        print(f"💵 Profit/Trade:   ${r['profit_per_trade']:+.2f}")
        print(f"🎯 Expectancy:     ${r['expectancy']:+.2f}")
        print("-"*60)
        print(f"⭐ SCORE:          {r['score']:.1f}/100")
        print(f"   Rating:         {r['rating']}")
        print("="*60)
        
        # Empfehlung
        if r['score'] >= 70 and r['profit_factor'] >= 1.5:
            print("✅ EMPFEHLUNG: Strategie für Paper Trading geeignet!")
        elif r['score'] >= 50:
            print("⚠️  EMPFEHLUNG: Weitere Optimierung empfohlen")
        else:
            print("❌ EMPFEHLUNG: Strategie nicht empfohlen")
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Rapid Backtest - 5 Minuten Strategie-Test',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python rapid_backtest.py --strategy bollinger --symbol PLTR --days 90
  python rapid_backtest.py --strategy sma_crossover --symbol AAPL --days 60
  python rapid_backtest.py --strategy rsi --symbol BTC-USD --market-type crypto --days 90
        """
    )
    
    parser.add_argument('--strategy', type=str, required=True,
                       choices=list(STRATEGIES.keys()),
                       help='Name der Strategie')
    parser.add_argument('--symbol', type=str, required=True,
                       help='Trading Symbol (z.B. PLTR, AAPL, BTC-USD)')
    parser.add_argument('--days', type=int, default=90,
                       help='Anzahl Tage für Backtest (default: 90)')
    parser.add_argument('--interval', type=str, default='1h',
                       choices=['15m', '30m', '1h', '4h', '1d'],
                       help='Datenintervall (default: 1h)')
    parser.add_argument('--market-type', type=str, default='stock',
                       choices=['stock', 'crypto'],
                       help='Markttyp (default: stock)')
    parser.add_argument('--capital', type=float, default=10000.0,
                       help='Startkapital (default: 10000)')
    parser.add_argument('--commission', type=float, default=0.001,
                       help='Kommission pro Trade (default: 0.001 = 0.1%%)')
    parser.add_argument('--save', action='store_true',
                       help='Ergebnisse als JSON speichern')
    parser.add_argument('--plot', action='store_true',
                       help='Equity Curve plotten')
    
    args = parser.parse_args()
    
    # Logging setup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Rapid Backtest durchführen
        rapid = RapidBacktest(
            initial_capital=args.capital,
            commission=args.commission
        )
        
        results = rapid.run(
            strategy_name=args.strategy,
            symbol=args.symbol,
            days=args.days,
            interval=args.interval,
            market_type=args.market_type
        )
        
        # Ergebnisse anzeigen
        rapid.print_summary()
        
        # Optional: Speichern
        if args.save:
            filepath = rapid.save_results()
            print(f"💾 Gespeichert: {filepath}")
        
        # Optional: Plot
        if args.plot:
            rapid.plot_equity_curve()
        
        # Exit code basierend auf Score
        return 0 if results['score'] >= 50 else 1
        
    except Exception as e:
        logging.error(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

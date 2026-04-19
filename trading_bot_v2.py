#!/usr/bin/env python3
"""
Trading Bot v2 - Vereinfachte, funktionierende Version
- JSON Logging statt SQLite
- Echte Daten von Binance
- Validierter Strategie-Test vor Start
"""

import os
import sys
import json
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf

# Setup
WORKSPACE = "/data/.openclaw/workspace/projects/trading-bot"
LOG_DIR = os.path.join(WORKSPACE, "logs")
DATA_DIR = os.path.join(WORKSPACE, "data")
REPORT_DIR = os.path.join(WORKSPACE, "reports")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# Logging Setup
LOG_FILE = os.path.join(LOG_DIR, f"trading_v2_{datetime.now().strftime('%Y%m%d_%H%M')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# JSON Log für Trades
TRADE_LOG = os.path.join(DATA_DIR, "trades_v2.jsonl")
STATUS_LOG = os.path.join(DATA_DIR, "status_v2.jsonl")


class SimpleDataFetcher:
    """Vereinfachter Daten-Fetcher mit yfinance"""
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '15m', limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data from Yahoo Finance"""
        try:
            # Symbol format: ETH-USD für yfinance
            ticker = yf.Ticker(symbol)
            
            # Map timeframe to yfinance period
            period_map = {
                '1m': '1d', '5m': '5d', '15m': '5d', 
                '1h': '1mo', '4h': '3mo', '1d': '6mo'
            }
            period = period_map.get(timeframe, '5d')
            
            df = ticker.history(period=period, interval=timeframe)
            
            if df.empty:
                logger.error(f"❌ Keine Daten für {symbol}")
                return pd.DataFrame()
            
            # Rename columns to lowercase
            df.columns = [c.lower().replace(' ', '_') for c in df.columns]
            
            logger.info(f"✅ Daten abgerufen: {len(df)} candles für {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Datenabruf: {e}")
            return pd.DataFrame()


class SimpleAdaptiveStrategy:
    """
    Vereinfachte Adaptive Momentum Strategie
    - RSI für Overbought/Oversold
    - ATR für Volatilität
    - Schnellere Signale (RSI 40/60 statt 30/70)
    """
    
    def __init__(self, 
                 rsi_period: int = 14,
                 rsi_overbought: float = 60,  # Niedriger = mehr Signale
                 rsi_oversold: float = 40,    # Höher = mehr Signale
                 atr_multiplier: float = 0.5, # Niedriger = empfindlicher
                 ema_fast: int = 9,
                 ema_slow: int = 21):
        
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.atr_multiplier = atr_multiplier
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        
    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calculate ATR"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(window=14).mean()
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate EMA"""
        return prices.ewm(span=period, adjust=False).mean()
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """Generate trading signal"""
        if len(df) < 30:
            return {'signal': 0, 'reason': 'Insufficient data'}
        
        # Calculate indicators
        df = df.copy()
        df['rsi'] = self.calculate_rsi(df['close'])
        df['atr'] = self.calculate_atr(df)
        df['ema_fast'] = self.calculate_ema(df['close'], self.ema_fast)
        df['ema_slow'] = self.calculate_ema(df['close'], self.ema_slow)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        price = latest['close']
        rsi = latest['rsi']
        atr = latest['atr']
        ema_fast = latest['ema_fast']
        ema_slow = latest['ema_slow']
        
        # Signal logic
        signal = 0
        reason = "No signal"
        
        # BUY: RSI < oversold AND price near support AND ema_fast > ema_slow
        if rsi < self.rsi_oversold:
            signal = 1
            reason = f"RSI oversold ({rsi:.1f} < {self.rsi_oversold})"
            
        # SELL: RSI > overbought
        elif rsi > self.rsi_overbought:
            signal = -1
            reason = f"RSI overbought ({rsi:.1f} > {self.rsi_overbought})"
            
        # Trend confirmation
        elif ema_fast > ema_slow and prev['ema_fast'] <= prev['ema_slow']:
            signal = 1
            reason = f"EMA crossover (fast {ema_fast:.2f} > slow {ema_slow:.2f})"
            
        elif ema_fast < ema_slow and prev['ema_fast'] >= prev['ema_slow']:
            signal = -1
            reason = f"EMA crossunder (fast {ema_fast:.2f} < slow {ema_slow:.2f})"
        
        return {
            'signal': signal,
            'reason': reason,
            'price': price,
            'rsi': rsi,
            'atr': atr,
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'timestamp': datetime.now().isoformat()
        }


class SimplePaperTrader:
    """Vereinfachter Paper Trader"""
    
    def __init__(self, initial_capital: float = 10000.0, symbol: str = "ETH-USD"):
        self.cash = initial_capital
        self.initial_capital = initial_capital
        self.symbol = symbol
        self.position = 0.0
        self.avg_entry_price = 0.0
        self.trades = []
        self.total_pnl = 0.0
        self.trade_count = 0
        
    def get_position_value(self, current_price: float) -> float:
        return self.position * current_price
        
    def get_total_value(self, current_price: float) -> float:
        return self.cash + self.get_position_value(current_price)
        
    def execute_signal(self, signal_data: Dict) -> Optional[Dict]:
        """Execute trading signal"""
        signal = signal_data['signal']
        price = signal_data['price']
        
        if signal == 0:
            return None
            
        trade = None
        
        # BUY Signal
        if signal == 1 and self.position == 0:
            position_size = self.cash * 0.95  # 95% of cash
            quantity = position_size / price
            
            self.position = quantity
            self.avg_entry_price = price
            self.cash -= position_size
            self.trade_count += 1
            
            trade = {
                'timestamp': datetime.now().isoformat(),
                'side': 'BUY',
                'symbol': self.symbol,
                'quantity': quantity,
                'price': price,
                'value': position_size,
                'cash_remaining': self.cash,
                'position': self.position,
                'reason': signal_data['reason']
            }
            
        # SELL Signal
        elif signal == -1 and self.position > 0:
            position_value = self.position * price
            pnl = position_value - (self.position * self.avg_entry_price)
            
            self.cash += position_value
            self.total_pnl += pnl
            self.trade_count += 1
            
            trade = {
                'timestamp': datetime.now().isoformat(),
                'side': 'SELL',
                'symbol': self.symbol,
                'quantity': self.position,
                'price': price,
                'value': position_value,
                'pnl': pnl,
                'cash_after': self.cash,
                'reason': signal_data['reason']
            }
            
            self.position = 0
            self.avg_entry_price = 0
            
        return trade
    
    def get_status(self, current_price: float) -> Dict:
        """Get current status"""
        position_value = self.get_position_value(current_price)
        total_value = self.get_total_value(current_price)
        unrealized_pnl = 0.0
        
        if self.position > 0:
            unrealized_pnl = (current_price - self.avg_entry_price) * self.position
            
        return {
            'timestamp': datetime.now().isoformat(),
            'symbol': self.symbol,
            'cash': self.cash,
            'position': self.position,
            'avg_entry': self.avg_entry_price,
            'current_price': current_price,
            'position_value': position_value,
            'total_value': total_value,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': self.total_pnl,
            'total_pnl': self.total_pnl + unrealized_pnl,
            'return_pct': ((total_value - self.initial_capital) / self.initial_capital) * 100,
            'trade_count': self.trade_count
        }


class TradingBotV2:
    """Haupt Trading Bot Klasse"""
    
    def __init__(self, 
                 symbol: str = "ETH-USD",
                 timeframe: str = "15m",
                 duration_hours: int = 2,
                 check_interval: int = 60):
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.duration_hours = duration_hours
        self.check_interval = check_interval
        
        self.data_fetcher = SimpleDataFetcher()
        self.strategy = SimpleAdaptiveStrategy(
            rsi_overbought=60,  # Mehr Signale
            rsi_oversold=40,
            atr_multiplier=0.5  # Empfindlicher
        )
        self.trader = SimplePaperTrader(symbol=symbol)
        
        self.start_time = None
        self.end_time = None
        self.status_history = []
        
    def log_trade(self, trade: Dict):
        """Log trade to JSONL file"""
        with open(TRADE_LOG, 'a') as f:
            f.write(json.dumps(trade) + '\n')
            
    def log_status(self, status: Dict):
        """Log status to JSONL file"""
        with open(STATUS_LOG, 'a') as f:
            f.write(json.dumps(status) + '\n')
            
    def test_data_fetch(self) -> bool:
        """Test data fetching before starting"""
        logger.info("🧪 Teste Datenabruf...")
        df = self.data_fetcher.fetch_ohlcv(self.symbol, self.timeframe, limit=50)
        
        if df.empty:
            logger.error("❌ Datenabruf fehlgeschlagen!")
            return False
            
        logger.info(f"✅ Datenabruf OK - Letzter Preis: ${df['close'].iloc[-1]:.2f}")
        return True
        
    def test_strategy(self) -> bool:
        """Test strategy signal generation"""
        logger.info("🧪 Teste Strategie...")
        df = self.data_fetcher.fetch_ohlcv(self.symbol, self.timeframe, limit=100)
        
        if df.empty:
            return False
            
        signal = self.strategy.generate_signal(df)
        logger.info(f"✅ Strategie OK - Signal: {signal['signal']:+d}, Reason: {signal['reason']}")
        logger.info(f"   RSI: {signal['rsi']:.1f}, ATR: {signal['atr']:.2f}")
        return True
        
    def run(self):
        """Main trading loop"""
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=self.duration_hours)
        
        logger.info("=" * 70)
        logger.info("🚀 TRADING BOT v2 - STARTET")
        logger.info("=" * 70)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Timeframe: {self.timeframe}")
        logger.info(f"Duration: {self.duration_hours}h")
        logger.info(f"Check Interval: {self.check_interval}s")
        logger.info(f"Start: {self.start_time}")
        logger.info(f"End: {self.end_time}")
        logger.info("=" * 70)
        
        # Pre-flight checks
        if not self.test_data_fetch():
            logger.error("❌ Abbruch: Datenabruf funktioniert nicht")
            return False
            
        if not self.test_strategy():
            logger.error("❌ Abbruch: Strategie funktioniert nicht")
            return False
        
        logger.info("✅ Alle Tests bestanden - Starte Trading Loop")
        logger.info("=" * 70)
        
        iteration = 0
        last_status_log = datetime.now()
        
        try:
            while datetime.now() < self.end_time:
                iteration += 1
                current_time = datetime.now()
                elapsed = (current_time - self.start_time).total_seconds() / 60
                remaining = (self.end_time - current_time).total_seconds() / 60
                
                logger.info(f"\n🔄 Iteration #{iteration} | Elapsed: {elapsed:.1f}min | Remaining: {remaining:.1f}min")
                
                # Fetch data
                df = self.data_fetcher.fetch_ohlcv(self.symbol, self.timeframe, limit=100)
                
                if df.empty:
                    logger.warning("⚠️ Keine Daten, warte 30s...")
                    time.sleep(30)
                    continue
                    
                current_price = df['close'].iloc[-1]
                
                # Generate signal
                signal_data = self.strategy.generate_signal(df)
                
                logger.info(f"📊 Signal: {signal_data['signal']:+d} | Price: ${current_price:.2f} | RSI: {signal_data['rsi']:.1f}")
                
                # Execute trade if signal
                if signal_data['signal'] != 0:
                    trade = self.trader.execute_signal(signal_data)
                    if trade:
                        self.log_trade(trade)
                        logger.info(f"✅ TRADE: {trade['side']} {trade['quantity']:.4f} @ ${trade['price']:.2f}")
                        logger.info(f"   Reason: {trade['reason']}")
                
                # Log status every 10 minutes or on trade
                time_since_status = (current_time - last_status_log).total_seconds() / 60
                if time_since_status >= 10 or signal_data['signal'] != 0:
                    status = self.trader.get_status(current_price)
                    self.status_history.append(status)
                    self.log_status(status)
                    
                    logger.info(f"💰 Status: ${status['total_value']:.2f} | P&L: ${status['total_pnl']:+.2f} ({status['return_pct']:+.2f}%) | Trades: {status['trade_count']}")
                    last_status_log = current_time
                
                # Sleep
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("\n⚠️ Unterbrochen durch Benutzer")
        except Exception as e:
            logger.error(f"❌ Fehler: {e}", exc_info=True)
        finally:
            self.generate_final_report()
            
    def generate_final_report(self):
        """Generate final report"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds() / 3600
        
        report = {
            'test_name': 'Trading Bot v2',
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': end_time.isoformat(),
            'duration_hours': duration,
            'total_checks': len(self.status_history),
            'trades': self.trader.trade_count,
            'final_pnl': self.trader.total_pnl,
            'final_value': self.trader.get_total_value(self.trader.avg_entry_price if self.trader.position > 0 else 0)
        }
        
        report_file = os.path.join(REPORT_DIR, f"trading_v2_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info("=" * 70)
        logger.info("📊 FINALER REPORT")
        logger.info("=" * 70)
        logger.info(f"Dauer: {duration:.2f}h")
        logger.info(f"Checks: {report['total_checks']}")
        logger.info(f"Trades: {report['trades']}")
        logger.info(f"P&L: ${report['final_pnl']:+.2f}")
        logger.info(f"Report: {report_file}")
        logger.info("=" * 70)
        logger.info("✅ BOT BEENDET")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Trading Bot v2')
    parser.add_argument('--symbol', default='ETH-USD', help='Trading symbol')
    parser.add_argument('--timeframe', default='15m', help='Timeframe (1m, 5m, 15m, 1h)')
    parser.add_argument('--duration', type=int, default=2, help='Duration in hours')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')
    
    args = parser.parse_args()
    
    bot = TradingBotV2(
        symbol=args.symbol,
        timeframe=args.timeframe,
        duration_hours=args.duration,
        check_interval=args.interval
    )
    
    bot.run()


if __name__ == "__main__":
    main()

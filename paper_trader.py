"""
Paper Trading Module - Simulated trading with virtual portfolio
Stores trades in SQLite database for persistence
"""
import os
import sys
import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies import BaseStrategy, MeanReversionStrategy, MomentumBreakoutStrategy, RangeScalperStrategy
from risk_management import PositionSizer, StopLossManager, PortfolioRiskManager, RiskParams, RiskCalculator


@dataclass
class Trade:
    """Represents a single trade."""
    id: Optional[int] = None
    timestamp: str = ""
    symbol: str = ""
    side: str = ""  # 'buy' or 'sell'
    quantity: float = 0.0
    price: float = 0.0
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    commission: float = 0.0
    notes: str = ""
    
    def to_dict(self) -> Dict:
        """Convert trade to dictionary."""
        return asdict(self)


@dataclass
class Position:
    """Represents current position in a symbol."""
    symbol: str = ""
    quantity: float = 0.0
    avg_entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    market_value: float = 0.0
    
    def update_price(self, price: float):
        """Update position with current price."""
        self.current_price = price
        self.market_value = self.quantity * price
        cost_basis = self.quantity * self.avg_entry_price
        self.unrealized_pnl = self.market_value - cost_basis
        if cost_basis > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl / cost_basis) * 100


class PaperTrader:
    """
    Paper trading simulator with virtual portfolio.
    
    Features:
    - Virtual balance tracking
    - Position management
    - Trade logging to SQLite
    - P&L calculation
    - Real-time portfolio updates
    """
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 commission: float = 0.001,
                 db_path: str = "data/paper_trades.db",
                 use_risk_management: bool = True,
                 max_position_pct: float = 0.2,
                 stop_loss_pct: float = 0.02,
                 trailing_stop_pct: float = 0.03,
                 take_profit_pct: float = 0.05):
        """
        Initialize paper trader.
        
        Args:
            initial_capital (float): Starting virtual balance
            commission (float): Commission rate per trade
            db_path (str): Path to SQLite database
            use_risk_management (bool): Enable risk management
            max_position_pct (float): Max position size as % of portfolio
            stop_loss_pct (float): Stop loss percentage
            trailing_stop_pct (float): Trailing stop percentage
            take_profit_pct (float): Take profit percentage
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Portfolio state
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Trade] = []
        
        # Risk management
        self.use_risk_management = use_risk_management
        if use_risk_management:
            risk_params = RiskParams(
                max_position_pct=max_position_pct,
                stop_loss_pct=stop_loss_pct,
                trailing_stop_pct=trailing_stop_pct,
                take_profit_pct=take_profit_pct
            )
            self.position_sizer = PositionSizer(risk_params)
            self.stop_manager = StopLossManager(risk_params)
            self.portfolio_risk = PortfolioRiskManager(risk_params)
        else:
            self.position_sizer = None
            self.stop_manager = None
            self.portfolio_risk = None
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        self.logger.info(f"Paper trader initialized with ${initial_capital:,.2f}")
    
    def _init_db(self):
        """Initialize SQLite database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                pnl REAL,
                pnl_pct REAL,
                commission REAL NOT NULL,
                notes TEXT
            )
        ''')
        
        # Portfolio snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cash REAL NOT NULL,
                total_value REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                positions TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        self.logger.info(f"Database initialized at {self.db_path}")
    
    def _save_trade_to_db(self, trade: Trade):
        """Save trade to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades (timestamp, symbol, side, quantity, price, pnl, pnl_pct, commission, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.timestamp, trade.symbol, trade.side, trade.quantity,
            trade.price, trade.pnl, trade.pnl_pct, trade.commission, trade.notes
        ))
        
        conn.commit()
        conn.close()
    
    def _save_portfolio_snapshot(self):
        """Save current portfolio state to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        total_value = self.get_portfolio_value()
        unrealized_pnl = self.get_unrealized_pnl()
        positions_json = json.dumps({
            symbol: {
                'quantity': pos.quantity,
                'avg_entry_price': pos.avg_entry_price,
                'current_price': pos.current_price
            }
            for symbol, pos in self.positions.items() if pos.quantity > 0
        })
        
        cursor.execute('''
            INSERT INTO portfolio_snapshots (timestamp, cash, total_value, unrealized_pnl, positions)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), self.cash, total_value, unrealized_pnl, positions_json))
        
        conn.commit()
        conn.close()
    
    def buy(self, symbol: str, price: float, quantity: Optional[float] = None, 
            position_pct: float = 0.95, notes: str = "") -> Optional[Trade]:
        """
        Execute buy order.
        
        Args:
            symbol (str): Trading symbol
            price (float): Current price
            quantity (float): Number of shares (optional)
            position_pct (float): Percentage of cash to use if quantity not specified
            notes (str): Optional notes for the trade
        
        Returns:
            Trade: Trade record or None if failed
        """
        if quantity is None:
            # Calculate quantity based on position_pct of available cash
            max_position_value = self.cash * position_pct
            quantity = max_position_value / price
        
        total_cost = quantity * price
        commission_amount = total_cost * self.commission
        total_cost_with_fees = total_cost + commission_amount
        
        # Check if we have enough cash
        if total_cost_with_fees > self.cash:
            self.logger.warning(f"Insufficient funds for {symbol} purchase")
            return None
        
        # Execute trade
        self.cash -= total_cost_with_fees
        
        # Update position
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        
        position = self.positions[symbol]
        old_quantity = position.quantity
        position.quantity += quantity
        position.avg_entry_price = (
            (old_quantity * position.avg_entry_price + quantity * price) / position.quantity
        )
        position.current_price = price
        position.update_price(price)
        
        # Record trade
        trade = Trade(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            side='buy',
            quantity=quantity,
            price=price,
            commission=commission_amount,
            notes=notes
        )
        
        self.trade_history.append(trade)
        self._save_trade_to_db(trade)
        
        self.logger.info(f"BUY {quantity:.4f} {symbol} @ ${price:.2f} | Cash: ${self.cash:.2f}")
        
        return trade
    
    def sell(self, symbol: str, price: float, quantity: Optional[float] = None,
             notes: str = "") -> Optional[Trade]:
        """
        Execute sell order.
        
        Args:
            symbol (str): Trading symbol
            price (float): Current price
            quantity (float): Number of shares (optional, sells all if None)
            notes (str): Optional notes for the trade
        
        Returns:
            Trade: Trade record or None if failed
        """
        if symbol not in self.positions or self.positions[symbol].quantity == 0:
            self.logger.warning(f"No position in {symbol} to sell")
            return None
        
        position = self.positions[symbol]
        
        if quantity is None or quantity >= position.quantity:
            quantity = position.quantity
        
        sell_value = quantity * price
        commission_amount = sell_value * self.commission
        net_proceeds = sell_value - commission_amount
        
        # Calculate P&L
        cost_basis = quantity * position.avg_entry_price
        realized_pnl = net_proceeds - cost_basis
        realized_pnl_pct = (realized_pnl / cost_basis) * 100 if cost_basis > 0 else 0
        
        # Execute trade
        self.cash += net_proceeds
        position.quantity -= quantity
        
        if position.quantity == 0:
            position.avg_entry_price = 0
        
        # Record trade
        trade = Trade(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            side='sell',
            quantity=quantity,
            price=price,
            pnl=realized_pnl,
            pnl_pct=realized_pnl_pct,
            commission=commission_amount,
            notes=notes
        )
        
        self.trade_history.append(trade)
        self._save_trade_to_db(trade)
        
        self.logger.info(f"SELL {quantity:.4f} {symbol} @ ${price:.2f} | P&L: ${realized_pnl:+.2f} | Cash: ${self.cash:.2f}")
        
        return trade
    
    def buy_with_atr(self, symbol: str, price: float, atr: float,
                     position_pct: float = 0.95, notes: str = "") -> Optional[Trade]:
        """
        Execute buy order with ATR-based position sizing.
        
        Args:
            symbol (str): Trading symbol
            price (float): Current price
            atr (float): Average True Range
            position_pct (float): Position percentage
            notes (str): Trade notes
            
        Returns:
            Trade: Trade record or None
        """
        if self.position_sizer:
            quantity = self.position_sizer.atr_based_sizing(
                self.cash, price, atr, risk_per_trade_pct=0.01
            )
        else:
            max_position_value = self.cash * position_pct
            quantity = max_position_value / price
        
        trade = self.buy(symbol, price, quantity, notes=notes)
        
        # Add to stop manager
        if trade and self.stop_manager:
            self.stop_manager.add_position(symbol, price, trade.quantity)
        
        return trade
    
    def check_stops(self, symbol: str, current_price: float) -> Optional[str]:
        """
        Check if stop loss or take profit triggered.
        
        Args:
            symbol (str): Trading symbol
            current_price (float): Current price
            
        Returns:
            str: Action to take or None
        """
        if not self.stop_manager:
            return None
        
        action = self.stop_manager.update_price(symbol, current_price)
        
        if action:
            notes = f"Stop triggered: {action}"
            self.sell(symbol, current_price, notes=notes)
            self.stop_manager.remove_position(symbol)
            return action
        
        return None
    
    def update_prices(self, prices: Dict[str, float]):
        """
        Update all positions with current prices and check stops.
        
        Args:
            prices (dict): Current prices by symbol
        """
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].update_price(price)
                self.check_stops(symbol, price)
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for symbol."""
        return self.positions.get(symbol)
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value (cash + positions)."""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value
    
    def get_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L."""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
    
    def get_total_pnl(self) -> float:
        """Calculate total P&L (realized + unrealized)."""
        realized_pnl = sum(t.pnl for t in self.trade_history if t.pnl is not None)
        return realized_pnl + self.get_unrealized_pnl()
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get complete portfolio summary."""
        total_value = self.get_portfolio_value()
        total_pnl = self.get_total_pnl()
        total_return_pct = (total_pnl / self.initial_capital) * 100
        
        return {
            'timestamp': datetime.now().isoformat(),
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'total_value': total_value,
            'total_pnl': total_pnl,
            'total_return_pct': total_return_pct,
            'positions': {
                symbol: {
                    'quantity': pos.quantity,
                    'avg_entry_price': pos.avg_entry_price,
                    'current_price': pos.current_price,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'unrealized_pnl_pct': pos.unrealized_pnl_pct
                }
                for symbol, pos in self.positions.items() if pos.quantity > 0
            },
            'trade_count': len(self.trade_history)
        }
    
    def execute_signal(self, symbol: str, signal: int, price: float, notes: str = "") -> Optional[Trade]:
        """
        Execute trade based on signal.
        
        Args:
            symbol (str): Trading symbol
            signal (int): 1 (buy), -1 (sell), 0 (hold)
            price (float): Current price
            notes (str): Optional notes
        
        Returns:
            Trade: Trade record or None
        """
        if signal == 1:
            # Buy signal - only buy if no position
            position = self.get_position(symbol)
            if position is None or position.quantity == 0:
                return self.buy(symbol, price, notes=notes)
        elif signal == -1:
            # Sell signal - only sell if we have position
            position = self.get_position(symbol)
            if position and position.quantity > 0:
                return self.sell(symbol, price, notes=notes)
        
        return None
    
    def get_trade_history(self, limit: int = 100) -> List[Trade]:
        """Get trade history from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, timestamp, symbol, side, quantity, price, pnl, pnl_pct, commission, notes
            FROM trades ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        
        trades = []
        for row in cursor.fetchall():
            trades.append(Trade(
                id=row[0], timestamp=row[1], symbol=row[2], side=row[3],
                quantity=row[4], price=row[5], pnl=row[6], pnl_pct=row[7],
                commission=row[8], notes=row[9]
            ))
        
        conn.close()
        return trades
    
    def print_portfolio(self):
        """Print portfolio summary to console."""
        summary = self.get_portfolio_summary()
        
        print("\n" + "="*60)
        print("📊 PAPER TRADING PORTFOLIO")
        print("="*60)
        print(f"💰 Cash:           ${summary['cash']:,.2f}")
        print(f"📈 Total Value:    ${summary['total_value']:,.2f}")
        print(f"💵 Initial:        ${summary['initial_capital']:,.2f}")
        print(f"📊 Total P&L:      ${summary['total_pnl']:+.2f} ({summary['total_return_pct']:+.2f}%)")
        print(f"🔄 Trades:         {summary['trade_count']}")
        
        if summary['positions']:
            print("\n📋 Positions:")
            for sym, pos in summary['positions'].items():
                print(f"  {sym}: {pos['quantity']:.4f} @ ${pos['avg_entry_price']:.2f} | "
                      f"Current: ${pos['current_price']:.2f} | "
                      f"P&L: ${pos['unrealized_pnl']:+.2f}")
        
        print("="*60)
    
    def save_summary(self, filepath: str):
        """Save portfolio summary to JSON."""
        summary = self.get_portfolio_summary()
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        self.logger.info(f"Portfolio summary saved to {filepath}")

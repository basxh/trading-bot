"""
Live Trading Module - Preparation for live trading with real broker APIs
Implements same interface as PaperTrader for easy switching
"""
import os
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any

from paper_trader import PaperTrader, Trade, Position


class BaseBroker(ABC):
    """
    Abstract base class for broker implementations.
    
    All broker integrations should inherit from this class
    and implement the required methods.
    """
    
    def __init__(self, api_key: str, api_secret: str, **kwargs):
        """
        Initialize broker connection.
        
        Args:
            api_key (str): API key
            api_secret (str): API secret
            **kwargs: Additional broker-specific parameters
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.config = kwargs
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to broker API."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from broker API."""
        pass
    
    @abstractmethod
    def get_account(self) -> Dict[str, Any]:
        """Get account information."""
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for symbol."""
        pass
    
    @abstractmethod
    def get_positions(self) -> Dict[str, Position]:
        """Get all current positions."""
        pass
    
    @abstractmethod
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Trade]:
        """
        Place market order.
        
        Args:
            symbol (str): Trading symbol
            side (str): 'buy' or 'sell'
            quantity (float): Order quantity
        
        Returns:
            Trade: Trade record or None if failed
        """
        pass
    
    @abstractmethod
    def place_limit_order(self, symbol: str, side: str, quantity: float, 
                          price: float) -> Optional[Trade]:
        """
        Place limit order.
        
        Args:
            symbol (str): Trading symbol
            side (str): 'buy' or 'sell'
            quantity (float): Order quantity
            price (float): Limit price
        
        Returns:
            Trade: Trade record or None if failed
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status."""
        pass


class AlpacaBroker(BaseBroker):
    """
    Alpaca Broker implementation.
    
    Supports both paper and live trading.
    Requires: pip install alpaca-trade-api
    """
    
    def __init__(self, api_key: str, api_secret: str, paper: bool = True, **kwargs):
        """
        Initialize Alpaca broker.
        
        Args:
            api_key (str): Alpaca API key
            api_secret (str): Alpaca API secret
            paper (bool): Use paper trading (True) or live (False)
        """
        super().__init__(api_key, api_secret, paper=paper, **kwargs)
        self.paper = paper
        self.client = None
        
        try:
            from alpaca_trade_api import REST
            self.REST = REST
        except ImportError:
            self.logger.error("alpaca-trade-api not installed. Run: pip install alpaca-trade-api")
            raise
    
    def connect(self) -> bool:
        """Connect to Alpaca API."""
        try:
            base_url = 'https://paper-api.alpaca.markets' if self.paper else 'https://api.alpaca.markets'
            self.client = self.REST(self.api_key, self.api_secret, base_url, raw_data=True)
            account = self.client.get_account()
            self.logger.info(f"Connected to Alpaca ({'paper' if self.paper else 'live'}). Account: {account['id']}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Alpaca: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Alpaca API."""
        self.client = None
        self.logger.info("Disconnected from Alpaca")
    
    def get_account(self) -> Dict[str, Any]:
        """Get Alpaca account information."""
        if not self.client:
            return {}
        try:
            account = self.client.get_account()
            return {
                'id': account['id'],
                'cash': float(account['cash']),
                'portfolio_value': float(account['portfolio_value']),
                'buying_power': float(account['buying_power']),
                'equity': float(account['equity']),
                'status': account['status']
            }
        except Exception as e:
            self.logger.error(f"Error getting account: {e}")
            return {}
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol."""
        if not self.client:
            return None
        try:
            pos = self.client.get_position(symbol)
            return Position(
                symbol=pos['symbol'],
                quantity=float(pos['qty']),
                avg_entry_price=float(pos['avg_entry_price']),
                current_price=float(pos['current_price']),
                unrealized_pnl=float(pos['unrealized_pl']),
                unrealized_pnl_pct=float(pos['unrealized_plpc']) * 100,
                market_value=float(pos['market_value'])
            )
        except Exception:
            return None
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all positions."""
        if not self.client:
            return {}
        try:
            positions = self.client.list_positions()
            return {
                pos['symbol']: Position(
                    symbol=pos['symbol'],
                    quantity=float(pos['qty']),
                    avg_entry_price=float(pos['avg_entry_price']),
                    current_price=float(pos['current_price']),
                    unrealized_pnl=float(pos['unrealized_pl']),
                    unrealized_pnl_pct=float(pos['unrealized_plpc']) * 100,
                    market_value=float(pos['market_value'])
                )
                for pos in positions
            }
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return {}
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Trade]:
        """Place market order on Alpaca."""
        if not self.client:
            return None
        try:
            side_map = {'buy': 'buy', 'sell': 'sell'}
            order = self.client.submit_order(
                symbol=symbol,
                qty=quantity,
                side=side_map.get(side.lower(), 'buy'),
                type='market',
                time_in_force='day'
            )
            
            return Trade(
                timestamp=datetime.now().isoformat(),
                symbol=symbol,
                side=side.lower(),
                quantity=quantity,
                price=0,  # Will be filled at market
                commission=0,
                notes=f"Market order submitted: {order['id']}"
            )
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
    
    def place_limit_order(self, symbol: str, side: str, quantity: float, 
                          price: float) -> Optional[Trade]:
        """Place limit order on Alpaca."""
        if not self.client:
            return None
        try:
            order = self.client.submit_order(
                symbol=symbol,
                qty=quantity,
                side=side.lower(),
                type='limit',
                limit_price=price,
                time_in_force='day'
            )
            
            return Trade(
                timestamp=datetime.now().isoformat(),
                symbol=symbol,
                side=side.lower(),
                quantity=quantity,
                price=price,
                commission=0,
                notes=f"Limit order submitted: {order['id']}"
            )
        except Exception as e:
            self.logger.error(f"Error placing limit order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if not self.client:
            return False
        try:
            self.client.cancel_order(order_id)
            return True
        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status."""
        if not self.client:
            return {}
        try:
            return self.client.get_order(order_id)
        except Exception as e:
            self.logger.error(f"Error getting order status: {e}")
            return {}


class BinanceBroker(BaseBroker):
    """
    Binance Broker implementation.
    
    Requires: pip install python-binance
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True, **kwargs):
        """
        Initialize Binance broker.
        
        Args:
            api_key (str): Binance API key
            api_secret (str): Binance API secret
            testnet (bool): Use testnet (True) or live (False)
        """
        super().__init__(api_key, api_secret, testnet=testnet, **kwargs)
        self.testnet = testnet
        self.client = None
        
        try:
            from binance.client import Client
            self.Client = Client
        except ImportError:
            self.logger.error("python-binance not installed. Run: pip install python-binance")
            raise
    
    def connect(self) -> bool:
        """Connect to Binance API."""
        try:
            self.client = self.Client(self.api_key, self.api_secret, testnet=self.testnet)
            account = self.client.get_account()
            self.logger.info(f"Connected to Binance ({'testnet' if self.testnet else 'live'})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Binance: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Binance API."""
        self.client = None
        self.logger.info("Disconnected from Binance")
    
    def get_account(self) -> Dict[str, Any]:
        """Get Binance account information."""
        if not self.client:
            return {}
        try:
            account = self.client.get_account()
            balances = [b for b in account['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]
            return {
                'balances': balances,
                'maker_commission': account['makerCommission'],
                'taker_commission': account['takerCommission']
            }
        except Exception as e:
            self.logger.error(f"Error getting account: {e}")
            return {}
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol."""
        # Binance doesn't have a direct position endpoint like Alpaca
        # You'd need to track this yourself or use margin/futures
        self.logger.warning("get_position not implemented for spot trading on Binance")
        return None
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all positions."""
        self.logger.warning("get_positions not implemented for spot trading on Binance")
        return {}
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Trade]:
        """Place market order on Binance."""
        if not self.client:
            return None
        try:
            order = self.client.order_market_buy(
                symbol=symbol.upper(),
                quantity=quantity
            ) if side.lower() == 'buy' else self.client.order_market_sell(
                symbol=symbol.upper(),
                quantity=quantity
            )
            
            return Trade(
                timestamp=datetime.now().isoformat(),
                symbol=symbol,
                side=side.lower(),
                quantity=quantity,
                price=float(order.get('fills', [{}])[0].get('price', 0)),
                commission=float(order.get('fills', [{}])[0].get('commission', 0)),
                notes=f"Order ID: {order['orderId']}"
            )
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
    
    def place_limit_order(self, symbol: str, side: str, quantity: float, 
                          price: float) -> Optional[Trade]:
        """Place limit order on Binance."""
        if not self.client:
            return None
        try:
            order = self.client.order_limit_buy(
                symbol=symbol.upper(),
                quantity=quantity,
                price=str(price)
            ) if side.lower() == 'buy' else self.client.order_limit_sell(
                symbol=symbol.upper(),
                quantity=quantity,
                price=str(price)
            )
            
            return Trade(
                timestamp=datetime.now().isoformat(),
                symbol=symbol,
                side=side.lower(),
                quantity=quantity,
                price=price,
                commission=0,
                notes=f"Limit Order ID: {order['orderId']}"
            )
        except Exception as e:
            self.logger.error(f"Error placing limit order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        self.logger.warning("cancel_order requires symbol parameter for Binance")
        return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status."""
        self.logger.warning("get_order_status requires symbol parameter for Binance")
        return {}


class LiveTrader:
    """
    Live Trading wrapper with safety checks.
    
    Provides same interface as PaperTrader but for live trading.
    Includes safety checks to prevent catastrophic losses.
    """
    
    def __init__(self, 
                 broker: str = 'alpaca',
                 api_key: str = '',
                 api_secret: str = '',
                 paper: bool = True,
                 max_position_size: float = 0.2,
                 max_daily_loss: float = 500.0,
                 stop_loss_pct: float = 0.02):
        """
        Initialize live trader.
        
        Args:
            broker (str): 'alpaca' or 'binance'
            api_key (str): API key
            api_secret (str): API secret
            paper (bool): Use paper trading mode
            max_position_size (float): Max position size as % of portfolio
            max_daily_loss (float): Max daily loss in base currency
            stop_loss_pct (float): Stop loss percentage
        """
        self.logger = logging.getLogger(__name__)
        
        # Safety settings
        self.max_position_size = max_position_size
        self.max_daily_loss = max_daily_loss
        self.stop_loss_pct = stop_loss_pct
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        
        # Initialize broker
        if broker.lower() == 'alpaca':
            self.broker = AlpacaBroker(api_key, api_secret, paper=paper)
        elif broker.lower() == 'binance':
            self.broker = BinanceBroker(api_key, api_secret, testnet=paper)
        else:
            raise ValueError(f"Unknown broker: {broker}")
        
        # Connect to broker
        if not self.broker.connect():
            raise ConnectionError(f"Failed to connect to {broker}")
        
        self.logger.info(f"Live trader initialized with {broker}")
    
    def _check_safety_limits(self, side: str, symbol: str, quantity: float, price: float) -> bool:
        """
        Check if trade passes safety limits.
        
        Args:
            side (str): 'buy' or 'sell'
            symbol (str): Trading symbol
            quantity (float): Trade quantity
            price (float): Current price
        
        Returns:
            bool: True if trade is safe, False otherwise
        """
        # Reset daily P&L if new day
        if datetime.now().date() != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = datetime.now().date()
        
        # Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            self.logger.error(f"DAILY LOSS LIMIT REACHED: ${abs(self.daily_pnl):.2f}")
            return False
        
        # Check position size limit
        if side == 'buy':
            account = self.broker.get_account()
            if account:
                portfolio_value = account.get('portfolio_value', account.get('equity', 0))
                position_value = quantity * price
                
                if portfolio_value > 0 and position_value / portfolio_value > self.max_position_size:
                    self.logger.error(f"MAX POSITION SIZE EXCEEDED: {position_value / portfolio_value:.2%}")
                    return False
        
        self.logger.info("Safety checks passed")
        return True
    
    def buy(self, symbol: str, price: float, quantity: Optional[float] = None,
            position_pct: float = 0.95, notes: str = "") -> Optional[Trade]:
        """
        Execute buy order with safety checks.
        
        Args:
            symbol (str): Trading symbol
            price (float): Current price
            quantity (float): Quantity to buy
            position_pct (float): Percentage of available cash to use
            notes (str): Trade notes
        
        Returns:
            Trade: Trade record or None
        """
        if quantity is None:
            account = self.broker.get_account()
            if account:
                cash = account.get('cash', 0)
                quantity = (cash * position_pct) / price
        
        if not self._check_safety_limits('buy', symbol, quantity, price):
            return None
        
        trade = self.broker.place_market_order(symbol, 'buy', quantity)
        
        if trade:
            self.logger.info(f"LIVE BUY EXECUTED: {quantity:.4f} {symbol} @ ${price:.2f}")
        
        return trade
    
    def sell(self, symbol: str, price: float, quantity: Optional[float] = None,
             notes: str = "") -> Optional[Trade]:
        """
        Execute sell order.
        
        Args:
            symbol (str): Trading symbol
            price (float): Current price
            quantity (float): Quantity to sell
            notes (str): Trade notes
        
        Returns:
            Trade: Trade record or None
        """
        if quantity is None:
            position = self.broker.get_position(symbol)
            if position:
                quantity = position.quantity
        
        trade = self.broker.place_market_order(symbol, 'sell', quantity)
        
        if trade:
            self.logger.info(f"LIVE SELL EXECUTED: {quantity:.4f} {symbol} @ ${price:.2f}")
        
        return trade
    
    def get_portfolio_value(self) -> float:
        """Get current portfolio value."""
        account = self.broker.get_account()
        if account:
            return account.get('portfolio_value', account.get('equity', 0))
        return 0.0
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol."""
        return self.broker.get_position(symbol)
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all positions."""
        return self.broker.get_positions()
    
    def execute_signal(self, symbol: str, signal: int, price: float, notes: str = "") -> Optional[Trade]:
        """
        Execute trade based on signal.
        
        Args:
            symbol (str): Trading symbol
            signal (int): 1 (buy), -1 (sell), 0 (hold)
            price (float): Current price
            notes (str): Trade notes
        
        Returns:
            Trade: Trade record or None
        """
        if signal == 1:
            position = self.get_position(symbol)
            if position is None or position.quantity == 0:
                return self.buy(symbol, price, notes=f"Signal: BUY - {notes}")
        elif signal == -1:
            position = self.get_position(symbol)
            if position and position.quantity > 0:
                return self.sell(symbol, price, notes=f"Signal: SELL - {notes}")
        
        return None
    
    def disconnect(self):
        """Disconnect from broker."""
        if self.broker:
            self.broker.disconnect()

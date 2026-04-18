"""
Risk Management Module
Advanced risk management utilities for trading
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RiskParams:
    """Risk management parameters."""
    max_position_pct: float = 0.2  # Max position size as % of portfolio
    stop_loss_pct: float = 0.02    # Default stop loss %
    take_profit_pct: float = 0.05  # Default take profit %
    trailing_stop_pct: float = 0.03  # Trailing stop %
    max_daily_loss: float = 500.0   # Max daily loss in base currency
    max_drawdown_pct: float = 0.10  # Max portfolio drawdown %
    kelly_fraction: float = 0.5     # Kelly criterion fraction (0.5 = half Kelly)


class PositionSizer:
    """
    Position sizing calculators.
    
    Supports multiple position sizing methods:
    - Fixed percentage
    - ATR-based volatility sizing
    - Kelly Criterion
    - Risk-parity
    """
    
    def __init__(self, risk_params: RiskParams = None):
        """
        Initialize position sizer.
        
        Args:
            risk_params (RiskParams): Risk parameters
        """
        self.risk_params = risk_params or RiskParams()
    
    def fixed_fraction(self, 
                       capital: float,
                       price: float,
                       fraction: float = 0.1) -> float:
        """
        Fixed fraction of capital.
        
        Args:
            capital (float): Available capital
            price (float): Current price
            fraction (float): Fraction of capital to use
            
        Returns:
            float: Number of shares
        """
        position_value = capital * min(fraction, self.risk_params.max_position_pct)
        return position_value / price
    
    def atr_based_sizing(self,
                        capital: float,
                        price: float,
                        atr: float,
                        risk_per_trade_pct: float = 0.01) -> float:
        """
        Position sizing based on ATR (Average True Range).
        
        Risk a fixed percentage of capital per trade based on volatility.
        
        Args:
            capital (float): Available capital
            price (float): Current price
            atr (float): Average True Range
            risk_per_trade_pct (float): Risk per trade as % of capital
            
        Returns:
            float: Number of shares
        """
        # Risk amount
        risk_amount = capital * risk_per_trade_pct
        
        # Distance to stop (2x ATR)
        stop_distance = 2 * atr
        
        # Position size
        position_size = risk_amount / stop_distance if stop_distance > 0 else 0
        
        # Limit to max position
        max_position_value = capital * self.risk_params.max_position_pct
        max_shares = max_position_value / price
        
        return min(position_size, max_shares)
    
    def kelly_criterion(self,
                        capital: float,
                        price: float,
                        win_rate: float,
                        avg_win: float,
                        avg_loss: float) -> float:
        """
        Kelly Criterion position sizing.
        
        Optimal bet size based on edge.
        
        Args:
            capital (float): Available capital
            price (float): Current price
            win_rate (float): Probability of winning (0-1)
            avg_win (float): Average win amount
            avg_loss (float): Average loss amount (positive number)
            
        Returns:
            float: Number of shares
        """
        if avg_loss == 0:
            return 0
        
        # Kelly fraction
        win_loss_ratio = avg_win / avg_loss
        kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio)
        
        # Use fractional Kelly
        kelly_pct = kelly_pct * self.risk_params.kelly_fraction
        
        # Kelly can be negative if no edge
        if kelly_pct <= 0:
            return 0
        
        position_value = capital * kelly_pct
        max_position_value = capital * self.risk_params.max_position_pct
        
        position_value = min(position_value, max_position_value)
        
        return position_value / price


class StopLossManager:
    """
    Stop loss and trailing stop management.
    """
    
    def __init__(self, risk_params: RiskParams = None):
        """
        Initialize stop loss manager.
        
        Args:
            risk_params (RiskParams): Risk parameters
        """
        self.risk_params = risk_params or RiskParams()
        self.positions: Dict[str, Dict] = {}
    
    def add_position(self,
                     symbol: str,
                     entry_price: float,
                     quantity: float,
                     stop_loss_pct: float = None,
                     trailing_stop_pct: float = None,
                     take_profit_pct: float = None):
        """
        Add a new position with stop management.
        
        Args:
            symbol (str): Trading symbol
            entry_price (float): Entry price
            quantity (float): Number of shares
            stop_loss_pct (float): Stop loss percentage
            trailing_stop_pct (float): Trailing stop percentage
            take_profit_pct (float): Take profit percentage
        """
        sl_pct = stop_loss_pct or self.risk_params.stop_loss_pct
        tp_pct = take_profit_pct or self.risk_params.take_profit_pct
        ts_pct = trailing_stop_pct or self.risk_params.trailing_stop_pct
        
        self.positions[symbol] = {
            'entry_price': entry_price,
            'quantity': quantity,
            'highest_price': entry_price,
            'lowest_price': entry_price,
            'stop_loss': entry_price * (1 - sl_pct),
            'take_profit': entry_price * (1 + tp_pct),
            'trailing_stop': entry_price * (1 - ts_pct),
            'trailing_stop_pct': ts_pct
        }
    
    def update_price(self, symbol: str, current_price: float) -> Optional[str]:
        """
        Update position with current price and check stops.
        
        Args:
            symbol (str): Trading symbol
            current_price (float): Current price
            
        Returns:
            str: Action to take ('sell', 'sell_trailing', 'sell_profit') or None
        """
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        
        # Update highest/lowest price
        if current_price > pos['highest_price']:
            pos['highest_price'] = current_price
            # Update trailing stop
            pos['trailing_stop'] = current_price * (1 - pos['trailing_stop_pct'])
        
        if current_price < pos['lowest_price']:
            pos['lowest_price'] = current_price
        
        # Check stop loss
        if current_price <= pos['stop_loss']:
            return 'sell'
        
        # Check trailing stop
        if current_price <= pos['trailing_stop']:
            return 'sell_trailing'
        
        # Check take profit
        if current_price >= pos['take_profit']:
            return 'sell_profit'
        
        return None
    
    def remove_position(self, symbol: str):
        """Remove a position."""
        if symbol in self.positions:
            del self.positions[symbol]
    
    def get_position_info(self, symbol: str) -> Optional[Dict]:
        """Get position information."""
        return self.positions.get(symbol)
    
    def calculate_r_multiple(self, symbol: str, exit_price: float) -> float:
        """
        Calculate R-multiple for a trade.
        
        R = (Exit - Entry) / (Entry - Stop)
        
        Args:
            symbol (str): Trading symbol
            exit_price (float): Exit price
            
        Returns:
            float: R-multiple
        """
        if symbol not in self.positions:
            return 0
        
        pos = self.positions[symbol]
        entry = pos['entry_price']
        stop = pos['stop_loss']
        
        risk = entry - stop
        profit = exit_price - entry
        
        return profit / risk if risk != 0 else 0


class PortfolioRiskManager:
    """
    Portfolio-level risk management.
    """
    
    def __init__(self, risk_params: RiskParams = None):
        """
        Initialize portfolio risk manager.
        
        Args:
            risk_params (RiskParams): Risk parameters
        """
        self.risk_params = risk_params or RiskParams()
        self.daily_pnl = 0.0
        self.peak_value = 0.0
        self.current_drawdown = 0.0
    
    def check_daily_limit(self, pnl: float) -> bool:
        """
        Check if daily loss limit is exceeded.
        
        Args:
            pnl (float): Current daily P&L
            
        Returns:
            bool: True if trading should continue
        """
        self.daily_pnl = pnl
        return self.daily_pnl > -self.risk_params.max_daily_loss
    
    def check_drawdown(self, portfolio_value: float) -> bool:
        """
        Check if drawdown limit is exceeded.
        
        Args:
            portfolio_value (float): Current portfolio value
            
        Returns:
            bool: True if trading should continue
        """
        # Update peak
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
        
        # Calculate drawdown
        if self.peak_value > 0:
            self.current_drawdown = (portfolio_value - self.peak_value) / self.peak_value
        
        return self.current_drawdown > -self.risk_params.max_drawdown_pct
    
    def calculate_correlation_risk(self, returns_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate correlation risk for portfolio.
        
        Args:
            returns_df (pd.DataFrame): Returns for each symbol
            
        Returns:
            dict: Risk metrics
        """
        # Correlation matrix
        corr = returns_df.corr()
        
        # Average correlation
        avg_corr = corr.mean().mean()
        
        # Portfolio concentration risk
        concentration = (returns_df.var(axis=1).mean()) / (returns_df.mean(axis=1).var() + 1e-10)
        
        return {
            'average_correlation': avg_corr,
            'concentration_risk': concentration,
            'diversification_score': 1 - avg_corr
        }
    
    def calculate_position_risk(self,
                               positions: Dict[str, Dict],
                               current_prices: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate risk for each position.
        
        Args:
            positions (dict): Position data
            current_prices (dict): Current prices
            
        Returns:
            dict: Risk metrics per position
        """
        position_risks = {}
        
        for symbol, pos in positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                entry_price = pos.get('avg_entry_price', current_price)
                quantity = pos.get('quantity', 0)
                
                market_value = quantity * current_price
                unrealized_pnl = quantity * (current_price - entry_price)
                pnl_pct = ((current_price / entry_price) - 1) * 100 if entry_price > 0 else 0
                
                position_risks[symbol] = {
                    'market_value': market_value,
                    'unrealized_pnl': unrealized_pnl,
                    'unrealized_pnl_pct': pnl_pct,
                    'distance_to_stop': self.risk_params.stop_loss_pct * 100
                }
        
        return position_risks


class RiskCalculator:
    """
    Various risk calculations.
    """
    
    @staticmethod
    def calculate_var(returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Calculate Value at Risk.
        
        Args:
            returns (pd.Series): Return series
            confidence (float): Confidence level
            
        Returns:
            float: VaR as percentage
        """
        return np.percentile(returns.dropna(), (1 - confidence) * 100) * 100
    
    @staticmethod
    def calculate_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall).
        
        Args:
            returns (pd.Series): Return series
            confidence (float): Confidence level
            
        Returns:
            float: CVaR as percentage
        """
        var = RiskCalculator.calculate_var(returns, confidence) / 100
        return returns[returns <= var].mean() * 100
    
    @staticmethod
    def calculate_max_drawdown(equity_curve: pd.Series) -> Tuple[float, pd.Series]:
        """
        Calculate maximum drawdown.
        
        Args:
            equity_curve (pd.Series): Equity curve
            
        Returns:
            tuple: (max_drawdown, drawdown_series)
        """
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        return max_drawdown, drawdown
    
    @staticmethod
    def calculate_beta(returns: pd.Series, market_returns: pd.Series) -> float:
        """
        Calculate beta relative to market.
        
        Args:
            returns (pd.Series): Strategy returns
            market_returns (pd.Series): Market returns
            
        Returns:
            float: Beta
        """
        covariance = returns.cov(market_returns)
        market_variance = market_returns.var()
        
        return covariance / market_variance if market_variance > 0 else 0
    
    @staticmethod
    def calculate_alpha(returns: pd.Series,
                       market_returns: pd.Series,
                       risk_free_rate: float = 0.02) -> float:
        """
        Calculate alpha (excess return).
        
        Args:
            returns (pd.Series): Strategy returns
            market_returns (pd.Series): Market returns
            risk_free_rate (float): Risk-free rate
            
        Returns:
            float: Alpha (annualized)
        """
        beta = RiskCalculator.calculate_beta(returns, market_returns)
        
        avg_return = returns.mean() * 252
        avg_market = market_returns.mean() * 252
        
        alpha = avg_return - (risk_free_rate + beta * (avg_market - risk_free_rate))
        
        return alpha


# Convenience function to create risk manager with default settings
def create_risk_manager(max_position_pct: float = 0.2,
                        stop_loss_pct: float = 0.02,
                        max_daily_loss: float = 500.0) -> Tuple[PositionSizer, StopLossManager, PortfolioRiskManager]:
    """
    Create complete risk management suite.
    
    Args:
        max_position_pct (float): Max position size
        stop_loss_pct (float): Stop loss percentage
        max_daily_loss (float): Max daily loss
        
    Returns:
        tuple: (PositionSizer, StopLossManager, PortfolioRiskManager)
    """
    params = RiskParams(
        max_position_pct=max_position_pct,
        stop_loss_pct=stop_loss_pct,
        max_daily_loss=max_daily_loss
    )
    
    return (
        PositionSizer(params),
        StopLossManager(params),
        PortfolioRiskManager(params)
    )

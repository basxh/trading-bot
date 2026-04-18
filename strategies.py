"""
Strategies Module - Contains base class and trading strategies
"""
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.
    
    All new strategies should inherit from this class
    and implement generate_signals() method.
    """
    
    def __init__(self, params=None):
        """
        Initialize strategy with parameters.
        
        Args:
            params (dict): Strategy-specific parameters
        """
        self.params = params or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals from market data.
        
        Args:
            data (pd.DataFrame): OHLCV data with columns:
                - open, high, low, close, volume
        
        Returns:
            pd.DataFrame: Original data with added columns:
                - signal: 1 (buy), -1 (sell), 0 (hold)
                - position: cumulative position (1 long, -1 short, 0 flat)
        """
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate that data has required columns."""
        required = ['open', 'high', 'low', 'close', 'volume']
        return all(col in data.columns for col in required)


class SMA_Crossover_Strategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy.
    
    Buy when short SMA crosses above long SMA (golden cross).
    Sell when short SMA crosses below long SMA (death cross).
    """
    
    def __init__(self, params=None):
        """
        Initialize SMA Crossover strategy.
        
        Args:
            params (dict): Must contain 'sma_short' and 'sma_long'
        """
        default_params = {
            'sma_short': 50,
            'sma_long': 200
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate SMA crossover signals."""
        if not self.validate_data(data):
            raise ValueError("Data missing required OHLCV columns")
        
        df = data.copy()
        short_period = self.params['sma_short']
        long_period = self.params['sma_long']
        
        # Calculate SMAs
        df['sma_short'] = df['close'].rolling(window=short_period).mean()
        df['sma_long'] = df['close'].rolling(window=long_period).mean()
        
        # Generate signals
        df['signal'] = 0
        df['position'] = 0
        
        # Buy signal: short SMA crosses above long SMA
        df.loc[df['sma_short'] > df['sma_long'], 'signal'] = 1
        
        # Sell signal: short SMA crosses below long SMA  
        df.loc[df['sma_short'] < df['sma_long'], 'signal'] = -1
        
        # Calculate position changes (entries/exits)
        df['position'] = df['signal'].diff().fillna(0)
        
        # Clean up NaN values from SMA calculation
        df['signal'] = df['signal'].fillna(0)
        
        return df


class RSI_Strategy(BaseStrategy):
    """
    RSI Overbought/Oversold Strategy.
    
    Buy when RSI falls below oversold level (oversold, expecting bounce).
    Sell when RSI rises above overbought level (overbought, expecting pullback).
    """
    
    def __init__(self, params=None):
        """
        Initialize RSI strategy.
        
        Args:
            params (dict): Contains 'rsi_period', 'rsi_overbought', 'rsi_oversold'
        """
        default_params = {
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate average gains and losses
        avg_gains = gains.rolling(window=period).mean()
        avg_losses = losses.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate RSI overbought/oversold signals."""
        if not self.validate_data(data):
            raise ValueError("Data missing required OHLCV columns")
        
        df = data.copy()
        period = self.params['rsi_period']
        overbought = self.params['rsi_overbought']
        oversold = self.params['rsi_oversold']
        
        # Calculate RSI
        df['rsi'] = self._calculate_rsi(df['close'], period)
        
        # Generate signals
        df['signal'] = 0
        
        # Buy signal: RSI below oversold threshold
        df.loc[df['rsi'] < oversold, 'signal'] = 1
        
        # Sell signal: RSI above overbought threshold
        df.loc[df['rsi'] > overbought, 'signal'] = -1
        
        # Calculate position changes
        df['position'] = df['signal'].diff().fillna(0)
        
        # Clean up NaN values
        df['signal'] = df['signal'].fillna(0)
        
        return df


class Combined_Strategy(BaseStrategy):
    """
    Combined Strategy - Uses multiple indicators together.
    
    Example: SMA crossover + RSI confirmation
    """
    
    def __init__(self, params=None):
        """Initialize combined strategy."""
        default_params = {
            'sma_short': 50,
            'sma_long': 200,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate combined signals."""
        # Calculate SMAs
        df = data.copy()
        short_period = self.params['sma_short']
        long_period = self.params['sma_long']
        
        df['sma_short'] = df['close'].rolling(window=short_period).mean()
        df['sma_long'] = df['close'].rolling(window=long_period).mean()
        
        # Calculate RSI
        delta = df['close'].diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        avg_gains = gains.rolling(window=self.params['rsi_period']).mean()
        avg_losses = losses.rolling(window=self.params['rsi_period']).mean()
        rs = avg_gains / avg_losses
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Combined logic: SMA crossover + RSI confirmation
        df['signal'] = 0
        
        # Buy: Golden cross + RSI not overbought
        golden_cross = (df['sma_short'] > df['sma_long']) & \
                       (df['sma_short'].shift(1) <= df['sma_long'].shift(1))
        df.loc[golden_cross & (df['rsi'] < self.params['rsi_overbought']), 'signal'] = 1
        
        # Sell: Death cross + RSI not oversold
        death_cross = (df['sma_short'] < df['sma_long']) & \
                      (df['sma_short'].shift(1) >= df['sma_long'].shift(1))
        df.loc[death_cross & (df['rsi'] > self.params['rsi_oversold']), 'signal'] = -1
        
        df['position'] = df['signal'].diff().fillna(0)
        
        return df


# Strategy registry for easy access
STRATEGIES = {
    'sma_crossover': SMA_Crossover_Strategy,
    'rsi': RSI_Strategy,
    'combined': Combined_Strategy
}


def get_strategy(name: str, params: dict = None) -> BaseStrategy:
    """
    Factory function to get strategy by name.
    
    Args:
        name (str): Strategy name from STRATEGIES registry
        params (dict): Strategy parameters
    
    Returns:
        BaseStrategy: Instantiated strategy
    """
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    
    return STRATEGIES[name](params)

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


class MACD_Strategy(BaseStrategy):
    """
    MACD (Moving Average Convergence Divergence) Strategy.
    
    Buy when MACD line crosses above Signal line.
    Sell when MACD line crosses below Signal line.
    """
    
    def __init__(self, params=None):
        """
        Initialize MACD strategy.
        
        Args:
            params (dict): Contains 'fast', 'slow', 'signal' periods
        """
        default_params = {
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate MACD crossover signals."""
        if not self.validate_data(data):
            raise ValueError("Data missing required OHLCV columns")
        
        df = data.copy()
        fast = self.params['macd_fast']
        slow = self.params['macd_slow']
        signal_period = self.params['macd_signal']
        
        # Calculate MACD
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Generate signals
        df['signal'] = 0
        
        # Buy signal: MACD crosses above signal line
        df.loc[(df['macd'] > df['macd_signal']) & 
               (df['macd'].shift(1) <= df['macd_signal'].shift(1)), 'signal'] = 1
        
        # Sell signal: MACD crosses below signal line
        df.loc[(df['macd'] < df['macd_signal']) & 
               (df['macd'].shift(1) >= df['macd_signal'].shift(1)), 'signal'] = -1
        
        df['position'] = df['signal'].diff().fillna(0)
        
        return df


class Bollinger_Strategy(BaseStrategy):
    """
    Bollinger Bands Strategy.
    
    Buy when price touches lower band (oversold).
    Sell when price touches upper band (overbought).
    """
    
    def __init__(self, params=None):
        """
        Initialize Bollinger Bands strategy.
        
        Args:
            params (dict): Contains 'period' and 'std_dev'
        """
        default_params = {
            'bb_period': 20,
            'bb_std': 2.0
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate Bollinger Bands signals."""
        if not self.validate_data(data):
            raise ValueError("Data missing required OHLCV columns")
        
        df = data.copy()
        period = self.params['bb_period']
        std_dev = self.params['bb_std']
        
        # Calculate Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        df['bb_std'] = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std_dev)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std_dev)
        df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Generate signals
        df['signal'] = 0
        
        # Buy signal: Price below lower band
        df.loc[df['close'] < df['bb_lower'], 'signal'] = 1
        
        # Sell signal: Price above upper band
        df.loc[df['close'] > df['bb_upper'], 'signal'] = -1
        
        df['position'] = df['signal'].diff().fillna(0)
        
        return df


class VWAP_Strategy(BaseStrategy):
    """
    VWAP (Volume Weighted Average Price) Strategy.
    
    Buy when price crosses above VWAP (bullish).
    Sell when price crosses below VWAP (bearish).
    Works best on intraday data.
    """
    
    def __init__(self, params=None):
        """
        Initialize VWAP strategy.
        
        Args:
            params (dict): Contains 'vwap_period'
        """
        default_params = {
            'vwap_period': 14
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate VWAP signals."""
        if not self.validate_data(data):
            raise ValueError("Data missing required OHLCV columns")
        
        df = data.copy()
        
        # Calculate VWAP
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        
        # Alternative: Rolling VWAP for daily reset
        period = self.params['vwap_period']
        df['vwap_rolling'] = (typical_price * df['volume']).rolling(window=period).sum() / \
                             df['volume'].rolling(window=period).sum()
        
        # Generate signals based on rolling VWAP
        df['signal'] = 0
        
        # Buy signal: Price crosses above VWAP
        df.loc[df['close'] > df['vwap_rolling'], 'signal'] = 1
        
        # Sell signal: Price crosses below VWAP
        df.loc[df['close'] < df['vwap_rolling'], 'signal'] = -1
        
        df['position'] = df['signal'].diff().fillna(0)
        
        return df


class Multi_Indicator_Strategy(BaseStrategy):
    """
    Multi-Indicator Strategy combining SMA, RSI, MACD, and Bollinger.
    
    Uses multiple confirmations to filter out false signals.
    Requires at least 2 indicators to agree for a signal.
    """
    
    def __init__(self, params=None):
        """
        Initialize multi-indicator strategy.
        
        Args:
            params (dict): Strategy parameters
        """
        default_params = {
            'sma_short': 20,
            'sma_long': 50,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2.0,
            'min_confirmation': 2  # Minimum indicators to agree
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI."""
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        avg_gains = gains.rolling(window=period).mean()
        avg_losses = losses.rolling(window=period).mean()
        rs = avg_gains / avg_losses
        return 100 - (100 / (1 + rs))
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate multi-indicator signals."""
        if not self.validate_data(data):
            raise ValueError("Data missing required OHLCV columns")
        
        df = data.copy()
        
        # Calculate SMA
        df['sma_short'] = df['close'].rolling(window=self.params['sma_short']).mean()
        df['sma_long'] = df['close'].rolling(window=self.params['sma_long']).mean()
        
        # Calculate RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.params['rsi_period'])
        
        # Calculate MACD
        ema_fast = df['close'].ewm(span=self.params['macd_fast'], adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.params['macd_slow'], adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=self.params['macd_signal'], adjust=False).mean()
        
        # Calculate Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=self.params['bb_period']).mean()
        df['bb_std'] = df['close'].rolling(window=self.params['bb_period']).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * self.params['bb_std'])
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * self.params['bb_std'])
        
        # Individual indicator signals (bullish = 1, bearish = -1)
        df['sma_signal'] = np.where(df['sma_short'] > df['sma_long'], 1, -1)
        df['rsi_signal'] = np.where(df['rsi'] < self.params['rsi_oversold'], 1,
                                     np.where(df['rsi'] > self.params['rsi_overbought'], -1, 0))
        df['macd_signal'] = np.where(df['macd'] > df['macd_signal'], 1, -1)
        df['bb_signal'] = np.where(df['close'] < df['bb_lower'], 1,
                                   np.where(df['close'] > df['bb_upper'], -1, 0))
        
        # Count confirmations
        df['buy_conf'] = (df['sma_signal'] == 1).astype(int) + \
                         (df['rsi_signal'] == 1).astype(int) + \
                         (df['macd_signal'] == 1).astype(int) + \
                         (df['bb_signal'] == 1).astype(int)
        
        df['sell_conf'] = (df['sma_signal'] == -1).astype(int) + \
                          (df['rsi_signal'] == -1).astype(int) + \
                          (df['macd_signal'] == -1).astype(int) + \
                          (df['bb_signal'] == -1).astype(int)
        
        # Generate combined signal
        df['signal'] = 0
        min_conf = self.params['min_confirmation']
        
        # Buy: At least min_confirmation indicators are bullish
        df.loc[df['buy_conf'] >= min_conf, 'signal'] = 1
        
        # Sell: At least min_confirmation indicators are bearish
        df.loc[df['sell_conf'] >= min_conf, 'signal'] = -1
        
        df['position'] = df['signal'].diff().fillna(0)
        
        return df


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion (Bounce) Strategy using Bollinger Bands and RSI.
    
    Konzept: Kaufe wenn Preis unter untere Bollinger Band fällt,
    verkaufe wenn er zurückkommt zur Mitte.
    
    Entry: Close < Lower Band AND RSI < 40
    Exit: Close > Middle Band OR Stop Loss 3%
    Timeframe: 1h
    """
    
    def __init__(self, params=None):
        default_params = {
            'bb_period': 20,
            'bb_std': 2.0,
            'rsi_period': 14,
            'rsi_oversold': 40,
            'stop_loss_pct': 3.0,
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def _calculate_rsi(self, prices, period):
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        avg_gains = gains.ewm(span=period, adjust=False).mean()
        avg_losses = losses.ewm(span=period, adjust=False).mean()
        rs = avg_gains / avg_losses
        return 100 - (100 / (1 + rs))
    
    def generate_signals(self, data):
        if not self.validate_data(data):
            raise ValueError("Data missing required OHLCV columns")
        
        df = data.copy()
        period = self.params['bb_period']
        std_dev = self.params['bb_std']
        rsi_period = self.params['rsi_period']
        rsi_oversold = self.params['rsi_oversold']
        stop_loss_pct = self.params['stop_loss_pct'] / 100
        
        # Calculate Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        df['bb_std'] = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std_dev)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std_dev)
        
        # Calculate RSI
        df['rsi'] = self._calculate_rsi(df['close'], rsi_period)
        
        # Track position state
        df['signal'] = 0
        df['position'] = 0
        entry_price = 0
        current_position = 0
        
        for i in range(len(df)):
            if i < max(period, rsi_period):
                continue
            
            close_price = df['close'].iloc[i]
            lower_band = df['bb_lower'].iloc[i]
            middle_band = df['bb_middle'].iloc[i]
            rsi_value = df['rsi'].iloc[i]
            
            if current_position == 0:
                if close_price < lower_band and rsi_value < rsi_oversold:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    current_position = 1
                    entry_price = close_price
            elif current_position == 1:
                exit_mean = close_price > middle_band
                exit_sl = close_price < entry_price * (1 - stop_loss_pct)
                if exit_mean or exit_sl:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    current_position = 0
                    entry_price = 0
        
        df['position'] = df['signal'].cumsum().clip(0, 1)
        return df


class MomentumBreakoutStrategy(BaseStrategy):
    """
    Momentum Breakout Strategy using ATR and SMA.
    
    Konzept: Folge starken Trends, wenn Volatilität explodiert.
    
    Entry: Close > SMA + 1.5xATR (Long) / Close < SMA - 1.5xATR (Short)
    Exit: ATR Trailing Stop
    Timeframe: 15min oder 1h
    """
    
    def __init__(self, params=None):
        default_params = {
            'atr_period': 14,
            'sma_period': 20,
            'atr_multiplier': 1.5,
            'trailing_stop_mult': 2.0,
            'allow_short': True,
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def _calculate_atr(self, df, period):
        high = df['high']
        low = df['low']
        close = df['close']
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    def generate_signals(self, data):
        if not self.validate_data(data):
            raise ValueError("Data missing required OHLCV columns")
        
        df = data.copy()
        atr_period = self.params['atr_period']
        sma_period = self.params['sma_period']
        atr_mult = self.params['atr_multiplier']
        trailing_mult = self.params['trailing_stop_mult']
        allow_short = self.params['allow_short']
        
        df['sma'] = df['close'].rolling(window=sma_period).mean()
        df['atr'] = self._calculate_atr(df, atr_period)
        df['long_entry'] = df['sma'] + (df['atr'] * atr_mult)
        df['short_entry'] = df['sma'] - (df['atr'] * atr_mult)
        
        df['signal'] = 0
        df['position'] = 0
        
        current_position = 0
        entry_price = 0
        highest_price = 0
        lowest_price = float('inf')
        trailing_stop = 0
        
        for i in range(len(df)):
            if i < max(atr_period, sma_period):
                continue
            
            close_price = df['close'].iloc[i]
            atr_value = df['atr'].iloc[i]
            long_level = df['long_entry'].iloc[i]
            short_level = df['short_entry'].iloc[i]
            
            if current_position == 1:
                highest_price = max(highest_price, close_price)
                trailing_stop = highest_price - (atr_value * trailing_mult)
                if close_price < trailing_stop:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    current_position = 0
                    highest_price = 0
            elif current_position == -1 and allow_short:
                lowest_price = min(lowest_price, close_price)
                trailing_stop = lowest_price + (atr_value * trailing_mult)
                if close_price > trailing_stop:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    current_position = 0
                    lowest_price = float('inf')
            
            if current_position == 0:
                if close_price > long_level:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    current_position = 1
                    entry_price = close_price
                    highest_price = close_price
                elif allow_short and close_price < short_level:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    current_position = -1
                    entry_price = close_price
                    lowest_price = close_price
        
        df['position'] = df['signal'].cumsum().clip(-1 if allow_short else 0, 1)
        return df


class RangeScalperStrategy(BaseStrategy):
    """
    Range Scalping Strategy using Support/Resistance and RSI.
    
    Konzept: Trade innerhalb einer Range (Support/Resistance)
    
    Entry: Near Support + RSI < 30 (Long) / Near Resistance + RSI > 70 (Short)
    Exit: Opposite side of the range
    Timeframe: 15min
    """
    
    def __init__(self, params=None):
        default_params = {
            'lookback_period': 20,
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'proximity_pct': 0.5,
            'allow_short': True,
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def _calculate_rsi(self, prices, period):
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        avg_gains = gains.ewm(span=period, adjust=False).mean()
        avg_losses = losses.ewm(span=period, adjust=False).mean()
        rs = avg_gains / avg_losses
        return 100 - (100 / (1 + rs))
    
    def generate_signals(self, data):
        if not self.validate_data(data):
            raise ValueError("Data missing required OHLCV columns")
        
        df = data.copy()
        lookback = self.params['lookback_period']
        rsi_period = self.params['rsi_period']
        rsi_oversold = self.params['rsi_oversold']
        rsi_overbought = self.params['rsi_overbought']
        proximity_pct = self.params['proximity_pct'] / 100
        allow_short = self.params['allow_short']
        
        df['rsi'] = self._calculate_rsi(df['close'], rsi_period)
        df['support'] = df['low'].rolling(window=lookback).min()
        df['resistance'] = df['high'].rolling(window=lookback).max()
        
        df['support_upper'] = df['support'] * (1 + proximity_pct)
        df['resistance_lower'] = df['resistance'] * (1 - proximity_pct)
        
        df['signal'] = 0
        df['position'] = 0
        
        current_position = 0
        
        for i in range(len(df)):
            if i < max(lookback, rsi_period):
                continue
            
            close_price = df['close'].iloc[i]
            support_level = df['support'].iloc[i]
            resistance_level = df['resistance'].iloc[i]
            support_upper = df['support_upper'].iloc[i]
            resistance_lower = df['resistance_lower'].iloc[i]
            rsi_value = df['rsi'].iloc[i]
            
            if current_position == 1:
                exit_res = close_price >= resistance_lower
                exit_break = close_price < support_level * 0.99
                if exit_res or exit_break:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    current_position = 0
            elif current_position == -1 and allow_short:
                exit_sup = close_price <= support_upper
                exit_break = close_price > resistance_level * 1.01
                if exit_sup or exit_break:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    current_position = 0
            
            if current_position == 0:
                near_support = close_price <= support_upper and close_price >= support_level
                if near_support and rsi_value < rsi_oversold:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    current_position = 1
                elif allow_short:
                    near_res = close_price >= resistance_lower and close_price <= resistance_level
                    if near_res and rsi_value > rsi_overbought:
                        df.iloc[i, df.columns.get_loc('signal')] = -1
                        current_position = -1
        
        df['position'] = df['signal'].cumsum().clip(-1 if allow_short else 0, 1)
        return df


class AdaptiveMomentumStrategy(BaseStrategy):
    """
    Adaptive Momentum Strategy - Arbeitet auch in Seitwärtsphasen.
    
    Kombiniert:
    - ATR-basierte Breakouts (für Trend-Phasen)
    - RSI-Mean-Reversion (für Seitwärtsphasen)
    - Dynamische Marktregime-Erkennung (Trend vs Range)
    """
    
    def __init__(self, params=None):
        default_params = {
            'atr_period': 14,
            'sma_period': 20,
            'atr_multiplier': 0.8,  # Aggressiver für mehr Trades
            'trailing_stop_mult': 2.0,
            'rsi_period': 14,
            'rsi_oversold': 35,  # Höher für mehr Entries
            'rsi_overbought': 65,  # Niedriger für mehr Exits
            'trend_threshold': 0.02,  # 2% über/unter SMA für Trend
            'allow_short': True,
            'max_hold_bars': 20,  # Maximale Hold-Zeit
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def _calculate_atr(self, df, period):
        high = df['high']
        low = df['low']
        close = df['close']
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    def _calculate_rsi(self, prices, period):
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        avg_gains = gains.ewm(span=period, adjust=False).mean()
        avg_losses = losses.ewm(span=period, adjust=False).mean()
        rs = avg_gains / avg_losses
        return 100 - (100 / (1 + rs))
    
    def generate_signals(self, data):
        if not self.validate_data(data):
            raise ValueError("Data missing required OHLCV columns")
        
        df = data.copy()
        
        # Indikatoren berechnen
        df['sma'] = df['close'].rolling(window=self.params['sma_period']).mean()
        df['atr'] = self._calculate_atr(df, self.params['atr_period'])
        df['rsi'] = self._calculate_rsi(df['close'], self.params['rsi_period'])
        
        # Marktregime erkennen (Trend vs Range)
        df['price_vs_sma_pct'] = (df['close'] - df['sma']) / df['sma']
        df['in_uptrend'] = df['price_vs_sma_pct'] > self.params['trend_threshold']
        df['in_downtrend'] = df['price_vs_sma_pct'] < -self.params['trend_threshold']
        df['in_range'] = ~(df['in_uptrend'] | df['in_downtrend'])
        
        # Entry Levels
        df['long_entry_breakout'] = df['sma'] + (df['atr'] * self.params['atr_multiplier'])
        df['short_entry_breakout'] = df['sma'] - (df['atr'] * self.params['atr_multiplier'])
        
        # Trading Logik
        df['signal'] = 0
        df['position'] = 0
        
        current_position = 0
        entry_price = 0
        entry_bar = 0
        bars_held = 0
        highest_price = 0
        lowest_price = float('inf')
        
        for i in range(len(df)):
            if i < max(self.params['atr_period'], self.params['sma_period'], self.params['rsi_period']):
                continue
            
            close = df['close'].iloc[i]
            sma = df['sma'].iloc[i]
            atr = df['atr'].iloc[i]
            rsi = df['rsi'].iloc[i]
            in_uptrend = df['in_uptrend'].iloc[i]
            in_downtrend = df['in_downtrend'].iloc[i]
            in_range = df['in_range'].iloc[i]
            long_level = df['long_entry_breakout'].iloc[i]
            short_level = df['short_entry_breakout'].iloc[i]
            
            bars_held += 1 if current_position != 0 else 0
            
            # EXIT LOGIK
            if current_position == 1:
                highest_price = max(highest_price, close)
                trailing_stop = highest_price - (atr * self.params['trailing_stop_mult'])
                
                # Exit Gründe
                exit_trailing = close < trailing_stop
                exit_rsi = rsi > self.params['rsi_overbought']  # Overbought = verkaufen
                exit_time = bars_held >= self.params['max_hold_bars']
                
                if exit_trailing or exit_rsi or exit_time:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    current_position = 0
                    bars_held = 0
                    highest_price = 0
                    
            elif current_position == -1 and self.params['allow_short']:
                lowest_price = min(lowest_price, close)
                trailing_stop = lowest_price + (atr * self.params['trailing_stop_mult'])
                
                exit_trailing = close > trailing_stop
                exit_rsi = rsi < self.params['rsi_oversold']  # Oversold = zurückkaufen
                exit_time = bars_held >= self.params['max_hold_bars']
                
                if exit_trailing or exit_rsi or exit_time:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    current_position = 0
                    bars_held = 0
                    lowest_price = float('inf')
            
            # ENTRY LOGIK
            if current_position == 0:
                # Trend-Phase: Breakout Trading
                if in_uptrend and close > long_level:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    current_position = 1
                    entry_price = close
                    entry_bar = i
                    bars_held = 0
                    highest_price = close
                    
                elif in_downtrend and self.params['allow_short'] and close < short_level:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    current_position = -1
                    entry_price = close
                    entry_bar = i
                    bars_held = 0
                    lowest_price = close
                    
                # Range-Phase: Mean Reversion
                elif in_range:
                    if rsi < self.params['rsi_oversold']:
                        # Oversold in Range = kaufen
                        df.iloc[i, df.columns.get_loc('signal')] = 1
                        current_position = 1
                        entry_price = close
                        entry_bar = i
                        bars_held = 0
                        highest_price = close
                    elif self.params['allow_short'] and rsi > self.params['rsi_overbought']:
                        # Overbought in Range = shorten
                        df.iloc[i, df.columns.get_loc('signal')] = -1
                        current_position = -1
                        entry_price = close
                        entry_bar = i
                        bars_held = 0
                        lowest_price = close
        
        df['position'] = df['signal'].cumsum().clip(-1 if self.params['allow_short'] else 0, 1)
        return df


# Strategy registry for easy access
STRATEGIES = {
    'sma_crossover': SMA_Crossover_Strategy,
    'rsi': RSI_Strategy,
    'combined': Combined_Strategy,
    'macd': MACD_Strategy,
    'bollinger': Bollinger_Strategy,
    'vwap': VWAP_Strategy,
    'multi_indicator': Multi_Indicator_Strategy,
    'mean_reversion': MeanReversionStrategy,
    'momentum_breakout': MomentumBreakoutStrategy,
    'range_scalper': RangeScalperStrategy,
    'adaptive_momentum': AdaptiveMomentumStrategy,  # NEW!
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

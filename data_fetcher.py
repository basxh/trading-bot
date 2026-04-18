"""
Data Fetcher Module - Fetches market data from various sources
Supports Yahoo Finance (stocks) and Binance (crypto)
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import yfinance as yf

# Optional Binance import
try:
    from binance.client import Client as BinanceClient
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    logging.warning("python-binance not installed. Crypto data fetching disabled.")


class DataFetcher:
    """
    Fetches market data from various sources.
    
    Supports:
    - Yahoo Finance (stocks, ETFs, forex)
    - Binance (cryptocurrencies)
    """
    
    # Valid intervals for each source
    YF_INTERVALS = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', 
                    '1d', '5d', '1wk', '1mo', '3mo']
    
    BINANCE_INTERVALS = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', 
                         '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize DataFetcher.
        
        Args:
            config (dict): Configuration containing:
                - save_path: Where to save downloaded data
                - api_key: For Binance (optional)
                - api_secret: For Binance (optional)
        """
        self.config = config or {}
        self.save_path = self.config.get('save_path', 'data/')
        self.logger = logging.getLogger(__name__)
        
        # Ensure save directory exists
        os.makedirs(self.save_path, exist_ok=True)
        
        # Initialize Binance client if credentials provided
        self.binance_client = None
        if BINANCE_AVAILABLE:
            api_key = self.config.get('api_key')
            api_secret = self.config.get('api_secret')
            if api_key and api_secret:
                self.binance_client = BinanceClient(api_key, api_secret)
                self.logger.info("Binance client initialized")
    
    def fetch_yahoo_finance(self, 
                           symbol: str, 
                           interval: str = '1d',
                           period: str = '2y',
                           start: Optional[str] = None,
                           end: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch data from Yahoo Finance.
        
        Args:
            symbol (str): Stock symbol (e.g., 'AAPL', 'MSFT')
            interval (str): Data interval ('1m', '5m', '1h', '1d', etc.)
            period (str): Lookback period ('1d', '5d', '1mo', '3mo', '6mo', 
                         '1y', '2y', '5y', '10y', 'ytd', 'max')
            start (str): Start date (YYYY-MM-DD) - overrides period
            end (str): End date (YYYY-MM-DD) - overrides period
        
        Returns:
            pd.DataFrame: OHLCV data
        """
        self.logger.info(f"Fetching {symbol} from Yahoo Finance ({interval})")
        
        if interval not in self.YF_INTERVALS:
            raise ValueError(f"Invalid interval: {interval}. Use: {self.YF_INTERVALS}")
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Use start/end dates if provided, otherwise period
            if start and end:
                df = ticker.history(start=start, end=end, interval=interval)
            else:
                df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                raise ValueError(f"No data returned for {symbol}")
            
            # Standardize column names
            df.columns = [c.lower().replace(' ', '_') for c in df.columns]
            
            # Remove timezone info for consistency
            df.index = df.index.tz_localize(None)
            
            self.logger.info(f"Fetched {len(df)} rows for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching {symbol} from Yahoo Finance: {e}")
            raise
    
    def fetch_binance(self,
                     symbol: str,
                     interval: str = '1h',
                     limit: int = 1000,
                     start_time: Optional[str] = None,
                     end_time: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch data from Binance.
        
        Args:
            symbol (str): Trading pair (e.g., 'BTCUSDT', 'ETHUSDT')
            interval (str): Kline interval ('1m', '5m', '1h', '1d', etc.)
            limit (int): Number of candles to fetch (max 1000)
            start_time (str): Start time (YYYY-MM-DD)
            end_time (str): End time (YYYY-MM-DD)
        
        Returns:
            pd.DataFrame: OHLCV data
        """
        if not BINANCE_AVAILABLE:
            raise ImportError("python-binance not installed. Run: pip install python-binance")
        
        if self.binance_client is None:
            # Use public API (no auth needed for historical data)
            self.binance_client = BinanceClient()
        
        self.logger.info(f"Fetching {symbol} from Binance ({interval})")
        
        if interval not in self.BINANCE_INTERVALS:
            raise ValueError(f"Invalid interval: {interval}. Use: {self.BINANCE_INTERVALS}")
        
        try:
            # Convert dates to timestamps if provided
            start_ts = None
            end_ts = None
            if start_time:
                start_ts = int(datetime.strptime(start_time, '%Y-%m-%d').timestamp() * 1000)
            if end_time:
                end_ts = int(datetime.strptime(end_time, '%Y-%m-%d').timestamp() * 1000)
            
            # Fetch klines (candlestick data)
            klines = self.binance_client.get_klines(
                symbol=symbol.upper(),
                interval=interval,
                limit=limit,
                startTime=start_ts,
                endTime=end_ts
            )
            
            if not klines:
                raise ValueError(f"No data returned for {symbol}")
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
                'taker_buy_quote_volume', 'ignore'
            ])
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Set index
            df.set_index('timestamp', inplace=True)
            
            # Select only OHLCV columns
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            self.logger.info(f"Fetched {len(df)} rows for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching {symbol} from Binance: {e}")
            raise
    
    def save_data(self, 
                  df: pd.DataFrame, 
                  symbol: str, 
                  interval: str,
                  format: str = 'csv') -> str:
        """
        Save fetched data to file.
        
        Args:
            df (pd.DataFrame): Data to save
            symbol (str): Symbol name
            interval (str): Data interval
            format (str): 'csv' or 'json'
        
        Returns:
            str: Path to saved file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{symbol}_{interval}_{timestamp}"
        
        if format == 'csv':
            filepath = os.path.join(self.save_path, f"{filename}.csv")
            df.to_csv(filepath)
        elif format == 'json':
            filepath = os.path.join(self.save_path, f"{filename}.json")
            df.to_json(filepath, orient='records', date_format='iso')
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"Saved data to {filepath}")
        return filepath
    
    def load_data(self, filepath: str) -> pd.DataFrame:
        """
        Load saved data from file.
        
        Args:
            filepath (str): Path to data file
        
        Returns:
            pd.DataFrame: Loaded data
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        elif filepath.endswith('.json'):
            df = pd.read_json(filepath)
            if 'timestamp' in df.columns:
                df.set_index('timestamp', inplace=True)
                df.index = pd.to_datetime(df.index)
        else:
            raise ValueError(f"Unsupported file format: {filepath}")
        
        self.logger.info(f"Loaded {len(df)} rows from {filepath}")
        return df
    
    def fetch(self,
              symbol: str,
              market_type: str = 'stock',
              interval: str = '1d',
              **kwargs) -> pd.DataFrame:
        """
        Universal fetch method - fetches from appropriate source.
        
        Args:
            symbol (str): Trading symbol
            market_type (str): 'stock' or 'crypto'
            interval (str): Data interval
            **kwargs: Additional args for specific fetchers
        
        Returns:
            pd.DataFrame: OHLCV data
        """
        if market_type == 'stock':
            return self.fetch_yahoo_finance(symbol, interval, **kwargs)
        elif market_type == 'crypto':
            return self.fetch_binance(symbol, interval, **kwargs)
        else:
            raise ValueError(f"Unknown market_type: {market_type}")


# Convenience function
def fetch_data(symbol: str, 
               market_type: str = 'stock',
               interval: str = '1d',
               save: bool = False,
               **kwargs) -> pd.DataFrame:
    """
    Convenience function to fetch market data.
    
    Args:
        symbol (str): Trading symbol
        market_type (str): 'stock' or 'crypto'
        interval (str): Data interval
        save (bool): Whether to save data to file
        **kwargs: Additional parameters
    
    Returns:
        pd.DataFrame: OHLCV data
    """
    fetcher = DataFetcher()
    df = fetcher.fetch(symbol, market_type, interval, **kwargs)
    
    if save:
        fetcher.save_data(df, symbol, interval)
    
    return df

"""
Machine Learning Trainer Module
Prepares features and targets for ML training
"""
import os
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd
import numpy as np


class FeatureEngineer:
    """
    Feature engineering for trading ML models.
    
    Creates technical indicators and features for prediction:
    - Returns (1d, 5d, 10d)
    - Volatility measures
    - Technical indicators (RSI, MACD, Bollinger)
    - Volume features
    - Price patterns
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def create_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Create comprehensive feature set from OHLCV data.
        
        Args:
            data (pd.DataFrame): OHLCV data
            
        Returns:
            pd.DataFrame: Data with features
        """
        self.logger.info("Creating features...")
        
        df = data.copy()
        
        # === RETURNS ===
        df['return_1d'] = df['close'].pct_change(1)
        df['return_5d'] = df['close'].pct_change(5)
        df['return_10d'] = df['close'].pct_change(10)
        df['return_20d'] = df['close'].pct_change(20)
        
        # === VOLATILITY ===
        df['volatility_5d'] = df['close'].pct_change().rolling(5).std() * np.sqrt(252)
        df['volatility_10d'] = df['close'].pct_change().rolling(10).std() * np.sqrt(252)
        df['volatility_20d'] = df['close'].pct_change().rolling(20).std() * np.sqrt(252)
        
        # True Range and ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr_14'] = df['tr'].rolling(14).mean()
        df['atr_20'] = df['tr'].rolling(20).mean()
        
        # === MOVING AVERAGES ===
        for period in [5, 10, 20, 50, 200]:
            df[f'sma_{period}'] = df['close'].rolling(period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # Distance from moving averages
        for period in [5, 10, 20, 50]:
            df[f'dist_sma_{period}'] = (df['close'] - df[f'sma_{period}']) / df[f'sma_{period}']
            df[f'dist_ema_{period}'] = (df['close'] - df[f'ema_{period}']) / df[f'ema_{period}']
        
        # === RSI ===
        for period in [7, 14, 21]:
            df[f'rsi_{period}'] = self._calculate_rsi(df['close'], period)
        
        # === MACD ===
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # === BOLLINGER BANDS ===
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # === VOLUME FEATURES ===
        df['volume_sma_20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        df['volume_change'] = df['volume'].pct_change()
        
        # On Balance Volume (OBV)
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        
        # Volume weighted average price
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        df['vwap_dist'] = (df['close'] - df['vwap']) / df['vwap']
        
        # === PRICE PATTERNS ===
        # High-Low range
        df['hl_range'] = (df['high'] - df['low']) / df['close']
        df['body_pct'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-10)
        
        # Price position in daily range
        df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)
        
        # Gap
        df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        
        # === MOMENTUM ===
        df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
        df['momentum_20'] = df['close'] / df['close'].shift(20) - 1
        
        # Rate of Change
        df['roc_10'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10)
        
        # === TREND ===
        # ADX calculation (simplified)
        df['dx'] = abs(df['high'] - df['low']) / (df['high'] + df['low'] + 1e-10) * 100
        df['adx'] = df['dx'].rolling(14).mean()
        
        self.logger.info(f"Features created: {len(df.columns)} total columns")
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI."""
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        avg_gains = gains.rolling(window=period).mean()
        avg_losses = losses.rolling(window=period).mean()
        rs = avg_gains / avg_losses
        return 100 - (100 / (1 + rs))
    
    def create_targets(self, data: pd.DataFrame, 
                       forecast_horizon: int = 1) -> pd.DataFrame:
        """
        Create target variables for ML training.
        
        Args:
            data (pd.DataFrame): Price data
            forecast_horizon (int): Days to forecast
            
        Returns:
            pd.DataFrame: Data with target columns
        """
        df = data.copy()
        
        # Future returns
        df['future_return'] = df['close'].shift(-forecast_horizon) / df['close'] - 1
        
        # Classify direction
        df['direction'] = np.where(df['future_return'] > 0.005, 1,  # Up (> 0.5%)
                          np.where(df['future_return'] < -0.005, -1,  # Down (< -0.5%)
                                   0))  # Sideways
        
        # Volatility target (will it move a lot?)
        df['future_volatility'] = df['close'].pct_change().shift(-forecast_horizon).rolling(5).std()
        
        return df
    
    def prepare_ml_dataset(self, data: pd.DataFrame,
                           forecast_horizon: int = 1,
                           drop_na: bool = True) -> pd.DataFrame:
        """
        Complete feature engineering pipeline.
        
        Args:
            data (pd.DataFrame): Raw OHLCV data
            forecast_horizon (int): Days to forecast
            drop_na (bool): Drop rows with NaN values
            
        Returns:
            pd.DataFrame: ML-ready dataset
        """
        # Create features
        df = self.create_features(data)
        
        # Create targets
        df = self.create_targets(df, forecast_horizon)
        
        # Drop NaN values
        if drop_na:
            df = df.dropna()
        
        return df


class MLTrainer:
    """
    Prepares training data for Machine Learning models.
    
    Saves data in CSV format for external training.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.feature_engineer = FeatureEngineer()
    
    def prepare_data(self,
                     symbol: str,
                     data: pd.DataFrame,
                     forecast_horizon: int = 1,
                     train_pct: float = 0.8) -> Dict[str, Any]:
        """
        Prepare ML training data.
        
        Args:
            symbol (str): Trading symbol
            data (pd.DataFrame): OHLCV data
            forecast_horizon (int): Days to forecast
            train_pct (float): Percentage for training
            
        Returns:
            dict: Paths to saved files and statistics
        """
        self.logger.info(f"Preparing ML data for {symbol}...")
        
        # Create features and targets
        ml_data = self.feature_engineer.prepare_ml_dataset(data, forecast_horizon)
        
        # Define feature columns (exclude non-feature columns)
        exclude_cols = ['open', 'high', 'low', 'close', 'volume', 
                       'future_return', 'direction', 'future_volatility']
        
        feature_cols = [c for c in ml_data.columns if c not in exclude_cols]
        
        # Add target columns
        target_cols = ['direction', 'future_return', 'future_volatility']
        
        # Split into train/test
        train_size = int(len(ml_data) * train_pct)
        train_data = ml_data.iloc[:train_size]
        test_data = ml_data.iloc[train_size:]
        
        # Save datasets
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = f"ml_data/{symbol}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Full dataset
        full_path = f"{output_dir}/features_{forecast_horizon}d_{timestamp}.csv"
        ml_data[feature_cols + target_cols].to_csv(full_path, index=True)
        
        # Train dataset
        train_path = f"{output_dir}/train_{forecast_horizon}d_{timestamp}.csv"
        train_data[feature_cols + target_cols].to_csv(train_path, index=True)
        
        # Test dataset
        test_path = f"{output_dir}/test_{forecast_horizon}d_{timestamp}.csv"
        test_data[feature_cols + target_cols].to_csv(test_path, index=True)
        
        # Feature info
        info = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'forecast_horizon': forecast_horizon,
            'total_samples': len(ml_data),
            'train_samples': len(train_data),
            'test_samples': len(test_data),
            'num_features': len(feature_cols),
            'feature_names': feature_cols,
            'target_columns': target_cols,
            'files': {
                'full': full_path,
                'train': train_path,
                'test': test_path
            },
            'class_distribution': {
                'up': int((ml_data['direction'] == 1).sum()),
                'down': int((ml_data['direction'] == -1).sum()),
                'sideways': int((ml_data['direction'] == 0).sum())
            }
        }
        
        # Save metadata
        import json
        info_path = f"{output_dir}/info_{forecast_horizon}d_{timestamp}.json"
        with open(info_path, 'w') as f:
            json.dump(info, f, indent=2)
        
        self.logger.info(f"ML data prepared: {len(train_data)} train, {len(test_data)} test samples")
        
        return info
    
    def print_summary(self, info: Dict[str, Any]):
        """Print dataset summary."""
        print(f"\n{'='*60}")
        print(f"ML DATASET SUMMARY FOR {info['symbol']}")
        print(f"{'='*60}")
        print(f"Total Samples:     {info['total_samples']}")
        print(f"Training Samples:  {info['train_samples']}")
        print(f"Test Samples:      {info['test_samples']}")
        print(f"Number of Features: {info['num_features']}")
        print(f"Forecast Horizon:  {info['forecast_horizon']} day(s)")
        print(f"\nClass Distribution:")
        print(f"  Up:       {info['class_distribution']['up']}")
        print(f"  Down:     {info['class_distribution']['down']}")
        print(f"  Sideways: {info['class_distribution']['sideways']}")
        print(f"\nFiles saved:")
        for key, path in info['files'].items():
            print(f"  {key}: {path}")
        print(f"{'='*60}\n")


def prepare_ml_data(symbol: str,
                     days: int = 365,
                     forecast_horizon: int = 1) -> Dict[str, Any]:
    """
    Fetch data and prepare ML dataset.
    
    Args:
        symbol (str): Trading symbol
        days (int): Days of historical data
        forecast_horizon (int): Days to forecast
        
    Returns:
        dict: Dataset information
    """
    from data_fetcher import fetch_yahoo_data
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Fetching {days} days of data for {symbol}...")
    data = fetch_yahoo_data(symbol, period=f"{days}d", interval='1d')
    
    if data is None or len(data) < 100:
        logger.error(f"Insufficient data for {symbol}")
        return None
    
    logger.info(f"Data loaded: {len(data)} rows")
    
    # Create trainer and prepare data
    trainer = MLTrainer()
    info = trainer.prepare_data(symbol, data, forecast_horizon)
    
    # Print summary
    trainer.print_summary(info)
    
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ML Data Preparation')
    parser.add_argument('--symbol', type=str, required=True, help='Trading symbol')
    parser.add_argument('--days', type=int, default=365, help='Days of data')
    parser.add_argument('--forecast-horizon', type=int, default=1, 
                        help='Forecast horizon in days')
    
    args = parser.parse_args()
    
    info = prepare_ml_data(
        symbol=args.symbol,
        days=args.days,
        forecast_horizon=args.forecast_horizon
    )
    
    if info:
        print("✅ ML data preparation complete!")

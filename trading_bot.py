#!/usr/bin/env python3
"""
Trading Bot - Main Entry Point

A modular trading bot supporting:
- Backtesting
- Paper Trading
- Live Trading (prepared)

Usage:
    python trading_bot.py --mode backtest --symbol AAPL --strategy sma_crossover
    python trading_bot.py --mode paper --symbol AAPL --strategy rsi
    python trading_bot.py --mode live --symbol AAPL --strategy sma_crossover
"""
import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, Any

import pandas as pd

from data_fetcher import DataFetcher
from strategies import get_strategy, STRATEGIES
from backtest import Backtest, run_backtest
from paper_trader import PaperTrader
from live_trader import LiveTrader


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """
    Setup logging configuration.
    
    Args:
        config (dict): Logging configuration
    
    Returns:
        Logger: Configured logger
    """
    log_level = getattr(logging, config.get('level', 'INFO').upper())
    log_file = config.get('file', 'logs/trading_bot.log')
    
    # Create logs directory
    os.makedirs(os.path.dirname(log_file) or '.', exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def load_config(filepath: str) -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Args:
        filepath (str): Path to config file
    
    Returns:
        dict: Configuration
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def run_backtest_mode(args: argparse.Namespace, config: Dict[str, Any], logger: logging.Logger):
    """
    Run backtest mode.
    
    Args:
        args: Command line arguments
        config: Configuration
        logger: Logger instance
    """
    logger.info("=" * 60)
    logger.info("STARTING BACKTEST MODE")
    logger.info("=" * 60)
    
    # Override config with CLI args
    symbol = args.symbol or config['general']['symbol']
    market_type = config['general']['market_type']
    interval = args.interval or config['data']['interval']
    period = config['data']['period']
    strategy_name = args.strategy or config['strategy']['name']
    
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Strategy: {strategy_name}")
    logger.info(f"Interval: {interval}")
    logger.info(f"Period: {period}")
    
    # Fetch data
    logger.info("Fetching market data...")
    fetcher = DataFetcher(config['data'])
    data = fetcher.fetch(symbol, market_type, interval, period=period)
    logger.info(f"Fetched {len(data)} data points")
    
    # Save data if requested
    if args.save_data:
        fetcher.save_data(data, symbol, interval, format='csv')
    
    # Initialize strategy
    strategy_params = config['strategy']['params']
    strategy = get_strategy(strategy_name, strategy_params)
    logger.info(f"Initialized {strategy.name}")
    
    # Run backtest
    logger.info("Running backtest...")
    backtest_config = config['backtest']
    results = run_backtest(strategy, data, backtest_config)
    
    # Print results
    backtest = results['backtest']
    print(backtest.get_summary())
    
    # Save report
    if args.save_report:
        report_path = f"reports/backtest_{symbol}_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backtest.save_report(report_path, strategy_name)
    
    # Plot equity curve
    if args.plot:
        plot_path = f"reports/backtest_{symbol}_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        backtest.plot_equity_curve(save_path=plot_path)
    
    logger.info("Backtest complete!")
    return results


def run_paper_mode(args: argparse.Namespace, config: Dict[str, Any], logger: logging.Logger):
    """
    Run paper trading mode.
    
    Args:
        args: Command line arguments
        config: Configuration
        logger: Logger instance
    """
    logger.info("=" * 60)
    logger.info("STARTING PAPER TRADING MODE")
    logger.info("=" * 60)
    
    # Override config with CLI args
    symbol = args.symbol or config['general']['symbol']
    market_type = config['general']['market_type']
    interval = args.interval or config['data']['interval']
    strategy_name = args.strategy or config['strategy']['name']
    
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Strategy: {strategy_name}")
    logger.info(f"Interval: {interval}")
    
    # Initialize paper trader
    paper_config = config['paper_trading']
    trader = PaperTrader(
        initial_capital=paper_config['initial_capital'],
        commission=paper_config['commission'],
        db_path=f"data/paper_trades_{symbol}_{strategy_name}.db"
    )
    
    # Initialize strategy
    strategy_params = config['strategy']['params']
    strategy = get_strategy(strategy_name, strategy_params)
    
    # For paper trading, we'll simulate on historical data
    # In production, this would fetch real-time data
    logger.info("Fetching market data...")
    fetcher = DataFetcher(config['data'])
    data = fetcher.fetch(symbol, market_type, interval, period='3mo')
    
    logger.info(f"Running paper trading simulation on {len(data)} data points...")
    
    # Generate signals
    signals_df = strategy.generate_signals(data)
    
    # Execute trades based on signals
    for timestamp, row in signals_df.iterrows():
        signal = row['signal']
        price = row['close']
        
        if pd.isna(signal) or signal == 0:
            continue
        
        # Execute signal
        trade = trader.execute_signal(symbol, signal, price, notes=f"Paper trade: {strategy_name}")
        
        # Update position with current price
        trader.update_prices({symbol: price})
    
    # Print final portfolio
    trader.print_portfolio()
    
    # Save summary
    if args.save_report:
        summary_path = f"reports/paper_trading_{symbol}_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        trader.save_summary(summary_path)
    
    logger.info("Paper trading complete!")
    return trader


def run_live_mode(args: argparse.Namespace, config: Dict[str, Any], logger: logging.Logger):
    """
    Run live trading mode.
    
    WARNING: This will execute REAL trades with REAL money!
    
    Args:
        args: Command line arguments
        config: Configuration
        logger: Logger instance
    """
    logger.info("=" * 60)
    logger.info("⚠️  STARTING LIVE TRADING MODE ⚠️")
    logger.info("=" * 60)
    
    # Safety check
    print("\n" + "=" * 60)
    print("⚠️  WARNING: LIVE TRADING MODE ⚠️")
    print("=" * 60)
    print("This mode will execute REAL trades with REAL money!")
    print("Make sure you have:")
    print("  1. Configured your broker API credentials")
    print("  2. Set appropriate safety limits")
    print("  3. Tested in paper mode first")
    print("=" * 60)
    
    confirm = input("\nType 'LIVE' to confirm: ")
    if confirm != "LIVE":
        logger.info("Live trading cancelled by user")
        return None
    
    # Override config with CLI args
    symbol = args.symbol or config['general']['symbol']
    strategy_name = args.strategy or config['strategy']['name']
    
    # Get live trading config
    live_config = config['live_trading']
    
    if not live_config.get('api_key') or not live_config.get('api_secret'):
        logger.error("API credentials not configured! Please set api_key and api_secret in config.json")
        return None
    
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Strategy: {strategy_name}")
    logger.info(f"Broker: {live_config['broker']}")
    logger.info(f"Paper Mode: {live_config.get('paper', True)}")
    
    # Initialize live trader
    try:
        trader = LiveTrader(
            broker=live_config['broker'],
            api_key=live_config['api_key'],
            api_secret=live_config['api_secret'],
            paper=live_config.get('paper', True),
            max_position_size=live_config['max_position_size'],
            max_daily_loss=live_config['max_daily_loss'],
            stop_loss_pct=live_config['stop_loss_pct']
        )
        
        # Print account info
        account = trader.broker.get_account()
        logger.info(f"Account connected. Cash: ${account.get('cash', 0):.2f}")
        
        # Initialize strategy
        strategy_params = config['strategy']['params']
        strategy = get_strategy(strategy_name, strategy_params)
        
        # Fetch latest data
        fetcher = DataFetcher(config['data'])
        data = fetcher.fetch(symbol, config['general']['market_type'], 
                           config['data']['interval'], period='5d')
        
        # Generate latest signal
        signals_df = strategy.generate_signals(data)
        latest = signals_df.iloc[-1]
        signal = latest['signal']
        price = latest['close']
        
        logger.info(f"Latest signal: {'BUY' if signal == 1 else 'SELL' if signal == -1 else 'HOLD'}")
        logger.info(f"Current price: ${price:.2f}")
        
        # Execute trade if signal present
        if signal != 0:
            trade = trader.execute_signal(symbol, signal, price)
            if trade:
                logger.info(f"Trade executed: {trade.side.upper()} {trade.quantity} {symbol}")
        else:
            logger.info("No trade signal - holding current position")
        
        # Disconnect
        trader.disconnect()
        logger.info("Live trading session complete!")
        
        return trader
        
    except Exception as e:
        logger.error(f"Live trading error: {e}")
        return None


def list_strategies():
    """List available strategies."""
    print("\nAvailable Strategies:")
    print("=" * 60)
    for name, strategy_class in STRATEGIES.items():
        print(f"  • {name}")
        print(f"    {strategy_class.__doc__.strip() if strategy_class.__doc__ else 'No description'}")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Modular Trading Bot - Backtest, Paper Trade, or Live Trade',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run backtest with SMA Crossover strategy
  python trading_bot.py --mode backtest --symbol AAPL --strategy sma_crossover
  
  # Run backtest and save report
  python trading_bot.py --mode backtest --symbol MSFT --strategy rsi --save-report --plot
  
  # Run paper trading
  python trading_bot.py --mode paper --symbol BTC-USD --strategy sma_crossover
  
  # List available strategies
  python trading_bot.py --list-strategies
        """
    )
    
    parser.add_argument('--mode', '-m',
                       choices=['backtest', 'paper', 'live'],
                       default='backtest',
                       help='Trading mode (default: backtest)')
    
    parser.add_argument('--symbol', '-s',
                       help='Trading symbol (e.g., AAPL, BTC-USD)')
    
    parser.add_argument('--strategy', '-st',
                       help='Strategy name')
    
    parser.add_argument('--interval', '-i',
                       help='Data interval (1m, 5m, 1h, 1d)')
    
    parser.add_argument('--config', '-c',
                       default='config.json',
                       help='Path to config file (default: config.json)')
    
    parser.add_argument('--save-report',
                       action='store_true',
                       help='Save results report')
    
    parser.add_argument('--save-data',
                       action='store_true',
                       help='Save downloaded market data')
    
    parser.add_argument('--plot',
                       action='store_true',
                       help='Generate equity curve plot (backtest only)')
    
    parser.add_argument('--list-strategies',
                       action='store_true',
                       help='List available strategies and exit')
    
    args = parser.parse_args()
    
    # List strategies and exit
    if args.list_strategies:
        list_strategies()
        return
    
    # Load configuration
    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}")
        print("Create a config.json file or use --config to specify path")
        sys.exit(1)
    
    config = load_config(args.config)
    
    # Setup logging
    logger = setup_logging(config['logging'])
    
    # Create necessary directories
    for directory in ['data', 'logs', 'reports']:
        os.makedirs(directory, exist_ok=True)
    
    # Run based on mode
    try:
        if args.mode == 'backtest':
            run_backtest_mode(args, config, logger)
        elif args.mode == 'paper':
            run_paper_mode(args, config, logger)
        elif args.mode == 'live':
            run_live_mode(args, config, logger)
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
    except Exception as e:
        logger.exception(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

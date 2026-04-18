"""
Backtest Module - Tests strategies on historical data
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from strategies import BaseStrategy


class Backtest:
    """
    Backtesting engine for trading strategies.
    
    Calculates performance metrics:
    - Win Rate
    - Profit Factor
    - Max Drawdown
    - Sharpe Ratio
    - Total Return
    """
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 commission: float = 0.001,
                 slippage: float = 0.0005):
        """
        Initialize backtester.
        
        Args:
            initial_capital (float): Starting capital
            commission (float): Commission per trade (0.001 = 0.1%)
            slippage (float): Slippage per trade (0.0005 = 0.05%)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.logger = logging.getLogger(__name__)
        
        # Results storage
        self.trades: List[Dict] = []
        self.equity_curve: pd.Series = None
        self.results: Dict[str, Any] = {}
    
    def run(self, 
            strategy: BaseStrategy, 
            data: pd.DataFrame,
            position_size: float = 1.0) -> Dict[str, Any]:
        """
        Run backtest with given strategy and data.
        
        Args:
            strategy (BaseStrategy): Trading strategy
            data (pd.DataFrame): OHLCV data
            position_size (float): Position size as fraction of capital (0-1)
        
        Returns:
            dict: Backtest results
        """
        self.logger.info(f"Running backtest with {strategy.name}")
        
        # Generate signals
        signals_df = strategy.generate_signals(data)
        
        # Initialize tracking variables
        capital = self.initial_capital
        position = 0
        shares = 0
        entry_price = 0
        self.trades = []
        equity_curve = []
        
        for i, (timestamp, row) in enumerate(signals_df.iterrows()):
            current_price = row['close']
            signal = row['signal']
            
            # Skip if no signal or NaN price
            if pd.isna(signal) or pd.isna(current_price):
                equity_curve.append({
                    'timestamp': timestamp,
                    'equity': capital,
                    'position': position
                })
                continue
            
            # Execute buy signal
            if signal == 1 and position == 0:
                position = 1
                # Calculate shares with commission/slippage
                adjusted_price = current_price * (1 + self.slippage + self.commission)
                shares = (capital * position_size) / adjusted_price
                entry_price = adjusted_price
                
                self.trades.append({
                    'timestamp': timestamp,
                    'type': 'buy',
                    'price': adjusted_price,
                    'shares': shares,
                    'capital_before': capital,
                    'capital_after': capital - (shares * adjusted_price)
                })
                
                capital = capital - (shares * adjusted_price)
            
            # Execute sell signal
            elif signal == -1 and position == 1:
                position = 0
                # Calculate exit with commission/slippage
                adjusted_price = current_price * (1 - self.slippage - self.commission)
                exit_value = shares * adjusted_price
                
                # Calculate P&L
                pnl = exit_value - (shares * entry_price)
                pnl_pct = (pnl / (shares * entry_price)) * 100
                
                self.trades.append({
                    'timestamp': timestamp,
                    'type': 'sell',
                    'price': adjusted_price,
                    'shares': shares,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'capital_before': capital,
                    'capital_after': capital + exit_value
                })
                
                capital = capital + exit_value
                shares = 0
            
            # Calculate current equity (mark to market)
            if position == 1:
                current_equity = capital + (shares * current_price)
            else:
                current_equity = capital
            
            equity_curve.append({
                'timestamp': timestamp,
                'equity': current_equity,
                'position': position
            })
        
        # Convert equity curve to DataFrame
        self.equity_curve = pd.DataFrame(equity_curve).set_index('timestamp')['equity']
        
        # Calculate metrics
        self.results = self._calculate_metrics()
        
        self.logger.info(f"Backtest complete. Total return: {self.results['total_return_pct']:.2f}%")
        
        return self.results
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics."""
        if self.equity_curve is None or len(self.equity_curve) == 0:
            return {}
        
        # Basic metrics
        final_equity = self.equity_curve.iloc[-1]
        total_return = final_equity - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Trade metrics
        completed_trades = [t for t in self.trades if t['type'] == 'sell']
        total_trades = len(completed_trades)
        
        if total_trades > 0:
            winning_trades = [t for t in completed_trades if t['pnl'] > 0]
            losing_trades = [t for t in completed_trades if t['pnl'] <= 0]
            
            win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
            
            gross_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
            gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            avg_win = gross_profit / len(winning_trades) if winning_trades else 0
            avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
        else:
            win_rate = 0
            profit_factor = 0
            avg_win = 0
            avg_loss = 0
        
        # Calculate returns for Sharpe ratio
        returns = self.equity_curve.pct_change().dropna()
        
        # Max drawdown
        rolling_max = self.equity_curve.expanding().max()
        drawdown = (self.equity_curve - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100  # Percentage
        
        # Sharpe ratio (annualized, assuming 252 trading days)
        if len(returns) > 1 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252) * 100 if len(returns) > 0 else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown_pct': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'volatility_annual_pct': volatility,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'num_winning_trades': len([t for t in self.trades if t.get('pnl', 0) > 0]),
            'num_losing_trades': len([t for t in self.trades if t.get('pnl', 0) <= 0])
        }
    
    def save_report(self, filepath: str, strategy_name: str = "Unknown") -> str:
        """
        Save backtest results to JSON report.
        
        Args:
            filepath (str): Path to save report
            strategy_name (str): Name of strategy tested
        
        Returns:
            str: Path to saved file
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy_name,
            'parameters': {
                'initial_capital': self.initial_capital,
                'commission': self.commission,
                'slippage': self.slippage
            },
            'results': self.results,
            'trades': [
                {**t, 'timestamp': t['timestamp'].isoformat() if hasattr(t['timestamp'], 'isoformat') else str(t['timestamp'])}
                for t in self.trades
            ]
        }
        
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Report saved to {filepath}")
        return filepath
    
    def plot_equity_curve(self, save_path: Optional[str] = None, show: bool = False):
        """
        Plot equity curve.
        
        Args:
            save_path (str): Path to save plot
            show (bool): Whether to display plot
        """
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            self.equity_curve.plot(ax=ax, label='Equity', color='blue')
            
            # Add buy/sell markers
            buy_trades = [t for t in self.trades if t['type'] == 'buy']
            sell_trades = [t for t in self.trades if t['type'] == 'sell']
            
            if buy_trades:
                buy_times = [t['timestamp'] for t in buy_trades]
                buy_equity = [self.equity_curve.loc[self.equity_curve.index.get_indexer([t], method='nearest')[0]] 
                              for t in buy_times]
                ax.scatter(buy_times, buy_equity, color='green', marker='^', 
                          s=100, label='Buy', zorder=5)
            
            if sell_trades:
                sell_times = [t['timestamp'] for t in sell_trades]
                sell_equity = [self.equity_curve.loc[self.equity_curve.index.get_indexer([t], method='nearest')[0]] 
                               for t in sell_times]
                ax.scatter(sell_times, sell_equity, color='red', marker='v', 
                          s=100, label='Sell', zorder=5)
            
            ax.set_title(f"Backtest Equity Curve")
            ax.set_xlabel("Date")
            ax.set_ylabel("Equity ($)")
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            if save_path:
                os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                self.logger.info(f"Plot saved to {save_path}")
            
            if show:
                plt.show()
            
            plt.close()
            
        except ImportError:
            self.logger.warning("matplotlib not installed, skipping plot")
    
    def get_summary(self) -> str:
        """Get formatted summary of backtest results."""
        if not self.results:
            return "No backtest results available"
        
        return f"""
╔══════════════════════════════════════════════════════════════╗
║                    BACKTEST RESULTS                            ║
╠══════════════════════════════════════════════════════════════╣
║  Initial Capital:    ${self.results['initial_capital']:,.2f}
║  Final Equity:       ${self.results['final_equity']:,.2f}
║  Total Return:        {self.results['total_return_pct']:+.2f}%
╠══════════════════════════════════════════════════════════════╣
║  Total Trades:        {self.results['total_trades']}
║  Win Rate:            {self.results['win_rate']:.2f}%
║  Profit Factor:       {self.results['profit_factor']:.2f}
║  Max Drawdown:        {self.results['max_drawdown_pct']:.2f}%
║  Sharpe Ratio:        {self.results['sharpe_ratio']:.2f}
║  Volatility (Ann.):   {self.results['volatility_annual_pct']:.2f}%
╚══════════════════════════════════════════════════════════════╝
        """


def run_backtest(strategy: BaseStrategy,
                 data: pd.DataFrame,
                 config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convenience function to run backtest.
    
    Args:
        strategy (BaseStrategy): Trading strategy
        data (pd.DataFrame): Market data
        config (dict): Backtest configuration
    
    Returns:
        dict: Backtest results
    """
    config = config or {}
    backtest = Backtest(
        initial_capital=config.get('initial_capital', 10000),
        commission=config.get('commission', 0.001),
        slippage=config.get('slippage', 0.0005)
    )
    
    results = backtest.run(strategy, data)
    return {
        'results': results,
        'backtest': backtest,
        'trades': backtest.trades,
        'equity_curve': backtest.equity_curve
    }

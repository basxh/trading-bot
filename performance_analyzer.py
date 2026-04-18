"""
Performance Analytics Module
Advanced performance metrics and visualizations
"""
import os
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np


class PerformanceAnalyzer:
    """
    Advanced performance analysis for trading strategies.
    
    Calculates:
    - Sharpe Ratio
    - Sortino Ratio
    - Calmar Ratio
    - Maximum Drawdown
    - VaR (Value at Risk)
    - Win Rate, Profit Factor
    - Trade statistics
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize analyzer.
        
        Args:
            risk_free_rate (float): Annual risk-free rate (e.g., 0.02 for 2%)
        """
        self.risk_free_rate = risk_free_rate
        self.logger = logging.getLogger(__name__)
    
    def analyze(self, 
                equity_curve: pd.Series,
                trades: List[Dict] = None,
                initial_capital: float = 10000.0) -> Dict[str, Any]:
        """
        Perform full analysis on equity curve.
        
        Args:
            equity_curve (pd.Series): Equity curve over time
            trades (list): List of completed trades
            initial_capital (float): Starting capital
            
        Returns:
            dict: Complete performance metrics
        """
        self.logger.info("Calculating performance metrics...")
        
        # Daily returns
        returns = equity_curve.pct_change().dropna()
        
        metrics = {
            'returns': self._calculate_return_metrics(equity_curve, initial_capital),
            'risk': self._calculate_risk_metrics(returns, equity_curve),
            'ratios': self._calculate_ratios(returns, equity_curve),
            'trades': self._calculate_trade_metrics(trades) if trades else {}
        }
        
        return metrics
    
    def _calculate_return_metrics(self, 
                                   equity_curve: pd.Series,
                                   initial_capital: float) -> Dict[str, float]:
        """Calculate return-based metrics."""
        final_value = equity_curve.iloc[-1]
        total_return = final_value - initial_capital
        total_return_pct = (total_return / initial_capital) * 100
        
        # Annualized return
        n_periods = len(equity_curve)
        n_years = n_periods / 252  # Assuming daily data
        annual_return_pct = (((final_value / initial_capital) ** (1 / n_years)) - 1) * 100 if n_years > 0 else 0
        
        returns = equity_curve.pct_change().dropna()
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'annualized_return_pct': annual_return_pct,
            'average_daily_return_pct': returns.mean() * 100,
            'best_day_pct': returns.max() * 100,
            'worst_day_pct': returns.min() * 100
        }
    
    def _calculate_risk_metrics(self, 
                                 returns: pd.Series,
                                 equity_curve: pd.Series) -> Dict[str, float]:
        """Calculate risk-based metrics."""
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252) * 100
        
        # Max drawdown
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100
        max_drawdown_date = drawdown.idxmin()
        
        # Max drawdown duration
        peak_idx = rolling_max.idxmax()
        trough_idx = drawdown.idxmin()
        
        # Value at Risk (95% confidence)
        var_95 = np.percentile(returns, 5) * 100
        var_99 = np.percentile(returns, 1) * 100
        
        # Conditional VaR (Expected Shortfall)
        cvar_95 = returns[returns <= np.percentile(returns, 5)].mean() * 100
        
        return {
            'volatility_annual_pct': volatility,
            'max_drawdown_pct': max_drawdown,
            'max_drawdown_date': str(max_drawdown_date),
            'var_95_pct': var_95,
            'var_99_pct': var_99,
            'cvar_95_pct': cvar_95,
            'skewness': returns.skew(),
            'kurtosis': returns.kurtosis()
        }
    
    def _calculate_ratios(self, 
                          returns: pd.Series,
                          equity_curve: pd.Series) -> Dict[str, float]:
        """Calculate risk-adjusted return ratios."""
        # Daily risk-free rate
        daily_rf = self.risk_free_rate / 252
        excess_returns = returns - daily_rf
        
        # Sharpe Ratio (annualized)
        sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252) if excess_returns.std() > 0 else 0
        
        # Sortino Ratio (only downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino = (returns.mean() - daily_rf) * 252 / downside_std if downside_std > 0 else 0
        
        # Calmar Ratio (annual return / max drawdown)
        final_value = equity_curve.iloc[-1]
        initial_value = equity_curve.iloc[0]
        n_years = len(equity_curve) / 252
        annual_return = ((final_value / initial_value) ** (1 / n_years)) - 1 if n_years > 0 else 0
        
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min())
        calmar = annual_return / max_drawdown if max_drawdown > 0 else 0
        
        # Information Ratio (excess return / tracking error)
        # Using zero as benchmark for absolute returns
        tracking_error = returns.std() * np.sqrt(252)
        information = (returns.mean() * 252) / tracking_error if tracking_error > 0 else 0
        
        # Omega Ratio
        threshold = 0
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns <= threshold].sum())
        omega = gains / losses if losses > 0 else float('inf')
        
        return {
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'calmar_ratio': calmar,
            'information_ratio': information,
            'omega_ratio': omega
        }
    
    def _calculate_trade_metrics(self, trades: List[Dict]) -> Dict[str, Any]:
        """Calculate trade-based metrics."""
        if not trades:
            return {}
        
        # Filter completed trades (sell orders with PnL)
        completed_trades = [t for t in trades if t.get('pnl') is not None]
        
        if not completed_trades:
            return {'total_trades': 0}
        
        # Basic counts
        total_trades = len(completed_trades)
        winning_trades = [t for t in completed_trades if t['pnl'] > 0]
        losing_trades = [t for t in completed_trades if t['pnl'] <= 0]
        
        win_rate = (len(winning_trades) / total_trades) * 100
        
        # PnL metrics
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        net_profit = gross_profit - gross_loss
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Average metrics
        avg_trade = net_profit / total_trades
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
        
        # Consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        
        for trade in completed_trades:
            if trade['pnl'] > 0:
                if current_streak > 0:
                    current_streak += 1
                else:
                    current_streak = 1
                max_win_streak = max(max_win_streak, current_streak)
            else:
                if current_streak < 0:
                    current_streak -= 1
                else:
                    current_streak = -1
                max_loss_streak = max(max_loss_streak, abs(current_streak))
        
        # Expectancy
        win_pct = len(winning_trades) / total_trades
        loss_pct = len(losing_trades) / total_trades
        expectancy = (win_pct * avg_win) - (loss_pct * avg_loss)
        
        # Trade duration (if timestamps available)
        # This would require entry/exit timestamps
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'net_profit': net_profit,
            'average_trade': avg_trade,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'largest_win': max(t['pnl'] for t in winning_trades) if winning_trades else 0,
            'largest_loss': min(t['pnl'] for t in losing_trades) if losing_trades else 0,
            'max_consecutive_wins': max_win_streak,
            'max_consecutive_losses': max_loss_streak,
            'expectancy': expectancy,
            'payoff_ratio': avg_win / abs(avg_loss) if avg_loss != 0 else float('inf')
        }
    
    def plot_equity_curve(self, 
                          equity_curve: pd.Series,
                          trades: List[Dict] = None,
                          save_path: str = None,
                          show: bool = False,
                          title: str = "Strategy Performance"):
        """
        Plot equity curve with trades.
        
        Args:
            equity_curve (pd.Series): Equity curve
            trades (list): Trades to mark
            save_path (str): Path to save plot
            show (bool): Show the plot
            title (str): Plot title
        """
        try:
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1, 1]})
            
            # Plot 1: Equity curve
            ax1 = axes[0]
            equity_curve.plot(ax=ax1, label='Equity', color='blue', linewidth=1.5)
            
            # Add buy/sell markers
            if trades:
                buy_trades = [t for t in trades if t['type'] == 'buy']
                sell_trades = [t for t in trades if t['type'] == 'sell']
                
                if buy_trades:
                    buy_times = [pd.to_datetime(t['timestamp']) for t in buy_trades]
                    buy_equity = [equity_curve.loc[equity_curve.index.get_indexer([t], method='nearest')[0]] 
                                  for t in buy_times]
                    ax1.scatter(buy_times, buy_equity, color='green', marker='^', 
                               s=80, label='Buy', zorder=5, alpha=0.7)
                
                if sell_trades:
                    sell_times = [pd.to_datetime(t['timestamp']) for t in sell_trades]
                    sell_equity = [equity_curve.loc[equity_curve.index.get_indexer([t], method='nearest')[0]] 
                                   for t in sell_times]
                    ax1.scatter(sell_times, sell_equity, color='red', marker='v', 
                               s=80, label='Sell', zorder=5, alpha=0.7)
            
            ax1.axhline(y=equity_curve.iloc[0], color='gray', linestyle='--', alpha=0.5, label='Start')
            ax1.set_title(title, fontsize=14, fontweight='bold')
            ax1.set_ylabel('Equity ($)')
            ax1.legend(loc='upper left')
            ax1.grid(True, alpha=0.3)
            
            # Plot 2: Drawdown
            ax2 = axes[1]
            rolling_max = equity_curve.expanding().max()
            drawdown = (equity_curve - rolling_max) / rolling_max * 100
            drawdown.plot(ax=ax2, color='red', alpha=0.7, fill_between=True)
            ax2.fill_between(drawdown.index, drawdown, 0, color='red', alpha=0.3)
            ax2.set_ylabel('Drawdown (%)')
            ax2.set_title('Drawdown Analysis')
            ax2.grid(True, alpha=0.3)
            
            # Plot 3: Returns distribution
            ax3 = axes[2]
            returns = equity_curve.pct_change().dropna() * 100
            ax3.hist(returns, bins=50, color='blue', alpha=0.5, edgecolor='black')
            ax3.axvline(returns.mean(), color='green', linestyle='--', label=f'Mean: {returns.mean():.2f}%')
            ax3.axvline(0, color='red', linestyle='--', alpha=0.5)
            ax3.set_xlabel('Daily Return (%)')
            ax3.set_ylabel('Frequency')
            ax3.set_title('Returns Distribution')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                self.logger.info(f"Plot saved to {save_path}")
            
            if show:
                plt.show()
            
            plt.close()
            
        except ImportError:
            self.logger.warning("matplotlib not installed, skipping plot")
    
    def generate_report(self, metrics: Dict[str, Any], 
                        save_path: str = None) -> str:
        """
        Generate formatted text report.
        
        Args:
            metrics (dict): Performance metrics
            save_path (str): Path to save report
            
        Returns:
            str: Formatted report
        """
        returns = metrics.get('returns', {})
        risk = metrics.get('risk', {})
        ratios = metrics.get('ratios', {})
        trades = metrics.get('trades', {})
        
        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    PERFORMANCE ANALYSIS REPORT                      ║
╠══════════════════════════════════════════════════════════════════╣
║  📊 RETURN METRICS
╠══════════════════════════════════════════════════════════════════╣
║  Initial Capital:     ${returns.get('initial_capital', 0):,.2f}
║  Final Value:        ${returns.get('final_value', 0):,.2f}
║  Total Return:        {returns.get('total_return_pct', 0):+.2f}%
║  Annualized Return:    {returns.get('annualized_return_pct', 0):.2f}%
║  Average Daily:        {returns.get('average_daily_return_pct', 0):+.3f}%
║  Best Day:             {returns.get('best_day_pct', 0):+.2f}%
║  Worst Day:            {returns.get('worst_day_pct', 0):+.2f}%
╠══════════════════════════════════════════════════════════════════╣
║  ⚠️  RISK METRICS
╠══════════════════════════════════════════════════════════════════╣
║  Volatility (Annual):  {risk.get('volatility_annual_pct', 0):.2f}%
║  Max Drawdown:         {risk.get('max_drawdown_pct', 0):.2f}%
║  VaR (95%):            {risk.get('var_95_pct', 0):.2f}%
║  CVaR (95%):           {risk.get('cvar_95_pct', 0):.2f}%
║  Skewness:             {risk.get('skewness', 0):.3f}
║  Kurtosis:             {risk.get('kurtosis', 0):.3f}
╠══════════════════════════════════════════════════════════════════╣
║  📈 RISK-ADJUSTED RATIOS
╠══════════════════════════════════════════════════════════════════╣
║  Sharpe Ratio:        {ratios.get('sharpe_ratio', 0):.3f}
║  Sortino Ratio:        {ratios.get('sortino_ratio', 0):.3f}
║  Calmar Ratio:         {ratios.get('calmar_ratio', 0):.3f}
║  Information Ratio:    {ratios.get('information_ratio', 0):.3f}
║  Omega Ratio:          {ratios.get('omega_ratio', 0):.3f}
╠══════════════════════════════════════════════════════════════════╣
║  💰 TRADE STATISTICS
╠══════════════════════════════════════════════════════════════════╣
║  Total Trades:         {trades.get('total_trades', 0)}
║  Win Rate:             {trades.get('win_rate', 0):.2f}%
║  Profit Factor:        {trades.get('profit_factor', 0):.2f}
║  Net Profit:          ${trades.get('net_profit', 0):,.2f}
║  Average Trade:       ${trades.get('average_trade', 0):,.2f}
║  Average Win:         ${trades.get('average_win', 0):,.2f}
║  Average Loss:         ${trades.get('average_loss', 0):,.2f}
║  Payoff Ratio:         {trades.get('payoff_ratio', 0):.2f}
║  Expectancy:          ${trades.get('expectancy', 0):,.2f}
║  Max Win Streak:       {trades.get('max_consecutive_wins', 0)}
║  Max Loss Streak:      {trades.get('max_consecutive_losses', 0)}
╚══════════════════════════════════════════════════════════════════╝
"""
        
        if save_path:
            os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
            with open(save_path, 'w') as f:
                f.write(report)
            self.logger.info(f"Report saved to {save_path}")
        
        return report


def analyze_backtest_results(filepath: str, 
                              risk_free_rate: float = 0.02,
                              save_path: str = None) -> Dict[str, Any]:
    """
    Analyze backtest results from JSON file.
    
    Args:
        filepath (str): Path to backtest results JSON
        risk_free_rate (float): Risk-free rate
        save_path (str): Path to save analysis
        
    Returns:
        dict: Analysis results
    """
    logging.basicConfig(level=logging.INFO)
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Load equity curve
    trades = data.get('trades', [])
    
    # Reconstruct equity curve from trades
    # This is simplified - actual implementation would need full equity data
    initial_capital = data.get('results', {}).get('initial_capital', 10000)
    final_equity = data.get('results', {}).get('final_equity', initial_capital)
    
    # Create simple equity curve from trades
    dates = [pd.to_datetime(t['timestamp']) for t in trades]
    equity_values = [initial_capital]
    for t in trades:
        if t['type'] == 'sell':
            equity_values.append(t['capital_after'])
    
    # Simple equity curve
    equity_curve = pd.Series([initial_capital, final_equity], 
                              index=pd.date_range(start='2020-01-01', periods=2, freq='D'))
    
    # Create analyzer
    analyzer = PerformanceAnalyzer(risk_free_rate=risk_free_rate)
    
    # Calculate metrics
    metrics = analyzer.analyze(equity_curve, trades, initial_capital)
    
    # Add original results
    metrics['original_results'] = data.get('results', {})
    
    # Generate report
    report = analyzer.generate_report(metrics)
    print(report)
    
    if save_path:
        output = {
            'timestamp': datetime.now().isoformat(),
            'source_file': filepath,
            'analysis': metrics
        }
        with open(save_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
    
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Performance Analyzer')
    parser.add_argument('--backtest-results', type=str, required=True,
                        help='Path to backtest results JSON file')
    parser.add_argument('--risk-free-rate', type=float, default=0.02,
                        help='Annual risk-free rate')
    parser.add_argument('--save-report', type=str, default=None,
                        help='Path to save report')
    parser.add_argument('--save-plot', type=str, default=None,
                        help='Path to save equity curve plot')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.backtest_results):
        print(f"Error: File not found: {args.backtest_results}")
        exit(1)
    
    metrics = analyze_backtest_results(
        filepath=args.backtest_results,
        risk_free_rate=args.risk_free_rate,
        save_path=args.save_report
    )
    
    print("\n✅ Analysis complete!")

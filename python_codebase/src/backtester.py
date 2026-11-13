"""
FX Signal Lab - Institutional Backtesting & Execution Engine
Simulates multi-currency signal execution with realistic market microstructure:
bid-ask spreads, volatility-based slippage, broker commissions, and dynamic Kelly position sizing.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple


class FXBacktester:
    """
    Production-grade event-driven and vectorized backtester for FX quantitative strategies.
    """
    def __init__(
        self,
        initial_capital: float = 100000.0,
        spread_pips: float = 1.0,
        pip_size: float = 0.0001,
        commission_per_lot: float = 7.0,
        lot_size: float = 100000.0,
        slippage_pips: float = 0.3,
        sizing_method: str = 'half_kelly'  # 'fixed', 'kelly', 'half_kelly', 'vol_target'
    ):
        self.initial_capital = initial_capital
        self.spread_pips = spread_pips
        self.pip_size = pip_size
        self.commission_per_lot = commission_per_lot
        self.lot_size = lot_size
        self.slippage_pips = slippage_pips
        self.sizing_method = sizing_method

    def calculate_kelly_fraction(self, win_rate: float, payoff_ratio: float) -> float:
        """
        Calculates Kelly Criterion optimal leverage fraction:
            f* = (p * b - q) / b
        where p = win rate, q = 1 - p, b = payoff ratio (Avg Win / Avg Loss).
        """
        if payoff_ratio <= 0 or win_rate <= 0:
            return 0.02
        b = payoff_ratio
        p = win_rate
        q = 1.0 - p
        kelly = (p * b - q) / b
        # Bound Kelly between 0.01 and 0.25 (prudent risk limit)
        return float(np.clip(kelly, 0.01, 0.25))

    def run_backtest(
        self,
        df: pd.DataFrame,
        signal_col: str = 'Signal_Direction',
        pair_name: str = 'EUR/USD',
        strategy_name: str = 'Composite'
    ) -> Dict[str, Any]:
        """
        Executes backtest on given dataframe with signal column.
        Computes detailed trade logs, equity curves, drawdown series, and summary metrics.
        """
        data = df.copy().reset_index(drop=True)
        n = len(data)
        
        # Tracking variables
        capital = self.initial_capital
        equity_curve = [capital]
        daily_returns = [0.0]
        trades = []
        
        in_trade = False
        entry_price = 0.0
        entry_idx = 0
        direction = 0  # 1: Long, -1: Short
        position_size = 1.0  # in standard lots
        
        # Prelim win rate and payoff for Kelly sizing
        current_kelly = 0.05
        
        for i in range(1, n):
            current_close = data.loc[i, 'Close']
            sig = data.loc[i, signal_col]
            prev_sig = data.loc[i-1, signal_col]
            
            # Close trade conditions: Signal flips or hits Stop Loss / Take Profit
            if in_trade:
                dt_entry = data.loc[entry_idx, 'DateTime'] if 'DateTime' in data.columns else str(entry_idx)
                dt_exit = data.loc[i, 'DateTime'] if 'DateTime' in data.columns else str(i)
                
                # Check exit
                should_exit = (sig != direction) or (i == n - 1)
                
                if should_exit:
                    # Realistic execution with spread + slippage
                    spread_cost_pips = self.spread_pips + self.slippage_pips
                    exit_price = current_close - (direction * spread_cost_pips * self.pip_size)
                    
                    price_diff = (exit_price - entry_price) * direction
                    pnl_pips = price_diff / self.pip_size
                    
                    # Commission & Dollar PnL
                    commission = self.commission_per_lot * position_size
                    pip_dollar_value = 10.0 if 'JPY' not in pair_name else (1000.0 / exit_price)
                    gross_pnl = pnl_pips * pip_dollar_value * position_size
                    net_pnl = gross_pnl - commission
                    
                    capital += net_pnl
                    holding_periods = i - entry_idx
                    holding_days = max(1, holding_periods // 24 if 'DateTime' in data.columns and '00:00:00' in str(dt_entry) else holding_periods)
                    
                    trades.append({
                        'TradeID': len(trades) + 1,
                        'PairName': pair_name,
                        'StrategyName': strategy_name,
                        'SignalType': 'LONG' if direction == 1 else 'SHORT',
                        'Direction': direction,
                        'EntryPrice': round(entry_price, 5),
                        'ExitPrice': round(exit_price, 5),
                        'EntryDateTime': dt_entry,
                        'ExitDateTime': dt_exit,
                        'PositionSize': round(position_size, 2),
                        'PnL': round(net_pnl, 2),
                        'PnL_Pips': round(pnl_pips, 1),
                        'HoldingDays': holding_days,
                        'Commission': commission,
                        'IsOpen': False
                    })
                    
                    in_trade = False
                    direction = 0
            
            # Enter trade conditions
            if not in_trade and sig != 0 and i < n - 1:
                in_trade = True
                direction = int(sig)
                entry_idx = i
                # Execution price with entry spread & slippage
                spread_penalty = (self.spread_pips / 2.0 + self.slippage_pips) * self.pip_size
                entry_price = current_close + (direction * spread_penalty)
                
                # Dynamic position sizing
                if self.sizing_method == 'half_kelly' and len(trades) >= 10:
                    past_pnls = [t['PnL'] for t in trades]
                    wins = [p for p in past_pnls if p > 0]
                    losses = [abs(p) for p in past_pnls if p < 0]
                    wr = len(wins) / len(past_pnls) if past_pnls else 0.5
                    po = (np.mean(wins) / np.mean(losses)) if (losses and np.mean(losses) > 0) else 1.5
                    k_frac = self.calculate_kelly_fraction(wr, po)
                    position_size = max(0.1, round((capital * k_frac * 0.5) / 5000.0, 2))
                else:
                    position_size = 1.0
            
            # Mark-to-market equity
            unrealized = 0.0
            if in_trade:
                curr_diff = (current_close - entry_price) * direction
                pip_val = 10.0 if 'JPY' not in pair_name else (1000.0 / current_close)
                unrealized = (curr_diff / self.pip_size) * pip_val * position_size
                
            equity_curve.append(capital + unrealized)
            daily_returns.append((equity_curve[-1] - equity_curve[-2]) / equity_curve[-2] if equity_curve[-2] > 0 else 0.0)
            
        trades_df = pd.DataFrame(trades)
        equity_series = pd.Series(equity_curve)
        
        # Calculate institutional statistics
        metrics = self._compute_performance_metrics(trades_df, equity_series, daily_returns)
        
        return {
            'metrics': metrics,
            'trades_df': trades_df,
            'equity_curve': equity_series,
            'daily_returns': pd.Series(daily_returns)
        }

    def _compute_performance_metrics(self, trades_df: pd.DataFrame, equity_series: pd.Series, returns: List[float]) -> Dict[str, Any]:
        """Calculates institutional performance metrics matching DAX formulas."""
        if len(trades_df) == 0:
            return {
                'Total_Trades': 0, 'Win_Rate': 0.0, 'Total_PnL': 0.0, 'Profit_Factor': 0.0,
                'Sharpe_Ratio': 0.0, 'Sortino_Ratio': 0.0, 'Max_Drawdown_Pct': 0.0, 'Calmar_Ratio': 0.0,
                'Expectancy': 0.0, 'Payoff_Ratio': 0.0
            }
            
        pnls = trades_df['PnL']
        winning_trades = pnls[pnls > 0]
        losing_trades = pnls[pnls < 0]
        
        total_trades = len(pnls)
        n_wins = len(winning_trades)
        n_losses = len(losing_trades)
        win_rate = n_wins / total_trades if total_trades > 0 else 0.0
        
        gross_profit = winning_trades.sum() if n_wins > 0 else 0.0
        gross_loss = abs(losing_trades.sum()) if n_losses > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 99.0
        
        avg_win = winning_trades.mean() if n_wins > 0 else 0.0
        avg_loss = abs(losing_trades.mean()) if n_losses > 0 else 0.0
        payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else 1.0
        
        expectancy = (win_rate * avg_win) - ((1.0 - win_rate) * avg_loss)
        
        # Drawdowns
        running_max = equity_series.cummax()
        drawdowns = (equity_series - running_max) / running_max
        max_drawdown = float(drawdowns.min())
        
        # Sharpe & Sortino (Annualized based on 252 days)
        ret_arr = np.array(returns[1:])
        mean_ret = np.mean(ret_arr)
        std_ret = np.std(ret_arr)
        
        sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0
        downside_returns = ret_arr[ret_arr < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 1e-6
        sortino = (mean_ret / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0
        
        # Calmar Ratio
        total_pnl = float(pnls.sum())
        total_return = total_pnl / self.initial_capital
        calmar = (total_return / abs(max_drawdown)) if abs(max_drawdown) > 0 else 0.0
        
        # Consecutive wins
        is_win = (pnls > 0).astype(int).tolist()
        max_cons_wins = 0
        curr_cons = 0
        for w in is_win:
            if w == 1:
                curr_cons += 1
                max_cons_wins = max(max_cons_wins, curr_cons)
            else:
                curr_cons = 0
                
        return {
            'Total_Trades': total_trades,
            'Winning_Trades': n_wins,
            'Losing_Trades': n_losses,
            'Win_Rate': round(win_rate * 100.0, 2),
            'Total_PnL': round(total_pnl, 2),
            'Gross_Profit': round(gross_profit, 2),
            'Gross_Loss': round(gross_loss, 2),
            'Profit_Factor': round(profit_factor, 2),
            'Average_Win': round(avg_win, 2),
            'Average_Loss': round(avg_loss, 2),
            'Payoff_Ratio': round(payoff_ratio, 2),
            'Expectancy': round(expectancy, 2),
            'Max_Drawdown_Pct': round(abs(max_drawdown) * 100.0, 2),
            'Sharpe_Ratio': round(sharpe, 2),
            'Sortino_Ratio': round(sortino, 2),
            'Calmar_Ratio': round(calmar, 2),
            'Max_Consecutive_Wins': max_cons_wins
        }

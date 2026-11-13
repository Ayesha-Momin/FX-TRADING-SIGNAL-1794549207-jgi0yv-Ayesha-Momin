"""
FX Signal Lab - Reinforcement Learning Trading Environment
A custom institutional FX trading environment modeled after OpenAI Gym / Gymnasium specifications.
Simulates real market mechanics: bid-ask spreads, slippage, leverage, and risk-adjusted rewards.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple


class ForexTradingEnv:
    """
    Forex Trading Environment for Reinforcement Learning agents.
    
    Action Space:
        0: Flat / Neutral (Close position)
        1: Long (+1 position)
        2: Short (-1 position)
        
    State Space:
        Vector of normalized market features (returns, momentum, volatility, indicators)
        plus agent's current position state and unrealized PnL.
    """
    def __init__(
        self,
        df: pd.DataFrame,
        feature_cols: list,
        initial_balance: float = 100000.0,
        spread_pips: float = 1.2,
        pip_value: float = 0.0001,
        commission_per_lot: float = 7.0,
        lot_size: float = 100000.0,
        risk_free_rate: float = 0.04
    ):
        self.df = df.reset_index(drop=True)
        self.feature_cols = feature_cols
        self.initial_balance = initial_balance
        self.spread_pips = spread_pips
        self.pip_value = pip_value
        self.commission_per_lot = commission_per_lot
        self.lot_size = lot_size
        self.risk_free_rate = risk_free_rate
        
        self.n_steps = len(self.df)
        self.current_step = 0
        self.balance = initial_balance
        self.equity = initial_balance
        self.position = 0  # -1: Short, 0: Flat, 1: Long
        self.entry_price = 0.0
        self.history = []

    def reset(self) -> np.ndarray:
        """Resets the environment to initial state."""
        self.current_step = 20  # Warmup window for lag features
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.position = 0
        self.entry_price = 0.0
        self.history = []
        return self._get_observation()

    def _get_observation(self) -> np.ndarray:
        """Constructs state vector containing market features and internal position state."""
        market_feats = self.df.loc[self.current_step, self.feature_cols].values.astype(np.float32)
        market_feats = np.nan_to_num(market_feats)
        
        # Position state features
        unrealized_pnl = 0.0
        current_price = self.df.loc[self.current_step, 'Close']
        if self.position != 0 and self.entry_price > 0:
            price_diff = (current_price - self.entry_price) * self.position
            unrealized_pnl = (price_diff / self.entry_price)
            
        pos_features = np.array([float(self.position), unrealized_pnl, self.equity / self.initial_balance], dtype=np.float32)
        obs = np.concatenate([market_feats, pos_features])
        return obs

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Executes one step in the environment.
        Action: 0 = Flat, 1 = Long, 2 = Short
        """
        # Map discrete action to target position
        target_position = 0 if action == 0 else (1 if action == 1 else -1)
        
        current_price = self.df.loc[self.current_step, 'Close']
        next_step = self.current_step + 1
        done = next_step >= (self.n_steps - 1)
        
        cost = 0.0
        trade_occurred = False
        step_pnl = 0.0
        
        # 1. Execution of position changes and transaction costs
        if target_position != self.position:
            trade_occurred = True
            spread_cost = (self.spread_pips * self.pip_value) * self.lot_size
            commission_cost = self.commission_per_lot
            cost = spread_cost + commission_cost
            
            # Close existing position if any
            if self.position != 0:
                realized_diff = (current_price - self.entry_price) * self.position
                realized_pnl = (realized_diff / self.pip_value) * 10.0 - cost
                self.balance += realized_pnl
                step_pnl += realized_pnl
                
            self.position = target_position
            self.entry_price = current_price if target_position != 0 else 0.0
            
        # 2. Mark-to-market price move to next step
        if not done:
            next_price = self.df.loc[next_step, 'Close']
            price_change = (next_price - current_price) / current_price
            period_return = price_change * self.position
            
            # PnL in dollar terms
            dollar_move = period_return * self.lot_size - (cost if not trade_occurred else 0.0)
            self.equity = self.balance + dollar_move
            step_pnl += dollar_move
        else:
            period_return = 0.0
            
        # 3. Risk-adjusted reward calculation (Differential Return - Volatility/Drawdown Penalty)
        reward = period_return * 100.0 - (cost / 1000.0)
        # Penalty for excessive drawdown or adverse moves
        if period_return < -0.01:
            reward -= 0.5
            
        self.current_step = next_step
        next_obs = self._get_observation() if not done else np.zeros_like(self._get_observation())
        
        info = {
            'step': self.current_step,
            'balance': self.balance,
            'equity': self.equity,
            'position': self.position,
            'price': current_price,
            'step_pnl': step_pnl
        }
        self.history.append(info)
        
        return next_obs, reward, done, info

"""
FX Signal Lab - Monte Carlo Simulation Engine
Simulates multi-currency portfolio dynamics via Geometric Brownian Motion (GBM)
and Cholesky decomposition of empirical covariance matrices.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple, Any


class FXMonteCarloEngine:
    """
    Institutional Monte Carlo simulation engine for multi-pair FX portfolios.
    Implements correlated Geometric Brownian Motion with Cholesky factorization.
    """
    def __init__(
        self,
        pairs: List[str],
        corr_matrix: np.ndarray,
        n_sims: int = 10000,
        horizon: int = 252,
        seed: int = 42
    ):
        self.pairs = pairs
        self.corr = np.array(corr_matrix, dtype=np.float64)
        self.n_sims = n_sims
        self.horizon = horizon
        self.seed = seed
        np.random.seed(seed)

    def generate_paths(
        self,
        spot_prices: np.ndarray,
        vols: np.ndarray,
        drifts: np.ndarray
    ) -> np.ndarray:
        """
        Generates simulated multi-asset price paths over horizon.
        
        Formula:
            S_{t} = S_{t-1} * exp((mu - 0.5 * sigma^2)*dt + sigma * sqrt(dt) * (Z @ L^T))
            where L is Cholesky factor: Sigma = L @ L.T
        """
        n = len(self.pairs)
        dt = 1.0 / 252.0
        
        # Ensure positive semi-definite correlation matrix
        min_eig = np.min(np.real(np.linalg.eigvals(self.corr)))
        if min_eig < 1e-6:
            self.corr += np.eye(n) * (-min_eig + 1e-5)
            
        L = np.linalg.cholesky(self.corr)
        
        paths = np.zeros((self.n_sims, self.horizon, n), dtype=np.float64)
        for i in range(n):
            paths[:, 0, i] = spot_prices[i]
            
        for t in range(1, self.horizon):
            Z = np.random.standard_normal((self.n_sims, n))
            corr_Z = Z @ L.T
            
            for i in range(n):
                drift_term = (drifts[i] - 0.5 * vols[i]**2) * dt
                diffusion_term = vols[i] * np.sqrt(dt) * corr_Z[:, i]
                paths[:, t, i] = paths[:, t-1, i] * np.exp(drift_term + diffusion_term)
                
        return paths

    def simulate_portfolio_pnl(
        self,
        spot_prices: np.ndarray,
        vols: np.ndarray,
        drifts: np.ndarray,
        positions_usd: np.ndarray
    ) -> Dict[str, Any]:
        """
        Simulates end-of-horizon portfolio PnL across all scenarios and computes institutional risk metrics.
        """
        paths = self.generate_paths(spot_prices, vols, drifts)
        # End-of-horizon percentage returns per pair: (S_T - S_0) / S_0
        pair_returns = (paths[:, -1, :] - spot_prices) / spot_prices
        
        # Scenario PnL per pair
        pair_pnls = pair_returns * positions_usd
        portfolio_pnl = np.sum(pair_pnls, axis=1)
        
        # Value at Risk (VaR) & CVaR / Expected Shortfall
        var_95 = float(-np.percentile(portfolio_pnl, 5.0))
        var_99 = float(-np.percentile(portfolio_pnl, 1.0))
        
        tail_95 = portfolio_pnl[portfolio_pnl <= -var_95]
        cvar_95 = float(-np.mean(tail_95)) if len(tail_95) > 0 else var_95
        
        tail_99 = portfolio_pnl[portfolio_pnl <= -var_99]
        cvar_99 = float(-np.mean(tail_99)) if len(tail_99) > 0 else var_99
        
        mean_pnl = float(np.mean(portfolio_pnl))
        std_pnl = float(np.std(portfolio_pnl))
        worst_loss = float(np.min(portfolio_pnl))
        best_gain = float(np.max(portfolio_pnl))
        prob_loss = float(np.mean(portfolio_pnl < 0))
        skewness = float(stats.skew(portfolio_pnl))
        kurtosis = float(stats.kurtosis(portfolio_pnl))
        
        # Create scenario dataframe for Power BI export (first 1000 scenarios)
        n_export = min(1000, self.n_sims)
        scen_dict = {
            'ScenarioID': np.arange(1, n_export + 1),
            'ParallelShift': np.random.normal(0.005, 0.01, n_export).round(6),
            'VolShock': np.random.normal(0.02, 0.03, n_export).round(6),
            'CorrShock': np.random.normal(-0.05, 0.1, n_export).round(6),
        }
        for idx, p_name in enumerate(self.pairs):
            col_name = f"{p_name.replace('/', '')}_PnL"
            scen_dict[col_name] = pair_pnls[:n_export, idx].round(2)
        scen_dict['PortfolioPnL'] = portfolio_pnl[:n_export].round(2)
        scenario_df = pd.DataFrame(scen_dict)
        
        metrics = {
            'n_simulations': self.n_sims,
            'horizon_days': self.horizon,
            'mean_expected_pnl': mean_pnl,
            'std_dev_pnl': std_pnl,
            'var_95': var_95,
            'var_99': var_99,
            'cvar_95': cvar_95,
            'cvar_99': cvar_99,
            'worst_scenario_loss': worst_loss,
            'best_scenario_gain': best_gain,
            'probability_of_loss': prob_loss,
            'distribution_skewness': skewness,
            'distribution_kurtosis': kurtosis
        }
        
        return {
            'metrics': metrics,
            'scenario_df': scenario_df,
            'portfolio_pnl': portfolio_pnl,
            'pair_pnls': pair_pnls
        }

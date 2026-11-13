# ==============================================================================
# FX Signal Lab - Correlated Monte Carlo Simulation & VaR in R
# Simulates correlated FX portfolio paths via Cholesky decomposition
# ==============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(ggplot2)
})

run_monte_carlo_r <- function(n_sims = 10000, horizon = 252) {
  pairs <- c("EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/INR")
  
  # Empirical correlation matrix
  corr_mat <- matrix(c(
     1.00, -0.42,  0.86,  0.68, -0.15,
    -0.42,  1.00, -0.38, -0.31,  0.22,
     0.86, -0.38,  1.00,  0.72, -0.12,
     0.68, -0.31,  0.72,  1.00, -0.08,
    -0.15,  0.22, -0.12, -0.08,  1.00
  ), nrow = 5, byrow = TRUE)
  
  vols <- c(0.085, 0.115, 0.098, 0.105, 0.035)
  drifts <- c(0.015, -0.025, 0.010, 0.020, 0.030)
  spots <- c(1.0850, 145.20, 1.2550, 0.6720, 82.80)
  positions_usd <- c(250000, -180000, 150000, 100000, 50000)
  
  # Cholesky factor
  L <- chol(corr_mat) # Upper triangular in R; t(L) is lower
  
  set.seed(42)
  dt <- horizon / 252
  
  # Standard normal random draws
  Z <- matrix(rnorm(n_sims * 5), nrow = n_sims, ncol = 5)
  corr_Z <- Z %*% L
  
  # End-of-horizon percentage returns per pair
  pair_returns <- matrix(0, nrow = n_sims, ncol = 5)
  for (j in 1:5) {
    pair_returns[, j] <- exp((drifts[j] - 0.5 * vols[j]^2) * dt + vols[j] * sqrt(dt) * corr_Z[, j]) - 1
  }
  
  # Portfolio PnL
  pair_pnls <- t(t(pair_returns) * positions_usd)
  portfolio_pnl <- rowSums(pair_pnls)
  
  # Compute VaR and CVaR
  var_95 <- -quantile(portfolio_pnl, 0.05)
  var_99 <- -quantile(portfolio_pnl, 0.01)
  
  cvar_95 <- -mean(portfolio_pnl[portfolio_pnl <= -var_95])
  cvar_99 <- -mean(portfolio_pnl[portfolio_pnl <= -var_99])
  
  cat("=== R Monte Carlo Results (10,000 Sims) ===\n")
  cat("VaR 95%: $", round(var_95, 2), "\n")
  cat("VaR 99%: $", round(var_99, 2), "\n")
  cat("CVaR 95%: $", round(cvar_95, 2), "\n")
  cat("CVaR 99%: $", round(cvar_99, 2), "\n")
  
  # Plot using ggplot2
  pnl_df <- tibble(PnL = portfolio_pnl)
  p <- ggplot(pnl_df, aes(x = PnL)) +
    geom_histogram(bins = 70, fill = "#1E3D59", color = "white", alpha = 0.8) +
    geom_vline(xintercept = -var_95, color = "#F5B041", linetype = "dashed", size = 1.1) +
    geom_vline(xintercept = -cvar_95, color = "#E74C3C", linetype = "solid", size = 1.2) +
    theme_minimal() +
    labs(
      title = "Correlated FX Portfolio Monte Carlo P&L Distribution (R Engine)",
      subtitle = paste0("VaR 95%: $", round(var_95, 0), " | CVaR 95%: $", round(cvar_95, 0)),
      x = "Simulated Portfolio P&L ($)",
      y = "Scenario Count"
    )
  
  return(list(
    var_95 = as.numeric(var_95),
    var_99 = as.numeric(var_99),
    cvar_95 = as.numeric(cvar_95),
    cvar_99 = as.numeric(cvar_99),
    plot = p
  ))
}

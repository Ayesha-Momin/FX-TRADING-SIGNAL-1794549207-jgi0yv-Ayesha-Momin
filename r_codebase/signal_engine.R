# ==============================================================================
# FX Signal Lab - R Signal Generation Engine
# Category: Quantitative Finance | FX Markets | Technical Analysis
# Replicates core signal generation in R using tidyverse, TTR, and quantmod
# ==============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(lubridate)
})

# ------------------------------------------------------------------------------
# 1. Technical Indicators Library
# ------------------------------------------------------------------------------

calculate_sma_r <- function(x, n = 20) {
  stats::filter(x, rep(1/n, n), sides = 1) %>% as.numeric()
}

calculate_ema_r <- function(x, n = 20, alpha = 2 / (n + 1)) {
  y <- numeric(length(x))
  y[1] <- x[1]
  for (i in 2:length(x)) {
    if (is.na(x[i])) {
      y[i] <- y[i-1]
    } else {
      y[i] <- alpha * x[i] + (1 - alpha) * y[i-1]
    }
  }
  return(y)
}

calculate_rsi_r <- function(x, n = 14) {
  delta <- c(NA, diff(x))
  gain <- ifelse(delta > 0, delta, 0)
  loss <- ifelse(delta < 0, -delta, 0)
  
  avg_gain <- calculate_ema_r(gain, n = n, alpha = 1 / n)
  avg_loss <- calculate_ema_r(loss, n = n, alpha = 1 / n)
  
  rs <- avg_gain / ifelse(avg_loss == 0, 1e-6, avg_loss)
  rsi <- 100 - (100 / (1 + rs))
  rsi[is.na(rsi)] <- 50
  return(rsi)
}

calculate_macd_r <- function(x, fast = 12, slow = 26, signal = 9) {
  ema_fast <- calculate_ema_r(x, n = fast)
  ema_slow <- calculate_ema_r(x, n = slow)
  macd_line <- ema_fast - ema_slow
  signal_line <- calculate_ema_r(macd_line, n = signal)
  histogram <- macd_line - signal_line
  
  tibble(
    MACD_Line = macd_line,
    MACD_Signal = signal_line,
    MACD_Hist = histogram
  )
}

calculate_bollinger_bands_r <- function(x, n = 20, num_std = 2.0) {
  middle <- calculate_sma_r(x, n = n)
  rolling_sd <- numeric(length(x))
  for (i in n:length(x)) {
    rolling_sd[i] <- sd(x[(i - n + 1):i], na.rm = TRUE)
  }
  
  upper <- middle + num_std * rolling_sd
  lower <- middle - num_std * rolling_sd
  pct_b <- (x - lower) / (upper - lower)
  bandwidth <- (upper - lower) / middle
  
  tibble(
    BB_Upper = upper,
    BB_Middle = middle,
    BB_Lower = lower,
    BB_PctB = pct_b,
    BB_Bandwidth = bandwidth
  )
}

# ------------------------------------------------------------------------------
# 2. Composite Signal Engine (Weighted Voting)
# ------------------------------------------------------------------------------

evaluate_composite_signals_r <- function(df) {
  # Add indicators
  df <- df %>%
    mutate(
      SMA_10 = calculate_sma_r(Close, 10),
      SMA_50 = calculate_sma_r(Close, 50),
      EMA_50 = calculate_ema_r(Close, 50),
      RSI_14 = calculate_rsi_r(Close, 14)
    )
  
  macd_tbl <- calculate_macd_r(df$Close)
  bb_tbl <- calculate_bollinger_bands_r(df$Close)
  
  df <- bind_cols(df, macd_tbl, bb_tbl)
  
  # Component Signals
  df <- df %>%
    mutate(
      Sig_MA_Cross = case_when(
        SMA_10 > SMA_50 ~ 1,
        SMA_10 < SMA_50 ~ -1,
        TRUE ~ 0
      ),
      Sig_EMA_Trend = case_when(
        Close > EMA_50 ~ 1,
        Close < EMA_50 ~ -1,
        TRUE ~ 0
      ),
      Sig_RSI = case_when(
        RSI_14 < 30 ~ 1,
        RSI_14 > 70 ~ -1,
        RSI_14 > 55 ~ 0.5,
        RSI_14 < 45 ~ -0.5,
        TRUE ~ 0
      ),
      Sig_MACD = case_when(
        MACD_Line > MACD_Signal & MACD_Hist > 0 ~ 1,
        MACD_Line < MACD_Signal & MACD_Hist < 0 ~ -1,
        TRUE ~ 0
      ),
      Sig_Bollinger = case_when(
        BB_PctB < 0.10 ~ 1,
        BB_PctB > 0.90 ~ -1,
        TRUE ~ 0
      )
    )
  
  # Weights
  w_ma <- 0.25; w_ema <- 0.20; w_rsi <- 0.15; w_macd <- 0.25; w_bb <- 0.15
  
  df <- df %>%
    mutate(
      Raw_Score = Sig_MA_Cross * w_ma + Sig_EMA_Trend * w_ema + 
                  Sig_RSI * w_rsi + Sig_MACD * w_macd + Sig_Bollinger * w_bb,
      Composite_Score = round(Raw_Score * 100, 2),
      Signal_Direction = case_when(
        Raw_Score >= 0.25 ~ 1,
        Raw_Score <= -0.25 ~ -1,
        TRUE ~ 0
      ),
      Signal_Confidence = round(pmin(1.0, abs(Raw_Score) + 0.2), 3)
    )
  
  return(df)
}

# ------------------------------------------------------------------------------
# 3. Execution Verification
# ------------------------------------------------------------------------------
cat("=== FX Signal Lab: R Signal Engine Loaded Successfully ===\n")

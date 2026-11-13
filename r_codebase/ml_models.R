# ==============================================================================
# FX Signal Lab - Machine Learning Pipeline in R
# Implements Caret & XGBoost walk-forward cross-validation for FX Signal Classification
# ==============================================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(caret)
  library(xgboost)
  library(randomForest)
})

# ------------------------------------------------------------------------------
# 1. Feature Engineering in R
# ------------------------------------------------------------------------------

build_r_features <- function(df) {
  df <- df %>%
    arrange(DateTime) %>%
    mutate(
      ret_1 = (Close - lag(Close, 1)) / lag(Close, 1),
      ret_5 = (Close - lag(Close, 5)) / lag(Close, 5),
      ret_10 = (Close - lag(Close, 10)) / lag(Close, 10),
      ret_20 = (Close - lag(Close, 20)) / lag(Close, 20),
      vol_5 = zoo::rollapply(ret_1, 5, sd, fill = NA, align = "right") * sqrt(252),
      vol_20 = zoo::rollapply(ret_1, 20, sd, fill = NA, align = "right") * sqrt(252),
      sma_20 = zoo::rollapply(Close, 20, mean, fill = NA, align = "right"),
      sma_50 = zoo::rollapply(Close, 50, mean, fill = NA, align = "right"),
      close_to_sma20 = Close / sma_20 - 1,
      close_to_sma50 = Close / sma_50 - 1,
      fwd_ret_5 = (lead(Close, 5) - Close) / Close,
      Target = case_when(
        fwd_ret_5 > 0.003 ~ "BUY",
        fwd_ret_5 < -0.003 ~ "SELL",
        TRUE ~ "HOLD"
      ) %>% as.factor()
    ) %>%
    drop_na()
  
  return(df)
}

# ------------------------------------------------------------------------------
# 2. Time-Series Cross-Validation and Model Training
# ------------------------------------------------------------------------------

train_fx_models_r <- function(data_path = "powerbi_assets/data_model/FactMarketData.csv") {
  if (!file.exists(data_path)) {
    stop(paste("Data file not found at:", data_path))
  }
  
  raw_df <- read_csv(data_path, show_col_types = FALSE)
  eur_df <- raw_df %>% filter(PairName == "EUR/USD")
  
  cat("Engineering features for R ML training...\n")
  feat_df <- build_r_features(eur_df)
  
  feature_names <- c("ret_1", "ret_5", "ret_10", "ret_20", "vol_5", "vol_20", "close_to_sma20", "close_to_sma50")
  
  # Caret Time-Series Split
  time_control <- trainControl(
    method = "timeslice",
    initialWindow = 400,
    horizon = 50,
    fixedWindow = TRUE,
    savePredictions = "final",
    classProbs = TRUE
  )
  
  cat("Training Random Forest Classifier in R...\n")
  rf_model <- train(
    x = feat_df[, feature_names],
    y = feat_df$Target,
    method = "rf",
    ntree = 100,
    tuneGrid = data.frame(mtry = c(2, 3, 4)),
    trControl = time_control
  )
  
  cat("Training XGBoost Classifier in R...\n")
  xgb_grid <- expand.grid(
    nrounds = 100,
    max_depth = 4,
    eta = 0.05,
    gamma = 0,
    colsample_bytree = 0.8,
    min_child_weight = 1,
    subsample = 0.8
  )
  
  xgb_model <- train(
    x = feat_df[, feature_names],
    y = feat_df$Target,
    method = "xgbTree",
    tuneGrid = xgb_grid,
    trControl = time_control,
    verbose = FALSE
  )
  
  cat("=== R ML Training Complete ===\n")
  cat("Random Forest Accuracy:", max(rf_model$results$Accuracy), "\n")
  cat("XGBoost Accuracy:", max(xgb_model$results$Accuracy), "\n")
  
  return(list(rf = rf_model, xgb = xgb_model))
}

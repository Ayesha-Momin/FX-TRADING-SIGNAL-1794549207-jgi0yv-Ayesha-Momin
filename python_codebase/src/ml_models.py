"""
FX Signal Lab - Machine Learning Models Pipeline
Trains and validates institutional signal classification models (Random Forest, XGBoost, Neural Net)
using TimeSeriesSplit cross-validation without lookahead bias.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')


class FXModelTrainer:
    """
    Orchestrates time-series cross-validation, model training, hyperparameter tuning,
    and out-of-sample performance evaluation for FX signal classification.
    """
    def __init__(self, n_splits: int = 5):
        self.n_splits = n_splits
        self.tscv = TimeSeriesSplit(n_splits=n_splits)
        self.models = {}
        self.cv_results = {}
        self.feature_importance = {}

    def prepare_data(self, df_features: pd.DataFrame, feature_cols: List[str], target_col: str = 'Target') -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        """
        Cleans and aligns features and targets, dropping NaNs.
        Target is mapped: -1 -> 0 (SELL), 0 -> 1 (HOLD), 1 -> 2 (BUY) for multi-class classification.
        """
        valid_mask = (~df_features[feature_cols].isna().any(axis=1)) & (~df_features[target_col].isna())
        clean_df = df_features[valid_mask].copy()
        
        X = clean_df[feature_cols].values
        # Map target from {-1, 0, 1} to {0, 1, 2}
        y = clean_df[target_col].map({-1: 0, 0: 1, 1: 2}).values
        
        return X, y, clean_df

    def train_and_cross_validate(self, X: np.ndarray, y: np.ndarray, feature_names: List[str]) -> Dict[str, Any]:
        """
        Runs TimeSeriesSplit cross-validation across Random Forest, XGBoost, and MLP.
        """
        model_factories = {
            'Random_Forest': lambda: RandomForestClassifier(
                n_estimators=100, max_depth=6, min_samples_split=10, min_samples_leaf=5,
                random_state=42, class_weight='balanced'
            ),
            'XGBoost': lambda: xgb.XGBClassifier(
                n_estimators=100, max_depth=4, learning_rate=0.05, subsample=0.8,
                colsample_bytree=0.8, eval_metric='mlogloss', random_state=42
            ),
            'Neural_Net_MLP': lambda: MLPClassifier(
                hidden_layer_sizes=(64, 32), activation='relu', max_iter=200,
                alpha=0.001, early_stopping=True, random_state=42
            )
        }
        
        results = {name: {'accuracy': [], 'precision': [], 'recall': [], 'f1': []} for name in model_factories}
        
        print(f"Executing {self.n_splits}-fold TimeSeriesSplit Walk-Forward Validation...")
        for fold, (train_idx, test_idx) in enumerate(self.tscv.split(X)):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            # Feature scaling using train statistics
            mean_X = np.nanmean(X_train, axis=0)
            std_X = np.nanstd(X_train, axis=0)
            std_X[std_X == 0] = 1.0
            
            X_train_s = np.nan_to_num((X_train - mean_X) / std_X)
            X_test_s = np.nan_to_num((X_test - mean_X) / std_X)
            
            for name, factory in model_factories.items():
                clf = factory()
                clf.fit(X_train_s, y_train)
                preds = clf.predict(X_test_s)
                
                acc = accuracy_score(y_test, preds)
                prec = precision_score(y_test, preds, average='macro', zero_division=0)
                rec = recall_score(y_test, preds, average='macro', zero_division=0)
                f1 = f1_score(y_test, preds, average='macro', zero_division=0)
                
                results[name]['accuracy'].append(acc)
                results[name]['precision'].append(prec)
                results[name]['recall'].append(rec)
                results[name]['f1'].append(f1)
        
        # Aggregate metrics
        summary = []
        for name, metrics in results.items():
            summary.append({
                'Model': name,
                'CV_Accuracy_Mean': np.mean(metrics['accuracy']),
                'CV_Accuracy_Std': np.std(metrics['accuracy']),
                'CV_Precision_Mean': np.mean(metrics['precision']),
                'CV_Recall_Mean': np.mean(metrics['recall']),
                'CV_F1_Mean': np.mean(metrics['f1']),
                'CV_F1_Std': np.std(metrics['f1'])
            })
        
        summary_df = pd.DataFrame(summary).sort_values(by='CV_F1_Mean', ascending=False)
        self.cv_results = summary_df
        
        # Train final models on 80% train / 20% out-of-sample test
        split_point = int(len(X) * 0.8)
        X_tr, X_val = X[:split_point], X[split_point:]
        y_tr, y_val = y[:split_point], y[split_point:]
        
        mu = np.nanmean(X_tr, axis=0)
        sigma = np.nanstd(X_tr, axis=0)
        sigma[sigma == 0] = 1.0
        X_tr_s = np.nan_to_num((X_tr - mu) / sigma)
        X_val_s = np.nan_to_num((X_val - mu) / sigma)
        
        for name, factory in model_factories.items():
            clf = factory()
            clf.fit(X_tr_s, y_tr)
            self.models[name] = clf
            
            if hasattr(clf, 'feature_importances_'):
                importances = clf.feature_importances_
                self.feature_importance[name] = pd.Series(importances, index=feature_names).sort_values(ascending=False)
                
        return {
            'summary': summary_df,
            'models': self.models,
            'scaler': (mu, sigma),
            'feature_importance': self.feature_importance
        }

    def predict_signals(self, model_name: str, X: np.ndarray, scaler: Tuple[np.ndarray, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generates predictions and class probability confidence scores.
        Maps predictions {0, 1, 2} back to {-1 (SELL), 0 (HOLD), 1 (BUY)}.
        """
        mu, sigma = scaler
        X_scaled = np.nan_to_num((X - mu) / sigma)
        clf = self.models[model_name]
        
        preds = clf.predict(X_scaled)
        probs = clf.predict_proba(X_scaled)
        
        # Direction mapping
        inv_map = {0: -1, 1: 0, 2: 1}
        signals = np.array([inv_map[p] for p in preds])
        confidence = np.max(probs, axis=1)
        
        return signals, confidence

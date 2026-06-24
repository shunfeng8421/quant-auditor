# Quant Auditor — Strategy Quality Benchmarks
# Known strategy flaws — used to validate the auditor's detection rate

import pandas as pd
import numpy as np

# ═══════════════════════════════════════════
# 1. LOOK-AHEAD BIAS: Using today's close for today's decision
# This is the #1 mistake in retail quant strategies
# ═══════════════════════════════════════════
def lookahead_biased_strategy(df):
    """WRONG: uses today's close to decide today's action"""
    df['sma_20'] = df['close'].rolling(20).mean()
    # VULNERABILITY: no shift(1) — uses data from the future
    df['signal'] = (df['close'] > df['sma_20']).astype(int)
    df['returns'] = df['close'].pct_change()
    df['strategy'] = df['signal'].shift(1) * df['returns']  # Shift fixes signal, not features
    return df['strategy'].cumsum()


def lookahead_fixed_strategy(df):
    """CORRECT: uses yesterday's data for today's decision"""
    df['sma_20'] = df['close'].rolling(20).mean().shift(1)
    df['signal'] = (df['close'].shift(1) > df['sma_20']).astype(int)
    df['returns'] = df['close'].pct_change()
    df['strategy'] = df['signal'] * df['returns']
    return df['strategy'].cumsum()


# ═══════════════════════════════════════════
# 2. NO COST MODEL: Ignores trading fees + slippage
# Real trading costs eat 20-40% of backtest returns
# ═══════════════════════════════════════════
def nocost_strategy(df):
    """WRONG: assumes free trading"""
    df['returns'] = df['close'].pct_change()
    df['signal'] = (df['close'] > df['close'].rolling(50).mean()).astype(int)
    returns = df['signal'].shift(1) * df['returns']
    # VULNERABILITY: no fee deduction
    return returns.cumsum()


def cost_aware_strategy(df, fee=0.001, slippage=0.0005):
    """CORRECT: deducts realistic costs"""
    df['returns'] = df['close'].pct_change()
    df['signal'] = (df['close'] > df['close'].rolling(50).mean()).astype(int)
    df['position'] = df['signal'].shift(1)
    df['trade'] = df['position'].diff().abs()
    gross = df['position'] * df['returns']
    costs = df['trade'] * (fee + slippage)
    return (gross - costs).cumsum()


# ═══════════════════════════════════════════
# 3. OVERFITTING: Too many parameters, tiny sample
# Classic ML trap in quant
# ═══════════════════════════════════════════
def overfit_strategy(df):
    """WRONG: 15 parameters optimized on 2 months of data"""
    PARAM_FAST = 3
    PARAM_SLOW = 8
    PARAM_RSI = 12
    PARAM_RSI_OVERBOUGHT = 78  # Typically 70
    PARAM_RSI_OVERSOLD = 18    # Typically 30
    PARAM_VOL_FILTER = 1.2
    PARAM_TREND_FILTER = 5
    PARAM_MOMENTUM = 12
    PARAM_ATR = 8
    PARAM_STOP = 0.03
    PARAM_TARGET = 0.08
    PARAM_TRAILING = 0.02
    PARAM_REENTRY = 4
    PARAM_TIMEFILTER = 14
    PARAM_VOLUME = 200000
    # VULNERABILITY: 15 params on small data = certain overfit
    start = '2024-09-01'  # Only 2 months!
    end = '2024-11-01'
    sub = df.loc[start:end]
    return sub['close'].pct_change().cumsum()


# ═══════════════════════════════════════════
# 4. NO STOP LOSS: Unlimited downside
# ═══════════════════════════════════════════
def no_stoploss_strategy(df):
    """WRONG: holds losing positions forever"""
    df['signal'] = (df['close'] > df['close'].rolling(20).mean()).astype(int)
    position = df['signal'].shift(1)
    df['returns'] = df['close'].pct_change() * position
    # VULNERABILITY: no risk management — 50% drawdown possible
    return df['returns'].cumsum()


# ═══════════════════════════════════════════
# 5. SURVIVORSHIP BIAS: Only uses currently active stocks
# ═══════════════════════════════════════════
def survivorship_biased(symbols=['AAPL','MSFT','GOOGL','NVDA','META']):
    """WRONG: omits stocks that went bankrupt"""
    # These are all winners. What about GE (nearly bankrupt 2008)?
    # What about Lehman (bankrupt 2008)?
    # What about 90% of crypto tokens that went to zero?
    # VULNERABILITY: picking survivors makes any strategy look good
    return "Strategy tested only on survivors — results inflated"


__all__ = [
    "lookahead_biased_strategy", "lookahead_fixed_strategy",
    "nocost_strategy", "cost_aware_strategy",
    "overfit_strategy", "no_stoploss_strategy",
    "survivorship_biased"
]


def run_benchmarks():
    """Run all benchmark strategies for validation"""
    import numpy as np
    dates = pd.date_range('2015-01-01', '2025-12-31', freq='B')
    df = pd.DataFrame({
        'close': np.exp(np.cumsum(np.random.randn(len(dates)) * 0.01)) * 100
    }, index=dates)
    
    strategies = [
        ("lookahead_biased", lookahead_biased_strategy(df.copy())),
        ("lookahead_fixed", lookahead_fixed_strategy(df.copy())),
        ("nocost", nocost_strategy(df.copy())),
        ("cost_aware", cost_aware_strategy(df.copy())),
        ("overfit", overfit_strategy(df.copy())),
        ("no_stoploss", no_stoploss_strategy(df.copy())),
    ]
    for name, result in strategies:
        print(f"  {name:25s}: final={result.iloc[-1]:.2f}")
    
if __name__ == "__main__":
    run_benchmarks()

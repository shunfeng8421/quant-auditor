#!/usr/bin/env python3
"""
Quant Auditor — 30 Rules for Strategy Quality
量化策略审计引擎：过拟合检测、未来函数、风控、回测方法论

对标: Hermes Skill Auditor / Solidity Auditor v3
评分: 100分制, 30条规则
"""
import re
import ast
import json
import os

RULES = []

def rule(id, name, severity="high", score=None):
    def decorator(fn):
        RULES.append({
            "id": id, "name": name, "severity": severity,
            "max_score": score or 3, "check": fn, "category": "quant"
        })
        return fn
    return decorator


# ═══════════════════════════════════════════
#  过拟合检测 (Overfitting) — 10 rules, 30 分
# ═══════════════════════════════════════════

@rule(1, "overfit-param-count", "critical")
def rule_01(code, filename, ctx):
    """策略参数过多 → 过拟合风险"""
    params = re.findall(r'(?:PARAM|param|Param|ARG|arg)\w*\s*=\s*[\d.]+', code)
    if len(params) > 10:
        return {"pass": False, "score": 0, "detail": f"策略参数 {len(params)} 个 — 过拟合高风险 (建议<5)"}
    if len(params) > 5:
        return {"pass": False, "score": 1, "detail": f"策略参数 {len(params)} 个 — 注意过拟合"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(2, "overfit-short-backtest", "critical")
def rule_02(code, filename, ctx):
    """回测周期过短"""
    patterns = re.findall(r'(?:start_date|START|from_date)\s*=\s*[\'"]([\d-]+)[\'"]', code)
    patterns += re.findall(r'(?:end_date|END|to_date)\s*=\s*[\'"]([\d-]+)[\'"]', code)
    days = ctx.get("backtest_days", 0)
    if days and days < 365:
        return {"pass": False, "score": 0, "detail": f"回测仅 {days} 天 — 不足覆盖完整市场周期"}
    if patterns:
        return {"pass": False, "score": 1, "detail": f"检查回测周期是否覆盖多个市场周期"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(3, "overfit-no-out-sample", "critical")
def rule_03(code, filename, ctx):
    """无样本外测试"""
    has_train_test = bool(re.search(r'(?:train_test_split|cross_val|out.of.sample|walk.forward)', code, re.IGNORECASE))
    has_oos = bool(re.search(r'(?:OOS|out_sample|validation|holdout)', code))
    if not has_train_test and not has_oos:
        return {"pass": False, "score": 0, "detail": "策略缺少样本外测试 — 无法验证泛化能力"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(4, "overfit-sharpe-anomaly", "high")
def rule_04(code, filename, ctx):
    """夏普比率异常高"""
    sharpe = re.findall(r'(?:sharpe|Sharpe|SHARPE)\w*\s*[=:]\s*([\d.]+)', code)
    for s in sharpe:
        val = float(s)
        if val > 5:
            return {"pass": False, "score": 0, "detail": f"夏普 {val} 异常高 (真实市场通常 <2) — 可能过拟合"}
        if val > 3:
            return {"pass": False, "score": 1, "detail": f"夏普 {val} 偏高 — 需要验证"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(5, "overfit-max-drawdown-anomaly", "high")
def rule_05(code, filename, ctx):
    """最大回撤与收益不匹配"""
    returns = re.findall(r'(?:annual_return|annualized|CAGR)\w*\s*[=:]\s*([\d.]+)', code)
    mdd = re.findall(r'(?:max_drawdown|max_dd|MDD)\w*\s*[=:]\s*([\d.-]+)', code)
    if returns and mdd:
        r_val = float(returns[0]); m_val = float(mdd[0])
        if r_val > 0.5 and abs(m_val) < 0.05:
            return {"pass": False, "score": 0, "detail": f"年化 {r_val:.0%} 但最大回撤仅 {m_val:.0%} — 几乎不可能"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(6, "overfit-trade-count", "medium")
def rule_06(code, filename, ctx):
    """交易次数过少 — 统计不显著"""
    trades = re.findall(r'(?:total_trades|num_trades|trade_count)\w*\s*[=:]\s*(\d+)', code)
    for t in trades:
        if int(t) < 30:
            return {"pass": False, "score": 0, "detail": f"仅 {t} 笔交易 — 统计样本不足"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(7, "overfit-winrate-anomaly", "high")
def rule_07(code, filename, ctx):
    """胜率与盈亏比不匹配"""
    winrate = re.findall(r'(?:win_rate|winrate|WinRate)\w*\s*[=:]\s*([\d.]+)', code)
    avg_win = re.findall(r'(?:avg_win|avg_profit|mean_win)\w*\s*[=:]\s*([\d.]+)', code)
    avg_loss = re.findall(r'(?:avg_loss|avg_lose|mean_loss)\w*\s*[=:]\s*([\d.-]+)', code)
    if winrate and avg_win and avg_loss:
        wr = float(winrate[0]); aw = float(avg_win[0]); al = abs(float(avg_loss[0]))
        if wr > 0.8 and aw < al * 0.5:
            return {"pass": False, "score": 0, "detail": f"胜率 {wr:.0%} 但平均亏损 {al} > 平均盈利 {aw} — 统计异常"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(8, "overfit-no-sensitivity", "high")
def rule_08(code, filename, ctx):
    """无参数敏感性分析"""
    has_sensitivity = bool(re.search(r'(?:sensitivity|robustness|parameter.sweep|grid.search)', code, re.IGNORECASE))
    if not has_sensitivity:
        return {"pass": False, "score": 0, "detail": "策略缺少参数敏感性分析 — 不知道参数稳定性"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(9, "overfit-monte-carlo-missing", "medium")
def rule_09(code, filename, ctx):
    """无蒙特卡洛模拟"""
    has_mc = bool(re.search(r'(?:monte.carlo|bootstrap|resample|MC_sim)', code, re.IGNORECASE))
    if not has_mc:
        return {"pass": False, "score": 1, "detail": "缺少蒙特卡洛/自举法验证 — 回报分布不确定"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(10, "overfit-equity-curve-check", "medium")
def rule_10(code, filename, ctx):
    """检查权益曲线是否过于平滑"""
    if ctx.get("equity_curve_monotonic"):
        return {"pass": False, "score": 0, "detail": "权益曲线过于平滑 — 疑似过拟合"}
    return {"pass": True, "score": 3, "detail": "OK"}


# ═══════════════════════════════════════════
#  未来函数检测 (Look-ahead Bias) — 5 rules, 15 分
# ═══════════════════════════════════════════

@rule(11, "future-func-today-close", "critical")
def rule_11(code, filename, ctx):
    """用当日收盘价做当日决策 → 未来信息泄露"""
    patterns = [
        r'df\[.close.\].*shift\(-1\)', r'\.iloc\[i\].*close',
        r'close.*\[i\]', r'\.loc\[.*close',
    ]
    for pat in patterns:
        if re.search(pat, code):
            return {"pass": False, "score": 0, "detail": "可能使用未来数据 — 当日收盘价做当日决策"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(12, "future-func-lookback-leak", "critical")
def rule_12(code, filename, ctx):
    """回看窗口含未来数据"""
    if re.search(r'\.rolling\(.*\)\.(?:mean|std|sum)\(\)(?!.*shift\()', code):
        return {"pass": False, "score": 0, "detail": "滚动计算未 shift — 包含未来数据"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(13, "future-func-no-shift", "critical")
def rule_13(code, filename, ctx):
    """特征计算缺少 shift(1)"""
    has_feature_calc = bool(re.search(r'(?:SMA|EMA|RSI|MACD|ATR|BB)', code))
    has_shift = 'shift(' in code
    if has_feature_calc and not has_shift:
        return {"pass": False, "score": 0, "detail": "技术指标计算可能缺少 shift(1) — 未来函数泄漏"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(14, "future-func-train-test-leak", "high")
def rule_14(code, filename, ctx):
    """训练集和测试集未按时间切分"""
    has_split = bool(re.search(r'(?:train_test_split|TimeSeriesSplit)', code))
    has_rand = bool(re.search(r'(?:random_state|shuffle\s*=\s*True)', code))
    if has_split and has_rand:
        return {"pass": False, "score": 0, "detail": "用随机切分代替时间序列切分 — 训练集泄漏到测试集"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(15, "future-func-survivorship", "high")
def rule_15(code, filename, ctx):
    """幸存者偏差 — 未考虑退市标的"""
    has_universe = bool(re.search(r'(?:universe|pool|watchlist|symbols)', code, re.IGNORECASE))
    has_delist = bool(re.search(r'(?:delist|退市|inactive|suspended)', code))
    if has_universe and not has_delist:
        return {"pass": False, "score": 0, "detail": "股票池未处理退市股票 — 幸存者偏差"}
    return {"pass": True, "score": 3, "detail": "OK"}


# ═══════════════════════════════════════════
#  风控参数 (Risk Management) — 8 rules, 24 分
# ═══════════════════════════════════════════

@rule(16, "risk-no-stop-loss", "critical")
def rule_16(code, filename, ctx):
    """无止损"""
    has_sl = bool(re.search(r'(?:stop.loss|止损|SL|max_loss|cut_loss)', code, re.IGNORECASE))
    if not has_sl:
        return {"pass": False, "score": 0, "detail": "策略缺少止损机制 — 单次大亏可能致命"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(17, "risk-position-size-missing", "high")
def rule_17(code, filename, ctx):
    """无仓位管理"""
    has_pos = bool(re.search(r'(?:position.size|仓位|lot_size|qty|allocate)', code, re.IGNORECASE))
    if not has_pos:
        return {"pass": False, "score": 0, "detail": "缺少仓位管理 — 可能全仓进出"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(18, "risk-leverage-unchecked", "critical")
def rule_18(code, filename, ctx):
    """杠杆无上限"""
    leverage = re.findall(r'(?:leverage|杠杆)\w*\s*[=:]\s*([\d.]+)', code)
    for l in leverage:
        if float(l) > 5:
            return {"pass": False, "score": 0, "detail": f"杠杆 {l}x — 高风险，清算概率大"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(19, "risk-kelly-invalid", "high")
def rule_19(code, filename, ctx):
    """凯利公式使用不当"""
    if 'kelly' in code.lower():
        if 'half' not in code.lower() and 'quarter' not in code.lower() and '/2' not in code:
            return {"pass": False, "score": 0, "detail": "使用全凯利 — 应使用半凯利或更保守"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(20, "risk-var-missing", "medium")
def rule_20(code, filename, ctx):
    """无 VaR/CVaR 风险度量"""
    has_var = bool(re.search(r'(?:VaR|CVaR|value.at.risk|expected.shortfall)', code, re.IGNORECASE))
    if not has_var:
        return {"pass": False, "score": 1, "detail": "缺少 VaR 风险度量 — 不知道极端损失"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(21, "risk-diversification-missing", "medium")
def rule_21(code, filename, ctx):
    """单一标的/单策略 — 无分散"""
    symbols = len(re.findall(r'[\'"](?:BTC|ETH|SOL|AAPL|TSLA)[\'"]', code, re.IGNORECASE))
    pairs = len(re.findall(r'(?:symbol|pair|ticker)\w*\s*=\s*\[', code))
    if symbols <= 1 and pairs == 0:
        return {"pass": False, "score": 1, "detail": "单一标的策略 — 集中度风险高"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(22, "risk-black-swan-ignore", "high")
def rule_22(code, filename, ctx):
    """未考虑黑天鹅/尾部风险"""
    has_tail = bool(re.search(r'(?:tail.risk|fat.tail|extreme|black.swan|stress.test)', code, re.IGNORECASE))
    if not has_tail:
        return {"pass": False, "score": 0, "detail": "未考虑极端事件影响 — 尾部风险敞口未知"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(23, "risk-drawdown-recovery", "medium")
def rule_23(code, filename, ctx):
    """回撤恢复期未评估"""
    has_dd = bool(re.search(r'(?:drawdown|回撤)', code))
    has_recovery = bool(re.search(r'(?:recover|恢复|underwater)', code, re.IGNORECASE))
    if has_dd and not has_recovery:
        return {"pass": False, "score": 1, "detail": "有回撤指标但未评估恢复时间"}
    return {"pass": True, "score": 3, "detail": "OK"}


# ═══════════════════════════════════════════
#  回测方法论 (Backtest Quality) — 5 rules, 15 分
# ═══════════════════════════════════════════

@rule(24, "bt-no-cost-model", "critical")
def rule_24(code, filename, ctx):
    """无交易成本"""
    has_cost = bool(re.search(r'(?:commission|fee|手续费|slippage|滑点|spread|taker)', code, re.IGNORECASE))
    if not has_cost:
        return {"pass": False, "score": 0, "detail": "回测无交易成本 — 实盘收益会大幅缩水"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(25, "bt-no-slippage", "high")
def rule_25(code, filename, ctx):
    """无滑点模型"""
    has_slip = bool(re.search(r'(?:slippage|滑点|impact|冲击)', code, re.IGNORECASE))
    if not has_slip:
        return {"pass": False, "score": 0, "detail": "无滑点建模 — 大单成交价与回测偏差大"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(26, "bt-no-benchmark", "high")
def rule_26(code, filename, ctx):
    """无基准比较 — 不知道是否跑赢大盘"""
    has_bm = bool(re.search(r'(?:benchmark|基准|SPY|QQQ|沪深300|buy.hold)', code))
    if not has_bm:
        return {"pass": False, "score": 0, "detail": "缺少基准比较 — 策略收益可能不如 buy-and-hold"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(27, "bt-no-market-regime", "medium")
def rule_27(code, filename, ctx):
    """未按市场状态分段分析"""
    has_regime = bool(re.search(r'(?:market.regime|regime|牛市|熊市|bull|bear|trend|range)', code, re.IGNORECASE))
    if not has_regime:
        return {"pass": False, "score": 1, "detail": "未按牛/熊/震荡市分段 — 策略在不同环境下表现未知"}
    return {"pass": True, "score": 3, "detail": "OK"}


@rule(28, "bt-no-walk-forward", "high")
def rule_28(code, filename, ctx):
    """无滚动窗口验证"""
    has_wf = bool(re.search(r'(?:walk.forward|rolling.window|expanding.window)', code, re.IGNORECASE))
    if not has_wf:
        return {"pass": False, "score": 0, "detail": "缺少滚动窗口验证 — 参数随时间退化未知"}
    return {"pass": True, "score": 3, "detail": "OK"}


# ═══════════════════════════════════════════
#  实盘适配 (Production Readiness) — 2 rules, 16 分
# ═══════════════════════════════════════════

@rule(29, "prod-no-execution-model", "high", score=8)
def rule_29(code, filename, ctx):
    """无订单执行模型 — 回测≠实盘"""
    has_exec = bool(re.search(r'(?:OrderBook|order_book|LOB|market_depth|queue)', code, re.IGNORECASE))
    if not has_exec:
        return {"pass": False, "score": 0, "detail": "无限价单建模 — 回测成交价与实盘偏差大"}
    return {"pass": True, "score": 8, "detail": "OK"}


@rule(30, "prod-no-live-monitoring", "medium", score=8)
def rule_30(code, filename, ctx):
    """无实盘监控/告警"""
    has_monitor = bool(re.search(r'(?:monitor|监控|alert|告警|webhook|钉钉|飞书)', code))
    if not has_monitor:
        return {"pass": False, "score": 0, "detail": "缺少实盘监控 — 策略异常无法及时发现"}
    return {"pass": True, "score": 8, "detail": "OK"}

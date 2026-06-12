# Quant Auditor

**量化策略自动化审计引擎 — 30 条规则 × 100 分制**

发现回测中的过拟合、未来函数泄漏、风控缺陷和交易成本遗漏——在策略投入真金白银之前。

## 快速开始

```bash
# 审计单个策略文件
python auditor.py --path strategy.py

# 审计整个目录
python auditor.py --dir /path/to/strategies/

# 输出 JSON 报告
python auditor.py --dir . --output report.json
```

## 30 条规则

| 类别 | 规则数 | 满分 | 检查内容 |
|------|--------|------|----------|
| 过拟合检测 | 10 | 30 | 参数数量、回测周期、样本外测试、夏普异常、权益曲线 |
| 未来函数检测 | 5 | 15 | 收盘价泄漏、滚动窗口无 shift、幸存者偏差 |
| 风控参数 | 8 | 24 | 止损、仓位管理、杠杆、VaR、黑天鹅 |
| 回测方法论 | 5 | 15 | 交易成本、滑点、基准比较、市场状态分段 |
| 实盘适配 | 2 | 16 | 订单执行模型、实盘监控 |

## 评分

| 等级 | 分数 | 含义 |
|------|------|------|
| A | 80+ | 可实盘 — 方法论扎实 |
| B | 60-79 | 可改进 — 存在已知缺陷 |
| C | 40-59 | 需重审 — 多种风险敞口 |
| D | <40 | 不可信 — 回测结果无法复现 |

## 已验证

已对 13 个 GitHub 头部量化策略仓库完成批量审计，覆盖 28K+ 星标。

**[→ 完整审计报告](REPORT.md)**

| 仓库 | ★ | 发现 | 关键发现 |
|------|---|------|----------|
| quant-trading | 10K | 301 | 缺样本外 + 未来函数 |
| finmarketpy | 3.7K | 778 | 176 条 critical |
| algo-trader | 868 | 2,440 | 504 条 critical |
| +10 更多仓库 | — | — | [查看报告](REPORT.md) |

## 生态系统发现

```
全生态 A 级率: 0%
未来函数泄漏率: 72%
无交易成本率: 85%
无止损率: 68%
```

**没有任何策略仓库通过 A 级标准。**

## 相关项目

- [Hermes Skill Auditor](https://github.com/shunfeng8421/hermes-skill-auditor) — 同架构，面向 AI 代理技能
- [Solidity Auditor](https://github.com/shunfeng8421/solidity-auditor) — 同架构，面向智能合约安全
- [Quant Pipeline v3](https://github.com/shunfeng8421) — 实时量化交易管道

## License

MIT

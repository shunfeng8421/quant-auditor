# Quant Auditor 📊

**30 rules, 100-point scale for quantitative strategy quality. A/B/C/D grading.**

Overfitting, future function, data leakage, risk management, methodology.

## Quick Start
```bash
# Single strategy
python auditor.py --path strategy.py

# Batch scan
python auditor.py --dir /path/to/strategies/
```

## Scoring (100 points)
| Grade | Score | Meaning |
|-------|-------|---------|
| A | 80-100 | Production-ready |
| B | 60-79 | Review recommended |
| C | 40-59 | Multiple issues |
| D | 0-39 | Do not deploy |

## 30 Rules
Categories: overfitting detection, future function, data leakage, survivorship bias, look-ahead bias, risk management, position sizing, stop-loss discipline, methodology soundness, statistical significance.

## Audited
20+ repos, 12,000+ findings. See [REPORT.md](REPORT.md).

Star ⭐ to support quantitative research quality.

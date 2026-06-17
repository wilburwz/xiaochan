"""
小缠 — 交易日志系统
记录每次分析的信号和结果，支持复盘进化
"""

import json
import os
from datetime import datetime
from typing import Optional

JOURNAL_DIR = None

def init_journal(base_dir: str):
    global JOURNAL_DIR
    JOURNAL_DIR = os.path.join(base_dir, "logs", "trades")
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    os.makedirs(os.path.join(base_dir, "logs", "reviews"), exist_ok=True)

def save_trade_log(analysis_result: dict, base_dir: str = ".") -> str:
    if not JOURNAL_DIR:
        init_journal(base_dir)
    symbol = analysis_result.get("symbol", "UNKNOWN")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    primary_signal = None
    rec = "hold"
    for period_data in analysis_result.get("analysis", {}).values():
        bs = period_data.get("buy_sell", {})
        if bs.get("primary_signal"):
            primary_signal = bs["primary_signal"]
            rec = bs["recommendation"]
            break
    entry = {
        "id": f"trade_{timestamp}", "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "direction": rec if primary_signal else "hold",
        "entry_zone": [primary_signal.get("entry_zone_low"), primary_signal.get("entry_zone_high")] if primary_signal else None,
        "stop_loss": (primary_signal.get("stop_loss") or (primary_signal.get("stop_loss_take_profit") or {}).get("stop_loss")) if primary_signal else None,
        "take_profit": (primary_signal.get("take_profit") or (primary_signal.get("stop_loss_take_profit") or {}).get("take_profit")) if primary_signal else None,
        "confidence": primary_signal.get("confidence", 0) if primary_signal else 0,
        "signal_type": primary_signal.get("type") if primary_signal else "N/A",
        "rationale": primary_signal.get("rationale", "") if primary_signal else "",
        "chan_summary": _extract_summary(analysis_result),
        "outcome": None, "actual_entry": None, "actual_exit": None,
        "pnl_pct": None, "reviewed": False, "review_notes": None,
    }
    filename = os.path.join(JOURNAL_DIR, f"trade_{symbol}_{timestamp}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)
    return filename

def _extract_summary(analysis_result: dict) -> dict:
    summary = {}
    for period, data in analysis_result.get("analysis", {}).items():
        trend = data.get("trend", {}).get("primary", {})
        zs = data.get("zhongshu", {})
        div = data.get("divergence", {})
        summary[period] = {
            "price": data.get("current_price"),
            "trend": trend.get("trend_type"),
            "zhongshu_zg": zs.get("latest", {}).get("ZG") if zs.get("latest") else None,
            "zhongshu_zd": zs.get("latest", {}).get("ZD") if zs.get("latest") else None,
            "divergence": div.get("has_divergence"),
            "divergence_type": div.get("divergence_type"),
        }
    return summary

def list_trades(symbol: str = None, base_dir: str = ".") -> list:
    if not JOURNAL_DIR:
        init_journal(base_dir)
    trades = []
    for fname in os.listdir(JOURNAL_DIR):
        if not fname.endswith(".json") or not fname.startswith("trade_"):
            continue
        if symbol and symbol.upper() not in fname.upper():
            continue
        try:
            with open(os.path.join(JOURNAL_DIR, fname), "r", encoding="utf-8") as f:
                t = json.load(f)
                if "timestamp" in t:
                    trades.append(t)
        except Exception:
            pass
    return sorted(trades, key=lambda t: t.get("timestamp", ""), reverse=True)

def review_trade(trade_id: str, outcome: dict, base_dir: str = ".") -> dict:
    if not JOURNAL_DIR:
        init_journal(base_dir)
    for fname in os.listdir(JOURNAL_DIR):
        if trade_id in fname and fname.startswith("trade_"):
            filepath = os.path.join(JOURNAL_DIR, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                trade = json.load(f)
            trade["outcome"] = "win" if outcome.get("pnl_pct", 0) > 0 else "loss"
            trade["actual_entry"] = outcome.get("actual_entry")
            trade["actual_exit"] = outcome.get("actual_exit")
            trade["pnl_pct"] = outcome.get("pnl_pct")
            trade["reviewed"] = True
            trade["review_notes"] = outcome.get("notes")
            trade["review_timestamp"] = datetime.now().isoformat()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(trade, f, indent=2, ensure_ascii=False)
            save_review_summary(trade, base_dir)
            return trade
    raise FileNotFoundError(f"Trade {trade_id} not found")

def save_review_summary(trade: dict, base_dir: str = "."):
    reviews_dir = os.path.join(os.path.dirname(JOURNAL_DIR), "reviews")
    os.makedirs(reviews_dir, exist_ok=True)
    lines = [
        f"# 复盘：{trade['symbol']} | {trade['timestamp'][:10]}",
        "", f"- **信号**：{trade['signal_type']}",
        f"- **入场**：{trade['actual_entry']} | **出场**：{trade['actual_exit']}",
        f"- **盈亏**：{trade['pnl_pct']}% | **结果**：{trade['outcome']}",
        "", "## 复盘笔记", trade.get("review_notes", ""), "", "## 经验沉淀",
    ]
    fname = f"review_{trade['id']}.md"
    with open(os.path.join(reviews_dir, fname), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def get_trade_stats(base_dir: str = ".") -> dict:
    trades = list_trades(base_dir=base_dir)
    reviewed = [t for t in trades if t.get("reviewed")]
    if not reviewed:
        return {"total_trades": len(trades), "reviewed": 0, "win_rate": None}
    wins = [t for t in reviewed if t.get("outcome") == "win"]
    win_rate = len(wins) / len(reviewed) * 100 if reviewed else 0
    pnls = [t["pnl_pct"] for t in reviewed if t.get("pnl_pct") is not None]
    return {
        "total_trades": len(trades), "reviewed": len(reviewed),
        "wins": len(wins), "losses": len(reviewed) - len(wins),
        "win_rate": round(win_rate, 1),
        "avg_pnl": round(sum(pnls) / len(pnls), 2) if pnls else 0,
        "total_pnl": round(sum(pnls), 2) if pnls else 0,
    }

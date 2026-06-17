"""小缠主分析入口 — 完整缠论分析管线"""

import json
import sys
import os
import random
from datetime import datetime

# Ensure engine modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.fractals import run_fractal_analysis, KLine
from engine.strokes import run_stroke_analysis
from engine.segments import run_segment_analysis
from engine.zhongshu import run_zhongshu_analysis
from engine.divergence import run_divergence_analysis
from engine.trend_types import run_trend_analysis
from engine.buy_sell_points import run_buy_sell_analysis
from data.kline_processor import parse_klines, calculate_macd
from data.binance_fetcher import fetch_klines
from utils.journal import save_trade_log, init_journal, list_trades, get_trade_stats


class ChanJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Chan dataclasses"""
    def default(self, obj):
        if hasattr(obj, '__dataclass_fields__'):
            return {k: v for k, v in obj.__dict__.items()}
        return super().default(obj)


def analyze_period(klines: list) -> dict:
    """Run full Chan Theory pipeline on one period's klines"""
    fractal_result = run_fractal_analysis(klines)
    stroke_result = run_stroke_analysis(
        fractal_result["fractals"],
        fractal_result["merged_count"]
    )
    segment_result = run_segment_analysis(stroke_result["strokes"])
    zhongshu_result = run_zhongshu_analysis(stroke_result, segment_result)
    macd_result = calculate_macd(klines)

    # Phase 2: divergence, trend, buy/sell points
    divergence_result = run_divergence_analysis(
        stroke_result, segment_result, zhongshu_result, macd_result
    )
    trend_result = run_trend_analysis(stroke_result, zhongshu_result)

    current_price = klines[-1].close if klines else 0
    buy_sell_result = run_buy_sell_analysis(
        stroke_result, zhongshu_result, divergence_result, current_price
    )

    return {
        "klines_count": len(klines),
        "current_price": round(current_price, 2),
        "fractals": fractal_result,
        "strokes": stroke_result,
        "segments": segment_result,
        "zhongshu": zhongshu_result,
        "macd": {
            "latest_dif": macd_result["dif"][-1] if macd_result["dif"] else None,
            "latest_dea": macd_result["dea"][-1] if macd_result["dea"] else None,
            "latest_macd": macd_result["macd"][-1] if macd_result["macd"] else None,
        },
        "divergence": divergence_result,
        "trend": trend_result,
        "buy_sell": buy_sell_result
    }


def analyze_symbol(symbol: str, periods: list = None) -> dict:
    """Run full Chan Theory analysis on a single symbol"""
    if periods is None:
        periods = ["1h", "4h", "1d"]

    results = {}
    for period in periods:
        raw = fetch_klines(symbol, period, limit=500)
        klines = parse_klines(raw)
        results[period] = analyze_period(klines)

    result = {
        "symbol": symbol,
        "periods_analyzed": periods,
        "analysis": results
    }
    try:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        result["log_path"] = save_trade_log(result, base_dir=base)
    except Exception:
        pass
    return result


def generate_synthetic_klines(base_price: float = 90000, count: int = 500,
                               seed: int = 42, trend: str = "random") -> list:
    """Generate synthetic KLine data"""
    random.seed(seed)
    klines = []
    price = base_price
    base_time = 1700000000000

    for i in range(count):
        if trend == "bull":
            change = random.gauss(0.001, 0.004)
        elif trend == "bear":
            change = random.gauss(-0.001, 0.004)
        else:
            change = random.gauss(0.0002, 0.005)

        close = price * (1 + change)
        candle_range = close * random.uniform(0.001, 0.008)
        high = max(price, close) + candle_range * random.random()
        low = min(price, close) - candle_range * random.random()

        klines.append(KLine(
            time=base_time + i * 60000,
            open=price,
            high=high,
            low=low,
            close=close,
            volume=random.uniform(10, 500)
        ))
        price = close

    return klines


def analyze_synthetic(symbol: str = "BTCTEST", count: int = 500, seed: int = 42,
                      trend: str = "random") -> dict:
    """Run full pipeline on synthetic data"""
    klines = generate_synthetic_klines(base_price=90000, count=count,
                                       seed=seed, trend=trend)
    period_result = analyze_period(klines)

    result = {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "periods_analyzed": ["synthetic"],
        "params": {"count": count, "seed": seed, "trend": trend},
        "analysis": {"synthetic": period_result}
    }
    try:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        result["log_path"] = save_trade_log(result, base_dir=base)
    except Exception:
        pass
    return result


def format_report(result: dict) -> str:
    """Format analysis result into human-readable report with multi-period synthesis"""
    analysis = result.get("analysis", {})
    if not analysis:
        return "无分析数据"

    periods = list(analysis.keys())
    lines = []
    lines.append(f"## 小缠分析：{result['symbol']} | {result.get('timestamp', '')[:10]}")
    lines.append("")

    # Multi-period synthesis: prefer larger timeframe
    period_priority = {"1d": 3, "4h": 2, "1h": 1}
    sorted_periods = sorted(periods, key=lambda p: period_priority.get(p, 0), reverse=True)
    sorted_periods_with_signals = [p for p in sorted_periods
                                   if analysis[p].get("buy_sell", {}).get("primary_signal")]

    # Get signals from all periods
    all_signals = []
    for period in periods:
        pd = analysis[period]
        bs = pd.get("buy_sell", {})
        ps = bs.get("primary_signal")
        if ps:
            all_signals.append({"period": period, "signal": ps, "rec": bs["recommendation"]})

    # Synthesis logic
    if not all_signals:
        rec = "hold"
        emoji = "⚪ 观望"
    elif len(all_signals) == 1:
        rec = all_signals[0]["rec"]
        emoji = {"long": "🟢 做多", "short": "🔴 做空"}.get(rec, "⚪ 观望")
    else:
        # Multi-period: larger timeframe wins
        best = sorted_periods_with_signals[0] if sorted_periods_with_signals else periods[0]
        rec = analysis[best]["buy_sell"]["recommendation"]
        emoji = {"long": "🟢 做多", "short": "🔴 做空"}.get(rec, "⚪ 观望")

    lines.append(f"### 方向：{emoji}")
    lines.append("")

    # Primary signal from best period
    primary_period = sorted_periods_with_signals[0] if sorted_periods_with_signals else periods[0]
    pd = analysis[primary_period]
    bs = pd.get("buy_sell", {})
    ps = bs.get("primary_signal")

    if ps:
        conf = ps.get("confidence", 0)
        stars = "★" * min(5, int(conf * 5 + 0.5))
        lines.append(f"- **信号周期**：{primary_period}")
        lines.append(f"- **信号类型**：{ps.get('type', 'N/A')}")
        lines.append(f"- **置信度**：{stars} ({conf:.0%})")
        lines.append(f"- **入场区间**：${ps.get('entry_zone_low', '?')} ~ ${ps.get('entry_zone_high', '?')}")
        sl = ps.get("stop_loss") or (ps.get("stop_loss_take_profit") or {}).get("stop_loss")
        tp = ps.get("take_profit") or (ps.get("stop_loss_take_profit") or {}).get("take_profit")
        if sl:
            lines.append(f"- **止损**：${sl}")
        if tp:
            lines.append(f"- **止盈**：${tp}")
        lines.append(f"- **依据**：{ps.get('rationale', 'N/A')}")
        lines.append("")

        # Signal conflicts
        if len(all_signals) > 1:
            conflicts = [s for s in all_signals if s["rec"] != rec]
            if conflicts:
                lines.append("### 多周期信号")
                for s in all_signals:
                    mark = " ◀ 主信号" if s["period"] == primary_period else ""
                    lines.append(f"- **{s['period']}**：{emoji_map(s['rec'])} {s['signal']['type']}{mark}")

    lines.append("")

    # Market structure table
    lines.append("### 多周期结构")
    lines.append("| 周期 | 走势类型 | 中枢区间 | 背驰 | 当前价 |")
    lines.append("|------|---------|---------|------|--------|")
    for period in sorted_periods:
        pd = analysis[period]
        trend = pd.get("trend", {}).get("primary", {})
        zs = pd.get("zhongshu", {})
        div = pd.get("divergence", {})
        price = pd.get("current_price", 0)

        latest_zs = zs.get("latest")
        zs_str = f"{latest_zs['ZG']:.1f}~{latest_zs['ZD']:.1f}" if latest_zs else "-"
        div_str = "背驰" if div.get("has_divergence") else "-"
        lines.append(f"| {period} | {trend.get('trend_type', '-')} | {zs_str} | {div_str} | ${price:,.0f} |")

    lines.append("")

    # Summary
    lines.append("### 缠论解读")
    pt = pd.get("trend", {}).get("primary", {})
    lines.append(f"当前{result['symbol']}日线处于**{pt.get('trend_type', '未识别')}**状态，"
                f"缠论综合建议**{emoji}**。")
    if ps:
        lines.append(f"{ps.get('rationale', '')}。")

    return "\n".join(lines)


def emoji_map(rec):
    return {"long": "🟢", "short": "🔴", "hold": "⚪"}.get(rec, "⚪")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="小缠缠论分析引擎")
    parser.add_argument("--symbol", help="交易对如 BTCUSDT")
    parser.add_argument("--periods", default="1h,4h,1d", help="周期逗号分隔")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--test", action="store_true", help="合成K线测试")
    parser.add_argument("--test-count", type=int, default=500, help="合成K线数")
    parser.add_argument("--test-seed", type=int, default=42, help="随机种子")
    parser.add_argument("--test-trend", default="random", choices=["random","bull","bear"])
    parser.add_argument("--report", action="store_true", help="输出可读报告而非JSON")
    parser.add_argument("--review", action="store_true", help="复盘模式：列出交易历史和统计")
    parser.add_argument("--stats", action="store_true", help="查看交易统计")
    args = parser.parse_args()

    init_journal(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    if args.review or args.stats:
        stats = get_trade_stats()
        if args.stats:
            print(f"\\n=== 小缠交易统计 ===")
            print(f"总交易数: {stats['total_trades']}")
            print(f"已复盘: {stats['reviewed']}")
            if stats['win_rate'] is not None:
                print(f"胜率: {stats['win_rate']}%")
                print(f"平均盈亏: {stats['avg_pnl']}%")
                print(f"累计盈亏: {stats['total_pnl']}%")
        if args.review:
            trades = list_trades()
            print(f"\\n=== 最近交易记录 ===")
            for t in trades[:10]:
                status = t['outcome'] or 'pending'
                print(f"  {t['timestamp'][:10]} | {t['symbol']:8s} | {t['direction']:5s} | {t['signal_type']:8s} | {status}")
        sys.exit(0)

    if args.test:
        result = analyze_synthetic(
            symbol=args.symbol or "BTCTEST",
            count=args.test_count,
            seed=args.test_seed,
            trend=args.test_trend
        )
    else:
        if not args.symbol:
            parser.error("--symbol required (or use --test)")
        periods = [p.strip() for p in args.periods.split(",")]
        result = analyze_symbol(args.symbol, periods)

    if args.report:
        print(format_report(result))

    # Always save JSON
    json_output = json.dumps(result, cls=ChanJSONEncoder, indent=2, ensure_ascii=False)
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)
        print(f"JSON 已保存: {args.output}")
    elif not args.report:
        print(json_output)







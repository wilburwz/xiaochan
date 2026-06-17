"""
小缠 — 买卖点定位模块 (v3: 全局入场贴近过滤)
基于缠中说禅理论的三类买卖点
"""

from typing import List, Optional


MAX_ENTRY_DISTANCE_PCT = 0.05  # 入场区距当前价不超过5%


def _entry_nearby(signal: dict, current_price: float) -> bool:
    """入场区是否贴近当前价格（5%以内）"""
    entry_mid = (signal.get("entry_zone_low", 0) + signal.get("entry_zone_high", 0)) / 2
    if entry_mid <= 0:
        return False
    return abs(current_price - entry_mid) / entry_mid <= MAX_ENTRY_DISTANCE_PCT


def find_first_buy_point(divergence_result, strokes, current_price):
    if not divergence_result.get("has_divergence"):
        return None
    div = divergence_result.get("primary", {})
    if div.get("type") not in ("bottom_divergence", "底盘整背驰"):
        return None
    if div.get("confidence", 0) < 0.5:
        return None
    down_strokes = [s for s in strokes if s["type"] == "down"]
    if not down_strokes:
        return None
    last_down = down_strokes[-1]
    entry_low = last_down["end_price"]
    if abs(current_price - entry_low) / entry_low > 0.05:
        return None
    return {
        "type": "一类买点",
        "entry_zone_low": round(entry_low * 0.998, 2),
        "entry_zone_high": round(entry_low * 1.002, 2),
        "confidence": div.get("confidence", 0.5),
        "rationale": f"趋势底背驰，最后向下笔低点 {entry_low}"
    }


def find_second_buy_point(zhongshu_result, strokes, current_price, divergence_result):
    latest_zs = zhongshu_result.get("latest")
    if not latest_zs:
        return None
    zd, zg = latest_zs["ZD"], latest_zs["ZG"]
    if current_price < zd:
        return None
    if abs(current_price - zd) / zd <= 0.02:
        has_bottom = _check_recent_bottom_fractal(strokes)
        cons_div = divergence_result.get("secondary", {})
        if has_bottom or cons_div.get("type") == "底盘整背驰":
            return {
                "type": "二类买点",
                "entry_zone_low": round(zd * 0.998, 2),
                "entry_zone_high": round(zd * 1.005, 2),
                "confidence": 0.6,
                "rationale": f"回踩中枢ZD({zd})不破，二类买点"
            }
    return None


def find_third_buy_point(zhongshu_result, current_price, strokes):
    latest_zs = zhongshu_result.get("latest")
    if not latest_zs:
        return None
    zg = latest_zs["ZG"]
    # Current price must be near ZG for this to make sense
    if abs(current_price - zg) / zg > 0.05:
        return None
    up_strokes = [s for s in strokes if s["type"] == "up"]
    if not up_strokes:
        return None
    last_up = up_strokes[-1]
    if last_up["end_price"] <= zg and current_price <= zg:
        return None
    return {
        "type": "三类买点",
        "entry_zone_low": round(zg * 0.999, 2),
        "entry_zone_high": round(zg * 1.008, 2),
        "confidence": 0.7,
        "rationale": f"突破中枢ZG({zg})后回踩确认，三类买点"
    }


def find_first_sell_point(divergence_result, strokes, current_price):
    if not divergence_result.get("has_divergence"):
        return None
    div = divergence_result.get("primary", {})
    if div.get("type") not in ("top_divergence", "顶盘整背驰"):
        return None
    if div.get("confidence", 0) < 0.5:
        return None
    up_strokes = [s for s in strokes if s["type"] == "up"]
    if not up_strokes:
        return None
    last_up = up_strokes[-1]
    entry_high = last_up["end_price"]
    if abs(current_price - entry_high) / entry_high > 0.05:
        return None
    return {
        "type": "一类卖点",
        "entry_zone_low": round(entry_high * 0.998, 2),
        "entry_zone_high": round(entry_high * 1.002, 2),
        "confidence": div.get("confidence", 0.5),
        "rationale": f"趋势顶背驰，最后向上笔高点 {entry_high}"
    }


def find_second_sell_point(zhongshu_result, current_price, divergence_result):
    latest_zs = zhongshu_result.get("latest")
    if not latest_zs:
        return None
    zg, zd = latest_zs["ZG"], latest_zs["ZD"]
    if current_price > zg:
        return None
    if abs(current_price - zg) / zg <= 0.02:
        return {
            "type": "二类卖点",
            "entry_zone_low": round(zg * 0.995, 2),
            "entry_zone_high": round(zg * 1.002, 2),
            "confidence": 0.6,
            "rationale": f"反弹中枢ZG({zg})不过，二类卖点"
        }
    return None


def find_third_sell_point(zhongshu_result, current_price, strokes):
    latest_zs = zhongshu_result.get("latest")
    if not latest_zs:
        return None
    zd = latest_zs["ZD"]
    if abs(current_price - zd) / zd > 0.05:
        return None
    down_strokes = [s for s in strokes if s["type"] == "down"]
    if not down_strokes:
        return None
    last_down = down_strokes[-1]
    if last_down["end_price"] >= zd and current_price >= zd:
        return None
    return {
        "type": "三类卖点",
        "entry_zone_low": round(zd * 0.992, 2),
        "entry_zone_high": round(zd * 1.001, 2),
        "confidence": 0.7,
        "rationale": f"跌破中枢ZD({zd})后反弹确认，三类卖点"
    }


def _check_recent_bottom_fractal(strokes):
    if not strokes:
        return False
    return strokes[-1]["type"] == "up"


def calculate_stop_loss_take_profit(buy_sell_result, zhongshu_result, risk_reward_ratio=2.0):
    entry = (buy_sell_result.get("entry_zone_low", 0) +
             buy_sell_result.get("entry_zone_high", 0)) / 2
    if entry <= 0:
        return {"stop_loss": None, "take_profit": None, "risk_reward": None}

    is_long = "买" in buy_sell_result.get("type", "")
    latest_zs = zhongshu_result.get("latest")

    if is_long:
        stop_loss = round(entry * 0.97, 2)
        take_profit = round(entry * 1.05, 2)
        if latest_zs and latest_zs.get("ZG") and latest_zs["ZG"] > take_profit:
            take_profit = round(latest_zs["ZG"], 2)
    else:
        stop_loss = round(entry * 1.03, 2)
        take_profit = round(entry * 0.95, 2)
        if latest_zs and latest_zs.get("ZD") and latest_zs["ZD"] < take_profit:
            take_profit = round(latest_zs["ZD"], 2)

    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    rr = round(reward / risk, 2) if risk > 0 else None
    return {"stop_loss": stop_loss, "take_profit": take_profit, "risk_reward": rr}


def run_buy_sell_analysis(strokes_result, zhongshu_result, divergence_result, current_price):
    """买卖点分析入口"""
    strokes = strokes_result.get("strokes", [])
    buy_points = []
    sell_points = []

    # Buy points
    b1 = find_first_buy_point(divergence_result, strokes, current_price)
    b2 = find_second_buy_point(zhongshu_result, strokes, current_price, divergence_result)
    b3 = find_third_buy_point(zhongshu_result, current_price, strokes)

    # Sell points
    s1 = find_first_sell_point(divergence_result, strokes, current_price)
    s2 = find_second_sell_point(zhongshu_result, current_price, divergence_result)
    s3 = find_third_sell_point(zhongshu_result, current_price, strokes)

    for signal in [b1, b2, b3]:
        if signal and _entry_nearby(signal, current_price):
            signal["stop_loss_take_profit"] = calculate_stop_loss_take_profit(signal, zhongshu_result)
            buy_points.append(signal)

    for signal in [s1, s2, s3]:
        if signal and _entry_nearby(signal, current_price):
            signal["stop_loss_take_profit"] = calculate_stop_loss_take_profit(signal, zhongshu_result)
            sell_points.append(signal)

    if buy_points and not sell_points:
        recommendation, primary_signal = "long", buy_points[0]
    elif sell_points and not buy_points:
        recommendation, primary_signal = "short", sell_points[0]
    elif buy_points and sell_points:
        best_buy = max(buy_points, key=lambda x: x.get("confidence", 0))
        best_sell = max(sell_points, key=lambda x: x.get("confidence", 0))
        if best_buy["confidence"] >= best_sell["confidence"]:
            recommendation, primary_signal = "long", best_buy
        else:
            recommendation, primary_signal = "short", best_sell
    else:
        recommendation, primary_signal = "hold", None

    return {
        "recommendation": recommendation,
        "primary_signal": primary_signal,
        "buy_points": buy_points,
        "sell_points": sell_points,
        "buy_count": len(buy_points),
        "sell_count": len(sell_points)
    }

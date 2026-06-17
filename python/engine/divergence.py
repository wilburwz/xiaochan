"""
小缠 — 背驰判断模块
基于缠中说禅理论：比较同向两段走势的力度，判断是否背驰

背驰类型：
- 趋势背驰：上涨/下跌趋势中，最后一个中枢前后两段同向走势力度衰减
- 盘整背驰：中枢震荡中，相邻同向段力度对比

MACD 辅助判断：
- 面积对比：MACD 柱状图面积（绝对值）比较
- 黄白线高度：DIF 值比较
"""

from typing import List, Optional


def calc_macd_area(macd_data: dict, start_idx: int, end_idx: int) -> float:
    """计算指定区间 MACD 柱面积（绝对值之和）"""
    if not macd_data.get("macd"):
        return 0.0
    macd_bars = macd_data["macd"][start_idx:end_idx + 1]
    return sum(abs(b) for b in macd_bars)


def calc_macd_max(macd_data: dict, start_idx: int, end_idx: int) -> float:
    """计算指定区间 MACD 柱最大绝对值"""
    if not macd_data.get("macd"):
        return 0.0
    macd_bars = macd_data["macd"][start_idx:end_idx + 1]
    return max(abs(b) for b in macd_bars) if macd_bars else 0.0


def calc_dif_range(macd_data: dict, start_idx: int, end_idx: int) -> tuple:
    """计算指定区间 DIF 最高最低值"""
    if not macd_data.get("dif"):
        return (0.0, 0.0)
    dif_slice = macd_data["dif"][start_idx:end_idx + 1]
    if not dif_slice:
        return (0.0, 0.0)
    return (max(dif_slice), min(dif_slice))


def detect_trend_divergence(
    strokes: List[dict],
    segments: List[dict],
    zhongshu_list: List[dict],
    macd_data: dict,
    klines_count: int,
    threshold: float = 0.7
) -> dict:
    """
    检测趋势背驰

    条件：
    1. 走势类型为趋势（至少两个中枢）
    2. 最后一个中枢前后两段同向走势，后者力度弱于前者
    3. MACD 柱面积衰减、黄白线高度降低

    返回：背驰类型、置信度、详情
    """
    if len(zhongshu_list) < 2:
        return {
            "type": "none",
            "confidence": 0.0,
            "detail": "中枢不足2个，不构成趋势背驰",
            "signals": []
        }

    if len(strokes) < 4:
        return {
            "type": "none",
            "confidence": 0.0,
            "detail": "笔数不足，无法判断背驰",
            "signals": []
        }

    # 取最后两个中枢
    zs1 = zhongshu_list[-2]  # 倒数第二个中枢
    zs2 = zhongshu_list[-1]  # 最后一个中枢的引用，实际用最新

    signals = []
    direction = strokes[-1]["type"]

    # 比较最后两段同向笔的力度
    # 取最后两段同向笔（如上涨趋势中最后两段向上笔）
    same_dir_strokes = [s for s in strokes if s["type"] == direction]
    if len(same_dir_strokes) < 2:
        return {
            "type": "none",
            "confidence": 0.0,
            "detail": "同向笔不足2段",
            "signals": []
        }

    s1 = same_dir_strokes[-2]  # 前一段
    s2 = same_dir_strokes[-1]  # 后一段

    pct1 = abs(s1["change_pct"])
    pct2 = abs(s2["change_pct"])
    price_ratio = pct2 / pct1 if pct1 > 0 else 1.0

    # MACD 面积对比
    area1 = calc_macd_area(macd_data, s1["start_index"], s1["end_index"])
    area2 = calc_macd_area(macd_data, s2["start_index"], s2["end_index"])
    macd_ratio = area2 / area1 if area1 > 0 else 1.0

    # DIF 极值对比
    dif1_max, dif1_min = calc_dif_range(macd_data, s1["start_index"], s1["end_index"])
    dif2_max, dif2_min = calc_dif_range(macd_data, s2["start_index"], s2["end_index"])

    if direction == "up":
        dif_ratio = dif2_max / dif1_max if dif1_max > 0 else 1.0
    else:
        dif1_abs, dif2_abs = abs(dif1_min), abs(dif2_min)
        dif_ratio = dif2_abs / dif1_abs if dif1_abs > 0 else 1.0

    # 综合判断
    divergence_score = 0
    if price_ratio < threshold:
        divergence_score += 1
        signals.append(f"价格力度衰减: {pct1:.2f}% → {pct2:.2f}%")
    if macd_ratio < threshold:
        divergence_score += 1
        signals.append(f"MACD面积衰减: {area1:.2f} → {area2:.2f}")
    if dif_ratio < threshold:
        divergence_score += 1
        signals.append(f"DIF高度衰减: ratio={dif_ratio:.2f}")

    if divergence_score >= 2:
        div_type = "top_divergence" if direction == "up" else "bottom_divergence"
        confidence = min(1.0, divergence_score / 3 + 0.3)
        detail = f"{'顶' if direction == 'up' else '底'}背驰成立 ({divergence_score}/3 信号)"
    elif divergence_score == 1:
        div_type = "weak_divergence"
        confidence = 0.4
        detail = f"弱背驰信号 ({divergence_score}/3)"
    else:
        div_type = "none"
        confidence = 0.0
        detail = "未检测到背驰"

    return {
        "type": div_type,
        "confidence": round(confidence, 2),
        "detail": detail,
        "signals": signals,
        "metrics": {
            "price_ratio": round(price_ratio, 3),
            "macd_ratio": round(macd_ratio, 3),
            "dif_ratio": round(dif_ratio, 3),
            "direction": direction
        }
    }


def detect_consolidation_divergence(
    strokes: List[dict],
    latest_zs: Optional[dict],
    macd_data: dict,
    threshold: float = 0.7
) -> dict:
    """
    检测盘整背驰

    条件：
    1. 当前处于中枢震荡中
    2. 中枢内相邻同向段力度衰减
    """
    if not latest_zs:
        return {
            "type": "none",
            "confidence": 0.0,
            "detail": "无中枢，不构成盘整背驰",
            "signals": []
        }

    # 取最后两段同向笔
    if len(strokes) < 3:
        return {"type": "none", "confidence": 0.0, "detail": "笔数不足", "signals": []}

    direction = strokes[-1]["type"]
    same_dir = [s for s in strokes if s["type"] == direction]

    if len(same_dir) < 2:
        return {"type": "none", "confidence": 0.0, "detail": "同向笔不足2段", "signals": []}

    s1 = same_dir[-2]
    s2 = same_dir[-1]

    pct1 = abs(s1["change_pct"])
    pct2 = abs(s2["change_pct"])
    price_ratio = pct2 / pct1 if pct1 > 0 else 1.0

    area1 = calc_macd_area(macd_data, s1["start_index"], s1["end_index"])
    area2 = calc_macd_area(macd_data, s2["start_index"], s2["end_index"])
    macd_ratio = area2 / area1 if area1 > 0 else 1.0

    signals = []
    score = 0
    if price_ratio < threshold:
        score += 1
        signals.append(f"盘整力度衰减: {pct1:.2f}% → {pct2:.2f}%")
    if macd_ratio < threshold:
        score += 1
        signals.append(f"MACD面积衰减: {area1:.2f} → {area2:.2f}")

    if score >= 2:
        return {
            "type": f"{'顶' if direction == 'up' else '底'}盘整背驰",
            "confidence": 0.7,
            "detail": f"中枢震荡中的{'顶' if direction == 'up' else '底'}背驰",
            "signals": signals,
            "metrics": {"price_ratio": round(price_ratio, 3), "macd_ratio": round(macd_ratio, 3)}
        }
    elif score == 1:
        return {
            "type": "weak_consolidation_divergence",
            "confidence": 0.3,
            "detail": "盘整弱背驰信号",
            "signals": signals,
            "metrics": {"price_ratio": round(price_ratio, 3), "macd_ratio": round(macd_ratio, 3)}
        }

    return {"type": "none", "confidence": 0.0, "detail": "未检测到盘整背驰", "signals": []}


def run_divergence_analysis(
    strokes_result: dict,
    segments_result: dict,
    zhongshu_result: dict,
    macd_result: dict
) -> dict:
    """背驰分析入口"""
    strokes = strokes_result.get("strokes", [])
    segments = segments_result.get("segments", [])
    zhongshu_list = zhongshu_result.get("stroke_level", {}).get("zhongshu", [])
    latest_zs = zhongshu_result.get("latest")
    klines_count = strokes_result.get("stroke_count", 0)

    trend_div = detect_trend_divergence(
        strokes, segments, zhongshu_list, macd_result, klines_count
    )
    cons_div = detect_consolidation_divergence(strokes, latest_zs, macd_result)

    # 取置信度更高的背驰
    if trend_div["confidence"] >= cons_div["confidence"]:
        primary = trend_div
        secondary = cons_div
    else:
        primary = cons_div
        secondary = trend_div

    return {
        "primary": primary,
        "secondary": secondary,
        "has_divergence": primary["confidence"] >= 0.5,
        "divergence_type": primary["type"],
        "confidence": primary["confidence"]
    }

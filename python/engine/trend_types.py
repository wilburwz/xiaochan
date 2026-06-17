"""
小缠 — 走势类型分类模块
基于缠中说禅理论：根据中枢数量判断走势类型

- 盘整：恰好一个中枢
- 上涨趋势：两个及以上中枢，中枢上移（ZG 递增）
- 下跌趋势：两个及以上中枢，中枢下移（ZG 递减）
"""

from typing import List


def classify_trend(zhongshu_list: List[dict]) -> dict:
    """
    根据中枢序列判断走势类型

    参数: zhongshu_list — 中枢列表，每个含 ZG, ZD
    返回: 走势类型和方向
    """
    count = len(zhongshu_list)

    if count == 0:
        return {
            "trend_type": "无中枢",
            "direction": "unknown",
            "zhongshu_count": 0,
            "description": "尚未形成可识别的走势结构"
        }
    elif count == 1:
        zs = zhongshu_list[0]
        return {
            "trend_type": "盘整",
            "direction": "consolidation",
            "zhongshu_count": 1,
            "zg": zs["ZG"],
            "zd": zs["ZD"],
            "mid": (zs["ZG"] + zs["ZD"]) / 2,
            "range_pct": round((zs["ZG"] - zs["ZD"]) / zs["ZD"] * 100, 2),
            "description": f"价格在 {zs['ZD']} ~ {zs['ZG']} 区间盘整"
        }
    else:
        # 检查中枢排列方向
        zg_values = [zs["ZG"] for zs in zhongshu_list]
        zd_values = [zs["ZD"] for zs in zhongshu_list]

        zg_rising = all(zg_values[i] < zg_values[i + 1] for i in range(len(zg_values) - 1))
        zg_falling = all(zg_values[i] > zg_values[i + 1] for i in range(len(zg_values) - 1))

        latest_zs = zhongshu_list[-1]
        first_zs = zhongshu_list[0]

        if zg_rising:
            return {
                "trend_type": "上涨趋势",
                "direction": "up",
                "zhongshu_count": count,
                "first_zg": first_zs["ZG"],
                "latest_zg": latest_zs["ZG"],
                "latest_zd": latest_zs["ZD"],
                "trend_strength": round((latest_zs["ZG"] - first_zs["ZG"]) / first_zs["ZG"] * 100, 2),
                "description": f"上涨趋势：{count}个中枢，ZG从{first_zs['ZG']}升至{latest_zs['ZG']}"
            }
        elif zg_falling:
            return {
                "trend_type": "下跌趋势",
                "direction": "down",
                "zhongshu_count": count,
                "first_zg": first_zs["ZG"],
                "latest_zg": latest_zs["ZG"],
                "latest_zd": latest_zs["ZD"],
                "trend_strength": round((latest_zs["ZG"] - first_zs["ZG"]) / first_zs["ZG"] * 100, 2),
                "description": f"下跌趋势：{count}个中枢，ZG从{first_zs['ZG']}降至{latest_zs['ZG']}"
            }
        else:
            return {
                "trend_type": "中枢扩张/扩展",
                "direction": "complex",
                "zhongshu_count": count,
                "first_zg": first_zs["ZG"],
                "latest_zg": latest_zs["ZG"],
                "latest_zd": latest_zs["ZD"],
                "description": f"中枢方向不明确，可能处于扩张或扩展中"
            }


def analyze_stroke_trend(strokes: List[dict]) -> dict:
    """分析笔的走势方向"""
    if not strokes:
        return {"direction": "unknown", "streak": 0}

    recent_dir = strokes[-1]["type"]
    # 计算连续同向笔数
    streak = 0
    for s in reversed(strokes):
        if s["type"] == recent_dir:
            streak += 1
        else:
            break

    # 整体偏多/偏空判断
    up_count = sum(1 for s in strokes if s["type"] == "up")
    down_count = sum(1 for s in strokes if s["type"] == "down")
    total = up_count + down_count

    bias = "neutral"
    if total > 0:
        up_ratio = up_count / total
        if up_ratio >= 0.6:
            bias = "bullish"
        elif up_ratio <= 0.4:
            bias = "bearish"

    return {
        "direction": recent_dir,
        "streak": streak,
        "up_count": up_count,
        "down_count": down_count,
        "bias": bias
    }


def run_trend_analysis(strokes_result: dict, zhongshu_result: dict) -> dict:
    """走势类型分析入口"""
    stroke_zs = zhongshu_result.get("stroke_level", {}).get("zhongshu", [])
    segment_zs = zhongshu_result.get("segment_level", {}).get("zhongshu", [])

    stroke_trend = classify_trend(stroke_zs)
    segment_trend = classify_trend(segment_zs)
    stroke_dir = analyze_stroke_trend(strokes_result.get("strokes", []))

    # 综合判断
    if segment_trend["direction"] in ("up", "down"):
        primary = segment_trend
    elif stroke_trend["direction"] in ("up", "down"):
        primary = stroke_trend
    else:
        primary = stroke_trend

    return {
        "primary": primary,
        "stroke_level": stroke_trend,
        "segment_level": segment_trend,
        "stroke_direction": stroke_dir,
        "overall_direction": primary["direction"],
        "summary": f"走势类型：{primary['trend_type']}，方向：{primary['direction']}"
    }

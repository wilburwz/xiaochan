"""
小缠 — 中枢识别模块
基于缠中说禅理论：中枢 = 至少连续三段次级别走势的重叠区间

ZG = min(三段的高点)   — 中枢上沿
ZD = max(三段的低点)   — 中枢下沿
ZG > ZD 时中枢成立
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Zhongshu:
    """中枢"""
    ZG: float     # 中枢上沿
    ZD: float     # 中枢下沿
    start_index: int
    end_index: int
    level: str    # "stroke_level" / "segment_level"
    segment_count: int


def find_zhongshu_from_strokes(strokes: List[dict], min_segments: int = 3) -> List[Zhongshu]:
    """从笔序列中寻找中枢"""
    if len(strokes) < min_segments:
        return []

    zhongshu_list = []
    i = 0

    while i <= len(strokes) - min_segments:
        window = strokes[i:i + min_segments]
        highs = []
        lows = []

        for s in window:
            if s["type"] == "up":
                highs.append(s["end_price"])
                lows.append(s["start_price"])
            else:
                highs.append(s["start_price"])
                lows.append(s["end_price"])

        ZG = round(min(highs), 4)
        ZD = round(max(lows), 4)

        if ZG > ZD:
            zhongshu_list.append(Zhongshu(
                ZG=ZG, ZD=ZD,
                start_index=window[0]["start_index"],
                end_index=window[-1]["end_index"],
                level="stroke_level",
                segment_count=min_segments
            ))
        i += 1

    return zhongshu_list


def find_zhongshu_from_segments(segments: List[dict], min_segments: int = 3) -> List[Zhongshu]:
    """从线段序列中寻找中枢"""
    if len(segments) < min_segments:
        return []

    zhongshu_list = []
    i = 0

    while i <= len(segments) - min_segments:
        window = segments[i:i + min_segments]
        highs = []
        lows = []

        for s in window:
            if s["direction"] == "up":
                highs.append(s["end_price"])
                lows.append(s["start_price"])
            else:
                highs.append(s["start_price"])
                lows.append(s["end_price"])

        ZG = round(min(highs), 4)
        ZD = round(max(lows), 4)

        if ZG > ZD:
            zhongshu_list.append(Zhongshu(
                ZG=ZG, ZD=ZD,
                start_index=window[0]["start_index"],
                end_index=window[-1]["end_index"],
                level="segment_level",
                segment_count=min_segments
            ))
        i += 1

    return zhongshu_list


def merge_overlapping_zhongshu(zhongshu_list: List[Zhongshu]) -> List[Zhongshu]:
    """合并重叠中枢（处理中枢扩展/扩张）"""
    if len(zhongshu_list) < 2:
        return zhongshu_list

    merged = [zhongshu_list[0]]
    for zs in zhongshu_list[1:]:
        prev = merged[-1]
        # 检查重叠：prev.ZD <= zs.ZG AND prev.ZG >= zs.ZD
        if zs.ZD <= prev.ZG and zs.ZG >= prev.ZD:
            prev.ZG = round(min(prev.ZG, zs.ZG), 4)
            prev.ZD = round(max(prev.ZD, zs.ZD), 4)
            prev.end_index = max(prev.end_index, zs.end_index)
            prev.segment_count += zs.segment_count
        else:
            merged.append(zs)

    return merged


def get_latest_zhongshu(merged: List[Zhongshu]) -> Optional[dict]:
    """获取最近一个中枢"""
    if not merged:
        return None
    latest = merged[-1]
    return {
        "ZG": latest.ZG,
        "ZD": latest.ZD,
        "mid": round((latest.ZG + latest.ZD) / 2, 4),
        "width_pct": round((latest.ZG - latest.ZD) / latest.ZD * 100, 2),
        "level": latest.level,
        "segments": latest.segment_count
    }


def run_zhongshu_analysis(strokes_result: dict, segments_result: dict) -> dict:
    """完整中枢分析入口"""
    stroke_zs = find_zhongshu_from_strokes(strokes_result.get("strokes", []))
    merged_stroke = merge_overlapping_zhongshu(stroke_zs)

    segment_zs = find_zhongshu_from_segments(segments_result.get("segments", []))
    merged_segment = merge_overlapping_zhongshu(segment_zs)

    return {
        "stroke_level": {
            "count": len(merged_stroke),
            "zhongshu": [
                {"ZG": zs.ZG, "ZD": zs.ZD, "mid": round((zs.ZG + zs.ZD) / 2, 4),
                 "segments": zs.segment_count}
                for zs in merged_stroke
            ]
        },
        "segment_level": {
            "count": len(merged_segment),
            "zhongshu": [
                {"ZG": zs.ZG, "ZD": zs.ZD, "mid": round((zs.ZG + zs.ZD) / 2, 4),
                 "segments": zs.segment_count}
                for zs in merged_segment
            ]
        },
        "latest": get_latest_zhongshu(merged_segment) or get_latest_zhongshu(merged_stroke),
        "price_in_zhongshu": {
            "stroke_level": _check_price_in_zs(
                strokes_result.get("strokes", []), merged_stroke
            ),
            "segment_level": _check_price_in_zs(
                segments_result.get("segments", []), merged_segment
            )
        }
    }


def _check_price_in_zs(items: List[dict], zs_list: List[Zhongshu]) -> dict:
    """判断当前价格相对于中枢的位置"""
    if not items or not zs_list:
        return {"position": "unknown"}

    latest_price = items[-1].get("end_price", 0)
    latest_zs = zs_list[-1]

    if latest_price >= latest_zs.ZG:
        return {"position": "above", "price": latest_price, "ZG": latest_zs.ZG}
    elif latest_price <= latest_zs.ZD:
        return {"position": "below", "price": latest_price, "ZD": latest_zs.ZD}
    else:
        return {"position": "inside", "price": latest_price,
                "ZG": latest_zs.ZG, "ZD": latest_zs.ZD}

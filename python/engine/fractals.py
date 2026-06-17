"""
小缠 — 分型识别模块
基于缠中说禅理论：顶分型、底分型识别及 K 线包含关系处理

核心规则：
- 顶分型：中间K线最高价最高，左右K线最高价较低
- 底分型：中间K线最低价最低，左右K线最低价较高
- 包含处理：相邻K线存在包含关系时，根据趋势方向合并
"""

from dataclasses import dataclass
from typing import List, Optional
import math


@dataclass
class KLine:
    """单根K线"""
    time: int          # 时间戳(ms)
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Fractal:
    """分型"""
    type: str          # "top" 或 "bottom"
    index: int         # 在K线列表中的位置
    bar: KLine         # 对应的K线（包含处理后的）
    original_index: int = -1  # 原始K线位置


def has_containment(k1: KLine, k2: KLine) -> bool:
    """判断两根K线是否存在包含关系"""
    return (k1.high >= k2.high and k1.low <= k2.low) or \
           (k1.high <= k2.high and k1.low >= k2.low)


def merge_kline(k1: KLine, k2: KLine, direction_up: bool) -> KLine:
    """
    合并两根有包含关系的K线
    direction_up=True: 向上趋势，取高高、低高
    direction_up=False: 向下趋势，取高低、低低
    """
    if direction_up:
        high = max(k1.high, k2.high)
        low = max(k1.low, k2.low)
    else:
        high = min(k1.high, k2.high)
        low = min(k1.low, k2.low)

    return KLine(
        time=k2.time,
        open=k1.open,
        high=high,
        low=low,
        close=k2.close,
        volume=k1.volume + k2.volume
    )


def process_containment(klines: List[KLine]) -> List[KLine]:
    """
    K线包含关系处理
    返回处理后的K线序列（不改变原始列表长度概念，合并包含的K线）
    """
    if len(klines) < 2:
        return klines.copy()

    result = [klines[0]]
    # 判断初始趋势方向
    i = 1
    while i < len(klines):
        current = klines[i]
        prev = result[-1]

        if has_containment(prev, current):
            # 确定方向
            if len(result) >= 2:
                direction_up = prev.high > result[-2].high
            else:
                # 只有两根时，按前一根的阴阳判断
                direction_up = prev.close >= prev.open

            merged = merge_kline(prev, current, direction_up)
            result[-1] = merged
        else:
            result.append(current)
        i += 1

    return result


def find_fractals(klines: List[KLine]) -> List[Fractal]:
    """
    在K线序列中寻找顶底分型
    注意：输入应为包含处理后的K线
    返回分型列表
    """
    if len(klines) < 3:
        return []

    fractals = []
    i = 1
    while i < len(klines) - 1:
        left, mid, right = klines[i - 1], klines[i], klines[i + 1]

        # 顶分型：中间最高价最高
        if mid.high > left.high and mid.high > right.high:
            fractals.append(Fractal(type="top", index=i, bar=mid))

        # 底分型：中间最低价最低
        elif mid.low < left.low and mid.low < right.low:
            fractals.append(Fractal(type="bottom", index=i, bar=mid))

        i += 1

    return fractals


def validate_fractals(fractals: List[Fractal]) -> List[Fractal]:
    """验证分型有效性：相邻分型不能同向"""
    if len(fractals) < 2:
        return fractals

    valid = [fractals[0]]
    for f in fractals[1:]:
        if f.type != valid[-1].type:
            valid.append(f)
    return valid


def run_fractal_analysis(klines: List[KLine]) -> dict:
    """
    完整的顶底分型分析流程
    返回：包含处理后的K线 + 顶底分型列表
    """
    merged = process_containment(klines)
    raw_fractals = find_fractals(merged)
    valid_fractals = validate_fractals(raw_fractals)

    return {
        "original_count": len(klines),
        "merged_count": len(merged),
        "merged_klines": merged,
        "fractals": [
            {
                "type": f.type,
                "index": f.index,
                "price": f.bar.high if f.type == "top" else f.bar.low,
                "time": f.bar.time
            }
            for f in valid_fractals
        ],
        "top_count": sum(1 for f in valid_fractals if f.type == "top"),
        "bottom_count": sum(1 for f in valid_fractals if f.type == "bottom")
    }

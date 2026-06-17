"""
小缠 — 笔的划分模块
基于缠中说禅理论：相邻顶底分型之间至少5根K线（含两端），
笔的高点取顶分型最高价，低点取底分型最低价

规则：
1. 笔必须顶底交替
2. 相邻顶底分型之间至少5根K线（含两端分型K线）
3. 向上的笔：底分型 → 顶分型
4. 向下的笔：顶分型 → 底分型
"""

from dataclasses import dataclass
from typing import List, Optional
from .fractals import Fractal, KLine


@dataclass
class Stroke:
    """一笔"""
    type: str           # "up" 或 "down"
    start_index: int    # 起始分型在K线列表中的位置
    end_index: int      # 结束分型在K线列表中的位置
    start_price: float  # 起点价格（底分型取最低价，顶分型取最高价）
    end_price: float    # 终点价格
    start_fractal: str  # 起始分型类型 "top" / "bottom"
    end_fractal: str    # 结束分型类型


def build_strokes(fractals: List[dict], klines_count: int,
                  min_bars: int = 5) -> List[Stroke]:
    """
    根据分型序列构建笔

    参数：
    - fractals: 分型列表 [{"type", "index", "price", "time"}]
    - klines_count: 原始K线总数
    - min_bars: 笔最少K线数（默认5根，含分型自身）
    """
    if len(fractals) < 2:
        return []

    strokes = []
    # 找到第一个分型作为起点
    pending = fractals[0]  # 当前持有的分型

    for i in range(1, len(fractals)):
        current = fractals[i]

        # 必须顶底交替
        if current["type"] == pending["type"]:
            # 同向分型：如果是顶分型，取更高的；底分型取更低的
            if current["type"] == "top" and current["price"] > pending["price"]:
                pending = current
            elif current["type"] == "bottom" and current["price"] < pending["price"]:
                pending = current
            continue

        # K线间距检查
        bar_distance = abs(current["index"] - pending["index"]) + 1
        if bar_distance < min_bars:
            # 间距不够，跳过此分型继续往后找
            continue

        # 构成一笔
        if pending["type"] == "bottom":
            stroke_type = "up"
            start_price = pending["price"]
            end_price = current["price"]
        else:
            stroke_type = "down"
            start_price = pending["price"]
            end_price = current["price"]

        strokes.append(Stroke(
            type=stroke_type,
            start_index=pending["index"],
            end_index=current["index"],
            start_price=start_price,
            end_price=end_price,
            start_fractal=pending["type"],
            end_fractal=current["type"]
        ))

        pending = current

    return strokes


def run_stroke_analysis(fractals: List[dict], klines_count: int,
                        min_bars: int = 5) -> dict:
    """
    完整的笔划分分析
    """
    strokes = build_strokes(fractals, klines_count, min_bars)

    # 计算每笔的涨跌幅
    stroke_details = []
    for s in strokes:
        if s.type == "up":
            pct = (s.end_price - s.start_price) / s.start_price * 100
        else:
            pct = (s.start_price - s.end_price) / s.start_price * 100 * -1

        stroke_details.append({
            "type": s.type,
            "start_index": s.start_index,
            "end_index": s.end_index,
            "start_price": round(s.start_price, 4),
            "end_price": round(s.end_price, 4),
            "change_pct": round(pct, 2),
            "bars": s.end_index - s.start_index + 1
        })

    return {
        "stroke_count": len(strokes),
        "strokes": stroke_details,
        "current_direction": strokes[-1].type if strokes else "unknown",
        "last_stroke_pct": stroke_details[-1]["change_pct"] if stroke_details else 0
    }

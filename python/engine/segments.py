"""
小缠 — 线段划分模块
基于缠中说禅理论的特征序列法划分线段

线段定义：至少连续三笔构成的走势段
向上线段：由向上笔开始，向下笔为特征序列
向下线段：由向下笔开始，向上笔为特征序列
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Segment:
    """线段"""
    direction: str    # "up" 或 "down"
    start_index: int  # 线段起始笔在K线列表中的位置
    end_index: int    # 线段结束笔在K线列表中的位置
    start_price: float
    end_price: float
    stroke_count: int  # 构成线段的笔数


def build_segments(strokes: List[dict]) -> List[Segment]:
    """
    用特征序列法从笔序列划分线段

    简化实现规则：
    - 初始方向由第一笔类型决定
    - 当反向笔连续出现2笔且第二笔幅度超过第一笔时，判定线段转折
    - 向上线段结束于最后的高点，向下线段结束于最后的低点
    """
    if len(strokes) < 3:
        return []

    segments = []
    direction = strokes[0]["type"]  # "up" 或 "down"
    seg_start_idx = strokes[0]["start_index"]
    seg_start_price = strokes[0]["start_price"]
    peak_price = seg_start_price  # 当前线段内极值
    reversal_count = 0

    for i in range(1, len(strokes)):
        s = strokes[i]

        # 更新线段内极值
        if direction == "up":
            peak_price = max(peak_price, s["end_price"])
        else:
            peak_price = min(peak_price, s["end_price"])

        # 检查反向笔
        if s["type"] != direction:
            reversal_count += 1
        else:
            # 同向笔出现，重置反转计数
            if reversal_count < 2:
                reversal_count = 0
            else:
                # 反转确认：线段在之前反向笔的起点处结束
                reversal_start = strokes[i - reversal_count]
                seg_end_price = reversal_start["start_price"]
                seg_end_idx = reversal_start["start_index"]

                segments.append(Segment(
                    direction=direction,
                    start_index=seg_start_idx,
                    end_index=seg_end_idx,
                    start_price=seg_start_price,
                    end_price=seg_end_price,
                    stroke_count=i - reversal_count + 1
                ))

                # 新线段开始
                direction = "down" if direction == "up" else "up"
                seg_start_idx = seg_end_idx
                seg_start_price = seg_end_price
                peak_price = seg_end_price
                reversal_count = 0

    # 最后一段未封闭的线段
    if segments:
        last = segments[-1]
        if last.end_index < strokes[-1]["end_index"] or \
           (last.direction == direction and last.start_index < strokes[-1]["start_index"]):
            # 还有剩余的笔，追加为最后一段
            final_end_price = strokes[-1]["end_price"]
            final_end_idx = strokes[-1]["end_index"]
            # 取线段方向上的极值终点
            if direction == "up":
                final_end_price = peak_price
            else:
                final_end_price = peak_price

            segments.append(Segment(
                direction=direction,
                start_index=seg_start_idx,
                end_index=final_end_idx,
                start_price=seg_start_price,
                end_price=final_end_price,
                stroke_count=sum(1 for _ in range(seg_start_idx, final_end_idx + 1) if True)
            ))

    if not segments:
        segments.append(Segment(
            direction=direction,
            start_index=strokes[0]["start_index"],
            end_index=strokes[-1]["end_index"],
            start_price=strokes[0]["start_price"],
            end_price=strokes[-1]["end_price"],
            stroke_count=len(strokes)
        ))

    return segments


def run_segment_analysis(strokes: List[dict]) -> dict:
    """线段分析入口"""
    segments = build_segments(strokes)

    segment_details = []
    for s in segments:
        pct = abs(s.end_price - s.start_price) / s.start_price * 100
        if s.direction == "down":
            pct = -pct

        segment_details.append({
            "direction": s.direction,
            "start_price": round(s.start_price, 4),
            "end_price": round(s.end_price, 4),
            "stroke_count": s.stroke_count,
            "change_pct": round(pct, 2),
            "start_index": s.start_index,
            "end_index": s.end_index
        })

    return {
        "segment_count": len(segments),
        "segments": segment_details,
        "current_direction": segments[-1].direction if segments else "unknown",
        "last_segment_pct": segment_details[-1]["change_pct"] if segment_details else 0
    }
